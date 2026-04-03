"""Shared data models used across the application."""

from __future__ import annotations

from typing import TypedDict


class ShopData(TypedDict, total=False):
    """A boba shop record returned by any data source."""

    source: str
    id: str
    name: str
    lat: float
    lng: float
    address: str
    categories: list[str]
    distance_miles: float
    is_premium: bool
    is_curated: bool
    is_blacklisted: bool


class GeoResult(TypedDict):
    """Geocoding result from Nominatim."""

    lat: float
    lng: float
    display_name: str


class ShopScore(TypedDict):
    """Per-shop scoring breakdown."""

    shop_id: str
    name: str
    tier: str
    tier_weight: float
    distance_miles: float
    raw_contribution: float


class IndexResult(TypedDict, total=False):
    """Full index computation result."""

    index: float
    grade: str
    shop_count: int
    raw_total: float
    breakdown: list[ShopScore]
    summary: str


class PriceEstimate(TypedDict):
    """Housing price estimate for a location."""

    zip_code: str
    label: str
    median_price: int
    price_per_sqft: int
    source: str


class CacheStats(TypedDict):
    """Cache statistics."""

    total_entries: int
    live_entries: int
