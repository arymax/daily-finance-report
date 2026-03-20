"use client";

import type { DashboardData } from "@/types/dashboard";
import { useLivePrices } from "@/hooks/useLivePrices";
import SummaryCard from "@/components/SummaryCard";
import PositionsTable from "@/components/PositionsTable";
import WatchlistTable from "@/components/WatchlistTable";
import AllocationChart from "@/components/AllocationChart";

interface Props {
  data: DashboardData;
}

export default function Dashboard({ data }: Props) {
  const { prices, lastUpdated } = useLivePrices(
    data.positions,
    data.crypto,
    data.meta.usd_twd
  );

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Header */}
      <header className="border-b border-zinc-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-lg font-semibold text-white">每日財務儀表板</h1>
          <span className="text-xs text-zinc-500">{data.meta.date} · {data.meta.session}</span>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {/* Summary + Allocation row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <SummaryCard
              summary={data.summary}
              usdTwd={data.meta.usd_twd}
              generatedAt={data.meta.generated_at}
              lastUpdated={lastUpdated}
            />
          </div>
          <AllocationChart allocation={data.allocation} />
        </div>

        {/* Positions */}
        <PositionsTable
          positions={data.positions}
          crypto={data.crypto}
          prices={prices}
          usdTwd={data.meta.usd_twd}
        />

        {/* Watchlist */}
        <WatchlistTable watchlist={data.watchlist} />
      </main>
    </div>
  );
}
