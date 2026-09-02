"""Iter 56: GA-T subscription loyalty allocation tests.

Verifies:
- Price update guardian €9 / 15 GA-T
- Allocation logic across 6 mutation scenarios
- Ledger idempotency + hash-chain integrity
- Regression of earn/spend endpoints
"""
import os
import uuid
import asyncio
import pytest
import httpx
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

BASE = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/") + "/api"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


def _bypass(email: str) -> str:
    r = httpx.post(f"{BASE}/auth/dev-bypass", json={"email": email}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["session_token"]


@pytest.fixture(scope="module")
def db():
    return MongoClient(MONGO_URL)[DB_NAME]


@pytest.fixture(scope="module")
def loyalty_user(db):
    email = f"loyalty-qa-{uuid.uuid4().hex[:8]}@example.com"
    tok = _bypass(email)
    u = db.users.find_one({"email": email}, {"user_id": 1})
    assert u, "user not seeded by dev-bypass"
    yield {"email": email, "token": tok, "user_id": u["user_id"]}


# ---------------- 1. PRICE REGRESSION ----------------
class TestPrices:
    def test_subscription_prices(self):
        tok = _bypass("free-tier-test@example.com")
        r = httpx.get(f"{BASE}/subscription", headers={"Authorization": f"Bearer {tok}"}, timeout=30)
        assert r.status_code == 200
        j = r.json()
        g = j["tiers"]["guardian"]
        assert g["price_eur"] == 9, f"guardian price_eur != 9: {g['price_eur']}"
        assert g["price_gat"] == 15, f"guardian price_gat != 15: {g['price_gat']}"
        assert g["price_eur_year"] == 86, f"guardian price_eur_year != 86: {g['price_eur_year']}"
        assert any("GA-T credited every month" in f for f in g["features"]), f"Missing monthly-credit feature: {g['features']}"
        assert "gat_allocation" in j and "eligible" in j["gat_allocation"]
        assert j["gat_monthly_by_tier"] == {"guardian": 100.0, "sentinel": 300.0, "archangel": 1000.0}

    def test_wallet_spend_prices(self):
        tok = _bypass("free-tier-test@example.com")
        r = httpx.get(f"{BASE}/token/wallet", headers={"Authorization": f"Bearer {tok}"}, timeout=30)
        assert r.status_code == 200
        si = r.json()["spend_items"]
        assert si["tier_guardian_30d"]["price"] == 15
        assert si["tier_guardian_365d"]["price"] == 144


# ---------------- 2. ALLOCATION LOGIC ----------------
class TestAllocation:
    
    def test_full_allocation_flow(self, db, loyalty_user):
        uid = loyalty_user["user_id"]
        tok = loyalty_user["token"]
        H = {"Authorization": f"Bearer {tok}"}

        # cleanup any priors
        db.token_ledger.delete_many({"account": uid})
        db.token_accounts.delete_many({"user_id": uid})
        db.users.update_one({"user_id": uid}, {
            "$set": {"tier": "sovereign", "tier_paid_with": None, "tier_until": None},
            "$unset": {"gat_alloc_anchor": "", "gat_alloc_count": ""}
        })

        # (1) fresh sovereign
        w = httpx.get(f"{BASE}/token/wallet", headers=H, timeout=30).json()
        a = w["subscription_allocation"]
        assert a["eligible"] is False
        assert a["reason"] == "no_active_subscription"
        assert w["balance"] == 0

        # (2) fresh card-paid guardian
        now = datetime.now(timezone.utc)
        db.users.update_one({"user_id": uid}, {"$set": {
            "tier": "guardian", "tier_paid_with": "card",
            "tier_until": now + timedelta(days=30)
        }, "$unset": {"gat_alloc_anchor": "", "gat_alloc_count": ""}})
        w = httpx.get(f"{BASE}/token/wallet", headers=H, timeout=30).json()
        a = w["subscription_allocation"]
        assert a["eligible"] is True, a
        assert a["credited_now"] == 1
        assert a["months_collected"] == 1
        assert w["balance"] == 100
        assert a["next_amount"] == 110
        assert a["next_bonus_pct"] == 10
        # ledger entry
        entry = db.token_ledger.find_one({"kind": "subscription_allocation", "account": uid, "meta.period_index": 1})
        assert entry is not None, "No subscription_allocation ledger entry for period_index=1"

        # (3) idempotency
        w2 = httpx.get(f"{BASE}/token/wallet", headers=H, timeout=30).json()
        assert w2["balance"] == 100
        assert w2["subscription_allocation"]["credited_now"] == 0

        # (4) 65 days later
        db.users.update_one({"user_id": uid}, {"$set": {
            "gat_alloc_anchor": now - timedelta(days=65),
            "tier_until": now + timedelta(days=300)
        }})
        w = httpx.get(f"{BASE}/token/wallet", headers=H, timeout=30).json()
        a = w["subscription_allocation"]
        assert a["credited_now"] == 2, f"expected 2, got {a['credited_now']}"
        assert a["months_collected"] == 3
        assert w["balance"] == 330  # 100 + 110 + 120
        assert a["next_amount"] == 130
        assert a["next_bonus_pct"] == 30

        # (5) paid_with GA-T
        db.users.update_one({"user_id": uid}, {"$set": {"tier_paid_with": "GA-T"}})
        w = httpx.get(f"{BASE}/token/wallet", headers=H, timeout=30).json()
        a = w["subscription_allocation"]
        assert a["eligible"] is False
        assert a["reason"] == "paid_with_gat_or_trial"
        assert w["balance"] == 330

        # (6) trial
        db.users.update_one({"user_id": uid}, {"$set": {"tier_paid_with": "trial"}})
        a = httpx.get(f"{BASE}/token/wallet", headers=H, timeout=30).json()["subscription_allocation"]
        assert a["eligible"] is False

        # (7) expired
        db.users.update_one({"user_id": uid}, {"$set": {
            "tier_paid_with": "card", "tier_until": now - timedelta(days=1)
        }})
        a = httpx.get(f"{BASE}/token/wallet", headers=H, timeout=30).json()["subscription_allocation"]
        assert a["eligible"] is False
        assert a["reason"] == "no_active_subscription"

        # (8) chain intact
        r = httpx.get(f"{BASE}/token/ledger?verify=1&limit=5", headers=H, timeout=30).json()
        assert r["chain"]["intact"] is True

        # Subscription endpoint reflects same numbers when card-paid & active
        db.users.update_one({"user_id": uid}, {"$set": {
            "tier_paid_with": "card", "tier_until": now + timedelta(days=300)
        }})
        s = httpx.get(f"{BASE}/subscription", headers=H, timeout=30).json()
        assert s["gat_allocation"]["eligible"] is True
        assert s["gat_allocation"]["months_collected"] == 3


# ---------------- 3. REGRESSION EARN/SPEND ----------------
class TestRegression:
    
    def test_earn_document_scan(self, db):
        email = f"earnqa-{uuid.uuid4().hex[:6]}@example.com"
        tok = _bypass(email)
        H = {"Authorization": f"Bearer {tok}"}
        r = httpx.post(f"{BASE}/token/earn", headers=H, json={"activity": "document_scan"}, timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["tx"]["amount"] == 2.0
        assert j["balance"] >= 2.0

    
    def test_spend_guardian_tier(self, db):
        email = f"spendqa-{uuid.uuid4().hex[:6]}@example.com"
        tok = _bypass(email)
        H = {"Authorization": f"Bearer {tok}"}
        # Grant balance directly
        u = db.users.find_one({"email": email}, {"user_id": 1})
        db.token_accounts.update_one(
            {"user_id": u["user_id"]},
            {"$set": {"balance": 20.0, "earned_total": 20.0, "spent_total": 0.0,
                      "updated_at": datetime.now(timezone.utc)}}, upsert=True)
        r = httpx.post(f"{BASE}/token/spend", headers=H, json={"item": "tier_guardian_30d"}, timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["effect"]["tier"] == "guardian"
        assert j["balance"] == 5.0  # 20 - 15
        # subsequent wallet call: paid_with should be GA-T → not eligible
        w = httpx.get(f"{BASE}/token/wallet", headers=H, timeout=30).json()
        assert w["subscription_allocation"]["eligible"] is False
        assert w["subscription_allocation"]["reason"] == "paid_with_gat_or_trial"


# ---------------- 4. LEAVE LOYALTY-TEST USER IN CARD-PAID GUARDIAN STATE ----------------
class TestFixupLoyaltyTest:
    
    def test_reset_loyalty_test_user(self, db):
        u = db.users.find_one({"email": "loyalty-test@example.com"}, {"user_id": 1})
        if not u:
            # Ensure via dev-bypass
            _bypass("loyalty-test@example.com")
            u = db.users.find_one({"email": "loyalty-test@example.com"}, {"user_id": 1})
        assert u is not None
        now = datetime.now(timezone.utc)
        db.users.update_one({"user_id": u["user_id"]}, {"$set": {
            "tier": "guardian", "tier_paid_with": "card",
            "tier_until": now + timedelta(days=300),
        }})
        # trigger an allocation
        tok = _bypass("loyalty-test@example.com")
        w = httpx.get(f"{BASE}/token/wallet", headers={"Authorization": f"Bearer {tok}"}, timeout=30).json()
        assert w["subscription_allocation"]["eligible"] is True
        assert w["balance"] >= 100
