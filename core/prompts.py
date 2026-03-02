"""
prompts.py — 組合兩個 Claude 分析任務的 Prompt（Schema v1.0）

持倉結構：long_term（ETF）/ tactical（個股）/ crypto / watchlist
即時股價由 prices dict 傳入，有值時顯示市值與損益，無值時只顯示成本
"""

from datetime import datetime, timezone, timedelta

TST = timezone(timedelta(hours=8))


def _taiwan_now() -> datetime:
    return datetime.now(TST)


def _date_header() -> str:
    now = _taiwan_now()
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    return now.strftime(f"%Y 年 %m 月 %d 日（星期{weekdays[now.weekday()]}）")


def _fmt(val, unit: str = "") -> str:
    """安全格式化數字，None 回傳 N/A。"""
    if val is None:
        return "N/A"
    try:
        return f"{int(val):,}{unit}"
    except (TypeError, ValueError):
        return str(val)


def _compute_value(pos: dict, prices: dict, usd_twd: float) -> tuple:
    """
    從即時股價計算市值（TWD）與未實現損益。
    回傳 (value_twd, pnl_twd, pnl_pct) 或 (None, None, None)
    """
    ticker  = pos.get("ticker", "")
    market  = pos.get("market", "US")
    shares  = pos.get("shares")
    cost    = pos.get("cost_twd")
    p_info  = prices.get(ticker)

    if p_info is None or shares is None:
        return None, None, None

    price     = p_info["price"]
    currency  = p_info["currency"]
    value_raw = price * shares

    # 轉換為 TWD
    value_twd = value_raw if currency == "TWD" else value_raw * usd_twd

    if cost and cost > 0:
        pnl_twd = value_twd - cost
        pnl_pct = pnl_twd / cost
        return value_twd, pnl_twd, pnl_pct

    return value_twd, None, None


def _build_pnl_table(portfolio: dict, prices: dict, usd_twd: float) -> list:
    """
    預算所有持倉的即時市值與未實現損益，回傳 Markdown table rows。
    供 build_portfolio_prompt 嵌入 prompt，讓 Claude 直接引用數字。
    """
    lines = [
        "| 類型 | 代碼 | 名稱 | 成本(TWD) | 現價 | 即時市值(TWD) | 損益(TWD) | 損益% |",
        "|------|------|------|-----------|------|--------------|-----------|-------|",
    ]

    def make_row(ptype: str, ticker: str, name: str,
                 cost, p_info, market: str, qty):
        if p_info and qty:
            price = p_info["price"]
            val_twd = price * qty if market == "TW" else price * qty * usd_twd
            pnl_twd = val_twd - cost if cost is not None else None
            pnl_pct = pnl_twd / cost if (pnl_twd is not None and cost) else None
        else:
            val_twd = pnl_twd = pnl_pct = None

        c = f"{cost:,.0f}" if cost else "—"
        p = f"{p_info['price']:.2f} {p_info['currency']}" if p_info else "（無報價）"
        v = f"{val_twd:,.0f}" if val_twd else "—"
        if pnl_twd is not None:
            sg = "+" if pnl_twd >= 0 else ""
            d = f"{sg}{pnl_twd:,.0f}"
            r = f"{sg}{pnl_pct * 100:.1f}%"
        else:
            d = r = "—"
        return f"| {ptype} | {ticker} | {name} | {c} | {p} | {v} | {d} | {r} |"

    # 長期 ETF
    for pos in portfolio.get("long_term", {}).get("positions", []):
        lines.append(make_row(
            "長期ETF", pos["ticker"], pos["name"],
            pos.get("cost_twd"), prices.get(pos["ticker"]),
            pos["market"], pos.get("shares"),
        ))
    # 波段個股
    for pos in portfolio.get("tactical", {}).get("positions", []):
        lines.append(make_row(
            "個股", pos["ticker"], pos["name"],
            pos.get("cost_twd"), prices.get(pos["ticker"]),
            pos["market"], pos.get("shares"),
        ))
    # 加密（現貨 + 穩定幣；合約不計入損益表）
    for pos in portfolio.get("crypto", {}).get("positions", []):
        if pos["type"] in ("spot", "stablecoin"):
            label = f"加密({pos['exchange']})"
            lines.append(make_row(
                label, pos["ticker"], pos["name"],
                pos.get("cost_twd"), prices.get(pos["ticker"]),
                "CRYPTO", pos.get("quantity"),
            ))
    return lines


