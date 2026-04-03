"""Persistent housing price store backed by SQLite.

Separate from ``shops.db`` — housing prices have their own refresh
cadence and data source (Redfin).  The DB file ``prices.db`` ships
alongside ``shops.db`` in the production container.

Stores median Single Family Home sale prices per zip code.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from models import PriceEstimate

_DB_PATH: Path = Path(__file__).parent / "prices.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS zip_medians (
    zip_code       TEXT PRIMARY KEY,
    label          TEXT NOT NULL,
    median_price   INTEGER NOT NULL,
    price_per_sqft INTEGER NOT NULL DEFAULT 0,
    source         TEXT NOT NULL,
    fetched_at     REAL NOT NULL
)
"""


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    for raw_stmt in _SCHEMA.strip().split(";"):
        cleaned = raw_stmt.strip()
        if cleaned:
            conn.execute(cleaned)
    return conn


def upsert_zip_median(estimate: PriceEstimate) -> None:
    """Insert or replace a zip-level median price."""
    with _conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO zip_medians
               (zip_code, label, median_price, price_per_sqft, source, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                estimate["zip_code"],
                estimate["label"],
                estimate["median_price"],
                estimate.get("price_per_sqft", 0),
                estimate["source"],
                time.time(),
            ),
        )


def get_zip_median(zip_code: str) -> PriceEstimate | None:
    """Return the stored median price for a zip, or None."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT zip_code, label, median_price, price_per_sqft, source FROM zip_medians WHERE zip_code = ?",
            (zip_code,),
        ).fetchone()
    if not row:
        return None
    return {
        "zip_code": row[0],
        "label": row[1],
        "median_price": row[2],
        "price_per_sqft": row[3],
        "source": row[4],
    }


def zip_median_count() -> int:
    with _conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM zip_medians").fetchone()[0]  # type: ignore[no-any-return]


def clear() -> None:
    """Drop all price data."""
    with _conn() as conn:
        conn.execute("DELETE FROM zip_medians")
