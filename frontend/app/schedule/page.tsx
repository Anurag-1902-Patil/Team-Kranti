"use client";

import React, { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { apiFetch, API_BASE, getAuthToken } from "@/lib/api";
import type { PlanActivity } from "@/lib/types";
import GanttChart from "@/components/GanttChart";
import ActivityDetailPanel from "@/components/ActivityDetailPanel";
import { Download, Upload, CheckCircle, AlertCircle, RefreshCw, Calendar } from "lucide-react";

interface ActivityListResponse {
  total: number;
  page: number;
  page_size: number;
  items: PlanActivity[];
}

function ScheduleContent() {
  const searchParams = useSearchParams();
  const deepLinkedActivityId = searchParams.get("activity_id");

  const [activities, setActivities] = useState<PlanActivity[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [selectedActivity, setSelectedActivity] = useState<PlanActivity | null>(null);

  const [exporting, setExporting] = useState(false);
  const [exportMsg, setExportMsg] = useState("");
  const [importing, setImporting] = useState(false);
  const [importMsg, setImportMsg] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function loadActivities() {
    setLoading(true);
    try {
      const data = await apiFetch<ActivityListResponse>("/api/v1/schedule/activities?page=1&page_size=100");
      const items = data.items || [];
      setActivities(items);
      setTotalCount(data.total || items.length);

      // Handle deep-link activity query parameter
      if (deepLinkedActivityId) {
        const found = items.find((a) => a.activity_id === deepLinkedActivityId);
        if (found) setSelectedActivity(found);
      }
    } catch (e) {
      console.error("Failed to load schedule activities:", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadActivities();
  }, [deepLinkedActivityId]);

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
      setImportMsg(`✓ Successfully imported ${data.total || 0} activities from ${file.name}`);
      await loadActivities();
    } catch (err: unknown) {
      setImportMsg(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
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
      setExportMsg("✓ Validated schedule exported to Primavera P6 XER.");
    } catch (e) {
      setExportMsg(`Export failed: ${String(e)}`);
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-5 font-sans">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-slate-100">
              Primavera P6 Schedule &amp; Execution Gantt
            </h1>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-cyan-950 text-cyan-400 border border-cyan-800/60">
              {totalCount} Plan Activities
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Canonical Primavera P6 L5/L6 Schedule • Baseline Dates, Real-time Actuals &amp; Delay Projections
          </p>
        </div>

        {/* Action Buttons: Import / Export XER */}
        <div className="flex items-center gap-2.5">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            accept=".xer,.csv,.xlsx"
            className="hidden"
            id="schedule-file-input"
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
            className="px-3 py-1.5 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs text-slate-300 flex items-center gap-1.5 transition-colors disabled:opacity-50"
            title="Upload P6 .XER or spreadsheet"
          >
            <Upload className="w-3.5 h-3.5 text-cyan-400" />
            {importing ? "Importing..." : "Import XER"}
          </button>

          <button
            onClick={exportXer}
            disabled={exporting}
            className="px-3 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-medium text-xs flex items-center gap-1.5 transition-colors disabled:opacity-50 shadow-sm"
            title="Download XER with actuals"
          >
            <Download className="w-3.5 h-3.5" />
            {exporting ? "Generating..." : "Export XER"}
          </button>

          <button
            onClick={loadActivities}
            disabled={loading}
            className="p-1.5 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-cyan-400" : ""}`} />
          </button>
        </div>
      </div>

      {/* Status Notifications */}
      {(importMsg || exportMsg) && (
        <div className="space-y-2">
          {importMsg && (
            <div className={`p-2.5 rounded text-xs flex items-center gap-2 border font-mono ${
              importMsg.startsWith("✓")
                ? "bg-emerald-950/60 border-emerald-800/60 text-emerald-400"
                : "bg-rose-950/60 border-rose-800/60 text-rose-400"
            }`}>
              {importMsg.startsWith("✓") ? (
                <CheckCircle className="w-3.5 h-3.5 flex-shrink-0" />
              ) : (
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
              )}
              <span>{importMsg}</span>
            </div>
          )}
          {exportMsg && (
            <div className={`p-2.5 rounded text-xs flex items-center gap-2 border font-mono ${
              exportMsg.startsWith("✓")
                ? "bg-emerald-950/60 border-emerald-800/60 text-emerald-400"
                : "bg-rose-950/60 border-rose-800/60 text-rose-400"
            }`}>
              <CheckCircle className="w-3.5 h-3.5 flex-shrink-0" />
              <span>{exportMsg}</span>
            </div>
          )}
        </div>
      )}

      {/* Gantt & Schedule Table View */}
      <GanttChart
        activities={activities}
        onSelectActivity={(act) => setSelectedActivity(act)}
        selectedActivityId={selectedActivity?.activity_id}
      />

      {/* Activity Slide-Out Detail Panel */}
      <ActivityDetailPanel
        activity={selectedActivity}
        onClose={() => setSelectedActivity(null)}
        onActivityUpdated={loadActivities}
      />
    </div>
  );
}

export default function SchedulePage() {
  return (
    <Suspense fallback={<div className="p-6 text-xs text-slate-400 font-sans">Loading schedule...</div>}>
      <ScheduleContent />
    </Suspense>
  );
}
