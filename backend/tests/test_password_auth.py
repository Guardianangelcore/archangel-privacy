"""
Tests for classic email/password authentication (register, login, session).
Also regressions for Google session exchange and dev-bypass.
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://guardian-vault-13.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

DEMO_EMAIL = "demo.judge@guardian.app"
DEMO_PASSWORD = "guardian-demo-2026"
FOUNDER_EMAIL = "guardian.angel.core@proton.me"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# -----------------------------------------------------------------------------
# Register (happy path + validation + duplicate)
# -----------------------------------------------------------------------------
class TestRegister:
    def test_register_happy_path(self, s):
        email = f"TEST_reg_{uuid.uuid4().hex[:10]}@guardian.app"
        r = s.post(f"{API}/auth/register", json={"email": email, "password": "abcdefghijkl12", "name": "TestReg"})
        assert r.status_code == 201, r.text
        data = r.json()
        assert "session_token" in data and data["session_token"].startswith("gs-")
        assert "user" in data
        user = data["user"]
        assert user["email"] == email.lower()
        assert user["language"] == "en", f"expected default lang=en, got {user.get('language')}"
        # No password_hash exposed anywhere
        assert "password_hash" not in user
        assert "password_hash" not in data

    def test_register_duplicate_email_409(self, s):
        email = f"TEST_dup_{uuid.uuid4().hex[:10]}@guardian.app"
        r1 = s.post(f"{API}/auth/register", json={"email": email, "password": "abcdefghijkl12"})
        assert r1.status_code == 201
        r2 = s.post(f"{API}/auth/register", json={"email": email, "password": "abcdefghijkl99"})
        assert r2.status_code == 409, r2.text

    def test_register_short_password_422(self, s):
        r = s.post(f"{API}/auth/register", json={"email": f"TEST_sp_{uuid.uuid4().hex[:8]}@x.com", "password": "short12345"})
        assert r.status_code == 422, r.text

    def test_register_bytes_over_72_422(self, s):
        # 30 multibyte chars × 3 bytes = 90 UTF-8 bytes (over 72)
        pw = "ř" * 30  # 'ř' is 2 bytes; use 3-byte char instead
        pw = "€" * 30  # '€' is 3 bytes -> 90 bytes; length 30 chars (< max_length=72 char limit)
        r = s.post(f"{API}/auth/register", json={"email": f"TEST_big_{uuid.uuid4().hex[:8]}@x.com", "password": pw})
        assert r.status_code == 422, f"expected 422 for >72 bytes, got {r.status_code}: {r.text}"


# -----------------------------------------------------------------------------
# Login (correct, wrong pw, unknown email - all generic 401)
# -----------------------------------------------------------------------------
class TestLogin:
    def test_login_correct_demo_creds(self, s):
        r = s.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["session_token"].startswith("gs-")
        assert data["user"]["email"].lower() == DEMO_EMAIL.lower()
        assert "password_hash" not in data["user"]

    def test_login_case_insensitive_email(self, s):
        r = s.post(f"{API}/auth/login", json={"email": DEMO_EMAIL.upper(), "password": DEMO_PASSWORD})
        assert r.status_code == 200, r.text

    def test_login_wrong_password_401(self, s):
        r = s.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": "not-the-right-password-99"})
        assert r.status_code == 401, r.text
        assert r.json().get("detail") == "Incorrect email or password"

    def test_login_unknown_email_same_401(self, s):
        r = s.post(f"{API}/auth/login",
                   json={"email": f"nobody_{uuid.uuid4().hex}@nowhere.example", "password": "abcdefghijkl12"})
        assert r.status_code == 401, r.text
        assert r.json().get("detail") == "Incorrect email or password"


# -----------------------------------------------------------------------------
# Session token usable on /auth/me, revoked by /auth/logout
# -----------------------------------------------------------------------------
class TestSessionLifecycle:
    def test_register_then_me_then_logout(self, s):
        email = f"TEST_life_{uuid.uuid4().hex[:10]}@guardian.app"
        r = s.post(f"{API}/auth/register", json={"email": email, "password": "abcdefghijkl12"})
        assert r.status_code == 201, r.text
        tok = r.json()["session_token"]
        me = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tok}"})
        assert me.status_code == 200, me.text
        assert me.json()["user"]["email"] == email.lower()
        # logout
        lo = requests.post(f"{API}/auth/logout", headers={"Authorization": f"Bearer {tok}"})
        assert lo.status_code == 200
        me2 = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tok}"})
        assert me2.status_code == 401, me2.text


# -----------------------------------------------------------------------------
# Regressions: Google session exchange + dev-bypass founder
# -----------------------------------------------------------------------------
class TestRegressions:
    def test_google_session_bogus_returns_401(self, s):
        r = s.post(f"{API}/auth/session", json={"session_id": f"bogus-{uuid.uuid4().hex}"})
        assert r.status_code == 401, r.text

    def test_dev_bypass_founder(self, s):
        r = s.post(f"{API}/auth/dev-bypass", json={"email": FOUNDER_EMAIL, "name": "Guardian Angel"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["session_token"].startswith("gs-")
        assert data["user"]["email"] == FOUNDER_EMAIL
        # Sanity: /auth/me works with token
        me = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {data['session_token']}"})
        assert me.status_code == 200
