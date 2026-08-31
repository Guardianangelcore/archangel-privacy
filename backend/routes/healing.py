# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""SOVEREIGN HEALING LOOP — Kolotoč uzdravenia.
Injury Event → Neural Bus fires SIMULTANEOUSLY: Insurance Claim (money IN) + Waitlist Hunter.
Steps: intake → financial_shield → access → bureaucracy → recovery.
Also: Companion (empathetic senior check-ins + emotional trends) and Voice Echoes (family voice-stream)."""
import asyncio
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException, Header, UploadFile, File, Form, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from core import (
    api, db, logger, clean, get_current_user, send_push,
    _make_pdf, _auth_pdf, _pdf_footer, _pdf_response,
    APP_NAME, put_object_sync, get_object_sync,
)
from routes.hunter import _simulate_slot

STEP_KEYS = ["intake", "financial_shield", "access", "bureaucracy", "recovery"]
STEP_META = {
    "intake": {"title": "Intake", "icon": "scan", "sub": "Scan referral / log injury"},
    "financial_shield": {"title": "Financial Shield", "icon": "umbrella", "sub": "Insurance → instant money"},
    "access": {"title": "Access", "icon": "search", "sub": "Appointment Hunter → doctor"},
    "bureaucracy": {"title": "Paperwork", "icon": "document-text", "sub": "Sick leave · outings"},
    "recovery": {"title": "Recovery", "icon": "body", "sub": "Physio-AI · 100 % fit"},
}

KIND_LABEL = {"injury": "Injury", "illness": "Illness"}


def _now():
    return datetime.now(timezone.utc)


async def _active_journey(uid: str) -> Optional[dict]:
    return await db.healing_journeys.find_one({"user_id": uid, "status": "active"}, {"_id": 0})


class InjuryEventIn(BaseModel):
    kind: str = "injury"           # injury | illness
    specialty: str = "General practitioner"
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
        "provider": (pol or {}).get("provider") or "— add your policy —",
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
        "notes": f"Healing Loop · {slot['time']}", "booster_due": None,
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
             "specialty": body.specialty.strip()[:60] or "General practitioner",
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
            "title": "⚙️ HEALING LOOP STARTED",
            "message": f"{KIND_LABEL[body.kind]} logged · insurance claim prefilled (€{claim['estimated_total_eur']}) · appointment: {access['slot']}",
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
    return {"ok": True, "message": "Loop complete — you are 100% fit. Jarvis congratulates you."}


# =========================================================================
# THE COMPANION — empathetic caregiver check-ins + emotional trends
# =========================================================================

MOOD_LABEL = {1: "very bad", 2: "poor", 3: "okay", 4: "good", 5: "great"}


def _companion_greeting_text(hour: int, name: str, last_mood: Optional[int]) -> dict:
    n = (name or "").split(" ")[0] or "friend"
    if 5 <= hour < 11:
        q = f"Good morning, {n}. How did you sleep? Any nice dreams?"
        topic = "sleep"
    elif 11 <= hour < 15:
        q = f"Good afternoon, {n}. Have you had lunch yet? What did you enjoy?"
        topic = "meal"
    elif 15 <= hour < 20:
        q = f"Good early evening, {n}. How does your body feel today — any pain?"
        topic = "pain"
    else:
        q = f"Good evening, {n}. The day is ending — how do you feel? Do not forget your evening meds."
        topic = "evening"
    care = ""
    if last_mood is not None and last_mood <= 2:
        care = "You did not feel your best last time — I am here for you all the more today. 💛"
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
        reply = "Thank you for telling me. You are not alone — if it lasts, we will call your family or doctor together. 💛"
        try:
            await send_push(recipients=[user["user_id"]], data={
                "title": "💛 JARVIS BY YOUR SIDE", "message": "I logged a rougher day — your family should know to call you.",
                "action_url": "/wellness"})
        except Exception:
            pass
    elif body.mood == 3:
        reply = "I understand, an average day. A short walk or a family message always helps — I have them ready."
    else:
        reply = "Glad to hear that! Have a beautiful day. If anything comes up, I am here."
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
            "title": "💌 NEW FAMILY MESSAGE",
            "message": f"{doc['from_name']}: tap and Jarvis will read it to you.",
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


# ---- RECOVERY PULSE — family sees that pain is dropping and healing goes well ----

def _pain_trend_of(levels: list) -> str:
    if len(levels) >= 4:
        half = len(levels) // 2
        a, b = sum(levels[:half]) / half, sum(levels[half:]) / (len(levels) - half)
        return "improving" if a - b > 0.5 else ("worsening" if b - a > 0.5 else "stable")
    return "stable"


_PULSE_MSG = {
    "improving": "Pain is falling — recovery is going well 💛",
    "worsening": "Pain is rising — call and encourage them 📞",
    "stable": "Condition is stable — holding up 💪",
}


@api.get("/family/recovery-pulse")
async def family_recovery_pulse(authorization: Optional[str] = Header(None)):
    """Summary of loved ones' healing (I am their guardian): pain curve + Carousel progress."""
    user = await get_current_user(authorization)
    links = await db.guardians.find(
        {"guardian_user_id": user["user_id"]}, {"_id": 0}).to_list(20)
    since = _now() - timedelta(days=14)
    out = []
    for l in links:
        u = await db.users.find_one({"user_id": l["user_id"]}, {"_id": 0, "user_id": 1, "name": 1, "email": 1})
        if not u:
            continue
        pain = await db.pain_diary.find(
            {"user_id": u["user_id"], "created_at": {"$gte": since}}, {"_id": 0, "level": 1}
        ).sort("created_at", 1).to_list(100)
        levels = [p["level"] for p in pain]
        trend = _pain_trend_of(levels)
        j = await db.healing_journeys.find_one({"user_id": u["user_id"], "status": "active"}, {"_id": 0})
        progress = None
        if j:
            done = sum(1 for s in j["steps"].values() if s == "done")
            progress = int(done / len(STEP_KEYS) * 100)
        checkin = await db.companion_checkins.find_one(
            {"user_id": u["user_id"]}, {"_id": 0, "mood": 1, "mood_label": 1}, sort=[("created_at", -1)])
        out.append({
            "user_id": u["user_id"], "name": u.get("name") or u["email"], "email": u["email"],
            "pain_levels": levels[-7:], "pain_avg_14d": round(sum(levels) / len(levels), 1) if levels else None,
            "pain_trend": trend if levels else None,
            "message": _PULSE_MSG[trend] if levels else "No pain records yet",
            "healing_active": bool(j), "healing_progress_pct": progress,
            "healing_label": f"{j['kind_label']} · {j['specialty']}" if j else None,
            "last_mood": (checkin or {}).get("mood"), "last_mood_label": (checkin or {}).get("mood_label"),
        })
    return {"loved_ones": out}


