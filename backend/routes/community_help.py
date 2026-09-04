# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
"""GA-T COMMUNITY HELP — peer-to-peer VERIFIED Proof-of-Help.

Nobody can credit themselves any more. Flow:
  1. Requester posts a request → the 10 GA-T reward is RESERVED (escrow) from their wallet;
     whatever the wallet cannot cover is topped up from the Community Fund (treasury pool).
  2. A helper accepts → performs the help → marks it done (requester gets a push).
  3. Requester confirms "yes, they helped me" → escrow is paid out to the helper (ledger `help_reward`).
  4. Safety: max 5 requests/day and 5 confirmations/day per user; a done-but-unconfirmed request
     expires 24 h after completion (open ones after 7 days) and the escrow is refunded to where it came from.
"""
from fastapi import HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid

from core import api, db, logger, clean, get_current_user, send_push
from routes.token import _ledger_append, _get_supply, debit_balance

HELP_REWARD = 10.0
DAILY_MAX_REQUESTS = 5
DAILY_MAX_CONFIRMS = 5
CONFIRM_WINDOW_H = 24
OPEN_TTL_DAYS = 7
CATEGORIES = ("errand", "medication", "transport", "companionship", "household", "tech", "other")


def _now():
    return datetime.now(timezone.utc)


def _day_start():
    return _now().replace(hour=0, minute=0, second=0, microsecond=0)


async def _reserve(user_id: str, amount: float) -> dict:
    """Escrow `amount`: wallet first (atomic, never negative), Community Fund covers the rest."""
    acct = await db.token_accounts.find_one({"user_id": user_id}, {"_id": 0, "balance": 1}) or {}
    from_wallet = round(min(max(float(acct.get("balance", 0.0)), 0.0), amount), 4)
    if from_wallet > 0 and not await debit_balance(user_id, from_wallet):
        from_wallet = 0.0                                   # lost a race → fund covers everything
    from_fund = round(amount - from_wallet, 4)
    if from_fund > 0:
        await _get_supply()
        res = await db.token_supply.update_one({"key": "gat", "treasury": {"$gte": from_fund}},
                                               {"$inc": {"treasury": -from_fund, "community_escrow": from_fund}})
        if res.matched_count == 0:
            if from_wallet > 0:                              # roll back the wallet part
                await db.token_accounts.update_one({"user_id": user_id}, {"$inc": {"balance": from_wallet}})
            raise HTTPException(503, "community_fund_empty: the Community Fund cannot cover this reward right now")
    return {"wallet": from_wallet, "fund": from_fund}


async def _release(req: dict, to_helper: bool):
    """Pay the escrow to the helper (confirmed) or refund it (expired / cancelled)."""
    r = req["reserved"]
    total = round(r["wallet"] + r["fund"], 4)
    if to_helper:
        await db.token_accounts.update_one({"user_id": req["helper_id"]},
                                           {"$inc": {"balance": total, "earned_total": total, "help_total": total},
                                            "$set": {"updated_at": _now()}}, upsert=True)
        if r["fund"] > 0:
            await db.token_supply.update_one({"key": "gat"}, {"$inc": {"community_escrow": -r["fund"], "circulating": r["fund"]}})
        await _ledger_append("help_reward", req["helper_id"], total,
                             {"req_id": req["req_id"], "from": req["requester_id"], "wallet_part": r["wallet"], "fund_part": r["fund"]})
        return
    if r["wallet"] > 0:
        await db.token_accounts.update_one({"user_id": req["requester_id"]},
                                           {"$inc": {"balance": r["wallet"]}, "$set": {"updated_at": _now()}}, upsert=True)
    if r["fund"] > 0:
        await db.token_supply.update_one({"key": "gat"}, {"$inc": {"community_escrow": -r["fund"], "treasury": r["fund"]}})
    await _ledger_append("help_refund", req["requester_id"], r["wallet"],
                         {"req_id": req["req_id"], "fund_part": r["fund"], "reason": req.get("status")})


async def expire_help_requests() -> int:
    """Sweep: open > 7 d or done-but-unconfirmed > 24 h → expired + refund (idempotent via status flip)."""
    now = _now()
    n = 0
    async for req in db.help_requests.find({"status": {"$in": ["open", "accepted", "done"]}, "expires_at": {"$lte": now}}, {"_id": 0}):
        flip = await db.help_requests.update_one({"req_id": req["req_id"], "status": req["status"]},
                                                 {"$set": {"status": "expired", "expired_at": now}})
        if flip.modified_count:
            req["status"] = "expired"
            await _release(req, to_helper=False)
            n += 1
    if n:
        logger.info(f"community help: {n} request(s) expired and refunded")
    return n


