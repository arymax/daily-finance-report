"use client";

import type { MarketData } from "@/types/dashboard";

interface Props {
  market: MarketData;
}

export default function MarketTab({ market }: Props) {
  const indices = Array.isArray(market.indices) ? market.indices : [];
  const ripple  = Array.isArray(market.ripple)  ? market.ripple  : [];
  const sectorsAny    = market.sectors as unknown as Record<string, string[]>;
  const strongSectors = sectorsAny?.strong ?? [];
  const weakSectors   = sectorsAny?.weak   ?? [];

  return (
    <div className="space-y-6">
      {/* Indices */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {indices.length ? (
          indices.map((idx: Record<string, unknown>, i: number) => {
            const chg = Number(idx.change_pct ?? 0);
            const pos = chg >= 0;
            return (
              <div
                key={i}
                className={`rounded-xl border p-5 ${pos ? "border-emerald-500/25 bg-emerald-950/20" : "border-red-500/25 bg-red-950/20"}`}
              >
                <p className="text-sm text-zinc-400 mb-1">{String(idx.name ?? "")}</p>
                <p className={`text-3xl font-bold ${pos ? "text-emerald-400" : "text-red-400"}`}>
                  {String(idx.change_str ?? (chg >= 0 ? `+${chg}%` : `${chg}%`))}
                </p>
              </div>
            );
          })
        ) : (
          <div className="col-span-3 text-zinc-500 text-center py-8">無指數資料</div>
        )}
      </div>

      {/* Sectors */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <SectorBlock title="強勢板塊" items={strongSectors} color="emerald" icon="📈" />
        <SectorBlock title="弱勢板塊" items={weakSectors}   color="red"     icon="📉" />
      </div>

      {/* Key events */}
      <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-5">
        <p className="text-sm font-medium mb-3">🔔 市場重要事件</p>
        <EventList items={market.key_events} dotColor="text-blue-400" />
      </div>

      {/* Risks */}
      <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-5">
        <p className="text-sm font-medium text-yellow-400 mb-3">⚠️ 風險提示</p>
        <EventList items={market.risks} dotColor="text-yellow-400" icon="⚡" />
      </div>

      {/* Ripple */}
      {ripple.length > 0 && (
        <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-5">
          <p className="text-sm font-medium text-cyan-400 mb-4">🌊 宏觀漣漪效應</p>
          <div className="space-y-4">
            {ripple.map((r: Record<string, unknown>, i: number) => (
              <div key={i} className="border border-zinc-700/60 rounded-lg p-4 bg-zinc-950/40">
                <p className="text-sm font-semibold text-cyan-300 mb-2">{String(r.title ?? "")}</p>
                {r.first_order  ? <p className="text-xs text-zinc-400 mb-1"><span className="text-zinc-500 mr-1.5">一階</span>{String(r.first_order)}</p>  : null}
                {r.second_order ? <p className="text-xs text-zinc-400 mb-1"><span className="text-zinc-500 mr-1.5">二階</span>{String(r.second_order)}</p> : null}
                {r.related      ? <p className="text-xs text-zinc-300 mt-2 font-mono leading-relaxed">{String(r.related)}</p>      : null}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SectorBlock({ title, items, color, icon }: { title: string; items: string[]; color: string; icon: string }) {
  const cls = color === "emerald" ? "text-emerald-400" : "text-red-400";
  return (
    <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-5">
      <p className={`text-sm font-medium ${cls} mb-3`}>{icon} {title}</p>
      {items.length ? (
        <div className="space-y-1.5">
          {items.map((s, i) => (
            <div key={i} className="flex items-center gap-2 text-sm py-1 border-b border-zinc-800 last:border-0">
              <span className={`text-xs ${cls}`}>▶</span>
              <span className="text-zinc-300">{s}</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-zinc-500 text-sm">無資料</p>
      )}
    </div>
  );
}

function EventList({ items, dotColor, icon = "•" }: { items: string[]; dotColor: string; icon?: string }) {
  if (!items?.length) return <p className="text-zinc-500 text-sm py-2">無資料</p>;
  return (
    <div className="divide-y divide-zinc-800/50">
      {items.map((e, i) => (
        <div key={i} className="flex gap-3 py-2.5">
          <span className={`${dotColor} mt-0.5 shrink-0`}>{icon}</span>
          <span className="text-sm text-zinc-300">{e}</span>
        </div>
      ))}
    </div>
  );
}
