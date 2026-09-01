"""Iteration 46 — FINAL competition bug-fix pass verification.

Covers:
- POST /api/auth/dev-bypass (founder login on preview env)
- GET  /api/geo/context (default NYC, EN city names)
- POST /api/geo/set-city (Vienna → then reset to New York)
- GET  /api/lifecard (predictions box contains 'Annual physical examination' 2026-09-15;
    calendar timeline retains 7 seeded demo records: flu/tetanus/covid/knee/appendectomy/2 labs).
- GET  /api/healing/state (steps_meta EN: Intake, Financial Shield, Access, Paperwork)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def founder_token():
    r = requests.post(
        f"{API}/auth/dev-bypass",
        json={"email": "guardian.angel.core@proton.me", "name": "Guardian Angel"},
        timeout=20,
    )
    assert r.status_code == 200, f"dev-bypass failed: {r.status_code} {r.text}"
    data = r.json()
    assert "session_token" in data, f"no session_token: {data}"
    return data["session_token"]


@pytest.fixture
def auth_headers(founder_token):
    return {"Authorization": f"Bearer {founder_token}", "Content-Type": "application/json"}


# ---- AUTH ----
class TestAuth:
    def test_dev_bypass_founder(self, founder_token):
        assert founder_token and len(founder_token) > 8

    def test_auth_me_language_en(self, auth_headers):
        r = requests.get(f"{API}/auth/me", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        user = data.get("user") or data
        assert user.get("email") == "guardian.angel.core@proton.me"
        # Founder is EN per iter 44
        assert user.get("language") == "en", f"language should be en, got: {user.get('language')}"


# ---- GEO ----
class TestGeo:
    def test_geo_context_defaults_nyc(self, auth_headers):
        r = requests.get(f"{API}/geo/context", headers=auth_headers, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        geo = data.get("geo") or data
        # Accept nested or flat
        city = geo.get("city")
        country = geo.get("country")
        lat = geo.get("lat")
        lng = geo.get("lng")
        assert city == "New York", f"expected 'New York', got {city!r}"
        assert country == "US", f"expected 'US', got {country!r}"
        assert abs(float(lat) - 40.7128) < 0.01, f"expected lat ~40.7128, got {lat}"
        assert abs(float(lng) - (-74.006)) < 0.01, f"expected lng ~-74.006, got {lng}"

    def test_set_city_vienna_then_reset_ny(self, auth_headers):
        # set Vienna
        r = requests.post(
            f"{API}/geo/set-city",
            headers=auth_headers,
            json={"city": "Vienna"},
            timeout=15,
        )
        assert r.status_code == 200, r.text

        # Verify persisted
        r2 = requests.get(f"{API}/geo/context", headers=auth_headers, timeout=15)
        assert r2.status_code == 200
        geo = (r2.json().get("geo") or r2.json())
        assert geo.get("city") == "Vienna", f"expected Vienna, got {geo.get('city')!r}"

        # Reset to New York
        r3 = requests.post(
            f"{API}/geo/set-city",
            headers=auth_headers,
            json={"city": "New York"},
            timeout=15,
        )
        assert r3.status_code == 200, r3.text
        r4 = requests.get(f"{API}/geo/context", headers=auth_headers, timeout=15)
        assert r4.status_code == 200
        geo2 = (r4.json().get("geo") or r4.json())
        assert geo2.get("city") == "New York", f"reset failed, got {geo2.get('city')!r}"


# ---- LIFECARD ----
class TestLifeCard:
    def test_lifecard_prediction_preserved(self, auth_headers):
        r = requests.get(f"{API}/lifecard", headers=auth_headers, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        preds = data.get("predictions") or []
        # 'predictions' may be dict with 'items' list per iter 44 note. Accept both shapes.
        if isinstance(preds, dict):
            preds = preds.get("items") or preds.get("predictions") or []
        titles = [str(p.get("title", "")).lower() for p in preds]
        dates = [str(p.get("suggested_date") or p.get("date") or "") for p in preds]
        assert any("annual physical" in t for t in titles), (
            f"'Annual physical examination' missing from predictions: {titles}"
        )
        assert any("2026-09-15" in d for d in dates), f"date 2026-09-15 missing: {dates}"

    def test_timeline_seven_seeded_demo_records(self, auth_headers):
        r = requests.get(f"{API}/calendar/timeline", headers=auth_headers, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        events = data.get("events") or data.get("items") or (data if isinstance(data, list) else [])
        titles = [str(e.get("title", "")).lower() for e in events]
        # 7 seeded demo records (excluding the 'Annual physical examination' prediction)
        expected_substrs = [
            "flu vaccine",
            "tetanus booster",
            "covid-19 booster",
            "knee arthroscopy",
            "appendectomy",
            "blood glucose",
            "cholesterol",
        ]
        missing = [s for s in expected_substrs if not any(s in t for t in titles)]
        assert not missing, f"missing seeded demo records: {missing}. Got: {titles}"


# ---- HEALING ----
class TestHealing:
    def test_healing_state_english_steps(self, auth_headers):
        r = requests.get(f"{API}/healing/state", headers=auth_headers, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        steps_meta = data.get("steps_meta") or {}
        # Expected EN titles
        # Backend key for Paperwork is 'bureaucracy'; title is 'Paperwork' (EN).
        expected = {
            "intake": "Intake",
            "financial_shield": "Financial Shield",
            "access": "Access",
            "bureaucracy": "Paperwork",
        }
        for key, title in expected.items():
            meta = steps_meta.get(key) or {}
            assert meta.get("title") == title, (
                f"steps_meta[{key}].title expected {title!r}, got {meta.get('title')!r}"
            )
        # Ensure no Slovak leaked back in
        all_titles = " ".join(str((m or {}).get("title", "")) for m in steps_meta.values()).lower()
        for slovak in ("príjem", "papierovačky", "zotavenie", "prístup", "financn"):
            assert slovak not in all_titles, f"Slovak leaked into steps_meta: {all_titles}"