# ─────────────────────────────────────────────
# Task 1：持倉分析與操作建議
# ─────────────────────────────────────────────

def build_portfolio_prompt(
    portfolio: dict,
    news_by_ticker: dict,
    prices: dict = None,
    usd_twd: float = 32.0,
    memory_context: str = "",
    thesis_dir: str = "",
) -> str:
    prices = prices or {}
    date_str = _date_header()

    long_term = portfolio.get("long_term", {})
    tactical  = portfolio.get("tactical", {})
    crypto    = portfolio.get("crypto", {})
    watchlist = portfolio.get("watchlist", [])
    strategy  = portfolio.get("strategy", {})
    cash      = portfolio.get("cash", {})

    lines = [
        f"你是一位專業的投資組合分析師，今天是 {date_str}。",
        "請根據以下完整資產配置與最新新聞，提供持倉評估與操作建議，以繁體中文回答。",
        f"（即時匯率：USD/TWD ≈ {usd_twd:.1f}）",
        "",
    ]

    if thesis_dir:
        lines += [
            "---",
            "",
            "# 個股買入背景資料庫（thesis）",
            "",
            f"在分析每支個股（波段持倉與觀察清單）時，請先嘗試讀取對應的 thesis 檔案：",
            f"`{thesis_dir}/{{TICKER}}.md`（例如：`{thesis_dir}/3030.md`、`{thesis_dir}/CRWD.md`）",
            "若檔案存在，請引用其內容，逐項驗證原始買入邏輯是否仍然成立；若不存在則略過。",
            "",
            "---",
            "",
        ]

    if memory_context:
        lines += [
            "---",
            "",
            "# 歷史記憶（請參考以下分析，保持決策連貫性）",
            "",
            memory_context,
            "",
            "---",
            "",
        ]

    lines += [
        "# 現金部位",
        f"- 合計：{_fmt(cash.get('total_twd'))} TWD",
        f"- 備注：{cash.get('note', '')}",
        "",
    ]

    # ── 長期配置（ETF）─────────────────────────
    lt_positions = long_term.get("positions", [])
    if lt_positions:
        lines += ["# 一、長期配置（ETF）", ""]
        for pos in lt_positions:
            ticker = pos["ticker"]
            name   = pos["name"]
            market = pos["market"]
            ptype  = pos["type"]
            cost   = pos.get("cost_twd")
            shares = pos.get("shares")

            value_twd, pnl_twd, pnl_pct = _compute_value(pos, prices, usd_twd)
            p_info = prices.get(ticker)

            lines += [f"## {name}（{ticker}）｜{ptype} / {market}"]
            if shares is not None:
                lines += [f"- 持股數：{shares} 股"]
            if p_info:
                lines += [f"- 即時股價：{p_info['price']:.2f} {p_info['currency']}"]
            if value_twd:
                lines += [f"- 即時市值：≈ {_fmt(round(value_twd))} TWD"]
            if cost:
                lines += [f"- 投入成本：{_fmt(cost)} TWD"]
            if pnl_twd is not None:
                sign = "+" if pnl_twd >= 0 else ""
                lines += [f"- 未實現損益：{sign}{_fmt(round(pnl_twd))} TWD（{sign}{pnl_pct*100:.1f}%）"]
            elif cost:
                lines += [f"- 投入成本：{_fmt(cost)} TWD（無法取得即時市值）"]
            lines += [f"- 板塊：{pos.get('sector', '')}　主題：{pos.get('theme', '')}"]
            if pos.get("dca_monthly"):
                lines += [f"- 月定額：{_fmt(pos.get('dca_amount_twd'))} TWD"]
            if pos.get("note"):
                lines += [f"- 備注：{pos['note']}"]
            lines += [""]

            news = news_by_ticker.get(ticker, [])
            if news:
                lines += ["**最新新聞：**"]
                for a in news[:3]:
                    lines += [f"- `{a['time']}` {a['title']}（{a['publisher']}）"]
                    if a.get("summary"):
                        lines += [f"  > {a['summary'][:180]}"]
            else:
                lines += ["*（本次未取得新聞）*"]
            lines += [""]

    # ── 波段投資（個股）───────────────────────
    ta_positions = tactical.get("positions", [])
    if ta_positions:
        lines += ["# 二、波段投資（個股）", ""]
        for pos in ta_positions:
            ticker = pos["ticker"]
            name   = pos["name"]
            market = pos["market"]
            cost   = pos.get("cost_twd")
            shares = pos.get("shares")

            value_twd, pnl_twd, pnl_pct = _compute_value(pos, prices, usd_twd)
            p_info = prices.get(ticker)

            lines += [f"## {name}（{ticker}）"]
            if pos.get("position_size"):
                size_map = {"full": "滿倉", "half": "半倉", "quarter": "1/4倉", "custom": "自訂"}
                lines += [f"- 倉位：{size_map.get(pos['position_size'], pos['position_size'])}"]
            if shares is not None:
                lines += [f"- 持股數：{shares} 股"]
            if p_info:
                lines += [f"- 即時股價：{p_info['price']:.2f} {p_info['currency']}"]
            if value_twd:
                lines += [f"- 即時市值：≈ {_fmt(round(value_twd))} TWD"]
            if cost:
                lines += [f"- 投入成本：{_fmt(cost)} TWD"]
                if pnl_twd is not None:
                    sign = "+" if pnl_twd >= 0 else ""
                    lines += [f"- 未實現損益：{sign}{_fmt(round(pnl_twd))} TWD（{sign}{pnl_pct*100:.1f}%）"]
            lines += [f"- 板塊：{pos.get('sector', '')}　主題：{pos.get('theme', '')}"]
            if pos.get("resistance_key"):
                lines += [f"- 關鍵壓力：{pos['resistance_key']}　參考支撐：{pos.get('support_ref', '—')}"]
            if pos.get("status"):
                lines += [f"- 目前狀態：{pos['status']}"]
            if pos.get("strategy"):
                lines += [f"- 操作策略：{pos['strategy']}"]

            catalysts = pos.get("catalysts", [])
            if catalysts:
                lines += ["- 近期催化劑："]
                for c in catalysts:
                    lines += [f"  - {c}"]

            fund = pos.get("fundamentals", {})
            if fund:
                lines += ["- 基本面："]
                for k, v in fund.items():
                    lines += [f"  - {k}：{v}"]

            if pos.get("note"):
                lines += [f"- 備注：{pos['note']}"]

            if thesis_dir:
                lines += [f"- 📋 買入背景：請讀取 `{thesis_dir}/{ticker}.md`（若存在）"]

            lines += [""]

            news = news_by_ticker.get(ticker, [])
            if news:
                lines += ["**最新新聞：**"]
                for a in news[:4]:
                    lines += [f"- `{a['time']}` {a['title']}（{a['publisher']}）"]
                    if a.get("summary"):
                        lines += [f"  > {a['summary'][:200]}"]
            else:
                lines += ["*（本次未取得新聞）*"]
            lines += [""]

    # ── 加密貨幣 ──────────────────────────────
    cr_positions = crypto.get("positions", [])
    if cr_positions:
        lines += ["# 三、加密貨幣", ""]
        for pos in cr_positions:
            ticker   = pos["ticker"]
            exchange = pos["exchange"]
            ptype    = pos["type"]
            cost     = pos.get("cost_twd")
            p_info   = prices.get(ticker)
            qty      = pos.get("quantity")

            entry = f"- **{ticker}**（{exchange} / {ptype}）"
            if p_info and qty:
                val_usd = p_info["price"] * qty
                entry  += f"　現價 {p_info['price']:.2f} USD，持倉 ≈ {val_usd * usd_twd:,.0f} TWD"
            elif cost:
                entry += f"　成本 {_fmt(cost)} TWD"
            if pos.get("role"):
                entry += f"　→ {pos['role']}"
            lines += [entry]

        lines += [""]

    # ── 觀察清單 ──────────────────────────────
    if watchlist:
        lines += ["# 四、觀察清單", ""]
        for w in watchlist:
            ticker = w["ticker"]
            km = w.get("key_metrics", {})
            high = km.get("52w_high_usd", "—")
            decline = km.get("decline_from_high")
            decline_str = f"{decline*100:.0f}%" if decline is not None else "—"

            lines += [f"## {w['name']}（{ticker}）　優先級 {w['priority']}"]
            lines += [f"- 52 週高點：USD {high}　距高點：{decline_str}"]
            lines += [f"- 觀察原因：{w.get('watch_reason', '')}"]
            lines += [f"- 進場條件：{w.get('entry_condition', '')}"]

            extra = km.get("additional", {})
            if extra:
                lines += ["- 指標：" + "　".join(f"{k}={v}" for k, v in list(extra.items())[:3])]

            catalysts = w.get("catalysts", [])
            if catalysts:
                lines += ["- 催化劑：" + "、".join(catalysts[:3])]

            risks = w.get("risks", [])
            if risks:
                lines += ["- 風險：" + "、".join(risks[:2])]

            if w.get("note"):
                lines += [f"- 備注：{w['note']}"]

            if thesis_dir:
                lines += [f"- 📋 買入背景：請讀取 `{thesis_dir}/{ticker}.md`（若存在）"]

            lines += [""]

            news = news_by_ticker.get(ticker, [])
            if news:
                lines += ["**最新新聞：**"]
                for a in news[:3]:
                    lines += [f"- `{a['time']}` {a['title']}"]
            else:
                lines += ["*（本次未取得新聞）*"]
            lines += [""]

    # ── 近期關鍵事件 ──────────────────────────
    events = strategy.get("key_upcoming_events", [])
    if events:
        today = _taiwan_now().date()
        upcoming = [e for e in events if e.get("date", "") >= str(today)]
        if upcoming:
            lines += ["# 近期關鍵事件", ""]
            for ev in sorted(upcoming, key=lambda x: x["date"])[:5]:
                ticker_tag = f"[{ev['ticker']}]" if ev.get("ticker") != "MARKET" else "[市場]"
                lines += [f"- `{ev['date']}` {ticker_tag} {ev['event']}"]
            lines += [""]

    # ── 持倉損益速覽（系統預算，Claude 直接引用）────────────
    lines += ["", "# 持倉損益速覽（數字由系統即時計算，請原樣引用至報告第一章節）", ""]
    lines += _build_pnl_table(portfolio, prices, usd_twd)
    lines += [""]

    # ── 輸出規範（7 章節）──────────────────────────────────
    lines += [
        "---",
        "",
        "# 請嚴格依照以下 7 個章節結構輸出分析報告（Markdown 格式）",
        "",
        "## 一、持股收益速覽",
        "直接複製上方「持倉損益速覽」表格（數字不得修改）。",
        "表格下方補充 1-2 句整體收益狀況說明（總市值估算、整體盈虧方向）。",
        "",
        "## 二、長期 ETF 評估",
        "針對每支 ETF，提供：",
        "- 近期市場動態（結合新聞，1-2 句）",
        "- 定額策略建議（粗體標示）：**維持定額 / 增加定額 / 暫停定額**，附理由",
        "",
        "## 三、個股操作建議",
        "針對每支個股，提供：",
        "- 近期市場動態（根據新聞，2-3 句）",
        "- 操作建議（粗體標示）：**繼續持有 / 加碼 / 減碼 / 停損**",
        "- 操作理由（具體，3-5 句，含基本面或技術面依據）",
        "- 關鍵技術位：壓力位 / 支撐位",
        "- **持倉檢核（每次必答，逐項回答）**",
        "  1. 買進邏輯：當初吸引買進的商業模式或成長驅動是什麼？（一句話）",
        "  2. 邏輯是否被破壞：有沒有出現「事實面」的改變讓原始邏輯失效？（非股價下跌）",
        "  3. 等待的事件：當初設定的催化劑有沒有出現 / 消失 / 延後？",
        "  4. 倉位匹配度：現在的確定性程度，和目前持倉規模是否還匹配？",
        "  5. 不安來源：若感到猶豫，是來自股價波動，還是基本面出現裂痕？",
        "- **合理賣出條件（明確列出，至少一條）**",
        "  - 當初等的事件已完全反映在股價中，且沒有新的催化劑接棒",
        "  - 買進邏輯被事實推翻（非股價推翻）",
        "  - 出現更高確定性的替代機會，倉位調配有明確意義",
        "",
        "## 四、加密貨幣評估",
        "- 現貨部位合理性（依市值佔比與市場環境評估）",
        "- 合約帳戶（Bitunix）風控操作提示（槓桿、停損建議）",
        "",
        "## 五、觀察清單進場評估",
        "針對每個標的，提供：",
        "- **進場決策框架（每次必答）**",
        "  1. 買進理由：這家公司的商業模式 / 成長驅動邏輯是什麼？（1-2 句）",
        "  2. 等待的事件：具體等待哪個催化劑？（訂單 / 產品發布 / 財報指標）",
        "  3. 定價評估：DCF 底線在哪裡（本金保護）？PE 重新定價的空間有多大？",
        "  4. 確定性階段：公司現在在哪個階段？（概念期 / 驗證期 / 加速成長期 / 成熟期）",
        "- 進場條件達成狀態：✅ 已達成 / ⏳ 未達成 / 🔄 部分達成",
        "- 建議動作（具體說明觸發條件與時程）",
        "",
        "## 六、整體資產健康度",
        "- 資產分布表（類型 ｜ 估算金額(TWD) ｜ 佔比）",
        "- 現金比例評估：是否過高？建議分階段部署時程與金額",
        "- 攻防比評估（進攻性 vs 防禦性部位）",
        "",
        "## 七、潛在問題 & 後續關注操作清單",
        "**① 目前潛在問題與風險**（條列，每項附簡短說明）",
        "**② 後續關注重點與操作清單**（依日期或優先順序排列）",
        "   格式：`[日期 / 觸發條件]` → 建議操作",
        "",
        "請以繁體中文輸出，語氣專業簡潔，嚴格依照上述章節標題。",
    ]

    return "\n".join(lines)


