# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Medical News Sentinel — personalized medical-breakthrough intelligence.

Curated feed (simulated real-time ingestion — Phase 3: live RSS/clinical-trial
APIs) cross-referenced with the user's Vault. Regional CZ/SK Tech-Tracker for
robotic surgery & 3D dental printing. Health-economics link into Wealth Advisor."""
from fastapi import HTTPException, Header
from typing import Optional
from datetime import datetime, timezone
import uuid

from core import api, db, clean, get_current_user

# Curated breakthrough database (seeded; refreshed by the swarm news agent)
NEWS_SEED = [
    {"news_id": "n-knee-cartilage", "tags": ["ortop", "koleno", "knee", "kĺb", "gonartr", "chrupavk"],
     "title": "Stanford: regenerácia kolennej chrupavky bez operácie",
     "summary": "Nová injekčná terapia (ACI 3.0) obnovuje chrupavku pri gonartróze. Podobnú technológiu nasadzuje robotická klinika v Brne.",
     "region": "CZ", "tech": "regenerative", "specialty": "Ortopédia", "hunt_city": "Brno",
     "savings_note": "Oproti TEP kolena úspora ~4 200 € a 6 mesiacov rekonvalescencie.", "savings_eur": 4200,
     "source": "Stanford Medicine · Nature Regen. Med. (2026)"},
    {"news_id": "n-veins-laser", "tags": ["žil", "zil", "varix", "varikóz", "varikoz", "cievn", "vein"],
     "title": "30-minútový laser na kŕčové žily už aj v Bratislave",
     "summary": "Endovenózna laserová ablácia novej generácie — ambulantne, bez celkovej anestézy, návrat do práce na druhý deň.",
     "region": "SK", "tech": "laser", "specialty": "Cievna chirurgia", "hunt_city": "Bratislava",
     "savings_note": "Bez hospitalizácie: úspora ~900 € a 2 týždne PN.", "savings_eur": 900,
     "source": "EuroVein Congress 2026"},
    {"news_id": "n-dental-3d", "tags": ["zub", "dental", "korunk", "implant"],
     "title": "3D tlač zubných koruniek za 30 minút (CZ/SK siete)",
     "summary": "Vysokorýchlostná keramická 3D tlač priamo v ambulancii — korunka na jedno sedenie namiesto 2–3 návštev.",
     "region": "CZ/SK", "tech": "dental_3d", "specialty": "Stomatológia", "hunt_city": "Praha",
     "savings_note": "Jedno sedenie namiesto troch: úspora ~350 € + cestovné.", "savings_eur": 350,
     "source": "3Shape / Dental Summit Praha 2026"},
    {"news_id": "n-davinci-sk", "tags": ["prostat", "urol", "onko", "nádor", "nador", "chirurg"],
     "title": "Tech-Tracker: DaVinci Xi rozšírený v Banskej Bystrici a Martine",
     "summary": "Robotická chirurgia (urológia, onkogynekológia) — o 40 % kratšia rekonvalescencia. Poisťovne SK ju už preplácajú.",
     "region": "SK", "tech": "robotic_surgery", "specialty": "Urológia", "hunt_city": "Banská Bystrica",
     "savings_note": "Kratšia PN o ~3 týždne = menšia strata príjmu.", "savings_eur": 1100,
     "source": "Roosevelt BB · Intuitive Surgical (2026)"},
    {"news_id": "n-cuvis-cz", "tags": ["ortop", "koleno", "bedr", "knee", "hip", "kĺb", "klb"],
     "title": "Tech-Tracker: CUVIS-joint robot na výmeny kĺbov v Brne a Ostrave",
     "summary": "Robotická presnosť pri TEP kolena/bedra — presnejšie osadenie, dlhšia životnosť implantátu, rýchlejšia rehabilitácia.",
     "region": "CZ", "tech": "robotic_surgery", "specialty": "Ortopédia", "hunt_city": "Brno",
     "savings_note": "Menej revíznych operácií — dlhodobá úspora aj zdravie.", "savings_eur": 2000,
     "source": "FN Brno · curexo (2026)"},
    {"news_id": "n-cardiac-ai", "tags": ["srdc", "kardio", "ekg", "arytmi"],
     "title": "AI-EKG odhalí arytmie 2 roky pred prvými príznakmi",
     "summary": "Nový AI skríning z bežného EKG záznamu — validovaný na 1,2 mil. pacientov. Dostupný u vybraných kardiológov v CZ/SK.",
     "region": "CZ/SK", "tech": "ai_screening", "specialty": "Kardiológia", "hunt_city": "Praha",
     "savings_note": "Včasný záchyt = prevencia hospitalizácie (~3 000 €).", "savings_eur": 3000,
     "source": "Mayo Clinic AI Lab (2026)"},
    {"news_id": "n-diabetes-patch", "tags": ["diabet", "cukrovk", "glykémi", "glykemi", "inzulín", "inzulin"],
     "title": "Náplasťový CGM senzor 4. generácie — bez pichania, 21 dní",
     "summary": "Kontinuálne meranie glukózy bez kalibrácie; dáta rovno do mobilu. V SK čiastočne hradený od júna 2026.",
     "region": "SK", "tech": "wearable", "specialty": "Diabetológia", "hunt_city": "Bratislava",
     "savings_note": "Úspora na prúžkoch ~25 €/mes. + lepšia kompenzácia.", "savings_eur": 300,
     "source": "EASD 2026"},
    {"news_id": "n-cataract-femto", "tags": ["oč", "oc", "zrak", "katarakt", "šošovk", "sosovk"],
     "title": "Femtosekundová operácia sivého zákalu — 8 minút, obe oči",
     "summary": "Bezčepieľková laserová katarakta s prémiovými šošovkami; čakačky v CZ klesli pod 3 týždne.",
     "region": "CZ", "tech": "laser", "specialty": "Oftalmológia", "hunt_city": "Brno",
     "savings_note": "Kratšia čakačka vs. SK (~5 mes.) — mobilita = zisk.", "savings_eur": 0,
     "source": "Gemini Eye Clinics (2026)"},
]

HIGH_TECH = {"robotic_surgery", "dental_3d", "laser", "regenerative"}


async def ensure_news_seed():
    for n in NEWS_SEED:
        await db.medical_news.update_one(
            {"news_id": n["news_id"]},
            {"$setOnInsert": {**n, "published_at": datetime.now(timezone.utc)}}, upsert=True)


async def _user_keywords(uid: str) -> str:
    """Build the personal context corpus from the user's Vault + autopilot history."""
    docs = await db.documents.find({"user_id": uid}, {"_id": 0, "title": 1, "extracted_text": 1}).sort("uploaded_at", -1).to_list(20)
    acts = await db.jarvis_actions.find({"user_id": uid}, {"_id": 0, "specialty": 1, "doc_title": 1}).to_list(20)
    wl = await db.waitlist.find({"user_id": uid}, {"_id": 0, "specialty": 1}).to_list(20)
    corpus = " ".join(
        [f"{d.get('title', '')} {(d.get('extracted_text') or '')[:2000]}" for d in docs]
        + [f"{a.get('specialty') or ''} {a.get('doc_title') or ''}" for a in acts]
        + [w.get("specialty") or "" for w in wl])
    return corpus.lower()


