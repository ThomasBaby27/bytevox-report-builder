import io
import csv
import json
from typing import Dict, Any, List, Tuple
import pandas as pd

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit

def guess_column_type(series: pd.Series) -> str:
    # Drop nulls/blanks to evaluate actual data
    non_null = series.dropna().astype(str).str.strip()
    non_null = non_null[non_null != ""]
    
    if len(non_null) == 0:
        return "text"

    # 1. Check Numeric
    numeric_count = pd.to_numeric(non_null, errors="coerce").notnull().sum()
    if numeric_count / len(non_null) >= 0.8:
        return "number"

    # 2. Check Date (must avoid guessing plain short numbers as dates)
    date_count = 0
    sample = non_null.head(100)
    for val in sample:
        if len(val) >= 4 and not val.isdigit():
            try:
                pd.to_datetime(val)
                date_count += 1
            except Exception:
                pass
    if date_count / len(sample) >= 0.7:
        return "date"

    # 3. Check Category: low cardinality (<= 20 unique values or < 20% of rows)
    unique_ratio = non_null.nunique() / len(non_null)
    if non_null.nunique() <= 20 or unique_ratio < 0.2:
        return "category"

    return "text"

def parse_and_profile_csv(file_bytes: bytes, filename: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    # Decode bytes safely
    try:
        content = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            content = file_bytes.decode("latin-1")
        except Exception:
            raise ValueError("File encoding not supported. Please upload a valid UTF-8 or Latin-1 encoded CSV.")

    lines = content.splitlines()
    if not lines:
        raise ValueError("The uploaded CSV file is empty.")

    # Detect delimiter
    sample_text = "\n".join(lines[:10])
    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters=",\t;|")
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ","

    reader = csv.reader(lines, delimiter=delimiter)
    try:
        header = next(reader)
    except StopIteration:
        raise ValueError("CSV has no rows or headers.")

    cleaned_header = [col.strip() for col in header]
    expected_col_count = len(cleaned_header)

    valid_rows = []
    unparsed_rows = []

    for idx, row in enumerate(reader, start=2):  # Line 1 is header
        if not row or all(field.strip() == "" for field in row):
            continue  # skip completely blank lines
        
        if len(row) != expected_col_count:
            unparsed_rows.append({
                "row_index": idx,
                "raw_content": delimiter.join(row),
                "reason": f"Expected {expected_col_count} columns, found {len(row)} columns."
            })
        else:
            cleaned_row = {cleaned_header[i]: row[i].strip() for i in range(expected_col_count)}
            valid_rows.append(cleaned_row)

    if not valid_rows:
        raise ValueError("No valid rows could be extracted from the CSV file.")

    df = pd.DataFrame(valid_rows)

    # Calculate profiling metadata per column
    columns_metadata = []
    for col in cleaned_header:
        series = df[col].replace("", None)
        col_type = guess_column_type(series)
        missing_count = series.isnull().sum()
        columns_metadata.append({
            "name": col,
            "type": col_type,
            "missing_count": int(missing_count),
            "missing_percentage": round((float(missing_count) / len(df)) * 100, 2)
        })

    profile = {
        "filename": filename,
        "total_rows_read": len(lines) - 1,
        "valid_rows_count": len(valid_rows),
        "unparsed_rows_count": len(unparsed_rows),
        "columns": columns_metadata,
        "unparsed_rows": unparsed_rows
    }

    return profile, valid_rows, unparsed_rows

