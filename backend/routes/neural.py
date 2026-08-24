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

    upcoming = sorted([e for e in cal if e["category"] == "exam" and e["date"] >= today], key=lambda e: e["date"])[:5]
    boosters = [e for e in cal if e["category"] == "vaccine" and e.get("booster_due")]
    low_stock = [c.get("name") for c in cabinet if (c.get("quantity") or 0) <= 2]

    return {
        "name": user.get("name"), "did": user["did"], "today": today,
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
            steps.append(_step("Referral Bridge", "skipped", "Žiadanka už bola zarezervovaná — reťaz sa nespúšťa znova (ochrana proti slučke)."))
            return {"chain": "healing", "steps": steps, "summary": "Už vybavené.", "simulated": True}
        specialty = specialty or drop.get("specialty_guess") or drop.get("doc_title")
        steps.append(_step("Referral Bridge", "ok", f"Žiadanka: {drop['doc_title']} od {drop['sender_name']}"))
    if not specialty:
        raise HTTPException(400, "specialty or drop_doc_id required")

    steps.append(_step("Waitlist Hunter", "ok", f"Hľadám najskorší termín: {specialty}"))

    campaigns = await db.campaigns.find({"user_id": uid}, {"_id": 0}).to_list(5)
    raised = sum(c.get("raised_amount", 0) for c in campaigns)
    dignity = await db.dignity_funds.find_one({"user_id": uid}, {"_id": 0}) or {}
    funds = raised + dignity.get("balance", 0)
    steps.append(_step("Solidarity Hub", "ok", f"Dostupné komunitné prostriedky: {round(funds, 2)} € " + ("(dostatočné)" if funds > 0 else "(0 € — vyšetrenie kryje poisťovňa)")))

    slot = _simulate_slot(specialty, "")
    found = f"{slot['date']} {slot['time']} — {slot['clinic']}"
    now = datetime.now(timezone.utc)
    await db.waitlist.insert_one({
        "item_id": uuid.uuid4().hex, "user_id": uid, "specialty": specialty, "clinic": slot["clinic"],
        "city": "", "current_date": "", "target_before": slot["date"], "priority": "auto",
        "status": "booked", "last_check": now, "found_slot": found, "created_at": now,
    })
    steps.append(_step("Auto-Booker", "ok", f"Termín zarezervovaný: {found} (simulované API kliniky)"))

    await db.calendar_events.insert_one({
        "event_id": uuid.uuid4().hex, "user_id": uid, "category": "exam",
        "title": f"{specialty} — {slot['clinic']}", "date": slot["date"],
        "notes": f"Healing Chain · {slot['time']}", "booster_due": None,
        "source": "chain:healing", "created_at": now,
    })
    steps.append(_step("Health Calendar", "ok", f"Zapísané do kalendára na {slot['date']}"))

    recovery = await db.recovery.find_one({"user_id": uid}, {"_id": 0})
    if recovery:
        steps.append(_step("Sick Leave Manager", "ok", "Hlásenie pre zamestnávateľa pripravené (PDF v Mojom zotavení)."))
    else:
        steps.append(_step("Sick Leave Manager", "skipped", "Žiadna aktívna PN — hlásenie netreba."))

    if drop:
        await db.health_drops.update_one({"drop_doc_id": drop["drop_doc_id"]}, {"$set": {"autobooked": True}})
    try:
        await send_push(recipients=[uid], data={"title": "🧠 HEALING CHAIN DOKONČENÁ", "message": f"{specialty}: {found}", "action_url": "/health-timeline"})
    except Exception as e:
        logger.warning(f"chain push failed: {e}")
    return {"chain": "healing", "steps": steps, "summary": f"Termín {specialty} zarezervovaný a zapísaný. {found}", "simulated": True}

class SafetyChainIn(BaseModel):
    trigger: str = "manual"  # fall | acoustic | manual

@api.post("/chains/safety")
async def chain_safety(body: SafetyChainIn, authorization: Optional[str] = Header(None)):
    """Fall/Acoustic → Emergency loop → Legacy check → first-responder info release."""
    user = await get_current_user(authorization)
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    steps: List[dict] = []
    steps.append(_step("Detekcia", "ok", f"Spúšťač: {body.trigger}"))

    await db.beacon_events.insert_one({
        "event_id": uuid.uuid4().hex, "user_id": uid, "kind": f"chain_safety_{body.trigger}",
        "created_at": now,
    })
    steps.append(_step("Emergency Loop", "ok", "Núdzový maják aktivovaný, rodina notifikovaná."))

    prof = await db.emergency_profiles.find_one({"user_id": uid}, {"_id": 0}) or {}
    testament = await db.legal_testaments.find_one({"user_id": uid}, {"_id": 0}) or {}
    proxy = await db.proxy_directives.find_one({"user_id": uid}, {"_id": 0}) or {}
    legacy_bits = []
    legacy_bits.append("darca orgánov: ÁNO" if prof.get("is_donor") else "darca orgánov: NIE")
    legacy_bits.append("závet: pripravený" if testament.get("document_text") else "závet: chýba")
    legacy_bits.append(f"splnomocnenec: {proxy.get('proxy_full_name')}" if proxy.get("proxy_full_name") else "splnomocnenec: neurčený")
    steps.append(_step("Legacy Module", "ok", " · ".join(legacy_bits)))

    ice = f"{prof.get('emergency_contact_name') or ''} {prof.get('emergency_contact_phone') or ''}".strip()
    steps.append(_step("Emergency Wallpaper", "ok",
                       f"Info pre záchranárov uvoľnené: krv {prof.get('blood_type') or '—'} · alergie {prof.get('allergies') or '—'} · ICE {ice or '—'} (QR na zamknutej obrazovke)"))
    try:
        await send_push(recipients=[uid], data={"title": "🛡️ SAFETY CHAIN AKTÍVNA", "message": "Núdzové info pripravené pre záchranárov.", "action_url": "/wallpaper"})
    except Exception as e:
        logger.warning(f"chain push failed: {e}")
    return {"chain": "safety", "steps": steps, "summary": "Núdzová slučka spustená, informácie pre záchranárov pripravené.", "simulated": False}

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
                       "Za 3 dni žiadny wellness check-in — pohyb je pravdepodobne nízky." if low_movement
                       else f"{len(checkins)} check-inov za 3 dni — aktivita v poriadku."))

    steps.append(_step("Physio-AI", "ok", "Navrhujem sprievodcu: Obnova kolena po operácii/úraze (10 min) — nájdete v Physio-AI → Expertní sprievodcovia."))

    recovery = await db.recovery.find_one({"user_id": uid}, {"_id": 0}) or {}
    outings = recovery.get("outings", [])
    walk = "Bez aktívnej PN — prechádzka je kedykoľvek v poriadku."
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
            walk = f"Vychádzka je AKTÍVNA do {active['to_time']} — prechádzku odporúčam TERAZ."
        elif nxt:
            walk = f"Teraz ostaňte doma (kontrola PN). Prechádzku plánujte na vychádzku {nxt['from_time']}–{nxt['to_time']}."
        else:
            walk = "Dnešné vychádzky už skončili — prechádzku nechajte na zajtra, dnes cvičte doma."
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
                       f"Skladom: {hit['pharmacy']} {hit['city']} ({hit['price_eur']} €) — DEMO dáta" if hit
                       else "Liek nie je skladom v žiadnej sledovanej lekárni (DEMO dáta)."))

    campaigns = await db.campaigns.find({"user_id": uid}, {"_id": 0}).to_list(5)
    raised = sum(c.get("raised_amount", 0) for c in campaigns)
    dignity = await db.dignity_funds.find_one({"user_id": uid}, {"_id": 0}) or {}
    funds = raised + dignity.get("balance", 0)
    cash_low = funds < (hit["price_eur"] if hit else 10)
    steps.append(_step("Solidarity Hub", "ok", f"Dostupná hotovosť v komunite: {round(funds, 2)} € — {'NÍZKA' if cash_low else 'postačuje'}."))

    if cash_low:
        offers = await db.barter_offers.find({"user_id": {"$ne": uid}}, {"_id": 0}).sort("created_at", -1).to_list(3)
        steps.append(_step("Skill Barter", "ok",
                           f"{len(offers)} výmenné ponuky v okolí — vymeňte zručnosť za liek (Barter Engine)." if offers
                           else "Žiadne barter ponuky — vytvorte vlastnú v Barter Engine."))
    else:
        steps.append(_step("Skill Barter", "skipped", "Hotovosť postačuje — barter netreba."))

    if hit:
        steps.append(_step("Logistics Engine", "ok", f"Trasa: {hit['pharmacy']} {hit['city']} — pri PN naplánujte vyzdvihnutie počas vychádzky."))
    else:
        steps.append(_step("Logistics Engine", "skipped", "Bez skladovej zásoby niet čo prepraviť — nastavte sledovanie v Pharmacy Hunter."))
    summary = (f"{body.med_name}: vyzdvihnite v {hit['pharmacy']} {hit['city']}" if hit else f"{body.med_name}: momentálne nedostupný — sledovanie odporúčané.")
    return {"chain": "supply", "steps": steps, "summary": summary, "simulated": True}

