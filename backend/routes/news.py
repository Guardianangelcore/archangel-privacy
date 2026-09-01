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
    {"news_id": "n-knee-cartilage", "tags": ["ortop", "koleno", "knee", "joint", "gonartr", "chrupavk"],
     "title": "Stanford: knee cartilage regeneration without surgery",
     "summary": "A new injectable therapy (ACI 3.0) restores cartilage in knee osteoarthritis. A similar technology is being deployed by a robotic clinic in Brno.",
     "region": "CZ", "tech": "regenerative", "specialty": "Orthopedics", "hunt_city": "Brno",
     "savings_note": "Compared to total knee replacement: ~€4,200 saved and 6 months less recovery.", "savings_eur": 4200,
     "source": "Stanford Medicine · Nature Regen. Med. (2026)"},
    {"news_id": "n-veins-laser", "tags": ["vein", "zil", "varix", "varikóz", "varikoz", "cievn", "vein"],
     "title": "30-minute laser for varicose veins now also in Bratislava",
     "summary": "Next-generation endovenous laser ablation — outpatient, without general anesthesia, return to work the next day.",
     "region": "SK", "tech": "laser", "specialty": "Cievna chirurgia", "hunt_city": "Bratislava",
     "savings_note": "No hospitalization: savings of ~€900 and 2 weeks of sick leave.", "savings_eur": 900,
     "source": "EuroVein Congress 2026"},
    {"news_id": "n-dental-3d", "tags": ["zub", "dental", "korunk", "implant"],
     "title": "3D printing of dental crowns in 30 minutes (CZ/SK networks)",
     "summary": "High-speed ceramic 3D printing directly in the clinic — a crown in one session instead of 2–3 visits.",
     "region": "CZ/SK", "tech": "dental_3d", "specialty": "Dentistry", "hunt_city": "Praha",
     "savings_note": "One session instead of three: savings of ~€350 + travel.", "savings_eur": 350,
     "source": "3Shape / Dental Summit Praha 2026"},
    {"news_id": "n-davinci-sk", "tags": ["prostat", "urol", "onko", "nádor", "nador", "chirurg"],
     "title": "Tech-Tracker: DaVinci Xi expanded in Banská Bystrica and Martin",
     "summary": "Robotic surgery (urology, onco-gynecology) — 40% shorter recovery. Slovak insurers already reimburse it.",
     "region": "SK", "tech": "robotic_surgery", "specialty": "Urology", "hunt_city": "Banská Bystrica",
     "savings_note": "Shorter sick leave by about 3 weeks = lower income loss.", "savings_eur": 1100,
     "source": "Roosevelt BB · Intuitive Surgical (2026)"},
    {"news_id": "n-cuvis-cz", "tags": ["ortop", "koleno", "bedr", "knee", "hip", "joint", "klb"],
     "title": "Tech-Tracker: CUVIS joint robot for joint replacements in Brno and Ostrava",
     "summary": "Robotic precision in knee/hip TEP — more precise placement, longer implant lifespan, faster rehabilitation.",
     "region": "CZ", "tech": "robotic_surgery", "specialty": "Orthopedics", "hunt_city": "Brno",
     "savings_note": "Fewer revision surgeries — long-term savings and better health.", "savings_eur": 2000,
     "source": "FN Brno · curexo (2026)"},
    {"news_id": "n-cardiac-ai", "tags": ["srdc", "kardio", "ekg", "arytmi"],
     "title": "AI ECG detects arrhythmias 2 years before first symptoms",
     "summary": "New AI screening from a standard ECG record — validated on 1.2 million patients. Available from selected cardiologists in CZ/SK.",
     "region": "CZ/SK", "tech": "ai_screening", "specialty": "Cardiology", "hunt_city": "Praha",
     "savings_note": "Early detection = prevention of hospitalization (~€3,000).", "savings_eur": 3000,
     "source": "Mayo Clinic AI Lab (2026)"},
    {"news_id": "n-diabetes-patch", "tags": ["diabet", "cukrovk", "glykémi", "glykemi", "inzulín", "inzulin"],
     "title": "Patch CGM sensor of the 4th generation — no finger pricks, 21 days",
     "summary": "Continuous glucose monitoring without calibration; data straight to mobile. In SK partially covered since June 2026.",
     "region": "SK", "tech": "wearable", "specialty": "Diabetology", "hunt_city": "Bratislava",
     "savings_note": "Savings on strips ~€25/month + better compensation.", "savings_eur": 300,
     "source": "EASD 2026"},
    {"news_id": "n-cataract-femto", "tags": ["eye", "oc", "zrak", "katarakt", "lens", "sosovk"],
     "title": "Femtosecond cataract surgery — 8 minutes, both eyes",
     "summary": "Blade-free laser cataract surgery with premium lenses; wait times in the Czech Republic have dropped below 3 weeks.",
     "region": "CZ", "tech": "laser", "specialty": "Ophthalmology", "hunt_city": "Brno",
     "savings_note": "Shorter wait vs. SK (~5 mo.) — mobility = profit.", "savings_eur": 0,
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
                                  f"Verified clinic: {n['hunt_city']} ({n['region']}). Should I hunt for an appointment?") if hit else None}
        (matched if hit else other).append(entry)
    return {"personalized": matched, "general": other,
            "note": "Curated feed (simulated real-time ingestion — Phase 3: live RSS/clinical-trials API)."}


@api.get("/news/tech-tracker")
async def tech_tracker(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    await ensure_news_seed()
    items = await db.medical_news.find(
        {"tech": {"$in": list(HIGH_TECH)}, "region": {"$regex": "CZ|SK"}}, {"_id": 0}).to_list(20)
    return {"deployments": items, "regions": ["CZ", "SK"],
            "hunter_note": "Waitlist Hunter prioritizes these high-tech locations when making reservations."}


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
            "message": f"Hunter activated: {n['specialty']} · {n['hunt_city']} (HIGH-TECH priority). Swarm is searching for an appointment."}
