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

@api.get("/")
async def root():
    return {"app": "Guardian Health & Angel", "author": "Guardian Angel Sovereign Foundation (DAO)", "status": "ok"}


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
        # Inner Circle whitelist — permanent Archangel status on first login
        # (Founder email guardian.angel.core@proton.me is auto-provisioned.)
        wl = await db.inner_circle.find_one({"email": email.lower()})
        is_founder = (email.lower() == FOUNDER_EMAIL)
        if wl or is_founder:
            await db.users.update_one({"user_id": user_id}, {"$set": {
                "inner_circle": True, "tier": "archangel", "tier_until": None, "tier_paid_with": "inner_circle"}})
            await db.inner_circle.update_one({"email": email.lower()},
                                             {"$set": {"linked_user_id": user_id, "linked_did": did}},
                                             upsert=True)
        user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})

    await db.user_sessions.insert_one({
        "session_token": session_token,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
    })
    # Social 2FA — guardian push-handshake on every new login (SAFE, non-blocking)
    try:
        from routes.recovery_suite import notify_login_handshake
        await notify_login_handshake(user_doc, session_token)
    except Exception as e:
        logger.warning(f"social 2fa handshake: {e}")
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


# --------- FOUNDER / DEV BYPASS ---------
# Guardian Angel's canonical sovereign email. First login with this email is
# auto-provisioned as the Foundation founder (inner_circle=true, tier=archangel).
FOUNDER_EMAIL = os.environ.get("FOUNDER_EMAIL", "guardian.angel.core@proton.me").lower()


