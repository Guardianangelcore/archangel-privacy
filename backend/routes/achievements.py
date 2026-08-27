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
