# Iteration 30 — Sentient UX Fork + Onyx TTS backend contract
# Covers: PATCH /me/prefs new fields (birth_year, biometric_enabled, wake_word_enabled),
# TTS onyx voice + 14 languages + mp3 roundtrip + caching + auth guards, and regression on
# GET /auth/me, GET /legal/tos, GET /healing/state, POST /agent/chat.
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/")
TOKEN = "smoketok-fresh-2026"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# ---------- PrefIn new fields ----------
class TestPrefIn:
    def test_patch_all_three_new_fields_persists(self, s):
        r = s.patch(f"{BASE_URL}/api/me/prefs", headers=HEADERS,
                    json={"birth_year": 1958, "biometric_enabled": True, "wake_word_enabled": True})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("birth_year") == 1958
        assert body.get("biometric_enabled") is True
        assert body.get("wake_word_enabled") is True

        # Verify via GET /auth/me
        me = s.get(f"{BASE_URL}/api/auth/me", headers=HEADERS)
        assert me.status_code == 200
        u = me.json().get("user") or {}
        assert u.get("birth_year") == 1958
        assert u.get("biometric_enabled") is True
        assert u.get("wake_word_enabled") is True

    def test_patch_birth_year_1800_rejected(self, s):
        r = s.patch(f"{BASE_URL}/api/me/prefs", headers=HEADERS, json={"birth_year": 1800})
        assert r.status_code == 400, r.text

    def test_patch_birth_year_2100_rejected(self, s):
        r = s.patch(f"{BASE_URL}/api/me/prefs", headers=HEADERS, json={"birth_year": 2100})
        assert r.status_code == 400, r.text

    def test_patch_birth_year_2000_accepted_boundary(self, s):
        r = s.patch(f"{BASE_URL}/api/me/prefs", headers=HEADERS, json={"birth_year": 2000})
        assert r.status_code == 200, r.text
        assert r.json().get("birth_year") == 2000
        # restore
        s.patch(f"{BASE_URL}/api/me/prefs", headers=HEADERS, json={"birth_year": 1958})

    def test_patch_biometric_false_leaves_other_fields(self, s):
        # ensure wake_word is True first
        s.patch(f"{BASE_URL}/api/me/prefs", headers=HEADERS,
                json={"wake_word_enabled": True, "birth_year": 1958})
        r = s.patch(f"{BASE_URL}/api/me/prefs", headers=HEADERS, json={"biometric_enabled": False})
        assert r.status_code == 200, r.text
        b = r.json()
        assert b.get("biometric_enabled") is False
        assert b.get("wake_word_enabled") is True
        assert b.get("birth_year") == 1958
        # restore
        s.patch(f"{BASE_URL}/api/me/prefs", headers=HEADERS, json={"biometric_enabled": True})

    def test_patch_prefs_unauth_401(self, s):
        r = s.patch(f"{BASE_URL}/api/me/prefs", json={"birth_year": 1990},
                    headers={"Content-Type": "application/json"})
        assert r.status_code == 401, r.text


# ---------- TTS onyx + languages + mp3 stream + auth ----------
class TestVoiceTTS:
    def test_tts_onyx_sk(self, s):
        payload = {"text": "Dobrý deň, som Jarvis", "voice": "onyx", "speed": 0.95, "language": "sk"}
        r = s.post(f"{BASE_URL}/api/voice/tts", headers=HEADERS, json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "key" in data and "url" in data
        assert data["url"].startswith("/api/voice/tts/") and data["url"].endswith(".mp3")

        # stream mp3
        audio = s.get(f"{BASE_URL}{data['url']}")
        assert audio.status_code == 200
        assert audio.headers.get("content-type", "").startswith("audio/mpeg")
        assert len(audio.content) > 1024, f"mp3 too small: {len(audio.content)} bytes"

    def test_tts_caching_deterministic_key(self, s):
        payload = {"text": "Cache test 12345", "voice": "onyx", "speed": 1.0, "language": "en"}
        r1 = s.post(f"{BASE_URL}/api/voice/tts", headers=HEADERS, json=payload)
        r2 = s.post(f"{BASE_URL}/api/voice/tts", headers=HEADERS, json=payload)
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["key"] == r2.json()["key"]

    @pytest.mark.parametrize("lang", ["sk", "cs", "en", "de", "fr", "es", "it", "pl", "hu", "uk", "ru", "pt", "nl", "ro"])
    def test_tts_14_languages_onyx(self, s, lang):
        # brief, language-agnostic text; server should accept any language code
        r = s.post(f"{BASE_URL}/api/voice/tts", headers=HEADERS,
                   json={"text": f"Hello {lang}", "voice": "onyx", "language": lang, "speed": 1.0})
        assert r.status_code == 200, f"{lang}: {r.status_code} {r.text}"
        assert r.json().get("key")

    def test_tts_empty_text_400(self, s):
        r = s.post(f"{BASE_URL}/api/voice/tts", headers=HEADERS,
                   json={"text": "", "voice": "onyx", "language": "sk"})
        assert r.status_code == 400, r.text

    def test_tts_empty_after_clean_400(self, s):
        # whitespace/markdown-only text becomes empty after clean_for_tts
        r = s.post(f"{BASE_URL}/api/voice/tts", headers=HEADERS,
                   json={"text": "   ", "voice": "onyx", "language": "sk"})
        assert r.status_code == 400, r.text

    def test_tts_unauth_401(self, s):
        r = s.post(f"{BASE_URL}/api/voice/tts",
                   headers={"Content-Type": "application/json"},
                   json={"text": "hello", "voice": "onyx", "language": "en"})
        assert r.status_code == 401, r.text

    def test_tts_stream_missing_key_404(self, s):
        r = s.get(f"{BASE_URL}/api/voice/tts/deadbeefdeadbeef.mp3")
        assert r.status_code == 404, r.text


# ---------- Regressions ----------
class TestRegression:
    def test_auth_me_ok(self, s):
        r = s.get(f"{BASE_URL}/api/auth/me", headers=HEADERS)
        assert r.status_code == 200
        assert (r.json().get("user") or {}).get("user_id") == "smoketest-user-1"

    def test_legal_tos_ok(self, s):
        r = s.get(f"{BASE_URL}/api/legal/tos", headers=HEADERS)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "version" in data or "text" in data or "content" in data or "html" in data

    def test_healing_state_ok(self, s):
        r = s.get(f"{BASE_URL}/api/healing/state", headers=HEADERS)
        assert r.status_code == 200, r.text

    def test_agent_chat_ok(self, s):
        r = s.post(f"{BASE_URL}/api/agent/chat", headers=HEADERS,
                   json={"message": "Ahoj Jarvis, si tam?", "language": "sk"},
                   timeout=60)
        assert r.status_code == 200, r.text
        # Should return some kind of assistant text
        body = r.json()
        assert any(k in body for k in ("reply", "message", "text", "response", "answer"))
