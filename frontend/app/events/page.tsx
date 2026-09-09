"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { ProgressEvent, ProgressEventList } from "@/lib/types";
import ProvenanceBadge from "@/components/ProvenanceBadge";
import { Search, RefreshCw, Filter, Layers } from "lucide-react";

const DISCIPLINES = [
  "all", "piping", "civil", "electrical", "instrumentation",
  "mechanical", "structural", "hse", "commissioning", "procurement"
];

const PROVENANCE_FILTERS = [
  "all", "source_fact", "ai_extraction", "ai_inference", "prediction", "human_approval"
];

export default function EventsPage() {
  const [events, setEvents] = useState<ProgressEventList | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedDiscipline, setSelectedDiscipline] = useState<string>("all");
  const [selectedProvenance, setSelectedProvenance] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  async function loadEvents() {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: "30" });
      if (selectedDiscipline !== "all") params.set("discipline", selectedDiscipline);
      const data = await apiFetch<ProgressEventList>(`/api/v1/events?${params}`);
      setEvents(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadEvents();
  }, [selectedDiscipline, page]);

  const filteredItems = (events?.items || []).filter((ev) => {
    if (selectedProvenance !== "all") {
      const p = (ev.provenance_category || "ai_extraction").toLowerCase();
      if (p !== selectedProvenance) return false;
    }
    if (search) {
      const q = search.toLowerCase();
      const matchDesc = ev.activity_description_extracted?.toLowerCase().includes(q) ||
        ev.activity_description_raw?.toLowerCase().includes(q);
      const matchPlan = ev.activity_id_plan?.toLowerCase().includes(q);
      const matchTag = ev.equipment_tag?.toLowerCase().includes(q);
      const matchLoc = ev.location_area?.toLowerCase().includes(q) || ev.location_reference?.toLowerCase().includes(q);
      if (!matchDesc && !matchPlan && !matchTag && !matchLoc) return false;
    }
    return true;
  });

  const totalPages = events ? Math.ceil((events.total || 1) / 30) : 1;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-5 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-slate-100">
              All Field Progress Events
            </h1>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-cyan-950 text-cyan-400 border border-cyan-800/60">
              {events?.total || 0} Ingested Events
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Complete audit register of structured activity events extracted across WhatsApp text, photos, and spreadsheets.
          </p>
        </div>

        <button
          onClick={loadEvents}
          disabled={loading}
          className="px-2.5 py-1.5 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs text-slate-300 flex items-center gap-1.5 transition-colors self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-cyan-400" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Filter Bar */}
      <div className="pm-card p-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search description, activity ID, equipment tag, location..."
              className="w-full pl-8 pr-3 py-1.5 bg-slate-900 border border-slate-700/70 rounded text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Discipline Dropdown */}
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedDiscipline}
              onChange={(e) => {
                setSelectedDiscipline(e.target.value);
                setPage(1);
              }}
              className="bg-slate-900 border border-slate-700/70 text-slate-200 py-1.5 px-2 rounded text-xs focus:outline-none focus:border-cyan-500"
            >
              {DISCIPLINES.map((d) => (
                <option key={d} value={d}>
                  {d === "all" ? "All Disciplines" : d.toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          {/* Provenance Filter Dropdown */}
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <select
              value={selectedProvenance}
              onChange={(e) => setSelectedProvenance(e.target.value)}
              className="bg-slate-900 border border-slate-700/70 text-slate-200 py-1.5 px-2 rounded text-xs focus:outline-none focus:border-cyan-500"
            >
              {PROVENANCE_FILTERS.map((p) => (
                <option key={p} value={p}>
                  {p === "all" ? "All Provenance" : p.replace(/_/g, " ").toUpperCase()}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Events Table */}
      <div className="pm-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="pm-table">
            <thead>
              <tr>
                <th>Date / Time</th>
                <th>Extracted Description</th>
                <th>Discipline</th>
                <th>Matched P6 Activity</th>
                <th>Location / Tag</th>
                <th>Contractor / Crew</th>
                <th>Provenance Category</th>
                <th>Progress %</th>
                <th>Delay / Blocker</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-xs text-slate-400">
                    Loading progress events...
                  </td>
                </tr>
              ) : filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-xs text-slate-400">
                    No progress events found matching current criteria.
                  </td>
                </tr>
              ) : (
                filteredItems.map((ev) => (
                  <tr key={ev.id}>
                    <td className="font-mono text-[11px] text-slate-400 whitespace-nowrap">
                      {ev.actual_start_datetime ? ev.actual_start_datetime.substring(0, 10) : ev.created_at.substring(0, 10)}
                    </td>
                    <td className="max-w-xs">
                      <p className="font-medium text-slate-200 text-xs truncate">
                        {ev.activity_description_extracted || ev.activity_description_raw}
                      </p>
                      {ev.drawing_reference && (
                        <span className="text-[10px] text-slate-400 font-mono mt-0.5 block">
                          DWG: {ev.drawing_reference}
                        </span>
                      )}
                    </td>
                    <td>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                        {String(ev.discipline).toUpperCase()}
                      </span>
                    </td>
                    <td className="font-mono text-xs whitespace-nowrap">
                      {ev.activity_id_plan ? (
                        <Link
                          href={`/schedule?activity_id=${ev.activity_id_plan}`}
                          className="text-cyan-400 hover:underline font-semibold"
                        >
                          {ev.activity_id_plan}
                        </Link>
                      ) : (
                        <span className="text-amber-400 text-xs">Unmatched</span>
                      )}
                    </td>
                    <td className="text-xs text-slate-300 whitespace-nowrap">
                      <div>{ev.location_area || ev.location_reference || "Not reported"}</div>
                      {ev.equipment_tag && (
                        <div className="text-[10px] text-cyan-400 font-mono">{ev.equipment_tag}</div>
                      )}
                    </td>
                    <td className="text-xs text-slate-300 whitespace-nowrap">
                      <div>{ev.contractor_name || "Self-performed"}</div>
                      {ev.supervisor_name && (
                        <div className="text-[10px] text-slate-400">{ev.supervisor_name}</div>
                      )}
                    </td>
                    <td>
                      <ProvenanceBadge category={ev.provenance_category || "ai_extraction"} />
                    </td>
                    <td className="font-mono text-xs text-slate-200 whitespace-nowrap">
                      {ev.percent_complete != null ? `${ev.percent_complete}%` : "—"}
                    </td>
                    <td className="text-xs max-w-xs truncate">
                      {ev.blocker_description ? (
                        <span className="text-rose-400 font-medium">{ev.blocker_description}</span>
                      ) : ev.delay_reason ? (
                        <span className="text-amber-400">{ev.delay_reason}</span>
                      ) : (
                        <span className="text-slate-500 font-mono text-[11px]">On track</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination footer */}
        {totalPages > 1 && (
          <div className="px-4 py-2.5 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <span>
              Page {page} of {totalPages}
            </span>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-2 py-1 rounded bg-slate-900 border border-slate-800 disabled:opacity-40"
              >
                Previous
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-2 py-1 rounded bg-slate-900 border border-slate-800 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
