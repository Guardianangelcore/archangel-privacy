# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Angel Gig Network — hyper-local help requests inside the Solidarity Hub.
Able-bodied users earn GA-T (Proof-of-Help) or cash for helping seniors nearby."""
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid

from core import api, db, clean, get_current_user, send_push

GIG_KINDS = {
    "transport": "Ride to a clinic / office",
    "grocery": "Food shopping",
    "pharmacy": "Medication pickup",
    "company": "Company / walk",
    "tech": "Help with phone / TV",
}

class GigIn(BaseModel):
    kind: str = "transport"
    title: str
    note: Optional[str] = ""
    city: str = ""
    reward_gat: float = 10.0
    reward_eur: float = 0.0

@api.get("/gigs/nearby")
async def gigs_nearby(city: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    q: dict = {"status": "open"}
    if city:
        q["city"] = {"$regex": city, "$options": "i"}
    gigs = await db.gigs.find(q, {"_id": 0}).sort("created_at", -1).to_list(30)
    mine = await db.gigs.find({"$or": [{"user_id": user["user_id"]}, {"taker_id": user["user_id"]}]},
                              {"_id": 0}).sort("created_at", -1).to_list(20)
    return {"open": gigs, "mine": mine, "kinds": GIG_KINDS}

@api.post("/gigs")
async def gig_create(body: GigIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if body.kind not in GIG_KINDS:
        raise HTTPException(400, f"kind must be one of {list(GIG_KINDS)}")
    if not body.title.strip():
        raise HTTPException(400, "title required")
    gig = {"gig_id": uuid.uuid4().hex, "user_id": user["user_id"],
           "requester_name": (user.get("name") or "Sused").split(" ")[0],
           "kind": body.kind, "title": body.title.strip()[:100], "note": (body.note or "")[:300],
           "city": body.city.strip()[:60], "reward_gat": round(min(body.reward_gat, 50.0), 1),
           "reward_eur": round(min(body.reward_eur, 100.0), 2),
           "status": "open", "taker_id": None, "created_at": datetime.now(timezone.utc)}
    await db.gigs.insert_one(gig.copy())
    # Hyper-local broadcast (demo: all other users; Phase 3: geo-filtered)
    try:
        others = await db.users.find({"user_id": {"$ne": user["user_id"]}}, {"_id": 0, "user_id": 1}).to_list(50)
        eur_part = f" + {gig['reward_eur']} €" if gig["reward_eur"] else ""
        if others:
            await send_push(recipients=[o["user_id"] for o in others],
                            data={"title": "🤝 A NEIGHBOR NEEDS HELP",
                                  "message": f"{GIG_KINDS[body.kind]}: {gig['title']} · reward {gig['reward_gat']} GA-T{eur_part}",
                                  "action_url": "/gigs"})
    except Exception:
        pass
    return clean(gig)

@api.post("/gigs/{gig_id}/accept")
async def gig_accept(gig_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    gig = await db.gigs.find_one({"gig_id": gig_id}, {"_id": 0})
    if not gig:
        raise HTTPException(404, "Gig not found")
    if gig["status"] != "open":
        raise HTTPException(409, "Gig is no longer available")
    if gig["user_id"] == user["user_id"]:
        raise HTTPException(400, "You cannot accept your own request")
    await db.gigs.update_one({"gig_id": gig_id},
                             {"$set": {"status": "taken", "taker_id": user["user_id"],
                                       "taker_name": (user.get("name") or "Anjel").split(" ")[0],
                                       "taken_at": datetime.now(timezone.utc)}})
    try:
        await send_push(recipients=[gig["user_id"]],
                        data={"title": "😇 THE ANGEL ACCEPTED YOUR REQUEST",
                              "message": f"{gig['title']} — the helper is on the way. After completion, confirm the reward.",
                              "action_url": "/gigs"})
    except Exception:
        pass
    return {"ok": True, "status": "taken"}

@api.post("/gigs/{gig_id}/complete")
async def gig_complete(gig_id: str, authorization: Optional[str] = Header(None)):
    """Requester confirms completion → taker earns GA-T (Proof-of-Help)."""
    user = await get_current_user(authorization)
    gig = await db.gigs.find_one({"gig_id": gig_id}, {"_id": 0})
    if not gig:
        raise HTTPException(404, "Gig not found")
    if gig["user_id"] != user["user_id"]:
        raise HTTPException(403, "Completion is confirmed by the requester")
    if gig["status"] != "taken":
        raise HTTPException(409, "Gig nie je v stave 'taken'")
    await db.gigs.update_one({"gig_id": gig_id},
                             {"$set": {"status": "done", "completed_at": datetime.now(timezone.utc)}})
    reward = None
    try:
        from routes.token import award_tokens
        reward = await award_tokens(gig["taker_id"], "proof_of_help", f"Angel Gig: {gig['title'][:50]}")
    except Exception:
        pass
    # Hard-coded 15% Guardian Tax on cash rewards → foundation treasury
    if gig.get("reward_eur"):
        try:
            from routes.subscription import record_revenue
            await record_revenue("guardian_tax", float(gig["reward_eur"]) * 0.15, user["user_id"],
                                 {"source": "gigs", "gig_id": gig_id, "gross": gig["reward_eur"]})
        except Exception:
            pass
    try:
        from routes.swarm import bus_publish
        await bus_publish("gigs.completed", "solidarity",
                          {"gig_id": gig_id, "kind": gig["kind"], "gat_rewarded": bool(reward)})
        await send_push(recipients=[gig["taker_id"]],
                        data={"title": "💎 REWARD FOR HELPING",
                              "message": f"Thank you! {''+ str(reward['amount']) + ' GA-T credited.' if reward else 'GA-T daily limit — reward tomorrow.'}",
                              "action_url": "/token"})
    except Exception:
        pass
    return {"ok": True, "status": "done", "gat_reward": reward["amount"] if reward else 0}
