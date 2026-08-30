# Iteration 31 — SENTIENT UX FINALE (Zero-Friction Age Sync via OCR + Voice Signatures)
# Covers:
#   1) PrefIn.onboarding_completed field (PATCH /me/prefs, GET /auth/me reflects)
#   2) OCR birth-year auto-detect (Slovak DOB, RČ, "no info", cache, existing-user guard)
#   3) Voice-signature endpoints (POST, GET, GET /file, DELETE) — Inner Circle voice prints
#
# Notes:
# - Uses pymongo to seed docs directly in db.documents / clear user.birth_year
#   (bypassing the upload endpoint's background orchestrator, per main-agent guidance).
# - Uses smoketest-user-1 / smoketok-fresh-2026 (bearer).
import io
import os
import uuid
import pytest
import requests
from datetime import datetime, timezone
from pymongo import MongoClient

BASE_URL = os.environ.get(
    "EXPO_PUBLIC_BACKEND_URL",
    "https://guardian-vault-13.preview.emergentagent.com",
).rstrip("/")
TOKEN = "smoketok-fresh-2026"
UID = "smoketest-user-1"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
MULTI = {"Authorization": f"Bearer {TOKEN}"}

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "guardian_health")


@pytest.fixture(scope="module")
def db():
    c = MongoClient(MONGO_URL)
    return c[DB_NAME]


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    return sess


# ---------- (1) onboarding_completed pref ----------
class TestOnboardingPref:
    def test_patch_true(self, s):
        r = s.patch(f"{BASE_URL}/api/me/prefs", headers=HEADERS,
                    json={"onboarding_completed": True})
        assert r.status_code == 200, r.text
        assert r.json().get("onboarding_completed") is True

        me = s.get(f"{BASE_URL}/api/auth/me", headers=HEADERS)
        assert me.status_code == 200
        assert (me.json().get("user") or {}).get("onboarding_completed") is True

    def test_patch_false(self, s):
        r = s.patch(f"{BASE_URL}/api/me/prefs", headers=HEADERS,
                    json={"onboarding_completed": False})
        # false is skipped by upd dict (None-check treats False as falsy? Let's verify)
        # Actual code: `if v is not None` — False stays, so False persists.
        assert r.status_code == 200, r.text
        body = r.json()
        # After patch, GET should show False
        me = s.get(f"{BASE_URL}/api/auth/me", headers=HEADERS)
        u = me.json().get("user") or {}
        assert u.get("onboarding_completed") is False, f"Expected False, got {u.get('onboarding_completed')}"
        # restore to True
        s.patch(f"{BASE_URL}/api/me/prefs", headers=HEADERS,
                json={"onboarding_completed": True})

    def test_patch_invalid_type_422(self, s):
        r = s.patch(f"{BASE_URL}/api/me/prefs", headers=HEADERS,
                    json={"onboarding_completed": "not-a-bool"})
        assert r.status_code == 422, f"Expected 422 Pydantic, got {r.status_code}: {r.text}"


# ---------- (2) OCR birth-year auto-detect ----------
def _seed_doc(db, extracted_text, doc_id=None, user_id=UID):
    """Seed a document row directly (no storage needed since extracted_text is cached)."""
    doc_id = doc_id or uuid.uuid4().hex
    db.documents.insert_one({
        "doc_id": doc_id,
        "user_id": user_id,
        "title": "TEST_iter31_doc",
        "file_name": "test.pdf",
        "content_type": "application/pdf",
        "size": 100,
        "storage_path": f"guardian/uploads/{user_id}/{doc_id}.pdf",
        "hash": "0" * 64,
        "extracted_text": extracted_text,   # None → will call extract_doc_text; str → cached branch
        "uploaded_at": datetime.now(timezone.utc),
    })
    return doc_id


def _cleanup_doc(db, doc_id):
    db.documents.delete_one({"doc_id": doc_id})


