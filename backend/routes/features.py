# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# MEGA-BATCH backend: User Type (B) · Health Card hub (C) · Multi-Agent system (E) ·
# Pay-per-feature (H) · Creator royalty 5 % (I).
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid, asyncio

from emergentintegrations.llm.chat import LlmChat, UserMessage
from core import api, db, logger, clean, get_current_user, EMERGENT_LLM_KEY, AI_COMPLIANCE_NOTE, apply_watermark
from routes.subscription import get_active_tier, current_tier, TIER_RANK
from routes.ai_models import resolve_model, FAST_MODEL

# ------------------------------------------------------------------ B. USER TYPE
USER_TYPES = ("adult", "senior", "clinician", "responder", "child")

class UserTypeIn(BaseModel):
    user_type: str

@api.put("/me/user-type")
async def set_user_type(body: UserTypeIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if body.user_type not in USER_TYPES:
        raise HTTPException(400, f"user_type must be one of {USER_TYPES}")
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"user_type": body.user_type}})
    return {"user_type": body.user_type}

# ------------------------------------------------------------------ C. HEALTH CARD HUB
class HealthCardIn(BaseModel):
    birth_cert_doc_id: Optional[str] = None
    eu_card_doc_id: Optional[str] = None
    insurance_number: Optional[str] = None
    insurer: Optional[str] = None
    contracts: Optional[List[dict]] = None   # [{title, insurer, number, doc_id, valid_until}]

