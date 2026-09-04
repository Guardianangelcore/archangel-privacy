"""Light backend regression for iter 81 — chain status, wallet validation, founder rename."""
import os
import requests
import pytest

BASE_URL = os.environ.get("EXPO_BACKEND_URL", os.environ.get("EXPO_PUBLIC_BACKEND_URL", "")).rstrip("/") or "https://physio-lang-fix.preview.emergentagent.com"
NEW_FOUNDER = "guardianangel.core@proton.me"
OLD_FOUNDER = "guardian.angel.core@proton.me"


def _dev_bypass(email: str, name: str = "Test User") -> str:
    r = requests.post(f"{BASE_URL}/api/auth/dev-bypass", json={"email": email, "name": name}, timeout=15)
    assert r.status_code == 200, f"dev-bypass failed: {r.status_code} {r.text}"
    return r.json()["session_token"]


@pytest.fixture(scope="module")
def founder_headers():
    return {"Authorization": f"Bearer {_dev_bypass(NEW_FOUNDER, 'Guardian Angel')}"}


# --- founder e-mail rename ---
def test_founder_me_new_email(founder_headers):
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=founder_headers, timeout=15)
    assert r.status_code == 200
    me = r.json().get("user") or r.json()
    assert me.get("email") == NEW_FOUNDER, f"unexpected email: {me.get('email')}"
    assert me.get("tier") == "archangel", f"tier not archangel: {me.get('tier')}"


def test_old_email_is_not_founder():
    token = _dev_bypass(OLD_FOUNDER, "Legacy")
    r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=15)
    assert r.status_code == 200
    me = r.json().get("user") or r.json()
    assert me.get("email") == OLD_FOUNDER
    assert me.get("tier") == "sovereign", f"old email should be sovereign, got {me.get('tier')}"
    assert not me.get("inner_circle"), "old email should NOT be inner_circle"


# --- /chain/status ---
def test_chain_status(founder_headers):
    r = requests.get(f"{BASE_URL}/api/chain/status", headers=founder_headers, timeout=15)
    assert r.status_code == 200
    cs = r.json()
    assert cs.get("configured") is False
    assert cs.get("mode") == "queued_until_deploy"
    assert cs.get("founder_wallet") == "0x0E6693153961c01CEa3e73e4e9596aCF35315567"
    assert cs.get("chain_id") == 8453
    assert cs["token"]["symbol"] == "GA-T"
    assert cs["token"]["cap"] == 1_000_000_000
    assert cs["token"]["genesis_founder_pct"] == 25


# --- /chain/wallet validation ---
def test_link_invalid_wallet(founder_headers):
    r = requests.post(f"{BASE_URL}/api/chain/wallet", headers=founder_headers, json={"address": "0xdead"}, timeout=15)
    assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text}"


def test_link_valid_wallet_and_unlink():
    # Use a fresh user to not pollute founder record
    token = _dev_bypass(f"iter81-wallet-{os.urandom(3).hex()}@example.com")
    h = {"Authorization": f"Bearer {token}"}
    addr = "0x0e6693153961c01cea3e73e4e9596acf35315567"
    r = requests.post(f"{BASE_URL}/api/chain/wallet", headers=h, json={"address": addr}, timeout=15)
    assert r.status_code == 200, f"link failed: {r.status_code} {r.text}"
    js = r.json()
    # Checksummed
    assert js["wallet_address"] == "0x0E6693153961c01CEa3e73e4e9596aCF35315567"
    # /me now reflects wallet via chain/status
    r = requests.get(f"{BASE_URL}/api/chain/status", headers=h, timeout=15)
    assert r.json().get("wallet_address") == "0x0E6693153961c01CEa3e73e4e9596aCF35315567"
    # unlink
    r = requests.delete(f"{BASE_URL}/api/chain/wallet", headers=h, timeout=15)
    assert r.status_code == 200
    r = requests.get(f"{BASE_URL}/api/chain/status", headers=h, timeout=15)
    assert r.json().get("wallet_address") in (None, "")
