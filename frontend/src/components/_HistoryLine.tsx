"use client";

import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, Legend,
} from "recharts";
import type { HistoryEntry } from "@/types/dashboard";

interface Props {
  history: HistoryEntry[];
}

export default function HistoryLine({ history }: Props) {
  // Keep one record per date (prefer evening)
  const byDate: Record<string, HistoryEntry> = {};
  for (const h of history) {
    if (!byDate[h.date] || h.session === "evening") byDate[h.date] = h;
  }
  const rows = Object.values(byDate).sort((a, b) => a.date.localeCompare(b.date));
  const data = rows.map((h) => ({
    date: h.date.slice(5),
    value: h.total_value_twd,
    pnl: h.total_pnl_pct,
  }));

  if (!data.length) {
    return <div className="text-zinc-600 text-sm text-center py-10">尚無歷史資料</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
        <XAxis dataKey="date" tick={{ fill: "#52525b", fontSize: 10 }} />
        <YAxis
          yAxisId="val"
          orientation="left"
          tick={{ fill: "#52525b", fontSize: 10 }}
          tickFormatter={(v) => `${(v / 1000).toFixed(0)}K`}
        />
        <YAxis
          yAxisId="pct"
          orientation="right"
          tick={{ fill: "#52525b", fontSize: 10 }}
          tickFormatter={(v) => `${v.toFixed(1)}%`}
        />
        <Tooltip
          contentStyle={{ backgroundColor: "#18181b", border: "1px solid #3f3f46", borderRadius: "0.5rem", color: "#e4e4e7" }}
          formatter={(value, name) =>
            name === "總資產"
              ? [`NT$${Number(value).toLocaleString()}`, name]
              : [`${Number(value).toFixed(1)}%`, name]
          }
        />
        <Legend wrapperStyle={{ fontSize: "11px", color: "#a1a1aa" }} />
        <Line yAxisId="val" type="monotone" dataKey="value" name="總資產" stroke="#3b82f6" dot={false} strokeWidth={2} />
        <Line yAxisId="pct" type="monotone" dataKey="pnl"   name="損益%" stroke="#4ade80" dot={false} strokeWidth={1.5} strokeDasharray="5 3" />
      </LineChart>
    </ResponsiveContainer>
  );
}
