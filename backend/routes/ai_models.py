# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
"""ChatGPT AI MODELS — user-selectable OpenAI model that powers Jarvis.

One catalog, one preference (`users.jarvis_model`). Every Jarvis surface (chat, live stream,
briefing, multi-agent pipeline) resolves the model through `resolve_model()` so a lapsed
subscription silently falls back to the default instead of failing the request.
"""
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from core import api, db, get_current_user
from routes.subscription import TIERS, TIER_RANK, get_active_tier, require_tier

PROVIDER = "openai"
DEFAULT_MODEL = "gpt-5.4"
FAST_MODEL = "gpt-5.4-mini"

# Ordered from lightest to strongest. `min_tier` = app tier needed to SELECT the model.
AI_MODELS = [
    {"id": "gpt-5.4-mini",  "name": "GPT-5.4 Mini",  "tag": "Fastest · lightweight answers",      "min_tier": "sovereign", "speed": 3, "depth": 1},
    {"id": "gpt-5.4",       "name": "GPT-5.4",       "tag": "Balanced · recommended default",     "min_tier": "sovereign", "speed": 2, "depth": 2},
    {"id": "gpt-5.6-luna",  "name": "GPT-5.6 Luna",  "tag": "Fast · creative · latest generation", "min_tier": "guardian",  "speed": 2, "depth": 3},
    {"id": "gpt-5.6-terra", "name": "GPT-5.6 Terra", "tag": "Flagship · deepest reasoning",       "min_tier": "sentinel",  "speed": 1, "depth": 4},
]
_BY_ID = {m["id"]: m for m in AI_MODELS}


def model_info(model_id: Optional[str]) -> dict:
    return _BY_ID.get(model_id or "", _BY_ID[DEFAULT_MODEL])


async def resolve_model(user: dict) -> str:
    """The model Jarvis should answer with for this user — their pick when the tier still
    allows it, otherwise the default. Never raises."""
    pick = (user or {}).get("jarvis_model")
    m = _BY_ID.get(pick or "")
    if not m or pick == DEFAULT_MODEL:
        return DEFAULT_MODEL
    if TIER_RANK[m["min_tier"]] == 0:
        return pick
    tier = await get_active_tier(user["user_id"])
    return pick if TIER_RANK.get(tier, 0) >= TIER_RANK[m["min_tier"]] else DEFAULT_MODEL


@api.get("/ai/models")
async def ai_models(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    tier = await get_active_tier(user["user_id"])
    rank = TIER_RANK.get(tier, 0)
    selected = await resolve_model(user)
    return {
        "provider": PROVIDER, "default": DEFAULT_MODEL, "selected": selected, "tier": tier,
        "models": [{**m, "locked": rank < TIER_RANK[m["min_tier"]],
                    "min_tier_name": TIERS[m["min_tier"]]["name"], "active": m["id"] == selected}
                   for m in AI_MODELS],
    }


class SelectIn(BaseModel):
    model: str


@api.put("/ai/models/select")
async def ai_models_select(body: SelectIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    m = _BY_ID.get(body.model)
    if not m:
        raise HTTPException(400, f"model must be one of {list(_BY_ID)}")
    if TIER_RANK[m["min_tier"]] > 0:
        await require_tier(user, m["min_tier"], m["name"])
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"jarvis_model": m["id"]}})
    return {"ok": True, "selected": m["id"], "name": m["name"], "provider": PROVIDER}
