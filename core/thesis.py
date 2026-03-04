"""thesis.py — 讀取、更新 thesis/*.md 投資論點檔案"""

import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

TST = timezone(timedelta(hours=8))


def load_all_theses(thesis_dir: Path) -> dict[str, str]:
    """讀取 thesis_dir 下所有 .md 檔案，回傳 {stem: content}。"""
    result = {}
    for p in sorted(thesis_dir.glob("*.md")):
        result[p.stem] = p.read_text(encoding="utf-8")
    return result


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

**更新原則：**
- 只更新有新的、具體、可驗證的事實（如財報數字、新的進場條件確認、管理層變動結果）
- 不更新觀點、策略判斷（這些由使用者自行維護）
- 近期催化劑表格：若事件已過且有結果，更新「意義」欄或在事件前加「✅」標記已完成
- 持倉狀態表格（如有）：若價格已超過關鍵阻力或跌破支撐，標記狀態變化
- 若某個 thesis 文件完全不需要更新，就不要輸出它

**輸出格式（嚴格遵守）：**
對於每個需要更新的 thesis 文件，輸出完整的新版本內容：

===THESIS: <檔名（不含 .md）>===
（此處放完整的更新後 .md 內容）
===END_THESIS===

若今日報告無新事實需要更新任何 thesis，僅輸出：
NO_UPDATE"""


def parse_and_save(response: str, thesis_dir: Path) -> list[str]:
    """解析 Claude 回傳的區塊，寫入對應 thesis 檔案，回傳更新的檔名列表。"""
    if response.strip() == "NO_UPDATE":
        return []

    pattern = r"===THESIS:\s*(\S+)===\n([\s\S]*?)===END_THESIS==="
    matches = re.findall(pattern, response)

    updated = []
    for name, content in matches:
        name = name.strip()
        target = thesis_dir / f"{name}.md"
        if target.exists():
            target.write_text(content.strip() + "\n", encoding="utf-8")
            logger.info(f"  Thesis 更新：{name}.md")
            updated.append(name)
        else:
            logger.warning(f"  Thesis 更新略過（檔案不存在）：{name}.md")

    return updated