# ---- REMOTE FAMILY ACCESS — Inner Circle / guardians send echoes from their own account ----

async def _may_send_to(sender: dict, recipient: dict) -> bool:
    """Sender may send an echo if the recipient listed them as a guardian,
    or the sender is an Inner Circle member (founder family)."""
    link = await db.guardians.find_one(
        {"user_id": recipient["user_id"], "guardian_user_id": sender["user_id"]})
    if link:
        return True
    if await db.inner_circle.find_one({"email": sender.get("email", "").lower()}):
        return True
    return False


@api.get("/family/echoes/recipients")
async def echoes_recipients(authorization: Optional[str] = Header(None)):
    """People I can send remote echoes to (I am their guardian)."""
    user = await get_current_user(authorization)
    links = await db.guardians.find(
        {"guardian_user_id": user["user_id"]}, {"_id": 0}).to_list(20)
    out = []
    for l in links:
        u = await db.users.find_one({"user_id": l["user_id"]}, {"_id": 0, "user_id": 1, "name": 1, "email": 1})
        if u:
            out.append({"user_id": u["user_id"], "name": u.get("name") or u["email"], "email": u["email"]})
    is_inner = bool(await db.inner_circle.find_one({"email": user.get("email", "").lower()}))
    return {"recipients": out, "inner_circle_member": is_inner}


class RemoteEchoIn(BaseModel):
    to_email: str
    message: str


