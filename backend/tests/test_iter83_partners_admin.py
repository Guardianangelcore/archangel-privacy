"""Iteration 83 — Partner Approval Panel: founder-only admin listing + approve/suspend/reactivate.

Follows the style of test_iter82_reaudit.py (password login helper).
"""
import os, uuid, time, hmac, hashlib, json, requests

BASE = os.environ.get("EXPO_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/") + "/api"
FOUNDER = "guardianangel.core@proton.me"


def _founder_pw() -> str:
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    return os.environ["FOUNDER_TEST_PASSWORD"]


def _founder():
    r = requests.post(f"{BASE}/auth/login", json={"email": FOUNDER, "password": _founder_pw()}, timeout=15)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['session_token']}"}


def _user(tag):
    d = requests.post(
        f"{BASE}/auth/dev-bypass",
        json={"email": f"iter83-{tag}-{uuid.uuid4().hex[:6]}@example.com", "name": tag},
        timeout=15,
    ).json()
    return {"Authorization": f"Bearer {d['session_token']}"}, d["user"]


def _register(tag="clinic"):
    body = {
        "org_name": f"TEST_iter83_{tag}_{uuid.uuid4().hex[:6]}",
        "org_type": "clinic",
        "country": "SK",
        "contact_email": f"partner-{uuid.uuid4().hex[:6]}@test.io",
    }
    r = requests.post(f"{BASE}/uhp/partners/register", json=body, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["partner_id"].startswith("uhp_")
    assert data["api_key"].startswith("uhpk_")
    assert data["hmac_secret"]
    return body["org_name"], data


def _sign(sec: str, ts: str, body_bytes: bytes) -> str:
    return hmac.new(sec.encode(), f"{ts}.".encode() + body_bytes, hashlib.sha256).hexdigest()


def _ingest_sensor(key: str, sec: str):
    body = json.dumps({
        "protocol": "UHP/1.0",
        "kind": "sensor",
        "idempotency_key": uuid.uuid4().hex,
        "subject": {},
        "payload": {"stream_id": f"s-{uuid.uuid4().hex[:6]}"},
    })
    ts = str(int(time.time()))
    sig = _sign(sec, ts, body.encode())
    return requests.post(
        f"{BASE}/uhp/ingest",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-UHP-Key": key,
            "X-UHP-Timestamp": ts,
            "X-UHP-Signature": sig,
        },
        timeout=15,
    )


# --- register partner (public) ---------------------------------------------
def test_register_partner_pending():
    org_name, data = _register("pending")
    fh = _founder()
    admin = requests.get(f"{BASE}/uhp/partners/admin", headers=fh, timeout=15).json()
    pending_ids = [p["partner_id"] for p in admin["pending"]]
    assert data["partner_id"] in pending_ids
    # ensure secrets never leak in admin listing
    for bucket in ("pending", "active", "suspended"):
        for row in admin[bucket]:
            assert "api_key" not in row and "hmac_secret" not in row
            assert isinstance(row.get("consents"), int)


# --- admin endpoint auth guards --------------------------------------------
def test_admin_requires_founder():
    r = requests.get(f"{BASE}/uhp/partners/admin", timeout=15)
    assert r.status_code == 401, r.text
    uh, _ = _user("plain")
    r = requests.get(f"{BASE}/uhp/partners/admin", headers=uh, timeout=15)
    assert r.status_code == 403, r.text
    fh = _founder()
    r = requests.get(f"{BASE}/uhp/partners/admin", headers=fh, timeout=15)
    assert r.status_code == 200
    body = r.json()
    for k in ("pending", "active", "suspended", "counts"):
        assert k in body
    for s in ("pending", "active", "suspended"):
        assert isinstance(body["counts"].get(s), int)
        assert len(body[s]) == body["counts"][s]


# --- approve / suspend / reactivate lifecycle ------------------------------
def test_approve_suspend_reactivate():
    org, p = _register("lifecycle")
    pid, key, sec = p["partner_id"], p["api_key"], p["hmac_secret"]
    fh = _founder()

    # non-founder cannot approve/suspend
    uh, _ = _user("nonfound")
    assert requests.post(f"{BASE}/uhp/partners/{pid}/approve", headers=uh, timeout=15).status_code == 403
    assert requests.post(f"{BASE}/uhp/partners/{pid}/suspend", headers=uh, timeout=15).status_code == 403

    # pending → ingest is rejected (401 unknown/suspended)
    r = _ingest_sensor(key, sec)
    assert r.status_code == 401, r.text

    # approve
    r = requests.post(f"{BASE}/uhp/partners/{pid}/approve", headers=fh, timeout=15)
    assert r.status_code == 200 and r.json() == {"ok": True, "partner_id": pid, "status": "active"}

    # approving an already-active partner → 404 (nothing to modify)
    r = requests.post(f"{BASE}/uhp/partners/{pid}/approve", headers=fh, timeout=15)
    assert r.status_code == 404, r.text

    # sensor ingest now works (no consent needed for kind=sensor)
    r = _ingest_sensor(key, sec)
    assert r.status_code == 200, r.text
    assert r.json().get("accepted") is True

    # suspend
    r = requests.post(f"{BASE}/uhp/partners/{pid}/suspend", headers=fh, timeout=15)
    assert r.status_code == 200 and r.json()["status"] == "suspended"

    # suspended → ingest 401 again
    r = _ingest_sensor(key, sec)
    assert r.status_code == 401

    # reactivate via approve
    r = requests.post(f"{BASE}/uhp/partners/{pid}/approve", headers=fh, timeout=15)
    assert r.status_code == 200 and r.json()["status"] == "active"

    r = _ingest_sensor(key, sec)
    assert r.status_code == 200

    # cleanup — leave in suspended state
    requests.post(f"{BASE}/uhp/partners/{pid}/suspend", headers=fh, timeout=15)


def test_suspend_unknown_id():
    fh = _founder()
    r = requests.post(f"{BASE}/uhp/partners/uhp_doesnotexist/suspend", headers=fh, timeout=15)
    assert r.status_code == 404, r.text


# --- counts reflect action ---------------------------------------------------
def test_counts_update_after_actions():
    fh = _founder()
    before = requests.get(f"{BASE}/uhp/partners/admin", headers=fh, timeout=15).json()["counts"]
    org, p = _register("counts")
    pid = p["partner_id"]
    after_reg = requests.get(f"{BASE}/uhp/partners/admin", headers=fh, timeout=15).json()["counts"]
    assert after_reg["pending"] == before["pending"] + 1

    requests.post(f"{BASE}/uhp/partners/{pid}/approve", headers=fh, timeout=15)
    after_appr = requests.get(f"{BASE}/uhp/partners/admin", headers=fh, timeout=15).json()["counts"]
    assert after_appr["pending"] == before["pending"]
    assert after_appr["active"] == before["active"] + 1

    requests.post(f"{BASE}/uhp/partners/{pid}/suspend", headers=fh, timeout=15)
    after_susp = requests.get(f"{BASE}/uhp/partners/admin", headers=fh, timeout=15).json()["counts"]
    assert after_susp["active"] == before["active"]
    assert after_susp["suspended"] == before["suspended"] + 1
