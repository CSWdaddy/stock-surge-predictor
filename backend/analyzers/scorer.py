from typing import List

from analyzers.technical import analyze_technical
from analyzers.sentiment import get_combined_sentiment
from data.fetcher import fetch_stock_data, fetch_stock_info
import pandas as pd


def calculate_volume_momentum_score(df: pd.DataFrame) -> float:
    """Calculate volume/momentum component score (0-100)."""
    if df is None or len(df) < 20:
        return 50.0

    score = 50.0

    # Volume trend (5-day avg vs 20-day avg)
    vol_5 = df["Volume"].iloc[-5:].mean()
    vol_20 = df["Volume"].iloc[-20:].mean()
    if vol_20 > 0:
        vol_trend = vol_5 / vol_20
        if vol_trend > 2.0:
            score += 20
        elif vol_trend > 1.5:
            score += 12
        elif vol_trend > 1.2:
            score += 5

    # Price momentum
    if len(df) >= 10:
        mom_5 = (df["Close"].iloc[-1] / df["Close"].iloc[-5] - 1) * 100
        mom_10 = (df["Close"].iloc[-1] / df["Close"].iloc[-10] - 1) * 100

        if mom_5 > 3:
            score += 10
        if mom_10 > 5:
            score += 8

        # Accelerating momentum
        if mom_5 > mom_10 / 2 and mom_5 > 0:
            score += 5

    # Price vs 52-week range position
    if len(df) >= 50:
        high_52 = df["Close"].max()
        low_52 = df["Close"].min()
        range_52 = high_52 - low_52
        if range_52 > 0:
            position = (df["Close"].iloc[-1] - low_52) / range_52
            if position > 0.8:
                score += 8  # near highs, breakout potential

    return max(0, min(100, score))


def score_stock(ticker: str) -> dict:
    """Generate comprehensive score for a stock."""
    df = fetch_stock_data(ticker, period="3mo")
    info = fetch_stock_info(ticker)

    # Technical analysis (40% weight)
    technical = analyze_technical(df)
    technical_score = technical["score"]

    # Sentiment analysis (30% weight)
    sentiment = get_combined_sentiment(ticker)
    sentiment_score = sentiment["score"]

    # Volume/momentum (30% weight)
    volume_score = calculate_volume_momentum_score(df)

    # Weighted total
    total_score = (
        technical_score * 0.4 +
        sentiment_score * 0.3 +
        volume_score * 0.3
    )

    # Build price history for charts
    price_history = []
    if df is not None and not df.empty:
        for date, row in df.tail(30).iterrows():
            price_history.append({
                "date": date.strftime("%Y-%m-%d"),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })

    return {
        "ticker": ticker,
        "name": info.get("name", ticker),
        "sector": info.get("sector", "N/A"),
        "current_price": info.get("current_price", 0),
        "total_score": round(total_score, 1),
        "technical_score": round(technical_score, 1),
        "sentiment_score": round(sentiment_score, 1),
        "volume_score": round(volume_score, 1),
        "signals": technical["signals"],
        "indicators": technical["indicators"],
        "sentiment_detail": sentiment,
        "price_history": price_history,
    }


def score_multiple_stocks(tickers: List[str]) -> List[dict]:
    """Score multiple stocks and return sorted by total score."""
    results = []
    for ticker in tickers:
        try:
            result = score_stock(ticker)
            results.append(result)
        except Exception:
            continue

    results.sort(key=lambda x: x["total_score"], reverse=True)
    return results
