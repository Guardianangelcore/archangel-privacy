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

from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

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
    source_text = body.excerpt.strip() or f"[Medical document titled '{doc['title']}' — user has not provided extracted text; give general guidance about what to look for and how to prepare questions for their doctor.]"

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
