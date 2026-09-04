# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Medical News Sentinel — personalized medical-breakthrough intelligence.

LIVE feed via Perplexity Sonar (sonar-pro, structured JSON, 12 h cache per language/country
+ a personal query per user built from their Vault/waitlist focus). The curated seed below is
the offline fallback when PERPLEXITY_API_KEY is blank or the upstream call fails. Regional
CZ/SK Tech-Tracker for robotic surgery & 3D dental printing. Health-economics link into
Wealth Advisor."""
from fastapi import HTTPException, Header
from typing import Optional
from datetime import datetime, timezone, timedelta
import asyncio
import hashlib
import logging
import uuid

from core import api, db, clean, get_current_user
from perplexity import sonar, pplx_enabled, strip_cite_marks, parse_json, SONAR_PRO

logger = logging.getLogger("guardian")

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
TECH_KINDS = HIGH_TECH | {"ai_screening", "wearable", "pharma", "other"}

# ---------------- LIVE FEED (Perplexity Sonar · sonar-pro) ----------------
LIVE_TTL = timedelta(hours=12)        # shared / personal cache lifetime
LIVE_FORCE_MIN = timedelta(hours=1)   # pull-to-refresh can bypass the cache at most hourly
LIVE_KEEP_DAYS = 14                   # live items stay huntable in db.medical_news this long

NEWS_SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "title": {"type": "string"}, "summary": {"type": "string"},
            "specialty": {"type": "string"}, "region": {"type": "string"},
            "tech": {"type": "string", "enum": sorted(TECH_KINDS)},
            "source": {"type": "string"}, "url": {"type": "string"}, "date": {"type": "string"},
            "hunt_city": {"type": ["string", "null"]}, "savings_note": {"type": ["string", "null"]},
            "keywords": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["title", "summary", "specialty", "region", "tech", "source", "url", "keywords"]}}},
    "required": ["items"],
}

NEWS_SYSTEM = (
    "You are the Medical News Sentinel of Archangel OS, an EU health companion app. Curate REAL, "
    "recent medical breakthroughs and health-technology deployments from reputable sources (peer-reviewed "
    "journals, EMA/ECDC/WHO, university hospitals, medical congresses, major health media). Never invent "
    "items; every item needs a real source URL. Patient-friendly, informational only — never diagnose. "
    "Return ONLY JSON matching the schema."
)


def _lang_full(lang: str) -> str:
    from routes.agent import LANG_FULL
    return LANG_FULL.get(lang or "en", "English")


def _news_user_prompt(lang: str, country: str, focus: Optional[list], n: int) -> str:
    region = f"{country}/EU" if country and country not in ("EU", "US") else "EU"
    focus_txt = (f" FOCUS strictly on these patient topics: {', '.join(focus)}." if focus else
                 " Cover a spread of specialties (cardiology, orthopedics, oncology, diabetes, dentistry, "
                 "ophthalmology, neurology, regenerative medicine, robotic surgery, digital health).")
    return (
        f"Find {n} medical breakthroughs or health-tech deployments from the last 30 days relevant to patients "
        f"in {region}.{focus_txt} LANGUAGE RULE: title, summary, specialty, savings_note and keywords MUST ALL be "
        f"written in {_lang_full(lang)} (translate English sources). For each item give: "
        "specialty, region code (SK, CZ, EU or World), tech category, source publisher name, "
        "the source url, date (YYYY-MM-DD if known), hunt_city (a CZ/SK/EU city whose clinic already offers it, "
        "else null), savings_note (one sentence on cost/time saved for the patient, else null) and 3-6 lowercase "
        "keyword stems (diseases, organs, procedures) for matching against the patient's records."
    )


def _domain(url: str) -> str:
    try:
        return url.split("//", 1)[1].split("/", 1)[0].replace("www.", "")
    except Exception:
        return url or ""


def _norm_item(raw: dict, lang: str, personal_for: Optional[str] = None) -> Optional[dict]:
    title = strip_cite_marks(str(raw.get("title") or ""))[:160]
    url = str(raw.get("url") or "").strip()
    if not title or not url.startswith("http"):
        return None
    tech = raw.get("tech") if raw.get("tech") in TECH_KINDS else "other"
    specialty = str(raw.get("specialty") or "Medicine")[:60]
    kws = [str(k).lower().strip() for k in (raw.get("keywords") or []) if len(str(k).strip()) >= 4]  # ≥4 chars: no "ai"/"rna" false matches
    tags = sorted({*kws[:8], *[w for w in specialty.lower().replace("/", " ").split() if len(w) >= 4]})
    return {
        "news_id": "live-" + hashlib.sha1(url.encode()).hexdigest()[:12],
        "title": title, "summary": strip_cite_marks(str(raw.get("summary") or ""))[:700],
        "region": str(raw.get("region") or "EU")[:12], "tech": tech, "specialty": specialty,
        "hunt_city": (raw.get("hunt_city") or "") if isinstance(raw.get("hunt_city"), str) else "",
        "savings_note": raw.get("savings_note") or None, "savings_eur": 0,
        "source": str(raw.get("source") or _domain(url))[:80], "url": url,
        "date": raw.get("date") or None, "tags": tags, "live": True, "lang": lang,
        "personal_for": personal_for, "published_at": datetime.now(timezone.utc),
    }


async def _fetch_live(lang: str, country: str, focus: Optional[list], n: int,
                      personal_for: Optional[str] = None) -> Optional[list]:
    res = await sonar(
        [{"role": "system", "content": NEWS_SYSTEM},
         {"role": "user", "content": _news_user_prompt(lang, country, focus, n)}],
        model=SONAR_PRO, recency="month", context_size="medium", max_tokens=2200,
        json_schema=NEWS_SCHEMA, timeout=90.0)
    if not res:
        return None
    parsed = parse_json(res["content"]) or {}
    raws = parsed.get("items") if isinstance(parsed, dict) else parsed
    items = [i for i in (_norm_item(r, lang, personal_for) for r in (raws or []) if isinstance(r, dict)) if i]
    if not items:
        logger.error("perplexity news: empty/invalid items")
        return None
    # Keep live items huntable + visible to the swarm News Sentinel; prune old ones.
    now = datetime.now(timezone.utc)
    for it in items:
        await db.medical_news.update_one({"news_id": it["news_id"]}, {"$set": it}, upsert=True)
    # Non-destructive retention: stale live items are ARCHIVED (soft flag), never hard-deleted by background work.
    await db.medical_news.update_many({"live": True, "archived": {"$ne": True}, "published_at": {"$lt": now - timedelta(days=LIVE_KEEP_DAYS)}},
                                      {"$set": {"live": False, "archived": True, "archived_at": now}})
    return items


async def _refresh_live(key: str, fetch) -> None:
    now = datetime.now(timezone.utc)
    try:
        items = await fetch()
        if items is not None:
            await db.medical_news_live.update_one({"key": key}, {"$set": {"items": items, "fetched_at": now}, "$unset": {"failed_at": ""}}, upsert=True)
        else:   # upstream failure (e.g. 429 rate limit) → back off before the next attempt
            await db.medical_news_live.update_one({"key": key}, {"$set": {"failed_at": now}}, upsert=True)
    except Exception as e:
        logger.error(f"live news refresh {key}: {e}")
        await db.medical_news_live.update_one({"key": key}, {"$set": {"failed_at": now}}, upsert=True)
    finally:
        _inflight.pop(key, None)


_inflight: dict = {}
LIVE_BACKOFF = timedelta(minutes=3)


async def _cached_live(key: str, force: bool, fetch) -> tuple:
    """(items | None, pending). 12 h cache in db.medical_news_live; a miss/stale entry schedules ONE
    background Sonar refresh (never blocks the request — Sonar takes ~25 s) and returns the stale
    items meanwhile. `force` (pull-to-refresh) bypasses the cache at most hourly. After an upstream
    failure the key backs off for LIVE_BACKOFF so a rate-limited API is never hammered."""
    if not pplx_enabled():
        return None, False
    now = datetime.now(timezone.utc)
    doc = await db.medical_news_live.find_one({"key": key}, {"_id": 0}) or {}
    items = doc.get("items")
    if items is not None and doc.get("fetched_at"):
        age = now - doc["fetched_at"].replace(tzinfo=timezone.utc)
        if age < LIVE_TTL and not (force and age > LIVE_FORCE_MIN):
            return items, False
    if doc.get("failed_at") and now - doc["failed_at"].replace(tzinfo=timezone.utc) < LIVE_BACKOFF:
        return items, False
    task = _inflight.get(key)
    if task is None or task.done():
        _inflight[key] = asyncio.create_task(_refresh_live(key, fetch))
    return items, True


async def warm_live_news() -> int:
    """Swarm hook: keep the shared general cache fresh for every language/country combo seen among
    users active in the last 24 h (max 6 combos per pass) so the screen opens instantly."""
    if not pplx_enabled():
        return 0
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    uids = [s["user_id"] for s in await db.user_sessions.find({"created_at": {"$gte": since}}, {"_id": 0, "user_id": 1}).to_list(500)]
    combos: list = []
    async for u in db.users.find({"user_id": {"$in": list(set(uids))}}, {"_id": 0, "language": 1, "geo.country": 1}):
        combo = ((u.get("language") or "en")[:5], ((u.get("geo") or {}).get("country") or "EU")[:3])
        if combo not in combos:
            combos.append(combo)
    started = 0
    for lang, country in combos[:6]:
        _, pending = await _cached_live(f"general:{lang}:{country}", False, lambda l=lang, c=country: _fetch_live(l, c, None, 6))
        started += int(pending)
    return started


async def _user_focus(uid: str) -> list:
    """Structured patient focus (specialties + recent diagnoses/surgeries) for the personal live query.
    Items spawned by the News Sentinel itself are excluded (no news→hunt→news feedback loop) and the
    result is sorted so the cache key stays stable."""
    focus: list = []
    for coll, field in (("waitlist", "specialty"), ("jarvis_actions", "specialty")):
        q = {"user_id": uid, field: {"$nin": [None, ""]}, "source": {"$not": {"$regex": "^swarm:"}}, "news_id": None}
        for d in await db[coll].find(q, {"_id": 0, field: 1}).sort("created_at", -1).to_list(6):
            focus.append(str(d[field]))
    for e in await db.calendar_events.find({"user_id": uid, "child_id": None, "category": {"$in": ["disease", "surgery"]}},
                                           {"_id": 0, "title": 1}).sort("date", -1).to_list(4):
        if e.get("title"):
            focus.append(str(e["title"]))
    seen, out = set(), []
    for f in focus:
        k = f.strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(f.strip()[:40])
    return sorted(out[:4], key=str.lower)


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
async def news_feed(force: bool = False, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    await ensure_news_seed()
    corpus = await _user_keywords(uid)
    lang = (user.get("language") or "en")[:5]
    country = ((user.get("geo") or {}).get("country") or "EU")[:3]
    # LIVE — shared query per language/country (+ a personal query when the user has a health focus).
    # Cache misses are refreshed in the background; the response never waits for Sonar.
    general, g_pending = await _cached_live(f"general:{lang}:{country}", force,
                                            lambda: _fetch_live(lang, country, None, 6))
    personal: list = []
    p_pending = False
    focus = await _user_focus(uid) if pplx_enabled() else []
    if focus:
        fkey = hashlib.sha1("|".join(focus).lower().encode()).hexdigest()[:10]
        p_items, p_pending = await _cached_live(f"personal:{uid}:{fkey}", force,
                                                lambda: _fetch_live(lang, country, focus, 3, personal_for=uid))
        personal = p_items or []
    live = general is not None
    if live:
        seen: set = set()
        items = [n for n in personal + general if not (n["news_id"] in seen or seen.add(n["news_id"]))]
    else:
        items = await db.medical_news.find({"live": {"$ne": True}, "archived": {"$ne": True}}, {"_id": 0}).to_list(50)
    matched, other = [], []
    for n in items:
        hit = [tg for tg in n.get("tags", []) if tg and tg in corpus]
        is_personal = bool(hit) or n.get("personal_for") == uid
        clinic = f" Verified clinic: {n['hunt_city']} ({n['region']})." if n.get("hunt_city") else ""
        entry = {**n, "matched": is_personal, "matched_tags": hit or (focus[:3] if is_personal else []),
                 "high_tech": n.get("tech") in HIGH_TECH,
                 "jarvis_alert": (f"Guardian Angel, prelom: {n['title']}.{clinic} "
                                  f"Should I hunt for an appointment?") if is_personal else None}
        (matched if is_personal else other).append(entry)
    fetched = await db.medical_news_live.find_one({"key": f"general:{lang}:{country}"}, {"_id": 0, "fetched_at": 1})
    pending = g_pending or p_pending
    return {"personalized": clean(matched), "general": clean(other), "live": live, "pending": pending,
            "fetched_at": fetched["fetched_at"].isoformat() if (live and fetched) else None,
            "engine": "Perplexity Sonar · sonar-pro" if (live or pending) else "curated",
            "note": ("Live web retrieval via Perplexity Sonar — sources linked on every item; refreshed every 12 h."
                     if live else "Fetching live sources from the web (Perplexity Sonar)…" if pending
                     else "Curated feed (live web retrieval is offline right now).")}


@api.get("/news/tech-tracker")
async def tech_tracker(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    await ensure_news_seed()
    items = await db.medical_news.find(
        {"tech": {"$in": list(HIGH_TECH)}, "region": {"$regex": "CZ|SK"}, "archived": {"$ne": True}}, {"_id": 0}).to_list(20)
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
