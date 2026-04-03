"""Persistent shop store backed by SQLite.

Stores all boba shop data in a single ``shops.db`` file that is pre-seeded
offline by ``seed_db.py`` and shipped read-only to production.

Tables:
- ``shops`` -- one row per physical shop (name, lat/lng, address).
- ``scraped_cells`` -- tracks which grid cells have been scraped (for
  incremental re-seeding).
"""

from __future__ import annotations

import json
import math
import sqlite3
import time
from pathlib import Path

from models import ShopData

_DB_PATH: Path = Path(__file__).parent / "shops.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS shops (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    lat          REAL NOT NULL,
    lng          REAL NOT NULL,
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

CELL_PRECISION: int = 2  # ~0.7 mi grid cells
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


def _normalize_name(name: str) -> str:
    """Lower-case, strip whitespace for fuzzy matching."""
    return name.lower().strip()


_DEDUP_RADIUS_MI = 0.05  # ~80 m — same storefront


def upsert_shops(shops: list[ShopData]) -> int:
    """Insert or update shops in the store.  Returns count of rows touched.

    Before inserting, removes any existing row that shares the same
    normalised name and is within ~80 m (prevents cross-source duplicates).
    """
    now = time.time()
    added = 0
    with _conn() as conn:
        for s in shops:
            sid = s.get("id", "")
            if not sid:
                continue

            slat = s.get("lat", 0.0)
            slng = s.get("lng", 0.0)
            norm = _normalize_name(s.get("name", ""))
            cats = json.dumps(s.get("categories", []))

            if norm:
                _remove_near_duplicates(conn, sid, norm, slat, slng)

            conn.execute(
                """INSERT INTO shops (id, name, lat, lng,
                                     address, categories, source, fetched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                       address = excluded.address,
                       categories = excluded.categories,
                       fetched_at = excluded.fetched_at""",
                (
                    sid,
                    s.get("name", ""),
                    slat,
                    slng,
                    s.get("address", ""),
                    cats,
                    s.get("source", ""),
                    now,
                ),
            )
            added += 1
    return added


def _remove_near_duplicates(
    conn: sqlite3.Connection,
    new_id: str,
    norm_name: str,
    lat: float,
    lng: float,
) -> None:
    """Delete existing rows that are the same physical shop under a different ID."""
    dlat = _DEDUP_RADIUS_MI / 69.0
    dlng = _DEDUP_RADIUS_MI / (69.0 * math.cos(math.radians(lat)) if lat else 69.0)
    rows = conn.execute(
        """SELECT id, name, lat, lng FROM shops
           WHERE lat BETWEEN ? AND ? AND lng BETWEEN ? AND ?
             AND id != ?""",
        (lat - dlat, lat + dlat, lng - dlng, lng + dlng, new_id),
    ).fetchall()
    for row_id, row_name, rlat, rlng in rows:
        if _normalize_name(row_name) != norm_name:
            continue
        if _haversine(lat, lng, rlat, rlng) <= _DEDUP_RADIUS_MI:
            conn.execute("DELETE FROM shops WHERE id = ?", (row_id,))


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
            """SELECT id, name, lat, lng, address, categories, source
               FROM shops
               WHERE lat BETWEEN ? AND ? AND lng BETWEEN ? AND ?""",
            (lat_lo, lat_hi, lng_lo, lng_hi),
        ).fetchall()

    results: list[ShopData] = []
    for row in rows:
        sid, name, slat, slng, addr, cats_json, source = row
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
                "address": addr,
                "categories": json.loads(cats_json),
                "distance_miles": round(dist, 2),
            }
        )
    results.sort(key=lambda s: s.get("distance_miles", 0.0))
    return _dedup_results(results)


def _dedup_results(shops: list[ShopData]) -> list[ShopData]:
    """Remove duplicate entries for the same physical shop.

    When two rows share a normalised name and are within ~80 m, keep
    the one from a live source (google / google_scrape) over demo data.
    """
    kept: list[ShopData] = []
    seen: dict[str, int] = {}  # norm_name -> index in kept

    source_rank = {"google": 2, "google_scrape": 1, "demo": 0}

    for shop in shops:
        norm = _normalize_name(shop.get("name", ""))
        if norm in seen:
            idx = seen[norm]
            existing = kept[idx]
            if _haversine(
                shop.get("lat", 0.0), shop.get("lng", 0.0),
                existing.get("lat", 0.0), existing.get("lng", 0.0),
            ) <= _DEDUP_RADIUS_MI:
                s_rank = source_rank.get(shop.get("source", ""), 0)
                e_rank = source_rank.get(existing.get("source", ""), 0)
                if s_rank > e_rank:
                    kept[idx] = shop
                continue

        seen[norm] = len(kept)
        kept.append(shop)
    return kept


# ── Stats / utilities ────────────────────────────────────────────────


def shop_count() -> int:
    """Total number of shops in the store."""
    with _conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM shops").fetchone()[0]  # type: ignore[no-any-return]


def cell_count() -> int:
    """Total number of scraped grid cells."""
    with _conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM scraped_cells").fetchone()[0]  # type: ignore[no-any-return]


def clear() -> None:
    """Drop all shop and cell data."""
    with _conn() as conn:
        conn.execute("DELETE FROM shops")
        conn.execute("DELETE FROM scraped_cells")
