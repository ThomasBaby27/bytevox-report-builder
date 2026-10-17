import React from "react";
import { X, Calculator, Filter, AlertCircle, CheckCircle2 } from "lucide-react";

interface WorkMetadata {
  summary: string;
  operation: string;
  filter_applied: string;
  total_rows: number;
  rows_included: number;
  rows_excluded: number;
  reason_excluded: string;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  work: WorkMetadata | null;
}

export const WorkDrawer: React.FC<Props> = ({ isOpen, onClose, title, work }) => {
  if (!isOpen || !work) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl max-w-lg w-full overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 px-6 py-4">
          <div className="flex items-center gap-2">
            <Calculator className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            <h3 className="font-semibold text-slate-800 dark:text-slate-100 text-base">
              Calculation Provenance: {title}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded-md"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-5 text-sm text-slate-600 dark:text-slate-300">
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">Plain English Explanation</label>
            <p className="mt-1 font-medium text-slate-900 dark:text-slate-100 text-base">
              {work.summary}
            </p>
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">Underlying Query / Operation</label>
            <div className="mt-1 bg-slate-900 text-indigo-300 font-mono text-xs p-3 rounded-lg overflow-x-auto">
              <code>{work.operation}</code>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" /> Filter Context
            </label>
            <p className="mt-1 font-mono text-xs bg-slate-100 dark:bg-slate-800 p-2.5 rounded-lg text-slate-800 dark:text-slate-200">
              {work.filter_applied}
            </p>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-lg border border-slate-100 dark:border-slate-800 text-center">
              <span className="text-xs text-slate-400 block">Total Input</span>
              <span className="text-lg font-bold text-slate-800 dark:text-slate-100">{work.total_rows}</span>
            </div>
            <div className="p-3 bg-emerald-50 dark:bg-emerald-950/30 rounded-lg border border-emerald-100 dark:border-emerald-900/50 text-center">
              <span className="text-xs text-emerald-600 dark:text-emerald-400 flex items-center justify-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Included
              </span>
              <span className="text-lg font-bold text-emerald-700 dark:text-emerald-300">{work.rows_included}</span>
            </div>
            <div className="p-3 bg-rose-50 dark:bg-rose-950/30 rounded-lg border border-rose-100 dark:border-rose-900/50 text-center">
              <span className="text-xs text-rose-600 dark:text-rose-400 flex items-center justify-center gap-1">
                <AlertCircle className="w-3 h-3" /> Excluded
              </span>
              <span className="text-lg font-bold text-rose-700 dark:text-rose-300">{work.rows_excluded}</span>
            </div>
          </div>

          {work.rows_excluded > 0 && (
            <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/50 text-amber-800 dark:text-amber-300 text-xs">
              <span className="font-semibold block mb-0.5">Why rows were excluded:</span>
              {work.reason_excluded}
            </div>
          )}
        </div>

        <div className="bg-slate-50 dark:bg-slate-800/50 px-6 py-3 border-t border-slate-100 dark:border-slate-800 text-right">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white dark:bg-slate-200 dark:text-slate-900 font-medium text-xs rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};