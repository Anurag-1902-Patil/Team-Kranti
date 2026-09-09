"use client";

import React, { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Search, Loader2, X, ExternalLink, Filter, Sparkles } from "lucide-react";
import { searchNatural } from "@/lib/api";
import type { NLSearchResult } from "@/lib/types";

const SUGGESTED_QUERIES = [
  "piping activities in Area A",
  "delayed activities with critical blockers",
  "hydrocarbon line erection",
  "equipment pump P-101",
];

export default function NLSearchBar() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<NLSearchResult | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function handleSearch(searchQuery: string) {
    const q = searchQuery.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    setIsOpen(true);
    try {
      const data = await searchNatural(q);
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSearch(query);
    } else if (e.key === "Escape") {
      setIsOpen(false);
    }
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-2xl">
      {/* Search Input Box */}
      <div className="relative flex items-center">
        <Search className="absolute left-3.5 w-4 h-4 text-slate-400 pointer-events-none" />
        <input
          id="nl-search-input"
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (result || query) setIsOpen(true);
          }}
          placeholder="Grounded search (e.g., 'delayed piping activities in Area A')..."
          className="w-full pl-10 pr-24 py-2 bg-slate-900/90 border border-slate-700/70 hover:border-slate-600 focus:border-cyan-500 rounded-lg text-sm text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-cyan-500/50 transition-all font-sans"
        />

        <div className="absolute right-2 flex items-center gap-1">
          {query && (
            <button
              onClick={() => {
                setQuery("");
                setResult(null);
                setIsOpen(false);
              }}
              className="p-1 text-slate-400 hover:text-slate-200"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}

          <button
            id="nl-search-submit-btn"
            onClick={() => handleSearch(query)}
            disabled={loading || !query.trim()}
            className="px-2.5 py-1 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 text-slate-950 font-medium text-xs rounded transition-colors flex items-center gap-1"
          >
            {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : "Search"}
          </button>
        </div>
      </div>

      {/* Dropdown Results Box */}
      {isOpen && (
        <div className="absolute left-0 right-0 top-full mt-1.5 z-50 pm-card shadow-2xl overflow-hidden border border-slate-700 bg-slate-950/95 backdrop-blur-md">
          {/* Preset Suggestions (if no query yet) */}
          {!result && !loading && (
            <div className="p-3 border-b border-slate-800">
              <p className="text-[11px] font-medium text-slate-400 mb-2 flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-cyan-400" />
                Example Queries:
              </p>
              <div className="flex flex-wrap gap-1.5">
                {SUGGESTED_QUERIES.map((preset) => (
                  <button
                    key={preset}
                    onClick={() => {
                      setQuery(preset);
                      handleSearch(preset);
                    }}
                    className="px-2 py-0.5 bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs rounded border border-slate-700/70 transition-colors"
                  >
                    {preset}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Loading Indicator */}
          {loading && (
            <div className="py-8 flex flex-col items-center justify-center text-slate-400 text-xs">
              <Loader2 className="w-5 h-5 animate-spin text-cyan-400 mb-2" />
              Parsing structured query and querying parameterized database...
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="p-4 text-xs text-rose-400 bg-rose-950/20 border-b border-rose-900/40">
              {error}
            </div>
          )}

          {/* Structured Filter Pills Display */}
          {result && !loading && (
            <div className="p-3 bg-slate-900/90 border-b border-slate-800">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] text-slate-400 flex items-center gap-1 font-medium">
                  <Filter className="w-3 h-3 text-cyan-400" />
                  Parsed Structured Filters:
                </span>
                <span className="text-[11px] text-slate-400 font-mono">
                  {result.total_matches} match{result.total_matches === 1 ? "" : "es"}
                </span>
              </div>

              <div className="flex flex-wrap gap-1.5">
                {result.parsed_filters.discipline && (
                  <span className="px-2 py-0.5 bg-cyan-950/70 text-cyan-300 border border-cyan-800/60 rounded text-[11px] font-mono">
                    Discipline: {result.parsed_filters.discipline}
                  </span>
                )}
                {result.parsed_filters.location && (
                  <span className="px-2 py-0.5 bg-sky-950/70 text-sky-300 border border-sky-800/60 rounded text-[11px] font-mono">
                    Location: {result.parsed_filters.location}
                  </span>
                )}
                {result.parsed_filters.equipment_tag && (
                  <span className="px-2 py-0.5 bg-amber-950/70 text-amber-300 border border-amber-800/60 rounded text-[11px] font-mono">
                    Tag: {result.parsed_filters.equipment_tag}
                  </span>
                )}
                {result.parsed_filters.is_delayed && (
                  <span className="px-2 py-0.5 bg-rose-950/70 text-rose-300 border border-rose-800/60 rounded text-[11px] font-mono">
                    Status: Delayed
                  </span>
                )}
                {result.parsed_filters.is_critical && (
                  <span className="px-2 py-0.5 bg-amber-950/70 text-amber-300 border border-amber-800/60 rounded text-[11px] font-mono">
                    Critical Path
                  </span>
                )}
                {result.parsed_filters.keyword && (
                  <span className="px-2 py-0.5 bg-slate-800 text-slate-300 border border-slate-700 rounded text-[11px] font-mono">
                    Keyword: "{result.parsed_filters.keyword}"
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Results List */}
          {result && !loading && (
            <div className="max-h-80 overflow-y-auto divide-y divide-slate-800/70">
              {result.results.length === 0 ? (
                <div className="p-4 text-center text-xs text-slate-400">
                  No records match this query. Try a broader search term.
                </div>
              ) : (
                result.results.map((item) => (
                  <div
                    key={`${item.record_type}-${item.id}`}
                    onClick={() => {
                      setIsOpen(false);
                      router.push(item.link_url);
                    }}
                    className="p-3 hover:bg-slate-900/80 cursor-pointer transition-colors flex items-start justify-between gap-3 group"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                          {item.record_type}
                        </span>
                        <span className="text-[10px] text-slate-400">{item.provenance}</span>
                      </div>
                      <p className="text-xs font-semibold text-slate-100 truncate group-hover:text-cyan-300 transition-colors">
                        {item.title}
                      </p>
                      <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-1">{item.summary}</p>
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0 text-right">
                      {item.progress_pct != null && (
                        <span className="text-xs font-mono font-medium text-slate-300">
                          {item.progress_pct}%
                        </span>
                      )}
                      <ExternalLink className="w-3.5 h-3.5 text-slate-500 group-hover:text-cyan-400 transition-colors" />
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
