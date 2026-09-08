"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  Inbox,
  CheckSquare,
  Calendar,
  Brain,
  Cpu,
  LogOut,
  User,
} from "lucide-react";

const navItems = [
  { href: "/", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/events", icon: Inbox, label: "All Events" },
  { href: "/review", icon: CheckSquare, label: "Review Queue" },
  { href: "/schedule", icon: Calendar, label: "Schedule" },
  { href: "/memory", icon: Brain, label: "Inst. Memory" },
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
      }).catch(() => {}); // Fire-and-forget
    }
    localStorage.removeItem("reviewer_token");
    localStorage.removeItem("reviewer_name");
    localStorage.removeItem("reviewer_role");
    router.push("/login");
  }

  return (
    <aside className="w-60 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Cpu className="w-6 h-6 text-violet-400" />
          <div>
            <p className="text-sm font-semibold text-white leading-tight">Team Kranti</p>
            <p className="text-[10px] text-gray-500 leading-tight">SIH26122 — Oil India</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ href, icon: Icon, label }) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                active
                  ? "bg-violet-500/15 text-violet-300 border border-violet-500/25"
                  : "text-gray-400 hover:text-white hover:bg-gray-800/60"
              }`}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Reviewer identity + logout */}
      <div className="px-4 py-4 border-t border-gray-800 space-y-3">
        {reviewerName ? (
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-violet-500/20 flex items-center justify-center flex-shrink-0">
              <User className="w-3.5 h-3.5 text-violet-400" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-gray-300 truncate">{reviewerName}</p>
              <p className="text-[10px] text-gray-600 capitalize">{reviewerRole}</p>
            </div>
          </div>
        ) : (
          <Link href="/login" className="text-xs text-violet-400 hover:text-violet-300">
            Sign in →
          </Link>
        )}

        {reviewerName && (
          <button
            id="sidebar-logout-btn"
            onClick={handleLogout}
            className="flex items-center gap-2 text-xs text-gray-600 hover:text-rose-400 transition-colors w-full"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign out
          </button>
        )}

        <div>
          <p className="text-[10px] text-gray-700">Smart India Hackathon 2026</p>
          <p className="text-[10px] text-gray-700">Problem SIH26122</p>
        </div>
      </div>
    </aside>
  );
}
