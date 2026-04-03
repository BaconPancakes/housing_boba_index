"""Housing Boba Index scoring engine.

Four-tier prestige model:

1. **Premium** -- hand-labeled top-tier brands (highest weight).
2. **Curated** -- hand-labeled notable shops (medium weight).
3. **Default** -- all other shops (base weight).
4. **Blacklisted** -- hand-labeled exclusions (zero contribution).

Each non-blacklisted shop contributes ``tier_weight / (1 + distance_miles)``.
The raw sum is normalized to 0.00-1.00 via a sigmoid whose parameters are
calibrated dynamically from the observed score distribution.
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


def compute_raw(shops_with_distance: list[ShopData]) -> float:
    """Return the raw (unnormalized) score sum for a set of nearby shops."""
    total = 0.0
    for shop in shops_with_distance:
        tier, weight = _classify_tier(shop.get("name", ""))
        if tier != "blacklisted":
            total += weight / (1.0 + shop.get("distance_miles", 0.0))
    return total


class Scorer:
    """Encapsulates the sigmoid normalization calibrated from observed data."""

    def __init__(self, raw_scores: list[float] | None = None) -> None:
        """Create a scorer, optionally calibrating from observed raw scores."""
        self._midpoint = 12.0
        self._k = 0.15
        if raw_scores:
            self.calibrate(raw_scores)

    def calibrate(self, raw_scores: list[float]) -> None:
        """Set sigmoid parameters from the observed raw score distribution.

        The midpoint is set to the median. k is derived from the IQR so
        that p25 maps to ~0.25 and p75 maps to ~0.75, giving a wide
        spread across the full 0-1 range.
        """
        if not raw_scores:
            return
        s = sorted(raw_scores)
        n = len(s)
        self._midpoint = s[n // 2]
        p25 = s[max(int(n * 0.25), 0)]
        p75 = s[min(int(n * 0.75), n - 1)]
        iqr = p75 - p25
        self._k = 2 * math.log(3) / iqr if iqr > 0 else 0.15

    def normalize(self, raw: float) -> float:
        """Map a raw score to 0.00-1.00 via sigmoid."""
        return 1.0 / (1.0 + math.exp(-self._k * (raw - self._midpoint)))

    def compute_index(self, shops_with_distance: list[ShopData]) -> IndexResult:
        """Compute the Housing Boba Index for a set of nearby shops."""
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
        index_val = round(self.normalize(raw_total), 2)
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


def score_shop(shop: ShopData, distance_miles: float) -> ShopScore:
    """Score an individual boba shop relative to a target address."""
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
