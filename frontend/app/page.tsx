"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, API_BASE, getAuthToken, fetchProgressEvents } from "@/lib/api";
import type { PlanActivity, ProgressEvent } from "@/lib/types";
import { MOCK_ACTIVITIES, MOCK_REVIEW_ITEMS, MOCK_INGESTION } from "@/lib/mockData";

/* ─── types ─── */
interface ActivityListResponse { total: number; items: PlanActivity[] }
interface ReviewItem {
  id: string; preview: string; tag: string; message: string;
  activityId: string; activityName: string; confidence: number;
  status: "accepted" | "declined" | null; eventId: string;
}
interface IngestionItem { sender: string; msg: string; }

/* ─── helpers ─── */
const MONTH_W = 160;

function formatDate(iso: string) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "2-digit" });
}

function buildTimeline(activities: PlanActivity[]) {
  const starts = activities.map(a => a.planned_start ? new Date(a.planned_start).getTime() : null).filter(Boolean) as number[];
  const ends   = activities.map(a => a.planned_finish ? new Date(a.planned_finish).getTime() : null).filter(Boolean) as number[];
  if (!starts.length) return { origin: new Date(), months: [] as {label:string;quarter:string}[], totalW: 0 };
  const minT = Math.min(...starts);
  const maxT = Math.max(...ends);
  const origin = new Date(minT);
  origin.setDate(1);
  const end = new Date(maxT);
  const months: { label: string; quarter: string }[] = [];
  const cursor = new Date(origin);
  while (cursor <= end || months.length < 12) {
    const q = Math.floor(cursor.getMonth() / 3) + 1;
    months.push({
      label: cursor.toLocaleString("en-GB", { month: "short" }),
      quarter: `Q${q} ${cursor.getFullYear()}`,
    });
    cursor.setMonth(cursor.getMonth() + 1);
  }
  return { origin, months, totalW: months.length * MONTH_W };
}

function monthOffset(origin: Date, iso: string) {
  const d = new Date(iso);
  const monthDiff = (d.getFullYear() - origin.getFullYear()) * 12 + (d.getMonth() - origin.getMonth());
  const daysInMonth = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();
  const fraction = (d.getDate() - 1) / daysInMonth;
  return monthDiff + fraction;
}

function confidenceTier(v: number) { return v >= 85 ? "high" : v >= 65 ? "med" : "low"; }

