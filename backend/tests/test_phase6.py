# Copyright © 2026 Guardian Angel. All Rights Reserved.
# This source code and its logic are the sole property of Guardian Angel.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Iteration 5 — PDF export (Testament / Proxy / TOS) + Medication reminders (Angel Mode).

Covers:
  - GET /api/legal/tos.pdf (SK & EN, token query + Authorization header + 401 no auth)
  - POST /api/legal/testament + GET /api/legal/testament.pdf (200 + 404 fresh)
  - PUT /api/proxy-directive + GET /api/legal/proxy.pdf (200 + 404 fresh)
  - Meds: create (valid + invalid time filtered / 400 empty), list, today (pending count),
          intake (idempotent), delete, foreign/unknown reminder 404
  - Regression: /api/legal/accept, /api/wellness/checkin, /api/vault/documents list
"""
import io
import os
import uuid
import asyncio
from datetime import datetime, timezone, timedelta

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent.parent.parent / "frontend" / ".env")

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

# ------- seed helpers -------

def _mk_user_sync(suffix: str) -> dict:
    """Insert a fresh user + session using pymongo (sync — avoids motor loop issues)."""
    from pymongo import MongoClient
    c = MongoClient(MONGO_URL)
    db = c[DB_NAME]
    uid = f"TEST_i5_{suffix}_{uuid.uuid4().hex[:6]}"
    token = f"TEST_i5tok_{uuid.uuid4().hex}"
    did = f"did:guardian:TEST{uuid.uuid4().hex[:16]}"
    email = f"TEST_{suffix}_{uuid.uuid4().hex[:5]}@example.com"
    now = datetime.now(timezone.utc)
    db.users.insert_one({
        "user_id": uid, "email": email, "did": did, "name": f"TEST {suffix}",
        "language": "sk", "angel_mode": True, "created_at": now,
    })
    db.user_sessions.insert_one({
        "session_token": token, "user_id": uid,
        "created_at": now, "expires_at": now + timedelta(days=7),
    })
    c.close()
    return {"user_id": uid, "token": token, "did": did, "email": email}


def _cleanup_sync(user_ids):
    from pymongo import MongoClient
    c = MongoClient(MONGO_URL)
    db = c[DB_NAME]
    q = {"user_id": {"$in": list(user_ids)}}
    for col in ("users", "user_sessions", "legal_testaments", "proxy_directives",
                "legal_acceptances", "med_reminders", "med_intakes",
                "wellness_checkins", "documents"):
        db[col].delete_many(q)
    # sessions live on token, users on user_id — sessions handled above already
    c.close()


@pytest.fixture(scope="module")
def users():
    a = _mk_user_sync("A")  # user with testament + proxy + meds
    b = _mk_user_sync("B")  # fresh user for 404 paths and foreign reminder attempt
    yield {"a": a, "b": b}
    _cleanup_sync([a["user_id"], b["user_id"]])


def H(u):
    return {"Authorization": f"Bearer {u['token']}"}


# =============== TOS PDF ===============

class TestTosPdf:
    def test_tos_pdf_sk_via_token_query(self, users):
        a = users["a"]
        r = requests.get(f"{BASE_URL}/api/legal/tos.pdf", params={"language": "sk", "token": a["token"]}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert "attachment" in r.headers.get("content-disposition", "").lower()
        assert r.content.startswith(b"%PDF-"), "Response is not a PDF"
        assert len(r.content) > 10_000, f"PDF too small: {len(r.content)} bytes"

    def test_tos_pdf_en_via_authorization_header(self, users):
        a = users["a"]
        r = requests.get(f"{BASE_URL}/api/legal/tos.pdf", params={"language": "en"}, headers=H(a), timeout=30)
        assert r.status_code == 200
        assert r.content.startswith(b"%PDF-")
        assert len(r.content) > 10_000

    def test_tos_pdf_401_without_auth(self):
        r = requests.get(f"{BASE_URL}/api/legal/tos.pdf", params={"language": "sk"}, timeout=15)
        assert r.status_code == 401


# =============== TESTAMENT PDF ===============

class TestTestamentPdf:
    def test_testament_pdf_404_before_generated(self, users):
        b = users["b"]
        r = requests.get(f"{BASE_URL}/api/legal/testament.pdf", params={"token": b["token"]}, timeout=15)
        assert r.status_code == 404

    def test_testament_generate_then_pdf(self, users):
        a = users["a"]
        body = {
            "country": "SK", "language": "sk",
            "full_name": "TEST Testator Poručiteľ",
            "wishes": "Všetok majetok odkazujem manželke.",
            "executor_name": "TEST Executor",
        }
        r = requests.post(f"{BASE_URL}/api/legal/testament", headers=H(a), json=body, timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["format"] == "civil_law_holograph"
        assert "document_text" in j and "doc_hash" in j

        r2 = requests.get(f"{BASE_URL}/api/legal/testament.pdf", params={"token": a["token"]}, timeout=30)
        assert r2.status_code == 200, r2.text
        assert r2.headers.get("content-type", "").startswith("application/pdf")
        assert r2.content.startswith(b"%PDF-")
        assert len(r2.content) > 10_000
        assert "attachment" in r2.headers.get("content-disposition", "").lower()


# =============== PROXY PDF ===============

class TestProxyPdf:
    def test_proxy_pdf_404_before_generated(self, users):
        b = users["b"]
        r = requests.get(f"{BASE_URL}/api/legal/proxy.pdf", params={"token": b["token"]}, timeout=15)
        assert r.status_code == 404

    def test_proxy_put_then_pdf(self, users):
        a = users["a"]
        body = {
            "proxy_full_name": "TEST Proxy Splnomocnenec",
            "proxy_relationship": "spouse",
            "proxy_phone": "+421 900 000 000",
            "scope": "full",
            "effective_immediately": True,
            "language": "sk",
        }
        r = requests.put(f"{BASE_URL}/api/proxy-directive", headers=H(a), json=body, timeout=20)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["proxy_full_name"] == "TEST Proxy Splnomocnenec"
        assert "document_text" in j and "doc_hash" in j

        r2 = requests.get(f"{BASE_URL}/api/legal/proxy.pdf", params={"token": a["token"]}, timeout=20)
        assert r2.status_code == 200, r2.text
        assert r2.headers.get("content-type", "").startswith("application/pdf")
        assert r2.content.startswith(b"%PDF-")
        assert len(r2.content) > 10_000


# =============== MEDS ===============

class TestMeds:
    def test_meds_create_invalid_only_400(self, users):
        a = users["a"]
        r = requests.post(f"{BASE_URL}/api/meds/reminders", headers=H(a),
                          json={"name": "Ibalgin", "dose": "400 mg", "times": ["8am", "morning"]}, timeout=15)
        assert r.status_code == 400, r.text

    def test_meds_create_valid_filters_invalid(self, users):
        a = users["a"]
        r = requests.post(f"{BASE_URL}/api/meds/reminders", headers=H(a),
                          json={"name": "Euthyrox", "dose": "50 mg", "times": ["08:00", "20:00", "8am"]}, timeout=15)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["name"] == "Euthyrox"
        assert j["times"] == ["08:00", "20:00"]  # sorted, unique, invalid filtered
        assert "reminder_id" in j
        # Store on module-level for downstream tests
        TestMeds.reminder_id = j["reminder_id"]

    def test_meds_list(self, users):
        a = users["a"]
        r = requests.get(f"{BASE_URL}/api/meds/reminders", headers=H(a), timeout=15)
        assert r.status_code == 200
        arr = r.json()
        assert any(x["reminder_id"] == TestMeds.reminder_id for x in arr)

    def test_meds_today_initial_two_pending(self, users):
        a = users["a"]
        r = requests.get(f"{BASE_URL}/api/meds/today", headers=H(a), timeout=15)
        assert r.status_code == 200
        j = r.json()
        # only items for this reminder (user was fresh besides this reminder)
        mine = [it for it in j["items"] if it["reminder_id"] == TestMeds.reminder_id]
        assert len(mine) == 2
        assert j["pending"] >= 2
        assert all(it["taken"] is False for it in mine)

    def test_meds_intake_marks_taken_and_reduces_pending(self, users):
        a = users["a"]
        r = requests.post(f"{BASE_URL}/api/meds/intake", headers=H(a),
                          json={"reminder_id": TestMeds.reminder_id, "time": "08:00"}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("taken") is True

        r2 = requests.get(f"{BASE_URL}/api/meds/today", headers=H(a), timeout=15)
        j = r2.json()
        mine = [it for it in j["items"] if it["reminder_id"] == TestMeds.reminder_id]
        taken = [it for it in mine if it["taken"] is True]
        pending_mine = [it for it in mine if it["taken"] is False]
        assert len(taken) == 1 and taken[0]["time"] == "08:00"
        assert len(pending_mine) == 1  # 20:00 still pending

    def test_meds_intake_idempotent(self, users):
        a = users["a"]
        # POST twice; expect single intake record via mongo count
        for _ in range(2):
            r = requests.post(f"{BASE_URL}/api/meds/intake", headers=H(a),
                              json={"reminder_id": TestMeds.reminder_id, "time": "08:00"}, timeout=15)
            assert r.status_code == 200

        from pymongo import MongoClient
        c = MongoClient(MONGO_URL)
        db = c[DB_NAME]
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        count = db.med_intakes.count_documents({
            "user_id": a["user_id"], "reminder_id": TestMeds.reminder_id,
            "date": day, "time": "08:00",
        })
        c.close()
        assert count == 1, f"Expected 1 intake record (idempotent), got {count}"

    def test_meds_intake_unknown_reminder_404(self, users):
        a = users["a"]
        r = requests.post(f"{BASE_URL}/api/meds/intake", headers=H(a),
                          json={"reminder_id": "does-not-exist-xyz", "time": "08:00"}, timeout=15)
        assert r.status_code == 404

    def test_meds_intake_foreign_reminder_404(self, users):
        # user B tries to mark user A's reminder → 404
        b = users["b"]
        r = requests.post(f"{BASE_URL}/api/meds/intake", headers=H(b),
                          json={"reminder_id": TestMeds.reminder_id, "time": "08:00"}, timeout=15)
        assert r.status_code == 404

    def test_meds_delete_removes_from_today(self, users):
        a = users["a"]
        r = requests.delete(f"{BASE_URL}/api/meds/reminders/{TestMeds.reminder_id}", headers=H(a), timeout=15)
        assert r.status_code == 200 and r.json().get("ok") is True

        r2 = requests.get(f"{BASE_URL}/api/meds/today", headers=H(a), timeout=15)
        j = r2.json()
        assert not any(it["reminder_id"] == TestMeds.reminder_id for it in j["items"]), \
            "Today items still show a deleted reminder"


# =============== REGRESSION ===============

class TestRegression:
    def test_legal_accept_still_works(self, users):
        a = users["a"]
        r = requests.post(f"{BASE_URL}/api/legal/accept", headers=H(a),
                          json={"language": "sk"}, timeout=15)
        assert r.status_code == 200, r.text
        j = r.json()
        # Response is updated user object with tos_accepted_version set
        assert isinstance(j, dict)
        assert j.get("tos_accepted_version") or j.get("accepted") or "version" in j or j.get("user_id")

    def test_vault_documents_list(self, users):
        a = users["a"]
        r = requests.get(f"{BASE_URL}/api/vault/documents", headers=H(a), timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_wellness_checkin_llm(self, users):
        a = users["a"]
        r = requests.post(f"{BASE_URL}/api/wellness/checkin", headers=H(a),
                          json={"mood": 4, "sleep_hours": 7, "notes": "TEST feeling ok",
                                "language": "sk"}, timeout=90)
        # If LLM key issues return 500, still record but mark as regression failure
        assert r.status_code == 200, f"Wellness checkin failed: {r.status_code} {r.text[:300]}"
        j = r.json()
        # Response contains some string field (advice/summary/message)
        assert isinstance(j, dict) and len(j) > 0
