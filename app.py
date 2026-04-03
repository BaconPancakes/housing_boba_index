"""Housing Boba Index -- Flask application.

Production mode: reads from a pre-seeded ``shops.db`` (populated offline
by ``seed_db.py``).  No scraping or external API calls for shop data.
"""

from __future__ import annotations

from typing import Any

from flask import Flask, Response, jsonify, render_template, request

import db_cache
import price_store
import shop_store
from api_clients.geocoding import geocode_address, reverse_geocode
from api_clients.housing_prices import _RAW_PRICES, _ZIP_CENTROIDS, estimate_price
from config import SEARCH_RADIUS_MILES
from scoring import Scorer, compute_raw, is_blacklisted, is_curated_brand, is_premium_brand

app = Flask(__name__)

_SCORE_CACHE_TTL = 90 * 86_400  # 90 days


def _build_scorer() -> Scorer:
    """Calibrate a Scorer from raw scores across all zip centroids."""
    raw_scores = [
        compute_raw(shop_store.get_nearby(lat, lng, SEARCH_RADIUS_MILES))
        for lat, lng in _ZIP_CENTROIDS.values()
    ]
    db_cache.clear("scores")
    return Scorer(raw_scores)


scorer = _build_scorer()


def _compute_correlation() -> list[dict[str, Any]]:
    """Compute boba-index-vs-price correlation for all zip codes."""
    points: list[dict[str, Any]] = []
    for zc in sorted(_RAW_PRICES):
        if zc not in _ZIP_CENTROIDS:
            continue
        lat, lng = _ZIP_CENTROIDS[zc]
        label = _RAW_PRICES[zc]["label"]
        shops = shop_store.get_nearby(lat, lng, SEARCH_RADIUS_MILES)
        idx = scorer.compute_index(shops)
        price_est = price_store.get_zip_median(zc)
        points.append({
            "zip_code": zc,
            "label": label,
            "lat": lat,
            "lng": lng,
            "boba_index": idx.get("index", 0),
            "grade": idx.get("grade", "F"),
            "median_price": price_est["median_price"] if price_est else None,
        })
    return points


def _cache_key(lat: float, lng: float) -> str:
    """Round to ~100 m grid for cache dedup."""
    return f"{lat:.3f},{lng:.3f}"


@app.route("/")
def index() -> str:
    """Serve the single-page application."""
    return render_template("index.html")


@app.route("/api/score", methods=["GET"])
def api_score() -> tuple[Response, int] | Response:
    """Compute the Housing Boba Index for an address or coordinate pair.

    Query params: ``address`` OR (``lat`` + ``lng``).
    """
    address = request.args.get("address", "").strip()
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)

    resolved_address: str

    if address:
        geo = geocode_address(address)
        if not geo:
            return jsonify({"error": f"Could not geocode address: {address}"}), 400
        lat, lng = geo["lat"], geo["lng"]
        resolved_address = geo["display_name"]
    elif lat is not None and lng is not None:
        resolved_address = reverse_geocode(lat, lng) or f"{lat:.5f}, {lng:.5f}"
    else:
        return jsonify({"error": "Provide 'address' or both 'lat' and 'lng'."}), 400

    ck = _cache_key(lat, lng)
    cached = db_cache.get("scores", ck, ttl=_SCORE_CACHE_TTL)
    if cached and cached.is_fresh:
        hit: dict[str, Any] = cached.value
        hit["address"] = resolved_address
        return jsonify(hit)

    shops = shop_store.get_nearby(lat, lng, SEARCH_RADIUS_MILES)
    result_data = scorer.compute_index(shops)
    price = estimate_price(lat, lng)

    visible_shops = [s for s in shops if not is_blacklisted(s.get("name", ""))]

    response: dict[str, Any] = {
        **result_data,
        "address": resolved_address,
        "lat": lat,
        "lng": lng,
        "search_radius_miles": SEARCH_RADIUS_MILES,
        "price_estimate": price,
        "shops": [
            {
                "id": s.get("id"),
                "name": s.get("name", ""),
                "lat": s.get("lat", 0.0),
                "lng": s.get("lng", 0.0),
                "address": s.get("address", ""),
                "distance_miles": s.get("distance_miles", 0),
                "categories": s.get("categories", []),
                "is_premium": is_premium_brand(s.get("name", "")),
                "is_curated": is_curated_brand(s.get("name", "")),
            }
            for s in visible_shops
        ],
    }

    db_cache.put("scores", ck, response)
    return jsonify(response)


@app.route("/api/correlation")
def api_correlation() -> Response:
    """Return Boba Index vs. median home price for all zip codes.

    Computed once on first request and cached for the server lifetime.
    """
    if not hasattr(app, "_correlation_cache"):
        app._correlation_cache = _compute_correlation()  # type: ignore[attr-defined]
    return jsonify(app._correlation_cache)  # type: ignore[attr-defined]


@app.route("/api/health")
def health() -> Response:
    """Return service health and shop store statistics."""
    return jsonify(
        {
            "status": "ok",
            "search_radius_miles": SEARCH_RADIUS_MILES,
            "shop_store": {
                "total_shops": shop_store.shop_count(),
                "scraped_cells": shop_store.cell_count(),
            },
        }
    )


def main() -> None:
    """Start the development server."""
    n = shop_store.shop_count()
    print("\n  Housing Boba Index")  # noqa: T201
    print(f"  Shop DB: {n} shops loaded")  # noqa: T201
    print(f"  Search radius: {SEARCH_RADIUS_MILES} miles\n")  # noqa: T201
    if n == 0:
        print("  WARNING: shops.db is empty — run `uv run seed_db.py` first.\n")  # noqa: T201
    app.run(debug=True, host="0.0.0.0", port=5000)  # noqa: S104, S201


if __name__ == "__main__":
    main()
