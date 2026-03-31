"""Generates realistic demo boba shop data for the South Bay, East Bay, and Peninsula.

Covers Sunnyvale, Cupertino, San Jose, Milpitas, Mountain View, Palo Alto,
Fremont, Oakland, Berkeley, and San Mateo/Burlingame with a curated mix of
premium Asian brands and local favourites.
"""

from __future__ import annotations

import hashlib
import math
from typing import TypedDict

from models import ShopData


class _RawShop(TypedDict):
    name: str
    lat: float
    lng: float
    rating: float
    reviews: int
    addr: str


DEMO_SHOPS_DB: list[_RawShop] = [
    # ── San Mateo / Burlingame ──
    {
        "name": "Tiger Sugar",
        "lat": 37.5630,
        "lng": -122.3220,
        "rating": 4.5,
        "reviews": 634,
        "addr": "218 E 4th Ave, San Mateo, CA",
    },
    {
        "name": "Teazzi",
        "lat": 37.5785,
        "lng": -122.3480,
        "rating": 4.4,
        "reviews": 312,
        "addr": "1208 Broadway, Burlingame, CA",
    },
    {
        "name": "Happy Lemon",
        "lat": 37.5620,
        "lng": -122.3250,
        "rating": 4.2,
        "reviews": 289,
        "addr": "65 E 3rd Ave, San Mateo, CA",
    },
    # ── Oakland · Chinatown / Downtown ──
    {
        "name": "Formosa Aroma",
        "lat": 37.8005,
        "lng": -122.2715,
        "rating": 4.5,
        "reviews": 378,
        "addr": "388 9th St, Oakland, CA",
    },
    {
        "name": "Ding Tea",
        "lat": 37.7990,
        "lng": -122.2700,
        "rating": 4.2,
        "reviews": 445,
        "addr": "268 10th St, Oakland, CA",
    },
    {
        "name": "Yi Fang",
        "lat": 37.8015,
        "lng": -122.2690,
        "rating": 4.3,
        "reviews": 267,
        "addr": "365 8th St, Oakland, CA",
    },
    {
        "name": "Quickly",
        "lat": 37.7980,
        "lng": -122.2720,
        "rating": 3.9,
        "reviews": 567,
        "addr": "398 11th St, Oakland, CA",
    },
    # ── Oakland · Temescal / Rockridge ──
    {
        "name": "Boba Guys",
        "lat": 37.8350,
        "lng": -122.2630,
        "rating": 4.4,
        "reviews": 678,
        "addr": "4525 Telegraph Ave, Oakland, CA",
    },
    {
        "name": "Asha Tea House",
        "lat": 37.8400,
        "lng": -122.2510,
        "rating": 4.6,
        "reviews": 534,
        "addr": "5515 College Ave, Oakland, CA",
    },
    # ── Berkeley ──
    {
        "name": "Asha Tea House",
        "lat": 37.8660,
        "lng": -122.2590,
        "rating": 4.7,
        "reviews": 823,
        "addr": "2086 University Ave, Berkeley, CA",
    },
    {
        "name": "Feng Cha",
        "lat": 37.8690,
        "lng": -122.2580,
        "rating": 4.3,
        "reviews": 412,
        "addr": "2120 Oxford St, Berkeley, CA",
    },
    {
        "name": "Sweetheart Cafe",
        "lat": 37.8710,
        "lng": -122.2680,
        "rating": 4.2,
        "reviews": 234,
        "addr": "1344 Shattuck Ave, Berkeley, CA",
    },
    {
        "name": "Share Tea",
        "lat": 37.8655,
        "lng": -122.2575,
        "rating": 4.0,
        "reviews": 345,
        "addr": "2079 University Ave, Berkeley, CA",
    },
    # ── Fremont / Union City ──
    {
        "name": "Tiger Sugar",
        "lat": 37.5485,
        "lng": -121.9886,
        "rating": 4.3,
        "reviews": 567,
        "addr": "39133 Fremont Hub, Fremont, CA",
    },
    {
        "name": "Gong Cha",
        "lat": 37.5510,
        "lng": -121.9840,
        "rating": 4.1,
        "reviews": 445,
        "addr": "43440 Christy St, Fremont, CA",
    },
    {
        "name": "Kung Fu Tea",
        "lat": 37.5530,
        "lng": -121.9860,
        "rating": 4.0,
        "reviews": 334,
        "addr": "3949 Stevenson Blvd, Fremont, CA",
    },
    {
        "name": "Quickly",
        "lat": 37.5880,
        "lng": -122.0190,
        "rating": 3.8,
        "reviews": 289,
        "addr": "33000 Dyer St, Union City, CA",
    },
    # ── San Jose · Downtown / Japantown ──
    {
        "name": "Molly Tea",
        "lat": 37.3382,
        "lng": -121.8863,
        "rating": 4.6,
        "reviews": 512,
        "addr": "92 S 1st St, San Jose, CA",
    },
    {
        "name": "Tiger Sugar",
        "lat": 37.3365,
        "lng": -121.8895,
        "rating": 4.4,
        "reviews": 878,
        "addr": "156 S 2nd St, San Jose, CA",
    },
    {
        "name": "Xing Fu Tang",
        "lat": 37.3400,
        "lng": -121.8910,
        "rating": 4.5,
        "reviews": 634,
        "addr": "54 W Santa Clara St, San Jose, CA",
    },
    {
        "name": "The Alley",
        "lat": 37.3350,
        "lng": -121.8880,
        "rating": 4.3,
        "reviews": 412,
        "addr": "244 Jackson St, San Jose, CA",
    },
    {
        "name": "Ding Tea",
        "lat": 37.3340,
        "lng": -121.8850,
        "rating": 4.1,
        "reviews": 345,
        "addr": "299 E Santa Clara St, San Jose, CA",
    },
    {
        "name": "CoCo",
        "lat": 37.3310,
        "lng": -121.8870,
        "rating": 4.0,
        "reviews": 523,
        "addr": "349 E William St, San Jose, CA",
    },
    # ── Cupertino ──
    {
        "name": "Heytea",
        "lat": 37.3230,
        "lng": -122.0322,
        "rating": 4.7,
        "reviews": 389,
        "addr": "10123 N Wolfe Rd, Cupertino, CA",
    },
    {
        "name": "Tiger Sugar",
        "lat": 37.3210,
        "lng": -122.0340,
        "rating": 4.4,
        "reviews": 723,
        "addr": "19620 Vallco Pkwy, Cupertino, CA",
    },
    {
        "name": "TP Tea",
        "lat": 37.3225,
        "lng": -122.0310,
        "rating": 4.5,
        "reviews": 412,
        "addr": "10171 S De Anza Blvd, Cupertino, CA",
    },
    {
        "name": "Sunright Tea Studio",
        "lat": 37.3195,
        "lng": -122.0290,
        "rating": 4.6,
        "reviews": 534,
        "addr": "20803 Stevens Creek Blvd, Cupertino, CA",
    },
    {
        "name": "Molly Tea",
        "lat": 37.3220,
        "lng": -122.0355,
        "rating": 4.5,
        "reviews": 445,
        "addr": "19500 Pruneridge Ave, Cupertino, CA",
    },
    {
        "name": "Teazzi",
        "lat": 37.3185,
        "lng": -122.0305,
        "rating": 4.4,
        "reviews": 367,
        "addr": "20735 Stevens Creek Blvd, Cupertino, CA",
    },
    {
        "name": "Xing Fu Tang",
        "lat": 37.3240,
        "lng": -122.0335,
        "rating": 4.6,
        "reviews": 489,
        "addr": "10123 N Wolfe Rd Ste 2060, Cupertino, CA",
    },
    {
        "name": "Gong Cha",
        "lat": 37.3200,
        "lng": -122.0310,
        "rating": 4.2,
        "reviews": 378,
        "addr": "20807 Stevens Creek Blvd, Cupertino, CA",
    },
    {
        "name": "Feng Cha",
        "lat": 37.3215,
        "lng": -122.0265,
        "rating": 4.3,
        "reviews": 267,
        "addr": "10919 N Wolfe Rd, Cupertino, CA",
    },
    # ── Sunnyvale ──
    {
        "name": "Tiger Sugar",
        "lat": 37.3505,
        "lng": -122.0360,
        "rating": 4.5,
        "reviews": 612,
        "addr": "1233 W El Camino Real, Sunnyvale, CA",
    },
    {
        "name": "Happy Lemon",
        "lat": 37.3680,
        "lng": -122.0140,
        "rating": 4.2,
        "reviews": 456,
        "addr": "132 E El Camino Real, Sunnyvale, CA",
    },
    {
        "name": "Gong Cha",
        "lat": 37.3700,
        "lng": -122.0160,
        "rating": 4.1,
        "reviews": 312,
        "addr": "159 S Murphy Ave, Sunnyvale, CA",
    },
    {
        "name": "Molly Tea",
        "lat": 37.3520,
        "lng": -122.0310,
        "rating": 4.6,
        "reviews": 378,
        "addr": "1245 W El Camino Real, Sunnyvale, CA",
    },
    {
        "name": "Teazzi",
        "lat": 37.3540,
        "lng": -122.0340,
        "rating": 4.5,
        "reviews": 289,
        "addr": "1080 W El Camino Real, Sunnyvale, CA",
    },
    {
        "name": "TP Tea",
        "lat": 37.3560,
        "lng": -122.0280,
        "rating": 4.3,
        "reviews": 345,
        "addr": "890 W El Camino Real, Sunnyvale, CA",
    },
    {
        "name": "Xing Fu Tang",
        "lat": 37.3485,
        "lng": -122.0320,
        "rating": 4.4,
        "reviews": 423,
        "addr": "1390 W El Camino Real, Sunnyvale, CA",
    },
    {
        "name": "OneZo",
        "lat": 37.3510,
        "lng": -122.0295,
        "rating": 4.3,
        "reviews": 256,
        "addr": "1171 Homestead Rd, Sunnyvale, CA",
    },
    {
        "name": "Sunright Tea Studio",
        "lat": 37.3575,
        "lng": -122.0250,
        "rating": 4.5,
        "reviews": 312,
        "addr": "725 S Wolfe Rd, Sunnyvale, CA",
    },
    # ── Milpitas ──
    {
        "name": "Molly Tea",
        "lat": 37.4323,
        "lng": -121.8996,
        "rating": 4.5,
        "reviews": 367,
        "addr": "338 Barber Ln, Milpitas, CA",
    },
    {
        "name": "Nayuki",
        "lat": 37.4340,
        "lng": -121.8970,
        "rating": 4.6,
        "reviews": 234,
        "addr": "525 Great Mall Dr, Milpitas, CA",
    },
    {
        "name": "Kung Fu Tea",
        "lat": 37.4310,
        "lng": -121.9010,
        "rating": 4.0,
        "reviews": 445,
        "addr": "292 S Abel St, Milpitas, CA",
    },
    {
        "name": "OneZo",
        "lat": 37.4350,
        "lng": -121.8950,
        "rating": 4.4,
        "reviews": 312,
        "addr": "649 Great Mall Dr, Milpitas, CA",
    },
    # ── Mountain View / Palo Alto ──
    {
        "name": "Teazzi",
        "lat": 37.3861,
        "lng": -122.0839,
        "rating": 4.5,
        "reviews": 278,
        "addr": "267 Castro St, Mountain View, CA",
    },
    {
        "name": "Gong Cha",
        "lat": 37.4449,
        "lng": -122.1600,
        "rating": 4.2,
        "reviews": 345,
        "addr": "528 University Ave, Palo Alto, CA",
    },
    {
        "name": "Boba Guys",
        "lat": 37.4430,
        "lng": -122.1620,
        "rating": 4.5,
        "reviews": 567,
        "addr": "444 University Ave, Palo Alto, CA",
    },
]

