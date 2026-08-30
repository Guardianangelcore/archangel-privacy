"""
Iteration 33 backend tests — Sovereign Streaks + OCR cache branch consistency.

Covers:
  - GET /api/streaks/physio (auth, empty, tiers 1/2/3, gap, grace day, cutoff)
  - POST /api/vault/documents/{id}/ocr cached branch returns 4 keys
  - Regression: /api/achievements returns 8 badges; /api/voice/tts (onyx) works

Seeded rows are tagged {"seeded_test": True} for safe cleanup. Real user
physio_videos are left untouched.
"""
import os
from datetime import datetime, timezone, timedelta

import pytest
import requests
from pymongo import MongoClient

# Tests share the same seeded_test rows via an autouse cleanup fixture; running
# in parallel workers causes cross-test wipes. Force serial execution.
pytestmark = pytest.mark.xdist_group(name="iter33_streaks_serial")

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://global-compass-hub.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "guardian_health")

TOKEN = "smoketok-fresh-2026"
UID = "smoketest-user-1"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


@pytest.fixture
def clean_seeds(db):
    """Remove any seeded physio_videos before AND after (used only by streak tests)."""
    db.physio_videos.delete_many({"user_id": UID, "seeded_test": True})
    yield
    db.physio_videos.delete_many({"user_id": UID, "seeded_test": True})


def _seed(db, day_offsets):
    """Seed physio_videos with created_at at today-offset (UTC), tagged seeded_test."""
    now = datetime.now(timezone.utc)
    docs = []
    for off in day_offsets:
        d = now - timedelta(days=off)
        docs.append({
            "user_id": UID,
            "created_at": d,
            "seeded_test": True,
            "video_id": f"seed-{off}-{now.timestamp()}",
        })
    if docs:
        db.physio_videos.insert_many(docs)


# ---------------- STREAKS ----------------

