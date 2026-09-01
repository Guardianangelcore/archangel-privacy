# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
"""FAMILY CONTACTS — encrypted emergency phone book for the Family Shield pillar.

Phone numbers are encrypted at rest (Fernet, key in backend/.env CONTACTS_ENC_KEY).
Endpoints: POST/GET /family-contacts · DELETE /family-contacts/{id} ·
POST /family-contacts/{id}/sos (silent emergency alert log + best-effort push).
"""
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid, os, re

from cryptography.fernet import Fernet
from core import api, db, logger, get_current_user, send_push

RELATIONS = {"partner": "Partner", "rodic": "Parent", "surodenec": "Sibling",
             "dieta": "Child", "priatel": "Friend", "lekar": "Doctor", "ine": "Other"}
_PHONE_RE = re.compile(r"^\+?[0-9 ()\-]{6,20}$")

_fernet: Optional[Fernet] = None


def _enc() -> Fernet:
    global _fernet
    if _fernet is None:
        key = os.environ.get("CONTACTS_ENC_KEY", "").strip()
        if not key:
            raise HTTPException(500, "CONTACTS_ENC_KEY missing")
        _fernet = Fernet(key.encode())
    return _fernet


def _view(doc: dict) -> dict:
    try:
        phone = _enc().decrypt(doc["phone_enc"].encode()).decode()
    except Exception:
        phone = "•••"
    return {"contact_id": doc["contact_id"], "name": doc["name"],
            "phone": phone, "relation": doc["relation"],
            "relation_label": RELATIONS.get(doc["relation"], "Other"),
            "created_at": doc.get("created_at")}


class ContactIn(BaseModel):
    name: str
    phone: str
    relation: str = "ine"


@api.post("/family-contacts")
async def add_family_contact(body: ContactIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    name = (body.name or "").strip()
    phone = (body.phone or "").strip()
    if not name or len(name) > 80:
        raise HTTPException(400, "Name is required (max 80 characters).")
    if not _PHONE_RE.match(phone):
        raise HTTPException(400, "Invalid phone number — use format +421 900 000 000.")
    relation = body.relation if body.relation in RELATIONS else "ine"
    count = await db.family_contacts.count_documents({"user_id": user["user_id"]})
    if count >= 20:
        raise HTTPException(400, "Maximum of 20 contacts.")
    doc = {"contact_id": uuid.uuid4().hex, "user_id": user["user_id"], "name": name,
           "phone_enc": _enc().encrypt(phone.encode()).decode(), "relation": relation,
           "created_at": datetime.now(timezone.utc)}
    await db.family_contacts.insert_one(doc.copy())
    return _view(doc)


@api.get("/family-contacts")
async def list_family_contacts(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.family_contacts.find(
        {"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", 1).to_list(50)
    return {"contacts": [_view(r) for r in rows], "total": len(rows)}


@api.delete("/family-contacts/{contact_id}")
async def delete_family_contact(contact_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.family_contacts.delete_one(
        {"contact_id": contact_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Contact not found.")
    return {"ok": True}


@api.post("/family-contacts/{contact_id}/sos")
async def sos_family_contact(contact_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    row = await db.family_contacts.find_one(
        {"contact_id": contact_id, "user_id": user["user_id"]}, {"_id": 0})
    if not row:
        raise HTTPException(404, "Contact not found.")
    now = datetime.now(timezone.utc)
    phone = _view(row)["phone"]

    # SOS message — include a live GPS map link when the user's position is known.
    who = user.get("name") or "Guardian Angel"
    geo = user.get("geo") or {}
    lat, lng = user.get("lat") or geo.get("lat"), user.get("lng") or geo.get("lng")
    loc = f" My location: https://maps.google.com/?q={lat},{lng}" if lat and lng else ""
    sms_body = f"🆘 SOS! I need help.{loc} — {who} (Guardian Health & Angel)"

    # TWILIO — real SMS when credentials are configured; graceful device-composer
    # fallback otherwise (keys arrive later → this switches on automatically).
    sms_sent, channel, sms_error = False, "device", None
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    tok = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    frm = os.environ.get("TWILIO_FROM_NUMBER", "").strip()
    if sid and tok and frm:
        try:
            from fastapi.concurrency import run_in_threadpool
            from twilio.rest import Client as TwilioClient

            def _send():
                to = "+" + re.sub(r"[^0-9]", "", phone) if not phone.strip().startswith("+") \
                    else "+" + re.sub(r"[^0-9]", "", phone)
                return TwilioClient(sid, tok).messages.create(to=to, from_=frm, body=sms_body)

            msg = await run_in_threadpool(_send)
            sms_sent, channel = True, "twilio"
            logger.info(f"twilio sos sent sid={msg.sid}")
        except Exception as e:
            sms_error = str(e)[:200]
            logger.error(f"twilio sos failed: {e}")

    await db.sos_events.insert_one({
        "event_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "contact_id": contact_id, "contact_name": row["name"],
        "kind": "family_sos", "channel": channel, "sms_sent": sms_sent, "at": now})
    try:
        await send_push([user["user_id"]], {
            "title": "🆘 SOS SENT",
            "body": f"Emergency signal for contact {row['name']} was recorded.",
        }, idempotency_key=f"sos-{contact_id}-{now.strftime('%Y%m%d%H%M')}")
    except Exception as e:
        logger.warning(f"sos push failed: {e}")
    message = (f"SOS SMS sent to {row['name']} via Twilio." if sms_sent
               else f"SOS for {row['name']} recorded. Call if possible.")
    return {"ok": True, "contact": row["name"], "phone": phone,
            "sms_sent": sms_sent, "channel": channel, "sms_error": sms_error,
            "message": message, "sms_body": sms_body}
