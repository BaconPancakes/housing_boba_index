"""Google Places API client for searching boba shops."""

from __future__ import annotations

import time
from typing import Any

import requests

import os

from config import SEARCH_RADIUS_METERS

GOOGLE_PLACES_API_KEY: str = os.getenv("GOOGLE_PLACES_API_KEY", "")
from models import ShopData

TEXTSEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
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
        "address": str(place.get("formatted_address", "")),
        "categories": list(place.get("types", [])),
    }


def search_boba_shops(lat: float, lng: float) -> list[ShopData]:
    """Search Google Places for boba shops near a coordinate.

    Uses the Text Search API which returns ``formatted_address`` (the full
    street address) rather than the vague ``vicinity`` from Nearby Search.

    Args:
        lat: Centre latitude for the search.
        lng: Centre longitude for the search.

    Returns:
        Deduplicated list of ``ShopData`` dicts (up to 60 results).
    """
    params: dict[str, str | int] = {
        "query": "boba",
        "location": f"{lat},{lng}",
        "radius": min(SEARCH_RADIUS_METERS, 50_000),
        "key": GOOGLE_PLACES_API_KEY,
    }
    seen_ids: set[str] = set()
    results: list[ShopData] = []

    for shop in _fetch_pages(params):
        pid = shop.get("id", "")
        if pid and pid not in seen_ids:
            seen_ids.add(pid)
            results.append(shop)

    return results


def _fetch_pages(params: dict[str, str | int]) -> list[ShopData]:
    """Fetch up to ``_MAX_PAGES`` of Text Search results."""
    all_results: list[ShopData] = []

    resp = requests.get(TEXTSEARCH_URL, params=params, timeout=10)  # type: ignore[arg-type]
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()
    all_results.extend(_parse_place(p) for p in data.get("results", []))

    for _ in range(_MAX_PAGES - 1):
        token: str | None = data.get("next_page_token")
        if not token:
            break
        time.sleep(_PAGE_DELAY)
        next_params: dict[str, str] = {"pagetoken": token, "key": GOOGLE_PLACES_API_KEY}
        resp2 = requests.get(TEXTSEARCH_URL, params=next_params, timeout=10)
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
