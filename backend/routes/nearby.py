# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""NEARBY CARE — GPS locator for pharmacies · doctors/GPs · emergency (hospitals).

Keyless OpenStreetMap Overpass API. Guardian+ tier gate (Sovereign → 402).
"""
from fastapi import HTTPException, Header, Request
from typing import Optional
import httpx, time, math

from core import api, get_current_user, clean
from routes.subscription import require_tier
from routes.geo import geo_of, ensure_geo, _haversine_km

OVERPASS_URLS = [
    "https://overpass.osm.ch/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_UA = {"User-Agent": "ArchangelOS/1.0 (health locator; contact: guardian.angel.core@proton.me)"}

# kind -> Overpass tag filters
_KIND_FILTERS = {
    "pharmacy": ['["amenity"="pharmacy"]'],
    "doctor":   ['["amenity"="doctors"]', '["healthcare"="doctor"]', '["amenity"="clinic"]'],
    "emergency": ['["amenity"="hospital"]', '["healthcare"="hospital"]', '["emergency"="yes"]'],
    "shelter":   ['["amenity"="shelter"]', '["emergency"="bunker"]', '["military"="bunker"]', '["building"="bunker"]', '["emergency"="assembly_point"]'],
}
# kind -> Nominatim special-phrase queries (fallback when every Overpass mirror is down)
_KIND_NOMINATIM = {
    "pharmacy": ["pharmacy"],
    "doctor": ["doctors", "clinic"],
    "emergency": ["hospital"],
    "shelter": ["shelter", "bunker"],
}

_CACHE: dict = {}          # (kind, latq, lngq) -> (ts, results)
_TTL = 30 * 60            # 30 min


def _round(v: float) -> float:
    return round(v, 3)     # ~110 m grid → cache-friendly


async def _overpass(query: str) -> Optional[dict]:
    for url in OVERPASS_URLS:
        try:
            async with httpx.AsyncClient(timeout=8.0) as cli:
                r = await cli.post(url, data={"data": query}, headers=_UA)
            if r.status_code == 200:
                return r.json()
        except Exception:
            continue
    return None


async def _nominatim(kind: str, lat: float, lng: float, radius: int) -> Optional[list]:
    """Fallback: bounded Nominatim search → same element shape as Overpass."""
    dlat = radius / 111_000.0
    dlng = radius / (111_000.0 * max(0.2, abs(math.cos(math.radians(lat)))))
    viewbox = f"{lng - dlng},{lat + dlat},{lng + dlng},{lat - dlat}"
    elements = []
    for q in _KIND_NOMINATIM[kind]:
        try:
            async with httpx.AsyncClient(timeout=12.0) as cli:
                r = await cli.get(NOMINATIM_URL, headers=_UA, params={
                    "q": q, "format": "jsonv2", "limit": 40, "extratags": 1,
                    "addressdetails": 1, "bounded": 1, "viewbox": viewbox,
                })
            if r.status_code != 200:
                continue
            for row in r.json():
                ex = row.get("extratags") or {}
                ad = row.get("address") or {}
                elements.append({
                    "type": row.get("osm_type", "n")[:1], "id": row.get("osm_id"),
                    "lat": float(row["lat"]), "lon": float(row["lon"]),
                    "tags": {
                        "name": row.get("name") or (row.get("display_name") or "").split(",")[0],
                        "opening_hours": ex.get("opening_hours", ""),
                        "phone": ex.get("phone") or ex.get("contact:phone", ""),
                        "addr:street": ad.get("road", ""), "addr:housenumber": ad.get("house_number", ""),
                        "addr:city": ad.get("city") or ad.get("town") or ad.get("village", ""),
                        "amenity": "hospital" if kind == "emergency" else "",
                        "emergency": ex.get("emergency", ""),
                    },
                })
        except Exception:
            continue
    return elements or None


def _name_of(tags: dict, kind: str) -> str:
    return (tags.get("name") or tags.get("operator") or tags.get("brand")
            or {"pharmacy": "Pharmacy", "doctor": "Doctor / Clinic", "emergency": "Hospital / ER", "shelter": "Shelter / Bunker"}.get(kind, "Place"))


@api.get("/nearby/care")
async def nearby_care(request: Request, kind: str = "pharmacy",
                      lat: Optional[float] = None, lng: Optional[float] = None,
                      radius: int = 5000, authorization: Optional[str] = Header(None)):
    """Nearby pharmacies / doctors / emergency via OpenStreetMap. Guardian+ only."""
    user = await get_current_user(authorization)
    if kind == "shelter":
        from routes.features import has_feature
        if not await has_feature(user, "bunker"):
            raise HTTPException(402, "sentinel_required: Bunker Locator requires the Sentinel Plan — or buy the Bunker Module once (€1.99).")
    else:
        await require_tier(user, "guardian", "Nearby Care Locator")
    if kind not in _KIND_FILTERS:
        raise HTTPException(400, "kind must be pharmacy | doctor | emergency | shelter")
    radius = min(radius, 20000)

    # Resolve position: explicit GPS coords win; else the user's stored geo (GPS/IP).
    if lat is None or lng is None:
        user = await ensure_geo(user, request)
        g = geo_of(user)
        lat, lng = g.get("lat"), g.get("lng")
    if lat is None or lng is None or not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise HTTPException(400, "no location — enable GPS or set your city")

    radius = max(500, min(radius, 20000))
    ckey = (kind, _round(lat), _round(lng), radius)
    hit = _CACHE.get(ckey)
    now = time.time()
    if hit and now - hit[0] < _TTL:
        return {"center": {"lat": lat, "lng": lng}, "kind": kind, "results": hit[1], "cached": True}

    clauses = "".join(
        f'node{f}(around:{radius},{lat},{lng});way{f}(around:{radius},{lat},{lng});'
        for f in _KIND_FILTERS[kind]
    )
    query = f"[out:json][timeout:15];({clauses});out center 40;"
    data = await _overpass(query)
    elements = data.get("elements", []) if data is not None else None
    source = "overpass"
    if not elements:
        elements = await _nominatim(kind, lat, lng, radius)
        source = "nominatim"
    if elements is None:
        raise HTTPException(503, "map service unavailable — try again shortly")

    results = []
    for el in elements:
        tags = el.get("tags") or {}
        plat = el.get("lat") or (el.get("center") or {}).get("lat")
        plng = el.get("lon") or (el.get("center") or {}).get("lon")
        if plat is None or plng is None:
            continue
        addr = ", ".join(x for x in [
            (tags.get("addr:street", "") + " " + tags.get("addr:housenumber", "")).strip(),
            tags.get("addr:city", ""),
        ] if x).strip(", ")
        results.append({
            "id": f"{el.get('type','n')}/{el.get('id')}",
            "name": _name_of(tags, kind),
            "lat": plat, "lng": plng,
            "distance_km": round(_haversine_km(lat, lng, plat, plng), 2),
            "opening_hours": tags.get("opening_hours") or "",
            "phone": tags.get("phone") or tags.get("contact:phone") or "",
            "address": addr,
            "emergency": tags.get("emergency") == "yes" or tags.get("amenity") == "hospital",
        })
    results.sort(key=lambda x: x["distance_km"])
    results = results[:30]
    _CACHE[ckey] = (now, results)
    return {"center": {"lat": lat, "lng": lng}, "kind": kind, "results": clean(results), "cached": False, "source": source}
