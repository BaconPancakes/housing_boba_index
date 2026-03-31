"""Grid-snapped cache for boba shop data backed by SQLite.

Coordinates are rounded to a grid so that queries within ~0.07 mi of each
other share a cache entry. Uses ``db_cache`` for persistent storage with
stale-data fallback.
"""

from __future__ import annotations

from typing import Any

import db_cache
from models import CacheStats

GRID_PRECISION: int = 3  # decimal places — ~0.07 mi cells at Bay Area latitudes
SHOPS_TTL: int = 7 * 86_400  # 7 days
_NAMESPACE: str = "shops"


def _grid_key(lat: float, lng: float) -> str:
    return (
        f"{round(lat, GRID_PRECISION):.{GRID_PRECISION}f},"
        f"{round(lng, GRID_PRECISION):.{GRID_PRECISION}f}"
    )


def get(lat: float, lng: float, *, namespace: str = "") -> Any | None:  # noqa: ANN401
    """Return cached value for the grid cell, or ``None`` if expired / missing.

    Stale entries are returned when fresh data is unavailable, letting
    callers decide whether to refresh.

    Args:
        lat: Latitude of the query point.
        lng: Longitude of the query point.
        namespace: Cache partition key (e.g. ``"shops"``).

    Returns:
        The cached value, or ``None`` if no valid entry exists.
    """
    ns = namespace or _NAMESPACE
    key = _grid_key(lat, lng)
    entry = db_cache.get(ns, key, ttl=SHOPS_TTL)
    if entry is None:
        return None
    return entry.value


def put(
    lat: float,
    lng: float,
    value: Any,  # noqa: ANN401
    *,
    namespace: str = "",
    ttl: int = SHOPS_TTL,  # noqa: ARG001
) -> None:
    """Store *value* in the grid cell.

    Args:
        lat: Latitude of the query point.
        lng: Longitude of the query point.
        value: Arbitrary JSON-serialisable data to cache.
        namespace: Cache partition key (e.g. ``"shops"``).
        ttl: Unused (retained for API compatibility); TTL is set per-namespace.
    """
    ns = namespace or _NAMESPACE
    key = _grid_key(lat, lng)
    db_cache.put(ns, key, value)


def clear() -> None:
    """Drop all shop cache entries."""
    db_cache.clear(_NAMESPACE)


def stats() -> CacheStats:
    """Return a snapshot of cache statistics.

    Returns:
        Dict with ``total_entries`` and ``live_entries`` counts.
    """
    s = db_cache.stats(_NAMESPACE, ttl=SHOPS_TTL)
    return {"total_entries": s["total"], "live_entries": s["fresh"]}
