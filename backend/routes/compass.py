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
    "Zachovajte pokoj. Skontrolujte dýchanie a krvácanie — najprv seba, potom ostatných.",
    "Bez signálu: SMS má vyššiu šancu než hovor. Skúste 112 — funguje v každej sieti EÚ.",
    "Voda: 3 l / osoba / deň. Pri neistote prevarte alebo použite dezinfekčné tablety.",
    "Teplo: 3 vrstvy oblečenia sú lepšie než 1 hrubá. Chráňte hlavu a krk.",
    "Lieky z lekárničky berte podľa plánu — pozrite sekciu LIEKY DNES nižšie.",
    "Ak ste na PN (neschopenka), dodržte vychádzky — okná máte uložené offline nižšie.",
    "Ukážte záchranárom NÚDZOVÝ QR alebo tento kompas — obsahuje krvnú skupinu a alergie.",
    "Bio-Beacon aktivujte LEN v reálnej núdzi — vysiela vašu polohu strážcom.",
]

EMERGENCY_NUMBERS = {"EU / SK / CZ": "112", "Záchranka SK": "155", "UK": "999", "USA / Kanada": "911"}

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
        {"user_id": uid, "category": "vaccine", "booster_due": {"$ne": None, "$lte": horizon}},
        {"_id": 0, "title": 1, "booster_due": 1, "date": 1}).sort("booster_due", 1).to_list(10)
    vaccines = await db.calendar_events.find(
        {"user_id": uid, "category": "vaccine"}, {"_id": 0, "title": 1, "date": 1, "booster_due": 1}
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
    "shortage": "Nedostatok liekov / zásob",
    "clinic": "Dostupnosť kliniky / lekára",
    "danger": "Nebezpečenstvo v okolí",
    "help": "Dostupná pomoc / zdroje",
    "other": "Iné overiteľné tvrdenie",
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
        raise HTTPException(400, "Tvrdenie musí mať aspoň 10 znakov.")
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
        raise HTTPException(400, "Vlastné tvrdenie nemôžete overovať.")
    dup = await db.truth_votes.find_one({"claim_id": claim_id, "voter_id": user["user_id"]})
    if dup:
        raise HTTPException(409, "Už ste hlasovali.")
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
                            data={"title": "🚨 BIO-BEACON AKTIVOVANÝ",
                                  "message": f"{user.get('name') or 'Váš blízky'} aktivoval núdzový Bio-Beacon — sledujte polohu a vitálne funkcie.",
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
        raise HTTPException(404, "Žiadny aktívny Bio-Beacon.")
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
