"""
main.py — 每日財務報告主程式（Schema v1.0）

新版架構：
  portfolio.json 的頂層為 long_term / tactical / crypto / watchlist / strategy
  股票即時股價由 yfinance API 抓取，JSON 只存 cost_twd
  啟動時自動驗證 portfolio.json 是否符合 schema

用法：
    python main.py             # 執行全部報告
    python main.py --portfolio # 只執行持倉分析
    python main.py --market    # 只執行市場總覽
    python main.py --validate  # 只做 schema 驗證，不生成報告
"""

import argparse
import io
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Windows terminal UTF-8 支援
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from core.config import load_config, setup_logging
from core.portfolio import load_portfolio, validate_portfolio
from core.news import fetch_stock_news, fetch_market_news
from core.prices import fetch_current_prices, fetch_usd_twd_rate
from core.prompts import build_portfolio_prompt, build_market_prompt
import core.memory as mem
import core.sync as sync
from core.thesis import build_update_prompt as build_thesis_prompt, parse_and_save as save_theses
from core.fundamentals import fetch_fundamentals, update_snapshot_in_thesis
from core.research import (
    build_enrich_prompt,
    build_candidate_prompt, parse_candidates,
    parse_market_signals,
    build_research_prompt, save_research_thesis,
)

# ── 時區 ──────────────────────────────────────
TST = timezone(timedelta(hours=8))
BASE_DIR = Path(__file__).parent

logger = logging.getLogger(__name__)


# ── Claude CLI 呼叫 ────────────────────────────
def call_claude(prompt: str, claude_cli: str, model: str, timeout: int, stream: bool = False) -> str:
    """
    透過 subprocess 呼叫本地 Claude CLI（stdin pipe 模式，無暫存檔）。
    移除 CLAUDECODE 環境變數，避免巢狀 session 錯誤。
    stream=True 時即時印出 Claude 的回應，同時仍捕捉並回傳完整文字。
    """
    import time

    cmd = [claude_cli, "--print", "--dangerously-skip-permissions"]
    if model:
        cmd += ["--model", model]

    env = os.environ.copy()
    # 清除所有 Claude Code session 標記，避免子進程被誤判為巢狀 session
    for _k in (
        "CLAUDECODE", "CLAUDE_CODE",
        "CLAUDE_CODE_SSE_PORT", "CLAUDE_CODE_ENTRY_POINT",
        "CLAUDE_SESSION_ID",
    ):
        env.pop(_k, None)

    if stream:
        chunks: list[str] = []
        start = time.monotonic()
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        try:
            assert proc.stdin and proc.stdout
            proc.stdin.write(prompt)
            proc.stdin.close()
            for line in iter(proc.stdout.readline, ""):
                if time.monotonic() - start > timeout:
                    proc.kill()
                    raise subprocess.TimeoutExpired(cmd, timeout)
                print(line, end="", flush=True)
                chunks.append(line)
            proc.wait()
        except Exception:
            proc.kill()
            raise
        if proc.returncode != 0:
            stderr_out = proc.stderr.read() if proc.stderr else ""
            raise RuntimeError(
                f"Claude CLI 失敗 (exit {proc.returncode})\n{stderr_out[:600].strip()}"
            )
        return "".join(chunks).strip()
    else:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Claude CLI 失敗 (exit {result.returncode})\n{result.stderr[:600].strip()}"
            )
        return result.stdout.strip()


# ── 報告儲存 ──────────────────────────────────
def save_report(content: str, report_type: str, reports_dir: Path) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(TST)
    filename = reports_dir / f"{now.strftime('%Y%m%d')}_{report_type}.md"
    header = f"*生成時間：{now.strftime('%Y-%m-%d %H:%M:%S')} 台灣時間*\n\n---\n\n"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(header + content)
    logger.info(f"✅ 報告儲存：{filename.name}")
    return filename


# ── 主流程 ────────────────────────────────────
# ── Lock file（防止多個 main.py 並行執行）────────────
LOCK_FILE = BASE_DIR / "main.lock"


