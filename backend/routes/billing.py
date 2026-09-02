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
import uuid
import hashlib
from fastapi import HTTPException, Header, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta

from core import api, db, clean, get_current_user, logger, _make_pdf, _pdf_footer, APP_NAME, put_object_sync, send_push
from routes.subscription import TIERS, record_revenue

from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionRequest,
)

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")

# Family pack — one payer unlocks Sentinel for themselves + up to 4 family guardians
FAMILY_PACK = {"monthly": 249.0, "annual": 2390.0, "max_members": 4}


def _packages() -> dict:
    """Fixed server-side price catalogue: {tier}_{billing} → EUR amount."""
    out = {}
    for tier in ("guardian", "sentinel", "archangel"):
        out[f"{tier}_monthly"] = float(TIERS[tier]["price_eur"])
        out[f"{tier}_annual"] = float(TIERS[tier]["price_eur_year"])
    out["family_sentinel_monthly"] = FAMILY_PACK["monthly"]
    out["family_sentinel_annual"] = FAMILY_PACK["annual"]
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
    if body.tier not in ("guardian", "sentinel", "archangel", "family_sentinel"):
        raise HTTPException(400, "tier must be guardian|sentinel|archangel|family_sentinel")
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


async def _issue_receipt(tx: dict, tier_until: datetime, family_members: int = 0):
    """Payment receipt → PDF stored directly in the user's Health Vault + timeline."""
    try:
        label = ("Family plan — Sentinel for the whole family" if tx["tier"] == "family_sentinel"
                 else f"{tx['tier'].capitalize()} Tier")
        billing_sk = "annual subscription (−20%)" if tx["billing"] == "annual" else "monthly subscription"
        now = datetime.now(timezone.utc)
        body = (
            f"Receipt number: {tx['session_id']}\n"
            f"Payment date: {now.strftime('%d.%m.%Y %H:%M UTC')}\n\n"
            f"Item: {label} — {billing_sk}\n"
            f"Suma: {tx['amount_eur']:.2f} EUR\n"
            f"Payment method: Card (Stripe)\n"
            f"Valid until: {tier_until.strftime('%d.%m.%Y')}\n"
            + (f"Family circle members with Sentinel activated: {family_members}\n" if family_members else "")
            + "\nThank you for protecting yourself and your family with Archangel OS."
        )
        pdf = await run_in_threadpool(_make_pdf, "POTVRDENIE O PLATBE — ARCHANGEL OS", body, _pdf_footer())
        doc_id = uuid.uuid4().hex
        path = f"{APP_NAME}/uploads/{tx['user_id']}/{doc_id}.pdf"
        await run_in_threadpool(put_object_sync, path, pdf, "application/pdf")
        title = f"Doklad o platbe — {label}"
        await db.documents.insert_one({
            "doc_id": doc_id, "user_id": tx["user_id"], "title": title,
            "file_name": f"doklad_{tx['session_id'][:14]}.pdf", "content_type": "application/pdf",
            "size": len(pdf), "storage_path": path, "hash": hashlib.sha256(pdf).hexdigest(),
            "uploaded_at": now, "source": "billing_receipt",
        })
        await db.calendar_events.insert_one({
            "event_id": uuid.uuid4().hex, "user_id": tx["user_id"], "category": "history",
            "title": f"🧾 {title}"[:140], "date": now.date().isoformat(),
            "notes": f"{tx['amount_eur']:.2f} EUR · karta (Stripe)", "booster_due": None,
            "source": "billing", "doc_id": doc_id, "created_at": now,
        })
    except Exception as e:
        logger.warning(f"receipt issue failed (payment unaffected): {e}")


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
    until = now + timedelta(days=days)
    family_members = 0
    prev = await db.users.find_one({"user_id": res["user_id"]},
                                   {"_id": 0, "tier_until": 1, "tier_paid_with": 1, "gat_alloc_anchor": 1}) or {}
    if res["tier"] == "family_sentinel":
        # payer gets Sentinel + up to 4 family-circle guardians get it too (never downgrades Archangel/Inner Circle)
        await db.users.update_one(
            {"user_id": res["user_id"], "inner_circle": {"$ne": True}, "tier": {"$ne": "archangel"}},
            {"$set": {"tier": "sentinel", "tier_until": until, "tier_paid_with": "card",
                      "tier_billing": res["billing"]}})
        await db.users.update_one({"user_id": res["user_id"]}, {"$set": {"family_pack_owner": True}})
        guardians = await db.guardians.find(
            {"user_id": res["user_id"]}, {"_id": 0, "guardian_user_id": 1}).to_list(FAMILY_PACK["max_members"])
        member_ids = [g["guardian_user_id"] for g in guardians if g.get("guardian_user_id")]
        if member_ids:
            upd = await db.users.update_many(
                {"user_id": {"$in": member_ids}, "inner_circle": {"$ne": True}, "tier": {"$ne": "archangel"}},
                {"$set": {"tier": "sentinel", "tier_until": until,
                          "tier_paid_with": "family_pack", "tier_billing": res["billing"]}})
            family_members = upd.modified_count
        await db.payment_transactions.update_one(
            {"session_id": session_id}, {"$set": {"family_members_activated": family_members}})
    else:
        await db.users.update_one({"user_id": res["user_id"]}, {"$set": {
            "tier": res["tier"], "tier_until": until,
            "tier_paid_with": "card", "tier_billing": res["billing"]}})
    await record_revenue("subscription", res["amount_eur"], res["user_id"],
                         {"tier": res["tier"], "billing": res["billing"], "paid_with": "card",
                          "stripe_session": session_id, "family_members": family_members})
    # LOYALTY LOOP — fiat subscription → monthly GA-T allocation (first credit instantly).
    try:
        from routes.token import start_subscription_allocation
        alloc = await start_subscription_allocation(res["user_id"], prev)
        await db.payment_transactions.update_one(
            {"session_id": session_id}, {"$set": {"gat_allocated": alloc.get("credited_now", 0)}})
    except Exception as e:
        logger.warning(f"GA-T allocation on activation failed (payment unaffected): {e}")
    await _issue_receipt(res, until, family_members)
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


