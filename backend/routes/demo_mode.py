# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""DEMO_ONLY — PAYMENT DEMO MODE for competition judges / investor walkthroughs.

Starts a 30-minute session during which every tier gate is unlocked (effective tier =
archangel, the highest plan) WITHOUT any real payment. Nothing is written to `tier`;
`current_tier()` simply honours `demo_until` while it is in the future, so expiry is an
automatic reset to the user's real (free) plan.

SECURITY: starting a session is FOUNDER-ONLY. Any signed-in account could previously grant
itself free Archangel access — the start endpoint now returns a uniform 403 for everybody
else (no role disclosure). Reading the status and stopping early stay open to the caller
(they can only reduce access, never grant it).
"""
from fastapi import Header, HTTPException
from typing import Optional
from datetime import datetime, timezone, timedelta

from core import api, db, get_current_user

DEMO_ONLY = True
DEMO_MINUTES = 30


def demo_active(user: dict) -> bool:
    """DEMO_ONLY — True while the judge demo session is running."""
    du = user.get("demo_until")
    if not du:
        return False
    if isinstance(du, str):
        try:
            du = datetime.fromisoformat(du.replace("Z", "+00:00"))
        except ValueError:
            return False
    if du.tzinfo is None:
        du = du.replace(tzinfo=timezone.utc)
    return du > datetime.now(timezone.utc)


def _status(fresh: dict) -> dict:
    du = fresh.get("demo_until")
    active = demo_active(fresh)
    return {"demo_only": DEMO_ONLY, "active": active, "minutes": DEMO_MINUTES,
            "demo_until": du.isoformat() if hasattr(du, "isoformat") else du,
            "seconds_left": int(max(0, (du - datetime.now(timezone.utc)).total_seconds())) if active else 0,
            "effective_tier": "archangel" if active else None}


@api.get("/demo-mode")
async def demo_mode_status(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "demo_until": 1}) or {}
    return _status(fresh)


@api.post("/demo-mode/start")
async def demo_mode_start(authorization: Optional[str] = Header(None)):
    """DEMO_ONLY — 30-minute full-access session, no payment. FOUNDER ONLY.

    Restarting extends to a fresh 30 min. Non-founder accounts get a uniform 403 so nobody
    can grant themselves free Archangel access (store reviewers use the reviewer account,
    which holds a permanent server-side Archangel entitlement instead)."""
    user = await get_current_user(authorization)
    from routes.subscription import _is_founder
    if not await _is_founder(user):
        raise HTTPException(403, "not_available: This action is not available for this account.")
    until = datetime.now(timezone.utc) + timedelta(minutes=DEMO_MINUTES)
    await db.users.update_one({"user_id": user["user_id"]},
                              {"$set": {"demo_until": until, "demo_started_at": datetime.now(timezone.utc)}})
    return _status({"demo_until": until})


@api.post("/demo-mode/stop")
async def demo_mode_stop(authorization: Optional[str] = Header(None)):
    """DEMO_ONLY — end the session early → immediate reset to the real plan."""
    user = await get_current_user(authorization)
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"demo_until": None}})
    return _status({})
