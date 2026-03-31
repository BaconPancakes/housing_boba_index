"""Application configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()

GOOGLE_PLACES_API_KEY: str = os.getenv("GOOGLE_PLACES_API_KEY", "")

DEMO_MODE: bool = not GOOGLE_PLACES_API_KEY

SEARCH_RADIUS_MILES: float = 3.0
SEARCH_RADIUS_METERS: int = int(SEARCH_RADIUS_MILES * 1609.34)

# Opinionated list of premium boba brands and their scoring multipliers.
# These are matched as substrings against shop names (case-insensitive).

PREMIUM_BRANDS: dict[str, float] = {
    "molly tea": 1.35,
    "teazzi": 1.35,
    "formosa aroma": 1.35,
    "shuyi grass jelly": 1.25,
    "heytea": 1.30,
    "tp tea": 1.2,
    "sunright": 1.2,
    "chicha sansen": 1.3,
    "junenov": 1.3,
    "wanpo": 1.2,
    "ume tea": 1.1,
}

MAX_INDEX_SCORE: float = 1.0
