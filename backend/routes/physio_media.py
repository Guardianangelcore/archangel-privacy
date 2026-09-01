# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""PHYSIO EXPERT VIDEOS — founder/user-uploaded massage & rehab videos attached to Physio-AI guides.
Founder uploads are GLOBAL (visible to every user — Founder's Expert Series);
regular user uploads are private to their own rehab.
Plus: AUTO-CAPTIONS (Whisper narration → numbered steps for the deaf)
and the WEEKLY RECOVERY PLAYLIST (7-day plan composed from guides + expert videos)."""
import asyncio
import inspect
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException, Header, UploadFile, File, Form, Response
from fastapi.concurrency import run_in_threadpool
from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.llm.openai import OpenAISpeechToText

from core import (
    api, db, clean, logger, get_current_user, send_push,
    APP_NAME, put_object_sync, get_object_sync, EMERGENT_LLM_KEY,
)

MAX_VIDEO = 100 * 1024 * 1024  # 100 MB
MAX_TRANSCRIBE = 24 * 1024 * 1024  # Whisper API hard limit


@api.post("/physio/videos")
async def physio_video_upload(
    file: UploadFile = File(...),
    guide_id: str = Form(...),
    title: str = Form(""),
    authorization: Optional[str] = Header(None),
):
    user = await get_current_user(authorization)
    data = await file.read()
    if not data:
        raise HTTPException(400, "empty file")
    if len(data) > MAX_VIDEO:
        raise HTTPException(400, "File too large (max 100MB)")
    video_id = uuid.uuid4().hex
    ctype = file.content_type or "video/mp4"
    path = f"{APP_NAME}/physio/{user['user_id']}/{video_id}.mp4"
    await run_in_threadpool(put_object_sync, path, data, ctype)
    doc = {"video_id": video_id, "user_id": user["user_id"],
           "guide_id": guide_id.strip()[:60], "title": title.strip()[:120] or "Expert video",
           "author_name": user.get("name") or "Expert",
           "is_global": bool(user.get("is_founder")),
           "content_type": ctype, "size": len(data),
           "transcript_status": "pending" if len(data) <= MAX_TRANSCRIBE else "too_large",
           "storage_path": path, "created_at": datetime.now(timezone.utc)}
    await db.physio_videos.insert_one(doc.copy())
    # ACCESSIBILITY: auto-caption in the background — Jarvis transcribes the narration for the deaf
    if len(data) <= MAX_TRANSCRIBE:
        asyncio.create_task(_transcribe_video_task(video_id, user.get("language") or "en"))
    return {"ok": True, "video": clean(doc)}


@api.get("/physio/videos")
async def physio_videos_list(guide_id: Optional[str] = None,
                             authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    q: dict = {"$or": [{"user_id": user["user_id"]}, {"is_global": True}]}
    if guide_id:
        q["guide_id"] = guide_id
    rows = await db.physio_videos.find(q, {"_id": 0}).sort("created_at", -1).to_list(50)
    for r in rows:
        r["mine"] = r["user_id"] == user["user_id"]
    return {"videos": rows}


@api.get("/physio/videos/{video_id}/file")
async def physio_video_file(video_id: str, token: Optional[str] = None,
                            authorization: Optional[str] = Header(None)):
    if not authorization and token:
        authorization = f"Bearer {token}"
    user = await get_current_user(authorization)
    v = await db.physio_videos.find_one(
        {"video_id": video_id,
         "$or": [{"user_id": user["user_id"]}, {"is_global": True}]}, {"_id": 0})
    if not v:
        raise HTTPException(404, "Video not found")
    try:
        content, ctype = await run_in_threadpool(get_object_sync, v["storage_path"])
    except Exception as ex:
        raise HTTPException(502, f"Storage read failed: {ex}")
    return Response(content=content, media_type=ctype or v.get("content_type") or "video/mp4",
                    headers={"Accept-Ranges": "bytes", "Cache-Control": "private, max-age=86400"})


@api.delete("/physio/videos/{video_id}")
async def physio_video_delete(video_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.physio_videos.delete_one({"video_id": video_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Video not found or not yours")
    return {"ok": True}


# =========================================================================
# AUTO-CAPTIONS — Whisper narration → numbered exercise steps for the deaf
# =========================================================================

async def _structure_steps(transcript: str, language: str) -> list:
    """LLM turns raw narration into clean numbered steps (captions for the deaf)."""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"physio-cc-{uuid.uuid4().hex[:8]}",
            system_message=(
                "You convert a rehab/massage video narration transcript into clear numbered exercise steps "
                "for deaf users. Reply ONLY with a JSON array of 3-10 short strings, no markdown. "
                f"Write the steps in language code '{language[:2] or 'en'}'."
            ),
        ).with_model("anthropic", "claude-sonnet-5")
        resp = await chat.send_message(UserMessage(text=transcript[:3000]))
        m = re.search(r"\[.*\]", str(resp), re.DOTALL)
        if m:
            arr = json.loads(m.group(0))
            steps = [str(s).strip()[:300] for s in arr if str(s).strip()][:10]
            if steps:
                return steps
    except Exception as e:
        logger.warning(f"caption structuring failed: {e}")
    # Fallback: sentence split of the raw transcript
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", transcript) if len(s.strip()) > 3]
    return sents[:8] or [transcript[:300]]


async def _transcribe_video_task(video_id: str, language: str):
    v = await db.physio_videos.find_one({"video_id": video_id}, {"_id": 0})
    if not v:
        return
    await db.physio_videos.update_one({"video_id": video_id}, {"$set": {"transcript_status": "processing"}})
    tmp_path = None
    try:
        if not EMERGENT_LLM_KEY:
            raise RuntimeError("AI key not configured")
        content, _ = await run_in_threadpool(get_object_sync, v["storage_path"])
        if len(content) > MAX_TRANSCRIBE:
            raise RuntimeError("Video is larger than 24 MB — subtitles support shorter videos")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        stt = OpenAISpeechToText(api_key=EMERGENT_LLM_KEY)
        result = stt.transcribe(open(tmp_path, "rb"), model="whisper-1", language=language[:2] or "en")
        if inspect.isawaitable(result):
            result = await result
        if isinstance(result, str):
            transcript = result.strip()
        elif isinstance(result, dict):
            transcript = str(result.get("text", "")).strip()
        else:
            transcript = str(getattr(result, "text", "")).strip()
        if not transcript:
            raise RuntimeError("No spoken narration was found in the video")
        steps = await _structure_steps(transcript, language)
        await db.physio_videos.update_one(
            {"video_id": video_id},
            {"$set": {"transcript": transcript[:4000], "caption_steps": steps,
                      "transcript_status": "done", "transcribed_at": datetime.now(timezone.utc)}})
    except Exception as e:
        logger.warning(f"physio transcribe {video_id}: {e}")
        await db.physio_videos.update_one(
            {"video_id": video_id},
            {"$set": {"transcript_status": "failed", "transcript_error": str(e)[:200]}})
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


@api.post("/physio/videos/{video_id}/transcribe")
async def physio_video_transcribe(video_id: str, authorization: Optional[str] = Header(None)):
    """Manual (re)run of the caption pipeline — owner only."""
    user = await get_current_user(authorization)
    v = await db.physio_videos.find_one({"video_id": video_id, "user_id": user["user_id"]}, {"_id": 0})
    if not v:
        raise HTTPException(404, "Video not found or not yours")
    await _transcribe_video_task(video_id, user.get("language") or "en")
    out = await db.physio_videos.find_one({"video_id": video_id}, {"_id": 0})
    return {"ok": out.get("transcript_status") == "done", "video": clean(out)}


# =========================================================================
# WEEKLY RECOVERY PLAYLIST — 7-day plan guiding the patient through the week
# =========================================================================

WEEKDAYS = {"sk": ["Pondelok", "Utorok", "Streda", "Štvrtok", "Piatok", "Sobota", "Nedeľa"],
            "cs": ["Pondělí", "Úterý", "Středa", "Čtvrtek", "Pátek", "Sobota", "Neděle"],
            "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            "de": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]}

DAY_THEMES = {
    "sk": [("body", "Mobilita a chrbtica"), ("expert", "Expertná masáž"), ("stress", "Uvoľnenie a stres"),
           ("body", "Sila a stabilita"), ("expert", "Lymfa a regenerácia"), ("stress", "Spánok a pokoj"),
           ("recap", "Ľahký deň — zopakuj obľúbené")],
    "cs": [("body", "Mobilita a páteř"), ("expert", "Expertní masáž"), ("stress", "Uvolnění a stres"),
           ("body", "Síla a stabilita"), ("expert", "Lymfa a regenerace"), ("stress", "Spánek a klid"),
           ("recap", "Lehký den — zopakuj oblíbené")],
    "en": [("body", "Mobility & spine"), ("expert", "Expert massage"), ("stress", "Release & stress"),
           ("body", "Strength & stability"), ("expert", "Lymph & regeneration"), ("stress", "Sleep & calm"),
           ("recap", "Light day — repeat favourites")],
    "de": [("body", "Mobilität & Wirbelsäule"), ("expert", "Experten-Massage"), ("stress", "Lösen & Stress"),
           ("body", "Kraft & Stabilität"), ("expert", "Lymphe & Regeneration"), ("stress", "Schlaf & Ruhe"),
           ("recap", "Leichter Tag — Favoriten wiederholen")],
}

ANCHOR_MAP = [("kolen", "knee"), ("chrbt", "spine"), ("záda", "spine"), ("ramen", "shoulders"),
              ("zápäst", "wrists"), ("ruk", "wrists"), ("krk", "cervical"), ("krčn", "cervical")]

# --------- Localized physio messages (pain diary, milestones, pushes) ---------
PHYSIO_MSG = {
    "pain_high": {
        "sk": "Zapísané. Bolesť 8+/10 je signál STOP — dnes už necvičte a ak potrvá do zajtra, kontaktujte lekára.",
        "cs": "Zapsáno. Bolest 8+/10 je signál STOP — dnes už necvičte a pokud potrvá do zítřka, kontaktujte lékaře.",
        "en": "Logged. Pain 8+/10 is a STOP signal — no more exercise today, and if it lasts until tomorrow, contact a doctor.",
        "de": "Notiert. Schmerz 8+/10 ist ein STOPP-Signal — heute nicht mehr trainieren; hält er bis morgen an, kontaktieren Sie einen Arzt.",
    },
    "pain_mid": {
        "sk": "Zapísané. Stredná bolesť — znížte intenzitu a skráťte sériu. Trend sledujem za vás.",
        "cs": "Zapsáno. Střední bolest — snižte intenzitu a zkraťte sérii. Trend sleduji za vás.",
        "en": "Logged. Moderate pain — lower the intensity and shorten the set. I'm tracking the trend for you.",
        "de": "Notiert. Mittlerer Schmerz — Intensität senken und Serie verkürzen. Ich beobachte den Trend für Sie.",
    },
    "pain_low": {
        "sk": "Zapísané. Nízka bolesť — výborné, telo sa hojí. Len tak ďalej!",
        "cs": "Zapsáno. Nízká bolest — výborně, tělo se hojí. Jen tak dál!",
        "en": "Logged. Low pain — excellent, your body is healing. Keep it up!",
        "de": "Notiert. Geringer Schmerz — ausgezeichnet, der Körper heilt. Weiter so!",
    },
    "milestone": {
        "sk": "🎉 MÍĽNIK ZOTAVENIA! Priemer bolesti klesol na {avg}/10 — hojenie krásne napreduje. Oslavujeme!",
        "cs": "🎉 MILNÍK ZOTAVENÍ! Průměr bolesti klesl na {avg}/10 — hojení krásně postupuje. Slavíme!",
        "en": "🎉 RECOVERY MILESTONE! Average pain dropped to {avg}/10 — healing is progressing beautifully. Celebrate!",
        "de": "🎉 GENESUNGS-MEILENSTEIN! Der Schmerzdurchschnitt fiel auf {avg}/10 — die Heilung macht schöne Fortschritte!",
    },
    "week_done_title": {
        "sk": "🏆 TÝŽDEŇ ZOTAVENIA DOKONČENÝ", "cs": "🏆 TÝDEN ZOTAVENÍ DOKONČEN",
        "en": "🏆 RECOVERY WEEK COMPLETED", "de": "🏆 GENESUNGSWOCHE ABGESCHLOSSEN",
    },
    "week_done_msg": {
        "sk": "Celý 7-dňový plán splnený — Jarvis vám gratuluje. Zajtra môžete zostaviť nový.",
        "cs": "Celý 7denní plán splněn — Jarvis vám gratuluje. Zítra můžete sestavit nový.",
        "en": "Full 7-day plan completed — Jarvis congratulates you. You can build a new one tomorrow.",
        "de": "Der ganze 7-Tage-Plan ist erfüllt — Jarvis gratuliert. Morgen können Sie einen neuen erstellen.",
    },
    "reminder_title": {
        "sk": "🧘 JARVIS — VEČERNÁ PRIPOMIENKA", "cs": "🧘 JARVIS — VEČERNÍ PŘIPOMÍNKA",
        "en": "🧘 JARVIS — EVENING REMINDER", "de": "🧘 JARVIS — ABENDERINNERUNG",
    },
    "reminder_msg": {
        "sk": "Dnešný deň plánu ({theme}) ešte nie je odškrtnutý. 10 minút pred spaním stačí — telo sa vám poďakuje.",
        "cs": "Dnešní den plánu ({theme}) ještě není odškrtnutý. 10 minut před spaním stačí — tělo vám poděkuje.",
        "en": "Today's plan day ({theme}) is not checked off yet. 10 minutes before bed is enough — your body will thank you.",
        "de": "Der heutige Plantag ({theme}) ist noch nicht abgehakt. 10 Minuten vor dem Schlafen genügen — Ihr Körper dankt es Ihnen.",
    },
}

def _pmsg(key: str, lang: Optional[str], **kw) -> str:
    d = PHYSIO_MSG[key]
    return d.get((lang or "en")[:2], d["en"]).format(**kw)


def _guide_index(lang: str) -> list:
    from content import PHYSIO_GUIDES
    from content_physio import PHYSIO_EXTRA, PHYSIO_CATEGORY
    lk = lang[:2] if lang[:2] in PHYSIO_EXTRA else "en"
    out = []
    for g in PHYSIO_GUIDES.get(lk, PHYSIO_GUIDES["en"]):
        out.append({"id": g["id"], "title": g["title"], "icon": g.get("icon", "body-outline"),
                    "category": PHYSIO_CATEGORY.get(g["id"], "body")})
    for g in PHYSIO_EXTRA.get(lk, PHYSIO_EXTRA["en"]):
        out.append({"id": g["id"], "title": g["title"], "icon": g.get("icon", "body-outline"),
                    "category": g.get("category", "body")})
    return out


@api.post("/physio/plan/generate")
async def physio_plan_generate(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    lang = (user.get("language") or "en")[:2]
    lk = lang if lang in DAY_THEMES else "en"
    guides = _guide_index(lk)
    by_cat: dict = {"body": [], "expert": [], "stress": []}
    for g in guides:
        by_cat.setdefault(g["category"], []).append(g)
    videos = await db.physio_videos.find(
        {"$or": [{"user_id": uid}, {"is_global": True}]}, {"_id": 0}).sort("created_at", -1).to_list(30)

    # DAILY ANCHOR — if an active healing journey targets a body part, that guide opens every day
    anchor = None
    j = await db.healing_journeys.find_one({"user_id": uid, "status": "active"}, {"_id": 0})
    if j:
        hint = f"{j.get('body_part') or ''} {j.get('specialty') or ''}".lower()
        for kw, gid in ANCHOR_MAP:
            if kw in hint:
                anchor = next((g for g in guides if g["id"] == gid), None)
                if anchor:
                    break

    today = datetime.now(timezone.utc).date()
    monday = today - timedelta(days=today.weekday())
    used_video_ids: set = set()
    days = []
    for i, (cat, theme) in enumerate(DAY_THEMES[lk]):
        items = []
        if anchor:
            items.append({"type": "guide", "id": anchor["id"], "title": anchor["title"],
                          "icon": anchor["icon"], "anchor": True})
        if cat == "recap":
            for c in ("body", "expert", "stress"):
                if by_cat.get(c):
                    g = by_cat[c][i % len(by_cat[c])]
                    if not any(x["id"] == g["id"] and x["type"] == "guide" for x in items):
                        items.append({"type": "guide", "id": g["id"], "title": g["title"], "icon": g["icon"]})
        else:
            pool = by_cat.get(cat) or []
            for k in range(2):
                if pool:
                    g = pool[(i + k) % len(pool)]
                    if not any(x["id"] == g["id"] and x["type"] == "guide" for x in items):
                        items.append({"type": "guide", "id": g["id"], "title": g["title"], "icon": g["icon"]})
        # Attach expert videos whose guide is trained today
        day_gids = {x["id"] for x in items if x["type"] == "guide"}
        for v in videos:
            if v["video_id"] not in used_video_ids and v.get("guide_id") in day_gids:
                items.append({"type": "video", "id": v["video_id"], "guide_id": v["guide_id"],
                              "title": f"🎬 {v['title']}", "icon": "videocam-outline"})
                used_video_ids.add(v["video_id"])
        days.append({"day": i + 1, "weekday": WEEKDAYS[lk][i],
                     "date": (monday + timedelta(days=i)).isoformat(),
                     "theme": theme, "items": items, "done": False})
    # Spread remaining expert videos over the expert days (2 and 5)
    leftovers = [v for v in videos if v["video_id"] not in used_video_ids]
    for idx, v in enumerate(leftovers[:6]):
        d = days[1 if idx % 2 == 0 else 4]
        d["items"].append({"type": "video", "id": v["video_id"], "guide_id": v.get("guide_id"),
                           "title": f"🎬 {v['title']}", "icon": "videocam-outline"})

    plan = {"plan_id": uuid.uuid4().hex, "user_id": uid, "language": lk,
            "week_start": monday.isoformat(), "anchor_guide": (anchor or {}).get("id"),
            "days": days, "created_at": datetime.now(timezone.utc)}
    await db.physio_plans.delete_many({"user_id": uid})
    await db.physio_plans.insert_one(plan.copy())
    return {"ok": True, "plan": clean(plan)}


@api.get("/physio/plan")
async def physio_plan_get(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    plan = await db.physio_plans.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not plan:
        return {"plan": None}
    # LANGUAGE CONSISTENCY — if the user switched language after generating the plan,
    # re-localize weekdays, day themes and guide titles on the fly.
    lang = (user.get("language") or "en")[:2]
    lk = lang if lang in DAY_THEMES else "en"
    if plan.get("language") != lk:
        titles = {g["id"]: g["title"] for g in _guide_index(lk)}
        for i, d in enumerate(plan["days"][:7]):
            d["weekday"] = WEEKDAYS[lk][i]
            d["theme"] = DAY_THEMES[lk][i][1]
            for it in d.get("items", []):
                if it.get("type") == "guide" and it.get("id") in titles:
                    it["title"] = titles[it["id"]]
        plan["language"] = lk
        await db.physio_plans.update_one({"plan_id": plan["plan_id"]},
                                         {"$set": {"days": plan["days"], "language": lk}})
    done = sum(1 for d in plan["days"] if d.get("done"))
    return {"plan": clean(plan), "done_days": done, "progress_pct": int(done / 7 * 100)}


@api.post("/physio/plan/day/{day}/complete")
async def physio_plan_day_done(day: int, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if not 1 <= day <= 7:
        raise HTTPException(400, "day must be 1..7")
    res = await db.physio_plans.update_one(
        {"user_id": user["user_id"], "days.day": day}, {"$set": {"days.$.done": True}})
    if res.matched_count == 0:
        raise HTTPException(404, "No plan found")
    plan = await db.physio_plans.find_one({"user_id": user["user_id"]}, {"_id": 0})
    done = sum(1 for d in plan["days"] if d.get("done"))
    if done == 7:
        try:
            _wl = user.get("language")
            await send_push(recipients=[user["user_id"]], data={
                "title": _pmsg("week_done_title", _wl),
                "message": _pmsg("week_done_msg", _wl),
                "action_url": "/physio"})
        except Exception:
            pass
    return {"ok": True, "done_days": done, "week_complete": done == 7}


# =========================================================================
# EVENING EXERCISE REMINDER — Jarvis nudges when today's plan day isn't done
# =========================================================================

async def physio_reminder_sweep(force: bool = False) -> int:
    now = datetime.now(timezone.utc)
    prague = now + timedelta(hours=2)
    if not force and not (18 <= prague.hour < 21):
        return 0
    today = prague.date().isoformat()
    sent = 0
    async for plan in db.physio_plans.find({}, {"_id": 0, "user_id": 1, "days": 1}):
        day = next((d for d in plan["days"] if d.get("date") == today), None)
        if not day or day.get("done"):
            continue
        if await db.physio_reminders.find_one({"user_id": plan["user_id"], "date": today}):
            continue
        try:
            _ru = await db.users.find_one({"user_id": plan["user_id"]}, {"_id": 0, "language": 1}) or {}
            _rl = _ru.get("language")
            await send_push(recipients=[plan["user_id"]], data={
                "title": _pmsg("reminder_title", _rl),
                "message": _pmsg("reminder_msg", _rl, theme=day.get('theme', '')),
                "action_url": "/physio"})
        except Exception as e:
            logger.warning(f"physio reminder push: {e}")
        await db.physio_reminders.insert_one({"user_id": plan["user_id"], "date": today, "created_at": now})
        sent += 1
    return sent


@api.post("/physio/plan/remind-sweep")
async def physio_remind_now(authorization: Optional[str] = Header(None)):
    """Manual trigger (testing) — bypasses the evening window, respects daily dedup."""
    await get_current_user(authorization)
    sent = await physio_reminder_sweep(force=True)
    return {"ok": True, "reminders_sent": sent}


# =========================================================================
# PAIN DIARY — 1-10 after every exercise; trend goes to the doctor's report
# =========================================================================

from pydantic import BaseModel


class PainIn(BaseModel):
    level: int                 # 1..10
    guide_id: Optional[str] = None
    note: Optional[str] = ""


@api.post("/physio/pain")
async def pain_log(body: PainIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if not 1 <= body.level <= 10:
        raise HTTPException(400, "level must be 1..10")
    doc = {"entry_id": uuid.uuid4().hex, "user_id": user["user_id"],
           "level": body.level, "guide_id": (body.guide_id or "")[:60] or None,
           "note": (body.note or "")[:200], "created_at": datetime.now(timezone.utc)}
    await db.pain_diary.insert_one(doc.copy())
    _pl = user.get("language")
    if body.level >= 8:
        reply = _pmsg("pain_high", _pl)
    elif body.level >= 5:
        reply = _pmsg("pain_mid", _pl)
    else:
        reply = _pmsg("pain_low", _pl)
    milestone, m_msg = await check_pain_milestone(user["user_id"], _pl)
    return {"ok": True, "reply": reply, "entry": clean(doc),
            "milestone": milestone, "milestone_message": m_msg}


async def check_pain_milestone(uid: str, lang: Optional[str] = None):
    """RECOVERY MILESTONE — celebrate every full-point drop of the 14-day pain average."""
    since = datetime.now(timezone.utc) - timedelta(days=14)
    rows = await db.pain_diary.find(
        {"user_id": uid, "created_at": {"$gte": since}}, {"_id": 0, "level": 1}).to_list(200)
    levels = [r["level"] for r in rows]
    if len(levels) < 3:
        return False, ""
    avg = round(sum(levels) / len(levels), 1)
    floor_now = int(avg)
    prev = await db.pain_milestones.find_one({"user_id": uid}, {"_id": 0})
    now = datetime.now(timezone.utc)
    if prev is None:
        await db.pain_milestones.insert_one({"user_id": uid, "best_floor": floor_now, "updated_at": now})
        return False, ""
    if floor_now < prev["best_floor"]:
        await db.pain_milestones.update_one(
            {"user_id": uid}, {"$set": {"best_floor": floor_now, "updated_at": now}})
        return True, _pmsg("milestone", lang, avg=avg)
    return False, ""


@api.get("/physio/pain/trends")
async def pain_trends(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    since = datetime.now(timezone.utc) - timedelta(days=14)
    rows = await db.pain_diary.find(
        {"user_id": user["user_id"], "created_at": {"$gte": since}}, {"_id": 0}
    ).sort("created_at", 1).to_list(100)
    levels = [r["level"] for r in rows]
    avg = round(sum(levels) / len(levels), 1) if levels else None
    direction = "stable"
    if len(levels) >= 4:
        half = len(levels) // 2
        a, b = sum(levels[:half]) / half, sum(levels[half:]) / (len(levels) - half)
        direction = "improving" if a - b > 0.5 else ("worsening" if b - a > 0.5 else "stable")
    return {"entries": rows, "avg_14d": avg, "trend": direction, "count": len(rows)}
