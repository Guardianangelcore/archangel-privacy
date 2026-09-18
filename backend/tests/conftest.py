"""Shared test plumbing for the backend suite.

PASSWORD SIGN-UP INSTEAD OF THE DEV BYPASS
------------------------------------------
`POST /auth/dev-bypass` (passwordless session minting) is DISABLED for security (SEC-001, Iter 92).
Dozens of older suites still create their throw-away accounts through it, so this conftest transparently
redirects every dev-bypass POST made with `requests`, `requests.Session` or `httpx` to real password
registration (`/auth/register`, falling back to `/auth/login` when the account already exists) using one
deterministic test password. The response keeps the dev-bypass shape (`session_token`, `user`, HTTP 200).

* Founder / store-reviewer e-mails are passed through to the REAL endpoint — those tests assert the 403.
* Sessions are minted against the local backend when it is reachable (same MongoDB as the preview URL),
  each call from a distinct fake X-Forwarded-For hop so the per-IP register/login throttles never trip
  during a full run. Otherwise the URL the test used is honoured.

Override the password with TEST_ACCOUNT_PASSWORD when the accounts were created with another one.
"""
import itertools
import json
import os
import re

import httpx
import requests
from dotenv import dotenv_values

_ENV = dotenv_values("/app/backend/.env")
TEST_PASSWORD = os.environ.get("TEST_ACCOUNT_PASSWORD", "GuardianTest-Passw0rd!2026")
TOS_VERSION = "2026-06.1"
LOCAL_API = os.environ.get("LOCAL_API", "http://localhost:8001").rstrip("/") + "/api"
PRIVILEGED = {e.strip().lower() for e in (
    os.environ.get("FOUNDER_EMAIL") or _ENV.get("FOUNDER_EMAIL") or "guardianangel.core@proton.me",
    os.environ.get("REVIEWER_EMAIL") or _ENV.get("REVIEWER_EMAIL") or "appreview@archangel-os.app",
)}
_BYPASS_RE = re.compile(r"/auth/dev-bypass/?$")

_real_requests_post = requests.post
_real_session_post = requests.Session.post
_real_httpx_post = httpx.post
_counter = itertools.count(1)
_local_ok = None


def _fake_ip() -> str:
    n = next(_counter)
    return f"10.{(n >> 16) & 255}.{(n >> 8) & 255}.{n & 255}"


def _local_available() -> bool:
    global _local_ok
    if _local_ok is None:
        try:
            _local_ok = requests.get(LOCAL_API.replace("/api", "/health"), timeout=3).status_code == 200
        except requests.RequestException:
            _local_ok = False
    return _local_ok


def _payload(kw: dict) -> dict:
    if kw.get("json") is not None:
        return dict(kw["json"])
    data = kw.get("data")
    if isinstance(data, (str, bytes)):
        try:
            return json.loads(data)
        except ValueError:
            return {}
    return dict(data or {})


def password_session(api_base: str, email: str, name: str | None = None) -> requests.Response:
    """Register (or log in) a test account with the deterministic password → dev-bypass-shaped Response."""
    email = email.strip().lower()
    bases = ([LOCAL_API] if _local_available() else []) + [api_base]
    last = None
    for base in bases:
        headers = {"X-Forwarded-For": _fake_ip(), "X-Device-Id": f"pytest-{email}"}
        try:
            r = _real_requests_post(f"{base}/auth/register",
                                    json={"email": email, "password": TEST_PASSWORD, "name": name or "Test Guardian",
                                          "tos_accepted": True, "tos_version": TOS_VERSION},
                                    headers=headers, timeout=25)
            if r.status_code == 409:                                    # account exists → sign in
                r = _real_requests_post(f"{base}/auth/login", json={"email": email, "password": TEST_PASSWORD},
                                        headers=headers, timeout=25)
            last = r
            if r.status_code in (200, 201):
                r.status_code = 200                                     # the bypass used to answer 200
                return r
        except requests.RequestException:
            continue
    return last


