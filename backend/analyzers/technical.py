import pandas as pd
import numpy as np


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index."""
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(df: pd.DataFrame) -> dict:
    """Calculate MACD, Signal line, and Histogram."""
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram,
    }


def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> dict:
    """Calculate Bollinger Bands."""
    sma = df["Close"].rolling(window=period).mean()
    std = df["Close"].rolling(window=period).std()
    return {
        "upper": sma + (std * std_dev),
        "middle": sma,
        "lower": sma - (std * std_dev),
    }


def calculate_obv(df: pd.DataFrame) -> pd.Series:
    """Calculate On Balance Volume."""
    obv = pd.Series(0.0, index=df.index)
    for i in range(1, len(df)):
        if df["Close"].iloc[i] > df["Close"].iloc[i - 1]:
            obv.iloc[i] = obv.iloc[i - 1] + df["Volume"].iloc[i]
        elif df["Close"].iloc[i] < df["Close"].iloc[i - 1]:
            obv.iloc[i] = obv.iloc[i - 1] - df["Volume"].iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i - 1]
    return obv


def calculate_volume_ratio(df: pd.DataFrame, period: int = 20) -> float:
    """Calculate current volume vs average volume ratio."""
    if len(df) < period:
        return 1.0
    avg_vol = df["Volume"].iloc[-period:].mean()
    if avg_vol == 0:
        return 1.0
    return df["Volume"].iloc[-1] / avg_vol


def analyze_technical(df: pd.DataFrame) -> dict:
    """Run full technical analysis and return scores + indicators."""
    if df is None or len(df) < 30:
        return {"score": 0, "signals": [], "indicators": {}}

    signals = []
    score = 50  # neutral starting point

    # RSI Analysis
    rsi = calculate_rsi(df)
    current_rsi = rsi.iloc[-1] if not rsi.empty else 50
    if current_rsi < 30:
        signals.append({"type": "bullish", "indicator": "RSI", "message": f"RSI oversold at {current_rsi:.1f}"})
        score += 15
    elif current_rsi < 40:
        signals.append({"type": "bullish", "indicator": "RSI", "message": f"RSI approaching oversold at {current_rsi:.1f}"})
        score += 8
    elif current_rsi > 70:
        signals.append({"type": "bearish", "indicator": "RSI", "message": f"RSI overbought at {current_rsi:.1f}"})
        score -= 10

    # MACD Analysis
    macd = calculate_macd(df)
    if len(macd["histogram"]) >= 2:
        current_hist = macd["histogram"].iloc[-1]
        prev_hist = macd["histogram"].iloc[-2]
        if current_hist > 0 and prev_hist <= 0:
            signals.append({"type": "bullish", "indicator": "MACD", "message": "MACD bullish crossover"})
            score += 15
        elif current_hist > prev_hist and current_hist > 0:
            signals.append({"type": "bullish", "indicator": "MACD", "message": "MACD momentum increasing"})
            score += 8

    # Bollinger Bands
    bb = calculate_bollinger_bands(df)
    current_price = df["Close"].iloc[-1]
    if not pd.isna(bb["lower"].iloc[-1]):
        bb_position = (current_price - bb["lower"].iloc[-1]) / (bb["upper"].iloc[-1] - bb["lower"].iloc[-1] + 1e-10)
        if bb_position < 0.1:
            signals.append({"type": "bullish", "indicator": "Bollinger", "message": "Price near lower Bollinger Band"})
            score += 12
        elif bb_position > 0.9:
            signals.append({"type": "bearish", "indicator": "Bollinger", "message": "Price near upper Bollinger Band"})
            score -= 5

    # Volume Analysis
    vol_ratio = calculate_volume_ratio(df)
    if vol_ratio > 3.0:
        signals.append({"type": "bullish", "indicator": "Volume", "message": f"Volume surge {vol_ratio:.1f}x average"})
        score += 15
    elif vol_ratio > 2.0:
        signals.append({"type": "bullish", "indicator": "Volume", "message": f"High volume {vol_ratio:.1f}x average"})
        score += 10
    elif vol_ratio > 1.5:
        signals.append({"type": "neutral", "indicator": "Volume", "message": f"Above avg volume {vol_ratio:.1f}x"})
        score += 5

    # OBV trend
    obv = calculate_obv(df)
    if len(obv) >= 5:
        obv_trend = obv.iloc[-1] - obv.iloc[-5]
        if obv_trend > 0:
            signals.append({"type": "bullish", "indicator": "OBV", "message": "OBV trending up"})
            score += 5

    # Price momentum (5-day)
    if len(df) >= 5:
        momentum = (df["Close"].iloc[-1] / df["Close"].iloc[-5] - 1) * 100
        if momentum > 5:
            signals.append({"type": "bullish", "indicator": "Momentum", "message": f"5-day momentum +{momentum:.1f}%"})
            score += 8

    score = max(0, min(100, score))

    return {
        "score": round(score, 1),
        "signals": signals,
        "indicators": {
            "rsi": round(float(current_rsi), 2) if not pd.isna(current_rsi) else None,
            "macd_histogram": round(float(macd["histogram"].iloc[-1]), 4) if not pd.isna(macd["histogram"].iloc[-1]) else None,
            "volume_ratio": round(vol_ratio, 2),
            "current_price": round(float(current_price), 2),
        }
    }
