# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Drug Interaction Guard — AI safety scan of the Medicine Cabinet inventory
for harmful drug-to-drug interactions with urgent warnings."""
from fastapi import HTTPException, Header
from typing import Optional
from datetime import datetime, timezone
import hashlib, json, re

from core import api, db, logger, get_current_user, send_push, EMERGENT_LLM_KEY, LlmChat, UserMessage

@api.post("/cabinet/interactions/scan")
async def interactions_scan(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    items = await db.cabinet.find({"user_id": uid, "category": {"$in": ["medication", "prescription", "other"]}},
                                  {"_id": 0, "name": 1}).to_list(100)
    reminders = await db.med_reminders.find({"user_id": uid}, {"_id": 0, "name": 1}).to_list(50)
    names = sorted({i["name"].strip() for i in items + reminders if i.get("name", "").strip()})
    if len(names) < 2:
        return {"interactions": [], "meds_scanned": names,
                "note": "Interaction check requires at least 2 medications in the medicine cabinet / reminders."}
    sig = hashlib.sha256("|".join(names).lower().encode()).hexdigest()
    cached = await db.interaction_scans.find_one({"user_id": uid, "sig": sig}, {"_id": 0})
    if cached:
        return {**cached["result"], "cached": True}
    if not EMERGENT_LLM_KEY:
        raise HTTPException(503, "AI unavailable")
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY, session_id=f"ddi-{uid[:8]}",
        system_message=(
            "You are a pharmacology safety screener. Given a list of medication/supplement names "
            "(Slovak/Czech/English brand or generic), identify clinically relevant drug-drug interactions. "
            "Output ONLY valid JSON: {\"interactions\": [{\"pair\": [\"A\",\"B\"], \"severity\": \"high\"|\"moderate\"|\"low\", "
            "\"warning\": \"1-2 sentence warning in the user's language\", \"advice\": \"short action in the user's language\"}]}. "
            "Only include real, known interactions. Empty list if none. Be conservative, never invent."
        ),
    ).with_model("anthropic", "claude-sonnet-5")
    try:
        resp = await chat.send_message(UserMessage(text="Medicine cabinet: " + ", ".join(names)))
        m = re.search(r"\{.*\}", resp, re.S)
        data = json.loads(m.group(0)) if m else {"interactions": []}
    except Exception as e:
        logger.error(f"interaction scan error: {e}")
        raise HTTPException(502, "AI service unavailable")
    inter = data.get("interactions", [])[:20]
    result = {"interactions": inter, "meds_scanned": names,
              "scanned_at": datetime.now(timezone.utc).isoformat(),
              "disclaimer": "AI screening — does not replace the pharmacist or the doctor. If in doubt, contact the pharmacist."}
    await db.interaction_scans.update_one({"user_id": uid, "sig": sig},
                                          {"$set": {"result": result, "at": datetime.now(timezone.utc)}}, upsert=True)
    high = [i for i in inter if i.get("severity") == "high"]
    if high:
        try:
            await send_push(recipients=[uid],
                            data={"title": "⚠️ RISKY DRUG COMBINATION",
                                  "message": f"{' + '.join(high[0]['pair'])}: {high[0]['warning'][:100]}",
                                  "action_url": "/medicine-cabinet"})
        except Exception:
            pass
    return result
