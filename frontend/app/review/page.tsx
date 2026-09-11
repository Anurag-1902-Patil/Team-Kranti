"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import {
  Check,
  X,
  Edit2,
  PlusCircle,
  FileText,
  AlertTriangle,
  ArrowUpDown,
  Search,
  CheckCircle2,
  Tag,
  Keyboard,
  ExternalLink,
} from "lucide-react";
import { useApp } from "@/lib/AppContext";
import {
  acceptReviewItem,
  declineReviewItem,
  editReviewItem,
  confirmNewActivity,
  fetchAliases,
  decideAlias,
  apiFetch,
} from "@/lib/api";
import type { EntityAlias, ProgressEvent } from "@/lib/types";

function ReviewQueueContent() {
  const searchParams = useSearchParams();
  const highlightId = searchParams.get("highlight");
  const tabParam = searchParams.get("tab");

  const { setReviewCount, openActivityDetail } = useApp();

  const [activeTab, setActiveTab] = useState<"events" | "aliases">(tabParam === "aliases" ? "aliases" : "events");
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [aliases, setAliases] = useState<EntityAlias[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);

  // Modals state
  const [editModalItem, setEditModalItem] = useState<ProgressEvent | null>(null);
  const [correctedActivityId, setCorrectedActivityId] = useState("");
  const [confirmNewModalItem, setConfirmNewModalItem] = useState<ProgressEvent | null>(null);
  const [newActivityName, setNewActivityName] = useState("");
  const [newDiscipline, setNewDiscipline] = useState("piping");
  const [actionProcessing, setActionProcessing] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [queueRes, aliasRes] = await Promise.all([
        apiFetch<{ total: number; items: ProgressEvent[] }>("/api/v1/review/queue?page_size=50").catch(() => ({ total: 0, items: [] })),
        fetchAliases("proposed").catch(() => []),
      ]);

      // Confidence-based Smart Ordering (Part D #5):
      // Lower confidence + is_critical_path first
      const sorted = (queueRes.items || []).sort((a, b) => {
        const critA = a.is_critical_path ? 0 : 1;
        const critB = b.is_critical_path ? 0 : 1;
        if (critA !== critB) return critA - critB;
        return (a.confidence_score || 0) - (b.confidence_score || 0);
      });

      setEvents(sorted);
      setAliases(aliasRes || []);
      setReviewCount(sorted.length);

      if (highlightId) {
        const idx = sorted.findIndex((e) => e.id === highlightId);
        if (idx >= 0) setSelectedIndex(idx);
      }
    } catch (err) {
      console.error("Failed to load review queue:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Keyboard Shortcuts (Part D #6: A = Accept, R = Reject, E = Edit, J/K = Row navigation)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Avoid firing when typing in an input
      if (["INPUT", "TEXTAREA", "SELECT"].includes((e.target as HTMLElement)?.tagName)) {
        return;
      }

      if (activeTab === "events" && events.length > 0) {
        const currentItem = events[selectedIndex];

        if (e.key.toLowerCase() === "j") {
          // Navigate Down
          e.preventDefault();
          setSelectedIndex((prev) => Math.min(events.length - 1, prev + 1));
        } else if (e.key.toLowerCase() === "k") {
          // Navigate Up
          e.preventDefault();
          setSelectedIndex((prev) => Math.max(0, prev - 1));
        } else if (e.key.toLowerCase() === "a" && currentItem) {
          // Accept
          e.preventDefault();
          handleAccept(currentItem.id);
        } else if (e.key.toLowerCase() === "r" && currentItem) {
          // Reject
          e.preventDefault();
          handleDecline(currentItem.id);
        } else if (e.key.toLowerCase() === "e" && currentItem) {
          // Edit
          e.preventDefault();
          setEditModalItem(currentItem);
          setCorrectedActivityId(currentItem.activity_id_plan || "");
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedIndex, events, activeTab]);

  const handleAccept = async (id: string) => {
    setActionProcessing(true);
    try {
      await acceptReviewItem(id, "Accepted via rapid reviewer triage");
      setEvents((prev) => prev.filter((e) => e.id !== id));
      setReviewCount(events.length - 1);
    } catch (err) {
      alert("Error accepting item: " + String(err));
    } finally {
      setActionProcessing(false);
    }
  };

  const handleDecline = async (id: string) => {
    setActionProcessing(true);
    try {
      await declineReviewItem(id, "Declined by planner");
      setEvents((prev) => prev.filter((e) => e.id !== id));
      setReviewCount(events.length - 1);
    } catch (err) {
      alert("Error declining item: " + String(err));
    } finally {
      setActionProcessing(false);
    }
  };

  const handleSaveEdit = async () => {
    if (!editModalItem || !correctedActivityId) return;
    setActionProcessing(true);
    try {
      await editReviewItem(editModalItem.id, correctedActivityId, "Re-matched to different plan activity");
      setEvents((prev) => prev.filter((e) => e.id !== editModalItem.id));
      setReviewCount(events.length - 1);
      setEditModalItem(null);
    } catch (err) {
      alert("Error updating match: " + String(err));
    } finally {
      setActionProcessing(false);
    }
  };

  const handleConfirmNew = async () => {
    if (!confirmNewModalItem || !newActivityName) return;
    setActionProcessing(true);
    try {
      await confirmNewActivity(confirmNewModalItem.id, {
        activity_name: newActivityName,
        discipline: newDiscipline,
      });
      setEvents((prev) => prev.filter((e) => e.id !== confirmNewModalItem.id));
      setReviewCount(events.length - 1);
      setConfirmNewModalItem(null);
    } catch (err) {
      alert("Error creating new activity: " + String(err));
    } finally {
      setActionProcessing(false);
    }
  };

  const handleDecideAlias = async (aliasId: string, decision: "approve" | "reject") => {
    try {
      await decideAlias(aliasId, decision);
      setAliases((prev) => prev.filter((a) => a.id !== aliasId));
    } catch (err) {
      alert("Error deciding alias: " + String(err));
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-200 pb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs font-semibold text-zinc-900 bg-zinc-100 border border-zinc-300 px-2 py-0.5 rounded">
              Human-in-the-Loop Controls
            </span>
            <span className="text-zinc-500 text-xs">OIL-NE-2026</span>
          </div>
          <h1 className="text-lg font-bold text-zinc-900 tracking-tight">
            Field Event & Classification Review Queue
          </h1>
        </div>

        {/* Keyboard Shortcut Hints (Part D #6) */}
        <div className="hidden md:flex items-center gap-2 text-[11px] text-zinc-500 bg-zinc-50 border border-zinc-200 px-2.5 py-1 rounded">
          <Keyboard className="w-3.5 h-3.5 text-zinc-400" />
          <span>Hotkeys:</span>
          <kbd className="bg-white px-1 py-0.5 rounded border border-zinc-200 font-mono text-[10px]">A</kbd> Accept
          <kbd className="bg-white px-1 py-0.5 rounded border border-zinc-200 font-mono text-[10px]">E</kbd> Edit
          <kbd className="bg-white px-1 py-0.5 rounded border border-zinc-200 font-mono text-[10px]">R</kbd> Reject
          <kbd className="bg-white px-1 py-0.5 rounded border border-zinc-200 font-mono text-[10px]">J/K</kbd> Prev/Next
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-3 border-b border-zinc-200 text-xs font-medium">
        <button
          onClick={() => setActiveTab("events")}
          className={`py-2 px-1 border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "events"
              ? "border-blue-700 text-blue-700 font-semibold"
              : "border-transparent text-zinc-500 hover:text-zinc-900"
          }`}
        >
          <span>Progress Events Queue</span>
          <span className="bg-amber-100 text-amber-800 font-mono text-[10px] px-1.5 py-0.2 rounded font-bold">
            {events.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("aliases")}
          className={`py-2 px-1 border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "aliases"
              ? "border-blue-700 text-blue-700 font-semibold"
              : "border-transparent text-zinc-500 hover:text-zinc-900"
          }`}
        >
          <span>Proposed Terminology Aliases</span>
          <span className="bg-zinc-100 text-zinc-700 font-mono text-[10px] px-1.5 py-0.2 rounded">
            {aliases.length}
          </span>
        </button>
      </div>

      {/* Events Queue Tab */}
      {activeTab === "events" && (
        <div className="space-y-3">
          {events.length === 0 ? (
            <div className="bg-white border border-zinc-200 rounded-lg p-12 text-center text-zinc-500 text-xs space-y-2">
              <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
              <div className="font-semibold text-zinc-800">All caught up!</div>
              <p className="text-zinc-400">Zero pending field events awaiting classification triage.</p>
            </div>
          ) : (
            <div className="bg-white border border-zinc-200 rounded-lg overflow-hidden">
              <table className="p6-table">
                <thead>
                  <tr>
                    <th className="w-28">Source</th>
                    <th className="min-w-[220px]">Extracted Event</th>
                    <th className="w-24">Discipline</th>
                    <th className="min-w-[180px]">Proposed Plan Match</th>
                    <th className="w-20 text-center">Confidence</th>
                    <th className="w-36 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((ev, index) => {
                    const isSelected = selectedIndex === index;
                    const conf = ev.confidence_score || 0.0;
                    const isLow = conf < 0.65;

                    return (
                      <tr
                        key={ev.id}
                        onClick={() => setSelectedIndex(index)}
                        className={`cursor-pointer transition-colors ${
                          isSelected ? "bg-blue-50/80" : ""
                        }`}
                      >
                        {/* Source Column */}
                        <td>
                          <div className="text-[11px] font-medium text-zinc-800 capitalize">
                            {ev.source_type?.replace(/_/g, " ") || "DPR"}
                          </div>
                          <div className="font-mono text-[10px] text-zinc-400">
                            {ev.extraction_timestamp ? ev.extraction_timestamp.slice(0, 10) : "15-Aug"}
                          </div>
                        </td>

                        {/* Extracted Event Column */}
                        <td>
                          <div className="text-xs font-semibold text-zinc-900 leading-snug">
                            {ev.activity_description_extracted || "Field Report"}
                          </div>
                          {ev.blocker_description && (
                            <div className="text-[10px] text-red-700 bg-red-50 border border-red-200 px-1 py-0.2 rounded inline-block mt-0.5">
                              Constraint: {ev.blocker_description}
                            </div>
                          )}
                        </td>

                        {/* Discipline */}
                        <td className="capitalize text-[11px] font-mono text-zinc-600">
                          {typeof ev.discipline === "object" ? (ev.discipline as any).value : ev.discipline}
                        </td>

                        {/* Proposed Match */}
                        <td>
                          {ev.activity_id_plan ? (
                            <div>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  openActivityDetail(ev.activity_id_plan!);
                                }}
                                className="font-mono text-xs font-bold text-blue-700 hover:underline flex items-center gap-1"
                              >
                                <span>{ev.activity_id_plan}</span>
                                <ExternalLink className="w-2.5 h-2.5 text-zinc-400" />
                              </button>
                              <div className="text-[11px] text-zinc-600 truncate max-w-xs">
                                {ev.activity_name_plan || "Plan Activity"}
                              </div>
                            </div>
                          ) : (
                            <span className="text-[11px] text-amber-700 font-medium italic">
                              Unmatched (Suggest New)
                            </span>
                          )}
                        </td>

                        {/* Confidence Score */}
                        <td className="text-center font-mono">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[11px] font-bold ${
                              conf >= 0.8
                                ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                                : conf >= 0.6
                                ? "bg-amber-50 text-amber-800 border border-amber-200"
                                : "bg-red-50 text-red-800 border border-red-200"
                            }`}
                          >
                            {(conf * 100).toFixed(0)}%
                          </span>
                        </td>

                        {/* Fast Actions */}
                        <td>
                          <div className="flex items-center justify-center gap-1">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleAccept(ev.id);
                              }}
                              disabled={actionProcessing}
                              className="px-2 py-1 bg-emerald-700 hover:bg-emerald-800 text-white rounded text-[11px] font-medium flex items-center gap-0.5 transition-colors"
                              title="Accept Match (Press 'A')"
                            >
                              <Check className="w-3 h-3" />
                              <span>Accept</span>
                            </button>

                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setEditModalItem(ev);
                                setCorrectedActivityId(ev.activity_id_plan || "");
                              }}
                              className="px-2 py-1 bg-white border border-zinc-300 hover:bg-zinc-100 text-zinc-700 rounded text-[11px] font-medium flex items-center gap-0.5 transition-colors"
                              title="Re-match to other activity (Press 'E')"
                            >
                              <Edit2 className="w-3 h-3" />
                              <span>Edit</span>
                            </button>

                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDecline(ev.id);
                              }}
                              className="px-1.5 py-1 text-zinc-400 hover:text-red-700 hover:bg-red-50 rounded text-[11px] transition-colors"
                              title="Decline / Reject (Press 'R')"
                            >
                              <X className="w-3 h-3" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Aliases Tab */}
      {activeTab === "aliases" && (
        <div className="bg-white border border-zinc-200 rounded-lg overflow-hidden">
          {aliases.length === 0 ? (
            <div className="p-8 text-center text-zinc-400 text-xs">
              No pending terminology aliases requiring review.
            </div>
          ) : (
            <table className="p6-table">
              <thead>
                <tr>
                  <th>Entity Type</th>
                  <th>Raw Field Term</th>
                  <th>Proposed Canonical Mapping</th>
                  <th>Frequency</th>
                  <th className="text-center">Action</th>
                </tr>
              </thead>
              <tbody>
                {aliases.map((al) => (
                  <tr key={al.id}>
                    <td className="capitalize font-medium text-zinc-700">{al.entity_type}</td>
                    <td className="font-mono text-zinc-900 font-semibold">"{al.raw_alias}"</td>
                    <td className="font-mono text-blue-700">→ {al.canonical_name}</td>
                    <td className="font-mono">{al.frequency ? `${al.frequency}x` : "1x"}</td>
                    <td className="text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        <button
                          onClick={() => handleDecideAlias(al.id, "approve")}
                          className="px-2 py-0.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded text-xs font-medium"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => handleDecideAlias(al.id, "reject")}
                          className="px-2 py-0.5 bg-zinc-100 hover:bg-zinc-200 text-zinc-700 rounded text-xs"
                        >
                          Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Edit Match Modal */}
      {editModalItem && (
        <div className="fixed inset-0 bg-black/40 z-60 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg border border-zinc-200 p-5 max-w-md w-full space-y-4 shadow-xl">
            <h3 className="text-sm font-bold text-zinc-900">Re-match Field Event</h3>
            <p className="text-xs text-zinc-600">
              Event: <strong className="text-zinc-900">{editModalItem.activity_description_extracted}</strong>
            </p>

            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">
                Corrected Target Activity ID
              </label>
              <input
                type="text"
                value={correctedActivityId}
                onChange={(e) => setCorrectedActivityId(e.target.value)}
                placeholder="e.g. PIP-101, CIV-204"
                className="w-full border border-zinc-300 rounded px-2.5 py-1.5 text-xs font-mono outline-none focus:border-blue-600"
              />
            </div>

            <div className="flex justify-between items-center pt-2 border-t border-zinc-100">
              <button
                onClick={() => {
                  setConfirmNewModalItem(editModalItem);
                  setNewActivityName(editModalItem.activity_description_extracted || "");
                  setEditModalItem(null);
                }}
                className="text-xs text-blue-700 hover:underline flex items-center gap-1"
              >
                <PlusCircle className="w-3.5 h-3.5" />
                <span>Confirm as New Activity instead</span>
              </button>

              <div className="flex gap-2">
                <button
                  onClick={() => setEditModalItem(null)}
                  className="px-3 py-1.5 text-xs text-zinc-600 hover:bg-zinc-100 rounded"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveEdit}
                  disabled={actionProcessing}
                  className="px-3 py-1.5 text-xs bg-blue-700 hover:bg-blue-800 text-white rounded font-medium"
                >
                  Save Match
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Confirm New Activity Modal */}
      {confirmNewModalItem && (
        <div className="fixed inset-0 bg-black/40 z-60 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg border border-zinc-200 p-5 max-w-md w-full space-y-4 shadow-xl">
            <h3 className="text-sm font-bold text-zinc-900">Confirm as New Field Activity</h3>
            <p className="text-xs text-zinc-500">
              This will insert a new row in <span className="font-mono">plan_activities</span> and immediately embed it in the vector store for future matching.
            </p>

            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">New Activity Name</label>
              <input
                type="text"
                value={newActivityName}
                onChange={(e) => setNewActivityName(e.target.value)}
                className="w-full border border-zinc-300 rounded px-2.5 py-1.5 text-xs outline-none focus:border-blue-600"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-zinc-700 block mb-1">Discipline</label>
              <select
                value={newDiscipline}
                onChange={(e) => setNewDiscipline(e.target.value)}
                className="w-full border border-zinc-300 rounded px-2.5 py-1.5 text-xs outline-none focus:border-blue-600 bg-white"
              >
                <option value="piping">Piping</option>
                <option value="civil">Civil</option>
                <option value="mechanical">Mechanical</option>
                <option value="electrical">Electrical</option>
                <option value="instrumentation">Instrumentation</option>
              </select>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-zinc-100">
              <button
                onClick={() => setConfirmNewModalItem(null)}
                className="px-3 py-1.5 text-xs text-zinc-600 hover:bg-zinc-100 rounded"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmNew}
                disabled={actionProcessing}
                className="px-3 py-1.5 text-xs bg-slate-900 hover:bg-slate-800 text-white rounded font-medium"
              >
                Confirm & Embed
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ReviewQueuePage() {
  return (
    <React.Suspense fallback={<div className="p-8 text-center text-xs text-zinc-400">Loading review queue...</div>}>
      <ReviewQueueContent />
    </React.Suspense>
  );
}