# ---------------- FOUNDER GIFTING — darovanie prémia ----------------
class GiftIn(BaseModel):
    email: str
    tier: str = "sentinel"   # guardian | sentinel | archangel
    days: int = 30
    note: str = ""


@api.post("/billing/gift")
async def billing_gift(body: GiftIn, authorization: Optional[str] = Header(None)):
    """Founder-only: gift a premium tier to any user by e-mail (free of charge)."""
    user = await get_current_user(authorization)
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "is_founder": 1})
    if not (fresh or {}).get("is_founder"):
        raise HTTPException(403, "founder_only: Only the founder can gift premium.")
    if body.tier not in ("guardian", "sentinel", "archangel"):
        raise HTTPException(400, "tier must be guardian|sentinel|archangel")
    days = max(1, min(3650, int(body.days)))
    email = body.email.strip().lower()
    target = await db.users.find_one({"email": email}, {"_id": 0, "user_id": 1, "email": 1, "inner_circle": 1, "name": 1})
    if not target:
        raise HTTPException(404, "user_not_found: No account exists for this e-mail yet.")
    if target.get("inner_circle"):
        raise HTTPException(409, "already_inner_circle: This user already has lifetime Archangel.")
    now = datetime.now(timezone.utc)
    until = now + timedelta(days=days)
    await db.users.update_one({"user_id": target["user_id"]}, {"$set": {
        "tier": body.tier, "tier_until": until,
        "tier_paid_with": "founder_gift", "tier_billing": "gift"}})
    gift = {"gift_id": uuid.uuid4().hex, "from_user_id": user["user_id"], "to_user_id": target["user_id"],
            "to_email": email, "tier": body.tier, "days": days, "note": body.note[:200],
            "tier_until": until, "created_at": now}
    await db.gifts.insert_one(gift.copy())
    try:
        await send_push([target["user_id"]],
                        {"title": "🎁 A gift from Guardian Angel",
                         "body": f"The founder gifted you {body.tier.upper()} for {days} days. Premium features are unlocked!"},
                        idempotency_key=f"gift-{gift['gift_id']}")
    except Exception:
        pass
    return {"ok": True, "gift": clean(gift)}


@api.get("/billing/gifts")
async def billing_gifts(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "is_founder": 1})
    if not (fresh or {}).get("is_founder"):
        raise HTTPException(403, "founder_only")
    rows = await db.gifts.find({}, {"_id": 0}).sort("created_at", -1).to_list(30)
    return clean(rows)
