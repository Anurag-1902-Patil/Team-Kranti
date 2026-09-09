"use client";

import React, { useState, useMemo } from "react";
import type { PlanActivity } from "@/lib/types";
import { Search, Filter, AlertCircle, CheckCircle2, Clock } from "lucide-react";

interface GanttChartProps {
  activities: PlanActivity[];
  onSelectActivity: (activity: PlanActivity) => void;
  selectedActivityId?: string | null;
}

export default function GanttChart({
  activities,
  onSelectActivity,
  selectedActivityId,
}: GanttChartProps) {
  const [search, setSearch] = useState("");
  const [selectedDiscipline, setSelectedDiscipline] = useState<string>("all");
  const [onlyCritical, setOnlyCritical] = useState<boolean>(false);

  // Extract unique disciplines
  const disciplines = useMemo(() => {
    const set = new Set<string>();
    activities.forEach((a) => {
      if (a.discipline) set.add(a.discipline);
    });
    return Array.from(set).sort();
  }, [activities]);

  // Filter activities
  const filteredActivities = useMemo(() => {
    return activities.filter((act) => {
      if (selectedDiscipline !== "all" && act.discipline?.toLowerCase() !== selectedDiscipline.toLowerCase()) {
        return false;
      }
      if (onlyCritical && !act.is_critical) {
        return false;
      }
      if (search) {
        const q = search.toLowerCase();
        const matchName = act.activity_name?.toLowerCase().includes(q);
        const matchId = act.activity_id?.toLowerCase().includes(q);
        const matchWbs = act.wbs_code?.toLowerCase().includes(q);
        if (!matchName && !matchId && !matchWbs) return false;
      }
      return true;
    });
  }, [activities, selectedDiscipline, onlyCritical, search]);

  return (
    <div className="space-y-4 font-sans">
      {/* Search & Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 pm-card">
        <div className="flex items-center gap-2 flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter by activity ID, name, or WBS..."
              className="w-full pl-8 pr-3 py-1.5 bg-slate-900 border border-slate-700/70 rounded text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Discipline Dropdown */}
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedDiscipline}
              onChange={(e) => setSelectedDiscipline(e.target.value)}
              className="bg-slate-900 border border-slate-700/70 text-slate-200 py-1.5 px-2.5 rounded text-xs focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Disciplines ({activities.length})</option>
              {disciplines.map((d) => (
                <option key={d} value={d}>
                  {d.toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          {/* Only Critical Toggle */}
          <label className="flex items-center gap-1.5 text-xs text-slate-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={onlyCritical}
              onChange={(e) => setOnlyCritical(e.target.checked)}
              className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0 focus:ring-offset-0"
            />
            <span>Critical Path Only</span>
          </label>
        </div>
      </div>

      {/* Main Schedule Table + Visual Timeline */}
      <div className="pm-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="pm-table">
            <thead>
              <tr>
                <th style={{ width: "110px" }}>Activity ID</th>
                <th>Activity Name &amp; WBS</th>
                <th style={{ width: "90px" }}>Discipline</th>
                <th style={{ width: "90px" }}>Start Date</th>
                <th style={{ width: "90px" }}>Finish Date</th>
                <th style={{ width: "65px" }}>Float</th>
                <th style={{ width: "80px" }}>Progress</th>
                <th style={{ minWidth: "160px" }}>Timeline (Progress vs Baseline)</th>
              </tr>
            </thead>
            <tbody>
              {filteredActivities.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400 text-xs">
                    No activities match current filters.
                  </td>
                </tr>
              ) : (
                filteredActivities.map((act) => {
                  const isSelected = selectedActivityId === act.activity_id;
                  const progress = Math.min(100, Math.max(0, act.actual_percent_complete || act.percent_complete_plan || 0));
                  const isCritical = act.is_critical || (act.total_float_days != null && act.total_float_days <= 0);

                  return (
                    <tr
                      key={act.id}
                      onClick={() => onSelectActivity(act)}
                      className={`cursor-pointer transition-colors ${
                        isSelected ? "bg-cyan-950/40 border-l-2 border-l-cyan-400" : ""
                      }`}
                    >
                      {/* ID */}
                      <td className="font-mono text-xs font-semibold whitespace-nowrap">
                        <span className="code-tag px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-cyan-400">
                          {act.activity_id}
                        </span>
                      </td>

                      {/* Name & WBS */}
                      <td className="max-w-xs">
                        <div className="font-medium text-slate-200 truncate">
                          {act.activity_name}
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                          {act.wbs_code || "WBS.ROOT"}
                        </div>
                      </td>

                      {/* Discipline */}
                      <td>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                          {act.discipline ? act.discipline.toUpperCase() : "GENERAL"}
                        </span>
                      </td>

                      {/* Planned Start */}
                      <td className="font-mono text-[11px] text-slate-300 whitespace-nowrap">
                        {act.planned_start ? act.planned_start.substring(0, 10) : "—"}
                      </td>

                      {/* Planned Finish */}
                      <td className="font-mono text-[11px] text-slate-300 whitespace-nowrap">
                        {act.planned_finish ? act.planned_finish.substring(0, 10) : "—"}
                      </td>

                      {/* Float */}
                      <td className="whitespace-nowrap">
                        <span
                          className={`text-[11px] font-mono font-medium ${
                            isCritical ? "text-rose-400" : "text-slate-400"
                          }`}
                        >
                          {act.total_float_days ?? 0}d
                        </span>
                      </td>

                      {/* Progress % */}
                      <td className="whitespace-nowrap">
                        <span className="font-mono text-xs font-medium text-slate-200">
                          {progress}%
                        </span>
                      </td>

                      {/* Mini Visual Gantt Bar */}
                      <td>
                        <div className="w-full bg-slate-900 border border-slate-800 h-2.5 rounded-full overflow-hidden flex">
                          <div
                            className={`h-full transition-all duration-300 ${
                              progress >= 100
                                ? "bg-emerald-500"
                                : isCritical
                                ? "bg-rose-500"
                                : "bg-cyan-500"
                            }`}
                            style={{ width: `${progress}%` }}
                            title={`${progress}% Complete`}
                          />
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
