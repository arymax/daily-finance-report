"""
dashboard.py — 靜態看板資料生成器

每次執行報告後呼叫 generate_dashboard_data()：
  - 覆寫 docs/data.json（當日快照）
  - 追加至 docs/history.json（歷史趨勢，保留最近 90 筆）
"""

import json
import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)
TST = timezone(timedelta(hours=8))


# ── 持倉計算 ─────────────────────────────────────────────────────────────────

def _compute_stock_value(pos: dict, prices: dict, usd_twd: float) -> dict | None:
    """計算股票 / ETF 持倉的當前市值與損益。"""
    ticker   = pos["ticker"]
    market   = pos.get("market", "US")
    cost_twd = pos.get("cost_twd", 0)
    shares   = pos.get("shares", 0)

    if ticker not in prices or not shares:
        return None

    price_info    = prices[ticker]
    current_price = price_info["price"]
    currency      = price_info["currency"]

    current_value_twd = shares * current_price * (1 if market == "TW" else usd_twd)
    pnl_twd  = current_value_twd - cost_twd
    pnl_pct  = (pnl_twd / cost_twd * 100) if cost_twd > 0 else 0.0

    return {
        "current_value_twd": round(current_value_twd),
        "pnl_twd":           round(pnl_twd),
        "pnl_pct":           round(pnl_pct, 1),
        "current_price":     f"{current_price:.2f} {currency}",
    }


def _compute_crypto_value(pos: dict, prices: dict, usd_twd: float) -> dict:
    """計算加密貨幣現貨 / 穩定幣持倉的當前市值與損益。"""
    ticker   = pos["ticker"]
    pos_type = pos.get("type", "spot")
    cost_twd = pos.get("cost_twd", 0)
    quantity = pos.get("quantity", 0.0)

    current_value_twd = 0.0
    current_price_str = ""

    if pos_type == "stablecoin":
        current_value_twd = quantity * usd_twd
        current_price_str = "1.00 USD"
    elif ticker in prices and quantity:
        price_info    = prices[ticker]
        current_price = price_info["price"]
        current_value_twd = quantity * current_price * usd_twd
        current_price_str = f"{current_price:.2f} USD"

    pnl_twd = current_value_twd - cost_twd
    pnl_pct = (pnl_twd / cost_twd * 100) if cost_twd > 0 else 0.0

    return {
        "current_value_twd": round(current_value_twd),
        "pnl_twd":           round(pnl_twd),
        "pnl_pct":           round(pnl_pct, 1),
        "current_price":     current_price_str,
    }


# ── Markdown 解析 ─────────────────────────────────────────────────────────────

def _parse_indices(market_content: str) -> list[dict]:
    """從市場總覽 markdown 的指數表格解析漲跌幅。"""
    indices = []
    pattern = r'\|\s*([^|\n]+?)\s*\|\s*\*{0,2}([+\-][\d.]+%)\*{0,2}\s*\|'
    for m in re.finditer(pattern, market_content):
        name       = m.group(1).strip()
        change_str = m.group(2).strip()
        if any(k in name for k in ["道瓊", "S&P", "納斯達克", "TAIEX", "台股"]):
            try:
                change_pct = float(change_str.replace("%", "").replace("+", ""))
            except ValueError:
                change_pct = 0.0
            indices.append({
                "name":       name,
                "change_pct": change_pct,
                "change_str": change_str,
            })
    return indices


def _parse_sectors(market_content: str) -> dict:
    """解析強勢 / 弱勢板塊清單（最多各 4 個）。"""
    strong: list[str] = []
    weak:   list[str] = []
    in_strong = in_weak = False

    for line in market_content.splitlines():
        stripped = line.strip()
        if re.search(r'[##]{2,3}\s*強勢板塊', stripped):
            in_strong, in_weak = True, False
        elif re.search(r'[##]{2,3}\s*弱勢板塊', stripped):
            in_strong, in_weak = False, True
        elif stripped.startswith("## "):
            in_strong = in_weak = False
        elif (in_strong or in_weak) and stripped.startswith("**"):
            # e.g. **① 能源（石油 / LNG）** → "能源"
            m = re.match(r'\*+[①②③\d]?\s*([^\s（(【\*、，,/]{2,8})', stripped)
            if m:
                name = m.group(1).strip("*① ②③④⑤")
                if name:
                    (strong if in_strong else weak).append(name)

    return {"strong": strong[:4], "weak": weak[:4]}


