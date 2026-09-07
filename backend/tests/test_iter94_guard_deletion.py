"""Iter 94 — GA-T farming guard + public account-deletion requests.

Runs against the LOCAL backend (http://localhost:8001) so the tests can spoof X-Forwarded-For /
X-Device-Id and exercise the same-device / same-network / pair-limit rules. Accounts are created
with password registration (the dev bypass is disabled).
"""
import os
import uuid
import requests
import pytest

BASE = os.environ.get("LOCAL_API", "http://localhost:8001").rstrip("/") + "/api"
TOS = "2026-06.1"
PW = "StrongPassw0rd!!94"


def _user(tag: str, ip: str, device: str):
    email = f"iter94-{tag}-{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{BASE}/auth/register", json={"email": email, "password": PW, "name": tag,
                                                     "tos_accepted": True, "tos_version": TOS},
                      headers={"X-Forwarded-For": ip, "X-Device-Id": device}, timeout=20)
    assert r.status_code in (200, 201), r.text
    tok = r.json()["session_token"]
    h = {"Authorization": f"Bearer {tok}", "X-Forwarded-For": ip, "X-Device-Id": device}
    return h, r.json()["user"]


def _create(h):
    r = requests.post(f"{BASE}/help/requests", json={"title": "Pick up my prescription", "category": "medication"}, headers=h, timeout=20)
    assert r.status_code == 201, r.text
    return r.json()["request"]["req_id"]


# ---------------- unverified daily cap ----------------
def test_unverified_daily_cap_20_gat():
    h, _ = _user("cap", "203.0.113.10", "dev-cap")
    earned = 0.0
    for _ in range(4):                                       # 4 × 5 GA-T = 20 → allowed
        r = requests.post(f"{BASE}/token/earn", json={"activity": "proof_of_health"}, headers=h, timeout=20)
        assert r.status_code == 200, r.text
        earned += r.json()["tx"]["amount"]
    assert earned == 20.0
    r = requests.post(f"{BASE}/token/earn", json={"activity": "proof_of_health"}, headers=h, timeout=20)
    assert r.status_code == 429, r.text                      # 5th would exceed the combined cap
    r = requests.post(f"{BASE}/token/earn", json={"activity": "document_scan"}, headers=h, timeout=20)
    assert r.status_code == 429, r.text                      # other unverified kind shares the cap
    w = requests.get(f"{BASE}/token/wallet", headers=h, timeout=20).json()
    assert w["unverified_daily_cap"] == 20.0 and w["balance"] == 20.0


# ---------------- same device / same network ----------------
def test_same_device_help_blocked():
    req_h, _ = _user("dev-a", "203.0.113.21", "shared-device-1")
    helper_h, _ = _user("dev-b", "203.0.113.22", "shared-device-1")   # different IP, SAME device
    rid = _create(req_h)
    r = requests.post(f"{BASE}/help/requests/{rid}/accept", headers=helper_h, timeout=20)
    assert r.status_code == 403 and "same_origin" in r.text and "device" in r.text, r.text


def test_same_network_help_blocked():
    req_h, _ = _user("net-a", "198.51.100.7", "dev-net-a")
    helper_h, _ = _user("net-b", "198.51.100.7", "dev-net-b")          # different device, SAME IP
    rid = _create(req_h)
    r = requests.post(f"{BASE}/help/requests/{rid}/accept", headers=helper_h, timeout=20)
    assert r.status_code == 403 and "network" in r.text, r.text


