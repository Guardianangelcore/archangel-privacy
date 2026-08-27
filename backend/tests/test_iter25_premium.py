"""Iteration 25 — Premium features (Stripe card payments + new GA-T prices + founder).

Coverage:
- /api/subscription tier prices (guardian 50 / sentinel 250 / archangel 800 monthly;
  480 / 2400 / 7680 annual) + billing_note mentions Stripe TEST.
- /api/billing/checkout (real Stripe checkout URL + amount fixed server-side; 400
  on invalid tier/billing).
- /api/billing/status/{session_id} → open/unpaid initially; 404 for foreign/unknown.
- GA-T insufficient_balance mentions 50 GA-T (not 290).
- Founder entitlement (first user = inner_circle/archangel).
- One-time trial (POST /api/subscription/trial) + gated endpoints unlock on Sentinel.
- Fresh user still hits 402 on gated endpoints.
"""
import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "guardian_health")

FOUNDER_TOKEN = "smoketok-fresh-2026"            # smoketest-user-1 = first user = founder (janitor-granted)
SMOKE_TOKEN = "smoketok-fresh-handover"          # user_smoke2026 = general smoke user (also premium in this env)


@pytest.fixture(scope="module")
def founder_h():
    return {"Authorization": f"Bearer {FOUNDER_TOKEN}"}


@pytest.fixture(scope="module")
def fresh_user():
    """Create a brand-new sovereign user + session directly in Mongo."""
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    uid = f"user_iter25_{uuid.uuid4().hex[:8]}"
    tok = f"iter25tok-{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)
    db.users.insert_one({
        "user_id": uid, "email": f"{uid}@test.sk", "did": f"did:guardian:{uid}",
        "name": "TEST_iter25 Fresh", "language": "sk", "angel_mode": False,
        "created_at": now, "tos_accepted": "v2026-06.1", "tos_accepted_at": now,
    })
    db.user_sessions.insert_one({
        "session_token": tok, "user_id": uid,
        "created_at": now, "expires_at": now + timedelta(days=7),
    })
    yield {"user_id": uid, "token": tok, "headers": {"Authorization": f"Bearer {tok}"}}
    # Teardown — remove test data
    db.users.delete_one({"user_id": uid})
    db.user_sessions.delete_one({"session_token": tok})
    db.payment_transactions.delete_many({"user_id": uid})
    db.token_accounts.delete_one({"user_id": uid})
    client.close()


# ---------- 1. Tier prices ----------
class TestSubscriptionPrices:
    def test_new_gat_prices_and_annual(self, founder_h):
        r = requests.get(f"{API}/subscription", headers=founder_h, timeout=10)
        assert r.status_code == 200, r.text
        d = r.json()
        tiers = d["tiers"]
        # Monthly GA-T
        assert tiers["guardian"]["price_gat"] == 50, tiers["guardian"]
        assert tiers["sentinel"]["price_gat"] == 250, tiers["sentinel"]
        assert tiers["archangel"]["price_gat"] == 800, tiers["archangel"]
        # Annual GA-T (20% off × 12)
        assert tiers["guardian"]["price_gat_year"] == 480
        assert tiers["sentinel"]["price_gat_year"] == 2400
        assert tiers["archangel"]["price_gat_year"] == 7680

    def test_billing_note_mentions_stripe_test(self, founder_h):
        r = requests.get(f"{API}/subscription", headers=founder_h, timeout=10)
        note = r.json().get("billing_note", "")
        assert "Stripe" in note and "TEST" in note, note


# ---------- 2. Founder entitlement ----------
class TestFounderEntitlement:
    def test_founder_is_archangel_inner_circle(self, founder_h):
        r = requests.get(f"{API}/subscription", headers=founder_h, timeout=10)
        d = r.json()
        assert d["tier"] == "archangel", d
        assert d["inner_circle"] is True, d


