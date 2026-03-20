"""
core/themes_updater.py — AI 驅動的主題燃料自動更新

每日根據市場報告自動調整 themes/*.md 的：
  - fuel_pct（剩餘燃料百分比）
  - status（active / building / cooling / peak）
  - 里程碑 checkboxes（- [ ] → - [x]）
  - last_updated（日期）

輸出格式（嚴格）：
  ===THEME: <stem>===
  FUEL_PCT: <0-100>
  STATUS: <active|building|cooling|peak>
  CHECK: <milestone 文字（不含 - [ ] 前綴，精確匹配）>
  ===END_THEME===

若無任何主題需要更新：輸出 NO_UPDATE
"""

import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

TST = timezone(timedelta(hours=8))

# 只更新這些狀態的主題（peak/cooling 仍可更新，但不拉高 fuel）
ACTIVE_STATUSES = {"active", "building", "cooling", "peak"}

# fuel_pct 每日允許最大變動幅度（防止 Claude 誇大）
MAX_FUEL_DELTA = 15


# ── 前端解析工具 ────────────────────────────────────────────────

def _parse_front_matter(content: str) -> dict:
    """解析 YAML front matter（--- ... ---），回傳 dict。"""
    fm: dict = {}
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return fm
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            break
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                fm[key] = [v.strip() for v in val[1:-1].split(",") if v.strip()]
            else:
                fm[key] = val
    return fm