@api.get("/health-card")
async def health_card_get(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    card = await db.health_cards.find_one({"user_id": uid}, {"_id": 0}) or {"user_id": uid, "contracts": []}
    docs = await db.documents.find({"user_id": uid}, {"_id": 0, "storage_path": 0}).sort("uploaded_at", -1).to_list(200)
    claims = await db.insurance_claims.find({"user_id": uid}, {"_id": 0}).sort("created_at", -1).to_list(50)
    by_id = {d["doc_id"]: d for d in docs}
    card["birth_cert"] = by_id.get(card.get("birth_cert_doc_id") or "")
    card["eu_card"] = by_id.get(card.get("eu_card_doc_id") or "")
    card["documents"] = [{**d, "has_text": bool(d.get("extracted_text")), "has_translation": bool(d.get("plain_language")),
                          "extracted_text": (d.get("extracted_text") or "")[:600], "plain_language": (d.get("plain_language") or "")[:600]}
                         for d in docs]
    card["claims"] = claims
    return clean(card)

@api.put("/health-card")
async def health_card_put(body: HealthCardIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    await db.health_cards.update_one({"user_id": user["user_id"]}, {"$set": {**upd, "updated_at": datetime.now(timezone.utc)}}, upsert=True)
    return await health_card_get(authorization)

# ------------------------------------------------------------------ H+I. PAY-PER-FEATURE · CREATOR ROYALTY
# One-off purchasable features (GA-T, permanent). Bunker Mode and Mesh SMS are NOT here on purpose:
# they are subscription-tier features (see TIER_FEATURES) and can never be bought one-off.
FEATURES = {
    "ghost_mode": {"label": "Ghost Mode", "eur": 2.99, "gat": 30.0, "tier": "sentinel"},
    "analyst":    {"label": "Analyst Agent", "eur": 3.99, "gat": 40.0, "tier": "sentinel"},
}
# Subscription-only features with a GRACE PERIOD after the paid tier expires:
#  • emergency core (Bunker Mode, Mesh SMS): Sentinel+, stay active 90 days after expiry, cached offline by the app
#  • Bio-Digital Twin: Archangel only, standard 14-day grace
# After grace → the user is simply a free (Sovereign) user again; the app itself is never locked.
TIER_FEATURES = {
    "bunker":   {"label": "Bunker Mode", "tier": "sentinel", "grace_days": 90, "emergency": True},
    "mesh_sms": {"label": "Mesh SMS", "tier": "sentinel", "grace_days": 90, "emergency": True},
    "twin":     {"label": "Bio-Digital Twin", "tier": "archangel", "grace_days": 14, "emergency": False},
}
CREATOR_CUT = 0.05


def _as_dt(v) -> Optional[datetime]:
    if not v:
        return None
    if isinstance(v, str):
        try:
            v = datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None
    return v if v.tzinfo else v.replace(tzinfo=timezone.utc)


async def tier_feature_states(user_id: str) -> dict:
    """{feature_id: {unlocked, in_grace, grace_until, offline_until, ...}} for every TIER_FEATURES entry.
    `offline_until` tells the app how long it may honour the entitlement WITHOUT contacting the server
    (active subscription → now + grace; lapsed but inside grace → grace end)."""
    fresh = await db.users.find_one({"user_id": user_id}, {"_id": 0, "tier": 1, "tier_until": 1, "inner_circle": 1, "demo_until": 1,
                                                          "features_owned": 1, "tier_last_paid": 1, "tier_last_until": 1}) or {}
    now = datetime.now(timezone.utc)
    active = current_tier(fresh)
    owned = fresh.get("features_owned") or []
    # last PAID tier + its expiry (kept after a downgrade so the grace period can be computed)
    paid_tier = fresh.get("tier") if (fresh.get("tier") or "sovereign") != "sovereign" else fresh.get("tier_last_paid")
    paid_until = _as_dt(fresh.get("tier_until")) if (fresh.get("tier") or "sovereign") != "sovereign" else _as_dt(fresh.get("tier_last_until"))
    out = {}
    for k, f in TIER_FEATURES.items():
        need = TIER_RANK[f["tier"]]
        unlocked = TIER_RANK.get(active, 0) >= need
        grace_until = None
        in_grace = False
        if paid_tier and TIER_RANK.get(paid_tier, 0) >= need and paid_until:
            grace_until = paid_until + timedelta(days=f["grace_days"])
            if not unlocked and now <= grace_until:
                unlocked, in_grace = True, True
        if k in owned:                      # grandfathered one-off purchases from before the subscription-only rule
            unlocked = True
        offline_until = None
        if unlocked:
            offline_until = grace_until if in_grace else (now + timedelta(days=f["grace_days"]))
        out[k] = {"id": k, **f, "unlocked": unlocked, "in_grace": in_grace, "purchasable": False,
                  "grace_until": grace_until.isoformat() if grace_until else None,
                  "offline_until": offline_until.isoformat() if offline_until else None}
    return out


async def require_feature(user: dict, feature: str) -> dict:
    """402 `<tier>_required: …` unless the tier feature is active (paid tier, grace period or grandfathered)."""
    st = (await tier_feature_states(user["user_id"]))[feature]
    if not st["unlocked"]:
        f = TIER_FEATURES[feature]
        raise HTTPException(402, f"{f['tier']}_required: {f['label']} is part of the {f['tier'].capitalize()} plan"
                                 f"{' and above' if f['tier'] != 'archangel' else ' (exclusive)'} — upgrade to unlock.")
    return st

async def creator_royalty(source: str, amount: float, currency: str, payer_id: str, meta: dict) -> Optional[dict]:
    """5 % of every GA-T sale / pay-per-feature purchase → the creator account (users.creator_account=True).
    GA-T royalties are credited to the creator's token account; EUR royalties are booked as earnings."""
    creator = await db.users.find_one({"creator_account": True}, {"_id": 0, "user_id": 1})
    cut = round(amount * CREATOR_CUT, 4)
    if not creator or cut <= 0:
        return None
    log = {"royalty_id": uuid.uuid4().hex, "creator_id": creator["user_id"], "source": source, "currency": currency,
           "gross": round(amount, 4), "cut": cut, "rate": CREATOR_CUT, "payer_id": payer_id, "meta": meta,
           "at": datetime.now(timezone.utc)}
    await db.creator_royalties.insert_one(log.copy())
    if currency == "gat":
        await db.token_accounts.update_one({"user_id": creator["user_id"]}, {"$inc": {"balance": cut}}, upsert=True)
    return clean(log)

@api.get("/features/catalog")
async def features_catalog(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "features_owned": 1}) or {}
    tier = await get_active_tier(user["user_id"])
    owned = fresh.get("features_owned") or []
    one_off = [{"id": k, **v, "purchasable": True, "unlocked": k in owned or TIER_RANK.get(tier, 0) >= TIER_RANK[v["tier"]]} for k, v in FEATURES.items()]
    tier_feats = list((await tier_feature_states(user["user_id"])).values())
    return {"tier": tier, "owned": owned, "features": one_off + tier_feats}

async def has_feature(user: dict, feature: str) -> bool:
    if feature in TIER_FEATURES:
        return (await tier_feature_states(user["user_id"]))[feature]["unlocked"]
    f = FEATURES[feature]
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "features_owned": 1}) or {}
    if feature in (fresh.get("features_owned") or []):
        return True
    return TIER_RANK.get(await get_active_tier(user["user_id"]), 0) >= TIER_RANK[f["tier"]]

