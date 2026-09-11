"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  CalendarRange,
  CheckSquare,
  BellRing,
  AlertOctagon,
  GitCommit,
  Network,
  Database,
  Layers,
} from "lucide-react";
import { useApp } from "@/lib/AppContext";
import { fetchUpdateCenterFeed } from "@/lib/api";

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badgeKey?: "review" | "update";
  isStretch?: boolean;
}

const MVP_NAV_ITEMS: NavItem[] = [
  { label: "Project Overview", href: "/", icon: LayoutDashboard },
  { label: "P6 Schedule & Gantt", href: "/schedule", icon: CalendarRange },
  { label: "Review Queue", href: "/review", icon: CheckSquare, badgeKey: "review" },
  { label: "Update Center", href: "/updates", icon: BellRing, badgeKey: "update" },
  { label: "Delay Analysis", href: "/analysis/delays", icon: AlertOctagon },
];

const STRETCH_NAV_ITEMS: NavItem[] = [
  { label: "Critical Path Network", href: "/schedule/network", icon: Network, isStretch: true },
  { label: "Project Timeline", href: "/schedule/timeline", icon: GitCommit, isStretch: true },
  { label: "Data Quality Register", href: "/updates/quality", icon: Database, isStretch: true },
];

export function Sidebar() {
  const pathname = usePathname();
  const { reviewCount, setReviewCount, updateCount, setUpdateCount } = useApp();

  // Periodically fetch live counts for review and update center badges
  useEffect(() => {
    let isMounted = true;
    async function loadCounts() {
      try {
        const feed = await fetchUpdateCenterFeed({ page_size: 10 });
        if (isMounted && feed?.summary) {
          setReviewCount(feed.summary.pending_reviews);
          setUpdateCount(feed.summary.total_items);
        }
      } catch {
        // quiet fallback
      }
    }
    loadCounts();
    const interval = setInterval(loadCounts, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [setReviewCount, setUpdateCount]);

  return (
    <aside className="w-60 bg-white border-r border-zinc-200 flex flex-col justify-between h-[calc(100vh-3.5rem)] select-none shrink-0">
      <div className="p-3 space-y-6">
        {/* Brand / Logo */}
        <div className="px-3 pt-1 flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-slate-900 flex items-center justify-center text-white text-xs font-bold font-mono">
            P6
          </div>
          <div>
            <div className="text-xs font-bold text-zinc-900 tracking-wide uppercase">
              Team Kranti
            </div>
            <div className="text-[10px] text-zinc-400">Controls Engine v2.4</div>
          </div>
        </div>

        {/* MVP Navigation */}
        <nav className="space-y-1">
          <div className="px-3 text-[10px] font-semibold text-zinc-400 uppercase tracking-wider mb-2">
            Execution Controls
          </div>
          {MVP_NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            const badgeValue =
              item.badgeKey === "review"
                ? reviewCount
                : item.badgeKey === "update"
                ? updateCount
                : null;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-slate-100 text-slate-900 font-semibold"
                    : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon
                    className={`w-4 h-4 ${
                      isActive ? "text-blue-700" : "text-zinc-400"
                    }`}
                  />
                  <span>{item.label}</span>
                </div>
                {badgeValue !== null && badgeValue > 0 && (
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-medium ${
                      item.badgeKey === "review"
                        ? "bg-amber-100 text-amber-800"
                        : "bg-slate-100 text-slate-700"
                    }`}
                  >
                    {badgeValue}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Stretch Items */}
        <div className="pt-2 border-t border-zinc-100">
          <div className="px-3 text-[10px] font-semibold text-zinc-400 uppercase tracking-wider mb-2 flex items-center justify-between">
            <span>Specialized Views</span>
            <span className="text-[9px] bg-zinc-100 text-zinc-500 px-1 rounded">Stretch</span>
          </div>
          <nav className="space-y-1">
            {STRETCH_NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center justify-between px-3 py-1.5 rounded-[2px] text-xs transition-colors ${
                    isActive
                      ? "bg-zinc-100 text-zinc-900 font-semibold"
                      : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className={`w-3.5 h-3.5 ${isActive ? "text-slate-900" : "text-zinc-400"}`} />
                    <span>{item.label}</span>
                  </div>
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* System Status Footer */}
      <div className="p-3 border-t border-zinc-100 bg-zinc-50/50">
        <div className="flex items-center justify-between text-[11px] text-zinc-500 mb-1">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
            Backend Connected
          </span>
          <span className="font-mono text-[10px] text-zinc-400">P6 XER Ready</span>
        </div>
        <div className="text-[10px] text-zinc-400">
          Smart India Hackathon 2026 — SIH26122
        </div>
      </div>
    </aside>
  );
}
