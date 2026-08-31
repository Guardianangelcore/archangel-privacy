"""
Iteration 32 — Sovereign UX Extensions backend contract tests
Covers:
  - /api/family/voice-signature/circle (new): family circle members + voice-print status
Regression:
  - /api/ocr/document still returns birth_year_detected + birth_year_applied
  - /api/voice/tts still 200 with onyx

NOTE: We use pymongo (sync) to seed/reset user fields and guardian links between
assertions, per main-agent instructions. We do NOT touch iteration 30/31 tests.
"""
from __future__ import annotations
import os
import io
import time
import uuid
import pytest
import requests
from datetime import datetime, timezone
from pymongo import MongoClient

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://guardian-vault-13.preview.emergentagent.com").rstrip("/")
TOKEN = "smoketok-fresh-2026"           # smoketest-user-1
TOKEN2 = "smoketok-fresh-2026-u2"       # smoketest-user-2
UID = "smoketest-user-1"
UID2 = "smoketest-user-2"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "guardian_health")

@pytest.fixture(scope="session")
def db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {TOKEN}"})
    return s


def _get(path: str, token: str | None = TOKEN):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.get(f"{BASE_URL}{path}", headers=h, timeout=30)


# --- VOICE CIRCLE ------------------------------------------------------------
class TestVoiceCircle:

    def test_no_auth_401(self):
        r = _get("/api/family/voice-signature/circle", token=None)
        assert r.status_code == 401, r.text

    def test_shape_and_self_is_present(self, api):
        r = api.get(f"{BASE_URL}/api/family/voice-signature/circle")
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("members", "recorded", "total"):
            assert k in d
        assert isinstance(d["members"], list)
        assert d["total"] == len(d["members"])
        # Caller must always be in the list with is_self=True
        selves = [m for m in d["members"] if m.get("is_self")]
        assert len(selves) == 1, selves
        self_row = selves[0]
        assert self_row["user_id"] == UID
        # Row shape
        for m in d["members"]:
            for f in ("user_id", "name", "email", "is_self", "has_signature", "label", "recorded_at"):
                assert f in m, f"circle row missing {f}: {m}"
            assert isinstance(m["is_self"], bool)
            assert isinstance(m["has_signature"], bool)

    def test_guardian_link_shows_other_user_in_circle(self, api, db):
        # Ensure both users exist
        assert db.users.find_one({"user_id": UID}), "smoketest-user-1 missing"
        assert db.users.find_one({"user_id": UID2}), "smoketest-user-2 missing"

        # A guardian link already exists (from iter30/31 fixtures). Verify the
        # circle surfaces the recipient. If no link yet, seed one and clean up.
        existing = db.guardians.find_one({
            "$or": [
                {"user_id": UID, "guardian_user_id": UID2},
                {"user_id": UID2, "guardian_user_id": UID},
            ]
        })
        seeded_marker = None
        if not existing:
            seeded_marker = f"iter32-link-{uuid.uuid4().hex[:8]}"
            db.guardians.insert_one({
                "link_id": seeded_marker,
                "user_id": UID,
                "guardian_user_id": UID2,
                "created_at": datetime.now(timezone.utc),
                "iter32_marker": True,
            })
        try:
            r = api.get(f"{BASE_URL}/api/family/voice-signature/circle")
            assert r.status_code == 200
            d = r.json()
            ids = {m["user_id"] for m in d["members"]}
            assert UID2 in ids, f"guardian recipient {UID2} not in circle: {ids}"
            # Guarantee at least self + recipient
            assert d["total"] >= 2
        finally:
            if seeded_marker:
                db.guardians.delete_one({"link_id": seeded_marker})

    def test_recorded_count_increments_after_voice_signature_upload(self, api, db):
        # Snapshot baseline
        r0 = api.get(f"{BASE_URL}/api/family/voice-signature/circle")
        assert r0.status_code == 200
        d0 = r0.json()
        self0 = next(m for m in d0["members"] if m["is_self"])
        # Baseline: whether self already has a signature (should not, iter31 deleted it in teardown, but be safe)
        prior_recorded = d0["recorded"]
        prior_has = self0["has_signature"]

        # Upload a small voice signature for self
        audio_bytes = b"RIFF" + b"\x00" * 2048  # dummy 2KB payload; endpoint only checks size bounds
        files = {"file": ("test_iter32.webm", io.BytesIO(audio_bytes), "audio/webm")}
        data = {"label": "Iter32Test"}
        up = requests.post(
            f"{BASE_URL}/api/family/voice-signature",
            headers={"Authorization": f"Bearer {TOKEN}"},
            files=files, data=data, timeout=30,
        )
        assert up.status_code == 200, up.text
        try:
            r1 = api.get(f"{BASE_URL}/api/family/voice-signature/circle")
            assert r1.status_code == 200
            d1 = r1.json()
            self1 = next(m for m in d1["members"] if m["is_self"])
            assert self1["has_signature"] is True, self1
            assert self1["label"] == "Iter32Test", self1
            # If self was previously not recorded, recorded should have incremented by exactly 1
            if not prior_has:
                assert d1["recorded"] == prior_recorded + 1, (prior_recorded, d1["recorded"])
        finally:
            # Cleanup uploaded signature (matches iter31 teardown behavior)
            requests.delete(
                f"{BASE_URL}/api/family/voice-signature",
                headers={"Authorization": f"Bearer {TOKEN}"},
                timeout=30,
            )


# --- REGRESSION --------------------------------------------------------------
class TestRegression:

    def test_ocr_endpoint_still_returns_birth_year_fields(self, api, db):
        """Trigger OCR on an existing vault document and verify the response
        still includes birth_year_detected + birth_year_applied fields
        (per iter31 contract)."""
        # Pick any existing vault document for smoketest-user-1
        doc = db.documents.find_one({"user_id": UID}, {"_id": 0, "doc_id": 1})
        if not doc or not doc.get("doc_id"):
            pytest.skip("No vault document available for OCR regression test")
        doc_id = doc["doc_id"]
        r = requests.post(
            f"{BASE_URL}/api/vault/documents/{doc_id}/ocr",
            headers={"Authorization": f"Bearer {TOKEN}"},
            timeout=90,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "birth_year_detected" in body, list(body.keys())
        # birth_year_applied is only returned on fresh OCR path (not cached).
        # Per iter31 spec, cached responses only return birth_year_detected (null).
        if not body.get("cached"):
            assert "birth_year_applied" in body, list(body.keys())

    def test_voice_tts_onyx_still_works(self):
        r = requests.post(
            f"{BASE_URL}/api/voice/tts",
            headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
            json={"text": "Iter32 tts regression check.", "voice": "onyx"}, timeout=60,
        )
        assert r.status_code == 200, f"TTS regression failed: {r.status_code} {r.text[:200]}"
        # /voice/tts returns a JSON pointer {key, url} to the cached mp3 (per app design)
        try:
            body = r.json()
        except Exception:
            # Or raw audio bytes (older contract) — both are acceptable
            assert len(r.content) > 500, f"TTS returned tiny payload: {len(r.content)}"
            return
        assert isinstance(body, dict)
        assert "key" in body or "url" in body, body
