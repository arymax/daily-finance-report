import { NextRequest, NextResponse } from "next/server";

const GEMINI_KEY = process.env.GEMINI_API_KEY ?? "";
const GEMINI_MODEL = "gemini-2.5-flash";

interface QuoteSnapshot {
  symbol: string;
  label: string;
  price: number | null;
  change: number | null;
  changePct: number | null;
}

function buildPrompt(quotes: QuoteSnapshot[], date: string): string {
  const fmt = (q: QuoteSnapshot | undefined) =>
    q?.price != null
      ? `${q.price.toFixed(q.price >= 100 ? 2 : 4)} (${q.changePct != null ? (q.changePct >= 0 ? "+" : "") + q.changePct.toFixed(2) + "%" : "—"})`
      : "N/A";

  const get = (sym: string) => quotes.find((q) => q.symbol === sym);

  const vix    = get("^VIX");
  const vvix   = get("^VVIX");
  const irx    = get("^IRX");
  const fvx    = get("^FVX");
  const tnx    = get("^TNX");
  const tyx    = get("^TYX");
  const esf    = get("ES=F");
  const nqf    = get("NQ=F");
  const ymf    = get("YM=F");
  const rtyf   = get("RTY=F");
  const dxy    = get("DX-Y.NYB");
  const gold   = get("GC=F");
  const oil    = get("CL=F");
  const copper = get("HG=F");
  const n225   = get("^N225");
  const hsi    = get("^HSI");
  const dax    = get("^GDAXI");
  const ftse   = get("^FTSE");

  const irxVal = irx?.price ?? null;
  const tnxVal = tnx?.price ?? null;
  const tyxVal = tyx?.price ?? null;
  const fvxVal = fvx?.price ?? null;
  const spread2s10s = irxVal != null && tnxVal != null ? (tnxVal - irxVal).toFixed(3) : "N/A";
  const spread5s30s = fvxVal != null && tyxVal != null ? (tyxVal - fvxVal).toFixed(3) : "N/A";

  return `你是一位資深美股盤前分析師。以下是今日（${date}）美股開盤前的即時市場數據，請以繁體中文撰寫一份結構化盤前分析報告。

---

## 即時市場數據

### 指數期貨
- S&P 500 期貨 (ES=F)：${fmt(esf)}
- Nasdaq 100 期貨 (NQ=F)：${fmt(nqf)}
- 道瓊期貨 (YM=F)：${fmt(ymf)}
- Russell 2000 (RTY=F)：${fmt(rtyf)}

### 恐慌指標
- VIX：${fmt(vix)}
- VVIX：${fmt(vvix)}

### 債券殖利率
- 3個月 T-Bill：${fmt(irx)}
- 5年期：${fmt(fvx)}
- 10年期：${fmt(tnx)}
- 30年期：${fmt(tyx)}
- **2s10s 利差：${spread2s10s}%**（負值 = 殖利率倒掛）
- **5s30s 利差：${spread5s30s}%**

### 美元與商品
- DXY 美元指數：${fmt(dxy)}
- 黃金：${fmt(gold)}
- WTI 原油：${fmt(oil)}
- 銅（景氣指標）：${fmt(copper)}

### 隔夜亞歐市場
- 日經 225：${fmt(n225)}
- 恆生指數：${fmt(hsi)}
- 德國 DAX：${fmt(dax)}
- 英國 FTSE：${fmt(ftse)}

---

請依以下架構撰寫報告（使用 Markdown 格式）：

## 一、市場情緒快照
簡要評估目前整體風險偏好（Risk-on / Risk-off / 中性），給出 1-3 句核心判斷。

## 二、期貨市場分析
分析四大指數期貨的相對強弱（ES vs NQ vs YM vs RTY），判斷哪些板塊領漲/領跌，推斷今日開盤可能的板塊輪動方向。

## 三、殖利率曲線解讀
- 現況：是否倒掛？倒掛程度？
- 2s10s 與 5s30s 利差的含義（對股市流動性、銀行股、成長股的影響）
- 短端 vs 長端的變動（升息預期 vs 衰退擔憂）

## 四、跨資產信號
整合美元（DXY）、黃金、原油、銅的多空信號，分析彼此是否一致（例如：避險需求 / 通膨預期 / 景氣方向）。

## 五、亞歐市場傳導
亞洲與歐洲主要指數的表現，判斷外資情緒和美股可能的傳導方向。

## 六、盤前操作建議
根據以上分析，給出今日開盤的 2-3 條具體觀察重點或操作提示（含需要警惕的風險）。

---
*分析時間：${date}　資料來源：Yahoo Finance 即時報價*`;
}

export async function POST(req: NextRequest) {
  if (!GEMINI_KEY) {
    return NextResponse.json({ error: "GEMINI_API_KEY not configured" }, { status: 503 });
  }

  let body: { quotes?: QuoteSnapshot[]; date?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid JSON" }, { status: 400 });
  }

  const quotes = body.quotes ?? [];
  const date   = body.date ?? new Date().toLocaleDateString("zh-TW");

  try {
    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${GEMINI_KEY}`,
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts: [{ text: buildPrompt(quotes, date) }] }],
          generationConfig: { maxOutputTokens: 8192, temperature: 0.4 },
        }),
      }
    );

    if (!res.ok) {
      const err = await res.text();
      return NextResponse.json({ error: `Gemini error: ${err}` }, { status: res.status });
    }

    const data = await res.json();
    // Gemini 2.5 Flash may return multiple parts (thinking + response)
    // Collect all non-thought text parts
    const parts: Array<{ text?: string; thought?: boolean }> =
      data?.candidates?.[0]?.content?.parts ?? [];
    const text: string = parts
      .filter((p) => !p.thought && p.text)
      .map((p) => p.text)
      .join("") ?? "";
    return NextResponse.json({ report: text });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 502 });
  }
}
