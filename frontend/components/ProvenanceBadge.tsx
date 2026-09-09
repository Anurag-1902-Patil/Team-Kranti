"use client";

import React from "react";
import type { ProvenanceCategory } from "@/lib/types";
import { Database, Cpu, Sparkles, TrendingUp, CheckCircle2 } from "lucide-react";

interface ProvenanceBadgeProps {
  category: ProvenanceCategory | string | undefined | null;
  confidence?: number | null;
  detail?: string | null;
  showIcon?: boolean;
  size?: "sm" | "md";
}

export default function ProvenanceBadge({
  category,
  confidence,
  detail,
  showIcon = true,
  size = "sm",
}: ProvenanceBadgeProps) {
  const normCategory = (category || "ai_extraction").toLowerCase().replace(/[\s-]/g, "_");

  let label = "AI Extraction";
  let badgeClass = "provenance-ai-extraction";
  let Icon = Cpu;
  let title = "Extracted by AI model from field message / document";

  if (normCategory.includes("source") || normCategory === "source_fact") {
    label = "Source Fact";
    badgeClass = "provenance-source-fact";
    Icon = Database;
    title = "Hard record from Primavera P6 schedule baseline or equipment master";
  } else if (normCategory.includes("inference") || normCategory === "ai_inference") {
    label = "AI Inference";
    badgeClass = "provenance-ai-inference";
    Icon = Sparkles;
    title = "Inferred relationship, implicit activity, or manpower estimate";
  } else if (normCategory.includes("predict") || normCategory === "prediction") {
    label = "Prediction";
    badgeClass = "provenance-prediction";
    Icon = TrendingUp;
    title = "Computed mathematically from historical variance and CPM float";
  } else if (
    normCategory.includes("human") ||
    normCategory.includes("approval") ||
    normCategory === "human_approval"
  ) {
    label = "Human Approval";
    badgeClass = "provenance-human-approval";
    Icon = CheckCircle2;
    title = "Verified and accepted or corrected by a human project planner";
  }

  const padding = size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs";

  return (
    <span
      title={detail || title}
      className={`inline-flex items-center gap-1.5 rounded font-medium tracking-wide ${badgeClass} ${padding}`}
    >
      {showIcon && <Icon className={size === "sm" ? "w-3 h-3" : "w-3.5 h-3.5"} />}
      <span>{label}</span>
      {confidence != null && (
        <span className="opacity-75 font-mono text-[10px]">
          {Math.round(confidence <= 1 ? confidence * 100 : confidence)}%
        </span>
      )}
    </span>
  );
}