class BuyIn(BaseModel):
    feature: str
    currency: str = "gat"   # gat | eur

@api.post("/features/buy")
async def features_buy(body: BuyIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if body.feature in TIER_FEATURES:
        raise HTTPException(400, f"{TIER_FEATURES[body.feature]['label']} is subscription-only ({TIER_FEATURES[body.feature]['tier'].capitalize()} plan) — it cannot be bought one-off.")
    f = FEATURES.get(body.feature)
    if not f:
        raise HTTPException(400, f"feature must be one of {list(FEATURES)}")
    uid = user["user_id"]
    fresh = await db.users.find_one({"user_id": uid}, {"_id": 0, "features_owned": 1}) or {}
    if body.feature in (fresh.get("features_owned") or []):
        return {"ok": True, "already_owned": True, "feature": body.feature}
    now = datetime.now(timezone.utc)
    if body.currency != "gat":
        # SEC: no unverified fiat path — card/IAP unlocks are only granted through a verified
        # store purchase (RevenueCat), never by a plain API call.
        raise HTTPException(400, "currency must be gat — features are bought with GA-T")
    from routes.token import debit_balance
    if not await debit_balance(uid, float(f["gat"]), spent_total=float(f["gat"])):
        raise HTTPException(402, f"insufficient_balance: You need {f['gat']:.0f} GA-T.")
    amount, cur = f["gat"], "gat"
    purchase = {"purchase_id": uuid.uuid4().hex, "user_id": uid, "feature": body.feature, "currency": cur,
                "amount": amount, "at": now}
    await db.feature_purchases.insert_one(purchase.copy())
    await db.users.update_one({"user_id": uid}, {"$addToSet": {"features_owned": body.feature}})
    royalty = await creator_royalty("pay_per_feature", amount, cur, uid, {"feature": body.feature, "purchase_id": purchase["purchase_id"]})
    return {"ok": True, "feature": body.feature, "purchase": clean(purchase), "creator_royalty": royalty}

@api.get("/creator/earnings")
async def creator_earnings(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "creator_account": 1, "is_admin": 1, "role": 1}) or {}
    if not (fresh.get("creator_account") or fresh.get("is_admin") or fresh.get("role") == "admin"):
        raise HTTPException(403, "creator account only")
    rows = await db.creator_royalties.find({}, {"_id": 0}).sort("at", -1).to_list(300)
    tot_gat = round(sum(r["cut"] for r in rows if r["currency"] == "gat"), 4)
    tot_eur = round(sum(r["cut"] for r in rows if r["currency"] == "eur"), 2)
    return {"rate": CREATOR_CUT, "total_gat": tot_gat, "total_eur": tot_eur, "count": len(rows), "log": clean(rows)}

