"""Seed a test session for frontend testing, print token."""
import asyncio, os, uuid
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")
MONGO = os.environ["MONGO_URL"]
DB = os.environ["DB_NAME"]

TOKEN = f"TEST_fe_{uuid.uuid4().hex}"
UID = f"TEST_fe_{uuid.uuid4().hex[:10]}"
DID = f"did:guardian:TESTFE{uuid.uuid4().hex[:18]}"

async def main():
    c = AsyncIOMotorClient(MONGO)
    db = c[DB]
    await db.users.insert_one({
        "user_id": UID, "email": f"{UID}@test.com", "did": DID,
        "name": "TEST FE User", "language": "sk", "angel_mode": False,
        "family_size": 3, "fall_guard": True, "inactivity_guard": True, "inactivity_hours": 8,
        "created_at": datetime.now(timezone.utc),
    })
    await db.user_sessions.insert_one({
        "session_token": TOKEN, "user_id": UID,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
    })
    c.close()
    print(f"TOKEN={TOKEN}")
    print(f"UID={UID}")

asyncio.run(main())
