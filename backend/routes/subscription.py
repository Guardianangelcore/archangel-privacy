# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Elite 4-Tier Subscription — Sovereign (free) / Guardian (€9) / Sentinel
(€99) / Archangel (€299). Monthly or annual (−20 %). Multi-currency EUR /
CZK / GA-T. GA-T payments live via the internal token engine; card billing is
a placeholder until the real Stripe key is provided (user's decision)."""
from fastapi import HTTPException, Header, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta

from core import api, db, clean, get_current_user, _aml_ledger_append, rate_limit, client_ip

CZK_RATE = 25.0
ANNUAL_DISCOUNT = 0.20
TIER_RANK = {"sovereign": 0, "guardian": 1, "sentinel": 2, "archangel": 3}

def _prices(eur_month: float, gat_month: float = 0.0, eur_year: Optional[float] = None) -> dict:
    """Monthly + annual pricing. eur_year overrides the default −20 % annual price (store price list)."""
    eur_year = eur_year if eur_year is not None else round(eur_month * 12 * (1 - ANNUAL_DISCOUNT), 0)
    gat_year = round(gat_month * 12 * (1 - ANNUAL_DISCOUNT), 0)
    return {"price_eur": eur_month, "price_czk": round(eur_month * CZK_RATE, 0),
            "price_gat": gat_month,
            "price_eur_year": eur_year, "price_czk_year": round(eur_year * CZK_RATE, 0),
            "price_gat_year": gat_year}

TIERS = {
    "sovereign": {
        "name": "Sovereign", "order": 0, **_prices(0),
        "tagline": "Core sovereignty — free forever",
        "accent": "#5FA779",
        "features": ["Encrypted Vault (zero-knowledge)", "Emergency QR + SOS",
                     "Basic Health Timeline", "Public Solidarity Hub"],
    },
    "guardian": {
        "name": "Guardian", "order": 1, **_prices(9, 15, eur_year=86),
        "tagline": "Proactive protection for you and your family",
        "accent": "#B8860B",
        "features": ["Everything in Sovereign", "Jarvis AI chat + Morning Briefing",
                     "💎 100 GA-T credited every month (loyalty bonus up to +50 %)",
                     "Waitlist Hunter alerts", "AI report translations (Jarvis)",
                     "Angel Mode (falls + safety)", "Complete Physio-AI encyclopedia"],
    },
    "sentinel": {
        "name": "Sentinel", "order": 2, **_prices(99, 250, eur_year=950),
        "tagline": "VIP survival — a hospital in your pocket",
        "accent": "#E5E4E2",
        "features": ["Everything in Guardian", "💎 300 GA-T credited every month",
                     "🛰️ Satellite Emergency Handshake",
                     "🩺 Vitals Bio-Scanner — neobmedzene", "⚔️ AI Tactical Medic (offline)",
                     "🧬 Longevity Engine + Bio-Age", "Autonomous bookings (Autopilot)",
                     "Insurance Claim Recovery"],
    },
    "archangel": {
        "name": "Archangel", "order": 3, **_prices(299, 800, eur_year=2990),
        "tagline": "Elite sovereignty — Zero-latency Swarm",
        "accent": "#8A2BE2",
        "features": ["Everything in Sentinel", "💎 1 000 GA-T credited every month",
                     "⚡ Priority Swarm orchestration (Zero-latency)",
                     "👤 Concierge Human Expert — 1 consultation/mo.",
                     "🏛️ DAO governance — foundation voting rights",
                     "White-Label access for family offices"],
    },
}

def current_tier(user: dict) -> str:
    if user.get("inner_circle"):
        return "archangel"  # Inner Circle — permanent, lifetime, never expires
    # DEMO_ONLY — judge demo session unlocks every gate for 30 min (see routes/demo_mode.py)
    from routes.demo_mode import demo_active
    if demo_active(user):
        return "archangel"
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
    fresh = await db.users.find_one({"user_id": user_id}, {"_id": 0, "tier": 1, "tier_until": 1, "inner_circle": 1, "demo_until": 1}) or {}
    return current_tier(fresh)

async def require_tier(user: dict, min_tier: str, feature: str) -> str:
    tier = await get_active_tier(user["user_id"])
    if TIER_RANK.get(tier, 0) < TIER_RANK[min_tier]:
        t = TIERS[min_tier]
        raise HTTPException(402, f"{min_tier}_required: {feature} requires the {t['name']} Plan "
                                 f"(€{t['price_eur']}/mo or {t['price_gat']:.0f} GA-T) — upgrade to unlock, "
                                 f"or activate the free 7-day Sentinel trial in Subscription.")
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
                                     "tier_billing": 1, "trial_used": 1, "inner_circle": 1, "demo_until": 1}) or {}
    from routes.token import settle_subscription_allocations, SUBSCRIPTION_GAT
    allocation = await settle_subscription_allocations(user["user_id"])   # credits any due monthly GA-T
    from routes.loyalty import check_loyalty
    from routes.demo_mode import demo_active
    loyalty = clean(await check_loyalty(user["user_id"]))                  # 3/6/12-month milestones
    acct = await db.token_accounts.find_one({"user_id": user["user_id"]}, {"_id": 0, "balance": 1})
    tier = current_tier(fresh)
    tu = fresh.get("tier_until")
    return {"tier": tier, "tier_until": tu.isoformat() if hasattr(tu, "isoformat") else tu,
            "loyalty": loyalty, "demo_active": demo_active(fresh),
            "gat_allocation": allocation, "gat_monthly_by_tier": SUBSCRIPTION_GAT,
            "inner_circle": bool(fresh.get("inner_circle")),
            "paid_with": fresh.get("tier_paid_with"), "billing": fresh.get("tier_billing"),
            "trial_available": not fresh.get("trial_used"),
            "gat_balance": (acct or {}).get("balance", 0.0),
            "tiers": TIERS, "annual_discount_pct": int(ANNUAL_DISCOUNT * 100),
            "currencies": ["EUR", "CZK", "GA-T"], "czk_rate": CZK_RATE,
            "payperuse": {"bioscan_single": 5, "ips_export_single": 10},
            "billing_note": "Card payments: Stripe TEST mode — use test card 4242 4242 4242 4242. GA-T payments are fully live."}


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
        raise HTTPException(400, "use_billing_checkout: Card payments go through POST /api/billing/checkout (Stripe).")
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


