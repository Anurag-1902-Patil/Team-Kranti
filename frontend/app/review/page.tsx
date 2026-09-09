"use client";

import React, { useState, useEffect } from "react";
import {
  CheckCircle2,
  XCircle,
  Edit3,
  AlertTriangle,
  RefreshCw,
  BookOpen,
  ListFilter,
  Check,
  X,
  Clock,
  Layers,
} from "lucide-react";
import { apiFetch, fetchAliases, decideAlias } from "@/lib/api";
import type { EntityAlias, ProgressEvent, ProgressEventList } from "@/lib/types";
import ProvenanceBadge from "@/components/ProvenanceBadge";

export default function ReviewQueuePage() {
  const [activeTab, setActiveTab] = useState<"events" | "terminology">("events");

  // Tab 1: Progress Events
  const [queue, setQueue] = useState<ProgressEventList | null>(null);
  const [loadingEvents, setLoadingEvents] = useState(true);
  const [selectedEvent, setSelectedEvent] = useState<ProgressEvent | null>(null);
  const [action, setAction] = useState<"accept" | "edit" | "decline" | null>(null);
  const [correctedId, setCorrectedId] = useState("");
  const [actionNotes, setActionNotes] = useState("");
  const [submittingAction, setSubmittingAction] = useState(false);
  const [eventMessage, setEventMessage] = useState("");

  // Tab 2: Terminology Proposals
  const [aliases, setAliases] = useState<EntityAlias[]>([]);
  const [loadingAliases, setLoadingAliases] = useState(false);
  const [aliasMessage, setAliasMessage] = useState("");

  async function loadEventsQueue() {
    setLoadingEvents(true);
    try {
      const data = await apiFetch<ProgressEventList>("/api/v1/review/queue?page_size=50");
      setQueue(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingEvents(false);
    }
  }

  async function loadProposedAliases() {
    setLoadingAliases(true);
    try {
      const data = await fetchAliases("proposed");
      setAliases(data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingAliases(false);
    }
  }

  useEffect(() => {
    loadEventsQueue();
    loadProposedAliases();
  }, []);

  async function handleEventDecision() {
    if (!selectedEvent || !action) return;
    setSubmittingAction(true);
    setEventMessage("");
    try {
      if (action === "accept") {
        await apiFetch(`/api/v1/review/${selectedEvent.id}/accept`, {
          method: "POST",
          body: JSON.stringify({ notes: actionNotes }),
        });
        setEventMessage("✓ Event accepted — actuals written to schedule.");
      } else if (action === "edit") {
        if (!correctedId.trim()) {
          setEventMessage("Please enter a valid activity ID.");
          setSubmittingAction(false);
          return;
        }
        await apiFetch(`/api/v1/review/${selectedEvent.id}/edit`, {
          method: "POST",
          body: JSON.stringify({
            corrected_activity_id: correctedId.trim(),
            notes: actionNotes,
          }),
        });
        setEventMessage(`✓ Match corrected to ${correctedId}.`);
      } else if (action === "decline") {
        await apiFetch(`/api/v1/review/${selectedEvent.id}/decline`, {
          method: "POST",
          body: JSON.stringify({ notes: actionNotes }),
        });
        setEventMessage("✓ Event declined.");
      }

      await loadEventsQueue();
      setSelectedEvent(null);
      setAction(null);
      setActionNotes("");
      setCorrectedId("");
    } catch (err: unknown) {
      setEventMessage(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setSubmittingAction(false);
    }
  }

  async function handleAliasDecision(aliasId: string, decision: "approve" | "reject") {
    try {
      await decideAlias(aliasId, decision);
      setAliasMessage(`✓ Terminology mapping ${decision}d.`);
      setTimeout(() => setAliasMessage(""), 3000);
      await loadProposedAliases();
    } catch (err: unknown) {
      setAliasMessage(`Failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-5 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-slate-100">
              Planner Review &amp; Quality Gate
            </h1>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-cyan-950 text-cyan-400 border border-cyan-800/60">
              Human-in-the-Loop
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Confidence-gated field events and terminology normalization proposals requiring planner confirmation.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1 p-1 bg-slate-900 border border-slate-800 rounded-lg">
          <button
            onClick={() => setActiveTab("events")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              activeTab === "events"
                ? "bg-cyan-600 text-slate-950 font-semibold"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <ListFilter className="w-3.5 h-3.5" />
            Field Events ({queue?.total || 0})
          </button>
          <button
            onClick={() => setActiveTab("terminology")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              activeTab === "terminology"
                ? "bg-cyan-600 text-slate-950 font-semibold"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            Terminology Proposals ({aliases.length})
          </button>
        </div>
      </div>

      {/* TAB 1: FIELD PROGRESS EVENTS REVIEW */}
      {activeTab === "events" && (
        <div className="space-y-4">
          {eventMessage && (
            <div className={`p-2.5 rounded text-xs flex items-center gap-2 border font-mono ${
              eventMessage.startsWith("✓")
                ? "bg-emerald-950/60 border-emerald-800/60 text-emerald-400"
                : "bg-rose-950/60 border-rose-800/60 text-rose-400"
            }`}>
              <span>{eventMessage}</span>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            {/* Table: Rapid Action Table */}
            <div className="lg:col-span-8 pm-card overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-amber-400" />
                  Events Awaiting Confirmation ({queue?.total || 0})
                </span>
                <button
                  onClick={loadEventsQueue}
                  disabled={loadingEvents}
                  className="p-1 text-slate-400 hover:text-slate-200"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingEvents ? "animate-spin text-cyan-400" : ""}`} />
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="pm-table">
                  <thead>
                    <tr>
                      <th>Source Update Text</th>
                      <th>Candidate Match</th>
                      <th>Tier</th>
                      <th>Provenance</th>
                      <th>Reported Details</th>
                      <th className="text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loadingEvents ? (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-xs text-slate-400">
                          Loading review queue...
                        </td>
                      </tr>
                    ) : !queue || queue.items.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-xs text-slate-400">
                          All caught up! No events currently pending review.
                        </td>
                      </tr>
                    ) : (
                      queue.items.map((ev) => {
                        const isSelected = selectedEvent?.id === ev.id;
                        return (
                          <tr
                            key={ev.id}
                            onClick={() => {
                              setSelectedEvent(ev);
                              setAction(null);
                              setEventMessage("");
                            }}
                            className={`cursor-pointer ${
                              isSelected ? "bg-cyan-950/40 border-l-2 border-l-cyan-400" : ""
                            }`}
                          >
                            <td className="max-w-xs">
                              <p className="font-medium text-slate-200 line-clamp-2">
                                {ev.activity_description_extracted || ev.activity_description_raw}
                              </p>
                              <span className="text-[10px] text-slate-400 font-mono mt-0.5 block">
                                {ev.actual_start_datetime ? ev.actual_start_datetime.substring(0, 10) : "Not reported"}
                              </span>
                            </td>

                            <td className="font-mono text-xs whitespace-nowrap">
                              {ev.activity_id_plan ? (
                                <span className="text-cyan-400 font-semibold">{ev.activity_id_plan}</span>
                              ) : (
                                <span className="text-amber-400 text-[11px]">Unmatched</span>
                              )}
                            </td>

                            <td>
                              <span
                                className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                                  (ev.confidence_score ?? 0.8) >= 0.85
                                    ? "badge-tier-high"
                                    : (ev.confidence_score ?? 0.8) >= 0.65
                                    ? "badge-tier-medium"
                                    : "badge-tier-low"
                                }`}
                              >
                                {ev.confidence_tier?.toUpperCase() || "MED"}
                              </span>
                            </td>

                            <td>
                              <ProvenanceBadge category={ev.provenance_category || "ai_extraction"} />
                            </td>

                            <td className="text-[11px] text-slate-400">
                              <div className="space-y-0.5">
                                <div>Loc: <span className="text-slate-200">{ev.location_area || ev.location_reference || "Not reported"}</span></div>
                                <div>Tag: <span className="text-slate-200 font-mono">{ev.equipment_tag || "Not reported"}</span></div>
                                <div>Progress: <span className="text-slate-200 font-mono">{ev.percent_complete != null ? `${ev.percent_complete}%` : "Not reported"}</span></div>
                              </div>
                            </td>

                            <td className="text-right">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSelectedEvent(ev);
                                  setAction("accept");
                                }}
                                className="px-2 py-1 rounded bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-600/40 text-xs font-medium"
                              >
                                Quick Accept
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Event Review Action Drawer */}
            <div className="lg:col-span-4 pm-card p-4 space-y-4">
              <div className="border-b border-slate-800 pb-2">
                <h2 className="text-xs font-semibold text-slate-100 uppercase tracking-wider font-mono">
                  Planner Decision Panel
                </h2>
              </div>

              {!selectedEvent ? (
                <div className="py-12 text-center text-xs text-slate-400">
                  Select any event from the table to review evidence, candidates, and confirm match.
                </div>
              ) : (
                <div className="space-y-4 text-xs">
                  <div>
                    <p className="text-[11px] text-slate-400 font-mono uppercase">Raw Field Message:</p>
                    <p className="mt-1 p-2 rounded bg-slate-900 border border-slate-800 text-slate-200 text-xs leading-relaxed">
                      {selectedEvent.activity_description_raw || selectedEvent.activity_description_extracted}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
                      <span className="text-slate-400">Discipline:</span>
                      <p className="font-semibold text-slate-200">{String(selectedEvent.discipline).toUpperCase()}</p>
                    </div>
                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
                      <span className="text-slate-400">Confidence:</span>
                      <p className="font-semibold text-cyan-400 font-mono">
                        {Math.round((selectedEvent.confidence_score ?? 0.8) * 100)}%
                      </p>
                    </div>
                  </div>

                  {/* Decision Action Form */}
                  <div className="space-y-2 pt-2 border-t border-slate-800">
                    <p className="text-[11px] font-mono text-slate-400 uppercase">Select Planner Action:</p>
                    <div className="grid grid-cols-3 gap-1.5">
                      <button
                        onClick={() => setAction("accept")}
                        className={`py-1.5 rounded text-xs font-medium border transition-colors ${
                          action === "accept"
                            ? "bg-emerald-600 text-slate-950 font-bold border-emerald-500"
                            : "bg-emerald-950/40 text-emerald-400 border-emerald-800/60 hover:bg-emerald-950/70"
                        }`}
                      >
                        Accept
                      </button>
                      <button
                        onClick={() => {
                          setAction("edit");
                          setCorrectedId(selectedEvent.activity_id_plan || "");
                        }}
                        className={`py-1.5 rounded text-xs font-medium border transition-colors ${
                          action === "edit"
                            ? "bg-cyan-600 text-slate-950 font-bold border-cyan-500"
                            : "bg-cyan-950/40 text-cyan-400 border-cyan-800/60 hover:bg-cyan-950/70"
                        }`}
                      >
                        Change Match
                      </button>
                      <button
                        onClick={() => setAction("decline")}
                        className={`py-1.5 rounded text-xs font-medium border transition-colors ${
                          action === "decline"
                            ? "bg-rose-600 text-slate-950 font-bold border-rose-500"
                            : "bg-rose-950/40 text-rose-400 border-rose-800/60 hover:bg-rose-950/70"
                        }`}
                      >
                        Reject
                      </button>
                    </div>

                    {action === "edit" && (
                      <div className="pt-2">
                        <label className="block text-[11px] font-mono text-slate-400 mb-1">
                          Corrected Activity ID (Primavera P6):
                        </label>
                        <input
                          type="text"
                          value={correctedId}
                          onChange={(e) => setCorrectedId(e.target.value)}
                          placeholder="e.g., PIP-002"
                          className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded text-xs text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
                        />
                      </div>
                    )}

                    {action && (
                      <div className="space-y-2 pt-2">
                        <label className="block text-[11px] font-mono text-slate-400">
                          Planner Review Notes (Audit Trail):
                        </label>
                        <textarea
                          rows={2}
                          value={actionNotes}
                          onChange={(e) => setActionNotes(e.target.value)}
                          placeholder="Rationale for decision..."
                          className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded text-xs text-slate-100 focus:outline-none focus:border-cyan-500 resize-none"
                        />

                        <button
                          onClick={handleEventDecision}
                          disabled={submittingAction}
                          className="w-full py-2 rounded bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold text-xs transition-colors disabled:opacity-50"
                        >
                          {submittingAction ? "Writing to schedule..." : "Submit Review Decision"}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: TERMINOLOGY PROPOSALS (HUMAN-GATED VOCABULARY LEARNING) */}
      {activeTab === "terminology" && (
        <div className="space-y-4">
          <div className="p-3 rounded bg-slate-900/80 border border-slate-800 text-xs text-slate-300">
            <span className="font-semibold text-cyan-400">Human-Gated Terminology Learning:</span>{" "}
            Unrecognized site jargon and local terminology detected in field updates are proposed here.
            They are <span className="underline">never</span> automatically added into canonical matching dictionaries without explicit human planner approval.
          </div>

          {aliasMessage && (
            <div className={`p-2.5 rounded text-xs flex items-center gap-2 border font-mono ${
              aliasMessage.startsWith("✓")
                ? "bg-emerald-950/60 border-emerald-800/60 text-emerald-400"
                : "bg-rose-950/60 border-rose-800/60 text-rose-400"
            }`}>
              <span>{aliasMessage}</span>
            </div>
          )}

          <div className="pm-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="pm-table">
                <thead>
                  <tr>
                    <th>Unrecognized Field Term</th>
                    <th>Suggested Canonical Name</th>
                    <th>Category</th>
                    <th>Frequency</th>
                    <th>Sample Source Context</th>
                    <th>Proposed By</th>
                    <th className="text-right">Human Decision</th>
                  </tr>
                </thead>
                <tbody>
                  {loadingAliases ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-xs text-slate-400">
                        Loading terminology proposals...
                      </td>
                    </tr>
                  ) : aliases.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-xs text-slate-400">
                        No pending terminology proposals. Controlled vocabulary is synchronized.
                      </td>
                    </tr>
                  ) : (
                    aliases.map((al) => (
                      <tr key={al.id}>
                        <td className="font-mono text-cyan-400 font-semibold text-xs whitespace-nowrap">
                          {al.raw_alias}
                        </td>
                        <td className="font-semibold text-slate-200 text-xs whitespace-nowrap">
                          {al.canonical_name}
                        </td>
                        <td>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                            {al.entity_type.toUpperCase()}
                          </span>
                        </td>
                        <td className="font-mono text-xs text-slate-300">
                          {al.frequency} report{al.frequency === 1 ? "" : "s"}
                        </td>
                        <td className="text-xs text-slate-400 max-w-sm truncate">
                          {al.sample_text || "Field WhatsApp message"}
                        </td>
                        <td className="text-[11px] text-slate-400 font-mono">
                          {al.proposed_by}
                        </td>
                        <td className="text-right whitespace-nowrap">
                          <div className="inline-flex items-center gap-1.5">
                            <button
                              onClick={() => handleAliasDecision(al.id, "approve")}
                              className="px-2 py-1 rounded bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-600/40 text-xs font-medium flex items-center gap-1"
                              title="Approve and add to system controlled vocabulary"
                            >
                              <Check className="w-3 h-3" />
                              Approve
                            </button>
                            <button
                              onClick={() => handleAliasDecision(al.id, "reject")}
                              className="px-2 py-1 rounded bg-rose-600/20 hover:bg-rose-600/30 text-rose-400 border border-rose-600/40 text-xs font-medium flex items-center gap-1"
                              title="Reject alias mapping"
                            >
                              <X className="w-3 h-3" />
                              Reject
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
