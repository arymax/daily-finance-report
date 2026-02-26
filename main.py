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
import tempfile
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

# ── 時區 ──────────────────────────────────────
TST = timezone(timedelta(hours=8))
BASE_DIR = Path(__file__).parent

logger = logging.getLogger(__name__)


# ── Claude CLI 呼叫 ────────────────────────────
def call_claude(prompt: str, claude_cli: str, model: str, timeout: int) -> str:
    """
    透過 subprocess 呼叫本地 Claude CLI（stdin 模式）。
    移除 CLAUDECODE 環境變數，避免巢狀 session 錯誤。
    """
    cmd = [claude_cli, "--print", "--dangerously-skip-permissions"]
    if model:
        cmd += ["--model", model]

    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE", None)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(prompt)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "r", encoding="utf-8") as stdin_file:
            result = subprocess.run(
                cmd,
                stdin=stdin_file,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
    finally:
        os.unlink(tmp_path)

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
def run(run_portfolio: bool = True, run_market: bool = True) -> None:
    config = load_config()

    claude_cli   = config.get("claude_cli", "claude")
    claude_model = config.get("claude_model", "")
    timeout      = config.get("claude_timeout_seconds", 300)
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
    memory_dir    = BASE_DIR / memory_cfg.get("memory_dir", "memory")
    context_days  = memory_cfg.get("context_days", 5)

    setup_logging(logs_dir)

    logger.info("=" * 55)
    logger.info("   Daily Finance Report — 啟動")
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

    # ── 載入歷史記憶 context ──
    memory_context = ""
    if memory_cfg.get("enabled", True):
        memory_context = mem.load_context(memory_dir, days=context_days)

    errors = []
    portfolio_content = ""
    market_content    = ""

    # ── Task 1：持倉分析 ──
    if run_portfolio:
        logger.info("── Task 1：持倉分析與操作建議 ───────")
        try:
            prompt = build_portfolio_prompt(
                portfolio, news_by_ticker, prices, usd_twd,
                memory_context=memory_context,
            )
            logger.info(f"   Prompt 長度：{len(prompt):,} 字元")
            portfolio_content = call_claude(prompt, claude_cli, claude_model, timeout)
            save_report(portfolio_content, "portfolio_analysis", reports_dir)
        except Exception as e:
            logger.error(f"持倉分析失敗：{e}")
            errors.append(str(e))

    # ── Task 2：市場總覽 ──
    if run_market:
        logger.info("── Task 2：昨晚美股市場總覽 ──────────")
        try:
            prompt = build_market_prompt(
                market_news, watchlist, extra_news_by_ticker,
                memory_context=memory_context,
            )
            logger.info(f"   Prompt 長度：{len(prompt):,} 字元")
            market_content = call_claude(prompt, claude_cli, claude_model, timeout)
            save_report(market_content, "market_overview", reports_dir)
        except Exception as e:
            logger.error(f"市場總覽失敗：{e}")
            errors.append(str(e))

    # ── Task 3：生成記憶摘要 ──
    if memory_cfg.get("enabled", True) and memory_cfg.get("generate_summary", True):
        if portfolio_content or market_content:
            logger.info("── Task 3：生成記憶摘要 ───────────────")
            try:
                summary_prompt = mem.generate_summary(portfolio_content, market_content)
                summary = call_claude(summary_prompt, claude_cli, claude_model, timeout)
                mem.save_summary(summary, memory_dir)
            except Exception as e:
                logger.warning(f"記憶摘要生成失敗（不影響主報告）：{e}")

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
    if errors:
        sys.exit(1)


# ── CLI 入口 ──────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="每日美股財務報告生成器")
    parser.add_argument("--portfolio", action="store_true", help="只執行持倉分析（Task 1）")
    parser.add_argument("--market",    action="store_true", help="只執行市場總覽（Task 2）")
    parser.add_argument("--validate",  action="store_true", help="只做 schema 驗證，不生成報告")
    args = parser.parse_args()

    if args.validate:
        config = load_config()
        portfolio_path = BASE_DIR / config.get("portfolio_file", "portfolio.json")
        validate_portfolio(portfolio_path)
        return

    if args.portfolio and not args.market:
        run(run_portfolio=True, run_market=False)
    elif args.market and not args.portfolio:
        run(run_portfolio=False, run_market=True)
    else:
        run(run_portfolio=True, run_market=True)


if __name__ == "__main__":
    main()
