"""
prices.py — 即時股價 + 匯率查詢

股價來源：yfinance fast_info（TW 加 .TW suffix；crypto 用 BTC-USD 格式）
"""

import logging

import yfinance as yf

from .news import _yf_ticker

logger = logging.getLogger(__name__)

# 加密貨幣 ticker → yfinance 代碼對應
_CRYPTO_YF_MAP = {
    "BTC": "BTC-USD", "ETH": "ETH-USD", "XRP": "XRP-USD",
    "SOL": "SOL-USD", "BNB": "BNB-USD", "ADA": "ADA-USD",
}
# 穩定幣不需抓價格（永遠約 1 USD）
_STABLECOINS = {"USDT", "USDC", "DAI", "BUSD"}


def fetch_usd_twd_rate() -> float:
    """
    查詢即時 USD/TWD 匯率（1 USD = ? TWD）。
    失敗時 fallback 到 32.0。
    """
    try:
        fi = yf.Ticker("TWD=X").fast_info
        rate = fi.last_price
        if rate and rate > 1:
            logger.info(f"  [FX] USD/TWD = {rate:.2f}")
            return float(rate)
    except Exception as e:
        logger.warning(f"USD/TWD fetch failed: {e}")
    return 32.0


def fetch_52w_high(ticker: str, market: str) -> float | None:
    """
    查詢單一標的的 52 週最高價。
    使用 yfinance .info（fast_info 不含此數據）。
    失敗時回傳 None。
    """
    yf_t = _yf_ticker(ticker, market)
    try:
        info = yf.Ticker(yf_t).info
        high = info.get("fiftyTwoWeekHigh")
        if high and float(high) > 0:
            logger.info(f"  [52w] {ticker} 52週高點 = {high:.2f}")
            return float(high)
    except Exception as e:
        logger.warning(f"  [52w] {ticker} 52週高點查詢失敗：{e}")
    return None


def fetch_current_prices(positions_with_market: list) -> dict:
    """
    批次查詢股票 / ETF / 加密貨幣即時價格。

    positions_with_market: list of (ticker, market)
        market = "TW" | "US" | "CRYPTO"

    回傳 dict:
        { ticker: {"price": float, "currency": str} }

    注意：
    - TW 市場：price 單位為 TWD
    - US 市場：price 單位為 USD
    - CRYPTO：price 單位為 USD（穩定幣跳過）
    """
    prices = {}

    for ticker, market in positions_with_market:
        if market == "CRYPTO":
            if ticker in _STABLECOINS:
                prices[ticker] = {"price": 1.0, "currency": "USD"}
                continue
            yf_t = _CRYPTO_YF_MAP.get(ticker, f"{ticker}-USD")
            currency = "USD"
        else:
            yf_t = _yf_ticker(ticker, market)
            currency = "TWD" if market == "TW" else "USD"

        try:
            fi = yf.Ticker(yf_t).fast_info
            price = fi.last_price
            if price and price > 0:
                prices[ticker] = {"price": float(price), "currency": currency}
                logger.info(f"  [price] {ticker} = {price:.4f} {currency}")
        except Exception as e:
            logger.warning(f"Price fetch failed [{ticker}]: {e}")

    return prices
