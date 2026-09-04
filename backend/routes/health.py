# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
from fastapi import HTTPException, Header, UploadFile, File, Form
from fastapi.responses import Response, StreamingResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import os, uuid, hashlib, json, io, re, base64, httpx, asyncio, math

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

from core import (
    api, db, logger, clean, get_current_user, send_push, _push_client,
    AI_COMPLIANCE_NOTE, _aml_ledger_append, apply_watermark,
    AML_UNVERIFIED_DAILY, AML_VERIFIED_DAILY, AML_MAX_TX_PER_DAY,
    _FONT_R, _FONT_B, _make_pdf, _auth_pdf, _pdf_footer, _pdf_response,
    APP_NAME, put_object_sync, get_object_sync, init_storage,
    EMERGENT_LLM_KEY, AUTH_SESSION_URL,
)
from models import User, EmergencyProfile, Document, WaitlistItem, FallEvent

from emergentintegrations.llm.openai import OpenAITextToSpeech
from content import MENTAL_TECHNIQUES, MENTAL_DISCLAIMERS, PHYSIO_GUIDES, STEP_WORD

# --------- VAULT: DOCUMENTS ---------
@api.get("/vault/documents")
async def list_documents(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    docs = await db.documents.find({"user_id": user["user_id"]}, {"_id": 0}).sort("uploaded_at", -1).to_list(500)
    return docs

@api.post("/vault/documents")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(""),
    authorization: Optional[str] = Header(None),
):
    user = await get_current_user(authorization)
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(400, "Empty file")
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 25MB)")

    doc_id = uuid.uuid4().hex
    ext = (file.filename or "").split(".")[-1].lower() if "." in (file.filename or "") else "bin"
    path = f"{APP_NAME}/uploads/{user['user_id']}/{doc_id}.{ext}"
    file_hash = hashlib.sha256(data).hexdigest()

    try:
        await run_in_threadpool(put_object_sync, path, data, file.content_type or "application/octet-stream")
    except Exception as e:
        logger.error(f"upload failed: {e}")
        raise HTTPException(502, "Storage upload failed")

    doc = Document(
        doc_id=doc_id, user_id=user["user_id"],
        title=title or file.filename or "Document",
        file_name=file.filename or f"{doc_id}.{ext}",
        content_type=file.content_type or "application/octet-stream",
        size=len(data), storage_path=path, hash=file_hash,
    ).model_dump()
    await db.documents.insert_one(doc.copy())
    # Health Timeline indexing — every saved file is immediately visible on the timeline
    await db.calendar_events.insert_one({
        "event_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "category": "history", "title": f"📄 {doc['title']}"[:140],
        "date": datetime.now(timezone.utc).date().isoformat(),
        "notes": "Document stored in the Health Vault", "booster_due": None,
        "source": "vault", "doc_id": doc_id,
        "created_at": datetime.now(timezone.utc),
    })
    # Jarvis Autopilot (Medical Sentinel) — orchestrate the new document in the
    # background: OCR → AI preklad → kalendár → rezervácia termínu, bez pýtania.
    if user.get("jarvis_autopilot", True):
        from routes.orchestrator import orchestrate_document
        asyncio.create_task(orchestrate_document(user["user_id"], doc_id))
        doc["autopilot"] = "started"
    return clean(doc)

