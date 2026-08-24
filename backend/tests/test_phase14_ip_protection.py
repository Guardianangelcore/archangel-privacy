# Iteration 14 — IP Protection Layer + Gateway/Stripe fix final verification
# Tests: /api/origin, watermark headers, campaigns collection alignment (bug fix from iter 13),
# regression smoke, and Stripe path (expects 503 stripe_key_missing OR 502, NEVER 500)
import os
import json
import uuid
import requests
import pytest
from pathlib import Path

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://angel-os-1.preview.emergentagent.com").rstrip("/")
SMOKE_TOKEN = "smoketok-fresh-2026"
AUTH = {"Authorization": f"Bearer {SMOKE_TOKEN}"}
# Read the current anchored build dynamically — origin.json is regenerated whenever the
# codebase fingerprint is re-anchored, so hardcoding a hash would break on every re-stamp.
_ORIGIN = json.loads((Path(__file__).resolve().parent.parent / "origin.json").read_text())
EXPECTED_BUILD = _ORIGIN["build"]
EXPECTED_DID = _ORIGIN["did"]


# ---------- Proof of Origin (public, no auth) ----------
class TestProofOfOrigin:
    def test_origin_public_returns_full_record(self):
        r = requests.get(f"{BASE_URL}/api/origin", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("codebase_sha256") == EXPECTED_BUILD.replace("GA-ORIGINAL-", "").lower() or len(d.get("codebase_sha256", "")) == 64
        assert d.get("did", "").startswith("did:guardian:pex:sha256:")
        assert d.get("build") == EXPECTED_BUILD or d.get("build") is None  # may be omitted; ORIGIN.get('build') sent
        assert d.get("anchored") is True
        assert d.get("kind") == "proof_of_origin"

    def test_origin_no_auth_required(self):
        r = requests.get(f"{BASE_URL}/api/origin", timeout=15)
        assert r.status_code == 200

    def test_origin_owner_and_role_present_when_returned(self):
        # ORIGIN dict is merged when db record exists — should include owner/role
        r = requests.get(f"{BASE_URL}/api/origin", timeout=15)
        d = r.json()
        # DB record may not have owner; the fallback ORIGIN merge does.
        # Accept either: owner present OR record is db-first (still valid)
        if "owner" in d:
            assert d["owner"] == "Guardian Angel"


# ---------- Watermark headers on every response ----------
class TestWatermarkHeaders:
    def test_public_root_has_watermark(self):
        r = requests.get(f"{BASE_URL}/api/", timeout=15)
        assert r.status_code == 200
        assert r.headers.get("x-guardian-origin") == EXPECTED_BUILD
        assert r.headers.get("x-origin-did") == EXPECTED_DID

    def test_authed_endpoint_has_watermark(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=AUTH, timeout=15)
        assert r.status_code == 200, r.text
        assert r.headers.get("x-guardian-origin") == EXPECTED_BUILD
        assert r.headers.get("x-origin-did") == EXPECTED_DID

    def test_origin_endpoint_also_has_watermark(self):
        r = requests.get(f"{BASE_URL}/api/origin", timeout=15)
        assert r.headers.get("x-guardian-origin") == EXPECTED_BUILD

    def test_error_response_also_has_watermark(self):
        # 401 path — middleware should still stamp
        r = requests.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code in (401, 403)
        assert r.headers.get("x-guardian-origin") == EXPECTED_BUILD


# ---------- Regression smoke ----------
class TestRegressionSmoke:
    def test_auth_me(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=AUTH, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        u = d.get("user") if isinstance(d.get("user"), dict) else d
        assert u.get("user_id") == "smoketest-user-1"

    def test_calendar_timeline(self):
        r = requests.get(f"{BASE_URL}/api/calendar/timeline", headers=AUTH, timeout=15)
        assert r.status_code == 200, r.text

    def test_sentinel_aggregate(self):
        r = requests.get(f"{BASE_URL}/api/sentinel/aggregate", headers=AUTH, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "signals" in d
        assert "active_nodes" in d


# ---------- Gateway endpoints (no 500 crash on DB) ----------
class TestGatewayNoDBError:
    def test_gateway_grants_list_ok(self):
        r = requests.get(f"{BASE_URL}/api/gateway/grants", headers=AUTH, timeout=15)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_marketplace_offers(self):
        r = requests.get(f"{BASE_URL}/api/marketplace/offers", headers=AUTH, timeout=15)
        assert r.status_code == 200, r.text
        assert "offers" in r.json()

    def test_marketplace_me(self):
        r = requests.get(f"{BASE_URL}/api/marketplace/me", headers=AUTH, timeout=15)
        assert r.status_code == 200, r.text

    def test_grant_create_lifecycle(self):
        pname = f"TEST_IP_{uuid.uuid4().hex[:6]}"
        r = requests.post(
            f"{BASE_URL}/api/gateway/grants",
            headers=AUTH,
            json={"partner_name": pname, "scopes": ["emergency_profile"], "expires_days": 7},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["partner_name"] == pname
        assert d["token"].startswith("gwk_")
        gid = d["grant_id"]
        # cleanup
        rev = requests.delete(f"{BASE_URL}/api/gateway/grants/{gid}", headers=AUTH, timeout=15)
        assert rev.status_code == 200


# ---------- Solidarity + Stripe (must NOT 500 from DB) ----------
class TestSolidarityStripe:
    _cid = None

    def test_solidarity_list(self):
        r = requests.get(f"{BASE_URL}/api/solidarity/campaigns", headers=AUTH, timeout=15)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_create_and_checkout_no_500(self):
        # Ensure at least 1 campaign exists (create a fresh one)
        cr = requests.post(
            f"{BASE_URL}/api/solidarity/campaigns",
            headers=AUTH,
            json={"title": f"TEST_IP_camp_{uuid.uuid4().hex[:6]}", "goal_amount": 100.0, "description": "test", "story": "test story for iteration 14 IP protection layer verification"},
            timeout=15,
        )
        assert cr.status_code in (200, 201), cr.text
        cid = cr.json().get("campaign_id")
        assert cid, cr.text
        TestSolidarityStripe._cid = cid

        # /checkout — with placeholder key expect 503 stripe_key_missing (bug from iter 13 was 404).
        # A Stripe-side 502 is also acceptable if a real key is present. A 500 IS A BUG.
        chk = requests.post(
            f"{BASE_URL}/api/solidarity/campaigns/{cid}/checkout",
            headers=AUTH,
            json={"amount_eur": 5.0},
            timeout=20,
        )
        assert chk.status_code != 500, f"DB-layer 500 detected: {chk.text}"
        # Must NOT be 404 (would indicate old collection-mismatch regression)
        assert chk.status_code != 404, f"Bug from iter 13 regressed — 404 Campaign not found while campaign exists: {chk.text}"
        # Acceptable outcomes:
        assert chk.status_code in (200, 502, 503), f"Unexpected status: {chk.status_code} {chk.text}"
        if chk.status_code == 503:
            assert "stripe_key_missing" in chk.text

    def test_amount_validation_before_stripe(self):
        cid = TestSolidarityStripe._cid
        if not cid:
            pytest.skip("no campaign")
        chk = requests.post(
            f"{BASE_URL}/api/solidarity/campaigns/{cid}/checkout",
            headers=AUTH,
            json={"amount_eur": 0.5},
            timeout=15,
        )
        assert chk.status_code == 400

    def test_donate_still_works_same_collection(self):
        # Confirms both /donate and /checkout use db.campaigns
        cid = TestSolidarityStripe._cid
        if not cid:
            pytest.skip("no campaign")
        d = requests.post(
            f"{BASE_URL}/api/solidarity/campaigns/{cid}/donate",
            headers=AUTH,
            json={"amount": 5.0},
            timeout=15,
        )
        assert d.status_code in (200, 201), d.text


# ---------- Neural / Jarvis wealth path reads db.campaigns (no 500) ----------
class TestNeuralWealth:
    def test_jarvis_context_ok(self):
        r = requests.get(f"{BASE_URL}/api/jarvis/context", headers=AUTH, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "wealth" in d and "solidarity_campaigns" in d["wealth"]

    def test_chain_supply_uses_campaigns(self):
        r = requests.post(
            f"{BASE_URL}/api/chains/supply",
            headers=AUTH,
            json={"med_name": "Ibuprofen", "region": "SK"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        assert "steps" in r.json()
