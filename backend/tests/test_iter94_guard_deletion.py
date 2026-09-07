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


def test_reward_actions_require_device_id():
    req_h, _ = _user("nodev-a", "203.0.113.71", "dev-nodev-a")
    helper_h, _ = _user("nodev-b", "203.0.113.72", "dev-nodev-b")
    rid = _create(req_h)
    anon = {k: v for k, v in helper_h.items() if k != "X-Device-Id"}      # client hiding its device identity
    r = requests.post(f"{BASE}/help/requests/{rid}/accept", headers=anon, timeout=20)
    assert r.status_code == 400 and "device_required" in r.text, r.text
    assert requests.post(f"{BASE}/help/requests/{rid}/accept", headers=helper_h, timeout=20).status_code == 200


def test_fund_sourced_rewards_capped_per_helper():
    helper_h, _ = _user("fund-h", "203.0.113.80", "dev-fund-h")
    for i in range(3):                                            # 3 empty-wallet requesters → fund-sourced escrow
        rh, _ = _user(f"fund-r{i}", f"203.0.113.{81 + i}", f"dev-fund-r{i}")
        rid = _create(rh)
        assert requests.post(f"{BASE}/help/requests/{rid}/accept", headers=helper_h, timeout=20).status_code == 200, i
    rh, _ = _user("fund-r9", "203.0.113.89", "dev-fund-r9")
    rid = _create(rh)
    r = requests.post(f"{BASE}/help/requests/{rid}/accept", headers=helper_h, timeout=20)
    assert r.status_code == 429 and "fund_limit" in r.text, r.text


def test_client_ip_ignores_spoofed_left_xff_hop():
    """Through the real ingress the chain is `client, cloudflare, lb`; a client-prepended hop must be ignored.
    Two accounts that only differ in a SPOOFED leftmost hop share the real (3rd-from-right) address → same network."""
    chain = "198.51.100.200, 172.71.1.1, 34.120.7.31"
    req_h, _ = _user("xff-a", "9.9.9.9, " + chain, "dev-xff-a")
    helper_h, _ = _user("xff-b", "8.8.8.8, " + chain, "dev-xff-b")
    rid = _create(req_h)
    r = requests.post(f"{BASE}/help/requests/{rid}/accept", headers=helper_h, timeout=20)
    assert r.status_code == 403 and "network" in r.text, r.text


# ---------------- public account-deletion requests ----------------
def test_deletion_policy_public():
    r = requests.get(f"{BASE}/account/deletion-policy", timeout=20)
    assert r.status_code == 200 and r.json()["processing_days"] == 30 and r.json()["erased"]


def test_deletion_request_public_and_founder_only_queue():
    h, u = _user("del", "203.0.113.51", "dev-del")
    # public, no auth, works for existing AND unknown e-mails with the same generic answer
    r = requests.post(f"{BASE}/account/deletion-request", json={"email": u["email"], "reason": "leaving"}, timeout=20)
    assert r.status_code == 202 and r.json()["ok"] and r.json()["req_id"] and r.json()["verify_required"], r.text
    rid = r.json()["req_id"]
    r2 = requests.post(f"{BASE}/account/deletion-request", json={"email": u["email"]}, timeout=20)
    assert r2.status_code == 202 and r2.json()["req_id"] == rid          # de-duplicated within 24 h
    r3 = requests.post(f"{BASE}/account/deletion-request", json={"email": f"nobody-{uuid.uuid4().hex[:6]}@example.com"}, timeout=20)
    assert r3.status_code == 202 and set(r3.json()) == set(r.json())     # no enumeration
    assert requests.post(f"{BASE}/account/deletion-request", json={"email": "not-an-email"}, timeout=20).status_code == 400
    # wrong / missing code → generic 400 (for the unknown-account request there is no code at all)
    assert requests.post(f"{BASE}/account/deletion-request/{rid}/verify", json={"code": "000000"}, timeout=20).status_code == 400
    assert requests.post(f"{BASE}/account/deletion-request/{r3.json()['req_id']}/verify", json={"code": "123456"}, timeout=20).status_code == 400
    # the queue is Founder-only
    assert requests.get(f"{BASE}/account/deletion-requests", headers=h, timeout=20).status_code == 403
    assert requests.post(f"{BASE}/account/deletion-requests/{rid}/process", headers=h, timeout=20).status_code == 403


def _code_for(req_id: str) -> str:
    """Test helper: brute-force the 6-digit code against the stored hash (test DB only)."""
    import hashlib
    from pymongo import MongoClient
    from dotenv import dotenv_values
    env = dotenv_values("/app/backend/.env")
    doc = MongoClient(env["MONGO_URL"])[env.get("DB_NAME", "test_database")].deletion_requests.find_one({"req_id": req_id})
    for n in range(10**6):
        code = f"{n:06d}"
        if hashlib.sha256(f"{req_id}:{code}".encode()).hexdigest() == doc["code_hash"]:
            return code
    raise AssertionError("code not found")


@pytest.mark.skipif(not os.environ.get("FOUNDER_TEST_PASSWORD"), reason="FOUNDER_TEST_PASSWORD not set")
def test_founder_processes_deletion_request():
    fe = os.environ.get("FOUNDER_EMAIL", "guardianangel.core@proton.me")
    r = requests.post(f"{BASE}/auth/login", json={"email": fe, "password": os.environ["FOUNDER_TEST_PASSWORD"]}, timeout=20)
    assert r.status_code == 200, r.text
    fh = {"Authorization": f"Bearer {r.json()['session_token']}"}
    h, u = _user("del2", "203.0.113.61", "dev-del2")
    rid = requests.post(f"{BASE}/account/deletion-request", json={"email": u["email"]}, timeout=20).json()["req_id"]
    q = requests.get(f"{BASE}/account/deletion-requests", headers=fh, timeout=20).json()
    row = next(x for x in q["requests"] if x["req_id"] == rid)
    assert row["account_exists"] and row["verified"] is False and "code_hash" not in row
    # unverified → the Founder cannot purge (412) …
    p = requests.post(f"{BASE}/account/deletion-requests/{rid}/process", headers=fh, timeout=20)
    assert p.status_code == 412, p.text
    assert requests.get(f"{BASE}/auth/me", headers=h, timeout=20).status_code == 200      # account still there
    # … the owner proves the e-mail with the code …
    code = _code_for(rid)
    v = requests.post(f"{BASE}/account/deletion-request/{rid}/verify", json={"code": code}, timeout=20)
    assert v.status_code == 200 and v.json()["verified"] is True, v.text
    # … and now the purge goes through
    p = requests.post(f"{BASE}/account/deletion-requests/{rid}/process", headers=fh, timeout=20)
    assert p.status_code == 200 and p.json()["account_purged"] is True, p.text
    assert requests.get(f"{BASE}/auth/me", headers=h, timeout=20).status_code == 401   # account is gone
    assert requests.post(f"{BASE}/account/deletion-requests/{rid}/process", headers=fh, timeout=20).status_code == 409
