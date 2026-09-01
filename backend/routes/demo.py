# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Investor Demo Mode — founder-only toggle that seeds a flawless presentation
dataset (successful waitlist hunt, €150 dental refund claim, answered family
safety pulse) for the Builders' Fest jury. Fully reversible (demo:true tags)."""
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid

from core import api, db, get_current_user

DEMO_COLLECTIONS = ["waitlist", "jarvis_actions", "pulse_requests"]

class DemoToggleIn(BaseModel):
    enabled: bool

async def _wipe_demo(uid: str) -> int:
    removed = 0
    for coll in DEMO_COLLECTIONS:
        res = await db[coll].delete_many({"user_id": uid, "demo": True})
        removed += res.deleted_count
    res2 = await db.pulse_requests.delete_many({"target_user": uid, "demo": True})
    return removed + res2.deleted_count

@api.get("/demo/status")
async def demo_status(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    from routes.subscription import _is_founder
    founder = await _is_founder(user)
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "demo_mode": 1}) or {}
    return {"is_founder": founder, "demo_mode": bool(fresh.get("demo_mode"))}

@api.post("/demo/toggle")
async def demo_toggle(body: DemoToggleIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    from routes.subscription import _is_founder
    if not await _is_founder(user):
        raise HTTPException(403, "founder_only: Demo Mode is available only in the founder admin view.")
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    await _wipe_demo(uid)  # idempotent — clean slate either way
    seeded = {}
    if body.enabled:
        # 1. Successful waitlist hunt (Kardiológia — slot found 14 days out)
        await db.waitlist.insert_one({
            "item_id": uuid.uuid4().hex, "user_id": uid,
            "specialty": "Cardiology", "clinic": "NÚSCH Bratislava", "city": "Bratislava",
            "current_date": (now + timedelta(days=210)).strftime("%Y-%m-%d"),
            "target_before": (now + timedelta(days=60)).strftime("%Y-%m-%d"),
            "priority": "high", "status": "slot_found",
            "found_slot": (now + timedelta(days=14)).strftime("%Y-%m-%d"),
            "last_check": now, "demo": True, "created_at": now})
        # 2. €150 insurance refund claim source (dental invoice processed by Jarvis)
        await db.jarvis_actions.insert_one({
            "action_id": uuid.uuid4().hex, "user_id": uid,
            "specialty": "Dentistry", "doc_title": "Invoice — Dental Premium Clinic (demo)",
            "booked_slot": (now + timedelta(days=7)).strftime("%Y-%m-%d 09:00"),
            "status": "done", "steps": [{"step": "OCR", "status": "ok", "detail": "demo"}],
            "demo": True, "created_at": now})
        # 3. Family safety pulse — Guardian answered 'V PORIADKU'
        await db.pulse_requests.insert_one({
            "req_id": uuid.uuid4().hex, "from_user": uid, "from_name": "Guardian",
            "target_user": uid, "target_did": user["did"], "status": "ok",
            "responded_at": now, "demo": True, "created_at": now})
        seeded = {"waitlist_hunt": "Cardiology · slot_found +14d",
                  "refund_claim": "Dentistry → 150 € (Claim My Benefits)",
                  "family_pulse": "Guardian · OK"}
    await db.users.update_one({"user_id": uid}, {"$set": {"demo_mode": body.enabled}})
    return {"demo_mode": body.enabled, "seeded": seeded}

# ---- COMPETITION DEMO SEED — pre-fills the Life Card for the demo user ----
# Idempotent (marker in db.demo_seed). English titles for the Builders' Fest jury.
DEMO_LIFECARD = [
    {"category": "vaccine", "title": "Flu vaccine", "date": "2023-10-15", "notes": "Seasonal influenza shot", "booster_due": None},
    {"category": "vaccine", "title": "Tetanus booster", "date": "2021-05-20", "notes": "Booster dose", "booster_due": "2036-05-20"},
    {"category": "vaccine", "title": "COVID-19 booster", "date": "2022-04-10", "notes": "mRNA booster dose", "booster_due": None},
    {"category": "surgery", "title": "Knee arthroscopy", "date": "2019-08-12", "notes": "Right knee, full recovery", "booster_due": None},
    {"category": "surgery", "title": "Appendectomy", "date": "2012-03-25", "notes": "Appendix removal, no complications", "booster_due": None},
    {"category": "exam", "title": "Lab: Blood glucose 5.2 mmol/L", "date": "2024-01-15", "notes": "Normal range (3.9–5.5 mmol/L) ✅", "booster_due": None},
    {"category": "exam", "title": "Lab: Total cholesterol 4.8 mmol/L", "date": "2024-01-15", "notes": "Normal range (< 5.0 mmol/L) ✅", "booster_due": None},
]
DEMO_PREDICTION = {
    "title": "Annual physical examination",
    "category": "exam",
    "suggested_date": "2026-09-15",
    "reason": "Based on your history, your annual physical examination is due in September 2026.",
}

@api.post("/demo/seed")
async def demo_seed_lifecard(authorization: Optional[str] = Header(None)):
    """Seed the competition demo Life Card for the current user (idempotent)."""
    user = await get_current_user(authorization)
    uid = user["user_id"]
    if await db.demo_seed.find_one({"user_id": uid, "kind": "lifecard"}):
        return {"ok": True, "seeded": False, "reason": "already seeded"}
    now = datetime.now(timezone.utc)
    # Identity — birth certificate: DOB 1985-03-15, blood type A+
    await db.users.update_one({"user_id": uid}, {"$set": {"birth_date": "1985-03-15", "birth_year": 1985, "language": "en"}})
    await db.emergency_profiles.update_one(
        {"user_id": uid},
        {"$set": {"user_id": uid, "blood_type": "A+",
                  "full_name": user.get("name") or "Guardian Angel"}},
        upsert=True)
    # Timeline records
    docs = []
    for d in DEMO_LIFECARD:
        docs.append({"event_id": uuid.uuid4().hex, "user_id": uid, "child_id": None,
                     "source": "manual", "demo": True, "created_at": now, **d})
    # Jarvis prediction shown in the timeline as an upcoming AI reminder
    docs.append({"event_id": uuid.uuid4().hex, "user_id": uid, "child_id": None,
                 "category": "exam", "title": DEMO_PREDICTION["title"],
                 "date": DEMO_PREDICTION["suggested_date"],
                 "notes": f"Jarvis prediction · {DEMO_PREDICTION['reason']}",
                 "booster_due": None, "source": "jarvis", "demo": True, "created_at": now})
    await db.calendar_events.insert_many(docs)
    # Prediction card in the PREDICTIONS box
    await db.lifecard_predictions.update_one(
        {"user_id": uid, "child_id": None},
        {"$set": {"user_id": uid, "child_id": None, "generated_at": now,
                  "predictions": [DEMO_PREDICTION]}},
        upsert=True)
    await db.demo_seed.insert_one({"user_id": uid, "kind": "lifecard", "at": now})
    return {"ok": True, "seeded": True, "records": len(docs)}
