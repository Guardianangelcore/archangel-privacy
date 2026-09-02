# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""GEOGRAPHIC FLUIDITY — dynamic proximity & language context.

Globally sovereign — no static city. Every user's context is resolved
dynamically from GPS → IP fallback → manual pick. The UI + Jarvis voice
follow the resolved locale (with Travel Mode auto-language switch).
"""
from fastapi import HTTPException, Header, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import math, httpx, time

from core import api, db, get_current_user, clean

# Supported city index — city display name, country, local language, coords, timezone
CITIES = [
    {"city": "New York", "country": "US", "lang": "en", "lat": 40.7128, "lng": -74.0060, "tz": "America/New_York"},
    {"city": "Prague", "country": "CZ", "lang": "cs", "lat": 50.0755, "lng": 14.4378, "tz": "Europe/Prague"},
    {"city": "Brno", "country": "CZ", "lang": "cs", "lat": 49.1951, "lng": 16.6068, "tz": "Europe/Prague"},
    {"city": "Ostrava", "country": "CZ", "lang": "cs", "lat": 49.8209, "lng": 18.2625, "tz": "Europe/Prague"},
    {"city": "Bratislava", "country": "SK", "lang": "sk", "lat": 48.1486, "lng": 17.1077, "tz": "Europe/Bratislava"},
    {"city": "Košice", "country": "SK", "lang": "sk", "lat": 48.7164, "lng": 21.2611, "tz": "Europe/Bratislava"},
    {"city": "Vienna", "country": "AT", "lang": "de", "lat": 48.2082, "lng": 16.3738, "tz": "Europe/Vienna"},
    {"city": "Berlin", "country": "DE", "lang": "de", "lat": 52.52, "lng": 13.405, "tz": "Europe/Berlin"},
    {"city": "Munich", "country": "DE", "lang": "de", "lat": 48.1351, "lng": 11.582, "tz": "Europe/Berlin"},
    {"city": "Paris", "country": "FR", "lang": "fr", "lat": 48.8566, "lng": 2.3522, "tz": "Europe/Paris"},
    {"city": "London", "country": "GB", "lang": "en", "lat": 51.5074, "lng": -0.1278, "tz": "Europe/London"},
    {"city": "Warsaw", "country": "PL", "lang": "pl", "lat": 52.2297, "lng": 21.0122, "tz": "Europe/Warsaw"},
    {"city": "Krakow", "country": "PL", "lang": "pl", "lat": 50.0647, "lng": 19.945, "tz": "Europe/Warsaw"},
    {"city": "Budapest", "country": "HU", "lang": "hu", "lat": 47.4979, "lng": 19.0402, "tz": "Europe/Budapest"},
    {"city": "Rome", "country": "IT", "lang": "it", "lat": 41.9028, "lng": 12.4964, "tz": "Europe/Rome"},
    {"city": "Madrid", "country": "ES", "lang": "es", "lat": 40.4168, "lng": -3.7038, "tz": "Europe/Madrid"},
    {"city": "Kyiv", "country": "UA", "lang": "uk", "lat": 50.4501, "lng": 30.5234, "tz": "Europe/Kyiv"},
]

# Used ONLY when there is no signal at all (no GPS, no IP, no manual pick). Consumers
# must treat source == "default" as "location unknown" — never show its weather/city
# as if it were the user's real place.
DEFAULT_GEO = {"city": "New York", "country": "US", "lang": "en", "tz": "America/New_York",
               "lat": 40.7128, "lng": -74.0060, "source": "default"}

UNRESOLVED_SOURCES = ("default", "ip-fallback")


def geo_of(user: dict) -> dict:
    """Current geo context of a user — falls back to DEFAULT_GEO only when unset."""
    g = user.get("geo") or {}
    return {**DEFAULT_GEO, **g} if g else dict(DEFAULT_GEO)


def geo_resolved(user: dict) -> bool:
    return geo_of(user).get("source") not in UNRESOLVED_SOURCES


async def _reverse_geocode(lat: float, lng: float) -> Optional[dict]:
    """Keyless reverse geocoding (BigDataCloud client API) → real city name for the
    user's actual GPS position instead of the nearest indexed metro."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as cli:
            r = await cli.get("https://api.bigdatacloud.net/data/reverse-geocode-client",
                              params={"latitude": lat, "longitude": lng, "localityLanguage": "en"})
        d = r.json()
        city = (d.get("city") or d.get("locality") or "").strip()
        cc = (d.get("countryCode") or "").strip().upper()
        return {"city": city, "country": cc} if city and cc else None
    except Exception:
        return None


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


# ---------- CONTEXT & MANUAL ----------

