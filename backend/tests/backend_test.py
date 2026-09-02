# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Backend tests for Archangel OS MVP."""
import io
import os
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") if os.environ.get("EXPO_PUBLIC_BACKEND_URL") else "https://physio-lang-fix.preview.emergentagent.com"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

SESSION_TOKEN = f"TEST_tok_{uuid.uuid4().hex}"
USER_ID = f"TEST_user_{uuid.uuid4().hex[:10]}"
DID = f"did:guardian:TEST{uuid.uuid4().hex[:20]}"
EMAIL = f"TEST_{uuid.uuid4().hex[:6]}@example.com"


@pytest.fixture(scope="module")
def seed():
    """Seed a test user + session in Mongo, teardown after."""
    async def _seed():
        c = AsyncIOMotorClient(MONGO_URL)
        db = c[DB_NAME]
        await db.users.insert_one({
            "user_id": USER_ID, "email": EMAIL, "did": DID,
            "name": "Test User", "language": "sk", "angel_mode": False,
            "created_at": datetime.now(timezone.utc),
        })
        await db.user_sessions.insert_one({
            "session_token": SESSION_TOKEN, "user_id": USER_ID,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        })
        c.close()

    async def _teardown():
        c = AsyncIOMotorClient(MONGO_URL)
        db = c[DB_NAME]
        await db.users.delete_one({"user_id": USER_ID})
        await db.user_sessions.delete_one({"session_token": SESSION_TOKEN})
        await db.emergency_profiles.delete_many({"user_id": USER_ID})
        await db.documents.delete_many({"user_id": USER_ID})
        await db.waitlist.delete_many({"user_id": USER_ID})
        await db.fall_events.delete_many({"user_id": USER_ID})
        c.close()

    asyncio.get_event_loop().run_until_complete(_seed())
    yield {"token": SESSION_TOKEN, "user_id": USER_ID, "did": DID}
    asyncio.get_event_loop().run_until_complete(_teardown())


@pytest.fixture
def auth_headers(seed):
    return {"Authorization": f"Bearer {seed['token']}"}


# --- Public / root ---
def test_root_public():
    r = requests.get(f"{BASE_URL}/api/")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("author") == "Guardian Angel Sovereign Foundation (DAO)"
    assert d.get("app") == "Archangel OS"
    assert d.get("status") == "ok"


def test_auth_session_invalid():
    r = requests.post(f"{BASE_URL}/api/auth/session", json={"session_id": "invalid_bad_id"})
    assert r.status_code == 401


# --- Protected endpoints require auth ---
@pytest.mark.parametrize("method,path,payload", [
    ("get", "/api/auth/me", None),
    ("patch", "/api/me/prefs", {}),
    ("get", "/api/vault/documents", None),
    ("get", "/api/waitlist", None),
    ("get", "/api/emergency-profile", None),
    ("post", "/api/ai/translate", {"text": "x", "language": "sk"}),
    ("post", "/api/fall-event", {"verified": True}),
])
def test_protected_endpoints_require_auth(method, path, payload):
    fn = getattr(requests, method)
    r = fn(f"{BASE_URL}{path}", json=payload) if payload is not None else fn(f"{BASE_URL}{path}")
    assert r.status_code == 401, f"{method} {path} -> {r.status_code}"


# --- Auth me ---
def test_auth_me(auth_headers, seed):
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
    assert r.status_code == 200, r.text
    u = r.json()["user"]
    assert u["did"] == seed["did"]
    assert u["language"] == "sk"
    assert u["angel_mode"] is False


# --- Prefs ---
def test_prefs_update(auth_headers):
    r = requests.patch(f"{BASE_URL}/api/me/prefs",
                       headers=auth_headers,
                       json={"language": "en", "angel_mode": True})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["language"] == "en"
    assert d["angel_mode"] is True
    # Verify persistence
    r2 = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
    assert r2.json()["user"]["language"] == "en"


