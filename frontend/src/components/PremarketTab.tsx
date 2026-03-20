"use client";

import { usePremarket, PREMARKET_GROUPS } from "@/hooks/usePremarket";
import type { ReportEntry } from "@/types/indices";
import { rawUrl } from "@/lib/github";
import MarkdownViewer from "./MarkdownViewer";
import { useState } from "react";

interface Props {
  reports: ReportEntry[];
}

function fmtPrice(v: number | null, sym: string): string {
  if (v == null) return "—";
  // Yields are in percentage points already
  const isYield = sym.startsWith("^") && ["^IRX","^FVX","^TNX","^TYX"].includes(sym);
  if (isYield) return `${v.toFixed(3)}%`;
  if (v >= 1000) return v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return v.toFixed(v >= 10 ? 2 : 4);
}

function fmtPct(v: number | null): string {
  if (v == null) return "";
  const sign = v >= 0 ? "+" : "";
  return `${sign}${v.toFixed(2)}%`;
}

function signColor(v: number | null, invert = false): string {
  if (v == null) return "text-zinc-400";
  const pos = v >= 0;
  const good = invert ? !pos : pos;
  return good ? "text-emerald-400" : "text-red-400";
}

export default function PremarketTab({ reports }: Props) {
  const { quotes, lastUpdated, loading } = usePremarket();

  // Latest premarket_check report
  const latestPremarket = reports
    .filter((r) => r.type === "premarket_check")
    .sort((a, b) => b.date.localeCompare(a.date) || b.session.localeCompare(a.session))[0];

  const [reportContent, setReportContent]   = useState<string | null>(null);
  const [reportLoading, setReportLoading]   = useState(false);
  const [reportLoaded,  setReportLoaded]    = useState(false);

  async function loadReport() {
    if (!latestPremarket || reportLoaded) return;
    setReportLoading(true);
    try {
      const res = await fetch(rawUrl(`reports/${latestPremarket.filename}`));
      if (res.ok) setReportContent(await res.text());
    } finally {
      setReportLoading(false);
      setReportLoaded(true);
    }
  }

  // VIX level interpretation
  const vix = quotes["^VIX"]?.price;
  const vixStatus =
    vix == null  ? null
    : vix >= 35  ? { label: "極端恐慌", cls: "text-red-400 bg-red-900/30 border-red-700" }
    : vix >= 25  ? { label: "高度恐慌", cls: "text-orange-400 bg-orange-900/20 border-orange-700" }
    : vix >= 18  ? { label: "警戒區間", cls: "text-yellow-400 bg-yellow-900/20 border-yellow-700" }
    : vix >= 12  ? { label: "正常", cls: "text-emerald-400 bg-emerald-900/20 border-emerald-700" }
    :              { label: "過度樂觀", cls: "text-blue-400 bg-blue-900/20 border-blue-700" };

  // 2s10s spread (if both available)
  const y2  = quotes["^IRX"]?.price;
  const y10 = quotes["^TNX"]?.price;
  const spread = y2 != null && y10 != null ? y10 - y2 : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-zinc-100">盤前監控</h2>
          <p className="text-xs text-zinc-500 mt-0.5">
            每 60 秒自動更新 · 資料來源：Yahoo Finance
          </p>
        </div>
        <div className="text-right text-xs">
          {loading && <span className="text-zinc-500">載入中…</span>}
          {!loading && lastUpdated && (
            <span className="text-emerald-400">
              ● 更新 {lastUpdated.toLocaleTimeString("zh-TW")}
            </span>
          )}
        </div>
      </div>

      {/* VIX + Spread quick-read */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {vixStatus && (
          <div className={`rounded-xl border p-4 ${vixStatus.cls}`}>
            <p className="text-xs opacity-70 mb-1">VIX 恐慌指數</p>
            <p className="text-2xl font-bold">{vix?.toFixed(2)}</p>
            <p className="text-xs mt-1">{vixStatus.label}</p>
          </div>
        )}
        {spread != null && (
          <div className={`rounded-xl border p-4 ${spread >= 0 ? "bg-emerald-900/20 border-emerald-700 text-emerald-400" : "bg-red-900/20 border-red-700 text-red-400"}`}>
            <p className="text-xs opacity-70 mb-1">2s10s 殖利率利差</p>
            <p className="text-2xl font-bold">{spread >= 0 ? "+" : ""}{spread.toFixed(3)}%</p>
            <p className="text-xs mt-1">{spread >= 0 ? "正常（未倒掛）" : "⚠️ 殖利率倒掛"}</p>
          </div>
        )}
        {/* ES futures quick */}
        {quotes["ES=F"]?.price != null && (
          <div className={`rounded-xl border p-4 ${signColor(quotes["ES=F"].changePct) === "text-emerald-400" ? "bg-emerald-900/20 border-emerald-700" : "bg-red-900/20 border-red-700"}`}>
            <p className="text-xs text-zinc-400 mb-1">S&P 500 期貨</p>
            <p className={`text-2xl font-bold ${signColor(quotes["ES=F"].changePct)}`}>
              {fmtPct(quotes["ES=F"].changePct)}
            </p>
            <p className="text-xs text-zinc-400 mt-1">{fmtPrice(quotes["ES=F"].price, "ES=F")}</p>
          </div>
        )}
        {/* NQ futures quick */}
        {quotes["NQ=F"]?.price != null && (
          <div className={`rounded-xl border p-4 ${signColor(quotes["NQ=F"].changePct) === "text-emerald-400" ? "bg-emerald-900/20 border-emerald-700" : "bg-red-900/20 border-red-700"}`}>
            <p className="text-xs text-zinc-400 mb-1">Nasdaq 100 期貨</p>
            <p className={`text-2xl font-bold ${signColor(quotes["NQ=F"].changePct)}`}>
              {fmtPct(quotes["NQ=F"].changePct)}
            </p>
            <p className="text-xs text-zinc-400 mt-1">{fmtPrice(quotes["NQ=F"].price, "NQ=F")}</p>
          </div>
        )}
      </div>

      {/* All groups */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {PREMARKET_GROUPS.map((group) => (
          <div key={group.title} className="rounded-xl bg-zinc-900 border border-zinc-800">
            <div className="px-5 py-3 border-b border-zinc-800">
              <h3 className={`text-xs font-semibold uppercase tracking-wider ${group.color}`}>
                {group.title}
              </h3>
            </div>
            <div className="divide-y divide-zinc-800">
              {group.items.map((item) => {
                const q   = quotes[item.symbol];
                const inv = item.symbol === "^VIX" || item.symbol === "^VVIX" ||
                            item.symbol.startsWith("^") && ["^IRX","^FVX","^TNX","^TYX"].includes(item.symbol);
                // Bond yields: rising = bad for stocks (invert color) — actually neutral, don't invert
                const colorInvert = item.symbol === "^VIX" || item.symbol === "^VVIX";
                return (
                  <div key={item.symbol} className="flex items-center justify-between px-5 py-2.5">
                    <div>
                      <span className="text-sm text-zinc-200">{item.label}</span>
                      <span className="text-xs text-zinc-600 ml-2">{item.symbol}</span>
                    </div>
                    <div className="text-right">
                      {q?.error || q == null ? (
                        <span className="text-zinc-600 text-sm">{loading ? "…" : "—"}</span>
                      ) : (
                        <>
                          <div className="text-sm font-mono font-medium text-zinc-100">
                            {fmtPrice(q.price, item.symbol)}
                          </div>
                          <div className={`text-xs font-mono ${signColor(q.changePct, colorInvert)}`}>
                            {fmtPct(q.changePct)}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Latest premarket report */}
      {latestPremarket && (
        <div className="rounded-xl bg-zinc-900 border border-zinc-800">
          <button
            onClick={loadReport}
            className="w-full flex items-center justify-between px-6 py-4 hover:bg-zinc-800/50 transition-colors text-left"
          >
            <div>
              <p className="text-sm font-semibold text-zinc-200">最新盤前晨檢報告</p>
              <p className="text-xs text-zinc-500 mt-0.5">{latestPremarket.label}</p>
            </div>
            <span className="text-xs text-zinc-500">{reportLoaded ? "▲ 收起" : "▼ 展開"}</span>
          </button>
          {reportLoaded && (
            <div className="border-t border-zinc-800 px-7 py-5">
              {reportLoading && <div className="text-zinc-500 text-center py-8">載入中…</div>}
              {reportContent && <MarkdownViewer content={reportContent} />}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