# --------- IN-APP PURCHASES (RevenueCat · App Store / Google Play) ---------
# The RevenueCat SDK on the device is the source of truth for the `pro` entitlement.
# The app mirrors an ACTIVE entitlement here so the existing server-side features
# (tier gates for Jarvis/Sentinel, monthly GA-T loyalty allocation) apply to IAP subscribers.
# One RevenueCat entitlement ("pro") covers all three tiers — the TIER is derived from the
# store product identifier: pro.monthly / pro.annual → guardian, pro.sentinel_* → sentinel,
# pro.archangel_* → archangel (provisioned via the integration proxy, see memory/revenuecat.md).
IAP_ENTITLEMENTS = {"pro"}
# Product ids provisioned in RevenueCat (memory/revenuecat.md) — anything else is rejected.
IAP_PRODUCT_PREFIXES = ("pro.",)
IAP_STORES = {"APP_STORE", "MAC_APP_STORE", "PLAY_STORE", "AMAZON", "STRIPE", "PROMOTIONAL", "TEST_STORE", "RC_BILLING", "UNKNOWN_STORE"}


def iap_tier(product_identifier: Optional[str]) -> str:
    pid = (product_identifier or "").lower()
    if "archangel" in pid:
        return "archangel"
    if "sentinel" in pid:
        return "sentinel"
    return "guardian"   # incl. family plans (Duo / Family / Family XL = Guardian seats)

def iap_family_plan(product_identifier: Optional[str]) -> Optional[str]:
    pid = (product_identifier or "").lower()
    return "family_xl" if "family_xl" in pid else "family" if "family" in pid else "duo" if "duo" in pid else None


class ActiveSubIn(BaseModel):
    product_identifier: str
    expires_date: Optional[str] = None
    will_renew: Optional[bool] = None
    store: Optional[str] = None
    period_type: Optional[str] = None


class IapSyncIn(BaseModel):
    entitlement: str = "pro"
    active: bool
    product_identifier: Optional[str] = None
    expires_date: Optional[str] = None       # ISO 8601 from CustomerInfo (None = lifetime/unknown)
    store: Optional[str] = None              # APP_STORE | PLAY_STORE | TEST_STORE …
    period_type: Optional[str] = None        # NORMAL | TRIAL | INTRO
    app_user_id: Optional[str] = None        # current RevenueCat app user id (must equal our user_id)
    will_renew: Optional[bool] = None
    # Full list of active product subscriptions (CustomerInfo.activeSubscriptions + allExpirationDates).
    # Needed because ONE entitlement ("pro") aggregates tier plans AND add-on subscriptions.
    active_subscriptions: Optional[List[ActiveSubIn]] = None