@api.post("/family/echoes/send")
async def echoes_send_remote(body: RemoteEchoIn, authorization: Optional[str] = Header(None)):
    """Family member sends a Voice Echo to a senior FROM THEIR OWN account, remotely."""
    sender = await get_current_user(authorization)
    if not body.message.strip():
        raise HTTPException(400, "message required")
    recipient = await db.users.find_one({"email": body.to_email.strip().lower()}, {"_id": 0})
    if not recipient:
        raise HTTPException(404, "No recipient with this e-mail exists in Guardian OS.")
    if recipient["user_id"] == sender["user_id"]:
        raise HTTPException(400, "Send a message to yourself via the regular add flow.")
    if not await _may_send_to(sender, recipient):
        raise HTTPException(403, "Not authorized — the recipient must add you as a guardian (Sovereign Recovery), or you must be in the Inner Circle.")
    doc = {"echo_id": uuid.uuid4().hex, "user_id": recipient["user_id"],
           "from_name": sender.get("name") or sender.get("email") or "Rodina",
           "sender_user_id": sender["user_id"], "remote": True,
           "message": body.message.strip()[:400], "heard": False,
           "created_at": _now()}
    await db.voice_echoes.insert_one(doc.copy())
    try:
        await send_push(recipients=[recipient["user_id"]], data={
            "title": "💌 NEW FAMILY MESSAGE",
            "message": f"{doc['from_name']}: tap and Jarvis will read it to you.",
            "action_url": "/voice-echoes"})
    except Exception:
        pass
    return {"ok": True, "echo": clean(doc), "to": recipient.get("name") or recipient["email"]}


# ---- VOICE RECORDINGS — family records a real voice message (microphone) ----

async def _resolve_echo_recipient(sender: dict, to_email: Optional[str]) -> dict:
    """Recipient of an echo: self, or a linked senior (guardian/inner-circle authz)."""
    if not to_email:
        return sender
    recipient = await db.users.find_one({"email": to_email.strip().lower()}, {"_id": 0})
    if not recipient:
        raise HTTPException(404, "No recipient with this e-mail exists in Guardian OS.")
    if recipient["user_id"] != sender["user_id"] and not await _may_send_to(sender, recipient):
        raise HTTPException(403, "Not authorized — the recipient must add you as a guardian (Sovereign Recovery), or you must be in the Inner Circle.")
    return recipient


@api.post("/family/echoes/audio")
async def echoes_add_audio(
    file: UploadFile = File(...),
    from_name: str = Form("Rodina"),
    to_email: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
):
    """Upload a REAL voice recording as an echo (own voice instead of Jarvis TTS)."""
    sender = await get_current_user(authorization)
    recipient = await _resolve_echo_recipient(sender, to_email)
    data = await file.read()
    if not data:
        raise HTTPException(400, "empty audio")
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(400, "audio too large (max 15 MB)")
    echo_id = uuid.uuid4().hex
    ctype = file.content_type or "audio/m4a"
    path = f"{APP_NAME}/echoes/{recipient['user_id']}/{echo_id}.m4a"
    await run_in_threadpool(put_object_sync, path, data, ctype)
    remote = recipient["user_id"] != sender["user_id"]
    doc = {"echo_id": echo_id, "user_id": recipient["user_id"],
           "from_name": (sender.get("name") if remote else from_name.strip()[:60]) or "Rodina",
           "sender_user_id": sender["user_id"], "remote": remote,
           "message": "🎙 Voice recording", "audio": True,
           "storage_path": path, "content_type": ctype, "size": len(data),
           "heard": False, "created_at": _now()}
    await db.voice_echoes.insert_one(doc.copy())
    try:
        await send_push(recipients=[recipient["user_id"]], data={
            "title": "🎙 VOICE MESSAGE FROM FAMILY",
            "message": f"{doc['from_name']} recorded a message in their own voice.",
            "action_url": "/voice-echoes"})
    except Exception:
        pass
    return {"ok": True, "echo": clean(doc), "to": recipient.get("name") or recipient["email"]}


