# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""LIQUIDITY & SETTLEMENT ENGINE — the functional bank of the Monolith.

Bank-grade shape: double-entry ledger, idempotent payout state machine
(initiated → authorized → settled | failed), fees, FX with margin, and
Data-Backed Credit. Card rails run through a swappable adapter — the
SimulatedRails adapter is replaced by Visa Direct / Mastercard Send the day
institutional keys are connected (RAILS_MODE env)."""
from fastapi import HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import uuid, os, hashlib

from core import api, db, clean, get_current_user, logger, _aml_ledger_append

RAILS_MODE = os.environ.get("RAILS_MODE", "simulation")
FEE_PCT = 0.012          # 1.2 %
FEE_FIXED = 0.25         # € per payout
FEE_MIN = 0.50
FX_MARGIN = 0.006        # 0.6 %
FX_EUR = {"EUR": 1.0, "USD": 1.09, "CZK": 25.2, "GBP": 0.85, "CHF": 0.94,
          "PLN": 4.30, "HUF": 395.0, "UAH": 45.1, "JPY": 168.0}
DEMO_OPENING_BALANCE = 500.0
PAYOUT_LIMIT_EUR = 10000.0


# ---------------------------------------------------------------- rails adapter
class RailsAdapter:
    """Swappable card-rails interface (Visa Direct / Mastercard Send shape)."""
    name = "abstract"

    async def authorize(self, payout: dict) -> dict:
        raise NotImplementedError

    async def settle(self, payout: dict) -> dict:
        raise NotImplementedError


class SimulatedRails(RailsAdapter):
    """Production-shaped simulation — deterministic approvals, network refs.
    Replace with VisaDirectRails/MastercardSendRails once institutional keys exist."""
    name = "simulated_rails_v1"

    async def authorize(self, payout: dict) -> dict:
        if payout["amount_eur"] > PAYOUT_LIMIT_EUR:
            return {"approved": False, "reason": "amount_over_network_limit"}
        ref = "AUTH-" + hashlib.sha256(payout["payout_id"].encode()).hexdigest()[:12].upper()
        return {"approved": True, "network_ref": ref,
                "network": payout["network"], "latency_ms": 142}

    async def settle(self, payout: dict) -> dict:
        trace = "STL-" + hashlib.sha256((payout["payout_id"] + "s").encode()).hexdigest()[:12].upper()
        return {"settled": True, "trace_id": trace, "latency_ms": 388}


_rails: RailsAdapter = SimulatedRails()


# ---------------------------------------------------------------- ledger core
async def _post_ledger(tx_id: str, entries: list):
    """Double-entry: sum(debits) must equal sum(credits) — enforced."""
    debits = round(sum(e["amount_eur"] for e in entries if e["side"] == "debit"), 2)
    credits = round(sum(e["amount_eur"] for e in entries if e["side"] == "credit"), 2)
    if debits != credits:
        raise HTTPException(500, f"Ledger imbalance: D{debits} != C{credits}")
    now = datetime.now(timezone.utc)
    await db.ledger_entries.insert_many([
        {"entry_id": uuid.uuid4().hex, "tx_id": tx_id, "account": e["account"],
         "side": e["side"], "amount_eur": round(e["amount_eur"], 2),
         "memo": e.get("memo", ""), "at": now}
        for e in entries])


async def _balance(uid: str) -> dict:
    bal = await db.liq_balances.find_one({"user_id": uid}, {"_id": 0})
    if not bal:
        bal = {"user_id": uid, "available_eur": DEMO_OPENING_BALANCE,
               "currency": "EUR", "opened_at": datetime.now(timezone.utc)}
        await db.liq_balances.insert_one(bal.copy())
        await _post_ledger(f"open-{uid[:12]}", [
            {"account": "treasury_demo", "side": "debit", "amount_eur": DEMO_OPENING_BALANCE, "memo": "opening grant"},
            {"account": f"user:{uid}", "side": "credit", "amount_eur": DEMO_OPENING_BALANCE, "memo": "opening balance"},
        ])
    return bal


def _fees(amount_eur: float) -> float:
    return round(max(FEE_MIN, amount_eur * FEE_PCT + FEE_FIXED), 2)


def _fx(amount: float, currency: str) -> dict:
    if currency not in FX_EUR:
        raise HTTPException(400, f"currency must be one of {list(FX_EUR.keys())}")
    rate = FX_EUR[currency]
    eff = rate * (1 - FX_MARGIN) if currency != "EUR" else 1.0
    return {"rate": rate, "effective_rate": round(eff, 6),
            "amount_eur": round(amount / eff, 2) if currency != "EUR" else round(amount, 2)}


# ---------------------------------------------------------------- payout API
class PayoutIn(BaseModel):
    amount: float = Field(gt=0)
    currency: str = "EUR"
    card_last4: str = Field(min_length=4, max_length=4)
    network: str = "visa"          # visa → Visa Direct · mc → Mastercard Send
    idempotency_key: Optional[str] = None


@api.post("/liquidity/payout")
async def liquidity_payout(body: PayoutIn,
                           authorization: Optional[str] = Header(None),
                           idempotency_key: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    if body.network not in ("visa", "mc"):
        raise HTTPException(400, "network must be visa|mc")
    if not body.card_last4.isdigit():
        raise HTTPException(400, "card_last4 must be 4 digits")
    idem = body.idempotency_key or idempotency_key
    if not idem:
        raise HTTPException(400, "Idempotency-Key required (header or body)")
    existing = await db.payouts.find_one({"user_id": uid, "idempotency_key": idem}, {"_id": 0})
    if existing:
        return {"payout": clean(existing), "duplicate": True}
    fx = _fx(body.amount, body.currency.upper())
    amount_eur = fx["amount_eur"]
    fee = _fees(amount_eur)
    bal = await _balance(uid)
    if bal["available_eur"] < amount_eur + fee:
        raise HTTPException(400, f"insufficient_funds: available {bal['available_eur']} €, need {round(amount_eur + fee, 2)} €")
    now = datetime.now(timezone.utc)
    payout = {
        "payout_id": f"po_{uuid.uuid4().hex[:16]}", "user_id": uid,
        "idempotency_key": idem, "network": body.network, "card_last4": body.card_last4,
        "amount": round(body.amount, 2), "currency": body.currency.upper(),
        "amount_eur": amount_eur, "fee_eur": fee, "fx": fx,
        "rails_mode": RAILS_MODE, "rails_adapter": _rails.name,
        "state": "initiated", "timeline": [{"state": "initiated", "at": now}],
    }
    await db.payouts.insert_one(payout.copy())
    # 1) authorize on rails
    auth = await _rails.authorize(payout)
    if not auth.get("approved"):
        await db.payouts.update_one({"payout_id": payout["payout_id"]}, {"$set": {
            "state": "failed", "fail_reason": auth.get("reason")},
            "$push": {"timeline": {"state": "failed", "at": datetime.now(timezone.utc)}}})
        raise HTTPException(402, f"rails_declined: {auth.get('reason')}")
    await db.payouts.update_one({"payout_id": payout["payout_id"]}, {"$set": {
        "state": "authorized", "network_ref": auth["network_ref"]},
        "$push": {"timeline": {"state": "authorized", "at": datetime.now(timezone.utc)}}})
    # 2) settle + move money (double-entry)
    stl = await _rails.settle(payout)
    total_debit = round(amount_eur + fee, 2)
    await db.liq_balances.update_one({"user_id": uid}, {"$inc": {"available_eur": -total_debit}})
    await _post_ledger(payout["payout_id"], [
        {"account": f"user:{uid}", "side": "debit", "amount_eur": total_debit, "memo": f"payout {body.network} ****{body.card_last4}"},
        {"account": "rails_clearing", "side": "credit", "amount_eur": amount_eur, "memo": stl["trace_id"]},
        {"account": "fees_revenue", "side": "credit", "amount_eur": fee, "memo": "payout fee"},
    ])
    await db.payouts.update_one({"payout_id": payout["payout_id"]}, {"$set": {
        "state": "settled", "trace_id": stl["trace_id"], "settled_at": datetime.now(timezone.utc)},
        "$push": {"timeline": {"state": "settled", "at": datetime.now(timezone.utc)}}})
    await _aml_ledger_append(uid, "instant_card_payout", {
        "payout_id": payout["payout_id"], "amount_eur": amount_eur, "network": body.network})
    final = await db.payouts.find_one({"payout_id": payout["payout_id"]}, {"_id": 0})
    logger.info(f"Payout settled {payout['payout_id']} {amount_eur}€ via {body.network}")
    return {"payout": clean(final), "duplicate": False}


@api.get("/liquidity/balance")
async def liquidity_balance(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    bal = await _balance(user["user_id"])
    credit = await db.credit_lines.find_one({"user_id": user["user_id"], "status": "active"}, {"_id": 0})
    return {"balance": clean(bal), "rails_mode": RAILS_MODE, "adapter": _rails.name,
            "credit_line": clean(credit) if credit else None}


@api.get("/liquidity/payouts")
async def liquidity_payouts(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.payouts.find({"user_id": user["user_id"]}, {"_id": 0}).sort("timeline.0.at", -1).to_list(25)
    return {"payouts": clean(rows)}


@api.get("/liquidity/ledger")
async def liquidity_ledger(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.ledger_entries.find(
        {"account": f"user:{user['user_id']}"}, {"_id": 0}).sort("at", -1).to_list(50)
    return {"entries": clean(rows)}


# ---------------------------------------------------------------- data-backed credit
@api.post("/liquidity/credit/score")
async def credit_score(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    docs = await db.documents.count_documents({"user_id": uid})
    scans = await db.bioscan_results.count_documents({"user_id": uid})
    mems = await db.agent_memories.count_documents({"user_id": uid})
    deals = await db.data_deals.count_documents({"user_id": uid})
    wallet = await db.token_wallets.find_one({"user_id": uid}, {"_id": 0}) or {}
    gat = float(wallet.get("balance", 0))
    limit = round(min(5000.0, 100 + docs * 15 + scans * 5 + mems * 2 + deals * 25 + gat * 0.5), 2)
    score = {"user_id": uid, "limit_eur": limit, "apr_pct": 9.9,
             "collateral": {"documents": docs, "bioscans": scans, "memories": mems,
                            "data_deals": deals, "gat_balance": gat},
             "basis": "Data-Backed Credit — limit derived from sovereign data wealth, not from credit bureaus.",
             "at": datetime.now(timezone.utc)}
    await db.credit_scores.update_one({"user_id": uid}, {"$set": score}, upsert=True)
    return clean(score)


class CreditDrawIn(BaseModel):
    amount: float = Field(gt=0)


@api.post("/liquidity/credit/draw")
async def credit_draw(body: CreditDrawIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    score = await db.credit_scores.find_one({"user_id": uid}, {"_id": 0})
    if not score:
        raise HTTPException(400, "Run /liquidity/credit/score first")
    line = await db.credit_lines.find_one({"user_id": uid, "status": "active"}, {"_id": 0})
    outstanding = float(line["outstanding_eur"]) if line else 0.0
    if outstanding + body.amount > score["limit_eur"]:
        raise HTTPException(400, f"limit_exceeded: limit {score['limit_eur']} €, outstanding {outstanding} €")
    amount = round(body.amount, 2)
    now = datetime.now(timezone.utc)
    if line:
        await db.credit_lines.update_one({"line_id": line["line_id"]},
                                         {"$inc": {"outstanding_eur": amount}, "$set": {"updated_at": now}})
        line_id = line["line_id"]
    else:
        line_id = f"cl_{uuid.uuid4().hex[:12]}"
        await db.credit_lines.insert_one({
            "line_id": line_id, "user_id": uid, "status": "active",
            "limit_eur": score["limit_eur"], "outstanding_eur": amount,
            "apr_pct": 9.9, "opened_at": now, "updated_at": now})
    await _balance(uid)
    await db.liq_balances.update_one({"user_id": uid}, {"$inc": {"available_eur": amount}})
    await _post_ledger(f"draw-{uuid.uuid4().hex[:10]}", [
        {"account": "credit_book", "side": "debit", "amount_eur": amount, "memo": f"draw {line_id}"},
        {"account": f"user:{uid}", "side": "credit", "amount_eur": amount, "memo": "data-backed credit draw"},
    ])
    fresh = await db.credit_lines.find_one({"line_id": line_id}, {"_id": 0})
    return {"credit_line": clean(fresh), "drawn_eur": amount}