def _pid_alive(pid: int) -> bool:
    """判斷 PID 是否仍在執行中（Windows / Unix 通用，無第三方依賴）。"""
    if sys.platform == "win32":
        # Windows：用 tasklist 查詢 PID
        try:
            out = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True, timeout=5,
            )
            return str(pid) in out.stdout
        except Exception:
            return False
    else:
        # Unix：透過 /proc 檔案系統
        return Path(f"/proc/{pid}").exists()


def _acquire_lock() -> bool:
    """嘗試取得執行鎖，回傳是否成功。"""
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            if _pid_alive(pid):
                return False
            # 舊進程已結束，清除殘留 lock
            LOCK_FILE.unlink(missing_ok=True)
        except Exception:
            LOCK_FILE.unlink(missing_ok=True)
    LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
    return True


def _release_lock() -> None:
    LOCK_FILE.unlink(missing_ok=True)


def run(run_portfolio: bool = True, run_market: bool = True, session: str = "morning") -> None:
    config = load_config()

    claude_cli    = config.get("claude_cli", "claude")
    claude_model  = config.get("claude_model", "")
    timeout       = config.get("claude_timeout_seconds", 300)
    stream_output = config.get("stream_claude_output", False)
    reports_dir  = BASE_DIR / config.get("reports_dir", "reports")
    logs_dir     = BASE_DIR / config.get("logs_dir", "logs")
    portfolio_path       = BASE_DIR / config.get("portfolio_file", "portfolio.json")
    max_stock_articles        = config.get("max_articles_per_stock", 5)
    max_market_articles       = config.get("max_market_articles", 20)
    max_extra_ticker_articles = config.get("max_articles_per_extra_ticker", 3)
    news_sources  = config.get("news_sources", {})
    market_rss    = news_sources.get("market_rss", [])
    extra_tickers = news_sources.get("market_extra_tickers", [])
    memory_cfg    = config.get("memory", {})
    sync_cfg      = config.get("sync", {})
    thesis_cfg    = config.get("thesis", {})
    memory_dir    = BASE_DIR / memory_cfg.get("memory_dir", "memory")
    thesis_dir    = BASE_DIR / "thesis"
    context_days  = memory_cfg.get("context_days", 5)
    max_per_day   = thesis_cfg.get("max_per_day", 3)

    setup_logging(logs_dir)

    # ── 取得執行鎖（防止並行）──
    if not _acquire_lock():
        logger.warning(
            f"另一個 main.py（PID {LOCK_FILE.read_text().strip()}）正在執行中，本次略過。"
        )
        return

    session_label = "早盤（台股盤前／美股盤後）" if session == "morning" else "收盤（台股盤後／美股盤前）"
    logger.info("=" * 55)
    logger.info(f"   Daily Finance Report — {session_label}")
    logger.info("=" * 55)

    # ── Git 同步（執行前 pull）──
    if sync_cfg.get("enabled") and sync_cfg.get("auto_pull", True):
        logger.info("── Git 同步（pull）─────────────────────")
        sync.pull(BASE_DIR)

    # ── Schema 驗證 ──
    validate_portfolio(portfolio_path)

    portfolio = load_portfolio(portfolio_path)
    long_term = portfolio.get("long_term", {})
    tactical  = portfolio.get("tactical", {})
    crypto    = portfolio.get("crypto", {})
    watchlist = portfolio.get("watchlist", [])

    lt_positions = long_term.get("positions", [])
    ta_positions = tactical.get("positions", [])
    cr_positions = crypto.get("positions", [])

    logger.info(
        f"長期 {len(lt_positions)} 筆 | 波段 {len(ta_positions)} 筆 | "
        f"加密 {len(cr_positions)} 筆 | 觀察 {len(watchlist)} 筆"
    )

    # ── 收集需要抓取新聞的 ticker（帶 market）──
    news_tickers: list[tuple[str, str]] = []
    for pos in lt_positions + ta_positions:
        news_tickers.append((pos["ticker"], pos["market"]))
    for w in watchlist:
        news_tickers.append((w["ticker"], w["market"]))

    # ── 抓取新聞 ──
    logger.info("── 抓取個股新聞 ──────────────────────")
    news_by_ticker: dict = {}
    for ticker, market in news_tickers:
        news_by_ticker[ticker] = fetch_stock_news(
            ticker, market=market, max_articles=max_stock_articles
        )

    logger.info("── 抓取市場新聞 ──────────────────────")
    market_news = fetch_market_news(
        sources=market_rss or None, max_articles=max_market_articles
    )

    logger.info("── 抓取重要市場個股新聞 ──────────────")
    extra_news_by_ticker: dict = {}
    for ticker in extra_tickers:
        extra_news_by_ticker[ticker] = fetch_stock_news(
            ticker, market="US", max_articles=max_extra_ticker_articles
        )

    # ── 抓取即時股價（供 prompt 顯示市值 / 損益）──
    logger.info("── 查詢即時股價 ──────────────────────")
    price_tickers: list[tuple[str, str]] = [
        (pos["ticker"], pos["market"]) for pos in lt_positions + ta_positions
    ]
    # 加密貨幣（排除穩定幣與合約帳戶，只取現貨）
    for pos in cr_positions:
        if pos["type"] in ("spot", "stablecoin"):
            price_tickers.append((pos["ticker"], "CRYPTO"))

    prices = fetch_current_prices(price_tickers)
    usd_twd = fetch_usd_twd_rate()
    logger.info(f"  USD/TWD = {usd_twd:.2f}")

    # ── 抓取基本面指標並寫入 thesis 快照 ──
    fundamental_tickers: list[tuple[str, str]] = [
        (pos["ticker"], pos["market"]) for pos in ta_positions
    ] + [(w["ticker"], w["market"]) for w in watchlist]

    if fundamental_tickers:
        logger.info("── 抓取基本面指標 ──────────────────────")
        fundamentals = fetch_fundamentals(fundamental_tickers)
        update_time = datetime.now(TST).strftime("%Y-%m-%d %H:%M TST")
        for ticker, metrics in fundamentals.items():
            tf = thesis_dir / f"{ticker}.md"
            if tf.exists():
                update_snapshot_in_thesis(tf, metrics, update_time)

    # ── 載入歷史記憶 context ──
    memory_context = ""
    if memory_cfg.get("enabled", True):
        memory_context = mem.load_context(memory_dir, days=context_days)

    errors = []
    portfolio_content = ""
    market_content    = ""

    # ── Task 1：持倉分析 ──
    if run_portfolio:
        task_label = "持倉分析與操作建議" if session == "morning" else "收盤持倉檢視與夜盤操作計畫"
        logger.info(f"── Task 1：{task_label} ───────")
        try:
            prompt = build_portfolio_prompt(
                portfolio, news_by_ticker, prices, usd_twd,
                memory_context=memory_context,
                thesis_dir=str(thesis_dir),
                session=session,
            )
            logger.info(f"   Prompt 長度：{len(prompt):,} 字元")
            portfolio_content = call_claude(prompt, claude_cli, claude_model, timeout, stream=stream_output)
            save_report(portfolio_content, f"{session}_portfolio_analysis", reports_dir)
        except Exception as e:
            logger.error(f"持倉分析失敗：{e}")
            errors.append(str(e))

    # ── Task 2：市場總覽 ──
    if run_market:
        task_label = "美股盤後市場總覽" if session == "morning" else "台股收盤總覽與美股盤前預備"
        logger.info(f"── Task 2：{task_label} ──────────")
        try:
            existing_thesis_tickers = {f.stem for f in thesis_dir.glob("*.md")}
            prompt = build_market_prompt(
                market_news, watchlist, extra_news_by_ticker,
                memory_context=memory_context,
                thesis_dir=str(thesis_dir),
                session=session,
                max_research_candidates=max_per_day,
                existing_thesis_tickers=existing_thesis_tickers,
            )
            logger.info(f"   Prompt 長度：{len(prompt):,} 字元")
            market_content = call_claude(prompt, claude_cli, claude_model, timeout, stream=stream_output)
            save_report(market_content, f"{session}_market_overview", reports_dir)
        except Exception as e:
            logger.error(f"市場總覽失敗：{e}")
            errors.append(str(e))

    # ── 解析 Task 2 機器讀取區塊 ──
    triggered_tickers: set[str] = set()
    candidates: list[dict] = []
    if market_content:
        triggered_tickers, candidates = parse_market_signals(market_content)
        logger.info(
            f"  Task 2 訊號：THESIS_TRIGGER {len(triggered_tickers)} 個"
            f"（{', '.join(sorted(triggered_tickers)) or '無'}），"
            f"RESEARCH_CANDIDATE {len(candidates)} 個"
        )

    # ── Task 3：生成記憶摘要 ──
    if memory_cfg.get("enabled", True) and memory_cfg.get("generate_summary", True):
        if portfolio_content or market_content:
            logger.info("── Task 3：生成記憶摘要 ───────────────")
            try:
                summary_prompt = mem.generate_summary(portfolio_content, market_content)
                summary = call_claude(summary_prompt, claude_cli, claude_model, timeout, stream=stream_output)
                mem.save_summary(summary, memory_dir)
            except Exception as e:
                logger.warning(f"記憶摘要生成失敗（不影響主報告）：{e}")

    # ── Task 4：Thesis 自動更新（只更新 Task 2 觸發的 ticker）──
    if thesis_cfg.get("auto_update", True) and (portfolio_content or market_content):
        logger.info("── Task 4：Thesis 自動更新 ────────────────")
        try:
            theses = {
                stem: (thesis_dir / f"{stem}.md").read_text(encoding="utf-8")
                for stem in triggered_tickers
                if (thesis_dir / f"{stem}.md").exists()
            }
            logger.info(
                f"   THESIS_TRIGGER {len(triggered_tickers)} 個，"
                f"其中 {len(theses)} 個有 thesis：{', '.join(sorted(theses)) or '無'}"
            )
            if theses:
                update_prompt = build_thesis_prompt(
                    theses, portfolio_content, market_content, session=session
                )
                logger.info(f"   Prompt 長度：{len(update_prompt):,} 字元")
                thesis_response = call_claude(update_prompt, claude_cli, claude_model, timeout, stream=stream_output)
                updated, alerts = save_theses(thesis_response, thesis_dir)
                if updated:
                    logger.info(f"  ✅ 更新了 {len(updated)} 個 thesis：{', '.join(updated)}")
                else:
                    logger.info("  ℹ️ 今日無 thesis 更新")
                for ticker, alert_text in alerts.items():
                    logger.warning("  " + "!" * 50)
                    logger.warning(f"  ⚠️  重大質化事件警報：{ticker}")
                    logger.warning(f"  {alert_text}")
                    logger.warning("  請手動重新評估此 thesis 的策略部分")
                    logger.warning("  " + "!" * 50)
            else:
                logger.info("  ℹ️ 今日無 thesis 需要質化更新")
        except Exception as e:
            logger.warning(f"Thesis 自動更新失敗（不影響主報告）：{e}")

    # ── Task 5：自動研究新標的（直接使用 Task 2 解析的候選，無需額外 Claude call）──
    if candidates and (portfolio_content or market_content):
        max_per_day = thesis_cfg.get("max_per_day", 3)
        run_candidates = candidates[:max_per_day]
        logger.info("── Task 5：自動研究新標的 ────────────────")
        logger.info(f"  候選 {len(run_candidates)} 個：{', '.join(c['ticker'] for c in run_candidates)}")
        try:
            existing_tickers = {f.stem for f in thesis_dir.glob("*.md")}
            today_str = datetime.now(TST).strftime("%Y-%m-%d")
            for c in run_candidates:
                t_ticker = c["ticker"]
                if t_ticker in existing_tickers:
                    logger.info(f"  ⚠️  {t_ticker}.md 已存在，跳過")
                    continue
                t_name   = c["name"]
                t_market = c.get("market", "US")
                t_reason = c.get("reason", "")
                logger.info(f"  ── 研究 {t_ticker}（{t_name}）────")
                try:
                    t_articles   = fetch_stock_news(t_ticker, market=t_market, max_articles=8)
                    t_fund_data  = fetch_fundamentals([(t_ticker, t_market)])
                    t_price_data = fetch_current_prices([(t_ticker, t_market)])
                    t_price      = t_price_data.get(t_ticker, {}).get("price")
                    research_prompt = build_research_prompt(
                        ticker=t_ticker, name=t_name, market=t_market,
                        reason=t_reason,
                        news_articles=t_articles,
                        fundamentals=t_fund_data.get(t_ticker, {}),
                        price=t_price, usd_twd=usd_twd, today=today_str,
                    )
                    logger.info(f"     Research Prompt 長度：{len(research_prompt):,} 字元")
                    research_content = call_claude(research_prompt, claude_cli, claude_model, timeout, stream=stream_output)
                    saved_path = save_research_thesis(research_content, t_ticker, thesis_dir)
                    t_metrics = t_fund_data.get(t_ticker, {})
                    if t_metrics:
                        update_time = datetime.now(TST).strftime("%Y-%m-%d %H:%M TST")
                        update_snapshot_in_thesis(saved_path, t_metrics, update_time)
                    logger.info(f"  ✅ 新 thesis 已建立：{saved_path.name}")
                except Exception as e:
                    logger.error(f"  研究 {t_ticker} 失敗：{e}")
        except Exception as e:
            logger.warning(f"Task 5 自動研究失敗（不影響主報告）：{e}")

    logger.info("=" * 55)
    if errors:
        logger.error(f"完成，但有 {len(errors)} 個錯誤：")
        for e in errors:
            logger.error(f"  • {e}")
    else:
        logger.info("✅ 所有報告生成完畢！")
        logger.info(f"   報告目錄：{reports_dir.resolve()}")

    # ── Git 同步（執行後 push）──
    if sync_cfg.get("enabled") and sync_cfg.get("auto_push", True):
        logger.info("── Git 同步（push）─────────────────────")
        today = datetime.now(TST).strftime("%Y-%m-%d")
        sync.push(BASE_DIR, f"report: {today}")

    logger.info("=" * 55)
    _release_lock()
    if errors:
        _release_lock()  # 確保 exit 前釋放
        sys.exit(1)


