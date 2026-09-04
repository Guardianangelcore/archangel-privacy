"""
Iteration 52 — Forgot / Reset password flow (Emergent Resend playbook).

Tests /api/auth/forgot-password and /api/auth/reset-password end-to-end.
Codes are recovered by brute-forcing sha256(f"{email}:{code}") over 000000..999999
against the code_hash stored in db.password_resets (email inbox is not readable).

Also runs quick regressions on /register, /login, /dev-bypass, /auth/session.
"""
import os
import time
import uuid
import hashlib
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL",
                          "https://physio-lang-fix.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

# Mongo — same host as backend .env
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "guardian_health"

RESET_EMAIL = "delivered@resend.dev"
INITIAL_PASSWORD = "reset-password-2026-01"  # current password on entry (set by set_known_pw.py)
NEW_PASSWORD = f"reset-password-2026-{uuid.uuid4().hex[:6]}"  # 12+ chars, set during test
FOUNDER_EMAIL = "guardianangel.core@proton.me"
DEMO_EMAIL = "demo.judge@guardian.app"
DEMO_PASSWORD = "guardian-demo-2026"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    return client[DB_NAME]


@pytest.fixture(scope="module", autouse=True)
def known_password(db):
    """Self-healing: force the reset-test account to INITIAL_PASSWORD so the
    suite is rerunnable regardless of what previous runs left in the DB."""
    import bcrypt
    h = bcrypt.hashpw(INITIAL_PASSWORD.encode(), bcrypt.gensalt(12)).decode()
    db.users.update_one({"email": RESET_EMAIL.lower()},
                        {"$set": {"password_hash": h}}, upsert=False)


def _code_hash(email: str, code: str) -> str:
    return hashlib.sha256(f"{email}:{code}".encode()).hexdigest()


def _brute_force_code(target_hash: str, email: str) -> str | None:
    """Recover the 6-digit code by exhaustive sha256 over 000000..999999."""
    for i in range(1_000_000):
        code = f"{i:06d}"
        if hashlib.sha256(f"{email}:{code}".encode()).hexdigest() == target_hash:
            return code
    return None


def _reset_rate_limit(db, email: str):
    """Delete recent password_resets for email so the 3/hour limit resets."""
    db.password_resets.delete_many({"email": email.lower()})


# -----------------------------------------------------------------------------
# 1. forgot-password: identical generic 200 for known & unknown; 422 for junk
# -----------------------------------------------------------------------------
class TestForgotPasswordSurface:
    def test_forgot_known_email_generic_200(self, s, db):
        _reset_rate_limit(db, RESET_EMAIL)
        r = s.post(f"{API}/auth/forgot-password", json={"email": RESET_EMAIL})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        assert "reset code" in body.get("message", "").lower()
        # A password_resets doc must have been created (used=False)
        docs = list(db.password_resets.find({"email": RESET_EMAIL.lower(), "used": False}))
        assert len(docs) >= 1

    def test_forgot_unknown_email_identical_body(self, s):
        r_known = s.post(f"{API}/auth/forgot-password", json={"email": RESET_EMAIL})
        r_unknown = s.post(f"{API}/auth/forgot-password",
                           json={"email": f"nobody_{uuid.uuid4().hex}@nowhere.example"})
        assert r_known.status_code == 200
        assert r_unknown.status_code == 200
        # Exact same body → no enumeration
        assert r_known.json() == r_unknown.json()

    def test_forgot_invalid_email_422(self, s):
        r = s.post(f"{API}/auth/forgot-password", json={"email": "notanemail"})
        assert r.status_code == 422, r.text


# -----------------------------------------------------------------------------
# 2. rate limit — 4th request in an hour must NOT create a new doc
# -----------------------------------------------------------------------------
class TestForgotRateLimit:
    def test_rate_limit_bug_present(self, s, db):
        """BUG: rate limit is bypassed because delete_many({used:False}) wipes
        prior unused codes before the next count runs. Result: recent count
        never exceeds 1, so >_RESET_MAX_PER_HOUR requests are silently allowed.
        Expected (per spec): 4th call should NOT create a new password_resets doc.
        Actual: every call replaces the prior doc, so the limit never engages."""
        _reset_rate_limit(db, RESET_EMAIL)
        # Request 4 codes back-to-back.
        for _ in range(4):
            r = s.post(f"{API}/auth/forgot-password", json={"email": RESET_EMAIL})
            assert r.status_code == 200
        # Spec says: count in last hour should be 3 (4th call rate-limited).
        # Bug: after each call, delete_many wipes the previous doc — so count == 1.
        count = db.password_resets.count_documents({"email": RESET_EMAIL.lower()})
        if count == 1:
            pytest.fail(
                "RATE-LIMIT BUG: 4 forgot-password calls produced only 1 doc in DB. "
                "delete_many({used:False}) runs BEFORE the next call's count, wiping "
                "prior codes and defeating the 3/hour limit. Attackers can spam the "
                "endpoint indefinitely, causing the Emergent proxy to send unlimited "
                "reset e-mails to a target address."
            )
        assert count == 3, f"expected 3 docs (last one was rate-limited), got {count}"


