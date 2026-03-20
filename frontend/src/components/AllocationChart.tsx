"use client";

import dynamic from "next/dynamic";
import type { AllocationData } from "@/types/dashboard";

const COLORS = [
  "#6366f1", "#22d3ee", "#f59e0b", "#10b981",
  "#f43f5e", "#a78bfa", "#fb923c", "#34d399",
];

// Recharts is not SSR-safe; load only on the client
const Chart = dynamic(() => import("./_AllocationPie"), { ssr: false });

interface Props {
  allocation: AllocationData;
}

export default function AllocationChart({ allocation }: Props) {
  const data = Object.entries(allocation).map(([name, pct]) => ({
    name,
    pct,
    value: pct,
    fill: COLORS[Object.keys(allocation).indexOf(name) % COLORS.length],
  }));

  return (
    <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-6">
      <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider mb-4">
        資產配置
      </h2>
      <Chart data={data} />
    </div>
  );
}