async def _push(user_id: str, title: str, message: str, key: str):
    try:
        await send_push([user_id], {"title": title, "message": message, "action_url": "/community-help"}, idempotency_key=key)
    except Exception as e:
        logger.warning(f"help push skipped: {e}")


# HELPER REPUTATION — counts only help CONFIRMED by the requester (the peer-verified flow).
BADGES = (("gold", 20), ("silver", 5), ("bronze", 1))


def badge_for(completed: int) -> Optional[str]:
    for name, need in BADGES:
        if completed >= need:
            return name
    return None


async def helper_reputation(helper_ids: list) -> dict:
    ids = [h for h in set(helper_ids) if h]
    if not ids:
        return {}
    rows = await db.help_requests.aggregate([
        {"$match": {"helper_id": {"$in": ids}, "status": "confirmed"}},
        {"$group": {"_id": "$helper_id", "completed": {"$sum": 1}, "earned": {"$sum": {"$add": ["$reserved.wallet", "$reserved.fund"]}},
                    "last_at": {"$max": "$confirmed_at"}}},
    ]).to_list(len(ids))
    stats = {r["_id"]: r for r in rows}
    out = {}
    for h in ids:
        r = stats.get(h) or {}
        n = int(r.get("completed", 0))
        out[h] = {"completed": n, "badge": badge_for(n), "earned_gat": round(float(r.get("earned", 0.0)), 2),
                  "last_at": r["last_at"].isoformat() if r.get("last_at") else None,
                  "next_badge": next(({"badge": b, "need": need - n} for b, need in reversed(BADGES) if n < need), None)}
    return out


def _view(req: dict, uid: str, rep: Optional[dict] = None) -> dict:
    req = clean(req)
    req["mine"] = req["requester_id"] == uid
    req["helping"] = req.get("helper_id") == uid
    req["reward"] = round(req["reserved"]["wallet"] + req["reserved"]["fund"], 2)
    req["helper_reputation"] = (rep or {}).get(req.get("helper_id")) if req.get("helper_id") else None
    return req


# ---------------- API ----------------
class RequestIn(BaseModel):
    title: str = Field(min_length=3, max_length=80)
    details: str = Field(default="", max_length=400)
    category: str = "other"


@api.get("/help/requests")
async def help_list(scope: str = "open", authorization: Optional[str] = Header(None)):
    """scope=open (others' open requests) | mine (I asked) | helping (I accepted) | all"""
    user = await get_current_user(authorization)
    uid = user["user_id"]
    await expire_help_requests()
    if scope == "mine":
        q = {"requester_id": uid}
    elif scope == "helping":
        q = {"helper_id": uid}
    elif scope == "open":
        q = {"status": "open", "requester_id": {"$ne": uid}}
    else:
        q = {"$or": [{"requester_id": uid}, {"helper_id": uid}, {"status": "open"}]}
    rows = await db.help_requests.find(q, {"_id": 0}).sort("created_at", -1).to_list(100)
    rep = await helper_reputation([r.get("helper_id") for r in rows] + [uid])
    day = _day_start()
    made = await db.help_requests.count_documents({"requester_id": uid, "created_at": {"$gte": day}})
    confirmed = await db.help_requests.count_documents({"requester_id": uid, "confirmed_at": {"$gte": day}})
    supply = await _get_supply()
    return {"requests": [_view(r, uid, rep) for r in rows], "reward": HELP_REWARD, "my_reputation": rep.get(uid),
            "badges": {b: need for b, need in BADGES},
            "limits": {"requests_today": made, "confirms_today": confirmed, "daily_max": DAILY_MAX_REQUESTS},
            "community_fund": round(float(supply.get("treasury", 0.0)), 2), "categories": list(CATEGORIES)}


