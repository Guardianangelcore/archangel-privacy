"""Iter 54 — 3 urgent bug regression tests.

Fixes under test:
  #1 Jarvis chat error path (503 JSON, not 502/HTML) + streaming SSE JSON error frame.
  #2 SOS keyword endpoint: 400 on empty; on non-empty must NOT return sos_detected=true
     (LLM budget exhausted → 503 or 502; NEVER return sos_detected).
  #3 Geo: /geo/locate reverse-geocodes GPS, /geo/context resolves by IP for new users,
     briefing weather is never "New York" default when unresolved.
"""
import os
import io
import json
import time
import uuid
import requests
import pytest

BASE = (os.environ.get("EXPO_BACKEND_URL")
        or os.environ.get("EXPO_PUBLIC_BACKEND_URL")
        or "https://physio-lang-fix.preview.emergentagent.com").rstrip("/")


# ---------- helpers ----------
@pytest.fixture
def founder_token():
    r = requests.post(f"{BASE}/api/auth/dev-bypass",
                      json={"email": "guardianangel.core@proton.me",
                            "name": "Guardian Angel"}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["session_token"]


@pytest.fixture
def new_user_token():
    email = f"geo-test-{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{BASE}/api/auth/dev-bypass",
                      json={"email": email, "name": "Geo Test"}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["session_token"], email


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------- BUG #1: Jarvis readable error ----------
class TestJarvisReadableError:
    def test_chat_returns_503_json_not_502(self, founder_token):
        r = requests.post(f"{BASE}/api/agent/chat",
                          headers={**H(founder_token), "Content-Type": "application/json"},
                          json={"message": "hi", "language": "en"}, timeout=60)
        # Expected: 503 with clear JSON detail. NOT 502 HTML.
        assert r.status_code == 503, f"expected 503, got {r.status_code} body={r.text[:400]}"
        assert "application/json" in r.headers.get("content-type", ""), r.headers
        body = r.json()
        detail = body.get("detail", "")
        assert "budget" in detail.lower() or "unavailable" in detail.lower(), detail
        assert "<html" not in r.text.lower()

    def test_chat_stream_emits_json_error_event(self, founder_token):
        r = requests.post(f"{BASE}/api/agent/chat/stream",
                          headers={**H(founder_token), "Content-Type": "application/json"},
                          json={"message": "hi", "language": "en"}, timeout=60, stream=True)
        assert r.status_code == 200, r.text
        first_data = None
        for raw in r.iter_lines(decode_unicode=True):
            if raw and raw.startswith("data:"):
                try:
                    first_data = json.loads(raw[5:].strip())
                except Exception:
                    first_data = raw
                break
        r.close()
        assert first_data is not None, "no SSE data event received"
        # Should be an error frame with readable message
        assert isinstance(first_data, dict), first_data
        assert "error" in first_data, first_data
        msg = first_data["error"].lower()
        assert ("budget" in msg or "unavailable" in msg), first_data


# ---------- BUG #2: Angel SOS keyword ----------
class TestSosKeyword:
    def test_empty_audio_returns_400(self, founder_token):
        files = {"file": ("empty.webm", b"", "audio/webm")}
        r = requests.post(f"{BASE}/api/voice/sos-keyword",
                          headers=H(founder_token), files=files, timeout=30)
        assert r.status_code == 400, r.text
        assert "empty" in r.text.lower()

    def test_endpoint_exists_and_never_returns_sos_true_on_llm_fail(self, founder_token):
        # Small non-empty fake webm bytes → Whisper attempted → LLM budget → 502 or 503
        fake = b"\x1a\x45\xdf\xa3" + b"\x00" * 128
        files = {"file": ("fake.webm", fake, "audio/webm")}
        r = requests.post(f"{BASE}/api/voice/sos-keyword",
                          headers=H(founder_token), files=files, timeout=60)
        assert r.status_code != 404, "endpoint missing"
        assert r.status_code != 405, "wrong method"
        # LLM is down → we expect 502/503. Must NEVER falsely detect SOS.
        assert r.status_code in (502, 503), f"unexpected status {r.status_code}: {r.text[:300]}"
        try:
            body = r.json()
            assert body.get("sos_detected") is not True
        except ValueError:
            pass  # non-JSON error body — that's fine as long as no sos_detected:true


# ---------- BUG #3: Geo location resolution ----------
class TestGeoLocate:
    def test_locate_gps_reverse_geocodes(self, founder_token):
        # Košice coordinates
        r = requests.post(f"{BASE}/api/geo/locate",
                          headers={**H(founder_token), "Content-Type": "application/json"},
                          json={"lat": 48.72, "lng": 21.26}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        geo = body["geo"]
        assert geo["source"] == "gps"
        # raw coords preserved
        assert abs(geo["lat"] - 48.72) < 0.01
        assert abs(geo["lng"] - 21.26) < 0.01
        assert geo.get("nearest_city") == "Košice"
        # city reverse-geocoded (network best-effort) — fallback to nearest_city "Košice"
        assert geo["city"], geo
        # never the default
        assert geo["city"] != "New York"

    def test_context_matches_located_city(self, founder_token):
        r = requests.get(f"{BASE}/api/geo/context", headers=H(founder_token), timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["resolved"] is True
        assert body["geo"]["city"] != "New York"

    def test_briefing_weather_matches_located_city(self, founder_token):
        r = requests.get(f"{BASE}/api/agent/briefing?force=true",
                         headers=H(founder_token), timeout=60)
        # briefing text uses LLM fallback since budget exhausted → still 200
        assert r.status_code == 200, r.text
        body = r.json()
        w = body.get("weather")
        # weather may be None or must not be NY
        if w:
            assert w.get("city") != "New York", w
            assert w.get("source") in ("gps", "ip", "manual"), w

    def test_new_user_ip_fallback_never_new_york(self, new_user_token):
        tok, email = new_user_token
        # Slovak Telekom IP
        h = {**H(tok), "X-Forwarded-For": "195.28.64.1"}
        r = requests.get(f"{BASE}/api/geo/context", headers=h, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["resolved"] is True, body
        assert body["geo"]["source"] == "ip", body
        # Some Slovak city (Bratislava most likely; never New York)
        assert body["geo"]["city"] != "New York", body
        assert body["geo"]["country"] == "SK", body

    def test_new_user_briefing_never_new_york(self, new_user_token):
        tok, _ = new_user_token
        h = {**H(tok), "X-Forwarded-For": "195.28.64.1"}
        r = requests.get(f"{BASE}/api/agent/briefing?force=true", headers=h, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        w = body.get("weather")
        if w:
            assert w.get("city") != "New York", w
