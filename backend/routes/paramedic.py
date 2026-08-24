# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""The Paramedic Key — IoT smart-lock integration (Nuki/Somfy API placeholders).
In a verified Angel Mode emergency the system issues a temporary digital entry
code for emergency proxies / first responders."""
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid, random

from core import api, db, clean, get_current_user, send_push

LOCK_VENDORS = ["nuki", "somfy", "tedee", "yale"]

class LockIn(BaseModel):
    vendor: str = "nuki"
    name: str = "Vchodové dvere"

@api.get("/paramedic/locks")
async def paramedic_locks(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    locks = await db.smart_locks.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(10)
    return {"locks": locks, "vendors": LOCK_VENDORS,
            "note": "API integrácia Nuki/Somfy je placeholder — kódy sa generujú, reálne odomknutie sa aktivuje po prepojení účtu výrobcu (Phase 3)."}

@api.post("/paramedic/locks")
async def paramedic_lock_add(body: LockIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if body.vendor not in LOCK_VENDORS:
        raise HTTPException(400, f"vendor must be one of {LOCK_VENDORS}")
    lock = {"lock_id": uuid.uuid4().hex, "user_id": user["user_id"], "vendor": body.vendor,
            "name": body.name.strip()[:60], "api_status": "placeholder",
            "created_at": datetime.now(timezone.utc)}
    await db.smart_locks.insert_one(lock.copy())
    return clean(lock)

@api.delete("/paramedic/locks/{lock_id}")
async def paramedic_lock_delete(lock_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.smart_locks.delete_one({"lock_id": lock_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Lock not found")
    return {"ok": True}


class AccessIn(BaseModel):
    reason: str = "emergency"
    confirm: bool = False   # manual founder override when no live emergency exists

async def _verified_emergency(uid: str) -> Optional[str]:
    since = datetime.now(timezone.utc) - timedelta(minutes=30)
    beacon = await db.beacon_events.find_one({"user_id": uid, "at": {"$gte": since}})
    if beacon:
        return "beacon"
    bio = await db.bio_beacons.find_one({"user_id": uid, "active": True})
    if bio:
        return "bio_beacon"
    fall = await db.fall_events.find_one({"user_id": uid, "triggered_at": {"$gte": since}})
    if fall:
        return "fall"
    pulse = await db.pulse_requests.find_one({"target_user": uid, "status": "need_help",
                                              "responded_at": {"$gte": since}})
    if pulse:
        return "pulse_need_help"
    return None

@api.post("/paramedic/access")
async def paramedic_access(body: AccessIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    emergency = await _verified_emergency(uid)
    if not emergency and not body.confirm:
        raise HTTPException(409, "no_verified_emergency: Za posledných 30 min nebola overená núdzová udalosť (maják/pád/pulse). Pošlite confirm=true pre manuálne vydanie kódu.")
    locks = await db.smart_locks.find({"user_id": uid}, {"_id": 0}).to_list(10)
    if not locks:
        raise HTTPException(404, "Najprv zaregistrujte smart zámok.")
    code = f"{random.randint(0, 999999):06d}"
    expires = datetime.now(timezone.utc) + timedelta(minutes=60)
    rec = {"access_id": uuid.uuid4().hex, "user_id": uid, "code": code,
           "locks": [l["name"] for l in locks], "reason": body.reason[:100],
           "emergency_verified": emergency or "manual_override",
           "expires_at": expires, "created_at": datetime.now(timezone.utc)}
    await db.paramedic_keys.insert_one(rec.copy())
    # Notify emergency proxies / guardians with the entry code
    guardians = await db.guardians.find({"user_id": uid}, {"_id": 0, "guardian_user_id": 1}).to_list(10)
    recipients = [g["guardian_user_id"] for g in guardians if g.get("guardian_user_id")]
    try:
        if recipients:
            await send_push(recipients=recipients,
                            data={"title": "🔑 PARAMEDIC KEY — DOČASNÝ VSTUP",
                                  "message": f"Núdzový vstupný kód: {code} (platí 60 min). Dôvod: {body.reason}.",
                                  "action_url": "/paramedic"})
    except Exception:
        pass
    try:
        from routes.swarm import bus_publish
        await bus_publish("paramedic.access_issued", "angel_agent",
                          {"user": uid[:8], "emergency": rec["emergency_verified"], "locks": len(locks)})
    except Exception:
        pass
    return clean(rec)

@api.get("/paramedic/access/active")
async def paramedic_active(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    now = datetime.now(timezone.utc)
    codes = await db.paramedic_keys.find({"user_id": user["user_id"], "expires_at": {"$gte": now}},
                                         {"_id": 0}).sort("created_at", -1).to_list(5)
    return {"active": codes}


# ---------------- STATE REGISTRY VERIFICATION (NCZI / ÚZIS — simulated) ----------------
REGISTRIES = {"SK": "NCZI — Národné centrum zdravotníckych informácií",
              "CZ": "ÚZIS — Ústav zdravotnických informací a statistiky"}

class RegistryVerifyIn(BaseModel):
    license_number: str          # e.g. A12345678
    country: str = "SK"          # SK | CZ
    responder_name: str = ""

@api.post("/paramedic/verify-registry")
async def paramedic_verify_registry(body: RegistryVerifyIn, authorization: Optional[str] = Header(None)):
    """Verify a first responder's license against the state health registry.
    SIMULATED: deterministic checksum mock of the NCZI/ÚZIS lookup (real API = Phase 3)."""
    user = await get_current_user(authorization)
    country = body.country.upper()
    if country not in REGISTRIES:
        raise HTTPException(400, "country must be SK|CZ")
    lic = body.license_number.strip().upper().replace(" ", "")
    if not (4 <= len(lic) <= 12) or not any(ch.isdigit() for ch in lic):
        raise HTTPException(400, "Číslo licencie musí mať 4–12 znakov a obsahovať číslice.")
    # Deterministic mock: registry hit when digit-sum is even (stable per licence)
    digit_sum = sum(int(c) for c in lic if c.isdigit())
    valid = digit_sum % 2 == 0
    rec = {"verify_id": uuid.uuid4().hex, "user_id": user["user_id"],
           "license_number": lic, "responder_name": body.responder_name.strip()[:80],
           "country": country, "registry": REGISTRIES[country],
           "valid": valid, "simulated": True,
           "detail": ("Licencia nájdená v registri — zdravotnícky pracovník OVERENÝ." if valid
                      else "Licencia sa v registri nenašla — vstupný kód NEVYDÁVAJTE."),
           "at": datetime.now(timezone.utc)}
    await db.registry_verifications.insert_one(rec.copy())
    try:
        from routes.swarm import bus_publish
        await bus_publish("paramedic.registry_check", "security_sentinel",
                          {"country": country, "valid": valid})
    except Exception:
        pass
    return clean(rec)

@api.get("/paramedic/registry-info")
async def paramedic_registry_info(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.registry_verifications.find({"user_id": user["user_id"]}, {"_id": 0}).sort("at", -1).to_list(10)
    return {"registries": REGISTRIES, "history": rows,
            "note": "SIMULÁCIA — reálne NCZI/ÚZIS API vyžaduje štátnu autorizáciu (Phase 3)."}
