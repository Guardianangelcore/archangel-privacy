# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
from fastapi import HTTPException, Header, UploadFile, File, Form
from fastapi.responses import Response, StreamingResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import os, uuid, hashlib, json, io, re, base64, httpx

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

from core import (
    api, db, logger, clean, get_current_user, send_push, _push_client,
    AI_COMPLIANCE_NOTE, _aml_ledger_append,
    AML_UNVERIFIED_DAILY, AML_VERIFIED_DAILY, AML_MAX_TX_PER_DAY,
    _FONT_R, _FONT_B, _make_pdf, _auth_pdf, _pdf_footer, _pdf_response,
    APP_NAME, put_object_sync, get_object_sync, init_storage,
    EMERGENT_LLM_KEY, AUTH_SESSION_URL,
)
from models import User, EmergencyProfile, Document, WaitlistItem, FallEvent
from core import LANG_NAMES

# --------- EMERGENCY PROFILE ---------
class EmergencyIn(BaseModel):
    full_name: Optional[str] = ""
    blood_type: Optional[str] = ""
    allergies: Optional[str] = ""
    medications: Optional[str] = ""
    conditions: Optional[str] = ""
    emergency_contact_name: Optional[str] = ""
    emergency_contact_phone: Optional[str] = ""
    is_donor: bool = False
    donor_organs: Optional[str] = ""
    life_testament: Optional[str] = ""

@api.get("/emergency-profile")
async def get_emergency(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    prof = await db.emergency_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not prof:
        prof = EmergencyProfile(user_id=user["user_id"]).model_dump()
    return prof

@api.put("/emergency-profile")
async def put_emergency(body: EmergencyIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    doc = body.model_dump()
    doc["user_id"] = user["user_id"]
    doc["updated_at"] = datetime.now(timezone.utc)
    await db.emergency_profiles.update_one(
        {"user_id": user["user_id"]}, {"$set": doc}, upsert=True
    )
    return await db.emergency_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})

@api.get("/emergency-qr/{did}")
async def public_emergency(did: str):
    """Public read-only for QR scans — surfaces critical info only."""
    user = await db.users.find_one({"did": did}, {"_id": 0})
    if not user:
        raise HTTPException(404, "Not found")
    prof = await db.emergency_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    proxy = await db.proxy_directives.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    return {
        "did": did,
        "full_name": prof.get("full_name") or user.get("name"),
        "blood_type": prof.get("blood_type"),
        "allergies": prof.get("allergies"),
        "conditions": prof.get("conditions"),
        "medications": prof.get("medications"),
        "emergency_contact_name": prof.get("emergency_contact_name"),
        "emergency_contact_phone": prof.get("emergency_contact_phone"),
        "is_donor": prof.get("is_donor", False),
        "donor_organs": prof.get("donor_organs"),
        "healthcare_proxy": {
            "name": proxy.get("proxy_full_name"),
            "relationship": proxy.get("proxy_relationship"),
            "phone": proxy.get("proxy_phone"),
            "scope": proxy.get("scope"),
            "doc_hash": proxy.get("doc_hash"),
        } if proxy.get("proxy_full_name") else None,
    }


# --------- PUSH NOTIFICATIONS (Emergent managed) ---------
class RegisterPushBody(BaseModel):
    user_id: str
    platform: str   # "android" | "ios"
    device_token: str

@api.post("/register-push", status_code=201)
async def register_push(body: RegisterPushBody):
    resp = await _push_client.post("/api/v1/push/users/register", json=body.model_dump())
    if resp.status_code == 401:
        raise HTTPException(500, "EMERGENT_PUSH_KEY missing or invalid")
    if resp.status_code >= 500:
        raise HTTPException(502, "Push provider unavailable")
    resp.raise_for_status()
    return {"status": "registered"}

# --------- FALL DETECTION ---------
class FallIn(BaseModel):
    verified: bool = False
    cancelled: bool = False

