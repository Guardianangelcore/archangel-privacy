from fastapi import FastAPI, APIRouter, HTTPException, Header, UploadFile, File, Form, Request
from fastapi.responses import Response, StreamingResponse
from fastapi.concurrency import run_in_threadpool
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os, uuid, logging, hashlib, httpx, requests, asyncio, json

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
from emergentintegrations.llm.openai import OpenAITextToSpeech
import re
import base64

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# Emergent managed push (SuprSend relay) — key injected by deployment pipeline
PUSH_BASE_URL = "https://integrations.emergentagent.com"
EMERGENT_PUSH_KEY = os.environ.get('EMERGENT_PUSH_KEY', 'placeholder')
_push_client = httpx.AsyncClient(base_url=PUSH_BASE_URL, headers={"X-Push-Key": EMERGENT_PUSH_KEY}, timeout=10.0)

# Storage config
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
APP_NAME = "guardian-health-angel"

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="Guardian Health & Angel API")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("guardian")

storage_key: Optional[str] = None

def init_storage() -> str:
    global storage_key
    if storage_key:
        return storage_key
    try:
        resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_LLM_KEY}, timeout=30)
        resp.raise_for_status()
        storage_key = resp.json()["storage_key"]
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
        raise
    return storage_key

def put_object_sync(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120,
    )
    resp.raise_for_status()
    return resp.json()

def get_object_sync(path: str):
    global storage_key
    key = init_storage()
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key}, timeout=60,
    )
    if resp.status_code == 503:
        storage_key = None
        key = init_storage()
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

# --------- MODELS ---------
class User(BaseModel):
    user_id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    did: str
    language: str = "sk"
    angel_mode: bool = False
    fall_guard: bool = False
    inactivity_guard: bool = False
    inactivity_hours: int = 6
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EmergencyProfile(BaseModel):
    user_id: str
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
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Document(BaseModel):
    doc_id: str
    user_id: str
    title: str
    file_name: str
    content_type: str
    size: int
    storage_path: str
    hash: str
    translation: Optional[str] = None
    plain_language: Optional[str] = None
    extracted_text: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class WaitlistItem(BaseModel):
    item_id: str
    user_id: str
    specialty: str
    clinic: str
    city: str
    current_date: str
    target_before: str
    priority: str = "normal"
    status: str = "hunting"
    last_check: Optional[datetime] = None
    found_slot: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class FallEvent(BaseModel):
    event_id: str
    user_id: str
    verified: bool
    cancelled: bool
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# --------- HELPERS ---------
def clean(doc):
    if isinstance(doc, dict) and "_id" in doc:
        doc.pop("_id", None)
    return doc

async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        raise HTTPException(401, "Invalid session")
    exp = session["expires_at"]
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < datetime.now(timezone.utc):
        raise HTTPException(401, "Session expired")
    user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(401, "User not found")
    return user

# --------- AUTH ---------
class SessionExchangeIn(BaseModel):
    session_id: str

@api.post("/auth/session")
async def auth_session(body: SessionExchangeIn):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": body.session_id},
        )
    if r.status_code != 200:
        raise HTTPException(401, "Invalid session id")
    data = r.json()
    email = data["email"]
    name = data.get("name")
    picture = data.get("picture")
    session_token = data["session_token"]

    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": name, "picture": picture}},
        )
        user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        did = f"did:guardian:{uuid.uuid4().hex[:24]}"
        user_doc = User(user_id=user_id, email=email, name=name, picture=picture, did=did).model_dump()
        await db.users.insert_one(user_doc.copy())
        user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})

    await db.user_sessions.insert_one({
        "session_token": session_token,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
    })
    return {"session_token": session_token, "user": user_doc}

