"use client";

import React, { useState, useRef, useEffect } from "react";
import { ChevronRight, ChevronDown, Calendar, AlertCircle } from "lucide-react";
import type { GanttActivity, WBSNode, DependencyEdge } from "@/lib/types";

interface P6GanttProps {
  wbsTree: WBSNode[];
  activities: GanttActivity[];
  dependencies: DependencyEdge[];
  onSelectActivity: (activityId: string) => void;
  selectedActivityId: string | null;
}

type ZoomLevel = "day" | "week" | "month" | "quarter";

export function P6Gantt({
  wbsTree,
  activities,
  dependencies,
  onSelectActivity,
  selectedActivityId,
}: P6GanttProps) {
  const [collapsedWbs, setCollapsedWbs] = useState<Record<string, boolean>>({});
  const [zoom, setZoom] = useState<ZoomLevel>("month");

  const leftTableRef = useRef<HTMLDivElement>(null);
  const rightTimelineRef = useRef<HTMLDivElement>(null);
  const isSyncingRef = useRef(false);

  // Sync vertical scrolling between table and timeline
  const handleTableScroll = () => {
    if (isSyncingRef.current) return;
    isSyncingRef.current = true;
    if (rightTimelineRef.current && leftTableRef.current) {
      rightTimelineRef.current.scrollTop = leftTableRef.current.scrollTop;
    }
    isSyncingRef.current = false;
  };

  const handleTimelineScroll = () => {
    if (isSyncingRef.current) return;
    isSyncingRef.current = true;
    if (leftTableRef.current && rightTimelineRef.current) {
      leftTableRef.current.scrollTop = rightTimelineRef.current.scrollTop;
    }
    isSyncingRef.current = false;
  };

  const toggleWbs = (wbsCode: string) => {
    setCollapsedWbs((prev) => ({ ...prev, [wbsCode]: !prev[wbsCode] }));
  };

  // Compute timeline date range
  const allDates = activities
    .flatMap((a) => [a.planned_start, a.planned_finish, a.actual_start, a.actual_finish])
    .filter(Boolean) as string[];

  const minDate = allDates.length
    ? new Date(Math.min(...allDates.map((d) => new Date(d).getTime())))
    : new Date(2026, 7, 1);
  const maxDate = allDates.length
    ? new Date(Math.max(...allDates.map((d) => new Date(d).getTime())))
    : new Date(2026, 9, 30);

  // Buffer date range
  const startRange = new Date(minDate.getFullYear(), minDate.getMonth(), 1);
  const endRange = new Date(maxDate.getFullYear(), maxDate.getMonth() + 2, 0);

  const totalDays = Math.max(1, Math.ceil((endRange.getTime() - startRange.getTime()) / (1000 * 3600 * 24)));

  // Day width according to zoom level
  const dayWidth = zoom === "day" ? 28 : zoom === "week" ? 14 : zoom === "month" ? 6 : 2.5;
  const timelineWidth = Math.max(800, totalDays * dayWidth);

  // Helper to compute pixel offset from startRange
  const getX = (dateStr: string | null) => {
    if (!dateStr) return null;
    const d = new Date(dateStr);
    const diffDays = (d.getTime() - startRange.getTime()) / (1000 * 3600 * 24);
    return Math.max(0, diffDays * dayWidth);
  };

  // Today marker (Aug 15, 2026)
  const todayX = getX("2026-08-15");

  // Generate Month header ticks
  const months: Array<{ label: string; left: number; width: number }> = [];
  const cursor = new Date(startRange);
  while (cursor < endRange) {
    const monthStart = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
    const nextMonth = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
    const daysInMonth = (nextMonth.getTime() - monthStart.getTime()) / (1000 * 3600 * 24);
    const left = ((monthStart.getTime() - startRange.getTime()) / (1000 * 3600 * 24)) * dayWidth;
    const width = daysInMonth * dayWidth;

    months.push({
      label: monthStart.toLocaleDateString("en-GB", { month: "short", year: "2-digit" }),
      left,
      width,
    });
    cursor.setMonth(cursor.getMonth() + 1);
  }

  // Flatten visible rows (WBS headers + activities)
  const visibleRows: Array<{
    type: "wbs" | "activity";
    wbs?: WBSNode;
    activity?: GanttActivity;
    key: string;
  }> = [];

  wbsTree.forEach((wbs) => {
    visibleRows.push({ type: "wbs", wbs, key: `wbs_${wbs.wbs_code}` });
    if (!collapsedWbs[wbs.wbs_code]) {
      wbs.activities.forEach((act) => {
        visibleRows.push({ type: "activity", activity: act, key: act.id });
      });
    }
  });

  const rowHeight = 32;

  // Map activity ID to row Y position for dependency line rendering
  const activityYMap = new Map<string, number>();
  visibleRows.forEach((row, index) => {
    if (row.type === "activity" && row.activity) {
      activityYMap.set(row.activity.activity_id, index * rowHeight + rowHeight / 2);
    }
  });

  return (
    <div className="bg-white border border-zinc-200 rounded-lg flex flex-col overflow-hidden select-none">
      {/* Zoom Toolbar */}
      <div className="p-2.5 border-b border-zinc-200 bg-zinc-50 flex items-center justify-between text-xs">
        <div className="flex items-center gap-3">
          <span className="text-zinc-500 font-medium">Timescale:</span>
          <div className="flex items-center bg-zinc-200/70 p-0.5 rounded border border-zinc-300">
            {(["day", "week", "month", "quarter"] as const).map((z) => (
              <button
                key={z}
                onClick={() => setZoom(z)}
                className={`px-2.5 py-1 rounded text-[11px] font-medium capitalize transition-colors ${
                  zoom === z
                    ? "bg-white text-zinc-900 font-bold shadow-xs"
                    : "text-zinc-600 hover:text-zinc-900"
                }`}
              >
                {z}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-4 text-[11px] text-zinc-500 font-mono">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-1.5 bg-zinc-300 rounded-xs inline-block" />
            <span>Baseline</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-2 bg-blue-700 rounded-xs inline-block" />
            <span>Actual Progress</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-2 bg-red-600 rounded-xs inline-block" />
            <span>Critical Path</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-0.5 border-t border-red-500 border-dashed inline-block" />
            <span>Today (15-Aug)</span>
          </div>
        </div>
      </div>

      {/* Split View Container */}
      <div className="flex flex-1 overflow-hidden h-[580px]">
        {/* Left Side: P6 Activity Table */}
        <div
          ref={leftTableRef}
          onScroll={handleTableScroll}
          className="w-1/2 min-w-[480px] max-w-[620px] overflow-x-auto overflow-y-auto border-r border-zinc-200"
        >
          <table className="p6-table">
            <thead className="sticky top-0 z-20 bg-zinc-50 shadow-xs">
              <tr>
                <th className="w-24">Activity ID</th>
                <th className="min-w-[180px]">Activity Name</th>
                <th className="w-20">Discipline</th>
                <th className="w-16 text-right">Dur</th>
                <th className="w-14 text-right">%</th>
                <th className="w-16 text-right">Float</th>
                <th className="w-20">Status</th>
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((row) => {
                if (row.type === "wbs" && row.wbs) {
                  const isCollapsed = !!collapsedWbs[row.wbs.wbs_code];
                  return (
                    <tr
                      key={row.key}
                      onClick={() => toggleWbs(row.wbs!.wbs_code)}
                      className="bg-zinc-100 hover:bg-zinc-200/70 font-semibold cursor-pointer text-zinc-900"
                      style={{ height: rowHeight }}
                    >
                      <td colSpan={2} className="py-1 px-2 font-mono text-xs">
                        <div className="flex items-center gap-1.5">
                          {isCollapsed ? (
                            <ChevronRight className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                          ) : (
                            <ChevronDown className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                          )}
                          <span className="text-blue-800">{row.wbs.wbs_code}</span>
                          <span className="font-normal text-zinc-700 truncate">{row.wbs.wbs_name}</span>
                        </div>
                      </td>
                      <td className="text-zinc-500 text-[10px]">WBS Level</td>
                      <td className="text-right text-zinc-500 font-mono text-[11px]">—</td>
                      <td className="text-right font-mono font-bold text-zinc-800 text-[11px]">
                        {row.wbs.percent_complete}%
                      </td>
                      <td className="text-right text-zinc-500 font-mono text-[11px]">—</td>
                      <td>
                        {row.wbs.is_critical && (
                          <span className="text-[10px] text-red-700 bg-red-50 border border-red-200 px-1 rounded font-semibold">
                            Critical WBS
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                }

                const act = row.activity!;
                const isSelected = selectedActivityId === act.activity_id;

                return (
                  <tr
                    key={row.key}
                    onClick={() => onSelectActivity(act.activity_id)}
                    className={`cursor-pointer transition-colors ${
                      isSelected ? "selected" : ""
                    }`}
                    style={{ height: rowHeight }}
                  >
                    <td className="font-mono text-xs font-medium text-blue-700 pl-6 truncate">
                      {act.activity_id}
                    </td>
                    <td className="truncate text-xs text-zinc-800 font-medium">
                      {act.activity_name}
                    </td>
                    <td className="capitalize text-[11px] text-zinc-600">
                      {act.discipline}
                    </td>
                    <td className="text-right font-mono text-[11px] text-zinc-600">
                      {act.original_duration_days}d
                    </td>
                    <td className="text-right font-mono font-semibold text-zinc-900 text-[11px]">
                      {act.actual_percent_complete.toFixed(0)}%
                    </td>
                    <td
                      className={`text-right font-mono text-[11px] font-semibold ${
                        act.total_float_days < 0 ? "text-red-700" : "text-zinc-600"
                      }`}
                    >
                      {act.total_float_days.toFixed(0)}d
                    </td>
                    <td>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                          act.status === "completed"
                            ? "badge-ontrack"
                            : act.status === "delayed"
                            ? "badge-delayed"
                            : act.status === "in_progress"
                            ? "badge-atrisk"
                            : "badge-neutral"
                        }`}
                      >
                        {act.status.replace("_", " ")}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Right Side: Gantt Timeline Visualization */}
        <div
          ref={rightTimelineRef}
          onScroll={handleTimelineScroll}
          className="flex-1 overflow-x-auto overflow-y-auto bg-white relative"
        >
          <div style={{ width: timelineWidth, minHeight: visibleRows.length * rowHeight + 36 }}>
            {/* Timeline Header (Sticky) */}
            <div className="sticky top-0 z-20 bg-zinc-50 border-b border-zinc-200 h-9 relative">
              {months.map((m, idx) => (
                <div
                  key={idx}
                  className="absolute top-0 bottom-0 border-r border-zinc-200 px-2 flex items-center text-[11px] font-mono text-zinc-500 font-semibold"
                  style={{ left: m.left, width: m.width }}
                >
                  {m.label}
                </div>
              ))}
            </div>

            {/* Timeline Body Canvas */}
            <div className="relative">
              {/* Today Vertical Line (15-Aug-2026) */}
              {todayX !== null && (
                <div
                  className="absolute top-0 bottom-0 z-10 border-l border-red-500 border-dashed pointer-events-none"
                  style={{ left: todayX, height: visibleRows.length * rowHeight }}
                >
                  <span className="bg-red-500 text-white text-[9px] font-mono px-1 py-0.2 rounded absolute top-1 -left-5">
                    TODAY
                  </span>
                </div>
              )}

              {/* Rows and Bars */}
              {visibleRows.map((row, index) => {
                const y = index * rowHeight;

                if (row.type === "wbs" && row.wbs) {
                  // WBS summary bar
                  const startX = getX(row.wbs.planned_start);
                  const endX = getX(row.wbs.planned_finish);
                  const barWidth = startX !== null && endX !== null ? Math.max(10, endX - startX) : 0;

                  return (
                    <div
                      key={row.key}
                      className="absolute w-full bg-zinc-100/80 border-b border-zinc-200"
                      style={{ top: y, height: rowHeight }}
                    >
                      {startX !== null && barWidth > 0 && (
                        <div
                          className="absolute top-2 h-3.5 bg-zinc-400/80 rounded-xs flex items-center px-1"
                          style={{ left: startX, width: barWidth }}
                        >
                          <div
                            className="h-full bg-zinc-700 rounded-xs"
                            style={{ width: `${row.wbs.percent_complete}%` }}
                          />
                        </div>
                      )}
                    </div>
                  );
                }

                // Activity Row
                const act = row.activity!;
                const isSelected = selectedActivityId === act.activity_id;

                // Baseline bar coords
                const planStartX = getX(act.planned_start);
                const planEndX = getX(act.planned_finish);
                const planWidth = planStartX !== null && planEndX !== null ? Math.max(8, planEndX - planStartX) : 0;

                // Actual bar coords
                const actStartX = getX(act.actual_start || act.planned_start);
                const actEndX = getX(act.actual_finish || act.planned_finish);
                const actWidth = actStartX !== null && actEndX !== null ? Math.max(8, actEndX - actStartX) : 0;

                const isCrit = act.is_critical;

                return (
                  <div
                    key={row.key}
                    onClick={() => onSelectActivity(act.activity_id)}
                    className={`absolute w-full border-b border-zinc-100 hover:bg-zinc-50 cursor-pointer ${
                      isSelected ? "bg-blue-50/50" : ""
                    }`}
                    style={{ top: y, height: rowHeight }}
                  >
                    {/* Top: Thin Baseline Bar */}
                    {planStartX !== null && planWidth > 0 && (
                      <div
                        className="absolute top-1.5 h-1.5 bg-zinc-300 rounded-xs"
                        style={{ left: planStartX, width: planWidth }}
                        title={`Baseline: ${act.planned_start?.slice(0, 10)} to ${act.planned_finish?.slice(0, 10)}`}
                      />
                    )}

                    {/* Bottom: Actual Progress Bar (P6 Dual Bar) */}
                    {actStartX !== null && actWidth > 0 && (
                      <div
                        className={`absolute top-3.5 h-4 rounded-xs overflow-hidden border ${
                          isCrit
                            ? "border-red-600 bg-red-100"
                            : "border-blue-600 bg-blue-100"
                        }`}
                        style={{ left: actStartX, width: actWidth }}
                        title={`${act.activity_id}: ${act.actual_percent_complete}% (${act.status})`}
                      >
                        {/* Progress Fill */}
                        <div
                          className={`h-full ${
                            isCrit ? "bg-red-600" : "bg-blue-700"
                          }`}
                          style={{ width: `${act.actual_percent_complete}%` }}
                        />
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Dependency Connection Lines (SVG overlay) */}
              <svg
                className="absolute top-0 left-0 pointer-events-none"
                style={{ width: timelineWidth, height: visibleRows.length * rowHeight }}
              >
                {dependencies.map((dep, idx) => {
                  const predY = activityYMap.get(dep.predecessor);
                  const succY = activityYMap.get(dep.successor);
                  if (predY === undefined || succY === undefined) return null;

                  const predAct = activities.find((a) => a.activity_id === dep.predecessor);
                  const succAct = activities.find((a) => a.activity_id === dep.successor);
                  if (!predAct || !succAct) return null;

                  const fromX = (getX(predAct.actual_finish || predAct.planned_finish) || 0) + 4;
                  const toX = (getX(succAct.actual_start || succAct.planned_start) || 0) - 4;

                  const isCriticalEdge = predAct.is_critical && succAct.is_critical;

                  return (
                    <g key={idx}>
                      <path
                        d={`M ${fromX} ${predY} H ${fromX + 8} V ${succY} H ${toX}`}
                        fill="none"
                        stroke={isCriticalEdge ? "#dc2626" : "#94a3b8"}
                        strokeWidth={isCriticalEdge ? 1.5 : 1}
                        strokeDasharray={isCriticalEdge ? "none" : "2 2"}
                      />
                      <polygon
                        points={`${toX},${succY} ${toX - 4},${succY - 3} ${toX - 4},${succY + 3}`}
                        fill={isCriticalEdge ? "#dc2626" : "#94a3b8"}
                      />
                    </g>
                  );
                })}
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
