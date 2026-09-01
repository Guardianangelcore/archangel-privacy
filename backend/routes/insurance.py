# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Sovereign Insurance Guard — policy dashboard, voice ingestion, neural alerts,
Solidarity micro-loan bridge. Global insurer templates for the 14-language launch."""
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid, json, re

from core import api, db, logger, clean, get_current_user, EMERGENT_LLM_KEY, LlmChat, UserMessage

POLICY_TYPES = ["health", "life", "disability", "property"]

# Global insurer quick-pick templates (per region)
INSURER_TEMPLATES = [
    {"region": "SK", "providers": ["Dôvera", "VšZP", "Union", "Allianz SK", "Generali SK", "Kooperativa"]},
    {"region": "CZ", "providers": ["VZP", "ČPZP", "OZP", "Kooperativa ČR", "Generali ČR"]},
    {"region": "EU", "providers": ["Allianz", "AXA", "Generali", "UNIQA", "Zurich"]},
    {"region": "UK", "providers": ["Bupa", "AXA Health", "Vitality", "Aviva"]},
    {"region": "US", "providers": ["UnitedHealthcare", "Aetna", "Cigna", "Blue Cross"]},
    {"region": "GLOBAL", "providers": ["Cigna Global", "Allianz Care", "IMG Global"]},
]

def _policy_status(p: dict) -> str:
    pu = p.get("paid_until") or ""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return "paid" if pu >= today else "overdue"


class PolicyIn(BaseModel):
    provider: str
    type: str = "health"
    premium_monthly: float = 0.0
    currency: str = "EUR"
    paid_until: Optional[str] = None   # YYYY-MM-DD
    note: Optional[str] = ""

@api.get("/insurance/policies")
async def insurance_policies(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    pols = await db.insurance_policies.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)
    out = [{**p, "status": _policy_status(p)} for p in pols]
    overdue = [p for p in out if p["status"] == "overdue"]
    health_active = any(p["type"] == "health" and p["status"] == "paid" for p in out)
    return {"policies": out, "overdue_count": len(overdue),
            "health_insurance_active": health_active,
            "hunter_warning": None if health_active else
            "⚠ Health insurance is not active/paid — Waitlist Hunter may have trouble with reservations with contracted doctors.",
            "microloan_suggested": bool(overdue),
            "templates": INSURER_TEMPLATES}

@api.post("/insurance/policies")
async def insurance_add(body: PolicyIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if body.type not in POLICY_TYPES:
        raise HTTPException(400, f"type must be one of {POLICY_TYPES}")
    if body.paid_until and not re.match(r"^\d{4}-\d{2}-\d{2}$", body.paid_until):
        raise HTTPException(400, "paid_until must be YYYY-MM-DD")
    pol = {"policy_id": uuid.uuid4().hex, "user_id": user["user_id"],
           "provider": body.provider.strip()[:80], "type": body.type,
           "premium_monthly": round(body.premium_monthly, 2), "currency": body.currency.upper()[:4],
           "paid_until": body.paid_until, "note": (body.note or "")[:200],
           "created_at": datetime.now(timezone.utc)}
    await db.insurance_policies.insert_one(pol.copy())
    return {**clean(pol), "status": _policy_status(pol)}

@api.put("/insurance/policies/{policy_id}")
async def insurance_update(policy_id: str, body: PolicyIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.insurance_policies.update_one(
        {"policy_id": policy_id, "user_id": user["user_id"]},
        {"$set": {"provider": body.provider.strip()[:80], "type": body.type,
                  "premium_monthly": round(body.premium_monthly, 2), "currency": body.currency.upper()[:4],
                  "paid_until": body.paid_until, "note": (body.note or "")[:200]}})
    if res.matched_count == 0:
        raise HTTPException(404, "Policy not found")
    p = await db.insurance_policies.find_one({"policy_id": policy_id}, {"_id": 0})
    return {**p, "status": _policy_status(p)}

@api.delete("/insurance/policies/{policy_id}")
async def insurance_delete(policy_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.insurance_policies.delete_one({"policy_id": policy_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Policy not found")
    return {"ok": True}


class IngestIn(BaseModel):
    text: str

@api.post("/insurance/ingest")
async def insurance_ingest(body: IngestIn, authorization: Optional[str] = Header(None)):
    """Voice/text ingestion: 'Jarvis, I have health insurance with Dôvera, paid until December.'
    → LLM parses provider/type/paid_until and upserts the policy record."""
    user = await get_current_user(authorization)
    if not body.text.strip():
        raise HTTPException(400, "text required")
    if not EMERGENT_LLM_KEY:
        raise HTTPException(503, "AI unavailable")
    year = datetime.now(timezone.utc).year
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY, session_id=f"ins-{user['user_id'][:8]}",
        system_message=(
            "You extract insurance policy facts from a short Slovak/Czech/English utterance. "
            "Output ONLY valid JSON, no markdown: "
            '{"provider": str|null, "type": "health"|"life"|"disability"|"property"|null, '
            '"paid_until": "YYYY-MM-DD"|null, "premium_monthly": number|null, "found": true|false}. '
            f"If only a month is mentioned (e.g. 'December'), use the last day of that month in {year} "
            f"(or {year + 1} if the month already passed). Default type is health when unclear but insurance-related."
        ),
    ).with_model("anthropic", "claude-sonnet-5")
    try:
        resp = await chat.send_message(UserMessage(text=body.text[:600]))
        m = re.search(r"\{.*\}", resp, re.S)
        data = json.loads(m.group(0)) if m else {"found": False}
    except Exception as e:
        logger.error(f"insurance ingest error: {e}")
        raise HTTPException(502, "AI service unavailable")
    if not data.get("found") or not data.get("provider"):
        return {"found": False, "hint": "Try: 'I have health insurance with Dôvera, paid until December.'"}
    ptype = data.get("type") if data.get("type") in POLICY_TYPES else "health"
    existing = await db.insurance_policies.find_one(
        {"user_id": user["user_id"], "type": ptype, "provider": {"$regex": f"^{re.escape(data['provider'])}$", "$options": "i"}})
    fields = {"provider": data["provider"][:80], "type": ptype,
              "paid_until": data.get("paid_until"),
              "premium_monthly": round(float(data.get("premium_monthly") or 0), 2)}
    if existing:
        await db.insurance_policies.update_one({"policy_id": existing["policy_id"]}, {"$set": fields})
        pol = await db.insurance_policies.find_one({"policy_id": existing["policy_id"]}, {"_id": 0})
        action = "updated"
    else:
        pol = {"policy_id": uuid.uuid4().hex, "user_id": user["user_id"], **fields,
               "currency": "EUR", "note": "via Jarvis voice ingest",
               "created_at": datetime.now(timezone.utc)}
        await db.insurance_policies.insert_one(pol.copy())
        pol = clean(pol)
        action = "created"
    return {"found": True, "action": action, "policy": {**pol, "status": _policy_status(pol)}}
