# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# PLANS & STORE — one simple surface: card + price in EUR. Under the hood every purchase mints
# GA-T to the user's account (invisible unless they open Settings → Advanced → Blockchain & Tokens).
# Wires together: subscription.TIERS, token ledger, features (pay-per-feature), creator royalty.
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid

from core import api, db, logger, clean, get_current_user
from routes.subscription import TIERS, get_active_tier
from routes.token import _ledger_append, _get_supply, debit_balance, BURN_RATE
from routes.features import FEATURES, creator_royalty

# Payments: RevenueCat (App Store / Google Play) — see frontend IAP_PACKAGES. Sovereign = free default.
FAMILY_PLANS = [
    {"id": "duo",       "name": "Duo",       "seats": 2, "price_eur": 15, "price_eur_year": 150, "gat_month": 25,
     "tagline": "Two Guardians — you and the one you protect",
     "features": ["2 Guardian seats", "Shared family dashboard", "Family pulse & fall alerts", "Shared Health Card"]},
    {"id": "family",    "name": "Family",    "seats": 5, "price_eur": 35, "price_eur_year": 350, "gat_month": 60,
     "tagline": "Whole household under one roof",
     "features": ["5 Guardian seats", "Child growth & senior modes", "Family contacts + SOS chain", "Shared meds & documents"]},
    {"id": "family_xl", "name": "Family XL", "seats": 10, "price_eur": 50, "price_eur_year": 500, "gat_month": 90,
     "tagline": "Three generations, one shield",
     "features": ["10 Guardian seats", "Everything in Family", "Priority Nearby Care", "Guardian Circle sync"]},
]
# Add-ons — one-time unlocks and recurring boosts. `gat` = hidden token grant per purchase.
ADDONS = {
    "bunker_map_premium": {"name": "Bunker Map Premium", "kind": "one_time", "price_eur": 4.99, "gat": 50, "feature": "bunker",
                           "desc": "Shelter locator + 72-hour checklist, unlocked forever."},
    "ghost_mode":         {"name": "Ghost Mode", "kind": "one_time", "price_eur": 2.99, "gat": 30, "feature": "ghost_mode",
                           "desc": "Disappear from every feed and tracker at one tap."},
    "analyst_agent":      {"name": "Analyst Agent", "kind": "one_time", "price_eur": 3.99, "gat": 40, "feature": "analyst",
                           "desc": "Medical & crisis analysis agent, permanently on."},
    "mesh_sms":           {"name": "Mesh SMS", "kind": "one_time", "price_eur": 1.49, "gat": 15, "feature": "mesh_sms",
                           "desc": "Offline messages via nearby Archangel devices."},
    "bioscan_credits_10": {"name": "BioScan · 10 extra scans", "kind": "one_time", "price_eur": 2.99, "gat": 30, "credits": {"bioscan_credits": 10},
                           "desc": "Ten additional BioScan analyses."},
    "perplexity_ultra":   {"name": "Perplexity Ultra Search", "kind": "recurring", "price_eur": 5.00, "gat": 50,
                           "desc": "Unlimited Sonar web search with citations, every month."},
    "premium_voice":      {"name": "Premium Voice Pack", "kind": "recurring", "price_eur": 3.00, "gat": 30,
                           "desc": "Studio-grade Jarvis voices (ElevenLabs) in your language."},
}
GAT_PER_EUR = 10.0   # add-on GA-T price = EUR price × 10 (same ratio as the pay-per-feature catalog)


def addon_price_gat(a: dict) -> float:
    return float(round(a["price_eur"] * GAT_PER_EUR))


PROMO_CODES = {"ARCHANGEL2026": {"tier": "sentinel", "days": 30, "label": "1 month of Sentinel — free"}}


