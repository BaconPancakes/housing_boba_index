"""Housing price estimates for the Bay Area.

Uses a two-tier approach:
1. **Redfin scrape** -- for addresses with a known Redfin property URL,
   fetches the live Redfin Estimate (AVM) directly from the page.
2. **Demo data** -- curated median home prices by zip code, used as fallback.
"""

from __future__ import annotations

import logging
import math
from typing import TypedDict

from models import PriceEstimate

_log = logging.getLogger(__name__)

_PRICE_TTL: int = 90 * 86_400  # 90 days


class _ZipData(TypedDict):
    label: str
    median_price: int
    price_per_sqft: int


_RAW_PRICES: dict[str, _ZipData] = {
    # ── Cupertino ──
    "95014": {"label": "Cupertino", "median_price": 2_800_000, "price_per_sqft": 1_450},
    # ── Sunnyvale ──
    "94085": {"label": "Sunnyvale (East)", "median_price": 1_700_000, "price_per_sqft": 1_100},
    "94086": {"label": "Sunnyvale (Central)", "median_price": 1_900_000, "price_per_sqft": 1_200},
    "94087": {"label": "Sunnyvale (West)", "median_price": 2_400_000, "price_per_sqft": 1_350},
    "94089": {"label": "Sunnyvale (North)", "median_price": 1_600_000, "price_per_sqft": 1_050},
    # ── Mountain View ──
    "94040": {"label": "Mountain View (South)", "median_price": 2_300_000, "price_per_sqft": 1_350},
    "94041": {"label": "Mountain View", "median_price": 2_100_000, "price_per_sqft": 1_300},
    "94043": {"label": "Mountain View (North)", "median_price": 1_700_000, "price_per_sqft": 1_100},
    # ── Palo Alto / Menlo Park ──
    "94025": {"label": "Menlo Park", "median_price": 2_800_000, "price_per_sqft": 1_500},
    "94301": {"label": "Palo Alto (Downtown)", "median_price": 3_500_000, "price_per_sqft": 1_700},
    "94303": {"label": "Palo Alto (East)", "median_price": 2_600_000, "price_per_sqft": 1_350},
    "94304": {"label": "Palo Alto (Stanford)", "median_price": 3_200_000, "price_per_sqft": 1_650},
    "94306": {"label": "Palo Alto (South)", "median_price": 3_200_000, "price_per_sqft": 1_600},
    # ── San Jose ──
    "95110": {"label": "San Jose (W Downtown)", "median_price": 950_000, "price_per_sqft": 680},
    "95112": {"label": "San Jose (Downtown)", "median_price": 1_100_000, "price_per_sqft": 750},
    "95113": {"label": "San Jose (Central)", "median_price": 1_000_000, "price_per_sqft": 720},
    "95116": {"label": "San Jose (East)", "median_price": 900_000, "price_per_sqft": 650},
    "95118": {"label": "San Jose (Almaden)", "median_price": 1_500_000, "price_per_sqft": 900},
    "95119": {"label": "SJ (Blossom Valley)", "median_price": 1_400_000, "price_per_sqft": 850},
    "95120": {"label": "SJ (Almaden Valley)", "median_price": 2_200_000, "price_per_sqft": 1_150},
    "95121": {"label": "San Jose (SE)", "median_price": 1_100_000, "price_per_sqft": 700},
    "95122": {"label": "San Jose (E Foothills)", "median_price": 950_000, "price_per_sqft": 650},
    "95123": {"label": "San Jose (Blossom Hill)", "median_price": 1_300_000, "price_per_sqft": 800},
    "95124": {"label": "San Jose (Cambrian)", "median_price": 1_600_000, "price_per_sqft": 950},
    "95125": {"label": "San Jose (Willow Glen)", "median_price": 1_600_000, "price_per_sqft": 950},
    "95126": {"label": "San Jose (Shasta)", "median_price": 1_300_000, "price_per_sqft": 850},
    "95127": {"label": "San Jose (Alum Rock)", "median_price": 950_000, "price_per_sqft": 650},
    "95128": {"label": "San Jose (West)", "median_price": 1_500_000, "price_per_sqft": 900},
    "95129": {"label": "San Jose (W Valley)", "median_price": 2_200_000, "price_per_sqft": 1_200},
    "95130": {"label": "San Jose (Westgate)", "median_price": 1_800_000, "price_per_sqft": 1_050},
    "95131": {"label": "San Jose (Berryessa)", "median_price": 1_200_000, "price_per_sqft": 780},
    "95132": {"label": "San Jose (NE)", "median_price": 1_300_000, "price_per_sqft": 800},
    "95133": {"label": "San Jose (N San Jose)", "median_price": 1_100_000, "price_per_sqft": 750},
    "95134": {"label": "San Jose (N First)", "median_price": 1_300_000, "price_per_sqft": 800},
    "95135": {"label": "SJ (Evergreen Hills)", "median_price": 1_800_000, "price_per_sqft": 950},
    "95136": {"label": "San Jose (Snell)", "median_price": 1_100_000, "price_per_sqft": 720},
    "95148": {"label": "San Jose (Evergreen)", "median_price": 1_500_000, "price_per_sqft": 850},
    # ── Campbell ──
    "95008": {"label": "Campbell", "median_price": 1_800_000, "price_per_sqft": 1_050},
    # ── Milpitas ──
    "95035": {"label": "Milpitas", "median_price": 1_500_000, "price_per_sqft": 900},
    # ── Santa Clara ──
    "95050": {"label": "Santa Clara (Central)", "median_price": 1_700_000, "price_per_sqft": 1_050},
    "95051": {"label": "Santa Clara", "median_price": 1_800_000, "price_per_sqft": 1_100},
    "95054": {"label": "Santa Clara (North)", "median_price": 1_500_000, "price_per_sqft": 950},
    # ── Fremont ──
    "94536": {"label": "Fremont (Central)", "median_price": 1_600_000, "price_per_sqft": 900},
    "94538": {"label": "Fremont (Warm Springs)", "median_price": 1_500_000, "price_per_sqft": 880},
    "94539": {"label": "Fremont (Mission SJ)", "median_price": 2_100_000, "price_per_sqft": 1_050},
    "94555": {"label": "Fremont (Ardenwood)", "median_price": 1_700_000, "price_per_sqft": 920},
    # ── Union City ──
    "94587": {"label": "Union City", "median_price": 1_300_000, "price_per_sqft": 800},
    # ── Redwood City ──
    "94063": {"label": "Redwood City", "median_price": 1_600_000, "price_per_sqft": 1_000},
    # ── San Mateo / Burlingame / Millbrae ──
    "94010": {"label": "Burlingame", "median_price": 2_500_000, "price_per_sqft": 1_350},
    "94030": {"label": "Millbrae", "median_price": 2_000_000, "price_per_sqft": 1_150},
    "94401": {"label": "San Mateo (Downtown)", "median_price": 1_600_000, "price_per_sqft": 1_000},
    "94402": {"label": "San Mateo (Hillsdale)", "median_price": 2_200_000, "price_per_sqft": 1_200},
    "94403": {"label": "San Mateo (South)", "median_price": 1_800_000, "price_per_sqft": 1_050},
    # ── Oakland ──
    "94607": {"label": "Oakland (West)", "median_price": 650_000, "price_per_sqft": 550},
    "94610": {"label": "Oakland (Grand Lake)", "median_price": 1_100_000, "price_per_sqft": 750},
    "94611": {"label": "Oakland (Rockridge)", "median_price": 1_500_000, "price_per_sqft": 900},
    "94612": {"label": "Oakland (Downtown)", "median_price": 750_000, "price_per_sqft": 600},
    # ── Berkeley ──
    "94702": {"label": "Berkeley (West)", "median_price": 1_100_000, "price_per_sqft": 780},
    "94704": {"label": "Berkeley (Southside)", "median_price": 1_300_000, "price_per_sqft": 850},
    "94709": {"label": "Berkeley (North)", "median_price": 1_700_000, "price_per_sqft": 1_000},
    # ── Los Gatos / Saratoga ──
    "95030": {"label": "Los Gatos", "median_price": 2_900_000, "price_per_sqft": 1_400},
    "95070": {"label": "Saratoga", "median_price": 3_400_000, "price_per_sqft": 1_500},
}