# ------------------------------------------------------------------ E. AUTONOMOUS MULTI-AGENT SYSTEM
AGENTS = [
    {"id": "jarvis",   "name": "JARVIS",   "role": "Orchestrator · talks to you, coordinates the others", "tier": "sovereign", "icon": "planet"},
    {"id": "lens",     "name": "LENS",     "role": "OCR · photo analysis · document scan",                "tier": "guardian",  "icon": "scan"},
    {"id": "scribe",   "name": "SCRIBE",   "role": "Voice transcript · notes · archive to Health Card",    "tier": "sentinel",  "icon": "create"},
    {"id": "analyst",  "name": "ANALYST",  "role": "Medical / crisis analysis · medication interactions",  "tier": "sentinel",  "icon": "analytics"},
    {"id": "guardian", "name": "GUARDIAN", "role": "Survival protocols · evacuation · crisis answers",     "tier": "archangel", "icon": "shield"},
]
LANG_NAMES = {"sk": "Slovak", "cs": "Czech", "en": "English", "de": "German", "pl": "Polish", "hu": "Hungarian"}

async def _agent_access(user: dict) -> dict:
    tier = await get_active_tier(user["user_id"])
    rank = TIER_RANK.get(tier, 0)
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "features_owned": 1}) or {}
    owned = fresh.get("features_owned") or []
    out = {}
    for a in AGENTS:
        ok = rank >= TIER_RANK[a["tier"]] or (a["id"] == "analyst" and "analyst" in owned)
        out[a["id"]] = ok
    return {"tier": tier, "access": out, "priority": rank >= TIER_RANK["archangel"]}

@api.get("/agents/status")
async def agents_status(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    acc = await _agent_access(user)
    return {"tier": acc["tier"], "priority": acc["priority"],
            "agents": [{**a, "active": acc["access"][a["id"]]} for a in AGENTS]}

class AgentRunIn(BaseModel):
    input_type: str                 # text | photo | voice
    text: Optional[str] = None      # user text or voice transcript
    doc_id: Optional[str] = None    # vault document (photo path)
    language: str = "sk"

def _llm(tag: str, system: str, model: str):
    return LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"agents-{tag}-{uuid.uuid4().hex[:6]}", system_message=system)\
        .with_model("openai", model)

