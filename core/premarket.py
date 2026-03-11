"""
core/premarket.py
盤前晨檢模組：抓取 5 大宏觀指標 + 建立 Gemini 判讀 prompt。
"""
import logging
from datetime import datetime, timezone, timedelta

import yfinance as yf

logger = logging.getLogger(__name__)

TST = timezone(timedelta(hours=8))

# 指標定義：symbol → (中文名稱, 單位, 解讀提示)
PREMARKET_INDICATORS = [
    ("ES=F",      "S&P 500 期貨（ES）",    "USD pts", "上漲偏多，下跌偏空"),
    ("NQ=F",      "NASDAQ 100 期貨（NQ）", "USD pts", "科技股方向指標"),
    ("^TNX",      "10年期美債殖利率",       "%",       "上升 → 成長股估值壓力；下降 → 資金轉向股市"),
    ("^VIX",      "VIX 恐慌指數",           "",        "<15 貪婪；15-25 正常；>25 恐慌；>30 極度恐慌"),
    ("DX-Y.NYB",  "美元指數（DXY）",        "",        "上升 → 外資撤離新興市場/台股壓力；下降 → 有利台股"),
]


def fetch_premarket_data() -> list[dict]:
    """
    抓取 5 大指標的最新收盤價與前日收盤，計算漲跌幅。
    回傳 list of dict，每個 dict 含：
        symbol, name, unit, hint,
        current, prev_close, change, change_pct,
        error（如抓取失敗）
    """
    results = []
    for symbol, name, unit, hint in PREMARKET_INDICATORS:
        entry: dict = {"symbol": symbol, "name": name, "unit": unit, "hint": hint}
        try:
            hist = yf.Ticker(symbol).history(period="5d", auto_adjust=True)
            if len(hist) < 2:
                raise ValueError("歷史資料不足 2 筆")
            prev_close = float(hist["Close"].iloc[-2])
            current    = float(hist["Close"].iloc[-1])
            change     = current - prev_close
            change_pct = (change / prev_close) * 100 if prev_close else 0.0
            entry.update({
                "current":    round(current, 4),
                "prev_close": round(prev_close, 4),
                "change":     round(change, 4),
                "change_pct": round(change_pct, 2),
            })
            direction = "▲" if change >= 0 else "▼"
            logger.info(
                f"  [{symbol}] {current:.4f} {direction}{abs(change_pct):.2f}%"
            )
        except Exception as e:
            entry["error"] = str(e)
            logger.warning(f"  [{symbol}] 抓取失敗：{e}")
        results.append(entry)
    return results


def _format_indicator_table(data: list[dict]) -> str:
    """將指標資料格式化為 Markdown 表格。"""
    lines = [
        "| 指標 | 現值 | 前日收盤 | 變化 | 漲跌幅 |",
        "|------|------|----------|------|--------|",
    ]
    for d in data:
        if "error" in d:
            lines.append(f"| {d['name']} | ❌ 抓取失敗 | — | — | — |")
        else:
            sign   = "▲" if d["change"] >= 0 else "▼"
            color  = "🟢" if d["change"] >= 0 else "🔴"
            unit   = d["unit"]
            lines.append(
                f"| {d['name']} "
                f"| {d['current']}{' ' + unit if unit else ''} "
                f"| {d['prev_close']}{' ' + unit if unit else ''} "
                f"| {sign}{abs(d['change']):.4f} "
                f"| {color} {sign}{abs(d['change_pct']):.2f}% |"
            )
    return "\n".join(lines)


def build_premarket_prompt(
    data: list[dict],
    market_overview: str,
    today: str,
    now_time: str,
) -> str:
    """建立 Gemini 盤前晨檢 prompt。"""
    table = _format_indicator_table(data)

    # 從 market_overview 擷取「事件」相關段落（前 2000 字已足夠）
    overview_excerpt = market_overview[:2500] if market_overview else "（無今日市場總覽）"

    hints_text = "\n".join(
        f"- **{d['name']}**：{d['hint']}"
        for d in data if "hint" in d
    )

    return f"""你是一位資深台美股投資人，正在進行美股開盤前的「5分鐘晨檢」。
現在時間：{now_time} TST，距美股開盤約 15 分鐘。

---

## 即時宏觀指標

{table}

### 指標解讀提示
{hints_text}

---

## 今日市場總覽摘要（來自早盤報告）

{overview_excerpt}

---

## 你的任務

根據以上 5 大指標與今日市場背景，輸出一份簡潔的盤前晨檢報告。

**輸出格式（嚴格遵守）：**

# 盤前晨檢 {today}

## 五大指標訊號解讀
（每個指標一行：現值 → 對市場的意涵，不超過 20 字）

## 今日重大事件
（條列今晚可能影響市場的事件，若無則填「無重大事件」）

## 綜合判斷

| 維度 | 結論 |
|------|------|
| 今日偏向 | 偏多 / 偏空 / 中性 |
| 操作傾向 | 進攻 / 防守 / 觀望 |
| 波動預期 | 低 / 中 / 高 |

## 一句話結論
（最多 30 字，直接說今天該怎麼做）

---

請保持精簡，整份報告不超過 300 字。以繁體中文輸出。"""
