# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Elite 4-Tier Subscription — Sovereign (free) / Guardian (€29) / Sentinel
(€149) / Archangel (€499). Monthly or annual (−20 %). Multi-currency EUR /
CZK / GA-T. GA-T payments live via the internal token engine; card billing is
a placeholder until the real Stripe key is provided (user's decision)."""
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta

from core import api, db, clean, get_current_user

CZK_RATE = 25.0
ANNUAL_DISCOUNT = 0.20
TIER_RANK = {"sovereign": 0, "guardian": 1, "sentinel": 2, "archangel": 3}

def _prices(eur_month: float) -> dict:
    eur_year = round(eur_month * 12 * (1 - ANNUAL_DISCOUNT), 0)
    return {"price_eur": eur_month, "price_czk": round(eur_month * CZK_RATE, 0),
            "price_gat": round(eur_month * 10, 0),
            "price_eur_year": eur_year, "price_czk_year": round(eur_year * CZK_RATE, 0),
            "price_gat_year": round(eur_year * 10, 0)}

TIERS = {
    "sovereign": {
        "name": "Sovereign", "order": 0, **_prices(0),
        "tagline": "Základná suverenita — navždy zadarmo",
        "accent": "#5FA779",
        "features": ["Šifrovaný Trezor (zero-knowledge)", "Emergency QR + SOS",
                     "Základný Health Timeline", "Verejný Solidarity Hub"],
    },
    "guardian": {
        "name": "Guardian", "order": 1, **_prices(29),
        "tagline": "Proaktívna ochrana pre teba aj rodinu",
        "accent": "#B8860B",
        "features": ["Všetko zo Sovereign", "Waitlist Hunter upozornenia",
                     "AI preklady správ (Jarvis)", "Angel Mode (pády + bezpečnosť)",
                     "Kompletná Physio-AI encyklopédia"],
    },
    "sentinel": {
        "name": "Sentinel", "order": 2, **_prices(149),
        "tagline": "VIP prežitie — nemocnica vo vrecku",
        "accent": "#E5E4E2",
        "features": ["Všetko z Guardian", "🛰️ Satellite Emergency Handshake",
                     "🩺 Vitals Bio-Scanner — neobmedzene", "⚔️ AI Tactical Medic (offline)",
                     "🧬 Longevity Engine + Bio-Age", "Autonómne rezervácie (Autopilot)",
                     "Insurance Claim Recovery"],
    },
    "archangel": {
        "name": "Archangel", "order": 3, **_prices(499),
        "tagline": "Elitná suverenita — Zero-latency Swarm",
        "accent": "#8A2BE2",
        "features": ["Všetko zo Sentinel", "⚡ Prioritná orchestrácia Swarmu (Zero-latency)",
                     "👤 Concierge Human Expert — 1 konzultácia/mes.",
                     "🏛️ DAO governance — hlasovacie práva nadácie",
                     "White-Label prístup pre rodinné officy"],
    },
}

def current_tier(user: dict) -> str:
    if user.get("inner_circle"):
        return "archangel"  # Inner Circle — permanent, lifetime, never expires
    tier = user.get("tier") or "sovereign"
    until = user.get("tier_until")
    if tier != "sovereign" and until:
        if isinstance(until, str):
            active = until >= datetime.now(timezone.utc).isoformat()
        else:
            u2 = until if until.tzinfo else until.replace(tzinfo=timezone.utc)
            active = u2 >= datetime.now(timezone.utc)
        if not active:
            return "sovereign"
    return tier

async def get_active_tier(user_id: str) -> str:
    fresh = await db.users.find_one({"user_id": user_id}, {"_id": 0, "tier": 1, "tier_until": 1, "inner_circle": 1}) or {}
    return current_tier(fresh)

async def require_tier(user: dict, min_tier: str, feature: str) -> str:
    tier = await get_active_tier(user["user_id"])
    if TIER_RANK.get(tier, 0) < TIER_RANK[min_tier]:
        t = TIERS[min_tier]
        raise HTTPException(402, f"{min_tier}_required: {feature} je exkluzívny pre {t['name']} tier "
                                 f"(€{t['price_eur']}/mes. alebo {t['price_gat']:.0f} GA-T). "
                                 f"Aktivujte 7-dňový Sentinel trial zadarmo v Subscription.")
    return tier

async def record_revenue(kind: str, amount_eur: float, user_id: str, meta: dict) -> None:
    """Founder wealth ledger — subscriptions, guardian tax, pay-per-use events."""
    await db.revenue_events.insert_one({
        "kind": kind, "amount_eur": round(amount_eur, 2), "user_id": user_id,
        "meta": meta, "at": datetime.now(timezone.utc)})

async def _is_founder(user: dict) -> bool:
    if user.get("is_founder"):
        return True
    first = await db.users.find_one({}, {"_id": 0, "user_id": 1}, sort=[("created_at", 1)])
    return bool(first and first["user_id"] == user["user_id"])


@api.get("/subscription")
async def subscription_info(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    fresh = await db.users.find_one({"user_id": user["user_id"]},
                                    {"_id": 0, "tier": 1, "tier_until": 1, "tier_paid_with": 1,
                                     "tier_billing": 1, "trial_used": 1, "inner_circle": 1}) or {}
    acct = await db.token_accounts.find_one({"user_id": user["user_id"]}, {"_id": 0, "balance": 1})
    tier = current_tier(fresh)
    tu = fresh.get("tier_until")
    return {"tier": tier, "tier_until": tu.isoformat() if hasattr(tu, "isoformat") else tu,
            "inner_circle": bool(fresh.get("inner_circle")),
            "paid_with": fresh.get("tier_paid_with"), "billing": fresh.get("tier_billing"),
            "trial_available": not fresh.get("trial_used"),
            "gat_balance": (acct or {}).get("balance", 0.0),
            "tiers": TIERS, "annual_discount_pct": int(ANNUAL_DISCOUNT * 100),
            "currencies": ["EUR", "CZK", "GA-T"], "czk_rate": CZK_RATE,
            "payperuse": {"bioscan_single": 5, "ips_export_single": 10},
            "billing_note": "Platba kartou sa aktivuje po vložení reálneho Stripe kľúča (placeholder). GA-T platby fungujú naplno."}


class UpgradeIn(BaseModel):
    tier: str                 # guardian | sentinel | archangel
    method: str = "gat"       # gat | card
    billing: str = "monthly"  # monthly | annual (−20 %)

@api.post("/subscription/upgrade")
async def subscription_upgrade(body: UpgradeIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if body.tier not in ("guardian", "sentinel", "archangel"):
        raise HTTPException(400, "tier must be guardian|sentinel|archangel")
    if body.billing not in ("monthly", "annual"):
        raise HTTPException(400, "billing must be monthly|annual")
    if body.method == "card":
        raise HTTPException(503, "stripe_key_missing: Platby kartou sa spustia po doplnení reálneho Stripe kľúča. Zatiaľ použite GA-T tokeny.")
    # GA-T payment via the internal token engine (burn applies automatically)
    from routes.token import token_spend, SpendIn
    item = f"tier_{body.tier}_{'365d' if body.billing == 'annual' else '30d'}"
    result = await token_spend(SpendIn(item=item), authorization)
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"tier_billing": body.billing}})
    t = TIERS[body.tier]
    amount = t["price_eur_year"] if body.billing == "annual" else t["price_eur"]
    await record_revenue("subscription", amount, user["user_id"],
                         {"tier": body.tier, "billing": body.billing, "paid_with": "GA-T"})
    return {"ok": True, "tier": body.tier, "billing": body.billing, "paid_with": "GA-T", **result}