@api.post("/agents/run")
async def agents_run(body: AgentRunIn, authorization: Optional[str] = Header(None)):
    """Shared-context pipeline: LENS (OCR) → SCRIBE (archive) → ANALYST (assessment) → GUARDIAN (crisis) → JARVIS (reply).
    Each agent runs only if the user's tier / purchases unlock it; the trace shows who worked."""
    user = await get_current_user(authorization)
    uid = user["user_id"]
    acc = await _agent_access(user)
    lang = LANG_NAMES.get((body.language or user.get("language") or "sk")[:2], "English")
    strong = acc["priority"]
    # Priority tiers answer with the user's chosen ChatGPT model; others get the fast model.
    model = (await resolve_model(user)) if strong else FAST_MODEL
    ctx = {"input_type": body.input_type, "user_text": (body.text or "")[:3000], "extracted_text": "", "archived": None,
           "analysis": "", "crisis": ""}
    trace = []
    now = datetime.now(timezone.utc)

    # LENS
    if body.doc_id:
        if not acc["access"]["lens"]:
            trace.append({"agent": "lens", "status": "locked", "detail": "Lens requires the Guardian Plan"})
        else:
            doc = await db.documents.find_one({"doc_id": body.doc_id, "user_id": uid}, {"_id": 0})
            if not doc:
                raise HTTPException(404, "document not found")
            from routes.health import extract_doc_text
            try:
                ctx["extracted_text"] = (await extract_doc_text(doc))[:6000]
                trace.append({"agent": "lens", "status": "done", "detail": f"OCR · {len(ctx['extracted_text'])} characters"})
            except Exception as e:
                logger.warning(f"lens ocr failed: {e}")
                trace.append({"agent": "lens", "status": "error", "detail": "OCR failed"})
    # SCRIBE
    source = ctx["extracted_text"] or ctx["user_text"]
    if acc["access"]["scribe"] and source:
        title = (ctx["user_text"] or "Scan")[:60]
        ev = {"event_id": uuid.uuid4().hex, "user_id": uid, "category": "disease" if body.doc_id else "exam",
              "title": f"📝 {title}", "date": now.date().isoformat(), "notes": source[:500],
              "source": "agents", "doc_id": body.doc_id, "child_id": None, "created_at": now}
        await db.calendar_events.insert_one(ev.copy())
        ctx["archived"] = ev["event_id"]
        trace.append({"agent": "scribe", "status": "done", "detail": "Archived to the Health Card timeline"})
    elif source:
        trace.append({"agent": "scribe", "status": "locked", "detail": "Scribe requires the Sentinel Plan"})
    # ANALYST
    if acc["access"]["analyst"] and source:
        try:
            resp = await _llm("analyst", f"You are ANALYST, a careful medical & crisis analyst. Assess the text (medications, interactions, red flags, "
                              f"what matters). Bullet points, max 120 words, in {lang}. Never invent data." + AI_COMPLIANCE_NOTE, model)\
                .send_message(UserMessage(text=source[:6000]))
            ctx["analysis"] = str(resp)
            trace.append({"agent": "analyst", "status": "done", "detail": "Assessment ready"})
        except Exception as e:
            logger.warning(f"analyst failed: {e}")
            trace.append({"agent": "analyst", "status": "error", "detail": "AI unavailable"})
    elif source:
        trace.append({"agent": "analyst", "status": "locked", "detail": "Analyst requires Sentinel — or buy it for €3.99"})
    # GUARDIAN (crisis keywords)
    crisis = any(k in (ctx["user_text"] or "").lower() for k in ("evaku", "kryt", "bunker", "poplach", "blackout", "výpadok", "krízov", "shelter", "evacuat", "attack", "flood", "povod"))
    if crisis:
        if acc["access"]["guardian"]:
            try:
                resp = await _llm("guardian", f"You are GUARDIAN, a survival & evacuation protocol agent. Give a numbered, calm 5-step action plan "
                                  f"for the situation, max 100 words, in {lang}." + AI_COMPLIANCE_NOTE, model).send_message(UserMessage(text=ctx["user_text"][:2000]))
                ctx["crisis"] = str(resp)
                trace.append({"agent": "guardian", "status": "done", "detail": "Protocol prepared"})
            except Exception as e:
                logger.warning(f"guardian failed: {e}")
        else:
            trace.append({"agent": "guardian", "status": "locked", "detail": "Guardian agent requires the Archangel Plan"})
    # JARVIS — always
    sys = (f"You are JARVIS, the orchestrator of the Archangel OS agents, speaking to {user.get('name') or 'the user'}. "
           f"Reply ONLY in {lang}, warm, concise (max 150 words), plain text. Summarise what the agents found and answer the user. "
           "If a step is locked, mention it in one short sentence." + AI_COMPLIANCE_NOTE)
    brief = (f"USER INPUT ({body.input_type}): {ctx['user_text'] or '-'}\n\nLENS OCR TEXT: {ctx['extracted_text'][:3000] or '-'}\n\n"
             f"ANALYST: {ctx['analysis'] or '-'}\n\nGUARDIAN: {ctx['crisis'] or '-'}\n\nTRACE: {trace}")
    try:
        reply = apply_watermark(str(await _llm("jarvis", sys, model).send_message(UserMessage(text=brief))))
    except Exception as e:
        logger.error(f"jarvis orchestrator failed: {e}")
        raise HTTPException(502, "AI unavailable")
    trace.append({"agent": "jarvis", "status": "done", "detail": "Reply composed"})
    await db.agent_conversations.insert_many([
        {"conv_id": uuid.uuid4().hex, "user_id": uid, "role": "user", "text": (ctx["user_text"] or f"[{body.input_type}]")[:1000], "at": now},
        {"conv_id": uuid.uuid4().hex, "user_id": uid, "role": "agent", "text": reply[:2000], "mood": "calm", "at": now}])
    return {"reply": reply, "trace": trace, "extracted_text": ctx["extracted_text"][:1500], "analysis": ctx["analysis"], "model": model,
            "crisis": ctx["crisis"], "archived_event_id": ctx["archived"], "tier": acc["tier"]}
