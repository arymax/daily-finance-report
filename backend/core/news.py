"""
news.py — 個股 + 市場新聞抓取

新聞來源：yfinance (v1.2+) + Yahoo Finance RSS + 市場 RSS feeds
"""

import re
import time
import logging
from datetime import datetime

import feedparser
import yfinance as yf

logger = logging.getLogger(__name__)


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _yf_ticker(ticker: str, market: str) -> str:
    """將用戶 ticker 轉為 yfinance 可識別的代碼。"""
    if market == "TW":
        return f"{ticker}.TW"
    return ticker


def fetch_stock_news(ticker: str, market: str = "US", max_articles: int = 5) -> list:
    """
    抓取個股 / ETF 最新新聞。
    market: "TW" | "US"（台股自動加 .TW suffix）
    回傳 list of {title, publisher, time, summary, link}
    """
    articles = []
    yf_t = _yf_ticker(ticker, market)

    # --- 來源 1：yfinance (v1.2+，資料在 content 子層) ---
    try:
        stock = yf.Ticker(yf_t)
        for item in (stock.news or [])[:max_articles]:
            c = item.get("content", {}) or {}
            title = c.get("title", "").strip()
            if not title:
                continue
            summary = _strip_html(c.get("summary", ""))[:300]
            pub_date = c.get("pubDate", "") or c.get("displayTime", "")
            try:
                pub_str = datetime.strptime(pub_date, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M")
            except Exception:
                pub_str = pub_date[:16] if pub_date else "—"
            provider = (c.get("provider") or {})
            publisher = provider.get("displayName", "")
            link = ((c.get("canonicalUrl") or c.get("clickThroughUrl") or {}).get("url", ""))
            articles.append({"title": title, "publisher": publisher,
                              "time": pub_str, "summary": summary, "link": link})
    except Exception as e:
        logger.warning(f"yfinance news failed [{yf_t}]: {e}")

    # --- 來源 2：Yahoo Finance RSS 補充 ---
    remaining = max_articles - len(articles)
    if remaining > 0:
        try:
            region = "TW" if market == "TW" else "US"
            lang   = "zh-Hant-TW" if market == "TW" else "en-US"
            rss_url = (
                f"https://feeds.finance.yahoo.com/rss/2.0/headline"
                f"?s={yf_t}&region={region}&lang={lang}"
            )
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:remaining]:
                articles.append({
                    "title":     entry.get("title", "").strip(),
                    "publisher": "Yahoo Finance",
                    "time":      entry.get("published", "—"),
                    "summary":   _strip_html(entry.get("summary", ""))[:300],
                    "link":      entry.get("link", ""),
                })
        except Exception as e:
            logger.warning(f"Yahoo RSS failed [{yf_t}]: {e}")

    logger.info(f"  [{ticker}/{market}] {len(articles)} news articles")
    return articles


def fetch_market_news(sources: list = None, max_articles: int = 15) -> list:
    """從 RSS feeds 抓取美股市場整體新聞。"""
    default_sources = [
        "https://finance.yahoo.com/rss/topfinstories",
        "https://feeds.reuters.com/reuters/businessNews",
        "https://feeds.marketwatch.com/marketwatch/topstories/",
    ]
    sources = sources or default_sources
    per_source = max(3, max_articles // len(sources))
    articles = []

    for url in sources:
        try:
            feed = feedparser.parse(url)
            source_name = feed.feed.get("title", url.split("/")[2])
            for entry in feed.entries[:per_source]:
                summary = _strip_html(entry.get("summary", ""))
                articles.append({
                    "title":     entry.get("title", "").strip(),
                    "summary":   summary[:400],
                    "published": entry.get("published", ""),
                    "source":    source_name,
                    "link":      entry.get("link", ""),
                })
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Market RSS failed ({url}): {e}")

    logger.info(f"  [market] {len(articles)} articles from {len(sources)} sources")
    return articles
