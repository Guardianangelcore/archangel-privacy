# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Jarvis Orchestrator (Medical Sentinel) + Daily Brief.

Autopilot: every new Vault document is processed autonomously in the background
— OCR → AI plain-language translation → specialty detection → appointment
auto-booking → Health Calendar — and the user only receives the confirmation.
"""
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid

from core import (api, db, logger, clean, get_current_user, send_push,
                  EMERGENT_LLM_KEY, LlmChat, UserMessage)
from routes.hunter import _simulate_slot

# ---------------- SPECIALTY DETECTION (deterministic keyword map) ----------------
SPECIALTY_MAP = [
    (("ortop", "joint", "klb", "koleno", "bedrov"), "Orthopedics"),
    (("kardio", "srdc", "ekg", "infarkt"), "Cardiology"),
    (("neurol", "migrén", "epilep"), "Neurology"),
    (("oftalm", "ophthalmic", "ocn", "zrak"), "Ophthalmology"),
    (("dermat", "dermatologic", "kozn"), "Dermatology"),
    (("onkol", "nádor", "nador", "biopsi"), "Oncology"),
    (("urol", "prostat"), "Urology"),
    (("gastro", "stomach", "zalud", "intestines", "criev"), "Gastroenterology"),
    (("diabet", "cukrovk", "glykémi", "glykemi"), "Diabetology"),
    (("rtg", "röntgen", "rontgen", "rádiol", "radiol"), "Radiology (X-ray)"),
    (("sono", "ultrazvuk", "usg"), "Radiology (ultrasound)"),
    (("rehab", "fyzio"), "Physiotherapy"),
    (("pulmonary", "pluc", "pneumo", "spirometri"), "Pulmonology"),
    (("orl", "ENT", "usn", "ENT", "krcn"), "ORL"),
    (("chirurg", "operáci", "operaci"), "Surgery"),
    (("krv", "odber", "laborat", "hematol"), "Blood draw / Laboratory"),
    (("intern", "interné"), "Internal medicine"),
]

def detect_specialty(text: str) -> Optional[str]:
    low = (text or "").lower()
    for keys, spec in SPECIALTY_MAP:
        if any(k in low for k in keys):
            return spec
    return None


def _step(name: str, status: str, detail: str) -> dict:
    return {"step": name, "status": status, "detail": detail}


# ---------------- AUTOPILOT PIPELINE ----------------
async def orchestrate_document(user_id: str, doc_id: str, force: bool = False) -> dict:
    """Background pipeline for a freshly uploaded Vault document."""
    steps = []
    doc = await db.documents.find_one({"doc_id": doc_id, "user_id": user_id}, {"_id": 0})
    if not doc:
        return {"error": "doc not found"}
    if doc.get("orchestrated") and not force:
        return {"skipped": "already orchestrated"}
    await db.documents.update_one({"doc_id": doc_id}, {"$set": {"orchestrated": True}})

    # 1. OCR / text extraction
    text = ""
    try:
        from routes.health import extract_doc_text
        text = await extract_doc_text(doc)
        steps.append(_step("OCR", "ok", f"Extracted {len(text)} characters of text"))
    except Exception as e:
        steps.append(_step("OCR", "skipped", f"Text could not be extracted ({str(e)[:60]})"))

    # 2. AI plain-language translation (Jarvis translator)
    if text and EMERGENT_LLM_KEY:
        try:
            from routes.health import build_translator_system
            user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "language": 1}) or {}
            chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"autopilot-{doc_id}",
                           system_message=build_translator_system(user.get("language", "sk"))
                           ).with_model("anthropic", "claude-sonnet-5")
            resp = await chat.send_message(UserMessage(text=text[:8000]))
            await db.documents.update_one({"doc_id": doc_id},
                                          {"$set": {"plain_language": resp, "translation": resp}})
            steps.append(_step("AI Translator", "ok", "Document translated into human language (stored in Vault)"))
        except Exception as e:
            logger.warning(f"autopilot translate failed: {e}")
            steps.append(_step("AI Translator", "skipped", "AI translation failed — try manually in Vault"))
    else:
        steps.append(_step("AI Translator", "skipped", "Without text, there is nothing to translate"))

    # 3. Specialty detection → auto-booking → calendar
    specialty = detect_specialty(f"{doc.get('title', '')} {text[:3000]}")
    booked = None
    now = datetime.now(timezone.utc)
    if specialty:
        slot = _simulate_slot(specialty, "")
        booked = f"{slot['date']} {slot['time']} — {slot['clinic']}"
        await db.waitlist.insert_one({
            "item_id": uuid.uuid4().hex, "user_id": user_id, "specialty": specialty,
            "clinic": slot["clinic"], "city": "", "current_date": "", "target_before": slot["date"],
            "priority": "auto", "status": "booked", "last_check": now,
            "found_slot": booked, "created_at": now,
        })
        await db.calendar_events.insert_one({
            "event_id": uuid.uuid4().hex, "user_id": user_id, "category": "exam",
            "title": f"{specialty} — {slot['clinic']}", "date": slot["date"],
            "notes": f"Jarvis Autopilot · {slot['time']} · z dokumentu: {doc.get('title', '')[:40]}",
            "booster_due": None, "source": f"autopilot:{doc_id}", "created_at": now,
        })
        steps.append(_step("Auto-Booker", "ok", f"Appointment booked: {booked} (simulated clinic API)"))
        steps.append(_step("Health Calendar", "ok", f"Added to calendar for {slot['date']}"))
    else:
        steps.append(_step("Auto-Booker", "skipped", "Specialty not recognized in the document — booking was not started"))

    # 4. Record + notify (single confirmation, no questions asked)
    action = {"action_id": uuid.uuid4().hex, "user_id": user_id, "doc_id": doc_id,
              "doc_title": doc.get("title", ""), "specialty": specialty, "booked_slot": booked,
              "steps": steps, "created_at": now}
    await db.jarvis_actions.insert_one(action.copy())
    try:
        from routes.swarm import bus_publish
        await bus_publish("jarvis.autopilot", "medical_sentinel",
                          {"doc_id": doc_id, "specialty": specialty, "booked": bool(booked)})
    except Exception:
        pass
    try:
        msg = f"Appointment booked: {booked}" if booked else f"Document „{doc.get('title', '')[:40]}“ processed and translated."
        await send_push(recipients=[user_id],
                        data={"title": "🧠 JARVIS AUTOPILOT", "message": msg, "action_url": "/health-timeline"})
    except Exception as e:
        logger.warning(f"autopilot push failed: {e}")
    return clean(action)


# ---------------- API ----------------
class AutopilotIn(BaseModel):
    enabled: bool

@api.put("/jarvis/autopilot")
async def set_autopilot(body: AutopilotIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"jarvis_autopilot": body.enabled}})
    return {"jarvis_autopilot": body.enabled}

@api.get("/jarvis/actions")
async def jarvis_actions(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    acts = await db.jarvis_actions.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(20)
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "jarvis_autopilot": 1})
    return {"autopilot": (fresh or {}).get("jarvis_autopilot", True), "actions": acts}

@api.post("/jarvis/orchestrate/{doc_id}")
async def orchestrate_now(doc_id: str, force: int = 0, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    doc = await db.documents.find_one({"doc_id": doc_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Doc not found")
    return await orchestrate_document(user["user_id"], doc_id, force=bool(force))


# ---------------- DAILY BRIEF (senior morning overview) ----------------
@api.get("/daily-brief")
async def daily_brief(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    horizon = (now + timedelta(days=3)).strftime("%Y-%m-%d")

    # Meds today (reminder schedule + intake status)
    reminders = await db.med_reminders.find({"user_id": uid}, {"_id": 0}).to_list(100)
    intakes = await db.med_intakes.find({"user_id": uid, "date": day}, {"_id": 0}).to_list(300)
    taken = {(i["reminder_id"], i["time"]) for i in intakes}
    meds = sorted(
        [{"reminder_id": r["reminder_id"], "name": r["name"], "dose": r["dose"], "time": tm,
          "taken": (r["reminder_id"], tm) in taken}
         for r in reminders for tm in r["times"]],
        key=lambda x: x["time"])

    # Calendar — today + next 3 days
    events = await db.calendar_events.find(
        {"user_id": uid, "date": {"$gte": day, "$lte": horizon}}, {"_id": 0}).sort("date", 1).to_list(20)
    events_today = [e for e in events if e["date"] == day]
    events_upcoming = [e for e in events if e["date"] > day]

    # Family — pending silent pings + emergency contact
    pending_pulse = await db.pulse_requests.find(
        {"target_user": uid, "status": {"$exists": False}}, {"_id": 0}).sort("created_at", -1).to_list(5)
    prof = await db.emergency_profiles.find_one({"user_id": uid}, {"_id": 0}) or {}

    # Recovery + GA-T + last autopilot action
    recovery = await db.recovery.find_one(
        {"user_id": uid}, {"_id": 0, "status": 1, "end_date": 1, "start_date": 1, "outings": 1})
    acct = await db.token_accounts.find_one({"user_id": uid}, {"_id": 0, "balance": 1})
    last_action = await db.jarvis_actions.find_one({"user_id": uid}, {"_id": 0}, sort=[("created_at", -1)])

    # Vaccination boosters due within 90 days (Health Calendar)
    horizon90 = (now + timedelta(days=90)).strftime("%Y-%m-%d")
    boosters = await db.calendar_events.find(
        {"user_id": uid, "category": "vaccine", "booster_due": {"$ne": None, "$lte": horizon90}},
        {"_id": 0, "title": 1, "booster_due": 1}).sort("booster_due", 1).to_list(5)

    return {
        "date": day, "name": (user.get("name") or "Guardian").split(" ")[0],
        "meds": {"items": meds, "pending": sum(1 for m in meds if not m["taken"])},
        "events_today": events_today, "events_upcoming": events_upcoming,
        "family": {"pending_pulse": pending_pulse,
                   "emergency_contact": prof.get("emergency_contact_name") or None},
        "recovery": recovery, "vaccine_boosters": boosters,
        "gat_balance": (acct or {}).get("balance", 0.0),
        "jarvis_last_action": last_action,
    }
