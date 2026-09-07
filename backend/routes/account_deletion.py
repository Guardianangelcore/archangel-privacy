# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
"""PUBLIC ACCOUNT-DELETION REQUESTS — Google Play "Data deletion" URL / Apple guideline 5.1.1(v).

The in-app path (Profile → Delete account → DELETE /auth/account) erases the account immediately.
Store policy additionally requires a web page reachable WITHOUT signing in where a user can request
deletion: the app's public route `/delete-account` posts here. Requests are queued for the Founder,
who executes them with the very same purge as the in-app deletion (routes.auth.purge_user_data).
Responses never reveal whether an account exists (no enumeration)."""
from fastapi import HTTPException, Header, Request
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone, timedelta
import hashlib
import re
import secrets
import uuid

from core import api, db, clean, get_current_user, rate_limit, client_ip, logger
from routes.auth import purge_user_data
from emailer import send_email, EMAIL_FROM_NAME

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
DEDUPE_HOURS = 24
CODE_TTL_MIN = 30
CODE_MAX_ATTEMPTS = 5
# What is erased vs. retained — shown on the public page and returned by GET /account/deletion-policy.
DELETION_POLICY = {
    "processing_days": 30,
    "erased": ["account & sign-in (e-mail, name, sessions)", "Life Card & health timeline", "vault documents & scans",
               "vitals, wellness check-ins, fall events", "medication cabinet & reminders", "family contacts & Guardian Circle",
               "waitlist, refunds, wealth vault entries", "GA-T wallet & Community Help history (personal fields)"],
    "retained": ["AML/audit ledger entries — cryptographic hashes only, no personal data (legal obligation)",
                 "counterparty records of completed trades/bookings/donations — user_id only, no personal payload",
                 "anonymised aggregate statistics"],
}


class DeletionRequestIn(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    reason: str = Field(default="", max_length=500)


class VerifyIn(BaseModel):
    code: str = Field(min_length=6, max_length=6)


def _code_hash(req_id: str, code: str) -> str:
    return hashlib.sha256(f"{req_id}:{code}".encode()).hexdigest()


def _code_email_html(code: str) -> str:
    # Fixed server-side template — no links, no forms, just the one-time code.
    return (
        '<table role="presentation" width="100%"><tr><td '
        'style="padding:24px;font-family:Arial,sans-serif;color:#1a1a1a">'
        '<h2 style="margin:0 0 12px 0">Account deletion request</h2>'
        '<p>Someone asked us to delete the Archangel OS account for this e-mail address. '
        'If that was you, enter this one-time code on the deletion page to confirm ownership:</p>'
        f'<p style="font-size:30px;font-weight:bold;letter-spacing:6px;margin:16px 0">{code}</p>'
        f'<p>The code expires in {CODE_TTL_MIN} minutes. If you did not request this, ignore this e-mail — '
        'nothing is deleted without the code.</p>'
        '</td></tr></table>'
    )


def _public(req: dict) -> dict:
    return {"ok": True, "req_id": req["req_id"], "verify_required": True,
            "processing_days": DELETION_POLICY["processing_days"]}


@api.get("/account/deletion-policy")
async def deletion_policy():
    return DELETION_POLICY


@api.post("/account/deletion-request", status_code=202)
async def deletion_request(body: DeletionRequestIn, request: Request):
    """PUBLIC — no login. Queues a deletion request for the e-mail address and, when an account
    exists, e-mails a one-time code that proves ownership (no code → the Founder will not process it).
    The response is identical whether or not the account exists."""
    rate_limit(request, "deletion_request")
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "invalid_email")
    now = datetime.now(timezone.utc)
    dup = await db.deletion_requests.find_one(
        {"email": email, "status": "pending", "created_at": {"$gte": now - timedelta(hours=DEDUPE_HOURS)}},
        {"_id": 0, "req_id": 1})
    if dup:                                   # already queued — same generic answer, no new code
        return _public(dup)
    exists = bool(await db.users.find_one({"email": email}, {"_id": 1}))
    doc = {"req_id": uuid.uuid4().hex[:12], "email": email, "reason": body.reason.strip(), "status": "pending",
           "account_exists": exists, "verified": False, "attempts": 0, "ip": client_ip(request), "created_at": now}
    if exists:
        code = f"{secrets.randbelow(10**6):06d}"
        doc["code_hash"] = _code_hash(doc["req_id"], code)
        doc["code_expires_at"] = now + timedelta(minutes=CODE_TTL_MIN)
    await db.deletion_requests.insert_one(doc)
    if exists:
        try:
            await send_email(to=email, subject=f"{EMAIL_FROM_NAME} — account deletion code", html=_code_email_html(code))
        except Exception as e:                # e-mail outage must not reveal anything nor break the flow
            logger.error(f"deletion code e-mail failed for {email}: {e}")
    logger.info(f"account deletion requested for {email} (account_exists={exists})")
    return _public(doc)


