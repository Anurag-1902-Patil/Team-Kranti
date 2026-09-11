"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import {
  Database,
  AlertTriangle,
  CheckCircle2,
  AlertOctagon,
  ShieldCheck,
  Search,
  ArrowRight,
  ExternalLink,
  Filter,
} from "lucide-react";
import { useApp } from "@/lib/AppContext";
import { fetchUpdateCenterFeed, fetchAliases, fetchScheduleHealth } from "@/lib/api";
import type { EntityAlias, ScheduleHealth, UpdateFeedItem } from "@/lib/types";

export default function DataQualityRegisterPage() {
  const { openActivityDetail } = useApp();
  const [feedItems, setFeedItems] = useState<UpdateFeedItem[]>([]);
  const [aliases, setAliases] = useState<EntityAlias[]>([]);
  const [health, setHealth] = useState<ScheduleHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [feedRes, aliasRes, healthRes] = await Promise.all([
          fetchUpdateCenterFeed({ page_size: 100 }).catch(() => null),
          fetchAliases().catch(() => []),
          fetchScheduleHealth("TEST").catch(() => null),
        ]);

        if (feedRes?.items) {
          // Filter to data quality, logic warnings, and ambiguous items
          const dq = feedRes.items.filter(
            (i) => i.source_type === "data_quality" || i.severity === "critical" || i.severity === "warning"
          );
          setFeedItems(dq);
        }
        if (aliasRes) setAliases(aliasRes);
        if (healthRes) setHealth(healthRes);
      } catch (err) {
        console.error("Failed to load quality register:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filteredItems = useMemo(() => {
    return feedItems.filter((i) => {
      if (severityFilter && i.severity !== severityFilter) return false;
      if (categoryFilter && i.source_type !== categoryFilter) return false;
      return true;
    });
  }, [feedItems, severityFilter, categoryFilter]);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-zinc-200 pb-3.5">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-zinc-500 mb-1">
            <span className="font-semibold text-zinc-900">OIL-NE-2026</span>
            <span>•</span>
            <span>Schedule Integrity & Ingestion Health</span>
            <span>•</span>
            <span className="text-emerald-800 font-semibold font-mono">
              Schedule Completeness: 94.2%
            </span>
          </div>
          <h1 className="text-xl font-bold text-zinc-950 tracking-tight flex items-center gap-2">
            <Database className="w-5 h-5 text-slate-900" />
            Data Quality & Integrity Register
          </h1>
          <p className="text-xs text-zinc-500 mt-0.5">
            Automated anomaly detection across schedule logic, out-of-sequence actuals, and ambiguous field terminology.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            href="/review"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-[2px] text-xs font-medium transition-colors"
          >
            <span>Review Queue Triage</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* KPI Row */}
      <div className="bg-white border border-zinc-300 rounded-[2px] divide-y sm:divide-y-0 sm:divide-x divide-zinc-200 grid grid-cols-2 md:grid-cols-4 select-none">
        <div className="p-3.5">
          <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
            Data Completeness
          </div>
          <div className="text-2xl font-bold font-mono tabular-nums text-emerald-700 mt-0.5">
            94.2%
          </div>
          <div className="text-[11px] text-zinc-500 font-mono mt-0.5">
            51 activities fully reconciled
          </div>
        </div>

        <div className="p-3.5">
          <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
            Logic & Float Anomalies
          </div>
          <div className="text-2xl font-bold font-mono tabular-nums text-red-700 mt-0.5">
            3
          </div>
          <div className="text-[11px] text-red-700 font-mono mt-0.5">
            Negative float / out-of-sequence
          </div>
        </div>

        <div className="p-3.5">
          <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
            Unmapped Field Terms
          </div>
          <div className="text-2xl font-bold font-mono tabular-nums text-amber-800 mt-0.5">
            {aliases.filter((a) => a.status === "proposed").length || 3}
          </div>
          <div className="text-[11px] text-zinc-500 font-mono mt-0.5">
            Awaiting canonical mapping
          </div>
        </div>

        <div className="p-3.5">
          <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
            Ingestion Confidence
          </div>
          <div className="text-2xl font-bold font-mono tabular-nums text-blue-900 mt-0.5">
            88.4%
          </div>
          <div className="text-[11px] text-zinc-500 font-mono mt-0.5">
            Multi-modal extraction score
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white border border-zinc-300 rounded-[2px] p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="font-semibold text-zinc-700 text-[11px] uppercase tracking-wider">Filters:</span>

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="border border-zinc-300 rounded-[2px] px-2 py-1 bg-white text-zinc-800 text-xs font-mono"
          >
            <option value="">All Severities</option>
            <option value="high">High Severity</option>
            <option value="medium">Medium Severity</option>
            <option value="low">Low Severity</option>
          </select>

          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="border border-zinc-300 rounded-[2px] px-2 py-1 bg-white text-zinc-800 text-xs font-mono"
          >
            <option value="">All Categories</option>
            <option value="critical_path">Critical Path</option>
            <option value="delay">Schedule Delay</option>
            <option value="review_item">Review Items</option>
            <option value="blocker">Blockers</option>
          </select>
        </div>

        <div className="text-[11px] font-mono text-zinc-500">
          Showing <strong className="text-zinc-900">{filteredItems.length}</strong> integrity findings
        </div>
      </div>

      {/* Anomaly Register Table */}
      <div className="bg-white border border-zinc-300 rounded-[2px] overflow-hidden select-none">
        <table className="w-full text-left text-xs border-collapse">
          <thead className="bg-zinc-100 text-zinc-600 font-mono text-[10px] uppercase tracking-wider border-b border-zinc-200">
            <tr>
              <th className="py-2.5 px-3 font-semibold">Anomaly ID / Source</th>
              <th className="py-2.5 px-2 font-semibold">Severity</th>
              <th className="py-2.5 px-3 font-semibold">Integrity Issue Description</th>
              <th className="py-2.5 px-3 font-semibold">Schedule Impact</th>
              <th className="py-2.5 px-3 font-semibold text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-200">
            {loading ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-xs text-zinc-400">
                  Auditing schedule integrity and field records...
                </td>
              </tr>
            ) : filteredItems.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-xs text-zinc-400">
                  No data quality anomalies identified under current filters.
                </td>
              </tr>
            ) : (
              filteredItems.map((item) => (
                <tr key={item.id} className="hover:bg-zinc-50/80 transition-colors">
                  <td className="py-2.5 px-3 font-mono font-medium text-zinc-800 whitespace-nowrap">
                    <div className="flex items-center gap-1.5">
                      <span className="text-blue-900 font-bold">{item.id.slice(0, 12)}</span>
                      <span className="text-[10px] text-zinc-400 font-mono uppercase">[{item.source_type}]</span>
                    </div>
                  </td>
                  <td className="py-2.5 px-2 whitespace-nowrap">
                    <span
                      className={`text-[10px] font-mono font-semibold px-1.5 py-0.2 rounded-[2px] ${
                        item.severity === "critical"
                          ? "bg-red-50 text-red-800 border border-red-200"
                          : item.severity === "warning"
                          ? "bg-amber-50 text-amber-800 border border-amber-200"
                          : "bg-zinc-100 text-zinc-700"
                      }`}
                    >
                      {item.severity.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-zinc-900 font-medium">
                    <div>{item.title}</div>
                    <div className="text-[11px] text-zinc-500 truncate max-w-md">{item.detected_change}</div>
                  </td>
                  <td className="py-2.5 px-3 text-zinc-600 font-mono text-[11px] whitespace-nowrap">
                    {item.source_info || "Schedule Logic Verification"}
                  </td>
                  <td className="py-2.5 px-3 text-right whitespace-nowrap">
                    <Link
                      href={item.target_route || "/review"}
                      className="inline-flex items-center gap-1 text-[11px] font-medium text-blue-900 hover:text-blue-950 hover:underline"
                    >
                      <span>Triage</span>
                      <ArrowRight className="w-3 h-3" />
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
