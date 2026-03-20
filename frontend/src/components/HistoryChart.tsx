"use client";

import dynamic from "next/dynamic";
import type { HistoryEntry } from "@/types/dashboard";

const Chart = dynamic(() => import("./_HistoryLine"), { ssr: false });

interface Props {
  history: HistoryEntry[];
}

export default function HistoryChart({ history }: Props) {
  return (
    <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-6">
      <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider mb-4">
        資產歷史走勢
      </h2>
      <Chart history={history} />
    </div>
  );
}
