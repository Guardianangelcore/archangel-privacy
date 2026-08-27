# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# SILENT WITNESS — decentralised, encrypted, ambient-audio recording.
# Trigger: hidden gesture (frontend) — e.g. triple-tap the back of the phone.
# Recording chunks are streamed straight into the Sovereign Vault (Emergent Object
# Storage) so that even if the device is destroyed, the evidence survives.
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import Header, HTTPException, UploadFile, File, Form
from fastapi.concurrency import run_in_threadpool

from core import api, db, clean, get_current_user, logger, put_object_sync, APP_NAME, send_push


@api.post("/silent-witness/session")
async def sw_open(authorization: Optional[str] = Header(None)):
    """Open a new Silent Witness session. Returns session_id for chunk uploads."""
    user = await get_current_user(authorization)
    session_id = uuid.uuid4().hex
    doc = {
        "session_id": session_id,
        "user_id": user["user_id"],
        "did": user.get("did"),
        "opened_at": datetime.now(timezone.utc),
        "closed_at": None,
        "chunk_count": 0,
        "total_bytes": 0,
        "status": "active",
    }
    await db.silent_witness.insert_one(doc.copy())
    # Notify the user's Inner Circle silently — they should know a recording started.
    try:
        # find guardian links (both sides) — same pattern as voice-circle
        peer_ids = []
        async for l in db.guardians.find({"user_id": user["user_id"]}, {"_id": 0, "guardian_user_id": 1}):
            if l.get("guardian_user_id"):
                peer_ids.append(l["guardian_user_id"])
        if peer_ids:
            await send_push(recipients=peer_ids, data={
                "title": "🛡️ TICHÝ SVEDOK AKTÍVNY",
                "message": f"{user.get('name') or 'Rodinný člen'} spustil Silent Witness. Nahrávanie sa streamuje do Trezoru.",
                "action_url": "/silent-witness",
            })
    except Exception as e:
        logger.warning(f"silent-witness push: {e}")
    return {"session_id": session_id, "status": "active"}


@api.post("/silent-witness/{session_id}/chunk")
async def sw_chunk(
    session_id: str,
    file: UploadFile = File(...),
    index: int = Form(0),
    authorization: Optional[str] = Header(None),
):
    user = await get_current_user(authorization)
    sess = await db.silent_witness.find_one({"session_id": session_id, "user_id": user["user_id"]}, {"_id": 0})
    if not sess:
        raise HTTPException(404, "Session not found")
    if sess.get("status") != "active":
        raise HTTPException(409, "Session already closed")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty chunk")
    if len(data) > 5 * 1024 * 1024:  # 5MB per chunk hard limit
        raise HTTPException(400, "Chunk too large (max 5MB)")
    path = f"{APP_NAME}/silent-witness/{user['user_id']}/{session_id}/{index:04d}.webm"
    try:
        await run_in_threadpool(put_object_sync, path, data, file.content_type or "audio/webm")
    except Exception as e:
        logger.error(f"sw chunk store: {e}")
        raise HTTPException(502, "Storage failed")
    await db.silent_witness.update_one(
        {"session_id": session_id},
        {
            "$inc": {"chunk_count": 1, "total_bytes": len(data)},
            "$push": {"chunks": {"index": index, "path": path, "size": len(data), "at": datetime.now(timezone.utc)}},
        },
    )
    return {"ok": True, "index": index, "size": len(data)}


@api.post("/silent-witness/{session_id}/close")
async def sw_close(session_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    r = await db.silent_witness.find_one_and_update(
        {"session_id": session_id, "user_id": user["user_id"], "status": "active"},
        {"$set": {"status": "closed", "closed_at": datetime.now(timezone.utc)}},
        return_document=True,
    )
    if not r:
        raise HTTPException(404, "Not found or already closed")
    r.pop("_id", None)
    return clean(r)


@api.get("/silent-witness/sessions")
async def sw_list(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.silent_witness.find(
        {"user_id": user["user_id"]},
        {"_id": 0, "chunks": 0},
    ).sort("opened_at", -1).to_list(50)
    return {"sessions": clean(rows), "count": len(rows)}
