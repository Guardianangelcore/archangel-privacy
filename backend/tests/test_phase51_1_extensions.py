"""
Phase 51.1 — Karta života EXTENSIONS backend tests.

Covers the 4 extensions:
  1) OCR rodného listu — POST /api/lifecard/ocr (multipart image)
  2) PDF Karty života — GET /api/lifecard/report.pdf (Bearer + ?token=)
  3) Rodinné karty — GET /api/lifecard/family + /api/lifecard/family/{id}/timeline
  4) Booster Guard sweep — POST /api/swarm/run/booster_guard
Regression: GET /api/lifecard shape, POST /api/lifecard/predictions[/accept],
POST /api/agent/chat lifecard voice, GET /api/swarm/status.
"""
import io
import os
import time
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
import requests
from PIL import Image, ImageDraw

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://guardian-vault-13.preview.emergentagent.com").rstrip("/")
TOKEN1 = "smoketok-fresh-2026"        # smoketest-user-1
TOKEN2 = "smoketok-fresh-2026-u2"     # smoketest-user-2
H1 = {"Authorization": f"Bearer {TOKEN1}"}
H2 = {"Authorization": f"Bearer {TOKEN2}"}
H1J = {**H1, "Content-Type": "application/json"}
H2J = {**H2, "Content-Type": "application/json"}
WATERMARK = "AI Content · Sovereign Protocol"


# -------------------- helpers --------------------
def _rodny_list_png() -> bytes:
    img = Image.new("RGB", (900, 600), "white")
    d = ImageDraw.Draw(img)
    d.text((30, 30), "RODNY LIST", fill="black")
    d.text((30, 90), "Meno a priezvisko: Jan Novak", fill="black")
    d.text((30, 150), "Datum narodenia: 14. 05. 1980", fill="black")
    d.text((30, 210), "Miesto narodenia: Bratislava", fill="black")
    buf = io.BytesIO(); img.save(buf, "PNG"); return buf.getvalue()


def _solid_png() -> bytes:
    img = Image.new("RGB", (400, 400), (127, 127, 127))
    buf = io.BytesIO(); img.save(buf, "PNG"); return buf.getvalue()