@api.post("/account/deletion-request/{req_id}/verify")
async def deletion_request_verify(req_id: str, body: VerifyIn, request: Request):
    """PUBLIC — proves e-mail ownership with the one-time code. Generic 400 on any failure."""
    rate_limit(request, "deletion_verify")
    now = datetime.now(timezone.utc)
    req = await db.deletion_requests.find_one({"req_id": req_id, "status": "pending"}, {"_id": 0})
    if not req or req.get("verified"):
        raise HTTPException(400, "invalid_code")
    exp = req.get("code_expires_at")
    if exp is not None and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if not req.get("code_hash") or req.get("attempts", 0) >= CODE_MAX_ATTEMPTS or not exp or exp < now:
        raise HTTPException(400, "invalid_code")
    if not secrets.compare_digest(req["code_hash"], _code_hash(req_id, body.code.strip())):
        await db.deletion_requests.update_one({"req_id": req_id}, {"$inc": {"attempts": 1}})
        raise HTTPException(400, "invalid_code")
    await db.deletion_requests.update_one({"req_id": req_id}, {"$set": {"verified": True, "verified_at": now},
                                                               "$unset": {"code_hash": ""}})
    return {"ok": True, "verified": True, "processing_days": DELETION_POLICY["processing_days"]}


async def _founder(authorization: Optional[str]) -> dict:
    user = await get_current_user(authorization)
    from routes.subscription import _is_founder
    if not await _is_founder(user):
        raise HTTPException(403, "founder_only")
    return user


@api.get("/account/deletion-requests")
async def deletion_requests_list(status: str = "pending", authorization: Optional[str] = Header(None)):
    """FOUNDER — queue of public deletion requests (status=pending|done|rejected|all). `verified` = e-mail ownership proven."""
    await _founder(authorization)
    q = {} if status == "all" else {"status": status}
    rows = await db.deletion_requests.find(q, {"_id": 0, "code_hash": 0}).sort("created_at", -1).to_list(200)
    return {"requests": [clean(r) for r in rows], "pending": await db.deletion_requests.count_documents({"status": "pending"})}


@api.post("/account/deletion-requests/{req_id}/process")
async def deletion_request_process(req_id: str, force: bool = False, authorization: Optional[str] = Header(None)):
    """FOUNDER — erase the matching account (if any) with the standard purge and close the request.
    Refused while e-mail ownership is unproven (`verified` false) unless `force=true` (support-verified case)."""
    founder = await _founder(authorization)
    req = await db.deletion_requests.find_one({"req_id": req_id}, {"_id": 0})
    if not req:
        raise HTTPException(404, "request not found")
    if req["status"] != "pending":
        raise HTTPException(409, f"request already {req['status']}")
    if req.get("account_exists") and not req.get("verified") and not force:
        raise HTTPException(412, "unverified: the requester has not confirmed the e-mail code — use force=true only after verifying identity another way")
    target = await db.users.find_one({"email": req["email"]}, {"_id": 0, "user_id": 1, "is_founder": 1})
    removed, purged = 0, False
    if target and not target.get("is_founder"):
        removed = await purge_user_data(target["user_id"])
        purged = True
    await db.deletion_requests.update_one({"req_id": req_id}, {"$set": {
        "status": "done", "processed_at": datetime.now(timezone.utc), "processed_by": founder["user_id"],
        "forced": bool(force and not req.get("verified")), "account_purged": purged, "records_removed": removed}})
    return {"ok": True, "account_purged": purged, "records_removed": removed}


@api.post("/account/deletion-requests/{req_id}/reject")
async def deletion_request_reject(req_id: str, authorization: Optional[str] = Header(None)):
    founder = await _founder(authorization)
    res = await db.deletion_requests.update_one({"req_id": req_id, "status": "pending"}, {"$set": {
        "status": "rejected", "processed_at": datetime.now(timezone.utc), "processed_by": founder["user_id"]}})
    if res.modified_count == 0:
        raise HTTPException(409, "request is not pending")
    return {"ok": True}
