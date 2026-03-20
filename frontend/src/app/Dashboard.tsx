"use client";

import { useState } from "react";
import type { DashboardData, HistoryEntry } from "@/types/dashboard";
import type { ReportEntry, ThesisCategory, ThemeEntry } from "@/types/indices";
import { useLivePrices } from "@/hooks/useLivePrices";
import SummaryCard    from "@/components/SummaryCard";
import PositionsTable from "@/components/PositionsTable";
import WatchlistGrid  from "@/components/WatchlistGrid";
import AllocationChart from "@/components/AllocationChart";
import HistoryChart   from "@/components/HistoryChart";
import MarketTab      from "@/components/MarketTab";
import ReportsTab     from "@/components/ReportsTab";
import ThesisTab      from "@/components/ThesisTab";
import ThemesTab      from "@/components/ThemesTab";

type Tab = "portfolio" | "watchlist" | "market" | "reports" | "themes" | "thesis";

const TABS: { id: Tab; label: string }[] = [
  { id: "portfolio", label: "持倉總覽" },
  { id: "watchlist", label: "觀察清單" },
  { id: "market",    label: "市場摘要" },
  { id: "reports",   label: "報告記錄" },
  { id: "themes",    label: "主題催化劑" },
  { id: "thesis",    label: "產業研究" },
];

interface Props {
  data: DashboardData;
  history: HistoryEntry[];
  reports: ReportEntry[];
  thesis: ThesisCategory[];
  themes: ThemeEntry[];
}

export default function Dashboard({ data, history, reports, thesis, themes }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>("portfolio");
  const { prices, lastUpdated } = useLivePrices(data.positions, data.crypto, data.meta.usd_twd);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Header / Nav */}
      <header className="sticky top-0 z-50 bg-zinc-900/95 backdrop-blur border-b border-zinc-800">
        <div className="max-w-[1400px] mx-auto px-5 h-14 flex items-center gap-6">
          <span className="font-semibold text-white tracking-tight text-base shrink-0">
            📊 Finance Dashboard
          </span>

          <nav className="flex gap-0 h-full overflow-x-auto">
            {TABS.map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`px-4 text-sm font-medium h-full border-b-2 whitespace-nowrap transition-colors ${
                  activeTab === id
                    ? "border-blue-500 text-blue-300"
                    : "border-transparent text-zinc-500 hover:text-zinc-300"
                }`}
              >
                {label}
              </button>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-4 shrink-0">
            {lastUpdated && (
              <div className="flex flex-col items-end gap-0.5">
                <span className="text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full font-semibold tracking-wide animate-pulse">
                  ● LIVE
                </span>
                <span className="text-xs text-zinc-600">
                  {lastUpdated.toLocaleTimeString("zh-TW")}
                </span>
              </div>
            )}
            <div className="text-right text-xs leading-5 text-zinc-400">
              <div className="text-zinc-300 font-mono text-xs">{data.meta.date}</div>
              <div className="text-zinc-600">{data.meta.session === "morning" ? "早盤" : "收盤"}</div>
            </div>
            <div className="text-right text-xs text-zinc-500">
              USD/TWD {data.meta.usd_twd}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-[1400px] mx-auto px-5 py-6">
        {/* 持倉總覽 */}
        {activeTab === "portfolio" && (
          <div className="space-y-6">
            <SummaryCard
              summary={data.summary}
              usdTwd={data.meta.usd_twd}
              generatedAt={data.meta.generated_at}
              lastUpdated={lastUpdated}
            />
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
              <div className="lg:col-span-3">
                <PositionsTable
                  positions={data.positions}
                  crypto={data.crypto}
                  prices={prices}
                  usdTwd={data.meta.usd_twd}
                />
              </div>
              <div className="lg:col-span-2">
                <AllocationChart allocation={data.allocation} />
              </div>
            </div>
            <HistoryChart history={history} />
          </div>
        )}

        {/* 觀察清單 */}
        {activeTab === "watchlist" && (
          <WatchlistGrid watchlist={data.watchlist} />
        )}

        {/* 市場摘要 */}
        {activeTab === "market" && (
          <MarketTab market={data.market} />
        )}

        {/* 報告記錄 */}
        {activeTab === "reports" && (
          <ReportsTab reports={reports} />
        )}

        {/* 主題催化劑 */}
        {activeTab === "themes" && (
          <ThemesTab themes={themes} />
        )}

        {/* 產業研究 */}
        {activeTab === "thesis" && (
          <ThesisTab thesis={thesis} />
        )}
      </main>
    </div>
  );
}