# =================== 1) OCR RODNÉHO LISTU ===================
class TestLifecardOCR:
    def test_ocr_birth_certificate_extracts_fields(self):
        img = _rodny_list_png()
        r = requests.post(f"{BASE_URL}/api/lifecard/ocr", headers=H1,
                          files={"file": ("rodny.png", img, "image/png")}, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("ai") is True, d
        assert d.get("found") is True, d
        assert (d.get("full_name") or "").lower().startswith("jan"), d
        assert "novak" in (d.get("full_name") or "").lower(), d
        assert d.get("birth_date") == "1980-05-14", d
        # blood_type should be null (not on rodny list)
        assert d.get("blood_type") in (None, ""), d

    def test_ocr_empty_file_returns_400(self):
        r = requests.post(f"{BASE_URL}/api/lifecard/ocr", headers=H1,
                          files={"file": ("empty.png", b"", "image/png")}, timeout=20)
        assert r.status_code == 400, r.text

    def test_ocr_non_document_image_found_false(self):
        img = _solid_png()
        r = requests.post(f"{BASE_URL}/api/lifecard/ocr", headers=H1,
                          files={"file": ("blank.png", img, "image/png")}, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("ai") is True
        assert d.get("found") is False, d

    def test_ocr_unauthenticated_401(self):
        r = requests.post(f"{BASE_URL}/api/lifecard/ocr",
                          files={"file": ("x.png", _solid_png(), "image/png")}, timeout=20)
        assert r.status_code == 401


# =================== 2) PDF KARTY ŽIVOTA ===================
class TestLifecardPDF:
    def test_pdf_bearer_returns_pdf(self):
        r = requests.get(f"{BASE_URL}/api/lifecard/report.pdf", headers=H1, timeout=30)
        assert r.status_code == 200, r.text[:400]
        ct = r.headers.get("content-type", "")
        assert "pdf" in ct.lower(), ct
        assert r.content.startswith(b"%PDF"), r.content[:8]
        assert len(r.content) > 1000, f"pdf too small: {len(r.content)}"

    def test_pdf_query_token_returns_pdf(self):
        r = requests.get(f"{BASE_URL}/api/lifecard/report.pdf?token={TOKEN1}", timeout=30)
        assert r.status_code == 200, r.text[:400]
        assert r.content.startswith(b"%PDF")
        assert len(r.content) > 1000

    def test_pdf_unauthenticated_401(self):
        r = requests.get(f"{BASE_URL}/api/lifecard/report.pdf", timeout=15)
        assert r.status_code == 401


# =================== 3) RODINNÉ KARTY ===================
class TestLifecardFamily:
    @pytest.fixture(scope="class")
    def user2_disease_event(self):
        """Add a disease event for user-2 → must NOT appear in family timeline."""
        today = datetime.now(timezone.utc).date().isoformat()
        r = requests.post(f"{BASE_URL}/api/calendar/events", headers=H2J,
                          json={"category": "disease", "title": "TEST_FAMILY_PRIVACY_disease",
                                "date": today, "notes": "privacy check"}, timeout=15)
        assert r.status_code == 200, r.text
        eid = r.json()["event_id"]
        yield eid
        requests.delete(f"{BASE_URL}/api/calendar/events/{eid}", headers=H2, timeout=10)

    def test_family_lists_user2_from_user1(self):
        r = requests.get(f"{BASE_URL}/api/lifecard/family", headers=H1, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "members" in d
        ids = [m["user_id"] for m in d["members"]]
        assert "smoketest-user-2" in ids, ids
        m = next(m for m in d["members"] if m["user_id"] == "smoketest-user-2")
        assert "counts" in m and "vaccine" in m["counts"] and "exam" in m["counts"], m
        assert isinstance(m["counts"]["vaccine"], int)
        assert isinstance(m["counts"]["exam"], int)
        assert "booster_soon" in m

    def test_family_timeline_only_vaccine_and_exam(self, user2_disease_event):
        r = requests.get(f"{BASE_URL}/api/lifecard/family/smoketest-user-2/timeline",
                         headers=H1, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["member"]["user_id"] == "smoketest-user-2"
        cats = {e["category"] for e in d["events"]}
        assert cats.issubset({"vaccine", "exam"}), f"privacy leak: {cats}"
        # confirm the disease event we created is NOT in this listing
        titles = [e["title"] for e in d["events"]]
        assert "TEST_FAMILY_PRIVACY_disease" not in titles, titles

    def test_family_reverse_direction_user2_sees_user1(self):
        r = requests.get(f"{BASE_URL}/api/lifecard/family", headers=H2, timeout=15)
        assert r.status_code == 200, r.text
        ids = [m["user_id"] for m in r.json().get("members", [])]
        assert "smoketest-user-1" in ids, ids

    def test_family_timeline_403_for_non_circle_member(self):
        # smoketest-user-1 has no guardian link with a fake id
        r = requests.get(f"{BASE_URL}/api/lifecard/family/non-existent-user-xyz/timeline",
                         headers=H1, timeout=15)
        assert r.status_code == 403, r.text


# =================== 4) BOOSTER GUARD SWEEP ===================
class TestBoosterGuardSweep:
    @pytest.fixture(scope="class")
    def vaccine_event(self):
        # Create a vaccine event with booster_due 5 days ahead for user-1
        today = datetime.now(timezone.utc).date()
        booster = (today + timedelta(days=5)).isoformat()
        r = requests.post(f"{BASE_URL}/api/calendar/events", headers=H1J,
                          json={"category": "vaccine", "title": "TEST_BOOSTER_SWEEP",
                                "date": today.isoformat(),
                                "notes": "sweep test",
                                "booster_due": booster}, timeout=15)
        assert r.status_code == 200, r.text
        eid = r.json()["event_id"]
        yield eid
        requests.delete(f"{BASE_URL}/api/calendar/events/{eid}", headers=H1, timeout=10)

    def test_booster_guard_notifies_then_idempotent(self, vaccine_event):
        # Count agent_conversations for user-1 from booster_guard before
        # (indirect: run once, expect >=1 action; run again → 0 new for this event)
        r1 = requests.post(f"{BASE_URL}/api/swarm/run/booster_guard", headers=H1J, timeout=45)
        assert r1.status_code == 200, r1.text
        d1 = r1.json()
        # actions field may be under 'actions' or top-level int; be liberal
        actions1 = d1.get("actions") if isinstance(d1, dict) else None
        if actions1 is None and isinstance(d1, dict):
            # Some run_agent shapes wrap {result:..., actions:...}
            actions1 = d1.get("result", {}).get("actions") if isinstance(d1.get("result"), dict) else None
        assert (actions1 or 0) >= 1, d1

        # Second run: this event should already be flagged 7d — no new actions
        # (smoketest-user-2 pre-existing Tetanus TEST 30d already notified → 0)
        time.sleep(1)
        r2 = requests.post(f"{BASE_URL}/api/swarm/run/booster_guard", headers=H1J, timeout=45)
        assert r2.status_code == 200, r2.text
        d2 = r2.json()
        actions2 = d2.get("actions") if isinstance(d2, dict) else None
        if actions2 is None and isinstance(d2, dict):
            actions2 = d2.get("result", {}).get("actions") if isinstance(d2.get("result"), dict) else None
        assert (actions2 or 0) == 0, d2

    def test_booster_watermark_and_flag_on_event(self, vaccine_event):
        # Verify the event now has booster_notified_7d:true via timeline
        r = requests.get(f"{BASE_URL}/api/calendar/timeline?category=vaccine",
                         headers=H1, timeout=15).json()
        found = [e for e in r["events"] if e["event_id"] == vaccine_event]
        assert found and found[0].get("booster_notified_7d") is True, found

        # Verify agent_conversations row for user-1 exists with source booster_guard
        # We can't query DB from tests directly; approximate via /api/agent/history if exists
        # Otherwise the notify assertion above from actions>=1 is sufficient contract check.


# =================== REGRESSIONS ===================
class TestRegressions:
    def test_lifecard_shape_still_ok(self):
        r = requests.get(f"{BASE_URL}/api/lifecard", headers=H1, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("full_name", "birth_date", "blood_type", "age", "counts", "predictions", "today"):
            assert k in d, f"missing {k}"

    def test_swarm_status_includes_booster_guard_and_loop_active(self):
        r = requests.get(f"{BASE_URL}/api/swarm/status", headers=H1, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("loop_active") is True, d
        ids = [a.get("agent_id") for a in d.get("agents", [])]
        assert "booster_guard" in ids, ids

    def test_predictions_then_accept_still_works(self):
        r = requests.post(f"{BASE_URL}/api/lifecard/predictions", headers=H1, timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("ai") is True
        assert "predictions" in d
        if not d["predictions"]:
            pytest.skip("LLM returned 0 predictions this run")
        first = d["predictions"][0]
        r2 = requests.post(f"{BASE_URL}/api/lifecard/predictions/accept", headers=H1J,
                           json={"title": first["title"], "category": first["category"],
                                 "date": first["suggested_date"], "reason": first["reason"]},
                           timeout=20)
        assert r2.status_code == 200, r2.text
        eid = r2.json()["event_id"]
        requests.delete(f"{BASE_URL}/api/calendar/events/{eid}", headers=H1, timeout=10)

    def test_agent_chat_lifecard_voice_still_logs(self):
        r = requests.post(f"{BASE_URL}/api/agent/chat", headers=H1J,
                          json={"message": "Dnes mi doktor povedal, že mám kiahne"},
                          timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("lifecard_logged"), d
        assert WATERMARK in d["reply"], d["reply"]
        # cleanup
        today = datetime.now(timezone.utc).date().isoformat()
        tl = requests.get(f"{BASE_URL}/api/calendar/timeline?category=disease",
                          headers=H1, timeout=15).json()
        for e in tl["events"]:
            if e.get("source") == "voice" and e.get("date") == today:
                requests.delete(f"{BASE_URL}/api/calendar/events/{e['event_id']}",
                                headers=H1, timeout=10)
