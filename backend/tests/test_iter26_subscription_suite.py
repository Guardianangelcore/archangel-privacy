"""ITERATION 26 — Subscription Suite Expansion
Backend tests:
  1. billing/checkout for family_sentinel (monthly=249, annual=2390) + invalid tier→400
  2. subscription/cancel — active→sovereign, repeat→409, inner_circle→400
  3. billing/gift — founder-only 200, non-founder 403, unknown email 404, /billing/gifts founder-only
  4. Receipt PDF creation flow (idempotent guarantee — cannot fully E2E a Stripe pay in headless,
     so we validate the code path via find_one_and_update simulation on a paid tx and check
     db.documents + db.calendar_events entries appear).
  5. Family pack activation multi-member (via simulated paid tx with linked db.guardians).

Uses BASE_URL from EXPO_PUBLIC_BACKEND_URL (public ingress). Also uses direct Mongo access
for seeding test users/guardians and simulating paid Stripe transactions (bypassing Stripe API).
"""
import os
import time
import uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/") or "https://biometric-onboard-3.preview.emergentagent.com"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "guardian_health")

FOUNDER_TOKEN = "smoketok-fresh-2026"          # smoketest-user-1 (inner_circle/founder)
SMOKE_TOKEN = "smoketok-fresh-handover"        # user_smoke2026 (sovereign — used for cancel/gift target)

client = MongoClient(MONGO_URL)
db = client[DB_NAME]


def _hdr(token: str):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------- helpers ----------
def _reset_smoke_to_sovereign():
    db.users.update_one({"user_id": "user_smoke2026"}, {"$set": {
        "tier": "sovereign", "tier_until": None,
        "tier_paid_with": None, "tier_billing": None,
        "family_pack_owner": False,
    }})


def _make_user(prefix: str, email: str | None = None) -> tuple[str, str]:
    uid = f"user_{prefix}_{uuid.uuid4().hex[:6]}"
    tok = f"tok_{prefix}_{uuid.uuid4().hex[:10]}"
    email = email or f"TEST_{prefix}_{uuid.uuid4().hex[:6]}@example.com"
    now = datetime.now(timezone.utc)
    db.users.insert_one({
        "user_id": uid, "email": email, "did": f"did:guardian:{uid}",
        "name": f"Test {prefix}", "language": "sk", "angel_mode": False,
        "tier": "sovereign", "created_at": now,
    })
    db.user_sessions.insert_one({
        "session_token": tok, "user_id": uid,
        "created_at": now, "expires_at": now + timedelta(days=1),
    })
    return uid, tok, email


@pytest.fixture(scope="module", autouse=True)
def _reset():
    _reset_smoke_to_sovereign()
    yield
    _reset_smoke_to_sovereign()