@api.get("/help/reputation/{user_id}")
async def help_reputation(user_id: str, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    rep = await helper_reputation([user_id])
    return {"user_id": user_id, **rep[user_id], "badges": {b: need for b, need in BADGES}}


@api.post("/help/requests", status_code=201)
async def help_create(body: RequestIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    if body.category not in CATEGORIES:
        raise HTTPException(400, f"category must be one of {list(CATEGORIES)}")
    made = await db.help_requests.count_documents({"requester_id": uid, "created_at": {"$gte": _day_start()}})
    if made >= DAILY_MAX_REQUESTS:
        raise HTTPException(429, f"daily_limit: max {DAILY_MAX_REQUESTS} help requests per day")
    reserved = await _reserve(uid, HELP_REWARD)
    now = _now()
    req = {"req_id": uuid.uuid4().hex[:16], "requester_id": uid, "requester_name": user.get("name") or "Guardian",
           "title": body.title.strip(), "details": body.details.strip(), "category": body.category,
           "reserved": reserved, "status": "open", "helper_id": None, "helper_name": None,
           "created_at": now, "expires_at": now + timedelta(days=OPEN_TTL_DAYS)}
    await db.help_requests.insert_one(req.copy())
    await _ledger_append("help_escrow", uid, -reserved["wallet"], {"req_id": req["req_id"], "fund_part": reserved["fund"]})
    return {"ok": True, "request": _view(req, uid)}


async def _load(req_id: str) -> dict:
    req = await db.help_requests.find_one({"req_id": req_id}, {"_id": 0})
    if not req:
        raise HTTPException(404, "request not found")
    return req


@api.post("/help/requests/{req_id}/accept")
async def help_accept(req_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    req = await _load(req_id)
    if req["requester_id"] == uid:
        raise HTTPException(400, "You cannot accept your own request")
    res = await db.help_requests.update_one({"req_id": req_id, "status": "open"},
                                            {"$set": {"status": "accepted", "helper_id": uid, "helper_name": user.get("name") or "Guardian",
                                                      "accepted_at": _now()}})
    if res.modified_count == 0:
        raise HTTPException(409, "This request was already taken")
    await _push(req["requester_id"], "🤝 Someone is coming to help", f"{user.get('name') or 'A Guardian'} accepted: {req['title']}", f"help-acc-{req_id}")
    return {"ok": True, "request": _view(await _load(req_id), uid, await helper_reputation([uid]))}


@api.post("/help/requests/{req_id}/done")
async def help_done(req_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    now = _now()
    res = await db.help_requests.update_one({"req_id": req_id, "status": "accepted", "helper_id": uid},
                                            {"$set": {"status": "done", "done_at": now, "expires_at": now + timedelta(hours=CONFIRM_WINDOW_H)}})
    if res.modified_count == 0:
        raise HTTPException(409, "Only the helper of an accepted request can mark it done")
    req = await _load(req_id)
    await _push(req["requester_id"], "✅ Did they help you?", f"Confirm '{req['title']}' within 24 h to release {HELP_REWARD:.0f} GA-T.", f"help-done-{req_id}")
    return {"ok": True, "request": _view(req, uid)}


@api.post("/help/requests/{req_id}/confirm")
async def help_confirm(req_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    req = await _load(req_id)
    if req["requester_id"] != uid:
        raise HTTPException(403, "Only the requester can confirm")
    confirmed = await db.help_requests.count_documents({"requester_id": uid, "confirmed_at": {"$gte": _day_start()}})
    if confirmed >= DAILY_MAX_CONFIRMS:
        raise HTTPException(429, f"daily_limit: max {DAILY_MAX_CONFIRMS} confirmations per day")
    res = await db.help_requests.update_one({"req_id": req_id, "status": "done"},
                                            {"$set": {"status": "confirmed", "confirmed_at": _now()}})
    if res.modified_count == 0:
        raise HTTPException(409, "Request is not awaiting confirmation")
    req = await _load(req_id)
    await _release(req, to_helper=True)
    await _push(req["helper_id"], "💎 Help confirmed", f"+{HELP_REWARD:.0f} GA-T for '{req['title']}' — thank you.", f"help-conf-{req_id}")
    return {"ok": True, "request": _view(req, uid, await helper_reputation([req["helper_id"]]))}


@api.post("/help/requests/{req_id}/cancel")
async def help_cancel(req_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    res = await db.help_requests.update_one({"req_id": req_id, "status": "open", "requester_id": uid},
                                            {"$set": {"status": "cancelled", "cancelled_at": _now()}})
    if res.modified_count == 0:
        raise HTTPException(409, "Only your own OPEN request can be cancelled")
    req = await _load(req_id)
    await _release(req, to_helper=False)
    return {"ok": True, "request": _view(req, uid)}
