"""Persistent shop store backed by SQLite.

Every scraped shop is stored individually by place ID so that subsequent
queries only need a distance lookup — no re-scraping required for areas
that have already been covered.

A separate ``scraped_cells`` table tracks which grid cells have been
scraped (and when), so we know when fresh data needs to be fetched.
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import time
from pathlib import Path

from models import ShopData

_DB_PATH: Path = Path(__file__).parent / "cache.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS shops (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    lat          REAL NOT NULL,
    lng          REAL NOT NULL,
    rating       REAL NOT NULL DEFAULT 0,
    review_count INTEGER NOT NULL DEFAULT 0,
    address      TEXT NOT NULL DEFAULT '',
    categories   TEXT NOT NULL DEFAULT '[]',
    source       TEXT NOT NULL DEFAULT '',
    fetched_at   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS scraped_cells (
    cell_key   TEXT PRIMARY KEY,
    scraped_at REAL NOT NULL
);
"""

CELL_PRECISION: int = 2  # ~0.7 mi grid cells (coarser than old cache)
CELL_TTL: int = 7 * 86_400  # re-scrape after 7 days

_EARTH_RADIUS_MI = 3958.8


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    for raw_stmt in _SCHEMA.strip().split(";"):
        cleaned = raw_stmt.strip()
        if cleaned:
            conn.execute(cleaned)
    return conn


def _cell_key(lat: float, lng: float) -> str:
    return (
        f"{round(lat, CELL_PRECISION):.{CELL_PRECISION}f},"
        f"{round(lng, CELL_PRECISION):.{CELL_PRECISION}f}"
    )


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return _EARTH_RADIUS_MI * 2 * math.asin(math.sqrt(a))


# ── public API ────────────────────────────────────────────────────────


def upsert_shops(shops: list[ShopData]) -> int:
    """Insert or update shops in the store.  Returns count of new inserts."""
    now = time.time()
    added = 0
    with _conn() as conn:
        for s in shops:
            sid = s.get("id", "")
            if not sid:
                continue
            cats = json.dumps(s.get("categories", []))
            conn.execute(
                """INSERT INTO shops (id, name, lat, lng, rating, review_count,
                                     address, categories, source, fetched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                       rating = excluded.rating,
                       review_count = excluded.review_count,
                       address = excluded.address,
                       categories = excluded.categories,
                       fetched_at = excluded.fetched_at""",
                (
                    sid,
                    s.get("name", ""),
                    s.get("lat", 0.0),
                    s.get("lng", 0.0),
                    s.get("rating", 0.0),
                    s.get("review_count", 0),
                    s.get("address", ""),
                    cats,
                    s.get("source", ""),
                    now,
                ),
            )
            added += 1
    return added


def mark_cell_scraped(lat: float, lng: float) -> None:
    """Record that the grid cell containing *lat*, *lng* has been scraped."""
    key = _cell_key(lat, lng)
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO scraped_cells (cell_key, scraped_at) VALUES (?, ?)",
            (key, time.time()),
        )


def is_cell_fresh(lat: float, lng: float) -> bool:
    """Return whether the grid cell was scraped within ``CELL_TTL``."""
    key = _cell_key(lat, lng)
    with _conn() as conn:
        row = conn.execute(
            "SELECT scraped_at FROM scraped_cells WHERE cell_key = ?", (key,),
        ).fetchone()
    if not row:
        return False
    return (time.time() - row[0]) <= CELL_TTL


def get_nearby(lat: float, lng: float, radius_miles: float) -> list[ShopData]:
    """Return all stored shops within *radius_miles* of the point.

    Uses a bounding-box pre-filter in SQL then exact haversine in Python.
    """
    dlat = radius_miles / 69.0
    dlng = radius_miles / (69.0 * math.cos(math.radians(lat)))
    lat_lo, lat_hi = lat - dlat, lat + dlat
    lng_lo, lng_hi = lng - dlng, lng + dlng

    with _conn() as conn:
        rows = conn.execute(
            """SELECT id, name, lat, lng, rating, review_count,
                      address, categories, source
               FROM shops
               WHERE lat BETWEEN ? AND ? AND lng BETWEEN ? AND ?""",
            (lat_lo, lat_hi, lng_lo, lng_hi),
        ).fetchall()

    results: list[ShopData] = []
    for row in rows:
        sid, name, slat, slng, rating, reviews, addr, cats_json, source = row
        dist = _haversine(lat, lng, slat, slng)
        if dist > radius_miles:
            continue
        results.append(
            {
                "source": source,
                "id": sid,
                "name": name,
                "lat": slat,
                "lng": slng,
                "rating": rating,
                "review_count": reviews,
                "address": addr,
                "categories": json.loads(cats_json),
                "distance_miles": round(dist, 2),
            }
        )
    results.sort(key=lambda s: s.get("distance_miles", 0.0))
    return results


def shop_count() -> int:
    """Total number of shops in the store."""
    with _conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM shops").fetchone()[0]  # type: ignore[no-any-return]


def cell_count() -> int:
    """Total number of scraped grid cells."""
    with _conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM scraped_cells").fetchone()[0]  # type: ignore[no-any-return]


def seed_from_demo() -> int:
    """Load demo shops into the store and mark the Bay Area as covered.

    Inserts all demo shops and marks every neighbourhood centroid cell
    (plus every shop cell) as freshly scraped so that subsequent
    ``_ensure_coverage`` calls are no-ops for those areas.

    Idempotent — skips the seed if the store already has data.
    Returns the number of shops inserted.
    """
    if shop_count() > 0:
        return 0

    from api_clients.demo_data import DEMO_SHOPS_DB  # noqa: PLC0415
    from api_clients.housing_prices import _ZIP_CENTROIDS  # noqa: PLC0415

    shops: list[ShopData] = [
        {
            "source": "demo",
            "id": hashlib.md5(
                f"{s['name']}:{s['lat']:.5f}:{s['lng']:.5f}".encode(),
                usedforsecurity=False,
            ).hexdigest(),
            "name": s["name"],
            "lat": s["lat"],
            "lng": s["lng"],
            "rating": s["rating"],
            "review_count": s["reviews"],
            "address": s["addr"],
            "categories": ["Bubble Tea", "Tea"],
        }
        for s in DEMO_SHOPS_DB
    ]
    n = upsert_shops(shops)

    seen_cells: set[str] = set()
    all_points = [(s.get("lat", 0.0), s.get("lng", 0.0)) for s in shops]
    all_points.extend(_ZIP_CENTROIDS.values())

    for plat, plng in all_points:
        key = _cell_key(plat, plng)
        if key not in seen_cells:
            seen_cells.add(key)
            mark_cell_scraped(plat, plng)

    return n


def clear() -> None:
    """Drop all shop and cell data."""
    with _conn() as conn:
        conn.execute("DELETE FROM shops")
        conn.execute("DELETE FROM scraped_cells")
