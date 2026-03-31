# Housing Boba Index

A web application that scores any address in the SF Bay Area by its proximity
to top-tier boba shops from Asia — Molly Tea, Teazzi, Formosa Aroma, Tiger
Sugar, Gong Cha, and more.

The index (0.00–1.00) considers shop quality, review volume, distance, brand
prestige, and density. Results are displayed on an interactive map.

## Quick start

```bash
uv sync
uv run python app.py
```

Then open **http://localhost:5000** in your browser.

The app launches in **demo mode** with curated Bay Area data. To use live
data from Google Places, create a `.env` file (see `.env.example`) with your
API key.

## How the score works

| Factor | Description |
|---|---|
| **Shop quality** | Google rating normalised 0–1 |
| **Review confidence** | Log-scaled — 500+ reviews ≈ full confidence |
| **Brand premium** | 1.1×–1.35× multiplier for recognised Asian chains |
| **Distance decay** | Gaussian (σ = 0.6 mi) — closer shops count more |
| **Density bonus** | Extra points for having many shops nearby (capped) |

Raw score is passed through a sigmoid to produce a smooth 0.00–1.00 index,
then mapped to a letter grade (S / A / B / C / D / F).

## Premium brands

The scoring engine has a built-in list of premium boba brands from Asia that
receive a scoring multiplier (1.1×–1.35×). These are matched as substrings
against shop names. The current list includes:

Molly Tea, Teazzi, Formosa Aroma, Tiger Sugar, Gong Cha, CoCo, Happy Lemon,
Yi Fang, The Alley, Xing Fu Tang, Heytea, Nayuki, OneZo, Ding Tea,
Kung Fu Tea, Share Tea, Quickly, Tea Station.

Edit `PREMIUM_BRANDS` in `config.py` to add or adjust brands.

## Project structure

```
app.py               Flask application + API routes
config.py            Settings, API key, premium brand list
scoring.py           Index computation engine
cache.py             Grid-snapped in-memory cache (7-day TTL)
api_clients/
  google_places.py   Google Places API client
  geocoding.py       Nominatim geocoding (free)
  demo_data.py       Curated Bay Area demo dataset
templates/
  index.html         Single-page app shell
static/
  css/style.css      Dark-theme UI
  js/app.js          Leaflet map + score rendering
```

## Google Places API key (optional)

Copy `.env.example` to `.env` and fill in your key:

```
GOOGLE_PLACES_API_KEY=your_key_here
```

Get one at https://console.cloud.google.com/apis/credentials (enable the
**Places API**). The free tier includes $200/month in credit.

When no key is present the app falls back to built-in demo data.
