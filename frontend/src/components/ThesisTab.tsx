"use client";

import { useState, useMemo } from "react";
import type { ThesisCategory } from "@/types/indices";
import { rawUrl } from "@/lib/github";
import MarkdownViewer from "./MarkdownViewer";

interface Props {
  thesis: ThesisCategory[];
}

const CATEGORY_COLORS: Record<string, string> = {
  "AI基礎建設": "text-violet-400", "AI應用":  "text-purple-400",
  "半導體":    "text-blue-400",   "光通訊":   "text-cyan-400",
  "企業軟體":  "text-indigo-400", "資安":     "text-green-400",
  "能源":      "text-amber-400",  "航太國防": "text-orange-400",
  "航運":      "text-sky-400",    "電動車":   "text-emerald-400",
  "生技醫療":  "text-pink-400",   "消費電子": "text-rose-400",
  "零信任資安": "text-green-400", "AI ASIC客製晶片": "text-blue-400",
};

interface SelectedTicker { ticker: string; filename: string; category: string }

export default function ThesisTab({ thesis }: Props) {
  const [search, setSearch]     = useState("");
  const [selected, setSelected] = useState<SelectedTicker | null>(null);
  const [content, setContent]   = useState<string | null>(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return thesis
      .map((cat) => ({
        category: cat.category,
        files: cat.files.filter(
          (f) => !q || f.ticker.toLowerCase().includes(q) || cat.category.toLowerCase().includes(q)
        ),
      }))
      .filter((cat) => cat.files.length > 0);
  }, [thesis, search]);

  async function loadThesis(ticker: string, filename: string, category: string) {
    setSelected({ ticker, filename, category });
    setLoading(true);
    setError(null);
    setContent(null);
    try {
      const res = await fetch(rawUrl(`thesis/${filename}`));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setContent(await res.text());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex gap-5 min-h-[70vh]">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 flex flex-col gap-2">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="搜尋 ticker / 板塊…"
          className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-500 outline-none focus:border-zinc-500 w-full"
        />
        <div className="flex-1 overflow-y-auto space-y-0.5 pr-1" style={{ maxHeight: "72vh" }}>
          {filtered.length === 0 && (
            <div className="text-zinc-500 text-sm text-center py-6">無符合結果</div>
          )}
          {filtered.map((cat) => {
            const cc = CATEGORY_COLORS[cat.category] ?? "text-zinc-400";
            return (
              <div key={cat.category} className="mb-2">
                <div className={`flex items-center justify-between px-2 py-1.5 text-xs font-semibold ${cc} tracking-wider`}>
                  <span>{cat.category}</span>
                  <span className="text-zinc-600 font-normal">{cat.files.length}</span>
                </div>
                <div className="space-y-0.5">
                  {cat.files.map((f) => (
                    <button
                      key={f.ticker}
                      onClick={() => loadThesis(f.ticker, f.filename, cat.category)}
                      className={`w-full text-left px-3 py-1.5 rounded text-xs font-mono tracking-wide transition-colors ${
                        selected?.ticker === f.ticker
                          ? "bg-blue-500/20 text-blue-300"
                          : "text-zinc-400 hover:bg-zinc-700/50 hover:text-zinc-200"
                      }`}
                    >
                      {f.ticker}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </aside>

      {/* Viewer */}
      <div className="flex-1 min-w-0 bg-zinc-900 rounded-xl border border-zinc-800 flex flex-col">
        <div className="px-6 py-3 border-b border-zinc-800 flex items-center justify-between shrink-0">
          <span className="text-sm font-medium text-zinc-300">
            {selected ? selected.ticker : "← 選擇左側標的"}
          </span>
          <span className="text-xs text-zinc-500">{selected?.category ?? ""}</span>
        </div>
        <div className="flex-1 overflow-y-auto px-7 py-5">
          {loading && <div className="text-zinc-500 text-center py-16">載入中…</div>}
          {error   && <div className="text-red-400 text-center py-16 text-sm">無法載入：{error}</div>}
          {!loading && !error && content && <MarkdownViewer content={content} />}
          {!loading && !error && !content && (
            <div className="text-zinc-500 text-center py-20 text-sm">請從左側選擇產業板塊與標的</div>
          )}
        </div>
      </div>
    </div>
  );
}
