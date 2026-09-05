"""Iter 60 — RevenueCat IAP sync backend tests.

Tests POST /api/subscription/iap-sync end-to-end via dev-bypass users.
"""
import os
import time
import pytest
pytestmark = pytest.mark.skip(reason="SEC-001 (Iter 86): /subscription/iap-sync now verifies entitlements server-side with RevenueCat — forged payloads grant nothing; see tests/test_iter86_security.py")
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _bypass(email: str, name: str = "IAP Tester") -> dict:
    r = requests.post(f"{API}/auth/dev-bypass", json={"email": email, "name": name}, timeout=30)
    assert r.status_code == 200, f"dev-bypass failed: {r.status_code} {r.text}"
    return r.json()


def _hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _fresh_user():
    ts = int(time.time() * 1000)
    email = f"iap-t-{ts}@example.com"
    data = _bypass(email)
    return data["session_token"], data["user"]["user_id"], email


def _future_iso(days: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat().replace("+00:00", "Z")


def _past_iso(days: int = 5) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")


def _iap_payload(user_id: str, active: bool = True, entitlement: str = "pro",
                 period_type: str = "NORMAL", expires_date: str | None = None,
                 app_user_id: str | None = None):
    return {
        "entitlement": entitlement,
        "active": active,
        "product_identifier": "pro.monthly",
        "expires_date": expires_date if expires_date is not None else _future_iso(30),
        "store": "TEST_STORE",
        "period_type": period_type,
        "app_user_id": app_user_id if app_user_id is not None else user_id,
        "will_renew": True,
    }


# ------------------- CASES 1 & 2: activate then idempotent replay -------------------
class TestActivationAndIdempotency:
    def test_activate_guardian_and_credit_100_gat(self):
        tok, uid, _ = _fresh_user()
        r = requests.post(f"{API}/subscription/iap-sync", json=_iap_payload(uid), headers=_hdr(tok), timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["status"] == "synced"
        assert j["tier"] == "guardian"
        alloc = j.get("gat_allocation") or {}
        assert alloc.get("eligible") is True
        assert alloc.get("credited_now") == 1

        sub = requests.get(f"{API}/subscription", headers=_hdr(tok), timeout=30).json()
        assert sub["tier"] == "guardian"
        assert (sub.get("paid_with") or "").lower() == "iap"

        w = requests.get(f"{API}/token/wallet", headers=_hdr(tok), timeout=30).json()
        assert float(w.get("balance", 0)) == 100.0

    def test_replay_same_payload_no_double_credit(self):
        tok, uid, _ = _fresh_user()
        payload = _iap_payload(uid)
        r1 = requests.post(f"{API}/subscription/iap-sync", json=payload, headers=_hdr(tok), timeout=30)
        assert r1.status_code == 200
        assert r1.json()["status"] == "synced"

        r2 = requests.post(f"{API}/subscription/iap-sync", json=payload, headers=_hdr(tok), timeout=30)
        assert r2.status_code == 200, r2.text
        j2 = r2.json()
        assert j2["status"] == "unchanged"

        w = requests.get(f"{API}/token/wallet", headers=_hdr(tok), timeout=30).json()
        assert float(w.get("balance", 0)) == 100.0


# ------------------- CASES 3-6: identity / validation errors -------------------
class TestValidationErrors:
    def test_mismatched_app_user_id_returns_409(self):
        tok, uid, _ = _fresh_user()
        payload = _iap_payload(uid, app_user_id="user_someotheruser123")
        r = requests.post(f"{API}/subscription/iap-sync", json=payload, headers=_hdr(tok), timeout=30)
        assert r.status_code == 409, r.text

    def test_anonymous_rc_id_returns_409(self):
        tok, uid, _ = _fresh_user()
        payload = _iap_payload(uid, app_user_id="$RCAnonymousID:abcdef123456")
        r = requests.post(f"{API}/subscription/iap-sync", json=payload, headers=_hdr(tok), timeout=30)
        assert r.status_code == 409, r.text

    def test_expired_expires_date_returns_422(self):
        tok, uid, _ = _fresh_user()
        payload = _iap_payload(uid, expires_date=_past_iso(5))
        r = requests.post(f"{API}/subscription/iap-sync", json=payload, headers=_hdr(tok), timeout=30)
        assert r.status_code == 422, r.text

    def test_unknown_entitlement_returns_400(self):
        tok, uid, _ = _fresh_user()
        payload = _iap_payload(uid, entitlement="gold")
        r = requests.post(f"{API}/subscription/iap-sync", json=payload, headers=_hdr(tok), timeout=30)
        assert r.status_code == 400, r.text


# ------------------- CASES 7 & 8: deactivation / lapse -------------------
class TestDeactivation:
    def test_active_false_after_iap_activation_downgrades(self):
        tok, uid, _ = _fresh_user()
        # first activate
        r1 = requests.post(f"{API}/subscription/iap-sync", json=_iap_payload(uid), headers=_hdr(tok), timeout=30)
        assert r1.status_code == 200 and r1.json()["status"] == "synced"
        # now deactivate
        r2 = requests.post(f"{API}/subscription/iap-sync",
                           json=_iap_payload(uid, active=False), headers=_hdr(tok), timeout=30)
        assert r2.status_code == 200, r2.text
        j = r2.json()
        assert j["status"] == "downgraded"
        assert j["tier"] == "sovereign"

    def test_active_false_for_fresh_free_user_noop(self):
        tok, uid, _ = _fresh_user()
        r = requests.post(f"{API}/subscription/iap-sync",
                          json=_iap_payload(uid, active=False), headers=_hdr(tok), timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["status"] == "noop"


# ------------------- CASE 9: trial period ineligible for GA-T -------------------
class TestTrialPeriod:
    def test_trial_active_grants_guardian_no_gat(self):
        tok, uid, _ = _fresh_user()
        payload = _iap_payload(uid, period_type="TRIAL")
        r = requests.post(f"{API}/subscription/iap-sync", json=payload, headers=_hdr(tok), timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["tier"] == "guardian"
        alloc = j.get("gat_allocation") or {}
        assert alloc.get("eligible") is False
        assert alloc.get("reason") == "trial_or_intro_period"


# ------------------- CASE 10: higher tier user kept -------------------
class TestKeepHigherTier:
    def test_founder_archangel_kept_on_iap_activate(self):
        # founder bypass — inner_circle=True, tier archangel
        r = requests.post(f"{API}/auth/dev-bypass",
                          json={"email": "guardianangel.core@proton.me", "name": "Founder"},
                          timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        tok = d["session_token"]
        uid = d["user"]["user_id"]

        sub_before = requests.get(f"{API}/subscription", headers=_hdr(tok), timeout=30).json()
        assert sub_before["tier"] == "archangel"

        r2 = requests.post(f"{API}/subscription/iap-sync", json=_iap_payload(uid),
                           headers=_hdr(tok), timeout=30)
        assert r2.status_code == 200, r2.text
        j = r2.json()
        assert j["status"] == "kept_higher_tier"
        assert j["tier"] == "archangel"


# ------------------- require_tier gate: guardian must unlock Jarvis -------------------
class TestGuardianGateUnlocked:
    def test_agent_briefing_not_402_after_iap_activation(self):
        tok, uid, _ = _fresh_user()
        r0 = requests.post(f"{API}/subscription/iap-sync", json=_iap_payload(uid),
                           headers=_hdr(tok), timeout=30)
        assert r0.status_code == 200 and r0.json()["tier"] == "guardian"

        # briefing: LLM may be exhausted (503) — that's acceptable; 402 guardian_required is NOT
        rb = requests.get(f"{API}/agent/briefing", headers=_hdr(tok), timeout=60)
        assert rb.status_code in (200, 503), f"unexpected status {rb.status_code} body={rb.text[:200]}"
        assert rb.status_code != 402

        rc = requests.post(f"{API}/agent/chat", json={"message": "hello"}, headers=_hdr(tok), timeout=60)
        assert rc.status_code in (200, 503), f"unexpected status {rc.status_code} body={rc.text[:200]}"
        assert rc.status_code != 402