# ── Enrich 模式：補充現有 thesis 質化深度 ──────────────
def run_enrich_theses(only_tickers: list[str] | None = None) -> None:
    """對現有 thesis 補充深度質化分析（一次性執行）。
    only_tickers: 若指定，只處理這些代碼；否則處理所有 thesis 檔案。
    """
    config      = load_config()
    claude_cli  = config.get("claude_cli", "claude")
    claude_model= config.get("claude_model", "")
    timeout     = config.get("claude_timeout_seconds", 300)
    stream_output = config.get("stream_claude_output", False)
    thesis_dir  = BASE_DIR / "thesis"
    logs_dir    = BASE_DIR / config.get("logs_dir", "logs")
    portfolio_path = BASE_DIR / config.get("portfolio_file", "portfolio.json")

    setup_logging(logs_dir)
    logger.info("=" * 55)
    if only_tickers:
        logger.info(f"  Thesis Enrichment 模式（指定：{', '.join(only_tickers)}）")
    else:
        logger.info("  Thesis Enrichment 模式（全部）")
    logger.info("=" * 55)

    portfolio = load_portfolio(portfolio_path)
    # 建立 ticker → market 映射
    market_map: dict[str, str] = {}
    for pos in portfolio.get("long_term", {}).get("positions", []) + \
                portfolio.get("tactical", {}).get("positions", []):
        market_map[pos["ticker"]] = pos["market"]
    for w in portfolio.get("watchlist", []):
        market_map[w["ticker"]] = w["market"]

    today_str   = datetime.now(TST).strftime("%Y-%m-%d")
    update_time = datetime.now(TST).strftime("%Y-%m-%d %H:%M TST")
    usd_twd     = fetch_usd_twd_rate()

    _SKIP = {"README", "CHANGELOG", "LICENSE", "TODO", "NOTES", "INDEX"}

    # 決定要處理的檔案清單
    if only_tickers:
        files_to_process = []
        for t in only_tickers:
            f = thesis_dir / f"{t}.md"
            if f.exists():
                files_to_process.append(f)
            else:
                logger.warning(f"  找不到 thesis/{t}.md，跳過")
    else:
        files_to_process = [
            f for f in sorted(thesis_dir.glob("*.md"))
            if f.stem.upper() not in _SKIP
        ]

    for thesis_file in files_to_process:
        ticker = thesis_file.stem
        market = market_map.get(ticker, "US" if not ticker.isdigit() else "TW")
        name   = ticker  # fallback; Claude will refine

        logger.info(f"── 補充 {ticker}.md ─────────────────")
        try:
            current_thesis = thesis_file.read_text(encoding="utf-8")
            articles  = fetch_stock_news(ticker, market=market, max_articles=8)
            fund_data = fetch_fundamentals([(ticker, market)])
            price_data = fetch_current_prices([(ticker, market)])
            price = price_data.get(ticker, {}).get("price")

            prompt = build_enrich_prompt(
                ticker=ticker, name=name, market=market,
                current_thesis=current_thesis,
                news_articles=articles,
                fundamentals=fund_data.get(ticker, {}),
                price=price, usd_twd=usd_twd, today=today_str,
            )
            logger.info(f"   Prompt 長度：{len(prompt):,} 字元")
            enriched = call_claude(prompt, claude_cli, claude_model, timeout, stream=stream_output)

            # 驗證輸出：第一個字元必須是 '#'
            enriched_stripped = enriched.strip()
            if not enriched_stripped.startswith("#"):
                logger.error(
                    f"  ❌ {ticker}.md 補充失敗：Claude 輸出不是有效的 Markdown 文件\n"
                    f"     輸出開頭（前150字）：{enriched_stripped[:150]!r}\n"
                    f"     原始檔案未修改。"
                )
                continue

            thesis_file.write_text(enriched_stripped + "\n", encoding="utf-8")

            # 重新寫入快照（enriched 內容覆蓋了原快照）
            metrics = fund_data.get(ticker, {})
            if metrics:
                update_snapshot_in_thesis(thesis_file, metrics, update_time)

            logger.info(f"  ✅ 已補充：{ticker}.md")
        except Exception as e:
            logger.error(f"  補充 {ticker} 失敗：{e}")

    logger.info("=" * 55)
    logger.info("✅ Thesis Enrichment 完成")
    logger.info("=" * 55)


