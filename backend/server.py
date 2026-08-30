# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from starlette.middleware.cors import CORSMiddleware
import asyncio

from core import api, db, client, logger, init_storage
from db_indexes import ensure_indexes
# Importing route modules registers their endpoints on the shared `api` router.
from routes import auth, health, family, hunter, legacy, neural, gateway, origin, token, swarm, orchestrator, insurance, recommend, news, subscription, paramedic, gigs, interactions, refunds, recovery_suite, compass, globalnet, medic, bioscan, longevity, enviro, mosaic, demo, wealth, seal, lens, clinic_sync, agent, uhp, arbitrage, liquidity, ascension, founder, geo, billing, healing, physio_media, achievements, pantry, impact, silent_witness, triage, family_contacts  # noqa: F401
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
    await ensure_indexes()
    # GA-T genesis + DePIN seed + autonomous swarm loop
    try:
        await token.ensure_genesis()
        await swarm.seed_depin()
        asyncio.create_task(swarm.swarm_loop())
    except Exception as e:
        logger.warning(f"tokenized ecosystem init: {e}")
    # Founder whitelist — always keep Guardian Angel canonical email on the Inner Circle
    try:
        await auth._ensure_founder_whitelist()
    except Exception as e:
        logger.warning(f"founder whitelist: {e}")
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
