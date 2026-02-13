from typing import List, Dict
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

from db.database import init_db, save_prediction, get_latest_predictions
from data.screener import get_tickers_by_group
from analyzers.scorer import score_stock
from models.predictor import predict_surge, train_model, train_model_background, is_model_trained

# Per-group cache: {"all": [...], "sp500": [...], "russell": [...]}
_predictions_cache: Dict[str, List[dict]] = {}
_cache_lock = threading.Lock()
_last_refresh_info: Dict[str, dict] = {}

VALID_GROUPS = ("all", "sp500", "russell")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Auto-train ML model in background if not yet trained
    if not is_model_trained():
        train_model_background()
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


def _make_stats(results: List[dict]) -> dict:
    return {
        "strong": sum(1 for r in results if r["total_score"] >= 70),
        "moderate": sum(1 for r in results if 60 <= r["total_score"] < 70),
        "weak": sum(1 for r in results if r["total_score"] < 60),
        "top_score": round(results[0]["total_score"], 1) if results else 0,
    }


@app.get("/api/predictions")
def get_predictions(
    limit: int = Query(default=200, ge=1, le=500),
    min_score: float = Query(default=0, ge=0, le=100),
    group: str = Query(default="all"),
):
    """Get the latest surge predictions sorted by score."""
    if group not in VALID_GROUPS:
        group = "all"

    with _cache_lock:
        cached = _predictions_cache.get(group)
        if cached:
            filtered = [p for p in cached if p["total_score"] >= min_score]
            return {
                "disclaimer": "For educational purposes only. NOT investment advice.",
                "group": group,
                "total_analyzed": len(cached),
                "showing": min(limit, len(filtered)),
                "stats": _make_stats(cached),
                "predictions": filtered[:limit],
            }

    return {
        "disclaimer": "For educational purposes only. NOT investment advice.",
        "group": group,
        "predictions": [],
        "message": f"No predictions for '{group}' yet. Call /api/refresh?group={group} to generate.",
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
    group: str = Query(default="all"),
    workers: int = Query(default=8, ge=1, le=20),
):
    """Refresh predictions for a specific group."""
    if group not in VALID_GROUPS:
        group = "all"

    start_time = time.time()

    candidates, sources = get_tickers_by_group(group)
    total_candidates = len(candidates)

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
        _predictions_cache[group] = results
        _last_refresh_info[group] = {
            "total_candidates": total_candidates,
            "analyzed": len(results),
            "failed": len(failed),
            "elapsed_seconds": elapsed,
            "sources": sources,
        }

    return {
        "disclaimer": "For educational purposes only. NOT investment advice.",
        "status": "refreshed",
        "group": group,
        "scan_info": {
            "total_candidates": total_candidates,
            "analyzed": len(results),
            "failed": len(failed),
            "failed_tickers": failed,
            "elapsed_seconds": elapsed,
            "sources": sources,
        },
        "stats": _make_stats(results),
        "predictions": results,
    }


@app.get("/api/train")
def train_ml_model():
    """Train/retrain the ML prediction model."""
    result = train_model()
    return {
        "status": result.get("status"),
        "details": result,
    }


# ─── Serve Frontend Static Files ────────────────────────────────────────────
# Mount after all API routes so /api/* takes priority

FRONTEND_DIR = Path(__file__).parent / "static"

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        """Serve frontend SPA — fallback to index.html for client-side routing."""
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")
