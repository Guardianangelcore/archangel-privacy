# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
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
# Single source of truth for the legal document version (ToS + Privacy Policy).
# Must match LEGAL_VERSION in frontend/src/legal.ts.
TOS_VERSION = "2026-06.1"

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

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


# --------- AI COMPLIANCE (EU AI Act Art. 50 — applicable 2 Aug 2026) ---------
LANG_NAMES = {"sk": "Slovak", "cs": "Czech", "en": "English", "de": "German"}
AI_COMPLIANCE_NOTE = (
    " COMPLIANCE: You are an AI system and the user must always know they interact with AI (EU AI Act Art. 50). "
    "Your output is AI-generated, strictly informational and NOT medical, legal or financial advice — the user acts at their own risk. "
    "Never diagnose, prescribe or draft binding legal acts. In emergencies direct to 112/155 (EU), 999 (UK), 911 (US). "
    "End with one short disclaimer sentence in the user's language stating this is AI-generated informational content."
)

# EU AI Act Art. 50 watermark — every AI-generated response is marked
AI_WATERMARK = "AI Content · Sovereign Protocol"

def apply_watermark(text: str) -> str:
    """Append the Sovereign Protocol watermark once (idempotent)."""
    if not text:
        return text
    t = str(text).rstrip()
    if AI_WATERMARK in t:
        return t
    # Discreet single-line footer, separated by newline
    return f"{t}\n\n— {AI_WATERMARK}"

def did_hash(user_id: str) -> str:
    """Deterministic short DID hash for logs/metadata (no PII leak)."""
    if not user_id:
        return "did:0"
    return "did:" + hashlib.sha256(str(user_id).encode()).hexdigest()[:12]


AI_BUDGET_MSG = ("AI budget exhausted — the Universal LLM key needs a top-up "
                 "(Emergent → Profile → Manage plan → Universal Key → Add Balance).")
AI_DOWN_MSG = "AI is temporarily unavailable — please try again in a moment."


def ai_error_message(e: Exception) -> str:
    """Human-readable reason for an LLM failure (never leaks provider internals)."""
    return AI_BUDGET_MSG if "budget has been exceeded" in str(e).lower() else AI_DOWN_MSG


def ai_http_error(e: Exception) -> HTTPException:
    """503 (not 502) so the edge proxy passes our JSON detail through instead of
    replacing it with a generic 'error code: 502' page."""
    return HTTPException(503, ai_error_message(e))


async def send_push(recipients: List[str], data: dict, idempotency_key: Optional[str] = None) -> None:
    if not recipients:
        return
    payload: dict = {"recipients": recipients[:100], "data": data}
    if idempotency_key:
        payload["$idempotency_key"] = idempotency_key
    resp = await _push_client.post("/api/v1/push/trigger", json=payload)
    resp.raise_for_status()


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
        f"Archangel OS · Guardian Angel Sovereign Foundation (DAO) · Vygenerované / Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
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