@api.get("/geo/context")
async def geo_context(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    user = await ensure_geo(user, request)
    g = geo_of(user)
    return {"geo": clean(g), "resolved": g.get("source") not in UNRESOLVED_SOURCES,
            "travel_mode": bool(user.get("travel_mode")),
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


async def _apply_geo(user: dict, near: dict, source: str, raw: Optional[tuple] = None) -> dict:
    """Persist geo update, optionally auto-switch language when Travel Mode ON, and
    always surface a language suggestion when the country changed regardless.
    `raw` = the user's actual (lat, lng): stored for precise weather and reverse-geocoded
    to the real city name (nearest indexed metro is only the fallback label)."""
    prev = geo_of(user)
    geo = {"city": near["city"], "country": near["country"], "lang": near["lang"],
           "tz": near["tz"], "lat": near["lat"], "lng": near["lng"],
           "source": source, "located_at": datetime.now(timezone.utc).isoformat()}
    if raw:
        geo["lat"], geo["lng"] = raw
        geo["nearest_city"] = near["city"]
        rev = await _reverse_geocode(*raw)
        if rev:
            geo["city"], geo["country"] = rev["city"], rev["country"]
    update: dict = {"geo": geo}
    current_lang = (user.get("language") or "sk")
    language_switched = False
    lang_suggestion = None
    country_changed = prev.get("country") != near["country"]
    if user.get("travel_mode") and near["lang"] != current_lang:
        update["language"] = near["lang"]
        language_switched = True
    elif country_changed and near["lang"] != current_lang:
        lang_suggestion = {"from": current_lang, "to": near["lang"], "city": near["city"], "country": near["country"]}
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": update})
    return {"geo": clean(geo), "previous_city": prev.get("city"),
            "city_changed": prev.get("city") != near["city"],
            "country_changed": country_changed,
            "language": update.get("language", current_lang),
            "language_switched": language_switched,
            "language_suggestion": lang_suggestion,
            "distance_km": near.get("distance_km", 0)}


@api.post("/geo/locate")
async def geo_locate(body: LocateIn, authorization: Optional[str] = Header(None)):
    """GPS → nearest supported city. Updates the user's geo; with Travel Mode ON
    auto-switches language, else surfaces a `language_suggestion` when crossing borders."""
    user = await get_current_user(authorization)
    if not (-90 <= body.lat <= 90 and -180 <= body.lng <= 180):
        raise HTTPException(400, "invalid coordinates")
    return await _apply_geo(user, nearest_city(body.lat, body.lng), "gps", raw=(body.lat, body.lng))


# ---------- IP FALLBACK ----------

_IP_CACHE: dict = {}   # ip -> (ts, {city, country, lat, lng})
_IP_TTL = 24 * 3600    # 24 h — IPs rarely move fast enough to matter


def _client_ip(req: Request) -> Optional[str]:
    xff = req.headers.get("x-forwarded-for")
    if xff:
        ip = xff.split(",")[0].strip()
        if ip:
            return ip
    xreal = req.headers.get("x-real-ip")
    if xreal:
        return xreal.strip()
    try:
        return req.client.host if req.client else None
    except Exception:
        return None


async def _ip_to_coords(ip: str) -> Optional[dict]:
    """Free keyless IP geolocation (ip-api.com — 45 req/min, no signup)."""
    now = time.time()
    cached = _IP_CACHE.get(ip)
    if cached and (now - cached[0]) < _IP_TTL:
        return cached[1]
    try:
        async with httpx.AsyncClient(timeout=3.0) as cli:
            r = await cli.get(f"http://ip-api.com/json/{ip}",
                              params={"fields": "status,country,countryCode,city,lat,lon"})
        d = r.json()
        if d.get("status") != "success":
            return None
        row = {"city": d.get("city") or "", "country": d.get("countryCode") or "",
               "lat": float(d["lat"]), "lng": float(d["lon"])}
        _IP_CACHE[ip] = (now, row)
        return row
    except Exception:
        return None


async def _locate_by_ip(user: dict, request: Request) -> dict:
    ip = _client_ip(request)
    resolved = None
    if ip and not _is_private_ip(ip):
        resolved = await _ip_to_coords(ip)
    if not resolved:
        # Graceful default — still persist as "ip-fallback" so UI knows to prompt manual pick.
        return await _apply_geo(user, {**DEFAULT_GEO, "distance_km": 0.0}, "ip-fallback")
    near = nearest_city(resolved["lat"], resolved["lng"])
    res = await _apply_geo(user, near, "ip", raw=(resolved["lat"], resolved["lng"]))
    return {**res, "raw_ip_city": resolved["city"], "raw_ip_country": resolved["country"]}


async def ensure_geo(user: dict, request: Request) -> dict:
    """Server-side safety net: if the user has never been located, resolve by IP now.
    Returns the (possibly updated) user dict. Never raises."""
    if geo_resolved(user):
        return user
    try:
        res = await _locate_by_ip(user, request)
        return {**user, "geo": res["geo"]}
    except Exception:
        return user


@api.post("/geo/ip-locate")
async def geo_ip_locate(request: Request, authorization: Optional[str] = Header(None)):
    """IP-based fallback when GPS is unavailable/denied. Uses X-Forwarded-For (behind
    ingress). Falls back to the unresolved default if IP is private or lookup fails."""
    user = await get_current_user(authorization)
    return await _locate_by_ip(user, request)


def _is_private_ip(ip: str) -> bool:
    if not ip or ip in ("localhost", "127.0.0.1", "::1"):
        return True
    try:
        parts = ip.split(".")
        if len(parts) != 4:
            return False
        a, b = int(parts[0]), int(parts[1])
        return a == 10 or (a == 172 and 16 <= b <= 31) or (a == 192 and b == 168) or a == 127
    except Exception:
        return False


# ---------- MANUAL CITY PICK ----------

class ManualCityIn(BaseModel):
    city: str


@api.post("/geo/set-city")
async def geo_set_city(body: ManualCityIn, authorization: Optional[str] = Header(None)):
    """Manual override — the user picks a city from the supported index."""
    user = await get_current_user(authorization)
    target = next((c for c in CITIES if c["city"].lower() == body.city.strip().lower()), None)
    if not target:
        raise HTTPException(400, f"unsupported_city: pick one of {[c['city'] for c in CITIES]}")
    return await _apply_geo(user, {**target, "distance_km": 0.0}, "manual")