_EARTH_RADIUS_MI = 3958.8


def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return _EARTH_RADIUS_MI * 2 * math.asin(math.sqrt(a))


def _stable_id(name: str, lat: float, lng: float) -> str:
    raw = f"{name}:{lat:.6f}:{lng:.6f}"
    return hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:16]


def search_boba_shops(
    lat: float,
    lng: float,
    radius_miles: float = 3.0,
) -> list[ShopData]:
    """Return demo shops within *radius_miles* of the given coordinate.

    Args:
        lat: Centre latitude for the search.
        lng: Centre longitude for the search.
        radius_miles: Search radius in miles.

    Returns:
        List of ``ShopData`` dicts sorted by distance, nearest first.
    """
    results: list[ShopData] = []
    for shop in DEMO_SHOPS_DB:
        dist = _haversine_miles(lat, lng, shop["lat"], shop["lng"])
        if dist <= radius_miles:
            results.append(
                {
                    "source": "demo",
                    "id": _stable_id(shop["name"], shop["lat"], shop["lng"]),
                    "name": shop["name"],
                    "lat": shop["lat"],
                    "lng": shop["lng"],
                    "rating": shop["rating"],
                    "review_count": shop["reviews"],
                    "address": shop["addr"],
                    "categories": ["Bubble Tea", "Tea"],
                    "distance_miles": round(dist, 2),
                }
            )
    results.sort(key=lambda s: s.get("distance_miles", 0.0))
    return results