class TestStreaksPhysio:
    @pytest.fixture(autouse=True)
    def _clean(self, clean_seeds):
        yield

    def test_no_auth_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/streaks/physio")
        assert r.status_code == 401, r.text

    def test_empty_returns_zero(self, db):
        # Also clear any REAL physio_videos temporarily by ensuring nothing seeded — but
        # user_1 could legitimately have real records. We can't wipe real data.
        # Instead, if real records exist, we skip and note. Check first.
        real_count = db.physio_videos.count_documents({"user_id": UID, "seeded_test": {"$ne": True}})
        if real_count > 0:
            pytest.skip(f"User has {real_count} real physio_videos — cannot test empty state without destroying user data")
        r = requests.get(f"{BASE_URL}/api/streaks/physio", headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        # API gained freeze_available/blazing_celebrated in iter33 — assert the core empty-state subset.
        assert data["current"] == 0 and data["best"] == 0 and data["tier"] == 0 and data["active_today"] is False, data

    def test_tier1_ember_4_consecutive(self, db):
        real_count = db.physio_videos.count_documents({"user_id": UID, "seeded_test": {"$ne": True}})
        _seed(db, [0, 1, 2, 3])
        r = requests.get(f"{BASE_URL}/api/streaks/physio", headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        if real_count == 0:
            assert data["current"] == 4, data
            assert data["tier"] == 1, data
            assert data["active_today"] is True
            assert data["best"] >= 4
        else:
            # Real data may extend streak; just assert basic tier logic still valid
            assert data["current"] >= 4
            assert data["active_today"] is True

    def test_tier2_golden_8_consecutive(self, db):
        real_count = db.physio_videos.count_documents({"user_id": UID, "seeded_test": {"$ne": True}})
        _seed(db, list(range(8)))
        r = requests.get(f"{BASE_URL}/api/streaks/physio", headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        if real_count == 0:
            assert data["current"] == 8, data
            assert data["tier"] == 2, data
            assert data["active_today"] is True
        else:
            assert data["current"] >= 8
            assert data["tier"] >= 2

    def test_tier3_blazing_30_plus(self, db):
        real_count = db.physio_videos.count_documents({"user_id": UID, "seeded_test": {"$ne": True}})
        _seed(db, list(range(32)))
        r = requests.get(f"{BASE_URL}/api/streaks/physio", headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        if real_count == 0:
            assert data["current"] == 32, data
            assert data["tier"] == 3, data
        else:
            assert data["tier"] == 3

    def test_gap_current_2_best_5(self, db):
        real_count = db.physio_videos.count_documents({"user_id": UID, "seeded_test": {"$ne": True}})
        if real_count > 0:
            pytest.skip("cannot verify gap semantics against real records")
        # today, today-1 (recent run = 2) then gap of 2 days (today-2 & today-3 missing)
        # then 5 consecutive: today-4, today-5, today-6, today-7, today-8
        _seed(db, [0, 1, 4, 5, 6, 7, 8])
        r = requests.get(f"{BASE_URL}/api/streaks/physio", headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        assert data["current"] == 2, data
        assert data["best"] == 5, data
        assert data["tier"] == 1
        assert data["active_today"] is True

    def test_grace_day_yesterday_only(self, db):
        real_count = db.physio_videos.count_documents({"user_id": UID, "seeded_test": {"$ne": True}})
        if real_count > 0:
            pytest.skip("cannot verify grace-day semantics against real records")
        _seed(db, [1])  # only yesterday
        r = requests.get(f"{BASE_URL}/api/streaks/physio", headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        assert data["current"] == 1, data
        assert data["active_today"] is False
        assert data["tier"] == 1

    def test_cutoff_ignores_older_than_60_days(self, db):
        real_count = db.physio_videos.count_documents({"user_id": UID, "seeded_test": {"$ne": True}})
        if real_count > 0:
            pytest.skip("cannot verify cutoff against real records")
        # seed one entry from 65 days ago; should be ignored → current=0
        _seed(db, [65, 70, 75])
        r = requests.get(f"{BASE_URL}/api/streaks/physio", headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        assert data["current"] == 0, data
        assert data["best"] == 0, data
        assert data["tier"] == 0


# ---------------- OCR cached branch ----------------

class TestOCRCachedBranch:
    def test_cached_ocr_returns_all_four_keys(self, db):
        # Find any existing document with extracted_text for smoketest-user-1
        doc = db.documents.find_one({"user_id": UID, "extracted_text": {"$exists": True, "$ne": ""}})
        cleanup_id = None
        if not doc:
            # Create a synthetic cached doc to test the cache path
            import uuid
            doc_id = uuid.uuid4().hex
            cleanup_id = doc_id
            db.documents.insert_one({
                "doc_id": doc_id,
                "user_id": UID,
                "title": "TEST_ocr_cache",
                "file_name": "test.pdf",
                "content_type": "application/pdf",
                "size": 100,
                "storage_path": "irrelevant",
                "extracted_text": "SYNTHETIC CACHED TEXT",
                "hash": "abc",
                "uploaded_at": datetime.now(timezone.utc),
            })
            doc = {"doc_id": doc_id, "extracted_text": "SYNTHETIC CACHED TEXT"}
        try:
            r = requests.post(f"{BASE_URL}/api/vault/documents/{doc['doc_id']}/ocr", headers=AUTH)
            assert r.status_code == 200, r.text
            data = r.json()
            # All 4 keys present
            assert set(data.keys()) >= {"extracted_text", "cached", "birth_year_detected", "birth_year_applied"}, data
            assert data["cached"] is True
            assert data["birth_year_detected"] is None
            assert data["birth_year_applied"] is False
            assert data["extracted_text"] == doc["extracted_text"]
        finally:
            if cleanup_id:
                db.documents.delete_one({"doc_id": cleanup_id})


# ---------------- Regressions ----------------

class TestRegressions:
    def test_achievements_returns_8_badges(self):
        r = requests.get(f"{BASE_URL}/api/achievements", headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 8, data
        assert len(data["unlocked"]) + len(data["locked"]) == 8
        # spot-check some keys
        keys = {b["key"] for b in data["unlocked"] + data["locked"]}
        assert "voice_print_first" in keys
        assert "physio_first_series" in keys

    def test_voice_signature_circle(self):
        r = requests.get(f"{BASE_URL}/api/family/voice-signature/circle", headers=AUTH)
        # Endpoint should return 200 (may be empty list or an object)
        assert r.status_code == 200, r.text

    def test_voice_tts_onyx(self):
        r = requests.post(
            f"{BASE_URL}/api/voice/tts",
            headers={**AUTH, "Content-Type": "application/json"},
            json={"text": "Test onyx voice", "voice": "onyx", "language": "en", "speed": 1.0},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "key" in data and "url" in data
        assert data["url"].endswith(".mp3")
