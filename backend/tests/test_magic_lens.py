"""Magic Lens end-to-end backend tests.

Covers:
- Founder dev-bypass auth
- POST /api/magic-lens with a PIL-generated fake lab-result JPEG (base64)
- Auth guard (401) + empty body guard (400)
- Life Card save through /api/calendar/events + GET & DELETE
"""
import base64
import io
import os
import time
from datetime import date

import pytest
import requests
from PIL import Image, ImageDraw

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
LONG_TIMEOUT = 120  # AI can take 10-60s


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def session_token():
    r = requests.post(
        f"{API}/auth/dev-bypass",
        json={"email": "guardian.angel.core@proton.me", "name": "Guardian Angel"},
        timeout=30,
    )
    assert r.status_code == 200, f"dev-bypass failed: {r.status_code} {r.text}"
    tok = r.json().get("session_token")
    assert tok, "no session_token in dev-bypass response"
    return tok


@pytest.fixture(scope="module")
def auth_headers(session_token):
    return {"Authorization": f"Bearer {session_token}", "Content-Type": "application/json"}


def _fake_lab_result_b64() -> str:
    """Generate a white JPEG with black text simulating a lab report."""
    img = Image.new("RGB", (900, 1200), "white")
    d = ImageDraw.Draw(img)
    lines = [
        "SAINT MICHAEL HOSPITAL",
        "LABORATORY REPORT",
        "",
        "Patient: John Smith",
        "Date of birth: 12.05.1950",
        "Report date: 15.01.2026",
        "",
        "GLUCOSE:      5.4 mmol/L    (Normal 3.9 - 5.8)",
        "CHOLESTEROL:  4.8 mmol/L    (Normal < 5.2)",
        "HEMOGLOBIN:   145 g/L        (Normal 130 - 170)",
        "CREATININE:   85 umol/L      (Normal 60 - 106)",
        "",
        "Interpretation: All values within normal limits.",
        "No follow-up required. Continue current regimen.",
        "",
        "Dr. Anna Kovac, Internal Medicine",
    ]
    y = 60
    for line in lines:
        d.text((60, y), line, fill="black")
        y += 42
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


# ---------- 1. Auth ----------
class TestAuth:
    def test_dev_bypass_returns_token(self, session_token):
        assert isinstance(session_token, str) and len(session_token) > 8


# ---------- 2. Magic Lens ----------
class TestMagicLens:
    ALLOWED_DETECTED = {
        "medications", "allergies", "vaccinations", "lab_results", "diagnoses",
        "surgeries", "doctor_visits", "insurance", "emergency_contacts", "other",
    }
    ALLOWED_LIFECARD = {"vaccine", "disease", "surgery", "injury", "exam", "dental"}

    def test_magic_lens_no_auth(self):
        r = requests.post(f"{API}/magic-lens", json={"image_base64": "abc"}, timeout=30)
        assert r.status_code == 401, f"expected 401, got {r.status_code}"

    def test_magic_lens_empty_body(self, auth_headers):
        r = requests.post(f"{API}/magic-lens", headers=auth_headers, json={"image_base64": ""}, timeout=30)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"

    def test_magic_lens_extracts_document(self, auth_headers):
        b64 = _fake_lab_result_b64()
        t0 = time.time()
        r = requests.post(
            f"{API}/magic-lens",
            headers=auth_headers,
            json={"image_base64": b64},
            timeout=LONG_TIMEOUT,
        )
        elapsed = time.time() - t0
        print(f"[magic-lens] elapsed={elapsed:.1f}s status={r.status_code}")
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:400]}"
        data = r.json()
        # Shape
        for k in ("found", "extracted_text", "summary", "detected_category",
                  "suggested_title", "lifecard_category"):
            assert k in data, f"missing key {k} in response {data}"
        assert data["found"] is True, f"AI did not find a document: {data}"
        assert isinstance(data["extracted_text"], str) and len(data["extracted_text"]) > 5, \
            f"extracted_text too short: {data['extracted_text']!r}"
        assert isinstance(data["summary"], str) and len(data["summary"]) > 10
        assert data["detected_category"] in self.ALLOWED_DETECTED
        assert data["lifecard_category"] in self.ALLOWED_LIFECARD
        assert isinstance(data["suggested_title"], str) and data["suggested_title"].strip()


# ---------- 3. Calendar / Life Card save ----------
class TestCalendarLifeCard:
    def test_create_and_verify_and_cleanup(self, auth_headers):
        today = date.today().isoformat()
        payload = {
            "category": "exam",
            "title": "TEST_ Magic Lens test event",
            "date": today,
            "notes": "TEST_ notes from magic lens flow",
        }
        # CREATE
        r = requests.post(f"{API}/calendar/events", headers=auth_headers, json=payload, timeout=30)
        assert r.status_code == 200, f"POST /calendar/events failed: {r.status_code} {r.text}"
        created = r.json()
        event_id = created.get("event_id")
        assert event_id, f"no event_id in {created}"
        assert created["category"] == "exam"
        assert created["title"].startswith("TEST_")

        # VERIFY via timeline
        r = requests.get(f"{API}/calendar/timeline", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        events = r.json().get("events", [])
        assert any(e.get("event_id") == event_id for e in events), \
            f"created event {event_id} not found in timeline"

        # DELETE (keep demo Life Card clean)
        r = requests.delete(f"{API}/calendar/events/{event_id}", headers=auth_headers, timeout=30)
        assert r.status_code == 200, f"DELETE failed: {r.status_code} {r.text}"

        # VERIFY deleted
        r = requests.get(f"{API}/calendar/timeline", headers=auth_headers, timeout=30)
        events = r.json().get("events", [])
        assert not any(e.get("event_id") == event_id for e in events), "event still present after delete"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
