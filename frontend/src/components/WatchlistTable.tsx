"use client";

import type { WatchlistItem } from "@/types/dashboard";

interface Props {
  watchlist: WatchlistItem[];
}

const priorityColor: Record<string, string> = {
  "1": "bg-red-500/20 text-red-400 border-red-500/30",
  "2": "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  "3": "bg-zinc-700 text-zinc-400 border-zinc-600",
  P1:  "bg-red-500/20 text-red-400 border-red-500/30",
  P2:  "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  P3:  "bg-zinc-700 text-zinc-400 border-zinc-600",
};

function priorityLabel(p: string | number | undefined): string {
  if (p == null) return "—";
  return typeof p === "number" ? `P${p}` : p;
}

function prioritySort(p: string | number | undefined): number {
  if (p == null) return 9;
  return typeof p === "number" ? p : parseInt(p.replace("P", "")) || 9;
}

function colorKey(p: string | number | undefined): string {
  if (p == null) return "3";
  return typeof p === "number" ? String(p) : p;
}

export default function WatchlistTable({ watchlist }: Props) {
  const sorted = [...watchlist].sort(
    (a, b) => prioritySort(a.priority) - prioritySort(b.priority)
  );

  return (
    <div className="rounded-xl bg-zinc-900 border border-zinc-800 overflow-hidden">
      <div className="px-6 py-4 border-b border-zinc-800">
        <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider">
          觀察清單
        </h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-zinc-500 border-b border-zinc-800">
              <th className="text-left px-6 py-3">優先</th>
              <th className="text-left px-4 py-3">標的</th>
              <th className="text-left px-4 py-3">市場</th>
              <th className="text-left px-4 py-3">論點摘要</th>
              <th className="text-right px-6 py-3">狀態</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {sorted.map((item) => {
              const ck = colorKey(item.priority);
              const pColor = priorityColor[ck] ?? priorityColor["3"];
              const label = priorityLabel(item.priority);
              return (
                <tr key={item.ticker} className="hover:bg-zinc-800/50 transition-colors">
                  <td className="px-6 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded border ${pColor}`}>
                      {label}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-white">{item.ticker}</div>
                    <div className="text-xs text-zinc-500">{item.name}</div>
                  </td>
                  <td className="px-4 py-3 text-zinc-400">{item.market}</td>
                  <td className="px-4 py-3 text-zinc-400 max-w-xs truncate">
                    {item.thesis ?? item.catalyst ?? item.theme ?? "—"}
                  </td>
                  <td className="px-6 py-3 text-right text-zinc-400">
                    {item.status_icon ?? item.status ?? "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
