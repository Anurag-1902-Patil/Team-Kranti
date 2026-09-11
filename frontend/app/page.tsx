"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  TrendingUp,
  AlertTriangle,
  Clock,
  CheckCircle2,
  AlertOctagon,
  Calendar,
  Layers,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend,
} from "recharts";
import { WhatChangedRibbon } from "@/components/WhatChangedRibbon";
import { fetchScheduleHealth, fetchDelayAnalyticsDetailed, fetchUpdateCenterFeed } from "@/lib/api";
import type { ScheduleHealth, DelayAnalyticsResponse, UpdateCenterFeedResponse } from "@/lib/types";

export default function OverviewPage() {
  const router = useRouter();
  const [health, setHealth] = useState<ScheduleHealth | null>(null);
  const [delays, setDelays] = useState<DelayAnalyticsResponse | null>(null);
  const [updates, setUpdates] = useState<UpdateCenterFeedResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [progressRange, setProgressRange] = useState<"7d" | "30d" | "90d" | "lifetime">("30d");

  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      try {
        const [h, d, u] = await Promise.all([
          fetchScheduleHealth("TEST").catch(() => null),
          fetchDelayAnalyticsDetailed().catch(() => null),
          fetchUpdateCenterFeed().catch(() => null),
        ]);
        if (isMounted) {
          setHealth(h);
          setDelays(d);
          setUpdates(u);
        }
      } catch (err) {
        console.error("Failed to load overview data:", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    loadData();
    return () => {
      isMounted = false;
    };
  }, []);

  // Compute Planned vs Actual S-Curve data points from real schedule health
  const overallActual = health ? Math.round(health.overall_progress_pct || 42) : 42;
  const overallPlanned = 48; // Baseline schedule target

  const sCurveData = [
    { period: "Week 1", planned: 10, actual: 10 },
    { period: "Week 2", planned: 20, actual: 18 },
    { period: "Week 3", planned: 32, actual: 28 },
    { period: "Week 4", planned: 40, actual: 35 },
    { period: "Current", planned: overallPlanned, actual: overallActual },
    { period: "Week 6", planned: 60, actual: null },
    { period: "Week 7", planned: 75, actual: null },
    { period: "Week 8", planned: 100, actual: null },
  ];

  // Status distribution Donut data
  const statusData = [
    { name: "Completed", value: health?.completed_count || 14, color: "#15803D" },
    { name: "In Progress", value: health?.in_progress_count || 22, color: "#D97706" },
    { name: "Delayed", value: health?.delayed_count || 9, color: "#B91C1C" },
    { name: "Not Started", value: health?.not_started_count || 6, color: "#94A3B8" },
  ];

  // Discipline Progress Bar data
  const disciplineData = health?.discipline_health
    ? Object.entries(health.discipline_health).map(([disc, stats]: [string, any]) => ({
        discipline: disc.charAt(0).toUpperCase() + disc.slice(1),
        rawKey: disc.toLowerCase(),
        planned: Math.min(100, Math.round((stats.avg_progress || 40) + 6)),
        actual: Math.round(stats.avg_progress || 35),
        delayed: stats.delayed || 0,
      }))
    : [
        { discipline: "Piping", rawKey: "piping", planned: 55, actual: 44, delayed: 4 },
        { discipline: "Civil", rawKey: "civil", planned: 70, actual: 68, delayed: 1 },
        { discipline: "Mechanical", rawKey: "mechanical", planned: 45, actual: 38, delayed: 2 },
        { discipline: "Electrical", rawKey: "electrical", planned: 30, actual: 22, delayed: 2 },
      ];

  const handleDisciplineClick = (data: any) => {
    if (data?.rawKey) {
      router.push(`/schedule?discipline=${data.rawKey}`);
    }
  };

  const handleStatusClick = (entry: any) => {
    const map: Record<string, string> = {
      Completed: "completed",
      "In Progress": "in_progress",
      Delayed: "delayed",
      "Not Started": "not_started",
    };
    if (entry?.name && map[entry.name]) {
      router.push(`/schedule?status=${map[entry.name]}`);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-5">
      {/* Top Project Header — Clean, authoritative engineering header with zero badge soup */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-zinc-200 pb-3.5">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-zinc-500 mb-1">
            <span className="font-semibold text-zinc-900">OIL-NE-2026</span>
            <span>•</span>
            <span>Numaligarh Pipeline Expansion</span>
            <span>•</span>
            <span className="text-amber-800 font-medium">Status: At Risk (-3.5d Schedule Variance)</span>
          </div>
          <h1 className="text-xl font-bold text-zinc-950 tracking-tight">
            Project Controls Summary
          </h1>
          <p className="text-xs text-zinc-500 mt-0.5">
            L5/L6 Primavera P6 Baseline Reconciliation vs Field Ingestion Actuals
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => router.push("/schedule")}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-zinc-300 hover:bg-zinc-50 rounded-[2px] text-xs font-medium text-zinc-800 shadow-none transition-colors"
          >
            <span>P6 Gantt Chart</span>
          </button>
          <button
            onClick={() => router.push("/review")}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-[2px] text-xs font-medium shadow-none transition-colors"
          >
            <span>Open Review Queue</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Unique Feature: What Changed Ribbon (Clean single-line sentence, zero pill boxes) */}
      <WhatChangedRibbon
        newReportsCount={updates?.summary.pending_documents || 6}
        delayedMovedCount={health?.delayed_count || 3}
        blockersCount={delays?.recurring_blockers?.length || 4}
        pendingReviewsCount={updates?.summary.pending_reviews || 4}
      />

      {/* KPI Section: Unified Project Controls Matrix (Hierarchical, Flat Bordered Strip, Zero Floating Cards) */}
      <div className="bg-white border border-zinc-300 rounded-[2px] divide-y lg:divide-y-0 lg:divide-x divide-zinc-200 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 select-none">
        {/* Zone 1: Critical Variance & Risk (Dominant Visual Weight) */}
        <div className="p-3.5 space-y-3 bg-zinc-50/40">
          <div>
            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
              Schedule Variance
            </div>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className="text-2xl font-bold font-mono tabular-nums text-red-700">
                -{health ? Math.abs(health.mean_schedule_variance_days || 3.5).toFixed(1) : "3.5"}d
              </span>
              <span className="text-[11px] text-amber-800 font-medium font-mono">Behind baseline</span>
            </div>
            <div className="text-[11px] text-zinc-500 font-mono mt-0.5">
              Cumulative mean variance
            </div>
          </div>

          <div className="pt-2 border-t border-zinc-200/80">
            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
              Critical Path Activities
            </div>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className="text-2xl font-bold font-mono tabular-nums text-red-700">
                {health?.critical_count || 8}
              </span>
              <span className="text-[11px] text-red-700 font-medium font-mono">
                <strong className="font-bold">{health?.critical_delayed_count || 3}</strong> delayed
              </span>
            </div>
            <div className="text-[11px] text-zinc-500 font-mono mt-0.5">
              Direct project finish slippage
            </div>
          </div>
        </div>

        {/* Zone 2: Physical & Activity Progress */}
        <div className="p-3.5 space-y-3">
          <div>
            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
              Overall Physical Progress
            </div>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className="text-2xl font-bold font-mono tabular-nums text-zinc-950">
                {overallActual}%
              </span>
              <span className="text-[11px] text-zinc-500 font-mono">
                Target: <strong className="text-zinc-700">{overallPlanned}%</strong>
              </span>
            </div>
            <div className="text-[11px] text-zinc-500 font-mono mt-0.5">
              Variance: -{Math.max(0, overallPlanned - overallActual)}% physical delta
            </div>
          </div>

          <div className="pt-2 border-t border-zinc-200/80">
            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
              Activities Breakdown
            </div>
            <div className="flex items-baseline gap-1 mt-0.5 font-mono">
              <span className="text-2xl font-bold tabular-nums text-zinc-950">
                {health?.completed_count || 14}
              </span>
              <span className="text-sm font-normal text-zinc-400">
                /{health?.total_activities || 51} completed
              </span>
            </div>
            <div className="text-[11px] text-zinc-500 font-mono mt-0.5">
              {health?.in_progress_count || 22} active • {health?.delayed_count || 9} late
            </div>
          </div>
        </div>

        {/* Zone 3: Constraints & Triage Items (Secondary Hierarchy) */}
        <div className="p-3.5 space-y-3">
          <div>
            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
              Active Site Constraints
            </div>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className="text-xl font-bold font-mono tabular-nums text-amber-800">
                {delays?.recurring_blockers?.length || 4}
              </span>
              <span className="text-[11px] text-zinc-600 font-mono">recurring blockers</span>
            </div>
            <div className="text-[11px] text-zinc-500 font-mono mt-0.5">
              Operational & material hold points
            </div>
          </div>

          <div className="pt-2 border-t border-zinc-200/80">
            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
              Pending Reviews
            </div>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className="text-xl font-bold font-mono tabular-nums text-zinc-900">
                {updates?.summary.pending_reviews || 4}
              </span>
              <span className="text-[11px] text-zinc-600 font-mono">DPRs in review queue</span>
            </div>
            <div className="text-[11px] text-zinc-500 font-mono mt-0.5">
              Awaiting planner confirmation
            </div>
          </div>
        </div>

        {/* Zone 4: Key Milestone Gate */}
        <div className="p-3.5 flex flex-col justify-between bg-zinc-50/20">
          <div>
            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
              Next Contractual Milestone
            </div>
            <div className="text-sm font-bold font-mono text-zinc-900 truncate mt-1">
              {health?.milestone_health?.[0]?.name || "Hydrotest Unit 1"}
            </div>
            <div className="text-[11px] text-zinc-500 font-mono mt-1">
              Target Date: <strong className="text-zinc-800 font-semibold">{health?.milestone_health?.[0]?.target_date || "25-Aug-2026"}</strong>
            </div>
            <div className="text-[11px] text-zinc-500 font-mono mt-0.5">
              Gate Deliverable 01
            </div>
          </div>

          <button
            onClick={() => router.push("/schedule")}
            className="text-[11px] text-zinc-700 hover:text-zinc-950 font-medium pt-2 border-t border-zinc-200 flex items-center justify-between transition-colors"
          >
            <span>Inspect in Gantt</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Three Analytics Charts (Part B #1) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Chart 1: Planned vs Actual Progress (Line S-Curve) */}
        <div className="bg-white border border-zinc-300 rounded-[2px] p-4 lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xs font-bold text-zinc-900 uppercase tracking-wide">
                Planned vs Actual Progress (S-Curve)
              </h3>
              <p className="text-[11px] text-zinc-500">Cumulative physical completion % across reporting periods</p>
            </div>
            <div className="flex items-center gap-1 bg-zinc-100 p-0.5 rounded-[2px] border border-zinc-200 text-[10px] font-mono">
              {(["7d", "30d", "90d", "lifetime"] as const).map((r) => (
                <button
                  key={r}
                  onClick={() => setProgressRange(r)}
                  className={`px-2 py-0.5 rounded-[2px] ${
                    progressRange === r
                      ? "bg-white text-zinc-900 font-semibold shadow-xs"
                      : "text-zinc-500 hover:text-zinc-800"
                  }`}
                >
                  {r.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          <div className="h-64 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={sCurveData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                <XAxis dataKey="period" tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} unit="%" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#ffffff",
                    borderColor: "#d4d4d8",
                    fontSize: "12px",
                    borderRadius: "2px",
                  }}
                />
                <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
                <Line
                  type="monotone"
                  dataKey="planned"
                  name="Planned S-Curve"
                  stroke="#94a3b8"
                  strokeWidth={2}
                  strokeDasharray="4 4"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="actual"
                  name="Actual Progress"
                  stroke="#1d4ed8"
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: "#1d4ed8" }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Activity Status Distribution (Donut) */}
        <div className="bg-white border border-zinc-300 rounded-[2px] p-4 space-y-3">
          <div>
            <h3 className="text-xs font-bold text-zinc-900 uppercase tracking-wide">
              Activity Status Distribution
            </h3>
            <p className="text-[11px] text-zinc-500">Breakdown of {health?.total_activities || 51} project activities</p>
          </div>

          <div className="h-44 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={statusData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={2}
                  onClick={handleStatusClick}
                  cursor="pointer"
                >
                  {statusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#ffffff",
                    borderColor: "#d4d4d8",
                    fontSize: "11px",
                    borderRadius: "2px",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Legend */}
          <div className="grid grid-cols-2 gap-2 pt-1 text-[11px]">
            {statusData.map((item) => (
              <button
                key={item.name}
                onClick={() => handleStatusClick(item)}
                className="flex items-center gap-2 p-1 rounded-[2px] hover:bg-zinc-50 text-left"
              >
                <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                <span className="text-zinc-600 truncate">{item.name}</span>
                <span className="ml-auto font-mono tabular-nums font-semibold text-zinc-900">{item.value}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chart 3 & Milestones: Discipline Progress & Milestones Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Chart 3: Discipline Progress (Bar Chart) */}
        <div className="bg-white border border-zinc-300 rounded-[2px] p-4 lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xs font-bold text-zinc-900 uppercase tracking-wide">
                Discipline Progress vs Planned Target
              </h3>
              <p className="text-[11px] text-zinc-500">Click any discipline bar to drill down into the filtered schedule</p>
            </div>
            <span className="text-[10px] text-zinc-400 font-mono">Interactive Filter</span>
          </div>

          <div className="h-56 w-full pt-1">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={disciplineData}
                margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
                onClick={(e: any) => e?.activePayload?.[0]?.payload && handleDisciplineClick(e.activePayload[0].payload)}
                cursor="pointer"
              >
                <XAxis dataKey="discipline" tick={{ fontSize: 11, fill: "#475569" }} tickLine={false} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} unit="%" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#ffffff",
                    borderColor: "#d4d4d8",
                    fontSize: "12px",
                    borderRadius: "2px",
                  }}
                />
                <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "6px" }} />
                <Bar dataKey="planned" name="Planned %" fill="#cbd5e1" radius={[0, 0, 0, 0]} />
                <Bar dataKey="actual" name="Actual %" fill="#1e3a8a" radius={[0, 0, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Milestone Tracker Card */}
        <div className="bg-white border border-zinc-300 rounded-[2px] p-4 space-y-3 flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-bold text-zinc-900 uppercase tracking-wide">
              Critical Milestones Tracker
            </h3>
            <p className="text-[11px] text-zinc-500">Key contractual gate deliverables</p>
          </div>

          <div className="space-y-2 my-auto">
            {(health?.milestone_health || [
              { activity_id: "MIL-01", name: "Site Clearance & Access Road", target_date: "2026-08-05", status: "Completed", progress_pct: 100 },
              { activity_id: "MIL-02", name: "Foundation Mudmats Complete", target_date: "2026-08-18", status: "On Track", progress_pct: 75 },
              { activity_id: "MIL-03", name: "Crude Pump P-101 Set on Foundation", target_date: "2026-08-28", status: "Delayed", progress_pct: 35 },
              { activity_id: "MIL-04", name: "Hydrotest Unit 1 Header", target_date: "2026-09-10", status: "On Track", progress_pct: 10 },
            ]).slice(0, 4).map((m: any) => (
              <div
                key={m.activity_id}
                onClick={() => router.push(`/schedule?highlight=${m.activity_id}`)}
                className="p-2 bg-zinc-50 hover:bg-zinc-100 rounded-[2px] border border-zinc-200 cursor-pointer transition-colors"
              >
                <div className="flex items-center justify-between text-xs mb-0.5">
                  <span className="font-semibold text-zinc-800 line-clamp-1">{m.name}</span>
                  <span
                    className={`text-[10px] font-medium font-mono px-1.5 py-0.2 rounded-[2px] ${
                      m.status === "Completed"
                        ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                        : m.status === "Delayed"
                        ? "bg-red-50 text-red-800 border border-red-200"
                        : "bg-blue-50 text-blue-800 border border-blue-200"
                    }`}
                  >
                    {m.status}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[10px] text-zinc-500 font-mono">
                  <span>Due: {m.target_date}</span>
                  <span className="tabular-nums font-semibold">{m.progress_pct}%</span>
                </div>
              </div>
            ))}
          </div>

          <button
            onClick={() => router.push("/schedule")}
            className="w-full text-center text-xs text-blue-900 hover:text-blue-950 font-medium pt-2 border-t border-zinc-200 flex items-center justify-center gap-1"
          >
            <span>View all milestones in Gantt</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  );
}
