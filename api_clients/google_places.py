"""Google Places API client for searching boba/bubble tea shops."""

from __future__ import annotations

import time
from typing import Any

import requests

from config import GOOGLE_PLACES_API_KEY, SEARCH_RADIUS_METERS
from models import ShopData

NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

_MAX_PAGES = 3
_PAGE_DELAY = 2.0


def _parse_place(place: dict[str, Any]) -> ShopData:
    loc: dict[str, Any] = place.get("geometry", {}).get("location", {})
    return {
        "source": "google",
        "id": str(place["place_id"]),
        "name": str(place["name"]),
        "lat": float(loc.get("lat", 0)),
        "lng": float(loc.get("lng", 0)),
        "rating": float(place.get("rating", 0)),
        "review_count": int(place.get("user_ratings_total", 0)),
        "address": str(place.get("vicinity", "")),
        "categories": list(place.get("types", [])),
    }


def search_boba_shops(lat: float, lng: float) -> list[ShopData]:
    """Search Google Places for boba/bubble tea shops near a coordinate.

    Runs multiple keyword queries to maximise coverage, then deduplicates
    by place ID. Fetches up to 3 pages per query.

    Args:
        lat: Centre latitude for the search.
        lng: Centre longitude for the search.

    Returns:
        Deduplicated list of ``ShopData`` dicts.
    """
    seen_ids: set[str] = set()
    results: list[ShopData] = []

    keywords = ["boba tea", "bubble tea", "milk tea"]

    for kw in keywords:
        params: dict[str, str | int] = {
            "location": f"{lat},{lng}",
            "radius": min(SEARCH_RADIUS_METERS, 50_000),
            "keyword": kw,
            "key": GOOGLE_PLACES_API_KEY,
        }
        page_results = _fetch_pages(params)
        for shop in page_results:
            pid = shop.get("id", "")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                results.append(shop)

    return results


def _fetch_pages(params: dict[str, str | int]) -> list[ShopData]:
    """Fetch up to ``_MAX_PAGES`` of Nearby Search results."""
    all_results: list[ShopData] = []

    resp = requests.get(NEARBY_URL, params=params, timeout=10)  # type: ignore[arg-type]
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()
    all_results.extend(_parse_place(p) for p in data.get("results", []))

    for _ in range(_MAX_PAGES - 1):
        token: str | None = data.get("next_page_token")
        if not token:
            break
        time.sleep(_PAGE_DELAY)
        next_params: dict[str, str] = {"pagetoken": token, "key": GOOGLE_PLACES_API_KEY}
        resp2 = requests.get(NEARBY_URL, params=next_params, timeout=10)
        if not resp2.ok:
            break
        data = resp2.json()
        all_results.extend(_parse_place(p) for p in data.get("results", []))

    return all_results


def get_place_details(place_id: str) -> dict[str, Any]:
    """Fetch detailed info including reviews for a Google Place.

    Args:
        place_id: Google Places unique identifier.

    Returns:
        Raw ``result`` dict from the Places Details response.
    """
    params: dict[str, str] = {
        "place_id": place_id,
        "fields": "name,rating,user_ratings_total,reviews,formatted_address",
        "key": GOOGLE_PLACES_API_KEY,
    }
    resp = requests.get(DETAILS_URL, params=params, timeout=10)
    resp.raise_for_status()
    result: dict[str, Any] = resp.json().get("result", {})
    return result
