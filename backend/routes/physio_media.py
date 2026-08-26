# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""PHYSIO EXPERT VIDEOS — founder/user-uploaded massage & rehab videos attached to Physio-AI guides.
Founder uploads are GLOBAL (visible to every user — Founder's Expert Series);
regular user uploads are private to their own rehab."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, Header, UploadFile, File, Form, Response
from fastapi.concurrency import run_in_threadpool

from core import api, db, clean, get_current_user, APP_NAME, put_object_sync, get_object_sync

MAX_VIDEO = 100 * 1024 * 1024  # 100 MB


@api.post("/physio/videos")
async def physio_video_upload(
    file: UploadFile = File(...),
    guide_id: str = Form(...),
    title: str = Form(""),
    authorization: Optional[str] = Header(None),
):
    user = await get_current_user(authorization)
    data = await file.read()
    if not data:
        raise HTTPException(400, "empty file")
    if len(data) > MAX_VIDEO:
        raise HTTPException(400, "File too large (max 100MB)")
    video_id = uuid.uuid4().hex
    ctype = file.content_type or "video/mp4"
    path = f"{APP_NAME}/physio/{user['user_id']}/{video_id}.mp4"
    await run_in_threadpool(put_object_sync, path, data, ctype)
    doc = {"video_id": video_id, "user_id": user["user_id"],
           "guide_id": guide_id.strip()[:60], "title": title.strip()[:120] or "Expertné video",
           "author_name": user.get("name") or "Expert",
           "is_global": bool(user.get("is_founder")),
           "content_type": ctype, "size": len(data),
           "storage_path": path, "created_at": datetime.now(timezone.utc)}
    await db.physio_videos.insert_one(doc.copy())
    return {"ok": True, "video": clean(doc)}


@api.get("/physio/videos")
async def physio_videos_list(guide_id: Optional[str] = None,
                             authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    q: dict = {"$or": [{"user_id": user["user_id"]}, {"is_global": True}]}
    if guide_id:
        q["guide_id"] = guide_id
    rows = await db.physio_videos.find(q, {"_id": 0}).sort("created_at", -1).to_list(50)
    for r in rows:
        r["mine"] = r["user_id"] == user["user_id"]
    return {"videos": rows}


@api.get("/physio/videos/{video_id}/file")
async def physio_video_file(video_id: str, token: Optional[str] = None,
                            authorization: Optional[str] = Header(None)):
    if not authorization and token:
        authorization = f"Bearer {token}"
    user = await get_current_user(authorization)
    v = await db.physio_videos.find_one(
        {"video_id": video_id,
         "$or": [{"user_id": user["user_id"]}, {"is_global": True}]}, {"_id": 0})
    if not v:
        raise HTTPException(404, "Video not found")
    try:
        content, ctype = await run_in_threadpool(get_object_sync, v["storage_path"])
    except Exception as ex:
        raise HTTPException(502, f"Storage read failed: {ex}")
    return Response(content=content, media_type=ctype or v.get("content_type") or "video/mp4",
                    headers={"Accept-Ranges": "bytes", "Cache-Control": "private, max-age=86400"})


@api.delete("/physio/videos/{video_id}")
async def physio_video_delete(video_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.physio_videos.delete_one({"video_id": video_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Video not found or not yours")
    return {"ok": True}
