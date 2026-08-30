# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
"""Phase 22: JARVIS 2.0 — THE SOUL ENGINE (self-teaching companion).

Covers non-LLM contracts: agent state & levels, XP awards (calibration,
med intake), anomaly detection, memories CRUD, transcribe validation.
LLM paths (chat / briefing / analyze / memory extraction) consume credits
and are validated manually + by the e2e testing agent."""
import os
import uuid
import requests

BASE_URL = (os.environ.get("EXPO_BACKEND_URL")
            or os.environ.get("EXPO_PUBLIC_BACKEND_URL")
            or "https://guardian-vault-13.preview.emergentagent.com").rstrip("/")
H1 = {"Authorization": "Bearer smoketok-fresh-2026"}
H2 = {"Authorization": "Bearer smoketok-fresh-2026-u2"}


def _get(path, h=H1):
    return requests.get(f"{BASE_URL}/api{path}", headers=h, timeout=30)

def _post(path, h=H1, json=None, **kw):
    return requests.post(f"{BASE_URL}/api{path}", headers=h, json=json, timeout=60, **kw)

def _delete(path, h=H1):
    return requests.delete(f"{BASE_URL}/api{path}", headers=h, timeout=30)


class TestAgentState:
    def test_state_shape_and_levels(self):
        r = _get("/agent/state", h=H2)
        assert r.status_code == 200, r.text
        st = r.json()
        assert 1 <= st["level"] <= 10
        assert st["level_name"]
        assert st["xp"] >= 0 and st["xp_next"] > 0
        assert 0 <= st["progress_pct"] <= 100
        assert len(st["abilities"]) == 10
        assert st["abilities"][0]["unlocked"] is True  # L1 always unlocked
        assert st["mood"] in ("calm", "thinking", "alert", "energetic", "concerned")

    def test_state_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/agent/state", timeout=30)
        assert r.status_code == 401


class TestXpEngine:
    def test_calibration_awards_10_xp(self):
        before = _get("/agent/state", h=H2).json()["xp"]
        r = _post("/bioscan/calibrate", h=H2, json={"heart_rate": 72})
        assert r.status_code == 200, r.text
        after = _get("/agent/state", h=H2).json()["xp"]
        assert after == before + 10

    def test_med_intake_awards_10_xp(self):
        rem = _post("/meds/reminders", h=H2, json={
            "name": f"XPTest-{uuid.uuid4().hex[:6]}", "dose": "1 tbl", "times": ["08:00"]}).json()
        before = _get("/agent/state", h=H2).json()["xp"]
        r = _post("/meds/intake", h=H2, json={"reminder_id": rem["reminder_id"], "time": "08:00"})
        assert r.status_code == 200, r.text
        after = _get("/agent/state", h=H2).json()["xp"]
        assert after == before + 10
        _delete(f"/meds/reminders/{rem['reminder_id']}", h=H2)

    def test_xp_events_logged(self):
        st = _get("/agent/state", h=H2).json()
        assert isinstance(st["recent_xp"], list) and len(st["recent_xp"]) >= 1
        assert st["recent_xp"][0]["amount"] > 0


class TestAnomalyWatch:
    def test_high_bp_triggers_alert(self):
        r = _post("/bioscan/calibrate", h=H2, json={"systolic": 168, "diastolic": 98})
        assert r.status_code == 200, r.text
        alerts = _get("/agent/anomalies", h=H2).json()["alerts"]
        kinds = [a["kind"] for a in alerts]
        assert "bp_critical" in kinds
        crit = next(a for a in alerts if a["kind"] == "bp_critical")
        assert crit["severity"] == "high"

    def test_normal_values_clear_critical(self):
        _post("/bioscan/calibrate", h=H2, json={"systolic": 122, "diastolic": 78})
        alerts = _get("/agent/anomalies", h=H2).json()["alerts"]
        assert "bp_critical" not in [a["kind"] for a in alerts]

    def test_low_glucose_alert(self):
        _post("/bioscan/calibrate", h=H2, json={"glucose_mmol": 3.1})
        alerts = _get("/agent/anomalies", h=H2).json()["alerts"]
        assert "glucose_low" in [a["kind"] for a in alerts]
        # restore a healthy value so other tests aren't affected
        _post("/bioscan/calibrate", h=H2, json={"glucose_mmol": 5.4, "systolic": 120, "diastolic": 76})

    def test_calibrate_validation(self):
        assert _post("/bioscan/calibrate", h=H2, json={}).status_code == 400
        assert _post("/bioscan/calibrate", h=H2, json={"systolic": 400, "diastolic": 90}).status_code == 400
        assert _post("/bioscan/calibrate", h=H2, json={"glucose_mmol": 55}).status_code == 400


class TestMemories:
    def test_list_memories(self):
        r = _get("/agent/memories", h=H2)
        assert r.status_code == 200
        assert isinstance(r.json()["memories"], list)

    def test_delete_unknown_404(self):
        r = _delete(f"/agent/memories/{uuid.uuid4().hex}", h=H2)
        assert r.status_code == 404


class TestTranscribe:
    def test_empty_audio_400(self):
        r = requests.post(f"{BASE_URL}/api/agent/transcribe", headers=H2,
                          files={"file": ("v.webm", b"", "audio/webm")}, timeout=30)
        assert r.status_code == 400

    def test_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/agent/transcribe",
                          files={"file": ("v.webm", b"x", "audio/webm")}, timeout=30)
        assert r.status_code == 401


class TestTtsEmotionalSpeed:
    def test_speed_param_accepted(self):
        r = _post("/voice/tts", h=H2, json={"text": "Dobré ráno, Jaroslav.", "voice": "nova", "speed": 1.08})
        assert r.status_code == 200, r.text
        assert r.json()["url"].startswith("/api/voice/tts/")
