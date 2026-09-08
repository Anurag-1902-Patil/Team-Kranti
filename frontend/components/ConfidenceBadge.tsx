"use client";

import type { MatchStatus, Discipline } from "@/lib/types";

export function ConfidenceBadge({ score, status }: { score: number | null; status: MatchStatus }) {
  const statusConfig: Record<MatchStatus, { label: string; cls: string }> = {
    matched: { label: "Matched", cls: "badge-matched" },
    low_confidence_review: { label: "Review", cls: "badge-review" },
    unmatched_new: { label: "New Activity", cls: "badge-new" },
    declined: { label: "Declined", cls: "badge-declined" },
    pending_match: { label: "Pending", cls: "badge-declined" },
    processing_failed: { label: "Failed", cls: "badge-declined" },
  };

  const { label, cls } = statusConfig[status] ?? { label: status, cls: "badge-declined" };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {label}
      {score !== null && score !== undefined && (
        <span className="opacity-70">{(score * 100).toFixed(0)}%</span>
      )}
    </span>
  );
}

export function DisciplineChip({ discipline }: { discipline: Discipline | string }) {
  const cls = `chip-${discipline.toLowerCase()}`;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize ${cls}`}>
      {discipline}
    </span>
  );
}

export function ConfidenceBar({ score }: { score: number | null }) {
  if (score === null || score === undefined) return null;
  const pct = Math.round(score * 100);
  const color = pct >= 85 ? "bg-emerald-500" : pct >= 55 ? "bg-amber-500" : "bg-rose-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-gray-400 tabular-nums w-8 text-right">{pct}%</span>
    </div>
  );
}
