"""Geocoding via Nominatim (free, no API key required)."""

from __future__ import annotations

import functools

from geopy.exc import GeocoderServiceError, GeocoderTimedOut  # type: ignore[import-untyped]
from geopy.geocoders import Nominatim  # type: ignore[import-untyped]

from models import GeoResult

_geocoder: Nominatim = Nominatim(user_agent="housing-boba-index/1.0")

_TIMEOUT: int = 10


@functools.lru_cache(maxsize=512)
def geocode_address(address: str) -> GeoResult | None:
    """Convert an address string to lat/lng coordinates.

    Results are cached in-process so the same address never hits Nominatim twice.

    Args:
        address: Free-form address string (e.g. ``"350 Grant Ave, SF"``).

    Returns:
        A ``GeoResult`` with ``lat``, ``lng``, and ``display_name``, or
        ``None`` if geocoding failed.
    """
    try:
        location = _geocoder.geocode(address, timeout=_TIMEOUT)  # type: ignore[union-attr]
        if location:
            return {
                "lat": float(location.latitude),  # type: ignore[union-attr]
                "lng": float(location.longitude),  # type: ignore[union-attr]
                "display_name": str(location.address),  # type: ignore[union-attr]
            }
    except (GeocoderTimedOut, GeocoderServiceError):
        pass
    return None


@functools.lru_cache(maxsize=512)
def reverse_geocode(lat: float, lng: float) -> str | None:
    """Convert coordinates to a human-readable address.

    Args:
        lat: Latitude (rounded to 4 decimal places before lookup).
        lng: Longitude (rounded to 4 decimal places before lookup).

    Returns:
        Human-readable address string, or ``None`` on failure.
    """
    lat = round(lat, 4)
    lng = round(lng, 4)
    try:
        location = _geocoder.reverse((lat, lng), timeout=_TIMEOUT)  # type: ignore[union-attr]
        if location:
            return str(location.address)  # type: ignore[union-attr]
    except (GeocoderTimedOut, GeocoderServiceError):
        pass
    return None
