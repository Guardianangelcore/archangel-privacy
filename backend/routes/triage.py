# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""COGNITIVE TRIAGE — Automatic Stress UI (world-first).

Watches the user's recent biometrics (Bio-Scanner HR/SpO2/stress) plus optional
voice-tremor signals from Jarvis conversations. When distress crosses the
threshold, the front-end auto-switches to the CRISIS HUD: two big buttons
(Emergency Call · Immediate Survival Instructions).

State is server-authoritative so ALL devices of the same user (phone, tablet,
family dashboard) share the same triage frame — the Guardian Circle sees the
same crisis instantly.
"""
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta

from core import api, db, get_current_user, clean, apply_watermark

# ---------------- THRESHOLDS ----------------
HR_CRISIS = 120        # bpm — anything at or above triggers CRISIS
HR_ELEVATED = 100      # bpm — elevated but not crisis
SPO2_CRISIS = 92       # % — anything below is critical hypoxia
STRESS_CRISIS = "high"
VOICE_TREMOR_CRISIS = 0.75  # 0..1 tremor score
COOLDOWN_MIN = 15      # after dismiss, do not re-trigger for N minutes

SURVIVAL_INSTRUCTIONS = {
    "sk": [
        "1. Sadnite si a dýchajte pomaly — 4 sekundy nádych, 6 sekúnd výdych.",
        "2. Zavolajte 112 alebo blízku osobu — číslo je nižšie.",
        "3. Ak máte tabletky pri sebe (napr. nitroglycerín), použite podľa pokynov.",
        "4. Zostaňte v pokoji, neohýbajte sa, nešoférujte.",
        "5. Guardian Angel medzičasom pošle núdzový signál Vášmu Guardian Circle.",
    ],
    "cs": [
        "1. Posaďte se a dýchejte pomalu — 4 s nádech, 6 s výdech.",
        "2. Volejte 112 nebo blízkého — číslo je níže.",
        "3. Máte-li léky (např. nitroglycerin), užijte dle pokynů.",
        "4. Zůstaňte v klidu, neřiďte, nezvedejte se prudce.",
        "5. Guardian Angel mezitím pošle nouzový signál Vašemu Guardian Circle.",
    ],
    "en": [
        "1. Sit down and breathe slowly — 4s in, 6s out.",
        "2. Call 112 or a trusted person — number is below.",
        "3. If you carry prescribed medication (e.g. nitroglycerin), use as directed.",
        "4. Stay calm, do not drive, avoid sudden movement.",
        "5. Guardian Angel is silently alerting your Guardian Circle.",
    ],
}

EMERGENCY_NUMBERS = {"EU": "112", "SK": "155", "CZ": "155", "UK": "999", "US": "911"}


# ---------------- CORE ----------------
def _classify(hr, spo2, stress_level, voice_tremor) -> tuple[str, list[str]]:
    """Return (crisis_level, reasons[]). crisis_level in {'calm','elevated','crisis'}."""
    reasons: list[str] = []
    is_crisis = False
    is_elevated = False
    if hr is not None:
        if hr >= HR_CRISIS:
            is_crisis = True
            reasons.append(f"heart rate {hr} bpm ≥ {HR_CRISIS}")
        elif hr >= HR_ELEVATED:
            is_elevated = True
            reasons.append(f"heart rate {hr} bpm elevated")
    if spo2 is not None:
        if spo2 < SPO2_CRISIS:
            is_crisis = True
            reasons.append(f"SpO₂ {spo2}% < {SPO2_CRISIS}%")
    if stress_level == STRESS_CRISIS:
        is_elevated = True
        reasons.append("stress: high")
    if voice_tremor is not None and voice_tremor >= VOICE_TREMOR_CRISIS:
        is_crisis = True
        reasons.append(f"voice tremor {voice_tremor:.2f}")
    level = "crisis" if is_crisis else ("elevated" if is_elevated else "calm")
    return level, reasons


async def _resolve_state(user: dict) -> dict:
    """Compute the CURRENT triage state from recent bio signals + manual override."""
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    # Manual override — either forced ON (until dismissed) or in cooldown
    override = await db.triage_state.find_one({"user_id": uid}, {"_id": 0}) or {}
    if override.get("manual_dismiss_until"):
        exp = override["manual_dismiss_until"]
        if isinstance(exp, str):
            try:
                exp = datetime.fromisoformat(exp.replace("Z", "+00:00"))
            except Exception:
                exp = None
        if exp and exp.replace(tzinfo=timezone.utc) > now:
            return {"crisis_level": "calm", "reasons": [], "source": "dismissed",
                    "cooldown_until": exp.isoformat(), "auto_open_hud": False,
                    "instructions": [], "emergency_numbers": EMERGENCY_NUMBERS}
    if override.get("manual_trigger"):
        lang = (user.get("language") or "sk")[:2]
        return {"crisis_level": "crisis", "reasons": ["manually activated"],
                "source": "manual", "auto_open_hud": True,
                "instructions": SURVIVAL_INSTRUCTIONS.get(lang, SURVIVAL_INSTRUCTIONS["en"]),
                "emergency_numbers": EMERGENCY_NUMBERS,
                "guardian_ping_at": override.get("triggered_at").isoformat() if override.get("triggered_at") else None}
    # Automatic: latest bioscan within last 15 minutes
    since = now - timedelta(minutes=15)
    scan = await db.bioscan_results.find_one(
        {"user_id": uid, "at": {"$gte": since}}, {"_id": 0}, sort=[("at", -1)]
    ) or {}
    voice = await db.triage_voice.find_one(
        {"user_id": uid, "at": {"$gte": since}}, {"_id": 0}, sort=[("at", -1)]
    ) or {}
    level, reasons = _classify(
        scan.get("heart_rate"), scan.get("spo2"),
        scan.get("stress_level"), voice.get("tremor_score"),
    )
    lang = (user.get("language") or "sk")[:2]
    return {
        "crisis_level": level,
        "reasons": reasons,
        "source": "auto",
        "auto_open_hud": level == "crisis",
        "instructions": SURVIVAL_INSTRUCTIONS.get(lang, SURVIVAL_INSTRUCTIONS["sk"]) if level == "crisis" else [],
        "emergency_numbers": EMERGENCY_NUMBERS,
        "last_scan_at": scan.get("at").isoformat() if scan.get("at") else None,
        "latest_vitals": {"heart_rate": scan.get("heart_rate"), "spo2": scan.get("spo2"),
                          "stress_level": scan.get("stress_level")},
    }


@api.get("/triage/state")
async def triage_state(authorization: Optional[str] = Header(None)):
    """Poll-safe crisis snapshot for the Crisis HUD overlay."""
    user = await get_current_user(authorization)
    return await _resolve_state(user)


class TriggerIn(BaseModel):
    reason: Optional[str] = None
    hr: Optional[int] = None
    spo2: Optional[int] = None
    voice_tremor: Optional[float] = None


@api.post("/triage/trigger")
async def triage_trigger(body: TriggerIn, authorization: Optional[str] = Header(None)):
    """Manually or programmatically raise the Crisis HUD.
    Also silently pings the Guardian Circle (guardians collection)."""
    user = await get_current_user(authorization)
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    await db.triage_state.update_one(
        {"user_id": uid},
        {"$set": {"user_id": uid, "manual_trigger": True, "manual_dismiss_until": None,
                  "triggered_at": now, "reason": (body.reason or "")[:200]}},
        upsert=True,
    )
    # Silent Guardian Circle push (best-effort)
    try:
        from core import send_push
        guardians = await db.guardians.find({"user_id": uid}, {"_id": 0, "guardian_user_id": 1}).to_list(10)
        if guardians:
            await send_push(
                recipients=[g["guardian_user_id"] for g in guardians],
                data={"title": "🚨 GUARDIAN — CRISIS MODE",
                      "message": f"{user.get('name') or 'Your loved one'} has the Crisis HUD active. Please check on them.",
                      "action_url": "/family-dashboard"},
                idempotency_key=f"triage-{uid}-{int(now.timestamp() // 60)}",
            )
    except Exception:
        pass
    try:
        from routes.swarm import bus_publish
        await bus_publish("triage.crisis", "cognitive_triage",
                          {"user": uid[:8], "reason": (body.reason or "manual")[:60]})
    except Exception:
        pass
    return await _resolve_state(user)


@api.post("/triage/dismiss")
async def triage_dismiss(authorization: Optional[str] = Header(None)):
    """Dismiss the HUD — puts user in a 15-min cooldown so it doesn't immediately re-fire."""
    user = await get_current_user(authorization)
    uid = user["user_id"]
    until = datetime.now(timezone.utc) + timedelta(minutes=COOLDOWN_MIN)
    await db.triage_state.update_one(
        {"user_id": uid},
        {"$set": {"user_id": uid, "manual_trigger": False,
                  "manual_dismiss_until": until, "dismissed_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return {"ok": True, "cooldown_until": until.isoformat()}


class VoiceIn(BaseModel):
    tremor_score: float  # 0..1
    sample_ms: int = 0


@api.post("/triage/voice")
async def triage_voice(body: VoiceIn, authorization: Optional[str] = Header(None)):
    """Ingest a voice-tremor signal from Jarvis/Whisper. Stored + factored into state."""
    user = await get_current_user(authorization)
    if not (0 <= body.tremor_score <= 1):
        raise HTTPException(400, "tremor_score out of range (0..1)")
    await db.triage_voice.insert_one({
        "user_id": user["user_id"], "tremor_score": round(body.tremor_score, 3),
        "sample_ms": max(0, int(body.sample_ms)), "at": datetime.now(timezone.utc),
    })
    return await _resolve_state(user)


@api.get("/triage/instructions")
async def triage_instructions(language: str = "sk", authorization: Optional[str] = Header(None)):
    """Fetch the localized 5-step crisis survival instructions (also embedded in state)."""
    _ = await get_current_user(authorization)
    lang = (language or "sk")[:2]
    instructions = SURVIVAL_INSTRUCTIONS.get(lang, SURVIVAL_INSTRUCTIONS["en"])
    header = apply_watermark("Stay calm — Guardian Angel is guiding you step by step.")
    return {"instructions": instructions, "header": header, "emergency_numbers": EMERGENCY_NUMBERS}
