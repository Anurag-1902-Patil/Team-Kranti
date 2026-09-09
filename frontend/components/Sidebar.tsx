"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  Calendar,
  CheckSquare,
  ListOrdered,
  AlertTriangle,
  Brain,
  Layers,
  LogOut,
  User,
} from "lucide-react";

interface NavItem {
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}

const executionNav: NavItem[] = [
  { href: "/schedule", icon: Calendar, label: "Schedule (Gantt)" },
  { href: "/review", icon: CheckSquare, label: "Review Queue" },
  { href: "/events", icon: ListOrdered, label: "All Progress Events" },
];

const analysisNav: NavItem[] = [
  { href: "/analysis/delays", icon: AlertTriangle, label: "Delay & Bottlenecks" },
  { href: "/memory", icon: Brain, label: "Institutional Memory" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [reviewerName, setReviewerName] = useState<string | null>(null);
  const [reviewerRole, setReviewerRole] = useState<string | null>(null);

  useEffect(() => {
    setReviewerName(localStorage.getItem("reviewer_name"));
    setReviewerRole(localStorage.getItem("reviewer_role"));
  }, []);

  function handleLogout() {
    const token = localStorage.getItem("reviewer_token");
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    if (token) {
      fetch(`${API_BASE}/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      }).catch(() => {});
    }
    localStorage.removeItem("reviewer_token");
    localStorage.removeItem("reviewer_name");
    localStorage.removeItem("reviewer_role");
    router.push("/login");
  }

  function renderLink(item: NavItem) {
    const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
    const Icon = item.icon;
    return (
      <Link
        key={item.href}
        href={item.href}
        className={`flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-medium transition-all duration-150 ${
          active
            ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/30"
            : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/60"
        }`}
      >
        <Icon className={`w-4 h-4 flex-shrink-0 ${active ? "text-cyan-400" : "text-slate-400"}`} />
        <span>{item.label}</span>
      </Link>
    );
  }

  return (
    <aside className="w-64 flex-shrink-0 bg-slate-950 border-r border-slate-800 flex flex-col font-sans">
      {/* Brand Header */}
      <div className="px-5 py-4 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded bg-cyan-950 border border-cyan-800/60 flex items-center justify-center text-cyan-400 font-bold text-sm">
            <Layers className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm font-semibold text-slate-100 tracking-tight leading-none">
              Team Kranti
            </h1>
            <p className="text-[10px] text-slate-400 mt-1 font-mono leading-none truncate">
              SIH26122 • Oil India Ltd
            </p>
          </div>
        </div>
      </div>

      {/* Navigation Sections */}
      <div className="flex-1 px-3 py-4 space-y-6 overflow-y-auto">
        {/* Overview Link */}
        <div>
          <Link
            href="/"
            className={`flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-medium transition-all duration-150 ${
              pathname === "/"
                ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/30"
                : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/60"
            }`}
          >
            <LayoutDashboard className={`w-4 h-4 flex-shrink-0 ${pathname === "/" ? "text-cyan-400" : "text-slate-400"}`} />
            <span>Overview Dashboard</span>
          </Link>
        </div>

        {/* Execution Section */}
        <div>
          <p className="px-3 mb-1.5 text-[10px] font-semibold tracking-wider text-slate-400 uppercase font-mono">
            Execution
          </p>
          <div className="space-y-1">{executionNav.map(renderLink)}</div>
        </div>

        {/* Analysis Section */}
        <div>
          <p className="px-3 mb-1.5 text-[10px] font-semibold tracking-wider text-slate-400 uppercase font-mono">
            Analysis
          </p>
          <div className="space-y-1">{analysisNav.map(renderLink)}</div>
        </div>
      </div>

      {/* User / Session Info */}
      <div className="px-4 py-3.5 border-t border-slate-800/80 bg-slate-950/60 space-y-2.5">
        {reviewerName ? (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-6 h-6 rounded-full bg-cyan-950 border border-cyan-800/50 flex items-center justify-center flex-shrink-0 text-cyan-300">
                <User className="w-3.5 h-3.5" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-medium text-slate-200 truncate">{reviewerName}</p>
                <p className="text-[10px] text-slate-400 capitalize truncate">{reviewerRole || "Planner"}</p>
              </div>
            </div>
            <button
              id="sidebar-logout-btn"
              onClick={handleLogout}
              title="Sign out"
              className="p-1 text-slate-500 hover:text-rose-400 transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <Link
            href="/login"
            className="flex items-center justify-between text-xs text-cyan-400 hover:text-cyan-300 font-medium"
          >
            <span>Planner Sign In</span>
            <span>→</span>
          </Link>
        )}

        <div className="text-[10px] text-slate-400 font-mono leading-tight">
          P6 Schedule Intelligence Layer
        </div>
      </div>
    </aside>
  );
}