def build_market_prompt(
    market_news: list,
    watchlist: list,
    extra_news: dict = None,
    memory_context: str = "",
    thesis_dir: str = "",
) -> str:
    date_str = _date_header()

    lines = [
        f"你是一位資深美股市場策略師，今天是 {date_str}（台灣時間）。",
        "請根據以下昨晚美股收盤後的市場新聞，提供今日早晨的市場總覽與投資機會簡報，以繁體中文回答。",
        "",
    ]

    if thesis_dir:
        lines += [
            "---",
            "",
            "# 個股買入背景資料庫（thesis）",
            "",
            f"在分析觀察清單中的每個標的時，請先嘗試讀取對應的 thesis 檔案：",
            f"`{thesis_dir}/{{TICKER}}.md`（例如：`{thesis_dir}/CRWD.md`）",
            "若檔案存在，請引用其中的買入邏輯，結合今日市場新聞，判斷原始投資背景的時空條件是否已發生變化。",
            "",
            "---",
            "",
        ]

    if memory_context:
        lines += [
            "---",
            "",
            "# 歷史市場記憶（請參考以下分析，保持分析連貫性）",
            "",
            memory_context,
            "",
            "---",
            "",
        ]

    lines += [
        "# 市場總體新聞",
        "",
    ]

    for a in market_news[:20]:
        lines += [f"**{a['title']}**"]
        if a.get("summary"):
            lines += [f"> {a['summary'][:350]}"]
        lines += [f"*來源：{a.get('source', '—')}　{a.get('published', '')}*", ""]

    # ── 重要市場個股新聞（NVDA / AAPL / MSFT 等大盤權重股）──
    if extra_news:
        lines += ["---", "", "# 重要個股近期新聞（大盤權重股 / 財報重點）", ""]
        for ticker, articles in extra_news.items():
            if not articles:
                continue
            lines += [f"**{ticker}**"]
            for a in articles:
                pub = a.get("time") or a.get("published", "")
                pub_short = pub[:10] if pub else "—"
                src = a.get("publisher") or a.get("source", "—")
                lines += [f"- {a['title']}　*{src} {pub_short}*"]
                if a.get("summary"):
                    lines += [f"  > {a['summary'][:200]}"]
            lines += [""]

    if watchlist:
        lines += ["---", "", "# 我的觀察清單（請在分析中特別關注）", ""]
        for w in watchlist:
            ticker  = w["ticker"]
            km      = w.get("key_metrics", {})
            high    = km.get("52w_high_usd", "—")
            decline = km.get("decline_from_high")
            decline_str = f"{decline*100:.0f}%" if decline is not None else "—"

            lines += [f"### {w['name']}（{ticker}）　優先級 {w['priority']}"]
            lines += [f"- 52 週高點 USD {high}，距高點 {decline_str}"]
            if w.get("watch_reason"):
                lines += [f"- 觀察原因：{w['watch_reason']}"]
            if w.get("entry_condition"):
                lines += [f"- 進場條件：{w['entry_condition']}"]

            extra = km.get("additional", {})
            for k, v in list(extra.items())[:3]:
                lines += [f"- {k}：{v}"]

            catalysts = w.get("catalysts", [])
            if catalysts:
                lines += ["- 催化劑：" + "、".join(catalysts[:3])]
            if w.get("note"):
                lines += [f"- 策略：{w['note']}"]

            if thesis_dir:
                lines += [f"- 📋 買入背景：請讀取 `{thesis_dir}/{ticker}.md`（若存在）"]

            lines += [""]

    lines += [
        "---",
        "",
        "# 請嚴格依照以下 6 個章節結構輸出市場分析報告（Markdown 格式）",
        "",
        "## 一、昨日三大指數表現",
        "以表格呈現：指數 ｜ 漲跌幅 ｜ 收盤價（如已知）｜ 主要驅動因素",
        "涵蓋：道瓊工業 / 納斯達克 / S&P 500",
        "",
        "## 二、昨日財報重點",
        "依新聞判斷昨日已發布財報的重要公司，格式：",
        "| 公司（代碼）| 實際EPS vs 預期 | 實際營收 vs 預期 | 盤後漲跌 | 一句重點摘要 |",
        "若昨日無重大財報，請明確寫：「昨日無重大財報發布」。",
        "",
        "## 三、市場新聞與板塊影響",
        "列出 3-5 條重要新聞，格式：",
        "- **[新聞標題摘要]** → 影響板塊：[板塊] → 方向：利多 / 利空 / 中性",
        "並附「近期板塊漲跌背景說明」（1-2 句解釋近期板塊強弱的宏觀背景）。",
        "",
        "## 四、板塊輪動分析",
        "強勢板塊（1-3 個）：板塊名稱 + 強勢原因 + 代表個股",
        "弱勢板塊（1-3 個）：板塊名稱 + 弱勢原因",
        "",
        "## 五、可關注的潛在板塊與龍頭（3 個）",
        "每個板塊提供：",
        "- 機會背景（2-3 句）",
        "- 代表性個股（2-3 檔）",
        "- 切入理由",
        "若觀察清單標的有相關機會，請特別標注，並對照其 thesis 買入邏輯說明目前時空背景是否仍然成立。",
        "",
        "## 六、今日風險提示",
        "- 今日需特別注意的市場風險（條列）",
        "- 今日重要財報 / 數據發布預告（如已知）",
        "",
        "請以繁體中文輸出，格式工整、資訊密度高，適合早晨快速閱讀。",
    ]

    return "\n".join(lines)
