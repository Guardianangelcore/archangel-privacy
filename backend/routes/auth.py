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
        wl = await db.inner_circle.find_one({"email": email})
        if wl:
            await db.users.update_one({"user_id": user_id}, {"$set": {
                "inner_circle": True, "tier": "archangel", "tier_until": None, "tier_paid_with": "inner_circle"}})
            await db.inner_circle.update_one({"email": email}, {"$set": {"linked_user_id": user_id, "linked_did": did}})
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

