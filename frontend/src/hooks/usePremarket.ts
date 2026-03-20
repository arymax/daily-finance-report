"use client";

import { useEffect, useRef, useState } from "react";

export interface QuoteData {
  symbol: string;
  price: number | null;
  change: number | null;     // absolute change
  changePct: number | null;  // percent change
  prev: number | null;
  label: string;
  error?: boolean;
}

const REFRESH_MS = 60_000;

// Yahoo Finance via server-side Next.js proxy (/api/yf-quote)
async function fetchYahooQuote(symbol: string): Promise<{ price: number; change: number; changePct: number; prev: number } | null> {
  try {
    const res = await fetch(
      `/api/yf-quote?symbol=${encodeURIComponent(symbol)}`,
      { signal: AbortSignal.timeout(10000) }
    );
    if (!res.ok) return null;
    const data = await res.json();
    if (data.price == null) return null;
    return { price: data.price, change: data.change, changePct: data.changePct, prev: data.prev };
  } catch {
    return null;
  }
}

async function batchFetch(symbols: string[]): Promise<Record<string, QuoteData>> {
  const results = await Promise.allSettled(
    symbols.map((sym) => fetchYahooQuote(sym))
  );
  const out: Record<string, QuoteData> = {};
  results.forEach((r, i) => {
    const sym = symbols[i];
    if (r.status === "fulfilled" && r.value) {
      out[sym] = {
        symbol: sym,
        price: r.value.price,
        change: r.value.change,
        changePct: r.value.changePct,
        prev: r.value.prev,
        label: sym,
      };
    } else {
      out[sym] = { symbol: sym, price: null, change: null, changePct: null, prev: null, label: sym, error: true };
    }
  });
  return out;
}

// All symbols to track
export const PREMARKET_GROUPS = [
  {
    title: "指數期貨",
    color: "text-violet-400",
    items: [
      { symbol: "ES=F",  label: "S&P 500 期貨" },
      { symbol: "NQ=F",  label: "Nasdaq 100 期貨" },
      { symbol: "YM=F",  label: "道瓊期貨" },
      { symbol: "RTY=F", label: "Russell 2000" },
    ],
  },
  {
    title: "恐慌指標",
    color: "text-red-400",
    items: [
      { symbol: "^VIX",  label: "VIX 恐慌指數" },
      { symbol: "^VVIX", label: "VVIX" },
    ],
  },
  {
    title: "債券殖利率",
    color: "text-cyan-400",
    items: [
      { symbol: "^IRX", label: "3個月 T-Bill" },
      { symbol: "^FVX", label: "5年期殖利率" },
      { symbol: "^TNX", label: "10年期殖利率" },
      { symbol: "^TYX", label: "30年期殖利率" },
    ],
  },
  {
    title: "美元與商品",
    color: "text-amber-400",
    items: [
      { symbol: "DX-Y.NYB", label: "DXY 美元指數" },
      { symbol: "GC=F",     label: "黃金" },
      { symbol: "CL=F",     label: "WTI 原油" },
      { symbol: "HG=F",     label: "銅（景氣指標）" },
    ],
  },
  {
    title: "隔夜市場",
    color: "text-sky-400",
    items: [
      { symbol: "^N225",  label: "日經 225" },
      { symbol: "^HSI",   label: "恆生指數" },
      { symbol: "^GDAXI", label: "德國 DAX" },
      { symbol: "^FTSE",  label: "英國 FTSE" },
    ],
  },
] as const;

const ALL_SYMBOLS = PREMARKET_GROUPS.flatMap((g) => g.items.map((i) => i.symbol));

export function usePremarket() {
  const [quotes, setQuotes]         = useState<Record<string, QuoteData>>({});
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [loading, setLoading]       = useState(true);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = async () => {
    const data = await batchFetch(ALL_SYMBOLS);
    // Attach labels from config
    PREMARKET_GROUPS.forEach((g) => {
      g.items.forEach((item) => {
        if (data[item.symbol]) data[item.symbol].label = item.label;
      });
    });
    setQuotes(data);
    setLastUpdated(new Date());
    setLoading(false);
  };

  useEffect(() => {
    refresh();
    timerRef.current = setInterval(refresh, REFRESH_MS);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return { quotes, lastUpdated, loading };
}