@api.post("/fall-event")
async def log_fall(body: FallIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    ev = FallEvent(event_id=uuid.uuid4().hex, user_id=user["user_id"], **body.model_dump()).model_dump()
    await db.fall_events.insert_one(ev.copy())
    return clean(ev)

@api.get("/fall-events")
async def list_falls(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    events = await db.fall_events.find({"user_id": user["user_id"]}, {"_id": 0}).sort("triggered_at", -1).to_list(50)
    return events


# --------- INCLUSIVE RESPECT MAP ---------
class ProviderIn(BaseModel):
    name: str
    city: str
    specialty: str
    respect_score: int = Field(ge=1, le=5)
    tags: List[str] = []
    review: Optional[str] = ""
    minority_safety: Optional[int] = Field(default=None, ge=1, le=5)
    waiting_weeks: Optional[int] = Field(default=None, ge=0)
    financial_transparency: Optional[int] = Field(default=None, ge=1, le=5)

@api.get("/respect/providers")
async def list_providers(city: Optional[str] = None, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    q = {}
    if city:
        q["city"] = city
    docs = await db.providers.find(q, {"_id": 0}).sort("avg_score", -1).to_list(500)
    return docs

def _merge_metric(existing: dict, avg_key: str, cnt_key: str, new_val: Optional[float]) -> dict:
    if new_val is None:
        return {}
    old_avg = existing.get(avg_key) or 0.0
    old_cnt = existing.get(cnt_key) or 0
    new_cnt = old_cnt + 1
    return {avg_key: (old_avg * old_cnt + new_val) / new_cnt, cnt_key: new_cnt}

@api.post("/respect/providers")
async def add_provider(body: ProviderIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    existing = await db.providers.find_one({"name": body.name, "city": body.city}, {"_id": 0})
    if existing:
        pid = existing["provider_id"]
        new_count = existing["review_count"] + 1
        new_avg = (existing["avg_score"] * existing["review_count"] + body.respect_score) / new_count
        upd = {"avg_score": new_avg, "review_count": new_count, "tags": list(set(existing.get("tags", []) + body.tags))}
        upd.update(_merge_metric(existing, "avg_minority_safety", "minority_safety_count", body.minority_safety))
        upd.update(_merge_metric(existing, "avg_waiting_weeks", "waiting_weeks_count", body.waiting_weeks))
        upd.update(_merge_metric(existing, "avg_financial_transparency", "financial_transparency_count", body.financial_transparency))
        await db.providers.update_one({"provider_id": pid}, {"$set": upd})
    else:
        pid = uuid.uuid4().hex
        await db.providers.insert_one({
            "provider_id": pid,
            "name": body.name, "city": body.city, "specialty": body.specialty,
            "tags": body.tags,
            "avg_score": float(body.respect_score),
            "review_count": 1,
            "avg_minority_safety": float(body.minority_safety) if body.minority_safety else None,
            "minority_safety_count": 1 if body.minority_safety else 0,
            "avg_waiting_weeks": float(body.waiting_weeks) if body.waiting_weeks is not None else None,
            "waiting_weeks_count": 1 if body.waiting_weeks is not None else 0,
            "avg_financial_transparency": float(body.financial_transparency) if body.financial_transparency else None,
            "financial_transparency_count": 1 if body.financial_transparency else 0,
            "created_by": user["user_id"],
            "created_at": datetime.now(timezone.utc),
        })
    if body.review:
        await db.provider_reviews.insert_one({
            "provider_id": pid, "user_id": user["user_id"],
            "score": body.respect_score, "review": body.review, "tags": body.tags,
            "minority_safety": body.minority_safety, "waiting_weeks": body.waiting_weeks,
            "financial_transparency": body.financial_transparency,
            "created_at": datetime.now(timezone.utc),
        })
    return await db.providers.find_one({"provider_id": pid}, {"_id": 0})


# --------- WELLNESS MONITORING (Angel Mode) ---------
class CheckinIn(BaseModel):
    mood: Optional[int] = None  # 1-5 quick pick
    feeling_text: Optional[str] = ""
    language: str = "sk"

@api.post("/wellness/checkin")
async def wellness_checkin(body: CheckinIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    lang = LANG_NAMES.get(body.language, "Slovak")
    described = (body.feeling_text or "").strip()
    mood_map = {1: "very bad", 2: "bad", 3: "tired/neutral", 4: "good", 5: "great"}
    mood_hint = mood_map.get(body.mood or 0, "not specified")
    system = (
        f"You are Jarvis, the caring Guardian Angel wellness companion for a senior. "
        f"The user answered the daily check-in. Reply warmly in 2-3 short sentences in {lang}. "
        f"If they feel bad, gently suggest one simple action (drink water, rest, call family, or dial 155 if serious). "
        f"Return STRICT JSON only: {{\"reply\": \"...\", \"sentiment_score\": <1-5 integer>, \"summary\": \"<3-6 word status for the family dashboard in {lang}>\"}}"
    )
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"wellness-{user['user_id']}-{uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-5")
    reply, score, summary = "", body.mood or 3, described[:60] or mood_hint
    try:
        resp = await chat.send_message(UserMessage(text=f"Quick mood pick: {mood_hint}. User said: {described or '(nothing typed)'}"))
        m = re.search(r"\{.*\}", resp, re.DOTALL)
        parsed = json.loads(m.group(0)) if m else {}
        reply = parsed.get("reply", resp)
        score = int(parsed.get("sentiment_score", score))
        summary = parsed.get("summary", summary)
    except Exception as e:
        logger.error(f"wellness ai err {e}")
        reply = "Thank you, I have recorded it. Have a nice day!"
    doc = {
        "checkin_id": uuid.uuid4().hex,
        "user_id": user["user_id"],
        "mood": body.mood,
        "feeling_text": described,
        "sentiment_score": max(1, min(5, score)),
        "summary": summary,
        "reply": reply,
        "created_at": datetime.now(timezone.utc),
    }
    await db.wellness_checkins.insert_one(doc.copy())
    return clean(doc)

@api.get("/wellness/checkins")
async def wellness_checkins(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.wellness_checkins.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(30)

class VitalsIn(BaseModel):
    steps: Optional[int] = None
    heart_rate: Optional[int] = None

@api.post("/wellness/vitals")
async def wellness_vitals(body: VitalsIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if not upd:
        raise HTTPException(400, "Nothing to record")
    upd["updated_at"] = datetime.now(timezone.utc)
    await db.wellness_vitals.update_one(
        {"user_id": user["user_id"], "date": day},
        {"$set": upd, "$setOnInsert": {"user_id": user["user_id"], "date": day}},
        upsert=True,
    )
    return await db.wellness_vitals.find_one({"user_id": user["user_id"], "date": day}, {"_id": 0})

class InactivityIn(BaseModel):
    hours_inactive: int = 6

@api.post("/wellness/inactivity-alert")
async def inactivity_alert(body: InactivityIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    prof = await db.emergency_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    doc = {
        "alert_id": uuid.uuid4().hex,
        "user_id": user["user_id"],
        "hours_inactive": body.hours_inactive,
        "contact_notified": prof.get("emergency_contact_name") or None,
        "created_at": datetime.now(timezone.utc),
    }
    await db.inactivity_alerts.insert_one(doc.copy())
    try:
        await send_push(
            recipients=[user["user_id"]],
            data={
                "title": "Guardian Angel ⚠️",
                "message": f"No movement {body.hours_inactive} h. Contacting: {prof.get('emergency_contact_name') or 'family'}.",
                "action_url": "/wellness",
            },
        )
    except Exception as e:
        logger.warning(f"Push failed (non-blocking): {e}")
    return clean(doc)

@api.get("/wellness/dashboard")
async def wellness_dashboard(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    checkins = await db.wellness_checkins.find({"user_id": uid}, {"_id": 0}).sort("created_at", -1).to_list(7)
    vitals = await db.wellness_vitals.find({"user_id": uid}, {"_id": 0}).sort("date", -1).to_list(7)
    falls = await db.fall_events.find({"user_id": uid}, {"_id": 0}).sort("triggered_at", -1).to_list(5)
    inactivity = await db.inactivity_alerts.find({"user_id": uid}, {"_id": 0}).sort("created_at", -1).to_list(5)

    steps_vals = [v["steps"] for v in vitals if v.get("steps")]
    hr_vals = [v["heart_rate"] for v in vitals if v.get("heart_rate")]
    avg_steps = round(sum(steps_vals) / len(steps_vals)) if steps_vals else 0
    avg_hr = round(sum(hr_vals) / len(hr_vals)) if hr_vals else 0

    anomalies = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_v = next((v for v in vitals if v["date"] == today), None)
    if today_v and avg_steps and today_v.get("steps") is not None and len(steps_vals) >= 3 and today_v["steps"] < avg_steps * 0.5:
        anomalies.append({"type": "low_steps", "detail": f"{today_v['steps']} vs avg {avg_steps}"})
    if today_v and avg_hr and today_v.get("heart_rate") and len(hr_vals) >= 3 and abs(today_v["heart_rate"] - avg_hr) > avg_hr * 0.2:
        anomalies.append({"type": "heart_rate_deviation", "detail": f"{today_v['heart_rate']} vs avg {avg_hr}"})
    scores = [c["sentiment_score"] for c in checkins if c.get("sentiment_score")]
    if scores and scores[0] <= 2:
        anomalies.append({"type": "low_mood", "detail": checkins[0].get("summary", "")})

    return {
        "checkins": checkins,
        "vitals": vitals,
        "fall_events": falls,
        "inactivity_alerts": inactivity,
        "avg_steps": avg_steps,
        "avg_heart_rate": avg_hr,
        "anomalies": anomalies,
        "checked_in_today": bool(checkins and str(checkins[0]["created_at"])[:10] == today),
    }

# --------- JARVIS ADVISOR (cross-module proactive advice) ---------
class AdviceIn(BaseModel):
    module: str = "general"
    context: str = ""
    language: str = "sk"

@api.post("/ai/advice")
async def ai_advice(body: AdviceIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    lang = LANG_NAMES.get(body.language, "Slovak")
    system = (
        f"You are Jarvis, the proactive Guardian Angel advisor. The user is in the '{body.module}' module. "
        f"Give warm, practical, senior-friendly advice in max 4 short sentences based on the provided data. "
        f"Be specific and actionable. Respond ONLY in {lang}." + AI_COMPLIANCE_NOTE
    )
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"advice-{user['user_id']}-{uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-5")
    try:
        resp = await chat.send_message(UserMessage(text=body.context[:4000] or "No data yet — give a starter tip for this module."))
        return {"advice": resp}
    except Exception as e:
        logger.error(f"advice err {e}")
        raise HTTPException(502, "AI unavailable")


# --------- AI SCAM SHIELD ---------
class ScamCheckIn(BaseModel):
    text: str
    language: str = "sk"

@api.post("/scam/check")
async def scam_check(body: ScamCheckIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if not body.text.strip():
        raise HTTPException(400, "Empty text")
    lang = LANG_NAMES.get(body.language, "Slovak")
    system = (
        f"You are the Guardian Scam Shield protecting seniors from fraud. Analyze the message/link for "
        f"phishing, vishing, fake bank/parcel/lottery scams, urgency manipulation, and grandparent scams. "
        f"Return STRICT JSON only: {{\"risk\": \"low\"|\"medium\"|\"high\", \"verdict\": \"<one sentence in {lang}>\", "
        f"\"reasons\": [\"<up to 3 short reasons in {lang}>\"], \"advice\": \"<what the user should do now, in {lang}>\"}}"
    )
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"scam-{user['user_id']}-{uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-5")
    risk, verdict, reasons, advice = "medium", "Analysis failed — be careful.", [], "Never send money or codes."
    try:
        resp = await chat.send_message(UserMessage(text=body.text[:4000]))
        m = re.search(r"\{.*\}", resp, re.DOTALL)
        parsed = json.loads(m.group(0)) if m else {}
        risk = parsed.get("risk", risk)
        verdict = parsed.get("verdict", verdict)
        reasons = parsed.get("reasons", [])
        advice = parsed.get("advice", advice)
    except Exception as e:
        logger.error(f"scam ai err {e}")
    doc = {
        "check_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "text": body.text[:1000], "risk": risk, "verdict": verdict,
        "reasons": reasons, "advice": advice, "created_at": datetime.now(timezone.utc),
    }
    await db.scam_checks.insert_one(doc.copy())
    if risk == "high":
        prof = await db.emergency_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
        try:
            await send_push(
                recipients=[user["user_id"]],
                data={"title": "🛡️ SCAM SHIELD — HIGH RISK", "message": f"Fraudulent message detected. Alerting: {prof.get('emergency_contact_name') or 'family'}.", "action_url": "/scam-shield"},
            )
        except Exception as e:
            logger.warning(f"push failed: {e}")
    return clean(doc)

@api.get("/scam/history")
async def scam_history(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.scam_checks.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(30)


# --------- EMERGENCY BEACON (Stealth Mode) ---------
class BeaconIn(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    note: Optional[str] = ""

@api.post("/beacon/trigger")
async def beacon_trigger(body: BeaconIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    prof = await db.emergency_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    doc = {
        "beacon_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "lat": body.lat, "lng": body.lng, "note": body.note,
        "contact_notified": prof.get("emergency_contact_name") or None,
        "created_at": datetime.now(timezone.utc),
    }
    await db.beacon_events.insert_one(doc.copy())
    loc = f"https://maps.google.com/?q={body.lat},{body.lng}" if body.lat is not None else "location unavailable"
    try:
        await send_push(
            recipients=[user["user_id"]],
            data={"title": "🔴 SILENT BEACON ACTIVATED", "message": f"Signal sent to family. {loc}", "action_url": "/family-dashboard"},
        )
    except Exception as e:
        logger.warning(f"push failed: {e}")
    return clean(doc)

@api.get("/beacon/history")
async def beacon_history(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.beacon_events.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(20)


# --------- EMERGENCY LOCKSCREEN WALLPAPER ---------

def _make_wallpaper(user: dict, prof: dict) -> bytes:
    from PIL import Image as PILImage, ImageDraw, ImageFont
    import qrcode
    W, H = 1080, 1920
    img = PILImage.new("RGB", (W, H), "#121212")
    draw = ImageDraw.Draw(img)
    f_big = ImageFont.truetype(_FONT_B, 54)
    f_med = ImageFont.truetype(_FONT_B, 44)
    f_sm = ImageFont.truetype(_FONT_R, 36)
    f_tiny = ImageFont.truetype(_FONT_R, 26)
    gold = "#D4AF37"

    def center(text, y, font, fill):
        w = draw.textlength(text, font=font)
        draw.text(((W - w) / 2, y), text, font=font, fill=fill)

    # Lockscreen clock occupies top ~30% — keep it clear
    y = 640
    center("＋ MEDICAL ID · IN EMERGENCY ＋", y, f_med, gold); y += 90
    name = prof.get("full_name") or user.get("name") or ""
    if name:
        center(name, y, f_big, "#F5F5F5"); y += 100
    rows = [
        ("BLOOD TYPE", prof.get("blood_type")),
        ("ALLERGIES", prof.get("allergies")),
        ("ICE CONTACT", f"{prof.get('emergency_contact_name') or ''} {prof.get('emergency_contact_phone') or ''}".strip()),
    ]
    for label, val in rows:
        if not val:
            continue
        center(label, y, f_tiny, "#8E8E93"); y += 42
        center(str(val)[:44], y, f_med, "#F5F5F5"); y += 84

    # QR — offline payload, readable by any scanner without unlocking the phone
    payload = json.dumps({
        "did": user.get("did"),
        "name": name,
        "blood": prof.get("blood_type"),
        "allergies": prof.get("allergies"),
        "ice": f"{prof.get('emergency_contact_name') or ''} {prof.get('emergency_contact_phone') or ''}".strip(),
    }, ensure_ascii=False)
    qr = qrcode.QRCode(border=2, box_size=10)
    qr.add_data(payload)
    qr.make(fit=True)
    qimg = qr.make_image(fill_color="#121212", back_color="#FFFFFF").get_image().convert("RGB")
    qsize = 420
    qimg = qimg.resize((qsize, qsize))
    qy = max(y + 30, 1280)
    img.paste(qimg, ((W - qsize) // 2, qy))
    center("GUARDIAN HEALTH & ANGEL · SCAN FOR SURVIVAL INFO", qy + qsize + 36, f_tiny, "#8E8E93")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

@api.get("/family/wallpaper.png")
async def family_wallpaper(token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    prof = await db.emergency_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    png = await run_in_threadpool(_make_wallpaper, user, prof)
    return Response(content=png, media_type="image/png",
                    headers={"Content-Disposition": 'attachment; filename="guardian_emergency_wallpaper.png"'})


# --------- ACOUSTIC THREAT DETECTION (Angel Mode) ---------
class AcousticIn(BaseModel):
    kind: str = "loud_noise"  # loud_noise | glass | scream | gunshot
    db_level: Optional[float] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

@api.post("/acoustic-event")
async def acoustic_event(body: AcousticIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    doc = {
        "event_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "kind": body.kind, "db_level": body.db_level,
        "lat": body.lat, "lng": body.lng,
        "created_at": datetime.now(timezone.utc),
    }
    await db.acoustic_events.insert_one(doc.copy())
    try:
        await send_push(
            recipients=[user["user_id"]],
            data={"title": "🔊 ACOUSTIC THREAT DETECTED", "message": f"Loud sound ({body.kind}) — check the senior's condition.", "action_url": "/family-dashboard"},
        )
    except Exception as e:
        logger.warning(f"acoustic push failed: {e}")
    return clean(doc)

@api.get("/acoustic-events")
async def acoustic_events(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.acoustic_events.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(30)


# --------- GUARDIAN PULSE CHECK (Silent Ping — STRICTLY OPT-IN) ---------
class PulseRequestIn(BaseModel):
    target_did: str

@api.post("/pulse/request")
async def pulse_request(body: PulseRequestIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    target = await db.users.find_one({"did": body.target_did.strip()}, {"_id": 0})
    if not target:
        raise HTTPException(404, "DID not found")
    if target["user_id"] == user["user_id"]:
        raise HTTPException(400, "Cannot ping yourself")
    if not target.get("pulse_check_optin"):
        raise HTTPException(403, "opt_in_required: The user did not enable Guardian Pulse Check (privacy is opt-in).")
    doc = {
        "req_id": uuid.uuid4().hex,
        "from_user": user["user_id"], "from_name": user.get("name") or "Rodina",
        "target_user": target["user_id"], "target_did": target["did"],
        "status": "pending", "responded_at": None,
        "created_at": datetime.now(timezone.utc),
    }
    await db.pulse_requests.insert_one(doc.copy())
    try:
        await send_push(recipients=[target["user_id"]], data={"title": "💛 SILENT PING FROM FAMILY", "message": f"{doc['from_name']} is asking whether you are okay. Reply with one tap.", "action_url": "/pulse-check"})
    except Exception as e:
        logger.warning(f"pulse push failed: {e}")
    return clean(doc)

@api.get("/pulse/requests")
async def pulse_requests_inbox(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.pulse_requests.find({"target_user": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(30)

class PulseRespondIn(BaseModel):
    status: str  # ok | need_help

@api.post("/pulse/requests/{req_id}/respond")
async def pulse_respond(req_id: str, body: PulseRespondIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if body.status not in ("ok", "need_help"):
        raise HTTPException(400, "status must be ok|need_help")
    req = await db.pulse_requests.find_one({"req_id": req_id, "target_user": user["user_id"]}, {"_id": 0})
    if not req:
        raise HTTPException(404, "Not found")
    await db.pulse_requests.update_one({"req_id": req_id}, {"$set": {"status": body.status, "responded_at": datetime.now(timezone.utc)}})
    title = "💚 ALL GOOD" if body.status == "ok" else "🔴 NEEDS HELP"
    try:
        await send_push(recipients=[req["from_user"]], data={"title": title, "message": f"Reply to silent ping: {body.status}", "action_url": "/pulse-check"})
    except Exception as e:
        logger.warning(f"pulse respond push failed: {e}")
    # GA-T Proof-of-Help — reward the family member who checked in (loop completed)
    try:
        from routes.token import award_tokens
        await award_tokens(req["from_user"], "proof_of_help", "pulse check completed")
    except Exception as e:
        logger.warning(f"proof_of_help award failed: {e}")
    return {"ok": True, "status": body.status}

@api.get("/pulse/sent")
async def pulse_sent(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.pulse_requests.find({"from_user": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(30)



# --------- VOICE SIGNATURES (Inner Circle Voice Prints) ---------
# The founder's vision: each family member records a 5-second voice print.
# When they send a Voice Echo to grandma, Jarvis announces the sender by name.
# The recognition itself is by user_id (secure) — the audio is stored so a future
# voice-ID model can match unknown callers to their print.

@api.post("/family/voice-signature")
async def voice_signature_upload(
    file: UploadFile = File(...),
    label: str = Form(""),
    authorization: Optional[str] = Header(None),
):
    """Record a 5-second voice print. Overwrites the previous one for this user."""
    user = await get_current_user(authorization)
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty audio")
    if len(data) > 3 * 1024 * 1024:  # 3MB is plenty for 5s at any sane bitrate
        raise HTTPException(400, "Audio too large (max 3MB)")
    sig_id = uuid.uuid4().hex
    ext = "m4a" if (file.content_type or "").endswith(("mp4", "aac", "m4a")) else "webm"
    path = f"{APP_NAME}/voice-signatures/{user['user_id']}.{ext}"
    try:
        await run_in_threadpool(put_object_sync, path, data, file.content_type or "audio/webm")
    except Exception as e:
        logger.error(f"voice-sig upload failed: {e}")
        raise HTTPException(502, "Storage upload failed")
    label_clean = (label or user.get("name") or user.get("email") or "").strip()[:60]
    rec = {
        "sig_id": sig_id,
        "user_id": user["user_id"],
        "did": user["did"],
        "label": label_clean or "Guardian",
        "storage_path": path,
        "size": len(data),
        "content_type": file.content_type or "audio/webm",
        "updated_at": datetime.now(timezone.utc),
    }
    await db.voice_signatures.update_one(
        {"user_id": user["user_id"]},
        {"$set": rec},
        upsert=True,
    )
    return {"ok": True, "sig_id": sig_id, "label": rec["label"]}

@api.get("/family/voice-signature")
async def voice_signature_get(authorization: Optional[str] = Header(None)):
    """Returns the caller's own voice-print record (without the audio bytes)."""
    user = await get_current_user(authorization)
    rec = await db.voice_signatures.find_one({"user_id": user["user_id"]}, {"_id": 0, "storage_path": 0})
    return rec or {}

@api.get("/family/voice-signature/file")
async def voice_signature_file(token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    """Streams the caller's own voice-print audio bytes."""
    user = await _auth_pdf(authorization, token)
    rec = await db.voice_signatures.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "No voice signature recorded yet")
    try:
        content, ctype = await run_in_threadpool(get_object_sync, rec["storage_path"])
    except Exception as e:
        raise HTTPException(502, f"Storage read failed: {e}")
    return Response(content=content, media_type=ctype)

@api.delete("/family/voice-signature")
async def voice_signature_delete(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await db.voice_signatures.delete_one({"user_id": user["user_id"]})
    return {"ok": True}


# --------- ANGEL PULSE (Haptic Heartbeat) ---------
# Send a wordless heartbeat vibration to an Inner Circle member. The receiver's
# phone plays a rhythmic pulse (frontend uses expo-haptics). No message body —
# only "I'm alive, thinking of you." Push notification carries the pulse spec.

class AngelPulseIn(BaseModel):
    to_user_id: Optional[str] = None
    to_email: Optional[str] = None
    pattern: Optional[str] = "heartbeat"   # heartbeat | soft | strong | sos
    bpm: Optional[int] = 72                 # 40..120 (frontend clamps too)

@api.post("/angel/pulse")
async def angel_pulse_send(body: AngelPulseIn, authorization: Optional[str] = Header(None)):
    sender = await get_current_user(authorization)
    if not body.to_user_id and not body.to_email:
        raise HTTPException(400, "Provide to_user_id or to_email")
    recipient = None
    if body.to_user_id:
        recipient = await db.users.find_one({"user_id": body.to_user_id}, {"_id": 0})
    if not recipient and body.to_email:
        recipient = await db.users.find_one({"email": body.to_email.strip().lower()}, {"_id": 0})
    if not recipient:
        raise HTTPException(404, "Recipient not found")
    if recipient["user_id"] == sender["user_id"]:
        raise HTTPException(400, "Cannot pulse yourself")

    # Circle check — sender must be in a guardian link either direction, or Inner Circle.
    ok = await db.guardians.find_one({
        "$or": [
            {"user_id": recipient["user_id"], "guardian_user_id": sender["user_id"]},
            {"user_id": sender["user_id"], "guardian_user_id": recipient["user_id"]},
        ]
    })
    if not ok:
        if not await db.inner_circle.find_one({"email": sender.get("email", "").lower()}):
            raise HTTPException(403, "Not in the recipient's Inner Circle")

    pattern = body.pattern or "heartbeat"
    if pattern not in {"heartbeat", "soft", "strong", "sos"}:
        pattern = "heartbeat"
    bpm = max(40, min(120, int(body.bpm or 72)))

    pulse = {
        "pulse_id": uuid.uuid4().hex,
        "from_user_id": sender["user_id"],
        "from_name": sender.get("name") or sender.get("email") or "Guardian",
        "to_user_id": recipient["user_id"],
        "pattern": pattern,
        "bpm": bpm,
        "created_at": datetime.now(timezone.utc),
        "delivered": False,
    }
    await db.angel_pulses.insert_one(pulse.copy())
    try:
        await send_push(recipients=[recipient["user_id"]], data={
            "title": "💓 TEP ANJELA",
            "message": f"{pulse['from_name']} sent you their heartbeat. Tap for a feeling of connection.",
            "action_url": f"/angel-pulse?id={pulse['pulse_id']}",
            "pulse_pattern": pattern,
            "pulse_bpm": str(bpm),
        })
    except Exception as e:
        logger.warning(f"pulse push: {e}")
    return {"ok": True, "pulse": clean(pulse)}


@api.get("/angel/pulse/inbox")
async def angel_pulse_inbox(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.angel_pulses.find(
        {"to_user_id": user["user_id"]},
        {"_id": 0},
    ).sort("created_at", -1).to_list(30)
    return {"pulses": clean(rows), "count": len(rows)}


@api.post("/angel/pulse/{pulse_id}/felt")
async def angel_pulse_felt(pulse_id: str, authorization: Optional[str] = Header(None)):
    """Recipient acknowledges they felt the pulse — the sender sees a 💛 confirmation."""
    user = await get_current_user(authorization)
    r = await db.angel_pulses.find_one_and_update(
        {"pulse_id": pulse_id, "to_user_id": user["user_id"]},
        {"$set": {"delivered": True, "felt_at": datetime.now(timezone.utc)}},
        return_document=True,
    )
    if not r:
        raise HTTPException(404, "Pulse not found")
    r.pop("_id", None)
    # Notify sender that the pulse was felt.
    try:
        await send_push(recipients=[r["from_user_id"]], data={
            "title": "💛 HEARTBEAT FELT",
            "message": f"Your angelic heartbeat has arrived.",
            "action_url": "/",
        })
    except Exception:
        pass
    return clean(r)


# --------- FAMILY VOICE CIRCLE ---------
# The founder's Sentient vision: every family member (Tomáš, mama, babička)
# records a 5-second voice print in ONE shared circle. Grandma hears
# "Máte novú správu od Tomáša" — Jarvis knows who is who by user_id.
# The circle = anyone in a guardian relationship with the caller (either direction).

@api.get("/family/voice-signature/circle")
async def voice_circle(authorization: Optional[str] = Header(None)):
    """Every family member in your circle + whether they have a voice print yet."""
    user = await get_current_user(authorization)
    uid = user["user_id"]

    # Collect member user_ids from BOTH sides of the guardian relationship.
    member_ids: set[str] = set()
    async for l in db.guardians.find({"user_id": uid}, {"_id": 0, "guardian_user_id": 1}):
        if l.get("guardian_user_id"):
            member_ids.add(l["guardian_user_id"])
    async for l in db.guardians.find({"guardian_user_id": uid}, {"_id": 0, "user_id": 1}):
        if l.get("user_id"):
            member_ids.add(l["user_id"])
    # Include self in the circle so Tomáš sees his own tile too.
    member_ids.add(uid)

    # One round-trip per collection instead of N per member.
    users_by_id = {}
    async for u in db.users.find(
        {"user_id": {"$in": list(member_ids)}},
        {"_id": 0, "user_id": 1, "name": 1, "email": 1, "did": 1},
    ):
        users_by_id[u["user_id"]] = u
    sigs_by_uid = {}
    async for s in db.voice_signatures.find(
        {"user_id": {"$in": list(member_ids)}},
        {"_id": 0, "user_id": 1, "label": 1, "size": 1, "updated_at": 1, "sig_id": 1},
    ):
        sigs_by_uid[s["user_id"]] = s

    members = []
    for m_uid in member_ids:
        u = users_by_id.get(m_uid) or {"user_id": m_uid, "name": "Unknown", "email": ""}
        sig = sigs_by_uid.get(m_uid)
        members.append({
            "user_id": m_uid,
            "name": (u.get("name") or u.get("email") or "Rodina").split(" ")[0],
            "email": u.get("email") or "",
            "is_self": m_uid == uid,
            "has_signature": bool(sig),
            "label": (sig or {}).get("label") if sig else None,
            "recorded_at": (sig or {}).get("updated_at"),
        })
    # Self first, then recorded members alphabetically, then not-yet-recorded.
    members.sort(key=lambda m: (
        0 if m["is_self"] else (1 if m["has_signature"] else 2),
        (m["name"] or "").lower(),
    ))
    recorded = sum(1 for m in members if m["has_signature"])
    return {
        "members": clean(members),
        "recorded": recorded,
        "total": len(members),
    }
