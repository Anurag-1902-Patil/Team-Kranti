import { apiFetch } from "@/lib/api";
import type { ProgressEventList } from "@/lib/types";
import { ConfidenceBadge, DisciplineChip, ConfidenceBar } from "@/components/ConfidenceBadge";
import { AlertTriangle, Clock, FileText } from "lucide-react";
import Link from "next/link";

async function getReviewQueue() {
  try {
    return await apiFetch<ProgressEventList>("/api/v1/review/queue?page_size=5");
  } catch {
    return null;
  }
}

async function getEvents() {
  try {
    return await apiFetch<ProgressEventList>("/api/v1/events?page_size=10");
  } catch {
    return null;
  }
}

export default async function DashboardPage() {
  const [queue, events] = await Promise.all([getReviewQueue(), getEvents()]);

  const statusBreakdown = events?.items.reduce(
    (acc, e) => {
      acc[e.match_status] = (acc[e.match_status] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  ) ?? {};

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold gradient-text">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">
          SIH26122 — Intelligent Data Capture &amp; Schedule-Linking Layer
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Events", value: events?.total ?? "—", color: "text-white" },
          { label: "Matched (Auto)", value: statusBreakdown.matched ?? 0, color: "text-emerald-400" },
          { label: "Awaiting Review", value: (statusBreakdown.low_confidence_review ?? 0) + (statusBreakdown.unmatched_new ?? 0), color: "text-amber-400" },
          { label: "New Activities", value: statusBreakdown.unmatched_new ?? 0, color: "text-violet-400" },
        ].map(({ label, value, color }) => (
          <div key={label} className="glass-card p-4">
            <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</p>
            <p className={`text-3xl font-bold mt-1 ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Review Queue Preview */}
      <div className="glass-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <h2 className="text-sm font-semibold text-white">Review Queue</h2>
            {queue && queue.total > 0 && (
              <span className="ml-1 bg-amber-500/20 text-amber-400 text-xs px-2 py-0.5 rounded-full border border-amber-500/30 pulse-soft">
                {queue.total} pending
              </span>
            )}
          </div>
          <Link
            href="/review"
            className="text-xs text-violet-400 hover:text-violet-300 transition-colors"
          >
            View all →
          </Link>
        </div>

        {!queue || queue.total === 0 ? (
          <p className="text-sm text-gray-500 py-4 text-center">No events pending review.</p>
        ) : (
          <div className="space-y-2">
            {queue.items.map((ev) => (
              <Link
                href={`/review/${ev.id}`}
                key={ev.id}
                className="flex items-start gap-3 p-3 rounded-lg bg-gray-800/40 hover:bg-gray-800/70 transition-colors group"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-200 truncate group-hover:text-white transition-colors">
                    {ev.activity_description_extracted || "(no description)"}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <DisciplineChip discipline={ev.discipline} />
                    <span className="text-xs text-gray-600">
                      {ev.source_type?.replace(/_/g, " ")}
                    </span>
                  </div>
                </div>
                <div className="flex-shrink-0 w-32">
                  <ConfidenceBar score={ev.confidence_score} />
                  <div className="mt-1">
                    <ConfidenceBadge score={null} status={ev.match_status} />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Recent Events */}
      <div className="glass-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="w-4 h-4 text-gray-400" />
          <h2 className="text-sm font-semibold text-white">Recent Events</h2>
        </div>
        {!events || events.items.length === 0 ? (
          <p className="text-sm text-gray-500 py-4 text-center">
            No events yet. Send a WhatsApp message or run the demo script.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 border-b border-gray-800">
                  <th className="text-left py-2 pr-4 font-medium">Description</th>
                  <th className="text-left py-2 pr-4 font-medium">Plan Activity</th>
                  <th className="text-left py-2 pr-4 font-medium">Discipline</th>
                  <th className="text-left py-2 pr-4 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/50">
                {events.items.map((ev) => (
                  <tr key={ev.id} className="hover:bg-gray-800/30 transition-colors">
                    <td className="py-2 pr-4 text-gray-300 max-w-[200px] truncate">
                      {ev.activity_description_extracted || "—"}
                    </td>
                    <td className="py-2 pr-4 text-gray-400 max-w-[180px] truncate">
                      {ev.activity_name_plan || <span className="text-gray-600 italic">unmatched</span>}
                    </td>
                    <td className="py-2 pr-4">
                      <DisciplineChip discipline={ev.discipline} />
                    </td>
                    <td className="py-2">
                      <ConfidenceBadge score={ev.confidence_score} status={ev.match_status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
