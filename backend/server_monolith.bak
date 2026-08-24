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
import os, uuid, logging, hashlib, httpx, requests, asyncio, json, io

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
from emergentintegrations.llm.openai import OpenAITextToSpeech
import re
import base64

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# Emergent managed Google Auth session-exchange endpoint (env-configurable)
AUTH_SESSION_URL = os.environ.get('AUTH_SESSION_URL', 'https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data')

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
            AUTH_SESSION_URL,
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
    pulse_check_optin: Optional[bool] = None
    acoustic_guard: Optional[bool] = None

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

# --------- AI COMPLIANCE (EU AI Act Art. 50 — applicable 2 Aug 2026) ---------
AI_COMPLIANCE_NOTE = (
    " COMPLIANCE: You are an AI system and the user must always know they interact with AI (EU AI Act Art. 50). "
    "Your output is AI-generated, strictly informational and NOT medical, legal or financial advice — the user acts at their own risk. "
    "Never diagnose, prescribe or draft binding legal acts. In emergencies direct to 112/155 (EU), 999 (UK), 911 (US). "
    "End with one short disclaimer sentence in the user's language stating this is AI-generated informational content."
)

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
        f"Respond ONLY in {lang}. Use short sentences and numbered steps." + AI_COMPLIANCE_NOTE
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
    if not user.get("kyc_verified"):
        raise HTTPException(403, "kyc_required: Campaign creation requires KYC verification (AML). Complete it in Legal & Compliance.")
    doc = {
        "campaign_id": uuid.uuid4().hex,
        "user_id": user["user_id"],
        "owner_name": user.get("name") or user["email"],
        "owner_did": user["did"],
        "owner_kyc_attestation": user.get("kyc_attestation"),
        **body.model_dump(),
        "raised_amount": 0.0,
        "supporters": 0,
        "created_at": datetime.now(timezone.utc),
    }
    await db.campaigns.insert_one(doc.copy())
    await _aml_ledger_append(user["user_id"], "campaign_create", {"campaign_id": doc["campaign_id"], "goal": body.goal_amount})
    return clean(doc)

class DonateIn(BaseModel):
    amount: float
    message: Optional[str] = ""

@api.post("/solidarity/campaigns/{cid}/donate")
async def donate(cid: str, body: DonateIn, authorization: Optional[str] = Header(None)):
    """MOCKED payment rails — but real AML rules engine with tamper-evident ledger."""
    user = await get_current_user(authorization)
    if body.amount <= 0:
        raise HTTPException(400, "Invalid amount")
    camp = await db.campaigns.find_one({"campaign_id": cid}, {"_id": 0})
    if not camp:
        raise HTTPException(404, "not found")
    # AML checks: daily limit + velocity
    donated, tx = await _donations_today(user["user_id"])
    limit = AML_VERIFIED_DAILY if user.get("kyc_verified") else AML_UNVERIFIED_DAILY
    if tx >= AML_MAX_TX_PER_DAY:
        await _aml_ledger_append(user["user_id"], "aml_block_velocity", {"tx_today": tx})
        raise HTTPException(403, f"aml_velocity: Max {AML_MAX_TX_PER_DAY} donations per day exceeded.")
    if donated + body.amount > limit:
        await _aml_ledger_append(user["user_id"], "aml_block_limit", {"attempted": body.amount, "donated_today": donated, "limit": limit})
        raise HTTPException(403, f"aml_limit: Daily limit €{limit:.0f} exceeded (today €{donated:.0f}). {'Complete KYC to raise the limit.' if not user.get('kyc_verified') else ''}")
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
    ledger_hash = await _aml_ledger_append(user["user_id"], "donation", {"campaign_id": cid, "amount": body.amount, "kyc": bool(user.get("kyc_verified"))})
    return {"ok": True, "mocked": True, "ledger_hash": ledger_hash}

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

# --------- GLOBAL LEGAL ENGINE (2026 standards) ---------
TOS_VERSION = "2026-06.1"
EU_CC = {"SK","CZ","DE","AT","PL","HU","FR","IT","ES","PT","NL","BE","LU","IE","DK","SE","FI","EE","LV","LT","SI","HR","RO","BG","GR","CY","MT"}
COMMON_LAW_CC = {"US","CA","AU","NZ","IE"}

def resolve_jurisdiction(country: Optional[str]) -> str:
    cc = (country or "").upper()
    if cc in ("GB", "UK"):
        return "UK"
    if cc == "US":
        return "US"
    if cc in EU_CC:
        return "EU"
    return "OTHER"

def _lang_key(language: str) -> str:
    return "sk" if language in ("sk", "cs") else "en"

DISCLAIMERS = {
    "EU": {
        "sk": [
            {"id": "eu_ai_act", "title": "EU AI Act — Čl. 50 (účinné od 2. 8. 2026)", "text": "Komunikujete s AI systémom. Všetok obsah generovaný Jarvisom je označený ako AI výstup. Aplikácia nie je vysokorizikový AI systém ani zdravotnícka pomôcka podľa MDR (EÚ) 2017/745 — slúži na všeobecné wellness a informačné účely."},
            {"id": "eu_gdpr", "title": "GDPR (EÚ) 2016/679", "text": "Vaše zdravotné údaje (čl. 9) sú spracúvané výlučne s vaším súhlasom, uložené šifrovane a ukotvené na vašom DID. Máte právo na prístup, opravu, vymazanie a prenositeľnosť. Prevádzkovateľ nezdieľa údaje s tretími stranami."},
            {"id": "eu_medical", "title": "Nie je lekárska rada", "text": "AI preklady, wellness analýzy a fyzio-rutiny sú informačné. Nenahrádzajú lekára. V núdzi volajte 112 / 155."},
        ],
        "en": [
            {"id": "eu_ai_act", "title": "EU AI Act — Art. 50 (effective 2 Aug 2026)", "text": "You are interacting with an AI system. All Jarvis content is labelled as AI-generated. This app is not a high-risk AI system nor a medical device under MDR (EU) 2017/745 — it serves general wellness and informational purposes."},
            {"id": "eu_gdpr", "title": "GDPR (EU) 2016/679", "text": "Your health data (Art. 9) is processed only with your consent, stored encrypted and anchored to your DID. You have rights of access, rectification, erasure and portability."},
            {"id": "eu_medical", "title": "Not medical advice", "text": "AI translations, wellness analyses and physio routines are informational. They do not replace a doctor. In emergency call 112 / 155."},
        ],
    },
    "UK": {
        "sk": [
            {"id": "uk_dpa", "title": "UK GDPR · Data Protection Act 2018 · DUAA 2025", "text": "Spracovanie osobných a zdravotných údajov podlieha UK GDPR a Data (Use and Access) Act 2025. Údaje sú šifrované a viazané na váš DID."},
            {"id": "uk_ai", "title": "AI transparentnosť", "text": "Komunikujete s AI systémom. Výstupy sú informačné, nie odborná rada. V núdzi volajte 999 / 111 (NHS)."},
        ],
        "en": [
            {"id": "uk_dpa", "title": "UK GDPR · Data Protection Act 2018 · DUAA 2025", "text": "Processing of personal and health data is subject to UK GDPR and the Data (Use and Access) Act 2025. Data is encrypted and bound to your DID."},
            {"id": "uk_ai", "title": "AI transparency", "text": "You are interacting with an AI system. Outputs are informational, not professional advice. In emergency call 999 / 111 (NHS)."},
        ],
    },
    "US": {
        "sk": [
            {"id": "us_fda", "title": "FDA — General Wellness", "text": "Táto aplikácia je „general wellness product” podľa usmernenia FDA — nie je zdravotnícka pomôcka, nediagnostikuje ani nelieči. AI výstupy sú informačné."},
            {"id": "us_hipaa", "title": "HIPAA", "text": "Prevádzkovateľ nie je „covered entity” podľa HIPAA. Údaje sú šifrované a pod vašou kontrolou cez DID. V núdzi volajte 911."},
        ],
        "en": [
            {"id": "us_fda", "title": "FDA — General Wellness", "text": "This app is a general wellness product under FDA guidance — not a medical device; it does not diagnose or treat. AI outputs are informational only."},
            {"id": "us_hipaa", "title": "HIPAA", "text": "The operator is not a HIPAA covered entity. Data is encrypted and under your control via DID. In emergency call 911."},
        ],
    },
    "OTHER": {
        "sk": [
            {"id": "global", "title": "Globálne upozornenie", "text": "Komunikujete s AI systémom. Všetky výstupy sú informačné, nie lekárska či právna rada. Používate ich na vlastné riziko. V núdzi kontaktujte miestne tiesňové služby."},
        ],
        "en": [
            {"id": "global", "title": "Global notice", "text": "You are interacting with an AI system. All outputs are informational, not medical or legal advice. You use them at your own risk. In emergency contact local emergency services."},
        ],
    },
}

