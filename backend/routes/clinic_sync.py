# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""CLINIC SYNC — proximity data sharing (The Doctor Link).

A doctor beams a report straight into the patient's Vault via a secure
one-time QR handshake. Bluetooth/NFC proximity radar is SIMULATED (real BLE
requires a native build); the QR handshake + server relay are fully real.
"""
from fastapi import HTTPException, Header
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid, hashlib, random

from core import (
    api, db, logger, clean, get_current_user, send_push,
    APP_NAME, put_object_sync,
)
from models import Document

SYNC_TTL_MIN = 10

@api.post("/clinic-sync/session")
async def clinic_sync_create(authorization: Optional[str] = Header(None)):
    """Creates a one-time handshake code (shown as QR to the doctor)."""
    user = await get_current_user(authorization)
    code = uuid.uuid4().hex[:6].upper()
    now = datetime.now(timezone.utc)
    sess = {
        "sync_id": uuid.uuid4().hex, "code": code,
        "user_id": user["user_id"], "did": user["did"],
        "patient_label": (user.get("name") or user["email"]).split(" ")[0],
        "qr_payload": f"GA-CLINIC-SYNC|{code}",
        "status": "waiting", "received_docs": [],
        "created_at": now, "expires_at": now + timedelta(minutes=SYNC_TTL_MIN),
    }
    # one active session per user
    await db.clinic_sync_sessions.delete_many({"user_id": user["user_id"], "status": "waiting"})
    await db.clinic_sync_sessions.insert_one(sess.copy())
    return clean(sess)

@api.get("/clinic-sync/session")
async def clinic_sync_status(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    sess = await db.clinic_sync_sessions.find_one({"user_id": user["user_id"]}, {"_id": 0}, sort=[("created_at", -1)])
    if not sess:
        return {}
    exp = sess["expires_at"]
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if sess["status"] == "waiting" and exp < datetime.now(timezone.utc):
        sess["status"] = "expired"
        await db.clinic_sync_sessions.update_one({"sync_id": sess["sync_id"]}, {"$set": {"status": "expired"}})
    return clean(sess)

class BeamIn(BaseModel):
    clinic_name: str
    doctor_name: Optional[str] = ""
    title: str
    report_text: str = Field(min_length=10, max_length=20000)

@api.post("/clinic-sync/beam/{code}")
async def clinic_sync_beam(code: str, body: BeamIn):
    """PUBLIC doctor-side endpoint — the clinic scans the patient's QR and
    beams the report. No patient credentials ever leave the phone."""
    sess = await db.clinic_sync_sessions.find_one({"code": code.upper(), "status": "waiting"}, {"_id": 0})
    if not sess:
        raise HTTPException(404, "Invalid or expired sync code")
    exp = sess["expires_at"]
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < datetime.now(timezone.utc):
        await db.clinic_sync_sessions.update_one({"sync_id": sess["sync_id"]}, {"$set": {"status": "expired"}})
        raise HTTPException(410, "Sync code expired")

    # materialize the report as a vault document
    doc_id = uuid.uuid4().hex
    content = body.report_text.encode()
    path = f"{APP_NAME}/clinic-sync/{sess['user_id']}/{doc_id}.txt"
    try:
        await run_in_threadpool(put_object_sync, path, content, "text/plain")
    except Exception as e:
        logger.error(f"clinic sync storage failed: {e}")
        raise HTTPException(502, "Storage upload failed")
    doc = Document(
        doc_id=doc_id, user_id=sess["user_id"],
        title=f"🏥 {body.title}"[:120],
        file_name=f"clinic_report_{doc_id[:8]}.txt",
        content_type="text/plain", size=len(content),
        storage_path=path, hash=hashlib.sha256(content).hexdigest(),
    ).model_dump()
    doc["extracted_text"] = body.report_text
    doc["source"] = f"clinic_sync:{body.clinic_name}"
    await db.documents.insert_one(doc.copy())

    received = {"doc_id": doc_id, "title": body.title, "clinic_name": body.clinic_name,
                "doctor_name": body.doctor_name or "", "at": datetime.now(timezone.utc).isoformat()}
    await db.clinic_sync_sessions.update_one(
        {"sync_id": sess["sync_id"]},
        {"$set": {"status": "received"}, "$push": {"received_docs": received}})
    try:
        await send_push(recipients=[sess["user_id"]], data={
            "title": "🏥 CLINIC SYNC", "message": f"{body.clinic_name}: {body.title} — saved to Vault",
            "action_url": "/clinic-sync"})
    except Exception as e:
        logger.warning(f"clinic sync push failed: {e}")
    return {"ok": True, "beamed": True, "doc_id": doc_id, "patient": sess["patient_label"]}

_RADAR_CLINICS = [
    ("Poliklinika Ružinov", "Cardiology · Internal Medicine"), ("ProCare Central", "General Outpatient Clinic"),
    ("Nemocnica Bory", "Radiology · MRI"), ("GA Labs Ortho Clinic", "Private Outpatient Clinic"),
    ("Alpha Medical Lab", "Laboratory Results"),
]

@api.get("/clinic-sync/radar")
async def clinic_sync_radar(authorization: Optional[str] = Header(None)):
    """SIMULATED BLE/NFC proximity radar — real radio requires a native build."""
    user = await get_current_user(authorization)
    rng = random.Random(int(hashlib.sha256(f"{user['user_id']}{datetime.now(timezone.utc).strftime('%Y%m%d%H')}".encode()).hexdigest(), 16))
    n = rng.randint(2, 4)
    picks = rng.sample(_RADAR_CLINICS, n)
    return {"simulated": True,
            "transport": "BLE / NFC (simulation — real radio in native build)",
            "nearby": [{"clinic": c, "dept": d, "distance_m": rng.randint(3, 40), "signal": rng.choice(["strong", "medium"])} for c, d in picks]}

class SimulateBeamIn(BaseModel):
    clinic_name: Optional[str] = "Poliklinika Ružinov"

@api.post("/clinic-sync/simulate-beam")
async def clinic_sync_simulate(body: SimulateBeamIn, authorization: Optional[str] = Header(None)):
    """Demo helper — simulates the doctor scanning the QR and beaming a report
    into the user's active session (clearly labelled simulation)."""
    user = await get_current_user(authorization)
    sess = await db.clinic_sync_sessions.find_one({"user_id": user["user_id"], "status": "waiting"}, {"_id": 0}, sort=[("created_at", -1)])
    if not sess:
        raise HTTPException(404, "No active sync session — generate a QR code first")
    demo = BeamIn(
        clinic_name=body.clinic_name or "Poliklinika Ružinov",
        doctor_name="Dr. Guardian Angel",
        title="Cardiology Finding — Checkup",
        report_text=("SIMULATED REPORT (Clinic Sync demo)\n\n"
                     "The patient underwent a follow-up cardiology examination. ECG: sinus rhythm, 72/min. "
                     "BP 128/82 mmHg. Echocardiography: EF 60 %, no regurgitations. "
                     "Recommendation: continue the prescribed medication, checkup in 6 months, "
                     "or sooner if symptoms occur. Exercise 30 min daily."),
    )
    return await clinic_sync_beam(sess["code"], demo)