_ZIP_CENTROIDS: dict[str, tuple[float, float]] = {
    # ── Cupertino ──
    "95014": (37.323, -122.015),
    # ── Sunnyvale ──
    "94085": (37.386, -121.995),
    "94086": (37.372, -122.025),
    "94087": (37.350, -122.035),
    "94089": (37.399, -122.028),
    # ── Mountain View ──
    "94040": (37.373, -122.092),
    "94041": (37.390, -122.078),
    "94043": (37.406, -122.077),
    # ── Palo Alto / Menlo Park ──
    "94025": (37.452, -122.182),
    "94301": (37.445, -122.160),
    "94303": (37.450, -122.120),
    "94304": (37.420, -122.148),
    "94306": (37.418, -122.130),
    # ── San Jose ──
    "95110": (37.335, -121.905),
    "95112": (37.350, -121.880),
    "95113": (37.335, -121.890),
    "95116": (37.350, -121.845),
    "95118": (37.258, -121.875),
    "95119": (37.242, -121.880),
    "95120": (37.215, -121.870),
    "95121": (37.305, -121.815),
    "95122": (37.330, -121.830),
    "95123": (37.245, -121.840),
    "95124": (37.265, -121.920),
    "95125": (37.303, -121.890),
    "95126": (37.330, -121.910),
    "95127": (37.370, -121.825),
    "95128": (37.318, -121.945),
    "95129": (37.305, -121.990),
    "95130": (37.290, -121.975),
    "95131": (37.387, -121.870),
    "95132": (37.395, -121.850),
    "95133": (37.370, -121.862),
    "95134": (37.410, -121.945),
    "95135": (37.310, -121.780),
    "95136": (37.280, -121.850),
    "95148": (37.330, -121.790),
    # ── Campbell ──
    "95008": (37.287, -121.940),
    # ── Milpitas ──
    "95035": (37.433, -121.900),
    # ── Santa Clara ──
    "95050": (37.355, -121.955),
    "95051": (37.350, -121.975),
    "95054": (37.395, -121.960),
    # ── Fremont ──
    "94536": (37.555, -121.985),
    "94538": (37.500, -121.960),
    "94539": (37.525, -121.920),
    "94555": (37.555, -122.040),
    # ── Union City ──
    "94587": (37.590, -122.020),
    # ── Redwood City ──
    "94063": (37.485, -122.220),
    # ── San Mateo / Burlingame / Millbrae ──
    "94010": (37.580, -122.345),
    "94030": (37.598, -122.390),
    "94401": (37.570, -122.320),
    "94402": (37.550, -122.310),
    "94403": (37.535, -122.305),
    # ── Oakland ──
    "94607": (37.795, -122.285),
    "94610": (37.810, -122.245),
    "94611": (37.835, -122.245),
    "94612": (37.805, -122.270),
    # ── Berkeley ──
    "94702": (37.865, -122.290),
    "94704": (37.865, -122.260),
    "94709": (37.880, -122.268),
    # ── Los Gatos / Saratoga ──
    "95030": (37.230, -121.960),
    "95070": (37.264, -122.023),
}

