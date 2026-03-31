"""Redfin property data scraper.

Fetches property value estimates from Redfin by scraping the React server
state embedded in HTML pages. Two strategies:

1. **Zip median** -- loads the zip code listing page, extracts listing
   prices for all ~60 properties, and computes the median. Fast (one HTTP
   request) and representative of the neighbourhood.
2. **Single-property AVM** -- loads an individual property detail page and
   extracts the Redfin Estimate (Automated Valuation Model). More precise
   for a specific address but requires knowing the property URL.

All data comes from server-rendered HTML, avoiding the CloudFront-blocked
Stingray API endpoints.
"""

from __future__ import annotations

import json
import logging
import math
import re
from typing import Any

import requests

from models import PriceEstimate

_log = logging.getLogger(__name__)

_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html",
}

_REACT_STATE_RE = re.compile(
    r"root\.__reactServerState\.InitialContext\s*=\s*(.*?);\s*root\.",
    re.DOTALL,
)

_AVM_KEY = "/stingray/api/home/details/avm"
_STINGRAY_PREFIX = "{}&&"
_TIMEOUT = 15


def _parse_react_state(html: str) -> dict[str, Any] | None:
    m = _REACT_STATE_RE.search(html)
    if not m:
        return None
    try:
        return json.loads(m.group(1))  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        return None


def _get_data_cache(html: str) -> dict[str, Any]:
    state = _parse_react_state(html)
    if not state:
        return {}
    return state.get("ReactServerAgent.cache", {}).get("dataCache", {})  # type: ignore[no-any-return]


def _decode_body(raw: str) -> dict[str, Any]:
    text = raw.removeprefix(_STINGRAY_PREFIX)
    if not text:
        return {}
    try:
        return json.loads(text)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        return {}


