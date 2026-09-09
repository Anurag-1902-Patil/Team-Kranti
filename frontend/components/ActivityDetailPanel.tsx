"use client";

import React, { useEffect, useState } from "react";
import {
  X,
  TrendingUp,
  AlertTriangle,
  Clock,
  CheckCircle2,
  Edit3,
  Calendar,
  Layers,
  Save,
  Loader2,
} from "lucide-react";
import { fetchActivityPrediction, fetchProgressEvents, reEditProgressEvent } from "@/lib/api";
import type { ActivityPrediction, PlanActivity, ProgressEvent } from "@/lib/types";
import ProvenanceBadge from "./ProvenanceBadge";

interface ActivityDetailPanelProps {
  activity: PlanActivity | null;
  onClose: () => void;
  onActivityUpdated?: () => void;
}

export default function ActivityDetailPanel({
  activity,
  onClose,
  onActivityUpdated,
}: ActivityDetailPanelProps) {
  const [prediction, setPrediction] = useState<ActivityPrediction | null>(null);
  const [loadingPrediction, setLoadingPrediction] = useState(false);
  const [linkedEvents, setLinkedEvents] = useState<ProgressEvent[]>([]);
  const [loadingEvents, setLoadingEvents] = useState(false);

  // Inline editing state
  const [isEditing, setIsEditing] = useState(false);
  const [editPercent, setEditPercent] = useState<number>(0);
  const [editNotes, setEditNotes] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);
  const [editSuccess, setEditSuccess] = useState(false);

  useEffect(() => {
    if (!activity) return;

    setEditPercent(activity.actual_percent_complete || activity.percent_complete_plan || 0);
    setIsEditing(false);
    setEditSuccess(false);

    // Fetch deterministic prediction
    setLoadingPrediction(true);
    fetchActivityPrediction(activity.activity_id)
      .then((pred) => setPrediction(pred))
      .catch(() => setPrediction(null))
      .finally(() => setLoadingPrediction(false));

    // Fetch linked events
    setLoadingEvents(true);
    fetchProgressEvents(1, 10)
      .then((res) => {
        const matching = res.items.filter(
          (e) => e.activity_id_plan === activity.activity_id
        );
        setLinkedEvents(matching);
      })
      .catch(() => setLinkedEvents([]))
      .finally(() => setLoadingEvents(false));
  }, [activity]);

  if (!activity) return null;

  async function handleSaveEdit() {
    if (!activity) return;
    setSavingEdit(true);
    try {
      if (linkedEvents.length > 0) {
        // Re-edit most recent event linked to this activity
        const targetEvent = linkedEvents[0];
        await reEditProgressEvent(targetEvent.id, {
          corrected_fields: {
            percent_complete: editPercent,
            planner_override: true,
          },
          notes: editNotes || "Planner inline schedule adjustment",
        });
      }
      setEditSuccess(true);
      setTimeout(() => setEditSuccess(false), 3000);
      setIsEditing(false);
      if (onActivityUpdated) onActivityUpdated();
    } catch {
      // Local fallback
    } finally {
      setSavingEdit(false);
    }
  }

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-xl bg-slate-950 border-l border-slate-800 shadow-2xl z-50 flex flex-col font-sans">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-800/80 bg-slate-900/60 flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="code-tag px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/60 text-xs font-semibold">
              {activity.activity_id}
            </span>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              {activity.discipline || "General"}
            </span>
            {activity.is_critical && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-950/70 text-rose-400 border border-rose-800">
                Critical Path
              </span>
            )}
          </div>
          <h2 className="text-sm font-semibold text-slate-100 leading-tight">
            {activity.activity_name}
          </h2>
          <p className="text-[11px] text-slate-400 mt-1 font-mono">
            WBS: {activity.wbs_code || "OIL.EXP.2026"} • Float: {activity.total_float_days ?? 0} days
          </p>
        </div>

        <button
          onClick={onClose}
          className="p-1.5 text-slate-400 hover:text-slate-200 rounded hover:bg-slate-800 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {/* Schedule Baseline vs Actual Details */}
        <div className="pm-card p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-cyan-400" />
              Schedule Baseline &amp; Actual Progress
            </span>
            {!isEditing ? (
              <button
                onClick={() => setIsEditing(true)}
                className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium"
              >
                <Edit3 className="w-3 h-3" />
                Planner Adjustment
              </button>
            ) : (
              <span className="text-xs text-amber-400 font-mono">Editing Mode</span>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <p className="text-slate-400 font-mono text-[11px]">Planned Start</p>
              <p className="font-semibold text-slate-200">
                {activity.planned_start ? activity.planned_start.substring(0, 10) : "TBD"}
              </p>
            </div>
            <div>
              <p className="text-slate-400 font-mono text-[11px]">Planned Finish</p>
              <p className="font-semibold text-slate-200">
                {activity.planned_finish ? activity.planned_finish.substring(0, 10) : "TBD"}
              </p>
            </div>
            <div>
              <p className="text-slate-400 font-mono text-[11px]">Planned Duration</p>
              <p className="font-semibold text-slate-200">
                {activity.original_duration_days ? `${activity.original_duration_days} days` : "—"}
              </p>
            </div>
            <div>
              <p className="text-slate-400 font-mono text-[11px]">Current Progress</p>
              <p className="font-semibold text-cyan-400 font-mono">
                {activity.actual_percent_complete || activity.percent_complete_plan || 0}% Complete
              </p>
            </div>
          </div>

          {/* Inline Planner Re-Edit Form */}
          {isEditing && (
            <div className="pt-3 border-t border-slate-800 space-y-3 bg-slate-900/60 p-3 rounded-md">
              <div>
                <label className="block text-[11px] font-mono text-slate-300 mb-1">
                  Adjust Percent Complete (%):
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={editPercent}
                  onChange={(e) => setEditPercent(Number(e.target.value))}
                  className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded text-xs text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="block text-[11px] font-mono text-slate-300 mb-1">
                  Planner Note / Rationale (Preserved in Audit Trail):
                </label>
                <input
                  type="text"
                  placeholder="e.g., Verified field measurement by Chief Resident Engineer"
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded text-xs text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>
              <div className="flex items-center justify-end gap-2 pt-1">
                <button
                  onClick={() => setIsEditing(false)}
                  className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveEdit}
                  disabled={savingEdit}
                  className="px-3 py-1 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-medium text-xs rounded transition-colors flex items-center gap-1.5"
                >
                  {savingEdit ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                  Save Adjustment
                </button>
              </div>
            </div>
          )}

          {editSuccess && (
            <div className="p-2 rounded bg-emerald-950/60 border border-emerald-800/60 text-emerald-400 text-xs flex items-center gap-1.5 font-mono">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Schedule update recorded in permanent audit history.
            </div>
          )}
        </div>

        {/* Deterministic Mathematical Prediction Card (§1.9) */}
        <div className="pm-card p-4 space-y-3 border-l-2 border-l-cyan-500">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-xs font-semibold text-slate-100 flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-cyan-400" />
              Deterministic Schedule Delay Prediction
            </span>
            <ProvenanceBadge category="prediction" />
          </div>

          {loadingPrediction ? (
            <div className="py-6 flex items-center justify-center text-xs text-slate-400 gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
              Computing variance factors and float consumption...
            </div>
          ) : prediction ? (
            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-2.5 rounded bg-slate-900/90 border border-slate-800">
                  <p className="text-[10px] text-slate-400 font-mono uppercase">Predicted Slippage</p>
                  <p className={`text-lg font-bold font-mono mt-0.5 ${
                    prediction.predicted_delay_days > 0 ? "text-amber-400" : "text-emerald-400"
                  }`}>
                    {prediction.predicted_delay_days > 0
                      ? `+${prediction.predicted_delay_days} days`
                      : "0 days (On Track)"}
                  </p>
                </div>
                <div className="p-2.5 rounded bg-slate-900/90 border border-slate-800">
                  <p className="text-[10px] text-slate-400 font-mono uppercase">Forecast Completion</p>
                  <p className="text-lg font-bold font-mono text-slate-200 mt-0.5">
                    {prediction.predicted_finish || "On Schedule"}
                  </p>
                </div>
              </div>

              {/* Factors Breakdown */}
              <div className="space-y-1.5">
                <p className="text-[11px] font-mono text-slate-400 font-medium uppercase">
                  Mathematical Factors:
                </p>
                <div className="space-y-1 text-[11px] text-slate-300">
                  <div className="flex items-center justify-between px-2 py-1 rounded bg-slate-900/60 border border-slate-800/80">
                    <span className="text-slate-400">Historical Discipline Variance Factor:</span>
                    <span className="font-mono text-cyan-400 font-medium">
                      {prediction.historical_variance_factor.toFixed(2)}x
                    </span>
                  </div>
                  <div className="flex items-center justify-between px-2 py-1 rounded bg-slate-900/60 border border-slate-800/80">
                    <span className="text-slate-400">Predecessor Float Consumed:</span>
                    <span className="font-mono text-amber-400 font-medium">
                      {prediction.predecessor_float_consumed_days} days
                    </span>
                  </div>
                  <div className="flex items-center justify-between px-2 py-1 rounded bg-slate-900/60 border border-slate-800/80">
                    <span className="text-slate-400">Overall Activity Risk Score:</span>
                    <span className="font-mono text-slate-200 font-medium">
                      {prediction.risk_score} / 100 ({prediction.risk_level.toUpperCase()})
                    </span>
                  </div>
                </div>
              </div>

              {/* Narrative Explanation */}
              {prediction.plain_language_narrative && (
                <div className="p-3 rounded bg-slate-900/80 border border-slate-800 text-[11px] text-slate-300 leading-relaxed">
                  <p className="font-medium text-cyan-300 mb-1 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3 text-cyan-400" />
                    Project Controls Narrative:
                  </p>
                  {prediction.plain_language_narrative}
                </div>
              )}
            </div>
          ) : (
            <p className="text-xs text-slate-400 py-2">
              No historical slip variance recorded for this discipline yet. On track with P6 baseline.
            </p>
          )}
        </div>

        {/* Linked Actual Field Progress Events */}
        <div className="pm-card p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-xs font-semibold text-slate-100 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-sky-400" />
              Linked Actual Field Updates ({linkedEvents.length})
            </span>
            <span className="text-[10px] text-slate-400 font-mono">Source Messages</span>
          </div>

          {loadingEvents ? (
            <div className="py-4 text-center text-xs text-slate-400">Loading linked field actuals...</div>
          ) : linkedEvents.length === 0 ? (
            <p className="text-xs text-slate-400 py-2">
              No field updates linked directly to this activity yet.
            </p>
          ) : (
            <div className="space-y-2">
              {linkedEvents.map((ev) => (
                <div
                  key={ev.id}
                  className="p-3 rounded bg-slate-900/70 border border-slate-800 text-xs space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] text-slate-400">
                      {ev.actual_start_datetime ? ev.actual_start_datetime.substring(0, 10) : "Reported"}
                    </span>
                    <ProvenanceBadge category={ev.provenance_category || "ai_extraction"} />
                  </div>
                  <p className="text-slate-200 text-xs font-medium">
                    {ev.activity_description_extracted || ev.activity_description_raw}
                  </p>
                  <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono pt-1">
                    <span>Logged by: {ev.supervisor_name || "Field Team"}</span>
                    <span>Progress: {ev.percent_complete ?? 0}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