TOS_TEXT = {
    "sk": (
        "PODMIENKY POUŽÍVANIA — GUARDIAN HEALTH & ANGEL (v{ver})\n"
        "=====================================================\n\n"
        "1. POVAHA SLUŽBY: Aplikácia je suverénny informačný a wellness nástroj. NIE JE poskytovateľom zdravotnej starostlivosti, zdravotníckou pomôckou, právnou kanceláriou ani finančnou inštitúciou.\n\n"
        "2. AI VÝSTUPY (EU AI Act čl. 50): Všetok obsah generovaný AI (Jarvis) je označený a je VÝLUČNE INFORMAČNÝ. Používateľ berie na vedomie a súhlasí, že AI výstupy používa NA VLASTNÉ RIZIKO a pred akýmkoľvek rozhodnutím o zdraví, práve či financiách sa poradí s kvalifikovaným odborníkom.\n\n"
        "3. ÚPLNÉ ZBAVENIE ZODPOVEDNOSTI: Zakladateľ a autor („Guardian Angel”), vývojári a prevádzkovatelia NENESÚ ŽIADNU ZODPOVEDNOSŤ za akúkoľvek priamu, nepriamu, náhodnú, následnú alebo exemplárnu škodu vzniknutú použitím aplikácie, AI výstupov, P2P výmen, barterov, majáku, detekcie pádu či komunitných funkcií — v maximálnom rozsahu povolenom právom jurisdikcie používateľa.\n\n"
        "4. BEZPEČNOSTNÉ FUNKCIE: Detekcia pádu, strážca nečinnosti, scam štít a núdzový maják sú POMOCNÉ funkcie typu best-effort. Nenahrádzajú tiesňové linky ani profesionálny dohľad. Ich zlyhanie nezakladá nárok na náhradu škody.\n\n"
        "5. P2P A KOMUNITA: Výmeny liekov (len voľnopredajné), barter a trhovisko prebiehajú priamo medzi používateľmi. Prevádzkovateľ nie je zmluvnou stranou, neručí za kvalitu, zákonnosť ani bezpečnosť plnení. Solidarity Hub podlieha AML pravidlám (denné limity, KYC).\n\n"
        "6. DÁTA: Zero-knowledge princíp; údaje sú viazané na váš DID. Právne dokumenty (splnomocnenia, testamenty) sú ŠABLÓNY — pre plnú právnu záväznosť sa vyžaduje vlastnoručný podpis, prípadne svedkovia či notár podľa vašej jurisdikcie.\n\n"
        "7. SÚHLAS: Potvrdením vyhlasujete, že máte 18+ rokov, prečítali ste si tieto podmienky, rozumiete im a prijímate ich vrátane úplného zbavenia zodpovednosti podľa bodu 3.\n\n"
        "AGPL-v3 · Vízia a autorstvo: Guardian Angel · Verzia {ver}"
    ),
    "en": (
        "TERMS OF SERVICE — GUARDIAN HEALTH & ANGEL (v{ver})\n"
        "===================================================\n\n"
        "1. NATURE OF SERVICE: The app is a sovereign informational and wellness tool. It is NOT a healthcare provider, medical device, law firm or financial institution.\n\n"
        "2. AI OUTPUTS (EU AI Act Art. 50): All AI-generated content (Jarvis) is labelled and STRICTLY INFORMATIONAL. The user acknowledges and agrees that AI outputs are used AT THE USER'S OWN RISK and that a qualified professional must be consulted before any health, legal or financial decision.\n\n"
        "3. TOTAL WAIVER OF LIABILITY: The founder and author (\"Guardian Angel\"), developers and operators BEAR NO LIABILITY WHATSOEVER for any direct, indirect, incidental, consequential or exemplary damages arising from use of the app, AI outputs, P2P exchanges, barter, beacon, fall detection or community features — to the maximum extent permitted by the law of the user's jurisdiction.\n\n"
        "4. SAFETY FEATURES: Fall detection, inactivity guard, scam shield and the emergency beacon are best-effort AUXILIARY features. They do not replace emergency lines or professional supervision; their failure creates no claim for damages.\n\n"
        "5. P2P & COMMUNITY: Medicine exchange (OTC only), barter and marketplace occur directly between users. The operator is not a contracting party and does not warrant quality, legality or safety. The Solidarity Hub is subject to AML rules (daily limits, KYC).\n\n"
        "6. DATA: Zero-knowledge principle; data is bound to your DID. Legal documents (proxies, wills) are TEMPLATES — full legal validity requires a handwritten signature and, depending on your jurisdiction, witnesses or a notary.\n\n"
        "7. CONSENT: By accepting you declare you are 18+, have read and understood these terms and accept them, including the total waiver of liability in clause 3.\n\n"
        "AGPL-v3 · Vision & authorship: Guardian Angel · Version {ver}"
    ),
}

