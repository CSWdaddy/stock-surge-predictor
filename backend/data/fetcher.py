from typing import Optional, Dict, List

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


def fetch_stock_data(ticker: str, period: str = "3mo") -> Optional[pd.DataFrame]:
    """Fetch historical stock data from Yahoo Finance."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty:
            return None
        return df
    except Exception:
        return None


def fetch_stock_info(ticker: str) -> dict:
    """Fetch stock info (name, sector, market cap, etc.)."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "ticker": ticker,
            "name": info.get("shortName", ticker),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap", 0),
            "current_price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
            "previous_close": info.get("previousClose", 0),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh", 0),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow", 0),
            "avg_volume": info.get("averageVolume", 0),
        }
    except Exception:
        return {"ticker": ticker, "name": ticker}


def fetch_multiple_stocks(tickers: List[str], period: str = "3mo") -> Dict[str, pd.DataFrame]:
    """Fetch data for multiple stocks."""
    results = {}
    for ticker in tickers:
        df = fetch_stock_data(ticker, period)
        if df is not None and not df.empty:
            results[ticker] = df
    return results
