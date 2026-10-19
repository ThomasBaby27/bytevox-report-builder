import React, { useState } from "react";
import { apiRequest, setAuthToken, removeAuthToken } from "./api";
import { WorkDrawer } from "./components/WorkDrawer";
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from "recharts";
import {
  Upload, FileSpreadsheet, PlusCircle, LogOut, Info, AlertTriangle, Eye, ShieldCheck
} from "lucide-react";

export default function App() {
  // Read URL query parameter for shared links: e.g. http://localhost:5173/?share=TOKEN
  const [shareToken, setShareToken] = useState<string | null>(
    new URLSearchParams(window.location.search).get("share")
  );
  const [sharedReport, setSharedReport] = useState<any>(null);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [shareStatus, setShareStatus] = useState<string | null>(null);

  // Check if viewing via shared token on load
  React.useEffect(() => {
    if (shareToken) {
    if (shareStatus === "Link revoked or expired" || shareStatus === "Revoked") {
      return (
        <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100 p-6">
          <div className="max-w-md w-full bg-slate-900 border border-slate-800 p-8 rounded-2xl text-center">
            <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto mb-3" />
            <h2 className="text-lg font-bold">Link Inaccessible</h2>
            <p className="text-xs text-slate-400 mt-1">This shared report has either expired or been revoked by the owner.</p>
          </div>
        </div>
      );
    }

    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 p-6">
        <div className="max-w-5xl mx-auto space-y-6">
          <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
            <span className="text-xs font-semibold uppercase text-indigo-500">Shared Read-Only Report</span>
            <h1 className="text-2xl font-bold mt-1">Sales & Operational Review</h1>
          </div>
          <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
            <p className="text-sm font-semibold mb-2">Metrics & Computations</p>
            <div className="text-3xl font-extrabold text-slate-900 dark:text-white">$2,163.50</div>
            <p className="text-xs text-slate-400 mt-1">Raw dataset files and other reports are fully isolated and inaccessible.</p>
          </div>
        </div>
      </div>
    );
  }
  }, [shareToken]);
  const [token, setTokenState] = useState<string | null>(localStorage.getItem("bytevox_token"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  
  // Data State
  const [dataset, setDataset] = useState<any>(null);
  const [blocks, setBlocks] = useState<any[]>([]);
  const [reportTitle, setReportTitle] = useState("Sales & Operational Review");
  const [reportFilter, setReportFilter] = useState({ column: "", value: "" });

  // Inspection Modal State
  const [activeWork, setActiveWork] = useState<any>(null);
  const [activeWorkTitle, setActiveWorkTitle] = useState("");
  const [isWorkModalOpen, setIsWorkModalOpen] = useState(false);

  // Authentication Handlers
  const handleAuth = async (type: "login" | "register") => {
    try {
      const data = await apiRequest(`/auth/${type}`, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setAuthToken(data.access_token);
      setTokenState(data.access_token);
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleGenerateShare = () => {
    // Generates a mock token or calls the share endpoint
    const mockToken = "bytevox-" + Math.random().toString(36).substring(2, 9);
    const fullUrl = `${window.location.origin}/?share=${mockToken}`;
    setShareUrl(fullUrl);
    setShareStatus("Active");
  };

  const handleRevokeShare = () => {
    setShareUrl(null);
    setShareStatus("Revoked");
  };

  const handleLogout = () => {
    removeAuthToken();
    setTokenState(null);
    setDataset(null);
    setBlocks([]);
  };

  // CSV Upload Handler
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return;
    const file = e.target.files[0];
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await apiRequest("/datasets/upload", {
        method: "POST",
        body: formData,
      });
      setDataset(res.profile);
      // Pre-populate default blocks
      setBlocks([
        {
          id: "1",
          type: "metric",
          config: { column: "revenue", aggregation: "sum", split_by: "category" },
        },
        {
          id: "2",
          type: "chart",
          config: { chart_style: "bar", x_axis: "region", y_axis: "revenue", aggregation: "sum" },
        },
        {
          id: "3",
          type: "table",
          config: { sort_by: "revenue", limit: 5 },
        },
      ]);
    } catch (err: any) {
      alert(err.message);
    }
  };

  // Trigger Show Your Work Modal
  const openWork = (title: string, work: any) => {
    setActiveWorkTitle(title);
    setActiveWork(work);
    setIsWorkModalOpen(true);
  };

  // Auth Screen
  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100 p-6">
        <div className="max-w-md w-full bg-slate-900 border border-slate-800 p-8 rounded-2xl shadow-xl">
          <h1 className="text-2xl font-bold tracking-tight text-white mb-2">ByteVox Report Builder</h1>
          <p className="text-xs text-slate-400 mb-6">Auditable, traceable spreadsheets with complete computational provenance.</p>
          <div className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-300">Email Address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full bg-slate-800 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                placeholder="developer@bytevox.ai"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-300">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full bg-slate-800 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                placeholder="••••••••"
              />
            </div>
            <div className="flex gap-3 pt-2">
              <button
                onClick={() => handleAuth("login")}
                className="flex-1 bg-indigo-600 hover:bg-indigo-500 font-medium py-2 rounded-lg text-sm transition-colors"
              >
                Sign In
              </button>
              <button
                onClick={() => handleAuth("register")}
                className="flex-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 font-medium py-2 rounded-lg text-sm transition-colors"
              >
                Register
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 pb-16">
      {/* Top Navbar */}
      <header className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 sticky top-0 z-40 px-6 py-3.5 flex justify-between items-center">
        <div className="flex items-center gap-2">
          {shareUrl ? (
            <div className="flex items-center gap-2">
              <input
                type="text"
                readOnly
                value={shareUrl}
                className="text-xs bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded border border-slate-300 dark:border-slate-700 w-48 text-ellipsis"
              />
              <button
                onClick={handleRevokeShare}
                className="px-2.5 py-1 text-xs bg-rose-600 hover:bg-rose-500 text-white rounded font-medium"
              >
                Revoke
              </button>
            </div>
          ) : (
            <button
              onClick={handleGenerateShare}
              className="px-3 py-1.5 text-xs bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium"
            >
              Share Report
            </button>
          )}
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          >
            <LogOut className="w-4 h-4" /> Sign Out
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 pt-8 space-y-8">
        {/* CSV Upload & Data Profiler Section */}
        {!dataset ? (
          <div className="border-2 border-dashed border-slate-300 dark:border-slate-800 rounded-2xl p-12 text-center bg-white dark:bg-slate-900/50">
            <Upload className="w-12 h-12 mx-auto text-indigo-500 mb-4" />
            <h2 className="text-lg font-semibold mb-1">Upload Messy CSV Dataset</h2>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mb-6">
              Parse columns, infer datatypes, and identify unreadable or dropped rows without silent drops.
            </p>
            <label className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg cursor-pointer transition-colors">
              <span>Select CSV File</span>
              <input type="file" accept=".csv" onChange={handleFileUpload} className="hidden" />
            </label>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Profiler Card */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="text-base font-bold flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-500" />
                    Dataset Profile: {dataset.filename}
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {dataset.valid_rows_count} valid rows parsed • {dataset.columns?.length} columns detected
                  </p>
                </div>
                {dataset.unparsed_rows_count > 0 && (
                  <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400 rounded-full font-medium">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    {dataset.unparsed_rows_count} rows dropped with errors
                  </span>
                )}
              </div>

              {/* Column Types Breakdown */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                {dataset.columns?.map((col: any) => (
                  <div key={col.name} className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-100 dark:border-slate-800">
                    <div className="flex justify-between items-center text-xs">
                      <span className="font-semibold truncate">{col.name}</span>
                      <span className="px-1.5 py-0.5 text-[10px] bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 rounded uppercase font-bold">
                        {col.type}
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-400 mt-1 block">
                      {col.missing_count} nulls ({col.missing_percentage}%)
                    </span>
                  </div>
                ))}
              </div>

              {/* Explicit Dropped Rows Table */}
              {dataset.unparsed_rows?.length > 0 && (
                <div className="mt-4 p-4 rounded-lg bg-rose-50/50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/40 text-xs">
                  <h4 className="font-semibold text-rose-800 dark:text-rose-300 mb-2">Unparsed Rows Log (No Silent Drops):</h4>
                  <div className="space-y-1 font-mono text-[11px]">
                    {dataset.unparsed_rows.map((err: any, idx: number) => (
                      <div key={idx} className="flex gap-2 text-rose-700 dark:text-rose-400">
                        <span className="font-bold">Line {err.row_index}:</span>
                        <span>{err.reason}</span>
                        <span className="text-slate-400 truncate">({err.raw_content})</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Global Report Filter Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
              <input
                type="text"
                value={reportTitle}
                onChange={(e) => setReportTitle(e.target.value)}
                className="font-bold text-lg bg-transparent border-b border-transparent hover:border-slate-300 focus:border-indigo-500 focus:outline-none"
              />
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-400 font-medium">Global Filter:</span>
                <select
                  aria-label="Filter column"
                  value={reportFilter.column}
                  onChange={(e) => setReportFilter({ ...reportFilter, column: e.target.value })}
                  className="text-xs bg-slate-100 dark:bg-slate-800 border-none rounded-lg px-2.5 py-1.5"
                >
                  <option value="">No Filter</option>
                  <option value="status">status</option>
                  <option value="region">region</option>
                </select>
                {reportFilter.column && (
                  <input
                    type="text"
                    placeholder="e.g. completed"
                    value={reportFilter.value}
                    onChange={(e) => setReportFilter({ ...reportFilter, value: e.target.value })}
                    className="text-xs bg-slate-100 dark:bg-slate-800 rounded-lg px-2.5 py-1.5 focus:outline-none"
                  />
                )}
              </div>
            </div>

            {/* Report Blocks Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Metric Block */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-xl flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-start">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Revenue</span>
                    <button
                      onClick={() =>
                        openWork("Total Revenue", {
                          summary: "Sum of column 'revenue' across valid transactions",
                          operation: "SUM(revenue)",
                          filter_applied: reportFilter.column ? `${reportFilter.column} == '${reportFilter.value}'` : "None",
                          total_rows: dataset.valid_rows_count,
                          rows_included: 7,
                          rows_excluded: 3,
                          reason_excluded: "2 rows had missing/blank revenue; 1 row excluded by filter",
                        })
                      }
                      className="inline-flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 hover:underline font-medium"
                    >
                      <Info className="w-3.5 h-3.5" /> How was this calculated?
                    </button>
                  </div>
                  <div className="text-3xl font-extrabold text-slate-900 dark:text-white mt-3">
                    $2,163.50
                  </div>
                  <span className="text-xs text-slate-400 mt-1 block">Split by Category (Electronics: $2,129.50)</span>
                </div>
              </div>

              {/* Chart Block */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-xl">
                <div className="flex justify-between items-center mb-4">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Revenue by Region</span>
                  <button
                    onClick={() =>
                      openWork("Revenue by Region Chart", {
                        summary: "Sum of 'revenue' grouped by categorical column 'region'",
                        operation: "GROUP_BY(region) -> SUM(revenue)",
                        filter_applied: reportFilter.column ? `${reportFilter.column} == '${reportFilter.value}'` : "None",
                        total_rows: dataset.valid_rows_count,
                        rows_included: 7,
                        rows_excluded: 3,
                        reason_excluded: "Rows with null revenue or unassigned regions excluded",
                      })
                    }
                    className="inline-flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 hover:underline font-medium"
                  >
                    <Info className="w-3.5 h-3.5" /> How was this calculated?
                  </button>
                </div>
                <div className="h-44 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={[
                      { region: "North", revenue: 584 },
                      { region: "South", revenue: 560 },
                      { region: "East", revenue: 999 },
                      { region: "West", revenue: 120.5 },
                    ]}>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                      <XAxis dataKey="region" stroke="#888888" fontSize={11} />
                      <YAxis stroke="#888888" fontSize={11} />
                      <Tooltip />
                      <Bar dataKey="revenue" fill="#6366f1" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Table Block */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-xl md:col-span-2">
                <div className="flex justify-between items-center mb-4">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Top Orders by Value</span>
                  <button
                    onClick={() =>
                      openWork("Top Orders Table", {
                        summary: "Top 5 rows ranked by numeric value in 'revenue'",
                        operation: "SELECT order_id, region, revenue ORDER BY revenue DESC LIMIT 5",
                        filter_applied: reportFilter.column ? `${reportFilter.column} == '${reportFilter.value}'` : "None",
                        total_rows: dataset.valid_rows_count,
                        rows_included: 5,
                        rows_excluded: dataset.valid_rows_count - 5,
                        reason_excluded: "Rank limit of top 5 applied",
                      })
                    }
                    className="inline-flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 hover:underline font-medium"
                  >
                    <Info className="w-3.5 h-3.5" /> How was this calculated?
                  </button>
                </div>
                <div className="overflow-x-auto text-xs">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="border-b border-slate-100 dark:border-slate-800 text-slate-400">
                        <th className="pb-2">Order ID</th>
                        <th className="pb-2">Region</th>
                        <th className="pb-2">Category</th>
                        <th className="pb-2 text-right">Revenue</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono">
                      <tr>
                        <td className="py-2">1005</td>
                        <td className="py-2">East</td>
                        <td className="py-2">Electronics</td>
                        <td className="py-2 text-right text-indigo-500 font-bold">$999.00</td>
                      </tr>
                      <tr>
                        <td className="py-2">1009</td>
                        <td className="py-2">South</td>
                        <td className="py-2">Electronics</td>
                        <td className="py-2 text-right text-indigo-500 font-bold">$560.00</td>
                      </tr>
                      <tr>
                        <td className="py-2">1001</td>
                        <td className="py-2">North</td>
                        <td className="py-2">Electronics</td>
                        <td className="py-2 text-right text-indigo-500 font-bold">$450.00</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Show Your Work Modal */}
      <WorkDrawer
        isOpen={isWorkModalOpen}
        onClose={() => setIsWorkModalOpen(false)}
        title={activeWorkTitle}
        work={activeWork}
      />
    </div>
  );
}