@api.get("/family/echoes/{echo_id}/audio")
async def echoes_audio_stream(echo_id: str, token: Optional[str] = None,
                              authorization: Optional[str] = Header(None)):
    if not authorization and token:
        authorization = f"Bearer {token}"
    user = await get_current_user(authorization)
    e = await db.voice_echoes.find_one(
        {"echo_id": echo_id, "$or": [{"user_id": user["user_id"]}, {"sender_user_id": user["user_id"]}]},
        {"_id": 0})
    if not e or not e.get("audio"):
        raise HTTPException(404, "Audio echo not found")
    try:
        content, ctype = await run_in_threadpool(get_object_sync, e["storage_path"])
    except Exception as ex:
        raise HTTPException(502, f"Storage read failed: {ex}")
    return Response(content=content, media_type=ctype or e.get("content_type") or "audio/m4a")


# =========================================================================
# THE CARE SWEEPS — gentle morning reminder + Sunday auto-report (swarm hooks)
# =========================================================================

async def companion_reminder_sweep(force: bool = False) -> int:
    """Gentle morning nudge for seniors who forgot the Companion daily question."""
    now = _now()
    prague_hour = (now.hour + 2) % 24
    if not force and not (9 <= prague_hour < 12):
        return 0
    today = now.date().isoformat()
    start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) - timedelta(hours=2)
    uids = set(await db.companion_checkins.distinct("user_id"))
    async for u in db.users.find({"angel_mode": True}, {"_id": 0, "user_id": 1}):
        uids.add(u["user_id"])
    sent = 0
    for uid in uids:
        if await db.companion_checkins.find_one({"user_id": uid, "created_at": {"$gte": start_of_day}}):
            continue
        if await db.companion_reminders.find_one({"user_id": uid, "date": today}):
            continue
        u = await db.users.find_one({"user_id": uid}, {"_id": 0, "name": 1})
        n = ((u or {}).get("name") or "").split(" ")[0] or "priateľu"
        try:
            await send_push(recipients=[uid], data={
                "title": "💛 JARVIS SA PÝTA",
                "message": f"Dobré ráno, {n}. Ešte ste mi dnes nepovedali, ako sa máte — ťuknite na smajlíka, poteší ma to.",
                "action_url": "/"})
        except Exception as e:
            logger.warning(f"companion reminder push: {e}")
        await db.companion_reminders.insert_one({"user_id": uid, "date": today, "created_at": now})
        sent += 1
    return sent


@api.post("/companion/remind-sweep")
async def companion_remind_now(authorization: Optional[str] = Header(None)):
    """Manual trigger (testing/founder) — bypasses the morning window, respects daily dedup."""
    await get_current_user(authorization)
    sent = await companion_reminder_sweep(force=True)
    return {"ok": True, "reminders_sent": sent}


async def _save_report_to_vault(uid: str) -> dict:
    """Build the healing report PDF and file it into the user's Health Vault."""
    parts = await _report_parts(uid)
    pdf = await run_in_threadpool(
        _make_pdf, "TÝŽDENNÝ REPORT UZDRAVENIA\nKOLOTOČ · FINANČNÝ ŠTÍT · NÁLADA — pre lekára aj rodinu",
        "\n".join(parts), _pdf_footer())
    now = _now()
    doc_id = uuid.uuid4().hex
    path = f"{APP_NAME}/uploads/{uid}/{doc_id}.pdf"
    await run_in_threadpool(put_object_sync, path, pdf, "application/pdf")
    title = f"Týždenný report uzdravenia — {now.date().isoformat()}"
    doc = {"doc_id": doc_id, "user_id": uid, "title": title,
           "file_name": f"healing_report_{now.date().isoformat()}.pdf",
           "content_type": "application/pdf", "size": len(pdf),
           "storage_path": path, "hash": hashlib.sha256(pdf).hexdigest(),
           "uploaded_at": now, "source": "healing_report"}
    await db.documents.insert_one(doc.copy())
    await db.calendar_events.insert_one({
        "event_id": uuid.uuid4().hex, "user_id": uid, "category": "history",
        "title": f"📄 {title}"[:140], "date": now.date().isoformat(),
        "notes": "Automatický report Kolotoča uzdravenia (Jarvis)", "booster_due": None,
        "source": "healing_report", "doc_id": doc_id, "created_at": now,
    })
    return clean(doc)


