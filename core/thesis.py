"""thesis.py — 讀取、更新 thesis/*.md 投資論點檔案"""

import json
import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

TST = timezone(timedelta(hours=8))


def load_all_theses(thesis_dir: Path) -> dict[str, str]:
    """遞迴讀取 thesis_dir 下所有 .md 檔案，回傳 {stem: content}，跳過 README。"""
    _SKIP = {"README"}
    result = {}
    for p in sorted(thesis_dir.rglob("*.md")):
        if p.stem in _SKIP:
            continue
        result[p.stem] = p.read_text(encoding="utf-8")
    return result


def find_thesis(thesis_dir: Path, ticker: str) -> Path | None:
    """遞迴搜尋 thesis_dir 中 ticker 對應的 .md 檔案，找不到回傳 None。"""
    matches = [p for p in thesis_dir.rglob(f"{ticker}.md") if p.stem != "README"]
    return matches[0] if matches else None


# 可被 Task 4 更新的 thesis 區塊（靜態分析區塊不在更新範圍內）
_UPDATABLE_SECTIONS = ["買入邏輯初步評估", "近期催化劑", "觀察清單建議"]


def extract_updatable_sections(content: str) -> str:
    """
    從 thesis 全文提取：檔案 header + 可更新區塊（買入邏輯、催化劑、觀察清單建議）。
    靜態分析區塊（核心業務、競爭護城河、行業KPI、成長驅動力、主要風險）不納入。
    節省 Task 4 約 60-70% 的 input tokens。
    """
    parts = []

    # 1. 檔案 header（第一個 --- 之前）
    sep_idx = content.find("\n---\n")
    header = content[:sep_idx].strip() if sep_idx > 0 else content[:400].strip()
    parts.append(header)

    # 2. 可更新 sections
    for sec_name in _UPDATABLE_SECTIONS:
        pattern = rf"(### {re.escape(sec_name)}\n.*?)(?=\n---\n|\Z)"
        m = re.search(pattern, content, re.DOTALL)
        if m:
            parts.append(m.group(1).strip())

    return "\n\n---\n\n".join(parts)


def build_update_prompt(
    theses: dict[str, str],
    portfolio_content: str,
    market_content: str,
    session: str = "morning",
) -> str:
    """建立 thesis 自動更新 prompt（section-diff 模式，只傳可更新區塊節省 tokens）。"""
    thesis_text = ""
    for name, content in theses.items():
        extracted = extract_updatable_sections(content)
        thesis_text += f"=== {name}.md（僅可更新區塊）===\n{extracted}\n\n"

    today = datetime.now(TST).strftime("%Y-%m-%d")
    session_label = "早盤" if session == "morning" else "收盤"

    # 報告內容截取前 2000 字元，保留事實密度最高的部分
    p_report = (portfolio_content or "（本次未生成）")[:2000]
    m_report = (market_content   or "（本次未生成）")[:2000]

    updatable_list = "、".join(_UPDATABLE_SECTIONS)

    return f"""你是一位嚴謹的投資分析師助理，負責維護投資論點（thesis）文件的準確性。
今天是 {today}（{session_label}）。

## 今日已生成的報告摘要（前 2000 字）

### 持倉分析報告
{p_report}

### 市場總覽報告
{m_report}

---

## 現有 Thesis 可更新區塊

（注意：靜態分析區塊（核心業務、競爭護城河、行業KPI、成長驅動力、主要風險、財務數據）
**不在本次更新範圍**，請勿輸出這些區塊）

可更新區塊：**{updatable_list}**

{thesis_text}
---

## 你的任務

仔細比對今日報告內容與 thesis 可更新區塊，找出**需要更新的內容**。

**事實更新原則：**
- 只更新有新的、具體、可驗證的事實（如財報數字、進場條件確認、管理層變動結果）
- 不更新觀點、策略判斷
- 近期催化劑表格：若事件已過且有結果，在事件前加「✅」或更新意義欄
- 若某個 thesis 完全不需要更新，就不要輸出它

**重大質化事件警報（⚠️）：**
若偵測到以下類型事件，輸出警報區塊：
- 公司宣布重大收購 / 被收購
- 核心業務方向轉型
- 強力新競爭對手進入
- 創辦人 / CEO 離職
- 重大監管行動影響商業模式
- 重大客戶流失

**輸出格式（嚴格遵守）：**

對每個需要更新的 thesis，輸出 THESIS 區塊，內部每個變動區塊用 SECTION 標記：

===THESIS: <檔名（不含 .md）>===
===SECTION: <區塊名稱，如「近期催化劑」>===
（此區塊更新後的完整內容，包含 ### 標題行）
===END_SECTION===
===END_THESIS===

警報格式：
===ALERT: <TICKER>===
（描述事件，說明為什麼需要使用者手動重新評估）
===END_ALERT===

若今日無任何 thesis 需要更新，且無警報，僅輸出：
NO_UPDATE"""


