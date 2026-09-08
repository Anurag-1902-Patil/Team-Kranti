"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { User, Shield, HardHat } from "lucide-react";

const ROLES = [
  { value: "reviewer", label: "Reviewer", icon: User, desc: "Review matched events" },
  { value: "planner", label: "Planner", icon: HardHat, desc: "Full schedule + confirm new activities" },
  { value: "admin", label: "Admin", icon: Shield, desc: "All access + audit view" },
];

export default function LoginPage() {
  const [name, setName] = useState("");
  const [role, setRole] = useState("reviewer");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) { setError("Please enter your name."); return; }
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), role }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      localStorage.setItem("reviewer_token", data.token);
      localStorage.setItem("reviewer_name", data.name);
      localStorage.setItem("reviewer_role", data.role);
      router.push("/");
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-violet-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h12a2.25 2.25 0 002.25-2.25V3m-16.5 0h16.5m-16.5 0H3m18 0h-.75" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 3v11.25M16.5 3v11.25M12 3v11.25" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold gradient-text">Team Kranti</h1>
          <p className="text-sm text-gray-500 mt-1">SIH26122 — Schedule Linking Layer</p>
        </div>

        {/* Login card */}
        <form onSubmit={handleLogin} className="glass-card p-6 space-y-5">
          <h2 className="text-base font-semibold text-white">Sign in to Review Dashboard</h2>

          <div>
            <label className="text-xs text-gray-500 uppercase tracking-wide font-medium block mb-1.5">
              Your Name
            </label>
            <input
              id="login-name-input"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Rajesh Kumar"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-violet-500"
              autoFocus
            />
          </div>

          <div>
            <label className="text-xs text-gray-500 uppercase tracking-wide font-medium block mb-1.5">
              Role
            </label>
            <div className="grid grid-cols-3 gap-2">
              {ROLES.map(({ value, label, icon: Icon, desc }) => (
                <button
                  key={value}
                  type="button"
                  id={`role-${value}`}
                  onClick={() => setRole(value)}
                  className={`p-3 rounded-lg border text-left transition-all ${
                    role === value
                      ? "border-violet-500 bg-violet-500/10 text-violet-300"
                      : "border-gray-700 bg-gray-800/40 text-gray-400 hover:border-gray-600"
                  }`}
                >
                  <Icon className="w-4 h-4 mb-1.5" />
                  <p className="text-xs font-semibold">{label}</p>
                  <p className="text-[10px] text-gray-600 mt-0.5 leading-tight">{desc}</p>
                </button>
              ))}
            </div>
          </div>

          {error && <p className="text-xs text-rose-400">{error}</p>}

          <button
            type="submit"
            id="login-submit-btn"
            disabled={loading}
            className="w-full py-2.5 rounded-lg bg-violet-600 text-white text-sm font-semibold hover:bg-violet-500 disabled:opacity-50 transition-colors"
          >
            {loading ? "Signing in..." : "Enter Dashboard"}
          </button>

          <p className="text-center text-xs text-gray-700">
            No password required — this is a hackathon demo.
            <br />Your name appears in the audit trail for all review decisions.
          </p>
        </form>
      </div>
    </div>
  );
}
