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