"""Housing Boba Index scoring engine.

The index (0.00-1.00) quantifies how attractive an address is based on nearby
premium boba shops.  The formula considers:

1. **Shop quality** -- Google rating normalised to 0-1.
2. **Review confidence** -- a log-scaled factor so highly-reviewed shops carry
   more weight, but diminishing returns kick in after ~500 reviews.
3. **Brand premium** -- multiplier for recognised top-tier Asian boba brands
   (Molly Tea, Teazzi, Formosa Aroma, etc.).
4. **Distance decay** -- shops closer to the address contribute exponentially
   more (Gaussian decay with sigma = 0.8 mi).
5. **Density bonus** -- having many shops nearby adds an extra kick, capped to
   avoid runaway scores in hyper-dense areas.

The raw aggregate is passed through a sigmoid to produce a smooth 0.00-1.00 score.
"""

from __future__ import annotations

import math

from config import MAX_INDEX_SCORE, PREMIUM_BRANDS
from models import IndexResult, ShopData, ShopScore

DISTANCE_SIGMA: float = 0.8
REVIEW_LOG_BASE: int = 500
DENSITY_BONUS_CAP: float = 20.0
SIGMOID_MIDPOINT: float = 25.0
SIGMOID_STEEPNESS: float = 0.08
MIN_RATING: float = 3.5  # shops below this rating contribute nothing to the index


def is_premium_brand(name: str) -> bool:
    """Check whether a shop name matches any known premium brand.

    Args:
        name: Shop name to check (case-insensitive substring match).

    Returns:
        ``True`` if the name contains a recognised premium brand.
    """
    lower = name.lower().strip()
    return any(brand in lower for brand in PREMIUM_BRANDS)


def _brand_multiplier(name: str) -> float:
    lower = name.lower().strip()
    for brand, mult in PREMIUM_BRANDS.items():
        if brand in lower:
            return mult
    return 1.0


def _distance_weight(distance_miles: float) -> float:
    return math.exp(-0.5 * (distance_miles / DISTANCE_SIGMA) ** 2)


def _review_confidence(review_count: int) -> float:
    if review_count <= 0:
        return 0.1
    return min(1.4, math.log1p(review_count) / math.log1p(REVIEW_LOG_BASE))


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-SIGMOID_STEEPNESS * (x - SIGMOID_MIDPOINT)))


def score_shop(shop: ShopData, distance_miles: float) -> ShopScore:
    """Score an individual boba shop relative to a target address.

    Args:
        shop: Shop record with at least ``name``, ``rating``, and
            ``review_count`` fields.
        distance_miles: Distance from the target address in miles.

    Returns:
        Per-shop scoring breakdown including raw contribution.
    """
    rating = float(shop.get("rating", 0) or 0)
    review_count = int(shop.get("review_count", 0) or 0)

    quality = rating / 5.0
    confidence = _review_confidence(review_count)
    brand_mult = _brand_multiplier(shop.get("name", ""))
    dist_w = _distance_weight(distance_miles)

    # Shops below MIN_RATING contribute nothing — their presence should not
    # inflate the index.
    raw = 0.0 if rating < MIN_RATING else quality * confidence * brand_mult * dist_w * 10.0

    return {
        "shop_id": shop.get("id", ""),
        "name": shop.get("name", ""),
        "rating": round(rating, 2),
        "review_count": review_count,
        "brand_multiplier": brand_mult,
        "distance_miles": round(distance_miles, 2),
        "distance_weight": round(dist_w, 4),
        "quality": round(quality, 4),
        "confidence": round(confidence, 4),
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

    # Only shops that actually contribute count toward density.
    contributing = sum(1 for d in breakdown if d["raw_contribution"] > 0)
    shop_count = len(breakdown)
    density_bonus = min(DENSITY_BONUS_CAP, contributing * 1.2)
    raw_total += density_bonus

    index_val = round(_sigmoid(raw_total) * MAX_INDEX_SCORE, 2)
    index_val = min(MAX_INDEX_SCORE, max(0.0, index_val))

    grade = _grade(index_val)

    breakdown.sort(key=lambda d: d["raw_contribution"], reverse=True)

    top_brand: str | None = None
    for b in breakdown:
        if b["brand_multiplier"] > 1.0:
            top_brand = b["name"]
            break

    summary_parts = [f"{shop_count} boba shop{'s' if shop_count != 1 else ''} within range."]
    if top_brand:
        premium_count = sum(1 for b in breakdown if b["brand_multiplier"] > 1.0)
        summary_parts.append(
            f"{premium_count} premium brand{'s' if premium_count != 1 else ''}"
            f" detected (e.g. {top_brand})."
        )
    if breakdown:
        best = breakdown[0]
        summary_parts.append(
            f"Top contributor: {best['name']}"
            f" ({best['rating']}\u2605, {best['distance_miles']} mi)."
        )

    return {
        "index": index_val,
        "grade": grade,
        "shop_count": shop_count,
        "density_bonus": round(density_bonus, 2),
        "raw_total": round(raw_total, 2),
        "breakdown": breakdown,
        "summary": " ".join(summary_parts),
    }


def _grade(index: float) -> str:
    if index >= 0.90:  # noqa: PLR2004
        return "S"
    if index >= 0.80:  # noqa: PLR2004
        return "A"
    if index >= 0.65:  # noqa: PLR2004
        return "B"
    if index >= 0.50:  # noqa: PLR2004
        return "C"
    if index >= 0.30:  # noqa: PLR2004
        return "D"
    return "F"