_EARTH_RADIUS_MI = 3958.8
_MAX_LOOKUP_MILES = 5.0


def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return _EARTH_RADIUS_MI * 2 * math.asin(math.sqrt(a))


def _nearest_zip(lat: float, lng: float) -> str | None:
    """Find the nearest zip code centroid within ``_MAX_LOOKUP_MILES``."""
    best_zip: str | None = None
    best_dist = _MAX_LOOKUP_MILES
    for zc, (clat, clng) in _ZIP_CENTROIDS.items():
        d = _haversine_miles(lat, lng, clat, clng)
        if d < best_dist:
            best_dist = d
            best_zip = zc
    return best_zip


def _demo_estimate(zip_code: str) -> PriceEstimate | None:
    data = _RAW_PRICES.get(zip_code)
    if not data:
        return None
    return {
        "zip_code": zip_code,
        "label": data["label"],
        "median_price": data["median_price"],
        "price_per_sqft": data["price_per_sqft"],
        "source": "demo",
    }


def estimate_price(
    lat: float,
    lng: float,
    zip_code: str | None = None,
    *,
    try_redfin: bool = True,
) -> PriceEstimate | None:
    """Estimate housing price for a location.

    Tries a live Redfin scrape for the nearest known property URL, then
    falls back to demo zip code data.

    Args:
        lat: Latitude of the property.
        lng: Longitude of the property.
        zip_code: Optional zip code string (e.g. ``"94087"``).
        try_redfin: Whether to attempt the live Redfin scrape.

    Returns:
        A ``PriceEstimate`` dict, or ``None`` if no data is available.
    """
    resolved_zip = zip_code if (zip_code and zip_code in _RAW_PRICES) else _nearest_zip(lat, lng)
    if not resolved_zip:
        return None

    import db_cache  # noqa: PLC0415

    entry = db_cache.get("prices", resolved_zip, ttl=_PRICE_TTL)
    if entry and entry.is_fresh:
        return entry.value  # type: ignore[return-value]

    stale_fallback: PriceEstimate | None = entry.value if entry else None  # type: ignore[assignment]

    if try_redfin:
        try:
            from api_clients.redfin_client import median_by_zip  # noqa: PLC0415

            live = median_by_zip(resolved_zip)
            if live:
                db_cache.put("prices", resolved_zip, live)
                return live
        except Exception:  # noqa: BLE001
            _log.exception("Redfin scrape failed for zip %s", resolved_zip)

    if stale_fallback:
        return stale_fallback

    demo = _demo_estimate(resolved_zip)
    if demo:
        db_cache.put("prices", resolved_zip, demo)
    return demo


def correlation_samples() -> list[dict[str, str | float]]:
    """Generate a correlation sample point for every zip code in the database.

    Returns:
        One entry per zip with ``label``, ``lat``, ``lng``, and ``zip`` fields.
    """
    return [
        {
            "label": _RAW_PRICES[zc]["label"],
            "lat": _ZIP_CENTROIDS[zc][0],
            "lng": _ZIP_CENTROIDS[zc][1],
            "zip": zc,
        }
        for zc in sorted(_RAW_PRICES)
        if zc in _ZIP_CENTROIDS
    ]