class TestOCRBirthYearAutoDetect:
    def test_slovak_dob_detected_and_applied(self, s, db):
        # Clear user.birth_year first
        prev = db.users.find_one({"user_id": UID}, {"birth_year": 1})
        prev_by = (prev or {}).get("birth_year")
        db.users.update_one({"user_id": UID}, {"$unset": {"birth_year": ""}})

        # Seed doc with pre-extracted text so OCR endpoint short-circuits to detection
        # BUT — the endpoint returns cached=True and birth_year_detected=None when extracted_text is cached!
        # So we need extracted_text=None to force detection. That requires storage read.
        # Workaround: patch db.documents so extracted_text is None, then we'll need real storage — instead,
        # we take a different path: temporarily set extracted_text=None AND intercept via storage.
        # Simpler: seed with extracted_text=None and rely on the doc's storage_path resolving to a real
        # object; but we can't create storage objects directly. So we use a different tactic:
        # POST a small text-based PDF through the API (with autopilot disabled), then call OCR.
        try:
            # Disable jarvis_autopilot to prevent background orchestrator
            r = s.put(f"{BASE_URL}/api/jarvis/autopilot", headers=HEADERS,
                      json={"enabled": False})
            assert r.status_code == 200, r.text

            # Build tiny PDF with the Slovak DOB text (ASCII fallback matches regex — 'date of birth' too)
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=12)
            # Slovak with diacritics — fpdf latin-1 can't encode á, so use ASCII pattern
            # pattern 1 accepts 'date of birth' too: use it and also include 'Datum narodenia' (no accents)
            pdf.cell(0, 10, "Test document", ln=True)
            pdf.cell(0, 10, "date of birth: 15.03.1958", ln=True)
            pdf_bytes = bytes(pdf.output())
            files = {"file": ("dob.pdf", pdf_bytes, "application/pdf")}
            up = s.post(f"{BASE_URL}/api/vault/documents", headers=MULTI,
                        files=files, data={"title": "TEST_iter31_dob"})
            assert up.status_code == 200, up.text
            doc_id = up.json()["doc_id"]

            try:
                # Call OCR
                r = s.post(f"{BASE_URL}/api/vault/documents/{doc_id}/ocr",
                           headers=HEADERS, timeout=90)
                assert r.status_code == 200, r.text
                data = r.json()
                # First call — text is extracted fresh, birth_year_detected=1958, applied=True
                assert data.get("birth_year_detected") == 1958, data
                assert data.get("birth_year_applied") is True, data
                # cached should NOT be True (fresh scan)
                assert not data.get("cached"), data

                # User must now have birth_year=1958
                me = s.get(f"{BASE_URL}/api/auth/me", headers=HEADERS)
                assert (me.json().get("user") or {}).get("birth_year") == 1958

                # ---- Same doc again — cached=True, birth_year_detected=None
                r2 = s.post(f"{BASE_URL}/api/vault/documents/{doc_id}/ocr",
                            headers=HEADERS, timeout=30)
                assert r2.status_code == 200, r2.text
                d2 = r2.json()
                assert d2.get("cached") is True, d2
                assert d2.get("birth_year_detected") is None, d2
            finally:
                # Cleanup document
                s.delete(f"{BASE_URL}/api/vault/documents/{doc_id}", headers=HEADERS)
        finally:
            # Restore autopilot + birth_year
            s.put(f"{BASE_URL}/api/jarvis/autopilot", headers=HEADERS,
                  json={"enabled": True})
            if prev_by:
                db.users.update_one({"user_id": UID}, {"$set": {"birth_year": prev_by}})

    def test_never_overwrites_existing_birth_year(self, s, db):
        """User already has birth_year → applied=False."""
        # Ensure birth_year is set
        db.users.update_one({"user_id": UID}, {"$set": {"birth_year": 1970}})
        try:
            # Disable autopilot
            s.put(f"{BASE_URL}/api/jarvis/autopilot", headers=HEADERS,
                  json={"enabled": False})
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=12)
            pdf.cell(0, 10, "date of birth: 15.03.1958", ln=True)
            pdf_bytes = bytes(pdf.output())
            files = {"file": ("dob2.pdf", pdf_bytes, "application/pdf")}
            up = s.post(f"{BASE_URL}/api/vault/documents", headers=MULTI,
                        files=files, data={"title": "TEST_iter31_dob2"})
            assert up.status_code == 200, up.text
            doc_id = up.json()["doc_id"]
            try:
                r = s.post(f"{BASE_URL}/api/vault/documents/{doc_id}/ocr",
                           headers=HEADERS, timeout=90)
                assert r.status_code == 200, r.text
                data = r.json()
                assert data.get("birth_year_detected") == 1958, data
                assert data.get("birth_year_applied") is False, data
                # user still 1970
                me = s.get(f"{BASE_URL}/api/auth/me", headers=HEADERS)
                assert (me.json().get("user") or {}).get("birth_year") == 1970
            finally:
                s.delete(f"{BASE_URL}/api/vault/documents/{doc_id}", headers=HEADERS)
        finally:
            db.users.update_one({"user_id": UID}, {"$set": {"birth_year": 1958}})
            s.put(f"{BASE_URL}/api/jarvis/autopilot", headers=HEADERS,
                  json={"enabled": True})

    def test_rc_pattern_detects_1958(self, s, db):
        """RČ (rodné číslo) '580315/1234' → 1958."""
        prev = db.users.find_one({"user_id": UID}, {"birth_year": 1})
        prev_by = (prev or {}).get("birth_year")
        db.users.update_one({"user_id": UID}, {"$unset": {"birth_year": ""}})
        try:
            s.put(f"{BASE_URL}/api/jarvis/autopilot", headers=HEADERS,
                  json={"enabled": False})
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=12)
            # ASCII "rodne cislo" is in the regex
            pdf.cell(0, 10, "rodne cislo: 580315/1234", ln=True)
            pdf_bytes = bytes(pdf.output())
            files = {"file": ("rc.pdf", pdf_bytes, "application/pdf")}
            up = s.post(f"{BASE_URL}/api/vault/documents", headers=MULTI,
                        files=files, data={"title": "TEST_iter31_rc"})
            assert up.status_code == 200, up.text
            doc_id = up.json()["doc_id"]
            try:
                r = s.post(f"{BASE_URL}/api/vault/documents/{doc_id}/ocr",
                           headers=HEADERS, timeout=90)
                assert r.status_code == 200, r.text
                assert r.json().get("birth_year_detected") == 1958, r.json()
            finally:
                s.delete(f"{BASE_URL}/api/vault/documents/{doc_id}", headers=HEADERS)
        finally:
            s.put(f"{BASE_URL}/api/jarvis/autopilot", headers=HEADERS,
                  json={"enabled": True})
            if prev_by:
                db.users.update_one({"user_id": UID}, {"$set": {"birth_year": prev_by}})

    def test_no_birth_info_returns_null(self, s, db):
        try:
            s.put(f"{BASE_URL}/api/jarvis/autopilot", headers=HEADERS,
                  json={"enabled": False})
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=12)
            pdf.cell(0, 10, "This document contains only random text, no dates.", ln=True)
            pdf_bytes = bytes(pdf.output())
            files = {"file": ("plain.pdf", pdf_bytes, "application/pdf")}
            up = s.post(f"{BASE_URL}/api/vault/documents", headers=MULTI,
                        files=files, data={"title": "TEST_iter31_plain"})
            assert up.status_code == 200, up.text
            doc_id = up.json()["doc_id"]
            try:
                r = s.post(f"{BASE_URL}/api/vault/documents/{doc_id}/ocr",
                           headers=HEADERS, timeout=90)
                assert r.status_code == 200, r.text
                data = r.json()
                assert data.get("birth_year_detected") is None, data
                assert data.get("birth_year_applied") is False, data
            finally:
                s.delete(f"{BASE_URL}/api/vault/documents/{doc_id}", headers=HEADERS)
        finally:
            s.put(f"{BASE_URL}/api/jarvis/autopilot", headers=HEADERS,
                  json={"enabled": True})