# ---------------- legit pair → then pair limit ----------------
def test_legit_help_then_pair_limit():
    req_h, req_u = _user("pair-a", "203.0.113.31", "dev-pair-a")
    helper_h, helper_u = _user("pair-b", "203.0.113.32", "dev-pair-b")
    rid = _create(req_h)
    assert requests.post(f"{BASE}/help/requests/{rid}/accept", headers=helper_h, timeout=20).status_code == 200
    assert requests.post(f"{BASE}/help/requests/{rid}/done", headers=helper_h, timeout=20).status_code == 200
    r = requests.post(f"{BASE}/help/requests/{rid}/confirm", headers=req_h, timeout=20)
    assert r.status_code == 200, r.text
    assert r.json()["request"]["status"] == "confirmed"
    # second rewarded help between the same two people within 24 h → blocked at accept (either direction)
    rid2 = _create(req_h)
    r = requests.post(f"{BASE}/help/requests/{rid2}/accept", headers=helper_h, timeout=20)
    assert r.status_code == 429 and "pair_limit" in r.text, r.text
    rid3 = _create(helper_h)
    r = requests.post(f"{BASE}/help/requests/{rid3}/accept", headers=req_h, timeout=20)
    assert r.status_code == 429 and "pair_limit" in r.text, r.text
    # a third, unrelated helper is still fine
    other_h, _ = _user("pair-c", "203.0.113.33", "dev-pair-c")
    assert requests.post(f"{BASE}/help/requests/{rid2}/accept", headers=other_h, timeout=20).status_code == 200
    lim = requests.get(f"{BASE}/help/requests", headers=req_h, timeout=20).json()["limits"]
    assert lim["pair_window_h"] == 24 and lim["same_origin_blocked"] is True


def test_device_and_ip_log_not_exposed():
    h, _ = _user("priv", "203.0.113.41", "dev-priv")
    _create(h)
    me = requests.get(f"{BASE}/auth/me", headers=h, timeout=20).json()
    blob = str(me)
    assert "device_ids" not in blob and "ip_log" not in blob


# ---------------- public account-deletion requests ----------------
def test_deletion_policy_public():
    r = requests.get(f"{BASE}/account/deletion-policy", timeout=20)
    assert r.status_code == 200 and r.json()["processing_days"] == 30 and r.json()["erased"]


def test_deletion_request_public_and_founder_only_queue():
    h, u = _user("del", "203.0.113.51", "dev-del")
    # public, no auth, works for existing AND unknown e-mails with the same generic answer
    r = requests.post(f"{BASE}/account/deletion-request", json={"email": u["email"], "reason": "leaving"}, timeout=20)
    assert r.status_code == 202 and r.json()["ok"] and r.json()["req_id"], r.text
    rid = r.json()["req_id"]
    r2 = requests.post(f"{BASE}/account/deletion-request", json={"email": u["email"]}, timeout=20)
    assert r2.status_code == 202 and r2.json()["req_id"] == rid          # de-duplicated within 24 h
    r3 = requests.post(f"{BASE}/account/deletion-request", json={"email": f"nobody-{uuid.uuid4().hex[:6]}@example.com"}, timeout=20)
    assert r3.status_code == 202 and set(r3.json()) == set(r.json())     # no enumeration
    assert requests.post(f"{BASE}/account/deletion-request", json={"email": "not-an-email"}, timeout=20).status_code == 400
    # the queue is Founder-only
    assert requests.get(f"{BASE}/account/deletion-requests", headers=h, timeout=20).status_code == 403
    assert requests.post(f"{BASE}/account/deletion-requests/{rid}/process", headers=h, timeout=20).status_code == 403


@pytest.mark.skipif(not os.environ.get("FOUNDER_TEST_PASSWORD"), reason="FOUNDER_TEST_PASSWORD not set")
def test_founder_processes_deletion_request():
    fe = os.environ.get("FOUNDER_EMAIL", "guardianangel.core@proton.me")
    r = requests.post(f"{BASE}/auth/login", json={"email": fe, "password": os.environ["FOUNDER_TEST_PASSWORD"]}, timeout=20)
    assert r.status_code == 200, r.text
    fh = {"Authorization": f"Bearer {r.json()['session_token']}"}
    h, u = _user("del2", "203.0.113.61", "dev-del2")
    rid = requests.post(f"{BASE}/account/deletion-request", json={"email": u["email"]}, timeout=20).json()["req_id"]
    q = requests.get(f"{BASE}/account/deletion-requests", headers=fh, timeout=20).json()
    assert any(x["req_id"] == rid and x["account_exists"] for x in q["requests"])
    p = requests.post(f"{BASE}/account/deletion-requests/{rid}/process", headers=fh, timeout=20)
    assert p.status_code == 200 and p.json()["account_purged"] is True, p.text
    assert requests.get(f"{BASE}/auth/me", headers=h, timeout=20).status_code == 401   # account is gone
    assert requests.post(f"{BASE}/account/deletion-requests/{rid}/process", headers=fh, timeout=20).status_code == 409
