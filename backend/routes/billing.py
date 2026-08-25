# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""BILLING — real card payments via Stripe Checkout (emergentintegrations).

Security model per playbook:
- Prices are FIXED server-side (derived from subscription.TIERS) — the client
  only sends a tier + billing enum, never an amount.
- payment_transactions collection tracks every session; activation is
  idempotent (processed flag) and driven by Stripe's payment_status, polled
  via GET /billing/status/{session_id} and confirmed by POST /webhook/stripe.
"""
import os
from fastapi import HTTPException, Header, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta

from core import api, db, clean, get_current_user
from routes.subscription import TIERS, record_revenue

from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionRequest,
)

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")


def _packages() -> dict:
    """Fixed server-side price catalogue: {tier}_{billing} → EUR amount."""
    out = {}
    for tier in ("guardian", "sentinel", "archangel"):
        out[f"{tier}_monthly"] = float(TIERS[tier]["price_eur"])
        out[f"{tier}_annual"] = float(TIERS[tier]["price_eur_year"])
    return out


def _stripe(request: Request) -> StripeCheckout:
    if not STRIPE_API_KEY:
        raise HTTPException(503, "stripe_key_missing")
    host_url = str(request.base_url).rstrip("/")
    return StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=f"{host_url}/api/webhook/stripe")


class CheckoutIn(BaseModel):
    tier: str                  # guardian | sentinel | archangel
    billing: str = "monthly"   # monthly | annual
    origin_url: str            # frontend origin — success/cancel redirect base


@api.post("/billing/checkout")
async def billing_checkout(body: CheckoutIn, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if body.tier not in ("guardian", "sentinel", "archangel"):
        raise HTTPException(400, "tier must be guardian|sentinel|archangel")
    if body.billing not in ("monthly", "annual"):
        raise HTTPException(400, "billing must be monthly|annual")
    amount = _packages()[f"{body.tier}_{body.billing}"]
    origin = body.origin_url.rstrip("/")
    success_url = f"{origin}/subscription?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/subscription?payment=cancelled"
    stripe_checkout = _stripe(request)
    try:
        session = await stripe_checkout.create_checkout_session(CheckoutSessionRequest(
            amount=amount, currency="eur",
            success_url=success_url, cancel_url=cancel_url,
            metadata={"user_id": user["user_id"], "tier": body.tier, "billing": body.billing,
                      "source": "subscription_upgrade"},
        ))
    except Exception as e:
        raise HTTPException(502, f"stripe_error: {e}")
    now = datetime.now(timezone.utc)
    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "user_id": user["user_id"],
        "tier": body.tier, "billing": body.billing,
        "amount_eur": amount, "currency": "eur",
        "payment_status": "initiated", "processed": False,
        "created_at": now, "updated_at": now,
    })
    return {"checkout_url": session.url, "session_id": session.session_id,
            "amount_eur": amount, "tier": body.tier, "billing": body.billing}


async def _activate_tier(session_id: str) -> bool:
    """Idempotent fulfilment — activates the tier exactly once per paid session."""
    now = datetime.now(timezone.utc)
    res = await db.payment_transactions.find_one_and_update(
        {"session_id": session_id, "processed": {"$ne": True}},
        {"$set": {"processed": True, "payment_status": "paid", "paid_at": now, "updated_at": now}},
    )
    if not res:
        return False
    days = 365 if res["billing"] == "annual" else 30
    await db.users.update_one({"user_id": res["user_id"]}, {"$set": {
        "tier": res["tier"], "tier_until": now + timedelta(days=days),
        "tier_paid_with": "card", "tier_billing": res["billing"]}})
    await record_revenue("subscription", res["amount_eur"], res["user_id"],
                         {"tier": res["tier"], "billing": res["billing"], "paid_with": "card",
                          "stripe_session": session_id})
    return True


@api.get("/billing/status/{session_id}")
async def billing_status(session_id: str, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    tx = await db.payment_transactions.find_one({"session_id": session_id, "user_id": user["user_id"]}, {"_id": 0})
    if not tx:
        raise HTTPException(404, "transaction_not_found")
    if tx.get("processed"):
        return {"session_id": session_id, "status": "complete", "payment_status": "paid",
                "tier": tx["tier"], "billing": tx["billing"], "activated": True}
    stripe_checkout = _stripe(request)
    try:
        st = await stripe_checkout.get_checkout_status(session_id)
    except Exception as e:
        raise HTTPException(502, f"stripe_error: {e}")
    activated = False
    if st.payment_status == "paid":
        activated = await _activate_tier(session_id)
    elif st.status in ("expired",):
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": "expired", "updated_at": datetime.now(timezone.utc)}})
    return {"session_id": session_id, "status": st.status, "payment_status": st.payment_status,
            "tier": tx["tier"], "billing": tx["billing"], "activated": activated}


@api.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Authoritative fulfilment source — Stripe webhook (idempotent)."""
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature")
    stripe_checkout = _stripe(request)
    try:
        event = await stripe_checkout.handle_webhook(payload, signature)
    except Exception as e:
        raise HTTPException(400, f"webhook_error: {e}")
    if event.session_id and (event.payment_status == "paid"):
        await _activate_tier(event.session_id)
    return {"received": True, "event_type": event.event_type}


@api.get("/billing/transactions")
async def billing_transactions(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.payment_transactions.find(
        {"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(20)
    return clean(rows)