# ---------- (3) Voice-signature endpoints ----------
def _make_audio(size_bytes=2048):
    # simulate a small webm blob — server only checks size + storage roundtrip
    return b"\x1a\x45\xdf\xa3" + os.urandom(size_bytes - 4)


class TestVoiceSignature:
    def test_get_empty_baseline(self, s):
        # Clean any prior sig
        s.delete(f"{BASE_URL}/api/family/voice-signature", headers=HEADERS)
        r = s.get(f"{BASE_URL}/api/family/voice-signature", headers=HEADERS)
        assert r.status_code == 200
        assert r.json() == {} or r.json() is None

    def test_post_without_audio_400(self, s):
        # No file at all → FastAPI treats missing UploadFile as 422 (Pydantic).
        # If we send an empty file, server checks `if not data` → 400.
        r = s.post(f"{BASE_URL}/api/family/voice-signature", headers=MULTI,
                   files={"file": ("empty.webm", b"", "audio/webm")},
                   data={"label": "Empty"})
        assert r.status_code == 400, r.text

    def test_post_too_large_400(self, s):
        big = _make_audio(3 * 1024 * 1024 + 1)  # > 3MB
        r = s.post(f"{BASE_URL}/api/family/voice-signature", headers=MULTI,
                   files={"file": ("big.webm", big, "audio/webm")},
                   data={"label": "Big"})
        assert r.status_code == 400, r.text

    def test_post_and_get_and_file(self, s):
        audio = _make_audio(8192)
        r = s.post(f"{BASE_URL}/api/family/voice-signature", headers=MULTI,
                   files={"file": ("sig.webm", audio, "audio/webm")},
                   data={"label": "Founder"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        assert body.get("sig_id")
        assert body.get("label") == "Founder"

        # GET (no storage_path)
        g = s.get(f"{BASE_URL}/api/family/voice-signature", headers=HEADERS)
        assert g.status_code == 200
        rec = g.json()
        assert rec.get("label") == "Founder"
        assert rec.get("user_id") == UID
        assert "storage_path" not in rec

        # GET /file with bearer
        f = s.get(f"{BASE_URL}/api/family/voice-signature/file", headers=HEADERS)
        assert f.status_code == 200
        assert len(f.content) == len(audio)

    def test_file_without_auth_401(self, s):
        r = s.get(f"{BASE_URL}/api/family/voice-signature/file")
        assert r.status_code == 401, r.text

    def test_post_idempotent_update_label(self, s):
        # Second POST with a new label — overwrites for the same user_id
        audio = _make_audio(4096)
        r = s.post(f"{BASE_URL}/api/family/voice-signature", headers=MULTI,
                   files={"file": ("sig2.webm", audio, "audio/webm")},
                   data={"label": "GuardianV2"})
        assert r.status_code == 200, r.text
        assert r.json().get("label") == "GuardianV2"

        g = s.get(f"{BASE_URL}/api/family/voice-signature", headers=HEADERS)
        assert g.status_code == 200
        assert g.json().get("label") == "GuardianV2"
        # Only one record exists — via db uniqueness (upsert on user_id)

    def test_delete_and_verify_empty(self, s):
        d = s.delete(f"{BASE_URL}/api/family/voice-signature", headers=HEADERS)
        assert d.status_code == 200
        assert d.json().get("ok") is True

        g = s.get(f"{BASE_URL}/api/family/voice-signature", headers=HEADERS)
        assert g.status_code == 200
        assert g.json() == {}

        # /file after delete → 404 (No voice signature recorded yet)
        f = s.get(f"{BASE_URL}/api/family/voice-signature/file", headers=HEADERS)
        assert f.status_code == 404, f.text


# ---------- (4) Regression: existing prefs still work + /auth/me full shape ----------
class TestRegression:
    def test_patch_multiple_prefs(self, s):
        r = s.patch(f"{BASE_URL}/api/me/prefs", headers=HEADERS,
                    json={"birth_year": 1958, "biometric_enabled": True, "wake_word_enabled": True})
        assert r.status_code == 200
        b = r.json()
        assert b.get("birth_year") == 1958
        assert b.get("biometric_enabled") is True
        assert b.get("wake_word_enabled") is True

    def test_tts_onyx_still_works(self, s):
        r = s.post(f"{BASE_URL}/api/voice/tts", headers=HEADERS,
                   json={"text": "Ahoj", "voice": "onyx", "language": "sk"})
        assert r.status_code == 200, r.text
        assert r.json().get("key")

    def test_auth_me_full_fields(self, s):
        r = s.get(f"{BASE_URL}/api/auth/me", headers=HEADERS)
        assert r.status_code == 200
        u = r.json().get("user") or {}
        # All new sentient UX fields present
        for k in ("birth_year", "biometric_enabled", "wake_word_enabled", "onboarding_completed"):
            assert k in u, f"missing key {k} in /auth/me user payload"
