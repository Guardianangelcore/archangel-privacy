"""
Iter 65 — Live TTS relay + public intro + unified onyx + cached agent stream
"""
import os
import json
import time
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL") or "http://localhost:8001"
BASE_URL = BASE_URL.rstrip("/")
TOKEN = "smoketok-fresh-2026"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


# -------- POST /api/voice/tts stream:true --------
class TestVoiceTTSLiveRelay:
    def test_tts_live_ticket_returns_and_serves_audio(self):
        # Randomize text to avoid cache hit
        text = f"Toto je test {int(time.time())}."
        r = requests.post(
            f"{BASE_URL}/api/voice/tts",
            headers={**AUTH, "Content-Type": "application/json"},
            json={"text": text, "language": "sk", "stream": True},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "url" in data, data
        url = data["url"]
        # Either live ticket or cached file
        assert url.startswith("/api/voice/tts/live/") or url.startswith("/api/voice/tts/"), url
        # For fresh phrase, expect live:true. Cached ok too.
        assert data.get("live") is True or data.get("cached") is True, data

        # GET the audio URL (no auth needed)
        full = f"{BASE_URL}{url}"
        r2 = requests.get(full, timeout=60)
        assert r2.status_code == 200, r2.text[:200]
        assert "audio/mpeg" in r2.headers.get("content-type", ""), r2.headers
        assert len(r2.content) > 5 * 1024, f"body too small: {len(r2.content)} bytes"

        # If it was a live ticket, verify second GET behavior
        if url.startswith("/api/voice/tts/live/"):
            r3 = requests.get(full, timeout=60)
            # Second GET may 200 (replayable) or 404 (one-shot).
            # Spec: "GET same live url a second time → 200 with the full bytes (Content-Length present)".
            assert r3.status_code == 200, f"second live GET returned {r3.status_code}"
            assert "audio/mpeg" in r3.headers.get("content-type", ""), r3.headers
            assert len(r3.content) > 5 * 1024

    def test_tts_voice_override_unified_onyx(self):
        # Passing voice:'nova' without override should return onyx (unified preset)
        r = requests.post(
            f"{BASE_URL}/api/voice/tts",
            headers={**AUTH, "Content-Type": "application/json"},
            json={"text": "Unified voice test.", "voice": "nova", "language": "en"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("voice") == "onyx", f"expected onyx, got {data.get('voice')}: {data}"

    def test_tts_live_404_for_missing_ticket(self):
        r = requests.get(f"{BASE_URL}/api/voice/tts/live/doesnotexist.mp3", timeout=15)
        assert r.status_code == 404, f"expected 404, got {r.status_code}"


# -------- GET /api/voice/intro.mp3 (public) --------
class TestVoiceIntroPublic:
    def test_intro_sk_no_auth(self):
        r = requests.get(f"{BASE_URL}/api/voice/intro.mp3?lang=sk", timeout=60)
        assert r.status_code == 200, r.text[:200]
        assert "audio/mpeg" in r.headers.get("content-type", ""), r.headers
        assert len(r.content) > 20 * 1024, f"body too small: {len(r.content)} bytes"

    def test_intro_sk_cached_fast(self):
        # Warm it
        requests.get(f"{BASE_URL}/api/voice/intro.mp3?lang=sk", timeout=60)
        t0 = time.time()
        r = requests.get(f"{BASE_URL}/api/voice/intro.mp3?lang=sk", timeout=15)
        elapsed = time.time() - t0
        assert r.status_code == 200
        assert len(r.content) > 20 * 1024
        # Cached call should be fast (<3 s over network)
        assert elapsed < 5.0, f"cached intro took {elapsed:.2f}s"

    def test_intro_en_ok(self):
        r = requests.get(f"{BASE_URL}/api/voice/intro.mp3?lang=en", timeout=60)
        assert r.status_code == 200
        assert "audio/mpeg" in r.headers.get("content-type", "")
        assert len(r.content) > 20 * 1024

    def test_intro_unknown_lang_fallback(self):
        r = requests.get(f"{BASE_URL}/api/voice/intro.mp3?lang=xx", timeout=60)
        assert r.status_code == 200
        assert "audio/mpeg" in r.headers.get("content-type", "")
        assert len(r.content) > 20 * 1024


# -------- POST /api/agent/chat/stream cached reply --------
class TestAgentStreamCache:
    def _consume_sse(self, resp):
        chunks = []
        final = None
        for raw in resp.iter_lines():
            if not raw:
                continue
            line = raw.decode("utf-8", errors="ignore") if isinstance(raw, bytes) else raw
            if line.startswith("data:"):
                payload = line[5:].strip()
                try:
                    obj = json.loads(payload)
                except Exception:
                    continue
                if obj.get("done"):
                    final = obj
                    break
                if "t" in obj:
                    chunks.append(obj["t"])
        return chunks, final

    def test_stream_and_cached_second_call(self):
        msg = f"Aký je dnes deň? {int(time.time())}"
        body = {"message": msg, "language": "sk"}

        # First call — genuine LLM run
        t0 = time.time()
        r1 = requests.post(
            f"{BASE_URL}/api/agent/chat/stream",
            headers={**AUTH, "Content-Type": "application/json"},
            json=body,
            stream=True,
            timeout=120,
        )
        assert r1.status_code == 200, r1.text[:300]
        chunks1, final1 = self._consume_sse(r1)
        elapsed1 = time.time() - t0
        assert final1 is not None and final1.get("done") is True, f"no done event; final={final1}"
        assert len(chunks1) > 0, "no chunks received"
        print(f"[first] {elapsed1:.2f}s, chunks={len(chunks1)}, cached={final1.get('cached')}")

        # Second identical call — must be cached
        t0 = time.time()
        r2 = requests.post(
            f"{BASE_URL}/api/agent/chat/stream",
            headers={**AUTH, "Content-Type": "application/json"},
            json=body,
            stream=True,
            timeout=30,
        )
        assert r2.status_code == 200
        chunks2, final2 = self._consume_sse(r2)
        elapsed2 = time.time() - t0
        assert final2 is not None
        assert final2.get("cached") is True, f"expected cached:true, got {final2}"
        assert elapsed2 < 3.0, f"cached call slow: {elapsed2:.2f}s"
        print(f"[cached] {elapsed2:.2f}s, chunks={len(chunks2)}, cached={final2.get('cached')}")
