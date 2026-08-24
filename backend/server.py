from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from starlette.middleware.cors import CORSMiddleware

from core import api, db, client, logger, init_storage
# Importing route modules registers their endpoints on the shared `api` router.
from routes import auth, health, family, hunter, legacy  # noqa: F401

app = FastAPI(title="Guardian Health & Angel API")
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

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
    except Exception as e:
        logger.warning(f"index setup: {e}")
    try:
        await run_in_threadpool(init_storage)
    except Exception as e:
        logger.warning(f"storage init at startup failed (non-fatal): {e}")

@app.on_event("shutdown")
async def shutdown():
    client.close()
