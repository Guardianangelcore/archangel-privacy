# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
from fastapi import HTTPException, Header, UploadFile, File, Form
from fastapi.responses import Response, StreamingResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import os, uuid, hashlib, json, io, re, base64, httpx, asyncio

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
        "notes": "Dokument uložený v Zdravotnom trezore", "booster_due": None,
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
        f"Structure the response as: 1) Súhrn / Summary in 1-2 sentences, "
        f"2) Čo to znamená / What this means (bullet list of plain-language points), "
        f"3) Odporúčania / Recommendations (2-3 practical next steps). "
        f"NEVER invent medications or diagnoses. If information is unclear, say so. "
        f"Respond ONLY in {lang}." + AI_COMPLIANCE_NOTE
    )

# --------- NEXT-APPOINTMENT EXTRACTION (gpt-5.4, strict JSON) ---------
APPT_SYSTEM = (
    "You extract the next upcoming medical appointment from medical text. "
    'Reply ONLY with strict JSON: {"found": true/false, "date": "YYYY-MM-DD" or null, '
    '"time": "HH:MM" or null, "title": "short Slovak label, e.g. Kontrola — ortopédia"}. '
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
                    "title": (data.get("title") or "Kontrola u lekára")[:140]}
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


# --------- VOICE: TTS ---------
_tts_client: Optional[OpenAITextToSpeech] = None
def get_tts():
    global _tts_client
    if _tts_client is None:
        _tts_client = OpenAITextToSpeech(api_key=EMERGENT_LLM_KEY)
    return _tts_client

