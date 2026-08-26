# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""SOVEREIGN HEALING LOOP — Kolotoč uzdravenia.
Injury Event → Neural Bus fires SIMULTANEOUSLY: Insurance Claim (money IN) + Waitlist Hunter.
Steps: intake → financial_shield → access → bureaucracy → recovery.
Also: Companion (empathetic senior check-ins + emotional trends) and Voice Echoes (family voice-stream)."""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException, Header
from pydantic import BaseModel

from core import api, db, logger, clean, get_current_user, send_push
from routes.hunter import _simulate_slot

STEP_KEYS = ["intake", "financial_shield", "access", "bureaucracy", "recovery"]
STEP_META = {
    "intake": {"title": "Príjem", "icon": "scan", "sub": "Sken žiadanky / zápis úrazu"},
    "financial_shield": {"title": "Finančný štít", "icon": "umbrella", "sub": "Poistka → peniaze hneď"},
    "access": {"title": "Prístup", "icon": "search", "sub": "Lovec termínov → doktor"},
    "bureaucracy": {"title": "Papierovačky", "icon": "document-text", "sub": "Neschopenka · vychádzky"},
    "recovery": {"title": "Zotavenie", "icon": "body", "sub": "Physio-AI · 100 % fit"},
}

KIND_LABEL = {"injury": "Úraz", "illness": "Choroba"}


def _now():
    return datetime.now(timezone.utc)


async def _active_journey(uid: str) -> Optional[dict]:
    return await db.healing_journeys.find_one({"user_id": uid, "status": "active"}, {"_id": 0})


class InjuryEventIn(BaseModel):
    kind: str = "injury"           # injury | illness
    specialty: str = "Všeobecný lekár"
    body_part: Optional[str] = None
    note: Optional[str] = ""


async def _fire_insurance_claim(uid: str, event: dict) -> dict:
    """Financial Shield: check accident/health policies and PRE-FILL a benefit claim draft."""
    pols = await db.insurance_policies.find({"user_id": uid}, {"_id": 0}).to_list(20)
    prof = await db.emergency_profiles.find_one({"user_id": uid}, {"_id": 0}) or {}
    # Prefer disability/accident cover, then health
    pol = next((p for p in pols if p.get("type") == "disability"), None) or \
        next((p for p in pols if p.get("type") == "health"), None) or (pols[0] if pols else None)
    daily = round((pol.get("premium_monthly", 0) or 20) * 0.8 + 12, 2) if pol else 15.0
    claim = {
        "claim_id": uuid.uuid4().hex, "user_id": uid,
        "journey_id": event["journey_id"],
        "provider": (pol or {}).get("provider") or "— doplňte poistku —",
        "policy_id": (pol or {}).get("policy_id"),
        "policy_found": bool(pol),
        "claimant_name": prof.get("full_name") or "",
        "event_kind": event["kind"], "specialty": event["specialty"],
        "body_part": event.get("body_part"), "note": event.get("note") or "",
        "daily_benefit_eur": daily,
        "estimated_days": 21,
        "estimated_total_eur": round(daily * 21, 2),
        "status": "prefilled",  # prefilled → submitted → paid
        "created_at": _now(),
    }
    await db.insurance_claims.insert_one(claim.copy())
    return clean(claim)


async def _fire_waitlist_hunter(uid: str, event: dict) -> dict:
    """Access: Waitlist Hunter immediately hunts the earliest slot (Prague base)."""
    slot = _simulate_slot(event["specialty"], "Praha")
    found = f"{slot['date']} {slot['time']} — {slot['clinic']}"
    item = {
        "item_id": uuid.uuid4().hex, "user_id": uid, "specialty": event["specialty"],
        "clinic": slot["clinic"], "city": "Praha", "current_date": "", "target_before": slot["date"],
        "priority": "auto", "status": "booked", "last_check": _now(), "found_slot": found,
        "created_at": _now(), "source": "healing_loop",
    }
    await db.waitlist.insert_one(item.copy())
    await db.calendar_events.insert_one({
        "event_id": uuid.uuid4().hex, "user_id": uid, "category": "exam",
        "title": f"{event['specialty']} — {slot['clinic']}", "date": slot["date"],
        "notes": f"Kolotoč uzdravenia · {slot['time']}", "booster_due": None,
        "source": "healing_loop", "created_at": _now(),
    })
    return {"slot": found, "clinic": slot["clinic"], "date": slot["date"], "time": slot["time"]}


@api.post("/healing/injury-event")
async def healing_injury_event(body: InjuryEventIn, authorization: Optional[str] = Header(None)):
    """NEURAL BUS: one injury event triggers Insurance Claim AND Waitlist Hunter SIMULTANEOUSLY."""
    user = await get_current_user(authorization)
    uid = user["user_id"]
    if body.kind not in ("injury", "illness"):
        raise HTTPException(400, "kind must be injury|illness")
    existing = await _active_journey(uid)
    if existing:
        await db.healing_journeys.update_one(
            {"journey_id": existing["journey_id"]}, {"$set": {"status": "superseded"}})
    journey_id = uuid.uuid4().hex
    event = {"journey_id": journey_id, "kind": body.kind,
             "specialty": body.specialty.strip()[:60] or "Všeobecný lekár",
             "body_part": (body.body_part or "").strip()[:60] or None,
             "note": (body.note or "")[:300]}

    # SIMULTANEOUS neural-bus dispatch — money and doctor at the same instant
    claim, access = await asyncio.gather(
        _fire_insurance_claim(uid, event),
        _fire_waitlist_hunter(uid, event),
    )
    await db.neural_bus.insert_one({
        "event_id": uuid.uuid4().hex, "user_id": uid, "type": "injury_event",
        "journey_id": journey_id, "triggered": ["insurance_claim", "waitlist_hunter"],
        "created_at": _now(),
    })

    steps = {k: "pending" for k in STEP_KEYS}
    steps["intake"] = "done"
    steps["financial_shield"] = "done" if claim["policy_found"] else "action_needed"
    steps["access"] = "done"
    journey = {
        "journey_id": journey_id, "user_id": uid, "status": "active",
        "kind": body.kind, "kind_label": KIND_LABEL[body.kind],
        "specialty": event["specialty"], "body_part": event["body_part"], "note": event["note"],
        "steps": steps, "claim_id": claim["claim_id"], "access": access,
        "created_at": _now(),
    }
    await db.healing_journeys.insert_one(journey.copy())
    try:
        await send_push(recipients=[uid], data={
            "title": "⚙️ KOLOTOČ UZDRAVENIA SPUSTENÝ",
            "message": f"{KIND_LABEL[body.kind]} zapísaný · poistná žiadosť predvyplnená ({claim['estimated_total_eur']} €) · termín: {access['slot']}",
            "action_url": "/healing"})
    except Exception as e:
        logger.warning(f"healing push: {e}")
    return {"journey": clean(journey), "claim": claim, "access": access, "simulated": True}


@api.get("/healing/state")
async def healing_state(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    j = await _active_journey(uid)
    if not j:
        last = await db.healing_journeys.find_one(
            {"user_id": uid, "status": "recovered"}, {"_id": 0}, sort=[("created_at", -1)])
        return {"active": False, "last_recovered": clean(last) if last else None,
                "steps_meta": STEP_META, "step_keys": STEP_KEYS}
    claim = await db.insurance_claims.find_one({"claim_id": j.get("claim_id")}, {"_id": 0})
    recovery = await db.recovery.find_one({"user_id": uid}, {"_id": 0}) or {}
    if recovery.get("start_date") and j["steps"].get("bureaucracy") == "pending":
        j["steps"]["bureaucracy"] = "done"
        await db.healing_journeys.update_one(
            {"journey_id": j["journey_id"]}, {"$set": {"steps.bureaucracy": "done"}})
    done = sum(1 for s in j["steps"].values() if s == "done")
    return {"active": True, "journey": clean(j), "claim": clean(claim) if claim else None,
            "recovery": clean(recovery), "progress_pct": int(done / len(STEP_KEYS) * 100),
            "steps_meta": STEP_META, "step_keys": STEP_KEYS}


@api.post("/healing/step/{step_key}/complete")
async def healing_step_complete(step_key: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if step_key not in STEP_KEYS:
        raise HTTPException(400, f"step must be one of {STEP_KEYS}")
    j = await _active_journey(user["user_id"])
    if not j:
        raise HTTPException(404, "No active healing journey")
    await db.healing_journeys.update_one(
        {"journey_id": j["journey_id"]}, {"$set": {f"steps.{step_key}": "done"}})
    return {"ok": True, "step": step_key}


@api.post("/healing/claim/{claim_id}/submit")
async def healing_claim_submit(claim_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.insurance_claims.update_one(
        {"claim_id": claim_id, "user_id": user["user_id"], "status": "prefilled"},
        {"$set": {"status": "submitted", "submitted_at": _now()}})
    if res.matched_count == 0:
        raise HTTPException(404, "Claim not found or already submitted")
    c = await db.insurance_claims.find_one({"claim_id": claim_id}, {"_id": 0})
    return {"ok": True, "claim": clean(c)}


@api.post("/healing/close")
async def healing_close(authorization: Optional[str] = Header(None)):
    """Founder is 100% fit for work — close the loop with dignity."""
    user = await get_current_user(authorization)
    j = await _active_journey(user["user_id"])
    if not j:
        raise HTTPException(404, "No active healing journey")
    await db.healing_journeys.update_one(
        {"journey_id": j["journey_id"]},
        {"$set": {"status": "recovered", "steps.recovery": "done", "recovered_at": _now()}})
    return {"ok": True, "message": "Kolotoč dokončený — ste 100 % fit. Jarvis vám gratuluje."}


# =========================================================================
# THE COMPANION — empathetic caregiver check-ins + emotional trends
# =========================================================================

MOOD_LABEL = {1: "veľmi zle", 2: "slabšie", 3: "ujde to", 4: "dobre", 5: "výborne"}


def _companion_greeting_text(hour: int, name: str, last_mood: Optional[int]) -> dict:
    n = (name or "").split(" ")[0] or "priateľu"
    if 5 <= hour < 11:
        q = f"Dobré ráno, {n}. Ako ste sa dnes vyspali? Snívalo sa vám niečo pekné?"
        topic = "sleep"
    elif 11 <= hour < 15:
        q = f"Pekné poludnie, {n}. Už ste dnes obedovali? Čo dobré ste mali?"
        topic = "meal"
    elif 15 <= hour < 20:
        q = f"Dobrý podvečer, {n}. Ako sa dnes cíti vaše telo — nebolí vás niečo?"
        topic = "pain"
    else:
        q = f"Dobrý večer, {n}. Deň sa končí — ako sa cítite? Nezabudnite na večerné lieky."
        topic = "evening"
    care = ""
    if last_mood is not None and last_mood <= 2:
        care = "Naposledy ste sa necítili najlepšie — dnes som tu pre vás o to viac. 💛"
    return {"question": q, "topic": topic, "care_note": care}


@api.get("/companion/greeting")
async def companion_greeting(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    last = await db.companion_checkins.find_one(
        {"user_id": uid}, {"_id": 0}, sort=[("created_at", -1)])
    today = _now().date().isoformat()
    answered_today = bool(last and str(last.get("created_at", ""))[:10] == today)
    hour = (_now().hour + 2) % 24  # Europe/Prague approximation (CEST)
    g = _companion_greeting_text(hour, user.get("name") or "", (last or {}).get("mood"))
    return {**g, "answered_today": answered_today, "last_mood": (last or {}).get("mood")}


class CheckinIn(BaseModel):
    mood: int                      # 1..5
    note: Optional[str] = ""
    topic: Optional[str] = None


@api.post("/companion/checkin")
async def companion_checkin(body: CheckinIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if not 1 <= body.mood <= 5:
        raise HTTPException(400, "mood must be 1..5")
    doc = {"checkin_id": uuid.uuid4().hex, "user_id": user["user_id"],
           "mood": body.mood, "mood_label": MOOD_LABEL[body.mood],
           "note": (body.note or "")[:300], "topic": body.topic,
           "created_at": _now()}
    await db.companion_checkins.insert_one(doc.copy())
    if body.mood <= 2:
        reply = "Ďakujem, že ste mi to povedali. Nie ste v tom sami — ak to potrvá, spolu zavoláme rodine alebo lekárovi. 💛"
        try:
            await send_push(recipients=[user["user_id"]], data={
                "title": "💛 JARVIS PRI VÁS", "message": "Zaznamenal som horší deň — rodina má vedieť, že vám má zavolať.",
                "action_url": "/wellness"})
        except Exception:
            pass
    elif body.mood == 3:
        reply = "Rozumiem, taký stredný deň. Krátka prechádzka alebo odkaz od rodiny vždy pomôže — mám ich pripravené."
    else:
        reply = "To rád počujem! Krásny deň, nech vám vydrží. Keby čokoľvek, som tu."
    return {"ok": True, "reply": reply, "checkin": clean(doc)}


@api.get("/companion/trends")
async def companion_trends(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    since = _now() - timedelta(days=14)
    rows = await db.companion_checkins.find(
        {"user_id": user["user_id"], "created_at": {"$gte": since}}, {"_id": 0}
    ).sort("created_at", 1).to_list(60)
    moods = [r["mood"] for r in rows]
    avg = round(sum(moods) / len(moods), 2) if moods else None
    direction = "stable"
    if len(moods) >= 4:
        half = len(moods) // 2
        a, b = sum(moods[:half]) / half, sum(moods[half:]) / (len(moods) - half)
        direction = "improving" if b - a > 0.3 else ("declining" if a - b > 0.3 else "stable")
    return {"checkins": rows, "avg_mood_14d": avg, "trend": direction, "count": len(rows)}


# =========================================================================
# VOICE ECHOES — family voice-stream for seniors (one tap, no menus)
# =========================================================================

class EchoIn(BaseModel):
    from_name: str
    message: str


@api.get("/family/echoes")
async def echoes_list(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.voice_echoes.find({"user_id": user["user_id"]}, {"_id": 0}) \
        .sort("created_at", -1).to_list(30)
    unheard = sum(1 for r in rows if not r.get("heard"))
    return {"echoes": rows, "unheard": unheard}


@api.post("/family/echoes")
async def echoes_add(body: EchoIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if not body.message.strip():
        raise HTTPException(400, "message required")
    doc = {"echo_id": uuid.uuid4().hex, "user_id": user["user_id"],
           "from_name": body.from_name.strip()[:60] or "Rodina",
           "message": body.message.strip()[:400], "heard": False,
           "created_at": _now()}
    await db.voice_echoes.insert_one(doc.copy())
    try:
        await send_push(recipients=[user["user_id"]], data={
            "title": "💌 NOVÝ ODKAZ OD RODINY",
            "message": f"{doc['from_name']}: ťuknite a Jarvis vám ho prečíta.",
            "action_url": "/voice-echoes"})
    except Exception:
        pass
    return {"ok": True, "echo": clean(doc)}


@api.post("/family/echoes/{echo_id}/heard")
async def echoes_heard(echo_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await db.voice_echoes.update_one(
        {"echo_id": echo_id, "user_id": user["user_id"]}, {"$set": {"heard": True}})
    return {"ok": True}
