"use client";

import { useEffect, useRef, useState } from "react";
import type { LivePrices } from "@/types/dashboard";
import type { Position, CryptoPosition } from "@/types/dashboard";

const REFRESH_MS = 60_000;

const BINANCE_MAP: Record<string, string> = {
  BTC: "BTCUSDT",
  ETH: "ETHUSDT",
  XRP: "XRPUSDT",
  SOL: "SOLUSDT",
};

async function fetchCryptoPrices(tickers: string[]): Promise<LivePrices> {
  const symbols = tickers.map((t) => BINANCE_MAP[t]).filter(Boolean);
  if (!symbols.length) return {};
  try {
    const encoded = encodeURIComponent(JSON.stringify(symbols));
    const r = await fetch(
      `https://api.binance.com/api/v3/ticker/price?symbols=${encoded}`
    );
    const arr: Array<{ symbol: string; price: string }> = await r.json();
    const result: LivePrices = {};
    for (const item of arr) {
      const tk = Object.keys(BINANCE_MAP).find(
        (k) => BINANCE_MAP[k] === item.symbol
      );
      if (tk) result[tk] = parseFloat(item.price);
    }
    return result;
  } catch {
    return {};
  }
}

async function fetchTWPrices(tickers: string[]): Promise<LivePrices> {
  if (!tickers.length) return {};
  const result: LivePrices = {};
  try {
    const ex = tickers.join("|");
    const url = `https://corsproxy.io/?https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=${ex}&json=1&delay=0`;
    const r = await fetch(url);
    const data = await r.json();
    for (const item of data?.msgArray ?? []) {
      const price = parseFloat(item.z !== "-" ? item.z : item.y);
      if (item.c && price > 0) result[item.c] = price;
    }
  } catch { /* non-blocking */ }
  return result;
}

async function fetchUSPrices(tickers: string[]): Promise<LivePrices> {
  if (!tickers.length) return {};
  const result: LivePrices = {};
  await Promise.all(
    tickers.map(async (ticker) => {
      try {
        const res = await fetch(`/api/quote?symbol=${ticker}`);
        if (res.ok) {
          const data = await res.json();
          if (data.c && data.c > 0) result[ticker] = data.c;
        }
      } catch { /* non-blocking */ }
    })
  );
  return result;
}

export function useLivePrices(
  positions: Position[],
  crypto: CryptoPosition[],
  usdTwd: number
): { prices: LivePrices; lastUpdated: Date | null } {
  const [prices, setPrices] = useState<LivePrices>({});
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const twTickers = positions
    .filter((p) => p.market === "TW")
    .map((p) => `tse_${p.ticker}.tw`);

  const usTickers = positions
    .filter((p) => p.market === "US")
    .map((p) => p.ticker);

  const cryptoTickers = crypto
    .filter((p) => p.type !== "contract")
    .map((p) => p.ticker);

  const refresh = async () => {
    const [twPrices, usPrices, cryptoPrices] = await Promise.all([
      fetchTWPrices(twTickers),
      fetchUSPrices(usTickers),
      fetchCryptoPrices(cryptoTickers),
    ]);
    // Crypto prices from Binance are in USD — convert to TWD for display
    const cryptoPricesTwd: LivePrices = {};
    for (const [tk, usdPrice] of Object.entries(cryptoPrices)) {
      cryptoPricesTwd[tk] = usdPrice * usdTwd;
    }
    setPrices({ ...twPrices, ...usPrices, ...cryptoPricesTwd });
    setLastUpdated(new Date());
  };

  useEffect(() => {
    refresh();
    timerRef.current = setInterval(refresh, REFRESH_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return { prices, lastUpdated };
}