@api.get("/store/catalog")
async def store_catalog(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    tier = await get_active_tier(uid)
    fresh = await db.users.find_one({"user_id": uid}, {"_id": 0, "features_owned": 1, "addons_active": 1, "family_plan": 1, "promo_used": 1}) or {}
    owned = set(fresh.get("features_owned") or [])
    active = fresh.get("addons_active") or {}
    now = datetime.now(timezone.utc)
    tiers = [{"id": k, "name": v["name"], "tagline": v["tagline"], "accent": v["accent"],
              "features": [f for f in v["features"] if "GA-T" not in f],   # tokens stay under the hood
              "price_eur": v["price_eur"], "price_eur_year": v["price_eur_year"],
              "iap": None if k == "sovereign" else {"monthly": f"{k}_monthly", "annual": f"{k}_annual"},
              "current": k == tier} for k, v in sorted(TIERS.items(), key=lambda kv: kv[1]["order"])]
    family = [{**p, "iap": {"monthly": f"{p['id']}_monthly", "annual": f"{p['id']}_annual"}, "current": fresh.get("family_plan") == p["id"]} for p in FAMILY_PLANS]
    addons = []
    for k, a in ADDONS.items():
        until = active.get(k)
        owned_now = (a.get("feature") in owned) if a["kind"] == "one_time" and a.get("feature") else \
                    (bool(until) and datetime.fromisoformat(until) > now) if a["kind"] == "recurring" else False
        addons.append({"id": k, "name": a["name"], "kind": a["kind"], "price_eur": a["price_eur"], "price_gat": addon_price_gat(a),
                       "desc": a["desc"], "owned": owned_now, "until": until if a["kind"] == "recurring" else None})
    return {"tier": tier, "tiers": tiers, "family": family, "addons": addons, "promo_used": fresh.get("promo_used") or []}


class PromoIn(BaseModel):
    code: str

@api.post("/store/promo")
async def store_promo(body: PromoIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    code = body.code.strip().upper()
    promo = PROMO_CODES.get(code)
    if not promo:
        raise HTTPException(400, "Unknown promo code")
    uid = user["user_id"]
    fresh = await db.users.find_one({"user_id": uid}, {"_id": 0, "promo_used": 1, "tier": 1, "tier_until": 1}) or {}
    if code in (fresh.get("promo_used") or []):
        raise HTTPException(409, "This promo code was already used on your account")
    from routes.subscription import TIER_RANK
    if TIER_RANK.get(await get_active_tier(uid), 0) >= TIER_RANK[promo["tier"]]:
        await db.users.update_one({"user_id": uid}, {"$addToSet": {"promo_used": code}})
        return {"ok": True, "message": f"Your current plan already includes {TIERS[promo['tier']]['name']} — the code is saved on your account.", "tier": None, "until": None}
    until = datetime.now(timezone.utc) + timedelta(days=promo["days"])
    await db.users.update_one({"user_id": uid}, {
        "$set": {"tier": promo["tier"], "tier_until": until, "tier_paid_with": "promo", "tier_billing": "promo",
                 "tier_started_at": datetime.now(timezone.utc)},
        "$addToSet": {"promo_used": code}})
    await db.promo_redemptions.insert_one({"user_id": uid, "code": code, "tier": promo["tier"], "until": until, "at": datetime.now(timezone.utc)})
    return {"ok": True, "message": f"🎉 {promo['label']} activated until {until.date().isoformat()}.", "tier": promo["tier"], "until": until}


class AddonBuyIn(BaseModel):
    addon_id: str

@api.post("/store/addon/buy")
async def store_addon_buy(body: AddonBuyIn, authorization: Optional[str] = Header(None)):
    """Add-on purchase paid in GA-T (ATOMIC debit) → unlock + 2 % burn + 5 % creator royalty.
    SEC: there is no unverified fiat path — subscriptions go through RevenueCat, add-ons through GA-T."""
    user = await get_current_user(authorization)
    a = ADDONS.get(body.addon_id)
    if not a:
        raise HTTPException(400, f"addon_id must be one of {list(ADDONS)}")
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    price = addon_price_gat(a)
    await _get_supply()
    if not await debit_balance(uid, price, spent_total=price):
        raise HTTPException(402, f"insufficient_balance: You need {price:.0f} GA-T.")
    burn = round(price * BURN_RATE, 4)
    await db.token_supply.update_one({"key": "gat"}, {"$inc": {"circulating": -price, "burned": burn, "treasury": price - burn}})
    upd: dict = {}
    if a.get("feature"):
        upd["$addToSet"] = {"features_owned": a["feature"]}
    if a.get("credits"):
        upd["$inc"] = dict(a["credits"])
    if a["kind"] == "recurring":
        upd.setdefault("$set", {})[f"addons_active.{body.addon_id}"] = (now + timedelta(days=30)).isoformat()
    if upd:
        await db.users.update_one({"user_id": uid}, upd)
    purchase = {"purchase_id": uuid.uuid4().hex, "user_id": uid, "addon_id": body.addon_id, "kind": a["kind"],
                "amount_gat": price, "currency": "gat", "at": now}
    await db.addon_purchases.insert_one(purchase.copy())
    tx = await _ledger_append("spend", uid, -price, {"item": f"addon:{body.addon_id}", "burned": burn, "purchase_id": purchase["purchase_id"]})
    await _ledger_append("burn", "burn-address", burn, {"source_tx": tx["tx_id"], "item": f"addon:{body.addon_id}"})
    royalty = await creator_royalty("addon", price, "gat", uid, {"addon": body.addon_id, "purchase_id": purchase["purchase_id"]})
    acct = await db.token_accounts.find_one({"user_id": uid}, {"_id": 0, "balance": 1}) or {}
    return {"ok": True, "purchase": clean(purchase), "tx": clean(tx), "balance": acct.get("balance", 0.0), "creator_royalty": royalty}


class TransferIn(BaseModel):
    to_email: str
    amount: float
    note: str = ""

@api.post("/store/transfer")
async def gat_transfer(body: TransferIn, authorization: Optional[str] = Header(None)):
    """Advanced layer — send GA-T to another Archangel account (by e-mail)."""
    user = await get_current_user(authorization)
    if body.amount <= 0:
        raise HTTPException(400, "amount must be positive")
    to = await db.users.find_one({"email": body.to_email.strip().lower()}, {"_id": 0, "user_id": 1})
    if not to or to["user_id"] == user["user_id"]:
        raise HTTPException(404, "Recipient not found")
    now = datetime.now(timezone.utc)
    if not await debit_balance(user["user_id"], body.amount):
        acct = await db.token_accounts.find_one({"user_id": user["user_id"]}, {"_id": 0, "balance": 1}) or {}
        raise HTTPException(402, f"insufficient_balance: you have {acct.get('balance', 0.0):.2f} GA-T")
    await db.token_accounts.update_one({"user_id": to["user_id"]}, {"$inc": {"balance": body.amount}, "$set": {"updated_at": now}}, upsert=True)
    out = await _ledger_append("transfer_out", user["user_id"], -body.amount, {"to": to["user_id"], "note": body.note[:120]})
    await _ledger_append("transfer_in", to["user_id"], body.amount, {"from": user["user_id"], "note": body.note[:120]})
    return {"ok": True, "tx": clean(out)}
