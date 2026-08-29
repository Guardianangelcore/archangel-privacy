# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""GUARDIAN LENS — the One-Lens actionable vision system + Voice Liveness.

1. POST /lens/analyze — one photo of ANY medical artefact (pill bottle, box,
   doctor's report, prescription, lab results). Vision AI identifies it and
   returns a structured verdict with instant workflow suggestions
   (Translator / Calendar / Interaction Guard / Med reminder).
2. POST /voice/liveness — Whisper STT: senior says "Som v poriadku" /
   "I am OK" after a fall → hands-free alarm cancellation (Angel Mode 2.0).
"""
from fastapi import HTTPException, Header, UploadFile, File, Form
from fastapi.concurrency import run_in_threadpool
from typing import Optional
from datetime import datetime, timezone
import os, uuid, hashlib, json, base64, re, tempfile, inspect, asyncio

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
from emergentintegrations.llm.openai import OpenAISpeechToText

from core import (
    api, db, logger, clean, get_current_user, _aml_ledger_append,
    APP_NAME, put_object_sync, EMERGENT_LLM_KEY, send_push, apply_watermark,
)

# GUARDIAN EYE — three sovereign vision providers (multi-model consensus).
# Each ID matches an entry from the emergentintegrations vision registry.
VISION_MODELS = {
    "gpt": ("openai", "gpt-5.4"),
    "claude": ("anthropic", "claude-sonnet-5"),
    "gemini": ("gemini", "gemini-3.1-pro-preview"),
}
DEFAULT_MODEL_KEY = "gpt"

LENS_SYSTEM = (
    "You are GUARDIAN LENS — a precise medical vision analyst for a Slovak health app. "
    "The user photographs ONE medical artefact: a pill bottle/box, a doctor's report, a prescription, or lab results. "
    "Identify it and answer ONLY with a single valid JSON object (no markdown fences, no commentary) with EXACTLY these keys:\n"
    '{"kind": "medication|medical_report|prescription|lab_results|other",'
    '"name": "short name of the medication or document (in Slovak)",'
    '"summary_sk": "2-4 sentence plain-Slovak summary a grandmother would understand",'
    '"warnings": ["max 3 short Slovak warnings (interactions, dosing, urgency)"],'
    '"specialty": "medical specialty to book if a follow-up visit is advisable, else empty string",'
    '"suggested_actions": ["subset of: translate, add_med_reminder, check_interactions, book_specialist, save_to_vault"]}'
    "\nBe conservative: never diagnose, never prescribe. If unreadable, use kind=other and explain in summary_sk."
)

def _parse_lens_json(raw: str) -> dict:
    txt = raw.strip()
    txt = re.sub(r"^```(json)?", "", txt).strip()
    txt = re.sub(r"```$", "", txt).strip()
    m = re.search(r"\{.*\}", txt, re.DOTALL)
    if m:
        txt = m.group(0)
    d = json.loads(txt)
    return {
        "kind": str(d.get("kind") or "other")[:30],
        "name": str(d.get("name") or "Neznámy artefakt")[:120],
        "summary_sk": str(d.get("summary_sk") or "")[:1200],
        "warnings": [str(w)[:200] for w in (d.get("warnings") or [])][:3],
        "specialty": str(d.get("specialty") or "")[:60],
        "suggested_actions": [str(a)[:40] for a in (d.get("suggested_actions") or [])][:5],
    }

@api.post("/lens/analyze")
async def lens_analyze(file: UploadFile = File(...),
                       model: Optional[str] = Form(None),
                       pillar: Optional[str] = Form(None),
                       authorization: Optional[str] = Header(None)):
    """Single-model vision OCR + analysis. `model` = gpt|claude|gemini (default gpt).
    `pillar` = optional context (health|hunter|legacy) used for downstream auto-routing."""
    user = await get_current_user(authorization)
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(400, "Empty file")
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(400, "Image too large (max 15MB)")
    ctype = file.content_type or "image/jpeg"
    if not ctype.startswith("image/"):
        raise HTTPException(400, "Only images are accepted")
    if not EMERGENT_LLM_KEY:
        raise HTTPException(500, "AI key not configured")

    model_key = (model or DEFAULT_MODEL_KEY).lower()
    if model_key not in VISION_MODELS:
        raise HTTPException(400, f"unsupported model: choose {list(VISION_MODELS)}")
    provider, model_id = VISION_MODELS[model_key]

    # keep the photo in the vault-grade storage (for save_to_vault action)
    scan_id = uuid.uuid4().hex
    path = f"{APP_NAME}/lens/{user['user_id']}/{scan_id}.jpg"
    try:
        await run_in_threadpool(put_object_sync, path, data, ctype)
    except Exception as e:
        logger.warning(f"lens storage failed (non-fatal): {e}")
        path = None

    b64 = base64.b64encode(data).decode()
    verdict = await _run_vision(provider, model_id, b64, scan_id, seed=f"single-{model_key}")

    scan = {
        "scan_id": scan_id, "user_id": user["user_id"],
        "sha256": hashlib.sha256(data).hexdigest(),
        "storage_path": path, "image_size": len(data),
        "model": f"{provider}/{model_id}", "pillar": (pillar or "").strip()[:20],
        **verdict,
        "ai_generated": True,
        "created_at": datetime.now(timezone.utc),
    }
    scan["summary_sk"] = apply_watermark(scan.get("summary_sk") or "")
    await db.lens_scans.insert_one(scan.copy())
    return clean(scan)


async def _run_vision(provider: str, model_id: str, b64: str, scan_id: str, seed: str = "") -> dict:
    """Run a single vision provider — always returns a normalised verdict dict."""
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"lens-{seed[:8]}-{scan_id[:6]}",
        system_message=LENS_SYSTEM,
    ).with_model(provider, model_id)
    try:
        resp = await chat.send_message(UserMessage(
            text="Analyze this medical artefact photo. Answer with the JSON object only.",
            file_contents=[ImageContent(image_base64=b64)],
        ))
        try:
            return _parse_lens_json(resp or "")
        except json.JSONDecodeError:
            return {"kind": "other", "name": "Neznámy artefakt",
                    "summary_sk": (resp or "").strip()[:800] or
                                  "Obsah sa nepodarilo spoľahlivo rozpoznať. Skúste ostrejšiu fotku pri lepšom svetle.",
                    "warnings": [], "specialty": "", "suggested_actions": ["save_to_vault"]}
    except Exception as e:
        logger.error(f"lens vision error ({provider}/{model_id}): {e}")
        return {"kind": "other", "name": "Zlyhanie modelu",
                "summary_sk": f"Model {provider}/{model_id} nedostupný.",
                "warnings": [], "specialty": "", "suggested_actions": [],
                "_error": str(e)[:120]}


@api.post("/lens/analyze-consensus")
async def lens_analyze_consensus(file: UploadFile = File(...),
                                  pillar: Optional[str] = Form(None),
                                  authorization: Optional[str] = Header(None)):
    """Multi-model consensus — runs GPT-5.4 + Claude Sonnet 5 + Gemini 3.1 Pro in parallel.
    Merges verdicts by majority vote on `kind`, longest coherent `summary_sk` and dedup warnings.
    Returns `agreement_pct` (0-100) plus per-model breakdown."""
    user = await get_current_user(authorization)
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(400, "Empty file")
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(400, "Image too large (max 15MB)")
    ctype = file.content_type or "image/jpeg"
    if not ctype.startswith("image/"):
        raise HTTPException(400, "Only images are accepted")
    if not EMERGENT_LLM_KEY:
        raise HTTPException(500, "AI key not configured")

    scan_id = uuid.uuid4().hex
    path = f"{APP_NAME}/lens/{user['user_id']}/{scan_id}.jpg"
    try:
        await run_in_threadpool(put_object_sync, path, data, ctype)
    except Exception as e:
        logger.warning(f"lens storage failed (non-fatal): {e}")
        path = None

    b64 = base64.b64encode(data).decode()
    keys = list(VISION_MODELS.keys())
    results = await asyncio.gather(*[
        _run_vision(*VISION_MODELS[k], b64=b64, scan_id=scan_id, seed=k) for k in keys
    ], return_exceptions=False)

    per_model = {k: r for k, r in zip(keys, results)}
    valid = [r for r in results if not r.get("_error") and r.get("kind") != "other"]
    # Majority vote on kind
    kind_votes: dict = {}
    for r in results:
        kind_votes[r.get("kind", "other")] = kind_votes.get(r.get("kind", "other"), 0) + 1
    kind = max(kind_votes.items(), key=lambda kv: kv[1])[0]
    agreement_pct = round(100 * kind_votes[kind] / max(1, len(results)))
    # Pick the longest, most detailed summary from a valid provider
    def _score(r: dict) -> int:
        return len(r.get("summary_sk", "")) + 50 * len(r.get("warnings", []))
    best = max(valid, key=_score) if valid else results[0]
    warnings_all: list = []
    for r in results:
        for w in r.get("warnings", []):
            if w and w not in warnings_all:
                warnings_all.append(w)
    actions_all: list = []
    for r in results:
        for a in r.get("suggested_actions", []):
            if a and a not in actions_all:
                actions_all.append(a)

    merged = {
        "kind": kind,
        "name": best.get("name", "Neznámy artefakt"),
        "summary_sk": best.get("summary_sk", ""),
        "warnings": warnings_all[:5],
        "specialty": best.get("specialty", ""),
        "suggested_actions": actions_all[:6],
    }
    merged["summary_sk"] = apply_watermark(merged["summary_sk"])

    scan = {
        "scan_id": scan_id, "user_id": user["user_id"],
        "sha256": hashlib.sha256(data).hexdigest(),
        "storage_path": path, "image_size": len(data),
        "model": "consensus/3", "pillar": (pillar or "").strip()[:20],
        "consensus": {"agreement_pct": agreement_pct, "kind_votes": kind_votes,
                      "per_model": {k: {"kind": v.get("kind"), "name": v.get("name"),
                                        "error": v.get("_error")} for k, v in per_model.items()}},
        **merged,
        "ai_generated": True,
        "created_at": datetime.now(timezone.utc),
    }
    await db.lens_scans.insert_one(scan.copy())
    return clean(scan)

@api.get("/lens/models")
async def lens_models():
    """List available Guardian Eye vision models — for frontend chip selector."""
    return {"models": [
        {"key": "gpt", "label": "GPT-5.4 Vision", "provider": "openai", "model": "gpt-5.4"},
        {"key": "claude", "label": "Claude Sonnet 5", "provider": "anthropic", "model": "claude-sonnet-5"},
        {"key": "gemini", "label": "Gemini 3.1 Pro", "provider": "gemini", "model": "gemini-3.1-pro-preview"},
        {"key": "consensus", "label": "Konsenzus (3 modely)", "provider": "multi", "model": "consensus/3"},
    ], "default": DEFAULT_MODEL_KEY}


@api.post("/lens/{scan_id}/to-jarvis")
async def lens_to_jarvis(scan_id: str, authorization: Optional[str] = Header(None)):
    """Send a scan verdict into the Jarvis conversation — the user can then dive
    deeper conversationally (dosage, interactions, next steps)."""
    user = await get_current_user(authorization)
    scan = await db.lens_scans.find_one({"scan_id": scan_id, "user_id": user["user_id"]}, {"_id": 0})
    if not scan:
        raise HTTPException(404, "Scan not found")
    # Compose a synthetic user-side message that Jarvis will react to.
    parts = [
        f"[Guardian Eye — {scan.get('kind', 'other').upper()}]",
        f"Názov: {scan.get('name') or '—'}",
        f"Zhrnutie: {scan.get('summary_sk') or '—'}",
    ]
    if scan.get("warnings"):
        parts.append("Varovania: " + " · ".join(scan["warnings"][:3]))
    if scan.get("specialty"):
        parts.append(f"Odporúčaná špecializácia: {scan['specialty']}")
    synthetic_msg = "\n".join(parts)[:1200]

    # Delegate to agent chat — preserves memory + XP loop.
    from routes.agent import agent_chat, AgentChatIn
    result = await agent_chat(
        AgentChatIn(message=f"Analyzoval som toto pomocou Guardian Eye. Poraď mi ďalšie kroky:\n{synthetic_msg}",
                    language=(user.get("language") or "sk")),
        authorization=authorization,
    )
    # Link the Jarvis interaction to the scan for audit/history
    await db.lens_scans.update_one({"scan_id": scan_id},
                                   {"$set": {"jarvis_sent_at": datetime.now(timezone.utc),
                                             "jarvis_reply": (result.get("reply") or "")[:1500]}})
    return {"ok": True, "scan_id": scan_id, "jarvis": result}


@api.get("/lens/history")
async def lens_history(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.lens_scans.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(20)
    return {"scans": rows}

@api.post("/lens/{scan_id}/save-to-vault")
async def lens_save_to_vault(scan_id: str, authorization: Optional[str] = Header(None)):
    """Files the already-stored lens photo into the health vault as a document."""
    from models import Document
    user = await get_current_user(authorization)
    scan = await db.lens_scans.find_one({"scan_id": scan_id, "user_id": user["user_id"]}, {"_id": 0})
    if not scan:
        raise HTTPException(404, "Scan not found")
    if not scan.get("storage_path"):
        raise HTTPException(410, "Scan image not stored")
    existing = await db.documents.find_one({"user_id": user["user_id"], "hash": scan["sha256"]}, {"_id": 0, "doc_id": 1})
    if existing:
        return {"ok": True, "doc_id": existing["doc_id"], "already_saved": True}
    doc = Document(
        doc_id=uuid.uuid4().hex, user_id=user["user_id"],
        title=f"🔍 Lens: {scan.get('name') or 'sken'}"[:120],
        file_name=f"lens_{scan_id[:8]}.jpg", content_type="image/jpeg",
        size=scan.get("image_size") or 0, storage_path=scan["storage_path"],
        hash=scan["sha256"],
    ).model_dump()
    doc["extracted_text"] = scan.get("summary_sk") or ""
    doc["source"] = "guardian_lens"
    await db.documents.insert_one(doc.copy())
    return {"ok": True, "doc_id": doc["doc_id"]}


# ============================================================
# VOICE LIVENESS — hands-free "Som v poriadku" (Whisper STT)
# ============================================================
OK_PATTERNS = [
    "v poriadku", "v poradku", "v poriadko", "poriadku", "poradku",
    "som ok", "jsem ok", "som oukej", "i am ok", "im ok", "i am okay", "im okay",
    "je mi dobre", "nic mi nie je", "nic mi neni", "okej", "okay",
]

def _normalize(t: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFD", t.lower().strip())
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")  # strip diacritics
    t = re.sub(r"[.,!?…'']", " ", t)
    return re.sub(r"\s+", " ", t)

@api.post("/voice/liveness")
async def voice_liveness(file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    """Angel Mode 2.0 — the senior shouts 'Jarvis, som v poriadku!' after a
    fall; Whisper transcribes and the alarm is cancelled hands-free."""
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
        result = stt.transcribe(open(tmp_path, "rb"), model="whisper-1")
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
        logger.error(f"voice liveness STT error: {e}")
        raise HTTPException(502, "Transcription provider failed")
    finally:
        if tmp_path:
            try: os.unlink(tmp_path)
            except Exception: pass

    norm = _normalize(transcript)
    ok = any(p in norm for p in OK_PATTERNS) or norm.strip() == "ok"
    await db.liveness_events.insert_one({
        "event_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "transcript": transcript[:300], "ok_detected": ok,
        "at": datetime.now(timezone.utc),
    })
    if ok:
        try:
            await db.fall_events.insert_one({
                "event_id": uuid.uuid4().hex, "user_id": user["user_id"],
                "verified": False, "cancelled": True, "via": "voice_liveness",
                "created_at": datetime.now(timezone.utc),
            })
        except Exception:
            pass
    return {"transcript": transcript, "ok_detected": ok,
            "note": "Alarm zrušený hlasom." if ok else "Fráza „som v poriadku“ nebola rozpoznaná."}