def parse_and_save(
    response: str, thesis_dir: Path
) -> tuple[list[str], dict[str, str]]:
    """
    解析 Claude 回傳的 THESIS 與 ALERT 區塊。
    支援兩種 THESIS 格式：
      1. Section-diff 模式（新）：THESIS 內含 SECTION 子區塊，只更新指定區塊
      2. Full-thesis 模式（舊，向後相容）：THESIS 內含完整 .md 內容

    回傳 (updated_list, alerts_dict)。
    """
    updated: list[str] = []
    alerts: dict[str, str] = {}

    if response.strip() == "NO_UPDATE":
        return updated, alerts

    today = datetime.now(TST).strftime("%Y-%m-%d")

    # 解析 THESIS 區塊
    thesis_pattern = r"===THESIS:\s*(\S+)===\n([\s\S]*?)===END_THESIS==="
    for name, thesis_body in re.findall(thesis_pattern, response):
        name = name.strip()
        target = find_thesis(thesis_dir, name)
        if target is None:
            logger.warning(f"  Thesis 更新略過（檔案不存在）：{name}.md")
            continue

        # 判斷是 section-diff 模式還是 full-thesis 模式
        section_pattern = r"===SECTION:\s*(.+?)===\n([\s\S]*?)===END_SECTION==="
        sections = re.findall(section_pattern, thesis_body)

        if sections:
            # Section-diff 模式：只替換指定區塊，其餘內容保持不變
            original = target.read_text(encoding="utf-8")
            text = original
            for sec_name, sec_content in sections:
                sec_name = sec_name.strip()
                sec_content = sec_content.strip()
                # 替換 ### SectionName 到下一個 --- 或 EOF
                pat = rf"(### {re.escape(sec_name)}\n).*?(?=\n---\n|\Z)"
                repl = rf"\g<1>{sec_content}"
                text, n = re.subn(pat, repl, text, flags=re.DOTALL)
                if n == 0:
                    logger.warning(f"  Section 未找到，略過：{name}.md / {sec_name}")
            # 更新 last_updated 標記
            text = re.sub(r"\n<!-- last_updated: \d{4}-\d{2}-\d{2} -->", "", text)
            text = text.rstrip() + f"\n<!-- last_updated: {today} -->\n"
        else:
            # Full-thesis 模式（向後相容）
            text = thesis_body.strip()
            text = re.sub(r"\n<!-- last_updated: \d{4}-\d{2}-\d{2} -->", "", text)
            text += f"\n<!-- last_updated: {today} -->\n"

        target.write_text(text, encoding="utf-8")
        logger.info(f"  Thesis 更新：{name}.md")
        updated.append(name)

    # 解析 ALERT 區塊
    alert_pattern = r"===ALERT:\s*(\S+)===\n([\s\S]*?)===END_ALERT==="
    for ticker, text in re.findall(alert_pattern, response):
        alerts[ticker.strip()] = text.strip()

    return updated, alerts


