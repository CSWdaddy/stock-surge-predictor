from typing import Optional, List, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from analyzers.technical import calculate_rsi, calculate_macd, calculate_volume_ratio
from data.fetcher import fetch_stock_data
import pickle
import threading
from pathlib import Path

MODEL_PATH = Path(__file__).parent / "trained_model.pkl"

# In-memory model cache
_model = None
_model_lock = threading.Lock()
_training_in_progress = False


def _load_model():
    """Load model from disk into memory cache."""
    global _model
    if MODEL_PATH.exists():
        with open(MODEL_PATH, "rb") as f:
            _model = pickle.load(f)


def extract_features(df: pd.DataFrame) -> Optional[np.ndarray]:
    """Extract ML features from stock data."""
    if df is None or len(df) < 30:
        return None

    rsi = calculate_rsi(df)
    macd = calculate_macd(df)
    vol_ratio = calculate_volume_ratio(df)

    current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
    macd_hist = macd["histogram"].iloc[-1] if not pd.isna(macd["histogram"].iloc[-1]) else 0

    ret_5 = (df["Close"].iloc[-1] / df["Close"].iloc[-5] - 1) * 100 if len(df) >= 5 else 0
    ret_10 = (df["Close"].iloc[-1] / df["Close"].iloc[-10] - 1) * 100 if len(df) >= 10 else 0

    volatility = df["Close"].pct_change().iloc[-20:].std() * 100 if len(df) >= 20 else 0

    vol_5 = df["Volume"].iloc[-5:].mean()
    vol_20 = df["Volume"].iloc[-20:].mean()
    vol_trend = vol_5 / vol_20 if vol_20 > 0 else 1

    features = np.array([
        current_rsi,
        macd_hist,
        vol_ratio,
        ret_5,
        ret_10,
        volatility,
        vol_trend,
    ]).reshape(1, -1)

    return features


def build_training_data(tickers: List[str]) -> Tuple[np.ndarray, np.ndarray]:
    """Build training dataset from historical data.

    Label: 1 if stock surged >5% in next 5 days, 0 otherwise.
    """
    all_features = []
    all_labels = []

    for ticker in tickers:
        try:
            df = fetch_stock_data(ticker, period="1y")
            if df is None or len(df) < 60:
                continue

            for i in range(30, len(df) - 5):
                window = df.iloc[:i]
                future = df.iloc[i:i + 5]

                rsi = calculate_rsi(window)
                macd = calculate_macd(window)

                current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
                macd_hist = macd["histogram"].iloc[-1] if not pd.isna(macd["histogram"].iloc[-1]) else 0

                ret_5 = (window["Close"].iloc[-1] / window["Close"].iloc[-5] - 1) * 100
                ret_10 = (window["Close"].iloc[-1] / window["Close"].iloc[-10] - 1) * 100

                vol = window["Close"].pct_change().iloc[-20:].std() * 100
                vol_5 = window["Volume"].iloc[-5:].mean()
                vol_20 = window["Volume"].iloc[-20:].mean()
                vol_trend = vol_5 / vol_20 if vol_20 > 0 else 1
                vol_ratio = window["Volume"].iloc[-1] / vol_20 if vol_20 > 0 else 1

                features = [current_rsi, macd_hist, vol_ratio, ret_5, ret_10, vol, vol_trend]

                future_max = future["Close"].max()
                current = window["Close"].iloc[-1]
                surged = 1 if (future_max / current - 1) > 0.05 else 0

                all_features.append(features)
                all_labels.append(surged)

        except Exception:
            continue

    if not all_features:
        return np.array([]), np.array([])
    return np.array(all_features), np.array(all_labels)


def train_model(tickers: Optional[List[str]] = None) -> dict:
    """Train the surge prediction model."""
    global _model, _training_in_progress

    if _training_in_progress:
        return {"status": "already_training", "message": "Training is already in progress"}

    _training_in_progress = True
    try:
        if tickers is None:
            tickers = [
                "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "AMD", "META", "NFLX", "PLTR",
                "JPM", "BA", "DIS", "COIN", "SQ", "SHOP", "CRWD", "NET", "SNOW", "SOFI",
            ]

        X, y = build_training_data(tickers)

        if len(X) < 50:
            return {"status": "error", "message": "Insufficient training data"}

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        model.fit(X_train, y_train)

        accuracy = model.score(X_test, y_test)

        with open(MODEL_PATH, "wb") as f:
            pickle.dump(model, f)

        with _model_lock:
            _model = model

        return {
            "status": "success",
            "accuracy": round(accuracy, 3),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "surge_ratio": round(float(y.mean()), 3),
        }
    finally:
        _training_in_progress = False


def train_model_background():
    """Train model in a background thread."""
    thread = threading.Thread(target=train_model, daemon=True)
    thread.start()


def predict_surge(ticker: str) -> float:
    """Predict surge probability for a ticker. Returns probability 0-100."""
    global _model

    # Load from disk on first call
    if _model is None:
        _load_model()

    if _model is None:
        return 50.0  # no model yet

    df = fetch_stock_data(ticker, period="3mo")
    features = extract_features(df)

    if features is None:
        return 50.0

    try:
        with _model_lock:
            proba = _model.predict_proba(features)
        surge_prob = proba[0][1] * 100 if proba.shape[1] > 1 else 50.0
        return round(surge_prob, 1)
    except Exception:
        return 50.0


def is_model_trained() -> bool:
    """Check if a trained model exists."""
    return MODEL_PATH.exists() or _model is not None
