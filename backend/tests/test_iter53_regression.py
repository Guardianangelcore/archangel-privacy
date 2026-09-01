"""Iteration 53 — light auth regression (no backend changes expected)."""
import os
import time
import uuid
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/")


def test_register_success():
    email = f"TEST_iter53_reg_{uuid.uuid4().hex[:8]}@guardian.app"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "iter53-test-password-01", "name": "Iter53"},
        timeout=15,
    )
    assert r.status_code == 201, f"expected 201 got {r.status_code} body={r.text}"
    j = r.json()
    assert "session_token" in j and "user" in j
    assert j["user"]["email"] == email.lower()


def test_register_short_password_rejected():
    email = f"TEST_iter53_short_{uuid.uuid4().hex[:8]}@guardian.app"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "short", "name": "X"},
        timeout=15,
    )
    assert r.status_code in (400, 422), f"expected 400/422 got {r.status_code}"


def test_login_demo_ok():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "demo.judge@guardian.app", "password": "guardian-demo-2026"},
        timeout=15,
    )
    assert r.status_code == 200, f"expected 200 got {r.status_code} body={r.text}"
    j = r.json()
    assert "session_token" in j


def test_login_wrong_password():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "demo.judge@guardian.app", "password": "definitely-wrong-pw-01"},
        timeout=15,
    )
    assert r.status_code == 401


def test_dev_bypass_founder():
    r = requests.post(
        f"{BASE_URL}/api/auth/dev-bypass",
        json={"email": "guardian.angel.core@proton.me", "name": "Guardian Angel"},
        timeout=15,
    )
    assert r.status_code == 200, f"expected 200 got {r.status_code} body={r.text}"
    j = r.json()
    assert "session_token" in j
    tok = j["session_token"]
    me = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {tok}"}, timeout=15)
    assert me.status_code == 200
    mj = me.json().get("user", me.json())
    assert mj.get("email") == "guardian.angel.core@proton.me"
    assert mj.get("tier") in ("archangel", "sentinel", "guardian", "sovereign"), mj.get("tier")