def _parse_key_events(market_content: str) -> list[str]:
    """解析 【XXX】 格式的重要市場事件（最多 5 個）。"""
    events = []
    for line in market_content.splitlines():
        m = re.match(r'-\s*\*+【(.+?)】', line)
        if m:
            events.append(m.group(1))
        if len(events) >= 5:
            break
    return events


def _parse_risks(market_content: str) -> list[str]:
    """解析台股今日特別注意風險的編號條列項（最多 5 個）。"""
    risks = []
    in_risk = False
    for line in market_content.splitlines():
        if "特別注意風險" in line or ("風險提示" in line and "台股" in line):
            in_risk = True
        elif in_risk and line.startswith("## "):
            break
        elif in_risk:
            raw = line.strip()
            m = re.match(r'\d+\.\s*\*{0,2}(.+?)\*{0,2}[—–:-]', raw)
            if m:
                risks.append(m.group(1).strip("【】 "))
            elif re.match(r'\d+\.', raw) and raw:
                text = re.sub(r'^\d+\.\s*', '', raw)
                text = re.sub(r'\*+', '', text)[:70]
                if text:
                    risks.append(text)
    return risks[:5]


def _parse_watchlist_status(portfolio_content: str, watchlist: list) -> list[dict]:
    """從持倉分析 markdown 提取觀察清單各標的的進場狀態與建議動作。"""
    STATUS_MAP = {
        "⏳": "未達成",
        "🔄": "部分達成",
        "✅": "已達成",
        "❌": "未達成",
    }

    result = []
    for item in watchlist:
        ticker   = item["ticker"]
        priority = item.get("priority", 2)

        status_icon = "⏳"
        status      = "未達成"
        action      = ""

        # 找到該 ticker 的分析段落（### TICKER｜...）
        pat = rf'###\s+{re.escape(ticker)}\|[^\n]*\n([\s\S]*?)(?=\n###\s|\Z)'
        m = re.search(pat, portfolio_content)
        if m:
            section = m.group(0)
            sm = re.search(r'進場條件達成狀態[：:]\s*([⏳🔄✅❌])', section)
            if sm:
                status_icon = sm.group(1)
                status      = STATUS_MAP.get(status_icon, "觀察中")
            am = re.search(r'\*\*建議動作[：:]\*\*\s*(.+?)(?=\n\n|\n\*\*|\Z)', section, re.DOTALL)
            if am:
                action = re.sub(r'\n+', ' ', am.group(1).strip())[:160]

        result.append({
            "ticker":      ticker,
            "name":        item.get("name", ticker),
            "priority":    priority,
            "market":      item.get("market", "US"),
            "sector":      item.get("sector", ""),
            "theme":       (item.get("theme", "") or "")[:80],
            "status":      status,
            "status_icon": status_icon,
            "action":      action,
        })

    result.sort(key=lambda x: x["priority"])
    return result


# ── 報告同步 ──────────────────────────────────────────────────────────────────