@api.get("/auth/me", name="me")
async def me(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return {"user": user}

@api.post("/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        await db.user_sessions.delete_one({"session_token": token})
    return {"ok": True}

# --------- USER PREFS ---------
class PrefIn(BaseModel):
    language: Optional[str] = None
    angel_mode: Optional[bool] = None
    fall_guard: Optional[bool] = None
    inactivity_guard: Optional[bool] = None
    inactivity_hours: Optional[int] = None
    family_size: Optional[int] = None

@api.patch("/me/prefs")
async def update_prefs(body: PrefIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if upd:
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": upd})
    return clean(await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0}))

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

@api.post("/vault/documents/{doc_id}/ocr")
async def ocr_document(doc_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    doc = await db.documents.find_one({"doc_id": doc_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Not found")
    if doc.get("extracted_text"):
        return {"extracted_text": doc["extracted_text"], "cached": True}
    try:
        content, _ = await run_in_threadpool(get_object_sync, doc["storage_path"])
    except Exception as e:
        raise HTTPException(502, f"Storage read failed: {e}")

    ctype = (doc.get("content_type") or "").lower()
    fname = (doc.get("file_name") or "").lower()
    text = ""
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR error: {e}")
        raise HTTPException(502, "OCR service failed")

    if not text:
        raise HTTPException(422, "No text could be extracted from this document")
    await db.documents.update_one({"doc_id": doc_id}, {"$set": {"extracted_text": text}})
    return {"extracted_text": text}

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
        f"Respond ONLY in {lang}."
    )

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
        return {"plain_language": resp}
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
        await db.documents.update_one(
            {"doc_id": doc["doc_id"]},
            {"$set": {"plain_language": resp, "translation": resp}},
        )
        return {"plain_language": resp}
    except Exception as e:
        logger.error(f"AI translate doc error: {e}")
        raise HTTPException(502, "AI service unavailable")

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

async def send_push(recipients: List[str], data: dict, idempotency_key: Optional[str] = None) -> None:
    if not recipients:
        return
    payload: dict = {"recipients": recipients[:100], "data": data}
    if idempotency_key:
        payload["$idempotency_key"] = idempotency_key
    resp = await _push_client.post("/api/v1/push/trigger", json=payload)
    resp.raise_for_status()

# --------- WAITLIST HUNTER ---------
class WaitlistIn(BaseModel):
    specialty: str
    clinic: str
    city: str
    current_date: str
    target_before: str
    priority: str = "normal"

@api.get("/waitlist")
async def list_waitlist(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    items = await db.waitlist.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return items

@api.post("/waitlist")
async def add_waitlist(body: WaitlistIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    item = WaitlistItem(
        item_id=uuid.uuid4().hex,
        user_id=user["user_id"],
        **body.model_dump(),
    ).model_dump()
    await db.waitlist.insert_one(item.copy())
    return clean(item)

@api.post("/waitlist/{item_id}/scan")
async def scan_waitlist(item_id: str, authorization: Optional[str] = Header(None)):
    """Simulated scan — in production integrates with clinic booking systems via ZK-proofs."""
    import random
    user = await get_current_user(authorization)
    item = await db.waitlist.find_one({"item_id": item_id, "user_id": user["user_id"]}, {"_id": 0})
    if not item:
        raise HTTPException(404, "Not found")
    found = random.random() < 0.35
    upd = {"last_check": datetime.now(timezone.utc)}
    if found:
        earlier_days = random.randint(7, 45)
        found_date = (datetime.now(timezone.utc) + timedelta(days=earlier_days)).strftime("%Y-%m-%d")
        upd["found_slot"] = found_date
        upd["status"] = "slot_found"
    await db.waitlist.update_one({"item_id": item_id}, {"$set": upd})
    if found:
        try:
            await send_push(
                recipients=[user["user_id"]],
                data={
                    "title": "Termín nájdený! 🎯",
                    "message": f"{item['specialty']} · {item['clinic']} — voľný termín {upd['found_slot']}",
                    "action_url": "/(tabs)/waitlist",
                },
                idempotency_key=f"slot-{item_id}-{upd['found_slot']}",
            )
        except Exception as e:
            logger.warning(f"Push failed (non-blocking): {e}")
    return {"found": found, "slot": upd.get("found_slot")}

@api.delete("/waitlist/{item_id}")
async def del_waitlist(item_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.waitlist.delete_one({"item_id": item_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}

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

@api.post("/voice/tts")
async def tts_generate(body: TTSIn, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    if not EMERGENT_LLM_KEY:
        raise HTTPException(500, "TTS key not configured")
    text = clean_for_tts(body.text)
    if not text:
        raise HTTPException(400, "Empty text")
    key = hashlib.sha256(f"{text}|{body.voice}|1.0|tts-1|mp3".encode()).hexdigest()
    if key not in _tts_cache:
        try:
            audio = await get_tts().generate_speech(text=text, model="tts-1", voice=body.voice)
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
        f"Respond ONLY in {lang}. Use short sentences and numbered steps."
    )
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"physio-{user['user_id']}-{uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-5")
    try:
        resp = await chat.send_message(UserMessage(text=f"Region: {body.region}. Intensity: {body.intensity}."))
        return {"routine": resp}
    except Exception as e:
        logger.error(f"physio err {e}")
        raise HTTPException(502, "AI unavailable")

# --------- SOLIDARITY HUB (MOCKED P2P) ---------
class CampaignIn(BaseModel):
    title: str
    story: str
    goal_amount: float
    currency: str = "EUR"

@api.get("/solidarity/campaigns")
async def list_campaigns(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    items = await db.campaigns.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return items

@api.post("/solidarity/campaigns")
async def new_campaign(body: CampaignIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    doc = {
        "campaign_id": uuid.uuid4().hex,
        "user_id": user["user_id"],
        "owner_name": user.get("name") or user["email"],
        "owner_did": user["did"],
        **body.model_dump(),
        "raised_amount": 0.0,
        "supporters": 0,
        "created_at": datetime.now(timezone.utc),
    }
    await db.campaigns.insert_one(doc.copy())
    return clean(doc)

class DonateIn(BaseModel):
    amount: float
    message: Optional[str] = ""

@api.post("/solidarity/campaigns/{cid}/donate")
async def donate(cid: str, body: DonateIn, authorization: Optional[str] = Header(None)):
    """MOCKED donation — no real payment. Ledger only."""
    user = await get_current_user(authorization)
    camp = await db.campaigns.find_one({"campaign_id": cid}, {"_id": 0})
    if not camp:
        raise HTTPException(404, "not found")
    await db.donations.insert_one({
        "donation_id": uuid.uuid4().hex,
        "campaign_id": cid,
        "donor_user_id": user["user_id"],
        "donor_did": user["did"],
        "amount": body.amount,
        "message": body.message,
        "created_at": datetime.now(timezone.utc),
        "mocked": True,
    })
    await db.campaigns.update_one(
        {"campaign_id": cid},
        {"$inc": {"raised_amount": body.amount, "supporters": 1}},
    )
    return {"ok": True, "mocked": True}

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

# --------- BLACKOUT PROTOCOL (Survival Snapshot) ---------
@api.get("/blackout/snapshot")
async def blackout_snapshot(authorization: Optional[str] = Header(None)):
    """Returns everything the phone needs to survive an internet outage — cache locally."""
    user = await get_current_user(authorization)
    prof = await db.emergency_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    docs = await db.documents.find({"user_id": user["user_id"]}, {"_id": 0}).sort("uploaded_at", -1).limit(20).to_list(20)
    contacts = [{
        "name": prof.get("emergency_contact_name"),
        "phone": prof.get("emergency_contact_phone"),
    }]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user": {"name": user.get("name"), "did": user["did"], "email": user["email"]},
        "emergency_profile": prof,
        "contacts": contacts,
        "documents_meta": [{"doc_id": d["doc_id"], "title": d["title"], "size": d["size"]} for d in docs],
        "survival_tips": [
            "SK: Pri výpadku sietí zdieľajte tento snapshot cez Bluetooth s dôveryhodným zariadením.",
            "SK: Núdzové čísla: 112 · Záchranná služba 155 · Polícia 158 · Hasiči 150",
            "SK: QR kód s DID je čitateľný aj bez internetu.",
        ],
    }

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
        reply = "Ďakujem, zaznamenal som to. Prajem pekný deň!"
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
                "message": f"Žiadny pohyb {body.hours_inactive} h. Kontaktujeme: {prof.get('emergency_contact_name') or 'rodinu'}.",
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
        f"Be specific and actionable. Respond ONLY in {lang}."
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

# --------- DIGITAL HEALTHCARE PROXY ---------
class ProxyDirectiveIn(BaseModel):
    proxy_full_name: str
    proxy_relationship: str = "partner"
    proxy_phone: Optional[str] = ""
    proxy_email: Optional[str] = ""
    scope: str = "full"  # full | info_access | decisions
    effective_immediately: bool = True
    alternate_name: Optional[str] = ""
    notes: Optional[str] = ""
    language: str = "sk"

PROXY_TEMPLATES = {
    "sk": (
        "SPLNOMOCNENIE A URČENIE ZDRAVOTNÉHO ZÁSTUPCU\n"
        "==============================================\n\n"
        "Ja, {principal}, identifikovaný/á decentralizovaným identifikátorom (DID):\n{did}\n\n"
        "týmto v plnom rozsahu SPLNOMOCŇUJEM a určujem za svojho zdravotného zástupcu:\n\n"
        "  MENO: {proxy}\n  VZŤAH: {relationship}\n  TELEFÓN: {phone}\n  E-MAIL: {email}\n\n"
        "ROZSAH OPRÁVNENIA: {scope_text}\n\n"
        "Splnomocnenec je oprávnený v súlade s § 6 ods. 1 písm. b) zákona č. 576/2004 Z. z. "
        "o zdravotnej starostlivosti prijímať informácie o mojom zdravotnom stave, nahliadať do "
        "zdravotnej dokumentácie a — v rozsahu vyššie uvedenom — udeľovať informovaný súhlas v mojom mene, "
        "ak nebudem schopný/á prejaviť svoju vôľu.\n\n"
        "Toto splnomocnenie {effective}.\n"
        "Náhradný zástupca: {alternate}\n"
        "Poznámky: {notes}\n\n"
        "Dátum vystavenia: {date}\nKryptografický odtlačok (SHA-256): {hash}\n\n"
        "Tento dokument bol vytvorený v aplikácii Guardian Health & Angel a je ukotvený na DID vlastníka. "
        "Odporúčame notárske overenie podpisu pre plnú právnu istotu."
    ),
    "en": (
        "POWER OF ATTORNEY & HEALTHCARE PROXY DESIGNATION\n"
        "================================================\n\n"
        "I, {principal}, identified by decentralized identifier (DID):\n{did}\n\n"
        "hereby fully AUTHORIZE and designate as my healthcare proxy:\n\n"
        "  NAME: {proxy}\n  RELATIONSHIP: {relationship}\n  PHONE: {phone}\n  E-MAIL: {email}\n\n"
        "SCOPE OF AUTHORITY: {scope_text}\n\n"
        "The proxy is entitled to receive information about my health condition, access my medical records, "
        "and — to the extent stated above — give informed consent on my behalf if I am unable to express my will.\n\n"
        "This authorization {effective}.\nAlternate proxy: {alternate}\nNotes: {notes}\n\n"
        "Date of issue: {date}\nCryptographic fingerprint (SHA-256): {hash}\n\n"
        "Created in Guardian Health & Angel, anchored to the owner's DID. Notarization recommended for full legal certainty."
    ),
}
SCOPE_TEXT = {
    "sk": {"full": "PLNÉ — informácie, dokumentácia aj rozhodnutia o liečbe", "info_access": "PRÍSTUP K INFORMÁCIÁM a zdravotnej dokumentácii", "decisions": "ROZHODNUTIA o liečbe pri mojej nespôsobilosti"},
    "en": {"full": "FULL — information, records and treatment decisions", "info_access": "ACCESS TO INFORMATION and medical records", "decisions": "TREATMENT DECISIONS during my incapacity"},
}

@api.get("/proxy-directive")
async def get_proxy(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    doc = await db.proxy_directives.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return doc or {}

@api.put("/proxy-directive")
async def put_proxy(body: ProxyDirectiveIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    lang = body.language if body.language in PROXY_TEMPLATES else ("sk" if body.language in ("sk", "cs") else "en")
    now = datetime.now(timezone.utc)
    principal = user.get("name") or user["email"]
    scope_text = SCOPE_TEXT[lang].get(body.scope, SCOPE_TEXT[lang]["full"])
    effective = ("nadobúda účinnosť okamžite podpisom" if body.effective_immediately else "nadobúda účinnosť pri strate spôsobilosti") if lang == "sk" \
        else ("takes effect immediately upon signature" if body.effective_immediately else "takes effect upon my incapacity")
    base = f"{principal}|{user['did']}|{body.proxy_full_name}|{body.scope}|{now.date().isoformat()}"
    doc_hash = hashlib.sha256(base.encode()).hexdigest()
    document_text = PROXY_TEMPLATES[lang].format(
        principal=principal, did=user["did"], proxy=body.proxy_full_name,
        relationship=body.proxy_relationship, phone=body.proxy_phone or "—", email=body.proxy_email or "—",
        scope_text=scope_text, effective=effective, alternate=body.alternate_name or "—",
        notes=body.notes or "—", date=now.strftime("%Y-%m-%d"), hash=doc_hash,
    )
    doc = {
        "user_id": user["user_id"], **body.model_dump(),
        "document_text": document_text, "doc_hash": doc_hash,
        "principal_name": principal, "principal_did": user["did"],
        "updated_at": now,
    }
    await db.proxy_directives.update_one({"user_id": user["user_id"]}, {"$set": doc}, upsert=True)
    return await db.proxy_directives.find_one({"user_id": user["user_id"]}, {"_id": 0})

# --------- DIRECT SERVICE MARKETPLACE ---------
class ServiceIn(BaseModel):
    title: str
    description: Optional[str] = ""
    category: str = "massage"  # massage | consultation | physio | care | other
    price: float = 0
    currency: str = "EUR"
    payment_methods: List[str] = ["cash"]  # cash | crypto
    city: str = ""
    contact: Optional[str] = ""

@api.get("/market/services")
async def market_list(city: Optional[str] = None, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    q: dict = {"active": True}
    if city:
        q["city"] = city
    return await db.market_services.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)

@api.post("/market/services")
async def market_add(body: ServiceIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    doc = {
        "service_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "provider_name": user.get("name") or user["email"], "provider_did": user["did"],
        **body.model_dump(), "active": True, "bookings": 0,
        "created_at": datetime.now(timezone.utc),
    }
    await db.market_services.insert_one(doc.copy())
    return clean(doc)

@api.delete("/market/services/{service_id}")
async def market_del(service_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.market_services.update_one({"service_id": service_id, "user_id": user["user_id"]}, {"$set": {"active": False}})
    if res.matched_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}

class BookIn(BaseModel):
    message: Optional[str] = ""
    payment_method: str = "cash"

@api.post("/market/services/{service_id}/book")
async def market_book(service_id: str, body: BookIn, authorization: Optional[str] = Header(None)):
    """Direct booking — payment happens cash/crypto peer-to-peer, no middleman."""
    user = await get_current_user(authorization)
    svc = await db.market_services.find_one({"service_id": service_id, "active": True}, {"_id": 0})
    if not svc:
        raise HTTPException(404, "Not found")
    booking = {
        "booking_id": uuid.uuid4().hex, "service_id": service_id,
        "provider_user_id": svc["user_id"], "client_user_id": user["user_id"],
        "client_name": user.get("name") or user["email"],
        "message": body.message, "payment_method": body.payment_method,
        "status": "requested", "created_at": datetime.now(timezone.utc),
    }
    await db.market_bookings.insert_one(booking.copy())
    await db.market_services.update_one({"service_id": service_id}, {"$inc": {"bookings": 1}})
    try:
        await send_push(
            recipients=[svc["user_id"]],
            data={"title": "Nová objednávka 💼", "message": f"{booking['client_name']}: {svc['title']} ({body.payment_method})", "action_url": "/marketplace"},
        )
    except Exception as e:
        logger.warning(f"push failed: {e}")
    return clean(booking)

@api.get("/market/bookings")
async def market_bookings(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    docs = await db.market_bookings.find({"$or": [{"provider_user_id": uid}, {"client_user_id": uid}]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return docs

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
    risk, verdict, reasons, advice = "medium", "Analýza zlyhala — buďte opatrní.", [], "Nikdy neposielajte peniaze ani kódy."
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
                data={"title": "🛡️ SCAM SHIELD — VYSOKÉ RIZIKO", "message": f"Podvodná správa zachytená. Upozorňujeme: {prof.get('emergency_contact_name') or 'rodinu'}.", "action_url": "/scam-shield"},
            )
        except Exception as e:
            logger.warning(f"push failed: {e}")
    return clean(doc)

@api.get("/scam/history")
async def scam_history(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.scam_checks.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(30)

# --------- SURVIVAL AUDITOR ---------
class SurvivalItemIn(BaseModel):
    name: str
    category: str = "food"  # water | food | power | meds | tools
    quantity: float = 1
    unit: str = "ks"
    daily_need_per_person: float = 1.0

@api.get("/survival/items")
async def survival_list(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.survival_items.find({"user_id": user["user_id"]}, {"_id": 0}).sort("category", 1).to_list(300)

@api.post("/survival/items")
async def survival_add(body: SurvivalItemIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    doc = {"item_id": uuid.uuid4().hex, "user_id": user["user_id"], **body.model_dump(), "created_at": datetime.now(timezone.utc)}
    await db.survival_items.insert_one(doc.copy())
    return clean(doc)

@api.delete("/survival/items/{item_id}")
async def survival_del(item_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.survival_items.delete_one({"item_id": item_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}

@api.get("/survival/runway")
async def survival_runway(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    family = max(1, int(user.get("family_size") or 2))
    items = await db.survival_items.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(300)
    cats: dict = {}
    for it in items:
        need = max(0.01, float(it.get("daily_need_per_person") or 1)) * family
        days = float(it.get("quantity") or 0) / need
        cats.setdefault(it["category"], 0.0)
        cats[it["category"]] += days
    category_runways = {k: round(v, 1) for k, v in cats.items()}
    essential = [category_runways.get(c) for c in ("water", "food") if c in category_runways]
    overall = round(min(essential), 1) if essential else 0.0
    return {
        "family_size": family,
        "category_runways": category_runways,
        "overall_days": overall,
        "items_count": len(items),
    }

# --------- SKILL BARTER ENGINE ---------
BARTER_START_CREDITS = 10

async def _barter_credits(user_id: str) -> int:
    u = await db.users.find_one({"user_id": user_id}, {"_id": 0, "barter_credits": 1})
    c = u.get("barter_credits") if u else None
    if c is None:
        await db.users.update_one({"user_id": user_id}, {"$set": {"barter_credits": BARTER_START_CREDITS}})
        return BARTER_START_CREDITS
    return int(c)

class BarterOfferIn(BaseModel):
    offer_skill: str
    want_in_return: Optional[str] = ""
    category: str = "other"  # health | legal | craft | care | food | other
    city: str = ""
    credits_value: int = Field(default=1, ge=1, le=50)

@api.get("/barter/me")
async def barter_me(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    credits = await _barter_credits(user["user_id"])
    trades = await db.barter_trades.find(
        {"$or": [{"provider_user_id": user["user_id"]}, {"client_user_id": user["user_id"]}]}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return {"credits": credits, "trades": trades}

@api.get("/barter/offers")
async def barter_list(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    return await db.barter_offers.find({"status": "open"}, {"_id": 0}).sort("created_at", -1).to_list(200)

@api.post("/barter/offers")
async def barter_add(body: BarterOfferIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await _barter_credits(user["user_id"])
    doc = {
        "offer_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "owner_name": user.get("name") or user["email"], "owner_did": user["did"],
        **body.model_dump(), "status": "open", "created_at": datetime.now(timezone.utc),
    }
    await db.barter_offers.insert_one(doc.copy())
    return clean(doc)

@api.post("/barter/offers/{offer_id}/accept")
async def barter_accept(offer_id: str, authorization: Optional[str] = Header(None)):
    """Trust-credit trade: client spends credits, provider earns them."""
    user = await get_current_user(authorization)
    offer = await db.barter_offers.find_one({"offer_id": offer_id, "status": "open"}, {"_id": 0})
    if not offer:
        raise HTTPException(404, "Not found or closed")
    if offer["user_id"] == user["user_id"]:
        raise HTTPException(400, "Cannot accept your own offer")
    cost = int(offer.get("credits_value") or 1)
    balance = await _barter_credits(user["user_id"])
    if balance < cost:
        raise HTTPException(402, f"Not enough trust credits ({balance}/{cost})")
    await _barter_credits(offer["user_id"])
    await db.users.update_one({"user_id": user["user_id"]}, {"$inc": {"barter_credits": -cost}})
    await db.users.update_one({"user_id": offer["user_id"]}, {"$inc": {"barter_credits": cost}})
    await db.barter_offers.update_one({"offer_id": offer_id}, {"$set": {"status": "traded"}})
    trade = {
        "trade_id": uuid.uuid4().hex, "offer_id": offer_id,
        "offer_skill": offer["offer_skill"], "credits": cost,
        "provider_user_id": offer["user_id"], "provider_name": offer["owner_name"],
        "client_user_id": user["user_id"], "client_name": user.get("name") or user["email"],
        "created_at": datetime.now(timezone.utc),
    }
    await db.barter_trades.insert_one(trade.copy())
    try:
        await send_push(
            recipients=[offer["user_id"]],
            data={"title": "Barter dohodnutý 🔁", "message": f"{trade['client_name']} prijal: {offer['offer_skill']} (+{cost} kreditov)", "action_url": "/barter"},
        )
    except Exception as e:
        logger.warning(f"push failed: {e}")
    return clean(trade)

@api.delete("/barter/offers/{offer_id}")
async def barter_del(offer_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.barter_offers.delete_one({"offer_id": offer_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}

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
    loc = f"https://maps.google.com/?q={body.lat},{body.lng}" if body.lat is not None else "poloha nedostupná"
    try:
        await send_push(
            recipients=[user["user_id"]],
            data={"title": "🔴 TICHÝ MAJÁK AKTIVOVANÝ", "message": f"Signál odoslaný rodine. {loc}", "action_url": "/family-dashboard"},
        )
    except Exception as e:
        logger.warning(f"push failed: {e}")
    return clean(doc)

@api.get("/beacon/history")
async def beacon_history(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.beacon_events.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(20)

# --------- ROOT ---------
@api.get("/")
async def root():
    return {"app": "Guardian Health & Angel", "author": "Guardian Angel", "status": "ok"}

app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    try:
        await db.users.create_index("email", unique=True)
        await db.users.create_index("user_id", unique=True)
        await db.users.create_index("did", unique=True)
        await db.user_sessions.create_index("session_token", unique=True)
        await db.user_sessions.create_index("expires_at", expireAfterSeconds=0)
        await db.documents.create_index([("user_id", 1), ("uploaded_at", -1)])
        await db.waitlist.create_index([("user_id", 1), ("created_at", -1)])
    except Exception as e:
        logger.warning(f"index setup: {e}")
    try:
        await run_in_threadpool(init_storage)
    except Exception as e:
        logger.warning(f"storage init at startup failed (non-fatal): {e}")

@app.on_event("shutdown")
async def shutdown():
    client.close()