@api.get("/vault/documents/{doc_id}/file")
async def download_document(doc_id: str, authorization: Optional[str] = Header(None), token: Optional[str] = None):
    # Accept token via query for <img> tags on web
    if not authorization and token:
        authorization = f"Bearer {token}"
    user = await get_current_user(authorization)
    doc = await db.documents.find_one({"doc_id": doc_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Not found")
    try:
        content, ctype = await run_in_threadpool(get_object_sync, doc["storage_path"])
    except Exception as e:
        raise HTTPException(502, f"Storage read failed: {e}")
    return Response(content=content, media_type=ctype)

@api.delete("/vault/documents/{doc_id}")
async def delete_document(doc_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.documents.delete_one({"doc_id": doc_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}

# --------- OCR (vision AI) ---------
OCR_SYSTEM = (
    "You are a precise OCR engine for medical documents. Extract ALL text from the provided "
    "image exactly as written, preserving line structure, tables and values. "
    "Output ONLY the extracted text — no commentary, no markdown fences."
)

async def _ocr_image_bytes(img_bytes: bytes, tag: str) -> str:
    b64 = base64.b64encode(img_bytes).decode()
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"ocr-{tag}-{uuid.uuid4().hex[:6]}",
        system_message=OCR_SYSTEM,
    ).with_model("openai", "gpt-5.4")
    resp = await chat.send_message(UserMessage(
        text="Extract all text from this document image.",
        file_contents=[ImageContent(image_base64=b64)],
    ))
    return (resp or "").strip()

async def extract_doc_text(doc: dict) -> str:
    """Read a vault document from storage and extract its text (PDF text layer,
    scanned-PDF vision OCR fallback, or image vision OCR). Caches on the doc."""
    if doc.get("extracted_text"):
        return doc["extracted_text"]
    content, _ = await run_in_threadpool(get_object_sync, doc["storage_path"])
    ctype = (doc.get("content_type") or "").lower()
    fname = (doc.get("file_name") or "").lower()
    doc_id = doc["doc_id"]
    text = ""
    if "pdf" in ctype or fname.endswith(".pdf"):
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        text = "\n".join((p.extract_text() or "") for p in reader.pages[:20]).strip()
        if len(text) < 50:
            # Scanned PDF — rasterize first pages and run vision OCR
            import fitz  # pymupdf
            pdf = fitz.open(stream=content, filetype="pdf")
            parts = []
            for i, page in enumerate(pdf):
                if i >= 3:
                    break
                pix = page.get_pixmap(dpi=150)
                parts.append(await _ocr_image_bytes(pix.tobytes("png"), doc_id))
            text = "\n\n".join(p for p in parts if p).strip()
    elif ctype.startswith("image/") or fname.endswith((".jpg", ".jpeg", ".png", ".webp", ".heic")):
        text = await _ocr_image_bytes(content, doc_id)
    else:
        raise HTTPException(400, "OCR supports images and PDFs only")
    if text:
        await db.documents.update_one({"doc_id": doc_id}, {"$set": {"extracted_text": text}})
    return text

# --------- BIRTH YEAR AUTO-DETECT (Zero-Friction Age Sync) ---------
# When an ID/passport/birth certificate is OCR'd, extract the birth year and
# silently update the user's Bio-Timeline. Never overwrites an existing value.
_BIRTH_YEAR_PATTERNS = [
    # SK ID pattern: RČ (rodné číslo) — YYMMDD/XXXX; year=YY (with century inference)
    re.compile(r"\b(?:RČ|rodné\s*číslo|rodne\s*cislo|birth\s*number)[^0-9]{0,10}(\d{2})(\d{2})(\d{2})[/-]?(\d{3,4})\b", re.I),
    # Date of birth: DD.MM.YYYY / DD/MM/YYYY / DD-MM-YYYY (whitespace-tolerant)
    re.compile(r"\b(?:dátum\s+narodenia|datum\s+narozeni|date\s+of\s+birth|geburtsdatum|dob)[^0-9]{0,10}(\d{1,2})\s*[.\-/]\s*(\d{1,2})\s*[.\-/]\s*(\d{4})\b", re.I),
    # ISO YYYY-MM-DD after DOB label
    re.compile(r"\b(?:dátum\s+narodenia|datum\s+narozeni|date\s+of\s+birth|geburtsdatum|dob)[^0-9]{0,10}(\d{4})-(\d{2})-(\d{2})\b", re.I),
    # Loose "narodený/narodená DD.MM.YYYY" (whitespace-tolerant, gendered)
    re.compile(r"\bnaroden(?:[ýá]|a|y)?\s+(?:d[ňn]a\s+)?(\d{1,2})\s*[.\-/]\s*(\d{1,2})\s*[.\-/]\s*(\d{4})\b", re.I),
]

def _detect_birth_year(text: str) -> Optional[int]:
    if not text:
        return None
    t = text[:8000]
    now_year = datetime.now(timezone.utc).year
    for i, pat in enumerate(_BIRTH_YEAR_PATTERNS):
        m = pat.search(t)
        if not m:
            continue
        groups = m.groups()
        try:
            if i == 0:
                # RČ: century inference — trailing block of 3 digits ≈ pre-1954, 4 digits ≈ 1954+
                yy = int(groups[0])
                trailing = groups[3] or ""
                century = 1900 if len(trailing) == 3 else 2000 if yy < 54 else 1900
                year = century + yy
            elif i == 2:
                year = int(groups[0])
            else:
                year = int(groups[2])
            if 1900 <= year <= now_year - 1:
                return year
        except (ValueError, IndexError):
            continue
    return None


@api.post("/vault/documents/{doc_id}/ocr")
async def ocr_document(doc_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    doc = await db.documents.find_one({"doc_id": doc_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Not found")
    cached_text = doc.get("extracted_text")
    if cached_text:
        return {
            "extracted_text": cached_text,
            "cached": True,
            "birth_year_detected": None,  # already-cached docs don't re-scan
            "birth_year_applied": False,  # never mutates state on cache hits
        }
    try:
        text = await extract_doc_text(doc)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR error: {e}")
        raise HTTPException(502, "OCR service failed")

    if not text:
        raise HTTPException(422, "No text could be extracted from this document")

    # Zero-Friction Age Sync — auto-detect + patch only if user has NO birth_year yet.
    by_detected = _detect_birth_year(text)
    by_applied = False
    if by_detected and not user.get("birth_year"):
        try:
            await db.users.update_one(
                {"user_id": user["user_id"]},
                {"$set": {"birth_year": by_detected}},
            )
            by_applied = True
        except Exception as e:
            logger.warning(f"birth_year autofill failed: {e}")

    return {
        "extracted_text": text,
        "birth_year_detected": by_detected,
        "birth_year_applied": by_applied,
    }


# --------- AI HEALTH TRANSLATOR ---------
LANG_NAMES = {"sk": "Slovak", "cs": "Czech", "en": "English", "de": "German"}

def build_translator_system(lang_code: str) -> str:
    lang = LANG_NAMES.get(lang_code, "English")
    return (
        f"You are Jarvis, the Guardian Health medical translator. "
        f"Translate medical reports, diagnoses, and jargon into simple, warm, plain {lang} "
        f"that a senior patient with no medical background can understand. "
        f"Structure the response as: 1) Summary in 1-2 sentences, "
        f"2) What this means (bullet list of plain-language points), "
        f"3) Recommendations (2-3 practical next steps) — section headings in {lang}. "
        f"NEVER invent medications or diagnoses. If information is unclear, say so. "
        f"Respond ONLY in {lang}." + AI_COMPLIANCE_NOTE
    )

# --------- NEXT-APPOINTMENT EXTRACTION (gpt-5.4, strict JSON) ---------
APPT_SYSTEM = (
    "You extract the next upcoming medical appointment from medical text. "
    'Reply ONLY with strict JSON: {"found": true/false, "date": "YYYY-MM-DD" or null, '
    '"time": "HH:MM" or null, "title": "short label in the language of the document, e.g. Check-up — orthopedics"}. '
    "Only report a date explicitly stated as a FUTURE appointment / check-up "
    "(kontrola, termín, vyšetrenie, dostavte sa, objednaný na). If none, found=false. No prose."
)

async def extract_next_appointment(text: str, tag: str) -> Optional[dict]:
    """Flag the 'Next Appointment Date' from medical text — never raises."""
    if not text or not text.strip() or not EMERGENT_LLM_KEY:
        return None
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"appt-{tag}",
                       system_message=APPT_SYSTEM).with_model("openai", "gpt-5.4")
        resp = await chat.send_message(UserMessage(text=text[:6000]))
        import json as _json
        m = re.search(r"\{.*\}", resp or "", re.S)
        data = _json.loads(m.group(0)) if m else {}
        if data.get("found") and data.get("date"):
            datetime.strptime(str(data["date"]), "%Y-%m-%d")
            return {"date": data["date"], "time": data.get("time"),
                    "title": (data.get("title") or "Doctor's appointment")[:140]}
    except Exception as e:
        logger.warning(f"appointment extraction failed: {e}")
    return None

class TranslateIn(BaseModel):
    text: str
    language: str = "sk"

@api.post("/ai/translate")
async def ai_translate(body: TranslateIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if not body.text.strip():
        raise HTTPException(400, "Empty text")
    if not EMERGENT_LLM_KEY:
        raise HTTPException(500, "AI key not configured")

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"translate-{user['user_id']}-{uuid.uuid4().hex[:8]}",
        system_message=build_translator_system(body.language),
    ).with_model("anthropic", "claude-sonnet-5")

    try:
        resp = await chat.send_message(UserMessage(text=body.text[:8000]))
        appt = await extract_next_appointment(body.text, f"t{user['user_id'][:8]}")
        return {"plain_language": resp, "next_appointment": appt}
    except Exception as e:
        logger.error(f"AI translate error: {e}")
        raise HTTPException(502, "AI service unavailable")

class TranslateDocIn(BaseModel):
    doc_id: str
    language: str = "sk"
    excerpt: str = ""  # optional user-provided text if OCR not done

@api.post("/ai/translate-document")
async def ai_translate_doc(body: TranslateDocIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    doc = await db.documents.find_one({"doc_id": body.doc_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Doc not found")
    source_text = body.excerpt.strip() or (doc.get("extracted_text") or "").strip() or f"[Medical document titled '{doc['title']}' — user has not provided extracted text; give general guidance about what to look for and how to prepare questions for their doctor.]"

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"doctranslate-{doc['doc_id']}",
        system_message=build_translator_system(body.language),
    ).with_model("anthropic", "claude-sonnet-5")
    try:
        resp = await chat.send_message(UserMessage(text=source_text[:8000]))
        appt = await extract_next_appointment(source_text, doc["doc_id"][:12])
        await db.documents.update_one(
            {"doc_id": doc["doc_id"]},
            {"$set": {"plain_language": resp, "translation": resp, "next_appointment": appt}},
        )
        return {"plain_language": resp, "next_appointment": appt}
    except Exception as e:
        logger.error(f"AI translate doc error: {e}")
        raise HTTPException(502, "AI service unavailable")


# --------- VOICE: TTS (OpenAI via Emergent key · optional ElevenLabs for native Slovak) ---------
_tts_client: Optional[OpenAITextToSpeech] = None
def get_tts():
    global _tts_client
    if _tts_client is None:
        _tts_client = OpenAITextToSpeech(api_key=EMERGENT_LLM_KEY)
    return _tts_client

OPENAI_VOICES = {
    "alloy": "Neutral, balanced", "ash": "Clear, articulate", "coral": "Warm, friendly",
    "echo": "Smooth, calm", "fable": "Expressive, storytelling", "nova": "Energetic, upbeat",
    "onyx": "Deep, authoritative", "sage": "Wise, measured", "shimmer": "Bright, cheerful",
}
DEFAULT_OPENAI_VOICE = "onyx"       # JARVIS PRESET — deep, authoritative (Tony Stark's JARVIS)
DEFAULT_TTS_SPEED = 0.9             # slow, measured delivery
ELEVEN_MODEL = "eleven_multilingual_v2"     # native pronunciation for sk/cs/de/… (29 languages)

def _eleven_key() -> str:
    return os.environ.get("ELEVENLABS_API_KEY", "").strip()

_eleven_client = None
def get_eleven():
    global _eleven_client
    if _eleven_client is None:
        from elevenlabs.client import AsyncElevenLabs
        _eleven_client = AsyncElevenLabs(api_key=_eleven_key(), timeout=15.0)
    return _eleven_client

async def _eleven_speech(text: str, voice_id: str, speed: float) -> bytes:
    from elevenlabs import VoiceSettings
    # High stability + low style = calm, authoritative, even delivery (JARVIS preset).
    stream = get_eleven().text_to_speech.convert(
        text=text, voice_id=voice_id, model_id=ELEVEN_MODEL, output_format="mp3_44100_128",
        voice_settings=VoiceSettings(stability=0.7, similarity_boost=0.8, style=0.1,
                                     use_speaker_boost=True, speed=min(1.2, max(0.7, speed))),
    )
    buf = b""
    async for chunk in stream:
        buf += chunk
    return buf

_eleven_voices_cache: dict = {"at": 0.0, "voices": []}
async def _eleven_voices() -> list:
    """Voices available on the configured ElevenLabs account (premade + library/cloned)."""
    import time as _t
    if not _eleven_key():
        return []
    if _t.time() - _eleven_voices_cache["at"] < 600 and _eleven_voices_cache["voices"]:
        return _eleven_voices_cache["voices"]
    try:
        res = await get_eleven().voices.get_all()
        out = []
        for v in (res.voices or []):
            labels = getattr(v, "labels", None) or {}
            out.append({"voice_id": v.voice_id, "name": v.name, "category": getattr(v, "category", "") or "",
                        "language": labels.get("language", ""), "accent": labels.get("accent", ""),
                        "gender": labels.get("gender", ""), "description": labels.get("description", ""),
                        "preview_url": getattr(v, "preview_url", None)})
        _eleven_voices_cache.update(at=_t.time(), voices=out)
        return out
    except Exception as e:
        logger.warning(f"elevenlabs voices err {e}")
        return _eleven_voices_cache["voices"]

def clean_for_tts(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)
    text = re.sub(r"[*_#>~|]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:4000]

_tts_cache: dict = {}  # in-memory {hash: bytes}

class TTSIn(BaseModel):
    text: str
    voice: Optional[str] = None       # OpenAI voice — honoured ONLY with override (Settings preview)
    language: str = "sk"
    speed: float = DEFAULT_TTS_SPEED  # emotional pacing: 0.85 soothing · 0.9 default · 1.0 alert
    engine: Optional[str] = None      # "openai" | "elevenlabs" (preview / explicit)
    eleven_voice_id: Optional[str] = None
    override: bool = False            # True = use exactly the requested engine/voice (Settings preview)
    stream: bool = False              # True = LIVE: audio bytes are relayed while the engine still renders

def _resolve_voice(user: dict, body: TTSIn) -> tuple[str, str]:
    """→ (engine, voice). ONE unified JARVIS preset app-wide: the user's Settings voice, else
    'onyx'. Per-screen `voice` hints are ignored (only `override` — the Settings preview — wins).
    ElevenLabs silently falls back to OpenAI when no key / no voice is configured."""
    if body.override:
        engine = body.engine or "openai"
        voice = body.eleven_voice_id if engine == "elevenlabs" else (body.voice or DEFAULT_OPENAI_VOICE)
    else:
        engine = user.get("voice_engine") or "openai"
        voice = user.get("eleven_voice_id") if engine == "elevenlabs" \
            else (user.get("jarvis_voice") or DEFAULT_OPENAI_VOICE)
    if engine == "elevenlabs" and (not _eleven_key() or not voice):
        engine, voice = "openai", (user.get("jarvis_voice") or DEFAULT_OPENAI_VOICE)
    if engine == "openai" and voice not in OPENAI_VOICES:
        voice = DEFAULT_OPENAI_VOICE
    return engine, voice

@api.post("/voice/tts")
async def tts_generate(body: TTSIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if not EMERGENT_LLM_KEY:
        raise HTTPException(500, "TTS key not configured")
    text = clean_for_tts(body.text)
    if not text:
        raise HTTPException(400, "Empty text")
    speed = min(1.3, max(0.7, body.speed or DEFAULT_TTS_SPEED))
    engine, voice = _resolve_voice(user, body)
    model = ELEVEN_MODEL if engine == "elevenlabs" else "tts-1"
    key = hashlib.sha256(f"{text}|{engine}|{voice}|{speed}|{model}|mp3".encode()).hexdigest()
    if key in _tts_cache:
        return {"key": key, "url": f"/api/voice/tts/{key}.mp3", "engine": engine, "voice": voice, "cached": True}
    if body.stream:
        # LIVE — no wait for the full render, no second download round-trip: the player pulls
        # the bytes as ElevenLabs / OpenAI produce them (one-shot public ticket URL).
        job_id = _start_live_job(key, engine, voice, speed, text, body.language,
                                 fallback_voice=(user.get("jarvis_voice") or DEFAULT_OPENAI_VOICE))
        return {"key": key, "url": f"/api/voice/tts/live/{job_id}.mp3", "engine": engine, "voice": voice, "live": True}
    try:
        if engine == "elevenlabs":
            try:
                audio = await _eleven_speech(text, voice, speed)
            except Exception as e:
                logger.warning(f"elevenlabs tts failed, falling back to openai: {e}")
                engine, voice = "openai", (user.get("jarvis_voice") or DEFAULT_OPENAI_VOICE)
                audio = await get_tts().generate_speech(text=text, model="tts-1", voice=voice, speed=speed)
        else:
            audio = await get_tts().generate_speech(text=text, model="tts-1", voice=voice, speed=speed)
        _tts_cache[key] = audio
    except Exception as e:
        logger.error(f"tts err {e}")
        raise HTTPException(502, "TTS service failed")
    return {"key": key, "url": f"/api/voice/tts/{key}.mp3", "engine": engine, "voice": voice}


# --------- LIVE TTS RELAY (first sound in ~0.5 s with ElevenLabs Flash · no intermediate download) ---------
ELEVEN_LIVE_MODEL = "eleven_flash_v2_5"     # ~75 ms model latency · 32 languages incl. sk/cs/de/pl/hu
ELEVEN_LIVE_LANGS = {"sk", "cs", "en", "de", "pl", "hu", "ru", "es", "fr", "it", "uk", "zh", "ja", "ar", "pt", "nl", "ro"}
LIVE_JOB_TTL = 600.0
_live_jobs: dict = {}   # job_id -> {"chunks": [bytes], "done": bool, "error": str|None, "key": str, "at": float}


async def _eleven_stream(text: str, voice_id: str, speed: float, language: str):
    from elevenlabs import VoiceSettings
    lang = (language or "")[:2].lower()
    kwargs = {"language_code": lang} if lang in ELEVEN_LIVE_LANGS else {}
    stream = get_eleven().text_to_speech.stream(
        text=text, voice_id=voice_id, model_id=ELEVEN_LIVE_MODEL, output_format="mp3_44100_128",
        optimize_streaming_latency=3,
        voice_settings=VoiceSettings(stability=0.7, similarity_boost=0.8, style=0.1,
                                     use_speaker_boost=True, speed=min(1.2, max(0.7, speed))),
        **kwargs,
    )
    async for chunk in stream:
        if chunk:
            yield chunk


async def _openai_stream(text: str, voice: str, speed: float):
    """Relay OpenAI TTS bytes as the Emergent proxy sends them (OpenAI-compatible /audio/speech)."""
    base = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
    headers = {"Authorization": f"Bearer {EMERGENT_LLM_KEY}", "Content-Type": "application/json"}
    if os.environ.get("APP_URL"):
        headers["X-App-ID"] = os.environ["APP_URL"]
    payload = {"model": "tts-1", "input": text, "voice": voice, "speed": speed, "response_format": "mp3"}
    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=5.0)) as cli:
        async with cli.stream("POST", f"{base}/llm/audio/speech", headers=headers, json=payload) as r:
            r.raise_for_status()
            async for chunk in r.aiter_bytes():
                if chunk:
                    yield chunk


async def _run_live_job(job_id: str, engine: str, voice: str, speed: float, text: str, language: str, fallback_voice: str):
    job = _live_jobs[job_id]
    try:
        gen = _eleven_stream(text, voice, speed, language) if engine == "elevenlabs" else _openai_stream(text, voice, speed)
        async for chunk in gen:
            job["chunks"].append(chunk)
    except Exception as e:
        logger.warning(f"live tts ({engine}) failed: {e}")
        if not job["chunks"]:
            try:   # full-render fallback — never leave the player with an empty stream
                job["chunks"].append(await get_tts().generate_speech(text=text, model="tts-1", voice=fallback_voice, speed=speed))
            except Exception as e2:
                logger.error(f"live tts fallback err {e2}")
                job["error"] = str(e2)
    job["done"] = True
    if job["chunks"] and not job["error"]:
        _tts_cache[job["key"]] = b"".join(job["chunks"])


def _start_live_job(key: str, engine: str, voice: str, speed: float, text: str, language: str, fallback_voice: str) -> str:
    import time as _t
    now = _t.time()
    for jid in [j for j, v in _live_jobs.items() if now - v["at"] > LIVE_JOB_TTL]:
        _live_jobs.pop(jid, None)
    job_id = uuid.uuid4().hex
    _live_jobs[job_id] = {"chunks": [], "done": False, "error": None, "key": key, "at": now}
    asyncio.create_task(_run_live_job(job_id, engine, voice, speed, text, language, fallback_voice))
    return job_id


async def _iter_live(job: dict):
    i = 0
    while True:
        while i < len(job["chunks"]):
            yield job["chunks"][i]
            i += 1
        if job["done"]:
            return
        await asyncio.sleep(0.03)


def _live_response(job: dict):
    if job["done"]:   # finished (or player re-request / range probe) → plain file response
        if job["error"] and not job["chunks"]:
            raise HTTPException(502, "TTS service failed")
        return Response(content=b"".join(job["chunks"]), media_type="audio/mpeg", headers={"Cache-Control": "no-store"})
    return StreamingResponse(_iter_live(job), media_type="audio/mpeg",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@api.get("/voice/tts/live/{job_id}.mp3")
async def tts_live(job_id: str):
    job = _live_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "expired")
    return _live_response(job)


# --------- INTRO NARRATION (public · fixed script · JARVIS preset) ---------
INTRO_SCRIPT = {
    "sk": "Vitajte v Archangel OS. Som Jarvis — váš strážny anjel. Systém je pripravený.",
    "cs": "Vítejte v Archangel OS. Jsem Jarvis — váš strážný anděl. Systém je připraven.",
    "en": "Welcome to Archangel OS. I am Jarvis — your guardian angel. The system is ready.",
    "de": "Willkommen bei Archangel OS. Ich bin Jarvis — Ihr Schutzengel. Das System ist bereit.",
    "pl": "Witaj w Archangel OS. Jestem Jarvis — twój anioł stróż. System jest gotowy.",
    "hu": "Üdvözlöm az Archangel OS-ben. Jarvis vagyok — az őrangyala. A rendszer készen áll.",
    "es": "Bienvenido a Archangel OS. Soy Jarvis, su ángel guardián. El sistema está listo.",
    "fr": "Bienvenue dans Archangel OS. Je suis Jarvis, votre ange gardien. Le système est prêt.",
    "it": "Benvenuto in Archangel OS. Sono Jarvis, il tuo angelo custode. Il sistema è pronto.",
    "uk": "Вітаю в Archangel OS. Я Джарвіс — ваш янгол-охоронець. Система готова.",
    "ru": "Добро пожаловать в Archangel OS. Я Джарвис — ваш ангел-хранитель. Система готова.",
}


@api.get("/voice/intro.mp3")
async def voice_intro(lang: str = "en"):
    """PUBLIC (pre-login) — the cinematic intro narration in the app language, JARVIS preset."""
    if not EMERGENT_LLM_KEY:
        raise HTTPException(500, "TTS key not configured")
    lk = (lang or "en")[:2].lower()
    text = INTRO_SCRIPT.get(lk) or INTRO_SCRIPT["en"]
    speed = 0.88
    key = hashlib.sha256(f"{text}|openai|{DEFAULT_OPENAI_VOICE}|{speed}|tts-1|mp3".encode()).hexdigest()
    if key in _tts_cache:
        return Response(content=_tts_cache[key], media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=86400"})
    # one shared render per language — concurrent app starts attach to the same job
    for job in _live_jobs.values():
        if job["key"] == key and not job["done"]:
            return _live_response(job)
    job_id = _start_live_job(key, "openai", DEFAULT_OPENAI_VOICE, speed, text, lk, DEFAULT_OPENAI_VOICE)
    return _live_response(_live_jobs[job_id])

@api.get("/voice/voices")
async def tts_voices(authorization: Optional[str] = Header(None)):
    """Voice catalogue for Settings: 9 OpenAI voices (Emergent key) + the ElevenLabs account voices."""
    user = await get_current_user(authorization)
    eleven = await _eleven_voices()
    return {
        "openai": [{"id": k, "label": k.capitalize(), "description": v} for k, v in OPENAI_VOICES.items()],
        "elevenlabs": eleven,
        "elevenlabs_available": bool(_eleven_key()),
        "current": {"engine": user.get("voice_engine") or "openai",
                    "jarvis_voice": user.get("jarvis_voice") or DEFAULT_OPENAI_VOICE,
                    "eleven_voice_id": user.get("eleven_voice_id") or ""},
    }

@api.get("/voice/tts/{key}.mp3")
async def tts_stream(key: str):
    audio = _tts_cache.get(key)
    if not audio:
        raise HTTPException(404, "not cached")
    return Response(content=audio, media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=31536000"})

class STTIn(BaseModel):
    audio_base64: str  # base64-encoded audio
    language: Optional[str] = "sk"

@api.post("/voice/stt")
async def voice_stt(body: STTIn, authorization: Optional[str] = Header(None)):
    """STT stub — returns a mocked transcription. Real Whisper wire-in pending."""
    await get_current_user(authorization)
    # MOCKED: real Whisper integration deferred to Phase 3
    return {"transcript": "[MOCKED transcript — Whisper integration deferred]", "mocked": True}

# --------- PHYSIO-AI ---------
class PhysioIn(BaseModel):
    region: str  # neck, back, shoulders, hips, knees, hands, feet
    intensity: str = "light"
    language: str = "sk"

@api.post("/physio/session")
async def physio(body: PhysioIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    lang = LANG_NAMES.get(body.language, "English")
    system = (
        f"You are Physio-AI, guided by the Guardian Angel's professional experience in self-massage and ergonomics. "
        f"Give a warm, patient, senior-friendly 5-step self-massage & mobility routine for the {body.region} at {body.intensity} intensity. "
        f"Include: warning about pain, step-by-step actions with duration in seconds, breathing cue, and 1 ergonomic tip. "
        f"Respond ONLY in {lang}. Use short sentences and numbered steps." + AI_COMPLIANCE_NOTE
    )
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"physio-{user['user_id']}-{uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-5")
    try:
        resp = await chat.send_message(UserMessage(text=f"Region: {body.region}. Intensity: {body.intensity}."))
        try:
            from routes.agent import award_xp
            await award_xp(user["user_id"], 10, "physio_session")
        except Exception:
            pass
        return {"routine": resp}
    except Exception as e:
        logger.error(f"physio err {e}")
        raise HTTPException(502, "AI unavailable")


# --------- SURVIVAL MEDICINE CABINET ---------
class CabinetItemIn(BaseModel):
    name: str
    quantity: float = 1
    unit: str = "ks"
    expires_on: Optional[str] = None  # YYYY-MM-DD
    category: str = "other"
    prescription: bool = False
    notes: Optional[str] = ""

def _expiry_status(expires_on: Optional[str]) -> str:
    if not expires_on:
        return "ok"
    try:
        exp = datetime.strptime(expires_on, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return "ok"
    now = datetime.now(timezone.utc)
    if exp < now:
        return "expired"
    if exp < now + timedelta(days=30):
        return "expiring_soon"
    return "ok"

@api.get("/cabinet/items")
async def cabinet_list(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    items = await db.cabinet_items.find({"user_id": user["user_id"]}, {"_id": 0}).sort("expires_on", 1).to_list(300)
    for it in items:
        it["status"] = _expiry_status(it.get("expires_on"))
    return items

@api.post("/cabinet/items")
async def cabinet_add(body: CabinetItemIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    doc = {"item_id": uuid.uuid4().hex, "user_id": user["user_id"], **body.model_dump(), "created_at": datetime.now(timezone.utc)}
    await db.cabinet_items.insert_one(doc.copy())
    doc["status"] = _expiry_status(doc.get("expires_on"))
    return clean(doc)

class CabinetPatch(BaseModel):
    quantity: Optional[float] = None
    expires_on: Optional[str] = None
    notes: Optional[str] = None

@api.patch("/cabinet/items/{item_id}")
async def cabinet_patch(item_id: str, body: CabinetPatch, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    res = await db.cabinet_items.update_one({"item_id": item_id, "user_id": user["user_id"]}, {"$set": upd})
    if res.matched_count == 0:
        raise HTTPException(404, "Not found")
    doc = await db.cabinet_items.find_one({"item_id": item_id}, {"_id": 0})
    doc["status"] = _expiry_status(doc.get("expires_on"))
    return doc

@api.delete("/cabinet/items/{item_id}")
async def cabinet_del(item_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.cabinet_items.delete_one({"item_id": item_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}

class ExchangeIn(BaseModel):
    type: str  # "offer" | "request"
    item_name: str
    quantity: float = 1
    unit: str = "ks"
    city: str = ""
    note: Optional[str] = ""

@api.get("/cabinet/exchange")
async def exchange_list(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    return await db.cabinet_exchange.find({"status": "open"}, {"_id": 0}).sort("created_at", -1).to_list(200)

@api.post("/cabinet/exchange")
async def exchange_add(body: ExchangeIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if body.type not in ("offer", "request"):
        raise HTTPException(400, "type must be offer or request")
    doc = {
        "exchange_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "owner_name": user.get("name") or user["email"], "owner_did": user["did"],
        **body.model_dump(), "status": "open", "created_at": datetime.now(timezone.utc),
        "non_prescription_declared": True,
    }
    await db.cabinet_exchange.insert_one(doc.copy())
    return clean(doc)

class ExchangeRespondIn(BaseModel):
    message: Optional[str] = ""

@api.post("/cabinet/exchange/{exchange_id}/respond")
async def exchange_respond(exchange_id: str, body: ExchangeRespondIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    ex = await db.cabinet_exchange.find_one({"exchange_id": exchange_id, "status": "open"}, {"_id": 0})
    if not ex:
        raise HTTPException(404, "Not found or closed")
    if ex["user_id"] == user["user_id"]:
        raise HTTPException(400, "Cannot respond to your own listing")
    await db.cabinet_exchange.update_one(
        {"exchange_id": exchange_id},
        {"$set": {"status": "matched", "matched_with": user["user_id"], "matched_name": user.get("name") or user["email"], "matched_at": datetime.now(timezone.utc), "message": body.message}},
    )
    try:
        await send_push(
            recipients=[ex["user_id"]],
            data={"title": "P2P Exchange 🤝", "message": f"{user.get('name') or 'A neighbor'} is responding to: {ex['item_name']}", "action_url": "/medicine-cabinet"},
        )
    except Exception as e:
        logger.warning(f"push failed: {e}")
    return {"ok": True, "matched": True}

@api.delete("/cabinet/exchange/{exchange_id}")
async def exchange_del(exchange_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.cabinet_exchange.delete_one({"exchange_id": exchange_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}


# --------- MEDICATION REMINDERS (Angel Mode) ---------
class MedReminderIn(BaseModel):
    name: str
    dose: Optional[str] = ""
    times: List[str] = ["08:00"]
    slots: Optional[List[str]] = None  # upon_waking|breakfast|lunch|evening|night|as_needed

@api.get("/meds/reminders")
async def meds_list(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.med_reminders.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", 1).to_list(100)

@api.post("/meds/reminders")
async def meds_add(body: MedReminderIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    times = sorted({t for t in body.times if re.match(r"^\d{2}:\d{2}$", t)})
    as_needed = bool(body.slots and "as_needed" in body.slots)
    if not body.name or (not times and not as_needed):
        raise HTTPException(400, "Name and at least one valid time (HH:MM) required")
    doc = {
        "reminder_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "name": body.name, "dose": body.dose or "", "times": times,
        "slots": body.slots or [],
        "created_at": datetime.now(timezone.utc),
    }
    await db.med_reminders.insert_one(doc.copy())
    return clean(doc)

@api.delete("/meds/reminders/{reminder_id}")
async def meds_del(reminder_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.med_reminders.delete_one({"reminder_id": reminder_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    await db.med_intakes.delete_many({"reminder_id": reminder_id})
    return {"ok": True}

@api.get("/meds/today")
async def meds_today(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    reminders = await db.med_reminders.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(100)
    intakes = await db.med_intakes.find({"user_id": user["user_id"], "date": day}, {"_id": 0}).to_list(300)
    taken = {(i["reminder_id"], i["time"]) for i in intakes}
    out = []
    for r in reminders:
        for tm in r["times"]:
            out.append({
                "reminder_id": r["reminder_id"], "name": r["name"], "dose": r["dose"],
                "time": tm, "taken": (r["reminder_id"], tm) in taken,
            })
    out.sort(key=lambda x: x["time"])
    return {"date": day, "items": out, "pending": sum(1 for x in out if not x["taken"])}

class IntakeIn(BaseModel):
    reminder_id: str
    time: str

@api.post("/meds/intake")
async def meds_intake(body: IntakeIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rem = await db.med_reminders.find_one({"reminder_id": body.reminder_id, "user_id": user["user_id"]}, {"_id": 0})
    if not rem:
        raise HTTPException(404, "Not found")
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await db.med_intakes.update_one(
        {"user_id": user["user_id"], "reminder_id": body.reminder_id, "date": day, "time": body.time},
        {"$set": {"taken_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    try:
        from routes.agent import award_xp
        await award_xp(user["user_id"], 10, "med_taken")
    except Exception:
        pass
    return {"ok": True, "taken": True}


# =========================================================================

BORDER_LANGS = [
    ("en", "English", "The holder of this certificate carries personal prescription medication necessary for their health and survival. Please allow the transport of the listed medication across borders in accordance with medical and humanitarian necessity."),
    ("sk", "Slovenčina", "Držiteľ tohto certifikátu prepravuje osobné lieky na predpis, nevyhnutné pre jeho zdravie a prežitie. Prosíme, umožnite prevoz uvedených liekov cez hranice v súlade so zdravotnou a humanitárnou nevyhnutnosťou."),
    ("cs", "Čeština", "Držitel tohoto certifikátu převáží osobní léky na předpis, nezbytné pro jeho zdraví a přežití. Umožněte prosím převoz uvedených léků přes hranice v souladu se zdravotní a humanitární nezbytností."),
    ("de", "Deutsch", "Der Inhaber dieses Zertifikats führt persönliche verschreibungspflichtige Medikamente mit sich, die für seine Gesundheit und sein Überleben notwendig sind. Bitte gestatten Sie den Grenztransport der aufgeführten Medikamente gemäß medizinischer und humanitärer Notwendigkeit."),
    ("fr", "Français", "Le titulaire de ce certificat transporte des médicaments personnels sur ordonnance nécessaires à sa santé et à sa survie. Veuillez autoriser le transport transfrontalier des médicaments listés conformément à la nécessité médicale et humanitaire."),
    ("es", "Español", "El titular de este certificado transporta medicamentos personales recetados, necesarios para su salud y supervivencia. Por favor, permita el transporte transfronterizo de los medicamentos indicados conforme a la necesidad médica y humanitaria."),
    ("it", "Italiano", "Il titolare di questo certificato trasporta farmaci personali su prescrizione, necessari per la sua salute e sopravvivenza. Si prega di consentire il trasporto transfrontaliero dei farmaci elencati in conformità alla necessità medica e umanitaria."),
    ("pl", "Polski", "Posiadacz tego certyfikatu przewozi osobiste leki na receptę, niezbędne dla jego zdrowia i przetrwania. Prosimy o umożliwienie przewozu wymienionych leków przez granice zgodnie z koniecznością medyczną i humanitarną."),
    ("hu", "Magyar", "E tanúsítvány birtokosa személyes, vényköteles gyógyszereket szállít, amelyek egészségéhez és túléléséhez szükségesek. Kérjük, engedélyezze a felsorolt gyógyszerek határon átnyúló szállítását az orvosi és humanitárius szükségességnek megfelelően."),
    ("uk", "Українська", "Власник цього сертифіката перевозить особисті рецептурні ліки, необхідні для його здоров'я та виживання. Будь ласка, дозвольте перевезення зазначених ліків через кордон відповідно до медичної та гуманітарної необхідності."),
    ("ru", "Русский", "Владелец этого сертификата перевозит личные рецептурные лекарства, необходимые для его здоровья и выживания. Пожалуйста, разрешите провоз указанных лекарств через границу в соответствии с медицинской и гуманитарной необходимостью."),
    ("pt", "Português", "O titular deste certificado transporta medicamentos pessoais sujeitos a receita médica, necessários para a sua saúde e sobrevivência. Por favor, permita o transporte transfronteiriço dos medicamentos listados em conformidade com a necessidade médica e humanitária."),
    ("nl", "Nederlands", "De houder van dit certificaat vervoert persoonlijke receptgeneesmiddelen die noodzakelijk zijn voor zijn gezondheid en overleving. Sta het grensoverschrijdend vervoer van de vermelde medicatie toe in overeenstemming met medische en humanitaire noodzaak."),
    ("ro", "Română", "Titularul acestui certificat transportă medicamente personale eliberate pe bază de rețetă, necesare pentru sănătatea și supraviețuirea sa. Vă rugăm să permiteți transportul transfrontalier al medicamentelor enumerate în conformitate cu necesitatea medicală și umanitară."),
]

async def _border_payload(user: dict) -> dict:
    prof = await db.emergency_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    items = await db.cabinet.find({"user_id": user["user_id"], "prescription": True}, {"_id": 0}).to_list(100)
    if not items:
        items = await db.cabinet.find({"user_id": user["user_id"], "category": "medication"}, {"_id": 0}).to_list(100)
    meds = [{"name": i.get("name"), "quantity": i.get("quantity"), "unit": i.get("unit"), "prescription": bool(i.get("prescription"))} for i in items]
    issued = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    core = {
        "did": user["did"],
        "holder": prof.get("full_name") or user.get("name") or "",
        "blood_type": prof.get("blood_type") or "",
        "allergies": prof.get("allergies") or "",
        "conditions": prof.get("conditions") or "",
        "medications_free_text": prof.get("medications") or "",
        "medications": meds,
        "issued_at": issued,
    }
    signature = hashlib.sha256((user["did"] + json.dumps(core, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()
    core["did_signature"] = signature
    core["languages"] = [{"code": c, "name": n} for c, n, _ in BORDER_LANGS]
    return core

@api.get("/border/certificate")
async def border_certificate(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await _border_payload(user)

@api.get("/border/certificate.pdf")
async def border_certificate_pdf(token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    data = await _border_payload(user)
    med_lines = "\n".join([f"  • {m['name']} — {m['quantity']} {m['unit']}" + ("  [Rx]" if m["prescription"] else "") for m in data["medications"]]) or "  —"
    body = (
        f"Holder / Držiteľ: {data['holder']}\n"
        f"DID (Decentralized ID): {data['did']}\n"
        f"Blood type / Krvná skupina: {data['blood_type'] or '—'}\n"
        f"Allergies / Alergie: {data['allergies'] or '—'}\n"
        f"Conditions / Diagnózy: {data['conditions'] or '—'}\n"
        f"Issued / Vydané: {data['issued_at']}\n\n"
        f"MEDICATION LIST / ZOZNAM LIEKOV:\n{med_lines}\n"
        + (f"\nOther medication / Ďalšie lieky: {data['medications_free_text']}\n" if data["medications_free_text"] else "")
        + "\n" + "=" * 60 + "\n\n"
        + "\n\n".join([f"[{name} · {code.upper()}]\n{text}" for code, name, text in BORDER_LANGS])
    )
    footer = f"DID SIGNATURE (SHA-256): {data['did_signature']}\n" + _pdf_footer()
    pdf = await run_in_threadpool(_make_pdf, "INTERNATIONAL MEDICATION CERTIFICATE\nMEDZINÁRODNÝ CERTIFIKÁT O LIEKOCH", body, footer)
    return _pdf_response(pdf, "guardian_border_certificate.pdf")



# --------- MENTAL FORTRESS (Crisis Audio Guide — SK/CS/EN/DE) ---------
def _content_lang(language: str) -> str:
    lk = (language or "sk").lower()[:2]
    return lk if lk in ("sk", "cs", "en", "de") else "en"

@api.get("/mental/techniques")
async def mental_techniques(language: str = "sk", authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    lk = _content_lang(language)
    step_word = STEP_WORD[lk]
    techniques = []
    for t in MENTAL_TECHNIQUES[lk]:
        tts = f"{t['title']}. " + " ".join([f"{step_word} {i+1}: {s}" for i, s in enumerate(t["steps"])])
        techniques.append({**t, "tts_text": tts})
    return {"language": lk, "techniques": techniques, "disclaimer": MENTAL_DISCLAIMERS[lk]}

# --------- PHYSIO-AI GLOBAL ENCYCLOPEDIA (Founder content — SK/CS/EN/DE) ---------
# Premium educational video demonstrations (Mixkit free license, direct MP4 · HD + SD for adaptive start)
PHYSIO_VIDEOS = {
    "knee": ("https://assets.mixkit.co/videos/36710/36710-720.mp4", "https://assets.mixkit.co/videos/36710/36710-360.mp4"),
    "cervical": ("https://assets.mixkit.co/videos/49539/49539-720.mp4", "https://assets.mixkit.co/videos/49539/49539-360.mp4"),
    "panic-acupressure": ("https://assets.mixkit.co/videos/47583/47583-720.mp4", "https://assets.mixkit.co/videos/47583/47583-360.mp4"),
    "spine": ("https://assets.mixkit.co/videos/13041/13041-720.mp4", "https://assets.mixkit.co/videos/13041/13041-360.mp4"),
    "shoulders": ("https://assets.mixkit.co/videos/13039/13039-720.mp4", "https://assets.mixkit.co/videos/13039/13039-360.mp4"),
    "wrists": ("https://assets.mixkit.co/videos/52168/52168-720.mp4", "https://assets.mixkit.co/videos/52168/52168-360.mp4"),
    "lymph": ("https://assets.mixkit.co/videos/13062/13062-720.mp4", "https://assets.mixkit.co/videos/13062/13062-360.mp4"),
}
# Cervical Spine Relief — video-native guide (per-language)
CERVICAL_GUIDE = {
    "sk": {"id": "cervical", "category": "body", "icon": "body-outline", "title": "Krčná chrbtica — úľava (Cervical Relief)",
           "subtitle": "Video-návod · 5 minút · stuhnutý krk a hlava",
           "steps": ["Sadnite si vzpriamene, ramená stiahnite dole od uší.", "Pomaly ukloňte hlavu k pravému ramenu, 20 sekúnd — potom k ľavému.", "Bradu jemne zasuňte dozadu (double chin), podržte 5 sekúnd — 8 opakovaní.", "Prstami masírujte svaly pozdĺž krku od vlasov k ramenám, 60 sekúnd každá strana.", "Zakončite pomalými polkruhmi hlavy (nie plný kruh) — 5 opakovaní.", "Ostrá bolesť vystreľujúca do ruky = stop a konzultácia s lekárom."]},
    "cs": {"id": "cervical", "category": "body", "icon": "body-outline", "title": "Krční páteř — úleva (Cervical Relief)",
           "subtitle": "Video-návod · 5 minut · ztuhlý krk a hlava",
           "steps": ["Seďte vzpřímeně, ramena stáhněte dolů od uší.", "Pomalu ukloňte hlavu k pravému rameni, 20 sekund — pak k levému.", "Bradu jemně zasuňte dozadu (double chin), držte 5 sekund — 8 opakování.", "Prsty masírujte svaly podél krku od vlasů k ramenům, 60 sekund každá strana.", "Zakončete pomalými půlkruhy hlavy (ne plný kruh) — 5 opakování.", "Ostrá bolest vystřelující do ruky = stop a konzultace s lékařem."]},
    "en": {"id": "cervical", "category": "body", "icon": "body-outline", "title": "Cervical Spine Relief",
           "subtitle": "Video guide · 5 minutes · stiff neck & head",
           "steps": ["Sit tall, pull shoulders down away from the ears.", "Slowly tilt your head to the right shoulder for 20 seconds — then left.", "Gently tuck the chin back (double chin), hold 5 seconds — 8 reps.", "Massage the muscles along the neck from hairline to shoulders, 60 seconds each side.", "Finish with slow half-circles of the head (never a full circle) — 5 reps.", "Sharp pain radiating into the arm = stop and consult a doctor."]},
    "de": {"id": "cervical", "category": "body", "icon": "body-outline", "title": "Halswirbelsäule — Entlastung",
           "subtitle": "Video-Anleitung · 5 Minuten · steifer Nacken",
           "steps": ["Aufrecht sitzen, Schultern von den Ohren wegziehen.", "Kopf langsam zur rechten Schulter neigen, 20 Sekunden — dann links.", "Kinn sanft zurückziehen (Doppelkinn), 5 Sekunden halten — 8 Wiederholungen.", "Muskeln entlang des Nackens vom Haaransatz zu den Schultern massieren, 60 Sekunden pro Seite.", "Mit langsamen Halbkreisen des Kopfes abschließen (nie Vollkreis) — 5 Wiederholungen.", "Stechender Schmerz in den Arm = Stopp und Arztkonsultation."]},
}

def _attach_video(g: dict) -> dict:
    vid = PHYSIO_VIDEOS.get(g["id"])
    if vid:
        g["video_url"], g["video_url_sd"] = vid
        g["video_note"] = "Video: Mixkit free license · demo clip"
    return g

@api.get("/physio/guides")
async def physio_guides(language: str = "sk", authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    from content_physio import PHYSIO_EXTRA, PHYSIO_CATEGORY, CATEGORY_LABELS
    lk = _content_lang(language)
    step_word = STEP_WORD[lk]
    guides = []
    for g in PHYSIO_GUIDES[lk]:
        tts = f"{g['title']}. " + " ".join([f"{step_word} {i+1}: {s}" for i, s in enumerate(g["steps"])])
        guides.append(_attach_video({**g, "category": PHYSIO_CATEGORY.get(g["id"], "body"), "tts_text": tts}))
    cg = CERVICAL_GUIDE.get(lk, CERVICAL_GUIDE["en"])
    tts = f"{cg['title']}. " + " ".join([f"{step_word} {i+1}: {s}" for i, s in enumerate(cg["steps"])])
    guides.append(_attach_video({**cg, "tts_text": tts}))
    for g in PHYSIO_EXTRA[lk]:
        tts = f"{g['title']}. " + " ".join([f"{step_word} {i+1}: {s}" for i, s in enumerate(g["steps"])])
        guides.append(_attach_video({**g, "tts_text": tts}))
    return {"language": lk, "guides": guides, "category_labels": CATEGORY_LABELS[lk],
            "disclaimer": MENTAL_DISCLAIMERS[lk]}

# --------- HEALTH DROP (Referral Bridge — zero-knowledge provider-to-vault upload) ---------
# Encryption happens IN THE PROVIDER'S BROWSER (tweetnacl box with the patient's public key).
# The server only ever stores ciphertext — true zero-knowledge ingestion.

REFERRAL_HINTS = ("ortop", "kardio", "neuro", "chirurg", "onko", "reuma", "urolog", "gastro",
                  "vypis", "výmenný", "vymenny", "referral", "žiadanka", "ziadanka", "odporúčanie", "odporucanie")

def _guess_specialty(title: str) -> str:
    t = (title or "").lower()
    for kw, name in (("ortop", "Orthopedics"), ("kardio", "Cardiology"), ("neuro", "Neurology"),
                     ("chirurg", "Surgery"), ("onko", "Oncology"), ("reuma", "Rheumatology"),
                     ("urolog", "Urology"), ("gastro", "Gastroenterology")):
        if kw in t:
            return name
    return ""

@api.get("/health-drop/me")
async def health_drop_me(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    drop_id = user.get("drop_id")
    if not drop_id:
        drop_id = uuid.uuid4().hex[:16]
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"drop_id": drop_id}})
    return {"drop_id": drop_id, "public_key": user.get("drop_public_key"), "did": user["did"]}

class DropPubkeyIn(BaseModel):
    public_key: str  # base64 (32-byte X25519)

@api.put("/health-drop/pubkey")
async def health_drop_pubkey(body: DropPubkeyIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if len(body.public_key) < 40 or len(body.public_key) > 60:
        raise HTTPException(400, "Invalid public key")
    drop_id = user.get("drop_id") or uuid.uuid4().hex[:16]
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"drop_public_key": body.public_key, "drop_id": drop_id}})
    return {"drop_id": drop_id, "public_key": body.public_key}

@api.get("/health-drop/{drop_id}/info")
async def health_drop_info(drop_id: str):
    """PUBLIC — provider portal bootstrap. Returns only first name + public key."""
    user = await db.users.find_one({"drop_id": drop_id}, {"_id": 0})
    if not user:
        raise HTTPException(404, "Drop link not found")
    first = (user.get("name") or "").split(" ")[0]
    return {"patient_hint": first, "has_key": bool(user.get("drop_public_key")), "public_key": user.get("drop_public_key")}

@api.post("/health-drop/{drop_id}/upload")
async def health_drop_upload(
    drop_id: str,
    file: UploadFile = File(...),
    eph_pub: str = Form(...),
    nonce: str = Form(...),
    guardian_id: str = Form(...),
    sender_name: str = Form(""),
    doc_title: str = Form(""),
    orig_type: str = Form("application/pdf"),
):
    """PUBLIC — accepts ONLY ciphertext (encrypted in the provider's browser)."""
    user = await db.users.find_one({"drop_id": drop_id}, {"_id": 0})
    if not user:
        raise HTTPException(404, "Drop link not found")
    if not user.get("drop_public_key"):
        raise HTTPException(409, "Patient has not generated encryption keys yet")
    gid = guardian_id.strip().lower()
    did = user["did"].lower()
    if gid != did and gid != did[-6:]:
        raise HTTPException(403, "Guardian-ID does not match this Drop link")
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(400, "Empty file")
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 15MB)")
    drop_doc_id = uuid.uuid4().hex
    path = f"{APP_NAME}/drops/{user['user_id']}/{drop_doc_id}.bin"
    try:
        await run_in_threadpool(put_object_sync, path, data, "application/octet-stream")
    except Exception as e:
        logger.error(f"drop upload failed: {e}")
        raise HTTPException(502, "Storage upload failed")
    title_l = (doc_title or "").lower()
    is_referral = any(k in title_l for k in REFERRAL_HINTS)
    rec = {
        "drop_doc_id": drop_doc_id, "user_id": user["user_id"],
        "sender_name": sender_name.strip()[:80] or "Lekár",
        "doc_title": doc_title.strip()[:120] or "Lekársky dokument",
        "orig_type": orig_type[:60], "size": len(data),
        "eph_pub": eph_pub[:60], "nonce": nonce[:40],
        "storage_path": path, "is_referral": is_referral,
        "specialty_guess": _guess_specialty(doc_title),
        "autobooked": False,
        "created_at": datetime.now(timezone.utc),
    }
    await db.health_drops.insert_one(rec.copy())
    try:
        await send_push(recipients=[user["user_id"]],
                        data={"title": "📄 NOVÝ LEKÁRSKY DOKUMENT", "message": f"Prijatý dokument od: {rec['sender_name']}.", "action_url": "/health-drop"})
    except Exception as e:
        logger.warning(f"drop push failed: {e}")
    return {"ok": True, "drop_doc_id": drop_doc_id}

@api.get("/health-drop/inbox")
async def health_drop_inbox(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.health_drops.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)

@api.get("/health-drop/items/{drop_doc_id}/file")
async def health_drop_file(drop_doc_id: str, token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    rec = await db.health_drops.find_one({"drop_doc_id": drop_doc_id, "user_id": user["user_id"]}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "Not found")
    content, _ = await run_in_threadpool(get_object_sync, rec["storage_path"])
    return Response(content=content, media_type="application/octet-stream")

@api.delete("/health-drop/items/{drop_doc_id}")
async def health_drop_delete(drop_doc_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.health_drops.delete_one({"drop_doc_id": drop_doc_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}

# --------- KARTA ŽIVOTA (Life Card) — health axis from birth ---------
# Categories: vaccine=Očkovania · disease=Choroby · surgery=Operácie ·
# injury=Úrazy · exam=Prehliadky · dental=Zubár. Legacy 'history' remains for
# system rows (vault/billing) shown as documents; old MANUAL 'history' rows
# are lazily migrated to 'disease'.
LIFECARD_CATS = ("vaccine", "disease", "surgery", "injury", "exam", "dental")
BLOOD_TYPES = ("A+", "A-", "B+", "B-", "AB+", "AB-", "0+", "0-")

class CalendarEventIn(BaseModel):
    category: str  # vaccine | disease | surgery | injury | exam | dental
    title: str
    date: str      # YYYY-MM-DD
    notes: Optional[str] = ""
    booster_due: Optional[str] = None  # YYYY-MM-DD (vaccines)
    child_id: Optional[str] = None     # record on a child's Life Card
    tooth: Optional[str] = None        # FDI tooth number (dental — karta zubára)

@api.post("/calendar/events")
async def calendar_add(body: CalendarEventIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    cat = "disease" if body.category == "history" else body.category  # legacy alias
    if cat not in LIFECARD_CATS:
        raise HTTPException(400, "category must be vaccine|disease|surgery|injury|exam|dental")
    try:
        datetime.strptime(body.date, "%Y-%m-%d")
        if body.booster_due:
            datetime.strptime(body.booster_due, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "date must be YYYY-MM-DD")
    child_id = None
    if body.child_id:
        await _get_child(user["user_id"], body.child_id)
        child_id = body.child_id
    doc = {
        "event_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "category": cat, "title": body.title.strip()[:140],
        "date": body.date, "notes": (body.notes or "")[:500],
        "booster_due": body.booster_due, "source": "manual",
        "child_id": child_id,
        "tooth": (body.tooth or "").strip()[:4] or None,
        "created_at": datetime.now(timezone.utc),
    }
    await db.calendar_events.insert_one(doc.copy())
    return clean(doc)

async def _lifecard_counts(uid: str, child_id: Optional[str] = None) -> dict:
    counts = {c: 0 for c in LIFECARD_CATS}
    # child_id=None matches both missing and null → adult card excludes child records
    rows = await db.calendar_events.find({"user_id": uid, "child_id": child_id},
                                         {"_id": 0, "category": 1}).to_list(2000)
    for r in rows:
        c = r.get("category")
        if c in counts:
            counts[c] += 1
    return counts

@api.get("/calendar/timeline")
async def calendar_timeline(category: Optional[str] = None, child_id: Optional[str] = None,
                            authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    if child_id:
        await _get_child(uid, child_id)
    else:
        # Lazy migration: old manual 'history' rows ("Choroba / úraz") → disease
        await db.calendar_events.update_many(
            {"user_id": uid, "category": "history", "source": "manual"},
            {"$set": {"category": "disease"}})
    q: dict = {"user_id": uid, "child_id": child_id}
    if category in LIFECARD_CATS + ("history",):
        q["category"] = category
    events = await db.calendar_events.find(q, {"_id": 0}).sort("date", -1).to_list(500)
    today = datetime.now(timezone.utc).date().isoformat()
    horizon = (datetime.now(timezone.utc) + timedelta(days=90)).date().isoformat()
    upcoming = [e for e in events if e["category"] == "exam" and e["date"] >= today]
    booster_alerts = [e for e in events if e["category"] == "vaccine" and e.get("booster_due") and e["booster_due"] <= horizon]
    return {"events": events, "upcoming_exams": sorted(upcoming, key=lambda e: e["date"]),
            "booster_alerts": sorted(booster_alerts, key=lambda e: e["booster_due"]),
            "counts": await _lifecard_counts(uid, child_id), "today": today}

@api.delete("/calendar/events/{event_id}")
async def calendar_delete(event_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.calendar_events.delete_one({"event_id": event_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}

# --- Life Card identity (meno · dátum narodenia · krvná skupina — zdroj: rodný list) ---
def _age_from(birth_date: Optional[str]) -> Optional[int]:
    if not birth_date:
        return None
    try:
        bd = datetime.strptime(birth_date, "%Y-%m-%d").date()
    except ValueError:
        return None
    t = datetime.now(timezone.utc).date()
    return t.year - bd.year - ((t.month, t.day) < (bd.month, bd.day))

async def _lifecard_payload(user: dict) -> dict:
    uid = user["user_id"]
    prof = await db.emergency_profiles.find_one({"user_id": uid}, {"_id": 0}) or {}
    birth_date = user.get("birth_date")
    age = _age_from(birth_date)
    if age is None:
        birth_date = None
        if user.get("birth_year"):
            age = datetime.now(timezone.utc).year - int(user["birth_year"])
    pred = await db.lifecard_predictions.find_one({"user_id": uid, "child_id": None}, {"_id": 0}) or {}
    return {
        "full_name": prof.get("full_name") or user.get("name") or "",
        "birth_date": birth_date, "birth_year": user.get("birth_year"),
        "blood_type": prof.get("blood_type") or "", "age": age,
        "counts": await _lifecard_counts(uid),
        "predictions": pred.get("predictions", []),
        "predictions_at": pred.get("generated_at"),
        "today": datetime.now(timezone.utc).date().isoformat(),
    }

@api.get("/lifecard")
async def lifecard_get(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return clean(await _lifecard_payload(user))

class LifeCardIn(BaseModel):
    full_name: Optional[str] = None
    birth_date: Optional[str] = None  # YYYY-MM-DD — zdroj: rodný list
    blood_type: Optional[str] = None

@api.put("/lifecard")
async def lifecard_update(body: LifeCardIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    user_upd, prof_upd = {}, {}
    if body.birth_date is not None and body.birth_date != "":
        try:
            bd = datetime.strptime(body.birth_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(400, "birth_date must be YYYY-MM-DD")
        if bd.year < 1900 or bd > datetime.now(timezone.utc).date():
            raise HTTPException(400, "birth_date out of range")
        user_upd["birth_date"] = body.birth_date
        user_upd["birth_year"] = bd.year  # keep Bio-Timeline in sync
    if body.blood_type is not None:
        if body.blood_type not in BLOOD_TYPES + ("",):
            raise HTTPException(400, f"blood_type must be one of {'|'.join(BLOOD_TYPES)}")
        prof_upd["blood_type"] = body.blood_type
    if body.full_name is not None and body.full_name.strip():
        prof_upd["full_name"] = body.full_name.strip()[:120]
    if user_upd:
        await db.users.update_one({"user_id": uid}, {"$set": user_upd})
        user = await db.users.find_one({"user_id": uid}, {"_id": 0})
    if prof_upd:
        await db.emergency_profiles.update_one(
            {"user_id": uid}, {"$set": {**prof_upd, "user_id": uid}}, upsert=True)
    return clean(await _lifecard_payload(user))

# --- KARTA PRE DIEŤA — parent keeps separate children's Life Cards from birth ---
async def _get_child(uid: str, child_id: str) -> dict:
    ch = await db.lifecard_children.find_one({"child_id": child_id, "user_id": uid}, {"_id": 0})
    if not ch:
        raise HTTPException(404, "Child not found")
    return ch

async def _child_view(uid: str, ch: dict) -> dict:
    pred = await db.lifecard_predictions.find_one(
        {"user_id": uid, "child_id": ch["child_id"]}, {"_id": 0}) or {}
    return {
        "child_id": ch["child_id"], "name": ch["name"],
        "birth_date": ch.get("birth_date"), "blood_type": ch.get("blood_type") or "",
        "sex": ch.get("sex") or "",
        "age": _age_from(ch.get("birth_date")),
        "counts": await _lifecard_counts(uid, ch["child_id"]),
        "predictions": pred.get("predictions", []),
    }

class ChildIn(BaseModel):
    name: str
    birth_date: str  # YYYY-MM-DD — zdroj: rodný list
    blood_type: Optional[str] = ""
    sex: Optional[str] = ""  # m | f (pre WHO rastové percentily)

class ChildUpdateIn(BaseModel):
    name: Optional[str] = None
    birth_date: Optional[str] = None
    blood_type: Optional[str] = None
    sex: Optional[str] = None

def _validate_birth(birth_date: str):
    try:
        bd = datetime.strptime(birth_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "birth_date must be YYYY-MM-DD")
    if bd.year < 1900 or bd > datetime.now(timezone.utc).date():
        raise HTTPException(400, "birth_date out of range")

@api.get("/lifecard/children")
async def children_list(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.lifecard_children.find(
        {"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", 1).to_list(20)
    return {"children": [clean(await _child_view(user["user_id"], ch)) for ch in rows]}

@api.post("/lifecard/children")
async def child_add(body: ChildIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    if not body.name.strip():
        raise HTTPException(400, "name required")
    _validate_birth(body.birth_date)
    if body.blood_type not in BLOOD_TYPES + ("", None):
        raise HTTPException(400, f"blood_type must be one of {'|'.join(BLOOD_TYPES)}")
    if body.sex not in ("m", "f", "", None):
        raise HTTPException(400, "sex must be m|f")
    if await db.lifecard_children.count_documents({"user_id": uid}) >= 10:
        raise HTTPException(400, "Maximum 10 children")
    ch = {
        "child_id": uuid.uuid4().hex, "user_id": uid,
        "name": body.name.strip()[:80], "birth_date": body.birth_date,
        "blood_type": body.blood_type or "",
        "sex": body.sex or "",
        "created_at": datetime.now(timezone.utc),
    }
    await db.lifecard_children.insert_one(ch.copy())
    return clean(await _child_view(uid, ch))

@api.put("/lifecard/children/{child_id}")
async def child_update(child_id: str, body: ChildUpdateIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    await _get_child(uid, child_id)
    upd = {}
    if body.name is not None and body.name.strip():
        upd["name"] = body.name.strip()[:80]
    if body.birth_date is not None and body.birth_date != "":
        _validate_birth(body.birth_date)
        upd["birth_date"] = body.birth_date
    if body.blood_type is not None:
        if body.blood_type not in BLOOD_TYPES + ("",):
            raise HTTPException(400, f"blood_type must be one of {'|'.join(BLOOD_TYPES)}")
        upd["blood_type"] = body.blood_type
    if body.sex is not None:
        if body.sex not in ("m", "f", ""):
            raise HTTPException(400, "sex must be m|f")
        upd["sex"] = body.sex
    if upd:
        await db.lifecard_children.update_one({"child_id": child_id, "user_id": uid}, {"$set": upd})
    return clean(await _child_view(uid, await _get_child(uid, child_id)))

@api.delete("/lifecard/children/{child_id}")
async def child_delete(child_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    await _get_child(uid, child_id)
    await db.calendar_events.delete_many({"user_id": uid, "child_id": child_id})
    await db.lifecard_predictions.delete_many({"user_id": uid, "child_id": child_id})
    await db.growth_logs.delete_many({"user_id": uid, "child_id": child_id})
    await db.lifecard_children.delete_one({"child_id": child_id, "user_id": uid})
    return {"ok": True}

# --- RASTOVÁ KRIVKA — WHO growth percentiles (height-for-age 0-18y,
# --- weight-for-age 0-10y). Approximate WHO medians+SD, linear interpolation.
# --- Height-for-age is normal (WHO L=1): z=(v-M)/SD. Weight ~lognormal: z=ln(v/M)/S.
WHO_HEIGHT = {  # (months, median_cm, sd_cm)
    "m": [(0, 49.9, 1.9), (6, 67.6, 2.3), (12, 75.7, 2.7), (18, 82.3, 3.0), (24, 87.1, 3.3),
          (36, 96.1, 3.7), (48, 103.3, 4.1), (60, 110.0, 4.5), (72, 116.0, 4.9), (84, 121.7, 5.3),
          (96, 127.3, 5.7), (108, 132.6, 6.0), (120, 137.8, 6.4), (132, 143.1, 6.8), (144, 149.1, 7.3),
          (156, 156.0, 7.9), (168, 163.2, 8.0), (180, 169.0, 7.6), (192, 172.9, 7.1), (204, 175.2, 6.8), (216, 176.1, 6.7)],
    "f": [(0, 49.1, 1.9), (6, 65.7, 2.3), (12, 74.0, 2.6), (18, 80.7, 2.9), (24, 85.7, 3.2),
          (36, 95.1, 3.6), (48, 102.7, 4.0), (60, 109.4, 4.3), (72, 115.1, 4.7), (84, 120.8, 5.1),
          (96, 126.6, 5.5), (108, 132.5, 5.9), (120, 138.6, 6.3), (132, 145.0, 6.7), (144, 151.2, 6.9),
          (156, 156.4, 6.8), (168, 159.8, 6.6), (180, 161.7, 6.4), (192, 162.5, 6.3), (204, 163.0, 6.3), (216, 163.2, 6.3)],
}
WHO_WEIGHT = {  # (months, median_kg, s_lognormal)
    "m": [(0, 3.3, 0.13), (6, 7.9, 0.11), (12, 9.6, 0.11), (18, 10.9, 0.11), (24, 12.2, 0.11),
          (36, 14.3, 0.12), (48, 16.3, 0.13), (60, 18.3, 0.14), (72, 20.5, 0.15), (84, 22.9, 0.16),
          (96, 25.4, 0.17), (108, 28.1, 0.18), (120, 31.2, 0.19)],
    "f": [(0, 3.2, 0.14), (6, 7.3, 0.12), (12, 8.9, 0.12), (18, 10.2, 0.12), (24, 11.5, 0.12),
          (36, 13.9, 0.13), (48, 16.1, 0.14), (60, 18.2, 0.15), (72, 20.2, 0.16), (84, 22.4, 0.17),
          (96, 25.0, 0.18), (108, 28.2, 0.19), (120, 31.9, 0.20)],
}
Z_P3, Z_P97 = -1.8808, 1.8808

def _who_interp(table: list, months: float):
    if months <= table[0][0]:
        return table[0][1], table[0][2]
    if months >= table[-1][0]:
        return None if months > table[-1][0] + 12 else (table[-1][1], table[-1][2])
    for i in range(len(table) - 1):
        m0, v0, s0 = table[i]
        m1, v1, s1 = table[i + 1]
        if m0 <= months <= m1:
            t = (months - m0) / (m1 - m0)
            return v0 + t * (v1 - v0), s0 + t * (s1 - s0)
    return None

def _pct_from_z(z: float) -> float:
    return round(50.0 * (1.0 + math.erf(z / math.sqrt(2))), 1)

def _height_percentile(sex: str, months: float, cm: float) -> Optional[float]:
    r = _who_interp(WHO_HEIGHT.get(sex, []), months) if sex in ("m", "f") else None
    if not r:
        return None
    m, sd = r
    return _pct_from_z((cm - m) / sd)

def _weight_percentile(sex: str, months: float, kg: float) -> Optional[float]:
    if months > 121 or sex not in ("m", "f"):
        return None  # WHO weight-for-age ends at 10 y — ďalej sa sleduje BMI
    r = _who_interp(WHO_WEIGHT[sex], months)
    if not r:
        return None
    m, s = r
    return _pct_from_z(math.log(kg / m) / s)

def _growth_curves(sex: str, max_months: float) -> dict:
    out = {"height": [], "weight": []}
    if sex not in ("m", "f"):
        return out
    for table, key in ((WHO_HEIGHT[sex], "height"), (WHO_WEIGHT[sex], "weight")):
        for m, med, s in table:
            if m > max_months:
                break
            if key == "height":
                lo, hi = med + Z_P3 * s, med + Z_P97 * s
            else:
                lo, hi = med * math.exp(Z_P3 * s), med * math.exp(Z_P97 * s)
            out[key].append({"m": m, "p3": round(lo, 1), "p50": round(med, 1), "p97": round(hi, 1)})
    return out

class GrowthIn(BaseModel):
    date: str  # YYYY-MM-DD
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None

def _growth_months(birth_date: Optional[str], date: str) -> Optional[float]:
    if not birth_date:
        return None
    try:
        bd = datetime.strptime(birth_date, "%Y-%m-%d")
        d = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return None
    return max(0.0, (d - bd).days / 30.4375)

def _growth_view(log: dict, child: dict) -> dict:
    months = _growth_months(child.get("birth_date"), log["date"])
    sex = child.get("sex") or ""
    v = {**log, "age_months": round(months, 1) if months is not None else None,
         "height_percentile": None, "weight_percentile": None}
    if months is not None:
        if log.get("height_cm"):
            v["height_percentile"] = _height_percentile(sex, months, log["height_cm"])
        if log.get("weight_kg"):
            v["weight_percentile"] = _weight_percentile(sex, months, log["weight_kg"])
    return v

@api.post("/lifecard/children/{child_id}/growth")
async def growth_add(child_id: str, body: GrowthIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    ch = await _get_child(uid, child_id)
    try:
        datetime.strptime(body.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "date must be YYYY-MM-DD")
    if body.height_cm is None and body.weight_kg is None:
        raise HTTPException(400, "height_cm or weight_kg required")
    if body.height_cm is not None and not (30 <= body.height_cm <= 220):
        raise HTTPException(400, "height_cm out of range (30-220)")
    if body.weight_kg is not None and not (1 <= body.weight_kg <= 150):
        raise HTTPException(400, "weight_kg out of range (1-150)")
    log = {
        "log_id": uuid.uuid4().hex, "user_id": uid, "child_id": child_id,
        "date": body.date,
        "height_cm": round(body.height_cm, 1) if body.height_cm is not None else None,
        "weight_kg": round(body.weight_kg, 1) if body.weight_kg is not None else None,
        "created_at": datetime.now(timezone.utc),
    }
    await db.growth_logs.insert_one(log.copy())
    return clean(_growth_view(log, ch))

@api.get("/lifecard/children/{child_id}/growth")
async def growth_list(child_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    ch = await _get_child(uid, child_id)
    logs = await db.growth_logs.find({"user_id": uid, "child_id": child_id},
                                     {"_id": 0}).sort("date", 1).to_list(300)
    views = [_growth_view(l, ch) for l in logs]
    ages = [v["age_months"] for v in views if v["age_months"] is not None]
    max_m = max(ages + [24.0]) + 12
    sex = ch.get("sex") or ""
    return {"child": {"child_id": child_id, "name": ch["name"], "sex": sex,
                      "birth_date": ch.get("birth_date"), "age": _age_from(ch.get("birth_date"))},
            "logs": views, "curves": _growth_curves(sex, max_m),
            "sex_required": sex not in ("m", "f"),
            "note": "Indicative percentiles per WHO growth standards. Weight percentiles up to age 10 (BMI is tracked afterwards)."}

@api.delete("/lifecard/growth/{log_id}")
async def growth_delete(log_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.growth_logs.delete_one({"log_id": log_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}

# --- TRENDY ZDRAVIA — yearly counts per category + Jarvis summary ---
@api.get("/lifecard/trends")
async def lifecard_trends(child_id: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    if child_id:
        await _get_child(uid, child_id)
    events = await db.calendar_events.find(
        {"user_id": uid, "child_id": child_id, "category": {"$in": list(LIFECARD_CATS)}},
        {"_id": 0, "category": 1, "date": 1}).to_list(2000)
    by_year: dict = {}
    for e in events:
        y = str(e.get("date") or "")[:4]
        if not y.isdigit():
            continue
        row = by_year.setdefault(y, {c: 0 for c in LIFECARD_CATS})
        row[e["category"]] += 1
    years = [{"year": y, "counts": c, "total": sum(c.values())}
             for y, c in sorted(by_year.items())]
    return {"years": years, "total": sum(r["total"] for r in years)}

class TrendSummaryIn(BaseModel):
    child_id: Optional[str] = None

@api.post("/lifecard/trends/summary")
async def lifecard_trends_summary(body: Optional[TrendSummaryIn] = None,
                                  authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    child_id = body.child_id if body else None
    subject = "the user"
    if child_id:
        ch = await _get_child(uid, child_id)
        subject = f"the user's child ({_age_from(ch.get('birth_date'))} y old)"
    events = await db.calendar_events.find(
        {"user_id": uid, "child_id": child_id, "category": {"$in": list(LIFECARD_CATS)}},
        {"_id": 0, "category": 1, "date": 1, "title": 1}).sort("date", -1).to_list(300)
    if not events:
        return {"summary": "No records to evaluate trends yet. Add your first records to the Life Card.", "ai": False}
    lang = (user.get("language") or "sk")[:2]
    out_lang = "Slovak" if lang in ("sk", "cs") else f"the user's app language ({lang})"
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"lifecard-trends-{uuid.uuid4().hex[:6]}",
        system_message=(
            f"You are Jarvis, a warm health companion. You get {subject}'s Life Card records "
            "(category, date, title). Write a YEARLY TREND SUMMARY: how diseases, injuries, "
            "check-ups and dental visits evolve over time, which year stood out, and ONE "
            "practical, gentle recommendation. No diagnosis, no alarmism. "
            f"Write in {out_lang}, plain text, max 5 sentences."
        ),
    ).with_model("openai", "gpt-5.4")
    try:
        resp = await chat.send_message(UserMessage(
            text=json.dumps(events[:200], ensure_ascii=False, default=str)[:6000]))
        summary = str(resp).strip()[:1200]
    except Exception as e:
        logger.error(f"trends summary error: {e}")
        raise HTTPException(502, "AI service unavailable")
    return {"summary": summary + "\n\n⎯ AI Content · Sovereign Protocol", "ai": True}

# --- PREDIKCIE — Jarvis suggests the next vaccination / preventive check-up ---
class PredictIn(BaseModel):
    child_id: Optional[str] = None

@api.post("/lifecard/predictions")
async def lifecard_predictions(body: Optional[PredictIn] = None, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    child_id = body.child_id if body else None
    if child_id:
        ch = await _get_child(uid, child_id)
        age, birth_date = _age_from(ch.get("birth_date")), ch.get("birth_date")
    else:
        card = await _lifecard_payload(user)
        age, birth_date = card["age"], card["birth_date"]
    events = await db.calendar_events.find(
        {"user_id": uid, "child_id": child_id, "category": {"$in": list(LIFECARD_CATS)}},
        {"_id": 0, "category": 1, "title": 1, "date": 1, "booster_due": 1},
    ).sort("date", -1).to_list(200)
    today = datetime.now(timezone.utc).date().isoformat()
    lang = (user.get("language") or "sk")[:2]
    reason_lang = "Slovak" if lang in ("sk", "cs") else f"the user's app language ({lang})"
    child_rule = (
        "The patient is a CHILD — use the standard EU/Slovak childhood immunization schedule "
        "(hexavalent series, MMR at 15-18 months, boosters at 5-6 and 12-13 years, etc.) and "
        "paediatric preventive check-ups (roughly yearly). "
        if (child_id and (age is None or age < 18)) else "")
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"lifecard-pred-{uuid.uuid4().hex[:6]}",
        system_message=(
            "You are a preventive-care planner for Slovakia/Czechia (EU standards). "
            "Based on the patient's LIFE CARD history you suggest WHEN the next vaccination or "
            "preventive check-up is due. " + child_rule +
            "Use standard adult schedules: tetanus booster every 15 years, "
            "flu vaccine yearly for 59+, general preventive check-up every 2 years (yearly for 60+), "
            "dental check-up yearly, and respect explicit booster_due dates in the history. "
            'Return ONLY valid JSON, no markdown: {"predictions": [{"title": "...", '
            '"category": "vaccine|exam|dental", "suggested_date": "YYYY-MM-DD", "reason": "..."}]}. '
            f"Max 4 predictions. suggested_date must be AFTER {today} and within 24 months. "
            f"'title' and 'reason' (1 short sentence) must be written in {reason_lang}. "
            "Do not repeat a prediction for something already scheduled after today in the history."
        ),
    ).with_model("openai", "gpt-5.4")
    payload = {
        "today": today, "age": age, "birth_date": birth_date,
        "is_child": bool(child_id), "history": events[:100],
    }
    try:
        resp = await chat.send_message(UserMessage(text=json.dumps(payload, ensure_ascii=False, default=str)[:6000]))
        m = re.search(r"\{.*\}", str(resp), re.S)
        data = json.loads(m.group(0)) if m else {}
    except Exception as e:
        logger.error(f"lifecard predictions error: {e}")
        raise HTTPException(502, "AI service unavailable")
    preds = []
    for p in (data.get("predictions") or [])[:4]:
        cat = p.get("category")
        date = str(p.get("suggested_date") or "")
        if cat not in LIFECARD_CATS or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) or date <= today:
            continue
        preds.append({"title": str(p.get("title") or "")[:140], "category": cat,
                      "suggested_date": date, "reason": str(p.get("reason") or "")[:300]})
    generated_at = datetime.now(timezone.utc)
    await db.lifecard_predictions.update_one(
        {"user_id": uid, "child_id": child_id},
        {"$set": {"user_id": uid, "child_id": child_id,
                  "predictions": preds, "generated_at": generated_at}},
        upsert=True)
    from routes.agent import award_xp
    await award_xp(uid, 6, "lifecard_predictions")
    return {"predictions": preds, "generated_at": generated_at, "child_id": child_id, "ai": True}

class PredictionAcceptIn(BaseModel):
    title: str
    category: str = "exam"
    date: str  # YYYY-MM-DD
    reason: Optional[str] = ""
    child_id: Optional[str] = None

@api.post("/lifecard/predictions/accept")
async def lifecard_prediction_accept(body: PredictionAcceptIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    if body.category not in LIFECARD_CATS:
        raise HTTPException(400, "category must be vaccine|disease|surgery|injury|exam")
    try:
        datetime.strptime(body.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "date must be YYYY-MM-DD")
    child_id = None
    if body.child_id:
        await _get_child(uid, body.child_id)
        child_id = body.child_id
    doc = {
        "event_id": uuid.uuid4().hex, "user_id": uid,
        "category": body.category, "title": body.title.strip()[:140],
        "date": body.date, "notes": f"Jarvis predikcia · {(body.reason or '').strip()}"[:500],
        "booster_due": None, "source": "jarvis", "child_id": child_id,
        "created_at": datetime.now(timezone.utc),
    }
    await db.calendar_events.insert_one(doc.copy())
    await db.lifecard_predictions.update_one(
        {"user_id": uid, "child_id": child_id}, {"$pull": {"predictions": {"title": body.title}}})
    return clean(doc)

# --- OČKOVACÍ PREUKAZ EÚ — multilingual vaccination certificate for EU travel ---
VAXPASS_LANGS = [
    ("en", "English", "This certificate lists the holder's vaccinations as recorded in their sovereign Guardian Life Card. Issued for travel within the EU/EEA. Authenticity is verifiable via the DID signature below."),
    ("sk", "Slovenčina", "Tento preukaz uvádza očkovania držiteľa podľa jeho suverénnej Guardian Karty života. Vydané na cesty v rámci EÚ/EHP. Pravosť overíte pomocou DID podpisu nižšie."),
    ("cs", "Čeština", "Tento průkaz uvádí očkování držitele dle jeho suverénní Guardian Karty života. Vydáno pro cesty v rámci EU/EHP. Pravost ověříte pomocí DID podpisu níže."),
    ("de", "Deutsch", "Dieser Ausweis führt die Impfungen des Inhabers gemäß seiner souveränen Guardian-Lebenskarte auf. Ausgestellt für Reisen innerhalb der EU/des EWR. Die Echtheit ist über die untenstehende DID-Signatur überprüfbar."),
    ("fr", "Français", "Ce certificat répertorie les vaccinations du titulaire telles qu'enregistrées dans sa Carte de Vie Guardian souveraine. Délivré pour les voyages au sein de l'UE/EEE. L'authenticité est vérifiable via la signature DID ci-dessous."),
    ("es", "Español", "Este certificado enumera las vacunas del titular según su Tarjeta de Vida Guardian soberana. Emitido para viajes dentro de la UE/EEE. La autenticidad es verificable mediante la firma DID a continuación."),
    ("it", "Italiano", "Questo certificato elenca le vaccinazioni del titolare come registrate nella sua Carta della Vita Guardian sovrana. Rilasciato per viaggi all'interno dell'UE/SEE. L'autenticità è verificabile tramite la firma DID sottostante."),
    ("pl", "Polski", "Niniejszy certyfikat zawiera szczepienia posiadacza zapisane w jego suwerennej Karcie Życia Guardian. Wydany na podróże w obrębie UE/EOG. Autentyczność można zweryfikować za pomocą podpisu DID poniżej."),
    ("hu", "Magyar", "Ez az igazolás a birtokos oltásait sorolja fel a szuverén Guardian Életkártyája alapján. EU/EGT-n belüli utazásra kiállítva. A hitelesség az alábbi DID-aláírással ellenőrizhető."),
    ("uk", "Українська", "Цей сертифікат містить щеплення власника, записані в його суверенній Картці життя Guardian. Виданий для подорожей у межах ЄС/ЄЕЗ. Справжність можна перевірити за DID-підписом нижче."),
    ("ru", "Русский", "Данный сертификат содержит прививки владельца, записанные в его суверенной Карте жизни Guardian. Выдан для поездок в пределах ЕС/ЕЭЗ. Подлинность проверяется по DID-подписи ниже."),
    ("pt", "Português", "Este certificado lista as vacinas do titular registadas no seu Cartão de Vida Guardian soberano. Emitido para viagens na UE/EEE. A autenticidade é verificável através da assinatura DID abaixo."),
    ("nl", "Nederlands", "Dit certificaat vermeldt de vaccinaties van de houder zoals geregistreerd in zijn soevereine Guardian Levenskaart. Afgegeven voor reizen binnen de EU/EER. De echtheid is verifieerbaar via de onderstaande DID-handtekening."),
    ("ro", "Română", "Acest certificat enumeră vaccinările titularului, înregistrate în Cardul de Viață Guardian suveran. Emis pentru călătorii în UE/SEE. Autenticitatea poate fi verificată prin semnătura DID de mai jos."),
]

async def _vaxpass_payload(user: dict, child_id: Optional[str] = None) -> dict:
    uid = user["user_id"]
    if child_id:
        ch = await _get_child(uid, child_id)
        holder, birth_date, blood = ch["name"], ch.get("birth_date"), ch.get("blood_type") or ""
    else:
        prof = await db.emergency_profiles.find_one({"user_id": uid}, {"_id": 0}) or {}
        holder = prof.get("full_name") or user.get("name") or ""
        birth_date, blood = user.get("birth_date"), prof.get("blood_type") or ""
    vaccines = await db.calendar_events.find(
        {"user_id": uid, "child_id": child_id, "category": "vaccine"},
        {"_id": 0, "title": 1, "date": 1, "booster_due": 1, "notes": 1},
    ).sort("date", -1).to_list(100)
    core = {
        "holder": holder, "birth_date": birth_date, "blood_type": blood,
        "did": user["did"], "child": bool(child_id),
        "vaccinations": vaccines,
        "issued_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    core["did_signature"] = hashlib.sha256(
        (user["did"] + json.dumps(core, sort_keys=True, ensure_ascii=False, default=str)).encode()).hexdigest()
    core["languages"] = [{"code": c, "name": n} for c, n, _ in VAXPASS_LANGS]
    return core

@api.get("/lifecard/vaccine-pass")
async def lifecard_vaccine_pass(child_id: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await _vaxpass_payload(user, child_id)

@api.get("/lifecard/vaccine-pass.pdf")
async def lifecard_vaccine_pass_pdf(child_id: Optional[str] = None, token: Optional[str] = None,
                                    authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    data = await _vaxpass_payload(user, child_id)
    vax_lines = "\n".join(
        f"  • {v['date']}   {v['title']}"
        + (f" — {v['notes']}" if v.get("notes") else "")
        + (f"   [booster due / preskočkovanie do: {v['booster_due']}]" if v.get("booster_due") else "")
        for v in data["vaccinations"]) or "  — none recorded / žiadne záznamy"
    body = (
        f"Holder / Držiteľ: {data['holder'] or '—'}"
        + ("   (child / dieťa)" if data["child"] else "") + "\n"
        f"Date of birth / Dátum narodenia: {data['birth_date'] or '—'}\n"
        f"Blood type / Krvná skupina: {data['blood_type'] or '—'}\n"
        f"Guardian DID: {data['did']}\n"
        f"Issued / Vydané: {data['issued_at']}\n\n"
        f"VACCINATIONS / OČKOVANIA ({len(data['vaccinations'])}):\n{vax_lines}\n"
        + "\n" + "=" * 60 + "\n\n"
        + "\n\n".join(f"[{name} · {code.upper()}]\n{text}" for code, name, text in VAXPASS_LANGS)
    )
    footer = f"DID SIGNATURE (SHA-256): {data['did_signature']}\n" + _pdf_footer()
    pdf = await run_in_threadpool(
        _make_pdf, "EU VACCINATION CERTIFICATE\nOČKOVACÍ PREUKAZ EÚ — Guardian Life Card", body, footer)
    return _pdf_response(pdf, "guardian_ockovaci_preukaz_eu.pdf")

# --- OCR RODNÉHO LISTU — Guardian Eye scans a birth certificate / ID and
# --- prefills the Life Card identity (user confirms before saving).
LIFECARD_OCR_SYSTEM = (
    "You extract identity data from a photo of a birth certificate (rodný list), "
    "ID card or passport (Slovak/Czech/EU). Return ONLY valid JSON, no markdown: "
    '{"found": true|false, "full_name": string|null, "birth_date": "YYYY-MM-DD"|null, '
    '"blood_type": "A+|A-|B+|B-|AB+|AB-|0+|0-"|null}. '
    "found=false when the photo is not an identity document or is unreadable. "
    "blood_type is usually NOT printed on birth certificates — return null unless explicitly visible. "
    "full_name = given name + surname of the document holder (the child on a birth certificate)."
)

@api.post("/lifecard/ocr")
async def lifecard_ocr(file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(400, "Empty file")
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 15MB)")
    b64 = base64.b64encode(data).decode()
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"lifecard-ocr-{uuid.uuid4().hex[:6]}",
        system_message=LIFECARD_OCR_SYSTEM,
    ).with_model("openai", "gpt-5.4")
    try:
        resp = await chat.send_message(UserMessage(
            text="Extract the identity fields from this document photo. JSON only.",
            file_contents=[ImageContent(image_base64=b64)]))
        m = re.search(r"\{.*\}", str(resp), re.S)
        d = json.loads(m.group(0)) if m else {}
    except Exception as e:
        logger.error(f"lifecard ocr error: {e}")
        raise HTTPException(502, "AI service unavailable")
    birth = d.get("birth_date")
    if birth:
        try:
            bd = datetime.strptime(str(birth), "%Y-%m-%d").date()
            if bd.year < 1900 or bd > datetime.now(timezone.utc).date():
                birth = None
        except ValueError:
            birth = None
    blood = d.get("blood_type") if d.get("blood_type") in BLOOD_TYPES else None
    name = str(d.get("full_name") or "").strip()[:120] or None
    found = bool(d.get("found")) and bool(name or birth)
    return {"found": found, "full_name": name, "birth_date": birth, "blood_type": blood, "ai": True}

# --- PDF KARTY ŽIVOTA — printable health axis for the doctor / family ---
LIFECARD_LABELS = {"vaccine": "VACCINATIONS", "disease": "DISEASES", "surgery": "SURGERIES",
                   "injury": "INJURIES", "exam": "CHECK-UPS", "dental": "DENTAL"}

@api.get("/lifecard/report.pdf")
async def lifecard_report_pdf(child_id: Optional[str] = None, token: Optional[str] = None,
                              authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    if child_id:
        ch = await _get_child(user["user_id"], child_id)
        ident = {"full_name": ch["name"], "birth_date": ch.get("birth_date"),
                 "birth_year": None, "blood_type": ch.get("blood_type") or "",
                 "age": _age_from(ch.get("birth_date"))}
    else:
        ident = await _lifecard_payload(user)
    events = await db.calendar_events.find(
        {"user_id": user["user_id"], "child_id": child_id, "category": {"$in": list(LIFECARD_CATS)}},
        {"_id": 0}).sort("date", -1).to_list(500)
    age = f" (age {ident['age']})" if ident.get("age") is not None else ""
    lines = [
        f"Name: {ident['full_name'] or '—'}" + ("   (child card)" if child_id else ""),
        f"Date of birth: {ident['birth_date'] or ident.get('birth_year') or '—'}{age}",
        f"Blood type: {ident['blood_type'] or '—'}",
        f"DID (Guardian ID): {user['did']}",
        "",
    ]
    for cat in LIFECARD_CATS:
        lines.append(f"{LIFECARD_LABELS[cat]}:")
        rows = [e for e in events if e["category"] == cat]
        if not rows:
            lines.append("   — no records")
        for e in rows:
            note = f" — {e['notes']}" if e.get("notes") else ""
            extra = f" · booster due {e['booster_due']}" if e.get("booster_due") else ""
            tooth = f" · zub {e['tooth']}" if e.get("tooth") else ""
            lines.append(f"   • {e['date']}   {e['title']}{tooth}{note}{extra}")
        lines.append("")
    pdf = await run_in_threadpool(
        _make_pdf,
        "KARTA ŽIVOTA — ZDRAVOTNÁ OS OD NARODENIA\nLIFE CARD — HEALTH TIMELINE",
        "\n".join(lines), _pdf_footer())
    return _pdf_response(pdf, "guardian_karta_zivota.pdf")

# --- RODINNÉ KARTY — Guardian Circle members' vaccinations & check-ups.
# --- Privacy: only vaccine + exam categories are shared inside the circle.
async def _circle_member_ids(uid: str) -> set:
    """Guardian Circle = anyone in a guardian relationship (either direction)."""
    ids: set = set()
    async for l in db.guardians.find({"user_id": uid}, {"_id": 0, "guardian_user_id": 1}):
        if l.get("guardian_user_id"):
            ids.add(l["guardian_user_id"])
    async for l in db.guardians.find({"guardian_user_id": uid}, {"_id": 0, "user_id": 1}):
        ids.add(l["user_id"])
    ids.discard(uid)
    return ids

@api.get("/lifecard/family")
async def lifecard_family(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    ids = await _circle_member_ids(user["user_id"])
    today = datetime.now(timezone.utc).date().isoformat()
    h30 = (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat()
    members = []
    for mid in ids:
        m = await db.users.find_one({"user_id": mid}, {"_id": 0, "user_id": 1, "name": 1})
        if not m:
            continue
        evs = await db.calendar_events.find(
            {"user_id": mid, "child_id": None, "category": {"$in": ["vaccine", "exam"]}},
            {"_id": 0, "category": 1, "booster_due": 1}).to_list(500)
        members.append({
            "user_id": mid, "name": m.get("name") or "Člen kruhu",
            "counts": {"vaccine": sum(1 for e in evs if e["category"] == "vaccine"),
                       "exam": sum(1 for e in evs if e["category"] == "exam")},
            "booster_soon": sum(1 for e in evs if e["category"] == "vaccine"
                                and e.get("booster_due") and today <= e["booster_due"] <= h30),
        })
    members.sort(key=lambda x: x["name"])
    return {"members": members, "privacy": "vaccine+exam only"}

@api.get("/lifecard/family/{member_id}/timeline")
async def lifecard_family_timeline(member_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if member_id not in await _circle_member_ids(user["user_id"]):
        raise HTTPException(403, "Not in your Guardian Circle")
    m = await db.users.find_one({"user_id": member_id}, {"_id": 0, "user_id": 1, "name": 1})
    if not m:
        raise HTTPException(404, "Member not found")
    events = await db.calendar_events.find(
        {"user_id": member_id, "child_id": None, "category": {"$in": ["vaccine", "exam"]}},
        {"_id": 0, "event_id": 1, "category": 1, "title": 1, "date": 1, "booster_due": 1, "notes": 1},
    ).sort("date", -1).to_list(200)
    return {"member": {"user_id": member_id, "name": m.get("name") or "Člen kruhu"},
            "events": events, "today": datetime.now(timezone.utc).date().isoformat()}

# --- BOOSTER GUARD — swarm sweep: Jarvis announces boosters 30 & 7 days ahead ---
async def booster_guard_sweep() -> int:
    """Once per stage per event: push + proactive Jarvis chat message."""
    now = datetime.now(timezone.utc)
    today = now.date()
    t = today.isoformat()
    h30 = (today + timedelta(days=30)).isoformat()
    h7 = (today + timedelta(days=7)).isoformat()
    acted = 0
    rows = await db.calendar_events.find(
        {"category": "vaccine", "booster_due": {"$gte": t, "$lte": h30}}, {"_id": 0}).to_list(500)
    for e in rows:
        stage = "7d" if e["booster_due"] <= h7 else "30d"
        flag = f"booster_notified_{stage}"
        if e.get(flag):
            continue
        days_left = (datetime.strptime(e["booster_due"], "%Y-%m-%d").date() - today).days
        who = ""
        if e.get("child_id"):
            ch = await db.lifecard_children.find_one({"child_id": e["child_id"]}, {"_id": 0, "name": 1})
            if ch:
                who = f" (child {ch['name']})"
        msg = (f"⏰ Booster shot coming up{who}: {e['title']} — booster due {e['booster_due']} "
               f"(in {days_left} days). You'll find it in the Life Card. Want me to look for a doctor's appointment?")
        try:
            await send_push(recipients=[e["user_id"]], data={
                "title": "💉 BOOSTER SHOT COMING UP",
                "message": f"{e['title']}{who} — booster do {e['booster_due']} (o {days_left} dní).",
                "action_url": "/health-timeline"})
        except Exception as ex:
            logger.warning(f"booster push failed: {ex}")
        await db.agent_conversations.insert_one({
            "conv_id": uuid.uuid4().hex, "user_id": e["user_id"], "role": "agent",
            "text": apply_watermark(msg), "mood": "alert", "source": "booster_guard", "at": now})
        await db.calendar_events.update_one({"event_id": e["event_id"]}, {"$set": {flag: True}})
        acted += 1
    return acted

# --------- MY RECOVERY (Sick Leave / ePN — Hustle Recovery Guard) ---------
class OutingWindow(BaseModel):
    from_time: str  # HH:MM
    to_time: str    # HH:MM

class EpnIn(BaseModel):
    start_date: str                     # YYYY-MM-DD
    end_date: Optional[str] = None      # expected end
    note: Optional[str] = ""
    contract_type: str = "fulltime"     # fulltime | dpp | dpc
    monthly_gross: Optional[float] = 0
    country: str = "SK"                 # SK | CZ
    outings: List[OutingWindow] = []

def _valid_hhmm(s: str) -> bool:
    return bool(re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", s or ""))

@api.put("/recovery/epn")
async def recovery_epn_save(body: EpnIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    try:
        datetime.strptime(body.start_date, "%Y-%m-%d")
        if body.end_date:
            datetime.strptime(body.end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "dates must be YYYY-MM-DD")
    if body.contract_type not in ("fulltime", "dpp", "dpc"):
        raise HTTPException(400, "contract_type must be fulltime|dpp|dpc")
    for o in body.outings:
        if not (_valid_hhmm(o.from_time) and _valid_hhmm(o.to_time)):
            raise HTTPException(400, "outing times must be HH:MM")
    doc = {
        "user_id": user["user_id"], "start_date": body.start_date, "end_date": body.end_date,
        "note": (body.note or "")[:500], "contract_type": body.contract_type,
        "monthly_gross": float(body.monthly_gross or 0), "country": body.country.upper(),
        "outings": [o.model_dump() for o in body.outings],
        "status": "active", "updated_at": datetime.now(timezone.utc),
    }
    await db.recovery.update_one({"user_id": user["user_id"]}, {"$set": doc}, upsert=True)
    return clean(doc)

@api.get("/recovery/epn")
async def recovery_epn_get(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.recovery.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}

class OutingExtractIn(BaseModel):
    text: str

@api.post("/recovery/extract-outings")
async def recovery_extract_outings(body: OutingExtractIn, authorization: Optional[str] = Header(None)):
    """AI extracts allowed outing hours (vychádzky) from pasted ePN/medical certificate text."""
    await get_current_user(authorization)
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"outings-{uuid.uuid4().hex[:6]}",
        system_message=(
            "You extract allowed outing hours (vychádzky/vycházky) from Slovak or Czech sick-leave "
            "certificates (ePN/neschopenka). Output ONLY valid JSON, no markdown: "
            '{"outings": [{"from_time": "HH:MM", "to_time": "HH:MM"}], "found": true|false}. '
            "If no outing hours are mentioned, return {\"outings\": [], \"found\": false}."
        ),
    ).with_model("anthropic", "claude-sonnet-5")
    try:
        resp = await chat.send_message(UserMessage(text=body.text[:4000]))
        m = re.search(r"\{.*\}", resp, re.S)
        data = json.loads(m.group(0)) if m else {"outings": [], "found": False}
        outings = [o for o in data.get("outings", []) if _valid_hhmm(o.get("from_time", "")) and _valid_hhmm(o.get("to_time", ""))]
        return {"outings": outings, "found": bool(outings)}
    except Exception as e:
        logger.error(f"outing extract error: {e}")
        raise HTTPException(502, "AI service unavailable")

class SickPayIn(BaseModel):
    contract_type: str = "fulltime"   # fulltime | dpp | dpc
    monthly_gross: float
    days: int = 30
    country: str = "SK"               # SK | CZ | EU | UK | US

SICKPAY_CURRENCY = {"SK": "EUR", "CZ": "CZK", "EU": "EUR", "UK": "GBP", "US": "USD"}

@api.post("/recovery/sickpay")
async def recovery_sickpay(body: SickPayIn, authorization: Optional[str] = Header(None)):
    """Global sick-pay estimate — SK/CZ exact-ish 2026 rules, EU/UK/US generic templates.
    Informational only."""
    await get_current_user(authorization)
    if body.monthly_gross <= 0 or body.days <= 0 or body.days > 365:
        raise HTTPException(400, "monthly_gross > 0 and 1..365 days required")
    country = body.country.upper() if body.country.upper() in SICKPAY_CURRENCY else "SK"
    cur = SICKPAY_CURRENCY[country]
    dvz = round(body.monthly_gross * 12 / 365, 4)  # daily assessment base (approx)
    days = body.days
    warnings, breakdown = [], []

    if country in ("SK", "CZ"):
        if body.contract_type in ("dpp", "dpc"):
            warnings.append("DPP/DPČ contracts: you are entitled to sick pay only if you are covered by sickness insurance (regular income). Verify with Sociálna poisťovňa / ČSSZ.")
        d1_3 = min(days, 3); d4_10 = max(0, min(days, 10) - 3); d11p = max(0, days - 10)
        breakdown = [
            {"period": "Day 1–3 (employer, 25 %)", "days": d1_3, "amount": round(d1_3 * dvz * 0.25, 2)},
            {"period": "Day 4–10 (employer, 55 %)", "days": d4_10, "amount": round(d4_10 * dvz * 0.55, 2)},
            {"period": "Day 11+ (Sociálna poisťovňa / ČSSZ, 55 %)", "days": d11p, "amount": round(d11p * dvz * 0.55, 2)},
        ]
    elif country == "EU":
        d1_14 = min(days, 14); d15p = max(0, days - 14)
        breakdown = [
            {"period": "Day 1–14 (employer, 70 % — generic EU template)", "days": d1_14, "amount": round(d1_14 * dvz * 0.70, 2)},
            {"period": "Day 15+ (social insurance, 60 % — generic EU template)", "days": d15p, "amount": round(d15p * dvz * 0.60, 2)},
        ]
        warnings.append("Generic EU template (each member state differs). Check your national insurer for exact rates.")
    elif country == "UK":
        ssp_daily = round(118.75 / 7, 2)  # Statutory Sick Pay 2026 (£/week / 7)
        d_wait = min(days, 3); d_paid = min(max(0, days - 3), 28 * 7)
        breakdown = [
            {"period": "Day 1–3 (waiting days, £0)", "days": d_wait, "amount": 0.0},
            {"period": f"Day 4+ (SSP flat £{ssp_daily}/day, max 28 weeks)", "days": d_paid, "amount": round(d_paid * ssp_daily, 2)},
        ]
        warnings.append("UK SSP is a flat statutory rate — many employers pay more via Occupational Sick Pay. Check your contract.")
    else:  # US
        breakdown = [{"period": "Federal statutory sick pay (none in the US)", "days": days, "amount": 0.0}]
        warnings.append("The US has no federal statutory sick pay. Check state laws (e.g. CA, NY, WA paid sick leave) and your employer PTO policy.")

    employer_social = round(sum(b["amount"] for b in breakdown), 2)
    total = employer_social
    normal_income = round(body.monthly_gross / 30 * days, 2)
    shortfall = round(normal_income - total, 2)
    shortfall_pct = round(shortfall / normal_income * 100, 1) if normal_income else 0
    return {
        "dvz": round(dvz, 2), "days": days, "country": country, "currency": cur,
        "breakdown": breakdown,
        "total_estimate": total, "normal_income": normal_income,
        "shortfall": shortfall, "shortfall_pct": shortfall_pct,
        "solidarity_suggested": shortfall_pct >= 30,
        "warnings": warnings,
        "disclaimer": "Indicative calculation (simplified 2026 rules). Exact amounts are determined by the relevant insurer / authority.",
        "simulated": True,
    }

@api.get("/recovery/report.pdf")
async def recovery_report_pdf(kind: str = "employer", token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    rec = await db.recovery.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "No sick leave record")
    outs = ", ".join([f"{o['from_time']}–{o['to_time']}" for o in rec.get("outings", [])]) or "no outings"
    if kind == "social":
        title = "REPORT FOR THE SOCIAL INSURANCE AGENCY (Sociálna poisťovňa / ČSSZ)\nTEMPORARY SICK LEAVE STATUS"
        recipient = "Sociálna poisťovňa / ČSSZ"
    else:
        title = "REPORT FOR THE EMPLOYER\nTEMPORARY SICK LEAVE STATUS (ePN)"
        recipient = "Employer"
    body_txt = (
        f"Recipient: {recipient}\n"
        f"Name: {user.get('name') or '—'}\n"
        f"DID (Guardian ID): {user['did']}\n\n"
        f"Sick leave start: {rec['start_date']}\n"
        f"Expected end: {rec.get('end_date') or 'per doctor’s decision'}\n"
        f"Permitted outings: {outs}\n"
        f"Contract type: {rec.get('contract_type', 'fulltime').upper()}\n"
        f"Recovery status: {rec.get('note') or 'progressing per doctor’s instructions'}\n\n"
        f"This report was generated by the Archangel OS app at the patient's request.\n"
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    )
    pdf = await run_in_threadpool(_make_pdf, title, body_txt, _pdf_footer())
    return _pdf_response(pdf, f"guardian_pn_report_{kind}.pdf")


# --- MAGIC LENS — photograph ANY health document: AI OCR + plain-language
# --- summary + Life Card category detection. Senior-first, zero typing.
MAGIC_LENS_SYSTEM = (
    "You are Guardian Magic Lens. You read a photo of a health-related document for a senior user. "
    "Return ONLY valid JSON, no markdown: "
    '{"found": true|false, "extracted_text": string, "summary": string, '
    '"detected_category": "medications|allergies|vaccinations|lab_results|diagnoses|surgeries|doctor_visits|insurance|emergency_contacts|other", '
    '"suggested_title": string}. '
    "extracted_text = all legible text from the photo (verbatim OCR). "
    "summary = 3-4 SHORT sentences in plain, simple language a 75-year-old instantly understands. "
    "NO medical jargon — explain what the document says and what it means for the person. "
    "Write the summary in English. "
    "suggested_title = max 6 words naming the document (e.g. 'Tetanus vaccination record'). "
    "found=false only when the image contains no readable document at all."
)

MAGIC_TO_LIFECARD = {
    "vaccinations": "vaccine", "diagnoses": "disease", "allergies": "disease",
    "surgeries": "surgery", "lab_results": "exam", "doctor_visits": "exam",
    "medications": "exam", "insurance": "exam", "emergency_contacts": "exam", "other": "exam",
}


class MagicLensIn(BaseModel):
    image_base64: str


@api.post("/magic-lens")
async def magic_lens(body: MagicLensIn, authorization: Optional[str] = Header(None)):
    ml_user = await get_current_user(authorization)
    from routes.subscription import require_tier
    await require_tier(ml_user, "guardian", "Magic Lens")
    b64 = (body.image_base64 or "").split(",")[-1].strip()
    if not b64:
        raise HTTPException(400, "Empty image")
    if len(b64) > 20 * 1024 * 1024:
        raise HTTPException(400, "Image too large (max ~15MB)")
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"magic-lens-{uuid.uuid4().hex[:6]}",
        system_message=MAGIC_LENS_SYSTEM,
    ).with_model("openai", "gpt-5.4")
    try:
        resp = await chat.send_message(UserMessage(
            text="Read this document photo. JSON only.",
            file_contents=[ImageContent(image_base64=b64)]))
        m = re.search(r"\{.*\}", str(resp), re.S)
        d = json.loads(m.group(0)) if m else {}
    except Exception as e:
        logger.error(f"magic lens error: {e}")
        raise HTTPException(502, "AI service unavailable")
    cat = str(d.get("detected_category") or "other").lower()
    if cat not in MAGIC_TO_LIFECARD:
        cat = "other"
    # GA-T reward for enriching the Life Card with a scanned document (Mosaic data flow)
    gat_reward = 0.0
    if bool(d.get("found")):
        try:
            from routes.token import award_tokens
            gat_tx = await award_tokens(ml_user["user_id"], "document_scan", f"magic lens: {cat}")
            gat_reward = gat_tx["amount"] if gat_tx else 0.0
        except Exception as e:
            logger.warning(f"document_scan GA-T award failed: {e}")
    return {
        "found": bool(d.get("found")),
        "extracted_text": str(d.get("extracted_text") or "")[:8000],
        "summary": str(d.get("summary") or "")[:1200],
        "detected_category": cat,
        "suggested_title": str(d.get("suggested_title") or "Health document")[:80],
        "lifecard_category": MAGIC_TO_LIFECARD[cat],
        "gat_reward": gat_reward,
    }
