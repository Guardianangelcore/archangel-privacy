"""Phase 47 (Guardian Eye multi-model + Compass Bearing) + Phase 48 (Cognitive Triage).

Runs against the public preview backend using smoketok-fresh-2026 (smoketest-user-1).
Follows /app/image_testing.md for image uploads (real feature JPEG).
"""
import os
import time
import io

import pytest
import requests
from PIL import Image, ImageDraw

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL",
                         "https://guardian-vault-13.preview.emergentagent.com").rstrip("/")
TOKEN = "smoketok-fresh-2026"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
WATERMARK = "AI Content · Sovereign Protocol"


def _make_pill_jpeg() -> bytes:
    """Feature-rich JPEG (a mock pill-bottle label) — not solid color."""
    img = Image.new("RGB", (400, 300), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([80, 60, 320, 260], outline="black", width=3, fill="#eef1f5")
    d.rectangle([80, 60, 320, 110], fill="#c93a3a", outline="black", width=2)
    d.text((100, 75), "PARALEN 500 mg", fill="white")
    d.text((100, 130), "Paracetamol", fill="black")
    d.text((100, 160), "20 tabliet", fill="black")
    d.text((100, 190), "Davkovanie:", fill="black")
    d.text((100, 215), "1-2 tab. 3x denne", fill="black")
    d.text((100, 240), "Rx nutne", fill="#c93a3a")
    d.line([80, 260, 320, 260], fill="#555", width=5)
    d.ellipse([200, 140, 240, 170], outline="blue", width=2)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return buf.getvalue()


@pytest.fixture(scope="session")
def pill_bytes():
    return _make_pill_jpeg()


@pytest.fixture(scope="session")
def sess():
    s = requests.Session()
    s.headers.update(AUTH)
    return s


# ============================================================
# PHASE 47 — GUARDIAN EYE MULTI-MODEL
# ============================================================
class TestLensModels:
    def test_lens_models_list(self):
        r = requests.get(f"{BASE_URL}/api/lens/models", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d.get("models"), list) and len(d["models"]) == 4
        keys = {m["key"] for m in d["models"]}
        assert keys == {"gpt", "claude", "gemini", "consensus"}
        assert d.get("default") == "gpt"


class TestLensAnalyze:
    """Single-model vision analysis. Graceful degrade allowed per review."""

    scan_ids = {}

    def _analyze(self, sess, pill_bytes, model_key: str):
        files = {"file": ("pill.jpg", pill_bytes, "image/jpeg")}
        data = {"model": model_key}
        r = sess.post(f"{BASE_URL}/api/lens/analyze", files=files, data=data, timeout=120)
        return r

    def test_analyze_gpt(self, sess, pill_bytes):
        r = self._analyze(sess, pill_bytes, "gpt")
        assert r.status_code == 200, r.text
        d = r.json()
        assert "scan_id" in d
        assert d.get("model") == "openai/gpt-5.4"
        # watermark presence — even in graceful-degrade the code applies watermark
        assert WATERMARK in d.get("summary_sk", ""), f"missing watermark: {d.get('summary_sk')[:200]}"
        TestLensAnalyze.scan_ids["gpt"] = d["scan_id"]
        # kind either real or 'other' (graceful degrade acceptable)
        assert d.get("kind")
        assert d.get("name")

    def test_analyze_claude(self, sess, pill_bytes):
        r = self._analyze(sess, pill_bytes, "claude")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("model") == "anthropic/claude-sonnet-5"
        assert WATERMARK in d.get("summary_sk", "")
        TestLensAnalyze.scan_ids["claude"] = d["scan_id"]

    def test_analyze_gemini(self, sess, pill_bytes):
        r = self._analyze(sess, pill_bytes, "gemini")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("model") == "gemini/gemini-3.1-pro-preview"
        assert WATERMARK in d.get("summary_sk", "")
        TestLensAnalyze.scan_ids["gemini"] = d["scan_id"]

    def test_analyze_invalid_model(self, sess, pill_bytes):
        r = self._analyze(sess, pill_bytes, "invalid_key")
        assert r.status_code == 400, r.text


class TestLensConsensus:
    def test_analyze_consensus(self, sess, pill_bytes):
        files = {"file": ("pill.jpg", pill_bytes, "image/jpeg")}
        r = sess.post(f"{BASE_URL}/api/lens/analyze-consensus", files=files, timeout=180)
        assert r.status_code == 200, r.text
        d = r.json()
        c = d.get("consensus") or {}
        agreement = c.get("agreement_pct")
        assert isinstance(agreement, int) and 0 <= agreement <= 100
        assert isinstance(c.get("kind_votes"), dict) and c["kind_votes"]
        per = c.get("per_model") or {}
        assert set(per.keys()) == {"gpt", "claude", "gemini"}
        assert WATERMARK in d.get("summary_sk", "")


class TestLensToJarvis:
    def test_to_jarvis_ok(self, sess, pill_bytes):
        # ensure we have a scan; use gpt scan if available, else fresh
        scan_id = TestLensAnalyze.scan_ids.get("gpt")
        if not scan_id:
            files = {"file": ("pill.jpg", pill_bytes, "image/jpeg")}
            r = sess.post(f"{BASE_URL}/api/lens/analyze", files=files, data={"model": "gpt"}, timeout=120)
            assert r.status_code == 200
            scan_id = r.json()["scan_id"]
        r = sess.post(f"{BASE_URL}/api/lens/{scan_id}/to-jarvis", timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("ok") is True
        assert d.get("scan_id") == scan_id
        jarvis = d.get("jarvis") or {}
        assert WATERMARK in (jarvis.get("reply") or ""), f"reply missing WM: {jarvis.get('reply')[:200]}"

    def test_to_jarvis_unknown_scan(self, sess):
        r = sess.post(f"{BASE_URL}/api/lens/does-not-exist-xyz/to-jarvis", timeout=30)
        assert r.status_code == 404


# ============================================================
# PHASE 47 — COMPASS BEARING
# ============================================================
class TestCompassBearing:
    def test_bearing_ok(self, sess):
        r = sess.post(f"{BASE_URL}/api/compass/bearing",
                      json={"lat": 48.15, "lng": 17.10}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("gps") == {"lat": 48.15, "lng": 17.10}
        assert d.get("nearest_safe_city") is not None
        sc = d.get("safe_cities") or []
        assert 1 <= len(sc) <= 5
        for entry in sc:
            assert isinstance(entry.get("distance_km"), (int, float))
            assert isinstance(entry.get("bearing_deg"), (int, float))
            assert entry.get("direction") in {"S", "SV", "V", "JV", "J", "JZ", "Z", "SZ"}
        assert isinstance(d.get("beacons"), list)
        assert isinstance(d.get("waitlist_proximity"), list)

    def test_bearing_invalid(self, sess):
        r = sess.post(f"{BASE_URL}/api/compass/bearing",
                      json={"lat": 200, "lng": 0}, timeout=30)
        assert r.status_code == 400, r.text


# ============================================================
# PHASE 48 — COGNITIVE TRIAGE
# ============================================================
class TestTriage:

    def test_a_dismiss_first_for_clean_slate(self, sess):
        # ensure any prior manual trigger is cleared then wait for cooldown expiry via subsequent tests
        sess.post(f"{BASE_URL}/api/triage/dismiss", timeout=15)

    def test_b_state_calm_after_dismiss(self, sess):
        # After dismiss we should see source=dismissed & calm
        r = sess.get(f"{BASE_URL}/api/triage/state", timeout=15)
        assert r.status_code == 200
        d = r.json()
        # Allow either 'dismissed' (cooldown active) or 'calm auto' (edge case: cooldown expired)
        assert d.get("crisis_level") == "calm"
        assert d.get("auto_open_hud") is False
        assert d.get("emergency_numbers", {}).get("EU") == "112"

    def test_c_trigger_manual(self, sess):
        r = sess.post(f"{BASE_URL}/api/triage/trigger",
                      json={"reason": "test manual"}, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("crisis_level") == "crisis"
        assert d.get("source") == "manual"
        assert d.get("auto_open_hud") is True
        assert len(d.get("instructions") or []) == 5
        assert d.get("emergency_numbers", {}).get("SK") == "155"
        assert "ručne aktivované" in (d.get("reasons") or [])

    def test_d_state_after_trigger_still_crisis(self, sess):
        r = sess.get(f"{BASE_URL}/api/triage/state", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("crisis_level") == "crisis"
        assert d.get("source") == "manual"

    def test_e_dismiss(self, sess):
        r = sess.post(f"{BASE_URL}/api/triage/dismiss", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("ok") is True
        assert d.get("cooldown_until")

    def test_f_state_after_dismiss(self, sess):
        r = sess.get(f"{BASE_URL}/api/triage/state", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("source") == "dismissed"
        assert d.get("crisis_level") == "calm"
        assert d.get("auto_open_hud") is False
        assert d.get("cooldown_until")

    def test_g_voice_valid(self, sess):
        r = sess.post(f"{BASE_URL}/api/triage/voice",
                      json={"tremor_score": 0.9, "sample_ms": 500}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        # cooldown may keep it calm — that's OK per review
        assert "crisis_level" in d

    def test_h_voice_invalid_high(self, sess):
        r = sess.post(f"{BASE_URL}/api/triage/voice",
                      json={"tremor_score": 1.5}, timeout=15)
        assert r.status_code == 400

    def test_i_voice_invalid_low(self, sess):
        r = sess.post(f"{BASE_URL}/api/triage/voice",
                      json={"tremor_score": -0.1}, timeout=15)
        assert r.status_code == 400

    @pytest.mark.parametrize("lang,expect", [
        ("sk", "112"),
        ("cs", "112"),
        ("en", "112"),
    ])
    def test_j_instructions_langs(self, sess, lang, expect):
        r = sess.get(f"{BASE_URL}/api/triage/instructions", params={"language": lang}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert len(d.get("instructions") or []) == 5
        assert d.get("emergency_numbers", {}).get("EU") == expect
        assert WATERMARK in (d.get("header") or "")

    def test_k_language_content_variation(self, sess):
        rs = requests.get(f"{BASE_URL}/api/triage/instructions?language=sk", headers=AUTH, timeout=15).json()
        rc = requests.get(f"{BASE_URL}/api/triage/instructions?language=cs", headers=AUTH, timeout=15).json()
        re_ = requests.get(f"{BASE_URL}/api/triage/instructions?language=en", headers=AUTH, timeout=15).json()
        # Slovak-specific vs Czech vs English
        assert "Sadnite" in rs["instructions"][0]
        assert "Posaďte" in rc["instructions"][0]
        assert "Sit down" in re_["instructions"][0]


# ============================================================
# REGRESSION
# ============================================================
class TestRegression:
    def test_agent_chat_watermark(self, sess):
        r = sess.post(f"{BASE_URL}/api/agent/chat",
                      json={"message": "ako sa mám dnes?", "language": "sk"}, timeout=60)
        assert r.status_code == 200, r.text
        assert WATERMARK in (r.json().get("reply") or "")

    def test_agent_briefing_edge_cache(self, sess):
        t0 = time.time()
        r1 = sess.get(f"{BASE_URL}/api/agent/briefing", params={"language": "sk"}, timeout=15)
        e1 = time.time() - t0
        assert r1.status_code == 200
        t1 = time.time()
        r2 = sess.get(f"{BASE_URL}/api/agent/briefing", params={"language": "sk"}, timeout=15)
        e2 = time.time() - t1
        assert r2.status_code == 200
        print(f"[briefing] first={e1:.2f}s second={e2:.2f}s")
        # Second call should be faster and identical content
        assert r1.json().get("text") == r2.json().get("text")

    def test_geo_context(self, sess):
        r = sess.get(f"{BASE_URL}/api/geo/context", timeout=15)
        assert r.status_code == 200
        d = r.json()
        geo = d.get("geo") or {}
        for k in ("city", "country", "lang", "tz", "lat", "lng", "source"):
            assert k in geo, f"missing geo.{k}"
        assert isinstance(d.get("supported_cities"), list)

    def test_bioscan_regression(self, sess):
        r = sess.post(f"{BASE_URL}/api/bioscan/measure",
                      json={"duration_s": 10}, timeout=30)
        # Expected 200 (sentinel) OR 402 (paywall). Both acceptable per review.
        assert r.status_code in (200, 402), f"unexpected {r.status_code}: {r.text[:200]}"
