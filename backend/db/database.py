import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "stock_predictor.db"


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            score REAL NOT NULL,
            technical_score REAL,
            sentiment_score REAL,
            volume_score REAL,
            ml_prediction REAL,
            analysis_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS stock_cache (
            ticker TEXT NOT NULL,
            data_json TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ticker)
        );

        CREATE INDEX IF NOT EXISTS idx_predictions_ticker ON predictions(ticker);
        CREATE INDEX IF NOT EXISTS idx_predictions_created ON predictions(created_at);
    """)

    conn.commit()
    conn.close()


def save_prediction(ticker: str, score: float, technical_score: float,
                    sentiment_score: float, volume_score: float,
                    ml_prediction: float, analysis: dict):
    conn = get_connection()
    conn.execute(
        """INSERT INTO predictions
           (ticker, score, technical_score, sentiment_score, volume_score, ml_prediction, analysis_json)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (ticker, score, technical_score, sentiment_score, volume_score,
         ml_prediction, json.dumps(analysis))
    )
    conn.commit()
    conn.close()


def get_latest_predictions(limit: int = 20):
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM predictions
           WHERE created_at = (SELECT MAX(created_at) FROM predictions)
           ORDER BY score DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def cache_stock_data(ticker: str, data: dict):
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO stock_cache (ticker, data_json, updated_at)
           VALUES (?, ?, ?)""",
        (ticker, json.dumps(data, default=str), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_cached_stock(ticker: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM stock_cache WHERE ticker = ?", (ticker,)
    ).fetchone()
    conn.close()
    if row:
        return json.loads(row["data_json"])
    return None
