# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Offline Survival Compass + Truth-Validator (peer consensus) + Bio-Beacon.

Compass pack = one signed offline bundle: ICE identity, meds, sick-leave (ePN /
neschopenka incl. outing windows), vaccination boosters, guardians and survival
instructions — cached on-device for zero-connectivity survival."""
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid, hashlib

from core import api, db, clean, get_current_user, send_push

SURVIVAL_GUIDE = [
    "Stay calm. Check breathing and bleeding — yourself first, then others.",
    "No signal: SMS has a better chance than a call. Try 112 — it works on every EU network.",
    "Water: 3 l / person / day. When unsure, boil it or use purification tablets.",
    "Warmth: 3 clothing layers beat 1 thick one. Protect your head and neck.",
    "Take medication as scheduled — see the MEDS TODAY section below.",
    "If on sick leave (ePN), keep to your outing windows — stored offline below.",
    "Show responders the EMERGENCY QR or this compass — it holds your blood type and allergies.",
    "Activate the Bio-Beacon ONLY in a real emergency — it broadcasts your location to guardians.",
]

EMERGENCY_NUMBERS = {"EU / SK / CZ": "112", "Ambulance SK": "155", "UK": "999", "USA / Kanada": "911"}


# ---------------- SOVEREIGN COMPASS BEARING — GPS wiring ----------------
class BearingIn(BaseModel):
    lat: float
    lng: float


def _haversine_bearing(lat1, lng1, lat2, lng2):
    """Return (distance_km, bearing_deg) between two coordinates."""
    import math
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    dist = 2 * r * math.asin(math.sqrt(a))
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    brng = (math.degrees(math.atan2(y, x)) + 360) % 360
    return round(dist, 1), round(brng, 1)


def _compass_direction(bearing: float) -> str:
    dirs = ["S", "SV", "V", "JV", "J", "JZ", "Z", "SZ"]
    idx = int(((bearing + 22.5) % 360) // 45)
    return dirs[idx]


@api.post("/compass/bearing")
async def compass_bearing(body: BearingIn, authorization: Optional[str] = Header(None)):
    """Sovereign Compass — from live GPS coords compute distance + bearing to
    each supported safe-city + to the user's active guardians' Bio-Beacons.
    Powers the on-device compass needle (Waitlist Hunter proximity + Bio-Beacon direction)."""
    from routes.geo import CITIES
    user = await get_current_user(authorization)
    if not (-90 <= body.lat <= 90 and -180 <= body.lng <= 180):
        raise HTTPException(400, "invalid coordinates")

    targets = []
    for c in CITIES:
        dist, brng = _haversine_bearing(body.lat, body.lng, c["lat"], c["lng"])
        targets.append({
            "kind": "safe_city", "label": c["city"], "country": c["country"],
            "distance_km": dist, "bearing_deg": brng, "direction": _compass_direction(brng),
        })
    targets.sort(key=lambda t: t["distance_km"])

    # Active Bio-Beacons of guardians the user is linked with — priority targets
    guardians = await db.guardians.find({"user_id": user["user_id"]}, {"_id": 0, "guardian_user_id": 1, "guardian_name": 1}).to_list(10)
    beacon_targets = []
    for g in guardians:
        beacon = await db.bio_beacons.find_one({"user_id": g["guardian_user_id"], "active": True},
                                                {"_id": 0, "location": 1, "did": 1})
        loc = (beacon or {}).get("location") or {}
        if loc.get("lat") is not None and loc.get("lng") is not None:
            dist, brng = _haversine_bearing(body.lat, body.lng, loc["lat"], loc["lng"])
            beacon_targets.append({
                "kind": "beacon", "label": g.get("guardian_name") or "Guardian",
                "did": beacon.get("did"),
                "distance_km": dist, "bearing_deg": brng, "direction": _compass_direction(brng),
            })
    beacon_targets.sort(key=lambda t: t["distance_km"])

    # Waitlist proximity — items with clinic in a known city
    waitlist_items = await db.waitlist.find(
        {"user_id": user["user_id"], "status": {"$ne": "expired"}}, {"_id": 0}
    ).to_list(30)
    waitlist_targets = []
    for w in waitlist_items:
        city = (w.get("city") or "").strip().lower()
        c = next((x for x in CITIES if x["city"].lower() == city), None)
        if not c:
            continue
        dist, brng = _haversine_bearing(body.lat, body.lng, c["lat"], c["lng"])
        waitlist_targets.append({
            "kind": "waitlist", "label": f"{w.get('specialty') or 'Examination'} · {c['city']}",
            "item_id": w["item_id"], "clinic": w.get("clinic"),
            "status": w.get("status") or "hunting",
            "distance_km": dist, "bearing_deg": brng, "direction": _compass_direction(brng),
        })
    waitlist_targets.sort(key=lambda t: t["distance_km"])

    return {
        "gps": {"lat": body.lat, "lng": body.lng},
        "nearest_safe_city": targets[0] if targets else None,
        "safe_cities": targets[:5],
        "beacons": beacon_targets[:5],
        "waitlist_proximity": waitlist_targets[:8],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@api.get("/compass/pack")
async def compass_pack(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    prof = await db.emergency_profiles.find_one({"user_id": uid}, {"_id": 0}) or {}
    reminders = await db.med_reminders.find({"user_id": uid}, {"_id": 0}).to_list(50)
    meds = sorted([{"name": r["name"], "dose": r["dose"], "time": tm}
                   for r in reminders for tm in r.get("times", [])], key=lambda x: x["time"])
    # Sick Leave (ePN / neschopenka) — status + outing windows, offline-critical
    recovery = await db.recovery.find_one({"user_id": uid}, {"_id": 0}) or {}
    # Vaccination boosters due within 90 days (Health Calendar)
    horizon = (now + timedelta(days=90)).strftime("%Y-%m-%d")
    boosters = await db.calendar_events.find(
        {"user_id": uid, "child_id": None, "category": "vaccine", "booster_due": {"$ne": None, "$lte": horizon}},
        {"_id": 0, "title": 1, "booster_due": 1, "date": 1}).sort("booster_due", 1).to_list(10)
    vaccines = await db.calendar_events.find(
        {"user_id": uid, "child_id": None, "category": "vaccine"}, {"_id": 0, "title": 1, "date": 1, "booster_due": 1}
    ).sort("date", -1).to_list(10)
    guardians = await db.guardians.find({"user_id": uid}, {"_id": 0, "guardian_name": 1, "guardian_email": 1}).to_list(10)
    beacon = await db.bio_beacons.find_one({"user_id": uid, "active": True}, {"_id": 0})
    pack = {
        "generated_at": now.isoformat(), "date": day,
        "identity": {"name": user.get("name"), "did": user["did"],
                     "blood_type": prof.get("blood_type"), "allergies": prof.get("allergies"),
                     "conditions": prof.get("conditions"), "medications": prof.get("medications")},
        "emergency_contact": {"name": prof.get("emergency_contact_name"),
                              "phone": prof.get("emergency_contact_phone")},
        "meds_today": meds,
        "sick_leave": {"active": recovery.get("status") == "active",
                       "start_date": recovery.get("start_date"), "end_date": recovery.get("end_date"),
                       "contract_type": recovery.get("contract_type"),
                       "outings": recovery.get("outings", [])},
        "vaccinations": {"booster_alerts": boosters, "history": vaccines},
        "guardians": guardians,
        "bio_beacon_active": bool(beacon),
        "survival_guide": SURVIVAL_GUIDE,
        "emergency_numbers": EMERGENCY_NUMBERS,
    }
    pack["integrity_sha256"] = hashlib.sha256(str(sorted(pack.items())).encode()).hexdigest()
    return pack


# ---------------- TRUTH-VALIDATOR (peer consensus, ZK-hash anchored) ----------------
CLAIM_CATEGORIES = {
    "shortage": "Medication / supply shortage",
    "clinic": "Clinic / doctor availability",
    "danger": "Danger nearby",
    "help": "Available help / resources",
    "other": "Other verifiable claim",
}

class ClaimIn(BaseModel):
    text: str
    category: str = "other"
    city: Optional[str] = ""

def _consensus(v: int, d: int) -> str:
    if v >= 2 and v > d:
        return "verified"
    if d >= 2 and d >= v:
        return "disputed"
    return "pending"

@api.get("/truth/claims")
async def truth_claims(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.truth_claims.find({}, {"_id": 0}).sort("created_at", -1).to_list(30)
    my_votes = await db.truth_votes.find({"voter_id": user["user_id"]}, {"_id": 0, "claim_id": 1, "vote": 1}).to_list(100)
    voted = {v["claim_id"]: v["vote"] for v in my_votes}
    for r in rows:
        r["my_vote"] = voted.get(r["claim_id"])
    return {"claims": rows, "categories": CLAIM_CATEGORIES}

@api.post("/truth/claims")
async def truth_submit(body: ClaimIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if body.category not in CLAIM_CATEGORIES:
        raise HTTPException(400, f"category must be one of {list(CLAIM_CATEGORIES)}")
    text = body.text.strip()
    if len(text) < 10:
        raise HTTPException(400, "Claim must be at least 10 characters.")
    claim = {"claim_id": uuid.uuid4().hex, "user_id": user["user_id"],
             "author_name": (user.get("name") or "Guardian").split(" ")[0],
             "text": text[:400], "category": body.category, "city": (body.city or "").strip()[:60],
             "claim_sha256": hashlib.sha256(text.encode()).hexdigest(),
             "verify_votes": 0, "dispute_votes": 0, "status": "pending",
             "created_at": datetime.now(timezone.utc)}
    await db.truth_claims.insert_one(claim.copy())
    try:
        from routes.swarm import bus_publish
        await bus_publish("truth.claim_submitted", "truth_validator",
                          {"claim": claim["claim_id"], "sha256": claim["claim_sha256"][:16]})
    except Exception:
        pass
    return clean(claim)

class VoteIn(BaseModel):
    vote: str  # verify | dispute

@api.post("/truth/claims/{claim_id}/vote")
async def truth_vote(claim_id: str, body: VoteIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if body.vote not in ("verify", "dispute"):
        raise HTTPException(400, "vote must be verify|dispute")
    claim = await db.truth_claims.find_one({"claim_id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(404, "Claim not found")
    if claim["user_id"] == user["user_id"]:
        raise HTTPException(400, "You cannot verify your own claim.")
    dup = await db.truth_votes.find_one({"claim_id": claim_id, "voter_id": user["user_id"]})
    if dup:
        raise HTTPException(409, "You have already voted.")
    await db.truth_votes.insert_one({"vote_id": uuid.uuid4().hex, "claim_id": claim_id,
                                     "voter_id": user["user_id"], "vote": body.vote,
                                     "at": datetime.now(timezone.utc)})
    inc = {"verify_votes": 1} if body.vote == "verify" else {"dispute_votes": 1}
    await db.truth_claims.update_one({"claim_id": claim_id}, {"$inc": inc})
    fresh = await db.truth_claims.find_one({"claim_id": claim_id}, {"_id": 0})
    status = _consensus(fresh["verify_votes"], fresh["dispute_votes"])
    if status != fresh["status"]:
        await db.truth_claims.update_one({"claim_id": claim_id}, {"$set": {"status": status}})
        fresh["status"] = status
        try:
            from routes.swarm import bus_publish
            await bus_publish("truth.consensus", "truth_validator",
                              {"claim": claim_id, "status": status,
                               "verify": fresh["verify_votes"], "dispute": fresh["dispute_votes"]})
        except Exception:
            pass
    return clean(fresh)


# ---------------- BIO-BEACON (emergency vitals broadcast) ----------------
class BeaconActivateIn(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    note: Optional[str] = ""

@api.post("/bio-beacon/activate")
async def bio_beacon_activate(body: BeaconActivateIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    vitals = await db.wellness_vitals.find_one({"user_id": uid}, {"_id": 0}, sort=[("date", -1)])
    beacon = {"beacon_id": uuid.uuid4().hex, "user_id": uid, "did": user["did"],
              "active": True, "note": (body.note or "")[:200],
              "location": {"lat": body.lat, "lng": body.lng},
              "vitals": {"heart_rate": (vitals or {}).get("heart_rate"),
                         "steps": (vitals or {}).get("steps"), "date": (vitals or {}).get("date")},
              "pings": 0, "started_at": now, "last_ping": now,
              "expires_at": now + timedelta(hours=24)}
    await db.bio_beacons.update_many({"user_id": uid, "active": True}, {"$set": {"active": False}})
    await db.bio_beacons.insert_one(beacon.copy())
    guardians = await db.guardians.find({"user_id": uid}, {"_id": 0, "guardian_user_id": 1}).to_list(10)
    try:
        if guardians:
            await send_push(recipients=[g["guardian_user_id"] for g in guardians],
                            data={"title": "🚨 BIO-BEACON ACTIVATED",
                                  "message": f"{user.get('name') or 'Your loved one'} activated an emergency Bio-Beacon — track their location and vitals.",
                                  "action_url": f"/compass"})
    except Exception:
        pass
    try:
        from routes.swarm import bus_publish
        await bus_publish("beacon.bio_activated", "angel_agent",
                          {"user": uid[:8], "guardians_notified": len(guardians)})
    except Exception:
        pass
    return clean(beacon)

class BeaconPingIn(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    heart_rate: Optional[int] = None

@api.post("/bio-beacon/ping")
async def bio_beacon_ping(body: BeaconPingIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    beacon = await db.bio_beacons.find_one({"user_id": user["user_id"], "active": True}, {"_id": 0})
    if not beacon:
        raise HTTPException(404, "No active Bio-Beacon.")
    upd = {"last_ping": datetime.now(timezone.utc)}
    if body.lat is not None:
        upd["location"] = {"lat": body.lat, "lng": body.lng}
    if body.heart_rate is not None:
        upd["vitals.heart_rate"] = body.heart_rate
    await db.bio_beacons.update_one({"beacon_id": beacon["beacon_id"]}, {"$set": upd, "$inc": {"pings": 1}})
    return {"ok": True}

@api.post("/bio-beacon/deactivate")
async def bio_beacon_deactivate(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.bio_beacons.update_many({"user_id": user["user_id"], "active": True},
                                           {"$set": {"active": False, "ended_at": datetime.now(timezone.utc)}})
    return {"ok": True, "deactivated": res.modified_count}

@api.get("/bio-beacon/status")
async def bio_beacon_status(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    beacon = await db.bio_beacons.find_one({"user_id": user["user_id"], "active": True}, {"_id": 0})
    return {"active": bool(beacon), "beacon": beacon}

@api.get("/bio-beacon/public/{did}")
async def bio_beacon_public(did: str):
    """Public read-only for first responders (like the emergency QR)."""
    beacon = await db.bio_beacons.find_one({"did": did, "active": True}, {"_id": 0})
    if not beacon:
        raise HTTPException(404, "No active beacon")
    return beacon
