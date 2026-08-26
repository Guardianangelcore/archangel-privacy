"""Phase 33 backend tests — Family voice recordings, Companion morning reminder, Sunday vault auto-report."""
import io
import os
import sys
import uuid
import asyncio
from datetime import datetime, timezone, timedelta

import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://angel-os-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SENIOR_TOKEN = "test-token-abc"      # user_test123 / test@example.com (recipient)
FAMILY_TOKEN = "fam-token-abc"       # user_family1 / lucka@example.com (guardian of senior)

H_SENIOR = {"Authorization": f"Bearer {SENIOR_TOKEN}"}
H_FAMILY = {"Authorization": f"Bearer {FAMILY_TOKEN}"}

# fake WAV-ish bytes ~2KB
AUDIO_BYTES = b"RIFF" + b"\x00" * 2000 + b"WAVEfmt "
AUDIO_LEN = len(AUDIO_BYTES)


# --------------------- FEATURE: POST /family/echoes/audio ---------------------
class TestEchoAudioUpload:
    def test_self_upload_audio(self):
        files = {"file": ("me.m4a", io.BytesIO(AUDIO_BYTES), "audio/m4a")}
        r = requests.post(f"{API}/family/echoes/audio", headers=H_SENIOR,
                          files=files, data={"from_name": "Ja"})
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["ok"] is True
        echo = j["echo"]
        assert echo["audio"] is True
        assert echo["remote"] is False
        assert echo["size"] == AUDIO_LEN
        assert echo["user_id"] == "user_test123"
        pytest.self_echo_id = echo["echo_id"]

    def test_remote_upload_as_guardian(self):
        files = {"file": ("rem.m4a", io.BytesIO(AUDIO_BYTES), "audio/m4a")}
        r = requests.post(f"{API}/family/echoes/audio", headers=H_FAMILY,
                          files=files,
                          data={"from_name": "Lucka", "to_email": "test@example.com"})
        assert r.status_code == 200, r.text
        j = r.json()
        echo = j["echo"]
        assert echo["audio"] is True
        assert echo["remote"] is True
        assert echo["user_id"] == "user_test123"          # recipient
        assert echo["sender_user_id"] == "user_family1"
        pytest.remote_echo_id = echo["echo_id"]

    def test_remote_upload_non_guardian_403(self):
        # senior tries to send an audio echo to family (not a guardian of Lucka)
        files = {"file": ("x.m4a", io.BytesIO(AUDIO_BYTES), "audio/m4a")}
        r = requests.post(f"{API}/family/echoes/audio", headers=H_SENIOR,
                          files=files,
                          data={"from_name": "X", "to_email": "lucka@example.com"})
        assert r.status_code == 403, r.text

    def test_empty_file_400(self):
        files = {"file": ("empty.m4a", io.BytesIO(b""), "audio/m4a")}
        r = requests.post(f"{API}/family/echoes/audio", headers=H_SENIOR,
                          files=files, data={"from_name": "Ja"})
        assert r.status_code == 400, r.text

    def test_unknown_recipient_404(self):
        files = {"file": ("x.m4a", io.BytesIO(AUDIO_BYTES), "audio/m4a")}
        r = requests.post(f"{API}/family/echoes/audio", headers=H_FAMILY,
                          files=files,
                          data={"from_name": "L", "to_email": "nobody-xyz-9999@example.com"})
        assert r.status_code == 404, r.text


