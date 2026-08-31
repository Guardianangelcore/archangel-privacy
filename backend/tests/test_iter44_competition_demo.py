"""Iteration 44 — Competition Demo verification + Achievements removal.
Tests: founder dev-bypass login, /demo/seed idempotency, seeded lifecard/timeline,
prediction, /achievements 404, /streaks/physio moved module, /healing/state EN labels.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://guardian-vault-13.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

FOUNDER_EMAIL = "guardian.angel.core@proton.me"
FOUNDER_NAME = "Guardian Angel"


@pytest.fixture(scope="module")
def founder_token():
    r = requests.post(f"{API}/auth/dev-bypass",
                      json={"email": FOUNDER_EMAIL, "name": FOUNDER_NAME},
                      timeout=30)
    assert r.status_code == 200, f"dev-bypass failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("session_token") or data.get("token")
    assert tok, f"no token in response: {data}"
    return tok


@pytest.fixture(scope="module")
def auth(founder_token):
    return {"Authorization": f"Bearer {founder_token}"}


# ---------- AUTH ----------
class TestFounderAuth:
    def test_dev_bypass_returns_token(self, founder_token):
        assert founder_token and len(founder_token) > 5

    def test_auth_me(self, auth):
        r = requests.get(f"{API}/auth/me", headers=auth, timeout=15)
        assert r.status_code == 200
        u = r.json().get("user") or r.json()
        assert (u.get("email") or "").lower() == FOUNDER_EMAIL
        # Founder must be language=en per spec
        assert u.get("language") == "en", f"founder language should be 'en', got {u.get('language')}"


# ---------- DEMO SEED ----------
class TestDemoSeed:
    def test_demo_seed_idempotent(self, auth):
        r = requests.post(f"{API}/demo/seed", headers=auth, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        # Already seeded per handoff → seeded:false
        assert body.get("seeded") is False, f"expected seeded:false (idempotent), got {body}"

    def test_lifecard_identity(self, auth):
        r = requests.get(f"{API}/lifecard", headers=auth, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        # birth_date may live on user identity or profile — check both
        identity = data.get("identity") or data.get("user") or data
        birth = identity.get("birth_date") or data.get("birth_date")
        assert birth == "1985-03-15", f"birth_date mismatch: {birth} · payload={data}"
        blood = (identity.get("blood_type") or data.get("blood_type")
                 or (data.get("emergency") or {}).get("blood_type"))
        assert blood == "A+", f"blood_type mismatch: {blood}"

    def test_emergency_profile_blood(self, auth):
        r = requests.get(f"{API}/emergency-profile", headers=auth, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("blood_type") == "A+"

    def test_calendar_events_seeded(self, auth):
        r = requests.get(f"{API}/calendar/timeline", headers=auth, timeout=15)
        assert r.status_code == 200, r.text
        events = r.json()
        if isinstance(events, dict):
            events = events.get("events") or events.get("items") or events.get("timeline") or []
        titles = {e.get("title") for e in events}
        expected = {
            "Flu vaccine",
            "Tetanus booster",
            "COVID-19 booster",
            "Knee arthroscopy",
            "Appendectomy",
            "Lab: Blood glucose 5.2 mmol/L",
            "Lab: Total cholesterol 4.8 mmol/L",
            "Annual physical examination",
        }
        missing = expected - titles
        assert not missing, f"missing seeded events: {missing}. Present: {titles}"

    def test_calendar_events_exact_dates(self, auth):
        r = requests.get(f"{API}/calendar/timeline", headers=auth, timeout=15)
        events = r.json()
        if isinstance(events, dict):
            events = events.get("events") or events.get("items") or events.get("timeline") or []
        by_title = {e.get("title"): e for e in events}
        expected_dates = {
            "Flu vaccine": "2023-10-15",
            "Tetanus booster": "2021-05-20",
            "COVID-19 booster": "2022-04-10",
            "Knee arthroscopy": "2019-08-12",
            "Appendectomy": "2012-03-25",
            "Lab: Blood glucose 5.2 mmol/L": "2024-01-15",
            "Lab: Total cholesterol 4.8 mmol/L": "2024-01-15",
            "Annual physical examination": "2026-09-15",
        }
        for title, expected_date in expected_dates.items():
            got = by_title.get(title, {}).get("date")
            assert got == expected_date, f"{title}: expected {expected_date}, got {got}"

    def test_jarvis_prediction_event_flagged(self, auth):
        r = requests.get(f"{API}/calendar/timeline", headers=auth, timeout=15)
        events = r.json()
        if isinstance(events, dict):
            events = events.get("events") or events.get("items") or events.get("timeline") or []
        pred = [e for e in events if e.get("title") == "Annual physical examination"]
        assert pred, "annual physical examination event missing"
        p = pred[0]
        # Should be flagged as jarvis source
        assert p.get("source") == "jarvis", f"expected source=jarvis, got {p.get('source')}"

    def test_lifecard_prediction_box(self, auth):
        # Predictions are stored per lifecard_predictions collection — fetch via lifecard or dedicated endpoint
        r = requests.get(f"{API}/lifecard", headers=auth, timeout=20)
        data = r.json()
        preds = (data.get("predictions") or {}).get("predictions") if isinstance(data.get("predictions"), dict) else data.get("predictions")
        if not preds:
            # try alternate GET
            r2 = requests.get(f"{API}/lifecard/predictions", headers=auth, timeout=20)
            if r2.status_code == 200:
                d2 = r2.json()
                preds = d2.get("predictions") if isinstance(d2, dict) else d2
        assert preds, f"no predictions found in lifecard payload: {data}"
        titles = {p.get("title") for p in preds}
        assert "Annual physical examination" in titles
        for p in preds:
            if p.get("title") == "Annual physical examination":
                assert p.get("suggested_date") == "2026-09-15"


# ---------- ACHIEVEMENTS REMOVAL ----------
class TestAchievementsRemoved:
    def test_achievements_404(self, auth):
        r = requests.get(f"{API}/achievements", headers=auth, timeout=10)
        assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text[:200]}"


# ---------- STREAKS (moved module) ----------
class TestStreaksMoved:
    def test_streaks_physio(self, auth):
        r = requests.get(f"{API}/streaks/physio", headers=auth, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "current" in d and "tier" in d and "freeze_available" in d, f"missing fields: {d}"
        assert isinstance(d["current"], int)
        assert isinstance(d["tier"], int)
        assert isinstance(d["freeze_available"], bool)


# ---------- HEALING (English labels) ----------
class TestHealingEnglish:
    def test_healing_state_english_labels(self, auth):
        r = requests.get(f"{API}/healing/state", headers=auth, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        meta = d.get("steps_meta") or {}
        # Required EN titles
        expected = {
            "intake": "Intake",
            "financial_shield": "Financial Shield",
            "access": "Access",
            "bureaucracy": "Paperwork",
            "recovery": "Recovery",
        }
        for key, want in expected.items():
            got = (meta.get(key) or {}).get("title")
            assert got == want, f"steps_meta[{key}].title expected '{want}', got '{got}'"

        journey = d.get("journey") or {}
        kind_label = journey.get("kind_label")
        # Should be English 'Illness' (or None if no active journey — spec says 'Illness')
        if kind_label:
            assert kind_label == "Illness", f"kind_label expected 'Illness', got '{kind_label}'"
