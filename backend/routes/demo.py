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
        raise HTTPException(403, "founder_only: Demo Mode je dostupný iba v admin pohľade zakladateľa.")
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    await _wipe_demo(uid)  # idempotent — clean slate either way
    seeded = {}
    if body.enabled:
        # 1. Successful waitlist hunt (Kardiológia — slot found 14 days out)
        await db.waitlist.insert_one({
            "item_id": uuid.uuid4().hex, "user_id": uid,
            "specialty": "Kardiológia", "clinic": "NÚSCH Bratislava", "city": "Bratislava",
            "current_date": (now + timedelta(days=210)).strftime("%Y-%m-%d"),
            "target_before": (now + timedelta(days=60)).strftime("%Y-%m-%d"),
            "priority": "high", "status": "slot_found",
            "found_slot": (now + timedelta(days=14)).strftime("%Y-%m-%d"),
            "last_check": now, "demo": True, "created_at": now})
        # 2. €150 insurance refund claim source (dental invoice processed by Jarvis)
        await db.jarvis_actions.insert_one({
            "action_id": uuid.uuid4().hex, "user_id": uid,
            "specialty": "Stomatológia", "doc_title": "Faktúra — Dental Premium Clinic (demo)",
            "booked_slot": (now + timedelta(days=7)).strftime("%Y-%m-%d 09:00"),
            "status": "done", "steps": [{"step": "OCR", "status": "ok", "detail": "demo"}],
            "demo": True, "created_at": now})
        # 3. Family safety pulse — Guardian answered 'V PORIADKU'
        await db.pulse_requests.insert_one({
            "req_id": uuid.uuid4().hex, "from_user": uid, "from_name": "Strážca",
            "target_user": uid, "target_did": user["did"], "status": "ok",
            "responded_at": now, "demo": True, "created_at": now})
        seeded = {"waitlist_hunt": "Kardiológia · slot_found +14d",
                  "refund_claim": "Stomatológia → 150 € (Claim My Benefits)",
                  "family_pulse": "Strážca · V PORIADKU"}
    await db.users.update_one({"user_id": uid}, {"$set": {"demo_mode": body.enabled}})
    return {"demo_mode": body.enabled, "seeded": seeded}
