"use client";

import type { Summary } from "@/types/dashboard";
import { twd, pct, sign } from "@/lib/fmt";

interface Props {
  summary: Summary;
  usdTwd: number;
  generatedAt: string;
  lastUpdated: Date | null;
  isLive?: boolean;
}

export default function SummaryCard({ summary, usdTwd, generatedAt, lastUpdated, isLive }: Props) {
  return (
    <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-baseline gap-2">
            <div className="text-3xl font-bold text-white">
              {twd(summary.total_value_twd)}
            </div>
            {isLive && (
              <span className="text-xs bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 px-1.5 py-0.5 rounded font-semibold">
                LIVE
              </span>
            )}
          </div>
          <div className={`text-lg font-medium mt-1 ${sign(summary.total_pnl_pct)}`}>
            {twd(summary.total_pnl_twd)} ({pct(summary.total_pnl_pct)})
          </div>
        </div>
        <div className="text-right text-xs text-zinc-500 space-y-1">
          <div>快照：{generatedAt}</div>
          {lastUpdated && (
            <div className="text-emerald-500">
              即時：{lastUpdated.toLocaleTimeString("zh-TW")}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-zinc-800">
        <Stat label="現金" value={twd(summary.cash_twd)} sub={`${summary.cash_pct}%`} />
        <Stat label="投入" value={twd(summary.total_value_twd - summary.cash_twd)} />
        <Stat label="USD/TWD" value={usdTwd.toFixed(2)} />
      </div>
    </div>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <div className="text-xs text-zinc-500 mb-1">{label}</div>
      <div className="text-sm font-semibold text-white">{value}</div>
      {sub && <div className="text-xs text-zinc-400">{sub}</div>}
    </div>
  );
}
