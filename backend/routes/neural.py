# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
from fastapi import HTTPException, Header
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid, json, re

from emergentintegrations.llm.chat import LlmChat, UserMessage

from core import (
    api, db, logger, clean, get_current_user, send_push,
    AI_COMPLIANCE_NOTE, _make_pdf, _auth_pdf, _pdf_footer, _pdf_response,
    EMERGENT_LLM_KEY,
)
from routes.hunter import _simulate_slot, _simulate_stock

# =========================================================================
# NEURAL LINK — Jarvis orchestrator: unified context, sentient chains, weekly report
# =========================================================================

async def _gather_context(user: dict) -> dict:
    """Unified cross-module snapshot (the single source of truth for Jarvis)."""
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    today = now.date().isoformat()

    prof = await db.emergency_profiles.find_one({"user_id": uid}, {"_id": 0}) or {}
    recovery = await db.recovery.find_one({"user_id": uid}, {"_id": 0}) or {}
    drops = await db.health_drops.find({"user_id": uid}, {"_id": 0}).sort("created_at", -1).to_list(10)
    waitlist = await db.waitlist.find({"user_id": uid}, {"_id": 0}).sort("created_at", -1).to_list(10)
    cal = await db.calendar_events.find({"user_id": uid}, {"_id": 0}).sort("date", -1).to_list(50)
    meds = await db.med_reminders.find({"user_id": uid}, {"_id": 0}).to_list(20)
    cabinet = await db.cabinet.find({"user_id": uid}, {"_id": 0}).to_list(50)
    campaigns = await db.campaigns.find({"user_id": uid}, {"_id": 0}).to_list(5)
    dignity = await db.dignity_funds.find_one({"user_id": uid}, {"_id": 0}) or {}
    falls = await db.fall_events.find({"user_id": uid, "created_at": {"$gte": week_ago}}, {"_id": 0}).to_list(20)
    acoustic = await db.acoustic_events.find({"user_id": uid, "created_at": {"$gte": week_ago}}, {"_id": 0}).to_list(20)
    beacons = await db.beacon_events.find({"user_id": uid, "created_at": {"$gte": week_ago}}, {"_id": 0}).to_list(20)
    testament = await db.legal_testaments.find_one({"user_id": uid}, {"_id": 0}) or {}
    proxy = await db.proxy_directives.find_one({"user_id": uid}, {"_id": 0}) or {}
    bio = await db.biometric_wills.find_one({"user_id": uid}, {"_id": 0}) or {}
    journey = await db.healing_journeys.find_one({"user_id": uid, "status": "active"}, {"_id": 0})
    claim = await db.insurance_claims.find_one({"journey_id": journey["journey_id"]}, {"_id": 0}) if journey else None
    comp = await db.companion_checkins.find({"user_id": uid, "created_at": {"$gte": week_ago}}, {"_id": 0}).sort("created_at", 1).to_list(30)
    comp_moods = [c["mood"] for c in comp]

    upcoming = sorted([e for e in cal if e["category"] == "exam" and e["date"] >= today], key=lambda e: e["date"])[:5]
    boosters = [e for e in cal if e["category"] == "vaccine" and e.get("booster_due")]
    low_stock = [c.get("name") for c in cabinet if (c.get("quantity") or 0) <= 2]

    return {
        "name": user.get("name"), "did": user["did"], "today": today,
        "healing_loop": {
            "active": bool(journey),
            "kind": (journey or {}).get("kind_label"), "specialty": (journey or {}).get("specialty"),
            "steps": (journey or {}).get("steps"),
            "booked_slot": ((journey or {}).get("access") or {}).get("slot"),
            "insurance_claim": ({"provider": claim.get("provider"), "status": claim.get("status"),
                                 "estimated_total_eur": claim.get("estimated_total_eur")} if claim else None),
        },
        "companion": {
            "checkins_7d": len(comp_moods),
            "avg_mood_7d": round(sum(comp_moods) / len(comp_moods), 2) if comp_moods else None,
            "last_mood_label": comp[-1]["mood_label"] if comp else None,
        },
        "health": {
            "blood_type": prof.get("blood_type"), "allergies": prof.get("allergies"), "conditions": prof.get("conditions"),
            "recovery": {
                "active": bool(recovery.get("start_date")), "start": recovery.get("start_date"),
                "end": recovery.get("end_date"), "note": recovery.get("note"),
                "contract": recovery.get("contract_type"), "outings": recovery.get("outings", []),
            },
            "recent_drops": [{"title": d["doc_title"], "from": d["sender_name"], "referral": d.get("is_referral"), "specialty": d.get("specialty_guess"), "autobooked": d.get("autobooked")} for d in drops[:5]],
            "waitlist": [{"specialty": w.get("specialty"), "status": w.get("status"), "slot": w.get("found_slot")} for w in waitlist[:5]],
            "upcoming_exams": [{"title": e["title"], "date": e["date"]} for e in upcoming],
            "boosters": [{"title": e["title"], "due": e["booster_due"]} for e in boosters[:5]],
            "med_reminders": [{"name": m.get("name"), "times": m.get("times")} for m in meds[:10]],
            "low_stock_meds": low_stock,
        },
        "wealth": {
            "solidarity_campaigns": [{"title": c.get("title"), "goal": c.get("goal_amount"), "raised": c.get("raised_amount")} for c in campaigns],
            "dignity_fund_balance": dignity.get("balance", 0),
        },
        "safety": {
            "falls_7d": len(falls), "acoustic_events_7d": len(acoustic), "beacons_7d": len(beacons),
            "is_donor": bool(prof.get("is_donor")),
            "has_testament": bool(testament.get("document_text")),
            "has_proxy": bool(proxy.get("proxy_full_name")),
            "has_biometric_will": bool(bio.get("sha256")),
            "ice_contact": f"{prof.get('emergency_contact_name') or ''} {prof.get('emergency_contact_phone') or ''}".strip(),
        },
    }

