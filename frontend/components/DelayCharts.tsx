"use client";

import React from "react";
import type { DelayIntelligence } from "@/lib/types";
import { AlertTriangle, MapPin, Users, Flame } from "lucide-react";

interface DelayChartsProps {
  data: DelayIntelligence | null;
}

export default function DelayCharts({ data }: DelayChartsProps) {
  if (!data) {
    return (
      <div className="py-12 text-center text-slate-400 text-xs font-sans">
        Loading delay analytics data...
      </div>
    );
  }

  // Defensively extract data with fallbacks to either frontend or backend key conventions
  const rawCauses = (data as any).cause_breakdown || (data as any).categories || [];
  const causeBreakdown = Array.isArray(rawCauses) ? rawCauses : [];

  const rawBottlenecks = (data as any).bottlenecks || (data as any).bottleneck_locations || [];
  const bottlenecks = Array.isArray(rawBottlenecks) ? rawBottlenecks : [];

  const rawContractors = data.contractor_rankings || [];
  const contractorRankings = Array.isArray(rawContractors) ? rawContractors : [];

  const rawBlockers = data.recurring_blockers || [];
  const recurringBlockers = Array.isArray(rawBlockers) ? rawBlockers : [];

  const totalDelayEvents = data.total_delay_events ?? 0;

  return (
    <div className="space-y-6 font-sans">
      {/* Top 2 Columns: 12-Cause Breakdown + Bottleneck Locations */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* 12 Standard Delay Causes Breakdown (7 cols) */}
        <div className="lg:col-span-7 pm-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              Standard Delay Causes Breakdown ({totalDelayEvents} Total Events)
            </h2>
            <span className="text-[11px] font-mono text-slate-400">12 Standard Causes</span>
          </div>

          <div className="space-y-2.5 pt-1">
            {causeBreakdown.length === 0 ? (
              <p className="text-xs text-slate-500 py-4 text-center">No delay events recorded.</p>
            ) : (
              causeBreakdown.map((item: any) => {
                const key = item.cause || item.category || Math.random();
                const label = item.label || item.display_name || item.cause || "Unknown";
                const eventCount = item.event_count ?? item.count ?? 0;
                const percentage = item.percentage ?? 0;
                return (
                  <div key={key} className="space-y-1 text-xs">
                    <div className="flex justify-between text-slate-300">
                      <span className="font-medium text-slate-200">{label}</span>
                      <span className="font-mono text-slate-400">
                        {eventCount} events ({percentage}%)
                      </span>
                    </div>
                    <div className="w-full bg-slate-900 border border-slate-800 h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-amber-500/80 h-full rounded-full transition-all duration-500"
                        style={{ width: `${Math.max(2, percentage)}%` }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Bottleneck Locations & Units (5 cols) */}
        <div className="lg:col-span-5 pm-card p-5 space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
              <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                <MapPin className="w-4 h-4 text-cyan-400" />
                Bottleneck Locations &amp; Units
              </h2>
              <span className="text-[11px] font-mono text-slate-400">Site ROW</span>
            </div>

            <div className="divide-y divide-slate-800/60 mt-3">
              {bottlenecks.length === 0 ? (
                <p className="text-xs text-slate-500 py-4 text-center">No bottleneck locations identified.</p>
              ) : (
                bottlenecks.map((b: any) => {
                  const area = b.area || b.location || "General ROW";
                  const delayedEvents = b.delayed_events ?? b.delayed_events_count ?? 0;
                  const activeBlockers = b.active_blockers ?? (Array.isArray(b.sample_blockers) ? b.sample_blockers.length : 0);
                  return (
                    <div key={area} className="py-2.5 flex items-center justify-between text-xs">
                      <div>
                        <p className="font-semibold text-slate-200">{area}</p>
                        <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                          {delayedEvents} delayed field updates
                        </p>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-950/70 text-rose-400 border border-rose-800/60 font-semibold">
                          {activeBlockers} blocker{activeBlockers === 1 ? "" : "s"}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          <div className="p-3 rounded bg-slate-900/80 border border-slate-800 text-[11px] text-slate-400 leading-relaxed font-mono">
            Areas with concurrent active blockers represent critical path handover risks between Civil foundations and Piping erection.
          </div>
        </div>
      </div>

      {/* Bottom 2 Columns: Contractor Delay Ranking + Recurring Blockers */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Contractor Delay Ranking Table (6 cols) */}
        <div className="lg:col-span-6 pm-card overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-800 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <Users className="w-4 h-4 text-sky-400" />
              Contractor Delay &amp; Variance Ranking
            </h2>
            <span className="text-[11px] font-mono text-slate-400">Historical Actuals</span>
          </div>

          <div className="overflow-x-auto">
            <table className="pm-table">
              <thead>
                <tr>
                  <th>Contractor</th>
                  <th>Total Events</th>
                  <th>Delayed</th>
                  <th>Delay Ratio</th>
                  <th>Variance Factor</th>
                </tr>
              </thead>
              <tbody>
                {contractorRankings.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center text-xs text-slate-500 py-4">
                      No contractor delay variance recorded.
                    </td>
                  </tr>
                ) : (
                  contractorRankings.map((c: any) => {
                    const name = c.contractor || "Internal Direct Crew";
                    const totalEvents = c.total_events ?? c.delayed_activities ?? 0;
                    const delayEvents = c.delay_events ?? c.delayed_activities ?? 0;
                    const ratio = c.delay_ratio ?? (totalEvents > 0 ? delayEvents / totalEvents : 0);
                    const varianceFactor = c.avg_variance_factor ?? 1.0;
                    return (
                      <tr key={name}>
                        <td className="font-semibold text-slate-200 text-xs">{name}</td>
                        <td className="font-mono text-slate-300 text-xs">{totalEvents}</td>
                        <td className="font-mono text-amber-400 text-xs">{delayEvents}</td>
                        <td className="font-mono text-slate-300 text-xs">
                          {Math.round(ratio * 100)}%
                        </td>
                        <td className="font-mono text-cyan-400 font-semibold text-xs">
                          {Number(varianceFactor).toFixed(2)}x
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recurring Blockers Table (6 cols) */}
        <div className="lg:col-span-6 pm-card overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-800 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <Flame className="w-4 h-4 text-rose-400" />
              Top Recurring Field Blockers
            </h2>
            <span className="text-[11px] font-mono text-slate-400">Field Logs</span>
          </div>

          <div className="overflow-x-auto">
            <table className="pm-table">
              <thead>
                <tr>
                  <th>Blocker Description</th>
                  <th>Occurrences</th>
                  <th>Latest Logged</th>
                  <th className="text-right">Risk Level</th>
                </tr>
              </thead>
              <tbody>
                {recurringBlockers.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="text-center text-xs text-slate-500 py-4">
                      No recurring blockers logged.
                    </td>
                  </tr>
                ) : (
                  recurringBlockers.map((blk: any, idx: number) => {
                    const desc = blk.description || blk.blocker || "General blocker";
                    const count = blk.occurrences ?? blk.frequency ?? 1;
                    const latest = blk.latest_reported ? String(blk.latest_reported).substring(0, 10) : "Active";
                    return (
                      <tr key={`${desc}-${idx}`}>
                        <td className="font-medium text-slate-200 text-xs max-w-xs">
                          {desc}
                        </td>
                        <td className="font-mono text-xs text-amber-400 font-semibold">
                          {count}x
                        </td>
                        <td className="font-mono text-slate-400 text-[11px] whitespace-nowrap">
                          {latest}
                        </td>
                        <td className="text-right whitespace-nowrap">
                          <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold ${
                            count >= 4
                              ? "bg-rose-950/70 text-rose-400 border border-rose-800"
                              : "bg-amber-950/70 text-amber-400 border border-amber-800"
                          }`}>
                            {count >= 4 ? "CRITICAL" : "MODERATE"}
                          </span>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
