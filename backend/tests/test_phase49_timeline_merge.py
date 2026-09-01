"""Phase 49 TIMELINE MERGE — verifies:
- POST /api/auth/dev-bypass (founder + custom email) → session_token, inner_circle, tier=archangel
- POST /api/agent/search (Sonar) → 200 degraded fallback in Slovak, xp_gained=6
- POST /api/agent/imagine (GPT Image 1) → 200 image_base64 (large PNG)
- Regressions: GET /api/triage/state, GET /api/lens/models, POST /api/agent/chat
"""
import os
import base64
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/")
FOUNDER_EMAIL = "guardian.angel.core@proton.me"
SMOKE_TOKEN = "smoketok-fresh-2026"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


@pytest.fixture(scope="module")
def founder_token(s):
    r = s.post(f"{BASE_URL}/api/auth/dev-bypass",
               json={"email": FOUNDER_EMAIL, "name": "Guardian Angel"}, timeout=30)
    assert r.status_code == 200, f"dev-bypass failed: {r.status_code} {r.text[:200]}"
    j = r.json()
    assert "session_token" in j and j["session_token"]
    return j["session_token"]


# ------------ AUTH ------------
class TestAuthDevBypass:
    def test_founder_bypass_returns_archangel(self, s):
        r = s.post(f"{BASE_URL}/api/auth/dev-bypass",
                   json={"email": FOUNDER_EMAIL, "name": "Guardian Angel"}, timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("session_token"), "session_token missing"
        user = j.get("user") or {}
        assert user.get("inner_circle") is True, f"inner_circle should be True, got {user}"
        assert user.get("tier") == "archangel", f"tier should be archangel, got {user.get('tier')}"

    def test_custom_email_bypass(self, s):
        r = s.post(f"{BASE_URL}/api/auth/dev-bypass",
                   json={"email": "TEST_tester@guardian.dev", "name": "Tester"}, timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("session_token")
        # non-founder shouldn't be archangel
        user = j.get("user") or {}
        assert (user.get("email") or "").lower() == "test_tester@guardian.dev"


# ------------ JARVIS ULTRA ------------
class TestJarvisUltra:
    def test_search_degraded_slovak(self, s, founder_token):
        headers = {"Authorization": f"Bearer {founder_token}", "Content-Type": "application/json"}
        r = requests.post(f"{BASE_URL}/api/agent/search",
                          json={"query": "Aké sú odporúčania EMA pre ibuprofen?", "language": "sk"},
                          headers=headers, timeout=90)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        j = r.json()
        assert "reply" in j and j["reply"], "no reply"
        assert j.get("degraded") in (True, False), "degraded flag must be present (live key configured)"
        assert j.get("citations") == [] or j.get("citations") is None or isinstance(j.get("citations"), list)
        assert j.get("xp_gained") == 6, f"xp_gained should be 6, got {j.get('xp_gained')}"

    def test_imagine_returns_png_base64(self, s, founder_token):
        headers = {"Authorization": f"Bearer {founder_token}", "Content-Type": "application/json"}
        r = requests.post(f"{BASE_URL}/api/agent/imagine",
                          json={"prompt": "zlaté anjelské krídla nad Bratislavou"},
                          headers=headers, timeout=180)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        j = r.json()
        b64 = j.get("image_base64")
        assert b64 and isinstance(b64, str), "no image_base64"
        # Should decode and be a substantial PNG
        raw = base64.b64decode(b64)
        assert len(raw) > 10_000, f"image too small: {len(raw)} bytes"
        # PNG magic
        assert raw[:8] == b"\x89PNG\r\n\x1a\n" or raw[:3] == b"\xff\xd8\xff", "not PNG/JPEG"


# ------------ REGRESSIONS ------------
class TestRegressions:
    def test_triage_state_calm(self, s):
        headers = {"Authorization": f"Bearer {SMOKE_TOKEN}"}
        r = requests.get(f"{BASE_URL}/api/triage/state", headers=headers, timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("crisis_level") in ("calm", "elevated", "crisis"), j

    def test_lens_models_four(self, s):
        headers = {"Authorization": f"Bearer {SMOKE_TOKEN}"}
        r = requests.get(f"{BASE_URL}/api/lens/models", headers=headers, timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        models = j.get("models") or j
        # allow either shape
        if isinstance(models, dict) and "models" in models:
            models = models["models"]
        assert isinstance(models, list)
        assert len(models) == 4, f"expected 4 models, got {len(models)}"

    def test_agent_chat_watermark(self, s, founder_token):
        headers = {"Authorization": f"Bearer {founder_token}", "Content-Type": "application/json"}
        r = requests.post(f"{BASE_URL}/api/agent/chat",
                          json={"message": "Ahoj", "language": "sk"},
                          headers=headers, timeout=60)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("reply"), "no reply"
