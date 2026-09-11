"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import {
  Network,
  Filter,
  ArrowRight,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  Layers,
  Search,
  ExternalLink,
} from "lucide-react";
import { useApp } from "@/lib/AppContext";
import { fetchGanttData } from "@/lib/api";
import type { GanttActivity, GanttDataResponse } from "@/lib/types";

export default function CriticalPathNetworkPage() {
  const { openActivityDetail } = useApp();
  const [data, setData] = useState<GanttDataResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [criticalOnly, setCriticalOnly] = useState(true);
  const [disciplineFilter, setDisciplineFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const res = await fetchGanttData({ page_size: 100 });
        setData(res);
      } catch (err) {
        console.error("Failed to load network activities:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // Filter activities
  const filteredActivities = useMemo(() => {
    if (!data?.activities) return [];
    return data.activities.filter((act) => {
      if (criticalOnly && !act.is_critical && (act.total_float_days ?? 999) > 0) return false;
      if (disciplineFilter && act.discipline?.toLowerCase() !== disciplineFilter.toLowerCase()) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        return (
          act.activity_id.toLowerCase().includes(q) ||
          act.activity_name.toLowerCase().includes(q) ||
          (act.contractor_name || "").toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [data?.activities, criticalOnly, disciplineFilter, searchQuery]);

  // Distinct disciplines
  const disciplines = useMemo(() => {
    if (!data?.activities) return [];
    return Array.from(new Set(data.activities.map((a) => a.discipline))).filter(Boolean);
  }, [data?.activities]);

  const criticalCount = useMemo(() => {
    return data?.activities.filter((a) => a.is_critical || (a.total_float_days ?? 999) <= 0).length || 0;
  }, [data?.activities]);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-zinc-200 pb-3.5">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-zinc-500 mb-1">
            <span className="font-semibold text-zinc-900">OIL-NE-2026</span>
            <span>•</span>
            <span>Precedence Diagram Method (PDM)</span>
            <span>•</span>
            <span className="text-red-700 font-semibold font-mono">
              Critical Path: {criticalCount} Driven Activities
            </span>
          </div>
          <h1 className="text-xl font-bold text-zinc-950 tracking-tight flex items-center gap-2">
            <Network className="w-5 h-5 text-slate-900" />
            Critical Path Network Diagram
          </h1>
          <p className="text-xs text-zinc-500 mt-0.5">
            Logic network precedence boxes with early/late dates, total float consumption, and driving relationships.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            href="/schedule"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-zinc-300 hover:bg-zinc-50 rounded-[2px] text-xs font-medium text-zinc-800 transition-colors"
          >
            <span>Switch to P6 Gantt</span>
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
              checked={criticalOnly}
              onChange={(e) => setCriticalOnly(e.target.checked)}
              className="rounded-[2px] border-zinc-300 text-red-600 focus:ring-red-500"
            />
            <span className="text-red-700 font-semibold">Critical Path Only (Float ≤ 0d)</span>
          </label>

          <div className="h-4 w-px bg-zinc-200" />

          {/* Discipline filter */}
          <select
            value={disciplineFilter}
            onChange={(e) => setDisciplineFilter(e.target.value)}
            className="border border-zinc-300 rounded-[2px] px-2 py-1 bg-white text-zinc-800 text-xs font-mono"
          >
            <option value="">All Disciplines</option>
            {disciplines.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>

          {/* Search box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-400" />
            <input
              type="text"
              placeholder="Search node or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1 border border-zinc-300 rounded-[2px] text-xs w-48 focus:border-blue-900 focus:outline-none"
            />
          </div>
        </div>

        <div className="text-[11px] font-mono text-zinc-500">
          Showing <strong className="text-zinc-900">{filteredActivities.length}</strong> of{" "}
          <strong className="text-zinc-900">{data?.activities.length || 0}</strong> nodes
        </div>
      </div>

      {/* Logic Precedence Boxes Grid */}
      {loading ? (
        <div className="p-12 text-center text-xs text-zinc-400 bg-white border border-zinc-200 rounded-[2px]">
          Calculating logic network and float values...
        </div>
      ) : filteredActivities.length === 0 ? (
        <div className="p-12 text-center text-xs text-zinc-400 bg-white border border-zinc-200 rounded-[2px]">
          No activities match the current filter selection.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredActivities.map((act) => {
            const isCritical = act.is_critical || (act.total_float_days ?? 999) <= 0;
            return (
              <div
                key={act.id}
                onClick={() => openActivityDetail(act.activity_id)}
                className={`bg-white border rounded-[2px] cursor-pointer transition-all hover:shadow-sm ${
                  isCritical ? "border-red-400 shadow-xs" : "border-zinc-300"
                }`}
              >
                {/* Node Top Bar (Activity ID + Status) */}
                <div
                  className={`px-3 py-1.5 border-b text-xs flex items-center justify-between font-mono ${
                    isCritical ? "bg-red-50/80 border-red-200 text-red-900" : "bg-zinc-50 border-zinc-200 text-zinc-800"
                  }`}
                >
                  <span className="font-bold">{act.activity_id}</span>
                  <span
                    className={`text-[10px] font-semibold px-1.5 py-0.2 rounded-[2px] ${
                      isCritical
                        ? "bg-red-100 text-red-800 border border-red-300"
                        : "bg-zinc-200 text-zinc-700"
                    }`}
                  >
                    {isCritical ? "CRITICAL" : "NON-CRITICAL"}
                  </span>
                </div>

                {/* Node Body (Name & Discipline) */}
                <div className="p-3 space-y-2">
                  <div className="text-xs font-semibold text-zinc-900 line-clamp-2 min-h-[32px]" title={act.activity_name}>
                    {act.activity_name}
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-zinc-500 font-mono">
                    <span>Discipline: <strong className="text-zinc-800">{act.discipline || "General"}</strong></span>
                    <span>Prog: <strong className="text-zinc-800">{act.actual_percent_complete || 0}%</strong></span>
                  </div>

                  {/* Precedence Matrix (ES | EF | Float | OD) */}
                  <div className="grid grid-cols-4 border border-zinc-200 bg-zinc-50 text-[10px] font-mono text-center divide-x divide-zinc-200">
                    <div className="p-1">
                      <span className="text-zinc-400 block text-[9px]">START</span>
                      <span className="font-medium text-zinc-800 truncate block">
                        {act.planned_start ? act.planned_start.slice(5) : "—"}
                      </span>
                    </div>
                    <div className="p-1">
                      <span className="text-zinc-400 block text-[9px]">FINISH</span>
                      <span className="font-medium text-zinc-800 truncate block">
                        {act.planned_finish ? act.planned_finish.slice(5) : "—"}
                      </span>
                    </div>
                    <div className="p-1">
                      <span className="text-zinc-400 block text-[9px]">FLOAT</span>
                      <span
                        className={`font-bold block ${
                          isCritical ? "text-red-700 font-semibold" : "text-zinc-700"
                        }`}
                      >
                        {act.total_float_days ?? 0}d
                      </span>
                    </div>
                    <div className="p-1">
                      <span className="text-zinc-400 block text-[9px]">DUR</span>
                      <span className="font-medium text-zinc-800 block">
                        {act.original_duration_days || 0}d
                      </span>
                    </div>
                  </div>

                  {/* Predecessors / Successors logic chips */}
                  <div className="pt-1.5 flex items-center justify-between text-[10px] text-zinc-500 font-mono border-t border-zinc-100">
                    <span className="truncate max-w-[130px]">
                      Pred: {act.predecessors?.length ? act.predecessors.join(", ") : "None"}
                    </span>
                    <span className="truncate max-w-[130px]">
                      Succ: {act.successors?.length ? act.successors.join(", ") : "None"}
                    </span>
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
