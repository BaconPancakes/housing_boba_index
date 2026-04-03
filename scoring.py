"""Housing Boba Index scoring engine.

Four-tier prestige model:

1. **Premium** — hand-labeled top-tier brands (highest weight).
2. **Curated** — hand-labeled notable shops (medium weight).
3. **Default** — all other shops (base weight).
4. **Blacklisted** — hand-labeled exclusions (zero contribution).

Each non-blacklisted shop contributes ``tier_weight / (1 + distance_miles)``.
The raw sum is normalized to 0.00-1.00 via a sigmoid calibrated against
the observed score distribution across Bay Area zip codes.
"""

from __future__ import annotations

import math

from config import (
    BLACKLISTED_SHOPS,
    CURATED_BRANDS,
    PREMIUM_BRANDS,
    WEIGHT_CURATED,
    WEIGHT_DEFAULT,
    WEIGHT_PREMIUM,
)
from models import IndexResult, ShopData, ShopScore


def _classify_tier(name: str) -> tuple[str, float]:
    """Return ``(tier_name, weight)`` for a shop name.

    Resolution order: blacklisted > premium > curated > default.
    """
    lower = name.lower().strip()
    if any(kw in lower for kw in BLACKLISTED_SHOPS):
        return ("blacklisted", 0.0)
    if any(kw in lower for kw in PREMIUM_BRANDS):
        return ("premium", WEIGHT_PREMIUM)
    if any(kw in lower for kw in CURATED_BRANDS):
        return ("curated", WEIGHT_CURATED)
    return ("default", WEIGHT_DEFAULT)


def is_premium_brand(name: str) -> bool:
    """Check whether a shop name matches any known premium brand."""
    lower = name.lower().strip()
    return any(brand in lower for brand in PREMIUM_BRANDS)


def is_curated_brand(name: str) -> bool:
    """Check whether a shop name matches any curated brand."""
    lower = name.lower().strip()
    return any(brand in lower for brand in CURATED_BRANDS)


def is_blacklisted(name: str) -> bool:
    """Check whether a shop name matches the blacklist."""
    lower = name.lower().strip()
    return any(kw in lower for kw in BLACKLISTED_SHOPS)


def score_shop(shop: ShopData, distance_miles: float) -> ShopScore:
    """Score an individual boba shop relative to a target address.

    Args:
        shop: Shop record with at least a ``name`` field.
        distance_miles: Distance from the target address in miles.

    Returns:
        Per-shop scoring breakdown including raw contribution.
    """
    tier, weight = _classify_tier(shop.get("name", ""))
    raw = 0.0 if tier == "blacklisted" else weight / (1.0 + distance_miles)

    return {
        "shop_id": shop.get("id", ""),
        "name": shop.get("name", ""),
        "tier": tier,
        "tier_weight": weight,
        "distance_miles": round(distance_miles, 2),
        "raw_contribution": round(raw, 4),
    }


def compute_index(shops_with_distance: list[ShopData]) -> IndexResult:
    """Compute the Housing Boba Index for a set of nearby shops.

    Args:
        shops_with_distance: Each dict must include the shop fields **plus** a
            ``distance_miles`` key indicating how far it is from the target
            address.

    Returns:
        Dict with ``index``, ``grade``, ``breakdown`` (per-shop), and
        ``summary`` statistics.
    """
    if not shops_with_distance:
        return {
            "index": 0,
            "grade": "F",
            "shop_count": 0,
            "breakdown": [],
            "summary": "No boba shops found nearby.",
        }

    breakdown: list[ShopScore] = []
    raw_total = 0.0
    for shop in shops_with_distance:
        detail = score_shop(shop, shop.get("distance_miles", 0.0))
        raw_total += detail["raw_contribution"]
        breakdown.append(detail)

    shop_count = len(breakdown)
    index_val = round(_normalize(raw_total), 2)
    grade = _grade(index_val)

    breakdown.sort(key=lambda d: d["raw_contribution"], reverse=True)

    top_premium: str | None = None
    for b in breakdown:
        if b["tier"] == "premium":
            top_premium = b["name"]
            break

    summary_parts = [f"{shop_count} boba shop{'s' if shop_count != 1 else ''} within range."]
    premium_count = sum(1 for b in breakdown if b["tier"] == "premium")
    if top_premium:
        summary_parts.append(
            f"{premium_count} premium brand{'s' if premium_count != 1 else ''}"
            f" detected (e.g. {top_premium})."
        )
    if breakdown:
        best = breakdown[0]
        summary_parts.append(
            f"Top contributor: {best['name']}"
            f" ({best['tier']}, {best['distance_miles']} mi)."
        )

    return {
        "index": index_val,
        "grade": grade,
        "shop_count": shop_count,
        "raw_total": round(raw_total, 2),
        "breakdown": breakdown,
        "summary": " ".join(summary_parts),
    }


# Sigmoid calibrated on 62 Bay Area zip centroids (raw range ~2-35, median ~12).
_SIGMOID_MIDPOINT = 12.0
_SIGMOID_K = 0.15


def _normalize(raw: float) -> float:
    """Map a raw score to 0.00-1.00 via sigmoid."""
    return 1.0 / (1.0 + math.exp(-_SIGMOID_K * (raw - _SIGMOID_MIDPOINT)))


def _grade(index: float) -> str:
    if index >= 0.90:  # noqa: PLR2004
        return "S"
    if index >= 0.75:  # noqa: PLR2004
        return "A"
    if index >= 0.60:  # noqa: PLR2004
        return "B"
    if index >= 0.40:  # noqa: PLR2004
        return "C"
    if index >= 0.20:  # noqa: PLR2004
        return "D"
    return "F"
