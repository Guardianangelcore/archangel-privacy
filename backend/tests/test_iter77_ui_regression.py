# Copyright © 2026. Backend regression for iter77 model picker + P0 security hardening.
# Focused, minimal — the full suite is /app/backend/tests/test_iter77_models_security.py.
import os
import pytest
import requests

BASE = os.environ.get("EXPO_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def founder_token():
    r = requests.post(f"{BASE}/api/auth/dev-bypass",
                      json={"email": "guardian.angel.core@proton.me", "name": "Guardian Angel"},
                      timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["session_token"]


@pytest.fixture(scope="module")
def free_token():
    r = requests.post(f"{BASE}/api/auth/dev-bypass",
                      json={"email": "iter77-ui-free@example.com", "name": "Free UI"},
                      timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["session_token"]


# ── SECURITY: password_hash never returned ─────────────────────────────────────
def test_login_password_and_me_no_password_hash():
    r = requests.post(f"{BASE}/api/auth/login",
                      json={"email": "demo.judge@guardian.app", "password": "guardian-demo-2026"},
                      timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "password_hash" not in body.get("user", {})
    tok = body["session_token"]
    r2 = requests.get(f"{BASE}/api/auth/me", headers={"Authorization": f"Bearer {tok}"}, timeout=10)
    assert r2.status_code == 200
    assert "password_hash" not in r2.json().get("user", {})


# ── SECURITY: features endpoint refuses EUR ────────────────────────────────────
def test_features_buy_eur_rejected(free_token):
    # Use a fresh user who does NOT yet own bunker, else already_owned short-circuit
    r = requests.post(f"{BASE}/api/features/buy",
                      json={"feature": "bunker", "currency": "eur"},
                      headers={"Authorization": f"Bearer {free_token}"},
                      timeout=10)
    assert r.status_code == 400
    assert "gat" in r.json().get("detail", "").lower()


# ── SECURITY: dev-bypass works from preview host ───────────────────────────────
def test_dev_bypass_from_preview_host(founder_token):
    assert founder_token.startswith("gs-")


# ── MODELS: founder can see all 4 and none locked ──────────────────────────────
def test_ai_models_founder(founder_token):
    r = requests.get(f"{BASE}/api/ai/models", headers={"Authorization": f"Bearer {founder_token}"}, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["default"] == "gpt-5.4"
    assert d["tier"] == "archangel"
    ids = [m["id"] for m in d["models"]]
    assert ids == ["gpt-5.4-mini", "gpt-5.4", "gpt-5.6-luna", "gpt-5.6-terra"]
    assert all(m["locked"] is False for m in d["models"])


# ── MODELS: free-tier locked Luna & Terra, select denied 402 ───────────────────
def test_ai_models_free_gated(free_token):
    r = requests.get(f"{BASE}/api/ai/models", headers={"Authorization": f"Bearer {free_token}"}, timeout=10)
    assert r.status_code == 200
    d = r.json()
    lock = {m["id"]: m["locked"] for m in d["models"]}
    assert lock["gpt-5.4-mini"] is False and lock["gpt-5.4"] is False
    assert lock["gpt-5.6-luna"] is True and lock["gpt-5.6-terra"] is True
    r2 = requests.put(f"{BASE}/api/ai/models/select",
                      json={"model": "gpt-5.6-luna"},
                      headers={"Authorization": f"Bearer {free_token}"}, timeout=10)
    assert r2.status_code == 402


# ── MODELS: select+persist for founder (Luna → verify → restore default) ───────
def test_ai_models_select_persist(founder_token):
    r = requests.put(f"{BASE}/api/ai/models/select",
                     json={"model": "gpt-5.6-luna"},
                     headers={"Authorization": f"Bearer {founder_token}"}, timeout=10)
    assert r.status_code == 200 and r.json()["selected"] == "gpt-5.6-luna"
    r2 = requests.get(f"{BASE}/api/ai/models", headers={"Authorization": f"Bearer {founder_token}"}, timeout=10)
    assert r2.json()["selected"] == "gpt-5.6-luna"
    # restore default
    r3 = requests.put(f"{BASE}/api/ai/models/select",
                      json={"model": "gpt-5.4"},
                      headers={"Authorization": f"Bearer {founder_token}"}, timeout=10)
    assert r3.status_code == 200


# ── STORE: add-on requires GA-T; free user gets 402 insufficient_balance ───────
def test_addon_buy_ga_t_only(free_token):
    r = requests.post(f"{BASE}/api/store/addon/buy",
                      json={"addon_id": "ghost_mode"},
                      headers={"Authorization": f"Bearer {free_token}"}, timeout=10)
    assert r.status_code == 402
    assert "insufficient_balance" in r.json().get("detail", "")