def run_research_only(session: str = "morning") -> None:
    """讀取今日已生成的報告，單獨執行 Task 5 自動研究新標的。"""
    config       = load_config()
    claude_cli   = config.get("claude_cli", "claude")
    claude_model = config.get("claude_model", "")
    timeout      = config.get("claude_timeout_seconds", 300)
    stream_output = config.get("stream_claude_output", False)
    reports_dir  = BASE_DIR / config.get("reports_dir", "reports")
    logs_dir     = BASE_DIR / config.get("logs_dir", "logs")
    thesis_dir   = BASE_DIR / "thesis"
    thesis_cfg   = config.get("thesis", {})
    max_per_day  = thesis_cfg.get("max_per_day", 3)

    setup_logging(logs_dir)
    logger.info("=" * 55)
    logger.info(f"  Task 5 獨立執行（{session} session）")
    logger.info("=" * 55)

    # 讀取今日已生成的報告
    today_str  = datetime.now(TST).strftime("%Y%m%d")
    prefix     = f"{today_str}_{session}"
    portfolio_path_report = reports_dir / f"{prefix}_portfolio_analysis.md"
    market_path_report    = reports_dir / f"{prefix}_market_overview.md"

    portfolio_content = portfolio_path_report.read_text(encoding="utf-8") if portfolio_path_report.exists() else ""
    market_content    = market_path_report.read_text(encoding="utf-8")    if market_path_report.exists()    else ""

    if not portfolio_content and not market_content:
        logger.error(f"  找不到今日 {session} 報告（{prefix}_*.md），請先執行完整分析")
        return

    logger.info(f"  portfolio_analysis：{'✅' if portfolio_content else '❌ 未找到'}")
    logger.info(f"  market_overview   ：{'✅' if market_content    else '❌ 未找到'}")

    usd_twd = fetch_usd_twd_rate()

    try:
        existing_tickers = {f.stem for f in thesis_dir.glob("*.md")}
        today_label = datetime.now(TST).strftime("%Y-%m-%d")
        candidate_prompt = build_candidate_prompt(
            market_content=market_content,
            portfolio_content=portfolio_content,
            existing_tickers=existing_tickers,
            today=today_label,
            session=session,
            max_candidates=max_per_day,
        )
        logger.info(f"   Candidate Prompt 長度：{len(candidate_prompt):,} 字元")
        candidate_response = call_claude(candidate_prompt, claude_cli, claude_model, timeout, stream=stream_output)
        candidates = parse_candidates(candidate_response)[:max_per_day]

        if not candidates:
            logger.info("  ℹ️ 今日無新研究標的")
        else:
            logger.info(f"  識別到 {len(candidates)} 個候選（上限 {max_per_day}）：{', '.join(c['ticker'] for c in candidates)}")
            for c in candidates:
                t_ticker = c["ticker"]
                t_name   = c["name"]
                t_market = c.get("market", "US")
                t_reason = c.get("reason", "")
                logger.info(f"  ── 研究 {t_ticker}（{t_name}）────")
                try:
                    t_articles   = fetch_stock_news(t_ticker, market=t_market, max_articles=8)
                    t_fund_data  = fetch_fundamentals([(t_ticker, t_market)])
                    t_price_data = fetch_current_prices([(t_ticker, t_market)])
                    t_price      = t_price_data.get(t_ticker, {}).get("price")
                    research_prompt = build_research_prompt(
                        ticker=t_ticker, name=t_name, market=t_market,
                        reason=t_reason,
                        news_articles=t_articles,
                        fundamentals=t_fund_data.get(t_ticker, {}),
                        price=t_price, usd_twd=usd_twd, today=today_label,
                    )
                    logger.info(f"     Research Prompt 長度：{len(research_prompt):,} 字元")
                    research_content = call_claude(research_prompt, claude_cli, claude_model, timeout, stream=stream_output)
                    saved_path = save_research_thesis(research_content, t_ticker, thesis_dir)
                    t_metrics = t_fund_data.get(t_ticker, {})
                    if t_metrics:
                        update_time = datetime.now(TST).strftime("%Y-%m-%d %H:%M TST")
                        update_snapshot_in_thesis(saved_path, t_metrics, update_time)
                    logger.info(f"  ✅ 新 thesis 已建立：{saved_path.name}")
                except Exception as e:
                    logger.error(f"  研究 {t_ticker} 失敗：{e}")
    except Exception as e:
        logger.error(f"Task 5 執行失敗：{e}")

    logger.info("=" * 55)
    logger.info("✅ Task 5 完成")
    logger.info("=" * 55)


