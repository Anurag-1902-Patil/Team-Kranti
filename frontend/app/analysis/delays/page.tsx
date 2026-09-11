"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
  PieChart,
  Pie,
} from "recharts";
import { fetchDelayAnalyticsDetailed } from "@/lib/api";
import { useApp } from "@/lib/AppContext";
import type { DelayAnalyticsResponse, MajorDelayRecord } from "@/lib/types";

const CAUSE_COLORS = [
  "#1E3A8A", // slate navy
  "#2563EB", // blue
  "#0D9488", // teal
  "#D97706", // amber
  "#DC2626", // red
  "#7C3AED", // violet
  "#475569", // slate
  "#059669", // emerald
  "#EA580C", // orange
  "#9333EA", // purple
  "#4B5563", // gray
  "#0284C7", // light blue
];

export default function DelayAnalysisPage() {
  const { openActivityDetail } = useApp();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<DelayAnalyticsResponse | null>(null);

  // Filter states
  const [disciplineFilter, setDisciplineFilter] = useState<string>("");
  const [contractorFilter, setContractorFilter] = useState<string>("");
  const [causeFilter, setCauseFilter] = useState<string>("");
  const [locationFilter, setLocationFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchDelayAnalyticsDetailed({
        discipline: disciplineFilter || undefined,
        contractor: contractorFilter || undefined,
        cause: causeFilter || undefined,
        location: locationFilter || undefined,
      });
      setData(res);
    } catch (err) {
      console.error("Failed to load delay analytics:", err);
      setError("Unable to load delay intelligence records. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [disciplineFilter, contractorFilter, causeFilter, locationFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const resetFilters = () => {
    setDisciplineFilter("");
    setContractorFilter("");
    setCauseFilter("");
    setLocationFilter("");
    setSearchQuery("");
  };

  // Distinct filter options extracted from the current dataset or known lists
  const disciplines = useMemo(() => {
    if (!data?.by_discipline) return ["Civil", "Piping", "Electrical", "Instrumentation", "Mechanical", "Structure"];
    return Array.from(new Set(data.by_discipline.map((d) => d.discipline))).filter(Boolean);
  }, [data]);

  const contractors = useMemo(() => {
    if (!data?.by_contractor) return [];
    return Array.from(new Set(data.by_contractor.map((c) => c.contractor))).filter(Boolean);
  }, [data]);

  const causes = useMemo(() => {
    if (!data?.cause_breakdown) return [];
    return Array.from(new Set(data.cause_breakdown.map((c) => c.cause))).filter(Boolean);
  }, [data]);

  // Client-side search in Major Delays table
  const filteredMajorDelays = useMemo(() => {
    if (!data?.major_delays) return [];
    if (!searchQuery.trim()) return data.major_delays;
    const q = searchQuery.toLowerCase();
    return data.major_delays.filter(
      (m) =>
        m.activity_id.toLowerCase().includes(q) ||
        m.activity_name.toLowerCase().includes(q) ||
        m.contractor.toLowerCase().includes(q) ||
        m.reason.toLowerCase().includes(q) ||
        m.cause.toLowerCase().includes(q) ||
        m.recommended_action.toLowerCase().includes(q)
    );
  }, [data?.major_delays, searchQuery]);

  return (
    <div className="space-y-4 pb-12">
      {/* Header & Page Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-200 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">Delay Intelligence & Impact Register</h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-800 border border-blue-200">
              P6 L5/L6 Schedule Baseline
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            Root-cause breakdown, contractor delay ratios, critical-path impact, and AI-grounded mitigation actions.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => loadData()}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors shadow-xs"
          >
            <svg className="w-3.5 h-3.5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="p-3 bg-white border border-gray-200 rounded-lg shadow-xs flex flex-wrap items-center gap-2.5 text-xs">
        <span className="font-semibold text-gray-600 uppercase tracking-wider text-[10px] mr-1">Filters:</span>

        {/* Discipline Filter */}
        <select
          value={disciplineFilter}
          onChange={(e) => setDisciplineFilter(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1 bg-white text-gray-800 text-xs focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">All Disciplines</option>
          {disciplines.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>

        {/* Contractor Filter */}
        <select
          value={contractorFilter}
          onChange={(e) => setContractorFilter(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1 bg-white text-gray-800 text-xs focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">All Contractors</option>
          {contractors.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>

        {/* Cause Filter */}
        <select
          value={causeFilter}
          onChange={(e) => setCauseFilter(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1 bg-white text-gray-800 text-xs focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">All Root Causes</option>
          {causes.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>

        {/* Location Input */}
        <input
          type="text"
          placeholder="Filter Location/Area..."
          value={locationFilter}
          onChange={(e) => setLocationFilter(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1 bg-white text-gray-800 text-xs w-36 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        />

        {(disciplineFilter || contractorFilter || causeFilter || locationFilter) && (
          <button
            onClick={resetFilters}
            className="text-xs text-blue-700 hover:text-blue-900 font-medium px-2 py-1 hover:bg-blue-50 rounded"
          >
            Clear Filters
          </button>
        )}
      </div>

      {loading && !data && (
        <div className="p-12 text-center text-sm text-gray-500 bg-white border border-gray-200 rounded-lg">
          <div className="inline-block animate-spin w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full mb-2"></div>
          <p>Analyzing schedule actuals and delay events...</p>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-800 text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => loadData()} className="underline font-medium hover:text-red-900">
            Retry
          </button>
        </div>
      )}

      {data && (
        <>
          {/* KPI Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-white p-3.5 rounded-lg border border-gray-200 shadow-xs">
              <span className="text-[11px] font-medium text-gray-500 uppercase tracking-wider block">
                Delayed Activities
              </span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-bold text-gray-900">{data.kpis.total_delayed_activities}</span>
                <span className="text-xs text-gray-500">activities</span>
              </div>
              <span className="text-[11px] text-amber-700 mt-1 block">
                {data.total_delay_events} recorded delay events
              </span>
            </div>

            <div className="bg-white p-3.5 rounded-lg border border-gray-200 shadow-xs">
              <span className="text-[11px] font-medium text-gray-500 uppercase tracking-wider block">
                Total Delay Days
              </span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-bold text-amber-700">{data.kpis.total_delay_days}</span>
                <span className="text-xs text-gray-500">cumulative days</span>
              </div>
              <span className="text-[11px] text-gray-500 mt-1 block">
                Max single activity delay: <strong className="text-gray-700">{data.kpis.max_delay_days}d</strong>
              </span>
            </div>

            <div className="bg-white p-3.5 rounded-lg border border-gray-200 shadow-xs">
              <span className="text-[11px] font-medium text-gray-500 uppercase tracking-wider block">
                Average Activity Delay
              </span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-bold text-gray-900">
                  {typeof data.kpis.average_delay_days === "number" ? data.kpis.average_delay_days.toFixed(1) : "0.0"}
                </span>
                <span className="text-xs text-gray-500">days / delayed act.</span>
              </div>
              <span className="text-[11px] text-gray-500 mt-1 block">Mean schedule variance</span>
            </div>

            <div className="bg-white p-3.5 rounded-lg border border-gray-200 shadow-xs">
              <span className="text-[11px] font-medium text-gray-500 uppercase tracking-wider block">
                Critical Path Slippage
              </span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-bold text-red-700">{data.kpis.critical_delayed_count}</span>
                <span className="text-xs text-gray-500">critical activities</span>
              </div>
              <span className="text-[11px] text-red-600 font-medium mt-1 block">Direct project finish impact</span>
            </div>
          </div>

          {/* Charts Row: Trend Line & Cause Breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Delay Accumulation Trend */}
            <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-xs">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="text-xs font-bold text-gray-900 uppercase tracking-wider">Delay Accumulation Trend</h3>
                  <p className="text-[11px] text-gray-500">Cumulative delay days & monthly recorded delay incidents</p>
                </div>
                <span className="text-[10px] text-gray-400 font-mono">Monthly Timeline</span>
              </div>

              {data.trend && data.trend.length > 0 ? (
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data.trend} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                      <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#64748B" }} tickLine={false} />
                      <YAxis yAxisId="left" tick={{ fontSize: 11, fill: "#64748B" }} tickLine={false} />
                      <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: "#64748B" }} tickLine={false} />
                      <Tooltip
                        contentStyle={{
                          fontSize: "12px",
                          borderRadius: "4px",
                          borderColor: "#E2E8F0",
                          backgroundColor: "#FFFFFF",
                        }}
                      />
                      <Line
                        yAxisId="left"
                        type="monotone"
                        dataKey="delay_days"
                        name="Delay Days"
                        stroke="#DC2626"
                        strokeWidth={2}
                        dot={{ r: 3, fill: "#DC2626" }}
                        activeDot={{ r: 5 }}
                      />
                      <Line
                        yAxisId="right"
                        type="monotone"
                        dataKey="event_count"
                        name="Incident Count"
                        stroke="#2563EB"
                        strokeWidth={2}
                        strokeDasharray="4 4"
                        dot={{ r: 3, fill: "#2563EB" }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-64 flex items-center justify-center text-xs text-gray-400">
                  No monthly trend data available for current selection
                </div>
              )}
            </div>

            {/* Standard 12 Root Cause Breakdown */}
            <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-xs">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="text-xs font-bold text-gray-900 uppercase tracking-wider">Root Cause Breakdown</h3>
                  <p className="text-[11px] text-gray-500">Distribution across 12 standardized oil & gas delay categories</p>
                </div>
                <span className="text-[10px] text-gray-400 font-mono">Classification</span>
              </div>

              {data.cause_breakdown && data.cause_breakdown.length > 0 ? (
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={data.cause_breakdown.slice(0, 8)}
                      layout="vertical"
                      margin={{ top: 5, right: 25, left: 60, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E2E8F0" />
                      <XAxis type="number" tick={{ fontSize: 10, fill: "#64748B" }} />
                      <YAxis
                        type="category"
                        dataKey="display_name"
                        tick={{ fontSize: 10, fill: "#334155" }}
                        width={80}
                      />
                      <Tooltip
                        formatter={(val: any, name: any) => [
                          name === "count" ? `${val} incidents` : `${val} days`,
                          name === "count" ? "Incidents" : "Delay Days",
                        ]}
                        contentStyle={{
                          fontSize: "12px",
                          borderRadius: "4px",
                          borderColor: "#E2E8F0",
                          backgroundColor: "#FFFFFF",
                        }}
                      />
                      <Bar dataKey="count" name="Incidents" radius={[0, 4, 4, 0]}>
                        {data.cause_breakdown.slice(0, 8).map((_, index) => (
                          <Cell key={`cell-${index}`} fill={CAUSE_COLORS[index % CAUSE_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-64 flex items-center justify-center text-xs text-gray-400">
                  No delay cause distribution recorded
                </div>
              )}
            </div>
          </div>

          {/* Tables Row: Contractor Delay Rankings & Bottlenecks */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Contractor Delay Rankings */}
            <div className="bg-white rounded-lg border border-gray-200 shadow-xs overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
                <div>
                  <h3 className="text-xs font-bold text-gray-900 uppercase tracking-wider">Contractor Delay Rankings</h3>
                  <p className="text-[11px] text-gray-500">Variance factors, delay ratios, and primary drivers by contractor</p>
                </div>
                <span className="text-[10px] text-gray-400 font-mono">{data.by_contractor?.length || 0} contractors</span>
              </div>
              <div className="overflow-x-auto max-h-72">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-gray-100 text-gray-600 text-[10px] uppercase tracking-wider sticky top-0">
                    <tr>
                      <th className="py-2 px-3 font-semibold">Contractor</th>
                      <th className="py-2 px-2 font-semibold text-right">Delayed Act.</th>
                      <th className="py-2 px-2 font-semibold text-right">Delay Ratio</th>
                      <th className="py-2 px-2 font-semibold text-right">Variance Factor</th>
                      <th className="py-2 px-3 font-semibold">Primary Cause</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {data.by_contractor && data.by_contractor.length > 0 ? (
                      data.by_contractor.map((c, idx) => (
                        <tr key={idx} className="hover:bg-gray-50 transition-colors">
                          <td className="py-2 px-3 font-medium text-gray-900 truncate max-w-[140px]" title={c.contractor}>
                            {c.contractor}
                          </td>
                          <td className="py-2 px-2 text-right font-mono text-gray-700">
                            {c.delayed_activities || c.delay_events}
                          </td>
                          <td className="py-2 px-2 text-right font-mono">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                                c.delay_ratio > 0.4
                                  ? "bg-red-50 text-red-700 border border-red-200"
                                  : c.delay_ratio > 0.2
                                  ? "bg-amber-50 text-amber-700 border border-amber-200"
                                  : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              }`}
                            >
                              {(c.delay_ratio * 100).toFixed(0)}%
                            </span>
                          </td>
                          <td className="py-2 px-2 text-right font-mono text-gray-700">
                            {typeof c.avg_variance_factor === "number" ? `${c.avg_variance_factor.toFixed(2)}x` : "1.00x"}
                          </td>
                          <td className="py-2 px-3 text-gray-600 text-[11px] truncate max-w-[130px]" title={c.primary_delay_cause}>
                            {c.primary_delay_cause || "—"}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} className="py-4 text-center text-xs text-gray-400">
                          No contractor records available
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Bottlenecks & Recurring Blockers */}
            <div className="bg-white rounded-lg border border-gray-200 shadow-xs overflow-hidden flex flex-col">
              <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
                <div>
                  <h3 className="text-xs font-bold text-gray-900 uppercase tracking-wider">Bottlenecks & Recurring Blockers</h3>
                  <p className="text-[11px] text-gray-500">High-friction locations and recurring operational impediments</p>
                </div>
              </div>
              <div className="p-3 space-y-3 overflow-y-auto max-h-72">
                {/* Locations */}
                <div>
                  <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1.5">
                    Critical Location Clusters
                  </h4>
                  <div className="space-y-1.5">
                    {data.bottlenecks && data.bottlenecks.length > 0 ? (
                      data.bottlenecks.slice(0, 4).map((b, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between p-2 rounded bg-gray-50 border border-gray-200 text-xs"
                        >
                          <div>
                            <span className="font-semibold text-gray-900">{b.location || b.area || "General Site"}</span>
                            {b.sample_blockers && b.sample_blockers.length > 0 && (
                              <p className="text-[11px] text-gray-500 truncate max-w-xs">{b.sample_blockers[0]}</p>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-red-50 text-red-700 border border-red-200">
                              {b.delayed_events} delayed
                            </span>
                            {b.active_blockers > 0 && (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-amber-50 text-amber-700 border border-amber-200">
                                {b.active_blockers} blockers
                              </span>
                            )}
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-gray-400 italic">No geographic bottleneck clusters identified</p>
                    )}
                  </div>
                </div>

                {/* Recurring Blockers */}
                <div>
                  <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1.5">
                    Recurring Site Blockers
                  </h4>
                  <div className="space-y-1.5">
                    {data.recurring_blockers && data.recurring_blockers.length > 0 ? (
                      data.recurring_blockers.slice(0, 3).map((rb, idx) => (
                        <div
                          key={idx}
                          className="p-2 rounded bg-amber-50/50 border border-amber-200 text-xs flex items-center justify-between"
                        >
                          <div className="truncate max-w-[280px]">
                            <span className="font-medium text-gray-800">{rb.description}</span>
                            <p className="text-[10px] text-gray-500 mt-0.5">
                              Latest: {rb.latest_reported ? new Date(rb.latest_reported).toLocaleDateString() : "Recent"}
                            </p>
                          </div>
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-amber-100 text-amber-800">
                            {rb.occurrences}x repeated
                          </span>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-gray-400 italic">No recurring blocker patterns</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Major Delay Register Table */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-xs overflow-hidden">
            <div className="p-3.5 border-b border-gray-200 bg-gray-50 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h3 className="text-xs font-bold text-gray-900 uppercase tracking-wider">
                  Major Delay Register ({filteredMajorDelays.length})
                </h3>
                <p className="text-[11px] text-gray-500">
                  Itemized delay events with root-cause provenance and grounded recommended mitigations. Click row to inspect.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Search delays, reason, action..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="border border-gray-300 rounded px-2.5 py-1 text-xs bg-white text-gray-800 w-64 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-gray-100 text-gray-600 text-[10px] uppercase tracking-wider">
                  <tr>
                    <th className="py-2.5 px-3 font-semibold">Activity ID</th>
                    <th className="py-2.5 px-3 font-semibold">Activity Name</th>
                    <th className="py-2.5 px-2 font-semibold">Discipline</th>
                    <th className="py-2.5 px-2 font-semibold">Contractor</th>
                    <th className="py-2.5 px-2 font-semibold text-right">Delay</th>
                    <th className="py-2.5 px-3 font-semibold">Root Cause</th>
                    <th className="py-2.5 px-3 font-semibold">Impact Assessment</th>
                    <th className="py-2.5 px-3 font-semibold">Grounded Action Plan</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredMajorDelays.length > 0 ? (
                    filteredMajorDelays.map((item, idx) => (
                      <tr
                        key={idx}
                        onClick={() => openActivityDetail(item.activity_id)}
                        className="hover:bg-blue-50/50 cursor-pointer transition-colors group"
                      >
                        <td className="py-2.5 px-3 font-mono font-medium text-blue-700 group-hover:underline whitespace-nowrap">
                          {item.activity_id}
                        </td>
                        <td className="py-2.5 px-3 font-medium text-gray-900 max-w-[200px] truncate" title={item.activity_name}>
                          {item.activity_name}
                        </td>
                        <td className="py-2.5 px-2 text-gray-600 whitespace-nowrap">
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-gray-100 text-gray-700 font-medium">
                            {item.discipline || "General"}
                          </span>
                        </td>
                        <td className="py-2.5 px-2 text-gray-600 whitespace-nowrap truncate max-w-[120px]" title={item.contractor}>
                          {item.contractor || "—"}
                        </td>
                        <td className="py-2.5 px-2 text-right font-mono font-semibold whitespace-nowrap text-red-600">
                          +{item.delay_days}d
                        </td>
                        <td className="py-2.5 px-3 text-gray-800 whitespace-nowrap">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                            {item.cause}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-gray-600 max-w-[240px] truncate text-[11px]" title={item.impact}>
                          {item.impact || item.reason}
                        </td>
                        <td className="py-2.5 px-3 text-gray-700 max-w-[280px] text-[11px]">
                          <span className="line-clamp-2" title={item.recommended_action}>
                            {item.recommended_action || "Issue site instruction and resequence downstream dependencies."}
                          </span>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={8} className="py-8 text-center text-xs text-gray-400">
                        No delay records match the current filter selection
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
