"use client";

import { useState } from "react";
import type { ThemeEntry } from "@/types/indices";
import { rawUrl } from "@/lib/github";
import MarkdownViewer from "./MarkdownViewer";

interface Props {
  themes: ThemeEntry[];
}

const STATUS_CFG: Record<string, { icon: string; label: string; cls: string }> = {
  active:   { icon: "🔥", label: "熱門推進", cls: "bg-red-500/15 text-red-400 border-red-500/30" },
  building: { icon: "⏳", label: "蓄積中",   cls: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30" },
  cooling:  { icon: "💤", label: "降溫",     cls: "bg-blue-500/15 text-blue-400 border-blue-500/30" },
  peak:     { icon: "✅", label: "頂峰已過", cls: "bg-zinc-500/15 text-zinc-400 border-zinc-500/30" },
};

interface ViewerState { filename: string; name: string }

export default function ThemesTab({ themes }: Props) {
  const [viewer, setViewer]   = useState<ViewerState | null>(null);
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  async function openViewer(filename: string, name: string) {
    setViewer({ filename, name });
    setLoading(true);
    setError(null);
    setContent(null);
    try {
      const res = await fetch(rawUrl(`themes/${filename}`));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      let text = await res.text();
      // Strip YAML front matter
      if (text.startsWith("---")) {
        const end = text.indexOf("\n---", 3);
        if (end !== -1) text = text.slice(end + 4).trim();
      }
      setContent(text);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex gap-5 min-h-[70vh]">
      {/* Card grid */}
      <div className="flex-1 min-w-0">
        {themes.length === 0 ? (
          <div className="text-zinc-500 text-center py-16">無主題資料</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {themes.map((t) => {
              const sc = STATUS_CFG[t.status] ?? STATUS_CFG.building;
              const fp = t.fuel_pct ?? 0;
              const fuelColor = fp >= 70 ? "#22c55e" : fp >= 40 ? "#f59e0b" : "#ef4444";
              const msText = t.milestones_total > 0
                ? `${t.milestones_done}/${t.milestones_total} 里程碑`
                : "—";
              return (
                <div
                  key={t.id}
                  onClick={() => openViewer(t.filename, t.name)}
                  className={`bg-zinc-900 rounded-xl border p-5 flex flex-col gap-3 cursor-pointer transition-colors ${
                    viewer?.filename === t.filename
                      ? "border-blue-500/50"
                      : "border-zinc-800 hover:border-zinc-700"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-semibold text-zinc-100 text-sm leading-snug">{t.name}</p>
                    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium shrink-0 ${sc.cls}`}>
                      {sc.icon} {sc.label}
                    </span>
                  </div>

                  {/* Fuel gauge */}
                  <div>
                    <div className="flex justify-between text-xs text-zinc-400 mb-1">
                      <span>燃料剩餘</span>
                      <span className="font-semibold" style={{ color: fuelColor }}>{fp}%</span>
                    </div>
                    <div className="w-full bg-zinc-700 rounded-full h-1.5">
                      <div
                        className="h-1.5 rounded-full transition-all"
                        style={{ width: `${fp}%`, background: fuelColor }}
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs text-zinc-500">
                    <span>📌 {msText}</span>
                    <span>{t.last_updated ?? "—"}</span>
                  </div>

                  <div className="flex flex-wrap gap-1">
                    {(t.tickers ?? []).map((tk) => (
                      <span key={tk} className="text-xs bg-zinc-700 text-zinc-300 px-1.5 py-0.5 rounded font-mono">
                        {tk}
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Detail viewer */}
      {viewer && (
        <div className="w-[480px] shrink-0">
          <div className="bg-zinc-900 rounded-xl border border-zinc-800 h-full flex flex-col sticky top-20">
            <div className="px-5 py-3 border-b border-zinc-800 flex items-center justify-between shrink-0">
              <span className="text-sm font-medium text-zinc-200">{viewer.name}</span>
              <button
                onClick={() => setViewer(null)}
                className="text-zinc-500 hover:text-zinc-300 text-xs px-2 py-1 rounded hover:bg-zinc-700 transition-colors"
              >
                ✕ 關閉
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-6 py-4">
              {loading && <div className="text-zinc-500 text-center py-10">載入中…</div>}
              {error   && <div className="text-red-400 text-center py-10 text-sm">無法載入：{error}</div>}
              {!loading && !error && content && <MarkdownViewer content={content} />}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
