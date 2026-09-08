"use client";

import { useState, useEffect } from "react";
import { apiFetch, API_BASE, getAuthToken } from "@/lib/api";
import type { MemoryQueryResult } from "@/lib/types";
import { Brain, Search, Download, Database } from "lucide-react";

interface MemoryStats {
  indexed_events: number;
  indexed_activities: number;
}

export default function MemoryPage() {
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [query, setQuery] = useState("");
  const [discipline, setDiscipline] = useState("all");
  const [results, setResults] = useState<MemoryQueryResult | null>(null);
  const [querying, setQuerying] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportMsg, setExportMsg] = useState("");

  useEffect(() => {
    apiFetch<MemoryStats>("/api/v1/memory/stats")
      .then(setStats)
      .catch(console.error);
  }, []);

  async function search() {
    if (!query.trim()) return;
    setQuerying(true);
    try {
      const params = new URLSearchParams({ q: query, n: "10" });
      if (discipline !== "all") params.set("discipline", discipline);
      const data = await apiFetch<MemoryQueryResult>(`/api/v1/memory/query?${params}`);
      setResults(data);
    } catch (e) {
      console.error(e);
    } finally {
      setQuerying(false);
    }
  }

  async function exportDataset() {
    setExporting(true);
    setExportMsg("");
    try {
      const res = await fetch(`${API_BASE}/api/v1/memory/export`, {
        headers: { Authorization: `Bearer ${getAuthToken()}` },
      });
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "sih26122_institutional_memory.zip";
      a.click();
      URL.revokeObjectURL(url);
      setExportMsg("✓ Dataset exported: Parquet + CSV + SCHEMA.md");
    } catch (e) {
      setExportMsg(`Error: ${String(e)}`);
    } finally {
      setExporting(false);
    }
  }

  const EXAMPLE_QUERIES = [
    "piping spool erection duration delays",
    "pump foundation excavation civil",
    "cable pulling electrical MCC",
    "HSE audit toolbox talk",
  ];

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold gradient-text">Institutional Memory</h1>
          <p className="text-sm text-gray-500 mt-1">
            Semantic search over finalized progress events. The system's collective site knowledge.
          </p>
        </div>
        <button
          onClick={exportDataset}
          disabled={exporting}
          id="export-dataset-btn"
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-violet-600 text-white text-sm font-medium hover:bg-violet-500 disabled:opacity-50 transition-colors"
        >
          <Download className="w-4 h-4" />
          {exporting ? "Exporting..." : "Export Dataset"}
        </button>
      </div>

      {exportMsg && (
        <p className={`text-sm ${exportMsg.startsWith("✓") ? "text-emerald-400" : "text-rose-400"}`}>
          {exportMsg}
        </p>
      )}

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 gap-4">
          <div className="glass-card p-4 flex items-center gap-3">
            <Database className="w-8 h-8 text-violet-400/60" />
            <div>
              <p className="text-3xl font-bold text-violet-400">{stats.indexed_events}</p>
              <p className="text-xs text-gray-500 mt-0.5">Progress Events Indexed</p>
            </div>
          </div>
          <div className="glass-card p-4 flex items-center gap-3">
            <Brain className="w-8 h-8 text-blue-400/60" />
            <div>
              <p className="text-3xl font-bold text-blue-400">{stats.indexed_activities}</p>
              <p className="text-xs text-gray-500 mt-0.5">Plan Activities in Index</p>
            </div>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="glass-card p-5 space-y-4">
        <h2 className="text-sm font-semibold text-white">Semantic Query</h2>

        <div className="flex gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()}
            placeholder="e.g. piping delays chainage 12"
            id="memory-query-input"
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-violet-500"
          />
          <select
            value={discipline}
            onChange={(e) => setDiscipline(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-violet-500"
          >
            <option value="all">All Disciplines</option>
            {["piping", "civil", "electrical", "instrumentation", "hse", "structural", "mechanical"].map(d => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
          <button
            onClick={search}
            disabled={querying || !query.trim()}
            id="memory-search-btn"
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-violet-600 text-white text-sm font-medium hover:bg-violet-500 disabled:opacity-50 transition-colors"
          >
            <Search className="w-4 h-4" />
            {querying ? "Searching..." : "Search"}
          </button>
        </div>

        {/* Example queries */}
        <div className="flex flex-wrap gap-2">
          <span className="text-xs text-gray-600">Try:</span>
          {EXAMPLE_QUERIES.map((q) => (
            <button
              key={q}
              onClick={() => { setQuery(q); }}
              className="text-xs text-violet-400 hover:text-violet-300 bg-violet-500/10 px-2 py-1 rounded transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Results */}
      {results && (
        <div className="glass-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-white">
              {results.result_count} results for "{results.query}"
            </p>
            <p className="text-xs text-gray-600">
              Searching {results.total_indexed} indexed events
            </p>
          </div>

          {results.result_count === 0 ? (
            <p className="text-sm text-gray-500 py-4 text-center">
              No results found. Try a different query or process more messages first.
            </p>
          ) : (
            <div className="space-y-3">
              {results.results.map((r, i) => (
                <div
                  key={i}
                  className="p-4 rounded-lg bg-gray-800/40 border border-gray-800/60"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm text-gray-200">{r.text}</p>
                    <div className="flex-shrink-0 flex items-center gap-1.5">
                      <div
                        className="h-1.5 w-16 bg-gray-700 rounded-full overflow-hidden"
                        title={`Similarity: ${r.similarity_score}`}
                      >
                        <div
                          className="h-full bg-violet-500 rounded-full"
                          style={{ width: `${Math.round(r.similarity_score * 100)}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500">
                        {(r.similarity_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-3 mt-2 text-xs text-gray-600">
                    {String(r.metadata.discipline || "") && <span>Discipline: {String(r.metadata.discipline)}</span>}
                    {String(r.metadata.actual_start || "") && (
                      <span>Start: {new Date(String(r.metadata.actual_start)).toLocaleDateString()}</span>
                    )}
                    {String(r.metadata.confidence_score || "") && (
                      <span>Match Confidence: {(Number(r.metadata.confidence_score) * 100).toFixed(0)}%</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
