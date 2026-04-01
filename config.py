"""Application configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()

GOOGLE_PLACES_API_KEY: str = os.getenv("GOOGLE_PLACES_API_KEY", "")

# Scrape Google Maps HTML instead of calling the paid Places API.
# Auto-enabled when no API key is configured; set USE_SCRAPER=0 to
# fall back to the built-in demo dataset.
_scrape_env: str = os.getenv("USE_SCRAPER", "")
USE_SCRAPER: bool = (
    _scrape_env.lower() in ("1", "true", "yes")
    if _scrape_env
    else not GOOGLE_PLACES_API_KEY
)

DEMO_MODE: bool = not GOOGLE_PLACES_API_KEY and not USE_SCRAPER

SEARCH_RADIUS_MILES: float = 3.0
SEARCH_RADIUS_METERS: int = int(SEARCH_RADIUS_MILES * 1609.34)

# Opinionated list of premium boba brands and their scoring multipliers.
# These are matched as substrings against shop names (case-insensitive).

PREMIUM_BRANDS: dict[str, float] = {
    "chicha san chen": 1.35,
    "formosa aroma": 1.35,
    "heytea": 1.30,
    "molly tea": 1.35,
    "moontea": 1.30,
    "shuyi grass jelly": 1.25,
    "sunright": 1.2,
    "teazzi": 1.35,
    "tp tea": 1.2,
    "ume": 1.15,
    "wanpo": 1.2,
}

MAX_INDEX_SCORE: float = 1.0
