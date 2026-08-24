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
import uuid, hashlib, json

from core import api, db, logger, clean, get_current_user

# ---------------- TOKENOMICS ----------------
TOTAL_SUPPLY = 100_000_000.0
FOUNDER_RESERVE = 25_000_000.0          # 25% — time-locked for the founder
FOUNDER_LOCK_YEARS = 4
BURN_RATE = 0.02                         # 2% of every spend is burned forever

EARN_RULES = {
    "proof_of_help":     {"amount": 10.0, "daily_max": 5,  "label": "Proof-of-Help — pomoc seniorovi (Family Shield)"},
    "proof_of_health":   {"amount": 5.0,  "daily_max": 10, "label": "Proof-of-Health — anonymný zdravotný insight"},
    "community_support": {"amount": 5.0,  "daily_max": 5,  "label": "Komunitná podpora (Solidarita / Barter)"},
}
SPEND_ITEMS = {
    "vip_sentinel_30d":    {"price": 100.0, "label": "VIP Sentinel tier (30 dní)"},
    "expert_consult":      {"price": 40.0,  "label": "Expert Marketplace — konzultácia"},
    "priority_hunter_7d":  {"price": 25.0,  "label": "Prioritný Waitlist Hunter (7 dní)"},
    "tier_guardian_30d":   {"price": 290.0,   "label": "Guardian Tier — 30 dní (GA-T)"},
    "tier_sentinel_30d":   {"price": 1490.0,  "label": "Sentinel Tier — 30 dní (GA-T)"},
    "tier_archangel_30d":  {"price": 4990.0,  "label": "Archangel Tier — 30 dní (GA-T)"},
    "tier_guardian_365d":  {"price": 2780.0,  "label": "Guardian Tier — ročne −20 % (GA-T)"},
    "tier_sentinel_365d":  {"price": 14300.0, "label": "Sentinel Tier — ročne −20 % (GA-T)"},
    "tier_archangel_365d": {"price": 47900.0, "label": "Archangel Tier — ročne −20 % (GA-T)"},
    "bioscan_single":      {"price": 5.0,  "label": "Vitals Bio-Scanner — 1 meranie"},
    "ips_export_single":   {"price": 10.0, "label": "IPS Export — 1 export (HL7 FHIR)"},
}

# ---------------- HASH-CHAINED LEDGER ----------------
async def _ledger_append(kind: str, account: str, amount: float, meta: dict) -> dict:
    last = await db.token_ledger.find_one({}, {"_id": 0, "entry_hash": 1, "seq": 1}, sort=[("seq", -1)])
    prev_hash = last["entry_hash"] if last else "gat-genesis"
    seq = (last["seq"] + 1) if last else 1
    body = json.dumps({"seq": seq, "kind": kind, "account": account, "amount": round(amount, 4),
                       "meta": meta, "prev": prev_hash}, sort_keys=True, default=str)
    entry_hash = hashlib.sha256(body.encode()).hexdigest()
    entry = {"seq": seq, "tx_id": uuid.uuid4().hex, "kind": kind, "account": account,
             "amount": round(amount, 4), "meta": meta, "prev_hash": prev_hash,
             "entry_hash": entry_hash, "at": datetime.now(timezone.utc)}
    await db.token_ledger.insert_one(entry.copy())
    return entry


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
    supply = await _get_supply()
    if supply["treasury"] < rule["amount"]:
        return None
    await db.token_supply.update_one({"key": "gat"},
                                     {"$inc": {"treasury": -rule["amount"], "circulating": rule["amount"]}})
    await db.token_accounts.update_one(
        {"user_id": user_id},
        {"$inc": {"balance": rule["amount"], "earned_total": rule["amount"]},
         "$set": {"updated_at": datetime.now(timezone.utc)}},
        upsert=True)
    tx = await _ledger_append("earn", user_id, rule["amount"], {"activity": activity, "note": note[:120]})
    return clean(tx)


# ---------------- API ----------------
class EarnIn(BaseModel):
    activity: str
    note: Optional[str] = ""

class SpendIn(BaseModel):
    item: str

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
    acct = await db.token_accounts.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    acct = {"balance": 0.0, "earned_total": 0.0, "spent_total": 0.0, **acct}
    txs = await db.token_ledger.find({"account": user["user_id"]}, {"_id": 0}).sort("seq", -1).to_list(20)
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "vip_until": 1, "hunter_priority_until": 1})
    return {**acct, "symbol": "GA-T",
            "vip_until": (fresh or {}).get("vip_until"),
            "hunter_priority_until": (fresh or {}).get("hunter_priority_until"),
            "txs": txs, "earn_rules": EARN_RULES, "spend_items": SPEND_ITEMS}

@api.post("/token/earn")
async def token_earn(body: EarnIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if body.activity not in EARN_RULES:
        raise HTTPException(400, f"activity must be one of {list(EARN_RULES)}")
    tx = await award_tokens(user["user_id"], body.activity, body.note or "manual claim")
    if not tx:
        raise HTTPException(429, "daily_limit: Denný limit pre túto aktivitu je vyčerpaný — skúste zajtra.")
    acct = await db.token_accounts.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return {"tx": tx, "balance": acct["balance"]}

@api.post("/token/spend")
async def token_spend(body: SpendIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    item = SPEND_ITEMS.get(body.item)
    if not item:
        raise HTTPException(400, f"item must be one of {list(SPEND_ITEMS)}")
    await _get_supply()
    acct = await db.token_accounts.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not acct or acct.get("balance", 0.0) < item["price"]:
        raise HTTPException(402, f"insufficient_balance: Potrebujete {item['price']} GA-T.")
    price = item["price"]
    burn = round(price * BURN_RATE, 4)
    now = datetime.now(timezone.utc)
    await db.token_accounts.update_one(
        {"user_id": user["user_id"]},
        {"$inc": {"balance": -price, "spent_total": price}, "$set": {"updated_at": now}})
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
