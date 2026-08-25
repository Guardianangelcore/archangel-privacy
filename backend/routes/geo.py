# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""GEOGRAPHIC FLUIDITY — dynamic proximity & language context.

Default context: Prague, Czech Republic (founder's location). All searches for
doctors, clinics and pharmacies prioritize the user's geo city. Travel Mode:
when GPS coordinates move to another supported city, the OS re-indexes local
providers and (optionally) switches the UI + voice language to the local tongue.
"""
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import math

from core import api, db, get_current_user, clean

# Supported city index — city display name, country, local language, coords, timezone
CITIES = [
    {"city": "Praha", "country": "CZ", "lang": "cs", "lat": 50.0755, "lng": 14.4378, "tz": "Europe/Prague"},
    {"city": "Brno", "country": "CZ", "lang": "cs", "lat": 49.1951, "lng": 16.6068, "tz": "Europe/Prague"},
    {"city": "Ostrava", "country": "CZ", "lang": "cs", "lat": 49.8209, "lng": 18.2625, "tz": "Europe/Prague"},
    {"city": "Bratislava", "country": "SK", "lang": "sk", "lat": 48.1486, "lng": 17.1077, "tz": "Europe/Bratislava"},
    {"city": "Košice", "country": "SK", "lang": "sk", "lat": 48.7164, "lng": 21.2611, "tz": "Europe/Bratislava"},
    {"city": "Viedeň", "country": "AT", "lang": "de", "lat": 48.2082, "lng": 16.3738, "tz": "Europe/Vienna"},
    {"city": "Berlín", "country": "DE", "lang": "de", "lat": 52.52, "lng": 13.405, "tz": "Europe/Berlin"},
    {"city": "Mníchov", "country": "DE", "lang": "de", "lat": 48.1351, "lng": 11.582, "tz": "Europe/Berlin"},
    {"city": "Paríž", "country": "FR", "lang": "fr", "lat": 48.8566, "lng": 2.3522, "tz": "Europe/Paris"},
    {"city": "Londýn", "country": "GB", "lang": "en", "lat": 51.5074, "lng": -0.1278, "tz": "Europe/London"},
    {"city": "Varšava", "country": "PL", "lang": "pl", "lat": 52.2297, "lng": 21.0122, "tz": "Europe/Warsaw"},
    {"city": "Krakov", "country": "PL", "lang": "pl", "lat": 50.0647, "lng": 19.945, "tz": "Europe/Warsaw"},
    {"city": "Budapešť", "country": "HU", "lang": "hu", "lat": 47.4979, "lng": 19.0402, "tz": "Europe/Budapest"},
    {"city": "Rím", "country": "IT", "lang": "it", "lat": 41.9028, "lng": 12.4964, "tz": "Europe/Rome"},
    {"city": "Madrid", "country": "ES", "lang": "es", "lat": 40.4168, "lng": -3.7038, "tz": "Europe/Madrid"},
    {"city": "Kyjev", "country": "UA", "lang": "uk", "lat": 50.4501, "lng": 30.5234, "tz": "Europe/Kyiv"},
]

DEFAULT_GEO = {"city": "Praha", "country": "CZ", "lang": "cs", "tz": "Europe/Prague",
               "lat": 50.0755, "lng": 14.4378, "source": "default"}


def geo_of(user: dict) -> dict:
    """Current geo context of a user — defaults to Prague, CZ."""
    g = user.get("geo") or {}
    return {**DEFAULT_GEO, **g} if g else dict(DEFAULT_GEO)


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_city(lat: float, lng: float) -> dict:
    best, best_d = CITIES[0], float("inf")
    for c in CITIES:
        d = _haversine_km(lat, lng, c["lat"], c["lng"])
        if d < best_d:
            best, best_d = c, d
    return {**best, "distance_km": round(best_d, 1)}


@api.get("/geo/context")
async def geo_context(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return {"geo": clean(geo_of(user)), "travel_mode": bool(user.get("travel_mode")),
            "supported_cities": [{"city": c["city"], "country": c["country"], "lang": c["lang"]} for c in CITIES]}


class TravelModeIn(BaseModel):
    enabled: bool


@api.put("/geo/travel-mode")
async def geo_travel_mode(body: TravelModeIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"travel_mode": body.enabled}})
    return {"travel_mode": body.enabled, "geo": clean(geo_of(user))}


class LocateIn(BaseModel):
    lat: float
    lng: float


@api.post("/geo/locate")
async def geo_locate(body: LocateIn, authorization: Optional[str] = Header(None)):
    """GPS → nearest supported city. Updates the user's geo context; with Travel
    Mode ON it also switches the UI/voice language to the local tongue."""
    user = await get_current_user(authorization)
    if not (-90 <= body.lat <= 90 and -180 <= body.lng <= 180):
        raise HTTPException(400, "invalid coordinates")
    near = nearest_city(body.lat, body.lng)
    prev = geo_of(user)
    geo = {"city": near["city"], "country": near["country"], "lang": near["lang"],
           "tz": near["tz"], "lat": near["lat"], "lng": near["lng"],
           "source": "gps", "located_at": datetime.now(timezone.utc).isoformat()}
    update: dict = {"geo": geo}
    language_switched = False
    if user.get("travel_mode") and near["lang"] != (user.get("language") or "sk"):
        update["language"] = near["lang"]
        language_switched = True
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": update})
    return {"geo": clean(geo), "previous_city": prev.get("city"),
            "city_changed": prev.get("city") != near["city"],
            "language": update.get("language", user.get("language") or "sk"),
            "language_switched": language_switched,
            "distance_km": near["distance_km"]}
