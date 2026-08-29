# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import os, uuid, hashlib

from core import api, db, logger, clean, get_current_user

# =========================================================================
# GLOBAL INFRASTRUCTURE — Partner API Gateway · Data Marketplace · Sentinel Network · Stripe Onramp
# =========================================================================

# --------- 1. PARTNER API GATEWAY (user-consent scoped access for clinics/insurers/EMS) ---------
GATEWAY_SCOPES = ("emergency_profile", "vault_list", "recovery_status")

class GrantIn(BaseModel):
    partner_name: str
    scopes: List[str]
    expires_days: int = 30

@api.post("/gateway/grants")
async def gateway_grant_create(body: GrantIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    scopes = [s for s in body.scopes if s in GATEWAY_SCOPES]
    if not scopes or not body.partner_name.strip():
        raise HTTPException(400, f"partner_name and valid scopes required {GATEWAY_SCOPES}")
    if not 1 <= body.expires_days <= 365:
        raise HTTPException(400, "expires_days 1..365")
    token = f"gwk_{uuid.uuid4().hex}{uuid.uuid4().hex[:8]}"
    doc = {
        "grant_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "partner_name": body.partner_name.strip()[:80], "scopes": scopes,
        "token": token, "revoked": False,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=body.expires_days),
        "created_at": datetime.now(timezone.utc),
    }
    await db.gateway_grants.insert_one(doc.copy())
    return clean(doc)

@api.get("/gateway/grants")
async def gateway_grants(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    out = await db.gateway_grants.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)
    for g in out:
        g["token_preview"] = g["token"][:12] + "…"
    return out

@api.delete("/gateway/grants/{grant_id}")
async def gateway_grant_revoke(grant_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.gateway_grants.update_one({"grant_id": grant_id, "user_id": user["user_id"]}, {"$set": {"revoked": True}})
    if res.matched_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True, "revoked": True}

@api.get("/gateway/audit")
async def gateway_audit(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.gateway_audit.find({"user_id": user["user_id"]}, {"_id": 0}).sort("at", -1).to_list(100)

async def _partner_auth(x_partner_key: Optional[str], scope: str) -> dict:
    if not x_partner_key:
        raise HTTPException(401, "X-Partner-Key header required")
    g = await db.gateway_grants.find_one({"token": x_partner_key, "revoked": False}, {"_id": 0})
    if not g:
        raise HTTPException(403, "Invalid or revoked partner key")
    exp = g["expires_at"]
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < datetime.now(timezone.utc):
        raise HTTPException(403, "Partner key expired")
    if scope not in g["scopes"]:
        raise HTTPException(403, f"Scope '{scope}' not granted by user")
    await db.gateway_audit.insert_one({
        "user_id": g["user_id"], "partner_name": g["partner_name"], "scope": scope,
        "at": datetime.now(timezone.utc),
    })
    return g

@api.get("/partner/v1/profile")
async def partner_profile(x_partner_key: Optional[str] = Header(None)):
    g = await _partner_auth(x_partner_key, "emergency_profile")
    prof = await db.emergency_profiles.find_one({"user_id": g["user_id"]}, {"_id": 0}) or {}
    return {"scope": "emergency_profile", "data": prof, "consented_by_user": True}

@api.get("/partner/v1/vault")
async def partner_vault(x_partner_key: Optional[str] = Header(None)):
    g = await _partner_auth(x_partner_key, "vault_list")
    docs = await db.documents.find({"user_id": g["user_id"]}, {"_id": 0, "doc_id": 1, "title": 1, "category": 1, "uploaded_at": 1}).to_list(100)
    return {"scope": "vault_list", "data": docs, "note": "Metadata only — file contents remain encrypted/user-controlled."}

@api.get("/partner/v1/recovery")
async def partner_recovery(x_partner_key: Optional[str] = Header(None)):
    g = await _partner_auth(x_partner_key, "recovery_status")
    rec = await db.recovery.find_one({"user_id": g["user_id"]}, {"_id": 0, "start_date": 1, "end_date": 1, "status": 1, "outings": 1}) or {}
    return {"scope": "recovery_status", "data": rec}

# --------- 2. SOVEREIGN DATA MARKETPLACE (opt-in anonymized insights — payouts SIMULATED) ---------
MARKET_OFFERS = [
    {"offer_id": "resp-eu-2026", "institution": "EU Respiratory Research Consortium", "title": "Anonymné dáta o liekoch na dýchacie cesty", "reward_eur": 12.0, "reward_crypto": "4.1 USDC", "category": "medication"},
    {"offer_id": "senior-mobility", "institution": "WHO Healthy Ageing Lab", "title": "Anonymné vzorce pohybu seniorov 65+", "reward_eur": 18.5, "reward_crypto": "6.3 USDC", "category": "wellness"},
    {"offer_id": "sk-vaccination", "institution": "Stredoeurópsky epidemiologický inštitút", "title": "Anonymná preočkovanosť V4 regiónu", "reward_eur": 8.0, "reward_crypto": "2.7 USDC", "category": "vaccination"},
]

class MarketOptinIn(BaseModel):
    enabled: bool
    categories: List[str] = []

@api.put("/marketplace/optin")
async def marketplace_optin(body: MarketOptinIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await db.marketplace_optins.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"enabled": body.enabled, "categories": body.categories[:10], "updated_at": datetime.now(timezone.utc)},
         "$setOnInsert": {"earnings_eur": 0.0}},
        upsert=True,
    )
    return await db.marketplace_optins.find_one({"user_id": user["user_id"]}, {"_id": 0})

