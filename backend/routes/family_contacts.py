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

from cryptography.fernet import Fernet, MultiFernet
from core import api, db, logger, get_current_user, send_push

RELATIONS = {"partner": "Partner", "rodic": "Parent", "surodenec": "Sibling",
             "dieta": "Child", "priatel": "Friend", "lekar": "Doctor", "ine": "Other"}
_PHONE_RE = re.compile(r"^\+?[0-9 ()\-]{6,20}$")

_fernet: Optional[MultiFernet] = None


def _enc() -> MultiFernet:
    """Primary key CONTACTS_ENC_KEY encrypts; CONTACTS_ENC_KEY_PREV (optional, rotation) only decrypts legacy tokens."""
    global _fernet
    if _fernet is None:
        key = os.environ.get("CONTACTS_ENC_KEY", "").strip()
        if not key:
            raise HTTPException(500, "CONTACTS_ENC_KEY missing")
        keys = [Fernet(key.encode())]
        prev = os.environ.get("CONTACTS_ENC_KEY_PREV", "").strip()
        if prev and prev != key:
            keys.append(Fernet(prev.encode()))
        _fernet = MultiFernet(keys)
    return _fernet


async def rotate_contact_keys() -> int:
    """Startup task: re-encrypt every stored phone with the PRIMARY key (no-op unless CONTACTS_ENC_KEY_PREV is set)."""
    if not os.environ.get("CONTACTS_ENC_KEY_PREV", "").strip():
        return 0
    enc = _enc()
    n = 0
    async for doc in db.family_contacts.find({"phone_enc": {"$exists": True}}, {"_id": 1, "phone_enc": 1}):
        try:
            rotated = enc.rotate(doc["phone_enc"].encode()).decode()
        except Exception:
            continue   # undecryptable token — left untouched, shows as "•••"
        if rotated != doc["phone_enc"]:
            await db.family_contacts.update_one({"_id": doc["_id"]}, {"$set": {"phone_enc": rotated, "key_rotated_at": datetime.now(timezone.utc)}})
            n += 1
    return n


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


def _sos_body(user: dict, lat: Optional[float] = None, lng: Optional[float] = None) -> str:
    """SOS message — includes a live GPS map link when the position is known."""
    who = user.get("name") or "Guardian Angel"
    geo = user.get("geo") or {}
    lat = lat if lat is not None else (user.get("lat") or geo.get("lat"))
    lng = lng if lng is not None else (user.get("lng") or geo.get("lng"))
    loc = f" My live location: https://maps.google.com/?q={lat},{lng}" if lat and lng else ""
    return f"🆘 SOS! I need help.{loc} — {who} (Archangel OS)"


async def _send_sms(phone: str, body: str) -> tuple:
    """TWILIO — real SMS when credentials are configured; graceful device-composer
    fallback otherwise (keys arrive later → this switches on automatically).
    Returns (sent, channel, error)."""
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    tok = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    frm = os.environ.get("TWILIO_FROM_NUMBER", "").strip()
    if not (sid and tok and frm):
        return False, "device", None
    try:
        from fastapi.concurrency import run_in_threadpool
        from twilio.rest import Client as TwilioClient

        def _send():
            to = "+" + re.sub(r"[^0-9]", "", phone)
            return TwilioClient(sid, tok).messages.create(to=to, from_=frm, body=body)

        msg = await run_in_threadpool(_send)
        logger.info(f"twilio sos sent sid={msg.sid}")
        return True, "twilio", None
    except Exception as e:
        logger.error(f"twilio sos failed: {e}")
        return False, "device", str(e)[:200]


class SosBroadcastIn(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    source: str = "fall_verify"   # fall_verify | hold | keyword | manual


@api.post("/sos/broadcast")
async def sos_broadcast(body: SosBroadcastIn, authorization: Optional[str] = Header(None)):
    """GUARDIAN SOS ALERT — fired once the emergency loop is CONFIRMED (countdown
    elapsed, hold-to-SOS or explicit keyword). Texts every family contact the live
    GPS location (Twilio when configured, otherwise the app opens the device SMS
    composer pre-filled), pushes linked guardians, and records the event."""
    user = await get_current_user(authorization)
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    lat = body.lat if body.lat is not None and -90 <= body.lat <= 90 else None
    lng = body.lng if body.lng is not None and -180 <= body.lng <= 180 else None
    if lat is not None and lng is not None:
        await db.users.update_one({"user_id": uid}, {"$set": {"lat": lat, "lng": lng, "last_sos_at": now}})
    sms_body = _sos_body(user, lat, lng)
    maps_url = f"https://maps.google.com/?q={lat},{lng}" if lat is not None and lng is not None else None

    contacts, sms_sent_count = [], 0
    async for row in db.family_contacts.find({"user_id": uid}, {"_id": 0}).sort("created_at", 1):
        phone = _view(row)["phone"]
        sent, channel, err = await _send_sms(phone, sms_body)
        sms_sent_count += int(sent)
        contacts.append({"contact_id": row["contact_id"], "name": row["name"], "phone": phone,
                         "relation": row.get("relation"), "sms_sent": sent, "channel": channel, "error": err})

    # Linked guardians who have the app → instant push with the map link.
    guardian_ids = [g["guardian_user_id"] async for g in
                    db.guardians.find({"user_id": uid}, {"_id": 0, "guardian_user_id": 1})]
    push_sent = 0
    if guardian_ids:
        try:
            await send_push(guardian_ids, {
                "title": f"🆘 SOS — {user.get('name') or 'your family member'} needs help",
                "body": (f"Live location: {maps_url}" if maps_url else "Location unavailable — please call now."),
                "data": {"deeplink": "/family", "maps_url": maps_url, "user_id": uid},
            }, idempotency_key=f"sos-broadcast-{uid}-{now.strftime('%Y%m%d%H%M')}")
            push_sent = len(guardian_ids)
        except Exception as e:
            logger.warning(f"sos broadcast push failed: {e}")

    await db.sos_events.insert_one({
        "event_id": uuid.uuid4().hex, "user_id": uid, "kind": "sos_broadcast", "source": body.source,
        "lat": lat, "lng": lng, "contacts": len(contacts), "sms_sent": sms_sent_count,
        "push_sent": push_sent, "at": now})
    return {"ok": True, "contacts": contacts, "sms_sent": sms_sent_count, "push_sent": push_sent,
            "maps_url": maps_url, "sms_body": sms_body,
            "channel": "twilio" if sms_sent_count else "device"}


@api.post("/family-contacts/{contact_id}/sos")
async def sos_family_contact(contact_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    row = await db.family_contacts.find_one(
        {"contact_id": contact_id, "user_id": user["user_id"]}, {"_id": 0})
    if not row:
        raise HTTPException(404, "Contact not found.")
    now = datetime.now(timezone.utc)
    phone = _view(row)["phone"]

    sms_body = _sos_body(user)
    sms_sent, channel, sms_error = await _send_sms(phone, sms_body)

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
