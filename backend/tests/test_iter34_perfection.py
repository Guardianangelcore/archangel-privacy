"""
Iteration 34 backend tests — "1% Perfection Finale".

Covers:
  - Pantry: list/add/patch/delete/alerts/scan + _detect_expiry regex unit tests
  - Impact dashboard: shape + physio-seeded top_thread
  - Silent Witness: session/chunk/close/list lifecycle
  - Streak freeze (weekly cap) + blazing celebrated flag
  - Angel Pulse: send / inbox / felt
  - Regression: /api/streaks/physio flags + /api/voice/tts

Design notes:
  * Seed rows tagged {"seeded_test": True} where possible for safe cleanup.
  * Pantry "empty state" test wipes pantry BEFORE running so the test doesn't
    depend on hand-seeded data; user data is minimal on this smoke user.
  * Freeze weekly-cap test resets db.streak_freezes {kind:"weekly"} + phantom
    is_freeze physio rows before each run.
"""
import io
import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests
from pymongo import MongoClient

pytestmark = pytest.mark.xdist_group(name="iter34_perfection_serial")

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://guardian-vault-13.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "guardian_health")

TOKEN = "smoketok-fresh-2026"
UID = "smoketest-user-1"
AUTH = {"Authorization": f"Bearer {TOKEN}"}

TOKEN2 = "smoketok-fresh-2026-u2"
UID2 = "smoketest-user-2"
AUTH2 = {"Authorization": f"Bearer {TOKEN2}"}


@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


