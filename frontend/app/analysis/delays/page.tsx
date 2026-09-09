"use client";

import React, { useEffect, useState } from "react";
import { fetchDelayIntelligence } from "@/lib/api";
import type { DelayIntelligence } from "@/lib/types";
import DelayCharts from "@/components/DelayCharts";
import { AlertTriangle, RefreshCw, Layers } from "lucide-react";

export default function DelaysAnalysisPage() {
  const [data, setData] = useState<DelayIntelligence | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadData() {
    setLoading(true);
    try {
      const res = await fetchDelayIntelligence("TEST");
      setData(res);
    } catch (e) {
      console.error("Failed to load delay intelligence:", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-slate-100">
              Delay &amp; Bottleneck Intelligence
            </h1>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-amber-950 text-amber-400 border border-amber-800/60">
              12 Root Cause Taxonomy
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic delay analysis across historical field updates • Bottleneck locations, contractor variance, and recurring blockers.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="px-2.5 py-1.5 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs text-slate-300 flex items-center gap-1.5 transition-colors self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-cyan-400" : ""}`} />
          Refresh Analysis
        </button>
      </div>

      {/* Main Charts & Breakdown */}
      <DelayCharts data={data} />
    </div>
  );
}
