import { NextRequest, NextResponse } from "next/server";

// Server-side Yahoo Finance v8 proxy — avoids browser CORS & cookie restrictions
export async function GET(req: NextRequest) {
  const symbol = req.nextUrl.searchParams.get("symbol");
  if (!symbol) {
    return NextResponse.json({ error: "missing symbol" }, { status: 400 });
  }

  try {
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?interval=1d&range=2d`;
    const res = await fetch(url, {
      cache: "no-store",
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        Accept: "application/json",
      },
    });

    if (!res.ok) {
      // Try query2 as fallback
      const url2 = `https://query2.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?interval=1d&range=2d`;
      const res2 = await fetch(url2, {
        cache: "no-store",
        headers: {
          "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
          Accept: "application/json",
        },
      });
      if (!res2.ok) {
        return NextResponse.json({ error: "upstream error" }, { status: res2.status });
      }
      const json2 = await res2.json();
      return NextResponse.json(extractQuote(json2));
    }

    const json = await res.json();
    return NextResponse.json(extractQuote(json));
  } catch {
    return NextResponse.json({ error: "fetch failed" }, { status: 502 });
  }
}

function extractQuote(json: unknown): {
  price: number | null;
  change: number | null;
  changePct: number | null;
  prev: number | null;
} {
  try {
    const meta = (json as { chart?: { result?: Array<{ meta?: Record<string, number> }> } })
      ?.chart?.result?.[0]?.meta;
    if (!meta) return { price: null, change: null, changePct: null, prev: null };
    const price = meta.regularMarketPrice ?? meta.previousClose ?? null;
    const prev  = meta.chartPreviousClose ?? meta.previousClose ?? null;
    if (price == null || prev == null) return { price: null, change: null, changePct: null, prev: null };
    const change    = price - prev;
    const changePct = prev !== 0 ? (change / prev) * 100 : 0;
    return { price, change, changePct, prev };
  } catch {
    return { price: null, change: null, changePct: null, prev: null };
  }
}
