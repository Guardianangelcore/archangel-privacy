import pytest
"""Iteration 81 — founder e-mail rename, GA-T on-chain bridge (queued mode), STT plumbing untouched server-side."""
import os, uuid, requests
from datetime import datetime, timezone, timedelta

BASE = os.environ.get("EXPO_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/") + "/api"
FOUNDER = "guardianangel.core@proton.me"


def _bypass(email, name="T"):
    r = requests.post(f"{BASE}/auth/dev-bypass", json={"email": email, "name": name}, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json(); return {"token": d["session_token"], "user_id": d["user"]["user_id"], "user": d["user"]}


def _h(u): return {"Authorization": f"Bearer {u['token']}"}


def _founder_pw() -> str:
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    pw = os.environ.get("FOUNDER_TEST_PASSWORD", "").strip()   # SEC-002: never stored in the repo — export it before running
    if not pw:
        pytest.skip("FOUNDER_TEST_PASSWORD env not set (founder password is not stored in the repository)")
    return pw


def _founder():
    """Founder signs in with password (dev-bypass refuses privileged accounts since Iter 82)."""
    r = requests.post(f"{BASE}/auth/login", json={"email": FOUNDER, "password": _founder_pw()}, timeout=15)
    assert r.status_code == 200, f"founder login failed: {r.status_code} {r.text}"
    d = r.json(); return {"token": d["session_token"], "user_id": d["user"]["user_id"], "email": FOUNDER, "user": d["user"], "name": "Guardian Angel"}


def test_founder_email_renamed_same_account():
    f = _founder()
    assert f["user"]["email"] == FOUNDER and f["user"]["tier"] == "archangel" and f["user"].get("inner_circle") is True
    old = requests.post(f"{BASE}/auth/dev-bypass", json={"email": "guardian.angel.core@proton.me", "name": "x"}, timeout=15).json()["user"]
    assert old["user_id"] != f["user_id"] and old.get("tier", "sovereign") != "archangel"   # old address is no longer the founder


def test_chain_status_and_wallet_link():
    u = _bypass(f"iter81-{uuid.uuid4().hex[:8]}@example.com")
    st = requests.get(f"{BASE}/chain/status", headers=_h(u), timeout=15).json()
    assert st["token"]["symbol"] == "GA-T" and st["token"]["cap"] == 1_000_000_000 and st["token"]["genesis_founder_pct"] == 25
    assert st["founder_wallet"] == "0x0E6693153961c01CEa3e73e4e9596aCF35315567" and st["chain_id"] == 8453
    assert st["configured"] is False and st["mode"] == "queued_until_deploy"
    assert requests.post(f"{BASE}/chain/wallet", headers=_h(u), json={"address": "0xdead"}, timeout=15).status_code == 400
    r = requests.post(f"{BASE}/chain/wallet", headers=_h(u), json={"address": "0x0e6693153961c01cea3e73e4e9596acf35315567"}, timeout=15)
    assert r.status_code == 200 and r.json()["wallet_address"] == "0x0E6693153961c01CEa3e73e4e9596aCF35315567"   # checksummed


@pytest.mark.skip(reason="SEC-001 (Iter 86): /subscription/iap-sync now verifies entitlements server-side with RevenueCat — forged payloads grant nothing; see tests/test_iter86_security.py")
def test_verified_subscription_queues_onchain_mint_once():
    u = _bypass(f"iter81-mint-{uuid.uuid4().hex[:8]}@example.com")
    requests.post(f"{BASE}/chain/wallet", headers=_h(u), json={"address": "0x0E6693153961c01CEa3e73e4e9596aCF35315567"}, timeout=15)
    exp = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat().replace("+00:00", "Z")
    body = {"entitlement": "pro", "active": True, "product_identifier": "pro.guardian_monthly", "expires_date": exp, "store": "TEST_STORE",
            "app_user_id": u["user_id"], "active_subscriptions": [{"product_identifier": "pro.guardian_monthly", "expires_date": exp}]}
    r = requests.post(f"{BASE}/subscription/iap-sync", headers=_h(u), json=body, timeout=15)
    assert r.status_code == 200 and r.json()["tier"] == "guardian"
    requests.post(f"{BASE}/subscription/iap-sync", headers=_h(u), json=body, timeout=15)   # idempotent re-sync
    m = requests.get(f"{BASE}/chain/mints", headers=_h(u), timeout=15).json()["mints"]
    assert len(m) == 1 and m[0]["status"] == "queued" and m[0]["amount"] == 100.0 and m[0]["to"].startswith("0x0E66")
    # no wallet → no mint queued
    v = _bypass(f"iter81-nowallet-{uuid.uuid4().hex[:8]}@example.com")
    body["app_user_id"] = v["user_id"]
    requests.post(f"{BASE}/subscription/iap-sync", headers=_h(v), json=body, timeout=15)
    assert requests.get(f"{BASE}/chain/mints", headers=_h(v), timeout=15).json()["mints"] == []