def _fetch_page(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        if resp.ok:
            return resp.text
    except requests.RequestException:
        _log.exception("Request failed: %s", url)
    return None


# ---------------------------------------------------------------------------
# Step 1: Discover properties in a zip code
# ---------------------------------------------------------------------------


def _fetch_zip_properties(zip_code: str) -> list[dict[str, Any]]:
    """Fetch property listings from the Redfin zip code page.

    Args:
        zip_code: 5-digit zip code (e.g. ``"95014"``).

    Returns:
        List of home dicts from the GIS data embedded in the page.
    """
    html = _fetch_page(f"https://www.redfin.com/zipcode/{zip_code}")
    if not html:
        return []

    dc = _get_data_cache(html)
    homes: list[dict[str, Any]] = []
    for key in dc:
        if "gis" not in key:
            continue
        body = _decode_body(dc[key].get("res", {}).get("text", ""))
        homes.extend(body.get("payload", {}).get("homes", []))

    return homes


def median_by_zip(zip_code: str) -> PriceEstimate | None:
    """Scrape the Redfin housing-market page for the median sale price.

    Uses the ``/zipcode/<zip>/housing-market`` page which contains
    pre-rendered median sale price and other market statistics. Single
    HTTP request, authoritative Redfin data.

    Args:
        zip_code: 5-digit zip code (e.g. ``"95014"``).

    Returns:
        A ``PriceEstimate`` with the median sale price, or ``None`` on failure.
    """
    html = _fetch_page(f"https://www.redfin.com/zipcode/{zip_code}/housing-market")
    if not html:
        return None

    dc = _get_data_cache(html)

    median_price: int | None = None
    median_ppsf: int = 0

    for key in dc:
        if "home_prices" not in key:
            continue
        body = _decode_body(dc[key].get("res", {}).get("text", ""))
        for metric in body.get("payload", {}).get("metrics", []):
            label: str = metric.get("label", "")
            val_str: str = metric.get("value", "")
            if not val_str:
                continue
            cleaned = val_str.replace("$", "").replace(",", "")
            if "Median Sale Price" in label:
                median_price = int(cleaned)
            elif "Median" in label and "Sq" in label:
                median_ppsf = int(cleaned)

    if not median_price:
        return None

    return {
        "zip_code": zip_code,
        "label": "Redfin median sale",
        "median_price": median_price,
        "price_per_sqft": median_ppsf,
        "source": "redfin",
    }


# ---------------------------------------------------------------------------
# Step 2: Find the nearest property
# ---------------------------------------------------------------------------


def _find_nearest_url(
    homes: list[dict[str, Any]],
    lat: float,
    lng: float,
) -> str | None:
    """Find the Redfin URL of the property closest to the given coordinates.

    Args:
        homes: Property dicts from ``_fetch_zip_properties``.
        lat: Target latitude.
        lng: Target longitude.

    Returns:
        Redfin URL path (e.g. ``"/CA/Cupertino/.../home/1234"``), or ``None``.
    """
    best_url: str | None = None
    best_dist = float("inf")

    for h in homes:
        lo: dict[str, Any] = h.get("latLong", {})
        raw_lat: Any = lo.get("latitude")
        raw_lng: Any = lo.get("longitude")
        if raw_lat is None or raw_lng is None:
            nested: dict[str, Any] = dict(lo["value"]) if isinstance(lo.get("value"), dict) else {}
            raw_lat = raw_lat or nested.get("latitude")
            raw_lng = raw_lng or nested.get("longitude")
        if raw_lat is None or raw_lng is None:
            continue
        d = math.hypot(float(raw_lat) - lat, float(raw_lng) - lng)
        if d < best_dist:
            best_dist = d
            best_url = h.get("url")

    return best_url


# ---------------------------------------------------------------------------
# Step 3: Extract AVM from a property page
# ---------------------------------------------------------------------------


def _extract_avm_from_page(html: str, redfin_path: str) -> PriceEstimate | None:
    """Parse the property detail page and extract the AVM estimate."""
    dc = _get_data_cache(html)
    avm_entry: dict[str, Any] | None = dc.get(_AVM_KEY)
    if not avm_entry:
        return None

    payload = _decode_body(avm_entry.get("res", {}).get("text", "")).get("payload", {})
    predicted: float | None = payload.get("predictedValue")
    if not predicted:
        return None

    sqft_raw: object = payload.get("sqFt", {})
    sqft = (
        int(sqft_raw["value"])  # type: ignore[index]
        if isinstance(sqft_raw, dict) and "value" in sqft_raw
        else 0
    )
    price_per_sqft = round(predicted / sqft) if sqft > 0 else 0

    zip_match = re.search(r"-(\d{5})(?:/|$)", redfin_path)
    zip_code = zip_match.group(1) if zip_match else ""

    return {
        "zip_code": zip_code,
        "label": "Redfin Estimate",
        "median_price": round(predicted),
        "price_per_sqft": price_per_sqft,
        "source": "redfin",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_estimate(redfin_path: str) -> PriceEstimate | None:
    """Fetch the Redfin Estimate for a known property URL path.

    Args:
        redfin_path: Full Redfin URL path with ``/home/<id>`` suffix.

    Returns:
        A ``PriceEstimate`` if found, otherwise ``None``.
    """
    html = _fetch_page(f"https://www.redfin.com{redfin_path}")
    if not html:
        return None
    return _extract_avm_from_page(html, redfin_path)


def estimate_by_location(
    lat: float,
    lng: float,
    zip_code: str,
) -> PriceEstimate | None:
    """Estimate a property value by finding the nearest Redfin listing.

    Fetches the zip code listing page, finds the closest property to the
    target coordinates, then scrapes the AVM from that property's page.
    Requires two HTTP requests total.

    Args:
        lat: Target latitude.
        lng: Target longitude.
        zip_code: 5-digit zip code for the area.

    Returns:
        A ``PriceEstimate`` for the nearest property, or ``None`` on failure.
    """
    homes = _fetch_zip_properties(zip_code)
    if not homes:
        _log.warning("No properties found in zip %s", zip_code)
        return None

    nearest_url = _find_nearest_url(homes, lat, lng)
    if not nearest_url:
        return None

    _log.info("Fetching AVM for nearest property: %s", nearest_url)
    html = _fetch_page(f"https://www.redfin.com{nearest_url}")
    if not html:
        return None

    return _extract_avm_from_page(html, nearest_url)
