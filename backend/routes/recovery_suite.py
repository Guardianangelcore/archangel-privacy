# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Sovereign Recovery Suite + Social 2FA.

Three lockout-recovery options (Social Recovery via guardians, QR Talisman,
Passkeys placeholder) and a guardian push-handshake on every new login
(Social 2FA — SAFE mode: informational handshake, non-blocking)."""
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid, hashlib

from core import api, db, clean, get_current_user, send_push

# ---------------- GUARDIANS ----------------
class GuardianIn(BaseModel):
    contact: str  # email or DID of an existing Guardian user

@api.get("/recovery-suite/guardians")
async def guardians_list(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.guardians.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(10)
    return {"guardians": rows}

@api.post("/recovery-suite/guardians")
async def guardian_add(body: GuardianIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    c = body.contact.strip()
    target = await db.users.find_one({"$or": [{"email": c}, {"did": c}]}, {"_id": 0})
    if not target:
        raise HTTPException(404, "User with this email / DID does not exist in the Guardian network.")
    if target["user_id"] == user["user_id"]:
        raise HTTPException(400, "You cannot be your own guardian.")
    dup = await db.guardians.find_one({"user_id": user["user_id"], "guardian_user_id": target["user_id"]})
    if dup:
        raise HTTPException(409, "This guardian is already added.")
    g = {"guardian_id": uuid.uuid4().hex, "user_id": user["user_id"],
         "guardian_user_id": target["user_id"], "guardian_name": target.get("name") or target["email"],
         "guardian_email": target["email"], "created_at": datetime.now(timezone.utc)}
    await db.guardians.insert_one(g.copy())
    try:
        await send_push(recipients=[target["user_id"]],
                        data={"title": "🛡️ YOU HAVE BECOME A GUARDIAN",
                              "message": f"{user.get('name') or 'User'} has appointed you as an account recovery guardian (Social Recovery + 2FA).",
                              "action_url": "/recovery-suite"})
    except Exception:
        pass
    return clean(g)

@api.delete("/recovery-suite/guardians/{guardian_id}")
async def guardian_delete(guardian_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.guardians.delete_one({"guardian_id": guardian_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Guardian not found")
    remaining = await db.guardians.count_documents({"user_id": user["user_id"]})
    if remaining == 0:
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"social_2fa_enabled": False}})
    return {"ok": True}


# ---------------- STATUS / SECURITY SCORE ----------------
@api.get("/recovery-suite/status")
async def recovery_status(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    g = await db.guardians.count_documents({"user_id": uid})
    tal = await db.talismans.find_one({"user_id": uid}, {"_id": 0, "created_at": 1})
    keys = await db.passkeys.find({"user_id": uid}, {"_id": 0}).to_list(5)
    fresh = await db.users.find_one({"user_id": uid}, {"_id": 0, "social_2fa_enabled": 1})
    score = (25 if g else 0) + (25 if tal else 0) + (25 if keys else 0) + (25 if (fresh or {}).get("social_2fa_enabled") else 0)
    return {"guardians": g, "social_recovery_ready": g >= 1,
            "talisman_ready": bool(tal), "talisman_created_at": (tal or {}).get("created_at"),
            "passkeys": keys, "passkey_ready": bool(keys),
            "social_2fa_enabled": bool((fresh or {}).get("social_2fa_enabled")),
            "security_score": score}


# ---------------- SOCIAL 2FA (guardian push-handshake, SAFE non-blocking) ----------------
class TwoFaIn(BaseModel):
    enabled: bool

@api.patch("/recovery-suite/social-2fa")
async def social_2fa_toggle(body: TwoFaIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if body.enabled:
        g = await db.guardians.count_documents({"user_id": user["user_id"]})
        if g == 0:
            raise HTTPException(409, "Please add at least one guardian first.")
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"social_2fa_enabled": body.enabled}})
    return {"social_2fa_enabled": body.enabled}


async def notify_login_handshake(user_doc: dict, session_token: str) -> None:
    """Called from /auth/session — creates a guardian handshake for every new
    login when Social 2FA is on. SAFE mode: informs guardians instantly without
    blocking the session (hard-block = Phase 3)."""
    if not user_doc.get("social_2fa_enabled"):
        return
    guardians = await db.guardians.find({"user_id": user_doc["user_id"]}, {"_id": 0}).to_list(10)
    if not guardians:
        return
    now = datetime.now(timezone.utc)
    hs = {"handshake_id": uuid.uuid4().hex, "user_id": user_doc["user_id"],
          "user_name": user_doc.get("name") or user_doc.get("email"),
          "session_tail": session_token[-6:], "status": "pending",
          "created_at": now, "expires_at": now + timedelta(minutes=15)}
    await db.login_handshakes.insert_one(hs.copy())
    try:
        await send_push(recipients=[g["guardian_user_id"] for g in guardians],
                        data={"title": "🔐 SOCIAL 2FA — NEW SIGN-IN",
                              "message": f"{hs['user_name']} has just signed in (…{hs['session_tail']}). Please confirm that it is them.",
                              "action_url": "/recovery-suite"})
    except Exception:
        pass
    try:
        from routes.swarm import bus_publish
        await bus_publish("auth.social_2fa_handshake", "sovereign_guard",
                          {"user": user_doc["user_id"][:8], "handshake": hs["handshake_id"]})
    except Exception:
        pass


@api.get("/recovery-suite/2fa/pending")
async def twofa_pending(authorization: Optional[str] = Header(None)):
    """Handshakes waiting for MY confirmation (I am the guardian)."""
    user = await get_current_user(authorization)
    wards = await db.guardians.find({"guardian_user_id": user["user_id"]}, {"_id": 0, "user_id": 1}).to_list(20)
    ward_ids = [w["user_id"] for w in wards]
    if not ward_ids:
        return {"pending": []}
    rows = await db.login_handshakes.find(
        {"user_id": {"$in": ward_ids}, "status": "pending"}, {"_id": 0}).sort("created_at", -1).to_list(10)
    return {"pending": rows}

class ConfirmIn(BaseModel):
    legit: bool = True

@api.post("/recovery-suite/2fa/{handshake_id}/confirm")
async def twofa_confirm(handshake_id: str, body: ConfirmIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    hs = await db.login_handshakes.find_one({"handshake_id": handshake_id}, {"_id": 0})
    if not hs:
        raise HTTPException(404, "Handshake not found")
    is_guardian = await db.guardians.find_one({"user_id": hs["user_id"], "guardian_user_id": user["user_id"]})
    if not is_guardian:
        raise HTTPException(403, "You are not a guardian of this user.")
    if hs["status"] != "pending":
        raise HTTPException(409, f"Handshake is already in the '{hs['status']}' state.")
    new_status = "confirmed" if body.legit else "flagged"
    await db.login_handshakes.update_one(
        {"handshake_id": handshake_id},
        {"$set": {"status": new_status, "confirmed_by": user["user_id"],
                  "confirmed_at": datetime.now(timezone.utc)}})
    if not body.legit:
        await db.security_events.insert_one({
            "event_id": uuid.uuid4().hex, "kind": "suspicious_login", "severity": "critical",
            "detail": f"A guardian flagged the sign-in (…{hs['session_tail']}) of user {hs['user_name']} as SUSPICIOUS.",
            "at": datetime.now(timezone.utc)})
        try:
            await send_push(recipients=[hs["user_id"]],
                            data={"title": "🚨 SUSPICIOUS SIGN-IN",
                                  "message": "Your guardian flagged a new sign-in as suspicious. We recommend signing out of all devices.",
                                  "action_url": "/recovery-suite"})
        except Exception:
            pass
    try:
        from routes.swarm import bus_publish
        await bus_publish("auth.social_2fa_result", "sovereign_guard",
                          {"handshake": handshake_id, "result": new_status})
    except Exception:
        pass
    return {"ok": True, "status": new_status}


# ---------------- SOCIAL RECOVERY (locked-out flow, public initiate/poll) ----------------
class RecoveryInitIn(BaseModel):
    identifier: str  # email or DID

@api.post("/recovery-suite/social/initiate")
async def social_recovery_initiate(body: RecoveryInitIn):
    ident = body.identifier.strip()
    user = await db.users.find_one({"$or": [{"email": ident}, {"did": ident}]}, {"_id": 0})
    if not user:
        raise HTTPException(404, "Account not found.")
    guardians = await db.guardians.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(10)
    if len(guardians) < 2:
        raise HTTPException(409, "no_guardians: Social recovery needs at least 2 guardians — use QR Talizman or Passkey.")
    now = datetime.now(timezone.utc)
    needed = 2   # a single guardian must never be able to take over an account
    req = {"req_id": uuid.uuid4().hex, "user_id": user["user_id"], "needed": needed,
           "approvals": [], "status": "pending", "token_delivered": False,
           "created_at": now, "expires_at": now + timedelta(hours=24)}
    await db.recovery_requests.insert_one(req.copy())
    try:
        await send_push(recipients=[g["guardian_user_id"] for g in guardians],
                        data={"title": "🆘 ACCOUNT RECOVERY REQUEST",
                              "message": f"{user.get('name') or user['email']} is requesting Social Recovery. Approve only if you are sure it is him/her.",
                              "action_url": "/recovery-suite"})
    except Exception:
        pass
    return {"req_id": req["req_id"], "needed": needed, "guardians_notified": len(guardians)}

@api.get("/recovery-suite/social/requests")
async def social_recovery_requests(authorization: Optional[str] = Header(None)):
    """Pending recovery requests where I am a guardian."""
    user = await get_current_user(authorization)
    wards = await db.guardians.find({"guardian_user_id": user["user_id"]}, {"_id": 0, "user_id": 1}).to_list(20)
    ward_ids = [w["user_id"] for w in wards]
    if not ward_ids:
        return {"requests": []}
    rows = await db.recovery_requests.find(
        {"user_id": {"$in": ward_ids}, "status": "pending"},
        {"_id": 0, "recovery_token": 0}).sort("created_at", -1).to_list(10)
    for r in rows:
        u = await db.users.find_one({"user_id": r["user_id"]}, {"_id": 0, "name": 1, "email": 1})
        r["user_name"] = (u or {}).get("name") or (u or {}).get("email")
    return {"requests": rows}

@api.post("/recovery-suite/social/{req_id}/approve")
async def social_recovery_approve(req_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    req = await db.recovery_requests.find_one({"req_id": req_id}, {"_id": 0})
    if not req:
        raise HTTPException(404, "Request not found")
    if req["status"] != "pending":
        raise HTTPException(409, f"The request is in status '{req['status']}'.")
    is_guardian = await db.guardians.find_one({"user_id": req["user_id"], "guardian_user_id": user["user_id"]})
    if not is_guardian:
        raise HTTPException(403, "You are not a guardian of this user.")
    if user["user_id"] in req["approvals"]:
        raise HTTPException(409, "You have already approved.")
    approvals = req["approvals"] + [user["user_id"]]
    upd = {"approvals": approvals}
    if len(approvals) >= req["needed"]:
        token = f"recov-{uuid.uuid4().hex}"
        upd.update({"status": "approved", "recovery_token": token, "approved_at": datetime.now(timezone.utc)})
        await db.user_sessions.insert_one({
            "session_token": token, "user_id": req["user_id"], "recovered": True,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(days=7)})
    await db.recovery_requests.update_one({"req_id": req_id}, {"$set": upd})
    try:
        from routes.swarm import bus_publish
        await bus_publish("recovery.social_approval", "sovereign_guard",
                          {"req": req_id, "approvals": len(approvals), "needed": req["needed"]})
    except Exception:
        pass
    return {"ok": True, "approvals": len(approvals), "needed": req["needed"],
            "status": "approved" if len(approvals) >= req["needed"] else "pending"}

@api.get("/recovery-suite/social/{req_id}/status")
async def social_recovery_poll(req_id: str):
    """Public poll for the locked-out device. Delivers the one-time recovery
    session token exactly once after guardian quorum approves."""
    req = await db.recovery_requests.find_one({"req_id": req_id}, {"_id": 0})
    if not req:
        raise HTTPException(404, "Request not found")
    out = {"status": req["status"], "approvals": len(req["approvals"]), "needed": req["needed"]}
    if req["status"] == "approved" and not req.get("token_delivered"):
        await db.recovery_requests.update_one({"req_id": req_id}, {"$set": {"token_delivered": True}})
        user = await db.users.find_one({"user_id": req["user_id"]}, {"_id": 0, "password_hash": 0})
        out.update({"session_token": req["recovery_token"], "user": user})
    return out


# ---------------- QR TALISMAN (printable offline recovery key) ----------------
@api.post("/recovery-suite/talisman")
async def talisman_generate(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    secret = uuid.uuid4().hex + uuid.uuid4().hex
    await db.talismans.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"secret_hash": hashlib.sha256(secret.encode()).hexdigest(),
                  "created_at": datetime.now(timezone.utc), "used_at": None}},
        upsert=True)
    payload = f"GA-TALISMAN|{user['did']}|{secret}"
    return {"payload": payload, "did": user["did"],
            "note": "Print the QR and store it in the vault / wallet. The old talisman has been invalidated. The code will be shown ONLY ONCE."}

class TalismanRedeemIn(BaseModel):
    did: str
    secret: str

@api.post("/recovery-suite/talisman/redeem")
async def talisman_redeem(body: TalismanRedeemIn):
    user = await db.users.find_one({"did": body.did.strip()}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(404, "Account not found.")
    tal = await db.talismans.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not tal or tal.get("secret_hash") != hashlib.sha256(body.secret.strip().encode()).hexdigest():
        raise HTTPException(401, "Invalid talisman.")
    if tal.get("used_at"):
        raise HTTPException(409, "The talisman has already been used — generate a new one.")
    await db.talismans.update_one({"user_id": user["user_id"]},
                                  {"$set": {"used_at": datetime.now(timezone.utc)}})
    token = f"talis-{uuid.uuid4().hex}"
    await db.user_sessions.insert_one({
        "session_token": token, "user_id": user["user_id"], "recovered": True,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7)})
    await db.security_events.insert_one({
        "event_id": uuid.uuid4().hex, "kind": "talisman_redeemed", "severity": "warning",
        "detail": f"QR Talizman used to recover account {user['user_id'][:8]}… — talisman invalidated once-only.",
        "at": datetime.now(timezone.utc)})
    try:
        await send_push(recipients=[user["user_id"]],
                        data={"title": "🔑 TALISMAN USED",
                              "message": "Your QR Talizman has just restored access to the account. If it was not you, contact the guardians immediately.",
                              "action_url": "/recovery-suite"})
    except Exception:
        pass
    return {"session_token": token, "user": user}


# ---------------- PASSKEYS (functional placeholder — real WebAuthn in native build) ----------------
class PasskeyIn(BaseModel):
    device_name: str = "Moje zariadenie"

@api.post("/recovery-suite/passkey/register")
async def passkey_register(body: PasskeyIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    cred = {"cred_id": uuid.uuid4().hex, "user_id": user["user_id"],
            "device_name": body.device_name.strip()[:60],
            "algorithm": "ES256 (WebAuthn placeholder — native biometrics after build)",
            "simulated": True, "created_at": datetime.now(timezone.utc)}
    await db.passkeys.insert_one(cred.copy())
    return clean(cred)

@api.delete("/recovery-suite/passkey/{cred_id}")
async def passkey_delete(cred_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.passkeys.delete_one({"cred_id": cred_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Passkey not found")
    return {"ok": True}