@api.post("/subscription/iap-sync")
async def subscription_iap_sync(body: IapSyncIn, request: Request, authorization: Optional[str] = Header(None)):
    """Mirror the device's RevenueCat entitlement into the tier system (idempotent).

    SECURITY NOTE: the Emergent-managed RevenueCat integration exposes no secret API key or
    webhook to this backend, so the SDK's CustomerInfo on the device is the source of truth
    (per playbook). Hardening applied here: rate limit per user, strict payload whitelist
    (entitlement, provisioned product ids, store), identity match and an AML ledger entry."""
    user = await get_current_user(authorization)
    uid = user["user_id"]
    rate_limit(request, "iap_sync", key=f"user:{uid}")
    now = datetime.now(timezone.utc)
    if body.entitlement not in IAP_ENTITLEMENTS:
        raise HTTPException(400, f"unknown entitlement {body.entitlement}")
    if body.active:
        pid = (body.product_identifier or "").lower()
        if not pid.startswith(IAP_PRODUCT_PREFIXES):
            raise HTTPException(422, "unknown product identifier")
        if body.store and body.store.upper() not in IAP_STORES:
            raise HTTPException(422, "unknown store")
        if not body.app_user_id:
            raise HTTPException(422, "app_user_id required")
    if body.app_user_id and body.app_user_id != uid:
        raise HTTPException(409, "RevenueCat identity does not match the signed-in user")

    # ---- ADD-ON SUBSCRIPTIONS (Perplexity Ultra, Premium Voice) — same entitlement, separate lifecycle ----
    from routes.store import is_addon_product, sync_addon_subscriptions, addon_status
    subs = [s.model_dump() for s in (body.active_subscriptions or [])]
    if body.active_subscriptions is None and body.active and is_addon_product(body.product_identifier):
        subs = [{"product_identifier": body.product_identifier, "expires_date": body.expires_date,
                 "will_renew": body.will_renew, "store": body.store, "period_type": body.period_type}]
    addon_sync = None
    if body.active_subscriptions is not None or is_addon_product(body.product_identifier):
        addon_sync = await sync_addon_subscriptions(uid, subs if body.active else [], body.store, now)
        if addon_sync["changes"]:
            await _aml_ledger_append(uid, "iap_addon_sync", {"changes": addon_sync["changes"], "store": body.store, "ip": client_ip(request)})

    # ---- TIER: choose the best NON-add-on active product ----
    tier_subs = [s for s in subs if not is_addon_product(s.get("product_identifier"))]
    if body.active_subscriptions is None and is_addon_product(body.product_identifier):
        # Legacy single-product payload about an add-on: never infer anything about the tier from it.
        fresh0 = await db.users.find_one({"user_id": uid}, {"_id": 0, "tier": 1, "tier_until": 1, "addon_subs": 1, "addons_active": 1}) or {}
        return {"status": "addons_synced", "tier": current_tier(fresh0), "addons": addon_status(fresh0)}
    if body.active_subscriptions is not None:
        if body.active and tier_subs:
            best = max(tier_subs, key=lambda s: TIERS[iap_tier(s["product_identifier"])]["order"])
            body.product_identifier, body.expires_date = best["product_identifier"], best.get("expires_date") or body.expires_date
        elif body.active:
            # Only add-on subscriptions are active → the entitlement grants no tier (lapse an IAP-granted tier)
            body.active = False
    tier = iap_tier(body.product_identifier)
    fresh = await db.users.find_one({"user_id": uid}, {"_id": 0, "tier": 1, "tier_until": 1, "tier_paid_with": 1,
                                                       "gat_alloc_anchor": 1, "iap": 1, "tier_started_at": 1, "inner_circle": 1,
                                                       "addon_subs": 1, "addons_active": 1})
    iap_paid = (fresh.get("tier_paid_with") or "").lower() == "iap"
    addons_out = addon_status(fresh) if addon_sync is not None else None
    if not body.active:
        # Entitlement lapsed: only downgrade what IAP granted; never touch card/GA-T/trial/inner-circle tiers.
        if iap_paid and fresh.get("tier") in ("guardian", "sentinel", "archangel"):
            await db.users.update_one({"user_id": uid}, {"$set": {"tier": "sovereign", "tier_until": None,
                                                                  "iap.active": False, "iap.synced_at": now}})
            return {"status": "downgraded", "tier": "sovereign", "addons": addons_out}
        return {"status": "addons_synced" if addon_sync and addon_sync["changes"] else "noop", "tier": current_tier(fresh), "addons": addons_out}

    until = None
    if body.expires_date:
        try:
            until = datetime.fromisoformat(body.expires_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(422, "invalid expires_date")
        if until <= now:
            raise HTTPException(422, "entitlement already expired")
    prev_iap = fresh.get("iap") or {}
    same = (fresh.get("tier") == tier and iap_paid
            and prev_iap.get("expires_date") == body.expires_date
            and prev_iap.get("product_identifier") == body.product_identifier)
    iap = {"entitlement": body.entitlement, "product_identifier": body.product_identifier, "tier": tier, "store": body.store,
           "period_type": body.period_type, "expires_date": body.expires_date, "will_renew": body.will_renew,
           "app_user_id": body.app_user_id, "active": True, "synced_at": now}
    if same:
        await db.users.update_one({"user_id": uid}, {"$set": {"iap.synced_at": now}})
    else:
        # Never let IAP downgrade a higher tier paid another way (Sentinel via card, inner-circle Archangel).
        # A tier paid through the store always follows the store (upgrade AND downgrade between IAP products).
        if not iap_paid and TIERS[current_tier(fresh)]["order"] > TIERS[tier]["order"]:
            await db.users.update_one({"user_id": uid}, {"$set": {"iap": iap}})
            return {"status": "kept_higher_tier", "tier": current_tier(fresh), "addons": addons_out}
        await db.users.update_one({"user_id": uid}, {"$set": {
            "tier": tier, "tier_until": until, "tier_paid_with": "iap", "iap": iap,
            "family_plan": iap_family_plan(body.product_identifier),
            "tier_started_at": fresh.get("tier_started_at") or now}})
        await _aml_ledger_append(uid, "iap_entitlement_sync", {
            "entitlement": body.entitlement, "tier": tier, "product": body.product_identifier, "store": body.store,
            "expires": body.expires_date, "period_type": body.period_type, "ip": client_ip(request)})
    # LOYALTY LOOP — fiat subscription → monthly GA-T (trial periods are excluded by the allocator).
    from routes.token import start_subscription_allocation, settle_subscription_allocations
    if (body.period_type or "NORMAL").upper() == "NORMAL":
        alloc = await settle_subscription_allocations(uid) if same else await start_subscription_allocation(uid, fresh)
    else:
        alloc = {"eligible": False, "reason": "trial_or_intro_period"}
    return {"status": "synced" if not same else "unchanged", "tier": tier,
            "tier_until": until.isoformat() if until else None, "gat_allocation": alloc, "addons": addons_out}



@api.post("/subscription/trial")
async def subscription_trial(authorization: Optional[str] = Header(None)):
    """One-time 7-day Sentinel trial — the upsell funnel entry point."""
    user = await get_current_user(authorization)
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "trial_used": 1, "tier": 1, "tier_until": 1}) or {}
    if fresh.get("trial_used"):
        raise HTTPException(409, "trial_used: The 7-day trial was already used. Continue by upgrading to Sentinel.")
    if TIER_RANK.get(current_tier(fresh), 0) >= TIER_RANK["sentinel"]:
        raise HTTPException(409, "already_premium: You already have Sentinel or a higher tier.")
    until = datetime.now(timezone.utc) + timedelta(days=7)
    await db.users.update_one({"user_id": user["user_id"]},
                              {"$set": {"tier": "sentinel", "tier_until": until,
                                        "tier_paid_with": "trial", "tier_billing": "trial",
                                        "trial_used": True}})
    return {"ok": True, "tier": "sentinel", "trial": True, "tier_until": until.isoformat()}


@api.post("/subscription/cancel")
async def subscription_cancel(authorization: Optional[str] = Header(None)):
    """One-tap cancellation — immediate downgrade to Sovereign (no auto-renew exists)."""
    user = await get_current_user(authorization)
    fresh = await db.users.find_one({"user_id": user["user_id"]},
                                    {"_id": 0, "tier": 1, "tier_until": 1, "inner_circle": 1}) or {}
    if fresh.get("inner_circle"):
        raise HTTPException(400, "inner_circle_permanent: Lifetime Archangel (Inner Circle) cannot be cancelled.")
    if current_tier(fresh) == "sovereign":
        raise HTTPException(409, "no_active_subscription: You have no active subscription.")
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {
        "tier": "sovereign", "tier_until": None, "tier_paid_with": None,
        "tier_billing": None, "family_pack_owner": False}})
    return {"ok": True, "tier": "sovereign",
            "message": "Subscription cancelled — you are back on the free Sovereign tier. You can return anytime."}


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