@api.get("/legal/region")
async def legal_region(country: Optional[str] = None, language: str = "sk", authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    jur = resolve_jurisdiction(country)
    lk = _lang_key(language)
    testament_format = "common_law_uk" if jur == "UK" else ("common_law" if (country or "").upper() in COMMON_LAW_CC else "civil_law_holograph")
    return {
        "jurisdiction": jur,
        "country": (country or "").upper(),
        "disclaimers": DISCLAIMERS[jur][lk],
        "tos_version": TOS_VERSION,
        "testament_format": testament_format,
        "aml": {"unverified_daily_limit": 150, "verified_daily_limit": 5000, "max_tx_per_day": 10, "currency": "EUR"},
    }

@api.get("/legal/tos")
async def legal_tos(country: Optional[str] = None, language: str = "sk", authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    return {"version": TOS_VERSION, "jurisdiction": resolve_jurisdiction(country), "text": TOS_TEXT[_lang_key(language)].format(ver=TOS_VERSION)}

class TosAcceptIn(BaseModel):
    country: Optional[str] = ""
    language: str = "sk"

@api.post("/legal/accept")
async def legal_accept(body: TosAcceptIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {
        "tos_accepted_version": TOS_VERSION,
        "tos_accepted_at": datetime.now(timezone.utc),
        "tos_jurisdiction": resolve_jurisdiction(body.country),
    }})
    await _aml_ledger_append(user["user_id"], "tos_accept", {"version": TOS_VERSION, "jurisdiction": resolve_jurisdiction(body.country)})
    return clean(await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0}))

# --------- DECENTRALIZED AML (tamper-evident ledger = smart-contract simulation) ---------
AML_UNVERIFIED_DAILY = 150.0
AML_VERIFIED_DAILY = 5000.0
AML_MAX_TX_PER_DAY = 10

async def _aml_ledger_append(user_id: str, action: str, payload: dict) -> str:
    last = await db.aml_ledger.find_one({}, {"_id": 0, "entry_hash": 1}, sort=[("seq", -1)])
    prev_hash = last["entry_hash"] if last else "genesis"
    seq_doc = await db.aml_ledger.find_one({}, {"_id": 0, "seq": 1}, sort=[("seq", -1)])
    seq = (seq_doc["seq"] + 1) if seq_doc else 1
    body = json.dumps({"seq": seq, "user_id": user_id, "action": action, "payload": payload, "prev": prev_hash}, sort_keys=True, default=str)
    entry_hash = hashlib.sha256(body.encode()).hexdigest()
    await db.aml_ledger.insert_one({
        "seq": seq, "user_id": user_id, "action": action, "payload": payload,
        "prev_hash": prev_hash, "entry_hash": entry_hash,
        "created_at": datetime.now(timezone.utc),
    })
    return entry_hash

class KycIn(BaseModel):
    full_name: str
    birth_year: int = Field(ge=1900, le=2010)
    country: str
    declaration: bool = False  # sanctions & source-of-funds self-declaration

@api.post("/aml/kyc")
async def aml_kyc(body: KycIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if not body.declaration:
        raise HTTPException(400, "Sanctions & source-of-funds declaration is required")
    attestation = hashlib.sha256(f"{user['did']}|{body.full_name}|{body.birth_year}|{body.country.upper()}|{datetime.now(timezone.utc).date()}".encode()).hexdigest()
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {
        "kyc_verified": True,
        "kyc_attestation": attestation,
        "kyc_country": body.country.upper(),
        "kyc_verified_at": datetime.now(timezone.utc),
    }})
    ledger_hash = await _aml_ledger_append(user["user_id"], "kyc_attestation", {"attestation": attestation, "did": user["did"], "country": body.country.upper()})
    return {"kyc_verified": True, "attestation": attestation, "ledger_hash": ledger_hash}

async def _donations_today(user_id: str):
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    docs = await db.donations.find({"donor_user_id": user_id, "created_at": {"$gte": start}}, {"_id": 0, "amount": 1}).to_list(500)
    return sum(d.get("amount", 0) for d in docs), len(docs)

