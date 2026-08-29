# Phase 22 SOUL ENGINE — live LLM endpoint smoke (iteration 21)
# Focus: NEW gpt-5.4 flows requested by main agent.
import os, time, uuid, requests, pytest

BASE_URL = (os.environ.get("EXPO_BACKEND_URL")
            or os.environ.get("EXPO_PUBLIC_BACKEND_URL")
            or "https://global-compass-hub.preview.emergentagent.com").rstrip("/")
H = {"Authorization": "Bearer smoketok-fresh-2026"}


def _get(p, timeout=30):
    return requests.get(f"{BASE_URL}/api{p}", headers=H, timeout=timeout)

def _post(p, body=None, timeout=90):
    return requests.post(f"{BASE_URL}/api{p}", headers=H, json=body, timeout=timeout)

def _delete(p, timeout=15):
    return requests.delete(f"{BASE_URL}/api{p}", headers=H, timeout=timeout)


# --- agent state / abilities ---
class TestAgentState:
    def test_state_shape(self):
        r = _get("/agent/state")
        assert r.status_code == 200, r.text
        s = r.json()
        for k in ("level", "level_name", "xp", "xp_next", "progress_pct",
                  "abilities", "mood", "streak_days"):
            assert k in s, f"missing {k}"
        assert 1 <= s["level"] <= 10
        assert len(s["abilities"]) == 10
        assert s["mood"] in ("calm", "thinking", "alert", "energetic", "concerned")
        assert 0 <= s["progress_pct"] <= 100


# --- LIVE gpt-5.4 chat ---
class TestChatLive:
    def test_chat_slovak_reply(self):
        body = {"message": "Ahoj Jarvis, dnes ma bolí koleno", "language": "sk"}
        r = _post("/agent/chat", body, timeout=120)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("reply") and isinstance(j["reply"], str) and len(j["reply"]) > 5
        assert j.get("mood") in ("calm", "thinking", "alert", "energetic", "concerned")
        # xp_gained can be 0 if daily cap hit, but the KEY MUST exist
        assert "xp_gained" in j
        # Slovak-ish check (loose): expect at least one diacritic or common SK word
        low = j["reply"].lower()
        assert any(ch in low for ch in "áäčďéíĺľňóôŕšťúýž") or \
               any(w in low for w in (" je ", " sa ", " som ", " si ", " ma ", "koleno", "bolí"))


class TestMemories:
    def test_memory_extraction_eventual(self):
        # trigger chat with a strong memory-worthy fact
        _post("/agent/chat", {
            "message": "Mimochodom, mám rád ranné prechádzky v parku a beriem Concor 5mg.",
            "language": "sk"}, timeout=120)
        found = False
        mems = []
        for _ in range(3):
            time.sleep(6)
            r = _get("/agent/memories")
            if r.status_code == 200:
                mems = r.json().get("memories", [])
                if len(mems) >= 1:
                    found = True
                    break
        assert found, f"no memories extracted after ~18s: {mems!r}"
        # try delete first memory
        mid = mems[0].get("id") or mems[0].get("memory_id")
        if mid:
            d = _delete(f"/agent/memories/{mid}")
            assert d.status_code in (200, 204), d.text


class TestBriefing:
    def test_briefing_first_and_cache(self):
        r = _get("/agent/briefing", timeout=120)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("briefing") and isinstance(j["briefing"], str)
        assert "weather" in j
        assert "meds_today" in j
        assert "alerts" in j
        # second call same day → cached
        r2 = _get("/agent/briefing", timeout=60)
        assert r2.status_code == 200
        assert r2.json()["briefing"] == j["briefing"], "cache broken"


class TestDeepAnalyze:
    def test_analyze_steps_and_insight(self):
        r = _post("/agent/analyze", {}, timeout=120)
        assert r.status_code == 200, r.text
        j = r.json()
        assert isinstance(j.get("steps"), list) and len(j["steps"]) == 5
        assert j.get("insight") and isinstance(j["insight"], str)
        assert "xp_gained" in j  # can be 0 if consumed today


class TestAnomalyBP:
    def test_bp_elevated_then_clear(self):
        r = _post("/bioscan/calibrate", {"systolic": 150, "diastolic": 95})
        assert r.status_code == 200, r.text
        rec = r.json().get("record") or r.json()
        est = rec.get("bp_estimate") or rec.get("bp") or ""
        assert "150" in str(est) and "95" in str(est), f"bp_estimate mismatch: {rec}"
        alerts = _get("/agent/anomalies").json()["alerts"]
        kinds = [a["kind"] for a in alerts]
        assert any(k in kinds for k in ("bp_elevated", "bp_critical")), kinds
        # clear
        _post("/bioscan/calibrate", {"systolic": 120, "diastolic": 80})
        alerts2 = _get("/agent/anomalies").json()["alerts"]
        kinds2 = [a["kind"] for a in alerts2]
        assert "bp_elevated" not in kinds2 and "bp_critical" not in kinds2, kinds2


class TestTtsSpeed:
    def test_tts_with_speed(self):
        r = _post("/voice/tts", {"text": "Dobrý deň Jaroslav.", "voice": "nova", "speed": 1.08}, timeout=60)
        assert r.status_code == 200, r.text
        url = r.json()["url"]
        assert url.startswith("/api/voice/tts/")
        # stream it
        g = requests.get(f"{BASE_URL}{url}", headers=H, timeout=30)
        assert g.status_code == 200
        assert "audio" in g.headers.get("content-type", ""), g.headers


class TestPhysioGuides:
    def test_guides_have_video_urls(self):
        r = _get("/physio/guides?language=sk")
        assert r.status_code == 200, r.text
        guides = r.json().get("guides") or r.json()
        assert isinstance(guides, list) and len(guides) >= 3
        with_video = [g for g in guides if g.get("video_url")]
        assert with_video, f"no video_url in any guide: {guides[:2]}"
        assert any(".mp4" in (g.get("video_url") or "") for g in with_video)
