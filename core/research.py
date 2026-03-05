"""research.py — 質化研究引擎

兩種模式：
  A. enrich（--enrich-thesis）：對現有 thesis 補充深度質化分析
  B. auto（Task 5）：從當日新聞識別新公司，自動建立 thesis
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════
# Mode A：補充現有 thesis 的質化深度
# ════════════════════════════════════════════════════

def build_enrich_prompt(
    ticker: str,
    name: str,
    market: str,
    current_thesis: str,
    news_articles: list[dict],
    fundamentals: dict,
    price: float | None,
    usd_twd: float,
    today: str,
) -> str:
    """
    補充現有 thesis 的深度質化分析。
    保留使用者手動編輯的策略/進場條件，只新增/強化質化章節。
    """
    currency = "TWD" if market == "TW" else "USD"
    price_str = f"{price:.2f} {currency}" if price else "（無法取得）"

    news_text = _format_news(news_articles)
    fund_text = _format_fundamentals(fundamentals)

    return f"""你是一位資深投資研究分析師，負責補充強化現有的投資 thesis 文件。

---

## 研究標的

- **代碼：** {ticker}
- **公司名：** {name}
- **市場：** {market}
- **今日股價：** {price_str}
- **補充日期：** {today}

---

## 即時量化數據（來源：yfinance）

{fund_text}

---

## 今日相關新聞

{news_text}
---

## 現有 Thesis 內容

{current_thesis}

---

## 你的任務

請在**保留所有現有內容**的前提下，對 thesis 進行深度質化補充：

**必須強化或新增的質化章節（若現有 thesis 已有充足內容則保留，不足則補充）：**

1. **核心業務**：公司到底賣什麼？具體產品 / 服務 / 解決方案？
2. **商業模式**：怎麼賣？收入結構（訂閱？專案制？硬體+服務？平台？）
3. **客戶輪廓**：賣給誰？典型客戶是誰？採購決策者是誰？
4. **競爭護城河**：客戶為什麼非買它不可？有無替代品？轉換成本？
5. **市場地位**：龍頭 / 老二 / 老三？市佔率？主要競爭對手？
6. **行業 KPI**：這個行業特有的健康度指標（如 SaaS 的 ARR/NRR、資安的 ARR 成長、半導體的出貨量/毛利率）？
7. **成長驅動力**：未來 2-3 年的核心成長引擎

**不可修改的部分：**
- 現有的「策略說明」、「進場條件」、「停損設定」（這些是使用者判斷）
- 現有的「持倉狀態」數字（成本、均價等）

**輸出格式：**
直接輸出完整的更新後 thesis Markdown 文件（保留現有所有章節，在適當位置新增/強化質化章節）。
不需要說明你做了什麼修改，直接輸出最終版本。"""


# ════════════════════════════════════════════════════
# Mode B：自動識別新公司並建立 thesis（Task 5）
# ════════════════════════════════════════════════════

def build_candidate_prompt(
    market_content: str,
    portfolio_content: str,
    existing_tickers: set[str],
    today: str,
    max_candidates: int = 3,
) -> str:
    existing_list = "、".join(sorted(existing_tickers)) if existing_tickers else "（無）"
    return f"""你是一位嚴謹的投資研究助理，負責從每日市場報告中識別值得深入研究的新標的。

今天是 {today}。

## 今日已生成的報告

### 持倉分析
{portfolio_content or "（未生成）"}

### 市場總覽
{market_content or "（未生成）"}

---

## 已有 thesis 的標的（請勿重複選入）

{existing_list}

---

## 你的任務

從今日報告中，識別最多 {max_candidates} 間值得深入研究的公司。

**選擇標準（依優先順序）：**
1. **財報發布**：今日報告提到有公司公布財報（不論超預期或不如預期），且該公司尚無 thesis
2. **板塊強勢代表股**：今日某板塊表現特別強勢，選 1-2 間最具代表性的龍頭股，且尚無 thesis
3. **重大事件**：分析師大幅調評、重要業務更新、新客戶 / 合約宣布

**排除條件：**
- 已在「已有 thesis 的標的」列表中的任何代碼
- ETF 或指數基金（只研究個股）

**輸出格式（嚴格遵守，每個候選一個區塊）：**

===CANDIDATE===
ticker: <代碼，如 NVDA 或 2330>
name: <公司全名>
market: <US 或 TW>
exchange: <NASDAQ / NYSE / 上市 / 上櫃 / 等>
reason: <一句話說明觸發事件 + 為什麼值得研究>
===END_CANDIDATE===