def parse_watchlist_suggestion(content: str, ticker: str) -> dict | None:
    """
    解析 thesis .md 中的「觀察清單建議」區塊。
    若優先級為 1 且建議加入 watchlist，回傳可加入 portfolio.json 的 watchlist entry dict。
    否則回傳 None。
    """
    # 判斷是否建議加入 watchlist
    watchlist_match = re.search(r"是否加入\s*watchlist[：:][^\n]*", content)
    if not watchlist_match:
        return None
    if "是" not in watchlist_match.group(0):
        return None

    # 判斷優先級
    priority_match = re.search(r"優先級[：:][^\d]*(\d+)", content)
    if not priority_match or int(priority_match.group(1)) != 1:
        return None

    # 解析公司名（# 公司名（TICKER）｜...）
    name_match = re.search(r"^#\s+(.+?)(?:（" + re.escape(ticker) + r"）|\(" + re.escape(ticker) + r"\))", content, re.MULTILINE)
    name = name_match.group(1).strip() if name_match else ticker

    # 解析市場
    market_match = re.search(r"\*\*市場[：:]\*\*\s*(\S+)", content)
    market = market_match.group(1).strip() if market_match else "US"

    # 解析產業
    sector_match = re.search(r"\*\*產業[：:]\*\*\s*(.+)", content)
    sector = sector_match.group(1).strip() if sector_match else ""

    # 解析主題
    theme_match = re.search(r"\*\*主題[：:]\*\*\s*(.+)", content)
    theme = theme_match.group(1).strip() if theme_match else ""

    # 解析研究觸發（作為 watch_reason）
    trigger_match = re.search(r"\*\*研究觸發[：:]\*\*\s*(.+)", content)
    watch_reason = trigger_match.group(1).strip() if trigger_match else theme

    # 解析優先級理由
    priority_reason_match = re.search(r"優先級理由[：:]\*{0,2}\s*(.+?)(?=\n-|\Z)", content, re.DOTALL)
    if priority_reason_match:
        priority_reason = " ".join(priority_reason_match.group(1).strip().splitlines()).strip()
    else:
        priority_reason = ""

    # 解析對齊議題（themes）
    themes_match = re.search(r"對齊議題[：:]\*{0,2}\s*(.+)", content)
    if themes_match:
        raw_themes = themes_match.group(1).strip().strip("*").strip()
        if raw_themes in ("無", "—", "-", ""):
            themes: list[str] = []
        else:
            themes = [t.strip() for t in re.split(r"[/／、,，]", raw_themes) if t.strip()]
    else:
        themes = []

    # 解析進場條件
    entry_match = re.search(r"建議進場條件[：:](.+?)(?=\n###|\Z)", content, re.DOTALL)
    if entry_match:
        raw = entry_match.group(1).strip()
        entry_condition = " ".join(
            line.strip().lstrip("- ").strip()
            for line in raw.splitlines()
            if line.strip() and line.strip() not in ("**建議進場條件：**",)
        )
    else:
        entry_condition = ""

    # exchange 預設（US → NASDAQ，TW → 上市）
    exchange = "NASDAQ" if market == "US" else "上市"

    entry: dict = {
        "ticker": ticker,
        "name": name,
        "exchange": exchange,
        "market": market,
        "sector": sector,
        "theme": theme,
        "priority": 1,
        "watch_reason": watch_reason,
        "entry_condition": entry_condition,
        "key_metrics": {
            "52w_high_usd": 0,
            "decline_from_high": 0,
        },
        "note": "自動從 thesis 優先級 1 同步加入，請手動更新 key_metrics（52w_high_usd / decline_from_high）",
    }
    if priority_reason:
        entry["priority_reason"] = priority_reason
    if themes:
        entry["themes"] = themes
    return entry


def sync_priority1_watchlist(thesis_dir: Path, portfolio_path: Path) -> list[str]:
    """
    掃描所有 thesis .md 檔案，將優先級 1 且建議加入 watchlist 的標的
    自動寫入 portfolio.json（若尚未存在於 watchlist 或任何持倉中）。
    回傳新增的 ticker 列表。
    """
    with open(portfolio_path, "r", encoding="utf-8") as f:
        portfolio = json.load(f)

    # 已在任何持倉或 watchlist 的 ticker 不重複加入
    held = {
        pos["ticker"]
        for section in ("long_term", "tactical")
        for pos in portfolio.get(section, {}).get("positions", [])
    }
    existing = {w["ticker"] for w in portfolio.get("watchlist", [])} | held
    added: list[str] = []

    for thesis_path in sorted(thesis_dir.rglob("*.md")):
        if thesis_path.stem == "README":
            continue
        ticker = thesis_path.stem
        if ticker in existing:
            continue
        content = thesis_path.read_text(encoding="utf-8")
        entry = parse_watchlist_suggestion(content, ticker)
        if entry is not None:
            portfolio["watchlist"].append(entry)
            existing.add(ticker)
            added.append(ticker)
            logger.info(f"  [watchlist] 自動加入優先級 1：{ticker}")

    if added:
        with open(portfolio_path, "w", encoding="utf-8") as f:
            json.dump(portfolio, f, ensure_ascii=False, indent=2)
        logger.info(f"  [watchlist] portfolio.json 已更新，新增 {len(added)} 個標的：{added}")

    return added


