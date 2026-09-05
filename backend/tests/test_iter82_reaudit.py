import pytest
"""Iteration 82 — second security audit remediation: UHP partner vetting + patient consent, founder binding, beam throttle."""
import os, uuid, time, hmac, hashlib, json, requests

BASE = os.environ.get("EXPO_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/") + "/api"
FOUNDER = "guardianangel.core@proton.me"


def _founder_pw() -> str:
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    pw = os.environ.get("FOUNDER_TEST_PASSWORD", "").strip()   # SEC-002: never stored in the repo — export it before running
    if not pw:
        pytest.skip("FOUNDER_TEST_PASSWORD env not set (founder password is not stored in the repository)")
    return pw


def _founder():
    r = requests.post(f"{BASE}/auth/login", json={"email": FOUNDER, "password": _founder_pw()}, timeout=15)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['session_token']}"}


def _user(tag):
    d = requests.post(f"{BASE}/auth/dev-bypass", json={"email": f"iter82-{tag}-{uuid.uuid4().hex[:6]}@example.com", "name": tag}, timeout=15).json()
    return {"Authorization": f"Bearer {d['session_token']}"}, d["user"]


def _ingest(key, sec, email):
    body = json.dumps({"protocol": "UHP/1.0", "kind": "vitals", "idempotency_key": uuid.uuid4().hex, "subject": {"email": email}, "payload": {"hr": 72}})
    ts = str(int(time.time()))
    sig = hmac.new(sec.encode(), f"{ts}.".encode() + body.encode(), hashlib.sha256).hexdigest()
    return requests.post(f"{BASE}/uhp/ingest", data=body, headers={"Content-Type": "application/json", "X-UHP-Key": key, "X-UHP-Timestamp": ts, "X-UHP-Signature": sig}, timeout=15)


def test_partner_vetting_and_patient_consent():
    p = requests.post(f"{BASE}/uhp/partners/register", json={"org_name": "Audit Lab", "org_type": "lab", "country": "SK", "contact_email": "a@b.io"}, timeout=15).json()
    pid, key, sec = p["partner_id"], p["api_key"], p["hmac_secret"]
    vh, victim = _user("victim")
    assert _ingest(key, sec, victim["email"]).status_code == 401           # pending partner
    assert requests.post(f"{BASE}/uhp/partners/{pid}/approve", headers=vh, timeout=15).status_code == 403   # not foundation
    fh = _founder()
    assert requests.post(f"{BASE}/uhp/partners/{pid}/approve", headers=fh, timeout=15).status_code == 200
    r = _ingest(key, sec, victim["email"])
    assert r.status_code == 403 and "consent_required" in r.text          # approved but no patient consent
    assert requests.post(f"{BASE}/uhp/consents", json={"partner_id": pid}, headers=vh, timeout=15).status_code == 201
    assert _ingest(key, sec, victim["email"]).status_code == 200
    assert requests.delete(f"{BASE}/uhp/consents/{pid}", headers=vh, timeout=15).status_code == 200
    assert _ingest(key, sec, victim["email"]).status_code == 403
    # unknown subject → same 403 (no enumeration)
    assert _ingest(key, sec, f"nobody-{uuid.uuid4().hex[:6]}@example.com").status_code == 403
    assert requests.post(f"{BASE}/uhp/partners/{pid}/suspend", headers=fh, timeout=15).status_code == 200


def test_founder_flag_bound_to_founder_email():
    fh = _founder()
    me = requests.get(f"{BASE}/auth/me", headers=fh, timeout=15).json()["user"]
    assert me["email"] == FOUNDER and me.get("is_founder") is True and me.get("inner_circle") is True
    uh, u = _user("plain")
    assert not requests.get(f"{BASE}/auth/me", headers=uh, timeout=15).json()["user"].get("is_founder")


def test_beam_code_guessing_throttled():
    ip = f"203.0.113.{uuid.uuid4().int % 250 + 1}"
    codes = [requests.post(f"{BASE}/clinic-sync/beam/ABCDEF123456", json={"clinic_name": "c", "title": "t", "report_text": "x" * 12},
                           headers={"X-Forwarded-For": ip}, timeout=15).status_code for _ in range(12)]
    assert codes[0] == 404 and 429 in codes
