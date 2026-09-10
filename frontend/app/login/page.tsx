"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { User, Shield, HardHat, Mail, Lock, UserCircle2 } from "lucide-react";

const ROLES = [
  { value: "reviewer", label: "Reviewer", icon: User, desc: "Review matched events" },
  { value: "planner", label: "Planner", icon: HardHat, desc: "Full schedule + confirm" },
  { value: "admin", label: "Admin", icon: Shield, desc: "All access + audit view" },
];

export default function LoginPage() {
  const [name, setName] = useState("");
  const [role, setRole] = useState("reviewer");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [panel, setPanel] = useState<"signin" | "signup">("signin");
  const router = useRouter();

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  function enterDemo() {
    localStorage.setItem("reviewer_token", "dev-insecure-token");
    localStorage.setItem("reviewer_name", name.trim() || "Demo User");
    localStorage.setItem("reviewer_role", role);
    router.push("/navigator");
  }

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
      router.push("/navigator");
    } catch {
      // Backend offline — enter demo mode with synthetic data
      enterDemo();
    } finally {
      setLoading(false);
    }
  }

  const isRight = panel === "signup";

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--bg)",
        fontFamily: "'IBM Plex Sans', Arial, sans-serif",
        padding: "24px",
      }}
    >
      {/* Auth Card */}
      <div
        style={{
          position: "relative",
          width: "860px",
          maxWidth: "94vw",
          minHeight: "520px",
          background: "var(--surface)",
          borderRadius: "var(--radius-lg)",
          overflow: "hidden",
          boxShadow: "var(--shadow-lg)",
          border: "1px solid var(--border)",
        }}
      >
        {/* Sign-In Panel */}
        <div
          style={{
            position: "absolute",
            top: 0,
            height: "100%",
            width: "50%",
            left: 0,
            transition: "all 0.6s ease-in-out",
            transform: isRight ? "translateX(100%)" : "translateX(0)",
            zIndex: isRight ? 1 : 2,
            opacity: isRight ? 0 : 1,
          }}
        >
          <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", height: "100%", justifyContent: "center", padding: "0 48px", gap: "14px" }}>
            <div>
              <h2 style={{ fontSize: "22px", fontWeight: 700, color: "var(--ink)", margin: "0 0 4px", letterSpacing: "0.1px" }}>Welcome Back</h2>
              <p style={{ fontSize: "12.5px", color: "var(--muted)", margin: 0 }}>Sign in to continue to Team Kranti</p>
            </div>

            {/* Name field */}
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-sm)",
                background: "var(--surface-alt)",
                padding: "9px 12px",
                transition: "border-color 0.12s ease",
              }}
            >
              <UserCircle2 size={15} style={{ color: "var(--muted)", flexShrink: 0 }} />
              <input
                id="login-name-input"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name (e.g. Rajesh Kumar)"
                autoFocus
                style={{
                  border: "none",
                  background: "transparent",
                  outline: "none",
                  fontFamily: "inherit",
                  fontSize: "13px",
                  color: "var(--ink)",
                  width: "100%",
                }}
              />
            </label>

            {/* Role selector */}
            <div>
              <p style={{ fontSize: "10.5px", color: "var(--muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "7px", fontFamily: "'IBM Plex Mono', monospace" }}>
                Role
              </p>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "7px" }}>
                {ROLES.map(({ value, label, icon: Icon, desc }) => (
                  <button
                    key={value}
                    type="button"
                    id={`role-${value}`}
                    onClick={() => setRole(value)}
                    style={{
                      padding: "10px 8px",
                      borderRadius: "var(--radius-sm)",
                      border: role === value ? "1px solid rgba(217,130,43,0.4)" : "1px solid var(--border)",
                      background: role === value ? "var(--accent-soft)" : "var(--surface-alt)",
                      textAlign: "left",
                      cursor: "pointer",
                      transition: "all 0.12s ease",
                    }}
                  >
                    <Icon size={14} style={{ color: role === value ? "var(--accent)" : "var(--muted)", marginBottom: "4px", display: "block" }} />
                    <p style={{ fontSize: "11.5px", fontWeight: 600, color: role === value ? "var(--accent-ink)" : "var(--ink)", margin: "0 0 2px" }}>{label}</p>
                    <p style={{ fontSize: "9.5px", color: "var(--muted)", margin: 0, lineHeight: 1.3 }}>{desc}</p>
                  </button>
                ))}
              </div>
            </div>

            {error && (
              <p style={{ fontSize: "12px", color: "var(--danger)", margin: 0, background: "var(--danger-soft)", padding: "7px 10px", borderRadius: "var(--radius-sm)", border: "1px solid rgba(224,87,76,0.25)" }}>
                {error}
              </p>
            )}

            <button
              type="submit"
              id="login-submit-btn"
              disabled={loading}
              style={{
                marginTop: "4px",
                fontFamily: "inherit",
                fontSize: "13px",
                fontWeight: 700,
                color: "#fff",
                background: "var(--ink)",
                border: "none",
                borderRadius: "var(--radius-sm)",
                padding: "12px",
                cursor: loading ? "not-allowed" : "pointer",
                opacity: loading ? 0.7 : 1,
                transition: "background 0.12s ease",
                letterSpacing: "0.1px",
              }}
            >
              {loading ? "Signing in…" : "Sign In"}
            </button>

            <button
              type="button"
              onClick={enterDemo}
              style={{
                fontFamily: "inherit",
                fontSize: "12px",
                fontWeight: 600,
                color: "var(--ink-soft)",
                background: "transparent",
                border: "1px dashed var(--border-strong)",
                borderRadius: "var(--radius-sm)",
                padding: "10px",
                cursor: "pointer",
                letterSpacing: "0.1px",
              }}
            >
              ⚡ Enter Demo Mode (no backend needed)
            </button>

            <p style={{ fontSize: "10.5px", color: "var(--muted)", textAlign: "center", margin: 0, lineHeight: 1.5 }}>
              No password required — hackathon demo.
              <br />Your name appears in the audit trail.
            </p>
          </form>
        </div>

        {/* Sign-Up Panel (demo only, same submit) */}
        <div
          style={{
            position: "absolute",
            top: 0,
            height: "100%",
            width: "50%",
            left: 0,
            transition: "all 0.6s ease-in-out",
            transform: isRight ? "translateX(100%)" : "translateX(0)",
            opacity: isRight ? 1 : 0,
            zIndex: isRight ? 5 : 1,
          }}
        >
          <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", height: "100%", justifyContent: "center", padding: "0 48px", gap: "14px" }}>
            <div>
              <h2 style={{ fontSize: "22px", fontWeight: 700, color: "var(--ink)", margin: "0 0 4px" }}>Create Account</h2>
              <p style={{ fontSize: "12.5px", color: "var(--muted)", margin: 0 }}>Register with your work details</p>
            </div>

            <label style={{ display: "flex", alignItems: "center", gap: "10px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", background: "var(--surface-alt)", padding: "9px 12px" }}>
              <UserCircle2 size={15} style={{ color: "var(--muted)", flexShrink: 0 }} />
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Full name" style={{ border: "none", background: "transparent", outline: "none", fontFamily: "inherit", fontSize: "13px", color: "var(--ink)", width: "100%" }} />
            </label>

            <label style={{ display: "flex", alignItems: "center", gap: "10px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", background: "var(--surface-alt)", padding: "9px 12px" }}>
              <Mail size={15} style={{ color: "var(--muted)", flexShrink: 0 }} />
              <input type="email" placeholder="Work email" style={{ border: "none", background: "transparent", outline: "none", fontFamily: "inherit", fontSize: "13px", color: "var(--ink)", width: "100%" }} />
            </label>

            <label style={{ display: "flex", alignItems: "center", gap: "10px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", background: "var(--surface-alt)", padding: "9px 12px" }}>
              <Lock size={15} style={{ color: "var(--muted)", flexShrink: 0 }} />
              <input type="password" placeholder="Password" style={{ border: "none", background: "transparent", outline: "none", fontFamily: "inherit", fontSize: "13px", color: "var(--ink)", width: "100%" }} />
            </label>

            <button type="submit" disabled={loading} style={{ fontFamily: "inherit", fontSize: "13px", fontWeight: 700, color: "#fff", background: "var(--ink)", border: "none", borderRadius: "var(--radius-sm)", padding: "12px", cursor: "pointer", opacity: loading ? 0.7 : 1 }}>
              {loading ? "Creating…" : "Register"}
            </button>
          </form>
        </div>

        {/* Animated Overlay Panel */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: "50%",
            width: "50%",
            height: "100%",
            overflow: "hidden",
            transition: "transform 0.6s ease-in-out",
            zIndex: 100,
            transform: isRight ? "translateX(-100%)" : "translateX(0)",
          }}
        >
          <div
            style={{
              position: "relative",
              left: "-100%",
              height: "100%",
              width: "200%",
              background: "linear-gradient(155deg, #101826 0%, #1c2636 100%)",
              color: "#fff",
              transform: isRight ? "translateX(50%)" : "translateX(0)",
              transition: "transform 0.6s ease-in-out",
            }}
          >
            {/* Left overlay panel (show when right-active = signup) */}
            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "50%",
                height: "100%",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                padding: "0 40px",
                textAlign: "center",
                transition: "transform 0.6s ease-in-out",
                transform: isRight ? "translateX(0)" : "translateX(-20%)",
              }}
            >
              {/* Diamond brand mark */}
              <div style={{ width: "14px", height: "14px", background: "var(--accent)", borderRadius: "3px", transform: "rotate(45deg)", marginBottom: "20px" }} />
              <h2 style={{ fontSize: "20px", fontWeight: 700, margin: "0 0 12px", color: "#fff" }}>Welcome Back!</h2>
              <p style={{ fontSize: "12.5px", lineHeight: 1.65, color: "#c7cedc", margin: "0 0 24px" }}>
                Already have an account? Sign in to continue monitoring Oil India pipeline execution.
              </p>
              <button
                type="button"
                onClick={() => setPanel("signin")}
                style={{
                  fontFamily: "inherit",
                  fontSize: "12px",
                  fontWeight: 600,
                  color: "#fff",
                  background: "transparent",
                  border: "1px solid rgba(255,255,255,0.5)",
                  borderRadius: "20px",
                  padding: "10px 30px",
                  cursor: "pointer",
                  transition: "background 0.15s ease, border-color 0.15s ease",
                }}
              >
                Sign In
              </button>
            </div>

            {/* Right overlay panel (show when signin = default) */}
            <div
              style={{
                position: "absolute",
                top: 0,
                right: 0,
                width: "50%",
                height: "100%",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                padding: "0 40px",
                textAlign: "center",
                transition: "transform 0.6s ease-in-out",
                transform: isRight ? "translateX(20%)" : "translateX(0)",
              }}
            >
              <div style={{ width: "14px", height: "14px", background: "var(--accent)", borderRadius: "3px", transform: "rotate(45deg)", marginBottom: "20px" }} />
              <h2 style={{ fontSize: "20px", fontWeight: 700, margin: "0 0 12px", color: "#fff" }}>New Here?</h2>
              <p style={{ fontSize: "12.5px", lineHeight: 1.65, color: "#c7cedc", margin: "0 0 24px" }}>
                Create an account and let Kranti AI start turning field messages into schedule actuals.
              </p>
              <button
                type="button"
                onClick={() => setPanel("signup")}
                style={{
                  fontFamily: "inherit",
                  fontSize: "12px",
                  fontWeight: 600,
                  color: "#fff",
                  background: "transparent",
                  border: "1px solid rgba(255,255,255,0.5)",
                  borderRadius: "20px",
                  padding: "10px 30px",
                  cursor: "pointer",
                  transition: "background 0.15s ease, border-color 0.15s ease",
                }}
              >
                Create Account
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