@api.get("/aml/status")
async def aml_status(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    donated, tx = await _donations_today(user["user_id"])
    verified = bool(user.get("kyc_verified"))
    limit = AML_VERIFIED_DAILY if verified else AML_UNVERIFIED_DAILY
    entries = await db.aml_ledger.count_documents({"user_id": user["user_id"]})
    return {
        "kyc_verified": verified,
        "attestation": user.get("kyc_attestation"),
        "donated_today": donated,
        "tx_today": tx,
        "daily_limit": limit,
        "remaining_today": max(0.0, limit - donated),
        "max_tx_per_day": AML_MAX_TX_PER_DAY,
        "ledger_entries": entries,
    }

# --------- INTERNATIONAL LEGACY / TESTAMENT ENGINE ---------
class TestamentIn(BaseModel):
    country: str = "SK"
    language: str = "sk"
    full_name: str
    wishes: str
    executor_name: Optional[str] = ""
    witness1: Optional[str] = ""
    witness2: Optional[str] = ""

TESTAMENT_INSTRUCTIONS = {
    "civil_law_holograph": {
        "sk": "HOLOGRAFNÝ TESTAMENT (kontinentálne právo, napr. § 476 Občianskeho zákonníka SR): Aby bol PLATNÝ, musí byť CELÝ napísaný VLASTNOU RUKOU poručiteľa a vlastnoručne PODPÍSANÝ s uvedením dňa, mesiaca a roku. Svedkovia nie sú potrební. Nižšie uvedený text si ODPÍŠTE rukou — vytlačená verzia NIE JE platná.",
        "en": "HOLOGRAPHIC WILL (civil law, e.g. § 476 Slovak Civil Code): To be VALID it must be written ENTIRELY in the testator's OWN HAND and personally SIGNED with day, month and year. No witnesses required. COPY the text below by hand — a printed version is NOT valid.",
    },
    "common_law_uk": {
        "sk": "ZÁVET PODĽA UK PRÁVA (Wills Act 1837, s. 9 — Anglicko a Wales): Musí byť PÍSOMNÝ, PODPÍSANÝ poručiteľom v SÚČASNEJ prítomnosti DVOCH svedkov, ktorí ho tiež podpíšu. POZOR: holografný (rukou písaný nesvedčený) závet NIE JE v Anglicku a Walese platný. V Škótsku postačuje vlastnoručný podpis na každej strane („self-proving” pri podpise pred 1 svedkom).",
        "en": "WILL UNDER UK LAW (Wills Act 1837, s. 9 — England & Wales): Must be IN WRITING, SIGNED by the testator in the SIMULTANEOUS presence of TWO witnesses who also sign. NOTE: a holograph (handwritten unwitnessed) will is NOT valid in England & Wales. In Scotland a will subscribed on every page is self-proving if signed before 1 witness.",
    },
    "common_law": {
        "sk": "ZÁVET (common law — napr. USA): Vyžaduje sa PÍSOMNÁ forma, podpis poručiteľa a DVAJA svedkovia (vo väčšine štátov). Niektoré štáty USA uznávajú aj holografný závet — overte miestne právo. Odporúčame notárske overenie (self-proving affidavit).",
        "en": "WILL (common law — e.g. US): Requires WRITING, the testator's signature and TWO witnesses (most states). Some US states also accept holographic wills — verify local law. A notarized self-proving affidavit is recommended.",
    },
}

@api.post("/legal/testament")
async def legal_testament(body: TestamentIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    cc = body.country.upper()
    fmt = "common_law_uk" if cc in ("GB", "UK") else ("common_law" if cc in COMMON_LAW_CC else "civil_law_holograph")
    lk = _lang_key(body.language)
    now = datetime.now(timezone.utc)
    witnesses = ""
    if fmt != "civil_law_holograph":
        w1 = body.witness1 or "________________"
        w2 = body.witness2 or "________________"
        witnesses = (f"\n\nSVEDOK 1 / WITNESS 1: {w1}  Podpis/Signature: ____________\nSVEDOK 2 / WITNESS 2: {w2}  Podpis/Signature: ____________")
    head = "ZÁVET / POSLEDNÁ VÔĽA" if lk == "sk" else "LAST WILL AND TESTAMENT"
    doc_body = (
        f"{head}\n{'=' * len(head)}\n\n"
        f"{'Ja' if lk == 'sk' else 'I'}, {body.full_name}, DID: {user['did']},\n"
        f"{'týmto vyhlasujem svoju poslednú vôľu' if lk == 'sk' else 'hereby declare my last will'} ({now.strftime('%Y-%m-%d')}):\n\n"
        f"{body.wishes}\n\n"
        f"{'Vykonávateľ závetu' if lk == 'sk' else 'Executor'}: {body.executor_name or '—'}\n"
        f"{'Miesto a dátum' if lk == 'sk' else 'Place and date'}: ____________, {now.strftime('%d.%m.%Y')}\n"
        f"{'Vlastnoručný podpis' if lk == 'sk' else 'Handwritten signature'}: ____________"
        f"{witnesses}"
    )
    doc_hash = hashlib.sha256(f"{user['did']}|{body.full_name}|{fmt}|{now.date()}".encode()).hexdigest()
    document_text = f"{TESTAMENT_INSTRUCTIONS[fmt][lk]}\n\n----------------------------------------\n\n{doc_body}\n\nSHA-256: {doc_hash}"
    saved = {
        "user_id": user["user_id"], "format": fmt, "country": cc, "language": body.language,
        "full_name": body.full_name, "wishes": body.wishes, "executor_name": body.executor_name,
        "witness1": body.witness1, "witness2": body.witness2,
        "document_text": document_text, "doc_hash": doc_hash, "updated_at": now,
    }
    await db.legal_testaments.update_one({"user_id": user["user_id"]}, {"$set": saved}, upsert=True)
    return await db.legal_testaments.find_one({"user_id": user["user_id"]}, {"_id": 0})

@api.get("/legal/testament")
async def get_testament(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.legal_testaments.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}

# --------- PDF EXPORT (Testament / Proxy / TOS) ---------
_FONT_R = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
_FONT_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

def _make_pdf(title: str, body: str, footer: str) -> bytes:
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_font("Lib", "", _FONT_R)
    pdf.add_font("Lib", "B", _FONT_B)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_font("Lib", "B", 15)
    pdf.multi_cell(0, 8, title)
    pdf.ln(2)
    pdf.set_draw_color(0)
    pdf.line(pdf.l_margin, pdf.get_y(), 210 - pdf.r_margin, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Lib", "", 10.5)
    pdf.multi_cell(0, 5.5, body)
    pdf.ln(6)
    pdf.set_font("Lib", "", 7.5)
    pdf.set_text_color(110)
    pdf.multi_cell(0, 4, footer)
    return bytes(pdf.output())

async def _auth_pdf(authorization: Optional[str], token: Optional[str]) -> dict:
    if not authorization and token:
        authorization = f"Bearer {token}"
    return await get_current_user(authorization)

def _pdf_footer(doc_hash: Optional[str] = None) -> str:
    base = (
        f"Guardian Health & Angel · Vygenerované / Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
        "Dokument je šablóna — pre plnú právnu záväznosť sa vyžaduje vlastnoručný podpis a náležitosti podľa vašej jurisdikcie. "
        "This document is a template — full legal validity requires a handwritten signature and the formalities of your jurisdiction.\n"
        "AI obsah je len informačný / AI content is informational only (EU AI Act Art. 50)."
    )
    if doc_hash:
        base = f"SHA-256: {doc_hash}\n" + base
    return base

def _pdf_response(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@api.get("/legal/testament.pdf")
async def testament_pdf(token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    doc = await db.legal_testaments.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "No testament generated yet")
    pdf = await run_in_threadpool(_make_pdf, "ZÁVET / LAST WILL AND TESTAMENT", doc["document_text"], _pdf_footer(doc.get("doc_hash")))
    return _pdf_response(pdf, "guardian_testament.pdf")

@api.get("/legal/proxy.pdf")
async def proxy_pdf(token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    doc = await db.proxy_directives.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not doc or not doc.get("document_text"):
        raise HTTPException(404, "No proxy directive generated yet")
    pdf = await run_in_threadpool(_make_pdf, "SPLNOMOCNENIE / HEALTHCARE PROXY", doc["document_text"], _pdf_footer(doc.get("doc_hash")))
    return _pdf_response(pdf, "guardian_healthcare_proxy.pdf")

@api.get("/legal/tos.pdf")
async def tos_pdf(language: str = "sk", token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    await _auth_pdf(authorization, token)
    text = TOS_TEXT[_lang_key(language)].format(ver=TOS_VERSION)
    pdf = await run_in_threadpool(_make_pdf, f"PODMIENKY POUŽÍVANIA / TERMS OF SERVICE v{TOS_VERSION}", text, _pdf_footer())
    return _pdf_response(pdf, "guardian_tos.pdf")

# --------- MEDICATION REMINDERS (Angel Mode) ---------
class MedReminderIn(BaseModel):
    name: str
    dose: Optional[str] = ""
    times: List[str] = ["08:00"]

@api.get("/meds/reminders")
async def meds_list(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.med_reminders.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", 1).to_list(100)

@api.post("/meds/reminders")
async def meds_add(body: MedReminderIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    times = sorted({t for t in body.times if re.match(r"^\d{2}:\d{2}$", t)})
    if not body.name or not times:
        raise HTTPException(400, "Name and at least one valid time (HH:MM) required")
    doc = {
        "reminder_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "name": body.name, "dose": body.dose or "", "times": times,
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
    return {"ok": True, "taken": True}

# --------- FINAL DIGNITY & FUNERAL FUND (Legacy module) ---------
class DignityDepositIn(BaseModel):
    amount: float = Field(gt=0)
    currency: str = "EUR"  # EUR | CZK | CRYPTO
    method: str = "card"   # card | crypto

class DignityPlanIn(BaseModel):
    monthly_amount: float = Field(ge=0)
    currency: str = "EUR"
    enabled: bool = True

class DignityBeneficiaryIn(BaseModel):
    type: str = "proxy"  # proxy | funeral_director
    name: Optional[str] = ""
    contact: Optional[str] = ""
    iban: Optional[str] = ""

class DignityWishesIn(BaseModel):
    burial_type: str = "cremation"  # burial | cremation | natural
    ceremony_music: Optional[str] = ""
    guest_list: Optional[str] = ""
    notes: Optional[str] = ""

async def _dignity_fund(user_id: str) -> dict:
    fund = await db.dignity_funds.find_one({"user_id": user_id}, {"_id": 0})
    if not fund:
        fund = {
            "user_id": user_id, "balance": 0.0, "currency": "EUR", "status": "locked",
            "death_verified": False, "plan": None, "beneficiary": None,
            "last_plan_run": None, "created_at": datetime.now(timezone.utc),
        }
        await db.dignity_funds.insert_one(fund.copy())
    return fund

async def _apply_recurring(user_id: str, fund: dict) -> dict:
    """Simulated automated recurring transfers — applies missed monthly deposits."""
    plan = fund.get("plan")
    if not plan or not plan.get("enabled") or plan.get("monthly_amount", 0) <= 0 or fund.get("status") == "released":
        return fund
    now = datetime.now(timezone.utc)
    cur = now.strftime("%Y-%m")
    last = fund.get("last_plan_run")
    if last == cur:
        return fund
    # apply one automated deposit for the current month
    amt = float(plan["monthly_amount"])
    await db.dignity_contributions.insert_one({
        "contribution_id": uuid.uuid4().hex, "user_id": user_id, "amount": amt,
        "currency": plan.get("currency", "EUR"), "method": "recurring",
        "mocked": True, "created_at": now,
    })
    await db.dignity_funds.update_one({"user_id": user_id}, {"$inc": {"balance": amt}, "$set": {"last_plan_run": cur}})
    await _aml_ledger_append(user_id, "dignity_recurring", {"amount": amt, "month": cur})
    return await db.dignity_funds.find_one({"user_id": user_id}, {"_id": 0})

@api.get("/dignity/fund")
async def dignity_fund(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    fund = await _dignity_fund(user["user_id"])
    fund = await _apply_recurring(user["user_id"], fund)
    contributions = await db.dignity_contributions.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(20)
    wishes = await db.dignity_wishes.find_one({"user_id": user["user_id"]}, {"_id": 0})
    # default beneficiary = primary healthcare proxy
    if not fund.get("beneficiary"):
        proxy = await db.proxy_directives.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if proxy and proxy.get("proxy_full_name"):
            fund["beneficiary"] = {"type": "proxy", "name": proxy["proxy_full_name"], "contact": proxy.get("proxy_phone") or proxy.get("proxy_email") or "", "iban": "", "auto": True}
    return {**clean(fund), "contributions": contributions, "wishes": clean(wishes) if wishes else None}

@api.post("/dignity/fund/deposit")
async def dignity_deposit(body: DignityDepositIn, authorization: Optional[str] = Header(None)):
    """MOCKED payment rails — real ledger + AML audit."""
    user = await get_current_user(authorization)
    fund = await _dignity_fund(user["user_id"])
    if fund.get("status") == "released":
        raise HTTPException(400, "Fund already released")
    await db.dignity_contributions.insert_one({
        "contribution_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "amount": body.amount, "currency": body.currency, "method": body.method,
        "mocked": True, "created_at": datetime.now(timezone.utc),
    })
    await db.dignity_funds.update_one({"user_id": user["user_id"]}, {"$inc": {"balance": body.amount}, "$set": {"currency": body.currency}})
    ledger = await _aml_ledger_append(user["user_id"], "dignity_deposit", {"amount": body.amount, "currency": body.currency, "method": body.method})
    fund = await db.dignity_funds.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return {**clean(fund), "ledger_hash": ledger, "mocked": True}

@api.put("/dignity/fund/plan")
async def dignity_plan(body: DignityPlanIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await _dignity_fund(user["user_id"])
    await db.dignity_funds.update_one({"user_id": user["user_id"]}, {"$set": {"plan": body.model_dump()}})
    return clean(await db.dignity_funds.find_one({"user_id": user["user_id"]}, {"_id": 0}))

@api.put("/dignity/beneficiary")
async def dignity_beneficiary(body: DignityBeneficiaryIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await _dignity_fund(user["user_id"])
    ben = body.model_dump()
    if body.type == "proxy" and not body.name:
        proxy = await db.proxy_directives.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if proxy and proxy.get("proxy_full_name"):
            ben["name"] = proxy["proxy_full_name"]
            ben["contact"] = ben.get("contact") or proxy.get("proxy_phone") or proxy.get("proxy_email") or ""
    await db.dignity_funds.update_one({"user_id": user["user_id"]}, {"$set": {"beneficiary": ben}})
    return clean(await db.dignity_funds.find_one({"user_id": user["user_id"]}, {"_id": 0}))

@api.put("/dignity/wishes")
async def dignity_wishes(body: DignityWishesIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    now = datetime.now(timezone.utc)
    doc = {**body.model_dump(), "user_id": user["user_id"], "updated_at": now}
    doc["doc_hash"] = hashlib.sha256(f"{user['did']}|{body.burial_type}|{body.ceremony_music}|{now.date()}".encode()).hexdigest()
    await db.dignity_wishes.update_one({"user_id": user["user_id"]}, {"$set": doc}, upsert=True)
    return clean(await db.dignity_wishes.find_one({"user_id": user["user_id"]}, {"_id": 0}))

class DeathVerifyIn(BaseModel):
    death_certificate_number: str
    registry_country: str = "SK"

@api.post("/dignity/verify-death")
async def dignity_verify_death(body: DeathVerifyIn, authorization: Optional[str] = Header(None)):
    """SIMULATED state registry check — production hook point for official registry API.
    Would be called by the proxy/family with the official death certificate number."""
    user = await get_current_user(authorization)
    cert = body.death_certificate_number.strip()
    if len(cert) < 6:
        raise HTTPException(400, "Invalid death certificate number format")
    await _dignity_fund(user["user_id"])
    verification = {
        "verified": True,
        "simulated": True,
        "certificate_number": cert,
        "registry_country": body.registry_country.upper(),
        "verified_at": datetime.now(timezone.utc),
    }
    await db.dignity_funds.update_one({"user_id": user["user_id"]}, {"$set": {"death_verified": True, "verification": verification}})
    await _aml_ledger_append(user["user_id"], "death_verification", {"cert": cert, "country": body.registry_country.upper(), "simulated": True})
    return clean({**verification})

@api.post("/dignity/release")
async def dignity_release(authorization: Optional[str] = Header(None)):
    """Conditional release — funds stay locked until official death verification."""
    user = await get_current_user(authorization)
    fund = await _dignity_fund(user["user_id"])
    if fund.get("status") == "released":
        raise HTTPException(400, "Already released")
    if not fund.get("death_verified"):
        raise HTTPException(403, "locked: Funds are locked until official death verification is confirmed")
    ben = fund.get("beneficiary")
    if not ben or not ben.get("name"):
        proxy = await db.proxy_directives.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if proxy and proxy.get("proxy_full_name"):
            ben = {"type": "proxy", "name": proxy["proxy_full_name"], "contact": proxy.get("proxy_phone", "")}
    if not ben or not ben.get("name"):
        raise HTTPException(400, "No beneficiary designated (set a proxy or funeral director)")
    amount = float(fund.get("balance") or 0)
    now = datetime.now(timezone.utc)
    await db.dignity_funds.update_one({"user_id": user["user_id"]}, {"$set": {
        "status": "released", "released_at": now, "released_to": ben, "released_amount": amount, "balance": 0.0,
    }})
    ledger = await _aml_ledger_append(user["user_id"], "dignity_release", {"amount": amount, "to": ben.get("name"), "type": ben.get("type")})
    try:
        await send_push(recipients=[user["user_id"]], data={
            "title": "🕊 FINAL DIGNITY", "message": f"Fond {amount:.0f} {fund.get('currency','EUR')} uvoľnený pre: {ben.get('name')}", "action_url": "/dignity",
        })
    except Exception as e:
        logger.warning(f"push failed: {e}")
    return {"released": True, "amount": amount, "to": ben, "ledger_hash": ledger, "mocked": True}

# --------- ACCOUNT DELETION (App Store requirement) ---------
USER_DATA_COLLECTIONS = [
    "documents", "waitlist", "emergency_profiles", "fall_events",
    "wellness_checkins", "wellness_vitals", "inactivity_alerts",
    "cabinet_items", "cabinet_exchange", "proxy_directives",
    "market_services", "scam_checks", "survival_items", "barter_offers",
    "beacon_events", "med_reminders", "med_intakes",
    "dignity_funds", "dignity_contributions", "dignity_wishes",
    "legal_testaments", "campaigns", "provider_reviews",
]

@api.delete("/auth/account")
async def delete_account(authorization: Optional[str] = Header(None)):
    """Deletes the user's account and personal data. AML ledger entries are
    retained (hashes only) for regulatory audit; donations/trades/bookings keep
    counterparty records with the user_id but no personal payloads."""
    user = await get_current_user(authorization)
    uid = user["user_id"]
    removed = 0
    for col in USER_DATA_COLLECTIONS:
        res = await db[col].delete_many({"user_id": uid})
        removed += res.deleted_count
    await db.market_bookings.delete_many({"client_user_id": uid})
    await db.donations.delete_many({"donor_user_id": uid})
    await db.user_sessions.delete_many({"user_id": uid})
    await db.users.delete_one({"user_id": uid})
    await _aml_ledger_append(uid, "account_deleted", {"records_removed": removed})
    return {"deleted": True, "records_removed": removed}

# --------- ROOT ---------
@api.get("/")
async def root():
    return {"app": "Guardian Health & Angel", "author": "Guardian Angel", "status": "ok"}

# =========================================================================
# SURVIVAL & TRUST FEATURES (Border Crosser · Wallpaper · Mental Fortress · Biometric Will)
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
    center("＋ MEDICAL ID · V PRÍPADE NÚDZE ＋", y, f_med, gold); y += 90
    name = prof.get("full_name") or user.get("name") or ""
    if name:
        center(name, y, f_big, "#F5F5F5"); y += 100
    rows = [
        ("KRVNÁ SKUPINA / BLOOD", prof.get("blood_type")),
        ("ALERGIE / ALLERGIES", prof.get("allergies")),
        ("ICE KONTAKT", f"{prof.get('emergency_contact_name') or ''} {prof.get('emergency_contact_phone') or ''}".strip()),
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

# --------- MENTAL FORTRESS (Crisis Audio Guide) ---------

MENTAL_TECHNIQUES_SK = [
    {"id": "box", "icon": "square-outline", "title": "Dychový štvorec (Box Breathing)", "subtitle": "60 sekúnd · okamžité upokojenie nervového systému",
     "steps": ["Sadnite si rovno, uvoľnite ramená.", "Nádych nosom — počítajte do 4.", "Zadržte dych — počítajte do 4.", "Výdych ústami — počítajte do 4.", "Zadržte prázdne pľúca — počítajte do 4.", "Opakujte 4 až 6 kôl."]},
    {"id": "grounding", "icon": "earth-outline", "title": "Ukotvenie 5-4-3-2-1", "subtitle": "2 minúty · zastavenie panickej špirály",
     "steps": ["Pomenujte 5 vecí, ktoré vidíte.", "Pomenujte 4 veci, ktoré cítite dotykom.", "Pomenujte 3 zvuky, ktoré počujete.", "Pomenujte 2 vône, ktoré cítite.", "Pomenujte 1 chuť v ústach.", "Dýchajte pomaly a vnímajte, že ste tu a teraz v bezpečí."]},
    {"id": "li4", "icon": "hand-left-outline", "title": "Akupresúra LI4 (Hegu)", "subtitle": "Bod medzi palcom a ukazovákom · úzkosť a napätie",
     "steps": ["Nájdite mäkké miesto medzi palcom a ukazovákom druhej ruky.", "Stlačte palcom pevne, ale nie bolestivo.", "Masírujte krúživými pohybmi 60 sekúnd.", "Dýchajte pomaly a zhlboka.", "Vymeňte ruky a opakujte.", "Pozor: nepoužívajte počas tehotenstva."]},
    {"id": "pc6", "icon": "watch-outline", "title": "Akupresúra PC6 (Neiguan)", "subtitle": "Vnútro zápästia · panika, nevoľnosť, búšenie srdca",
     "steps": ["Otočte dlaň nahor.", "Priložte tri prsty druhej ruky pod zápästné ohyby.", "Bod je pod ukazovákom, medzi dvoma šľachami.", "Tlačte palcom jemne 60 až 90 sekúnd.", "Pri tlaku pomaly vydychujte.", "Vymeňte ruky a opakujte."]},
    {"id": "yintang", "icon": "eye-outline", "title": "Akupresúra Yintang (Tretie oko)", "subtitle": "Bod medzi obočím · okamžité upokojenie mysle",
     "steps": ["Zatvorte oči.", "Priložte ukazovák medzi obočie.", "Jemne masírujte malými krúžkami.", "Pokračujte 1 až 2 minúty.", "Sústreďte sa iba na dotyk a dych."]},
    {"id": "pmr", "icon": "body-outline", "title": "Progresívna svalová relaxácia", "subtitle": "5 minút · uvoľnenie tela pri strese a nespavosti",
     "steps": ["Zatnite päste na 5 sekúnd — potom úplne uvoľnite.", "Zatnite ramená k ušiam na 5 sekúnd — uvoľnite.", "Zatnite brucho na 5 sekúnd — uvoľnite.", "Zatnite stehná na 5 sekúnd — uvoľnite.", "Zatnite lýtka a chodidlá na 5 sekúnd — uvoľnite.", "Vnímajte teplo a ťažobu v celom tele."]},
]

@api.get("/mental/techniques")
async def mental_techniques(language: str = "sk", authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    techniques = []
    for t in MENTAL_TECHNIQUES_SK:
        tts = f"{t['title']}. " + " ".join([f"Krok {i+1}: {s}" for i, s in enumerate(t["steps"])])
        techniques.append({**t, "tts_text": tts})
    return {
        "techniques": techniques,
        "disclaimer": "Toto nie je zdravotná starostlivosť ani krízová linka. Pri ohrození života volajte 112. Linka dôvery Nezábudka: 0800 800 566. (EU AI Act Art. 50 — informačný obsah)",
    }

# --------- BIOMETRIC WILL CONFIRMATION (Legacy) ---------

@api.post("/legal/testament/biometric")
async def biometric_will_upload(file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(400, "Empty file")
    if len(data) > 50 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 50MB)")
    ctype = file.content_type or "application/octet-stream"
    if not (ctype.startswith("audio/") or ctype.startswith("video/")):
        raise HTTPException(400, "Only audio or video statements are accepted")
    file_hash = hashlib.sha256(data).hexdigest()
    rec_id = uuid.uuid4().hex
    ext = (file.filename or "").split(".")[-1].lower() if "." in (file.filename or "") else ("mp4" if ctype.startswith("video/") else "m4a")
    path = f"{APP_NAME}/biometric/{user['user_id']}/{rec_id}.{ext}"
    try:
        await run_in_threadpool(put_object_sync, path, data, ctype)
    except Exception as e:
        logger.error(f"biometric upload failed: {e}")
        raise HTTPException(502, "Storage upload failed")
    # Tamper-evident notarization on the hash-chain ledger (blockchain simulation)
    ledger_hash = await _aml_ledger_append(user["user_id"], "biometric_will", {"sha256": file_hash, "media": ctype, "size": len(data), "did": user["did"]})
    now = datetime.now(timezone.utc)
    rec = {
        "user_id": user["user_id"], "rec_id": rec_id, "media_type": ctype,
        "file_name": file.filename or f"{rec_id}.{ext}", "size": len(data),
        "sha256": file_hash, "storage_path": path, "ledger_hash": ledger_hash,
        "did": user["did"], "recorded_at": now.isoformat(),
    }
    await db.biometric_wills.update_one({"user_id": user["user_id"]}, {"$set": rec}, upsert=True)
    await db.legal_testaments.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"biometric_hash": file_hash, "biometric_ledger_hash": ledger_hash, "biometric_at": now.isoformat()}},
    )
    return clean(rec)

@api.get("/legal/testament/biometric")
async def biometric_will_get(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.biometric_wills.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}

@api.get("/legal/testament/biometric/file")
async def biometric_will_file(token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    rec = await db.biometric_wills.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "No biometric statement recorded")
    try:
        content, ctype = await run_in_threadpool(get_object_sync, rec["storage_path"])
    except Exception as e:
        raise HTTPException(502, f"Storage read failed: {e}")
    return Response(content=content, media_type=ctype)

@api.delete("/legal/testament/biometric")
async def biometric_will_delete(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.biometric_wills.delete_one({"user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    await db.legal_testaments.update_one({"user_id": user["user_id"]}, {"$unset": {"biometric_hash": "", "biometric_ledger_hash": "", "biometric_at": ""}})
    return {"ok": True}

# =========================================================================
# SURVIVAL EXTENSIONS (Acoustic Guard · Survival Bible · Pharmacy Hunter · Pulse Check)
# =========================================================================

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
            data={"title": "🔊 AKUSTICKÁ HROZBA DETEGOVANÁ", "message": f"Hlasný zvuk ({body.kind}) — overte stav seniora.", "action_url": "/family-dashboard"},
        )
    except Exception as e:
        logger.warning(f"acoustic push failed: {e}")
    return clean(doc)

@api.get("/acoustic-events")
async def acoustic_events(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.acoustic_events.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(30)

# --------- ANALOG RECOVERY KIT (Survival Bible PDF) ---------
@api.get("/survival/bible.pdf")
async def survival_bible_pdf(token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    uid = user["user_id"]
    prof = await db.emergency_profiles.find_one({"user_id": uid}, {"_id": 0}) or {}
    proxy = await db.proxy_directives.find_one({"user_id": uid}, {"_id": 0}) or {}
    testament = await db.legal_testaments.find_one({"user_id": uid}, {"_id": 0}) or {}
    meds = await db.med_reminders.find({"user_id": uid}, {"_id": 0}).to_list(50)
    cabinet = await db.cabinet.find({"user_id": uid}, {"_id": 0}).to_list(100)
    waitlist = await db.waitlist.find({"user_id": uid}, {"_id": 0}).to_list(50)
    bio = await db.biometric_wills.find_one({"user_id": uid}, {"_id": 0}) or {}

    parts = []
    parts.append("1. IDENTITA A NÚDZOVÉ INFO / IDENTITY & EMERGENCY")
    parts.append(f"Meno: {prof.get('full_name') or user.get('name') or '—'}")
    parts.append(f"DID: {user['did']}")
    parts.append(f"Krvná skupina: {prof.get('blood_type') or '—'}  ·  Alergie: {prof.get('allergies') or '—'}")
    parts.append(f"Diagnózy: {prof.get('conditions') or '—'}")
    parts.append(f"Lieky (voľný text): {prof.get('medications') or '—'}")
    parts.append(f"ICE kontakt: {prof.get('emergency_contact_name') or '—'} · {prof.get('emergency_contact_phone') or '—'}")
    parts.append(f"Darca orgánov: {'ÁNO — ' + str(prof.get('donor_organs') or 'všetky') if prof.get('is_donor') else 'NIE'}")

    parts.append("\n2. DENNÉ LIEKY / DAILY MEDICATION")
    if meds:
        for m in meds:
            parts.append(f"  • {m.get('name')} {m.get('dose') or ''} — časy: {', '.join(m.get('times') or [])}")
    else:
        parts.append("  — žiadne pripomienky liekov")

    parts.append("\n3. LEKÁRNIČKA A ZÁSOBY / MEDICINE CABINET")
    if cabinet:
        for c in cabinet[:40]:
            parts.append(f"  • {c.get('name')} — {c.get('quantity')} {c.get('unit')}" + (f" · exp. {c.get('expires_on')}" if c.get('expires_on') else ""))
    else:
        parts.append("  — lekárnička je prázdna")

    parts.append("\n4. ČAKACIE LISTINY / WAITLIST HUNTER")
    if waitlist:
        for w in waitlist[:20]:
            parts.append(f"  • {w.get('specialty') or w.get('title') or '—'} · {w.get('city') or ''} · stav: {w.get('status') or 'hunting'}")
    else:
        parts.append("  — žiadne aktívne čakacie listiny")

    parts.append("\n5. SPLNOMOCNENEC / HEALTHCARE PROXY")
    if proxy.get("proxy_full_name"):
        parts.append(f"  {proxy.get('proxy_full_name')} ({proxy.get('proxy_relationship') or '—'}) · {proxy.get('proxy_phone') or '—'}")
        parts.append(f"  Rozsah: {proxy.get('scope') or '—'}  ·  SHA-256: {proxy.get('doc_hash') or '—'}")
    else:
        parts.append("  — splnomocnenec nie je určený")

    parts.append("\n6. ODKAZ A ZÁVET / LEGACY")
    if testament.get("document_text"):
        t = testament["document_text"]
        parts.append(t[:1200] + ("…" if len(t) > 1200 else ""))
        parts.append(f"  SHA-256 závetu: {testament.get('doc_hash') or '—'}")
    else:
        parts.append("  — závet zatiaľ nevygenerovaný")
    if bio.get("sha256"):
        parts.append(f"  Biometrické potvrdenie: {bio.get('media_type')} · {bio.get('recorded_at', '')[:16]} · SHA-256 {bio.get('sha256')}")

    parts.append("\n7. KRÍZOVÉ TECHNIKY BEZ TECHNOLÓGIÍ / ANALOG CRISIS TECHNIQUES")
    for t in MENTAL_TECHNIQUES_SK:
        parts.append(f"  ▶ {t['title']} — {t['subtitle']}")
        for i, s in enumerate(t["steps"]):
            parts.append(f"     {i+1}. {s}")

    parts.append("\n8. NÚDZOVÉ ČÍSLA / EMERGENCY NUMBERS")
    parts.append("  112 — tieseň EÚ · 155 — záchranka (SK/CZ) · 158 — polícia CZ · 0800 800 566 — Linka dôvery Nezábudka")

    body = "\n".join(parts)
    pdf = await run_in_threadpool(_make_pdf, "SURVIVAL BIBLE — ANALOG RECOVERY KIT\nVYTLAČTE A ULOŽTE NA BEZPEČNÉ MIESTO", body, _pdf_footer())
    return _pdf_response(pdf, "guardian_survival_bible.pdf")

# --------- PHARMACY STOCK HUNTER (CZ/SK) ---------
# NOTE: No public real-time stock API exists for SK/CZ pharmacy chains — results are a
# DETERMINISTIC SIMULATION of the aggregator engine (clearly flagged simulated=True).
_PHARMACIES = {
    "SK": [("Dr. Max", "Bratislava"), ("BENU", "Bratislava"), ("Schneider", "Košice"), ("Dr. Max", "Žilina"), ("BENU", "Nitra"), ("Plus Lekáreň", "Prešov")],
    "CZ": [("Dr. Max", "Praha"), ("BENU", "Praha"), ("Pilulka", "Brno"), ("Dr. Max", "Ostrava"), ("BENU", "Plzeň"), ("Magistra", "Olomouc")],
}

def _simulate_stock(med: str, region: str) -> list:
    region = region.upper() if region.upper() in _PHARMACIES else "SK"
    out = []
    for i, (chain, city) in enumerate(_PHARMACIES[region]):
        h = int(hashlib.sha256(f"{med.lower()}|{chain}|{city}".encode()).hexdigest(), 16)
        status = ["in_stock", "low_stock", "out_of_stock"][h % 3]
        price = round(3.5 + (h % 4200) / 100, 2)
        out.append({
            "pharmacy": chain, "city": city, "region": region,
            "status": status, "price_eur": price if status != "out_of_stock" else None,
            "pieces": (h % 14) + 1 if status == "in_stock" else ((h % 3) + 1 if status == "low_stock" else 0),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    out.sort(key=lambda x: {"in_stock": 0, "low_stock": 1, "out_of_stock": 2}[x["status"]])
    return out

@api.get("/pharmacy/search")
async def pharmacy_search(med: str, region: str = "SK", authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    if not med.strip():
        raise HTTPException(400, "med required")
    return {"med": med.strip(), "region": region.upper(), "simulated": True, "results": _simulate_stock(med.strip(), region)}

class PharmacyWatchIn(BaseModel):
    med_name: str
    region: str = "SK"

@api.post("/pharmacy/watch")
async def pharmacy_watch_add(body: PharmacyWatchIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    doc = {
        "watch_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "med_name": body.med_name.strip(), "region": body.region.upper(),
        "status": "watching", "last_scan": None, "found_at": None,
        "created_at": datetime.now(timezone.utc),
    }
    await db.pharmacy_watches.insert_one(doc.copy())
    return clean(doc)

@api.get("/pharmacy/watches")
async def pharmacy_watches(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.pharmacy_watches.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)

@api.post("/pharmacy/watches/{watch_id}/scan")
async def pharmacy_watch_scan(watch_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    w = await db.pharmacy_watches.find_one({"watch_id": watch_id, "user_id": user["user_id"]}, {"_id": 0})
    if not w:
        raise HTTPException(404, "Not found")
    results = _simulate_stock(w["med_name"], w["region"])
    hit = next((r for r in results if r["status"] == "in_stock"), None)
    now = datetime.now(timezone.utc)
    upd = {"last_scan": now}
    if hit:
        upd.update({"status": "found", "found_at": now, "found_pharmacy": f"{hit['pharmacy']} {hit['city']}"})
        try:
            await send_push(recipients=[user["user_id"]], data={"title": "💊 LIEK NÁJDENÝ", "message": f"{w['med_name']} skladom: {hit['pharmacy']} {hit['city']}", "action_url": "/pharmacy-hunter"})
        except Exception as e:
            logger.warning(f"pharmacy push failed: {e}")
    await db.pharmacy_watches.update_one({"watch_id": watch_id}, {"$set": upd})
    return {"scanned": True, "simulated": True, "hit": hit, "results": results}

@api.delete("/pharmacy/watches/{watch_id}")
async def pharmacy_watch_del(watch_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.pharmacy_watches.delete_one({"watch_id": watch_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}

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
        raise HTTPException(403, "opt_in_required: Používateľ nepovolil Guardian Pulse Check (súkromie je opt-in).")
    doc = {
        "req_id": uuid.uuid4().hex,
        "from_user": user["user_id"], "from_name": user.get("name") or "Rodina",
        "target_user": target["user_id"], "target_did": target["did"],
        "status": "pending", "responded_at": None,
        "created_at": datetime.now(timezone.utc),
    }
    await db.pulse_requests.insert_one(doc.copy())
    try:
        await send_push(recipients=[target["user_id"]], data={"title": "💛 TICHÝ PING OD RODINY", "message": f"{doc['from_name']} sa pýta, či ste v poriadku. Odpovedzte jedným ťukom.", "action_url": "/pulse-check"})
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
    title = "💚 V PORIADKU" if body.status == "ok" else "🔴 POTREBUJE POMOC"
    try:
        await send_push(recipients=[req["from_user"]], data={"title": title, "message": f"Odpoveď na tichý ping: {body.status}", "action_url": "/pulse-check"})
    except Exception as e:
        logger.warning(f"pulse respond push failed: {e}")
    return {"ok": True, "status": body.status}

@api.get("/pulse/sent")
async def pulse_sent(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.pulse_requests.find({"from_user": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(30)

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
