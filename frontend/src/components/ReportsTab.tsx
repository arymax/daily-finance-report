"use client";

import { useState, useMemo } from "react";
import type { ReportEntry } from "@/types/indices";
import { rawUrl } from "@/lib/github";
import MarkdownViewer from "./MarkdownViewer";

interface Props {
  reports: ReportEntry[];
}

const TYPE_LABEL: Record<string, string> = {
  portfolio_analysis: "持倉分析",
  market_overview:    "市場總覽",
  premarket_check:    "盤前晨檢",
};
const SESSION_LABEL: Record<string, string> = { morning: "早盤", evening: "收盤" };

type FilterType = "" | "portfolio_analysis" | "market_overview";

export default function ReportsTab({ reports }: Props) {
  const [search, setSearch]     = useState("");
  const [typeFilter, setTypeFilter] = useState<FilterType>("");
  const [selected, setSelected] = useState<ReportEntry | null>(null);
  const [content, setContent]   = useState<string | null>(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return reports.filter((r) => {
      const matchType = !typeFilter || r.type === typeFilter;
      const matchQ    = !q || r.label.toLowerCase().includes(q) || r.date.includes(q);
      return matchType && matchQ;
    });
  }, [reports, search, typeFilter]);

  const byDate = useMemo(() => {
    const map: Record<string, ReportEntry[]> = {};
    for (const r of filtered) {
      (map[r.date] = map[r.date] ?? []).push(r);
    }
    return Object.entries(map).sort(([a], [b]) => b.localeCompare(a));
  }, [filtered]);

  async function loadReport(r: ReportEntry) {
    setSelected(r);
    setLoading(true);
    setError(null);
    setContent(null);
    try {
      const res = await fetch(rawUrl(`reports/${r.filename}`));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setContent(await res.text());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  const CHIPS: { key: FilterType; label: string }[] = [
    { key: "",                   label: "全部" },
    { key: "portfolio_analysis", label: "持倉" },
    { key: "market_overview",    label: "市場" },
  ];

  return (
    <div className="flex gap-5 min-h-[70vh]">
      {/* Sidebar */}
      <aside className="w-64 shrink-0 flex flex-col gap-2">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="搜尋日期 / 類型…"
          className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-500 outline-none focus:border-zinc-500 w-full"
        />
        <div className="flex gap-1.5 flex-wrap">
          {CHIPS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setTypeFilter(key)}
              className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                typeFilter === key
                  ? "bg-blue-700 text-blue-100 border-blue-600"
                  : "bg-zinc-800 text-zinc-400 border-zinc-700 hover:text-zinc-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="flex-1 overflow-y-auto space-y-0.5 pr-1" style={{ maxHeight: "72vh" }}>
          {byDate.length === 0 && (
            <div className="text-zinc-500 text-sm text-center py-6">無符合的報告</div>
          )}
          {byDate.map(([date, items]) => (
            <div key={date} className="mb-1">
              <div className="text-xs text-zinc-500 px-3 py-1 font-semibold">{date}</div>
              {items.map((r) => (
                <button
                  key={r.filename}
                  onClick={() => loadReport(r)}
                  className={`w-full text-left px-3 py-1.5 rounded text-xs transition-colors border-l-2 ${
                    selected?.filename === r.filename
                      ? "bg-blue-900/30 text-blue-200 border-blue-500"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 border-transparent"
                  }`}
                >
                  <span className="text-zinc-500 mr-1">{SESSION_LABEL[r.session] ?? ""}</span>
                  {TYPE_LABEL[r.type] ?? r.type}
                </button>
              ))}
            </div>
          ))}
        </div>
      </aside>

      {/* Viewer */}
      <div className="flex-1 min-w-0 bg-zinc-900 rounded-xl border border-zinc-800 flex flex-col">
        <div className="px-6 py-3 border-b border-zinc-800 flex items-center justify-between shrink-0">
          <span className="text-sm font-medium text-zinc-300">
            {selected ? selected.label : "← 選擇左側報告"}
          </span>
          {selected && (
            <span className="text-xs text-zinc-500">{selected.date}</span>
          )}
        </div>
        <div className="flex-1 overflow-y-auto px-7 py-5">
          {loading && <div className="text-zinc-500 text-center py-16">載入中…</div>}
          {error   && <div className="text-red-400 text-center py-16 text-sm">無法載入：{error}</div>}
          {!loading && !error && content && <MarkdownViewer content={content} />}
          {!loading && !error && !content && (
            <div className="text-zinc-500 text-center py-20 text-sm">請從左側選擇報告</div>
          )}
        </div>
      </div>
    </div>
  );
}
