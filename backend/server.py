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
from routes import auth, health, family, hunter, legacy, neural, gateway, origin, token, swarm, orchestrator, insurance, recommend, news, subscription, paramedic, gigs, interactions, refunds, recovery_suite, compass, globalnet, medic, bioscan, longevity, enviro, mosaic, demo, wealth, seal, lens, clinic_sync, agent, uhp, arbitrage, liquidity, ascension, founder, geo, billing, healing, physio_media, streaks, pantry, impact, silent_witness, triage, family_contacts, nearby, loyalty, demo_mode, features, store, ai_models, community_help, chain  # noqa: F401
from routes.origin import ORIGIN

app = FastAPI(title="Archangel OS API")
app.include_router(api)

@app.get("/health")
async def health_probe():
    return {"status": "ok"}

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


# ---------------------------------------------------------------------------
# TEMPORARY SOURCE EXPORT (remove before publishing). Founder session required —
# the codebase must never be downloadable anonymously from the public URL.
# ---------------------------------------------------------------------------
from fastapi import Header, HTTPException
from typing import Optional as _Opt
from core import get_current_user as _export_current_user

_EXPORT_SKIP_DIRS = {'node_modules', '.expo', '.metro-cache', 'dist', '__pycache__', '.pytest_cache', 'test_reports', '.git', 'export'}
_EXPORT_SKIP_FILES = {'memory/test_credentials.md', 'frontend/google-services.json'}   # credentials never leave the server


async def _require_founder(authorization: _Opt[str]):
    user = await _export_current_user(authorization)
    if (user.get("email") or "").lower() != "guardianangel.core@proton.me" and not user.get("inner_circle"):
        raise HTTPException(403, "founder only")
    return user


@app.get("/api/export/files")
async def export_files(authorization: _Opt[str] = Header(None)):
    """Temporary endpoint to export source file contents (founder only)."""
    await _require_founder(authorization)
    import os
    files = {}
    for root, dirs, filenames in os.walk("/app"):
        dirs[:] = [d for d in dirs if d not in _EXPORT_SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(('.py', '.tsx', '.ts', '.json', '.js', '.md', '.txt', '.cfg')):
                filepath = os.path.join(root, fn)
                relpath = os.path.relpath(filepath, "/app")
                if relpath in _EXPORT_SKIP_FILES:
                    continue
                try:
                    files[relpath] = open(filepath, 'r').read()
                except Exception:
                    pass
    return {"files": files, "count": len(files)}


@app.get("/api/export/key-files")
async def export_key_files(authorization: _Opt[str] = Header(None)):
    """Export only the most important files (founder only)."""
    await _require_founder(authorization)
    import os
    key_paths = [
        "frontend/app.json", "frontend/package.json", "frontend/babel.config.js",
        "frontend/tsconfig.json", "frontend/app/_layout.tsx", "frontend/app/index.tsx",
        "frontend/app/(tabs)/_layout.tsx",
        "backend/server.py", "backend/requirements.txt", "backend/models.py",
        "backend/core.py", "backend/content.py", "backend/emailer.py",
        "backend/perplexity.py", "backend/db_indexes.py",
        "README.md", "PROOF_OF_ORIGIN.md", "design_guidelines.json",
    ]
    routes_dir = "/app/backend/routes"
    if os.path.isdir(routes_dir):
        for f in sorted(os.listdir(routes_dir)):
            if f.endswith('.py'):
                key_paths.append(f"backend/routes/{f}")
    files = {}
    for rp in key_paths:
        fp = os.path.join("/app", rp)
        if os.path.isfile(fp):
            try:
                files[rp] = open(fp, 'r').read()
            except Exception:
                pass
    return {"files": files, "count": len(files)}
