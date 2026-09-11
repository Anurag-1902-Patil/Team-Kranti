"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  Calendar,
  Clock,
  User,
  FileText,
  TrendingUp,
  History,
  CheckCircle2,
  ChevronRight,
  Edit3,
  BarChart2,
} from "lucide-react";
import { useApp } from "@/lib/AppContext";
import { fetchActivityDetailAggregate, reEditProgressEvent } from "@/lib/api";
import type { ActivityDetailAggregate } from "@/lib/types";

export function ActivityDetailDrawer() {
  const { selectedActivityId, closeActivityDetail } = useApp();
  const [data, setData] = useState<ActivityDetailAggregate | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<
    "identity" | "schedule" | "progress" | "intelligence" | "risk" | "audit"
  >("identity");

  // Re-edit modal state
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editPercent, setEditPercent] = useState<number>(0);
  const [editNotes, setEditNotes] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);

  useEffect(() => {
    if (!selectedActivityId) {
      setData(null);
      return;
    }

    let isMounted = true;
    setLoading(true);
    fetchActivityDetailAggregate(selectedActivityId)
      .then((res) => {
        if (isMounted) {
          setData(res);
          setEditPercent(res.progress.percent_complete || 0);
        }
      })
      .catch((err) => {
        console.error("Failed to load activity detail:", err);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedActivityId]);

  if (!selectedActivityId) return null;

  const handleSaveReEdit = async () => {
    if (!data?.intelligence.latest_event_id) return;
    setSavingEdit(true);
    try {
      await reEditProgressEvent(data.intelligence.latest_event_id, {
        corrected_fields: {
          percent_complete: editPercent,
        },
        notes: editNotes || "Planner adjustment via Activity Detail Drawer",
      });
      // Refresh detail
      const refreshed = await fetchActivityDetailAggregate(selectedActivityId);
      setData(refreshed);
      setEditModalOpen(false);
      setEditNotes("");
    } catch (err) {
      alert("Failed to save correction: " + String(err));
    } finally {
      setSavingEdit(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return <span className="badge-ontrack px-2 py-0.5 rounded text-[11px] font-medium">Completed</span>;
      case "delayed":
        return <span className="badge-delayed px-2 py-0.5 rounded text-[11px] font-medium">Delayed</span>;
      case "in_progress":
        return <span className="badge-atrisk px-2 py-0.5 rounded text-[11px] font-medium">In Progress</span>;
      default:
        return <span className="badge-neutral px-2 py-0.5 rounded text-[11px] font-medium">Planned</span>;
    }
  };

  return (
    <div className="fixed inset-0 bg-black/30 z-50 flex justify-end backdrop-blur-[1px] animate-in fade-in duration-150">
      <div
        className="w-full max-w-2xl bg-white h-full shadow-2xl border-l border-zinc-200 flex flex-col justify-between overflow-hidden animate-in slide-in-from-right duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div className="p-4 border-b border-zinc-200 bg-zinc-50 flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded">
                {selectedActivityId}
              </span>
              {data && getStatusBadge(data.schedule.status)}
              {data?.identity.is_critical && (
                <span className="bg-red-50 text-red-700 border border-red-200 px-1.5 py-0.5 rounded text-[10px] font-semibold">
                  Critical Path
                </span>
              )}
            </div>
            <h2 className="text-sm font-semibold text-zinc-900 line-clamp-1">
              {data ? data.identity.activity_name : "Loading activity..."}
            </h2>
          </div>
          <button
            onClick={closeActivityDetail}
            className="text-zinc-400 hover:text-zinc-700 p-1.5 rounded-md hover:bg-zinc-200/60 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Evidence Breadcrumb Strip (Part D #3) */}
        {data && data.intelligence.evidence_breadcrumb && (
          <div className="px-4 py-2 bg-slate-50 border-b border-zinc-200 flex items-center gap-1.5 text-[11px] overflow-x-auto whitespace-nowrap">
            <span className="text-zinc-400 font-medium">Provenance:</span>
            {data.intelligence.evidence_breadcrumb.map((crumb, idx) => (
              <React.Fragment key={idx}>
                {idx > 0 && <ChevronRight className="w-3 h-3 text-zinc-300 shrink-0" />}
                <span
                  className={`px-1.5 py-0.5 rounded font-mono text-[10px] ${
                    idx === 0
                      ? "bg-white border border-zinc-200 text-zinc-800"
                      : idx === data.intelligence.evidence_breadcrumb.length - 1
                      ? "bg-emerald-50 border border-emerald-200 text-emerald-800 font-semibold"
                      : "bg-blue-50 border border-blue-200 text-blue-800"
                  }`}
                  title={`${crumb.level}: ${crumb.label}`}
                >
                  <span className="text-zinc-400 mr-1">{crumb.level}:</span>
                  {crumb.label}
                </span>
              </React.Fragment>
            ))}
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex border-b border-zinc-200 bg-white px-4 text-xs font-medium text-zinc-600 gap-4">
          {[
            { key: "identity", label: "Identity" },
            { key: "schedule", label: "Schedule" },
            { key: "progress", label: "Progress" },
            { key: "intelligence", label: "Intelligence" },
            { key: "risk", label: "Risk & Forecast" },
            { key: "audit", label: "Audit Trail" },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`py-2.5 border-b-2 transition-colors ${
                activeTab === tab.key
                  ? "border-blue-700 text-blue-700 font-semibold"
                  : "border-transparent hover:text-zinc-900"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content Area */}
        <div className="flex-1 overflow-y-auto p-4 text-xs">
          {loading && !data && (
            <div className="py-12 text-center text-zinc-400">Loading activity details...</div>
          )}

          {data && (
            <>
              {/* Tab 1: Identity */}
              {activeTab === "identity" && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-zinc-50 p-2.5 rounded border border-zinc-200">
                      <div className="text-[10px] text-zinc-400 uppercase font-semibold">Activity ID</div>
                      <div className="font-mono text-zinc-900 font-semibold mt-0.5">{data.identity.activity_id}</div>
                    </div>
                    <div className="bg-zinc-50 p-2.5 rounded border border-zinc-200">
                      <div className="text-[10px] text-zinc-400 uppercase font-semibold">WBS Code</div>
                      <div className="font-mono text-zinc-900 mt-0.5">{data.identity.wbs_code} ({data.identity.wbs_name})</div>
                    </div>
                    <div className="bg-zinc-50 p-2.5 rounded border border-zinc-200">
                      <div className="text-[10px] text-zinc-400 uppercase font-semibold">Discipline</div>
                      <div className="capitalize text-zinc-900 mt-0.5 font-medium">{data.identity.discipline}</div>
                    </div>
                    <div className="bg-zinc-50 p-2.5 rounded border border-zinc-200">
                      <div className="text-[10px] text-zinc-400 uppercase font-semibold">Contractor</div>
                      <div className="text-zinc-900 mt-0.5">{data.identity.contractor_name}</div>
                    </div>
                    <div className="bg-zinc-50 p-2.5 rounded border border-zinc-200">
                      <div className="text-[10px] text-zinc-400 uppercase font-semibold">Area / Unit</div>
                      <div className="text-zinc-900 mt-0.5">{data.identity.area} • {data.identity.unit}</div>
                    </div>
                    <div className="bg-zinc-50 p-2.5 rounded border border-zinc-200">
                      <div className="text-[10px] text-zinc-400 uppercase font-semibold">Critical Path</div>
                      <div className="text-zinc-900 mt-0.5 font-medium">
                        {data.identity.is_critical ? "Yes (Zero / Negative Float)" : "No (Float Available)"}
                      </div>
                    </div>
                  </div>

                  <div className="p-3 bg-slate-50 border border-slate-200 rounded text-slate-800 text-[11px] leading-relaxed">
                    <span className="font-semibold">Full Activity Description:</span> {data.identity.activity_name}
                  </div>
                </div>
              )}

              {/* Tab 2: Schedule */}
              {activeTab === "schedule" && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-2.5 bg-zinc-50 border border-zinc-200 rounded">
                      <div className="text-[10px] text-zinc-400 uppercase font-semibold">Planned Dates</div>
                      <div className="font-mono text-zinc-800 text-[11px] mt-1">
                        Start: {data.schedule.planned_start ? data.schedule.planned_start.slice(0, 10) : "—"}
                      </div>
                      <div className="font-mono text-zinc-800 text-[11px]">
                        Finish: {data.schedule.planned_finish ? data.schedule.planned_finish.slice(0, 10) : "—"}
                      </div>
                    </div>

                    <div className="p-2.5 bg-zinc-50 border border-zinc-200 rounded">
                      <div className="text-[10px] text-zinc-400 uppercase font-semibold">Actual / Current Dates</div>
                      <div className="font-mono text-zinc-800 text-[11px] mt-1">
                        Start: {data.schedule.actual_start ? data.schedule.actual_start.slice(0, 10) : "Not started"}
                      </div>
                      <div className="font-mono text-zinc-800 text-[11px]">
                        Finish: {data.schedule.actual_finish ? data.schedule.actual_finish.slice(0, 10) : "Open"}
                      </div>
                    </div>

                    <div className="p-2.5 bg-zinc-50 border border-zinc-200 rounded">
                      <div className="text-[10px] text-zinc-400 uppercase font-semibold">Original Duration</div>
                      <div className="font-mono text-zinc-800 font-semibold mt-1">
                        {data.schedule.original_duration_days} days
                      </div>
                    </div>

                    <div className="p-2.5 bg-zinc-50 border border-zinc-200 rounded">
                      <div className="text-[10px] text-zinc-400 uppercase font-semibold">Total Float</div>
                      <div className={`font-mono font-semibold mt-1 ${data.schedule.total_float_days < 0 ? "text-red-700" : "text-zinc-800"}`}>
                        {data.schedule.total_float_days.toFixed(1)} days
                      </div>
                    </div>
                  </div>

                  {/* Predecessors / Successors */}
                  <div className="grid grid-cols-2 gap-3 pt-2">
                    <div className="border border-zinc-200 rounded p-2.5">
                      <div className="text-[10px] font-semibold text-zinc-500 uppercase mb-1.5">Predecessors ({data.schedule.predecessors.length})</div>
                      {data.schedule.predecessors.length === 0 ? (
                        <div className="text-zinc-400 text-[11px]">None (Project Start)</div>
                      ) : (
                        <div className="space-y-1">
                          {data.schedule.predecessors.map((p, idx) => (
                            <div key={idx} className="font-mono text-[11px] text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded flex justify-between">
                              <span>{p.activity_id}</span>
                              <span className="text-zinc-400 text-[10px]">{p.type} +{p.lag}d</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="border border-zinc-200 rounded p-2.5">
                      <div className="text-[10px] font-semibold text-zinc-500 uppercase mb-1.5">Successors ({data.schedule.successors.length})</div>
                      {data.schedule.successors.length === 0 ? (
                        <div className="text-zinc-400 text-[11px]">None (Project Finish)</div>
                      ) : (
                        <div className="space-y-1">
                          {data.schedule.successors.map((s, idx) => (
                            <div key={idx} className="font-mono text-[11px] text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded flex justify-between">
                              <span>{s.activity_id}</span>
                              <span className="text-zinc-400 text-[10px]">{s.type} +{s.lag}d</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 3: Progress */}
              {activeTab === "progress" && (
                <div className="space-y-4">
                  <div className="p-3 bg-zinc-50 border border-zinc-200 rounded flex items-center justify-between">
                    <div>
                      <div className="text-[10px] text-zinc-400 uppercase font-semibold">Current Progress</div>
                      <div className="text-lg font-bold text-zinc-900 font-mono">
                        {data.progress.percent_complete.toFixed(0)}%
                      </div>
                    </div>
                    <button
                      onClick={() => setEditModalOpen(true)}
                      className="flex items-center gap-1.5 bg-white border border-zinc-300 hover:bg-zinc-100 text-zinc-700 px-2.5 py-1.5 rounded text-xs font-medium transition-colors"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      <span>Planner Re-edit</span>
                    </button>
                  </div>

                  <div>
                    <div className="font-semibold text-zinc-700 text-xs mb-2">Progress Ingestion History</div>
                    {data.progress.history.length === 0 ? (
                      <div className="text-zinc-400 py-6 text-center">No field progress events recorded yet.</div>
                    ) : (
                      <div className="border border-zinc-200 rounded divide-y divide-zinc-100">
                        {data.progress.history.map((h) => (
                          <div key={h.event_id} className="p-2.5 hover:bg-zinc-50">
                            <div className="flex items-center justify-between text-[11px] mb-1">
                              <span className="font-mono text-zinc-500">{h.timestamp.slice(0, 16).replace("T", " ")}</span>
                              <span className="font-mono font-semibold text-blue-700">
                                {h.percent_complete !== null ? `${h.percent_complete}%` : "Event logged"}
                              </span>
                            </div>
                            <div className="text-zinc-800 text-[11px] leading-snug">
                              {h.extracted_description}
                            </div>
                            {h.blocker_description && (
                              <div className="mt-1 text-[10px] text-amber-800 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200 inline-block">
                                Blocker: {h.blocker_description}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Tab 4: Intelligence & Evidence */}
              {activeTab === "intelligence" && (
                <div className="space-y-4">
                  <div className="p-3 bg-zinc-50 border border-zinc-200 rounded">
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-[10px] text-zinc-400 uppercase font-semibold">Latest Match Confidence</div>
                      <span className="font-mono font-bold text-sm text-blue-700">
                        {data.intelligence.confidence_score
                          ? `${(data.intelligence.confidence_score * 100).toFixed(0)}%`
                          : "N/A"}
                      </span>
                    </div>
                    <div className="text-[11px] text-zinc-700 leading-snug">
                      <span className="font-semibold">Extracted:</span> "{data.intelligence.extracted_description || "—"}"
                    </div>
                  </div>

                  {/* Raw Source Document Excerpt */}
                  {data.intelligence.source_document && (
                    <div className="border border-zinc-200 rounded p-3 bg-white space-y-2">
                      <div className="flex items-center justify-between text-xs text-zinc-500">
                        <div className="font-semibold text-zinc-800 flex items-center gap-1.5">
                          <FileText className="w-3.5 h-3.5 text-zinc-400" />
                          <span>Source Ingestion Record</span>
                        </div>
                        <span className="font-mono text-[10px]">Sender: {data.intelligence.source_document.sender_id}</span>
                      </div>
                      <div className="p-2 bg-zinc-50 rounded border border-zinc-100 font-mono text-[11px] text-zinc-700 whitespace-pre-wrap leading-relaxed">
                        {data.intelligence.source_document.raw_text_excerpt}
                      </div>
                    </div>
                  )}

                  {/* Considered Match Candidates */}
                  <div>
                    <div className="font-semibold text-zinc-700 text-xs mb-2">Candidate Evaluation Scores</div>
                    <div className="border border-zinc-200 rounded divide-y divide-zinc-100 text-[11px]">
                      {data.intelligence.match_candidates.map((c, idx) => (
                        <div key={idx} className="p-2 flex items-center justify-between">
                          <span className="font-mono text-zinc-800">{c.candidate_activity_id}</span>
                          <div className="flex items-center gap-3 font-mono text-[10px] text-zinc-500">
                            <span>Fuzzy: {c.fuzzy_score?.toFixed(2) || "—"}</span>
                            <span>Semantic: {c.semantic_score?.toFixed(2) || "—"}</span>
                            <span>LLM: {c.llm_score?.toFixed(2) || "—"}</span>
                            <span className="font-bold text-blue-700">Final: {c.final_score?.toFixed(2) || "—"}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 5: Risk & Forecast with Explainability Strip (Part D #4) */}
              {activeTab === "risk" && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-2.5 bg-zinc-50 border border-zinc-200 rounded">
                      <div className="text-[10px] text-zinc-400 uppercase font-semibold">Predicted Finish Date</div>
                      <div className="font-mono text-zinc-900 font-bold text-sm mt-1">
                        {data.risk.predicted_finish || "Within Baseline"}
                      </div>
                    </div>
                    <div className="p-2.5 bg-zinc-50 border border-zinc-200 rounded">
                      <div className="text-[10px] text-zinc-400 uppercase font-semibold">Predicted Delay</div>
                      <div className="font-mono text-amber-800 font-bold text-sm mt-1">
                        +{data.risk.predicted_delay_days.toFixed(1)} days
                      </div>
                    </div>
                  </div>

                  {/* Prediction Explainability Strip (Part D #4) */}
                  <div className="p-3 bg-white border border-zinc-200 rounded space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="font-semibold text-zinc-800 flex items-center gap-1.5 text-xs">
                        <BarChart2 className="w-3.5 h-3.5 text-blue-700" />
                        <span>Prediction Explainability Strip</span>
                      </div>
                      <span className="text-[10px] text-zinc-400">Historical Benchmarks Used</span>
                    </div>

                    <p className="text-[11px] text-zinc-600 leading-relaxed">
                      Forecast computed deterministically from past progress variances in the{" "}
                      <strong className="text-zinc-800 capitalize">{data.identity.discipline}</strong> discipline:
                    </p>

                    {data.risk.explainability_strip && data.risk.explainability_strip.length > 0 ? (
                      <div className="space-y-1.5 pt-1">
                        {data.risk.explainability_strip.slice(0, 4).map((hist, i) => (
                          <div
                            key={i}
                            className="flex items-center justify-between bg-zinc-50 px-2.5 py-1.5 rounded border border-zinc-200 text-[11px] font-mono"
                          >
                            <span className="text-zinc-700">{hist.activity_id_plan}</span>
                            <div className="flex items-center gap-3">
                              <span className="text-zinc-500">Plan: {hist.planned_duration_days}d</span>
                              <span className="text-zinc-900 font-medium">Act: {hist.actual_duration_days}d</span>
                              <span className={hist.variance_days > 0 ? "text-amber-700 font-bold" : "text-emerald-700"}>
                                {hist.variance_days > 0 ? `+${hist.variance_days}d` : `${hist.variance_days}d`}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-zinc-400 text-[11px] italic">
                        Standard variance prior applied (0.5d conservative factor).
                      </div>
                    )}
                  </div>

                  {/* Narrative Summary */}
                  {data.risk.narrative && (
                    <div className="p-3 bg-slate-50 border border-slate-200 rounded text-[11px] text-slate-800 leading-relaxed">
                      <span className="font-semibold">Analysis:</span> {data.risk.narrative}
                    </div>
                  )}
                </div>
              )}

              {/* Tab 6: Audit Trail */}
              {activeTab === "audit" && (
                <div className="space-y-4">
                  <div>
                    <div className="font-semibold text-zinc-700 text-xs mb-2">Planner Review Decisions</div>
                    {data.audit.decisions.length === 0 ? (
                      <div className="text-zinc-400 py-6 text-center">No human review decisions recorded yet.</div>
                    ) : (
                      <div className="border border-zinc-200 rounded divide-y divide-zinc-100">
                        {data.audit.decisions.map((d) => (
                          <div key={d.decision_id} className="p-2.5 text-xs">
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-semibold text-zinc-800 capitalize">{d.decision}</span>
                              <span className="font-mono text-[10px] text-zinc-400">
                                {d.decided_at ? d.decided_at.slice(0, 16).replace("T", " ") : "—"}
                              </span>
                            </div>
                            <div className="text-zinc-600 text-[11px]">
                              Reviewer: <span className="font-medium text-zinc-800">{d.reviewer}</span>
                            </div>
                            {d.notes && <div className="mt-1 text-zinc-500 italic text-[11px]">"{d.notes}"</div>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Correction History */}
                  {data.audit.correction_history && data.audit.correction_history.length > 0 && (
                    <div>
                      <div className="font-semibold text-zinc-700 text-xs mb-2">Re-edit Correction History</div>
                      <div className="border border-zinc-200 rounded divide-y divide-zinc-100 text-[11px]">
                        {data.audit.correction_history.map((c, i) => (
                          <div key={i} className="p-2.5">
                            <div className="font-mono text-[10px] text-zinc-400">{c.edited_at} by {c.edited_by}</div>
                            <div className="text-zinc-700 mt-0.5">Notes: {c.notes || "No notes"}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Drawer Footer */}
        <div className="p-3 border-t border-zinc-200 bg-zinc-50 flex items-center justify-between text-xs">
          <span className="text-zinc-400 font-mono text-[11px]">OIL-NE-2026</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setEditModalOpen(true)}
              className="px-3 py-1.5 bg-white border border-zinc-300 hover:bg-zinc-100 rounded text-zinc-700 font-medium transition-colors"
            >
              Adjust Actuals
            </button>
            <button
              onClick={closeActivityDetail}
              className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded font-medium transition-colors"
            >
              Close
            </button>
          </div>
        </div>

        {/* Re-edit Modal */}
        {editModalOpen && (
          <div className="fixed inset-0 bg-black/40 z-60 flex items-center justify-center p-4">
            <div className="bg-white rounded-lg border border-zinc-200 p-4 max-w-sm w-full space-y-4 shadow-xl">
              <h3 className="text-sm font-bold text-zinc-900">Planner Re-edit Actuals</h3>
              <div>
                <label className="text-xs font-semibold text-zinc-700 block mb-1">Percent Complete (%)</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={editPercent}
                  onChange={(e) => setEditPercent(Number(e.target.value))}
                  className="w-full border border-zinc-300 rounded px-2 py-1.5 text-xs font-mono outline-none focus:border-blue-600"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-zinc-700 block mb-1">Reason / Notes</label>
                <textarea
                  rows={3}
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  placeholder="Audit explanation for this correction..."
                  className="w-full border border-zinc-300 rounded p-2 text-xs outline-none focus:border-blue-600"
                />
              </div>
              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  onClick={() => setEditModalOpen(false)}
                  className="px-3 py-1.5 text-xs text-zinc-600 hover:bg-zinc-100 rounded"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveReEdit}
                  disabled={savingEdit}
                  className="px-3 py-1.5 text-xs bg-blue-700 hover:bg-blue-800 text-white rounded font-medium disabled:opacity-50"
                >
                  {savingEdit ? "Saving..." : "Save Correction"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