# --------------------- FEATURE: GET /family/echoes/{id}/audio (stream/authz) ---------------------
class TestEchoAudioStream:
    @classmethod
    def setup_class(cls):
        # Upload a remote audio echo once for this class (works across xdist workers)
        files = {"file": ("stream.m4a", io.BytesIO(AUDIO_BYTES), "audio/m4a")}
        r = requests.post(f"{API}/family/echoes/audio", headers=H_FAMILY,
                          files=files,
                          data={"from_name": "Lucka", "to_email": "test@example.com"})
        assert r.status_code == 200, r.text
        cls.echo_id = r.json()["echo"]["echo_id"]

    def test_recipient_can_stream(self):
        r = requests.get(f"{API}/family/echoes/{self.echo_id}/audio", headers=H_SENIOR)
        assert r.status_code == 200, r.text
        assert len(r.content) == AUDIO_LEN
        assert "audio" in (r.headers.get("content-type") or "")

    def test_sender_can_stream(self):
        r = requests.get(f"{API}/family/echoes/{self.echo_id}/audio", headers=H_FAMILY)
        assert r.status_code == 200, r.text
        assert len(r.content) == AUDIO_LEN

    def test_token_query_param_works(self):
        r = requests.get(f"{API}/family/echoes/{self.echo_id}/audio?token={SENIOR_TOKEN}")
        assert r.status_code == 200, r.text
        assert len(r.content) == AUDIO_LEN

    def test_stranger_gets_404(self):
        r = requests.get(f"{API}/family/echoes/{self.echo_id}/audio",
                         headers={"Authorization": "Bearer no-such-token-xyz"})
        assert r.status_code in (401, 404), r.text

    def test_non_audio_echo_404(self):
        # create a plain text echo and try streaming its audio
        r = requests.post(f"{API}/family/echoes", headers={**H_SENIOR, "Content-Type": "application/json"},
                          json={"from_name": "T", "message": "plain text"})
        assert r.status_code == 200
        eid = r.json()["echo"]["echo_id"]
        r2 = requests.get(f"{API}/family/echoes/{eid}/audio", headers=H_SENIOR)
        assert r2.status_code == 404


# --------------------- FEATURE: POST /companion/remind-sweep ---------------------
class TestCompanionRemindSweep:
    """Use a FRESH user (main agent already exercised today's rows for test/family tokens)."""

    fresh_uid = f"user_phase33_{uuid.uuid4().hex[:8]}"
    fresh_token = f"tok_phase33_{uuid.uuid4().hex[:10]}"

    @classmethod
    def setup_class(cls):
        # Seed a fresh angel_mode user + session directly in Mongo via a small helper endpoint?
        # Not available — use pymongo directly.
        sys.path.insert(0, "/app/backend")
        from pymongo import MongoClient
        cli = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        db = cli[os.environ.get("DB_NAME", "guardian_health")]
        now = datetime.now(timezone.utc)
        db.users.insert_one({
            "user_id": cls.fresh_uid, "email": f"{cls.fresh_uid}@example.com",
            "did": f"did:guardian:{cls.fresh_uid[-12:]}", "name": "Phase33 Fresh",
            "language": "sk", "angel_mode": True, "created_at": now,
        })
        db.user_sessions.insert_one({
            "session_token": cls.fresh_token, "user_id": cls.fresh_uid,
            "created_at": now, "expires_at": now + timedelta(days=7),
        })
        # Ensure no checkin today, no reminder today
        db.companion_checkins.delete_many({"user_id": cls.fresh_uid})
        db.companion_reminders.delete_many({"user_id": cls.fresh_uid})
        cls._db = db

    @classmethod
    def teardown_class(cls):
        cls._db.users.delete_one({"user_id": cls.fresh_uid})
        cls._db.user_sessions.delete_one({"session_token": cls.fresh_token})
        cls._db.companion_reminders.delete_many({"user_id": cls.fresh_uid})

    def test_remind_sweep_counts_fresh_user(self):
        r = requests.post(f"{API}/companion/remind-sweep",
                          headers={"Authorization": f"Bearer {self.fresh_token}"})
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["ok"] is True
        # >=1 because our fresh angel-mode user has no checkin today
        assert j["reminders_sent"] >= 1
        # verify db row
        today = datetime.now(timezone.utc).date().isoformat()
        row = self._db.companion_reminders.find_one({"user_id": self.fresh_uid, "date": today})
        assert row is not None

    def test_remind_sweep_dedup(self):
        # Second call must not re-count our fresh user (dedup per day)
        # Count reminders for fresh_uid before/after should stay the same
        today = datetime.now(timezone.utc).date().isoformat()
        before = self._db.companion_reminders.count_documents({"user_id": self.fresh_uid, "date": today})
        r = requests.post(f"{API}/companion/remind-sweep",
                          headers={"Authorization": f"Bearer {self.fresh_token}"})
        assert r.status_code == 200
        after = self._db.companion_reminders.count_documents({"user_id": self.fresh_uid, "date": today})
        assert after == before, "dedup broken — reminder inserted twice"

    def test_checked_in_user_skipped(self):
        # Insert a checkin for fresh user, wipe today's reminder, call sweep — should NOT create new one
        today = datetime.now(timezone.utc).date().isoformat()
        self._db.companion_checkins.insert_one({
            "checkin_id": uuid.uuid4().hex, "user_id": self.fresh_uid,
            "mood": 4, "mood_label": "dobre", "note": "", "topic": "sleep",
            "created_at": datetime.now(timezone.utc),
        })
        self._db.companion_reminders.delete_many({"user_id": self.fresh_uid, "date": today})
        r = requests.post(f"{API}/companion/remind-sweep",
                          headers={"Authorization": f"Bearer {self.fresh_token}"})
        assert r.status_code == 200
        exists = self._db.companion_reminders.find_one({"user_id": self.fresh_uid, "date": today})
        assert exists is None, "user with checkin today must NOT get a reminder"
        # cleanup
        self._db.companion_checkins.delete_many({"user_id": self.fresh_uid})


