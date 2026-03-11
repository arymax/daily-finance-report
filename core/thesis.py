"""thesis.py — 讀取、更新 thesis/*.md 投資論點檔案"""

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


def build_update_prompt(
    theses: dict[str, str],
    portfolio_content: str,
    market_content: str,
    session: str = "morning",
) -> str:
    """建立 thesis 自動更新 prompt。"""
    thesis_text = ""
    for name, content in theses.items():
        thesis_text += f"=== {name}.md ===\n{content}\n\n"

    today = datetime.now(TST).strftime("%Y-%m-%d")
    session_label = "早盤" if session == "morning" else "收盤"

    return f"""你是一位嚴謹的投資分析師助理，負責維護投資論點（thesis）文件的準確性。
今天是 {today}（{session_label}）。

## 今日已生成的報告內容

### 持倉分析報告
{portfolio_content or "（本次未生成）"}

### 市場總覽報告
{market_content or "（本次未生成）"}

---

## 現有 Thesis 文件

{thesis_text}
---

## 你的任務

仔細比對今日報告內容與現有 thesis 文件，找出**需要更新的內容**。

**事實更新原則：**
- 只更新有新的、具體、可驗證的事實（如財報數字、新的進場條件確認、管理層變動結果）
- 不更新觀點、策略判斷（這些由使用者自行維護）
- 近期催化劑表格：若事件已過且有結果，更新「意義」欄或在事件前加「✅」標記已完成
- 持倉狀態表格（如有）：若價格已超過關鍵阻力或跌破支撐，標記狀態變化
- 若某個 thesis 文件完全不需要更新，就不要輸出它

**重大質化事件警報（⚠️）：**
若偵測到以下類型事件，**不要**修改 thesis 的策略判斷部分，
而是在所有 THESIS 區塊之後輸出警報，讓使用者手動評估：
- 公司宣布重大收購 / 被收購
- 核心業務方向轉型（exit 主要業務線 / 推出顛覆性新業務）
- 強力新競爭對手進入（可能直接威脅護城河）
- 創辦人 / CEO 離職
- 重大監管行動影響商業模式
- 重大客戶流失影響護城河評估

警報格式：
===ALERT: <TICKER>===
（描述事件，說明為什麼需要使用者手動重新評估 thesis 策略部分）
===END_ALERT===

**輸出格式（嚴格遵守，先輸出所有 THESIS 區塊，再輸出所有 ALERT 區塊）：**

===THESIS: <檔名（不含 .md）>===
（完整的更新後 .md 內容）
===END_THESIS===

===ALERT: <TICKER>===
（重大質化事件說明）
===END_ALERT===

若今日報告無事實需要更新任何 thesis，且無警報，僅輸出：
NO_UPDATE"""


def parse_and_save(
    response: str, thesis_dir: Path
) -> tuple[list[str], dict[str, str]]:
    """
    解析 Claude 回傳的 THESIS 與 ALERT 區塊。
    回傳 (updated_list, alerts_dict)：
      updated_list: 已更新的 thesis 檔名列表
      alerts_dict:  {TICKER: 警報說明文字}
    更新時在檔案末尾寫入 <!-- last_updated: YYYY-MM-DD -->。
    """
    updated: list[str] = []
    alerts: dict[str, str] = {}

    if response.strip() == "NO_UPDATE":
        return updated, alerts

    today = datetime.now(TST).strftime("%Y-%m-%d")

    # 解析 THESIS 區塊
    thesis_pattern = r"===THESIS:\s*(\S+)===\n([\s\S]*?)===END_THESIS==="
    for name, content in re.findall(thesis_pattern, response):
        name = name.strip()
        target = find_thesis(thesis_dir, name)
        if target is not None:
            text = content.strip()
            # 移除舊的 last_updated 標記（避免重複）
            text = re.sub(r"\n<!-- last_updated: \d{4}-\d{2}-\d{2} -->", "", text)
            text += f"\n<!-- last_updated: {today} -->\n"
            target.write_text(text, encoding="utf-8")
            logger.info(f"  Thesis 更新：{name}.md")
            updated.append(name)
        else:
            logger.warning(f"  Thesis 更新略過（檔案不存在）：{name}.md")

    # 解析 ALERT 區塊
    alert_pattern = r"===ALERT:\s*(\S+)===\n([\s\S]*?)===END_ALERT==="
    for ticker, text in re.findall(alert_pattern, response):
        alerts[ticker.strip()] = text.strip()

    return updated, alerts
