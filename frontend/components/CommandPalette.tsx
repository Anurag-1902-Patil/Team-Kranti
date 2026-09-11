"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import {
  Search,
  CalendarRange,
  CheckSquare,
  AlertOctagon,
  FileDown,
  ArrowRight,
  Filter,
  CheckCircle2,
  Clock,
  ExternalLink,
} from "lucide-react";
import { useApp } from "@/lib/AppContext";
import { parseSearchFilter } from "@/lib/api";
import type { ParsedFilterResponse } from "@/lib/types";

export function CommandPalette() {
  const router = useRouter();
  const { commandPaletteOpen, setCommandPaletteOpen, openActivityDetail } = useApp();
  const [query, setQuery] = useState("");
  const [parsedResult, setParsedResult] = useState<ParsedFilterResponse | null>(null);
  const [loading, setLoading] = useState(false);

  // Debounced search call to /api/v1/search/parse-filter
  useEffect(() => {
    if (!query || query.trim().length < 2) {
      setParsedResult(null);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await parseSearchFilter(query.trim());
        setParsedResult(res);
      } catch (err) {
        console.error("Command palette parse error:", err);
      } finally {
        setLoading(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [query]);

  const handleSelectRoute = (route: string) => {
    setCommandPaletteOpen(false);
    router.push(route);
  };

  const handleSelectActivity = (activityId: string) => {
    setCommandPaletteOpen(false);
    openActivityDetail(activityId);
  };

  if (!commandPaletteOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/40 z-50 flex items-start justify-center pt-24 px-4 backdrop-blur-[1px] animate-in fade-in duration-150"
      onClick={() => setCommandPaletteOpen(false)}
    >
      <div
        className="w-full max-w-2xl bg-white rounded-lg border border-zinc-200 shadow-xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <Command label="Global Command Menu" shouldFilter={false}>
          {/* Search Input Box */}
          <div className="flex items-center px-3 border-b border-zinc-200 bg-white">
            <Search className="w-4 h-4 text-zinc-400 shrink-0 mr-2" />
            <Command.Input
              value={query}
              onValueChange={setQuery}
              placeholder="Type a natural language query or command (e.g. 'delayed piping in Area A')..."
              className="w-full py-3 text-xs bg-transparent border-none outline-none text-zinc-900 placeholder:text-zinc-400 font-sans"
              autoFocus
            />
            {loading && <span className="text-[10px] text-zinc-400 font-mono">Parsing...</span>}
            <kbd className="text-[10px] text-zinc-400 font-mono bg-zinc-100 px-1.5 py-0.5 rounded border border-zinc-200 ml-2">
              ESC
            </kbd>
          </div>

          {/* Parsed Filter Pills (Part B #7 inspectable filter pills) */}
          {parsedResult && parsedResult.filters && (
            <div className="px-3 py-2 bg-zinc-50 border-b border-zinc-200 flex flex-wrap items-center gap-1.5 text-[11px]">
              <span className="text-zinc-400 font-medium flex items-center gap-1">
                <Filter className="w-3 h-3 text-zinc-400" /> Parsed:
              </span>

              {parsedResult.filters.discipline && (
                <span className="bg-blue-50 text-blue-800 border border-blue-200 px-2 py-0.5 rounded font-mono">
                  discipline: {parsedResult.filters.discipline}
                </span>
              )}

              {parsedResult.filters.status && (
                <span className="bg-amber-50 text-amber-800 border border-amber-200 px-2 py-0.5 rounded font-mono">
                  status: {parsedResult.filters.status}
                </span>
              )}

              {parsedResult.filters.is_delayed && (
                <span className="bg-red-50 text-red-800 border border-red-200 px-2 py-0.5 rounded font-mono">
                  delayed: true
                </span>
              )}

              {parsedResult.filters.is_critical && (
                <span className="bg-red-50 text-red-800 border border-red-200 px-2 py-0.5 rounded font-mono">
                  critical: true
                </span>
              )}

              {parsedResult.filters.location && (
                <span className="bg-slate-100 text-slate-800 border border-slate-200 px-2 py-0.5 rounded font-mono">
                  location: {parsedResult.filters.location}
                </span>
              )}

              {parsedResult.filters.keyword && (
                <span className="bg-zinc-100 text-zinc-700 border border-zinc-200 px-2 py-0.5 rounded font-mono">
                  keyword: "{parsedResult.filters.keyword}"
                </span>
              )}

              <button
                onClick={() => handleSelectRoute(parsedResult.suggested_route)}
                className="ml-auto text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1 hover:underline text-[11px]"
              >
                Apply to Schedule <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          )}

          {/* Results List */}
          <Command.List className="max-h-80 overflow-y-auto p-2">
            {/* Search Match Results */}
            {parsedResult && parsedResult.results_preview && parsedResult.results_preview.length > 0 && (
              <Command.Group heading="Direct Matches">
                {parsedResult.results_preview.map((item) => (
                  <Command.Item
                    key={item.id}
                    onSelect={() => handleSelectActivity(item.id)}
                    className="flex items-center justify-between p-2 rounded hover:bg-zinc-100 cursor-pointer text-xs group"
                  >
                    <div className="flex items-center gap-2.5">
                      <span className="font-mono text-zinc-500 font-semibold">{item.id}</span>
                      <span className="text-zinc-800 font-medium">{item.title}</span>
                      <span className="text-[10px] text-zinc-400 capitalize">({item.discipline})</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-zinc-500">{item.status}</span>
                      <ExternalLink className="w-3 h-3 text-zinc-400 group-hover:text-blue-600" />
                    </div>
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            {/* Default Quick Navigation Commands */}
            <Command.Group heading="Quick Navigation">
              <Command.Item
                onSelect={() => handleSelectRoute("/schedule")}
                className="flex items-center gap-2.5 p-2 rounded hover:bg-zinc-100 cursor-pointer text-xs text-zinc-700"
              >
                <CalendarRange className="w-4 h-4 text-zinc-400" />
                <span>Open P6 Schedule & Gantt View</span>
                <kbd className="ml-auto text-[10px] text-zinc-400 font-mono">G S</kbd>
              </Command.Item>

              <Command.Item
                onSelect={() => handleSelectRoute("/review")}
                className="flex items-center gap-2.5 p-2 rounded hover:bg-zinc-100 cursor-pointer text-xs text-zinc-700"
              >
                <CheckSquare className="w-4 h-4 text-zinc-400" />
                <span>Open Human Review Queue</span>
                <kbd className="ml-auto text-[10px] text-zinc-400 font-mono">G R</kbd>
              </Command.Item>

              <Command.Item
                onSelect={() => handleSelectRoute("/updates")}
                className="flex items-center gap-2.5 p-2 rounded hover:bg-zinc-100 cursor-pointer text-xs text-zinc-700"
              >
                <Clock className="w-4 h-4 text-zinc-400" />
                <span>Open Update Center (Daily Control Hub)</span>
                <kbd className="ml-auto text-[10px] text-zinc-400 font-mono">G U</kbd>
              </Command.Item>

              <Command.Item
                onSelect={() => handleSelectRoute("/analysis/delays")}
                className="flex items-center gap-2.5 p-2 rounded hover:bg-zinc-100 cursor-pointer text-xs text-zinc-700"
              >
                <AlertOctagon className="w-4 h-4 text-zinc-400" />
                <span>Open Delay & Root Cause Analytics</span>
                <kbd className="ml-auto text-[10px] text-zinc-400 font-mono">G D</kbd>
              </Command.Item>
            </Command.Group>

            <Command.Group heading="Quick Filters">
              <Command.Item
                onSelect={() => handleSelectRoute("/schedule?discipline=piping")}
                className="flex items-center gap-2.5 p-2 rounded hover:bg-zinc-100 cursor-pointer text-xs text-zinc-700"
              >
                <Filter className="w-4 h-4 text-zinc-400" />
                <span>Filter Schedule by Piping Discipline</span>
              </Command.Item>

              <Command.Item
                onSelect={() => handleSelectRoute("/schedule?critical_only=true")}
                className="flex items-center gap-2.5 p-2 rounded hover:bg-zinc-100 cursor-pointer text-xs text-zinc-700"
              >
                <Filter className="w-4 h-4 text-red-500" />
                <span>Show Critical Path Activities Only</span>
              </Command.Item>

              <Command.Item
                onSelect={() => handleSelectRoute("/schedule?status=delayed")}
                className="flex items-center gap-2.5 p-2 rounded hover:bg-zinc-100 cursor-pointer text-xs text-zinc-700"
              >
                <Filter className="w-4 h-4 text-amber-500" />
                <span>Show All Delayed Schedule Activities</span>
              </Command.Item>
            </Command.Group>
          </Command.List>

          {/* Palette Footer */}
          <div className="p-2.5 bg-zinc-50 border-t border-zinc-200 flex items-center justify-between text-[11px] text-zinc-400 select-none font-mono">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>ESC Close</span>
          </div>
        </Command>
      </div>
    </div>
  );
}
