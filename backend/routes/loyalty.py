# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""LOYALTY MILESTONES — 3 / 6 / 12 months on a paid plan → one-time GA-T bonus + profile badge
+ in-app congratulation (unseen flag). Months are counted from `tier_started_at`.
"""
from fastapi import Header
from typing import Optional
from datetime import datetime, timezone

from core import api, db, clean, get_current_user

LOYALTY_MILESTONES = [
    {"months": 3, "gat": 50.0, "badge": "Loyal Guardian", "icon": "ribbon-outline"},
    {"months": 6, "gat": 150.0, "badge": "Sentinel Veteran", "icon": "medal-outline"},
    {"months": 12, "gat": 500.0, "badge": "Archangel Legend", "icon": "trophy-outline"},
]


def _months_between(start: datetime, now: datetime) -> int:
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    m = (now.year - start.year) * 12 + (now.month - start.month)
    if now.day < start.day:
        m -= 1
    return max(0, m)


async def check_loyalty(user_id: str) -> dict:
    """Idempotent: awards any newly reached milestone, returns the loyalty snapshot."""
    from routes.subscription import current_tier
    from routes.token import _ledger_append, _get_supply
    now = datetime.now(timezone.utc)
    fresh = await db.users.find_one({"user_id": user_id}, {"_id": 0, "tier": 1, "tier_until": 1, "inner_circle": 1,
                                                          "tier_started_at": 1, "loyalty_milestones": 1}) or {}
    tier = current_tier(fresh)
    achieved = fresh.get("loyalty_milestones") or []
    if tier == "sovereign":
        return {"tier": tier, "months": 0, "milestones": achieved, "badge": _badge(achieved), "unseen": [], "next": None}
    started = fresh.get("tier_started_at")
    if isinstance(started, str):
        started = datetime.fromisoformat(started.replace("Z", "+00:00"))
    if not started:
        # Paid tier bought via GA-T/card before this feature existed — start counting now.
        started = now
        await db.users.update_one({"user_id": user_id}, {"$set": {"tier_started_at": now}})
    months = _months_between(started, now)
    have = {m["months"] for m in achieved}
    new = []
    for ms in LOYALTY_MILESTONES:
        if months >= ms["months"] and ms["months"] not in have:
            supply = await _get_supply()
            if supply["treasury"] < ms["gat"]:
                break
            await db.token_supply.update_one({"key": "gat"}, {"$inc": {"treasury": -ms["gat"], "circulating": ms["gat"]}})
            await db.token_accounts.update_one({"user_id": user_id},
                                               {"$inc": {"balance": ms["gat"], "earned_total": ms["gat"]},
                                                "$set": {"updated_at": now}}, upsert=True)
            tx = await _ledger_append("earn", user_id, ms["gat"],
                                      {"activity": "loyalty_milestone", "months": ms["months"], "badge": ms["badge"]})
            new.append({"months": ms["months"], "gat": ms["gat"], "badge": ms["badge"], "icon": ms["icon"],
                        "at": now, "tx_id": tx["tx_id"], "seen": False})
    if new:
        achieved = achieved + new
        await db.users.update_one({"user_id": user_id}, {"$set": {"loyalty_milestones": achieved, "loyalty_badge": _badge(achieved)}})
    nxt = next((ms for ms in LOYALTY_MILESTONES if ms["months"] not in {m["months"] for m in achieved}), None)
    return {"tier": tier, "months": months, "started_at": started, "milestones": achieved, "badge": _badge(achieved),
            "unseen": [m for m in achieved if not m.get("seen")], "next": nxt}


def _badge(achieved: list) -> Optional[str]:
    if not achieved:
        return None
    top = max(achieved, key=lambda m: m["months"])
    return top["badge"]


@api.get("/loyalty")
async def loyalty_status(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return clean(await check_loyalty(user["user_id"]))


@api.post("/loyalty/seen")
async def loyalty_seen(authorization: Optional[str] = Header(None)):
    """Marks the congratulation as shown (in-app notification dismissed)."""
    user = await get_current_user(authorization)
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "loyalty_milestones": 1}) or {}
    ms = [{**m, "seen": True} for m in (fresh.get("loyalty_milestones") or [])]
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"loyalty_milestones": ms}})
    return {"ok": True, "milestones": clean(ms)}