# --------- WEEKLY GUARDIAN PULSE REPORT (PDF) ---------
@api.get("/reports/weekly.pdf")
async def weekly_report_pdf(token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    ctx = await _gather_context(user)
    h, w, s = ctx["health"], ctx["wealth"], ctx["safety"]
    parts = []
    parts.append("1. ZDRAVIE / HEALTH")
    parts.append(f"  PN aktívna: {'ÁNO (' + str(h['recovery']['start']) + ' → ' + str(h['recovery']['end'] or '?') + ')' if h['recovery']['active'] else 'NIE'}")
    parts.append(f"  Nadchádzajúce vyšetrenia: " + ("; ".join([f"{e['title']} ({e['date']})" for e in h["upcoming_exams"]]) or "žiadne"))
    parts.append(f"  Preočkovania: " + ("; ".join([f"{b['title']} do {b['due']}" for b in h["boosters"]]) or "žiadne"))
    parts.append(f"  Prijaté dokumenty (Health Drop): " + ("; ".join([f"{d['title']} od {d['from']}" for d in h["recent_drops"]]) or "žiadne"))
    parts.append(f"  Lieky s nízkou zásobou: " + (", ".join(h["low_stock_meds"]) or "žiadne"))
    parts.append("\n2. FINANCIE / WEALTH")
    parts.append(f"  Solidarity kampane: " + ("; ".join([f"{c['title']}: {c['raised']}/{c['goal']} €" for c in w["solidarity_campaigns"]]) or "žiadne"))
    parts.append(f"  Fond dôstojnosti: {w['dignity_fund_balance']} €")
    parts.append("\n3. BEZPEČNOSŤ / SAFETY (posledných 7 dní)")
    parts.append(f"  Pády: {s['falls_7d']} · Akustické hrozby: {s['acoustic_events_7d']} · Majáky: {s['beacons_7d']}")
    parts.append(f"  Závet: {'pripravený' if s['has_testament'] else 'chýba'} · Splnomocnenec: {'určený' if s['has_proxy'] else 'neurčený'} · Biometrické potvrdenie: {'áno' if s['has_biometric_will'] else 'nie'}")
    parts.append(f"  Darca orgánov: {'ÁNO' if s['is_donor'] else 'NIE'} · ICE kontakt: {s['ice_contact'] or '—'}")
    parts.append(f"\nVygenerované Neural Link vrstvou · {ctx['today']}")
    pdf = await run_in_threadpool(_make_pdf, "GUARDIAN PULSE REPORT\nTÝŽDENNÝ PREHĽAD: ZDRAVIE · FINANCIE · BEZPEČNOSŤ", "\n".join(parts), _pdf_footer())
    return _pdf_response(pdf, "guardian_pulse_report.pdf")
