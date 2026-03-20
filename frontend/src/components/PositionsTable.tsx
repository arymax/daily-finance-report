"use client";

import type { Position, CryptoPosition, LivePrices } from "@/types/dashboard";
import { twd, pct, sign } from "@/lib/fmt";

interface Props {
  positions: Position[];
  crypto: CryptoPosition[];
  prices: LivePrices;
  usdTwd: number;
}

function computeLive(
  ticker: string,
  market: string,
  shares: number | undefined,
  costTwd: number,
  prices: LivePrices,
  usdTwd: number
) {
  const livePrice = prices[ticker];
  if (!livePrice || !shares) return null;
  // TW stocks in TWD, US stocks in USD, crypto stored as TWD via hook
  const valueTwd =
    market === "US" ? livePrice * shares * usdTwd : livePrice * shares;
  const pnlTwd = valueTwd - costTwd;
  const pnlPct = costTwd ? (pnlTwd / costTwd) * 100 : 0;
  return { livePrice, valueTwd, pnlTwd, pnlPct };
}

function parsePrice(raw: string | number | undefined): number | null {
  if (raw == null) return null;
  const n = typeof raw === "number" ? raw : parseFloat(String(raw));
  return isFinite(n) && n > 0 ? n : null;
}

interface RowProps {
  ticker: string;
  name: string;
  type: string;
  market: string;
  shares?: number;
  costTwd: number;
  snapshotPrice?: string | number;
  snapshotValue?: number;
  snapshotPnl?: number;
  snapshotPnlPct?: number;
  prices: LivePrices;
  usdTwd: number;
}

function Row({
  ticker, name, type, market, shares, costTwd,
  snapshotPrice, snapshotValue, snapshotPnl, snapshotPnlPct,
  prices, usdTwd,
}: RowProps) {
  const live = computeLive(ticker, market, shares, costTwd, prices, usdTwd);
  const displayPnlPct = live?.pnlPct ?? snapshotPnlPct ?? 0;
  const displayPnl = live?.pnlTwd ?? snapshotPnl ?? 0;
  const displayValue = live?.valueTwd ?? snapshotValue ?? costTwd;
  const snapshotPriceNum = parsePrice(snapshotPrice);
  const displayPrice = live?.livePrice ?? snapshotPriceNum;

  return (
    <tr className="hover:bg-zinc-800/50 transition-colors">
      <td className="px-6 py-3">
        <div className="font-medium text-white">{ticker}</div>
        <div className="text-xs text-zinc-500">{name}</div>
      </td>
      <td className="px-4 py-3 text-right text-zinc-400 text-xs">{type}</td>
      <td className="px-4 py-3 text-right text-zinc-300">{shares ?? "—"}</td>
      <td className="px-4 py-3 text-right text-zinc-400">{twd(costTwd)}</td>
      <td className="px-4 py-3 text-right text-zinc-300">
        {displayPrice != null ? (
          <span className={live ? "text-yellow-400" : ""}>
            {displayPrice.toFixed(2)}
          </span>
        ) : (
          <span className="text-zinc-600">—</span>
        )}
      </td>
      <td className="px-4 py-3 text-right text-zinc-300">{twd(displayValue)}</td>
      <td className={`px-6 py-3 text-right font-medium ${sign(displayPnlPct)}`}>
        <div>{pct(displayPnlPct)}</div>
        <div className="text-xs opacity-75">{twd(displayPnl)}</div>
      </td>
    </tr>
  );
}

export default function PositionsTable({ positions, crypto, prices, usdTwd }: Props) {
  return (
    <div className="rounded-xl bg-zinc-900 border border-zinc-800 overflow-hidden">
      <div className="px-6 py-4 border-b border-zinc-800">
        <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider">
          持倉明細
        </h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-zinc-500 border-b border-zinc-800">
              <th className="text-left px-6 py-3">標的</th>
              <th className="text-right px-4 py-3">類型</th>
              <th className="text-right px-4 py-3">股數</th>
              <th className="text-right px-4 py-3">成本(TWD)</th>
              <th className="text-right px-4 py-3">即時股價</th>
              <th className="text-right px-4 py-3">市值(TWD)</th>
              <th className="text-right px-6 py-3">損益</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {positions.map((pos) => (
              <Row
                key={pos.ticker}
                ticker={pos.ticker}
                name={pos.name}
                type={pos.type}
                market={pos.market}
                shares={pos.shares}
                costTwd={pos.cost_twd}
                snapshotPrice={pos.current_price}
                snapshotValue={pos.current_value_twd}
                snapshotPnl={pos.pnl_twd ?? pos.pnl}
                snapshotPnlPct={pos.pnl_pct}
                prices={prices}
                usdTwd={usdTwd}
              />
            ))}
            {crypto.map((pos) => (
              <Row
                key={pos.ticker}
                ticker={pos.ticker}
                name={pos.name}
                type={pos.type}
                market="CRYPTO"
                shares={pos.shares}
                costTwd={pos.cost_twd}
                snapshotPrice={pos.current_price}
                snapshotValue={pos.current_value_twd}
                snapshotPnl={pos.pnl_twd ?? pos.pnl}
                snapshotPnlPct={pos.pnl_pct}
                prices={prices}
                usdTwd={usdTwd}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
