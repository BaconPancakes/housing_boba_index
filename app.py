"""Housing Boba Index -- Flask application."""

from __future__ import annotations

import traceback
from typing import Any

from flask import Flask, Response, jsonify, render_template, request

import config
import shop_store
from api_clients import demo_data
from api_clients.geocoding import geocode_address, reverse_geocode
from api_clients.housing_prices import correlation_samples, estimate_price
from models import ShopData
from scoring import compute_index, is_premium_brand

app = Flask(__name__)

if not config.DEMO_MODE:
    _seeded = shop_store.seed_from_demo()
    if _seeded:
        print(f"  Seeded shop store with {_seeded} demo shops")  # noqa: T201


def _fetch_shops(lat: float, lng: float) -> list[ShopData]:
    """Return boba shops near *lat*, *lng*.

    In scrape / API mode every scraped shop is persisted in the shop
    store (keyed by place-ID) so subsequent queries for overlapping
    areas are pure distance lookups — no re-scraping required.
    """
    if config.DEMO_MODE:
        return demo_data.search_boba_shops(lat, lng, config.SEARCH_RADIUS_MILES)

    _ensure_coverage(lat, lng)
    return shop_store.get_nearby(lat, lng, config.SEARCH_RADIUS_MILES)


def _ensure_coverage(lat: float, lng: float) -> None:
    """Scrape the area around *lat*, *lng* if it hasn't been scraped recently."""
    if shop_store.is_cell_fresh(lat, lng):
        return

    try:
        raw = _search_shops(lat, lng)
        shop_store.upsert_shops(raw)
    except Exception:  # noqa: BLE001
        traceback.print_exc()

    shop_store.mark_cell_scraped(lat, lng)


def _search_shops(lat: float, lng: float) -> list[ShopData]:
    """Dispatch to the configured shop-search backend."""
    if config.USE_SCRAPER:
        from api_clients import google_maps_scraper  # noqa: PLC0415

        return google_maps_scraper.search_boba_shops(lat, lng)

    from api_clients import google_places  # noqa: PLC0415

    return google_places.search_boba_shops(lat, lng)


@app.route("/")
def index() -> str:
    """Serve the single-page application."""
    return render_template(
        "index.html",
        demo_mode=config.DEMO_MODE,
        scrape_mode=config.USE_SCRAPER,
    )


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

    shops = _fetch_shops(lat, lng)
    result_data = compute_index(shops)

    price = estimate_price(lat, lng)

    response: dict[str, Any] = {
        **result_data,
        "address": resolved_address,
        "lat": lat,
        "lng": lng,
        "demo_mode": config.DEMO_MODE,
        "search_radius_miles": config.SEARCH_RADIUS_MILES,
        "price_estimate": price,
        "shops": [
            {
                "id": s.get("id"),
                "name": s.get("name", ""),
                "lat": s.get("lat", 0.0),
                "lng": s.get("lng", 0.0),
                "rating": s.get("rating", 0),
                "review_count": s.get("review_count", 0),
                "address": s.get("address", ""),
                "distance_miles": s.get("distance_miles", 0),
                "categories": s.get("categories", []),
                "is_premium": is_premium_brand(s.get("name", "")),
            }
            for s in shops
        ],
    }

    return jsonify(response)


@app.route("/api/correlation")
def api_correlation() -> Response:
    """Return Boba Index vs. median home price for sample Bay Area locations.

    Used by the frontend scatter-plot chart. Results are computed once and
    cached for the server lifetime.
    """
    import db_cache  # noqa: PLC0415

    _corr_ttl = 90 * 86_400
    entry = db_cache.get("correlation", "all", ttl=_corr_ttl)
    if entry and entry.is_fresh:
        return jsonify(entry.value)

    points: list[dict[str, Any]] = []
    for sample in correlation_samples():
        lat = float(sample["lat"])
        lng = float(sample["lng"])
        zc = str(sample["zip"])
        label = str(sample["label"])

        shops = _fetch_shops(lat, lng)
        idx = compute_index(shops)
        price = estimate_price(lat, lng, zip_code=zc)

        points.append(
            {
                "label": label,
                "lat": lat,
                "lng": lng,
                "boba_index": idx.get("index", 0),
                "grade": idx.get("grade", "F"),
                "median_price": price["median_price"] if price else None,
                "zip_code": zc,
            }
        )

    db_cache.put("correlation", "all", points)
    return jsonify(points)


@app.route("/api/health")
def health() -> Response:
    """Return service health and shop store statistics."""
    return jsonify(
        {
            "status": "ok",
            "demo_mode": config.DEMO_MODE,
            "search_radius_miles": config.SEARCH_RADIUS_MILES,
            "shop_store": {
                "total_shops": shop_store.shop_count(),
                "scraped_cells": shop_store.cell_count(),
            },
        }
    )


def main() -> None:
    """Start the development server."""
    if config.DEMO_MODE:
        mode = "DEMO (curated sample data)"
    elif config.USE_SCRAPER:
        mode = "SCRAPE (Google Maps HTML — no API key needed)"
    else:
        mode = "LIVE (Google Places API)"
    print("\n  Housing Boba Index")  # noqa: T201
    print(f"  Mode: {mode}")  # noqa: T201
    print(f"  Search radius: {config.SEARCH_RADIUS_MILES} miles\n")  # noqa: T201
    app.run(debug=True, host="0.0.0.0", port=5000)  # noqa: S104, S201


if __name__ == "__main__":
    main()
