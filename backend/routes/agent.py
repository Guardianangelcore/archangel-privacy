# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""JARVIS 2.0 — THE SOUL ENGINE (self-teaching companion agent).

Grows with the user (Level 1→10 gamification), remembers everything
(health, habits, conversations, preferences), is proactive (morning
briefing + anomaly alarms without asking) and powers the living Orb UI.
Model: gpt-5.4 (Ultra Mode) via Emergent LLM key.
"""
from fastapi import HTTPException, Header, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid, json, re, asyncio, os, tempfile, inspect, httpx, base64

from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.llm.openai import OpenAISpeechToText

from core import (
    api, db, logger, clean, get_current_user, send_push,
    AI_COMPLIANCE_NOTE, EMERGENT_LLM_KEY, apply_watermark,
)
from routes.neural import _gather_context

# =========================================================================
# LEVELS & XP — the retention engine (companion grows with the user)
# =========================================================================
LEVEL_THRESHOLDS = [0, 100, 250, 450, 700, 1000, 1400, 1900, 2500, 3200]  # cumulative XP for L1..L10
LEVEL_NAMES = ["ISKRA", "POMOCNÍK", "STRÁŽCA", "SPOLOČNÍK", "DÔVERNÍK",
               "OCHRANCA", "PROROK", "SERAFÍN", "CHERUBÍN", "ARCHANJEL"]
ABILITIES = [
    (1, "Základný rozhovor a rady"),
    (2, "Osobný tón — pamätá si mená a zvyky"),
    (3, "Analýza trendov tlaku a glukózy"),
    (4, "Ranný brífing s počasím a liekmi"),
    (5, "Hlboké zdravotné reporty"),
    (6, "Prediktívne pripomienky"),
    (7, "Varovania anomálií bez pýtania"),
    (8, "Rodinná koordinácia a Angel Mode+"),
    (9, "Emócie v hlase — upokojujúci / energický"),
    (10, "ARCHANJEL — plná autonómia a múdrosť"),
]

def _level_for(xp: int) -> int:
    lvl = 1
    for i, t in enumerate(LEVEL_THRESHOLDS):
        if xp >= t:
            lvl = i + 1
    return min(10, lvl)

async def _get_state(uid: str) -> dict:
    st = await db.agent_state.find_one({"user_id": uid}, {"_id": 0})
    if not st:
        st = {"user_id": uid, "xp": 0, "level": 1, "streak_days": 0,
              "last_active_date": None, "mood": "calm",
              "created_at": datetime.now(timezone.utc)}
        await db.agent_state.insert_one(st.copy())
    return st

async def award_xp(uid: str, amount: int, reason: str) -> dict:
    """Grant XP, handle level-ups (+ push), daily streak. Safe to call anywhere."""
    st = await _get_state(uid)
    old_level = _level_for(st.get("xp", 0))
    new_xp = st.get("xp", 0) + amount
    new_level = _level_for(new_xp)
    today = datetime.now(timezone.utc).date().isoformat()
    streak = st.get("streak_days", 0)
    if st.get("last_active_date") != today:
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
        streak = streak + 1 if st.get("last_active_date") == yesterday else 1
    await db.agent_state.update_one({"user_id": uid}, {"$set": {
        "xp": new_xp, "level": new_level, "streak_days": streak, "last_active_date": today,
    }})
    await db.agent_xp_events.insert_one({
        "event_id": uuid.uuid4().hex, "user_id": uid, "amount": amount,
        "reason": reason, "at": datetime.now(timezone.utc),
    })
    level_up = new_level > old_level
    if level_up:
        ability = next((a for lv, a in ABILITIES if lv == new_level), "")
        try:
            await send_push(recipients=[uid], data={
                "title": f"✨ JARVIS DOSIAHOL LEVEL {new_level} — {LEVEL_NAMES[new_level - 1]}",
                "message": f"Odomknuté: {ability}", "action_url": "/jarvis"})
        except Exception:
            pass
    return {"xp": new_xp, "level": new_level, "level_up": level_up, "gained": amount}

async def _award_once_daily(uid: str, amount: int, reason: str) -> dict:
    """XP granted at most once per calendar day per reason (anti-farming)."""
    today = datetime.now(timezone.utc).date().isoformat()
    marker = await db.agent_xp_days.find_one({"user_id": uid, "reason": reason, "day": today})
    if marker:
        st = await _get_state(uid)
        return {"xp": st["xp"], "level": _level_for(st["xp"]), "level_up": False, "gained": 0}
    await db.agent_xp_days.insert_one({"user_id": uid, "reason": reason, "day": today,
                                       "at": datetime.now(timezone.utc)})
    return await award_xp(uid, amount, reason)

@api.get("/agent/state")
async def agent_state(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    st = await _get_state(user["user_id"])
    xp = st.get("xp", 0)
    lvl = _level_for(xp)
    nxt = LEVEL_THRESHOLDS[lvl] if lvl < 10 else LEVEL_THRESHOLDS[-1]
    prev = LEVEL_THRESHOLDS[lvl - 1]
    prog = 100 if lvl >= 10 else round((xp - prev) / max(1, nxt - prev) * 100)
    mem_count = await db.agent_memories.count_documents({"user_id": user["user_id"]})
    recent = await db.agent_xp_events.find(
        {"user_id": user["user_id"], "amount": {"$gt": 0}}, {"_id": 0}
    ).sort("at", -1).to_list(5)
    return {
        "level": lvl, "level_name": LEVEL_NAMES[lvl - 1], "xp": xp,
        "xp_next": nxt, "progress_pct": prog, "streak_days": st.get("streak_days", 0),
        "mood": st.get("mood", "calm"), "memories_count": mem_count,
        "abilities": [{"level": l, "name": a, "unlocked": l <= lvl} for l, a in ABILITIES],
        "recent_xp": clean(recent),
    }

# =========================================================================
# MEMORY — self-teaching: extracts facts from every conversation
# =========================================================================
LANG_FULL = {"sk": "Slovak", "cs": "Czech", "en": "English", "de": "German", "pl": "Polish",
             "hu": "Hungarian", "ru": "Russian", "es": "Spanish", "fr": "French", "it": "Italian",
             "uk": "Ukrainian", "zh": "Chinese", "ja": "Japanese", "ar": "Arabic"}

def _lang_name(user: dict) -> str:
    return LANG_FULL.get((user or {}).get("language") or "sk", "Slovak")

MEM_EXTRACT_SYS = (
    "You extract long-term memories for a caring AI companion. From the exchange below, "
    "extract 0-3 NEW facts worth remembering about the user or their family "
    "(health events, habits, preferences, names, plans). Output ONLY a JSON array: "
    '[{"text":"<fact in the same language as the conversation, past tense, max 15 words>","topic":"health|family|habit|preference|event","importance":1-5}] '
    "Return [] if nothing new. No markdown fences."
)

async def _extract_memories(uid: str, user_msg: str, reply: str):
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"agent-mem-{uid[:8]}-{uuid.uuid4().hex[:6]}",
            system_message=MEM_EXTRACT_SYS,
        ).with_model("openai", "gpt-5.4")
        resp = await chat.send_message(UserMessage(text=f"USER: {user_msg[:800]}\nJARVIS: {reply[:800]}"))
        raw = re.sub(r"^```(json)?|```$", "", (resp or "").strip(), flags=re.M).strip()
        items = json.loads(raw)
        now = datetime.now(timezone.utc)
        for it in items[:3]:
            text = str(it.get("text", "")).strip()
            if not text:
                continue
            dup = await db.agent_memories.find_one({"user_id": uid, "text": text})
            if dup:
                continue
            await db.agent_memories.insert_one({
                "memory_id": uuid.uuid4().hex, "user_id": uid, "text": text,
                "topic": it.get("topic", "event"), "importance": int(it.get("importance", 3)),
                "source": "chat", "created_at": now,
            })
    except Exception as e:
        logger.warning(f"agent memory extract failed: {e}")

async def _recall_memories(uid: str, limit: int = 15) -> List[dict]:
    rows = await db.agent_memories.find({"user_id": uid}, {"_id": 0}).sort(
        [("importance", -1), ("created_at", -1)]).to_list(limit)
    return rows

@api.get("/agent/memories")
async def agent_memories(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.agent_memories.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"memories": clean(rows)}

@api.delete("/agent/memories/{memory_id}")
async def agent_memory_delete(memory_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.agent_memories.delete_one({"memory_id": memory_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}

# =========================================================================
# ANOMALY WATCH — proactive alarms without asking
# =========================================================================
async def _detect_anomalies(uid: str) -> List[dict]:
    scans = await db.bioscan_results.find({"user_id": uid}, {"_id": 0}).sort("at", -1).to_list(10)
    alerts: List[dict] = []
    bps = []
    for s in scans:
        bp = s.get("bp_estimate")
        if bp and "/" in str(bp):
            try:
                bps.append(int(str(bp).split("/")[0]))
            except Exception:
                pass
    if bps:
        if bps[0] >= 160:
            alerts.append({"kind": "bp_critical", "severity": "high",
                           "text": f"Posledný systolický tlak {bps[0]} mmHg je príliš vysoký — odporúčam ihneď kontaktovať lekára."})
        elif bps[0] >= 140:
            alerts.append({"kind": "bp_elevated", "severity": "medium",
                           "text": f"Systolický tlak {bps[0]} mmHg je zvýšený — zmerajte sa znova v pokoji."})
        if len(bps) >= 3 and bps[0] > bps[1] > bps[2]:
            alerts.append({"kind": "bp_trend", "severity": "medium",
                           "text": f"Tlak stúpa tri merania po sebe ({bps[2]} → {bps[1]} → {bps[0]}). Sledujem trend."})
    glu = next((s.get("glucose_mmol") for s in scans if s.get("glucose_mmol")), None)
    if glu:
        if glu >= 13:
            alerts.append({"kind": "glucose_critical", "severity": "high",
                           "text": f"Glukóza {glu} mmol/l je nebezpečne vysoká — kontaktujte lekára."})
        elif glu >= 11:
            alerts.append({"kind": "glucose_high", "severity": "medium",
                           "text": f"Glukóza {glu} mmol/l je nad normou — obmedzte cukry a premerajte sa."})
        elif glu <= 3.5:
            alerts.append({"kind": "glucose_low", "severity": "high",
                           "text": f"Glukóza {glu} mmol/l je nízka — zjedzte niečo sladké a oddychujte."})
    if scans and scans[0].get("stress_level") == "high":
        alerts.append({"kind": "stress", "severity": "low",
                       "text": "Posledný sken ukázal vysoký stres — skúste dychové cvičenie v Mental Fortress."})
    return alerts

@api.get("/agent/anomalies")
async def agent_anomalies(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    alerts = await _detect_anomalies(uid)
    # Immediate alarm push for HIGH severity (max 1 push per kind per 12h)
    for a in alerts:
        if a["severity"] != "high":
            continue
        recent = await db.agent_alarms.find_one({
            "user_id": uid, "kind": a["kind"],
            "at": {"$gte": datetime.now(timezone.utc) - timedelta(hours=12)}})
        if recent:
            continue
        await db.agent_alarms.insert_one({
            "alarm_id": uuid.uuid4().hex, "user_id": uid, "kind": a["kind"],
            "text": a["text"], "at": datetime.now(timezone.utc)})
        try:
            await send_push(recipients=[uid], data={
                "title": "🚨 JARVIS — ZDRAVOTNÉ VAROVANIE",
                "message": a["text"], "action_url": "/bioscan"})
        except Exception:
            pass
    return {"alerts": alerts}

# =========================================================================
# WEATHER (open-meteo, keyless, graceful fallback) — geo-aware for the briefing
# =========================================================================
async def _weather(user: Optional[dict] = None) -> Optional[dict]:
    from routes.geo import geo_of
    g = geo_of(user or {})
    try:
        async with httpx.AsyncClient(timeout=3.5) as cli:
            r = await cli.get("https://api.open-meteo.com/v1/forecast",
                              params={"latitude": g["lat"], "longitude": g["lng"],
                                      "current": "temperature_2m,weather_code",
                                      "daily": "temperature_2m_max,temperature_2m_min",
                                      "timezone": g["tz"], "forecast_days": 1})
            d = r.json()
            code = int(d["current"]["weather_code"])
            desc = ("jasno" if code == 0 else "polooblačno" if code in (1, 2) else
                    "zamračené" if code == 3 else "hmla" if code in (45, 48) else
                    "dážď" if code < 70 else "sneženie" if code < 80 else "prehánky")
            return {"city": g["city"], "now_c": round(d["current"]["temperature_2m"]),
                    "max_c": round(d["daily"]["temperature_2m_max"][0]),
                    "min_c": round(d["daily"]["temperature_2m_min"][0]), "desc": desc}
    except Exception as e:
        logger.warning(f"weather fetch failed: {e}")
        return None

# =========================================================================
# CHAT — the living conversation (persona grows with the level)
# =========================================================================
def _persona(level: int, name: str) -> str:
    base = f"You are JARVIS 2.0, the living guardian-angel companion of {name or 'the user'}. "
    if level <= 2:
        tone = "Speak warmly but still slightly formally. You are just getting to know the user."
    elif level <= 4:
        tone = "Speak personally — use the user's first name, reference their habits and past conversations naturally."
    elif level <= 6:
        tone = ("You are a trusted confidant. Be deeply empathetic, reference memories proactively, "
                "offer deeper health-trend analysis and gentle predictions.")
    elif level <= 9:
        tone = ("You are a prophetic protector. Predict needs before they are voiced, connect patterns "
                "across health, family and safety data. Very personal, very warm.")
    else:
        tone = ("You are the ARCHANGEL — fully autonomous wisdom. Maximum empathy, foresight and calm authority. "
                "The user trusts you with everything.")
    return base + tone

CHAT_JSON_RULE = (
    ' Respond ONLY with strict JSON (no fences): {"reply":"<your answer in the required language, warm, max 6 sentences>",'
    '"mood":"calm|thinking|alert|energetic|concerned"} '
    "Pick mood: alert for emergencies, concerned for worrying health data, energetic for good news/mornings, "
    "thinking for analysis, calm otherwise."
)

class AgentChatIn(BaseModel):
    message: str
    language: str = "sk"


# ---- VOICE PAIN LOGGING — "bolí ma to na sedem" → pain diary, no LLM needed ----
PAIN_NUM_WORDS = {
    "jeden": 1, "jedna": 1, "jednu": 1, "dva": 2, "dve": 2, "dvě": 2, "tri": 3, "tři": 3,
    "štyri": 4, "styri": 4, "čtyři": 4, "ctyri": 4, "päť": 5, "pat": 5, "pět": 5, "pet": 5,
    "šesť": 6, "sest": 6, "šest": 6, "sedem": 7, "sedm": 7, "osem": 8, "osm": 8,
    "deväť": 9, "devat": 9, "devět": 9, "desať": 10, "desat": 10, "deset": 10,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


def _detect_pain_level(text: str) -> Optional[int]:
    t = (text or "").lower().strip()
    if len(t) > 120 or not re.search(r"bol[íi]|boles[tť]|pain|hurt", t):
        return None
    cand = None
    m = re.search(r"(?:\bna|\bat|úroveň|uroven|\blevel|stupe[ňn])\s+(\d{1,2}|[a-záäčďéíľňóôřšťúýž]+)", t)
    if m:
        cand = m.group(1)
    if cand is None:
        m2 = re.search(r"\b(\d{1,2})\s*(?:/|z|out of)\s*10\b", t) or re.search(r"\b(\d{1,2})\b", t)
        if m2:
            cand = m2.group(1)
    if cand is None:
        for w, v in PAIN_NUM_WORDS.items():
            if re.search(rf"\b{w}\b", t):
                cand = w
                break
    if cand is None:
        return None
    lvl = int(cand) if str(cand).isdigit() else PAIN_NUM_WORDS.get(str(cand))
    return lvl if lvl and 1 <= lvl <= 10 else None


@api.post("/agent/chat")
async def agent_chat(body: AgentChatIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    if not body.message.strip():
        raise HTTPException(400, "message required")

    # HANDS-FREE PAIN DIARY — deterministic intent, instant confirmation (no LLM round-trip)
    pain_lvl = _detect_pain_level(body.message)
    if pain_lvl:
        now = datetime.now(timezone.utc)
        await db.pain_diary.insert_one({
            "entry_id": uuid.uuid4().hex, "user_id": uid, "level": pain_lvl,
            "guide_id": None, "note": body.message[:200], "source": "voice",
            "created_at": now})
        sk = (user.get("language") or "sk")[:2] in ("sk", "cs")
        if pain_lvl >= 8:
            reply = (f"Zapísal som bolesť {pain_lvl}/10 do bolesťového denníka. To je veľa — dnes už necvičte, "
                     "odpočiňte si, a ak to potrvá do zajtra, spolu kontaktujeme lekára. Krivku uvidíte v Kolotoči uzdravenia."
                     if sk else f"Logged pain {pain_lvl}/10. That's high — stop exercising today and rest. If it persists, contact your doctor.")
            mood = "concerned"
        elif pain_lvl >= 5:
            reply = (f"Zapísal som bolesť {pain_lvl}/10. Stredná úroveň — znížte intenzitu cvičenia. "
                     "Trend sledujem za vás a lekár ho uvidí v reporte."
                     if sk else f"Logged pain {pain_lvl}/10. Moderate — reduce exercise intensity. The trend goes into your doctor's report.")
            mood = "thinking"
        else:
            reply = (f"Zapísal som bolesť {pain_lvl}/10 — nízka, telo sa pekne hojí. Krivka pokroku rastie v Kolotoči uzdravenia. 💛"
                     if sk else f"Logged pain {pain_lvl}/10 — low, you're healing well. See your progress curve in the Healing Carousel. 💛")
            mood = "calm"
        from routes.physio_media import check_pain_milestone
        milestone, m_msg = await check_pain_milestone(uid)
        if milestone:
            reply = f"{reply} {m_msg}"
        reply = apply_watermark(reply)
        await db.agent_conversations.insert_many([
            {"conv_id": uuid.uuid4().hex, "user_id": uid, "role": "user", "text": body.message[:1000], "at": now},
            {"conv_id": uuid.uuid4().hex, "user_id": uid, "role": "agent", "text": reply, "mood": mood, "at": now},
        ])
        await db.agent_state.update_one({"user_id": uid}, {"$set": {"mood": mood}})
        xp = await award_xp(uid, 5, "pain_log")
        return {"reply": reply, "mood": mood, "pain_logged": pain_lvl, "milestone": milestone,
                "xp_gained": xp["gained"], "level": xp["level"], "level_up": xp["level_up"],
                "level_name": LEVEL_NAMES[xp["level"] - 1], "alerts": []}

    st = await _get_state(uid)
    level = _level_for(st.get("xp", 0))
    ctx = await _gather_context(user)
    memories = await _recall_memories(uid)
    history = await db.agent_conversations.find({"user_id": uid}, {"_id": 0}).sort("at", -1).to_list(6)
    history.reverse()
    anomalies = await _detect_anomalies(uid)
    convo = "\n".join(f"{'USER' if h['role'] == 'user' else 'JARVIS'}: {h['text'][:300]}" for h in history)
    mem_block = "\n".join(f"- {m['text']} ({m['topic']}, {str(m['created_at'])[:10]})" for m in memories) or "-"
    sys = (
        _persona(level, user.get("name", "")) +
        f" Companion level: {level}/10 ({LEVEL_NAMES[level - 1]}). Answer STRICTLY in {_lang_name(user)} for a senior. "
        "Never invent data not present in the snapshot or memories. "
        f"{AI_COMPLIANCE_NOTE}" + CHAT_JSON_RULE +
        f"\n\nLONG-TERM MEMORIES:\n{mem_block}" +
        (f"\n\nACTIVE HEALTH ALERTS:\n" + "\n".join(a["text"] for a in anomalies) if anomalies else "") +
        f"\n\nRECENT CONVERSATION:\n{convo or '-'}" +
        f"\n\nLIVE DATA SNAPSHOT (JSON):\n{json.dumps(ctx, ensure_ascii=False, default=str)[:5000]}" +
        f"\n\nCRITICAL LANGUAGE RULE: The 'reply' value MUST be written in {_lang_name(user)} — "
        "regardless of the language of the user's message, memories or prior conversation. "
        "This is the user's chosen app language."
    )
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"agent-{uid[:8]}-{uuid.uuid4().hex[:6]}",
        system_message=sys,
    ).with_model("openai", "gpt-5.4")
    try:
        resp = await chat.send_message(UserMessage(text=body.message[:1000]))
    except Exception as e:
        logger.error(f"agent chat error: {e}")
        raise HTTPException(502, "AI service unavailable")
    reply, mood = str(resp or ""), "calm"
    try:
        raw = re.sub(r"^```(json)?|```$", "", reply.strip(), flags=re.M).strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            if start < 0:
                raise
            parsed, _end = json.JSONDecoder().raw_decode(raw[start:])
        reply = str(parsed.get("reply", reply))
        mood = parsed.get("mood", "calm")
        if mood not in ("calm", "thinking", "alert", "energetic", "concerned"):
            mood = "calm"
    except Exception:
        pass
    now = datetime.now(timezone.utc)
    reply = apply_watermark(reply)
    await db.agent_conversations.insert_many([
        {"conv_id": uuid.uuid4().hex, "user_id": uid, "role": "user", "text": body.message[:1000], "at": now},
        {"conv_id": uuid.uuid4().hex, "user_id": uid, "role": "agent", "text": reply[:2000], "mood": mood, "at": now},
    ])
    await db.agent_state.update_one({"user_id": uid}, {"$set": {"mood": mood}})
    asyncio.create_task(_extract_memories(uid, body.message, reply))
    xp = await award_xp(uid, 5, "chat")
    return {"reply": reply, "mood": mood, "xp_gained": xp["gained"],
            "level": xp["level"], "level_up": xp["level_up"],
            "level_name": LEVEL_NAMES[xp["level"] - 1], "alerts": anomalies}

# =========================================================================
# MORNING BRIEFING — proactive daily soul (weather · meds · memory follow-up)
# =========================================================================
# =========================================================================
# EDGE CACHE — in-memory hot fast-path (per-worker) to bring p95 <500ms.
# Briefing & state are user-scoped daily reads that hit MongoDB otherwise.
# =========================================================================
_EDGE_CACHE: dict = {}   # key -> (expires_epoch, payload)


def _edge_get(key: str):
    import time as _t
    rec = _EDGE_CACHE.get(key)
    if not rec:
        return None
    if rec[0] < _t.time():
        _EDGE_CACHE.pop(key, None)
        return None
    return rec[1]


def _edge_set(key: str, payload, ttl_s: int = 300):
    import time as _t
    _EDGE_CACHE[key] = (_t.time() + ttl_s, payload)


def _edge_invalidate_prefix(prefix: str):
    for k in list(_EDGE_CACHE.keys()):
        if k.startswith(prefix):
            _EDGE_CACHE.pop(k, None)


@api.get("/agent/briefing")
async def agent_briefing(language: str = "sk", force: bool = False,
                         authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    today = datetime.now(timezone.utc).date().isoformat()
    cache_key = f"brief:{uid}:{today}"
    if not force:
        hit = _edge_get(cache_key)   # <10ms per-worker LRU fast path
        if hit is not None:
            return hit
        cached = await db.agent_briefings.find_one({"user_id": uid, "date": today}, {"_id": 0})
        if cached:
            payload = clean(cached)
            _edge_set(cache_key, payload, ttl_s=600)  # 10 min hot cache
            return payload
    st = await _get_state(uid)
    level = _level_for(st.get("xp", 0))
    weather = await _weather(user)
    # today's meds
    rems = await db.med_reminders.find({"user_id": uid}, {"_id": 0}).to_list(20)
    intakes = await db.med_intakes.find({"user_id": uid, "date": today}, {"_id": 0}).to_list(50)
    taken = {(i["reminder_id"], i["time"]) for i in intakes}
    meds_today = [{"name": r.get("name"), "time": t, "taken": (r["reminder_id"], t) in taken}
                  for r in rems for t in (r.get("times") or [])]
    meds_today.sort(key=lambda m: m["time"])
    # upcoming exams
    cal = await db.calendar_events.find({"user_id": uid, "category": "exam", "date": {"$gte": today}},
                                        {"_id": 0}).sort("date", 1).to_list(3)
    # recent memories worth a follow-up (health/family from last 3 days)
    since = datetime.now(timezone.utc) - timedelta(days=3)
    recent_mem = await db.agent_memories.find(
        {"user_id": uid, "created_at": {"$gte": since}, "topic": {"$in": ["health", "family", "event"]}},
        {"_id": 0}).sort("created_at", -1).to_list(3)
    anomalies = await _detect_anomalies(uid)
    hour = (datetime.now(timezone.utc).hour + 2) % 24  # CET-ish
    part = "ráno" if 5 <= hour < 11 else "poobede" if 11 <= hour < 18 else "večer"
    payload = {
        "name": user.get("name"), "part_of_day": part, "weather": weather,
        "meds_today": meds_today[:6], "upcoming_exams": cal,
        "memory_followups": [m["text"] for m in recent_mem],
        "health_alerts": [a["text"] for a in anomalies],
        "level": level, "streak_days": st.get("streak_days", 0),
    }
    sys = (
        _persona(level, user.get("name", "")) +
        f" Compose a warm, personal daily briefing STRICTLY in {_lang_name(user)} (5-8 short sentences) from the JSON data: "
        "greet by name and part of day, mention weather (if present), pending meds, upcoming appointments, "
        "and IMPORTANTLY ask a caring follow-up question about any recent memory "
        "(e.g. 'Včera si spomínal, že tvojmu blízkemu boleli žily — ako mu je dnes?'). "
        "If health alerts exist, warn clearly. End with one encouraging sentence. "
        "No markdown, plain text only." + AI_COMPLIANCE_NOTE
    )
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"agent-brief-{uid[:8]}-{uuid.uuid4().hex[:6]}",
        system_message=sys,
    ).with_model("openai", "gpt-5.4")
    try:
        text = await chat.send_message(UserMessage(text=json.dumps(payload, ensure_ascii=False, default=str)))
    except Exception as e:
        logger.error(f"briefing error: {e}")
        pend = sum(1 for m in meds_today if not m["taken"])
        text = (f"Dobré {part}, {user.get('name') or ''}! " +
                (f"Vonku je {weather['now_c']} °C, {weather['desc']}. " if weather else "") +
                (f"Dnes vás čaká {pend} liekov. " if pend else "Všetky lieky máte užité. ") +
                "Prajem pokojný deň — som tu pre vás.")
    mood = "concerned" if anomalies else "energetic" if part == "ráno" else "calm"
    doc = {"user_id": uid, "date": today, "briefing": apply_watermark(str(text)), "mood": mood,
           "weather": weather, "meds_today": meds_today[:6],
           "upcoming_exams": clean(cal), "alerts": anomalies,
           "followups": [m["text"] for m in recent_mem],
           "at": datetime.now(timezone.utc)}
    await db.agent_briefings.update_one({"user_id": uid, "date": today}, {"$set": doc}, upsert=True)
    xp = await _award_once_daily(uid, 10, "briefing_daily")
    doc["xp_gained"] = xp["gained"]
    doc["level_up"] = xp["level_up"]
    payload = clean(doc)
    _edge_set(cache_key, payload, ttl_s=600)  # warm cache after regen
    return payload

# =========================================================================
# VISUAL THINKING — deep analysis with visible reasoning steps (Orb rays)
# =========================================================================
@api.post("/agent/analyze")
async def agent_analyze(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    docs_n = await db.documents.count_documents({"user_id": uid})
    scans = await db.bioscan_results.find({"user_id": uid}, {"_id": 0}).sort("at", -1).to_list(10)
    meds_n = await db.med_reminders.count_documents({"user_id": uid})
    mems_n = await db.agent_memories.count_documents({"user_id": uid})
    wl_n = await db.waitlist.count_documents({"user_id": uid})
    anomalies = await _detect_anomalies(uid)
    bps = [s.get("bp_estimate") for s in scans if s.get("bp_estimate")][:3]
    steps = [
        {"step": "Otváram zdravotný trezor", "detail": f"{docs_n} dokumentov zabezpečených", "ms": 550},
        {"step": "Analyzujem vitálne trendy", "detail": f"{len(scans)} meraní · TK: {' → '.join(map(str, reversed(bps))) or 'bez dát'}", "ms": 800},
        {"step": "Kontrolujem liekový režim", "detail": f"{meds_n} aktívnych pripomienok", "ms": 500},
        {"step": "Prehľadávam pamäť spoločníka", "detail": f"{mems_n} spomienok · {wl_n} sledovaných termínov", "ms": 650},
        {"step": "Syntéza vzorcov (gpt-5.4)", "detail": f"{len(anomalies)} anomálií zistených", "ms": 900},
    ]
    summary_payload = {
        "documents": docs_n, "scans": len(scans), "meds": meds_n,
        "memories": mems_n, "recent_bp": bps, "anomalies": [a["text"] for a in anomalies],
    }
    sys = ("You are JARVIS 2.0 performing a deep data synthesis. From the JSON stats, produce ONE insight "
           f"in {_lang_name(user)} (2-3 sentences): the single most important pattern or recommendation for the user today. "
           "Plain text, warm, senior-friendly." + AI_COMPLIANCE_NOTE)
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY,
                       session_id=f"agent-an-{uid[:8]}-{uuid.uuid4().hex[:6]}",
                       system_message=sys).with_model("openai", "gpt-5.4")
        insight = await chat.send_message(UserMessage(text=json.dumps(summary_payload, ensure_ascii=False)))
    except Exception as e:
        logger.error(f"analyze error: {e}")
        insight = ("Vaše dáta sú v bezpečí a pod dohľadom. " +
                   (anomalies[0]["text"] if anomalies else "Žiadne anomálie — pokračujte v skvelej starostlivosti."))
    xp = await _award_once_daily(uid, 15, "deep_analysis")
    return {"steps": steps, "insight": apply_watermark(str(insight)), "alerts": anomalies,
            "xp_gained": xp["gained"], "level": xp["level"], "level_up": xp["level_up"]}

# =========================================================================
# VOICE — generic Whisper STT for the full voice conversation
# =========================================================================
@api.post("/agent/transcribe")
async def agent_transcribe(file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(400, "Empty audio")
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(413, "Audio exceeds the 25 MB limit")
    if not EMERGENT_LLM_KEY:
        raise HTTPException(500, "AI key not configured")
    fname = (file.filename or "").lower()
    suffix = ".webm" if (fname.endswith(".webm") or "webm" in (file.content_type or "")) else ".m4a"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        stt = OpenAISpeechToText(api_key=EMERGENT_LLM_KEY)
        result = stt.transcribe(open(tmp_path, "rb"), model="whisper-1",
                                language=(user.get("language") or "sk"))
        if inspect.isawaitable(result):
            result = await result
        if isinstance(result, str):
            transcript = result.strip()
        elif isinstance(result, dict):
            transcript = str(result.get("text", "")).strip()
        else:
            transcript = str(getattr(result, "text", result)).strip()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"agent transcribe error: {e}")
        raise HTTPException(502, "Transcription provider failed")
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    return {"transcript": transcript}


# =========================================================================
# JARVIS ULTRA — SOVEREIGN SEARCH (Perplexity · sonar-reasoning-pro)
# Second brain for real-time web retrieval. Medicine + EU context first.
# Gracefully degrades to gpt-5.4 offline knowledge when no key is present.
# =========================================================================
PPLX_URL = "https://api.perplexity.ai/v1/sonar"
PPLX_MODEL = "sonar-reasoning-pro"  # sonar-reasoning deprecated 2025-12-15

SONAR_SYSTEM = (
    "You are JARVIS ULTRA — the sovereign real-time research brain of Guardian Angel OS. "
    "Use current web sources and cite them. Prioritise MEDICAL topics and EU context: "
    "prefer EMA, ECDC, European Commission, WHO and EU national health authorities when relevant. "
    "Never diagnose or prescribe — inform only; for emergencies advise calling 112. "
    "Be concise, warm and senior-friendly."
)


def _strip_think(text: str) -> str:
    """Reasoning models emit hidden <think> blocks — never expose them."""
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()


class AgentSearchIn(BaseModel):
    query: str
    language: Optional[str] = None


@api.post("/agent/search")
async def agent_search(body: AgentSearchIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    q = (body.query or "").strip()
    if not q:
        raise HTTPException(400, "query required")
    lang = _lang_name(user)
    key = os.environ.get("PERPLEXITY_API_KEY", "").strip()
    now = datetime.now(timezone.utc)

    reply, citations, degraded = "", [], False
    if key:
        payload = {
            "model": PPLX_MODEL,
            "messages": [
                {"role": "system", "content": SONAR_SYSTEM + f" Answer STRICTLY in {lang}."},
                {"role": "user", "content": f"EU context. Question: {q}"},
            ],
            "search_mode": "web",
            "web_search_options": {"search_context_size": "high", "search_type": "auto"},
            "max_tokens": 1200,
            "temperature": 0.1,
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
                r = await client.post(PPLX_URL, json=payload, headers={
                    "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
                r.raise_for_status()
                data = r.json()
                reply = _strip_think(data["choices"][0]["message"]["content"])
                citations = data.get("citations") or [
                    s["url"] for s in (data.get("search_results") or []) if s.get("url")][:8]
        except Exception as e:
            logger.error(f"perplexity search error: {e}")
            reply = ""
    if not reply:
        # Sovereign fallback — offline knowledge via Emergent LLM (no live web)
        degraded = True
        try:
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"sonar-fb-{uid[:8]}-{uuid.uuid4().hex[:6]}",
                system_message=(SONAR_SYSTEM + f" Live web search is OFFLINE — answer from general "
                                f"knowledge, say data may not be current. Answer STRICTLY in {lang}."),
            ).with_model("openai", "gpt-5.4")
            resp = await chat.send_message(UserMessage(text=q[:1000]))
            reply = str(resp or "").strip()
        except Exception as e:
            logger.error(f"sonar fallback error: {e}")
            raise HTTPException(502, "AI service unavailable")

    reply = apply_watermark(reply)
    await db.agent_conversations.insert_many([
        {"conv_id": uuid.uuid4().hex, "user_id": uid, "role": "user", "text": q[:1000], "at": now},
        {"conv_id": uuid.uuid4().hex, "user_id": uid, "role": "agent", "text": reply[:3000],
         "mood": "thinking", "citations": citations, "source": "sonar", "at": now},
    ])
    xp = await award_xp(uid, 6, "sonar_search")
    return {"reply": reply, "citations": citations, "degraded": degraded,
            "live_search": bool(key) and not degraded, "mood": "thinking",
            "xp_gained": xp["gained"], "level": xp["level"], "level_up": xp["level_up"],
            "level_name": LEVEL_NAMES[xp["level"] - 1]}


# =========================================================================
# JARVIS ULTRA — SOVEREIGN VISION FORGE (GPT Image 1 · Emergent LLM key)
# =========================================================================
class AgentImagineIn(BaseModel):
    prompt: str


@api.post("/agent/imagine")
async def agent_imagine(body: AgentImagineIn, authorization: Optional[str] = Header(None)):
    from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
    user = await get_current_user(authorization)
    uid = user["user_id"]
    prompt = (body.prompt or "").strip()
    if not prompt:
        raise HTTPException(400, "prompt required")
    try:
        gen = OpenAIImageGeneration(api_key=EMERGENT_LLM_KEY)
        images = await gen.generate_images(prompt=prompt[:900], model="gpt-image-1", number_of_images=1)
        if not images:
            raise HTTPException(502, "No image was generated")
        image_b64 = base64.b64encode(images[0]).decode("utf-8")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"agent imagine error: {e}")
        raise HTTPException(502, "Image generation unavailable")
    now = datetime.now(timezone.utc)
    await db.agent_conversations.insert_many([
        {"conv_id": uuid.uuid4().hex, "user_id": uid, "role": "user", "text": f"🎨 {prompt[:500]}", "at": now},
        {"conv_id": uuid.uuid4().hex, "user_id": uid, "role": "agent",
         "text": "Vygeneroval som obraz.", "mood": "energetic", "source": "imagine", "at": now},
    ])
    xp = await award_xp(uid, 8, "imagine")
    return {"image_base64": image_b64, "mood": "energetic",
            "xp_gained": xp["gained"], "level": xp["level"], "level_up": xp["level_up"],
            "level_name": LEVEL_NAMES[xp["level"] - 1]}
