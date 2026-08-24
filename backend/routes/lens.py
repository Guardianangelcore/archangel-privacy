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
import os, uuid, hashlib, json, base64, re, tempfile, inspect

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
from emergentintegrations.llm.openai import OpenAISpeechToText

from core import (
    api, db, logger, clean, get_current_user, _aml_ledger_append,
    APP_NAME, put_object_sync, EMERGENT_LLM_KEY, send_push,
)

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
async def lens_analyze(file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
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

    # keep the photo in the vault-grade storage (for save_to_vault action)
    scan_id = uuid.uuid4().hex
    path = f"{APP_NAME}/lens/{user['user_id']}/{scan_id}.jpg"
    try:
        await run_in_threadpool(put_object_sync, path, data, ctype)
    except Exception as e:
        logger.warning(f"lens storage failed (non-fatal): {e}")
        path = None

    b64 = base64.b64encode(data).decode()
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"lens-{scan_id[:8]}",
        system_message=LENS_SYSTEM,
    ).with_model("openai", "gpt-5.4")
    try:
        resp = await chat.send_message(UserMessage(
            text="Analyze this medical artefact photo. Answer with the JSON object only.",
            file_contents=[ImageContent(image_base64=b64)],
        ))
        verdict = _parse_lens_json(resp or "")
    except json.JSONDecodeError:
        verdict = {"kind": "other", "name": "Neznámy artefakt",
                   "summary_sk": (resp or "").strip()[:800] or "Obsah sa nepodarilo spoľahlivo rozpoznať. Skúste ostrejšiu fotku pri lepšom svetle.",
                   "warnings": [], "specialty": "", "suggested_actions": ["save_to_vault"]}
    except Exception as e:
        logger.error(f"lens vision error: {e}")
        raise HTTPException(502, "AI vision service unavailable")

    scan = {
        "scan_id": scan_id, "user_id": user["user_id"],
        "sha256": hashlib.sha256(data).hexdigest(),
        "storage_path": path, "image_size": len(data),
        **verdict,
        "ai_generated": True,
        "created_at": datetime.now(timezone.utc),
    }
    await db.lens_scans.insert_one(scan.copy())
    return clean(scan)

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
