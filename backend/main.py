from typing import List
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

from db.database import init_db, save_prediction, get_latest_predictions
from data.screener import get_candidate_tickers
from analyzers.scorer import score_stock
from models.predictor import predict_surge, train_model

# Cache for latest predictions
_predictions_cache: List[dict] = []
_cache_lock = threading.Lock()
_last_refresh_info: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="US Stock Surge Predictor",
    description="Predicts potential stock surges using technical analysis, sentiment analysis, and ML",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _analyze_single_stock(ticker: str) -> dict:
    """Analyze a single stock (for parallel execution)."""
    try:
        result = score_stock(ticker)
        result["ml_surge_probability"] = predict_surge(ticker)
        return result
    except Exception:
        return None


@app.get("/")
def root():
    return {
        "message": "US Stock Surge Predictor API",
        "disclaimer": "This tool is for educational/reference purposes only. NOT investment advice.",
        "endpoints": {
            "/api/predictions": "GET - Surge predictions (params: limit, min_score)",
            "/api/stock/{ticker}": "GET - Single stock analysis",
            "/api/refresh": "GET - Rescan all stocks (params: max_stocks, workers)",
            "/api/train": "GET - Train ML model",
            "/api/screener-info": "GET - See screening sources and counts",
        },
    }


@app.get("/api/predictions")
def get_predictions(
    limit: int = Query(default=50, ge=1, le=200),
    min_score: float = Query(default=0, ge=0, le=100),
):
    """Get the latest surge predictions sorted by score."""
    with _cache_lock:
        if _predictions_cache:
            all_preds = _predictions_cache
            filtered = [p for p in all_preds if p["total_score"] >= min_score]
            return {
                "disclaimer": "For educational purposes only. NOT investment advice.",
                "total_analyzed": len(all_preds),
                "showing": min(limit, len(filtered)),
                "stats": {
                    "strong": sum(1 for p in all_preds if p["total_score"] >= 70),
                    "moderate": sum(1 for p in all_preds if 60 <= p["total_score"] < 70),
                    "weak": sum(1 for p in all_preds if p["total_score"] < 60),
                    "top_score": round(all_preds[0]["total_score"], 1) if all_preds else 0,
                },
                "predictions": filtered[:limit],
            }

    db_predictions = get_latest_predictions(limit)
    if db_predictions:
        return {
            "disclaimer": "For educational purposes only. NOT investment advice.",
            "predictions": db_predictions,
        }

    return {
        "disclaimer": "For educational purposes only. NOT investment advice.",
        "predictions": [],
        "message": "No predictions yet. Call /api/refresh to generate predictions.",
    }


@app.get("/api/stock/{ticker}")
def get_stock_analysis(ticker: str):
    """Get detailed analysis for a specific stock."""
    ticker = ticker.upper()
    result = score_stock(ticker)
    ml_prob = predict_surge(ticker)
    result["ml_surge_probability"] = ml_prob

    return {
        "disclaimer": "For educational purposes only. NOT investment advice.",
        "analysis": result,
    }


@app.get("/api/refresh")
def refresh_predictions(
    max_stocks: int = Query(default=0, ge=0, le=500, description="0 = analyze all candidates"),
    workers: int = Query(default=5, ge=1, le=20, description="Parallel worker threads"),
):
    """Refresh predictions by scanning candidate stocks in parallel."""
    global _predictions_cache, _last_refresh_info

    start_time = time.time()

    candidates, sources = get_candidate_tickers()
    total_candidates = len(candidates)

    if max_stocks > 0:
        candidates = candidates[:max_stocks]

    # Parallel analysis
    results = []
    failed = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_ticker = {
            executor.submit(_analyze_single_stock, t): t for t in candidates
        }
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
                else:
                    failed.append(ticker)
            except Exception:
                failed.append(ticker)

    results.sort(key=lambda x: x["total_score"], reverse=True)

    # Save to DB
    for r in results:
        try:
            save_prediction(
                ticker=r["ticker"],
                score=r["total_score"],
                technical_score=r["technical_score"],
                sentiment_score=r["sentiment_score"],
                volume_score=r["volume_score"],
                ml_prediction=r.get("ml_surge_probability", 50),
                analysis=r,
            )
        except Exception:
            pass

    elapsed = round(time.time() - start_time, 1)

    with _cache_lock:
        _predictions_cache = results
        _last_refresh_info = {
            "total_candidates": total_candidates,
            "analyzed": len(results),
            "failed": len(failed),
            "elapsed_seconds": elapsed,
            "sources": sources,
        }

    return {
        "disclaimer": "For educational purposes only. NOT investment advice.",
        "status": "refreshed",
        "scan_info": {
            "total_candidates": total_candidates,
            "analyzed": len(results),
            "failed": len(failed),
            "failed_tickers": failed,
            "elapsed_seconds": elapsed,
            "sources": sources,
        },
        "stats": {
            "strong": sum(1 for r in results if r["total_score"] >= 70),
            "moderate": sum(1 for r in results if 60 <= r["total_score"] < 70),
            "weak": sum(1 for r in results if r["total_score"] < 60),
            "top_score": round(results[0]["total_score"], 1) if results else 0,
        },
        "predictions": results[:50],
    }


@app.get("/api/screener-info")
def screener_info():
    """Show what screening sources are available and latest scan stats."""
    return {
        "sources_description": {
            "unusual_volume": "FINVIZ: Relative volume > 2x average (거래량 급증)",
            "gap_up": "FINVIZ: Gap up > 3% (갭업 종목)",
            "new_high": "FINVIZ: New 52-week high (신고가)",
            "oversold_bounce": "FINVIZ: RSI < 30 oversold (과매도 반등 후보)",
            "top_gainers": "FINVIZ: Today's top gainers > 5% (당일 급등)",
            "high_volatility": "FINVIZ: High weekly volatility > 6% (고변동성)",
            "yahoo_trending": "Yahoo Finance trending tickers",
            "default_list": "Curated list of popular US stocks across sectors",
        },
        "last_refresh": _last_refresh_info or "No refresh yet",
    }


@app.get("/api/train")
def train_ml_model():
    """Train/retrain the ML prediction model."""
    result = train_model()
    return {
        "status": result.get("status"),
        "details": result,
    }
