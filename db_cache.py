"""Persistent SQLite cache with namespace support.

Stores score-by-address caches, housing price lookups, and any other
namespaced KV entries.  Colocated in ``shops.db`` alongside shop and
correlation data.

Each namespace can have its own TTL.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, NamedTuple

_DB_PATH: Path = Path(__file__).parent / "shops.db"

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS kv (
    namespace  TEXT NOT NULL,
    key        TEXT NOT NULL,
    data       TEXT NOT NULL,
    fetched_at REAL NOT NULL,
    PRIMARY KEY (namespace, key)
)
"""


class CacheEntry(NamedTuple):
    """A cached value with freshness metadata."""

    value: Any
    is_fresh: bool


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(_CREATE_SQL)
    return conn


def get(namespace: str, key: str, ttl: int) -> CacheEntry | None:
    """Return a cached entry if one exists.

    Stale entries (older than *ttl* seconds) are still returned with
    ``is_fresh=False`` so callers can use them as fallback.

    Args:
        namespace: Cache partition (e.g. ``"shops"``, ``"prices"``).
        key: Lookup key within the namespace.
        ttl: Freshness threshold in seconds.

    Returns:
        A ``CacheEntry``, or ``None`` if nothing is cached for this key.
    """
    with _conn() as conn:
        row = conn.execute(
            "SELECT data, fetched_at FROM kv WHERE namespace = ? AND key = ?",
            (namespace, key),
        ).fetchone()
    if not row:
        return None

    data_str, fetched_at = row
    value: Any = json.loads(data_str)
    is_fresh = (time.time() - fetched_at) <= ttl
    return CacheEntry(value=value, is_fresh=is_fresh)


def put(namespace: str, key: str, value: Any) -> None:  # noqa: ANN401
    """Store a value in the persistent cache.

    Args:
        namespace: Cache partition.
        key: Lookup key within the namespace.
        value: JSON-serialisable data.
    """
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO kv (namespace, key, data, fetched_at) VALUES (?, ?, ?, ?)",
            (namespace, key, json.dumps(value), time.time()),
        )


def clear(namespace: str | None = None) -> None:
    """Drop cached entries.

    Args:
        namespace: If provided, only clear this namespace. Otherwise clear all.
    """
    with _conn() as conn:
        if namespace:
            conn.execute("DELETE FROM kv WHERE namespace = ?", (namespace,))
        else:
            conn.execute("DELETE FROM kv")


def stats(namespace: str | None = None, ttl: int = 0) -> dict[str, int]:
    """Return cache statistics.

    Args:
        namespace: If provided, stats for this namespace only.
        ttl: Freshness threshold for counting fresh vs stale.

    Returns:
        Dict with ``total``, ``fresh``, and ``stale`` counts.
    """
    now = time.time()
    with _conn() as conn:
        if namespace:
            total: int = conn.execute(
                "SELECT COUNT(*) FROM kv WHERE namespace = ?", (namespace,)
            ).fetchone()[0]
            fresh: int = conn.execute(
                "SELECT COUNT(*) FROM kv WHERE namespace = ? AND fetched_at > ?",
                (namespace, now - ttl),
            ).fetchone()[0] if ttl > 0 else total
        else:
            total = conn.execute("SELECT COUNT(*) FROM kv").fetchone()[0]
            fresh = conn.execute(
                "SELECT COUNT(*) FROM kv WHERE fetched_at > ?",
                (now - ttl,),
            ).fetchone()[0] if ttl > 0 else total
    return {"total": total, "fresh": fresh, "stale": total - fresh}
