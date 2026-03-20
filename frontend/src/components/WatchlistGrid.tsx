"use client";

import type { WatchlistItem } from "@/types/dashboard";

interface Props {
  watchlist: WatchlistItem[];
}

const PRIORITY_COLOR: Record<string, string> = {
  "1": "bg-blue-900/40 text-blue-400",
  "2": "bg-yellow-900/30 text-yellow-400",
  "3": "bg-zinc-800 text-zinc-400",
};
const STATUS_CFG: Record<string, { cls: string; icon: string }> = {
  "未達成":  { cls: "bg-sky-900/30 text-sky-400",      icon: "⏳" },
  "部分達成": { cls: "bg-yellow-900/30 text-yellow-400", icon: "🔄" },
  "已達成":  { cls: "bg-emerald-900/30 text-emerald-400", icon: "✅" },
};

function priorityNum(p: string | number | undefined): number {
  if (p == null) return 9;
  return typeof p === "number" ? p : parseInt(String(p).replace("P", "")) || 9;
}

export default function WatchlistGrid({ watchlist }: Props) {
  const sorted = [...watchlist].sort((a, b) => priorityNum(a.priority) - priorityNum(b.priority));

  if (!sorted.length) {
    return <div className="text-zinc-500 text-center py-16">無觀察清單資料</div>;
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-4 text-xs text-zinc-500">
        <span className="bg-blue-900/40 text-blue-400 px-2 py-0.5 rounded font-semibold">P1</span> 高優先 —
        <span className="bg-yellow-900/30 text-yellow-400 px-2 py-0.5 rounded font-semibold">P2</span> 中優先 —
        <span className="bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded font-semibold">P3</span> 持續追蹤
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {sorted.map((w) => {
          const pNum = priorityNum(w.priority);
          const pKey = String(pNum);
          const pColor = PRIORITY_COLOR[pKey] ?? PRIORITY_COLOR["3"];
          const sc = STATUS_CFG[w.status ?? "未達成"] ?? STATUS_CFG["未達成"];
          return (
            <div
              key={w.ticker}
              className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 flex flex-col gap-3 hover:border-zinc-700 transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-1.5 mb-0.5">
                    <span className="font-bold text-white">{w.ticker}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded font-semibold ${pColor}`}>
                      P{pNum}
                    </span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${sc.cls}`}>
                      {sc.icon} {w.status ?? "未達成"}
                    </span>
                  </div>
                  <p className="text-sm text-zinc-300 truncate">{w.name}</p>
                </div>
                <span className="text-xs text-zinc-500 shrink-0 mt-0.5">{w.market}</span>
              </div>
              {w.sector && (
                <div className="text-xs text-zinc-400 bg-zinc-800/60 rounded px-2.5 py-1.5 leading-relaxed truncate">
                  {w.sector}
                </div>
              )}
              {w.theme && (
                <p className="text-xs text-zinc-400 leading-relaxed line-clamp-2">{w.theme}</p>
              )}
              {w.action && (
                <div className="text-xs text-zinc-300 leading-relaxed border-l-2 border-zinc-600 pl-2.5">
                  {w.action}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