def _sync_reports(reports_dir: Path, docs_dir: Path) -> list[dict]:
    """
    將 reports/*.md 複製到 docs/reports/，並生成 docs/reports_index.json。
    回傳報告索引清單（最新在前）。
    """
    dest_dir = docs_dir / "reports"
    dest_dir.mkdir(parents=True, exist_ok=True)

    SESSION_LABEL = {"morning": "早盤", "evening": "收盤"}
    TYPE_LABEL = {
        "portfolio_analysis": "持倉分析",
        "market_overview":    "市場總覽",
        "premarket_check":    "盤前晨檢",
    }

    index: list[dict] = []
    for md_file in sorted(reports_dir.glob("*.md")):
        stem = md_file.stem  # e.g. "20260320_morning_portfolio_analysis"
        # 格式：YYYYMMDD_session_type  或  YYYYMMDD_type
        parts = stem.split("_", 1)
        if len(parts) < 2 or len(parts[0]) != 8:
            continue

        date_raw = parts[0]
        try:
            date_str = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:8]}"
        except Exception:
            continue

        rest = parts[1]  # "morning_portfolio_analysis"
        session = None
        type_part = rest
        for s in ("morning", "evening"):
            if rest.startswith(s + "_"):
                session   = s
                type_part = rest[len(s) + 1:]
                break

        type_label    = TYPE_LABEL.get(type_part, type_part.replace("_", " "))
        session_label = SESSION_LABEL.get(session, "") if session else ""
        label = f"{date_str} {session_label}・{type_label}".strip("・ ")

        # 複製到 docs/reports/
        dest = dest_dir / md_file.name
        dest.write_bytes(md_file.read_bytes())

        index.append({
            "date":     date_str,
            "session":  session or "",
            "type":     type_part,
            "filename": md_file.name,
            "label":    label,
        })

    # 最新在前
    index.sort(key=lambda x: (x["date"], x["session"]), reverse=True)

    (docs_dir / "reports_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return index


def _write_config_js(docs_dir: Path) -> None:
    """
    讀取 .env 中的 FINNHUB_API_KEY，生成 docs/config.js。
    docs/config.js 被 .gitignore 排除，僅本機使用。
    """
    import os
    from pathlib import Path as _Path

    # 嘗試從 .env 讀取（相對於專案根目錄）
    env_path = _Path(__file__).parent.parent / ".env"
    key = ""
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("FINNHUB_API_KEY="):
                key = line.split("=", 1)[1].strip()
                break

    # 如果 .env 沒有，也接受環境變數
    if not key:
        key = os.environ.get("FINNHUB_API_KEY", "")

    config_js = docs_dir / "config.js"
    config_js.write_text(
        f'// 本地 API key 設定（由 dashboard.py 自動生成，已加入 .gitignore）\n'
        f'window.FINNHUB_KEY = "{key}";\n',
        encoding="utf-8",
    )
    logger.info("✅ docs/config.js 已生成（本機用）")


def _sync_thesis(thesis_dir: Path, docs_dir: Path) -> list[dict]:
    """
    Sync thesis/{Category}/*.md → docs/thesis/{Category}/*.md
    Generate docs/thesis_index.json grouped by category.
    """
    out_dir = docs_dir / "thesis"
    out_dir.mkdir(parents=True, exist_ok=True)

    categories: dict[str, list[dict]] = {}

    for md_file in sorted(thesis_dir.rglob("*.md")):
        if md_file.name == "README.md":
            continue
        category = md_file.parent.name
        if category == thesis_dir.name:   # root-level files, skip
            continue

        ticker = md_file.stem

        # Copy preserving category subdir
        cat_dir = out_dir / category
        cat_dir.mkdir(exist_ok=True)
        (cat_dir / md_file.name).write_bytes(md_file.read_bytes())

        if category not in categories:
            categories[category] = []
        categories[category].append({
            "ticker":   ticker,
            "filename": f"{category}/{md_file.name}",
        })

    index = [
        {"category": cat, "files": sorted(files, key=lambda f: f["ticker"])}
        for cat, files in sorted(categories.items())
    ]

    (docs_dir / "thesis_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return index


def _parse_front_matter(content: str) -> tuple[dict, str]:
    """Parse YAML-like front matter between --- delimiters."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("\n---", 3)
    if end == -1:
        return {}, content
    fm_text = content[3:end].strip()
    body = content[end + 4:].strip()
    meta: dict = {}
    for line in fm_text.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            items = [v.strip().strip("\"'") for v in val[1:-1].split(",")]
            meta[key] = [i for i in items if i]
        else:
            try:
                meta[key] = int(val)
            except ValueError:
                try:
                    meta[key] = float(val)
                except ValueError:
                    meta[key] = val
    return meta, body


def _sync_themes(themes_dir: Path, docs_dir: Path) -> list[dict]:
    """
    Sync themes/*.md → docs/themes/*.md
    Parse YAML front matter and generate docs/themes_index.json.
    """
    out_dir = docs_dir / "themes"
    out_dir.mkdir(parents=True, exist_ok=True)

    index: list[dict] = []
    STATUS_ORDER = {"active": 0, "building": 1, "cooling": 2, "peak": 3}

    for md_file in sorted(themes_dir.glob("*.md")):
        if md_file.name == "README.md":
            continue
        content = md_file.read_text(encoding="utf-8")
        meta, body = _parse_front_matter(content)
        if not meta:
            continue

        # Count milestones
        total_ms   = len(re.findall(r"^- \[[ x]\]", body, re.MULTILINE))
        done_ms    = len(re.findall(r"^- \[x\]",    body, re.MULTILINE))

        entry = {
            "id":           md_file.stem,
            "name":         meta.get("name", md_file.stem),
            "status":       meta.get("status", "building"),
            "fuel_pct":     meta.get("fuel_pct", 50),
            "tickers":      meta.get("tickers", []),
            "last_updated": meta.get("last_updated", ""),
            "filename":     md_file.name,
            "milestones_total": total_ms,
            "milestones_done":  done_ms,
        }
        index.append(entry)
        (out_dir / md_file.name).write_bytes(md_file.read_bytes())

    index.sort(key=lambda x: (STATUS_ORDER.get(x["status"], 9), -x["fuel_pct"]))

    (docs_dir / "themes_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return index


def _parse_ripple(market_content: str) -> list[dict]:
    """
    Parse 宏觀漣漪分析 section from market overview report.
    Expected format:
      ## 八、宏觀漣漪分析
      ### Emoji Title
      - **一階影響**：...
      - **二階影響**：...
      - **關聯標的**：...
    """
    m = re.search(
        r"##\s*[八8]、宏觀漣漪分析(.*?)(?=^##\s|\Z)",
        market_content, re.MULTILINE | re.DOTALL,
    )
    if not m:
        return []

    section = m.group(1)
    ripples: list[dict] = []
    entries = re.split(r"^###\s+", section, flags=re.MULTILINE)
    for entry in entries[1:]:
        lines = entry.strip().splitlines()
        if not lines:
            continue
        title = lines[0].strip()
        first_order = second_order = related = ""
        for line in lines[1:]:
            clean = re.sub(r"\*\*[^*]+\*\*[：:]?\s*", "", line).strip().lstrip("- ")
            if "一階影響" in line:
                first_order = clean
            elif "二階影響" in line:
                second_order = clean
            elif "關聯標的" in line:
                related = clean
        if title:
            ripples.append({
                "title":        title,
                "first_order":  first_order,
                "second_order": second_order,
                "related":      related,
            })
    return ripples


# ── 主入口 ────────────────────────────────────────────────────────────────────

def generate_dashboard_data(
    portfolio:         dict,
    prices:            dict,
    usd_twd:           float,
    session:           str,
    portfolio_content: str,
    market_content:    str,
    docs_dir:          Path,
    reports_dir:       Path | None = None,
    thesis_dir:        Path | None = None,
    themes_dir:        Path | None = None,
    frontend_data_dir: Path | None = None,
) -> None:
    """
    生成 docs/data.json（當日快照）並追加至 docs/history.json。
    在 main.py run() 中 Git push 之前呼叫。
    失敗時只記錄 warning，不影響主報告流程。
    """
    try:
        docs_dir.mkdir(parents=True, exist_ok=True)
        now      = datetime.now(TST)
        date_str = now.strftime("%Y-%m-%d")

        lt_positions = portfolio.get("long_term", {}).get("positions", [])
        ta_positions = portfolio.get("tactical",  {}).get("positions", [])
        cr_positions = portfolio.get("crypto",    {}).get("positions", [])
        watchlist    = portfolio.get("watchlist", [])
        cash_twd     = portfolio.get("cash", {}).get("total_twd", 0)

        # ── 股票 / ETF 持倉 ──
        positions_out: list[dict] = []
        for pos in lt_positions:
            entry: dict = {
                "ticker":   pos["ticker"],
                "name":     pos.get("name", pos["ticker"]),
                "type":     "長期ETF",
                "market":   pos.get("market", "TW"),
                "cost_twd": pos.get("cost_twd", 0),
                "shares":   pos.get("shares", 0),
                "sector":   pos.get("sector", ""),
            }
            val = _compute_stock_value(pos, prices, usd_twd)
            if val:
                entry.update(val)
            positions_out.append(entry)

        for pos in ta_positions:
            entry = {
                "ticker":   pos["ticker"],
                "name":     pos.get("name", pos["ticker"]),
                "type":     "個股",
                "market":   pos.get("market", "US"),
                "cost_twd": pos.get("cost_twd", 0),
                "shares":   pos.get("shares", 0),
                "sector":   pos.get("sector", ""),
            }
            val = _compute_stock_value(pos, prices, usd_twd)
            if val:
                entry.update(val)
            positions_out.append(entry)

        # ── 加密貨幣 ──
        crypto_out: list[dict] = []
        contract_margin = 0
        for pos in cr_positions:
            pos_type = pos.get("type", "spot")
            if pos_type == "contract":
                contract_margin += pos.get("cost_twd", 0)
                continue
            entry = {
                "ticker":   pos["ticker"],
                "name":     pos.get("name", pos["ticker"]),
                "type":     pos_type,
                "exchange": pos.get("exchange", ""),
                "cost_twd": pos.get("cost_twd", 0),
                "shares":   pos.get("quantity", pos.get("shares", 0.0)),
            }
            entry.update(_compute_crypto_value(pos, prices, usd_twd))
            crypto_out.append(entry)

        # ── 資產分布 ──
        etf_value    = sum(p.get("current_value_twd", p["cost_twd"]) for p in positions_out if p["type"] == "長期ETF")
        stock_value  = sum(p.get("current_value_twd", p["cost_twd"]) for p in positions_out if p["type"] == "個股")
        crypto_value = sum(p["current_value_twd"] for p in crypto_out)
        total_value  = cash_twd + etf_value + stock_value + crypto_value + contract_margin

        allocation: dict[str, float] = {}
        if total_value > 0:
            def _pct(v: float) -> float:
                return round(v / total_value * 100, 1)
            allocation = {
                "現金":      _pct(cash_twd),
                "長期ETF":   _pct(etf_value),
                "波段個股":  _pct(stock_value),
                "加密貨幣":  _pct(crypto_value),
                "合約保證金": _pct(contract_margin),
            }
            # 移除 0% 項目
            allocation = {k: v for k, v in allocation.items() if v > 0}

        # ── 總損益 ──
        all_positions = positions_out + crypto_out
        total_pnl     = sum(p.get("pnl_twd", 0) for p in all_positions)
        total_cost    = sum(p["cost_twd"] for p in all_positions)
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0

        # ── 市場解析 ──
        indices    = _parse_indices(market_content)    if market_content else []
        sectors    = _parse_sectors(market_content)    if market_content else {"strong": [], "weak": []}
        key_events = _parse_key_events(market_content) if market_content else []
        risks      = _parse_risks(market_content)      if market_content else []
        ripple     = _parse_ripple(market_content)     if market_content else []

        # ── 觀察清單 ──
        watchlist_data = _parse_watchlist_status(portfolio_content, watchlist)

        # ── data.json ──
        data = {
            "meta": {
                "generated_at": now.strftime("%Y-%m-%d %H:%M:%S TST"),
                "date":         date_str,
                "session":      session,
                "usd_twd":      round(usd_twd, 2),
            },
            "summary": {
                "total_value_twd":      round(total_value),
                "total_pnl_twd":        round(total_pnl),
                "total_pnl_pct":        round(total_pnl_pct, 1),
                "cash_twd":             cash_twd,
                "cash_pct":             round(cash_twd / total_value * 100, 1) if total_value else 0,
                "contract_margin_twd":  round(contract_margin),
            },
            "allocation": allocation,
            "positions":  positions_out,
            "crypto":     crypto_out,
            "watchlist":  watchlist_data,
            "market": {
                "indices":    indices,
                "sectors":    sectors,
                "key_events": key_events,
                "risks":      risks,
                "ripple":     ripple,
            },
        }

        (docs_dir / "data.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("✅ 看板資料已生成：docs/data.json")

        # ── history.json ──
        hist_path = docs_dir / "history.json"
        history: list[dict] = []
        if hist_path.exists():
            try:
                history = json.loads(hist_path.read_text(encoding="utf-8"))
            except Exception:
                history = []

        # 覆蓋同日同 session 的舊紀錄
        history = [h for h in history if not (h["date"] == date_str and h["session"] == session)]
        history.append({
            "date":            date_str,
            "session":         session,
            "timestamp":       now.isoformat(),
            "total_value_twd": round(total_value),
            "total_pnl_twd":   round(total_pnl),
            "total_pnl_pct":   round(total_pnl_pct, 1),
            "cash_pct":        round(cash_twd / total_value * 100, 1) if total_value else 0,
            "positions_pnl":   {
                p["ticker"]: p.get("pnl_pct", 0)
                for p in all_positions
                if "pnl_pct" in p
            },
        })
        history = sorted(history, key=lambda x: (x["date"], x["session"]))[-90:]

        hist_path.write_text(
            json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info(f"✅ 歷史資料已更新：docs/history.json（{len(history)} 筆）")

        # ── 生成本地 config.js（含 Finnhub API key）──
        _write_config_js(docs_dir)

        # ── 同步報告 markdown ──
        if reports_dir and reports_dir.exists():
            report_index = _sync_reports(reports_dir, docs_dir)
            logger.info(f"✅ 報告已同步：docs/reports/（{len(report_index)} 份）")

        # ── 同步 thesis markdown ──
        if thesis_dir and thesis_dir.exists():
            thesis_index = _sync_thesis(thesis_dir, docs_dir)
            total = sum(len(c["files"]) for c in thesis_index)
            logger.info(f"✅ Thesis 已同步：docs/thesis/（{len(thesis_index)} 板塊，{total} 份）")

        # ── 同步主題催化劑 ──
        if themes_dir and themes_dir.exists():
            themes_index = _sync_themes(themes_dir, docs_dir)
            logger.info(f"✅ 主題已同步：docs/themes/（{len(themes_index)} 個主題）")

        # ── 同步至 frontend/src/data/ ──
        if frontend_data_dir is not None:
            frontend_data_dir.mkdir(parents=True, exist_ok=True)
            (frontend_data_dir / "data.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (frontend_data_dir / "history.json").write_text(
                json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            for idx_name in ("reports_index.json", "thesis_index.json", "themes_index.json"):
                src = docs_dir / idx_name
                if src.exists():
                    (frontend_data_dir / idx_name).write_text(
                        src.read_text(encoding="utf-8"), encoding="utf-8"
                    )
            logger.info(f"✅ 已同步至 frontend/src/data/（{frontend_data_dir}）")

    except Exception as exc:
        logger.warning(f"看板資料生成失敗（不影響主報告）：{exc}", exc_info=True)