@api.get("/news/feed")
async def news_feed(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await ensure_news_seed()
    corpus = await _user_keywords(user["user_id"])
    items = await db.medical_news.find({}, {"_id": 0}).to_list(50)
    matched, other = [], []
    for n in items:
        hit = [tg for tg in n["tags"] if tg in corpus]
        entry = {**n, "matched": bool(hit), "matched_tags": hit,
                 "high_tech": n["tech"] in HIGH_TECH,
                 "jarvis_alert": (f"Guardian Angel, prelom: {n['title']}. "
                                  f"Overená klinika: {n['hunt_city']} ({n['region']}). Mám uloviť termín?") if hit else None}
        (matched if hit else other).append(entry)
    return {"personalized": matched, "general": other,
            "note": "Kurátorovaný feed (simulovaná real-time ingescia — Phase 3: živé RSS/clinical-trials API)."}


@api.get("/news/tech-tracker")
async def tech_tracker(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    await ensure_news_seed()
    items = await db.medical_news.find(
        {"tech": {"$in": list(HIGH_TECH)}, "region": {"$regex": "CZ|SK"}}, {"_id": 0}).to_list(20)
    return {"deployments": items, "regions": ["CZ", "SK"],
            "hunter_note": "Waitlist Hunter prioritizuje tieto high-tech lokality pri rezerváciách."}


@api.post("/news/{news_id}/hunt")
async def news_hunt(news_id: str, authorization: Optional[str] = Header(None)):
    """'Hunt for Slot' — spawn a prioritized high-tech waitlist item from a news insight."""
    user = await get_current_user(authorization)
    await ensure_news_seed()
    n = await db.medical_news.find_one({"news_id": news_id}, {"_id": 0})
    if not n:
        raise HTTPException(404, "News item not found")
    item = {"item_id": uuid.uuid4().hex, "user_id": user["user_id"],
            "specialty": n["specialty"], "clinic": f"High-tech: {n['title'][:40]}",
            "city": n["hunt_city"], "current_date": "", "target_before": "",
            "priority": "hightech", "status": "searching", "last_check": datetime.now(timezone.utc),
            "found_slot": None, "created_at": datetime.now(timezone.utc),
            "source_news": news_id}
    await db.waitlist.insert_one(item.copy())
    try:
        from routes.swarm import bus_publish
        await bus_publish("news.hunt_started", "news_sentinel",
                          {"news_id": news_id, "specialty": n["specialty"], "city": n["hunt_city"]})
    except Exception:
        pass
    return {"ok": True, "waitlist_item": clean(item),
            "message": f"Hunter aktivovaný: {n['specialty']} · {n['hunt_city']} (priorita HIGH-TECH). Swarm hľadá termín."}