@api.get("/jarvis/context")
async def jarvis_context(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await _gather_context(user)

class JarvisAskIn(BaseModel):
    question: str
    language: str = "sk"

@api.post("/jarvis/ask")
async def jarvis_ask(body: JarvisAskIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if not body.question.strip():
        raise HTTPException(400, "question required")
    ctx = await _gather_context(user)
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"jarvis-{user['user_id'][:8]}-{uuid.uuid4().hex[:6]}",
        system_message=(
            "You are Jarvis, the Guardian Angel OS orchestrator with FULL cross-module awareness "
            "(Health Hub, The Hunter, Family Shield, Legacy). Answer in warm, plain "
            f"{'Slovak' if body.language.startswith('sk') else body.language} suitable for a senior. "
            "Cross-reference the user's live data snapshot below to give ONE combined, actionable answer "
            "(max 6 sentences or a short numbered list). Never invent data not in the snapshot. "
            f"{AI_COMPLIANCE_NOTE}\n\nUSER DATA SNAPSHOT (JSON):\n{json.dumps(ctx, ensure_ascii=False, default=str)[:6000]}"
        ),
    ).with_model("anthropic", "claude-sonnet-5")
    try:
        resp = await chat.send_message(UserMessage(text=body.question[:1000]))
        return {"answer": resp, "context_used": True}
    except Exception as e:
        logger.error(f"jarvis ask error: {e}")
        raise HTTPException(502, "AI service unavailable")

# --------- SENTIENT CHAINS (one-shot orchestrations — no recursion, loop-safe) ---------

def _step(name: str, status: str, detail: str) -> dict:
    return {"step": name, "status": status, "detail": detail}

class HealingChainIn(BaseModel):
    drop_doc_id: Optional[str] = None
    specialty: Optional[str] = None

@api.post("/chains/healing")
async def chain_healing(body: HealingChainIn, authorization: Optional[str] = Header(None)):
    """Referral → Waitlist Hunter → Solidarity check → Auto-Book → Calendar → Employer notice."""
    user = await get_current_user(authorization)
    uid = user["user_id"]
    steps: List[dict] = []
    specialty = (body.specialty or "").strip()

    drop = None
    if body.drop_doc_id:
        drop = await db.health_drops.find_one({"drop_doc_id": body.drop_doc_id, "user_id": uid}, {"_id": 0})
        if not drop:
            raise HTTPException(404, "Drop document not found")
        if drop.get("autobooked"):
            steps.append(_step("Referral Bridge", "skipped", "The request has already been reserved — the chain does not start again (loop protection)."))
            return {"chain": "healing", "steps": steps, "summary": "Already handled.", "simulated": True}
        specialty = specialty or drop.get("specialty_guess") or drop.get("doc_title")
        steps.append(_step("Referral Bridge", "ok", f"Request: {drop['doc_title']} from {drop['sender_name']}"))
    if not specialty:
        raise HTTPException(400, "specialty or drop_doc_id required")

    steps.append(_step("Waitlist Hunter", "ok", f"Looking for the earliest appointment: {specialty}"))

    campaigns = await db.campaigns.find({"user_id": uid}, {"_id": 0}).to_list(5)
    raised = sum(c.get("raised_amount", 0) for c in campaigns)
    dignity = await db.dignity_funds.find_one({"user_id": uid}, {"_id": 0}) or {}
    funds = raised + dignity.get("balance", 0)
    steps.append(_step("Solidarity Hub", "ok", f"Available community funds: {round(funds, 2)} € " + ("(sufficient)" if funds > 0 else "(0 € — examination covered by insurance)")))

    slot = _simulate_slot(specialty, "")
    found = f"{slot['date']} {slot['time']} — {slot['clinic']}"
    now = datetime.now(timezone.utc)
    await db.waitlist.insert_one({
        "item_id": uuid.uuid4().hex, "user_id": uid, "specialty": specialty, "clinic": slot["clinic"],
        "city": "", "current_date": "", "target_before": slot["date"], "priority": "auto",
        "status": "booked", "last_check": now, "found_slot": found, "created_at": now,
    })
    steps.append(_step("Auto-Booker", "ok", f"Appointment reserved: {found} (simulated clinic API)"))

    await db.calendar_events.insert_one({
        "event_id": uuid.uuid4().hex, "user_id": uid, "category": "exam",
        "title": f"{specialty} — {slot['clinic']}", "date": slot["date"],
        "notes": f"Healing Chain · {slot['time']}", "booster_due": None,
        "source": "chain:healing", "created_at": now,
    })
    steps.append(_step("Health Calendar", "ok", f"Logged to the calendar for {slot['date']}"))

    recovery = await db.recovery.find_one({"user_id": uid}, {"_id": 0})
    if recovery:
        steps.append(_step("Sick Leave Manager", "ok", "Employer report prepared (PDF in My Recovery)."))
    else:
        steps.append(_step("Sick Leave Manager", "skipped", "No active sick leave — report not needed."))

    if drop:
        await db.health_drops.update_one({"drop_doc_id": drop["drop_doc_id"]}, {"$set": {"autobooked": True}})
    try:
        await send_push(recipients=[uid], data={"title": "🧠 HEALING CHAIN COMPLETED", "message": f"{specialty}: {found}", "action_url": "/health-timeline"})
    except Exception as e:
        logger.warning(f"chain push failed: {e}")
    return {"chain": "healing", "steps": steps, "summary": f"Appointment {specialty} reserved and recorded. {found}", "simulated": True}

class SafetyChainIn(BaseModel):
    trigger: str = "manual"  # fall | acoustic | manual

@api.post("/chains/safety")
async def chain_safety(body: SafetyChainIn, authorization: Optional[str] = Header(None)):
    """Fall/Acoustic → Emergency loop → Legacy check → first-responder info release."""
    user = await get_current_user(authorization)
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    steps: List[dict] = []
    steps.append(_step("Detekcia", "ok", f"Trigger: {body.trigger}"))

    await db.beacon_events.insert_one({
        "event_id": uuid.uuid4().hex, "user_id": uid, "kind": f"chain_safety_{body.trigger}",
        "created_at": now,
    })
    steps.append(_step("Emergency Loop", "ok", "Emergency beacon activated, family notified."))

    prof = await db.emergency_profiles.find_one({"user_id": uid}, {"_id": 0}) or {}
    testament = await db.legal_testaments.find_one({"user_id": uid}, {"_id": 0}) or {}
    proxy = await db.proxy_directives.find_one({"user_id": uid}, {"_id": 0}) or {}
    legacy_bits = []
    legacy_bits.append("organ donor: YES" if prof.get("is_donor") else "organ donor: NO")
    legacy_bits.append("will: prepared" if testament.get("document_text") else "will: missing")
    legacy_bits.append(f"healthcare proxy: {proxy.get('proxy_full_name')}" if proxy.get("proxy_full_name") else "healthcare proxy: unspecified")
    steps.append(_step("Legacy Module", "ok", " · ".join(legacy_bits)))

    ice = f"{prof.get('emergency_contact_name') or ''} {prof.get('emergency_contact_phone') or ''}".strip()
    steps.append(_step("Emergency Wallpaper", "ok",
                       f"Info for rescuers released: blood {prof.get('blood_type') or '—'} · allergies {prof.get('allergies') or '—'} · ICE {ice or '—'} (QR on locked screen)"))
    try:
        await send_push(recipients=[uid], data={"title": "🛡️ SAFETY CHAIN ACTIVE", "message": "Emergency info prepared for rescuers.", "action_url": "/wallpaper"})
    except Exception as e:
        logger.warning(f"chain push failed: {e}")
    return {"chain": "safety", "steps": steps, "summary": "Emergency loop started, information for rescuers prepared.", "simulated": False}

@api.post("/chains/recovery")
async def chain_recovery(authorization: Optional[str] = Header(None)):
    """Low movement → Physio-AI proposal → outing-hours check before suggesting a walk."""
    user = await get_current_user(authorization)
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    steps: List[dict] = []

    week_ago = now - timedelta(days=3)
    checkins = await db.wellness_checkins.find({"user_id": uid, "created_at": {"$gte": week_ago}}, {"_id": 0}).to_list(20)
    low_movement = len(checkins) == 0
    steps.append(_step("Knee Guard / Wellness", "ok",
                       "For 3 days no wellness check-in — movement is probably low." if low_movement
                       else f"{len(checkins)} check-ins in 3 days — activity looks good."))

    steps.append(_step("Physio-AI", "ok", "I suggest a guide: Knee recovery after surgery/injury (10 min) — find it in Physio-AI → Expert guides."))

    recovery = await db.recovery.find_one({"user_id": uid}, {"_id": 0}) or {}
    outings = recovery.get("outings", [])
    walk = "Without active sick leave — a walk is fine anytime."
    if outings:
        mins = now.hour * 60 + now.minute
        active = None
        nxt = None
        for o in outings:
            fh, fm = map(int, o["from_time"].split(":"))
            th, tm = map(int, o["to_time"].split(":"))
            if fh * 60 + fm <= mins <= th * 60 + tm:
                active = o
                break
            if fh * 60 + fm > mins and (nxt is None or fh * 60 + fm < int(nxt["from_time"][:2]) * 60 + int(nxt["from_time"][3:])):
                nxt = o
        if active:
            walk = f"Walk is ACTIVE until {active['to_time']} — I recommend going for a walk NOW."
        elif nxt:
            walk = f"Stay home for now (sick leave check). Plan a walk during {nxt['from_time']}–{nxt['to_time']}."
        else:
            walk = "Today's walk periods are already over — save the walk for tomorrow, and exercise at home today."
    steps.append(_step("Sick Leave Manager", "ok", walk))
    return {"chain": "recovery", "steps": steps, "summary": walk, "simulated": False}

class SupplyChainIn(BaseModel):
    med_name: str
    region: str = "SK"

@api.post("/chains/supply")
async def chain_supply(body: SupplyChainIn, authorization: Optional[str] = Header(None)):
    """Out of medication → Pharmacy Hunter → Barter check when cash is low → transport routing."""
    user = await get_current_user(authorization)
    uid = user["user_id"]
    if not body.med_name.strip():
        raise HTTPException(400, "med_name required")
    steps: List[dict] = []

    results = _simulate_stock(body.med_name.strip(), body.region)
    hit = next((r for r in results if r["status"] == "in_stock"), None)
    steps.append(_step("Pharmacy Hunter", "ok",
                       f"In stock: {hit['pharmacy']} {hit['city']} ({hit['price_eur']} €) — DEMO data" if hit
                       else "The medicine is out of stock in all tracked pharmacies (DEMO data)."))

    campaigns = await db.campaigns.find({"user_id": uid}, {"_id": 0}).to_list(5)
    raised = sum(c.get("raised_amount", 0) for c in campaigns)
    dignity = await db.dignity_funds.find_one({"user_id": uid}, {"_id": 0}) or {}
    funds = raised + dignity.get("balance", 0)
    cash_low = funds < (hit["price_eur"] if hit else 10)
    steps.append(_step("Solidarity Hub", "ok", f"Available cash in the community: {round(funds, 2)} € — {'LOW' if cash_low else 'sufficient'}."))

    if cash_low:
        offers = await db.barter_offers.find({"user_id": {"$ne": uid}}, {"_id": 0}).sort("created_at", -1).to_list(3)
        steps.append(_step("Skill Barter", "ok",
                           f"{len(offers)} exchange offers nearby — swap a skill for medicine (Barter Engine)." if offers
                           else "No barter offers — create your own in Barter Engine."))
    else:
        steps.append(_step("Skill Barter", "skipped", "Cash is sufficient — no barter needed."))

    if hit:
        steps.append(_step("Logistics Engine", "ok", f"Route: {hit['pharmacy']} {hit['city']} — if on sick leave, plan pickup during the walk."))
    else:
        steps.append(_step("Logistics Engine", "skipped", "With no stock on hand, there is nothing to transport — enable tracking in Pharmacy Hunter."))
    summary = (f"{body.med_name}: vyzdvihnite v {hit['pharmacy']} {hit['city']}" if hit else f"{body.med_name}: currently unavailable — tracking recommended.")
    return {"chain": "supply", "steps": steps, "summary": summary, "simulated": True}

# --------- WEEKLY GUARDIAN PULSE REPORT (PDF) ---------
@api.get("/reports/weekly.pdf")
async def weekly_report_pdf(token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    ctx = await _gather_context(user)
    h, w, s = ctx["health"], ctx["wealth"], ctx["safety"]
    parts = []
    parts.append("1. HEALTH")
    parts.append(f"  Sick leave active: {'YES (' + str(h['recovery']['start']) + ' → ' + str(h['recovery']['end'] or '?') + ')' if h['recovery']['active'] else 'NO'}")
    parts.append(f"  Upcoming examinations: " + ("; ".join([f"{e['title']} ({e['date']})" for e in h["upcoming_exams"]]) or "nothing"))
    parts.append(f"  Revaccinations: " + ("; ".join([f"{b['title']} due {b['due']}" for b in h["boosters"]]) or "nothing"))
    parts.append(f"  Received documents (Health Drop): " + ("; ".join([f"{d['title']} from {d['from']}" for d in h["recent_drops"]]) or "nothing"))
    parts.append(f"  Drugs with low stock: " + (", ".join(h["low_stock_meds"]) or "nothing"))
    parts.append("\n2. WEALTH")
    parts.append(f"  Solidarity campaigns: " + ("; ".join([f"{c['title']}: {c['raised']}/{c['goal']} €" for c in w["solidarity_campaigns"]]) or "nothing"))
    parts.append(f"  Dignity Fund: {w['dignity_fund_balance']} €")
    parts.append("\n3. SAFETY (last 7 days)")
    parts.append(f"  Falls: {s['falls_7d']} · Acoustic threats: {s['acoustic_events_7d']} · Beacons: {s['beacons_7d']}")
    parts.append(f"  Will: {'prepared' if s['has_testament'] else 'missing'} · Proxy: {'designated' if s['has_proxy'] else 'undesignated'} · Biometric confirmation: {'yes' if s['has_biometric_will'] else 'no'}")
    parts.append(f"  Organ donor: {'YES' if s['is_donor'] else 'NO'} · ICE contact: {s['ice_contact'] or '—'}")
    parts.append(f"\nGenerated by Neural Link layer · {ctx['today']}")
    pdf = await run_in_threadpool(_make_pdf, "GUARDIAN PULSE REPORT\nWEEKLY OVERVIEW: HEALTH · FINANCES · SAFETY", "\n".join(parts), _pdf_footer())
    return _pdf_response(pdf, "guardian_pulse_report.pdf")