async def _ensure_founder_whitelist():
    """Idempotent seed: keep the Founder email permanently on the Inner-Circle whitelist."""
    try:
        await db.inner_circle.update_one(
            {"email": FOUNDER_EMAIL},
            {"$setOnInsert": {"email": FOUNDER_EMAIL, "note": "founder-auto-provision",
                              "added_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
    except Exception as e:
        logger.warning(f"founder whitelist seed: {e}")


async def _provision_user(email: str, name: Optional[str] = None, picture: Optional[str] = None) -> dict:
    """Fetch-or-create a user, apply Inner-Circle upgrade if whitelisted."""
    email_l = email.strip().lower()
    existing = await db.users.find_one({"email": email_l}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        if name or picture:
            await db.users.update_one({"user_id": user_id},
                                      {"$set": {k: v for k, v in {"name": name, "picture": picture}.items() if v}})
        return await db.users.find_one({"user_id": user_id}, {"_id": 0})
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    did = f"did:guardian:{uuid.uuid4().hex[:24]}"
    doc = User(user_id=user_id, email=email_l, name=name or "Guardian Angel",
               picture=picture, did=did).model_dump()
    await db.users.insert_one(doc.copy())
    wl = await db.inner_circle.find_one({"email": email_l})
    if wl or email_l == FOUNDER_EMAIL:
        await db.users.update_one({"user_id": user_id}, {"$set": {
            "inner_circle": True, "tier": "archangel", "tier_until": None,
            "tier_paid_with": "inner_circle", "tos_accepted_version": "2026-06.1"}})
        await db.inner_circle.update_one({"email": email_l},
                                         {"$set": {"linked_user_id": user_id, "linked_did": did}},
                                         upsert=True)
    return await db.users.find_one({"user_id": user_id}, {"_id": 0})


class DevBypassIn(BaseModel):
    email: str
    name: Optional[str] = None


@api.post("/auth/dev-bypass")
async def auth_dev_bypass(body: DevBypassIn):
    """SOVEREIGN BYPASS — creates a Guardian session without Google OAuth.

    Always allowed for the Founder email (guardian.angel.core@proton.me).
    Also allowed for any email when DEV_BYPASS_ENABLED=true (preview builds).
    Returns the same shape as /auth/session for a drop-in on the login screen."""
    email_l = body.email.strip().lower()
    if not email_l or "@" not in email_l:
        raise HTTPException(400, "invalid email")
    dev_enabled = os.environ.get("DEV_BYPASS_ENABLED", "true").lower() in ("1", "true", "yes")
    if email_l != FOUNDER_EMAIL and not dev_enabled:
        raise HTTPException(403, "dev bypass disabled — use Google Sign-In")
    await _ensure_founder_whitelist()
    user_doc = await _provision_user(email_l, body.name)
    session_token = f"gs-{uuid.uuid4().hex}"
    await db.user_sessions.insert_one({
        "session_token": session_token,
        "user_id": user_doc["user_id"],
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
        "via": "dev_bypass",
    })
    return {"session_token": session_token, "user": clean(user_doc)}


# --------- CLASSIC EMAIL / PASSWORD AUTH ---------
# Playbook-compliant: bcrypt (threadpool), 72-byte limit, timing-safe dummy check,
# generic errors (no account enumeration), opaque session tokens in user_sessions
# (same contract as Google OAuth + dev-bypass — get_current_user needs no changes).
import bcrypt as _bcrypt
from pymongo.errors import DuplicateKeyError

_BCRYPT_ROUNDS = 12
_DUMMY_HASH = _bcrypt.hashpw(b"dummy-password", _bcrypt.gensalt(_BCRYPT_ROUNDS))
_PASSWORD_SESSION_DAYS = 30


class RegisterIn(BaseModel):
    email: str
    password: str = Field(min_length=12, max_length=72)
    name: Optional[str] = None


class LoginIn(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=72)


def _validate_password_bytes(password: str):
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(422, "password must be at most 72 UTF-8 bytes")


async def _hash_password(password: str) -> str:
    hashed = await run_in_threadpool(_bcrypt.hashpw, password.encode("utf-8"), _bcrypt.gensalt(_BCRYPT_ROUNDS))
    return hashed.decode("utf-8")


async def _verify_password(password: str, stored_hash: Optional[str]) -> bool:
    candidate = stored_hash.encode("utf-8") if stored_hash else _DUMMY_HASH
    try:
        ok = await run_in_threadpool(_bcrypt.checkpw, password.encode("utf-8"), candidate)
    except (ValueError, TypeError):
        return False
    return ok and stored_hash is not None


async def _issue_password_session(user_doc: dict) -> dict:
    session_token = f"gs-{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc)
    await db.user_sessions.insert_one({
        "session_token": session_token,
        "user_id": user_doc["user_id"],
        "created_at": now,
        "expires_at": now + timedelta(days=_PASSWORD_SESSION_DAYS),
        "via": "password",
    })
    return {"session_token": session_token, "user": clean(user_doc)}


@api.post("/auth/register", status_code=201)
async def auth_register(body: RegisterIn):
    email_l = body.email.strip().casefold()
    if "@" not in email_l or "." not in email_l.split("@")[-1]:
        raise HTTPException(422, "invalid email")
    _validate_password_bytes(body.password)
    if await db.users.find_one({"email": email_l}, {"_id": 1}):
        raise HTTPException(409, "Unable to create account")
    password_hash = await _hash_password(body.password)
    await _ensure_founder_whitelist()
    try:
        user_doc = await _provision_user(email_l, body.name)
    except DuplicateKeyError:
        raise HTTPException(409, "Unable to create account")
    await db.users.update_one({"user_id": user_doc["user_id"]},
                              {"$set": {"password_hash": password_hash,
                                        "auth_providers": ["password"]}})
    user_doc = await db.users.find_one({"user_id": user_doc["user_id"]}, {"_id": 0})
    user_doc.pop("password_hash", None)
    return await _issue_password_session(user_doc)


@api.post("/auth/login")
async def auth_login(body: LoginIn):
    email_l = body.email.strip().casefold()
    _validate_password_bytes(body.password)
    user = await db.users.find_one({"email": email_l}, {"_id": 0})
    ok = await _verify_password(body.password, user.get("password_hash") if user else None)
    if not user or not ok:
        # Same generic message for unknown email and wrong password (no enumeration).
        raise HTTPException(401, "Incorrect email or password")
    user.pop("password_hash", None)
    return await _issue_password_session(user)


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
    # Sentient UX preferences (biometrics, wake-word, life-cycle age tracking)
    birth_year: Optional[int] = None  # 1900..2030 for Bio-Timeline (infant→senior)
    biometric_enabled: Optional[bool] = None  # FaceID/Fingerprint gate on app open
    wake_word_enabled: Optional[bool] = None  # Alexa-style "JARVIS" always-listening
    onboarding_completed: Optional[bool] = None  # 30-second Sovereign Tour played once

@api.patch("/me/prefs")
async def update_prefs(body: PrefIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if "birth_year" in upd:
        by = int(upd["birth_year"])
        if by < 1900 or by > 2030:
            from fastapi import HTTPException
            raise HTTPException(400, "birth_year must be between 1900 and 2030")
        upd["birth_year"] = by
    if upd:
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": upd})
    return clean(await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0}))


# --------- ACCOUNT DELETION (App Store requirement) ---------
USER_DATA_COLLECTIONS = [
    "documents", "waitlist", "emergency_profiles", "fall_events",
    "wellness_checkins", "wellness_vitals", "inactivity_alerts",
    "cabinet_items", "cabinet_exchange", "proxy_directives",
    "market_services", "scam_checks", "survival_items", "barter_offers",
    "beacon_events", "med_reminders", "med_intakes",
    "dignity_funds", "dignity_contributions", "dignity_wishes",
    "legal_testaments", "campaigns", "provider_reviews",
    "legacy_videos", "wealth_assets", "wealth_anchors", "wealth_payouts",
    "arbitrage_quotes", "bio_identity", "duress_configs", "duress_events",
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