def build_watchlist_reeval_prompt(
    watchlist: list[dict],
    news_by_ticker: dict[str, list[dict]],
    prices: dict[str, float],
    usd_twd: float,
    today: str,
) -> str:
    """
    建立 watchlist 動態重評 prompt。
    讓 Claude 根據最新股價、跌幅、新聞重新評估每個標的的優先級。
    """
    lines = [
        f"你是投資研究助理。今天是 {today}，請根據以下最新資訊重新評估 watchlist 各標的的優先級。",
        "",
        "## 優先級評分標準",
        "- **1**：護城河強 ＋ 估值距 52 週高點跌幅 >25% 或 Forward P/E 明顯低於同業 ＋ 有具體近期市場議題對齊",
        "- **2**：護城河強但估值合理，或護城河中等但估值明顯低估",
        "- **3**：值得追蹤，但進場條件尚未成熟",
        "- **4**：敘事或基本面仍需更多季度驗證",
        "- **5**：早期觀察，風險高或能見度低",
        "",
        "## 各標的現況",
        "",
    ]

    for w in watchlist:
        ticker = w["ticker"]
        market = w.get("market", "US")
        currency = "TWD" if market == "TW" else "USD"

        # 股價與跌幅
        price = prices.get(ticker)
        price_str = f"{price:.2f} {currency}" if price else "（無法取得）"
        km = w.get("key_metrics", {})
        high = km.get("52w_high_usd", 0)
        decline = km.get("decline_from_high", 0)
        decline_str = f"{decline * 100:.1f}%" if decline else "（未知）"

        lines += [f"### {w['name']}（{ticker}）　現優先級：{w['priority']}"]
        lines += [f"- 當前股價：{price_str}　52 週高點：{high}　距高點：{decline_str}"]
        if w.get("priority_reason"):
            lines += [f"- 原始優先級理由：{w['priority_reason'][:120]}"]
        if w.get("themes"):
            lines += [f"- 對齊議題：{' / '.join(w['themes'])}"]
        if w.get("entry_condition"):
            lines += [f"- 進場條件：{w['entry_condition'][:120]}"]

        news = news_by_ticker.get(ticker, [])
        if news:
            lines += ["- 近期新聞："]
            for a in news[:3]:
                lines += [f"  - `{a['time']}` {a['title']}"]
        else:
            lines += ["- 近期新聞：無"]
        lines += [""]

    lines += [
        "---",
        "",
        "## 輸出格式（嚴格遵守）",
        "",
        "對每個標的輸出一個區塊。若優先級無需變動，`changed` 填 false，`reason` 可省略。",
        "只要有任何一個標的需要輸出，就必須輸出所有標的（方便系統完整解析）。",
        "若所有標的均無變動，只輸出：NO_CHANGE",
        "",
        "===REEVAL: <TICKER>===",
        "priority: <新優先級，整數>",
        "changed: <true / false>",
        "reason: <若 changed=true，說明變動原因；否則省略此行>",
        "===END_REEVAL===",
    ]
    return "\n".join(lines)


def apply_reeval_results(
    response: str,
    portfolio_path: Path,
) -> list[dict]:
    """
    解析 Claude 重評結果，更新 portfolio.json 中 watchlist 的優先級。
    回傳有變動的標的清單：[{"ticker": ..., "old": ..., "new": ..., "reason": ...}]
    """
    if response.strip() == "NO_CHANGE":
        return []

    pattern = r"===REEVAL:\s*(\S+)===\s*\npriority:\s*(\d+)\s*\nchanged:\s*(true|false)(?:\s*\nreason:\s*(.+?))?\s*===END_REEVAL==="
    results: dict[str, dict] = {}
    for ticker, priority, changed, reason in re.findall(pattern, response, re.DOTALL):
        results[ticker.strip()] = {
            "priority": int(priority),
            "changed": changed.strip() == "true",
            "reason": (reason or "").strip(),
        }

    if not results:
        return []

    with open(portfolio_path, "r", encoding="utf-8") as f:
        portfolio = json.load(f)

    changes: list[dict] = []
    for w in portfolio.get("watchlist", []):
        ticker = w["ticker"]
        if ticker not in results:
            continue
        r = results[ticker]
        if r["changed"] and r["priority"] != w["priority"]:
            changes.append({
                "ticker": ticker,
                "old": w["priority"],
                "new": r["priority"],
                "reason": r["reason"],
            })
            w["priority"] = r["priority"]
            if r["reason"]:
                w["priority_reason"] = r["reason"]
            logger.info(f"  [reeval] {ticker} 優先級 {changes[-1]['old']} → {changes[-1]['new']}：{r['reason'][:60]}")

    if changes:
        with open(portfolio_path, "w", encoding="utf-8") as f:
            json.dump(portfolio, f, ensure_ascii=False, indent=2)
        logger.info(f"  [reeval] portfolio.json 已更新，{len(changes)} 個標的優先級異動")

    return changes