def _privileged_login(api_base: str, email: str) -> requests.Response | None:
    """Founder / reviewer never had a passwordless path any more — sign them in with their real password
    when the runner knows it (FOUNDER_TEST_PASSWORD env · REVIEWER_PASSWORD from backend/.env)."""
    founder = (os.environ.get("FOUNDER_EMAIL") or _ENV.get("FOUNDER_EMAIL") or "guardianangel.core@proton.me").lower()
    pw = os.environ.get("FOUNDER_TEST_PASSWORD") if email == founder else (os.environ.get("REVIEWER_PASSWORD") or _ENV.get("REVIEWER_PASSWORD"))
    if not pw:
        return None
    bases = ([LOCAL_API] if _local_available() else []) + [api_base]
    last = None
    for base in bases:
        try:
            r = _real_requests_post(f"{base}/auth/login", json={"email": email, "password": pw},
                                    headers={"X-Forwarded-For": _fake_ip()}, timeout=25)
            last = r
            if r.status_code == 200:
                return r
        except requests.RequestException:
            continue
    return last


def _redirect(url: str, kw: dict):
    """Return a Response when `url` is the dev bypass, else None (→ the real call is made)."""
    if not _BYPASS_RE.search(url):
        return None
    payload = _payload(kw)
    email = (payload.get("email") or "").strip().lower()
    if not email:
        return None
    api_base = url[: _BYPASS_RE.search(url).start()]
    if email in PRIVILEGED:
        return _privileged_login(api_base, email)                       # None → real endpoint (403)
    return password_session(api_base, email, payload.get("name"))


real_post = _real_requests_post   # for tests that must hit the REAL /auth/dev-bypass gate


def _requests_post(url, *args, **kwargs):
    return _redirect(url, kwargs) or _real_requests_post(url, *args, **kwargs)


def _session_post(self, url, *args, **kwargs):
    return _redirect(url, kwargs) or _real_session_post(self, url, *args, **kwargs)


def _httpx_post(url, *args, **kwargs):
    r = _redirect(str(url), kwargs)
    if r is None:
        return _real_httpx_post(url, *args, **kwargs)
    return httpx.Response(status_code=r.status_code, json=r.json() if r.content else None,
                          request=httpx.Request("POST", str(url)))


requests.post = _requests_post
requests.Session.post = _session_post
httpx.post = _httpx_post


# ---------------------------------------------------------------------------------------------
# FIXED SMOKE SESSIONS — ~36 suites authenticate with well-known bearer tokens that earlier agents
# seeded straight into MongoDB (`smoketok-fresh-2026` → smoketest-user-1, `…-u2` → smoketest-user-2,
# `smoketok-fresh-handover` → user_smoke2026). Sessions expire (30 d) and get swept, so every run
# re-arms them for another 30 days. Test/preview database only — the fixture is a no-op when the
# users do not exist (e.g. a production database).
# ---------------------------------------------------------------------------------------------
import pytest
from datetime import datetime, timezone, timedelta

SMOKE_SESSIONS = {
    "smoketok-fresh-2026": "smoketest-user-1",
    "smoketok-fresh-2026-u2": "smoketest-user-2",
    "smoketok-fresh-handover": "user_smoke2026",
}


@pytest.fixture(scope="session", autouse=True)
def _arm_smoke_sessions():
    try:
        from pymongo import MongoClient
        mongo_url = os.environ.get("MONGO_URL") or _ENV.get("MONGO_URL")
        if not mongo_url:
            return
        db = MongoClient(mongo_url, serverSelectionTimeoutMS=3000)[os.environ.get("DB_NAME") or _ENV.get("DB_NAME") or "test_database"]
        now = datetime.now(timezone.utc)
        for token, uid in SMOKE_SESSIONS.items():
            if not db.users.find_one({"user_id": uid}, {"_id": 1}):
                continue
            db.user_sessions.update_one({"session_token": token}, {"$set": {
                "user_id": uid, "expires_at": now + timedelta(days=30), "via": "pytest_smoke"},
                "$setOnInsert": {"created_at": now}}, upsert=True)
    except Exception as e:                      # never block the run on seeding problems
        print(f"[conftest] smoke sessions not armed: {e}")