def run_update_thesis(session: str = "morning") -> None:
    """讀取今日已生成的報告，單獨執行 Task 4 thesis 自動更新。"""
    config       = load_config()
    claude_cli   = config.get("claude_cli", "claude")
    claude_model = config.get("claude_model", "")
    timeout      = config.get("claude_timeout_seconds", 300)
    stream_output = config.get("stream_claude_output", False)
    reports_dir  = BASE_DIR / config.get("reports_dir", "reports")
    logs_dir     = BASE_DIR / config.get("logs_dir", "logs")
    thesis_dir   = BASE_DIR / "thesis"

    setup_logging(logs_dir)
    logger.info("=" * 55)
    logger.info(f"  Task 4 獨立執行（{session} session）")
    logger.info("=" * 55)

    # 讀取今日已生成的報告
    today_str  = datetime.now(TST).strftime("%Y%m%d")
    prefix     = f"{today_str}_{session}"
    portfolio_path_report = reports_dir / f"{prefix}_portfolio_analysis.md"
    market_path_report    = reports_dir / f"{prefix}_market_overview.md"

    portfolio_content = portfolio_path_report.read_text(encoding="utf-8") if portfolio_path_report.exists() else ""
    market_content    = market_path_report.read_text(encoding="utf-8")    if market_path_report.exists()    else ""

    if not portfolio_content and not market_content:
        logger.error(f"  找不到今日 {session} 報告（{prefix}_*.md），請先執行完整分析")
        return

    logger.info(f"  portfolio_analysis：{'✅' if portfolio_content else '❌ 未找到'}")
    logger.info(f"  market_overview   ：{'✅' if market_content    else '❌ 未找到'}")

    try:
        # 從報告文字中提取曾被分析的 ticker（只更新有 thesis 的那幾份）
        cfg_news = config.get("news_sources", {})
        portfolio_obj = load_portfolio(BASE_DIR / config.get("portfolio_file", "portfolio.json"))
        lt_pos  = portfolio_obj.get("long_term", {}).get("positions", [])
        ta_pos  = portfolio_obj.get("tactical",  {}).get("positions", [])
        wl      = portfolio_obj.get("watchlist", [])
        report_tickers = (
            {pos["ticker"] for pos in lt_pos + ta_pos}
            | {w["ticker"] for w in wl}
            | set(cfg_news.get("market_extra_tickers", []))
        )
        theses = {
            stem: (thesis_dir / f"{stem}.md").read_text(encoding="utf-8")
            for stem in report_tickers
            if (thesis_dir / f"{stem}.md").exists()
        }
        logger.info(
            f"   今日分析 {len(report_tickers)} 個 ticker，"
            f"其中 {len(theses)} 個有 thesis：{', '.join(sorted(theses))}"
        )
        if not theses:
            logger.info("  ℹ️ 今日分析的 ticker 無對應 thesis")
            return

        update_prompt = build_thesis_prompt(
            theses, portfolio_content, market_content, session=session
        )
        logger.info(f"   Prompt 長度：{len(update_prompt):,} 字元")
        thesis_response = call_claude(update_prompt, claude_cli, claude_model, timeout, stream=stream_output)
        updated, alerts = save_theses(thesis_response, thesis_dir)

        if updated:
            logger.info(f"  ✅ 更新了 {len(updated)} 個 thesis：{', '.join(updated)}")
        else:
            logger.info("  ℹ️ 今日無 thesis 更新")

        for ticker, alert_text in alerts.items():
            logger.warning("  " + "!" * 50)
            logger.warning(f"  ⚠️  重大質化事件警報：{ticker}")
            logger.warning(f"  {alert_text}")
            logger.warning("  請手動重新評估此 thesis 的策略部分")
            logger.warning("  " + "!" * 50)
    except Exception as e:
        logger.error(f"Task 4 執行失敗：{e}")

    logger.info("=" * 55)
    logger.info("✅ Task 4 完成")
    logger.info("=" * 55)


