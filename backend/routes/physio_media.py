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
           "guide_id": guide_id.strip()[:60], "title": title.strip()[:120] or "Expertné video",
           "author_name": user.get("name") or "Expert",
           "is_global": bool(user.get("is_founder")),
           "content_type": ctype, "size": len(data),
           "transcript_status": "pending" if len(data) <= MAX_TRANSCRIBE else "too_large",
           "storage_path": path, "created_at": datetime.now(timezone.utc)}
    await db.physio_videos.insert_one(doc.copy())
    # ACCESSIBILITY: auto-caption in the background — Jarvis transcribes the narration for the deaf
    if len(data) <= MAX_TRANSCRIBE:
        asyncio.create_task(_transcribe_video_task(video_id, user.get("language") or "sk"))
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
                f"Write the steps in language code '{language[:2] or 'sk'}'."
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
            raise RuntimeError("Video je väčšie ako 24 MB — titulky podporujú kratšie videá")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        stt = OpenAISpeechToText(api_key=EMERGENT_LLM_KEY)
        result = stt.transcribe(open(tmp_path, "rb"), model="whisper-1", language=language[:2] or "sk")
        if inspect.isawaitable(result):
            result = await result
        if isinstance(result, str):
            transcript = result.strip()
        elif isinstance(result, dict):
            transcript = str(result.get("text", "")).strip()
        else:
            transcript = str(getattr(result, "text", "")).strip()
        if not transcript:
            raise RuntimeError("Vo videu sa nenašla hovorená narácia")
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
    await _transcribe_video_task(video_id, user.get("language") or "sk")
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


def _guide_index(lang: str) -> list:
    from content import PHYSIO_GUIDES
    from content_physio import PHYSIO_EXTRA, PHYSIO_CATEGORY
    lk = lang[:2] if lang[:2] in PHYSIO_EXTRA else "sk"
    out = []
    for g in PHYSIO_GUIDES.get(lk, PHYSIO_GUIDES["sk"]):
        out.append({"id": g["id"], "title": g["title"], "icon": g.get("icon", "body-outline"),
                    "category": PHYSIO_CATEGORY.get(g["id"], "body")})
    for g in PHYSIO_EXTRA.get(lk, PHYSIO_EXTRA["sk"]):
        out.append({"id": g["id"], "title": g["title"], "icon": g.get("icon", "body-outline"),
                    "category": g.get("category", "body")})
    return out


@api.post("/physio/plan/generate")
async def physio_plan_generate(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    lang = (user.get("language") or "sk")[:2]
    lk = lang if lang in DAY_THEMES else "sk"
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
            await send_push(recipients=[user["user_id"]], data={
                "title": "🏆 TÝŽDEŇ ZOTAVENIA DOKONČENÝ",
                "message": "Celý 7-dňový plán splnený — Jarvis vám gratuluje. Zajtra môžete zostaviť nový.",
                "action_url": "/physio"})
        except Exception:
            pass
    return {"ok": True, "done_days": done, "week_complete": done == 7}
