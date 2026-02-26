"""
memory.py — 跨日記憶系統

每日執行完畢後，用 Claude 從當日報告提取結構化摘要，
存為 memory/YYYYMMDD.md。

次日執行時，自動載入最近 N 天摘要注入 prompt，
讓 Claude 的分析具備歷史連貫性。
"""

import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

TST = timezone(timedelta(hours=8))
logger = logging.getLogger(__name__)

_SUMMARY_PROMPT = """
你是一個財務助理。請從以下今日投資分析報告中，提取關鍵資訊，
輸出一份給明天使用的「記憶摘要」（繁體中文，總長度控制在 600 字以內）。

請嚴格依照以下格式輸出（保留各 ## 標題，不要加其他文字）：

## 今日市場重點
（2-3 句：指數表現、重要事件、整體氛圍）

## 各持倉狀態與操作結論
（每個持倉一行，格式：[代碼] 建議=XX，理由簡述）

## 觀察清單最新狀態
（每個 watchlist 標的一行，格式：[代碼] 進場條件達成情況）

## 下次需特別關注
（條列 3-5 項，格式：[日期/條件] → 應採取的動作）

---
以下是今日報告：

### 持倉分析報告
{portfolio_report}

### 市場總覽報告
{market_report}
"""


def load_context(memory_dir: Path, days: int = 5) -> str:
    """
    讀取最近 N 天的記憶摘要，合併為 context 字串。

    回傳格式：
        ## 歷史記憶（近 N 天）

        ### 2026-02-25
        ...

        ---

        ### 2026-02-24
        ...

    若 memory/ 目錄不存在或無任何摘要，安全回傳空字串（不報錯）。
    """
    if not memory_dir.exists():
        return ""

    today = datetime.now(TST).date()
    summaries = []

    for i in range(1, days + 1):
        target_date = today - timedelta(days=i)
        filename = memory_dir / f"{target_date.strftime('%Y%m%d')}.md"
        if filename.exists():
            content = filename.read_text(encoding="utf-8").strip()
            if content:
                summaries.append(f"### {target_date.strftime('%Y-%m-%d')}\n{content}")

    if not summaries:
        return ""

    header = f"## 歷史記憶（近 {len(summaries)} 天）\n\n"
    body   = "\n\n---\n\n".join(summaries)
    logger.info(f"  [memory] 載入 {len(summaries)} 天記憶（{len(header + body)} 字元）")
    return header + body


def generate_summary(portfolio_report: str, market_report: str) -> str:
    """
    建立「記憶摘要提取」的 Claude prompt，由 main.py 呼叫 call_claude() 執行。

    各報告截取前 3000 字元，避免 prompt 過長。
    回傳值為完整 prompt 字串（非最終摘要）。
    """
    p_report = (portfolio_report or "（本次未生成持倉分析）")[:3000]
    m_report = (market_report   or "（本次未生成市場總覽）")[:3000]
    return _SUMMARY_PROMPT.format(
        portfolio_report=p_report,
        market_report=m_report,
    )


def save_summary(summary: str, memory_dir: Path) -> Path:
    """
    將摘要存為 memory/YYYYMMDD.md。
    若 memory/ 目錄不存在則自動建立。
    回傳儲存路徑。
    """
    memory_dir.mkdir(parents=True, exist_ok=True)
    today    = datetime.now(TST).strftime("%Y%m%d")
    filepath = memory_dir / f"{today}.md"
    filepath.write_text(summary.strip(), encoding="utf-8")
    logger.info(f"✅ 記憶摘要儲存：{filepath.name}")
    return filepath