# ── CLI 入口 ──────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="每日財務報告生成器")
    parser.add_argument("--portfolio",     action="store_true", help="只執行持倉分析（Task 1）")
    parser.add_argument("--market",        action="store_true", help="只執行市場總覽（Task 2）")
    parser.add_argument("--validate",      action="store_true", help="只做 schema 驗證，不生成報告")
    parser.add_argument("--enrich-thesis", action="store_true", help="對所有現有 thesis 補充深度質化分析")
    parser.add_argument("--research",       action="store_true", help="讀取今日已生成報告，單獨執行 Task 5 自動研究新標的")
    parser.add_argument("--update-thesis",  action="store_true", help="讀取今日已生成報告，單獨執行 Task 4 thesis 自動更新")
    parser.add_argument(
        "--enrich-ticker",
        nargs="+",
        metavar="TICKER",
        help="只對指定代碼的 thesis 補充質化分析，例如：--enrich-ticker NET ALAB",
    )
    parser.add_argument(
        "--session",
        choices=["morning", "evening"],
        default="morning",
        help="執行時段：morning（07:00 台股盤前）或 evening（18:00 台股盤後），預設 morning",
    )
    args = parser.parse_args()

    if args.validate:
        config = load_config()
        portfolio_path = BASE_DIR / config.get("portfolio_file", "portfolio.json")
        validate_portfolio(portfolio_path)
        return

    if args.enrich_thesis:
        run_enrich_theses()
        return

    if args.enrich_ticker:
        run_enrich_theses(only_tickers=args.enrich_ticker)
        return

    if args.research:
        run_research_only(session=args.session)
        return

    if args.update_thesis:
        run_update_thesis(session=args.session)
        return

    if args.portfolio and not args.market:
        run(run_portfolio=True, run_market=False, session=args.session)
    elif args.market and not args.portfolio:
        run(run_portfolio=False, run_market=True, session=args.session)
    else:
        run(run_portfolio=True, run_market=True, session=args.session)


if __name__ == "__main__":
    main()