@api.post("/subscription/trial")
async def subscription_trial(authorization: Optional[str] = Header(None)):
    """One-time 7-day Sentinel trial — the upsell funnel entry point."""
    user = await get_current_user(authorization)
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "trial_used": 1, "tier": 1, "tier_until": 1}) or {}
    if fresh.get("trial_used"):
        raise HTTPException(409, "trial_used: 7-dňový trial už bol využitý. Pokračujte upgradom na Sentinel.")
    if TIER_RANK.get(current_tier(fresh), 0) >= TIER_RANK["sentinel"]:
        raise HTTPException(409, "already_premium: Už máte Sentinel alebo vyšší tier.")
    until = datetime.now(timezone.utc) + timedelta(days=7)
    await db.users.update_one({"user_id": user["user_id"]},
                              {"$set": {"tier": "sentinel", "tier_until": until,
                                        "tier_paid_with": "trial", "tier_billing": "trial",
                                        "trial_used": True}})
    return {"ok": True, "tier": "sentinel", "trial": True, "tier_until": until.isoformat()}


@api.get("/wealth/founder-dashboard")
async def founder_dashboard(authorization: Optional[str] = Header(None)):
    """Founder-only admin view — MRR, ACV, Guardian Tax and premium revenue."""
    user = await get_current_user(authorization)
    if not await _is_founder(user):
        raise HTTPException(403, "founder_only")
    now = datetime.now(timezone.utc)
    tier_counts, mrr, acv = {}, 0.0, 0.0
    async for u in db.users.find({"tier": {"$in": ["guardian", "sentinel", "archangel"]}},
                                 {"_id": 0, "tier": 1, "tier_until": 1, "tier_billing": 1}):
        if current_tier(u) == "sovereign":
            continue
        t = u["tier"]
        tier_counts[t] = tier_counts.get(t, 0) + 1
        if u.get("tier_billing") == "annual":
            acv += TIERS[t]["price_eur_year"]
        elif u.get("tier_billing") != "trial":
            mrr += TIERS[t]["price_eur"]
    rev: dict = {}
    async for e in db.revenue_events.find({}, {"_id": 0, "kind": 1, "amount_eur": 1}):
        rev[e["kind"]] = round(rev.get(e["kind"], 0.0) + e["amount_eur"], 2)
    last_events = await db.revenue_events.find({}, {"_id": 0}).sort("at", -1).to_list(10)
    supply = await db.token_supply.find_one({"key": "gat"}, {"_id": 0}) or {}
    return {"as_of": now.isoformat(), "founder_view": True,
            "mrr_eur": round(mrr, 2), "acv_eur": round(acv, 2),
            "tier_distribution": tier_counts,
            "revenue_by_kind": rev, "guardian_tax_rate": 0.15,
            "gat_treasury": supply.get("treasury", 0.0), "gat_burned": supply.get("burned", 0.0),
            "recent_events": clean(last_events),
            "wealth_engine": "SECURED — billing logic hash-chained via GA-T ledger"}
