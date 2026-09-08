"use client";

import { useState, useEffect, useRef } from "react";
import { apiFetch, API_BASE, getAuthToken } from "@/lib/api";
import type { PlanActivity } from "@/lib/types";
import { DisciplineChip } from "@/components/ConfidenceBadge";
import { Download, Upload, BarChart2, Calendar, CheckCircle, AlertCircle } from "lucide-react";

interface ActivityList {
  total: number;
  page: number;
  page_size: number;
  items: PlanActivity[];
}

export default function SchedulePage() {
  const [activities, setActivities] = useState<ActivityList | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [discipline, setDiscipline] = useState("all");
  const [exporting, setExporting] = useState(false);
  const [exportMsg, setExportMsg] = useState("");
  const [importing, setImporting] = useState(false);
  const [importMsg, setImportMsg] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function load() {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: "1", page_size: "30" });
      if (discipline !== "all") params.set("discipline", discipline);
      if (search.trim()) params.set("search", search.trim());
      const data = await apiFetch<ActivityList>(`/api/v1/schedule/activities?${params}`);
      setActivities(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [discipline, search]);

  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    setImportMsg("");
    setExportMsg("");
    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API_BASE}/api/v1/schedule/import`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getAuthToken()}`,
        },
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errData.detail || "Import failed");
      }

      const data = await res.json();
      setImportMsg(`✓ ${data.message || `Imported ${data.total} activities successfully from ${file.name}`}`);
      await load();
    } catch (err: any) {
      setImportMsg(`Error: ${err.message || String(err)}`);
    } finally {
      setImporting(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  async function exportXer() {
    setExporting(true);
    setExportMsg("");
    setImportMsg("");
    try {
      const res = await fetch(`${API_BASE}/api/v1/schedule/export-xer`, {
        headers: { Authorization: `Bearer ${getAuthToken()}` },
      });
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "sih26122_updated_schedule.xer";
      a.click();
      URL.revokeObjectURL(url);
      setExportMsg("✓ XER downloaded successfully.");
    } catch (e) {
      setExportMsg(`Error: ${String(e)}`);
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold gradient-text">Schedule</h1>
          <p className="text-sm text-gray-500 mt-1">Plan activities with validated actuals applied.</p>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            accept=".xer,.csv,.xlsx,.xls"
            className="hidden"
            id="import-schedule-input"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 text-gray-200 border border-gray-700 text-sm font-medium hover:bg-gray-700 hover:text-white disabled:opacity-50 transition-colors shadow-sm"
            id="import-schedule-btn"
            title="Import Primavera P6 (.xer) or Schedule spreadsheet (.csv, .xlsx)"
          >
            <Upload className="w-4 h-4 text-violet-400" />
            {importing ? "Importing..." : "Import Schedule"}
          </button>
          <button
            onClick={exportXer}
            disabled={exporting}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-violet-600 text-white text-sm font-medium hover:bg-violet-500 disabled:opacity-50 transition-colors shadow-sm"
            id="export-xer-btn"
          >
            <Download className="w-4 h-4" />
            {exporting ? "Generating..." : "Export XER"}
          </button>
        </div>
      </div>

      {(importMsg || exportMsg) && (
        <div className="space-y-1">
          {importMsg && (
            <div className={`p-3 rounded-lg flex items-center gap-2 text-sm border ${
              importMsg.startsWith("✓")
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                : "bg-rose-500/10 border-rose-500/30 text-rose-400"
            }`}>
              {importMsg.startsWith("✓") ? (
                <CheckCircle className="w-4 h-4 flex-shrink-0 text-emerald-400" />
              ) : (
                <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400" />
              )}
              <span>{importMsg}</span>
            </div>
          )}
          {exportMsg && (
            <div className={`p-3 rounded-lg flex items-center gap-2 text-sm border ${
              exportMsg.startsWith("✓")
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                : "bg-rose-500/10 border-rose-500/30 text-rose-400"
            }`}>
              {exportMsg.startsWith("✓") ? (
                <CheckCircle className="w-4 h-4 flex-shrink-0 text-emerald-400" />
              ) : (
                <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400" />
              )}
              <span>{exportMsg}</span>
            </div>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="glass-card p-4 flex flex-wrap gap-4 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="text-xs text-gray-500 block mb-1 uppercase tracking-wide font-medium">Search</label>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search activity name..."
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-violet-500"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1 uppercase tracking-wide font-medium">Discipline</label>
          <select
            value={discipline}
            onChange={(e) => setDiscipline(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-violet-500"
          >
            <option value="all">All</option>
            {["piping","civil","electrical","instrumentation","hse","structural","mechanical"].map(d => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Activities Table */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-gray-400" />
            <span className="text-sm font-medium text-white">
              {activities ? `${activities.total} activities` : "Loading..."}
            </span>
          </div>
          <p className="text-xs text-gray-600">Sorted by planned start</p>
        </div>

        {loading ? (
          <div className="p-10 text-center text-gray-500 text-sm">Loading activities...</div>
        ) : !activities || activities.items.length === 0 ? (
          <div className="p-12 text-center text-gray-500 text-sm space-y-3">
            <Calendar className="w-10 h-10 text-gray-600 mx-auto" />
            <p className="text-base text-gray-300 font-medium">No schedule activities found</p>
            <p className="text-sm text-gray-500 max-w-md mx-auto">
              Import a Primavera P6 (.xer) file or a schedule spreadsheet (.csv, .xlsx) to load plan activities and begin tracking progress.
            </p>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-violet-600 text-white text-sm font-medium hover:bg-violet-500 transition-colors"
            >
              <Upload className="w-4 h-4" />
              Import Schedule File
            </button>
          </div>
        ) : (
          <table className="w-full text-xs">
            <thead className="bg-gray-800/40 border-b border-gray-800">
              <tr className="text-gray-500 uppercase tracking-wide">
                <th className="text-left px-4 py-3 font-medium">ID</th>
                <th className="text-left px-4 py-3 font-medium">Activity Name</th>
                <th className="text-left px-4 py-3 font-medium">Discipline</th>
                <th className="text-left px-4 py-3 font-medium">Planned Start</th>
                <th className="text-left px-4 py-3 font-medium">Planned Finish</th>
                <th className="text-left px-4 py-3 font-medium">Actuals</th>
                <th className="text-left px-4 py-3 font-medium">Type</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/40">
              {activities.items.map((act) => (
                <tr key={act.id} className="hover:bg-gray-800/30 transition-colors">
                  <td className="px-4 py-3 font-mono text-gray-500 text-[11px]">{act.activity_id}</td>
                  <td className="px-4 py-3 text-gray-200 max-w-[250px]">
                    <p className="truncate">{act.activity_name}</p>
                    {act.wbs_code && <p className="text-gray-700 text-[10px]">{act.wbs_code}</p>}
                  </td>
                  <td className="px-4 py-3">
                    <DisciplineChip discipline={act.discipline || "unknown"} />
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {act.planned_start ? new Date(act.planned_start).toLocaleDateString() : "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {act.planned_finish ? new Date(act.planned_finish).toLocaleDateString() : "—"}
                  </td>
                  <td className="px-4 py-3">
                    {act.actual_start || act.actual_percent_complete !== null ? (
                      <div className="flex items-center gap-1">
                        <CheckCircle className="w-3 h-3 text-emerald-500" />
                        <span className="text-emerald-400">
                          {act.actual_percent_complete !== null
                            ? `${act.actual_percent_complete}%`
                            : "Started"}
                        </span>
                      </div>
                    ) : (
                      <span className="text-gray-700">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {act.is_field_confirmed ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-violet-500/10 text-violet-400 border border-violet-500/20">
                        Field-Confirmed
                      </span>
                    ) : (
                      <span className="text-gray-700 text-[10px]">XER</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
