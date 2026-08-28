"""Phase 45+46 — Anonymity Seal + Watermark and Dynamic GPS Intelligence tests.

Covers:
- Watermark applied to /api/agent/chat, /api/agent/briefing, /api/agent/analyze
- Pain-diary logging with watermark
- Anonymity Seal: /api/demo/toggle uses 'Strážca' instead of real names
- Dynamic GPS: /api/geo/context, /api/geo/ip-locate, /api/geo/set-city,
  /api/geo/locate, /api/geo/travel-mode
- Edge cache hot fast-path on /api/agent/briefing
- Regression: language pref update
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://biometric-onboard-3.preview.emergentagent.com").rstrip("/")
TOKEN = "smoketok-fresh-2026"      # smoketest-user-1 (founder)
TOKEN_U2 = "smoketok-fresh-2026-u2"  # smoketest-user-2 (non-founder)
WATERMARK = "— AI Content · Sovereign Protocol"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def client_u2():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {TOKEN_U2}", "Content-Type": "application/json"})
    return s


# ============================================================
# 1. Anonymity Seal + Watermark
# ============================================================
class TestWatermark:
    def test_chat_non_pain_has_watermark(self, client):
        r = client.post(f"{BASE_URL}/api/agent/chat", json={"message": "Ako sa máš?", "language": "sk"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert "reply" in data
        assert data["reply"].rstrip().endswith(WATERMARK), f"reply missing watermark tail: {data['reply'][-120:]}"

    def test_chat_pain_message_logs_and_watermarks(self, client):
        r = client.post(f"{BASE_URL}/api/agent/chat", json={"message": "bolí ma to na sedem", "language": "sk"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("pain_logged") == 7, data
        assert WATERMARK in data["reply"], f"pain reply missing watermark: {data['reply'][-160:]}"

    def test_briefing_has_watermark(self, client):
        r = client.get(f"{BASE_URL}/api/agent/briefing?force=true")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "briefing" in data
        assert WATERMARK in data["briefing"], f"briefing missing watermark: {data['briefing'][-160:]}"

    def test_analyze_insight_has_watermark(self, client):
        r = client.post(f"{BASE_URL}/api/agent/analyze")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "insight" in data
        assert WATERMARK in data["insight"], f"insight missing watermark: {data['insight'][-160:]}"


# ============================================================
# 2. Anonymity Seal — demo seed uses 'Strážca'
# ============================================================
class TestAnonymityDemo:
    def test_demo_toggle_founder_only(self, client_u2):
        r = client_u2.post(f"{BASE_URL}/api/demo/toggle", json={"enabled": True})
        # u2 is not the founder
        assert r.status_code == 403, r.text

    def test_demo_toggle_founder_uses_strazca(self, client):
        r = client.post(f"{BASE_URL}/api/demo/toggle", json={"enabled": True})
        assert r.status_code == 200, r.text
        data = r.json()
        seeded = data.get("seeded") or {}
        pulse = seeded.get("family_pulse", "")
        assert "Tomáš" not in pulse, f"Tomáš leaked: {pulse}"
        assert "Strážca" in pulse, f"Strážca missing: {pulse}"

        # cleanup
        client.post(f"{BASE_URL}/api/demo/toggle", json={"enabled": False})


# ============================================================
# 3. Dynamic GPS Intelligence
# ============================================================
class TestGeo:
    def test_geo_context_lists_supported_cities(self, client):
        r = client.get(f"{BASE_URL}/api/geo/context")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "geo" in data and "city" in data["geo"]
        assert isinstance(data.get("supported_cities"), list)
        assert len(data["supported_cities"]) >= 15, f"only {len(data['supported_cities'])} cities"

    def test_geo_ip_locate_fallback(self, client):
        r = client.post(f"{BASE_URL}/api/geo/ip-locate", json={})
        assert r.status_code == 200, r.text
        data = r.json()
        geo = data.get("geo") or {}
        assert geo.get("source") in ("ip", "ip-fallback"), geo
        # Behind ingress with private/proxy IP -> ip-fallback default
        if geo.get("source") == "ip-fallback":
            assert geo.get("city") == "Bratislava", geo

    def test_geo_set_city_vieden_returns_language_suggestion(self, client):
        # Ensure travel mode is OFF and current language is sk
        client.put(f"{BASE_URL}/api/geo/travel-mode", json={"enabled": False})
        client.patch(f"{BASE_URL}/api/me/prefs", json={"language": "sk"})

        r = client.post(f"{BASE_URL}/api/geo/set-city", json={"city": "Viedeň"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["geo"]["city"] == "Viedeň"
        assert data["geo"]["source"] == "manual"
        assert data.get("language_switched") is False
        sugg = data.get("language_suggestion") or {}
        assert sugg.get("to") == "de", sugg
        assert sugg.get("from") == "sk", sugg
        assert sugg.get("city") == "Viedeň"
        assert sugg.get("country") == "AT"

    def test_geo_set_city_invalid_400(self, client):
        r = client.post(f"{BASE_URL}/api/geo/set-city", json={"city": "NoSuchCity"})
        assert r.status_code == 400, r.text
        assert "unsupported_city" in r.text

    def test_geo_locate_paris(self, client):
        # travel mode off explicitly
        client.put(f"{BASE_URL}/api/geo/travel-mode", json={"enabled": False})
        client.patch(f"{BASE_URL}/api/me/prefs", json={"language": "sk"})

        r = client.post(f"{BASE_URL}/api/geo/locate", json={"lat": 48.8566, "lng": 2.3522})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["geo"]["city"] == "Paríž", data
        assert data.get("language_switched") is False
        sugg = data.get("language_suggestion") or {}
        assert sugg.get("to") == "fr", sugg


# ============================================================
# 4. Edge cache on briefing
# ============================================================
class TestEdgeCache:
    def test_briefing_cache_consistency(self, client):
        r1 = client.get(f"{BASE_URL}/api/agent/briefing")
        assert r1.status_code == 200, r1.text
        r2 = client.get(f"{BASE_URL}/api/agent/briefing")
        assert r2.status_code == 200, r2.text
        b1 = r1.json().get("briefing")
        b2 = r2.json().get("briefing")
        assert b1 and b2, (b1, b2)
        assert b1 == b2, "cached briefing should be identical"
        assert WATERMARK in b1

    def test_briefing_force_bypass_cache(self, client):
        r = client.get(f"{BASE_URL}/api/agent/briefing?force=true")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("briefing")
        assert WATERMARK in data["briefing"]


# ============================================================
# 5. Regression
# ============================================================
class TestRegression:
    def test_travel_mode_toggle(self, client):
        r = client.put(f"{BASE_URL}/api/geo/travel-mode", json={"enabled": True})
        assert r.status_code == 200, r.text
        assert r.json().get("travel_mode") is True

        # restore
        r2 = client.put(f"{BASE_URL}/api/geo/travel-mode", json={"enabled": False})
        assert r2.status_code == 200

    def test_geo_locate_prague(self, client):
        client.put(f"{BASE_URL}/api/geo/travel-mode", json={"enabled": False})
        client.patch(f"{BASE_URL}/api/me/prefs", json={"language": "sk"})
        r = client.post(f"{BASE_URL}/api/geo/locate", json={"lat": 50.0755, "lng": 14.4378})
        assert r.status_code == 200, r.text
        assert r.json()["geo"]["city"] == "Praha"

    def test_prefs_language_update(self, client):
        r = client.patch(f"{BASE_URL}/api/me/prefs", json={"language": "sk"})
        assert r.status_code == 200, r.text