def _load_themes(themes_dir: Path) -> dict[str, dict]:
    """
    載入 themes_dir 下所有 .md 檔案。
    回傳 {stem: {path, content, fm}} dict。
    """
    result: dict[str, dict] = {}
    for f in sorted(themes_dir.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        fm = _parse_front_matter(content)
        status = fm.get("status", "active")
        if status not in ACTIVE_STATUSES:
            continue
        result[f.stem] = {"path": f, "content": content, "fm": fm}
    return result


def _extract_pending_milestones(content: str) -> list[str]:
    """從 content 提取所有未完成里程碑（- [ ] ...）文字（不含前綴）。"""
    milestones = []
    for line in content.splitlines():
        m = re.match(r"^\s*-\s*\[\s*\]\s*(.+)$", line)
        if m:
            milestones.append(m.group(1).strip())
    return milestones


# ── Prompt 建構 ────────────────────────────────────────────────

def build_theme_update_prompt(
    themes: dict[str, dict],
    market_content: str,
    session: str = "morning",
) -> str:
    """建立主題燃料更新 prompt。"""
    today = datetime.now(TST).strftime("%Y-%m-%d")
    session_label = "早盤" if session == "morning" else "收盤"

    # 市場報告截取前 3000 字元（保留最高資訊密度）
    m_report = (market_content or "（本次未生成）")[:3000]

    # 建立各主題摘要（前端資訊 + 未完成里程碑）
    themes_text = ""
    for stem, info in themes.items():
        fm = info["fm"]
        pending = _extract_pending_milestones(info["content"])
        pending_str = "\n".join(f"  - [ ] {m}" for m in pending) if pending else "  （無待確認里程碑）"
        themes_text += (
            f"=== {stem} ===\n"
            f"名稱：{fm.get('name', stem)}\n"
            f"現有狀態：{fm.get('status', 'active')} | 燃料：{fm.get('fuel_pct', '?')}%\n"
            f"相關標的：{', '.join(fm.get('tickers', []))}\n"
            f"待確認里程碑：\n{pending_str}\n\n"
        )

    return f"""你是一位嚴謹的投資主題分析師，負責維護長期投資主題（themes）的燃料與狀態。
今天是 {today}（{session_label}）。

## 今日市場總覽報告（前 3000 字）

{m_report}

---

## 現有投資主題清單

{themes_text}---

## 你的任務

根據今日市場報告，判斷哪些投資主題的燃料、狀態或里程碑需要更新。

**更新原則：**
- `fuel_pct`：0–100 的整數。只在有明確正面/負面催化劑時調整，每次變動幅度不超過 {MAX_FUEL_DELTA}%
- `status` 規則：
  - `active`：主題持續有催化劑，正常追蹤
  - `building`：主題尚在蓄積動能，尚未爆發
  - `peak`：主題短期過熱，接近高點，需謹慎
  - `cooling`：主題催化劑消退，燃料持續下滑
- 里程碑 `CHECK`：只在今日報告有**明確事實確認**時才打勾，不要憑推測
- 若某主題今日無相關新聞或變化，就**不要**輸出它

**輸出格式（嚴格遵守）：**

對每個需要更新的主題輸出：

===THEME: <stem（檔名，不含 .md）>===
FUEL_PCT: <整數 0-100>
STATUS: <active|building|cooling|peak>
CHECK: <里程碑原文（精確匹配，不含 - [ ] 前綴），若無需打勾則省略此行>
===END_THEME===

每個 THEME 區塊只輸出**有變化**的欄位（FUEL_PCT 和 STATUS 必須都給，CHECK 視情況）。

若今日所有主題均無需更新，僅輸出：
NO_UPDATE"""


# ── 解析與儲存 ─────────────────────────────────────────────────

def parse_and_save_themes(
    response: str, themes_dir: Path
) -> list[str]:
    """
    解析 Claude 回傳的 THEME 區塊，更新對應 .md 檔案。
    回傳已更新的 stem 清單。
    """
    updated: list[str] = []

    if response.strip() == "NO_UPDATE":
        return updated

    today = datetime.now(TST).strftime("%Y-%m-%d")

    theme_pattern = r"===THEME:\s*(\S+)===\n([\s\S]*?)===END_THEME==="
    for stem, body in re.findall(theme_pattern, response):
        stem = stem.strip()
        theme_file = themes_dir / f"{stem}.md"
        if not theme_file.exists():
            logger.warning(f"  主題更新略過（檔案不存在）：{stem}.md")
            continue

        text = theme_file.read_text(encoding="utf-8")

        # 解析 FUEL_PCT
        fuel_match = re.search(r"FUEL_PCT:\s*(\d+)", body)
        # 解析 STATUS
        status_match = re.search(r"STATUS:\s*(\w+)", body)
        # 解析 CHECK（可多行）
        checks = re.findall(r"CHECK:\s*(.+)", body)

        if not fuel_match and not status_match and not checks:
            logger.warning(f"  主題 {stem}.md 解析不到有效欄位，跳過")
            continue

        changed = False

        # 更新 fuel_pct
        if fuel_match:
            new_fuel = int(fuel_match.group(1))
            new_fuel = max(0, min(100, new_fuel))
            # 取得現有值並限制變動幅度
            old_fuel_match = re.search(r"fuel_pct:\s*(\d+)", text)
            if old_fuel_match:
                old_fuel = int(old_fuel_match.group(1))
                delta = abs(new_fuel - old_fuel)
                if delta > MAX_FUEL_DELTA:
                    direction = 1 if new_fuel > old_fuel else -1
                    new_fuel = old_fuel + direction * MAX_FUEL_DELTA
                    logger.info(f"  ℹ️  {stem} fuel_pct 變動幅度限制：{old_fuel} → {new_fuel}")
            text = re.sub(r"(fuel_pct:\s*)\d+", f"\\g<1>{new_fuel}", text)
            changed = True
            logger.info(f"  [OK] {stem}.md fuel_pct → {new_fuel}")

        # 更新 status
        if status_match:
            new_status = status_match.group(1).strip()
            if new_status in ACTIVE_STATUSES:
                text = re.sub(r"(status:\s*)\w+", f"\\g<1>{new_status}", text)
                changed = True
                logger.info(f"  [OK] {stem}.md status → {new_status}")
            else:
                logger.warning(f"  無效 status 值：{new_status}，略過")

        # 打勾里程碑
        for check_text in checks:
            check_text = check_text.strip()
            if not check_text:
                continue
            # 嘗試精確匹配 - [ ] <text>
            escaped = re.escape(check_text)
            pattern = rf"(- \[ \] )({escaped})"
            new_text, count = re.subn(pattern, r"- [x] \2", text)
            if count > 0:
                text = new_text
                changed = True
                logger.info(f"  [OK] {stem}.md 里程碑打勾：{check_text[:60]}")
            else:
                logger.warning(f"  [WARN] {stem}.md 里程碑未找到：{check_text[:60]}")

        if not changed:
            continue

        # 更新 last_updated
        text = re.sub(r"(last_updated:\s*)\d{4}-\d{2}-\d{2}", f"\\g<1>{today}", text)

        theme_file.write_text(text, encoding="utf-8")
        logger.info(f"  主題更新：{stem}.md")
        updated.append(stem)

    return updated
