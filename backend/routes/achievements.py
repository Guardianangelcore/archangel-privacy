# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# SOVEREIGN ACHIEVEMENTS — small dopamine hits for building trust.
# Each badge is derived on-demand from cross-cutting collections. No new
# collection required (the source of truth stays in place).
from typing import Optional
from datetime import datetime, timezone
from fastapi import Header

from core import api, db, clean
from routes.auth import get_current_user

# Master catalog — ORDER MATTERS on the frontend grid.
CATALOG = [
    {
        "key": "sovereign_onboarded",
        "title": "Sovereign Uvítanie",
        "hint": "Dokončite 30-sekundovú Sovereign prehliadku po prvom prihlásení.",
        "icon": "sparkles",
        "check_field": "onboarding_completed",
    },
    {
        "key": "bio_timeline_set",
        "title": "Bio-Timeline nastavená",
        "hint": "Nastavte rok narodenia (ručne alebo naskenovaním OP).",
        "icon": "calendar",
        "check_field": "birth_year",
    },
    {
        "key": "biometric_gate",
        "title": "Osobný Signál",
        "hint": "Zapnite FaceID / odtlačok prsta ako zámok pri otvorení aplikácie.",
        "icon": "finger-print",
        "check_field": "biometric_enabled",
    },
    {
        "key": "voice_print_first",
        "title": "Prvý Hlasový Podpis",
        "hint": "Nahrajte svoju 5-sekundovú hlasovú vizitku pre rodinu.",
        "icon": "mic-circle",
        "check_collection": "voice_signatures",
    },
    {
        "key": "angel_first_contact",
        "title": "Prvý Rodinný Strážca",
        "hint": "Pridajte prvého člena rodinného kruhu (guardian link).",
        "icon": "people-circle",
        "check_collection": "guardians",
        "check_or_field": "guardian_user_id",
    },
    {
        "key": "physio_first_series",
        "title": "Prvá Fyzio Séria",
        "hint": "Dokončite prvé cvičenie s Physio-AI.",
        "icon": "fitness",
        "check_collection": "physio_videos",
    },
    {
        "key": "healing_loop_first",
        "title": "Prvý Kolotoč Uzdravenia",
        "hint": "Prejdite kolotočom: žiadanka → peniaze → doktor → fyzio.",
        "icon": "sync-circle",
        "check_collection": "healing_events",
    },
    {
        "key": "vault_first_doc",
        "title": "Prvý dokument v Trezore",
        "hint": "Uložte prvý dokument (OP / zmluva / faktúra) do Suverénneho Trezoru.",
        "icon": "shield-checkmark",
        "check_collection": "documents",
    },
]


async def _count_for(user_id: str, spec: dict) -> tuple[bool, Optional[datetime]]:
    """Return (unlocked, unlocked_at) for one badge spec."""
    if spec.get("check_field"):
        # Field-based check: unlocked when the user field is truthy.
        u = await db.users.find_one({"user_id": user_id}, {"_id": 0, spec["check_field"]: 1, "created_at": 1})
        if u and u.get(spec["check_field"]):
            return True, u.get("created_at")
        return False, None
    if spec.get("check_collection"):
        coll = getattr(db, spec["check_collection"])
        q: dict = {"user_id": user_id}
        if spec.get("check_or_field"):
            # e.g. guardians can be matched on user_id OR guardian_user_id (either direction).
            q = {"$or": [{"user_id": user_id}, {spec["check_or_field"]: user_id}]}
        row = await coll.find_one(q, sort=[("created_at", 1)])
        if row:
            return True, row.get("created_at") or row.get("updated_at")
        return False, None
    return False, None


@api.get("/achievements")
async def achievements(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]

    unlocked = []
    locked = []
    for spec in CATALOG:
        ok, when = await _count_for(uid, spec)
        row = {
            "key": spec["key"],
            "title": spec["title"],
            "hint": spec["hint"],
            "icon": spec["icon"],
            "unlocked": ok,
            "unlocked_at": when,
        }
        if ok:
            unlocked.append(row)
        else:
            locked.append(row)

    total = len(CATALOG)
    return {
        "unlocked": clean(unlocked),
        "locked": clean(locked),
        "unlocked_count": len(unlocked),
        "total": total,
        "progress": round(len(unlocked) * 100 / total) if total else 0,
    }


# --------- SOVEREIGN STREAKS ---------
# Habit-building for seniors: consecutive days with at least one Physio Video watched.
# The streak breaks the moment a full calendar day passes without a record.
# Purposely simple — the real habit strength comes from the tiny gold flame next to
# the trophy chip, not from complex tiers.

@api.get("/streaks/physio")
async def streak_physio(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]

    # Pull the last ~60 days worth of Physio activity — plenty for a 7-day flame.
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=60)
    day_set: set[str] = set()
    async for v in db.physio_videos.find(
        {"user_id": uid, "created_at": {"$gte": cutoff}},
        {"_id": 0, "created_at": 1},
    ):
        d = v.get("created_at")
        if not d:
            continue
        if isinstance(d, str):
            try:
                d = datetime.fromisoformat(d.replace("Z", "+00:00"))
            except Exception:
                continue
        # Motor strips tzinfo — treat naive datetimes as already-UTC (they were
        # inserted via datetime.now(timezone.utc)) so we don't accidentally shift.
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        day_set.add(d.astimezone(timezone.utc).date().isoformat())

    today = now.date()
    # Current streak: count backwards from today (or yesterday if today is empty)
    current = 0
    cursor = today
    if today.isoformat() not in day_set:
        # yesterday is the grace day — if that's also missing, streak = 0
        cursor = today - timedelta(days=1)
    while cursor.isoformat() in day_set:
        current += 1
        cursor = cursor - timedelta(days=1)

    # Best streak in the last 60 days
    best = 0
    if day_set:
        sorted_days = sorted(day_set)
        run = 1
        for i in range(1, len(sorted_days)):
            prev = datetime.fromisoformat(sorted_days[i - 1]).date()
            cur = datetime.fromisoformat(sorted_days[i]).date()
            if (cur - prev).days == 1:
                run += 1
                best = max(best, run)
            else:
                best = max(best, run)
                run = 1
        best = max(best, run)

    # Compute a "tier" for the flame glow — 1..3 based on current streak length.
    if current >= 30:
        tier = 3  # Blazing (30+ days)
    elif current >= 7:
        tier = 2  # Golden (7-29 days)
    elif current >= 1:
        tier = 1  # Ember (1-6 days)
    else:
        tier = 0  # Cold — no flame

    return {
        "current": current,
        "best": max(best, current),
        "tier": tier,
        "active_today": today.isoformat() in day_set,
    }