@api.get("/marketplace/me")
async def marketplace_me(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    me = await db.marketplace_optins.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {"enabled": False, "earnings_eur": 0.0}
    sold = await db.marketplace_sales.find({"user_id": user["user_id"]}, {"_id": 0}).sort("at", -1).to_list(20)
    return {**me, "sales": sold, "simulated": True}

@api.get("/marketplace/offers")
async def marketplace_offers(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    return {"offers": MARKET_OFFERS, "simulated": True,
            "disclaimer": "DEMO režim — reálne výskumné inštitúcie a výplaty budú napojené v produkcii. Dáta sú vždy anonymizované a zdieľané len s vaším výslovným súhlasom (GDPR čl. 9)."}

@api.post("/marketplace/offers/{offer_id}/accept")
async def marketplace_accept(offer_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    me = await db.marketplace_optins.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not me or not me.get("enabled"):
        raise HTTPException(403, "optin_required: Najprv zapnite anonymizované zdieľanie dát (opt-in).")
    offer = next((o for o in MARKET_OFFERS if o["offer_id"] == offer_id), None)
    if not offer:
        raise HTTPException(404, "Offer not found")
    dup = await db.marketplace_sales.find_one({"user_id": user["user_id"], "offer_id": offer_id})
    if dup:
        raise HTTPException(409, "Offer already accepted")
    sale = {"user_id": user["user_id"], "offer_id": offer_id, "institution": offer["institution"],
            "reward_eur": offer["reward_eur"], "reward_crypto": offer["reward_crypto"],
            "at": datetime.now(timezone.utc), "payout_status": "simulated"}
    await db.marketplace_sales.insert_one(sale.copy())
    await db.marketplace_optins.update_one({"user_id": user["user_id"]}, {"$inc": {"earnings_eur": offer["reward_eur"]}})
    # GA-T Proof-of-Health bonus alongside the (simulated) EUR payout
    try:
        from routes.token import award_tokens
        gat_tx = await award_tokens(user["user_id"], "proof_of_health", f"marketplace sale: {offer_id}")
        sale["gat_reward"] = gat_tx["amount"] if gat_tx else 0
    except Exception as e:
        logger.warning(f"marketplace GA-T award failed: {e}")
    return clean(sale)

# --------- 3. GLOBAL SENTINEL NETWORK (anonymized real-time survival signals) ---------
SENTINEL_KINDS = ("supply_shortage", "grid_down", "pharmacy_out", "water_issue")

class SentinelReportIn(BaseModel):
    kind: str
    region: str = "SK"
    note: Optional[str] = ""

@api.put("/sentinel/node")
async def sentinel_node(body: MarketOptinIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"sentinel_node": body.enabled}})
    return {"sentinel_node": body.enabled}

@api.post("/sentinel/report")
async def sentinel_report(body: SentinelReportIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if body.kind not in SENTINEL_KINDS:
        raise HTTPException(400, f"kind must be one of {SENTINEL_KINDS}")
    # Anonymized: only a salted hash for rate-limiting, never the user_id
    anon = hashlib.sha256(f"sentinel|{user['user_id']}".encode()).hexdigest()[:16]
    recent = await db.sentinel_signals.count_documents({
        "anon": anon, "kind": body.kind,
        "at": {"$gte": datetime.now(timezone.utc) - timedelta(hours=1)},
    })
    if recent >= 5:
        raise HTTPException(429, "Rate limit: max 5 reports of the same kind per hour")
    await db.sentinel_signals.insert_one({
        "anon": anon, "kind": body.kind, "region": body.region.upper()[:8],
        "note": (body.note or "")[:200], "at": datetime.now(timezone.utc),
    })
    # GA-T Proof-of-Health — reward anonymized survival signal
    gat_tx = None
    try:
        from routes.token import award_tokens
        gat_tx = await award_tokens(user["user_id"], "proof_of_health", f"sentinel signal: {body.kind}")
    except Exception as e:
        logger.warning(f"proof_of_health award failed: {e}")
    return {"ok": True, "anonymized": True, "gat_reward": gat_tx["amount"] if gat_tx else 0}

@api.get("/sentinel/aggregate")
async def sentinel_aggregate(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    since = datetime.now(timezone.utc) - timedelta(days=7)
    pipeline = [
        {"$match": {"at": {"$gte": since}}},
        {"$group": {"_id": {"kind": "$kind", "region": "$region"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}, {"$limit": 50},
    ]
    rows = await db.sentinel_signals.aggregate(pipeline).to_list(50)
    nodes = await db.users.count_documents({"sentinel_node": True})
    return {
        "window_days": 7, "active_nodes": nodes,
        "signals": [{"kind": r["_id"]["kind"], "region": r["_id"]["region"], "count": r["count"]} for r in rows],
    }

# --------- 4. UNIVERSAL FINANCIAL ONRAMP (Stripe Checkout — real when key configured) ---------
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")
FRONTEND_BASE = os.environ.get("FRONTEND_PUBLIC_URL", "https://global-compass-hub.preview.emergentagent.com")

def _stripe_ready() -> bool:
    return STRIPE_API_KEY.startswith("sk_") and STRIPE_API_KEY not in ("sk_test_emergent",)

class CheckoutIn(BaseModel):
    amount_eur: float

@api.post("/solidarity/campaigns/{cid}/checkout")
async def solidarity_checkout(cid: str, body: CheckoutIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if not 1.0 <= body.amount_eur <= 10000.0:
        raise HTTPException(400, "amount 1..10000 EUR")
    camp = await db.campaigns.find_one({"campaign_id": cid}, {"_id": 0})
    if not camp:
        raise HTTPException(404, "Campaign not found")
    if not _stripe_ready():
        raise HTTPException(503, "stripe_key_missing: Reálne platby vyžadujú platný Stripe kľúč (STRIPE_API_KEY). Zatiaľ použite komunitný mock-donate.")
    import stripe
    stripe.api_key = STRIPE_API_KEY
    amount_cents = int(round(body.amount_eur * 100))
    try:
        session = stripe.checkout.Session.create(
            mode="payment", submit_type="donate",
            line_items=[{"price_data": {"currency": "eur", "unit_amount": amount_cents,
                                        "product_data": {"name": f"Solidarity: {camp['title'][:60]}"}}, "quantity": 1}],
            success_url=f"{FRONTEND_BASE}/solidarity?paid=1&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_BASE}/solidarity",
            metadata={"campaign_id": cid, "amount_cents": str(amount_cents), "user_id": user["user_id"]},
        )
    except Exception as e:
        logger.error(f"stripe checkout error: {e}")
        raise HTTPException(502, "Stripe checkout failed")
    await db.stripe_donations.update_one(
        {"session_id": session.id},
        {"$setOnInsert": {"session_id": session.id, "campaign_id": cid, "user_id": user["user_id"],
                          "amount_cents": amount_cents, "status": "pending", "created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return {"checkout_url": session.url, "session_id": session.id}

@api.get("/solidarity/checkout/status/{session_id}")
async def solidarity_checkout_status(session_id: str, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    rec = await db.stripe_donations.find_one({"session_id": session_id}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "Session not found")
    if rec["status"] == "paid":
        return {"status": "paid", "amount_eur": rec["amount_cents"] / 100}
    if not _stripe_ready():
        raise HTTPException(503, "stripe_key_missing")
    import stripe
    stripe.api_key = STRIPE_API_KEY
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception:
        raise HTTPException(404, "Stripe session not found")
    if session.payment_status == "paid":
        # idempotent server-side verification against Stripe (webhook-equivalent for this env)
        res = await db.stripe_donations.update_one(
            {"session_id": session_id, "status": {"$ne": "paid"}},
            {"$set": {"status": "paid", "paid_at": datetime.now(timezone.utc)}},
        )
        if res.modified_count == 1:
            await db.campaigns.update_one(
                {"campaign_id": rec["campaign_id"]},
                {"$inc": {"raised_amount": rec["amount_cents"] / 100, "supporters": 1}},
            )
        return {"status": "paid", "amount_eur": rec["amount_cents"] / 100}
    return {"status": session.payment_status}
