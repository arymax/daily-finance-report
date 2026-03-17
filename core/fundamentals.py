"""fundamentals.py — 抓取個股關鍵基本面指標並寫入 thesis 快照區段

追蹤指標（來源：yfinance .info）：
  PE（trailing / forward）、EPS（TTM / forward）、毛利率、
  營業利益率、營收成長率、市值、分析師目標均價與人數
"""

import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yfinance as yf

from .news import _yf_ticker

logger = logging.getLogger(__name__)

TST = timezone(timedelta(hours=8))

# yfinance 欄位 → 中文標籤（依序顯示）
_METRICS: list[tuple[str, str]] = [
    ("trailingPE",              "本益比（Trailing P/E）"),
    ("forwardPE",               "預期本益比（Forward P/E）"),
    ("trailingEps",             "EPS（TTM）"),
    ("forwardEps",              "預期 EPS"),
    ("priceToBook",             "股價淨值比（P/B）"),
    ("grossMargins",            "毛利率（最新季）"),
    ("operatingMargins",        "營業利益率"),
    ("revenueGrowth",           "營收成長率（YoY）"),
    ("freeCashflow",            "自由現金流（FCF，TTM）"),
    ("marketCap",               "市值"),
    ("targetMeanPrice",         "分析師目標均價"),
    ("numberOfAnalystOpinions", "追蹤分析師數"),
]

_PCT_FIELDS = {"grossMargins", "operatingMargins", "revenueGrowth"}
_CASH_FIELDS = {"freeCashflow"}

# thesis 快照區段的邊界標記
_SNAPSHOT_RE = re.compile(
    r"### 即時市場指標（自動更新）\n<!-- snapshot:start -->.*?<!-- snapshot:end -->",
    re.DOTALL,
)


# ── 數值格式化 ────────────────────────────────────────
def _fmt(key: str, val, currency: str) -> str:
    if key in _PCT_FIELDS:
        return f"{val * 100:.1f}%"
    if key in ("marketCap", "freeCashflow"):
        if currency == "TWD":
            return f"{val / 1e8:.1f} 億 TWD"
        abs_val = abs(val)
        sign = "-" if val < 0 else ""
        s = f"{sign}{abs_val / 1e9:.2f} B {currency}" if abs_val >= 1e9 else f"{sign}{abs_val / 1e6:.0f} M {currency}"
        return s
    if key in ("trailingEps", "forwardEps", "targetMeanPrice"):
        return f"{val:.2f} {currency}"
    if isinstance(val, float):
        return f"{val:.2f}"
    return str(val)


# ── 抓取季度延伸指標（毛利率趨勢 + EPS Beat/Miss）────────
def _fetch_extra_metrics(yf_sym: str) -> dict[str, str]:
    """
    抓取需要多期計算的進階指標，回傳 {中文標籤: 格式化數值}。
    任何子項目失敗都安全跳過，不影響主流程。
    """
    import pandas as pd
    extra: dict[str, str] = {}
    t = yf.Ticker(yf_sym)

    # 1. 毛利率趨勢（最近 4 季）
    try:
        qf = t.quarterly_financials
        if not qf.empty and "Gross Profit" in qf.index and "Total Revenue" in qf.index:
            segments = []
            for col in qf.columns[:4]:
                gp  = qf.loc["Gross Profit",  col]
                rev = qf.loc["Total Revenue", col]
                if pd.notna(gp) and pd.notna(rev) and rev != 0:
                    q = f"{col.year}-Q{(col.month - 1) // 3 + 1}"
                    segments.append(f"{q}:{gp / rev * 100:.1f}%")
            if segments:
                extra["毛利率趨勢（近4季）"] = " → ".join(segments)
    except Exception as e:
        logger.debug(f"  [extra] 毛利率趨勢抓取失敗：{e}")

    # 2. EPS Beat/Miss（最近 4 季，需要 lxml）
    try:
        ed = t.get_earnings_dates(limit=12)
        if ed is not None and not ed.empty:
            past = ed[ed["Reported EPS"].notna()].head(4)
            beats = []
            for _, row in past.iterrows():
                est  = row.get("EPS Estimate")
                rep  = row.get("Reported EPS")
                surp = row.get("Surprise(%)")
                if pd.notna(rep):
                    if pd.notna(est):
                        tag = "Beat" if rep >= est else "Miss"
                        surp_str = f"{surp:+.1f}%" if pd.notna(surp) else ""
                        beats.append(f"{tag}({surp_str})" if surp_str else tag)
                    else:
                        beats.append(f"EPS {rep:.2f}")
            if beats:
                extra["近4季 EPS vs 預期"] = " | ".join(beats)
    except Exception as e:
        logger.debug(f"  [extra] EPS beat/miss 抓取失敗：{e}")

    return extra


# ── 抓取基本面資料 ────────────────────────────────────
def fetch_fundamentals(tickers: list[tuple[str, str]]) -> dict[str, dict]:
    """
    抓取一組 (ticker, market) 的基本面指標。
    market = "TW" | "US"（不含 CRYPTO）
    回傳 {ticker: {中文標籤: 格式化數值}}
    """
    result: dict[str, dict] = {}
    for ticker, market in tickers:
        yf_sym = _yf_ticker(ticker, market)
        currency = "TWD" if market == "TW" else "USD"
        try:
            info = yf.Ticker(yf_sym).info
            data: dict[str, str] = {}
            for key, label in _METRICS:
                val = info.get(key)
                if val is not None:
                    data[label] = _fmt(key, val, currency)
            extra = _fetch_extra_metrics(yf_sym)
            data.update(extra)
            result[ticker] = data
            logger.info(f"  [fundamentals] {ticker}: {len(data)} 項指標")
        except Exception as e:
            logger.warning(f"  [fundamentals] {ticker} 抓取失敗：{e}")
    return result


# ── 建立快照區段文字 ──────────────────────────────────
def _build_snapshot_section(metrics: dict[str, str], update_time: str) -> str:
    if metrics:
        rows = "\n".join(f"| {label} | {val} |" for label, val in metrics.items())
        table = f"| 指標 | 數值 |\n|------|------|\n{rows}"
    else:
        table = "（資料不可取得）"

    return (
        f"### 即時市場指標（自動更新）\n"
        f"<!-- snapshot:start -->\n"
        f"*最後更新：{update_time}*\n\n"
        f"{table}\n"
        f"<!-- snapshot:end -->"
    )


# ── 寫入 thesis 快照 ──────────────────────────────────
def update_snapshot_in_thesis(thesis_path: Path, metrics: dict[str, str], update_time: str) -> None:
    """
    在 thesis_path 對應的 .md 檔案中，找到快照區段並整體替換；
    若不存在，插入在「### 主要風險」之前（或檔尾）。
    """
    content = thesis_path.read_text(encoding="utf-8")
    new_section = _build_snapshot_section(metrics, update_time)

    if _SNAPSHOT_RE.search(content):
        new_content = _SNAPSHOT_RE.sub(new_section, content)
    else:
        # 插入在「### 主要風險」之前
        anchor = "### 主要風險"
        if anchor in content:
            new_content = content.replace(anchor, f"{new_section}\n\n---\n\n{anchor}", 1)
        else:
            new_content = content.rstrip("\n") + f"\n\n---\n\n{new_section}\n"

    thesis_path.write_text(new_content, encoding="utf-8")
    logger.info(f"  [snapshot] 寫入：{thesis_path.name}")
