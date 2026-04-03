#!/usr/bin/env python3
"""Offline DB seeder — scrapes boba shops and housing prices.

Run this in your dev environment before deploying:

    uv run seed_db.py               # full seed (incremental — skips fresh cells)
    uv run seed_db.py --clear       # wipe all DBs first
    uv run seed_db.py --prices-only # only re-scrape prices

Produces two files that ship with the production container:
- ``shops.db``  — boba shop locations
- ``prices.db`` — SFH median home prices by zip code
"""

from __future__ import annotations

import argparse
import time

import price_store
import shop_store
from api_clients.housing_prices import _RAW_PRICES, _ZIP_CENTROIDS
from api_clients.redfin_client import median_by_zip


# ── Phase 1: Boba shops ──────────────────────────────────────────────


def _seed_shops() -> int:
    """Scrape every zip-code centroid and upsert shops into the DB."""
    from api_clients.google_maps_scraper import search_boba_shops  # noqa: PLC0415

    centroids = sorted(_ZIP_CENTROIDS.items())
    total = len(centroids)
    all_added = 0

    for i, (zc, (lat, lng)) in enumerate(centroids, 1):
        label = _RAW_PRICES.get(zc, {}).get("label", zc)  # type: ignore[union-attr]

        if shop_store.is_cell_fresh(lat, lng):
            print(f"  [{i}/{total}] {label} ({zc}) — already fresh, skipping")  # noqa: T201
            continue

        print(f"  [{i}/{total}] {label} ({zc}) — scraping {lat:.3f}, {lng:.3f} …", end="", flush=True)  # noqa: T201

        try:
            shops = search_boba_shops(lat, lng)
            n = shop_store.upsert_shops(shops)
            shop_store.mark_cell_scraped(lat, lng)
            print(f" {n} shops")  # noqa: T201
            all_added += n
        except Exception as exc:  # noqa: BLE001
            print(f" FAILED: {exc}")  # noqa: T201

        time.sleep(1.5)

    return all_added


# ── Phase 2: SFH median prices ──────────────────────────────────────


def _seed_prices() -> tuple[int, int]:
    """Scrape Redfin for Single Family Home median sale prices.

    Returns (scraped_count, fallback_count).
    """
    zips = sorted(z for z in _RAW_PRICES if z in _ZIP_CENTROIDS)
    total = len(zips)
    scraped = 0
    fell_back = 0

    for i, zc in enumerate(zips, 1):
        label = _RAW_PRICES[zc]["label"]
        print(f"  [{i}/{total}] {label} ({zc}) …", end="", flush=True)  # noqa: T201

        try:
            result = median_by_zip(zc)
        except Exception as exc:  # noqa: BLE001
            print(f" scrape error: {exc}", end="")  # noqa: T201
            result = None

        if result:
            price_store.upsert_zip_median(result)
            src = "SFH" if "sfh" in result.get("source", "") else "all"
            print(f" ${result['median_price']:,} ({src})")  # noqa: T201
            scraped += 1
        else:
            raw = _RAW_PRICES.get(zc)
            if raw:
                price_store.upsert_zip_median({
                    "zip_code": zc,
                    "label": raw["label"],
                    "median_price": raw["median_price"],
                    "price_per_sqft": raw["price_per_sqft"],
                    "source": "hardcoded_fallback",
                })
                print(f" FALLBACK ${raw['median_price']:,}")  # noqa: T201
                fell_back += 1
            else:
                print(" NO DATA")  # noqa: T201

        time.sleep(2)

    return scraped, fell_back


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed shops.db + prices.db")
    parser.add_argument("--clear", action="store_true", help="Wipe all DBs before seeding")
    parser.add_argument("--prices-only", action="store_true", help="Only re-scrape prices")
    args = parser.parse_args()

    print("\n  Housing Boba Index — DB Seeder\n")  # noqa: T201

    if args.clear:
        shop_store.clear()
        price_store.clear()
        print("  Cleared all data.\n")  # noqa: T201

    if not args.prices_only:
        print("  Phase 1: Scraping boba shops …\n")  # noqa: T201
        added = _seed_shops()
        total = shop_store.shop_count()
        cells = shop_store.cell_count()
        print(f"\n  Done. {added} shops upserted, {total} total, {cells} cells.\n")  # noqa: T201

    print("  Phase 2: Scraping SFH median prices …\n")  # noqa: T201
    scraped, fell_back = _seed_prices()
    print(f"\n  Done. {scraped} scraped, {fell_back} used hardcoded fallback.\n")  # noqa: T201

    print(f"  shops.db:  {shop_store.shop_count()} shops, {shop_store.cell_count()} cells")  # noqa: T201
    print(f"  prices.db: {price_store.zip_median_count()} zip medians\n")  # noqa: T201

    print("  Note: correlation data is computed at server startup.\n")  # noqa: T201


if __name__ == "__main__":
    main()
