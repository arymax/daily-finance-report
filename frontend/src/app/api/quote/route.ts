import { NextRequest, NextResponse } from "next/server";

const FINNHUB_KEY = process.env.FINNHUB_API_KEY ?? "";

export async function GET(req: NextRequest) {
  const symbol = req.nextUrl.searchParams.get("symbol");
  if (!symbol) {
    return NextResponse.json({ error: "missing symbol" }, { status: 400 });
  }
  if (!FINNHUB_KEY) {
    return NextResponse.json({ error: "no api key" }, { status: 503 });
  }

  try {
    const res = await fetch(
      `https://finnhub.io/api/v1/quote?symbol=${encodeURIComponent(symbol)}&token=${FINNHUB_KEY}`,
      { cache: "no-store" }
    );
    if (!res.ok) {
      return NextResponse.json({ error: "upstream error" }, { status: res.status });
    }
    const data = await res.json();
    // Return only the current price to minimise payload
    return NextResponse.json({ c: data.c, t: data.t });
  } catch {
    return NextResponse.json({ error: "fetch failed" }, { status: 502 });
  }
}
