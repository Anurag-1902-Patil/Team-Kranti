"use client";

import React, { useState, useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";
import {
  Download,
  Upload,
  Filter,
  Search,
  RefreshCw,
  AlertTriangle,
  Calendar,
  Layers,
  CheckCircle2,
} from "lucide-react";
import { P6Gantt } from "@/components/P6Gantt";
import { useApp } from "@/lib/AppContext";
import { fetchGanttData, API_BASE, getAuthToken } from "@/lib/api";
import type { GanttDataResponse } from "@/lib/types";

function SchedulePageContent() {
  const searchParams = useSearchParams();
  const { openActivityDetail, selectedActivityId } = useApp();

  const [data, setData] = useState<GanttDataResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // Filters from query params or UI
  const [discipline, setDiscipline] = useState<string>(searchParams.get("discipline") || "");
  const [status, setStatus] = useState<string>(searchParams.get("status") || "");
  const [criticalOnly, setCriticalOnly] = useState<boolean>(searchParams.get("critical_only") === "true");
  const [search, setSearch] = useState<string>(searchParams.get("search") || "");

  // Import modal state
  const [importOpen, setImportOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await fetchGanttData({
        discipline: discipline || undefined,
        status: status || undefined,
        critical_only: criticalOnly || undefined,
        search: search || undefined,
      });
      setData(res);
    } catch (err) {
      console.error("Failed to load Gantt data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [discipline, status, criticalOnly, search]);

  const handleExportXER = () => {
    const token = getAuthToken();
    window.open(`${API_BASE}/api/v1/schedule/export-xer?token=${encodeURIComponent(token)}`, "_blank");
  };

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    setImportResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/api/v1/schedule/import`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getAuthToken()}`,
        },
        body: formData,
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`Import failed: ${errorText}`);
      }

      const json = await res.json();
      setImportResult(json.message || "Schedule imported successfully.");
      await loadData();
    } catch (err) {
      setImportResult(`Error: ${String(err)}`);
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-4">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-200 pb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs font-semibold text-zinc-900 bg-zinc-100 border border-zinc-300 px-2 py-0.5 rounded">
              Primavera P6 Level 5/6 Work Breakdown
            </span>
            <span className="text-zinc-400 text-xs">OIL-NE-2026</span>
          </div>
          <h1 className="text-lg font-bold text-zinc-900 tracking-tight">
            Project Master Schedule & Gantt Execution View
          </h1>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setImportOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-zinc-300 hover:bg-zinc-50 rounded text-xs font-medium text-zinc-700 transition-colors"
          >
            <Upload className="w-3.5 h-3.5 text-zinc-500" />
            <span>Import XER / Excel</span>
          </button>

          <button
            onClick={handleExportXER}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-700 hover:bg-blue-800 text-white rounded text-xs font-medium transition-colors shadow-none"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Updated XER</span>
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white border border-zinc-200 rounded-lg p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-3">
          {/* Discipline Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-zinc-500 font-medium">Discipline:</span>
            <select
              value={discipline}
              onChange={(e) => setDiscipline(e.target.value)}
              className="border border-zinc-300 rounded px-2 py-1 text-xs bg-white text-zinc-800 outline-none"
            >
              <option value="">All Disciplines</option>
              <option value="piping">Piping</option>
              <option value="civil">Civil</option>
              <option value="mechanical">Mechanical</option>
              <option value="electrical">Electrical</option>
              <option value="instrumentation">Instrumentation</option>
              <option value="structural">Structural</option>
            </select>
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-zinc-500 font-medium">Status:</span>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="border border-zinc-300 rounded px-2 py-1 text-xs bg-white text-zinc-800 outline-none"
            >
              <option value="">All Statuses</option>
              <option value="delayed">Delayed</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="not_started">Not Started</option>
            </select>
          </div>

          {/* Critical Path Toggle */}
          <label className="flex items-center gap-1.5 cursor-pointer select-none text-zinc-700 font-medium">
            <input
              type="checkbox"
              checked={criticalOnly}
              onChange={(e) => setCriticalOnly(e.target.checked)}
              className="rounded border-zinc-300 text-blue-600 focus:ring-0"
            />
            <span>Critical Path Only</span>
          </label>
        </div>

        {/* Search Box */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-2.5 top-2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search ID, name, WBS..."
              className="pl-8 pr-3 py-1 border border-zinc-300 rounded text-xs w-52 outline-none focus:border-blue-600"
            />
          </div>
          <button
            onClick={loadData}
            className="p-1.5 hover:bg-zinc-100 rounded text-zinc-500 transition-colors"
            title="Refresh Schedule"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Summary Stat Chips */}
      {data && data.summary && (
        <div className="flex items-center gap-4 text-xs font-mono text-zinc-500 px-1">
          <span>Total: <strong className="text-zinc-900">{data.summary.filtered_count}</strong> of {data.summary.total_activities} activities</span>
          <span>Completed: <strong className="text-emerald-700">{data.summary.completed_count}</strong></span>
          <span>In Progress: <strong className="text-amber-700">{data.summary.in_progress_count}</strong></span>
          <span>Delayed: <strong className="text-red-700">{data.summary.delayed_count}</strong></span>
          <span>Critical: <strong className="text-red-800">{data.summary.critical_count}</strong></span>
        </div>
      )}

      {/* P6 Interactive Gantt */}
      {loading && !data ? (
        <div className="bg-white border border-zinc-200 rounded-lg p-12 text-center text-zinc-400 text-xs">
          Loading Primavera P6 WBS schedule...
        </div>
      ) : data ? (
        <P6Gantt
          wbsTree={data.wbs_tree}
          activities={data.activities}
          dependencies={data.dependencies}
          onSelectActivity={openActivityDetail}
          selectedActivityId={selectedActivityId}
        />
      ) : (
        <div className="bg-white border border-zinc-200 rounded-lg p-12 text-center text-zinc-400 text-xs">
          No schedule activities found.
        </div>
      )}

      {/* Import Modal */}
      {importOpen && (
        <div className="fixed inset-0 bg-black/40 z-60 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg border border-zinc-200 p-5 max-w-md w-full space-y-4 shadow-xl">
            <h3 className="text-sm font-bold text-zinc-900">Import Primavera P6 Schedule</h3>
            <p className="text-xs text-zinc-500 leading-relaxed">
              Upload a Primavera P6 export file (<span className="font-mono font-semibold">.xer</span>) or an Excel activity table (<span className="font-mono">.xlsx</span>, <span className="font-mono">.csv</span>).
              Activities will be upserted into the schedule, and semantic matching embeddings will be rebuilt.
            </p>

            <input
              type="file"
              ref={fileInputRef}
              accept=".xer,.csv,.xlsx,.xls"
              onChange={handleImportFile}
              className="w-full text-xs file:mr-3 file:py-1.5 file:px-3 file:rounded file:border file:border-zinc-300 file:bg-zinc-50 file:text-xs file:font-medium hover:file:bg-zinc-100"
            />

            {importing && (
              <div className="text-xs text-blue-700 font-mono">
                Parsing schedule and reloading vector index...
              </div>
            )}

            {importResult && (
              <div className="text-xs text-emerald-800 bg-emerald-50 border border-emerald-200 p-2 rounded">
                {importResult}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2 border-t border-zinc-100">
              <button
                onClick={() => {
                  setImportOpen(false);
                  setImportResult(null);
                }}
                className="px-3 py-1.5 text-xs text-zinc-600 hover:bg-zinc-100 rounded"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function SchedulePage() {
  return (
    <React.Suspense fallback={<div className="p-8 text-center text-xs text-zinc-400">Loading schedule...</div>}>
      <SchedulePageContent />
    </React.Suspense>
  );
}
