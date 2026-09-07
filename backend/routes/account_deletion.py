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
import re
import uuid

from core import api, db, clean, get_current_user, rate_limit, client_ip, logger
from routes.auth import purge_user_data

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
DEDUPE_HOURS = 24
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


@api.get("/account/deletion-policy")
async def deletion_policy():
    return DELETION_POLICY


@api.post("/account/deletion-request", status_code=202)
async def deletion_request(body: DeletionRequestIn, request: Request):
    """PUBLIC — no login. Queues a deletion request for the e-mail address."""
    rate_limit(request, "deletion_request")
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "invalid_email")
    now = datetime.now(timezone.utc)
    dup = await db.deletion_requests.find_one(
        {"email": email, "status": "pending", "created_at": {"$gte": now - timedelta(hours=DEDUPE_HOURS)}},
        {"_id": 0, "req_id": 1})
    if dup:                                   # already queued — same generic answer, no new record
        return {"ok": True, "req_id": dup["req_id"], "processing_days": DELETION_POLICY["processing_days"]}
    exists = bool(await db.users.find_one({"email": email}, {"_id": 1}))
    doc = {"req_id": uuid.uuid4().hex[:12], "email": email, "reason": body.reason.strip(), "status": "pending",
           "account_exists": exists, "ip": client_ip(request), "created_at": now}
    await db.deletion_requests.insert_one(doc)
    logger.info(f"account deletion requested for {email} (account_exists={exists})")
    return {"ok": True, "req_id": doc["req_id"], "processing_days": DELETION_POLICY["processing_days"]}


async def _founder(authorization: Optional[str]) -> dict:
    user = await get_current_user(authorization)
    from routes.subscription import _is_founder
    if not await _is_founder(user):
        raise HTTPException(403, "founder_only")
    return user


@api.get("/account/deletion-requests")
async def deletion_requests_list(status: str = "pending", authorization: Optional[str] = Header(None)):
    """FOUNDER — queue of public deletion requests (status=pending|done|rejected|all)."""
    await _founder(authorization)
    q = {} if status == "all" else {"status": status}
    rows = await db.deletion_requests.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"requests": [clean(r) for r in rows], "pending": await db.deletion_requests.count_documents({"status": "pending"})}


@api.post("/account/deletion-requests/{req_id}/process")
async def deletion_request_process(req_id: str, authorization: Optional[str] = Header(None)):
    """FOUNDER — erase the matching account (if any) with the standard purge and close the request."""
    founder = await _founder(authorization)
    req = await db.deletion_requests.find_one({"req_id": req_id}, {"_id": 0})
    if not req:
        raise HTTPException(404, "request not found")
    if req["status"] != "pending":
        raise HTTPException(409, f"request already {req['status']}")
    target = await db.users.find_one({"email": req["email"]}, {"_id": 0, "user_id": 1, "is_founder": 1})
    removed, purged = 0, False
    if target and not target.get("is_founder"):
        removed = await purge_user_data(target["user_id"])
        purged = True
    await db.deletion_requests.update_one({"req_id": req_id}, {"$set": {
        "status": "done", "processed_at": datetime.now(timezone.utc), "processed_by": founder["user_id"],
        "account_purged": purged, "records_removed": removed}})
    return {"ok": True, "account_purged": purged, "records_removed": removed}


@api.post("/account/deletion-requests/{req_id}/reject")
async def deletion_request_reject(req_id: str, authorization: Optional[str] = Header(None)):
    founder = await _founder(authorization)
    res = await db.deletion_requests.update_one({"req_id": req_id, "status": "pending"}, {"$set": {
        "status": "rejected", "processed_at": datetime.now(timezone.utc), "processed_by": founder["user_id"]}})
    if res.modified_count == 0:
        raise HTTPException(409, "request is not pending")
    return {"ok": True}
