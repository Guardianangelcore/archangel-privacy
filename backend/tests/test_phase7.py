# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Iteration 6 — FINAL DIGNITY & FUNERAL FUND (Legacy module).

Covers:
  - GET /api/dignity/fund → auto-create locked fund + proxy-defaulted beneficiary
  - POST /api/dignity/fund/deposit → ledger_hash + amount<=0 rejects
  - PUT /api/dignity/fund/plan + GET → recurring applies once per month (no double-apply)
  - POST /api/dignity/release before verify → 403 'locked'
  - POST /api/dignity/verify-death → verified:true simulated:true; short cert → 400
  - POST /api/dignity/release without beneficiary → 400; then PUT beneficiary → 200 released
  - Second release → 400 'Already released'; deposit after release → 400
  - PUT /api/dignity/beneficiary type:'proxy' auto-fills from proxy_full_name
  - PUT /api/dignity/wishes → doc_hash saved + returned in GET
  - AML ledger contains dignity_deposit/dignity_recurring/death_verification/dignity_release
    with intact prev_hash chain (per-user view)
"""
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent.parent.parent / "frontend" / ".env")

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


def _mk_user_sync(suffix: str, with_proxy: bool = False) -> dict:
    from pymongo import MongoClient
    c = MongoClient(MONGO_URL)
    db = c[DB_NAME]
    uid = f"TEST_i6_{suffix}_{uuid.uuid4().hex[:6]}"
    token = f"TEST_i6tok_{uuid.uuid4().hex}"
    did = f"did:guardian:TEST{uuid.uuid4().hex[:16]}"
    email = f"TEST_i6_{suffix}_{uuid.uuid4().hex[:5]}@example.com"
    now = datetime.now(timezone.utc)
    db.users.insert_one({
        "user_id": uid, "email": email, "did": did, "name": f"TEST i6 {suffix}",
        "language": "sk", "angel_mode": True, "created_at": now,
    })
    db.user_sessions.insert_one({
        "session_token": token, "user_id": uid,
        "created_at": now, "expires_at": now + timedelta(days=7),
    })
    if with_proxy:
        db.proxy_directives.insert_one({
            "user_id": uid,
            "proxy_full_name": "Tomáš Novák",
            "proxy_phone": "+421900111222",
            "proxy_email": "tomas@example.com",
            "created_at": now,
        })
    c.close()
    return {"user_id": uid, "token": token, "did": did, "email": email}


def _cleanup_sync(user_ids):
    from pymongo import MongoClient
    c = MongoClient(MONGO_URL)
    db = c[DB_NAME]
    q = {"user_id": {"$in": list(user_ids)}}
    for col in (
        "users", "user_sessions", "proxy_directives",
        "dignity_funds", "dignity_contributions", "dignity_wishes",
        "aml_ledger",
    ):
        db[col].delete_many(q)
    c.close()


@pytest.fixture(scope="module")
def users():
    # A = user with proxy directive (tests auto-default beneficiary + auto-fill)
    # B = user without proxy (tests 'No beneficiary' path)
    a = _mk_user_sync("A", with_proxy=True)
    b = _mk_user_sync("B", with_proxy=False)
    yield {"a": a, "b": b}
    _cleanup_sync([a["user_id"], b["user_id"]])


def H(u):
    return {"Authorization": f"Bearer {u['token']}"}


# =============== GET /dignity/fund auto-create ===============

class TestDignityFundBootstrap:
    def test_get_creates_locked_fund_with_proxy_beneficiary(self, users):
        u = users["a"]
        r = requests.get(f"{BASE_URL}/api/dignity/fund", headers=H(u), timeout=15)
        assert r.status_code == 200, r.text
        f = r.json()
        assert f["balance"] == 0
        assert f["status"] == "locked"
        assert f["death_verified"] is False
        # proxy auto-default
        assert f.get("beneficiary") is not None, "beneficiary should auto-default from proxy"
        assert f["beneficiary"]["type"] == "proxy"
        assert f["beneficiary"]["name"] == "Tomáš Novák"

    def test_get_fresh_user_no_beneficiary(self, users):
        u = users["b"]
        r = requests.get(f"{BASE_URL}/api/dignity/fund", headers=H(u), timeout=15)
        assert r.status_code == 200
        f = r.json()
        assert f["balance"] == 0 and f["status"] == "locked"
        # user B has no proxy so beneficiary stays None/absent
        assert not f.get("beneficiary")


# =============== POST /dignity/fund/deposit ===============

class TestDignityDeposit:
    def test_deposit_updates_balance_and_returns_ledger_hash(self, users):
        u = users["a"]
        r = requests.post(f"{BASE_URL}/api/dignity/fund/deposit", headers=H(u),
                          json={"amount": 50, "currency": "EUR", "method": "card"}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["balance"] == 50
        assert body["currency"] == "EUR"
        assert "ledger_hash" in body and len(body["ledger_hash"]) == 64
        assert body.get("mocked") is True

    def test_deposit_zero_amount_rejected(self, users):
        r = requests.post(f"{BASE_URL}/api/dignity/fund/deposit", headers=H(users["a"]),
                          json={"amount": 0, "currency": "EUR", "method": "card"}, timeout=15)
        assert r.status_code in (400, 422), r.text

    def test_deposit_negative_amount_rejected(self, users):
        r = requests.post(f"{BASE_URL}/api/dignity/fund/deposit", headers=H(users["a"]),
                          json={"amount": -10, "currency": "EUR", "method": "card"}, timeout=15)
        assert r.status_code in (400, 422)


# =============== PUT /dignity/fund/plan → recurring auto-apply once ===============

class TestDignityRecurringPlan:
    def test_plan_save_and_recurring_applies_once_per_month(self, users):
        u = users["a"]
        # Baseline balance (worker-independent — deposits may or may not have run here)
        f0 = requests.get(f"{BASE_URL}/api/dignity/fund", headers=H(u), timeout=15).json()
        base = f0["balance"]
        # Save recurring plan
        r = requests.put(f"{BASE_URL}/api/dignity/fund/plan", headers=H(u),
                         json={"monthly_amount": 20, "currency": "EUR", "enabled": True}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["plan"]["monthly_amount"] == 20

        # GET → should auto-apply once (+20)
        r1 = requests.get(f"{BASE_URL}/api/dignity/fund", headers=H(u), timeout=15).json()
        assert r1["balance"] == base + 20, f"expected {base}+20={base + 20} got {r1['balance']}"
        assert r1.get("last_plan_run") is not None

        # Second GET → must NOT double-apply
        r2 = requests.get(f"{BASE_URL}/api/dignity/fund", headers=H(u), timeout=15).json()
        assert r2["balance"] == base + 20, f"double-applied! now {r2['balance']}"

        # At least one contribution with method:'recurring'
        methods = [c["method"] for c in r2.get("contributions", [])]
        assert "recurring" in methods, f"no recurring contribution: {methods}"


# =============== Release lifecycle (locked → verify → beneficiary → release) ===============

class TestDignityReleaseLifecycle:
    def test_release_before_verification_forbidden(self, users):
        u = users["a"]
        r = requests.post(f"{BASE_URL}/api/dignity/release", headers=H(u), timeout=15)
        assert r.status_code == 403, r.text
        assert "locked" in r.text.lower()

    def test_verify_death_short_cert_rejected(self, users):
        r = requests.post(f"{BASE_URL}/api/dignity/verify-death", headers=H(users["a"]),
                          json={"death_certificate_number": "UL", "registry_country": "SK"}, timeout=15)
        assert r.status_code == 400

    def test_verify_death_valid_cert(self, users):
        r = requests.post(f"{BASE_URL}/api/dignity/verify-death", headers=H(users["a"]),
                          json={"death_certificate_number": "UL-2026-9999", "registry_country": "SK"}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["verified"] is True
        assert body["simulated"] is True
        assert body["certificate_number"] == "UL-2026-9999"
        assert body["registry_country"] == "SK"

    def test_release_user_b_no_beneficiary_no_proxy_400(self, users):
        u = users["b"]
        # Verify death for B first
        rv = requests.post(f"{BASE_URL}/api/dignity/verify-death", headers=H(u),
                           json={"death_certificate_number": "UL-2026-B001", "registry_country": "SK"}, timeout=15)
        assert rv.status_code == 200
        # No beneficiary + no proxy → 400
        r = requests.post(f"{BASE_URL}/api/dignity/release", headers=H(u), timeout=15)
        assert r.status_code == 400, r.text
        assert "beneficiary" in r.text.lower()

    def test_beneficiary_proxy_auto_fill(self, users):
        # For USER A (has proxy directive), PUT type:proxy with empty name → name auto-filled
        u = users["a"]
        r = requests.put(f"{BASE_URL}/api/dignity/beneficiary", headers=H(u),
                         json={"type": "proxy", "name": "", "contact": "", "iban": ""}, timeout=15)
        assert r.status_code == 200, r.text
        f = r.json()
        assert f["beneficiary"]["type"] == "proxy"
        assert f["beneficiary"]["name"] == "Tomáš Novák"

    def test_user_b_set_funeral_director_and_release(self, users):
        u = users["b"]
        # Set beneficiary
        r = requests.put(f"{BASE_URL}/api/dignity/beneficiary", headers=H(u),
                         json={"type": "funeral_director", "name": "Pohrebná Bratislava s.r.o."}, timeout=15)
        assert r.status_code == 200

        # deposit some funds for B first so release amount > 0
        rd = requests.post(f"{BASE_URL}/api/dignity/fund/deposit", headers=H(u),
                           json={"amount": 100, "currency": "EUR", "method": "card"}, timeout=15)
        assert rd.status_code == 200
        assert rd.json()["balance"] == 100

        # Release
        rr = requests.post(f"{BASE_URL}/api/dignity/release", headers=H(u), timeout=15)
        assert rr.status_code == 200, rr.text
        rb = rr.json()
        assert rb["released"] is True
        assert rb["amount"] == 100
        assert rb["to"]["type"] == "funeral_director"
        assert rb["to"]["name"] == "Pohrebná Bratislava s.r.o."

        # GET should show balance=0, status released
        f = requests.get(f"{BASE_URL}/api/dignity/fund", headers=H(u), timeout=15).json()
        assert f["balance"] == 0
        assert f["status"] == "released"
        assert f["released_to"]["name"] == "Pohrebná Bratislava s.r.o."

    def test_second_release_rejected(self, users):
        r = requests.post(f"{BASE_URL}/api/dignity/release", headers=H(users["b"]), timeout=15)
        assert r.status_code == 400
        assert "already" in r.text.lower()

    def test_deposit_after_release_rejected(self, users):
        r = requests.post(f"{BASE_URL}/api/dignity/fund/deposit", headers=H(users["b"]),
                          json={"amount": 10, "currency": "EUR", "method": "card"}, timeout=15)
        assert r.status_code == 400
        assert "released" in r.text.lower()


# =============== Wishes ===============

class TestDignityWishes:
    def test_save_wishes_returns_doc_hash_and_reflects_in_get(self, users):
        u = users["a"]
        payload = {"burial_type": "cremation", "ceremony_music": "Hallelujah",
                   "guest_list": "Rodina + susedia", "notes": "Bez smútku"}
        r = requests.put(f"{BASE_URL}/api/dignity/wishes", headers=H(u), json=payload, timeout=15)
        assert r.status_code == 200, r.text
        w = r.json()
        assert w["burial_type"] == "cremation"
        assert w["ceremony_music"] == "Hallelujah"
        assert w.get("doc_hash") and len(w["doc_hash"]) == 64

        # GET fund reflects wishes
        f = requests.get(f"{BASE_URL}/api/dignity/fund", headers=H(u), timeout=15).json()
        assert f.get("wishes") is not None
        assert f["wishes"]["burial_type"] == "cremation"
        assert f["wishes"]["ceremony_music"] == "Hallelujah"


# =============== AML ledger integrity (per-user chain view) ===============

class TestAmlLedgerDignityChain:
    def test_ledger_contains_all_dignity_actions_with_intact_chain(self):
        """Verify per-user ledger contains all dignity_* actions and hash chain is intact.

        Chain is global (prev_hash across all users), so we can only verify per-entry
        integrity by recomputing the hash matches entry_hash. Uses DEDICATED users and
        performs the full flow itself — deterministic regardless of xdist scheduling."""
        from pymongo import MongoClient
        import hashlib
        import json as _json
        ua = _mk_user_sync("LEDGA", with_proxy=True)
        ub = _mk_user_sync("LEDGB", with_proxy=False)
        try:
            # user A: deposit + recurring plan (auto-applies on GET) + death verification
            assert requests.post(f"{BASE_URL}/api/dignity/fund/deposit", headers=H(ua),
                                 json={"amount": 50, "currency": "EUR", "method": "card"}, timeout=15).status_code == 200
            assert requests.put(f"{BASE_URL}/api/dignity/fund/plan", headers=H(ua),
                                json={"monthly_amount": 20, "currency": "EUR", "enabled": True}, timeout=15).status_code == 200
            assert requests.get(f"{BASE_URL}/api/dignity/fund", headers=H(ua), timeout=15).status_code == 200
            assert requests.post(f"{BASE_URL}/api/dignity/verify-death", headers=H(ua),
                                 json={"death_certificate_number": "UL-2026-7777", "registry_country": "SK"}, timeout=15).status_code == 200
            # user B: deposit + death verification + beneficiary + release
            assert requests.post(f"{BASE_URL}/api/dignity/fund/deposit", headers=H(ub),
                                 json={"amount": 100, "currency": "EUR", "method": "card"}, timeout=15).status_code == 200
            assert requests.post(f"{BASE_URL}/api/dignity/verify-death", headers=H(ub),
                                 json={"death_certificate_number": "UL-2026-8888", "registry_country": "SK"}, timeout=15).status_code == 200
            assert requests.put(f"{BASE_URL}/api/dignity/beneficiary", headers=H(ub),
                                json={"type": "funeral_director", "name": "Pohrebná Bratislava s.r.o."}, timeout=15).status_code == 200
            assert requests.post(f"{BASE_URL}/api/dignity/release", headers=H(ub), timeout=15).status_code == 200

            c = MongoClient(MONGO_URL)
            db = c[DB_NAME]
            u_a = ua["user_id"]
            u_b = ub["user_id"]

            entries_a = list(db.aml_ledger.find({"user_id": u_a}).sort("seq", 1))
            entries_b = list(db.aml_ledger.find({"user_id": u_b}).sort("seq", 1))
            c.close()

            actions_a = [e["action"] for e in entries_a]
            actions_b = [e["action"] for e in entries_b]

            # user A: deposit + recurring + death_verification
            assert "dignity_deposit" in actions_a, actions_a
            assert "dignity_recurring" in actions_a, actions_a
            assert "death_verification" in actions_a, actions_a

            # user B: deposit + death_verification + dignity_release
            assert "dignity_deposit" in actions_b, actions_b
            assert "death_verification" in actions_b, actions_b
            assert "dignity_release" in actions_b, actions_b

            # Recompute each entry hash and verify it matches stored entry_hash
            for e in entries_a + entries_b:
                body = _json.dumps({
                    "seq": e["seq"], "user_id": e["user_id"], "action": e["action"],
                    "payload": e["payload"], "prev": e["prev_hash"],
                }, sort_keys=True, default=str)
                recomputed = hashlib.sha256(body.encode()).hexdigest()
                assert recomputed == e["entry_hash"], f"tampered entry seq={e['seq']} action={e['action']}"
        finally:
            _cleanup_sync([ua["user_id"], ub["user_id"]])
