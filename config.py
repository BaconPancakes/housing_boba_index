"""Application configuration."""

SEARCH_RADIUS_MILES: float = 3.0
SEARCH_RADIUS_METERS: int = int(SEARCH_RADIUS_MILES * 1609.34)
WEIGHT_PREMIUM: float = 10.0
WEIGHT_CURATED: float = 5
WEIGHT_DEFAULT: float = 1.0

MAX_INDEX_SCORE: float = 1.0


# ── Shop prestige tiers (matched as case-insensitive substrings) ──────
#
# Tier resolution order: blacklisted > premium > curated > default.

PREMIUM_BRANDS: set[str] = {
    "chicha san chen",
    "formosa aroma",
    "heytea",
    "molly tea",
    "moontea",
    "shuyi grass jelly",
    "sunright",
    "teazzi",
    "tp tea",
    "wanpo",
    "junenov",
    "yogost",
    "shu shia",
}

CURATED_BRANDS: set[str] = {
    "ume",
    "ten ren",
    "tea era",
    "7 leaves",
    "o2 valley",
    "boba bliss",
    "shang yu lin",
    "teaspoon,"
    "yifang",
}

BLACKLISTED_SHOPS: set[str] = {
    "mia's",
    "liang's village",
    "honeyberry",
    "sips & scoops",
    "frozo",
    "the crepe stop",
    "sunfish poke",
    "alice street bakery",
    "milk & honey cafe",
    "u :dessert story",
    "mochi waffle corner",
}

