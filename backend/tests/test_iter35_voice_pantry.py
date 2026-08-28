"""
Iteration 35 backend tests — Voice-First Pantry Add.

Covers:
  * POST /api/pantry/voice/parse — deterministic Slovak/Czech transcript parser
    + database insertion (source='voice', notes contains raw transcript)
  * POST /api/pantry/voice — multipart audio (empty → 400, oversized → 413)
  * Unit-level parser functions: _parse_qty, _guess_category, _parse_location
  * Regression: /api/pantry, /api/pantry/alerts, /api/pantry/scan,
    /api/streaks/physio (freeze_available flag)

All test-created rows are cleaned via
    db.pantry.delete_many({"user_id": UID, "source": "voice"})
in an autouse fixture teardown.
"""
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests
from pymongo import MongoClient

# Ensure backend package is importable for unit tests
sys.path.insert(0, "/app/backend")

pytestmark = pytest.mark.xdist_group(name="iter35_voice_pantry_serial")

BASE_URL = os.environ.get(
    "EXPO_PUBLIC_BACKEND_URL",
    "https://biometric-onboard-3.preview.emergentagent.com",
).rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "guardian_health")

TOKEN = "smoketok-fresh-2026"
UID = "smoketest-user-1"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


# ============================================================================
# /api/pantry/voice/parse — integration tests
# ============================================================================
class TestPantryVoiceParse:
    @pytest.fixture(autouse=True)
    def _wipe_voice_rows(self, db):
        db.pantry.delete_many({"user_id": UID, "source": "voice"})
        yield
        db.pantry.delete_many({"user_id": UID, "source": "voice"})

    # ---- auth guard ----
    def test_voice_parse_unauth(self):
        r = requests.post(
            f"{BASE_URL}/api/pantry/voice/parse",
            json={"transcript": "Mám tri konzervy"},
        )
        assert r.status_code == 401

    # ---- empty transcript ----
    def test_voice_parse_empty(self):
        r = requests.post(
            f"{BASE_URL}/api/pantry/voice/parse",
            json={"transcript": ""},
            headers=AUTH,
        )
        assert r.status_code == 400

        r = requests.post(
            f"{BASE_URL}/api/pantry/voice/parse",
            json={"transcript": "   "},
            headers=AUTH,
        )
        assert r.status_code == 400

    # ---- prompt 1: food + qty=3 + location Bunker A ----
    def test_voice_parse_food_konzervy(self, db):
        transcript = "Mám tri konzervy fazule v bunkri A"
        r = requests.post(
            f"{BASE_URL}/api/pantry/voice/parse",
            json={"transcript": transcript},
            headers=AUTH,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["quantity"] == 3
        assert body["category"] == "food"
        assert "konzervy" in body["name"].lower()
        assert "bunkri a" in body["location"].lower()
        assert body["source"] == "voice"
        # notes contains the raw transcript verbatim (surrounded by mic quotes)
        assert transcript in body["notes"]

        # Persistence: verify row exists in DB with source='voice' and notes
        row = db.pantry.find_one({"pantry_id": body["pantry_id"]})
        assert row is not None
        assert row["source"] == "voice"
        assert transcript in row["notes"]
        assert row["user_id"] == UID

    # ---- prompt 2: batteries + qty=5 ----
    def test_voice_parse_batteries(self):
        r = requests.post(
            f"{BASE_URL}/api/pantry/voice/parse",
            json={"transcript": "Pridaj päť batérií AA do skrine v garáži"},
            headers=AUTH,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["quantity"] == 5
        assert body["category"] == "battery"

    # ---- prompt 3: water + qty=10 (word "desať") ----
    def test_voice_parse_water_desat(self):
        r = requests.post(
            f"{BASE_URL}/api/pantry/voice/parse",
            json={"transcript": "Máme desať litrov pitnej vody na chate"},
            headers=AUTH,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["quantity"] == 10
        assert body["category"] == "water"

    # ---- prompt 4: filter + qty=2 ----
    def test_voice_parse_filter(self):
        r = requests.post(
            f"{BASE_URL}/api/pantry/voice/parse",
            json={"transcript": "Chcem pridať 2 filtre na vodu do bunkra"},
            headers=AUTH,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["quantity"] == 2
        # BUG: category resolves to 'water' because "vod" keyword is checked
        # before "filter" in _CATEGORY_KEYWORDS ordering.
        assert body["category"] == "filter", (
            f"Expected category=filter but got '{body['category']}'. "
            f"Water keyword 'vod' incorrectly wins because it's checked "
            f"before 'filter' in _CATEGORY_KEYWORDS iteration order."
        )


# ============================================================================
# /api/pantry/voice — multipart audio endpoint
# ============================================================================
class TestPantryVoiceUpload:
    def test_voice_upload_unauth(self):
        files = {"file": ("a.webm", b"abc", "audio/webm")}
        r = requests.post(f"{BASE_URL}/api/pantry/voice", files=files)
        assert r.status_code == 401

    def test_voice_upload_empty(self):
        files = {"file": ("empty.webm", b"", "audio/webm")}
        r = requests.post(f"{BASE_URL}/api/pantry/voice", files=files, headers=AUTH)
        assert r.status_code == 400

    def test_voice_upload_oversized(self):
        # 20 MB + 1 byte should trip the 413 guard before Whisper is called.
        payload = b"x" * (20 * 1024 * 1024 + 1)
        files = {"file": ("big.webm", payload, "audio/webm")}
        r = requests.post(
            f"{BASE_URL}/api/pantry/voice",
            files=files,
            headers=AUTH,
            timeout=120,
        )
        assert r.status_code == 413


# ============================================================================
# Unit-level parser tests (imported directly from routes.pantry)
# ============================================================================
class TestParserUnits:
    def test_parse_qty_word_map(self):
        from routes.pantry import _parse_qty
        assert _parse_qty("jedno vedro") == 1
        assert _parse_qty("štyri konzervy") == 4
        assert _parse_qty("sedem batérií") == 7
        # extras from spec
        assert _parse_qty("tri konzervy fazule") == 3
        assert _parse_qty("päť batérií") == 5
        assert _parse_qty("desať litrov") == 10
        # digit wins
        assert _parse_qty("2 filtre") == 2
        assert _parse_qty("Chcem pridať 2 filtre") == 2
        # fallback
        assert _parse_qty("nič konkrétne") == 1

    def test_guess_category(self):
        from routes.pantry import _guess_category
        assert _guess_category("dve tablety Ibalginu") == "med"
        assert _guess_category("nôž survival") == "tool"
        assert _guess_category("muníc 9mm") == "ammo"
        # spot-checks matching integration tests
        assert _guess_category("tri konzervy fazule") == "food"
        assert _guess_category("desať litrov pitnej vody") == "water"

    def test_parse_location_lowercase(self):
        from routes.pantry import _parse_location
        assert _parse_location("v bunkri A") == "bunkri A"
        assert _parse_location("v pivnici") == "pivnici"
        assert _parse_location("do garáže") == "garáže"


# ============================================================================
# Regression on prior pantry endpoints + streak freeze flag
# ============================================================================
class TestRegression:
    @pytest.fixture(autouse=True)
    def _cleanup(self, db):
        db.pantry.delete_many({"user_id": UID, "notes": {"$regex": "^TEST_iter35"}})
        yield
        db.pantry.delete_many({"user_id": UID, "notes": {"$regex": "^TEST_iter35"}})

    def test_pantry_list_still_works(self):
        r = requests.get(f"{BASE_URL}/api/pantry", headers=AUTH)
        assert r.status_code == 200
        b = r.json()
        assert "items" in b and isinstance(b["items"], list)
        assert set(b["counts"].keys()) >= {
            "critical", "soon", "healthy", "fresh", "expired", "unknown",
        }
        assert b["total"] == len(b["items"])

    def test_pantry_alerts_still_works(self, db):
        soon = (datetime.now(timezone.utc).date() + timedelta(days=7)).isoformat()
        create = requests.post(
            f"{BASE_URL}/api/pantry",
            json={
                "name": "TEST_iter35_alertitem",
                "category": "food",
                "expiration_date": soon,
                "location": "Bunker A",
                "notes": "TEST_iter35_regression",
            },
            headers=AUTH,
        )
        assert create.status_code == 200, create.text
        r = requests.get(f"{BASE_URL}/api/pantry/alerts", headers=AUTH)
        assert r.status_code == 200
        b = r.json()
        assert b["count"] >= 1
        assert b["top_line"] is not None

    def test_pantry_scan_still_works(self, db):
        doc_id = uuid.uuid4().hex
        db.documents.insert_one({
            "doc_id": doc_id,
            "user_id": UID,
            "title": "TEST_iter35_scan",
            "extracted_text": "Konzerva fazule\nMHD 06/2029\nHmotnosť 400g",
            "created_at": datetime.now(timezone.utc),
            "seeded_test": True,
        })
        try:
            r = requests.post(
                f"{BASE_URL}/api/pantry/scan",
                json={
                    "doc_id": doc_id,
                    "hint_category": "food",
                    "location": "TEST_iter35_shelf",
                },
                headers=AUTH,
            )
            assert r.status_code == 200, r.text
            b = r.json()
            assert b["extracted_expiry"] == "2029-06-30"
            assert b["expiration_date"] == "2029-06-30"
            assert b["category"] == "food"
            db.pantry.delete_one({"pantry_id": b["pantry_id"]})
        finally:
            db.documents.delete_one({"doc_id": doc_id})

    def test_streaks_physio_freeze_flag(self):
        r = requests.get(f"{BASE_URL}/api/streaks/physio", headers=AUTH)
        assert r.status_code == 200
        b = r.json()
        assert "freeze_available" in b
        assert isinstance(b["freeze_available"], bool)