def compute_block_calculation(
    rows: List[Dict[str, Any]],
    block_type: str,
    config: Dict[str, Any],
    global_filter: Dict[str, Any] = None
) -> Dict[str, Any]:
    df = pd.DataFrame(rows)
    total_raw_rows = len(df)

    if total_raw_rows == 0:
        return {
            "value": None,
            "work": {
                "summary": "No data available in dataset",
                "operation": "None",
                "filter_applied": "None",
                "total_rows": 0,
                "rows_included": 0,
                "rows_excluded": 0,
                "reason_excluded": "Dataset is empty"
            }
        }

    # 1. Apply Global Filters
    filter_desc = []
    filtered_df = df.copy()

    if global_filter:
        col = global_filter.get("column")
        val = global_filter.get("value")
        op = global_filter.get("operator", "equals")

        if col and val is not None and col in filtered_df.columns:
            initial_count = len(filtered_df)
            if op == "equals":
                filtered_df = filtered_df[filtered_df[col].astype(str) == str(val)]
                filter_desc.append(f"{col} == '{val}'")
            elif op == "date_from":
                parsed_dates = pd.to_datetime(filtered_df[col], errors="coerce")
                filtered_df = filtered_df[parsed_dates >= pd.to_datetime(val)]
                filter_desc.append(f"{col} >= '{val}'")
            elif op == "date_to":
                parsed_dates = pd.to_datetime(filtered_df[col], errors="coerce")
                filtered_df = filtered_df[parsed_dates <= pd.to_datetime(val)]
                filter_desc.append(f"{col} <= '{val}'")

    rows_after_filter = len(filtered_df)
    filter_dropped = total_raw_rows - rows_after_filter
    filter_applied_str = " AND ".join(filter_desc) if filter_desc else "None"

    # 2. Text block handling
    if block_type == "text":
        return {
            "content": config.get("content", ""),
            "work": {
                "summary": "Static text note",
                "operation": "Text render",
                "filter_applied": filter_applied_str,
                "total_rows": total_raw_rows,
                "rows_included": rows_after_filter,
                "rows_excluded": filter_dropped,
                "reason_excluded": f"{filter_dropped} rows filtered out by report filter" if filter_dropped else "None"
            }
        }

    # 3. Metric block handling
    if block_type == "metric":
        target_col = config.get("column")
        agg_func = config.get("aggregation", "sum").lower()
        split_by = config.get("split_by")

        if not target_col or target_col not in filtered_df.columns:
            raise ValueError(f"Column '{target_col}' not found.")

        if agg_func == "count":
            valid_series = filtered_df[target_col].dropna().replace("", None).dropna()
            numeric_dropped = rows_after_filter - len(valid_series)
            val = len(valid_series)
            op_label = f"COUNT({target_col})"
        else:
            numeric_series = pd.to_numeric(filtered_df[target_col], errors="coerce")
            valid_df = filtered_df[numeric_series.notnull()].copy()
            valid_df["_numeric"] = numeric_series[numeric_series.notnull()]
            numeric_dropped = rows_after_filter - len(valid_df)

            if agg_func == "sum":
                val = round(float(valid_df["_numeric"].sum()), 2)
                op_label = f"SUM({target_col})"
            elif agg_func == "average":
                val = round(float(valid_df["_numeric"].mean()), 2) if len(valid_df) > 0 else 0
                op_label = f"AVG({target_col})"
            elif agg_func == "min":
                val = round(float(valid_df["_numeric"].min()), 2) if len(valid_df) > 0 else 0
                op_label = f"MIN({target_col})"
            elif agg_func == "max":
                val = round(float(valid_df["_numeric"].max()), 2) if len(valid_df) > 0 else 0
                op_label = f"MAX({target_col})"
            else:
                raise ValueError(f"Unsupported aggregation: {agg_func}")

        # Optional split_by handling
        breakdown = []
        if split_by and split_by in filtered_df.columns:
            if agg_func == "count":
                grouped = filtered_df.groupby(split_by)[target_col].count()
            else:
                grouped = valid_df.groupby(split_by)["_numeric"].agg(agg_func)
            breakdown = [{"category": str(k), "value": round(float(v), 2)} for k, v in grouped.items()]

        total_excluded = filter_dropped + numeric_dropped
        reason = []
        if filter_dropped > 0:
            reason.append(f"{filter_dropped} rows excluded by filter '{filter_applied_str}'")
        if numeric_dropped > 0:
            reason.append(f"{numeric_dropped} rows excluded due to null or non-numeric values in '{target_col}'")

        return {
            "value": val,
            "breakdown": breakdown,
            "work": {
                "summary": f"{agg_func.capitalize()} of '{target_col}'" + (f" grouped by '{split_by}'" if split_by else ""),
                "operation": op_label,
                "filter_applied": filter_applied_str,
                "total_rows": total_raw_rows,
                "rows_included": total_raw_rows - total_excluded,
                "rows_excluded": total_excluded,
                "reason_excluded": "; ".join(reason) if reason else "None (all rows valid)"
            }
        }

    # 4. Chart block handling (Bar / Line)
    if block_type == "chart":
        x_col = config.get("x_axis")
        y_col = config.get("y_axis")
        agg_func = config.get("aggregation", "sum").lower()

        if not x_col or not y_col:
            raise ValueError("Chart requires both x_axis and y_axis columns.")

        numeric_y = pd.to_numeric(filtered_df[y_col], errors="coerce")
        valid_df = filtered_df[numeric_y.notnull()].copy()
        valid_df["_val"] = numeric_y[numeric_y.notnull()]
        numeric_dropped = rows_after_filter - len(valid_df)

        if agg_func == "sum":
            grouped = valid_df.groupby(x_col)["_val"].sum()
        elif agg_func == "average":
            grouped = valid_df.groupby(x_col)["_val"].mean()
        elif agg_func == "count":
            grouped = valid_df.groupby(x_col)["_val"].count()
        else:
            grouped = valid_df.groupby(x_col)["_val"].sum()

        data_points = [{"label": str(k), "value": round(float(v), 2)} for k, v in grouped.items()][:20]
        total_excluded = filter_dropped + numeric_dropped

        return {
            "chart_type": config.get("chart_style", "bar"),
            "data": data_points,
            "work": {
                "summary": f"{agg_func.capitalize()} of '{y_col}' by '{x_col}'",
                "operation": f"GROUP_BY({x_col}) -> {agg_func.upper()}({y_col})",
                "filter_applied": filter_applied_str,
                "total_rows": total_raw_rows,
                "rows_included": total_raw_rows - total_excluded,
                "rows_excluded": total_excluded,
                "reason_excluded": f"{filter_dropped} excluded by filter; {numeric_dropped} excluded due to non-numeric '{y_col}'"
            }
        }

    # 5. Table block handling (Top N rows)
    if block_type == "table":
        sort_by = config.get("sort_by")
        limit = int(config.get("limit", 5))

        clean_table_df = filtered_df.copy()
        if sort_by and sort_by in clean_table_df.columns:
            # Try numeric sort first, fallback to string sort
            numeric_sort = pd.to_numeric(clean_table_df[sort_by], errors="coerce")
            if numeric_sort.notnull().sum() > 0:
                clean_table_df["_sort"] = numeric_sort
                clean_table_df = clean_table_df.sort_values(by="_sort", ascending=False).drop(columns=["_sort"])
            else:
                clean_table_df = clean_table_df.sort_values(by=sort_by, ascending=False)

        top_rows = clean_table_df.head(limit).to_dict(orient="records")

        return {
            "rows": top_rows,
            "work": {
                "summary": f"Top {limit} rows sorted by '{sort_by}'",
                "operation": f"SELECT * ORDER BY {sort_by} DESC LIMIT {limit}",
                "filter_applied": filter_applied_str,
                "total_rows": total_raw_rows,
                "rows_included": rows_after_filter,
                "rows_excluded": filter_dropped,
                "reason_excluded": f"{filter_dropped} rows excluded by filter" if filter_dropped else "None"
            }
        }

    raise ValueError(f"Unknown block type '{block_type}'")