"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import {
  GitCommit,
  Calendar,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ArrowRight,
  Filter,
} from "lucide-react";
import { useApp } from "@/lib/AppContext";
import { fetchGanttData, fetchScheduleHealth } from "@/lib/api";
import type { GanttActivity, ScheduleHealth } from "@/lib/types";

export default function ProjectTimelinePage() {
  const { openActivityDetail } = useApp();
  const [activities, setActivities] = useState<GanttActivity[]>([]);
  const [health, setHealth] = useState<ScheduleHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [milestonesOnly, setMilestonesOnly] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [ganttRes, healthRes] = await Promise.all([
          fetchGanttData({ page_size: 100 }).catch(() => null),
          fetchScheduleHealth("TEST").catch(() => null),
        ]);
        if (ganttRes?.activities) {
          // Sort chronologically by planned start or finish
          const sorted = [...ganttRes.activities].sort((a, b) => {
            const dateA = a.planned_start || a.planned_finish || "";
            const dateB = b.planned_start || b.planned_finish || "";
            return dateA.localeCompare(dateB);
          });
          setActivities(sorted);
        }
        if (healthRes) {
          setHealth(healthRes);
        }
      } catch (err) {
        console.error("Failed to load timeline events:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filteredTimeline = useMemo(() => {
    return activities.filter((act) => {
      const isMilestone =
        act.activity_id.includes("MIL") ||
        act.activity_name.toLowerCase().includes("milestone") ||
        act.original_duration_days === 0;

      if (milestonesOnly && !isMilestone) return false;
      if (statusFilter && act.status !== statusFilter) return false;
      return true;
    });
  }, [activities, milestonesOnly, statusFilter]);

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-5">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-zinc-200 pb-3.5">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-zinc-500 mb-1">
            <span className="font-semibold text-zinc-900">OIL-NE-2026</span>
            <span>•</span>
            <span>Milestones & Delivery Gates</span>
            <span>•</span>
            <span className="text-zinc-700 font-mono">
              Target Finish: {health?.forecast_project_finish || "2026-12-15"}
            </span>
          </div>
          <h1 className="text-xl font-bold text-zinc-950 tracking-tight flex items-center gap-2">
            <GitCommit className="w-5 h-5 text-slate-900" />
            Project Chronological Timeline
          </h1>
          <p className="text-xs text-zinc-500 mt-0.5">
            Sequential progression of key milestones, contractual checkpoints, and delivery gates.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            href="/schedule"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-zinc-300 hover:bg-zinc-50 rounded-[2px] text-xs font-medium text-zinc-800 transition-colors"
          >
            <span>P6 Gantt Chart</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Control Strip */}
      <div className="bg-white border border-zinc-300 rounded-[2px] p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3 flex-wrap">
          <label className="flex items-center gap-1.5 cursor-pointer font-medium text-zinc-800 select-none">
            <input
              type="checkbox"
              checked={milestonesOnly}
              onChange={(e) => setMilestonesOnly(e.target.checked)}
              className="rounded-[2px] border-zinc-300 text-blue-900 focus:ring-blue-900"
            />
            <span>Contractual Milestones Only</span>
          </label>

          <div className="h-4 w-px bg-zinc-200" />

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-zinc-300 rounded-[2px] px-2 py-1 bg-white text-zinc-800 text-xs font-mono"
          >
            <option value="">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="in_progress">In Progress</option>
            <option value="delayed">Delayed</option>
            <option value="not_started">Not Started</option>
          </select>
        </div>

        <div className="text-[11px] font-mono text-zinc-500">
          Showing <strong className="text-zinc-900">{filteredTimeline.length}</strong> chronological checkpoints
        </div>
      </div>

      {/* Vertical Timeline Rail */}
      {loading ? (
        <div className="p-12 text-center text-xs text-zinc-400 bg-white border border-zinc-200 rounded-[2px]">
          Loading chronological timeline...
        </div>
      ) : filteredTimeline.length === 0 ? (
        <div className="p-12 text-center text-xs text-zinc-400 bg-white border border-zinc-200 rounded-[2px]">
          No events found for current filter.
        </div>
      ) : (
        <div className="relative pl-6 border-l-2 border-zinc-200 ml-4 space-y-6 select-none">
          {filteredTimeline.map((act) => {
            const isMilestone =
              act.activity_id.includes("MIL") ||
              act.activity_name.toLowerCase().includes("milestone") ||
              act.original_duration_days === 0;

            const isDone = act.status === "completed" || (act.actual_percent_complete ?? 0) >= 100;
            const isDelayed = act.status === "delayed" || (act.total_float_days ?? 999) <= 0;

            return (
              <div key={act.id} className="relative group">
                {/* Node Bullet on Rail */}
                <div
                  className={`absolute -left-[31px] top-1.5 w-3.5 h-3.5 rounded-full border-2 bg-white transition-all group-hover:scale-125 ${
                    isDone
                      ? "border-emerald-600 bg-emerald-500"
                      : isDelayed
                      ? "border-red-600 bg-red-500"
                      : "border-blue-700 bg-blue-600"
                  }`}
                />

                {/* Event Card */}
                <div
                  onClick={() => openActivityDetail(act.activity_id)}
                  className={`p-3.5 bg-white border rounded-[2px] cursor-pointer hover:border-zinc-400 transition-all ${
                    isMilestone ? "border-l-4 border-l-slate-900 border-zinc-300 shadow-xs" : "border-zinc-200"
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 text-xs mb-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-zinc-900">{act.activity_id}</span>
                      {isMilestone && (
                        <span className="text-[10px] font-semibold bg-slate-900 text-white px-1.5 py-0.2 rounded-[2px]">
                          MILESTONE GATE
                        </span>
                      )}
                      <span className="text-[11px] text-zinc-500 font-mono">[{act.discipline || "General"}]</span>
                    </div>

                    <span
                      className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded-[2px] self-start sm:self-auto ${
                        isDone
                          ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                          : isDelayed
                          ? "bg-red-50 text-red-800 border border-red-200"
                          : "bg-blue-50 text-blue-800 border border-blue-200"
                      }`}
                    >
                      {act.status.toUpperCase()} ({act.actual_percent_complete || 0}%)
                    </span>
                  </div>

                  <div className="font-semibold text-xs text-zinc-900 mb-2">{act.activity_name}</div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-zinc-100 text-[11px] font-mono text-zinc-500">
                    <div>
                      <span>Planned: </span>
                      <strong className="text-zinc-800">{act.planned_start || "—"}</strong>
                    </div>
                    <div>
                      <span>Finish: </span>
                      <strong className="text-zinc-800">{act.planned_finish || "—"}</strong>
                    </div>
                    <div>
                      <span>Actual Finish: </span>
                      <strong className="text-zinc-800">{act.actual_finish || "In Progress"}</strong>
                    </div>
                    <div>
                      <span>Float: </span>
                      <strong className={isDelayed ? "text-red-700" : "text-zinc-800"}>
                        {act.total_float_days ?? 0}d
                      </strong>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
