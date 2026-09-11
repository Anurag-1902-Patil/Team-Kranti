"use client";

import React, { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  BellRing,
  AlertOctagon,
  AlertTriangle,
  Clock,
  ArrowRight,
  Filter,
  CheckCircle2,
  FileText,
  Calendar,
  Layers,
  Database,
} from "lucide-react";
import { useApp } from "@/lib/AppContext";
import { fetchUpdateCenterFeed } from "@/lib/api";
import type { UpdateCenterFeedResponse, UpdateFeedItem } from "@/lib/types";

function UpdateCenterContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialSource = searchParams.get("source") || "";

  const { setUpdateCount, openActivityDetail } = useApp();

  const [feed, setFeed] = useState<UpdateCenterFeedResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [sourceFilter, setSourceFilter] = useState<string>(initialSource);
  const [severityFilter, setSeverityFilter] = useState<string>("");

  const loadFeed = async () => {
    setLoading(true);
    try {
      const res = await fetchUpdateCenterFeed({
        source_type: sourceFilter || undefined,
        severity: severityFilter || undefined,
        page_size: 100,
      });
      setFeed(res);
      setUpdateCount(res.summary.total_items);
    } catch (err) {
      console.error("Failed to load update center feed:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFeed();
  }, [sourceFilter, severityFilter]);

  const handleItemAction = (item: UpdateFeedItem) => {
    if (item.target_route) {
      router.push(item.target_route);
    } else if (item.affected_activity_id) {
      openActivityDetail(item.affected_activity_id);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-200 pb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs font-semibold text-zinc-900 bg-zinc-100 border border-zinc-300 px-2 py-0.5 rounded">
              Daily Control Hub
            </span>
            <span className="text-zinc-500 text-xs">OIL-NE-2026</span>
          </div>
          <h1 className="text-lg font-bold text-zinc-900 tracking-tight">
            Update Center & Exception Feed
          </h1>
        </div>

        <div className="text-xs text-zinc-500 flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-zinc-400" />
          <span>Real-time anomaly & triage stream</span>
        </div>
      </div>

      {/* Summary KPI Chips */}
      {feed && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 text-xs">
          <button
            onClick={() => setSourceFilter("")}
            className={`p-2.5 rounded-lg border text-left transition-colors ${
              sourceFilter === "" ? "bg-slate-900 text-white border-slate-900 font-semibold" : "bg-white border-zinc-200 hover:bg-zinc-50 text-zinc-800"
            }`}
          >
            <div className="text-[10px] text-zinc-400">Total Items</div>
            <div className="text-base font-bold font-mono">{feed.summary.total_items}</div>
          </button>

          <button
            onClick={() => setSourceFilter("review_queue")}
            className={`p-2.5 rounded-lg border text-left transition-colors ${
              sourceFilter === "review_queue" ? "bg-blue-800 text-white border-blue-800 font-semibold" : "bg-white border-zinc-200 hover:bg-zinc-50 text-zinc-800"
            }`}
          >
            <div className="text-[10px] text-zinc-400">Pending Reviews</div>
            <div className="text-base font-bold font-mono text-blue-700">{feed.summary.pending_reviews}</div>
          </button>

          <button
            onClick={() => setSourceFilter("data_quality")}
            className={`p-2.5 rounded-lg border text-left transition-colors ${
              sourceFilter === "data_quality" ? "bg-amber-800 text-white border-amber-800 font-semibold" : "bg-white border-zinc-200 hover:bg-zinc-50 text-zinc-800"
            }`}
          >
            <div className="text-[10px] text-zinc-400">Data Quality Flags</div>
            <div className="text-base font-bold font-mono text-amber-700">{feed.summary.data_quality_flags}</div>
          </button>

          <button
            onClick={() => setSourceFilter("schedule_change")}
            className={`p-2.5 rounded-lg border text-left transition-colors ${
              sourceFilter === "schedule_change" ? "bg-emerald-800 text-white border-emerald-800 font-semibold" : "bg-white border-zinc-200 hover:bg-zinc-50 text-zinc-800"
            }`}
          >
            <div className="text-[10px] text-zinc-400">Schedule Actuals</div>
            <div className="text-base font-bold font-mono text-emerald-700">{feed.summary.schedule_changes}</div>
          </button>

          <button
            onClick={() => setSourceFilter("document")}
            className={`p-2.5 rounded-lg border text-left transition-colors ${
              sourceFilter === "document" ? "bg-slate-800 text-white border-slate-800 font-semibold" : "bg-white border-zinc-200 hover:bg-zinc-50 text-zinc-800"
            }`}
          >
            <div className="text-[10px] text-zinc-400">Ingested Documents</div>
            <div className="text-base font-bold font-mono text-zinc-700">{feed.summary.pending_documents}</div>
          </button>

          <button
            onClick={() => setSourceFilter("entity_alias")}
            className={`p-2.5 rounded-lg border text-left transition-colors ${
              sourceFilter === "entity_alias" ? "bg-slate-800 text-white border-slate-800 font-semibold" : "bg-white border-zinc-200 hover:bg-zinc-50 text-zinc-800"
            }`}
          >
            <div className="text-[10px] text-zinc-400">Proposed Aliases</div>
            <div className="text-base font-bold font-mono text-zinc-700">{feed.summary.pending_aliases}</div>
          </button>
        </div>
      )}

      {/* Filter Bar */}
      <div className="bg-white border border-zinc-200 rounded-lg p-2.5 flex items-center justify-between text-xs">
        <div className="flex items-center gap-3">
          <span className="text-zinc-500 font-medium">Severity:</span>
          <div className="flex items-center gap-1">
            {["", "critical", "warning", "info"].map((sev) => (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev)}
                className={`px-2 py-0.5 rounded text-[11px] font-medium capitalize transition-colors ${
                  severityFilter === sev
                    ? "bg-zinc-800 text-white"
                    : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
                }`}
              >
                {sev || "All"}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={loadFeed}
          className="text-zinc-500 hover:text-zinc-800 text-xs font-medium"
        >
          Refresh Feed
        </button>
      </div>

      {/* Feed List */}
      <div className="space-y-2">
        {loading && !feed ? (
          <div className="bg-white border border-zinc-200 rounded-lg p-12 text-center text-zinc-400 text-xs">
            Loading exception items...
          </div>
        ) : feed?.items && feed.items.length > 0 ? (
          feed.items.map((item) => (
            <div
              key={item.id}
              onClick={() => handleItemAction(item)}
              className="bg-white hover:bg-zinc-50 border border-zinc-200 rounded-lg p-3 cursor-pointer transition-all flex items-start justify-between gap-4 group"
            >
              <div className="space-y-1 flex-1">
                <div className="flex items-center gap-2">
                  <span
                    className={`px-1.5 py-0.2 rounded text-[10px] font-bold uppercase tracking-wider ${
                      item.severity === "critical"
                        ? "bg-red-50 text-red-800 border border-red-200"
                        : item.severity === "warning"
                        ? "bg-amber-50 text-amber-800 border border-amber-200"
                        : "bg-slate-100 text-slate-700 border border-slate-200"
                    }`}
                  >
                    {item.severity}
                  </span>

                  <span className="text-zinc-400 text-[11px] font-mono">
                    {item.source_type.replace(/_/g, " ")}
                  </span>

                  {item.confidence !== null && (
                    <span className="text-zinc-500 text-[10px] font-mono bg-zinc-100 px-1 rounded">
                      {(item.confidence * 100).toFixed(0)}% conf
                    </span>
                  )}

                  <span className="text-zinc-400 text-[10px] font-mono ml-auto sm:ml-0">
                    {item.timestamp ? item.timestamp.slice(0, 16).replace("T", " ") : "15-Aug-2026"}
                  </span>
                </div>

                <div className="text-xs font-semibold text-zinc-900 group-hover:text-blue-800 transition-colors">
                  {item.title}
                </div>

                <div className="text-[11px] text-zinc-600 leading-snug">
                  {item.detected_change}
                </div>

                {item.affected_activity_id && (
                  <div className="text-[10px] text-blue-700 font-mono flex items-center gap-1 pt-0.5">
                    <span>Affects: {item.affected_activity_id}</span>
                    {item.affected_activity_name && (
                      <span className="text-zinc-500 truncate">({item.affected_activity_name})</span>
                    )}
                  </div>
                )}
              </div>

              {/* Action Button linking to originating workflow */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleItemAction(item);
                }}
                className="shrink-0 flex items-center gap-1 px-2.5 py-1 bg-white border border-zinc-300 group-hover:border-blue-600 group-hover:text-blue-700 text-zinc-700 rounded text-xs font-medium transition-colors"
              >
                <span>{item.action_label}</span>
                <ArrowRight className="w-3 h-3 text-zinc-400 group-hover:text-blue-700" />
              </button>
            </div>
          ))
        ) : (
          <div className="bg-white border border-zinc-200 rounded-lg p-12 text-center text-zinc-400 text-xs">
            No items matching selected filters.
          </div>
        )}
      </div>
    </div>
  );
}

export default function UpdateCenterPage() {
  return (
    <React.Suspense fallback={<div className="p-8 text-center text-xs text-zinc-400">Loading updates...</div>}>
      <UpdateCenterContent />
    </React.Suspense>
  );
}
