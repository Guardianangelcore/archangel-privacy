# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""GA-T — Guardian Token Engine (internal utility-asset ledger).

Full internal token economy prepared for future on-chain (Layer-2) migration:
hash-chained ledger, genesis mint, 25% time-locked Founder's Reserve,
Proof-of-Help / Proof-of-Health earn rules, spend utilities and an
algorithmic burn on every spend (deflationary).
"""
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid, hashlib, json, asyncio

from core import api, db, logger, clean, get_current_user

# ---------------- TOKENOMICS ----------------
TOTAL_SUPPLY = 100_000_000.0
FOUNDER_RESERVE = 25_000_000.0          # 25% — time-locked for the founder
FOUNDER_LOCK_YEARS = 4
BURN_RATE = 0.02                         # 2% of every spend is burned forever

# SELF-CLAIM BLOCKED: help rewards are paid only through the peer-verified Community Help flow
# (routes/community_help.py — requester confirms, escrow released). No "I helped" button credits.
SELF_CLAIM_BLOCKED = {"proof_of_help", "community_support"}
EARN_RULES = {
    "proof_of_help":     {"amount": 10.0, "daily_max": 5,  "label": "Proof-of-Help — helping a senior (Family Shield)", "verified_only": True},
    "proof_of_health":   {"amount": 5.0,  "daily_max": 10, "label": "Proof-of-Health — anonymous health insight"},
    "community_support": {"amount": 5.0,  "daily_max": 5,  "label": "Community support (Solidarity / Barter)", "verified_only": True},
    "document_scan":     {"amount": 2.0,  "daily_max": 10, "label": "Document scan — Life Card enrichment (Magic Lens)"},
}
SPEND_ITEMS = {
    "vip_sentinel_30d":    {"price": 100.0, "label": "VIP Sentinel tier (30 days)"},
    "expert_consult":      {"price": 40.0,  "label": "Expert Marketplace — consultation"},
    "priority_hunter_7d":  {"price": 25.0,  "label": "Priority Waitlist Hunter (7 days)"},
    "tier_guardian_30d":   {"price": 15.0,    "label": "Guardian Tier — 30 days (GA-T)"},
    "tier_sentinel_30d":   {"price": 250.0,   "label": "Sentinel Tier — 30 days (GA-T)"},
    "tier_archangel_30d":  {"price": 800.0,   "label": "Archangel Tier — 30 days (GA-T)"},
    "tier_guardian_365d":  {"price": 144.0,   "label": "Guardian Tier — yearly −20% (GA-T)"},
    "tier_sentinel_365d":  {"price": 2400.0,  "label": "Sentinel Tier — yearly −20% (GA-T)"},
    "tier_archangel_365d": {"price": 7680.0,  "label": "Archangel Tier — yearly −20% (GA-T)"},
    "bioscan_single":      {"price": 5.0,  "label": "Vitals Bio-Scanner — 1 meranie"},
    "ips_export_single":   {"price": 10.0, "label": "IPS Export — 1 export (HL7 FHIR)"},
    "jarvis_query":        {"price": 0.5,  "label": "Jarvis Sovereign Search — 1 live web query"},
}

# ---------------- HASH-CHAINED LEDGER ----------------
async def _ledger_append(kind: str, account: str, amount: float, meta: dict) -> dict:
    """Append one hash-chained entry. The unique index on `seq` makes concurrent appends
    collide (DuplicateKeyError) — the loser simply re-reads the new head and retries."""
    from pymongo.errors import DuplicateKeyError
    for attempt in range(8):
        last = await db.token_ledger.find_one({}, {"_id": 0, "entry_hash": 1, "seq": 1}, sort=[("seq", -1)])
        prev_hash = last["entry_hash"] if last else "gat-genesis"
        seq = (last["seq"] + 1) if last else 1
        body = json.dumps({"seq": seq, "kind": kind, "account": account, "amount": round(amount, 4),
                           "meta": meta, "prev": prev_hash}, sort_keys=True, default=str)
        entry_hash = hashlib.sha256(body.encode()).hexdigest()
        entry = {"seq": seq, "tx_id": uuid.uuid4().hex, "kind": kind, "account": account,
                 "amount": round(amount, 4), "meta": meta, "prev_hash": prev_hash,
                 "entry_hash": entry_hash, "at": datetime.now(timezone.utc)}
        try:
            await db.token_ledger.insert_one(entry.copy())
            return entry
        except DuplicateKeyError:
            await asyncio.sleep(0.02 * (attempt + 1))
    raise RuntimeError("token_ledger append failed after concurrent retries")


async def verify_ledger_chain(limit: int = 5000) -> dict:
    rows = await db.token_ledger.find({}, {"_id": 0}).sort("seq", 1).to_list(limit)
    prev = "gat-genesis"
    for r in rows:
        body = json.dumps({"seq": r["seq"], "kind": r["kind"], "account": r["account"],
                           "amount": r["amount"], "meta": r["meta"], "prev": prev},
                          sort_keys=True, default=str)
        if hashlib.sha256(body.encode()).hexdigest() != r["entry_hash"] or r["prev_hash"] != prev:
            return {"intact": False, "broken_at_seq": r["seq"], "entries": len(rows)}
        prev = r["entry_hash"]
    return {"intact": True, "entries": len(rows)}


# ---------------- GENESIS ----------------
async def ensure_genesis():
    existing = await db.token_supply.find_one({"key": "gat"})
    if existing:
        return existing
    now = datetime.now(timezone.utc)
    supply = {
        "key": "gat", "symbol": "GA-T", "name": "Guardian Token",
        "chain": "internal-ledger (L2-ready)",
        "total_supply": TOTAL_SUPPLY,
        "treasury": TOTAL_SUPPLY - FOUNDER_RESERVE,
        "founder_reserve": FOUNDER_RESERVE,
        "founder_locked_until": now + timedelta(days=365 * FOUNDER_LOCK_YEARS),
        "circulating": 0.0, "burned": 0.0,
        "burn_rate": BURN_RATE, "created_at": now,
    }
    await db.token_supply.insert_one(supply.copy())
    await _ledger_append("genesis_mint", "treasury", TOTAL_SUPPLY - FOUNDER_RESERVE,
                         {"note": "GA-T genesis — treasury rewards pool (75%)"})
    await _ledger_append("reserve_lock", "founder", FOUNDER_RESERVE,
                         {"note": f"Founder's Reserve 25% time-locked {FOUNDER_LOCK_YEARS}y",
                          "locked_until": supply["founder_locked_until"].isoformat()})
    logger.info("GA-T genesis minted")
    return supply


async def _get_supply() -> dict:
    return await ensure_genesis()


async def debit_balance(user_id: str, amount: float, **inc_extra) -> bool:
    """ATOMIC GA-T debit — a single conditional update (`balance >= amount`) so concurrent
    spends can never drive a wallet below zero. Returns False when funds are insufficient."""
    if amount <= 0:
        return True
    res = await db.token_accounts.update_one(
        {"user_id": user_id, "balance": {"$gte": amount}},
        {"$inc": {"balance": -amount, **inc_extra}, "$set": {"updated_at": datetime.now(timezone.utc)}})
    return res.matched_count == 1


# ---------------- CORE OPERATIONS ----------------
async def award_tokens(user_id: str, activity: str, note: str = "") -> Optional[dict]:
    """Award GA-T for a verified activity. Returns tx or None when the daily cap is hit."""
    rule = EARN_RULES.get(activity)
    if not rule:
        return None
    day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today = await db.token_ledger.count_documents(
        {"kind": "earn", "account": user_id, "meta.activity": activity, "at": {"$gte": day_start}})
    if today >= rule["daily_max"]:
        return None
    await _get_supply()
    res = await db.token_supply.update_one({"key": "gat", "treasury": {"$gte": rule["amount"]}},
                                           {"$inc": {"treasury": -rule["amount"], "circulating": rule["amount"]}})
    if res.matched_count == 0:          # treasury exhausted — never mint from nothing
        return None
    await db.token_accounts.update_one(
        {"user_id": user_id},
        {"$inc": {"balance": rule["amount"], "earned_total": rule["amount"]},
         "$set": {"updated_at": datetime.now(timezone.utc)}},
        upsert=True)
    tx = await _ledger_append("earn", user_id, rule["amount"], {"activity": activity, "note": note[:120]})
    return clean(tx)


async def charge_tokens(user_id: str, item: str, note: str = "") -> Optional[dict]:
    """Soft-charge GA-T for a utility item (same burn mechanics as /token/spend).
    Returns the tx, or None when the balance is insufficient — NEVER raises,
    so core features keep working for users without tokens."""
    it = SPEND_ITEMS.get(item)
    if not it:
        return None
    if not await debit_balance(user_id, it["price"], spent_total=it["price"]):
        return None
    burn = round(it["price"] * BURN_RATE, 4)
    to_treasury = it["price"] - burn
    await db.token_supply.update_one({"key": "gat"},
                                     {"$inc": {"treasury": to_treasury,
                                               "circulating": -it["price"], "burned": burn}})
    tx = await _ledger_append("spend", user_id, it["price"],
                              {"item": item, "burned": burn, "note": note[:120]})
    return clean(tx)


# ---------------- API ----------------
class EarnIn(BaseModel):
    activity: str
    note: Optional[str] = ""

class SpendIn(BaseModel):
    item: str


# ---------------- SUBSCRIPTION LOYALTY ALLOCATION ----------------
# Paid (fiat) subscribers — card today, Apple/Google IAP when RevenueCat lands —
# automatically receive GA-T every 30 days while the subscription is active:
# pay fiat → premium features → tokens accrue. The longer you stay, the bigger the
# monthly credit (+10 % per consecutive month, capped at +50 %). Subscriptions paid
# WITH GA-T or trials never receive allocations (would be a circular mint).
SUBSCRIPTION_GAT = {"guardian": 100.0, "sentinel": 300.0, "archangel": 1000.0}
LOYALTY_BONUS_PER_MONTH = 0.10
LOYALTY_BONUS_CAP = 0.50
ALLOCATION_PERIOD_DAYS = 30
FIAT_SOURCES = ("card", "iap", "apple_iap", "google_iap", "family_pack")


def allocation_for(tier: str, month_index: int) -> dict:
    base = SUBSCRIPTION_GAT.get(tier, 0.0)
    bonus = min(LOYALTY_BONUS_CAP, LOYALTY_BONUS_PER_MONTH * max(0, month_index - 1))
    return {"amount": round(base * (1 + bonus), 2), "bonus_pct": int(round(bonus * 100)), "base": base}


def _as_utc(d):
    if d is None:
        return None
    if isinstance(d, str):
        d = datetime.fromisoformat(d.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


async def settle_subscription_allocations(user_id: str) -> dict:
    """Idempotently credit every 30-day allocation due since the paid subscription
    started (anchor). Runs lazily on wallet/subscription views, on activation and
    in the periodic sweep, so a renewal on ANY channel (Stripe, IAP) is honoured."""
    from routes.subscription import current_tier
    u = await db.users.find_one({"user_id": user_id}, {
        "_id": 0, "tier": 1, "tier_until": 1, "tier_paid_with": 1, "inner_circle": 1,
        "gat_alloc_anchor": 1, "gat_alloc_count": 1})
    if u is None:
        return {"eligible": False, "reason": "no_user",
                "monthly_amount": SUBSCRIPTION_GAT["guardian"]}
    tier = current_tier(u)
    paid_with = (u.get("tier_paid_with") or "").lower()
    if tier == "sovereign" or tier not in SUBSCRIPTION_GAT:
        return {"eligible": False, "reason": "no_active_subscription", "tier": tier,
                "monthly_amount": SUBSCRIPTION_GAT["guardian"]}
    if paid_with not in FIAT_SOURCES:
        return {"eligible": False, "reason": "paid_with_gat_or_trial", "tier": tier, "paid_with": paid_with,
                "monthly_amount": SUBSCRIPTION_GAT[tier]}
    now = datetime.now(timezone.utc)
    anchor = _as_utc(u.get("gat_alloc_anchor"))
    if not anchor:
        anchor = now
        await db.users.update_one({"user_id": user_id}, {"$set": {"gat_alloc_anchor": anchor, "gat_alloc_count": 0}})
    until = _as_utc(u.get("tier_until"))
    credited = int(u.get("gat_alloc_count") or 0)
    due = int((now - anchor).total_seconds() // (ALLOCATION_PERIOD_DAYS * 86400)) + 1
    credited_now, txs = 0, []
    for i in range(credited + 1, due + 1):
        period_start = anchor + timedelta(days=ALLOCATION_PERIOD_DAYS * (i - 1))
        if until and period_start > until:
            break
        dup = await db.token_ledger.find_one({"kind": "subscription_allocation", "account": user_id,
                                              "meta.anchor": anchor.isoformat(), "meta.period_index": i}, {"_id": 1})
        if dup:
            credited = i
            continue
        alloc = allocation_for(tier, i)
        supply = await _get_supply()
        if supply["treasury"] < alloc["amount"]:
            break
        await db.token_supply.update_one({"key": "gat"},
                                         {"$inc": {"treasury": -alloc["amount"], "circulating": alloc["amount"]}})
        await db.token_accounts.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": alloc["amount"], "earned_total": alloc["amount"], "subscription_total": alloc["amount"]},
             "$set": {"updated_at": now}}, upsert=True)
        tx = await _ledger_append("subscription_allocation", user_id, alloc["amount"], {
            "tier": tier, "paid_with": paid_with, "period_index": i, "anchor": anchor.isoformat(),
            "period_start": period_start.isoformat(), "bonus_pct": alloc["bonus_pct"],
            "note": f"Premium loyalty — month {i} ({tier}), +{alloc['bonus_pct']}% bonus"})
        txs.append(clean(tx))
        credited, credited_now = i, credited_now + 1
    if credited != int(u.get("gat_alloc_count") or 0):
        await db.users.update_one({"user_id": user_id}, {"$set": {"gat_alloc_count": credited}})
    next_at = anchor + timedelta(days=ALLOCATION_PERIOD_DAYS * credited)
    nxt = allocation_for(tier, credited + 1)
    return {"eligible": True, "tier": tier, "paid_with": paid_with,
            "months_collected": credited, "credited_now": credited_now, "credited_txs": txs,
            "next_at": next_at.isoformat() if (not until or next_at <= until) else None,
            "next_amount": nxt["amount"], "next_bonus_pct": nxt["bonus_pct"],
            "monthly_amount": SUBSCRIPTION_GAT[tier], "period_days": ALLOCATION_PERIOD_DAYS,
            "loyalty_bonus_per_month_pct": int(LOYALTY_BONUS_PER_MONTH * 100),
            "loyalty_bonus_cap_pct": int(LOYALTY_BONUS_CAP * 100)}


async def start_subscription_allocation(user_id: str, prev: Optional[dict] = None) -> dict:
    """Called on every fiat activation/renewal. Keeps the loyalty anchor (and the bonus
    streak) when the previous paid period is still active or lapsed < 7 days ago;
    otherwise the streak restarts. Then credits the first/next allocation immediately."""
    now = datetime.now(timezone.utc)
    prev = prev or {}
    prev_until = _as_utc(prev.get("tier_until"))
    keep = bool(prev.get("gat_alloc_anchor")) and (prev.get("tier_paid_with") or "").lower() in FIAT_SOURCES \
        and prev_until is not None and prev_until >= now - timedelta(days=7)
    if not keep:
        await db.users.update_one({"user_id": user_id}, {"$set": {"gat_alloc_anchor": now, "gat_alloc_count": 0}})
    return await settle_subscription_allocations(user_id)


_last_sweep: Optional[datetime] = None

async def sweep_subscription_allocations(every_hours: int = 6) -> int:
    """Periodic safety net (swarm loop): settle all fiat-paid subscribers so renewals
    are credited even if the user never opens the wallet."""
    global _last_sweep
    now = datetime.now(timezone.utc)
    if _last_sweep and (now - _last_sweep) < timedelta(hours=every_hours):
        return 0
    _last_sweep = now
    n = 0
    async for u in db.users.find({"tier": {"$in": list(SUBSCRIPTION_GAT)},
                                  "tier_paid_with": {"$in": list(FIAT_SOURCES)}}, {"_id": 0, "user_id": 1}):
        try:
            r = await settle_subscription_allocations(u["user_id"])
            n += r.get("credited_now", 0)
        except Exception as e:
            logger.warning(f"allocation sweep failed for {u['user_id']}: {e}")
    if n:
        logger.info(f"GA-T loyalty sweep credited {n} allocation(s)")
    return n

@api.get("/token/supply")
async def token_supply(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    s = clean(dict(await _get_supply()))
    s["burn_stats"] = {"burned": s["burned"], "burn_rate_pct": BURN_RATE * 100,
                       "deflationary": True}
    return s

@api.get("/token/wallet")
async def token_wallet(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await _get_supply()
    allocation = await settle_subscription_allocations(user["user_id"])   # lazy renewal credit
    acct = await db.token_accounts.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    acct = {"balance": 0.0, "earned_total": 0.0, "spent_total": 0.0, "subscription_total": 0.0, **acct}
    txs = await db.token_ledger.find({"account": user["user_id"]}, {"_id": 0}).sort("seq", -1).to_list(20)
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "vip_until": 1, "hunter_priority_until": 1})
    return {**acct, "symbol": "GA-T",
            "vip_until": (fresh or {}).get("vip_until"),
            "hunter_priority_until": (fresh or {}).get("hunter_priority_until"),
            "subscription_allocation": allocation,
            "txs": txs, "earn_rules": EARN_RULES, "spend_items": SPEND_ITEMS}

@api.post("/token/earn")
async def token_earn(body: EarnIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if body.activity not in EARN_RULES:
        raise HTTPException(400, f"activity must be one of {list(EARN_RULES)}")
    if body.activity in SELF_CLAIM_BLOCKED:
        raise HTTPException(403, "verified_only: help rewards are paid through Community Help — "
                                 "the person you helped must confirm it.")
    tx = await award_tokens(user["user_id"], body.activity, body.note or "manual claim")
    if not tx:
        raise HTTPException(429, "daily_limit: Daily limit for this activity reached — try again tomorrow.")
    acct = await db.token_accounts.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return {"tx": tx, "balance": acct["balance"]}

@api.post("/token/spend")
async def token_spend(body: SpendIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    item = SPEND_ITEMS.get(body.item)
    if not item:
        raise HTTPException(400, f"item must be one of {list(SPEND_ITEMS)}")
    await _get_supply()
    price = item["price"]
    burn = round(price * BURN_RATE, 4)
    now = datetime.now(timezone.utc)
    # ATOMIC debit first — nothing (royalty, effects, ledger) happens unless the wallet covered it.
    if not await debit_balance(user["user_id"], price, spent_total=price):
        raise HTTPException(402, f"insufficient_balance: You need {price} GA-T.")
    # CREATOR ROYALTY — 5 % of every GA-T sale goes to the Guardian Angel creator account
    try:
        from routes.features import creator_royalty
        await creator_royalty("gat_sale", price, "gat", user["user_id"], {"item": body.item})
    except Exception as _e:
        logger.warning(f"creator royalty skipped: {_e}")
    await db.token_supply.update_one(
        {"key": "gat"},
        {"$inc": {"circulating": -price, "burned": burn, "treasury": price - burn}})
    effect = {}
    if body.item == "vip_sentinel_30d":
        vip_until = now + timedelta(days=30)
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"vip_until": vip_until}})
        effect = {"vip_until": vip_until.isoformat()}
    elif body.item == "priority_hunter_7d":
        pri_until = now + timedelta(days=7)
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"hunter_priority_until": pri_until}})
        effect = {"hunter_priority_until": pri_until.isoformat()}
    elif body.item == "expert_consult":
        effect = {"consult_credit": True}
        await db.users.update_one({"user_id": user["user_id"]}, {"$inc": {"expert_credits": 1}})
    elif body.item.startswith("tier_"):
        _, tier, dur = body.item.split("_")
        days = 365 if dur == "365d" else 30
        tier_until = now + timedelta(days=days)
        await db.users.update_one({"user_id": user["user_id"]},
                                  {"$set": {"tier": tier, "tier_until": tier_until, "tier_paid_with": "GA-T"}})
        effect = {"tier": tier, "tier_until": tier_until.isoformat(), "days": days}
    elif body.item in ("bioscan_single", "ips_export_single"):
        effect = {"access": body.item}
    tx = await _ledger_append("spend", user["user_id"], -price,
                              {"item": body.item, "burned": burn, "effect": effect})
    await _ledger_append("burn", "burn-address", burn, {"source_tx": tx["tx_id"], "item": body.item})
    acct = await db.token_accounts.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return {"tx": clean(tx), "burned": burn, "effect": effect, "balance": acct["balance"]}

@api.get("/token/ledger")
async def token_ledger(limit: int = 50, verify: int = 0, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    rows = await db.token_ledger.find({}, {"_id": 0}).sort("seq", -1).to_list(min(limit, 200))
    out = {"entries": rows}
    if verify:
        out["chain"] = await verify_ledger_chain()
    return out
