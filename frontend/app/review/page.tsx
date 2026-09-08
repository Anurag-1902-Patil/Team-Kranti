"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import type { ProgressEvent, ProgressEventList } from "@/lib/types";
import { ConfidenceBadge, DisciplineChip, ConfidenceBar } from "@/components/ConfidenceBadge";
import { CheckCircle, XCircle, Edit3, PlusCircle, ChevronRight, AlertTriangle } from "lucide-react";

export default function ReviewQueuePage() {
  const [queue, setQueue] = useState<ProgressEventList | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<ProgressEvent | null>(null);
  const [action, setAction] = useState<"accept" | "edit" | "decline" | "confirm_new" | null>(null);
  const [notes, setNotes] = useState("");
  const [correctedId, setCorrectedId] = useState("");
  const [newActivityName, setNewActivityName] = useState("");
  const [newDiscipline, setNewDiscipline] = useState("unknown");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");

  async function loadQueue() {
    setLoading(true);
    try {
      const data = await apiFetch<ProgressEventList>("/api/v1/review/queue?page_size=20");
      setQueue(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadQueue();
  }, []);

  async function submitAction() {
    if (!selected || !action) return;
    setSubmitting(true);
    setMessage("");
    try {
      if (action === "accept") {
        await apiFetch(`/api/v1/review/${selected.id}/accept`, {
          method: "POST",
          body: JSON.stringify({ notes }),
        });
        setMessage(`✓ Accepted — actuals written to schedule.`);
      } else if (action === "edit") {
        if (!correctedId.trim()) { setMessage("Please enter a corrected activity ID."); setSubmitting(false); return; }
        await apiFetch(`/api/v1/review/${selected.id}/edit`, {
          method: "POST",
          body: JSON.stringify({ corrected_activity_id: correctedId, notes }),
        });
        setMessage(`✓ Edited — matched to ${correctedId}.`);
      } else if (action === "decline") {
        await apiFetch(`/api/v1/review/${selected.id}/decline`, {
          method: "POST",
          body: JSON.stringify({ notes }),
        });
        setMessage("✓ Declined.");
      } else if (action === "confirm_new") {
        if (!newActivityName.trim()) { setMessage("Please enter the new activity name."); setSubmitting(false); return; }
        await apiFetch(`/api/v1/review/${selected.id}/confirm_new`, {
          method: "POST",
          body: JSON.stringify({ activity_name: newActivityName, discipline: newDiscipline, notes }),
        });
        setMessage(`✓ Confirmed as new field activity. Added to plan and index.`);
      }
      // Reload queue after action
      await loadQueue();
      setSelected(null);
      setAction(null);
    } catch (e: unknown) {
      setMessage(`Error: ${String(e)}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold gradient-text">Review Queue</h1>
        <p className="text-sm text-gray-500 mt-1">
          Events requiring human planner review, sorted by lowest confidence first.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
        {/* Queue List */}
        <div className="lg:col-span-2 space-y-2">
          {loading ? (
            <p className="text-sm text-gray-500 py-4">Loading queue...</p>
          ) : !queue || queue.total === 0 ? (
            <div className="glass-card p-6 text-center">
              <CheckCircle className="w-10 h-10 text-emerald-500 mx-auto mb-3" />
              <p className="text-sm text-gray-400">All caught up! No events pending review.</p>
            </div>
          ) : (
            <>
              <p className="text-xs text-gray-600 font-medium">{queue.total} events pending</p>
              {queue.items.map((ev) => (
                <button
                  key={ev.id}
                  onClick={() => { setSelected(ev); setAction(null); setMessage(""); }}
                  className={`w-full text-left p-3 rounded-xl border transition-all duration-150 ${
                    selected?.id === ev.id
                      ? "bg-violet-500/10 border-violet-500/40"
                      : "glass-card hover:bg-gray-800/60 border-gray-800/60"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-gray-200 truncate font-medium">
                        {ev.activity_description_extracted || "(no description)"}
                      </p>
                      <div className="flex items-center gap-1.5 mt-1">
                        <DisciplineChip discipline={ev.discipline} />
                        <ConfidenceBadge score={null} status={ev.match_status} />
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-gray-600 flex-shrink-0 mt-0.5" />
                  </div>
                  <div className="mt-2">
                    <ConfidenceBar score={ev.confidence_score} />
                  </div>
                </button>
              ))}
            </>
          )}
        </div>

        {/* Review Panel */}
        <div className="lg:col-span-3">
          {!selected ? (
            <div className="glass-card p-8 text-center h-full flex flex-col items-center justify-center">
              <AlertTriangle className="w-10 h-10 text-amber-500/40 mb-3" />
              <p className="text-sm text-gray-500">Select an event from the queue to review it.</p>
            </div>
          ) : (
            <div className="glass-card p-5 space-y-5">
              {/* Event Details */}
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-white">
                      {selected.activity_description_extracted}
                    </p>
                    {selected.location_reference && (
                      <p className="text-xs text-gray-500 mt-0.5">{selected.location_reference}</p>
                    )}
                  </div>
                  <DisciplineChip discipline={selected.discipline} />
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <span className="text-gray-600 uppercase tracking-wide">Best Match</span>
                    <p className="text-gray-300 mt-0.5 font-mono text-[11px]">
                      {selected.activity_id_plan || "—"}
                    </p>
                    <p className="text-gray-500 truncate">{selected.activity_name_plan}</p>
                  </div>
                  <div>
                    <span className="text-gray-600 uppercase tracking-wide">Confidence</span>
                    <div className="mt-1">
                      <ConfidenceBar score={selected.confidence_score} />
                      <ConfidenceBadge score={null} status={selected.match_status} />
                    </div>
                  </div>
                  {selected.actual_start_datetime && (
                    <div>
                      <span className="text-gray-600 uppercase tracking-wide">Actual Start</span>
                      <p className="text-gray-300 mt-0.5">
                        {new Date(selected.actual_start_datetime).toLocaleString()}
                      </p>
                    </div>
                  )}
                  {selected.percent_complete !== null && (
                    <div>
                      <span className="text-gray-600 uppercase tracking-wide">% Complete</span>
                      <p className="text-gray-300 mt-0.5">{selected.percent_complete}%</p>
                    </div>
                  )}
                </div>

                {/* Match candidates */}
                {selected.match_candidates && selected.match_candidates.length > 0 && (
                  <div>
                    <p className="text-xs text-gray-600 uppercase tracking-wide mb-2">Match Candidates</p>
                    <div className="space-y-1">
                      {selected.match_candidates.slice(0, 5).map((c) => (
                        <div
                          key={c.candidate_activity_id}
                          className={`flex items-center justify-between px-3 py-1.5 rounded text-xs ${
                            c.was_selected ? "bg-emerald-500/10 border border-emerald-500/20" : "bg-gray-800/50"
                          }`}
                        >
                          <span className="text-gray-300 font-mono text-[11px]">{c.candidate_activity_id}</span>
                          <span className="text-gray-500 max-w-[140px] truncate">{c.activity_name}</span>
                          <span className="text-gray-400 tabular-nums">
                            {c.final_score !== null ? `${(c.final_score * 100).toFixed(0)}%` : "—"}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="border-t border-gray-800 pt-4">
                {/* Action Buttons */}
                {!action && (
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => setAction("accept")}
                      className="flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/25 transition-colors text-sm font-medium"
                    >
                      <CheckCircle className="w-4 h-4" />
                      Accept
                    </button>
                    <button
                      onClick={() => setAction("edit")}
                      className="flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-blue-500/15 text-blue-400 border border-blue-500/30 hover:bg-blue-500/25 transition-colors text-sm font-medium"
                    >
                      <Edit3 className="w-4 h-4" />
                      Edit Match
                    </button>
                    <button
                      onClick={() => setAction("confirm_new")}
                      className="flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-violet-500/15 text-violet-400 border border-violet-500/30 hover:bg-violet-500/25 transition-colors text-sm font-medium"
                    >
                      <PlusCircle className="w-4 h-4" />
                      New Activity
                    </button>
                    <button
                      onClick={() => setAction("decline")}
                      className="flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-gray-800/80 text-gray-400 border border-gray-700 hover:bg-gray-700 transition-colors text-sm font-medium"
                    >
                      <XCircle className="w-4 h-4" />
                      Decline
                    </button>
                  </div>
                )}

                {/* Action Form */}
                {action && (
                  <div className="space-y-3">
                    <p className="text-sm font-medium text-white capitalize">
                      {action.replace("_", " ")} Event
                    </p>

                    {action === "edit" && (
                      <div>
                        <label className="text-xs text-gray-500 block mb-1">Corrected Activity ID *</label>
                        <input
                          type="text"
                          value={correctedId}
                          onChange={(e) => setCorrectedId(e.target.value)}
                          placeholder="e.g. PIP-002"
                          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-violet-500"
                        />
                      </div>
                    )}

                    {action === "confirm_new" && (
                      <div className="space-y-2">
                        <div>
                          <label className="text-xs text-gray-500 block mb-1">New Activity Name *</label>
                          <input
                            type="text"
                            value={newActivityName}
                            onChange={(e) => setNewActivityName(e.target.value)}
                            placeholder="Descriptive activity name"
                            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-violet-500"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-gray-500 block mb-1">Discipline</label>
                          <select
                            value={newDiscipline}
                            onChange={(e) => setNewDiscipline(e.target.value)}
                            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-violet-500"
                          >
                            {["piping","civil","electrical","instrumentation","hse","structural","mechanical","unknown"].map(d => (
                              <option key={d} value={d}>{d}</option>
                            ))}
                          </select>
                        </div>
                      </div>
                    )}

                    <div>
                      <label className="text-xs text-gray-500 block mb-1">Notes (optional)</label>
                      <textarea
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        rows={2}
                        className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-violet-500 resize-none"
                        placeholder="Optional notes..."
                      />
                    </div>

                    <div className="flex gap-2">
                      <button
                        onClick={submitAction}
                        disabled={submitting}
                        className="flex-1 py-2 rounded-lg bg-violet-600 text-white text-sm font-medium hover:bg-violet-500 disabled:opacity-50 transition-colors"
                      >
                        {submitting ? "Submitting..." : "Confirm"}
                      </button>
                      <button
                        onClick={() => { setAction(null); setMessage(""); }}
                        className="px-4 py-2 rounded-lg bg-gray-800 text-gray-400 text-sm hover:bg-gray-700 transition-colors"
                      >
                        Cancel
                      </button>
                    </div>

                    {message && (
                      <p className={`text-sm ${message.startsWith("✓") ? "text-emerald-400" : "text-rose-400"}`}>
                        {message}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
