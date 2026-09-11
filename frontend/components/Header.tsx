"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, Calendar, ShieldCheck, AlertTriangle, LogOut, User } from "lucide-react";
import { useApp } from "@/lib/AppContext";
import { clearAuthToken } from "@/lib/api";

export function Header() {
  const router = useRouter();
  const { setCommandPaletteOpen } = useApp();
  const [userName, setUserName] = useState("Lead Planner");
  const [userRole, setUserRole] = useState("planner");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("reviewer_name");
      const role = localStorage.getItem("reviewer_role");
      if (stored) setUserName(stored);
      if (role) setUserRole(role);
    }
  }, []);

  const handleLogout = () => {
    clearAuthToken();
    router.push("/login");
  };

  return (
    <header className="h-14 bg-white border-b border-zinc-200 px-4 flex items-center justify-between z-30 select-none">
      {/* Project Identity & Health Status */}
      <div className="flex items-center gap-4">
        <div className="flex items-baseline gap-2">
          <span className="font-semibold text-zinc-900 text-sm tracking-tight">
            OIL-NE-2026
          </span>
          <span className="text-zinc-500 text-xs hidden sm:inline">
            Numaligarh Pipeline Expansion (L5/L6)
          </span>
        </div>

        <div className="h-4 w-px bg-zinc-200 hidden md:block" />

        {/* Reporting Metadata — clean text, zero badge soup */}
        <div className="hidden lg:flex items-center gap-3 text-xs text-zinc-500 font-mono">
          <span>Data Date: <strong className="text-zinc-800 font-semibold">15-Aug-2026</strong></span>
          <span className="text-zinc-300">•</span>
          <span>Baseline Model: <strong className="text-zinc-800 font-medium">L5/L6 Reconciled</strong></span>
        </div>
      </div>

      {/* Global Search Trigger (⌘K) & User */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setCommandPaletteOpen(true)}
          className="flex items-center gap-2 bg-zinc-50 hover:bg-zinc-100 text-zinc-500 hover:text-zinc-800 border border-zinc-200 px-3 py-1.5 rounded-md text-xs transition-colors shadow-none"
          title="Open Command Palette (⌘K)"
        >
          <Search className="w-3.5 h-3.5 text-zinc-400" />
          <span className="hidden md:inline text-zinc-500">Search activities, reports, delays...</span>
          <kbd className="hidden md:inline bg-white px-1.5 py-0.5 rounded border border-zinc-200 text-[10px] font-mono text-zinc-400">
            ⌘K
          </kbd>
        </button>

        <div className="h-4 w-px bg-zinc-200" />

        {/* User Identity */}
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-700">
            <User className="w-3.5 h-3.5" />
          </div>
          <div className="hidden sm:block text-left">
            <div className="text-xs font-medium text-zinc-800 leading-tight">{userName}</div>
            <div className="text-[10px] text-zinc-400 capitalize">{userRole}</div>
          </div>
          <button
            onClick={handleLogout}
            className="text-zinc-400 hover:text-red-600 p-1 rounded hover:bg-zinc-100 transition-colors"
            title="Log Out"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </header>
  );
}
