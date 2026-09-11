"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Sparkles, ArrowRight, X, Clock, AlertTriangle, CheckCircle2 } from "lucide-react";

interface WhatChangedRibbonProps {
  newReportsCount?: number;
  delayedMovedCount?: number;
  blockersCount?: number;
  pendingReviewsCount?: number;
}

export function WhatChangedRibbon({
  newReportsCount = 6,
  delayedMovedCount = 3,
  blockersCount = 4,
  pendingReviewsCount = 4,
}: WhatChangedRibbonProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div className="bg-zinc-50 border border-zinc-200 px-3.5 py-2 text-xs text-zinc-700 flex items-center justify-between select-none">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="font-semibold text-zinc-900">Since your last visit:</span>
        <span>
          <strong className="font-mono tabular-nums font-bold text-zinc-900">{newReportsCount}</strong> new DPRs ingested,{" "}
          <strong className="font-mono tabular-nums font-bold text-amber-800">{delayedMovedCount}</strong> activities flagged delayed,{" "}
          <strong className="font-mono tabular-nums font-bold text-red-700">{blockersCount}</strong> site blockers reported,{" "}
          <strong className="font-mono tabular-nums font-bold text-zinc-900">{pendingReviewsCount}</strong> pending review triage
        </span>
      </div>

      <div className="flex items-center gap-3 shrink-0 ml-4">
        <Link
          href="/updates"
          className="font-medium text-blue-900 hover:text-blue-950 flex items-center gap-1 hover:underline text-xs"
        >
          <span>Triage in Update Center</span>
          <ArrowRight className="w-3 h-3" />
        </Link>
        <button
          onClick={() => setDismissed(true)}
          className="text-zinc-400 hover:text-zinc-700 p-0.5 transition-colors"
          title="Dismiss notification"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