# ============================================================
# 1) BILLING CHECKOUT — family_sentinel
# ============================================================
class TestFamilyCheckout:
    def test_family_monthly_returns_249_and_stripe_url(self):
        r = requests.post(f"{BASE_URL}/api/billing/checkout",
                          headers=_hdr(SMOKE_TOKEN),
                          json={"tier": "family_sentinel", "billing": "monthly",
                                "origin_url": "https://example.com"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["amount_eur"] == 249.0
        assert data["tier"] == "family_sentinel"
        assert "stripe.com" in data["checkout_url"]
        assert data["session_id"].startswith("cs_")

    def test_family_annual_returns_2390(self):
        r = requests.post(f"{BASE_URL}/api/billing/checkout",
                          headers=_hdr(SMOKE_TOKEN),
                          json={"tier": "family_sentinel", "billing": "annual",
                                "origin_url": "https://example.com"})
        assert r.status_code == 200, r.text
        assert r.json()["amount_eur"] == 2390.0

    def test_invalid_tier_400(self):
        r = requests.post(f"{BASE_URL}/api/billing/checkout",
                          headers=_hdr(SMOKE_TOKEN),
                          json={"tier": "bogus", "billing": "monthly",
                                "origin_url": "https://example.com"})
        assert r.status_code == 400

    def test_invalid_billing_400(self):
        r = requests.post(f"{BASE_URL}/api/billing/checkout",
                          headers=_hdr(SMOKE_TOKEN),
                          json={"tier": "family_sentinel", "billing": "weekly",
                                "origin_url": "https://example.com"})
        assert r.status_code == 400


# ============================================================
# 2) SUBSCRIPTION CANCEL
# ============================================================
class TestCancel:
    def test_inner_circle_cannot_cancel(self):
        r = requests.post(f"{BASE_URL}/api/subscription/cancel", headers=_hdr(FOUNDER_TOKEN))
        assert r.status_code == 400
        assert "inner_circle" in r.text.lower()

    def test_cancel_active_then_repeat_conflict(self):
        # Give smoke user an active tier
        db.users.update_one({"user_id": "user_smoke2026"}, {"$set": {
            "tier": "guardian",
            "tier_until": datetime.now(timezone.utc) + timedelta(days=10),
            "tier_paid_with": "card", "tier_billing": "monthly",
        }})
        r1 = requests.post(f"{BASE_URL}/api/subscription/cancel", headers=_hdr(SMOKE_TOKEN))
        assert r1.status_code == 200, r1.text
        j = r1.json()
        assert j["tier"] == "sovereign"
        assert "zrušené" in j.get("message", "").lower() or "predplatné" in j.get("message", "").lower()

        # Verify persistence
        fresh = db.users.find_one({"user_id": "user_smoke2026"})
        assert fresh["tier"] == "sovereign"

        # Repeat — 409
        r2 = requests.post(f"{BASE_URL}/api/subscription/cancel", headers=_hdr(SMOKE_TOKEN))
        assert r2.status_code == 409


# ============================================================
# 3) FOUNDER GIFTING
# ============================================================
class TestGifting:
    def test_non_founder_forbidden(self):
        r = requests.post(f"{BASE_URL}/api/billing/gift",
                          headers=_hdr(SMOKE_TOKEN),
                          json={"email": "any@example.com", "tier": "sentinel", "days": 7})
        assert r.status_code == 403

    def test_unknown_email_404(self):
        r = requests.post(f"{BASE_URL}/api/billing/gift",
                          headers=_hdr(FOUNDER_TOKEN),
                          json={"email": "no_such_user_12345@example.com", "tier": "guardian", "days": 5})
        assert r.status_code == 404

    def test_invalid_tier_400(self):
        r = requests.post(f"{BASE_URL}/api/billing/gift",
                          headers=_hdr(FOUNDER_TOKEN),
                          json={"email": "smoke2026@example.com", "tier": "bogus", "days": 5})
        assert r.status_code == 400

    def test_founder_gift_success_and_history(self):
        # Ensure a recipient exists with known email
        db.users.update_one({"user_id": "user_smoke2026"},
                            {"$set": {"email": "smoke2026@example.com"}})
        _reset_smoke_to_sovereign()
        r = requests.post(f"{BASE_URL}/api/billing/gift",
                          headers=_hdr(FOUNDER_TOKEN),
                          json={"email": "smoke2026@example.com", "tier": "sentinel", "days": 14})
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("ok") is True
        assert j["gift"]["tier"] == "sentinel"
        assert j["gift"]["days"] == 14

        # Verify recipient upgraded with founder_gift
        fresh = db.users.find_one({"user_id": "user_smoke2026"})
        assert fresh["tier"] == "sentinel"
        assert fresh["tier_paid_with"] == "founder_gift"

        # Gift history — founder only
        r2 = requests.get(f"{BASE_URL}/api/billing/gifts", headers=_hdr(FOUNDER_TOKEN))
        assert r2.status_code == 200, r2.text
        gifts = r2.json()
        assert isinstance(gifts, list) and len(gifts) >= 1
        assert any(g.get("to_email") == "smoke2026@example.com" for g in gifts)

        # Non-founder gets 403
        r3 = requests.get(f"{BASE_URL}/api/billing/gifts", headers=_hdr(SMOKE_TOKEN))
        assert r3.status_code == 403

    def test_cleanup_reset_recipient(self):
        # Cancel via smoke user's own token
        r = requests.post(f"{BASE_URL}/api/subscription/cancel", headers=_hdr(SMOKE_TOKEN))
        assert r.status_code in (200, 409)  # if already reset by another test, 409 acceptable
        _reset_smoke_to_sovereign()


# ============================================================
# 4) RECEIPT + FAMILY ACTIVATION (via internal _activate_tier)
# ============================================================
# We CANNOT complete a Stripe UI flow from pytest headlessly. Instead we call the
# internal _activate_tier() function directly against a pre-inserted 'unpaid' tx.
# This validates receipt PDF + calendar event + multi-member family activation
# WITHOUT faking any user tier state — the function itself performs the writes.

@pytest.mark.asyncio
async def test_receipt_and_family_activation():
    import asyncio, sys
    sys.path.insert(0, "/app/backend")
    from routes.billing import _activate_tier
    from motor.motor_asyncio import AsyncIOMotorClient
    amc = AsyncIOMotorClient(MONGO_URL)
    adb = amc[DB_NAME]

    # 4a — Single-tier receipt (guardian monthly)
    payer_id, payer_tok, payer_email = _make_user("payer26")
    sid_solo = f"cs_test_iter26_solo_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)
    await adb.payment_transactions.insert_one({
        "session_id": sid_solo, "user_id": payer_id,
        "tier": "guardian", "billing": "monthly",
        "amount_eur": 29.0, "currency": "eur",
        "payment_status": "initiated", "processed": False,
        "created_at": now, "updated_at": now,
    })
    ok = await _activate_tier(sid_solo)
    assert ok is True

    # Verify tier applied
    u = await adb.users.find_one({"user_id": payer_id})
    assert u["tier"] == "guardian"
    assert u["tier_paid_with"] == "card"

    # Verify receipt PDF doc
    doc = await adb.documents.find_one({"user_id": payer_id, "source": "billing_receipt"})
    assert doc is not None, "No billing_receipt doc created"
    assert doc["content_type"] == "application/pdf"
    assert doc["title"].startswith("Doklad o platbe")
    assert doc["size"] > 100  # sensible PDF size

    # Verify calendar timeline entry with 🧾
    cal = await adb.calendar_events.find_one({"user_id": payer_id, "source": "billing"})
    assert cal is not None, "No calendar timeline entry"
    assert "🧾" in cal["title"]

    # Verify GET /api/vault/documents lists it, and file endpoint returns PDF
    r_docs = requests.get(f"{BASE_URL}/api/vault/documents", headers=_hdr(payer_tok))
    assert r_docs.status_code == 200
    doc_ids = [d.get("doc_id") for d in r_docs.json()]
    assert doc["doc_id"] in doc_ids

    r_file = requests.get(f"{BASE_URL}/api/vault/documents/{doc['doc_id']}/file?token={payer_tok}")
    assert r_file.status_code == 200, r_file.text[:200]
    assert r_file.headers.get("content-type", "").startswith("application/pdf")
    assert r_file.content[:4] == b"%PDF"

    # Verify /billing/transactions shows processed:true
    r_tx = requests.get(f"{BASE_URL}/api/billing/transactions", headers=_hdr(payer_tok))
    assert r_tx.status_code == 200
    tx = next((t for t in r_tx.json() if t["session_id"] == sid_solo), None)
    assert tx is not None and tx["processed"] is True

    # Idempotency — second activation must return False
    ok2 = await _activate_tier(sid_solo)
    assert ok2 is False

    # 4b — Family pack: payer with 2 guardian links + 1 archangel member (must NOT downgrade)
    fam_payer_id, fam_payer_tok, fam_payer_email = _make_user("fampay26")
    g1_id, g1_tok, g1_email = _make_user("famguard1")
    g2_id, g2_tok, g2_email = _make_user("famguard2")
    g3_id, g3_tok, g3_email = _make_user("famarch3")

    # Make g3 archangel — must NOT be downgraded
    await adb.users.update_one({"user_id": g3_id}, {"$set": {
        "tier": "archangel",
        "tier_until": datetime.now(timezone.utc) + timedelta(days=100),
    }})

    for g in (g1_id, g2_id, g3_id):
        await adb.guardians.insert_one({
            "user_id": fam_payer_id, "guardian_user_id": g,
            "guardian_name": g, "guardian_email": f"{g}@example.com",
            "created_at": datetime.now(timezone.utc),
        })

    sid_fam = f"cs_test_iter26_fam_{uuid.uuid4().hex[:10]}"
    await adb.payment_transactions.insert_one({
        "session_id": sid_fam, "user_id": fam_payer_id,
        "tier": "family_sentinel", "billing": "monthly",
        "amount_eur": 249.0, "currency": "eur",
        "payment_status": "initiated", "processed": False,
        "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc),
    })
    ok3 = await _activate_tier(sid_fam)
    assert ok3 is True

    # payer must be sentinel + family_pack_owner
    payer_fresh = await adb.users.find_one({"user_id": fam_payer_id})
    assert payer_fresh["tier"] == "sentinel"
    assert payer_fresh.get("family_pack_owner") is True

    # g1, g2 must be sentinel with family_pack
    for gid in (g1_id, g2_id):
        gu = await adb.users.find_one({"user_id": gid})
        assert gu["tier"] == "sentinel", f"{gid} not upgraded"
        assert gu["tier_paid_with"] == "family_pack"

    # g3 (archangel) must remain archangel — never downgraded
    g3_fresh = await adb.users.find_one({"user_id": g3_id})
    assert g3_fresh["tier"] == "archangel", "Family pack must NOT downgrade archangel"

    # payment_transactions must record family_members_activated
    fam_tx = await adb.payment_transactions.find_one({"session_id": sid_fam})
    assert fam_tx.get("family_members_activated") == 2  # g1+g2, not g3

    # Family receipt should mention family_members
    fam_doc = await adb.documents.find_one({
        "user_id": fam_payer_id, "source": "billing_receipt",
    })
    assert fam_doc is not None
    assert "Rodinný" in fam_doc["title"] or "family" in fam_doc["title"].lower()

    # Cleanup test seed data
    for uid in (payer_id, fam_payer_id, g1_id, g2_id, g3_id):
        await adb.users.delete_one({"user_id": uid})
        await adb.user_sessions.delete_many({"user_id": uid})
        await adb.documents.delete_many({"user_id": uid})
        await adb.calendar_events.delete_many({"user_id": uid})
        await adb.payment_transactions.delete_many({"user_id": uid})
        await adb.guardians.delete_many({"user_id": uid})
        await adb.guardians.delete_many({"guardian_user_id": uid})
        await adb.revenue_events.delete_many({"user_id": uid})
    amc.close()