# ---------- 3. /api/billing/checkout ----------
class TestBillingCheckout:
    def test_checkout_sentinel_monthly_returns_stripe_url(self, fresh_user):
        payload = {
            "tier": "sentinel", "billing": "monthly",
            "origin_url": "https://biometric-onboard-3.preview.emergentagent.com",
        }
        r = requests.post(f"{API}/billing/checkout", headers=fresh_user["headers"],
                          json=payload, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "checkout.stripe.com" in d["checkout_url"], d["checkout_url"]
        assert d["session_id"]
        assert d["amount_eur"] == 149.0, d      # server-fixed sentinel/monthly
        # stash for next tests
        pytest.sentinel_session_id = d["session_id"]

    def test_checkout_amount_is_server_fixed(self, fresh_user):
        # Client cannot inject an amount — request body has no such field
        r = requests.post(f"{API}/billing/checkout", headers=fresh_user["headers"],
                          json={"tier": "guardian", "billing": "annual",
                                "origin_url": "https://biometric-onboard-3.preview.emergentagent.com",
                                "amount": 0.01},
                          timeout=20)
        assert r.status_code == 200, r.text
        assert r.json()["amount_eur"] == round(29 * 12 * 0.8, 0), r.json()  # 278

    def test_checkout_invalid_tier(self, fresh_user):
        r = requests.post(f"{API}/billing/checkout", headers=fresh_user["headers"],
                          json={"tier": "diamond", "billing": "monthly",
                                "origin_url": "https://x"}, timeout=10)
        assert r.status_code == 400, r.text

    def test_checkout_invalid_billing(self, fresh_user):
        r = requests.post(f"{API}/billing/checkout", headers=fresh_user["headers"],
                          json={"tier": "sentinel", "billing": "weekly",
                                "origin_url": "https://x"}, timeout=10)
        assert r.status_code == 400, r.text


# ---------- 4. /api/billing/status ----------
class TestBillingStatus:
    def test_status_unpaid_before_payment(self, fresh_user):
        sid = getattr(pytest, "sentinel_session_id", None)
        if not sid:
            pytest.skip("no session_id from previous test")
        r = requests.get(f"{API}/billing/status/{sid}", headers=fresh_user["headers"], timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["activated"] is False
        assert d["payment_status"] in ("unpaid", "no_payment_required", "initiated"), d

    def test_status_404_for_unknown_session(self, fresh_user):
        r = requests.get(f"{API}/billing/status/cs_fake_{uuid.uuid4().hex}",
                         headers=fresh_user["headers"], timeout=10)
        assert r.status_code == 404, r.text

    def test_status_404_for_foreign_session(self, fresh_user, founder_h):
        """A different user cannot poll fresh_user's session."""
        sid = getattr(pytest, "sentinel_session_id", None)
        if not sid:
            pytest.skip("no session_id from previous test")
        r = requests.get(f"{API}/billing/status/{sid}", headers=founder_h, timeout=10)
        assert r.status_code == 404, r.text


# ---------- 5. GA-T upgrade insufficient balance ----------
class TestGatUpgradeInsufficient:
    def test_guardian_gat_says_50(self, fresh_user):
        r = requests.post(f"{API}/subscription/upgrade", headers=fresh_user["headers"],
                          json={"tier": "guardian", "method": "gat", "billing": "monthly"},
                          timeout=10)
        assert r.status_code == 402, r.text
        msg = r.json().get("detail", "")
        assert "50" in msg, msg
        assert "290" not in msg, msg  # old price must be gone


# ---------- 6. Trial + gated endpoints ----------
class TestTrialUnlocksPremium:
    """After activating trial on the fresh user, gated endpoints stop returning 402."""

    def test_fresh_user_hits_402_on_gated_endpoints(self, fresh_user):
        # Longevity + Satellite + Tactical Medic — all Sentinel-gated.
        r1 = requests.get(f"{API}/longevity/bioage", headers=fresh_user["headers"], timeout=10)
        assert r1.status_code == 402, f"longevity: {r1.status_code} {r1.text}"

    def test_activate_trial(self, fresh_user):
        r = requests.post(f"{API}/subscription/trial", headers=fresh_user["headers"], timeout=10)
        assert r.status_code == 200, r.text
        assert r.json()["tier"] == "sentinel"
        assert r.json()["trial"] is True

    def test_gated_endpoints_now_work(self, fresh_user):
        r1 = requests.get(f"{API}/longevity/bioage", headers=fresh_user["headers"], timeout=15)
        # 200 = full success; 409 profile_missing = also proof premium is unlocked (next gate, not 402)
        assert r1.status_code in (200, 409), f"longevity after trial: {r1.status_code} {r1.text[:200]}"
        assert r1.status_code != 402, "still 402 after trial — premium NOT unlocked"

    def test_trial_is_one_time(self, fresh_user):
        r = requests.post(f"{API}/subscription/trial", headers=fresh_user["headers"], timeout=10)
        # trial_used=True → 409; or already_premium=Sentinel → 409
        assert r.status_code == 409, r.text
