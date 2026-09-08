"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import type { ProgressEvent, ProgressEventList } from "@/lib/types";
import { ConfidenceBadge, DisciplineChip, ConfidenceBar } from "@/components/ConfidenceBadge";
import Link from "next/link";
import { Search, Filter, RefreshCw } from "lucide-react";

const STATUSES = ["all", "matched", "low_confidence_review", "unmatched_new", "declined"] as const;
const DISCIPLINES = ["all", "piping", "civil", "electrical", "instrumentation", "hse", "structural", "mechanical"];

export default function EventsPage() {
  const [events, setEvents] = useState<ProgressEventList | null>(null);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<string>("all");
  const [discipline, setDiscipline] = useState<string>("all");
  const [page, setPage] = useState(1);

  async function load() {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: "20" });
      if (status !== "all") params.set("status", status);
      if (discipline !== "all") params.set("discipline", discipline);
      const data = await apiFetch<ProgressEventList>(`/api/v1/events?${params}`);
      setEvents(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [status, discipline, page]);

  const totalPages = events ? Math.ceil(events.total / 20) : 1;

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold gradient-text">All Events</h1>
          <p className="text-sm text-gray-500 mt-1">
            {events ? `${events.total} total progress events` : "Loading..."}
          </p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors text-sm"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="glass-card p-4 flex flex-wrap gap-4">
        <div>
          <label className="text-xs text-gray-500 block mb-1 font-medium uppercase tracking-wide">Status</label>
          <div className="flex gap-1 flex-wrap">
            {STATUSES.map((s) => (
              <button
                key={s}
                onClick={() => { setStatus(s); setPage(1); }}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  status === s
                    ? "bg-violet-500/20 text-violet-300 border border-violet-500/40"
                    : "bg-gray-800 text-gray-400 hover:text-white border border-transparent"
                }`}
              >
                {s.replace(/_/g, " ")}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1 font-medium uppercase tracking-wide">Discipline</label>
          <div className="flex gap-1 flex-wrap">
            {DISCIPLINES.map((d) => (
              <button
                key={d}
                onClick={() => { setDiscipline(d); setPage(1); }}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  discipline === d
                    ? "bg-violet-500/20 text-violet-300 border border-violet-500/40"
                    : "bg-gray-800 text-gray-400 hover:text-white border border-transparent"
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="glass-card overflow-hidden">
        {loading ? (
          <div className="p-10 text-center text-gray-500 text-sm">Loading events...</div>
        ) : !events || events.items.length === 0 ? (
          <div className="p-10 text-center text-gray-500 text-sm">
            No events found. {status !== "all" && "Try removing filters."}
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-800/50 border-b border-gray-800">
              <tr className="text-gray-400 text-xs uppercase tracking-wide">
                <th className="text-left px-4 py-3 font-medium">Description</th>
                <th className="text-left px-4 py-3 font-medium">Plan Activity</th>
                <th className="text-left px-4 py-3 font-medium">Discipline</th>
                <th className="text-left px-4 py-3 font-medium">Confidence</th>
                <th className="text-left px-4 py-3 font-medium">Status</th>
                <th className="text-left px-4 py-3 font-medium">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/40">
              {events.items.map((ev) => (
                <tr
                  key={ev.id}
                  className="hover:bg-gray-800/30 transition-colors cursor-pointer"
                >
                  <td className="px-4 py-3 max-w-[200px]">
                    <p className="text-gray-200 truncate text-xs">
                      {ev.activity_description_extracted || "—"}
                    </p>
                    {ev.location_reference && (
                      <p className="text-gray-600 text-xs truncate mt-0.5">{ev.location_reference}</p>
                    )}
                  </td>
                  <td className="px-4 py-3 max-w-[180px]">
                    {ev.activity_id_plan ? (
                      <div>
                        <p className="text-gray-400 text-xs font-mono">{ev.activity_id_plan}</p>
                        <p className="text-gray-600 text-xs truncate">{ev.activity_name_plan}</p>
                      </div>
                    ) : (
                      <span className="text-gray-700 italic text-xs">unmatched</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <DisciplineChip discipline={ev.discipline} />
                  </td>
                  <td className="px-4 py-3 w-36">
                    <ConfidenceBar score={ev.confidence_score} />
                  </td>
                  <td className="px-4 py-3">
                    <ConfidenceBadge score={null} status={ev.match_status} />
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-600">
                    {ev.source_type?.replace(/_/g, " ") || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 text-sm rounded bg-gray-800 text-gray-300 disabled:opacity-40 hover:bg-gray-700 transition-colors"
          >
            Previous
          </button>
          <span className="px-3 py-1.5 text-sm text-gray-400">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 text-sm rounded bg-gray-800 text-gray-300 disabled:opacity-40 hover:bg-gray-700 transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