若今日報告沒有符合條件的研究標的，僅輸出：
NO_RESEARCH"""


def parse_candidates(response: str) -> list[dict]:
    if response.strip() == "NO_RESEARCH":
        return []
    pattern = r"===CANDIDATE===\s*(.*?)===END_CANDIDATE==="
    candidates = []
    for block in re.findall(pattern, response, re.DOTALL):
        candidate: dict[str, str] = {}
        for line in block.strip().splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                candidate[key.strip()] = val.strip()
        if candidate.get("ticker") and candidate.get("name"):
            candidates.append(candidate)
    return candidates


def build_research_prompt(
    ticker: str,
    name: str,
    market: str,
    reason: str,
    news_articles: list[dict],
    fundamentals: dict,
    price: float | None,
    usd_twd: float,
    today: str,
) -> str:
    """從零建立新公司的完整 thesis。"""
    currency = "TWD" if market == "TW" else "USD"
    price_str = f"{price:.2f} {currency}" if price else "（無法取得）"
    news_text = _format_news(news_articles)
    fund_text = _format_fundamentals(fundamentals)

    return f"""你是一位資深投資研究分析師，請對以下公司進行深度研究，輸出完整的投資 thesis 文件。

---

## 研究對象

- **代碼：** {ticker}
- **公司名：** {name}
- **市場：** {market}
- **今日股價：** {price_str}
- **研究日期：** {today}
- **研究觸發：** {reason}

---

## 即時量化數據（來源：yfinance）

{fund_text}

---

## 今日相關新聞

{news_text}
---

## 研究框架（請依序深入分析，質化分析是重點）

### 一、量化概覽（簡短）
- Revenue 及近期成長率
- EPS（GAAP / Non-GAAP 分開說明）、毛利率及趨勢
- PE / PS / PB 估值倍數，與同業比較

### 二、質化分析（重點，請詳細展開）
1. **核心業務**：這家公司到底賣什麼？具體產品 / 服務？
2. **商業模式**：怎麼賣？收入結構如何？
3. **客戶輪廓**：賣給誰？典型客戶？
4. **競爭護城河**：客戶為什麼非買它不可？有無替代品？轉換成本？
5. **市場地位**：龍頭 / 老二 / 老三？市佔率？主要競爭對手？
6. **行業 KPI**：行業特有健康度指標？公司在這些指標上的表現？
7. **成長驅動力**：未來 2-3 年的核心成長引擎？
8. **主要風險**：最核心的 2-3 個結構性風險

---

## 輸出格式（直接輸出 Markdown，不需要前言）

# {name}（{ticker}）｜研究報告

**產業：** [填入]
**市場：** {market}
**主題：** [一句話總結投資主題]
**研究日期：** {today}
**研究觸發：** {reason}

---

### 核心業務與商業模式

[詳細描述：賣什麼、怎麼賣、賣給誰、收入結構]

---

### 競爭護城河與市場地位

[護城河分析、市佔率、主要競爭對手]

---

### 行業 KPI 與公司表現

[行業特有 KPI + 公司在這些指標上的具體數據]

---

### 成長驅動力

[未來 2-3 年的核心成長引擎]

---

### 財務數據概覽

| 指標 | 數值 |
|------|------|
[量化數據：Revenue、EPS、毛利率、PE/PS 等]

---

### 主要風險

[2-3 個核心結構性風險]

---

### 買入邏輯初步評估

> [這間公司是否值得深入追蹤？有無潛在進場邏輯？]

---

### 觀察清單建議

- **是否加入 watchlist：** [是 / 暫不 / 需更多資訊]
- **優先級：** [1-5，1 最高]
- **建議進場條件：** [技術面 + 基本面觸發條件]
"""


def save_research_thesis(content: str, ticker: str, thesis_dir: Path) -> Path:
    """儲存研究結果為 thesis/TICKER.md，回傳路徑。"""
    target = thesis_dir / f"{ticker}.md"
    target.write_text(content.strip() + "\n", encoding="utf-8")
    return target


# ── 共用格式化工具 ────────────────────────────────────
def _format_news(articles: list[dict]) -> str:
    if not articles:
        return "（無可用新聞）"
    lines = []
    for i, art in enumerate(articles, 1):
        title = art.get("title", "")
        body  = art.get("body", art.get("summary", ""))[:600]
        pub   = art.get("published", "")
        lines.append(f"[{i}] {title}\n{pub}\n{body}\n")
    return "\n".join(lines)


def _format_fundamentals(fundamentals: dict) -> str:
    if not fundamentals:
        return "（資料不可取得）"
    return "\n".join(f"  {k}: {v}" for k, v in fundamentals.items())