# --------------------- FEATURE: POST /healing/report/save-to-vault ---------------------
class TestHealingReportToVault:
    def test_save_to_vault_and_visible_in_documents(self):
        r = requests.post(f"{API}/healing/report/save-to-vault", headers=H_SENIOR)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["ok"] is True
        doc = j["document"]
        assert doc["source"] == "healing_report"
        assert doc["content_type"] == "application/pdf"
        assert doc["size"] > 100
        doc_id = doc["doc_id"]

        # Visible in vault list
        r2 = requests.get(f"{API}/vault/documents", headers=H_SENIOR)
        assert r2.status_code == 200
        payload = r2.json()
        docs = payload if isinstance(payload, list) else (payload.get("documents") or [])
        assert any(d.get("doc_id") == doc_id for d in docs), "saved healing report not in vault list"

        # /file endpoint streams the PDF
        r3 = requests.get(f"{API}/vault/documents/{doc_id}/file", headers=H_SENIOR)
        assert r3.status_code == 200, r3.text
        assert r3.content.startswith(b"%PDF"), "content is not a PDF"

        # calendar_events entry exists (via Mongo)
        from pymongo import MongoClient
        cli = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        db = cli[os.environ.get("DB_NAME", "guardian_health")]
        ev = db.calendar_events.find_one({"doc_id": doc_id})
        assert ev is not None
        assert ev.get("source") == "healing_report"


# --------------------- FEATURE: weekly_report_sweep + swarm agents registration ---------------------
class TestSwarmSweep:
    def test_weekly_sweep_direct_saves_once_per_week(self):
        """Direct in-process call — the module owns db access."""
        sys.path.insert(0, "/app/backend")
        from routes.healing import weekly_report_sweep
        loop = asyncio.new_event_loop()
        try:
            first = loop.run_until_complete(weekly_report_sweep(force=True))
            second = loop.run_until_complete(weekly_report_sweep(force=True))
        finally:
            loop.close()
        # first can be 0 if main agent already ran it this week — but second MUST be 0 (dedup)
        assert second == 0, f"weekly sweep dedup broken — 2nd call saved {second}"

    def test_companion_care_and_weekly_reporter_agents_registered(self):
        r = requests.get(f"{API}/swarm/status", headers=H_SENIOR)
        assert r.status_code == 200
        agents = {a["agent_id"]: a for a in (r.json().get("agents") or [])}
        # Wait up to 30 s for the loop to tick both agents in
        deadline = datetime.now(timezone.utc) + timedelta(seconds=30)
        while ("companion_care" not in agents or "weekly_reporter" not in agents) and datetime.now(timezone.utc) < deadline:
            import time as _t; _t.sleep(3)
            r = requests.get(f"{API}/swarm/status", headers=H_SENIOR)
            agents = {a["agent_id"]: a for a in (r.json().get("agents") or [])}
        assert "companion_care" in agents, "companion_care agent not registered in swarm"
        assert "weekly_reporter" in agents, "weekly_reporter agent not registered in swarm"
        assert agents["companion_care"].get("last_run")
        assert agents["weekly_reporter"].get("last_run")
