# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Active Guardian Engine — 'Jarvis Suggests' proactive recommendation feed.
Rule-based, data-driven, personalized across the 4 pillars (Wealth / Health /
Safety / Hunter). Every recommendation carries an actionable deep-link."""
from fastapi import Header
from typing import Optional
from datetime import datetime, timezone, timedelta
import hashlib

from core import api, db, get_current_user
from routes.hunter import _simulate_slot
from routes.insurance import _policy_status

TRAVEL_COST = {"Brno": 28, "Wien": 35, "Praha": 45, "Budapest": 39, "Kraków": 42}

def _rec(pillar: str, icon: str, title: str, detail: str, action: str, route: str) -> dict:
    rid = hashlib.sha256(f"{pillar}|{title}".encode()).hexdigest()[:12]
    return {"rec_id": rid, "pillar": pillar, "icon": icon, "title": title,
            "detail": detail, "action_label": action, "action_route": route}


@api.get("/recommendations")
async def recommendations(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    recs = []

    # ---------- WEALTH SENTINEL ----------
    pols = await db.insurance_policies.find({"user_id": uid}, {"_id": 0}).to_list(50)
    overdue = [p for p in pols if _policy_status(p) == "overdue"]
    if overdue:
        p = overdue[0]
        recs.append(_rec("wealth", "shield-outline",
                         f"Poistka {p['provider']} je po splatnosti",
                         "Hrozí zánik krytia. Zaplaťte poistné alebo si vezmite mikro-pôžičku zo Solidarity Hubu, aby poistka nezanikla.",
                         "VYRIEŠIŤ TERAZ", "/insurance"))
        recs.append(_rec("wealth", "people-outline",
                         "Mikro-pôžička zo Solidarity Hubu",
                         f"Komunita môže preklenúť poistné ({p.get('premium_monthly', 0)} {p.get('currency', 'EUR')}/mes.), kým sa postavíte na nohy.",
                         "POŽIADAŤ", "/solidarity"))
    elif not pols:
        recs.append(_rec("wealth", "shield-outline",
                         "Insurance Guard je prázdny",
                         "Povedzte Jarvisovi: „Zdravotné poistenie mám v Dôvere, zaplatené do decembra“ — záznam sa vytvorí sám.",
                         "PRIDAŤ POISTKU", "/insurance"))
    fund = await db.dignity_funds.find_one({"user_id": uid}, {"_id": 0, "balance": 1})
    if fund and fund.get("balance", 0) >= 100:
        recs.append(_rec("wealth", "trending-up-outline",
                         f"Fond dôstojnosti: {fund['balance']:.0f} € stojí bez úroku",
                         "Wealth Advisor: časť fondu môže kryť ročné poistné pre blízkeho — porovnajte možnosti.",
                         "POZRIEŤ FOND", "/dignity"))

    # ---------- HEALTH SENTINEL ----------
    last_act = await db.jarvis_actions.find_one({"user_id": uid, "specialty": {"$ne": None}},
                                                {"_id": 0}, sort=[("created_at", -1)])
    if last_act:
        spec = (last_act.get("specialty") or "").lower()
        guide = "spine"
        if "ortop" in spec or "fyzio" in spec:
            guide = "knee"
        recs.append(_rec("health", "fitness-outline",
                         f"Physio-AI plán pre: {last_act['specialty']}",
                         f"Na základe dokumentu „{last_act.get('doc_title', '')[:40]}“ odporúčam dnešnú rutinu z Global Encyclopedia (sprievodca: {guide}).",
                         "ZAČAŤ CVIČIŤ", "/physio"))
    year_ago = (now - timedelta(days=365)).strftime("%Y-%m-%d")
    exams = await db.calendar_events.count_documents({"user_id": uid, "category": "exam", "date": {"$gte": year_ago}})
    if exams == 0:
        recs.append(_rec("health", "medkit-outline",
                         "Rok bez preventívnej prehliadky",
                         "Health Sentinel: naplánujte preventívku (krv, tlak, zrak). Waitlist Hunter ju vie ustrážiť za vás.",
                         "NAPLÁNOVAŤ", "/(tabs)/hunter"))
    reminders = await db.med_reminders.find({"user_id": uid}, {"_id": 0}).to_list(50)
    if reminders:
        intakes = await db.med_intakes.count_documents({"user_id": uid, "date": today})
        slots = sum(len(r["times"]) for r in reminders)
        if intakes < slots:
            recs.append(_rec("health", "medical-outline",
                             f"Lieky dnes: {slots - intakes} dávok čaká",
                             "Denný prehľad ukáže, čo ešte treba užiť — ťuknutím potvrdíte.",
                             "OTVORIŤ PREHĽAD", "/daily-brief"))

    # ---------- SAFETY SENTINEL ----------
    stale_pulse = await db.pulse_requests.find_one(
        {"from_user": uid, "status": {"$exists": False},
         "created_at": {"$lte": now - timedelta(hours=24)}}, {"_id": 0})
    week_ago = now - timedelta(days=7)
    recent_pulse = await db.pulse_requests.count_documents({"from_user": uid, "created_at": {"$gte": week_ago}})
    if stale_pulse:
        recs.append(_rec("safety", "heart-circle-outline",
                         "Tichý ping bez odpovede 24 h",
                         "Safety Sentinel: odporúčam zavolať alebo navštíviť. Bez odozvy eskalujte cez Family Shield.",
                         "SKONTROLOVAŤ", "/pulse-check"))
    elif recent_pulse == 0:
        recs.append(_rec("safety", "heart-outline",
                         "Týždeň bez kontroly blízkych",
                         "Pošlite tichý ping — jedno ťuknutie pre nich, veľký pokoj pre vás.",
                         "POSLAŤ PING", "/pulse-check"))
    soon = (now + timedelta(days=30)).strftime("%Y-%m-%d")
    expiring = await db.cabinet.count_documents(
        {"user_id": uid, "expires_on": {"$ne": None, "$lte": soon, "$gte": today}})
    if expiring:
        recs.append(_rec("safety", "cube-outline",
                         f"Rotácia zásob: {expiring} položiek expiruje do 30 dní",
                         "Prepper's Guard: spotrebujte a doplňte skôr, než prepadnú — lekárnička aj bunker.",
                         "OTVORIŤ SKLAD", "/medicine-cabinet"))

    # ---------- HUNTER STRATEGIST ----------
    matched_news = None
    try:
        from routes.news import ensure_news_seed, _user_keywords
        await ensure_news_seed()
        corpus = await _user_keywords(uid)
        if corpus.strip():
            for n in await db.medical_news.find({}, {"_id": 0}).to_list(50):
                if any(tg in corpus for tg in n["tags"]):
                    matched_news = n
                    break
    except Exception:
        pass
    if matched_news:
        recs.append(_rec("hunter", "flask-outline",
                         f"Prelom: {matched_news['title'][:48]}",
                         f"{matched_news['summary'][:110]} {matched_news['savings_note']}",
                         "ULOVIŤ TERMÍN", "/medical-news"))
    wl = await db.waitlist.find_one({"user_id": uid, "status": {"$nin": ["booked", "found"]}},
                                    {"_id": 0}, sort=[("created_at", -1)])
    if wl:
        alt_city = "Brno" if (wl.get("city") or "").lower() != "brno" else "Wien"
        slot = _simulate_slot(wl.get("specialty", ""), alt_city)
        cost = TRAVEL_COST.get(alt_city, 30)
        recs.append(_rec("hunter", "navigate-outline",
                         f"Stratég: {wl.get('specialty', 'Termín')} v {alt_city} skôr",
                         f"Cost-benefit: {alt_city} {slot['date']} vs. čakanie doma ~6 mes. Cesta ~{cost} € — mesiace zdravia sú viac.",
                         "ZVÁŽIŤ REZERVÁCIU", "/(tabs)/hunter"))
        # Jarvis proactive upsell — Sentinel tier books it autonomously
        from routes.subscription import current_tier, TIER_RANK
        fresh = await db.users.find_one({"user_id": uid}, {"_id": 0, "tier": 1, "tier_until": 1}) or {}
        if TIER_RANK.get(current_tier(fresh), 0) < TIER_RANK["sentinel"]:
            recs.append(_rec("wealth", "rocket-outline",
                             "Našiel som lovený termín — Sentinel ho zarezervuje sám",
                             "Upgrade na Sentinel Tier (€149/mes.): autonómne rezervácie, satelitná núdza, Bio-Scanner a Tactical Medic.",
                             "UPGRADE", "/subscription"))
    ins = await db.insurance_policies.find({"user_id": uid, "type": "health"}, {"_id": 0}).to_list(5)
    if ins and not any(_policy_status(p) == "paid" for p in ins):
        recs.append(_rec("hunter", "warning-outline",
                         "Hunter: rezervácie ohrozené poistkou",
                         "Zdravotná poistka nie je aktívna — zmluvní lekári môžu rezerváciu odmietnuť. Vyriešte poistku pred lovom termínov.",
                         "SKONTROLOVAŤ POISTKU", "/insurance"))

    # ---------- VALUE ADVISOR (Upsell Neural Logic) ----------
    from routes.subscription import current_tier as _ct, TIER_RANK as _tr
    fresh_tier = await db.users.find_one({"user_id": uid}, {"_id": 0, "tier": 1, "tier_until": 1}) or {}
    if _tr.get(_ct(fresh_tier), 0) < _tr["sentinel"]:
        ctx = ""
        if matched_news:
            ctx = f"Čítali ste o „{matched_news['title'][:38]}…“ — "
        elif last_act:
            ctx = f"Po dokumente „{(last_act.get('doc_title') or '')[:32]}…“ — "
        recs.append(_rec("wealth", "pulse-outline",
                         "Value Advisor: skontrolujte vitálne funkcie",
                         f"{ctx}Bio-Scanner zmeria tep, SpO2 a stres kamerou za 5 GA-T. Alebo Sentinel (€149/mes.) = neobmedzený monitoring + satelit + Tactical Medic.",
                         "SKÚSIŤ BIO-SCAN", "/bioscan"))

    return {"generated_at": now.isoformat(), "count": len(recs), "recommendations": recs}