# --- Emergency profile ---
def test_emergency_profile_crud(auth_headers, seed):
    r = requests.get(f"{BASE_URL}/api/emergency-profile", headers=auth_headers)
    assert r.status_code == 200

    payload = {"full_name": "TEST John Doe", "blood_type": "A+",
               "allergies": "penicillin", "medications": "aspirin",
               "conditions": "diabetes",
               "emergency_contact_name": "Jane", "emergency_contact_phone": "+421 900 000",
               "is_donor": True, "donor_organs": "kidneys", "life_testament": "none"}
    r2 = requests.put(f"{BASE_URL}/api/emergency-profile", headers=auth_headers, json=payload)
    assert r2.status_code == 200, r2.text
    d = r2.json()
    assert d["full_name"] == "TEST John Doe"
    assert d["is_donor"] is True

    # Public QR — no auth
    r3 = requests.get(f"{BASE_URL}/api/emergency-qr/{seed['did']}")
    assert r3.status_code == 200, r3.text
    q = r3.json()
    assert q["blood_type"] == "A+"
    assert q["is_donor"] is True


# --- Waitlist ---
def test_waitlist_crud(auth_headers):
    payload = {"specialty": "Cardiology", "clinic": "TEST Clinic", "city": "Bratislava",
               "current_date": "2026-06-01", "target_before": "2026-03-01", "priority": "high"}
    r = requests.post(f"{BASE_URL}/api/waitlist", headers=auth_headers, json=payload)
    assert r.status_code == 200, r.text
    item = r.json()
    item_id = item["item_id"]
    assert item["clinic"] == "TEST Clinic"

    r2 = requests.get(f"{BASE_URL}/api/waitlist", headers=auth_headers)
    assert r2.status_code == 200
    assert any(x["item_id"] == item_id for x in r2.json())

    r3 = requests.post(f"{BASE_URL}/api/waitlist/{item_id}/scan", headers=auth_headers)
    assert r3.status_code == 200
    body = r3.json()
    assert "found" in body and "slot" in body
    assert isinstance(body["found"], bool)

    r4 = requests.delete(f"{BASE_URL}/api/waitlist/{item_id}", headers=auth_headers)
    assert r4.status_code == 200


# --- Fall event ---
def test_fall_event(auth_headers):
    r = requests.post(f"{BASE_URL}/api/fall-event", headers=auth_headers,
                      json={"verified": True, "cancelled": False})
    assert r.status_code == 200, r.text
    assert r.json()["verified"] is True

    r2 = requests.get(f"{BASE_URL}/api/fall-events", headers=auth_headers)
    assert r2.status_code == 200
    assert len(r2.json()) >= 1


# --- AI translate (Claude Sonnet 5) ---
def test_ai_translate(auth_headers):
    r = requests.post(f"{BASE_URL}/api/ai/translate", headers=auth_headers,
                      json={"text": "Patient shows elevated LDL cholesterol at 4.5 mmol/L.",
                            "language": "en"}, timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "plain_language" in d
    assert len(d["plain_language"]) > 20


# --- Vault upload / download / delete ---
def test_vault_flow(auth_headers):
    files = {"file": ("test.txt", io.BytesIO(b"TEST vault content 12345"), "text/plain")}
    data = {"title": "TEST Doc"}
    r = requests.post(f"{BASE_URL}/api/vault/documents",
                      headers=auth_headers, files=files, data=data, timeout=60)
    assert r.status_code == 200, r.text
    doc = r.json()
    doc_id = doc["doc_id"]
    assert doc["size"] == len(b"TEST vault content 12345")

    r2 = requests.get(f"{BASE_URL}/api/vault/documents", headers=auth_headers)
    assert r2.status_code == 200
    assert any(x["doc_id"] == doc_id for x in r2.json())

    r3 = requests.get(f"{BASE_URL}/api/vault/documents/{doc_id}/file", headers=auth_headers)
    assert r3.status_code == 200, r3.text
    assert r3.content == b"TEST vault content 12345"

    r4 = requests.delete(f"{BASE_URL}/api/vault/documents/{doc_id}", headers=auth_headers)
    assert r4.status_code == 200