def clean_for_tts(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)
    text = re.sub(r"[*_#>~|]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:4000]

_tts_cache: dict = {}  # in-memory {hash: bytes}

class TTSIn(BaseModel):
    text: str
    voice: str = "nova"
    language: str = "sk"
    speed: float = 1.0  # emotional pacing: 0.9 calm/soothing · 1.05 energetic

@api.post("/voice/tts")
async def tts_generate(body: TTSIn, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    if not EMERGENT_LLM_KEY:
        raise HTTPException(500, "TTS key not configured")
    text = clean_for_tts(body.text)
    if not text:
        raise HTTPException(400, "Empty text")
    speed = min(1.3, max(0.7, body.speed or 1.0))
    key = hashlib.sha256(f"{text}|{body.voice}|{speed}|tts-1|mp3".encode()).hexdigest()
    if key not in _tts_cache:
        try:
            audio = await get_tts().generate_speech(text=text, model="tts-1", voice=body.voice, speed=speed)
            _tts_cache[key] = audio
        except Exception as e:
            logger.error(f"tts err {e}")
            raise HTTPException(502, "TTS service failed")
    return {"key": key, "url": f"/api/voice/tts/{key}.mp3"}

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
            data={"title": "P2P Výmena 🤝", "message": f"{user.get('name') or 'Sused'} reaguje na: {ex['item_name']}", "action_url": "/medicine-cabinet"},
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
    return lk if lk in ("sk", "cs", "en", "de") else "sk"

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
        g["video_note"] = "Video: Mixkit free license · demonštračný záber"
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
    for kw, name in (("ortop", "Ortopédia"), ("kardio", "Kardiológia"), ("neuro", "Neurológia"),
                     ("chirurg", "Chirurgia"), ("onko", "Onkológia"), ("reuma", "Reumatológia"),
                     ("urolog", "Urológia"), ("gastro", "Gastroenterológia")):
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
# injury=Úrazy · exam=Prehliadky. Legacy 'history' remains for system rows
# (vault documents, billing receipts); old MANUAL 'history' records are
# lazily migrated to 'disease'.
LIFECARD_CATS = ("vaccine", "disease", "surgery", "injury", "exam")
BLOOD_TYPES = ("A+", "A-", "B+", "B-", "AB+", "AB-", "0+", "0-")

class CalendarEventIn(BaseModel):
    category: str  # vaccine | disease | surgery | injury | exam
    title: str
    date: str      # YYYY-MM-DD
    notes: Optional[str] = ""
    booster_due: Optional[str] = None  # YYYY-MM-DD (vaccines)

@api.post("/calendar/events")
async def calendar_add(body: CalendarEventIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    cat = "disease" if body.category == "history" else body.category  # legacy alias
    if cat not in LIFECARD_CATS:
        raise HTTPException(400, "category must be vaccine|disease|surgery|injury|exam")
    try:
        datetime.strptime(body.date, "%Y-%m-%d")
        if body.booster_due:
            datetime.strptime(body.booster_due, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "date must be YYYY-MM-DD")
    doc = {
        "event_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "category": cat, "title": body.title.strip()[:140],
        "date": body.date, "notes": (body.notes or "")[:500],
        "booster_due": body.booster_due, "source": "manual",
        "created_at": datetime.now(timezone.utc),
    }
    await db.calendar_events.insert_one(doc.copy())
    return clean(doc)

async def _lifecard_counts(uid: str) -> dict:
    counts = {c: 0 for c in LIFECARD_CATS}
    rows = await db.calendar_events.find({"user_id": uid}, {"_id": 0, "category": 1}).to_list(2000)
    for r in rows:
        c = r.get("category")
        if c in counts:
            counts[c] += 1
    return counts

@api.get("/calendar/timeline")
async def calendar_timeline(category: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    # Lazy migration: old manual 'history' rows ("Choroba / úraz") → disease
    await db.calendar_events.update_many(
        {"user_id": uid, "category": "history", "source": "manual"},
        {"$set": {"category": "disease"}})
    q: dict = {"user_id": uid}
    if category in LIFECARD_CATS + ("history",):
        q["category"] = category
    events = await db.calendar_events.find(q, {"_id": 0}).sort("date", -1).to_list(500)
    today = datetime.now(timezone.utc).date().isoformat()
    horizon = (datetime.now(timezone.utc) + timedelta(days=90)).date().isoformat()
    upcoming = [e for e in events if e["category"] == "exam" and e["date"] >= today]
    booster_alerts = [e for e in events if e["category"] == "vaccine" and e.get("booster_due") and e["booster_due"] <= horizon]
    return {"events": events, "upcoming_exams": sorted(upcoming, key=lambda e: e["date"]),
            "booster_alerts": sorted(booster_alerts, key=lambda e: e["booster_due"]),
            "counts": await _lifecard_counts(uid), "today": today}

@api.delete("/calendar/events/{event_id}")
async def calendar_delete(event_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.calendar_events.delete_one({"event_id": event_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}

# --- Life Card identity (meno · dátum narodenia · krvná skupina — zdroj: rodný list) ---
async def _lifecard_payload(user: dict) -> dict:
    uid = user["user_id"]
    prof = await db.emergency_profiles.find_one({"user_id": uid}, {"_id": 0}) or {}
    birth_date = user.get("birth_date")
    age = None
    if birth_date:
        try:
            bd = datetime.strptime(birth_date, "%Y-%m-%d").date()
            t = datetime.now(timezone.utc).date()
            age = t.year - bd.year - ((t.month, t.day) < (bd.month, bd.day))
        except ValueError:
            birth_date = None
    if age is None and user.get("birth_year"):
        age = datetime.now(timezone.utc).year - int(user["birth_year"])
    pred = await db.lifecard_predictions.find_one({"user_id": uid}, {"_id": 0}) or {}
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

# --- PREDIKCIE — Jarvis suggests the next vaccination / preventive check-up ---
@api.post("/lifecard/predictions")
async def lifecard_predictions(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    card = await _lifecard_payload(user)
    events = await db.calendar_events.find(
        {"user_id": uid, "category": {"$in": list(LIFECARD_CATS)}},
        {"_id": 0, "category": 1, "title": 1, "date": 1, "booster_due": 1},
    ).sort("date", -1).to_list(200)
    today = card["today"]
    lang = (user.get("language") or "sk")[:2]
    reason_lang = "Slovak" if lang in ("sk", "cs") else f"the user's app language ({lang})"
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"lifecard-pred-{uuid.uuid4().hex[:6]}",
        system_message=(
            "You are a preventive-care planner for Slovakia/Czechia (EU standards). "
            "Based on the patient's LIFE CARD history you suggest WHEN the next vaccination or "
            "preventive check-up is due. Use standard adult schedules: tetanus booster every 15 years, "
            "flu vaccine yearly for 59+, general preventive check-up every 2 years (yearly for 60+), "
            "dental check-up yearly, and respect explicit booster_due dates in the history. "
            'Return ONLY valid JSON, no markdown: {"predictions": [{"title": "...", '
            '"category": "vaccine|exam", "suggested_date": "YYYY-MM-DD", "reason": "..."}]}. '
            f"Max 4 predictions. suggested_date must be AFTER {today} and within 24 months. "
            f"'title' and 'reason' (1 short sentence) must be written in {reason_lang}. "
            "Do not repeat a prediction for something already scheduled after today in the history."
        ),
    ).with_model("openai", "gpt-5.4")
    payload = {
        "today": today, "age": card["age"], "birth_date": card["birth_date"],
        "history": events[:100],
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
        {"user_id": uid},
        {"$set": {"user_id": uid, "predictions": preds, "generated_at": generated_at}},
        upsert=True)
    from routes.agent import award_xp
    await award_xp(uid, 6, "lifecard_predictions")
    return {"predictions": preds, "generated_at": generated_at, "ai": True}

class PredictionAcceptIn(BaseModel):
    title: str
    category: str = "exam"
    date: str  # YYYY-MM-DD
    reason: Optional[str] = ""

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
    doc = {
        "event_id": uuid.uuid4().hex, "user_id": uid,
        "category": body.category, "title": body.title.strip()[:140],
        "date": body.date, "notes": f"Jarvis predikcia · {(body.reason or '').strip()}"[:500],
        "booster_due": None, "source": "jarvis",
        "created_at": datetime.now(timezone.utc),
    }
    await db.calendar_events.insert_one(doc.copy())
    await db.lifecard_predictions.update_one(
        {"user_id": uid}, {"$pull": {"predictions": {"title": body.title}}})
    return clean(doc)

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
            warnings.append("DPP/DPČ: nárok na nemocenské máte len ak ste nemocensky poistený (pravidelný príjem). Overte si to v Sociálnej poisťovni / ČSSZ.")
        d1_3 = min(days, 3); d4_10 = max(0, min(days, 10) - 3); d11p = max(0, days - 10)
        breakdown = [
            {"period": "Deň 1–3 (zamestnávateľ, 25 %)", "days": d1_3, "amount": round(d1_3 * dvz * 0.25, 2)},
            {"period": "Deň 4–10 (zamestnávateľ, 55 %)", "days": d4_10, "amount": round(d4_10 * dvz * 0.55, 2)},
            {"period": "Deň 11+ (Sociálna poisťovňa / ČSSZ, 55 %)", "days": d11p, "amount": round(d11p * dvz * 0.55, 2)},
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
        "disclaimer": "Orientačný výpočet (zjednodušené pravidlá 2026). Presné sumy určí príslušná poisťovňa / úrad.",
        "simulated": True,
    }

@api.get("/recovery/report.pdf")
async def recovery_report_pdf(kind: str = "employer", token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    rec = await db.recovery.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "No sick leave record")
    outs = ", ".join([f"{o['from_time']}–{o['to_time']}" for o in rec.get("outings", [])]) or "bez vychádzok"
    if kind == "social":
        title = "HLÁSENIE PRE SOCIÁLNU POISŤOVŇU / ČSSZ\nSTATUS DOČASNEJ PRÁCENESCHOPNOSTI"
        recipient = "Sociálna poisťovňa / ČSSZ"
    else:
        title = "HLÁSENIE PRE ZAMESTNÁVATEĽA\nSTATUS DOČASNEJ PRÁCENESCHOPNOSTI (ePN)"
        recipient = "Zamestnávateľ"
    body_txt = (
        f"Adresát: {recipient}\n"
        f"Meno: {user.get('name') or '—'}\n"
        f"DID (Guardian ID): {user['did']}\n\n"
        f"Začiatok PN: {rec['start_date']}\n"
        f"Predpokladané ukončenie: {rec.get('end_date') or 'podľa rozhodnutia lekára'}\n"
        f"Povolené vychádzky: {outs}\n"
        f"Typ úväzku: {rec.get('contract_type', 'fulltime').upper()}\n"
        f"Stav rekonvalescencie: {rec.get('note') or 'prebieha podľa pokynov lekára'}\n\n"
        f"Toto hlásenie bolo vygenerované aplikáciou Guardian Health & Angel na žiadosť pacienta.\n"
        f"Vygenerované: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    )
    pdf = await run_in_threadpool(_make_pdf, title, body_txt, _pdf_footer())
    return _pdf_response(pdf, f"guardian_pn_report_{kind}.pdf")