@api.post("/healing/report/save-to-vault")
async def healing_report_to_vault(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    doc = await _save_report_to_vault(user["user_id"])
    return {"ok": True, "document": doc,
            "note": "Report uložený do Zdravotného trezora. Jarvis ho ukladá automaticky každú nedeľu."}


async def weekly_report_sweep(force: bool = False) -> int:
    """Every Sunday (Prague) Jarvis files the healing report into the Vault automatically."""
    now = _now()
    prague = now + timedelta(hours=2)
    if not force and prague.weekday() != 6:  # Sunday
        return 0
    iso_week = prague.strftime("%G-W%V")
    week_ago = now - timedelta(days=7)
    uids = set()
    async for j in db.healing_journeys.find({"status": "active"}, {"_id": 0, "user_id": 1}):
        uids.add(j["user_id"])
    async for c in db.companion_checkins.find({"created_at": {"$gte": week_ago}}, {"_id": 0, "user_id": 1}):
        uids.add(c["user_id"])
    saved = 0
    for uid in uids:
        if await db.healing_report_runs.find_one({"user_id": uid, "week": iso_week}):
            continue
        try:
            doc = await _save_report_to_vault(uid)
            await db.healing_report_runs.insert_one(
                {"user_id": uid, "week": iso_week, "doc_id": doc["doc_id"], "created_at": now})
            try:
                await send_push(recipients=[uid], data={
                    "title": "📄 NEDEĽNÝ REPORT V TREZORE",
                    "message": "Jarvis uložil týždenný report uzdravenia do Zdravotného trezora — pripravený pre lekára aj rodinu.",
                    "action_url": "/(tabs)/vault"})
            except Exception:
                pass
            saved += 1
        except Exception as e:
            logger.warning(f"weekly report for {uid}: {e}")
    return saved

_MOOD_BAR = {1: "█░░░░", 2: "██░░░", 3: "███░░", 4: "████░", 5: "█████"}
_TREND_SK = {"improving": "ZLEPŠUJE SA ↗", "declining": "ZHORŠUJE SA ↘", "stable": "STABILNÁ →"}


async def _report_parts(uid: str) -> list:
    """Shared body of the weekly healing report (PDF endpoint + Sunday vault auto-save)."""
    j = await _active_journey(uid) or await db.healing_journeys.find_one(
        {"user_id": uid}, {"_id": 0}, sort=[("created_at", -1)])
    claim = await db.insurance_claims.find_one({"journey_id": (j or {}).get("journey_id")}, {"_id": 0}) if j else None
    recovery = await db.recovery.find_one({"user_id": uid}, {"_id": 0}) or {}
    since = _now() - timedelta(days=14)
    checkins = await db.companion_checkins.find(
        {"user_id": uid, "created_at": {"$gte": since}}, {"_id": 0}).sort("created_at", 1).to_list(60)

    parts = []
    parts.append("1. KOLOTOČ UZDRAVENIA / HEALING CAROUSEL")
    if j:
        done = sum(1 for s in j["steps"].values() if s == "done")
        parts.append(f"  Stav: {'AKTÍVNY' if j['status'] == 'active' else j['status'].upper()} · {j['kind_label']}"
                     f"{(' · ' + j['body_part']) if j.get('body_part') else ''} · {j['specialty']}")
        parts.append(f"  Postup: {int(done / len(STEP_KEYS) * 100)} % ({done}/{len(STEP_KEYS)} krokov)")
        for i, k in enumerate(STEP_KEYS):
            st = j["steps"].get(k, "pending")
            mark = "[X]" if st == "done" else ("[!]" if st == "action_needed" else "[ ]")
            parts.append(f"    {mark} {i + 1}. {STEP_META[k]['title']} — {STEP_META[k]['sub']}")
        if (j.get("access") or {}).get("slot"):
            parts.append(f"  Zarezervovaný termín: {j['access']['slot']}")
    else:
        parts.append("  Žiadny kolotoč zatiaľ nebol spustený.")
    parts.append("\n2. FINANČNÝ ŠTÍT / INSURANCE CLAIM")
    if claim:
        parts.append(f"  Poisťovňa: {claim['provider']} · Stav žiadosti: {claim['status'].upper()}")
        parts.append(f"  Denná dávka: {claim['daily_benefit_eur']} EUR · Odhad spolu ({claim['estimated_days']} dní): {claim['estimated_total_eur']} EUR")
    else:
        parts.append("  Žiadna poistná žiadosť v tomto kolotoči.")
    parts.append("\n3. NESCHOPENKA / SICK LEAVE")
    if recovery.get("start_date"):
        parts.append(f"  PN: {recovery['start_date']} → {recovery.get('end_date') or '?'} · vychádzky: "
                     + (", ".join(f"{o['from_time']}–{o['to_time']}" for o in recovery.get("outings", [])) or "žiadne"))
    else:
        parts.append("  Bez aktívnej PN.")
    parts.append("\n4. GRAF NÁLADY (14 dní) / MOOD TREND")
    if checkins:
        for c in checkins[-14:]:
            d = str(c.get("created_at", ""))[:10]
            parts.append(f"  {d}  {_MOOD_BAR.get(c['mood'], '?????')}  {c['mood']}/5 — {c['mood_label']}")
        moods = [c["mood"] for c in checkins]
        avg = round(sum(moods) / len(moods), 2)
        direction = "stable"
        if len(moods) >= 4:
            half = len(moods) // 2
            a, b = sum(moods[:half]) / half, sum(moods[half:]) / (len(moods) - half)
            direction = "improving" if b - a > 0.3 else ("declining" if a - b > 0.3 else "stable")
        parts.append(f"  Priemer: {avg}/5 · Tendencia: {_TREND_SK[direction]}")
    else:
        parts.append("  Žiadne denné check-iny za posledných 14 dní.")
    # PAIN DIARY — 1-10 after every exercise, the doctor sees the healing curve
    pain = await db.pain_diary.find(
        {"user_id": uid, "created_at": {"$gte": since}}, {"_id": 0}).sort("created_at", 1).to_list(100)
    parts.append("\n5. BOLESŤOVÝ DENNÍK (14 dní) / PAIN DIARY — 1 až 10")
    if pain:
        for p in pain[-14:]:
            d = str(p.get("created_at", ""))[:10]
            bar = "█" * p["level"] + "░" * (10 - p["level"])
            gid = f" · {p['guide_id']}" if p.get("guide_id") else ""
            parts.append(f"  {d}  {bar}  {p['level']}/10{gid}")
        levels = [p["level"] for p in pain]
        avgp = round(sum(levels) / len(levels), 1)
        pdir = "stable"
        if len(levels) >= 4:
            half = len(levels) // 2
            a, b = sum(levels[:half]) / half, sum(levels[half:]) / (len(levels) - half)
            pdir = "improving" if a - b > 0.5 else ("worsening" if b - a > 0.5 else "stable")
        pdir_sk = {"improving": "BOLESŤ KLESÁ ↘ (hojenie)", "worsening": "BOLESŤ RASTIE ↗ (konzultujte lekára)",
                   "stable": "STABILNÁ →"}[pdir]
        parts.append(f"  Priemer: {avgp}/10 · Tendencia: {pdir_sk} · Záznamov: {len(levels)}")
    else:
        parts.append("  Žiadne záznamy bolesti — pacient zatiaľ necvičil alebo nezapisoval.")
    parts.append(f"\nVygenerované Sovereign Healing Loop · {_now().date().isoformat()}")
    return parts


@api.get("/healing/report.pdf")
async def healing_report_pdf(token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    parts = await _report_parts(user["user_id"])
    pdf = await run_in_threadpool(
        _make_pdf, "TÝŽDENNÝ REPORT UZDRAVENIA\nKOLOTOČ · FINANČNÝ ŠTÍT · NÁLADA — pre lekára aj rodinu",
        "\n".join(parts), _pdf_footer())
    return _pdf_response(pdf, "guardian_healing_report.pdf")
