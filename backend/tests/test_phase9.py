# Copyright © 2026 Guardian Angel. All Rights Reserved.
# This source code and its logic are the sole property of Guardian Angel.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Iteration 8 — Survival Extensions (Acoustic · Survival Bible · Pharmacy Hunter · Pulse Check).

Uses smoketest-user-1 (token=smoketok-fresh-2026) and creates a SECOND test user directly in
Mongo for the pulse-check opt-in scenarios (see /app/memory/test_credentials.md pattern).
"""
import os
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent.parent.parent / "frontend" / ".env")

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
TOKEN1 = "smoketok-fresh-2026"
H1 = {"Authorization": f"Bearer {TOKEN1}"}

# Second test user (created in Mongo directly)
USER2_ID = "smoketest-user-2"
USER2_DID = "did:guardian:smoke2"
TOKEN2 = "smoketok-fresh-2026-u2"
H2 = {"Authorization": f"Bearer {TOKEN2}"}


# --------------------------------------------------------------------
# FIXTURE: Ensure second test user exists (opt-in initially FALSE / unset)
# --------------------------------------------------------------------
@pytest.fixture(scope="module", autouse=True)
def seed_second_user():
    async def _seed():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        now = datetime.now(timezone.utc)
        # Remove any leftover pulse_check_optin so first test hits 403
        await db.users.update_one(
            {"user_id": USER2_ID},
            {"$set": {
                "user_id": USER2_ID,
                "email": "smoke2@example.com",
                "name": "Smoke Two",
                "did": USER2_DID,
                "language": "sk",
                "angel_mode": False,
                "created_at": now,
            }, "$unset": {"pulse_check_optin": ""}},
            upsert=True,
        )
        await db.user_sessions.update_one(
            {"session_token": TOKEN2},
            {"$set": {
                "session_token": TOKEN2,
                "user_id": USER2_ID,
                "created_at": now,
                "expires_at": now + timedelta(days=7),
            }},
            upsert=True,
        )
        # Clean up any leftover pulse requests from prior runs
        await db.pulse_requests.delete_many({
            "$or": [
                {"from_user": "smoketest-user-1", "target_user": USER2_ID},
                {"target_user": USER2_ID},
            ]
        })
        client.close()
    asyncio.get_event_loop().run_until_complete(_seed())
    yield
    # No teardown of user2 (keep for reuse); credentials will be appended to test_credentials.md


# ================== ACOUSTIC THREAT DETECTION ==================

class TestAcoustic:
    def test_create_event(self):
        r = requests.post(f"{BASE_URL}/api/acoustic-event", headers=H1,
                          json={"kind": "loud_noise", "db_level": -5}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("event_id")
        assert body.get("kind") == "loud_noise"
        assert body.get("db_level") == -5

    def test_list_events_contains_created(self):
        r = requests.get(f"{BASE_URL}/api/acoustic-events", headers=H1, timeout=15)
        assert r.status_code == 200, r.text
        arr = r.json()
        assert isinstance(arr, list) and len(arr) >= 1
        assert any(e.get("kind") == "loud_noise" for e in arr)


# ================== SURVIVAL BIBLE PDF ==================

class TestSurvivalBible:
    def test_pdf_with_token(self):
        r = requests.get(f"{BASE_URL}/api/survival/bible.pdf",
                         params={"token": TOKEN1}, timeout=45)
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        assert len(r.content) > 10_000, f"pdf too small: {len(r.content)} bytes"

    def test_pdf_unauthorized(self):
        r = requests.get(f"{BASE_URL}/api/survival/bible.pdf", timeout=15)
        assert r.status_code in (401, 403)


# ================== PHARMACY HUNTER ==================

class TestPharmacySearch:
    def test_search_sk_euthyrox(self):
        r = requests.get(f"{BASE_URL}/api/pharmacy/search",
                         params={"med": "Euthyrox", "region": "SK"},
                         headers=H1, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("simulated") is True
        assert body.get("region") == "SK"
        results = body.get("results")
        assert isinstance(results, list) and len(results) == 6
        # in_stock items must come before others
        statuses = [r["status"] for r in results]
        first_out = next((i for i, s in enumerate(statuses) if s != "in_stock"), len(statuses))
        assert all(s == "in_stock" for s in statuses[:first_out])

    def test_search_cz_returns_cz_pharmacies(self):
        r = requests.get(f"{BASE_URL}/api/pharmacy/search",
                         params={"med": "Paralen", "region": "CZ"},
                         headers=H1, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["region"] == "CZ"
        cities = {r["city"] for r in body["results"]}
        # CZ pharmacies live in Praha/Brno/Ostrava/Plzeň/Olomouc — none of those overlap with SK set
        assert any(c in {"Praha", "Brno", "Ostrava", "Plzeň", "Olomouc"} for c in cities)

    def test_search_empty_med_rejected(self):
        r = requests.get(f"{BASE_URL}/api/pharmacy/search",
                         params={"med": "  ", "region": "SK"},
                         headers=H1, timeout=15)
        assert r.status_code in (400, 422), r.text


class TestPharmacyWatchLifecycle:
    """Ordered watch lifecycle: create → list → scan → delete → delete-again(404)."""
    watch_id = None

    def test_1_add_watch(self):
        r = requests.post(f"{BASE_URL}/api/pharmacy/watch", headers=H1,
                          json={"med_name": "Euthyrox", "region": "SK"}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("watch_id")
        assert body.get("status") == "watching"
        TestPharmacyWatchLifecycle.watch_id = body["watch_id"]

    def test_2_list_contains(self):
        r = requests.get(f"{BASE_URL}/api/pharmacy/watches", headers=H1, timeout=15)
        assert r.status_code == 200
        arr = r.json()
        assert any(w.get("watch_id") == TestPharmacyWatchLifecycle.watch_id for w in arr)

    def test_3_scan(self):
        wid = TestPharmacyWatchLifecycle.watch_id
        r = requests.post(f"{BASE_URL}/api/pharmacy/watches/{wid}/scan",
                          headers=H1, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("scanned") is True
        assert body.get("simulated") is True
        assert isinstance(body.get("results"), list) and len(body["results"]) == 6
        # hit may be None or a dict; if dict, status must be in_stock
        if body.get("hit"):
            assert body["hit"]["status"] == "in_stock"

    def test_4_delete(self):
        wid = TestPharmacyWatchLifecycle.watch_id
        r = requests.delete(f"{BASE_URL}/api/pharmacy/watches/{wid}", headers=H1, timeout=15)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_5_delete_again_404(self):
        wid = TestPharmacyWatchLifecycle.watch_id
        r = requests.delete(f"{BASE_URL}/api/pharmacy/watches/{wid}", headers=H1, timeout=15)
        assert r.status_code == 404


# ================== PULSE CHECK (OPT-IN PRIVACY) ==================

class TestPulseCheck:
    """Ordered lifecycle: opt-in guard → enable → request → inbox → respond → sent."""
    req_id = None

    def test_1_request_without_optin_returns_403(self):
        r = requests.post(f"{BASE_URL}/api/pulse/request", headers=H1,
                          json={"target_did": USER2_DID}, timeout=15)
        assert r.status_code == 403, r.text
        assert "opt_in_required" in r.text or "opt-in" in r.text.lower()

    def test_2_enable_optin_on_user2(self):
        # user2 enables opt-in via /me/prefs
        r = requests.patch(f"{BASE_URL}/api/me/prefs", headers=H2,
                           json={"pulse_check_optin": True}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("pulse_check_optin") is True

    def test_3_request_succeeds_after_optin(self):
        r = requests.post(f"{BASE_URL}/api/pulse/request", headers=H1,
                          json={"target_did": USER2_DID}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("req_id")
        assert body.get("status") == "pending"
        assert body.get("target_did") == USER2_DID
        TestPulseCheck.req_id = body["req_id"]

    def test_4_user2_inbox_sees_request(self):
        r = requests.get(f"{BASE_URL}/api/pulse/requests", headers=H2, timeout=15)
        assert r.status_code == 200, r.text
        arr = r.json()
        assert any(x.get("req_id") == TestPulseCheck.req_id for x in arr)

    def test_5_user2_responds_ok(self):
        rid = TestPulseCheck.req_id
        r = requests.post(f"{BASE_URL}/api/pulse/requests/{rid}/respond",
                          headers=H2, json={"status": "ok"}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("status") == "ok"

    def test_6_user1_sent_shows_ok(self):
        r = requests.get(f"{BASE_URL}/api/pulse/sent", headers=H1, timeout=15)
        assert r.status_code == 200
        arr = r.json()
        match = next((x for x in arr if x.get("req_id") == TestPulseCheck.req_id), None)
        assert match is not None
        assert match.get("status") == "ok"

    def test_7_unknown_did_returns_404(self):
        r = requests.post(f"{BASE_URL}/api/pulse/request", headers=H1,
                          json={"target_did": "did:guardian:doesnotexist_xyz"}, timeout=15)
        assert r.status_code == 404

    def test_8_own_did_returns_400(self):
        # look up user1 did via /api/auth/me
        me = requests.get(f"{BASE_URL}/api/auth/me", headers=H1, timeout=15).json()
        my_did = (me.get("user") or me).get("did")
        assert my_did
        r = requests.post(f"{BASE_URL}/api/pulse/request", headers=H1,
                          json={"target_did": my_did}, timeout=15)
        assert r.status_code == 400

    def test_9_cleanup_reset_user1_optin_state(self):
        """Per test harness note: leave smoketest-user-1's pulse_check_optin OFF.
        (User1 was never opted in in these tests, but explicitly assert current state.)"""
        me = requests.get(f"{BASE_URL}/api/auth/me", headers=H1, timeout=15).json()
        user = me.get("user") or me
        # ensure user1 is off — if somehow toggled, turn back off
        if user.get("pulse_check_optin"):
            requests.patch(f"{BASE_URL}/api/me/prefs", headers=H1,
                           json={"pulse_check_optin": False}, timeout=15)
