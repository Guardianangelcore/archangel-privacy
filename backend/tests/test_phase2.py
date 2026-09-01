# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Phase 2 tests: TTS, Physio, Solidarity, Respect Map, Blackout."""
import os, uuid, asyncio
from datetime import datetime, timezone, timedelta
import pytest, requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

BASE_URL = "https://physio-lang-fix.preview.emergentagent.com"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

SESSION_TOKEN = f"TEST_p2_{uuid.uuid4().hex}"
USER_ID = f"TEST_user_{uuid.uuid4().hex[:10]}"
DID = f"did:guardian:TESTP2{uuid.uuid4().hex[:18]}"
EMAIL = f"TEST_p2_{uuid.uuid4().hex[:6]}@example.com"


@pytest.fixture(scope="module")
def seed():
    async def _seed():
        c = AsyncIOMotorClient(MONGO_URL); db = c[DB_NAME]
        await db.users.insert_one({"user_id": USER_ID, "email": EMAIL, "did": DID,
            "name": "Test P2", "language": "sk", "angel_mode": False,
            "created_at": datetime.now(timezone.utc)})
        await db.user_sessions.insert_one({"session_token": SESSION_TOKEN, "user_id": USER_ID,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(days=7)})
        c.close()
    async def _td():
        c = AsyncIOMotorClient(MONGO_URL); db = c[DB_NAME]
        await db.users.delete_one({"user_id": USER_ID})
        await db.user_sessions.delete_one({"session_token": SESSION_TOKEN})
        await db.campaigns.delete_many({"user_id": USER_ID})
        await db.donations.delete_many({"donor_user_id": USER_ID})
        await db.providers.delete_many({"created_by": USER_ID})
        await db.provider_reviews.delete_many({"user_id": USER_ID})
        c.close()
    asyncio.get_event_loop().run_until_complete(_seed())
    yield {"token": SESSION_TOKEN, "user_id": USER_ID, "did": DID}
    asyncio.get_event_loop().run_until_complete(_td())


@pytest.fixture
def h(seed):
    return {"Authorization": f"Bearer {seed['token']}"}


# --- Auth gating on new endpoints ---
@pytest.mark.parametrize("m,p,pl", [
    ("post", "/api/voice/tts", {"text": "hi"}),
    ("post", "/api/physio/session", {"region": "neck"}),
    ("get", "/api/solidarity/campaigns", None),
    ("post", "/api/solidarity/campaigns", {"title": "x", "story": "y", "goal_amount": 10}),
    ("get", "/api/respect/providers", None),
    ("post", "/api/respect/providers", {"name": "x", "city": "y", "specialty": "z", "respect_score": 3}),
    ("get", "/api/blackout/snapshot", None),
])
def test_auth_required(m, p, pl):
    fn = getattr(requests, m)
    r = fn(f"{BASE_URL}{p}", json=pl) if pl is not None else fn(f"{BASE_URL}{p}")
    assert r.status_code == 401, f"{m} {p} -> {r.status_code}"


# --- Voice TTS ---
def test_tts_generate_and_stream(h):
    r = requests.post(f"{BASE_URL}/api/voice/tts", headers=h,
                      json={"text": "Ahoj, som Jarvis.", "voice": "nova", "language": "sk"},
                      timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "key" in d and "url" in d
    assert d["url"].endswith(".mp3")
    r2 = requests.get(f"{BASE_URL}{d['url']}", timeout=30)
    assert r2.status_code == 200
    assert r2.headers.get("content-type", "").startswith("audio/mpeg")
    assert len(r2.content) > 500


# --- Physio (Claude Sonnet 5) ---
def test_physio_session(h):
    r = requests.post(f"{BASE_URL}/api/physio/session", headers=h,
                      json={"region": "neck", "intensity": "light", "language": "sk"},
                      timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "routine" in d and len(d["routine"]) > 30


# --- Solidarity ---
def test_solidarity_flow(h):
    # AML (iteration 4+): campaign creation requires KYC attestation first
    r = requests.post(f"{BASE_URL}/api/aml/kyc", headers=h,
                      json={"full_name": "Test User", "birth_year": 1980,
                            "country": "SK", "declaration": True})
    assert r.status_code == 200, r.text
    r = requests.post(f"{BASE_URL}/api/solidarity/campaigns", headers=h,
                      json={"title": "TEST Solidarity", "story": "help",
                            "goal_amount": 100.0, "currency": "EUR"})
    assert r.status_code == 200, r.text
    cid = r.json()["campaign_id"]
    assert r.json()["raised_amount"] == 0.0

    r2 = requests.get(f"{BASE_URL}/api/solidarity/campaigns", headers=h)
    assert r2.status_code == 200
    assert any(c["campaign_id"] == cid for c in r2.json())

    r3 = requests.post(f"{BASE_URL}/api/solidarity/campaigns/{cid}/donate", headers=h,
                       json={"amount": 25.0, "message": "TEST"})
    assert r3.status_code == 200, r3.text
    assert r3.json().get("mocked") is True

    # Verify increment
    r4 = requests.get(f"{BASE_URL}/api/solidarity/campaigns", headers=h)
    camp = next(c for c in r4.json() if c["campaign_id"] == cid)
    assert camp["raised_amount"] == 25.0
    assert camp["supporters"] == 1


# --- Respect Map ---
def test_respect_map_aggregation(h):
    name = f"TEST Doc {uuid.uuid4().hex[:6]}"
    city = "Bratislava"
    r = requests.post(f"{BASE_URL}/api/respect/providers", headers=h,
                      json={"name": name, "city": city, "specialty": "GP",
                            "respect_score": 4, "tags": ["kind", "clear"], "review": "great"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["avg_score"] == 4.0
    assert d["review_count"] == 1

    # Second review — same name+city → aggregate
    r2 = requests.post(f"{BASE_URL}/api/respect/providers", headers=h,
                       json={"name": name, "city": city, "specialty": "GP",
                             "respect_score": 2, "tags": ["kind", "patient"], "review": "ok"})
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    assert d2["review_count"] == 2
    assert abs(d2["avg_score"] - 3.0) < 0.01
    assert set(d2["tags"]) == {"kind", "clear", "patient"}

    r3 = requests.get(f"{BASE_URL}/api/respect/providers?city={city}", headers=h)
    assert r3.status_code == 200
    assert any(p["name"] == name for p in r3.json())


# --- Blackout snapshot ---
def test_blackout_snapshot(h, seed):
    r = requests.get(f"{BASE_URL}/api/blackout/snapshot", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "generated_at" in d
    assert d["user"]["did"] == seed["did"]
    assert "emergency_profile" in d
    assert "documents_meta" in d
    assert isinstance(d["documents_meta"], list)
    assert isinstance(d["survival_tips"], list) and len(d["survival_tips"]) >= 1
