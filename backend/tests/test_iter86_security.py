"""Iteration 86 — security audit remediation.

SEC-001: /subscription/iap-sync must never trust the device payload — entitlements are re-fetched from
         RevenueCat server-side; a forged "active pro.archangel" claim grants no tier and no GA-T.
SEC-002: the Founder password is not stored in the repository; contacts-at-rest key rotated (MultiFernet,
         legacy tokens re-encrypted at startup); exported source ZIP carries no .env / memory files.
Run: FOUNDER_TEST_PASSWORD=<pw> pytest tests/test_iter86_security.py  (password never lives in the repo)
"""
import os
import re
import uuid
import zipfile
import pytest
import requests
from dotenv import dotenv_values

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FE_ENV = dotenv_values(os.path.join(ROOT, "frontend", ".env"))
BE_ENV = dotenv_values(os.path.join(ROOT, "backend", ".env"))
BASE = FE_ENV["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") + "/api"


def _fresh(tag):
    r = requests.post(f"{BASE}/auth/dev-bypass", json={"email": f"iter86-{tag}-{uuid.uuid4().hex[:6]}@example.com", "name": tag}, timeout=15)
    if r.status_code == 429:
        pytest.skip("dev-bypass rate limited — rerun")
    assert r.status_code == 200, r.text
    d = r.json()
    return {"Authorization": f"Bearer {d['session_token']}"}, d["user"]["user_id"]


# ---------- SEC-001 ----------
def test_forged_iap_sync_grants_no_tier_and_no_gat():
    h, uid = _fresh("forge")
    before = requests.get(f"{BASE}/auth/me", headers=h, timeout=15).json()["user"]
    for product in ("pro.archangel_monthly_v2", "pro.sentinel_annual_v2", "pro.guardian_monthly", "pro.addon_perplexity_ultra_monthly"):
        r = requests.post(f"{BASE}/subscription/iap-sync", headers=h, timeout=30,
                          json={"entitlement": "pro", "active": True, "product_identifier": product, "app_user_id": uid,
                                "store": "TEST_STORE", "expires_date": "2030-01-01T00:00:00Z", "period_type": "NORMAL",
                                "active_subscriptions": [{"product_identifier": product, "expires_date": "2030-01-01T00:00:00Z", "store": "TEST_STORE"}]})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] in ("noop", "downgraded"), body
        assert body["tier"] == "sovereign"
    after = requests.get(f"{BASE}/auth/me", headers=h, timeout=15).json()["user"]
    assert (after.get("tier") or "sovereign") == "sovereign"
    assert (after.get("gat_balance") or 0) == (before.get("gat_balance") or 0)
    addons = requests.get(f"{BASE}/store/addons/status", headers=h, timeout=15).json()
    assert not any(a.get("active") for a in (addons.get("addons") or addons or {}).values() if isinstance(a, dict))


def test_iap_sync_identity_and_whitelist_still_enforced():
    h, uid = _fresh("ident")
    r = requests.post(f"{BASE}/subscription/iap-sync", headers=h, timeout=15,
                      json={"entitlement": "pro", "active": True, "product_identifier": "pro.archangel_monthly_v2", "app_user_id": "someone-else", "store": "TEST_STORE"})
    assert r.status_code == 409
    r = requests.post(f"{BASE}/subscription/iap-sync", headers=h, timeout=15,
                      json={"entitlement": "pro", "active": True, "product_identifier": "hack.archangel", "app_user_id": uid, "store": "TEST_STORE"})
    assert r.status_code == 422


def test_revenuecat_public_keys_configured_for_server_side_verification():
    assert BE_ENV.get("REVENUECAT_PUBLIC_KEY_TEST", "").startswith("test_")
    assert BE_ENV.get("REVENUECAT_PUBLIC_KEY_IOS", "").startswith("appl_")
    assert BE_ENV.get("REVENUECAT_PUBLIC_KEY_ANDROID", "").startswith("goog_")


# ---------- SEC-002 ----------
def test_founder_password_not_in_repo_files():
    assert "FOUNDER_TEST_PASSWORD" not in BE_ENV
    for rel in ("memory/test_credentials.md", "memory/PRD.md", "test_result.md"):
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            txt = open(p, encoding="utf-8", errors="ignore").read()
            assert not re.search(r"FOUNDER_TEST_PASSWORD\s*=\s*\S+", txt), rel


def test_contacts_key_rotated_and_multifernet_in_place():
    assert BE_ENV.get("CONTACTS_ENC_KEY") and BE_ENV.get("CONTACTS_ENC_KEY") != BE_ENV.get("CONTACTS_ENC_KEY_PREV")
    src = open(os.path.join(ROOT, "backend", "routes", "family_contacts.py"), encoding="utf-8").read()
    assert "MultiFernet" in src and "rotate_contact_keys" in src


def test_export_zip_has_no_env_or_memory():
    p = os.path.join(ROOT, "export", "archangel-os-source.zip")
    if not os.path.exists(p):
        pytest.skip("no export zip")
    names = zipfile.ZipFile(p).namelist()
    assert not [n for n in names if n.endswith("/.env") or n == ".env" or n.startswith("memory/") or n.endswith("google-services.json")]
