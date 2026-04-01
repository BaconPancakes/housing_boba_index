"""Google Maps scraper — find boba shops without Places API quotas.

Replicates the browser flow: fetches the Google Maps search page to
extract the internal ``tbm=map`` search URL, then calls that endpoint
directly to receive structured business-listing JSON.  This sidesteps
the per-request cost / daily quota of the official Places API.

**How it works**

1.  ``GET /maps/search/boba+tea/@{lat},{lng},{zoom}z/`` — the HTML
    response embeds the full ``tbm=map`` URL (including a protobuf-encoded
    ``pb`` parameter) that the Maps JS app would call.
2.  ``GET /search?tbm=map&…&pb=…`` — returns a JSON payload (prefixed
    with ``)]}'``) containing complete business entries.
3.  The business list is located dynamically inside the response and
    each entry is parsed into :class:`~models.ShopData`.

**Caveats**:  The data format is undocumented and may change without
notice.  If extraction fails the caller receives an empty list and
should fall back to demo data.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

from config import SEARCH_RADIUS_METERS
from models import ShopData

logger = logging.getLogger(__name__)

_MAPS_SEARCH_URL = "https://www.google.com/maps/search/{query}/@{lat},{lng},{zoom}z/"
_GOOGLE_SEARCH_BASE = "https://www.google.com/search?"
_TIMEOUT = 20
_MAX_RESPONSE = 5_000_000
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
_MAPS_REFERER = "https://www.google.com/maps/"
_JPREFIX = ")]}'"

# Google returns ~20 results per search.  A tight zoom (14-15) keeps
# results local but limits coverage.  We scrape a grid of overlapping
# viewports so nearby shops aren't missed.
_ZOOM = 14
_GRID_OFFSET_MI = 1.5  # offset between grid cells in miles
_MI_TO_DEG_LAT = 1 / 69.0
_MI_TO_DEG_LNG_AT_37 = 1 / 54.6  # cos(37°) correction

# Known indices into a business-entry array (len ~260).
_IDX_NAME = 11
_IDX_COORDS = 9       # [None, None, lat, lng]
_IDX_RATING_ARR = 4   # [None, …, None, rating]
_IDX_RATING_SUB = 7
_IDX_REVIEWS_ARR = 37  # [None, count, …]
_IDX_REVIEWS_SUB = 1
_IDX_ADDRESS = 39
_IDX_PLACE_ID = 78
_IDX_CATEGORIES = 13
_MIN_BIZ_LEN = 80     # business arrays are ~260 elements

# Relevance filter — only keep results that are actually boba / tea shops.
_BOBA_CATEGORY = "bubble tea store"
_TEA_CATEGORIES = frozenset({
    "bubble tea store", "tea store", "tea house", "chinese tea house",
})
_BOBA_NAME_KEYWORDS = (
    "boba", "bubble tea", "milk tea", "matcha",
    "tea ", " tea", "tea\u2019", "teahouse",
    "茶", "奶茶", "珍珠",
)
_EXCLUDE_CATEGORIES = frozenset({
    "bakery", "coffee shop", "donut shop", "grocery store",
    "supermarket", "restaurant", "ramen restaurant",
    "korean restaurant", "japanese restaurant",
    "vietnamese restaurant", "thai restaurant",
    "chinese restaurant", "pizza restaurant",
    "sandwich shop", "hamburger restaurant",
    "ice cream shop", "wholesaler",
    "food products supplier", "caterer", "mobile caterer",
})
_EXCLUDE_NAME_KEYWORDS = (
    "coffee", "ramen", "poke", "donut", "pizza", "burger",
    "chicken", "korean", "bulgogi", "pho ", "bakery",
    "grocery", "ranch market", "sushi", "filipino",
)


def _grid_offsets() -> list[tuple[float, float]]:
    """Return (dlat, dlng) offsets for a 3x3 grid around the centre."""
    step_lat = _GRID_OFFSET_MI * _MI_TO_DEG_LAT
    step_lng = _GRID_OFFSET_MI * _MI_TO_DEG_LNG_AT_37
    return [
        (dy * step_lat, dx * step_lng)
        for dy in (-1, 0, 1)
        for dx in (-1, 0, 1)
    ]


def _radius_cells(radius_m: int) -> list[tuple[float, float]]:
    """Decide how many grid cells to scrape based on search radius.

    Small radii (<=2 mi) use a single centre scrape; larger radii use
    a 3x3 grid so that every part of the circle has local results.
    """
    if radius_m <= 3200:  # noqa: PLR2004  — ~2 miles
        return [(0.0, 0.0)]
    return _grid_offsets()


# ── public entry point ────────────────────────────────────────────────


def search_boba_shops(lat: float, lng: float) -> list[ShopData]:
    """Scrape Google Maps for boba shops near *lat*, *lng*.

    For the configured search radius, scrapes a grid of overlapping
    viewports to maximise nearby coverage (Google caps each response
    at ~20 results).  Returns the same ``ShopData`` shape as
    :func:`api_clients.google_places.search_boba_shops`.
    """
    cells = _radius_cells(SEARCH_RADIUS_METERS)
    seen: set[str] = set()
    all_shops: list[ShopData] = []

    for dlat, dlng in cells:
        clat = round(lat + dlat, 6)
        clng = round(lng + dlng, 6)
        for shop in _scrape_one(clat, clng):
            sid = shop.get("id", "")
            if sid and sid not in seen:
                seen.add(sid)
                all_shops.append(shop)

    logger.info(
        "Scraped %d unique shops from %d grid cells", len(all_shops), len(cells),
    )
    return all_shops


def _scrape_one(lat: float, lng: float) -> list[ShopData]:
    """Single-viewport scrape at the given centre."""
    search_url = _MAPS_SEARCH_URL.format(
        query="boba+tea", lat=lat, lng=lng, zoom=_ZOOM,
    )
    try:
        api_url = _extract_internal_api_url(search_url)
    except _ScrapeError:
        logger.warning("No tbm=map URL for %.4f, %.4f", lat, lng)
        return []

    try:
        businesses = _fetch_businesses(api_url)
    except _ScrapeError:
        logger.warning("No business data for %.4f, %.4f", lat, lng)
        return []

    return _parse_businesses(businesses)


# ── internal helpers ──────────────────────────────────────────────────


class _ScrapeError(Exception):
    """Raised when any step of the scraping pipeline fails."""


def _extract_internal_api_url(maps_search_url: str) -> str:
    """Fetch the Maps search page and return the embedded ``tbm=map`` URL."""
    resp = requests.get(
        maps_search_url,
        headers={**_HEADERS, "Accept": "text/html"},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    html = resp.text[:_MAX_RESPONSE]

    m = re.search(r"tbm=map[^\"']*", html)
    if not m:
        msg = "Could not find tbm=map URL in Maps page"
        raise _ScrapeError(msg)

    raw = m.group(0).replace("&amp;", "&")
    return _GOOGLE_SEARCH_BASE + raw


def _fetch_businesses(api_url: str) -> list[list[Any]]:
    """Call the Maps internal search endpoint and return business entries."""
    resp = requests.get(
        api_url,
        headers={**_HEADERS, "Accept": "*/*", "Referer": _MAPS_REFERER},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    text = resp.text[:_MAX_RESPONSE]

    if text.startswith(_JPREFIX):
        text = text[len(_JPREFIX) :].lstrip("\n")

    try:
        data: list[Any] = json.loads(text)
    except (json.JSONDecodeError, ValueError) as exc:
        msg = "Could not parse Maps API JSON response"
        raise _ScrapeError(msg) from exc

    return _locate_business_list(data)


def _locate_business_list(data: list[Any]) -> list[list[Any]]:
    """Find the top-level element containing the business-detail arrays.

    The business list is the largest ``list[list]`` whose children are
    2-element lists where the second element is a very long list (the
    actual business record with ~260 fields).
    """
    best: list[list[Any]] = []
    for item in data:
        if not isinstance(item, list) or len(item) < 2:  # noqa: PLR2004
            continue
        if _looks_like_business_list(item) and len(item) > len(best):
            best = item
    if not best:
        msg = "Could not locate business entries in Maps response"
        raise _ScrapeError(msg)
    return best


def _looks_like_business_list(arr: list[Any]) -> bool:
    """Check whether *arr* is a list of ``[wrapper, details]`` pairs."""
    try:
        first = arr[0]
        return (
            isinstance(first, list)
            and len(first) >= 2  # noqa: PLR2004
            and isinstance(first[1], list)
            and len(first[1]) > _MIN_BIZ_LEN
        )
    except (IndexError, TypeError):
        return False


# ── parse individual business entries ─────────────────────────────────


def _parse_businesses(entries: list[list[Any]]) -> list[ShopData]:
    seen: set[str] = set()
    shops: list[ShopData] = []
    for wrapper in entries:
        shop = _parse_one(wrapper)
        if not shop or not _is_boba_related(shop):
            continue
        sid = shop.get("id", "")
        if sid and sid not in seen:
            seen.add(sid)
            shops.append(shop)
    return shops


def _is_boba_related(shop: ShopData) -> bool:
    """Return ``True`` if the shop looks like an actual boba / tea store.

    Logic:
    1. Has the ``Bubble tea store`` Google category → **always yes**.
    2. Name contains a boba/tea keyword (``tea``, ``boba``, ``matcha``,
       ``茶`` …) → **yes** regardless of other categories.
    3. Has a tea-adjacent category (``Tea store``, ``Tea house``) AND
       none of the hard-exclude categories are its *only* categories
       → **yes**.
    4. Name contains only exclude keywords (``coffee``, ``ramen`` …)
       with no boba signal → **no**.
    """
    cats_lower = frozenset(c.lower() for c in shop.get("categories", []))
    name_lower = shop.get("name", "").lower()

    if _BOBA_CATEGORY in cats_lower:
        return True

    has_boba_name = any(kw in name_lower for kw in _BOBA_NAME_KEYWORDS)
    if has_boba_name:
        return True

    has_tea_cat = bool(cats_lower & _TEA_CATEGORIES)
    has_only_excludes = cats_lower and cats_lower <= _EXCLUDE_CATEGORIES
    if has_tea_cat and not has_only_excludes:
        return True

    has_exclude_name = any(kw in name_lower for kw in _EXCLUDE_NAME_KEYWORDS)
    return not has_exclude_name and has_tea_cat


def _parse_one(wrapper: list[Any]) -> ShopData | None:
    """Convert a ``[meta, details]`` wrapper into a ``ShopData`` dict."""
    try:
        biz: list[Any] = wrapper[1]
        if not isinstance(biz, list) or len(biz) <= _IDX_PLACE_ID:
            return None

        name = _s(biz, _IDX_NAME)
        if not name:
            return None

        lat, lng = _coords(biz)
        if lat == 0.0 and lng == 0.0:
            return None

        return {
            "source": "google_scrape",
            "id": _s(biz, _IDX_PLACE_ID) or f"scrape:{lat:.7f},{lng:.7f}",
            "name": name,
            "lat": lat,
            "lng": lng,
            "rating": _rating(biz),
            "review_count": _reviews(biz),
            "address": _s(biz, _IDX_ADDRESS) or "",
            "categories": _categories(biz),
        }
    except Exception:  # noqa: BLE001
        return None


# ── safe field accessors ──────────────────────────────────────────────


def _s(arr: list[Any], idx: int) -> str:
    """Return ``arr[idx]`` if it's a non-empty string, else ``""``."""
    if idx < len(arr) and isinstance(arr[idx], str) and arr[idx]:
        return arr[idx]
    return ""


