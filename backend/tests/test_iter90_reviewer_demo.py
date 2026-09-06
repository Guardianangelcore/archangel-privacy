# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
"""Iter 90 — Lock Demo Mode · store-reviewer account · production billing note.

Run: FOUNDER_TEST_PASSWORD='<secret>' pytest tests/test_iter90_reviewer_demo.py -q
"""
import os
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

API = "https://physio-lang-fix.preview.emergentagent.com/api"
REVIEWER_EMAIL = os.environ.get("REVIEWER_EMAIL", "appreview@archangel-os.app")
REVIEWER_PASSWORD = os.environ.get("REVIEWER_PASSWORD", "")
FOUNDER_EMAIL = os.environ.get("FOUNDER_EMAIL", "guardianangel.core@proton.me")
FOUNDER_PASSWORD = os.environ.get("FOUNDER_TEST_PASSWORD", "")


def _login(email: str, password: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, (r.status_code, r.text[:300])
    return r.json()["session_token"]


@pytest.fixture(scope="module")
def reviewer_h():
    if not REVIEWER_PASSWORD:
        pytest.skip("REVIEWER_PASSWORD not configured")
    return {"Authorization": f"Bearer {_login(REVIEWER_EMAIL, REVIEWER_PASSWORD)}"}


@pytest.fixture(scope="module")
def founder_h():
    if not FOUNDER_PASSWORD:
        pytest.skip("FOUNDER_TEST_PASSWORD not in the process environment")
    return {"Authorization": f"Bearer {_login(FOUNDER_EMAIL, FOUNDER_PASSWORD)}"}


class TestReviewerAccount:
    def test_reviewer_can_sign_in_and_is_archangel(self, reviewer_h):
        d = requests.get(f"{API}/subscription", headers=reviewer_h, timeout=20).json()
        assert d["tier"] == "archangel", d
        assert d["paid_with"] == "store_reviewer", d
        assert d["demo_active"] is False, d

    def test_reviewer_is_not_privileged(self, reviewer_h):
        # No Foundation admin surface for the reviewer account.
        assert requests.get(f"{API}/wealth/founder-dashboard", headers=reviewer_h, timeout=20).status_code == 403
        assert requests.get(f"{API}/uhp/partners/admin", headers=reviewer_h, timeout=20).status_code == 403
        assert requests.get(f"{API}/demo/status", headers=reviewer_h, timeout=20).json()["is_founder"] is False

    def test_reviewer_has_showcase_data(self, reviewer_h):
        card = requests.get(f"{API}/lifecard", headers=reviewer_h, timeout=20).json()
        assert card["blood_type"] == "A+" and card["birth_date"], card
        assert sum(int(v) for v in (card.get("counts") or {}).values() if isinstance(v, (int, float))) >= 7, card
        assert card.get("predictions"), card
        contacts = requests.get(f"{API}/family-contacts", headers=reviewer_h, timeout=20).json()
        assert contacts["total"] >= 1, contacts

    def test_reviewer_reaches_premium_features(self, reviewer_h):
        # Sentinel-gated endpoint must not paywall the reviewer (402 = paywall).
        assert requests.get(f"{API}/medic/protocols", headers=reviewer_h, timeout=30).status_code != 402


class TestDemoModeLocked:
    def test_start_requires_auth(self):
        assert requests.post(f"{API}/demo-mode/start", timeout=20).status_code in (401, 403)

    def test_reviewer_cannot_self_grant(self, reviewer_h):
        r = requests.post(f"{API}/demo-mode/start", headers=reviewer_h, timeout=20)
        assert r.status_code == 403, (r.status_code, r.text[:200])
        assert "not_available" in r.text

    def test_founder_can_start_and_stop(self, founder_h):
        r = requests.post(f"{API}/demo-mode/start", headers=founder_h, timeout=20)
        assert r.status_code == 200, (r.status_code, r.text[:200])
        assert r.json()["active"] is True
        assert requests.post(f"{API}/demo-mode/stop", headers=founder_h, timeout=20).json()["active"] is False


class TestBillingNote:
    def test_no_test_card_hint(self, reviewer_h):
        note = requests.get(f"{API}/subscription", headers=reviewer_h, timeout=20).json()["billing_note"]
        low = note.lower()
        assert note and "test" not in low and "4242" not in low and "stripe" not in low, note
