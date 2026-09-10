"use client";

import { useRouter } from "next/navigation";
import { clearAuthToken } from "@/lib/api";

export default function NavigatorPage() {
  const router = useRouter();

  function go() {
    router.push("/");
  }

  function signOut() {
    clearAuthToken();
    router.push("/login");
  }

  const options = [
    {
      icon: "→",
      label: "Open Last Viewed",
      sub: "OIL India — Pipeline Expansion Phase 3",
      featured: true,
      action: go,
    },
    {
      icon: "📁",
      label: "Open Existing",
      sub: "Browse or search projects",
      featured: false,
      action: go,
    },
    {
      icon: "+",
      label: "Create New",
      sub: "Blank schedule",
      featured: false,
      action: go,
    },
    {
      icon: "🌐",
      label: "Global Data",
      sub: "EPS, Roles, Calendars",
      featured: false,
      action: go,
    },
  ];

  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        background: "#12161d",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'IBM Plex Sans', Arial, sans-serif",
      }}
    >
      <div
        style={{
          width: "420px",
          maxWidth: "92vw",
          background: "#1a1f29",
          border: "1px solid #2a3140",
          borderRadius: "14px",
          padding: "26px 24px 20px",
          boxShadow: "0 24px 60px rgba(0,0,0,.35)",
        }}
      >
        <h2
          style={{
            color: "#fff",
            fontSize: "16px",
            fontWeight: 600,
            textAlign: "center",
            margin: "4px 0 20px",
          }}
        >
          What are we working on today?
        </h2>

        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {options.map((opt) => (
            <button
              key={opt.label}
              onClick={opt.action}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "13px",
                width: "100%",
                textAlign: "left",
                background: "#232936",
                border: "1px solid #2f3646",
                borderRadius: "10px",
                padding: "12px 14px",
                cursor: "pointer",
                fontFamily: "inherit",
                transition: "background 0.12s ease, border-color 0.12s ease",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.background = "#282f3d";
                (e.currentTarget as HTMLElement).style.borderColor = "#3a4257";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.background = "#232936";
                (e.currentTarget as HTMLElement).style.borderColor = "#2f3646";
              }}
            >
              <span
                style={{
                  flexShrink: 0,
                  width: "34px",
                  height: "34px",
                  borderRadius: "9px",
                  background: opt.featured ? "#d9822b" : "#333c4d",
                  color: opt.featured ? "#1a1206" : "#dbe1ec",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "15px",
                  fontWeight: 700,
                }}
              >
                {opt.icon}
              </span>
              <span style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                <strong style={{ color: "#f2f4f8", fontSize: "13px", fontWeight: 600 }}>
                  {opt.label}
                </strong>
                <small style={{ color: "#8b93a3", fontSize: "11px" }}>{opt.sub}</small>
              </span>
            </button>
          ))}
        </div>

        <button
          onClick={signOut}
          style={{
            margin: "18px auto 2px",
            display: "block",
            background: "none",
            border: "none",
            cursor: "pointer",
            fontFamily: "inherit",
            fontSize: "11.5px",
            color: "#6b7385",
            padding: "4px",
          }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = "#c7cedc"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = "#6b7385"; }}
        >
          ← Sign out
        </button>
      </div>
    </div>
  );
}