# -----------------------------------------------------------------------------
# 3. Full reset-password happy path (+ wrong code, code reuse, short pw)
# -----------------------------------------------------------------------------
class TestResetPasswordFlow:
    def test_full_reset_flow(self, s, db):
        # Clean slate: reset rate limit and request a fresh code
        _reset_rate_limit(db, RESET_EMAIL)
        r = s.post(f"{API}/auth/forgot-password", json={"email": RESET_EMAIL})
        assert r.status_code == 200
        # Give backend a moment to insert the doc
        time.sleep(0.3)
        doc = db.password_resets.find_one(
            {"email": RESET_EMAIL.lower(), "used": False},
            sort=[("created_at", -1)],
        )
        assert doc, "No password_resets doc found after forgot-password"

        # Create a session BEFORE reset to verify it gets revoked
        login_before = s.post(f"{API}/auth/login",
                              json={"email": RESET_EMAIL, "password": INITIAL_PASSWORD})
        assert login_before.status_code == 200, login_before.text
        old_token = login_before.json()["session_token"]
        me1 = requests.get(f"{API}/auth/me",
                           headers={"Authorization": f"Bearer {old_token}"})
        assert me1.status_code == 200

        # Brute-force the code
        code = _brute_force_code(doc["code_hash"], RESET_EMAIL.lower())
        assert code, "Could not brute-force reset code"
        print(f"Recovered reset code: {code}")

        # Wrong code → 400 + attempts++
        wrong = "000000" if code != "000000" else "111111"
        r_wrong = s.post(f"{API}/auth/reset-password",
                         json={"email": RESET_EMAIL, "code": wrong, "new_password": NEW_PASSWORD})
        assert r_wrong.status_code == 400
        assert r_wrong.json().get("detail") == "Invalid or expired code"
        doc_after_wrong = db.password_resets.find_one(
            {"email": RESET_EMAIL.lower(), "code_hash": doc["code_hash"]})
        assert doc_after_wrong["attempts"] == 1, (
            f"attempts not incremented: {doc_after_wrong.get('attempts')}")

        # Short new_password → 422 (Pydantic min_length=12)
        r_short = s.post(f"{API}/auth/reset-password",
                         json={"email": RESET_EMAIL, "code": code, "new_password": "short11char"})
        assert r_short.status_code == 422, r_short.text

        # Correct code + valid password → 200
        r_ok = s.post(f"{API}/auth/reset-password",
                      json={"email": RESET_EMAIL, "code": code, "new_password": NEW_PASSWORD})
        assert r_ok.status_code == 200, r_ok.text
        assert "sign in" in r_ok.json().get("message", "").lower()

        # Session revocation: old token must now 401
        me2 = requests.get(f"{API}/auth/me",
                           headers={"Authorization": f"Bearer {old_token}"})
        assert me2.status_code == 401, f"expected 401 after reset, got {me2.status_code}"

        # Old password must fail (401)
        r_old = s.post(f"{API}/auth/login",
                       json={"email": RESET_EMAIL, "password": INITIAL_PASSWORD})
        assert r_old.status_code == 401

        # New password must succeed (200)
        r_new = s.post(f"{API}/auth/login",
                       json={"email": RESET_EMAIL, "password": NEW_PASSWORD})
        assert r_new.status_code == 200

        # Code reuse must fail (already used) → 400
        r_reuse = s.post(f"{API}/auth/reset-password",
                         json={"email": RESET_EMAIL, "code": code, "new_password": NEW_PASSWORD})
        assert r_reuse.status_code == 400

        # Persist new password for downstream tests / test_credentials.md
        print(f"RESET_EMAIL={RESET_EMAIL} NEW_PASSWORD={NEW_PASSWORD}")


# -----------------------------------------------------------------------------
# 4. Quick regressions — register, login, dev-bypass, bogus /auth/session
# -----------------------------------------------------------------------------
class TestRegressions:
    def test_register_still_works(self, s):
        email = f"TEST_reset_reg_{uuid.uuid4().hex[:8]}@guardian.app"
        r = s.post(f"{API}/auth/register",
                   json={"email": email, "password": "abcdefghijkl12", "name": "R"})
        assert r.status_code == 201, r.text
        assert r.json()["session_token"].startswith("gs-")

    def test_login_demo_still_works(self, s):
        r = s.post(f"{API}/auth/login",
                   json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
        assert r.status_code == 200, r.text

    def test_dev_bypass_founder(self, s):
        r = s.post(f"{API}/auth/dev-bypass",
                   json={"email": FOUNDER_EMAIL, "name": "Guardian Angel"})
        assert r.status_code == 200, r.text

    def test_bogus_session_id_401(self, s):
        r = s.post(f"{API}/auth/session",
                   json={"session_id": f"bogus-{uuid.uuid4().hex}"})
        assert r.status_code == 401