# ============================================================================
# PANTRY
# ============================================================================
class TestPantry:
    @pytest.fixture(autouse=True)
    def _wipe_pantry(self, db):
        # Only wipe rows we create in these tests (all created here or empty-state).
        # We tag our seeds with location prefix TEST_ or notes prefix TEST_.
        db.pantry.delete_many({"user_id": UID, "notes": {"$regex": "^TEST_"}})
        yield
        db.pantry.delete_many({"user_id": UID, "notes": {"$regex": "^TEST_"}})

    def test_pantry_unauth(self):
        r = requests.get(f"{BASE_URL}/api/pantry")
        assert r.status_code == 401

    def test_pantry_list_shape(self):
        r = requests.get(f"{BASE_URL}/api/pantry", headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert "items" in body and isinstance(body["items"], list)
        assert set(body["counts"].keys()) >= {"critical", "soon", "healthy", "fresh", "expired", "unknown"}
        assert body["total"] == len(body["items"])

    def test_pantry_empty_state(self, db):
        """Wipe entire pantry for smoke user, verify empty response shape."""
        # Capture existing rows so we can restore them after the test
        existing = list(db.pantry.find({"user_id": UID}))
        try:
            db.pantry.delete_many({"user_id": UID})
            r = requests.get(f"{BASE_URL}/api/pantry", headers=AUTH)
            assert r.status_code == 200
            body = r.json()
            assert body["items"] == []
            assert body["total"] == 0
            assert body["counts"] == {
                "critical": 0, "soon": 0, "healthy": 0,
                "fresh": 0, "expired": 0, "unknown": 0,
            }
        finally:
            if existing:
                # Strip _id to avoid duplicate key on restore
                for row in existing:
                    row.pop("_id", None)
                db.pantry.insert_many(existing)

    def test_pantry_add_valid(self):
        payload = {
            "name": "TEST_can_beans",
            "category": "food",
            "expiration_date": "2028-03-15",
            "quantity": 3,
            "location": "Bunker A",
            "notes": "TEST_seed",
        }
        r = requests.post(f"{BASE_URL}/api/pantry", json=payload, headers=AUTH)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b["category"] == "food"
        assert b["expiration_date"] == "2028-03-15"
        assert isinstance(b["days_left"], int) and b["days_left"] > 0
        assert b["urgency"] in {"critical", "soon", "healthy", "fresh"}
        assert b["quantity"] == 3

    def test_pantry_add_invalid_category(self):
        payload = {"name": "TEST_x", "category": "spaceship",
                   "expiration_date": "2028-03-15", "notes": "TEST_seed"}
        r = requests.post(f"{BASE_URL}/api/pantry", json=payload, headers=AUTH)
        assert r.status_code == 400

    def test_pantry_add_invalid_date_falls_back(self):
        """Invalid date string should fall back to default shelf-life (not error)."""
        payload = {"name": "TEST_bad_date", "category": "food",
                   "expiration_date": "not-a-date", "notes": "TEST_seed"}
        r = requests.post(f"{BASE_URL}/api/pantry", json=payload, headers=AUTH)
        assert r.status_code == 200
        b = r.json()
        # default shelf life for food = 730 days from today
        assert isinstance(b["days_left"], int) and 700 <= b["days_left"] <= 731

    def test_pantry_patch_and_delete(self):
        create = requests.post(f"{BASE_URL}/api/pantry", json={
            "name": "TEST_patch_target", "category": "food",
            "expiration_date": "2028-01-01", "notes": "TEST_seed"
        }, headers=AUTH).json()
        pid = create["pantry_id"]

        # patch valid
        r = requests.patch(f"{BASE_URL}/api/pantry/{pid}",
                           json={"quantity": 9, "location": "Shelf B"}, headers=AUTH)
        assert r.status_code == 200
        assert r.json()["quantity"] == 9
        assert r.json()["location"] == "Shelf B"

        # patch invalid category
        r = requests.patch(f"{BASE_URL}/api/pantry/{pid}",
                           json={"category": "moonrocks"}, headers=AUTH)
        assert r.status_code == 400

        # patch invalid date
        r = requests.patch(f"{BASE_URL}/api/pantry/{pid}",
                           json={"expiration_date": "nope"}, headers=AUTH)
        assert r.status_code == 400

        # delete
        r = requests.delete(f"{BASE_URL}/api/pantry/{pid}", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["ok"] is True

        # delete again → 404
        r = requests.delete(f"{BASE_URL}/api/pantry/{pid}", headers=AUTH)
        assert r.status_code == 404

    def test_pantry_alerts_top_line_sk(self):
        # Seed a "critical" item expiring in 5 days
        soon_date = (datetime.now(timezone.utc).date() + timedelta(days=5)).isoformat()
        requests.post(f"{BASE_URL}/api/pantry", json={
            "name": "TEST_alertitem", "category": "food",
            "expiration_date": soon_date, "location": "Bunker A",
            "notes": "TEST_seed",
        }, headers=AUTH)
        r = requests.get(f"{BASE_URL}/api/pantry/alerts", headers=AUTH)
        assert r.status_code == 200
        b = r.json()
        assert b["count"] >= 1
        assert b["top_line"] is not None
        # Slovak sentence sanity — either expired or "vyprší"/"rotovať"
        assert any(w in b["top_line"] for w in ["vyprší", "Odporúčam", "spotrebu", "prekročenú"])

    # ---- pantry/scan unit-level: _detect_expiry patterns ------------------
    def test_detect_expiry_patterns(self):
        import sys
        sys.path.insert(0, "/app/backend")
        from routes.pantry import _detect_expiry

        # month/year only patterns → last day of month
        assert _detect_expiry("MHD 12/2028") == "2028-12-31"
        assert _detect_expiry("BB 03/2029") == "2029-03-31"

        # day/month/year patterns
        assert _detect_expiry("Spotreba do 15.03.2028") == "2028-03-15"

        # ISO labeled
        assert _detect_expiry("Best before: 2028-03-15") == "2028-03-15"

        # invalid should return None
        assert _detect_expiry("no date here at all") is None

    def test_pantry_scan_from_vault_doc(self, db):
        """Seed a fake vault document with OCR text, call /pantry/scan → verify
        extracted_expiry + pantry entry created."""
        doc_id = uuid.uuid4().hex
        db.documents.insert_one({
            "doc_id": doc_id,
            "user_id": UID,
            "title": "TEST_scan_doc",
            "extracted_text": "Konzerva fazule\nMHD 12/2028\nHmotnosť 400g",
            "created_at": datetime.now(timezone.utc),
            "seeded_test": True,
        })
        try:
            r = requests.post(f"{BASE_URL}/api/pantry/scan", json={
                "doc_id": doc_id,
                "hint_category": "food",
                "location": "TEST_scan_loc",
            }, headers=AUTH)
            assert r.status_code == 200, r.text
            b = r.json()
            assert b["extracted_expiry"] == "2028-12-31"
            assert b["expiration_date"] == "2028-12-31"
            assert b["category"] == "food"
            # Cleanup pantry row from scan
            db.pantry.delete_one({"pantry_id": b["pantry_id"]})
        finally:
            db.documents.delete_one({"doc_id": doc_id})


# ============================================================================
# IMPACT DASHBOARD
# ============================================================================
class TestImpact:
    def test_impact_unauth(self):
        r = requests.get(f"{BASE_URL}/api/impact/dashboard")
        assert r.status_code == 401

    def test_impact_shape(self):
        r = requests.get(f"{BASE_URL}/api/impact/dashboard", headers=AUTH)
        assert r.status_code == 200
        b = r.json()
        for k in ("people_helped", "research_hours", "tokens_earned",
                  "contributions_total", "timeline_weeks", "breakdown"):
            assert k in b, f"missing key {k}"
        assert isinstance(b["timeline_weeks"], list) and len(b["timeline_weeks"]) == 4
        # timeline_weeks entries have week_ago + contributions
        for w in b["timeline_weeks"]:
            assert "week_ago" in w and "contributions" in w

    def test_impact_physio_seed_top_thread(self, db):
        """Seed a physio_video in the last 30 days, verify Physio-AI shows in top_thread."""
        seed_id = f"impact_seed_{uuid.uuid4().hex}"
        db.physio_videos.insert_one({
            "video_id": seed_id,
            "user_id": UID,
            "title": "TEST_impact_seed",
            "created_at": datetime.now(timezone.utc) - timedelta(days=1),
            "seeded_test": True,
        })
        try:
            r = requests.get(f"{BASE_URL}/api/impact/dashboard", headers=AUTH)
            assert r.status_code == 200
            b = r.json()
            assert b["breakdown"]["physio"] >= 1
            # top_thread should be Physio-AI (recent physio wins)
            assert b["top_thread"] is not None
            assert b["top_thread"]["title"] == "Physio-AI"
        finally:
            db.physio_videos.delete_one({"video_id": seed_id})


# ============================================================================
# SILENT WITNESS
# ============================================================================
class TestSilentWitness:
    def test_sw_unauth(self):
        r = requests.post(f"{BASE_URL}/api/silent-witness/session")
        assert r.status_code == 401

    def test_sw_full_lifecycle(self, db):
        # open
        r = requests.post(f"{BASE_URL}/api/silent-witness/session", headers=AUTH)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b["status"] == "active"
        sid = b["session_id"]

        try:
            # empty chunk → 400
            files = {"file": ("empty.webm", b"", "audio/webm")}
            r = requests.post(f"{BASE_URL}/api/silent-witness/{sid}/chunk",
                              files=files, data={"index": "0"}, headers=AUTH)
            assert r.status_code == 400

            # oversized chunk → 400
            big = b"x" * (5 * 1024 * 1024 + 1)
            files = {"file": ("big.webm", big, "audio/webm")}
            r = requests.post(f"{BASE_URL}/api/silent-witness/{sid}/chunk",
                              files=files, data={"index": "0"}, headers=AUTH)
            assert r.status_code == 400

            # valid small chunk
            payload = b"WEBM-fake-audio-bytes-1234"
            files = {"file": ("chunk0.webm", payload, "audio/webm")}
            r = requests.post(f"{BASE_URL}/api/silent-witness/{sid}/chunk",
                              files=files, data={"index": "0"}, headers=AUTH)
            assert r.status_code == 200, r.text
            cb = r.json()
            assert cb["ok"] is True and cb["index"] == 0 and cb["size"] == len(payload)

            # verify state incremented
            sess = db.silent_witness.find_one({"session_id": sid})
            assert sess["chunk_count"] == 1
            assert sess["total_bytes"] == len(payload)

            # list sessions includes this one
            r = requests.get(f"{BASE_URL}/api/silent-witness/sessions", headers=AUTH)
            assert r.status_code == 200
            ids = [s["session_id"] for s in r.json()["sessions"]]
            assert sid in ids

            # close
            r = requests.post(f"{BASE_URL}/api/silent-witness/{sid}/close", headers=AUTH)
            assert r.status_code == 200, r.text
            cbody = r.json()
            assert cbody["status"] == "closed"
            assert cbody.get("closed_at")

            # close again → 404 (find_one_and_update finds no active row)
            r = requests.post(f"{BASE_URL}/api/silent-witness/{sid}/close", headers=AUTH)
            assert r.status_code == 404
        finally:
            db.silent_witness.delete_one({"session_id": sid})


# ============================================================================
# STREAK FREEZE + BLAZING
# ============================================================================
class TestStreaks:
    @pytest.fixture(autouse=True)
    def _reset_freeze(self, db):
        # clear this-week freezes + phantom rows
        db.streak_freezes.delete_many({"user_id": UID, "kind": "weekly"})
        db.physio_videos.delete_many({"user_id": UID, "is_freeze": True})
        yield
        db.streak_freezes.delete_many({"user_id": UID, "kind": "weekly"})
        db.physio_videos.delete_many({"user_id": UID, "is_freeze": True})

    def test_freeze_once_per_week(self):
        # 1st call ok
        r = requests.post(f"{BASE_URL}/api/streaks/freeze", headers=AUTH)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b["ok"] is True and "used_at" in b and "message" in b

        # streaks endpoint reflects freeze
        r = requests.get(f"{BASE_URL}/api/streaks/physio", headers=AUTH)
        assert r.status_code == 200
        s = r.json()
        assert s["freeze_available"] is False
        assert s["current"] >= 1

        # 2nd call same week → 409
        r = requests.post(f"{BASE_URL}/api/streaks/freeze", headers=AUTH)
        assert r.status_code == 409

    def test_blazing_celebrated(self, db):
        # ensure not celebrated
        db.streak_freezes.delete_many({"user_id": UID, "kind": "blazing_celebration"})
        try:
            r = requests.post(f"{BASE_URL}/api/streaks/blazing/celebrated", headers=AUTH)
            assert r.status_code == 200
            assert r.json()["ok"] is True

            r = requests.get(f"{BASE_URL}/api/streaks/physio", headers=AUTH)
            assert r.status_code == 200
            assert r.json()["blazing_celebrated"] is True
        finally:
            db.streak_freezes.delete_many({"user_id": UID, "kind": "blazing_celebration"})


# ============================================================================
# ANGEL PULSE
# ============================================================================
class TestAngelPulse:
    def test_pulse_unauth(self):
        r = requests.post(f"{BASE_URL}/api/angel/pulse", json={"to_user_id": UID2})
        assert r.status_code == 401

    def test_pulse_missing_target(self):
        r = requests.post(f"{BASE_URL}/api/angel/pulse", json={}, headers=AUTH)
        assert r.status_code == 400

    def test_pulse_self_forbidden(self):
        r = requests.post(f"{BASE_URL}/api/angel/pulse",
                          json={"to_user_id": UID}, headers=AUTH)
        assert r.status_code == 400

    def test_pulse_unrelated_recipient(self, db):
        """Seed a random third user with no guardian link, expect 403."""
        stranger_id = f"stranger_{uuid.uuid4().hex[:8]}"
        db.users.insert_one({
            "user_id": stranger_id,
            "email": f"{stranger_id}@example.com",
            "did": f"did:guardian:{uuid.uuid4().hex}",
            "language": "sk",
            "angel_mode": False,
            "created_at": datetime.now(timezone.utc),
            "seeded_test": True,
        })
        try:
            r = requests.post(f"{BASE_URL}/api/angel/pulse",
                              json={"to_user_id": stranger_id}, headers=AUTH)
            assert r.status_code == 403
        finally:
            db.users.delete_one({"user_id": stranger_id})

    def test_pulse_send_inbox_felt(self, db):
        # send from u1 → u2 (guardian link exists per test_credentials.md)
        r = requests.post(f"{BASE_URL}/api/angel/pulse",
                          json={"to_user_id": UID2, "pattern": "heartbeat", "bpm": 78},
                          headers=AUTH)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        pulse = body["pulse"]
        assert pulse["from_user_id"] == UID
        assert pulse["to_user_id"] == UID2
        assert pulse["pattern"] == "heartbeat"
        assert pulse["bpm"] == 78
        assert pulse["delivered"] is False
        pid = pulse["pulse_id"]

        try:
            # u2 inbox includes it
            r = requests.get(f"{BASE_URL}/api/angel/pulse/inbox", headers=AUTH2)
            assert r.status_code == 200
            ids = [p["pulse_id"] for p in r.json()["pulses"]]
            assert pid in ids

            # u2 marks felt
            r = requests.post(f"{BASE_URL}/api/angel/pulse/{pid}/felt", headers=AUTH2)
            assert r.status_code == 200
            felt = r.json()
            assert felt["delivered"] is True
            assert felt.get("felt_at")
        finally:
            db.angel_pulses.delete_one({"pulse_id": pid})


# ============================================================================
# REGRESSION
# ============================================================================
class TestRegression:
    def test_streaks_flags(self):
        r = requests.get(f"{BASE_URL}/api/streaks/physio", headers=AUTH)
        assert r.status_code == 200
        b = r.json()
        assert "freeze_available" in b
        assert "blazing_celebrated" in b

    def test_voice_tts_onyx(self):
        r = requests.post(f"{BASE_URL}/api/voice/tts",
                          json={"text": "Test regresie hlasu.", "voice": "onyx"},
                          headers=AUTH)
        assert r.status_code == 200, r.text
