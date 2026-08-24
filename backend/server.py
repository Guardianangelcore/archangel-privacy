# Copyright © 2026 Guardian Angel. All Rights Reserved.
# This source code and its logic are the sole property of Guardian Angel.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from starlette.middleware.cors import CORSMiddleware

from core import api, db, client, logger, init_storage
# Importing route modules registers their endpoints on the shared `api` router.
from routes import auth, health, family, hunter, legacy, neural, gateway, origin  # noqa: F401
from routes.origin import ORIGIN

app = FastAPI(title="Guardian Health & Angel API")
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Hidden digital watermark — every response is signed as the original
# 'Guardian Angel' build (Proof of Origin, see /api/origin). Implemented as a
# raw ASGI middleware (zero overhead under high concurrency).
_WM_BUILD = ORIGIN.get("build", "GA-ORIGINAL").encode()
_WM_DID = ORIGIN.get("did", "").encode()

class GuardianWatermarkASGI:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_wrapped(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.append((b"x-guardian-origin", _WM_BUILD))
                if _WM_DID:
                    headers.append((b"x-origin-did", _WM_DID))
            await send(message)

        await self.app(scope, receive, send_wrapped)

app.add_middleware(GuardianWatermarkASGI)

@app.on_event("startup")
async def startup():
    try:
        await db.users.create_index("email", unique=True)
        await db.users.create_index("user_id", unique=True)
        await db.users.create_index("did", unique=True)
        await db.user_sessions.create_index("session_token", unique=True)
        await db.user_sessions.create_index("expires_at", expireAfterSeconds=0)
        await db.documents.create_index([("user_id", 1), ("uploaded_at", -1)])
        await db.waitlist.create_index([("user_id", 1), ("created_at", -1)])
        # High-velocity performance indexes (global scale prep)
        await db.calendar_events.create_index([("user_id", 1), ("date", -1)])
        await db.health_drops.create_index([("user_id", 1), ("created_at", -1)])
        await db.recovery.create_index("user_id")
        await db.pulse_requests.create_index([("target_user", 1), ("created_at", -1)])
        await db.pharmacy_watches.create_index("user_id")
        await db.gateway_grants.create_index("token", unique=True)
        await db.gateway_audit.create_index([("user_id", 1), ("at", -1)])
        await db.sentinel_signals.create_index([("at", -1)])
        await db.sentinel_signals.create_index([("anon", 1), ("kind", 1), ("at", -1)])
        await db.stripe_donations.create_index("session_id", unique=True)
        await db.marketplace_sales.create_index([("user_id", 1), ("offer_id", 1)], unique=True)
    except Exception as e:
        logger.warning(f"index setup: {e}")
    # Anchor Proof of Origin record (idempotent — one record per codebase hash)
    try:
        if ORIGIN.get("codebase_sha256"):
            await db.ip_protection.update_one(
                {"kind": "proof_of_origin", "codebase_sha256": ORIGIN["codebase_sha256"]},
                {"$setOnInsert": {**ORIGIN, "kind": "proof_of_origin", "anchored": True}},
                upsert=True,
            )
    except Exception as e:
        logger.warning(f"origin anchor: {e}")
    try:
        await run_in_threadpool(init_storage)
    except Exception as e:
        logger.warning(f"storage init at startup failed (non-fatal): {e}")

@app.on_event("shutdown")
async def shutdown():
    client.close()