def _coords(biz: list[Any]) -> tuple[float, float]:
    try:
        geo = biz[_IDX_COORDS]
        if isinstance(geo, list) and len(geo) >= 4:  # noqa: PLR2004
            lat = float(geo[2])
            lng = float(geo[3])
            return lat, lng
    except (IndexError, TypeError, ValueError):
        pass
    return 0.0, 0.0


def _rating(biz: list[Any]) -> float:
    try:
        arr = biz[_IDX_RATING_ARR]
        if isinstance(arr, list) and len(arr) > _IDX_RATING_SUB:
            val = arr[_IDX_RATING_SUB]
            if isinstance(val, (int, float)):
                return round(float(val), 1)
    except (IndexError, TypeError, ValueError):
        pass
    return 0.0


def _reviews(biz: list[Any]) -> int:
    try:
        arr = biz[_IDX_REVIEWS_ARR]
        if isinstance(arr, list) and len(arr) > _IDX_REVIEWS_SUB:
            val = arr[_IDX_REVIEWS_SUB]
            if isinstance(val, int):
                return val
    except (IndexError, TypeError):
        pass
    return 0


def _categories(biz: list[Any]) -> list[str]:
    try:
        cats = biz[_IDX_CATEGORIES]
        if isinstance(cats, list):
            return [str(c) for c in cats if isinstance(c, str)]
    except (IndexError, TypeError):
        pass
    return []