/* ─── component ─── */
export default function DashboardPage() {
  const router = useRouter();
  const [activities, setActivities] = useState<PlanActivity[]>([]);
  const [selected, setSelected] = useState<PlanActivity | null>(null);
  const [activeTab, setActiveTab] = useState("general");
  const [reviewItems, setReviewItems] = useState<ReviewItem[]>([]);
  const [ingestion, setIngestion] = useState<IngestionItem[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerSelected, setDrawerSelected] = useState<ReviewItem | null>(null);
  const [aiView, setAiView] = useState<"list" | "detail">("list");
  const [aiSelected, setAiSelected] = useState<ReviewItem | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [reviewCollapsed, setReviewCollapsed] = useState(false);
  const [ingestionCollapsed, setIngestionCollapsed] = useState(false);
  const [suggestionsCollapsed, setSuggestionsCollapsed] = useState(false);
  const [memoryCollapsed, setMemoryCollapsed] = useState(false);
  const [timeline, setTimeline] = useState<ReturnType<typeof buildTimeline> | null>(null);
  const tableScrollRef = useRef<HTMLDivElement>(null);
  const ganttScrollRef = useRef<HTMLDivElement>(null);
  const syncRef = useRef(false);

  /* sync scroll */
  const onTableScroll = useCallback(() => {
    if (syncRef.current || !ganttScrollRef.current || !tableScrollRef.current) return;
    syncRef.current = true;
    ganttScrollRef.current.scrollTop = tableScrollRef.current.scrollTop;
    syncRef.current = false;
  }, []);
  const onGanttScroll = useCallback(() => {
    if (syncRef.current || !tableScrollRef.current || !ganttScrollRef.current) return;
    syncRef.current = true;
    tableScrollRef.current.scrollTop = ganttScrollRef.current.scrollTop;
    syncRef.current = false;
  }, []);

  useEffect(() => {
    // Load activities from backend
    apiFetch<ActivityListResponse>("/api/v1/schedule/activities?page=1&page_size=100")
      .then(d => {
        const items = d.items || [];
        setActivities(items);
        setTimeline(buildTimeline(items));
        if (items.length) setSelected(items[0]);
      })
      .catch(err => {
        console.error("Failed to load activities:", err);
      });

    // Load review / ingestion from backend
    fetchProgressEvents(1, 20)
      .then(r => {
        const items = r.items || [];
        const rev: ReviewItem[] = items
          .filter((e: ProgressEvent) => !e.reviewed_by_planner &&
            (e.match_status === "low_confidence_review" || e.match_status === "matched" || e.match_status === "pending_match" || e.match_status === "unmatched_new"))
          .slice(0, 7)
          .map((e: ProgressEvent) => ({
            id: `EVT-${String(e.id).padStart(4, "0")}`,
            preview: (e.activity_description_extracted || e.activity_description_raw || "").slice(0, 50) + "…",
            message: e.activity_description_extracted || e.activity_description_raw || "No description",
            tag: e.discipline ? e.discipline.toUpperCase() : "GENERAL",
            activityId: e.activity_id_plan || "—",
            activityName: e.activity_description_extracted?.slice(0, 40) || "Unknown Activity",
            confidence: Math.round((e.confidence_score || 0.7) * 100),
            status: null,
            eventId: e.id,
          }));
        setReviewItems(rev);
        const ing = items.slice(0, 4).map((e: ProgressEvent) => ({
          sender: e.supervisor_name || "Field Team",
          msg: (e.activity_description_raw || "").slice(0, 48) + "…",
        }));
        setIngestion(ing);
      })
      .catch(err => {
        console.error("Failed to load events:", err);
      });
  }, []);

  async function applyStatus(item: ReviewItem, status: "accepted" | "declined") {
    try {
      await fetch(`${API_BASE}/api/v1/events/${item.eventId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${getAuthToken()}` },
        body: JSON.stringify({ decision: status }),
      });
    } catch {}
    setReviewItems(prev => prev.map(r => r.id === item.id ? { ...r, status } : r));
    if (aiSelected?.id === item.id) setAiSelected(prev => prev ? { ...prev, status } : prev);
    if (drawerSelected?.id === item.id) setDrawerSelected(prev => prev ? { ...prev, status } : prev);
  }

  /* ─── layout constants ─── */
  const ROW_H = 26;

  /* ─── Gantt bar renderer ─── */
  function renderBar(act: PlanActivity) {
    if (!timeline || !act.planned_start || !act.planned_finish) return null;
    const l = monthOffset(timeline.origin, act.planned_start) * MONTH_W;
    const r = monthOffset(timeline.origin, act.planned_finish) * MONTH_W;
    const w = Math.max(r - l, 4);
    const pct = act.actual_percent_complete || act.percent_complete_plan || 0;
    const isCritical = act.is_critical || (act.total_float_days != null && act.total_float_days <= 0);
    return (
      <div style={{ position: "absolute", left: l, width: w, top: 7, height: 9, borderRadius: 5,
        background: pct >= 100 ? "var(--success)" : isCritical ? "var(--danger)" : "var(--ink)",
        overflow: "hidden" }} title={`${act.activity_name} — ${pct}%`}>
        {pct > 0 && (
          <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${Math.min(pct,100)}%`,
            background: "rgba(217,130,43,0.7)", borderRadius: 5 }} />
        )}
      </div>
    );
  }

  const quarters = timeline ? (() => {
    const map: Record<string, string[]> = {};
    const order: string[] = [];
    timeline.months.forEach(m => {
      if (!map[m.quarter]) { map[m.quarter] = []; order.push(m.quarter); }
      map[m.quarter].push(m.label);
    });
    return order.map(q => ({ label: q, months: map[q] }));
  })() : [];

  /* ─── AI panel detail view ─── */
  function AiDetailView({ item, onBack, inDrawer }: { item: ReviewItem, onBack: () => void, inDrawer?: boolean }) {
    const tier = confidenceTier(item.confidence);
    const big = inDrawer;
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 14, animation: "fade-in .15s ease" }}>
        {!inDrawer && (
          <button onClick={onBack} style={{ alignSelf: "flex-start", background: "none", border: "none",
            color: "var(--ai-text-soft)", fontSize: 11.5, fontWeight: 500, cursor: "pointer",
            padding: "2px 0", display: "flex", alignItems: "center", gap: 5, fontFamily: "inherit" }}>
            ← Back to queue
          </button>
        )}
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: "var(--ai-text-soft)", fontFamily: "'IBM Plex Mono',monospace" }}>{item.id}</span>
          <span style={{ fontSize: 9, fontWeight: 600, color: "var(--ai-text-soft)", background: "var(--ai-surface3)", padding: "2px 8px", borderRadius: 20, border: "1px solid var(--ai-border)" }}>{item.tag}</span>
          {item.status && (
            <span style={{ fontSize: 9, fontWeight: 600, padding: "2px 8px", borderRadius: 20,
              background: item.status === "accepted" ? "var(--ai-text)" : "transparent",
              color: item.status === "accepted" ? "#fff" : "var(--ai-muted)",
              border: item.status === "accepted" ? "none" : "1px solid var(--ai-border-strong)" }}>
              {item.status === "accepted" ? "Accepted" : "Declined"}
            </span>
          )}
        </div>
        <div>
          <div style={{ fontSize: 10, fontWeight: 600, color: "var(--ai-text-soft)", textTransform: "uppercase", letterSpacing: ".5px", marginBottom: 5 }}>Message</div>
          <div style={{ fontSize: big ? 14 : 12.5, lineHeight: 1.5, color: "var(--ai-text)", background: "var(--ai-surface2)", border: "1px solid var(--ai-border)", borderRadius: 7, padding: big ? "16px 18px" : "10px 11px" }}>{item.message}</div>
        </div>
        <div>
          <div style={{ fontSize: 10, fontWeight: 600, color: "var(--ai-text-soft)", textTransform: "uppercase", letterSpacing: ".5px", marginBottom: 5 }}>Extracted Activity</div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, background: "var(--ai-surface2)", border: "1px solid var(--ai-border)", borderRadius: 7, padding: big ? "13px 15px" : "9px 11px" }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: "var(--ai-text)", background: "var(--ai-surface3)", padding: "2px 8px", borderRadius: 5, fontFamily: "'IBM Plex Mono',monospace" }}>{item.activityId}</span>
            <span style={{ fontSize: 12.5, color: "var(--ai-text)", fontWeight: 500 }}>{item.activityName}</span>
          </div>
        </div>
        <div>
          <div style={{ fontSize: 10, fontWeight: 600, color: "var(--ai-text-soft)", textTransform: "uppercase", letterSpacing: ".5px", marginBottom: 5 }}>Agent Confidence</div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ flex: 1, height: big ? 8 : 6, background: "var(--ai-surface3)", border: "1px solid var(--ai-border)", borderRadius: 20, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${item.confidence}%`, borderRadius: 20,
                background: tier === "high" ? "var(--ai-text)" : tier === "med" ? "var(--ai-border-strong)" : "var(--ai-muted)" }} />
            </div>
            <span style={{ fontSize: 11.5, fontWeight: 600, color: tier === "high" ? "var(--ai-text)" : tier === "med" ? "var(--ai-text-soft)" : "var(--ai-muted)", whiteSpace: "nowrap" }}>
              {item.confidence}% · {tier === "high" ? "High" : tier === "med" ? "Medium" : "Low"}
            </span>
          </div>
        </div>
        {!item.status && (
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={() => applyStatus(item, "accepted")} style={{ flex: 1, fontFamily: "inherit", fontSize: big ? 13 : 12, fontWeight: 600, padding: big ? "11px 10px" : "9px 8px", borderRadius: 7, border: "none", cursor: "pointer", background: "var(--ai-text)", color: "#fff" }}>Accept</button>
            <button onClick={() => { setEditMode(true); }} style={{ flex: 1, fontFamily: "inherit", fontSize: big ? 13 : 12, fontWeight: 600, padding: big ? "11px 10px" : "9px 8px", borderRadius: 7, border: "1px solid var(--ai-border)", cursor: "pointer", background: "transparent", color: "var(--ai-text-soft)" }}>Edit match</button>
            <button onClick={() => applyStatus(item, "declined")} style={{ flex: 1, fontFamily: "inherit", fontSize: big ? 13 : 12, fontWeight: 600, padding: big ? "11px 10px" : "9px 8px", borderRadius: 7, border: "1px solid var(--ai-border-strong)", cursor: "pointer", background: "transparent", color: "var(--ai-text-soft)" }}>Decline</button>
          </div>
        )}
        {editMode && (
          <div style={{ background: "var(--ai-surface2)", border: "1px solid var(--ai-border)", borderRadius: 7, padding: 11, display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: "var(--ai-text-soft)", textTransform: "uppercase", letterSpacing: ".5px" }}>Reassign to activity</div>
            <select style={{ fontFamily: "inherit", fontSize: 12, padding: "7px 8px", borderRadius: 7, border: "1px solid var(--ai-border)", background: "var(--ai-surface)", color: "var(--ai-text)" }}>
              {activities.filter(a => a.activity_id).map(a => (
                <option key={a.activity_id} value={a.activity_id}>{a.activity_id} — {a.activity_name}</option>
              ))}
            </select>
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={() => { applyStatus(item, "accepted"); setEditMode(false); }} style={{ flex: 1, fontFamily: "inherit", fontSize: 11.5, fontWeight: 600, padding: "7px 8px", borderRadius: 7, border: "1px solid var(--ai-text)", cursor: "pointer", background: "var(--ai-text)", color: "#fff" }}>Save match</button>
              <button onClick={() => setEditMode(false)} style={{ flex: 1, fontFamily: "inherit", fontSize: 11.5, fontWeight: 600, padding: "7px 8px", borderRadius: 7, border: "1px solid var(--ai-border)", cursor: "pointer", background: "transparent", color: "var(--ai-text-soft)" }}>Cancel</button>
            </div>
          </div>
        )}
      </div>
    );
  }

  /* ─── Details grid ─── */
  function DetailsGrid({ act }: { act: PlanActivity }) {
    if (activeTab === "general") return (
      <div style={{ display: "grid", gridTemplateColumns: "140px 1fr 140px 1fr", gap: "10px 18px", maxWidth: 780, fontSize: 12.5 }}>
        {[
          ["Activity ID", act.activity_id || "—"],
          ["Activity Name", act.activity_name],
          ["Activity Type", act.is_critical ? "Critical Task" : "Task"],
          ["% Complete", `${act.actual_percent_complete || act.percent_complete_plan || 0}%`],
          ["Start", formatDate(act.planned_start || "")],
          ["Finish", formatDate(act.planned_finish || "")],
          ["Original Duration", act.original_duration_days ? `${act.original_duration_days}d` : "—"],
          ["Remaining Duration", act.remaining_duration_days ? `${act.remaining_duration_days}d` : "—"],
          ["WBS Code", act.wbs_code || "—"],
          ["Discipline", act.discipline || "General"],
        ].map(([label, value]) => (
          <React.Fragment key={label}>
            <label style={{ color: "var(--muted)", alignSelf: "center", fontWeight: 500 }}>{label}</label>
            <div style={{ border: "1px solid var(--border)", borderRadius: 7, background: "var(--surface-alt)", padding: "6px 10px", minHeight: 14, fontFamily: label === "Activity ID" || label.includes("Duration") || label.includes("%") || label === "WBS Code" || label === "Start" || label === "Finish" ? "'IBM Plex Mono',monospace" : undefined, fontSize: 12 }}>{value}</div>
          </React.Fragment>
        ))}
      </div>
    );
    if (activeTab === "status") return (
      <div style={{ display: "grid", gridTemplateColumns: "140px 1fr 140px 1fr", gap: "10px 18px", maxWidth: 780, fontSize: 12.5 }}>
        {[
          ["Status", (act.actual_percent_complete || 0) > 0 ? "In Progress" : "Not Started"],
          ["Data Date", new Date().toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"2-digit"})],
          ["Physical % Complete", `${act.actual_percent_complete || 0}%`],
          ["Schedule % Complete", `${act.percent_complete_plan || 0}%`],
          ["Total Float", `${act.total_float_days ?? 0}d`],
          ["Critical", act.is_critical ? "Yes" : "No"],
        ].map(([label, value]) => (
          <React.Fragment key={label}>
            <label style={{ color: "var(--muted)", alignSelf: "center", fontWeight: 500 }}>{label}</label>
            <div style={{ border: "1px solid var(--border)", borderRadius: 7, background: "var(--surface-alt)", padding: "6px 10px", fontFamily: "'IBM Plex Mono',monospace", fontSize: 12 }}>{value}</div>
          </React.Fragment>
        ))}
      </div>
    );
    if (activeTab === "resources") return (
      <div style={{ display: "grid", gridTemplateColumns: "140px 1fr 140px 1fr", gap: "10px 18px", maxWidth: 780, fontSize: 12.5 }}>
        {[
          ["Resource", act.contractor_code || "Field Crew"],
          ["Role", act.discipline || "Site Labor"],
          ["Budgeted Units", "120h"], ["Actual Units", "0h"],
        ].map(([label, value]) => (
          <React.Fragment key={label}>
            <label style={{ color: "var(--muted)", alignSelf: "center", fontWeight: 500 }}>{label}</label>
            <div style={{ border: "1px solid var(--border)", borderRadius: 7, background: "var(--surface-alt)", padding: "6px 10px", fontSize: 12 }}>{value}</div>
          </React.Fragment>
        ))}
      </div>
    );
    return <div style={{ color: "var(--muted)", fontSize: 12.5 }}>No notebook topics recorded for &ldquo;{act.activity_name}&rdquo;.</div>;
  }

  return (
    <div style={{ display: "flex", width: "100vw", height: "100vh", padding: 16, gap: 16, boxSizing: "border-box", background: "var(--bg)" }}>

      {/* ── Kranti P1 frame ── */}
      <div style={{ flex: 1, minWidth: 0, border: "1px solid var(--border)", borderRadius: 14, background: "var(--surface)", boxShadow: "0 1px 2px rgba(16,24,38,.04), 0 6px 20px rgba(16,24,38,.06)", display: "flex", flexDirection: "column", overflow: "hidden" }}>

        {/* titlebar */}
        <div style={{ display: "flex", alignItems: "center", gap: 9, padding: "14px 18px", borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
          <span style={{ width: 9, height: 9, borderRadius: 2, background: "var(--accent)", display: "inline-block", transform: "rotate(45deg)" }} />
          <h1 style={{ fontSize: 14.5, fontWeight: 600, margin: 0 }}>Kranti P1</h1>
          <span style={{ fontSize: 11, color: "var(--muted)", fontWeight: 400, marginLeft: 2 }}>OIL India — Pipeline Expansion Phase 3</span>
          <button onClick={() => router.push("/navigator")} style={{ marginLeft: "auto", fontFamily: "inherit", fontSize: 11.5, fontWeight: 500, color: "var(--ink-soft)", background: "var(--surface-alt)", border: "1px solid var(--border)", borderRadius: 20, padding: "6px 13px", cursor: "pointer" }}>
            ↩ Projects
          </button>
        </div>

        {/* menubar */}
        <div style={{ display: "flex", gap: 2, padding: "6px 12px", borderBottom: "1px solid var(--border)", background: "var(--surface-alt)", flexShrink: 0 }}>
          {["File","Edit","View","Project","Enterprise","Tools","Help"].map(m => (
            <button key={m} style={{ fontFamily: "inherit", fontSize: 12.5, fontWeight: 500, padding: "6px 12px", background: "transparent", color: "var(--ink-soft)", border: "none", borderRadius: 7, cursor: "default" }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background="#e9edf3"; (e.currentTarget as HTMLElement).style.color="var(--ink)"; }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background="transparent"; (e.currentTarget as HTMLElement).style.color="var(--ink-soft)"; }}>
              {m}
            </button>
          ))}
        </div>

        {/* main row: activity table + gantt */}
        <div style={{ flex: "1 1 auto", display: "flex", minHeight: 0, borderBottom: "1px solid var(--border)" }}>

          {/* activity table pane */}
          <div style={{ width: "40%", minWidth: 260, borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column", minHeight: 0 }}>
            <div ref={tableScrollRef} onScroll={onTableScroll} style={{ overflow: "auto", flex: "1 1 auto", minHeight: 0 }}>
              <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 12, tableLayout: "fixed" }}>
                <thead>
                  <tr>
                    <th style={{ width: 64, position: "sticky", top: 0, zIndex: 2, background: "var(--surface-alt)", borderBottom: "1px solid var(--border-strong)", padding: "8px 10px", textAlign: "left", fontWeight: 600, fontSize: 10.5, color: "var(--ink-soft)", textTransform: "uppercase", letterSpacing: ".4px", whiteSpace: "nowrap" }}>Activity ID</th>
                    <th style={{ position: "sticky", top: 0, zIndex: 2, background: "var(--surface-alt)", borderBottom: "1px solid var(--border-strong)", padding: "8px 10px", textAlign: "left", fontWeight: 600, fontSize: 10.5, color: "var(--ink-soft)", textTransform: "uppercase", letterSpacing: ".4px" }}>Activity Name</th>
                    <th style={{ width: 42, position: "sticky", top: 0, zIndex: 2, background: "var(--surface-alt)", borderBottom: "1px solid var(--border-strong)", padding: "8px 10px", textAlign: "right", fontWeight: 600, fontSize: 10.5, color: "var(--ink-soft)", textTransform: "uppercase", letterSpacing: ".4px", whiteSpace: "nowrap" }}>Orig</th>
                    <th style={{ width: 42, position: "sticky", top: 0, zIndex: 2, background: "var(--surface-alt)", borderBottom: "1px solid var(--border-strong)", padding: "8px 10px", textAlign: "right", fontWeight: 600, fontSize: 10.5, color: "var(--ink-soft)", textTransform: "uppercase", letterSpacing: ".4px", whiteSpace: "nowrap" }}>Rem</th>
                    <th style={{ width: 38, position: "sticky", top: 0, zIndex: 2, background: "var(--surface-alt)", borderBottom: "1px solid var(--border-strong)", padding: "8px 10px", textAlign: "right", fontWeight: 600, fontSize: 10.5, color: "var(--ink-soft)", textTransform: "uppercase", letterSpacing: ".4px", whiteSpace: "nowrap" }}>%</th>
                  </tr>
                </thead>
                <tbody>
                  {activities.length === 0 && (
                    <tr><td colSpan={5} style={{ padding: "18px 12px", color: "var(--muted)", fontSize: 12, textAlign: "center" }}>No schedule loaded — import a P6 XER file.</td></tr>
                  )}
                  {activities.map((act) => {
                    const isSel = selected?.id === act.id;
                    const pct = act.actual_percent_complete || act.percent_complete_plan || 0;
                    return (
                      <tr key={act.id} onClick={() => { setSelected(act); setActiveTab("general"); }}
                        style={{ cursor: "pointer", background: isSel ? "var(--accent-soft)" : undefined, boxShadow: isSel ? "inset 3px 0 0 var(--accent)" : undefined, transition: "background .1s ease" }}>
                        <td style={{ borderBottom: "1px solid var(--border)", padding: "5px 10px", height: ROW_H, fontFamily: "'IBM Plex Mono',monospace", fontSize: 11, color: "var(--muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{act.activity_id}</td>
                        <td style={{ borderBottom: "1px solid var(--border)", padding: "5px 10px", height: ROW_H, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                            <span style={{ flex: "0 0 auto", width: 12, textAlign: "center", fontSize: 9, color: "var(--muted)" }}>●</span>
                            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{act.activity_name}</span>
                          </div>
                        </td>
                        <td style={{ borderBottom: "1px solid var(--border)", padding: "5px 10px", height: ROW_H, textAlign: "right", fontFamily: "'IBM Plex Mono',monospace", fontSize: 11, color: "var(--ink-soft)", whiteSpace: "nowrap" }}>{act.original_duration_days ? `${act.original_duration_days}d` : "—"}</td>
                        <td style={{ borderBottom: "1px solid var(--border)", padding: "5px 10px", height: ROW_H, textAlign: "right", fontFamily: "'IBM Plex Mono',monospace", fontSize: 11, color: "var(--ink-soft)", whiteSpace: "nowrap" }}>{act.remaining_duration_days ? `${act.remaining_duration_days}d` : "—"}</td>
                        <td style={{ borderBottom: "1px solid var(--border)", padding: "5px 10px", height: ROW_H, textAlign: "right", fontFamily: "'IBM Plex Mono',monospace", fontSize: 11, color: "var(--ink-soft)", whiteSpace: "nowrap" }}>{pct}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Gantt pane */}
          <div style={{ flex: "1 1 auto", minWidth: 0, display: "flex", flexDirection: "column", background: "var(--surface)" }}>
            <div ref={ganttScrollRef} onScroll={onGanttScroll} style={{ overflow: "auto", flex: "1 1 auto", minHeight: 0, position: "relative" }}>
              {timeline && (
                <div style={{ position: "relative", width: timeline.totalW, minWidth: "100%" }}>
                  {/* header */}
                  <div style={{ position: "sticky", top: 0, zIndex: 3, background: "var(--surface-alt)", width: timeline.totalW }}>
                    <div style={{ display: "flex" }}>
                      {quarters.map(q => (
                        <div key={q.label} style={{ width: q.months.length * MONTH_W, borderRight: "1px solid var(--border)", borderBottom: "1px solid var(--border-strong)", fontSize: 10.5, fontWeight: 600, color: "var(--ink-soft)", textAlign: "center", padding: "5px 0", whiteSpace: "nowrap" }}>
                          {q.label}
                        </div>
                      ))}
                    </div>
                    <div style={{ display: "flex" }}>
                      {timeline.months.map((m, i) => (
                        <div key={i} style={{ width: MONTH_W, borderRight: "1px solid var(--border)", borderBottom: "1px solid var(--border)", fontSize: 9.5, textAlign: "center", color: "var(--muted)", padding: "3px 0", flexShrink: 0 }}>
                          {m.label}
                        </div>
                      ))}
                    </div>
                  </div>
                  {/* body rows */}
                  <div style={{ position: "relative", width: timeline.totalW }}>
                    {activities.map((act) => {
                      const isSel = selected?.id === act.id;
                      return (
                        <div key={act.id} onClick={() => { setSelected(act); setActiveTab("general"); }}
                          style={{ height: ROW_H, position: "relative", borderBottom: "1px solid var(--border)", background: isSel ? "var(--accent-soft)" : undefined, cursor: "pointer", width: timeline.totalW }}>
                          {/* vertical grid lines */}
                          {timeline.months.map((_, i) => (
                            <div key={i} style={{ position: "absolute", top: 0, bottom: 0, left: i * MONTH_W, borderLeft: i % 3 === 0 ? "1px solid var(--border-strong)" : "1px solid #eef0f4" }} />
                          ))}
                          {renderBar(act)}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* details pane */}
        <div style={{ flex: "0 0 auto", maxHeight: "36%", display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div style={{ display: "flex", gap: 4, padding: "8px 18px 0", borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
            {["general","status","resources","notebook"].map(tab => (
              <button key={tab} onClick={() => setActiveTab(tab)} style={{ fontFamily: "inherit", fontSize: 12, fontWeight: activeTab === tab ? 600 : 500, padding: "7px 4px 9px", marginRight: 14, background: "none", color: activeTab === tab ? "var(--ink)" : "var(--muted)", border: "none", borderBottom: `2px solid ${activeTab === tab ? "var(--accent)" : "transparent"}`, cursor: "default" }}>
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>
          <div style={{ flex: "1 1 auto", overflow: "auto", padding: 18 }}>
            {selected ? <DetailsGrid act={selected} /> : <div style={{ color: "var(--muted)", fontSize: 12.5 }}>Select an activity above to view its details.</div>}
          </div>
        </div>
      </div>

      {/* ── Kranti AI frame ── */}
      <div style={{ width: 300, flexShrink: 0, border: "1px solid var(--ai-border)", borderRadius: 14, background: "var(--ai-bg)", display: "flex", flexDirection: "column", overflow: "hidden", boxShadow: "0 1px 2px rgba(16,24,38,.04), 0 6px 20px rgba(16,24,38,.06)" }}>

        {/* ai titlebar */}
        <div style={{ display: "flex", alignItems: "center", gap: 9, padding: "14px 18px", borderBottom: "1px solid var(--ai-border)", flexShrink: 0, background: "var(--ai-bg)" }}>
          <span style={{ width: 9, height: 9, borderRadius: 2, background: "var(--ai-text)", display: "inline-block", transform: "rotate(45deg)" }} />
          <h1 style={{ fontSize: 14.5, fontWeight: 600, margin: 0, color: "var(--ai-text)" }}>Kranti AI</h1>
        </div>

        <div style={{ flex: "1 1 auto", overflowY: "auto", display: "flex", flexDirection: "column", gap: 10, padding: 10 }}>

          {/* Review Queue section */}
          <div style={{ background: "var(--ai-surface)", border: "1px solid var(--ai-border)", borderRadius: 10, display: "flex", flexDirection: "column", flex: reviewCollapsed ? "0 0 auto" : "1 1 230px", minHeight: reviewCollapsed ? undefined : 170, overflow: "hidden" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 12px", borderBottom: reviewCollapsed ? "1px solid transparent" : "1px solid var(--ai-border)" }}>
              <button onClick={() => setReviewCollapsed(!reviewCollapsed)} style={{ width: 20, height: 20, flexShrink: 0, border: "none", background: "transparent", color: "var(--ai-text-soft)", fontSize: 11, cursor: "pointer", borderRadius: 5, display: "flex", alignItems: "center", justifyContent: "center", transition: "transform .15s ease" }}>
                {reviewCollapsed ? "▶" : "▾"}
              </button>
              <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--ai-text)" }}>Review Queue</span>
              <span style={{ marginLeft: "auto", fontSize: 10.5, color: "var(--ai-text-soft)", background: "var(--ai-surface3)", padding: "2px 8px", borderRadius: 20 }}>{reviewItems.filter(r => !r.status).length}</span>
              <button onClick={() => { setDrawerOpen(true); setDrawerSelected(null); }} title="Open full review queue" style={{ width: 20, height: 20, flexShrink: 0, border: "none", background: "transparent", color: "var(--ai-text-soft)", fontSize: 13, cursor: "pointer", borderRadius: 5, display: "flex", alignItems: "center", justifyContent: "center" }}>↗</button>
            </div>
            {!reviewCollapsed && (
              <div style={{ overflow: "hidden", flex: "1 1 auto", padding: "0 10px 10px", display: "flex", flexDirection: "column", minHeight: 0 }}>
                {aiView === "detail" && aiSelected ? (
                  <div style={{ overflow: "auto", flex: "1 1 auto", paddingTop: 4 }}>
                    <AiDetailView item={aiSelected} onBack={() => { setAiView("list"); setAiSelected(null); setEditMode(false); }} />
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 6, overflowY: "auto", flex: "1 1 auto", minHeight: 0, paddingTop: 4 }}>
                    {reviewItems.map(item => {
                      const tier = confidenceTier(item.confidence);
                      return (
                        <div key={item.id} onClick={() => { setAiSelected(item); setAiView("detail"); setEditMode(false); }}
                          style={{ background: "var(--ai-surface2)", border: "1px solid var(--ai-border)", borderRadius: 7, padding: "9px 10px", display: "flex", alignItems: "center", gap: 8, cursor: "pointer", minHeight: 24, transition: "border-color .12s ease" }}>
                          <span style={{ fontSize: 10, fontWeight: 600, color: "var(--ai-text-soft)", flexShrink: 0, fontFamily: "'IBM Plex Mono',monospace" }}>{item.id}</span>
                          <span style={{ fontSize: 11.5, color: "var(--ai-text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>{item.preview}</span>
                          <span style={{ fontSize: 9, fontWeight: 600, color: "var(--ai-text-soft)", background: "var(--ai-surface3)", padding: "2px 8px", borderRadius: 20, flexShrink: 0, whiteSpace: "nowrap", border: "1px solid var(--ai-border)" }}>{item.tag}</span>
                          {item.status ? (
                            <span style={{ fontSize: 9, fontWeight: 600, padding: "2px 8px", borderRadius: 20, flexShrink: 0, background: item.status === "accepted" ? "var(--ai-text)" : "transparent", color: item.status === "accepted" ? "#fff" : "var(--ai-muted)", border: item.status === "accepted" ? "none" : "1px solid var(--ai-border-strong)" }}>
                              {item.status === "accepted" ? "✓" : "✗"}
                            </span>
                          ) : (
                            <span style={{ fontSize: 9.5, fontWeight: 600, flexShrink: 0, padding: "2px 7px", borderRadius: 20, border: "1px solid transparent", color: tier === "high" ? "#fff" : tier === "med" ? "var(--ai-text)" : "var(--ai-text-soft)", background: tier === "high" ? "var(--ai-text)" : tier === "med" ? "var(--ai-border-strong)" : "var(--ai-surface2)" }}>
                              {item.confidence}%
                            </span>
                          )}
                        </div>
                      );
                    })}
                    {reviewItems.length === 0 && <div style={{ color: "var(--ai-muted)", fontSize: 12, padding: "10px 0" }}>No pending review items.</div>}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Ingestion Feed section */}
          <div style={{ background: "var(--ai-surface)", border: "1px solid var(--ai-border)", borderRadius: 10, display: "flex", flexDirection: "column", flex: ingestionCollapsed ? "0 0 auto" : "1 1 170px", minHeight: ingestionCollapsed ? undefined : 120, overflow: "hidden" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 12px", borderBottom: ingestionCollapsed ? "1px solid transparent" : "1px solid var(--ai-border)" }}>
              <button onClick={() => setIngestionCollapsed(!ingestionCollapsed)} style={{ width: 20, height: 20, flexShrink: 0, border: "none", background: "transparent", color: "var(--ai-text-soft)", fontSize: 11, cursor: "pointer", borderRadius: 5, display: "flex", alignItems: "center", justifyContent: "center" }}>
                {ingestionCollapsed ? "▶" : "▾"}
              </button>
              <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--ai-text)" }}>Ingestion Feed</span>
              <span style={{ marginLeft: "auto", fontSize: 10.5, color: "var(--ai-text-soft)", background: "var(--ai-surface3)", padding: "2px 8px", borderRadius: 20 }}>{ingestion.length}</span>
            </div>
            {!ingestionCollapsed && (
              <div style={{ overflow: "hidden", flex: "1 1 auto", padding: "0 10px 10px", display: "flex", flexDirection: "column", minHeight: 0 }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 6, overflowY: "auto", flex: "1 1 auto", paddingTop: 4 }}>
                  {ingestion.map((item, i) => (
                    <div key={i} style={{ background: "var(--ai-surface2)", border: "1px solid var(--ai-border)", borderRadius: 7, padding: "9px 10px", display: "flex", alignItems: "center", gap: 8, minHeight: 24 }}>
                      <span style={{ fontSize: 10.5, fontWeight: 600, color: "var(--ai-text-soft)", flexShrink: 0, width: 62 }}>{item.sender}</span>
                      <span style={{ fontSize: 11.5, color: "var(--ai-text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>{item.msg}</span>
                    </div>
                  ))}
                  {ingestion.length === 0 && <div style={{ color: "var(--ai-muted)", fontSize: 12, padding: "10px 0" }}>Waiting for field messages…</div>}
                </div>
              </div>
            )}
          </div>

          {/* Suggestions section */}
          <div style={{ background: "var(--ai-surface)", border: "1px solid var(--ai-border)", borderRadius: 10, display: "flex", flexDirection: "column", flex: suggestionsCollapsed ? "0 0 auto" : "0 1 120px", overflow: "hidden" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 12px", borderBottom: suggestionsCollapsed ? "1px solid transparent" : "1px solid var(--ai-border)" }}>
              <button onClick={() => setSuggestionsCollapsed(!suggestionsCollapsed)} style={{ width: 20, height: 20, flexShrink: 0, border: "none", background: "transparent", color: "var(--ai-text-soft)", fontSize: 11, cursor: "pointer", borderRadius: 5, display: "flex", alignItems: "center", justifyContent: "center" }}>
                {suggestionsCollapsed ? "▶" : "▾"}
              </button>
              <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--ai-text)" }}>Suggestions</span>
              <span style={{ marginLeft: "auto", fontSize: 10.5, color: "var(--ai-text-soft)", background: "var(--ai-surface3)", padding: "2px 8px", borderRadius: 20 }}>1</span>
            </div>
            {!suggestionsCollapsed && (
              <div style={{ overflow: "hidden", flex: "1 1 auto", padding: "4px 10px 10px" }}>
                <div style={{ background: "var(--ai-surface2)", border: "1px solid var(--ai-border)", borderRadius: 7, padding: "9px 10px", fontSize: 11.5, color: "var(--ai-text)" }}>
                  Check critical path — {activities.filter(a => a.is_critical).length} activities at risk of float exhaustion.
                </div>
              </div>
            )}
          </div>

          {/* Institutional Memory section */}
          <div style={{ background: "var(--ai-surface)", border: "1px solid var(--ai-border)", borderRadius: 10, display: "flex", flexDirection: "column", flex: memoryCollapsed ? "0 0 auto" : "0 1 120px", overflow: "hidden" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 12px", borderBottom: memoryCollapsed ? "1px solid transparent" : "1px solid var(--ai-border)" }}>
              <button onClick={() => setMemoryCollapsed(!memoryCollapsed)} style={{ width: 20, height: 20, flexShrink: 0, border: "none", background: "transparent", color: "var(--ai-text-soft)", fontSize: 11, cursor: "pointer", borderRadius: 5, display: "flex", alignItems: "center", justifyContent: "center" }}>
                {memoryCollapsed ? "▶" : "▾"}
              </button>
              <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--ai-text)" }}>Institutional Memory</span>
            </div>
            {!memoryCollapsed && (
              <div style={{ overflow: "hidden", flex: "1 1 auto", padding: "4px 10px 10px", display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ fontSize: 11, color: "var(--ai-text-soft)", padding: "2px 4px" }}>
                  Export dataset of validated events for predictive analysis.
                </div>
                <button onClick={() => window.open(`${API_BASE}/api/v1/memory/export`, '_blank')} style={{ fontFamily: "inherit", fontSize: 11.5, fontWeight: 600, padding: "7px 8px", borderRadius: 7, border: "1px solid var(--ai-border)", cursor: "pointer", background: "var(--ai-surface2)", color: "var(--ai-text)" }}>
                  Download Dataset
                </button>
              </div>
            )}
          </div>

        </div>
      </div>

      {/* ── Review Drawer (slide-in overlay) ── */}
      <div
        onClick={(e) => { if (e.target === e.currentTarget) setDrawerOpen(false); }}
        style={{ position: "fixed", inset: 0, background: "rgba(16,24,38,.4)", display: "flex", justifyContent: "flex-end", opacity: drawerOpen ? 1 : 0, pointerEvents: drawerOpen ? "auto" : "none", transition: "opacity .25s ease", zIndex: 500 }}
      >
        <div style={{ width: "min(1000px,92vw)", height: "100%", background: "var(--surface)", boxShadow: "-10px 0 34px rgba(16,24,38,.2)", transform: drawerOpen ? "translateX(0)" : "translateX(100%)", transition: "transform .32s cubic-bezier(.22,.9,.32,1)", display: "flex", flexDirection: "column" }}>

          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", padding: "22px 28px", borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 4 }}>
                <span style={{ width: 11, height: 11, borderRadius: 3, background: "var(--accent)", display: "inline-block", transform: "rotate(45deg)" }} />
                <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>Review Queue</h2>
              </div>
              <p style={{ margin: "4px 0 0", fontSize: 12, color: "var(--muted)" }}>Field messages matched to schedule activities by Kranti AI</p>
            </div>
            <button onClick={() => setDrawerOpen(false)} style={{ border: "none", background: "var(--surface-alt)", width: 32, height: 32, borderRadius: 9, fontSize: 19, lineHeight: 1, cursor: "pointer", color: "var(--ink-soft)" }}>×</button>
          </div>

          <div style={{ flex: "1 1 auto", display: "flex", minHeight: 0 }}>
            {/* drawer list */}
            <div style={{ width: 360, flexShrink: 0, borderRight: "1px solid var(--border)", overflowY: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 8 }}>
              {reviewItems.map(item => {
                const tier = confidenceTier(item.confidence);
                const isActive = drawerSelected?.id === item.id;
                return (
                  <div key={item.id} onClick={() => setDrawerSelected(item)}
                    style={{ background: isActive ? "#fff" : "var(--surface-alt)", border: `1px solid ${isActive ? "var(--ink)" : "var(--border)"}`, boxShadow: isActive ? "0 0 0 1px var(--ink) inset" : undefined, borderRadius: 7, padding: "12px 13px", cursor: "pointer", transition: "border-color .12s ease" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
                      <span style={{ fontSize: 10.5, fontWeight: 600, color: "var(--muted)", fontFamily: "'IBM Plex Mono',monospace" }}>{item.id}</span>
                      <span style={{ marginLeft: "auto", fontSize: 9, fontWeight: 600, color: "var(--ink-soft)", background: "var(--surface)", border: "1px solid var(--border)", padding: "2px 8px", borderRadius: 20 }}>{item.tag}</span>
                    </div>
                    <div style={{ fontSize: 12.5, color: "var(--ink)", lineHeight: 1.45 }}>{item.preview}</div>
                    <div style={{ marginTop: 9 }}>
                      {item.status ? (
                        <span style={{ fontSize: 9, fontWeight: 600, padding: "2px 8px", borderRadius: 20, background: item.status === "accepted" ? "var(--ink)" : "transparent", color: item.status === "accepted" ? "#fff" : "var(--muted)", border: item.status === "accepted" ? "none" : "1px solid var(--border-strong)" }}>
                          {item.status === "accepted" ? "Accepted" : "Declined"}
                        </span>
                      ) : (
                        <span style={{ fontSize: 9, fontWeight: 600, padding: "2px 8px", borderRadius: 20, color: tier === "high" ? "#fff" : "var(--ink)", background: tier === "high" ? "var(--ink)" : "var(--border)" }}>
                          {item.confidence}% confidence
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
            {/* drawer detail */}
            <div style={{ flex: "1 1 auto", overflowY: "auto", padding: "30px 34px" }}>
              {drawerSelected ? (
                <div style={{ maxWidth: 640 }}>
                  <AiDetailView item={drawerSelected} onBack={() => setDrawerSelected(null)} inDrawer />
                </div>
              ) : (
                <div style={{ color: "var(--muted)", fontSize: 13, textAlign: "center", marginTop: 80 }}>
                  Select a message on the left to review Kranti AI&apos;s match.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
