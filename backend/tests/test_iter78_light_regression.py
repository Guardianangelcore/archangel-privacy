"""Iter 78 — light backend regression for Community Help + self-claim block."""
import os, uuid, requests

BASE = os.environ.get("EXPO_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/") + "/api"


def _bypass(email, name="RegTest"):
    r = requests.post(f"{BASE}/auth/dev-bypass", json={"email": email, "name": name}, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    return {"token": d["session_token"], "user_id": d["user"]["user_id"], "email": email}


def _fresh(tag):
    return _bypass(f"reg78-{tag}-{uuid.uuid4().hex[:8]}@example.com", f"Reg78 {tag}")


def _h(u):
    return {"Authorization": f"Bearer {u['token']}"}


# --- Self-claim block: /token/earn must reject proof_of_help ---
def test_token_earn_proof_of_help_blocked():
    u = _fresh("self1")
    r = requests.post(f"{BASE}/token/earn", headers=_h(u), json={"activity": "proof_of_help"}, timeout=15)
    assert r.status_code == 403, r.text
    assert "verified_only" in r.text.lower()


# --- Free earn still works for a fresh user: proof_of_health first-time → 200 ---
def test_token_earn_proof_of_health_first_time_200():
    u = _fresh("phealth")
    r = requests.post(f"{BASE}/token/earn", headers=_h(u), json={"activity": "proof_of_health"}, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    # Basic sanity: response should indicate a positive credit
    assert isinstance(body, dict)


# --- Help list scope=open shape ---
def test_help_list_open_shape():
    u = _fresh("open")
    r = requests.get(f"{BASE}/help/requests?scope=open", headers=_h(u), timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "requests" in d
    assert d.get("reward") == 10
    assert "limits" in d and "daily_max" in d["limits"]
    assert "community_fund" in d
    assert "categories" in d and isinstance(d["categories"], list) and len(d["categories"]) >= 5
