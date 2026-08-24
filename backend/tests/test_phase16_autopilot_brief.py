# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
"""Phase 16: Jarvis Autopilot (Medical Sentinel) + Daily Brief tests."""
import io
import os
import time
import pytest
import requests
from reportlab.pdfgen import canvas

BASE_URL = (os.environ.get("EXPO_BACKEND_URL")
            or os.environ.get("EXPO_PUBLIC_BACKEND_URL")
            or "https://angel-os-1.preview.emergentagent.com").rstrip("/")
TOKEN = "smoketok-fresh-2026"
H = {"Authorization": f"Bearer {TOKEN}"}


def _make_pdf(text: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for line in text.split("\n"):
        c.drawString(50, y, line)
        y -= 20
    c.showPage()
    c.save()
    return buf.getvalue()


def _upload(title: str, body_text: str) -> dict:
    pdf = _make_pdf(body_text)
    files = {"file": (f"{title}.pdf", pdf, "application/pdf")}
    data = {"title": title}
    r = requests.post(f"{BASE_URL}/api/vault/documents", headers=H, files=files, data=data, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def _wait_action(doc_id: str, timeout: int = 45) -> dict | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(f"{BASE_URL}/api/jarvis/actions", headers=H, timeout=15)
        assert r.status_code == 200
        for a in r.json().get("actions", []):
            if a.get("doc_id") == doc_id:
                return a
        time.sleep(3)
    return None


# ------------------- Autopilot -------------------
class TestAutopilotUpload:
    def test_upload_with_specialty_triggers_autopilot(self):
        doc = _upload("TEST žiadanka ortopédia",
                      "Vyšetrenie ortopedické. Bolesť kolena. Odporúčam ortopéda.")
        assert doc.get("autopilot") == "started"
        doc_id = doc["doc_id"]
        act = _wait_action(doc_id)
        assert act is not None, "No autopilot action produced within 45s"
        steps = {s["step"]: s for s in act["steps"]}
        assert steps["OCR"]["status"] == "ok"
        assert steps["AI Prekladač"]["status"] == "ok"
        assert steps["Auto-Booker"]["status"] == "ok"
        assert act["specialty"] == "Ortopédia"
        assert act["booked_slot"]

        # calendar event created
        r = requests.get(f"{BASE_URL}/api/calendar/timeline", headers=H, timeout=15)
        assert r.status_code == 200
        events = r.json()["events"]
        assert any(e.get("source") == f"autopilot:{doc_id}" for e in events)

        # cleanup
        requests.delete(f"{BASE_URL}/api/vault/documents/{doc_id}", headers=H, timeout=15)

    def test_upload_without_specialty_skips_booker(self):
        doc = _upload("TEST poznamky", "Poznamky zo stretnutia. Nic zdravotnicke.")
        assert doc.get("autopilot") == "started"
        act = _wait_action(doc["doc_id"])
        assert act is not None
        steps = {s["step"]: s for s in act["steps"]}
        assert steps["Auto-Booker"]["status"] == "skipped"
        assert act.get("booked_slot") in (None, "")
        requests.delete(f"{BASE_URL}/api/vault/documents/{doc['doc_id']}", headers=H, timeout=15)

    def test_autopilot_toggle_off_skips_orchestration(self):
        r = requests.put(f"{BASE_URL}/api/jarvis/autopilot", headers=H, json={"enabled": False}, timeout=15)
        assert r.status_code == 200 and r.json()["jarvis_autopilot"] is False
        try:
            doc = _upload("TEST autopilot off", "Ortopédia test toggle off.")
            assert "autopilot" not in doc
            time.sleep(4)
            r2 = requests.get(f"{BASE_URL}/api/jarvis/actions", headers=H, timeout=15)
            assert not any(a["doc_id"] == doc["doc_id"] for a in r2.json()["actions"])
            requests.delete(f"{BASE_URL}/api/vault/documents/{doc['doc_id']}", headers=H, timeout=15)
        finally:
            requests.put(f"{BASE_URL}/api/jarvis/autopilot", headers=H, json={"enabled": True}, timeout=15)

    def test_manual_orchestrate_404(self):
        r = requests.post(f"{BASE_URL}/api/jarvis/orchestrate/does-not-exist", headers=H, timeout=15)
        assert r.status_code == 404

    def test_jarvis_actions_sorted_newest_first(self):
        r = requests.get(f"{BASE_URL}/api/jarvis/actions", headers=H, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "autopilot" in data and isinstance(data["autopilot"], bool)
        acts = data["actions"]
        for a, b in zip(acts, acts[1:]):
            assert a["created_at"] >= b["created_at"]


# ------------------- Daily Brief -------------------
class TestDailyBrief:
    def test_daily_brief_shape(self):
        r = requests.get(f"{BASE_URL}/api/daily-brief", headers=H, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("date", "name", "meds", "events_today", "events_upcoming",
                  "family", "recovery", "gat_balance", "jarvis_last_action"):
            assert k in d, f"missing {k}"
        assert "items" in d["meds"] and "pending" in d["meds"]
        assert "pending_pulse" in d["family"] and "emergency_contact" in d["family"]

    def test_daily_brief_meds_integration(self):
        r = requests.post(f"{BASE_URL}/api/meds/reminders", headers=H,
                          json={"name": "TEST Test liek", "dose": "1 tbl", "times": ["08:00"]}, timeout=15)
        assert r.status_code == 200
        rem = r.json()
        rid = rem["reminder_id"]
        try:
            b = requests.get(f"{BASE_URL}/api/daily-brief", headers=H, timeout=15).json()
            items = [m for m in b["meds"]["items"] if m["reminder_id"] == rid]
            assert items and items[0]["taken"] is False
            pending_before = b["meds"]["pending"]

            r2 = requests.post(f"{BASE_URL}/api/meds/intake", headers=H,
                               json={"reminder_id": rid, "time": "08:00"}, timeout=15)
            assert r2.status_code == 200

            b2 = requests.get(f"{BASE_URL}/api/daily-brief", headers=H, timeout=15).json()
            items2 = [m for m in b2["meds"]["items"] if m["reminder_id"] == rid]
            assert items2 and items2[0]["taken"] is True
            assert b2["meds"]["pending"] == pending_before - 1
        finally:
            requests.delete(f"{BASE_URL}/api/meds/reminders/{rid}", headers=H, timeout=15)


# ------------------- Regression -------------------
class TestRegression:
    def test_ocr_endpoint_still_works(self):
        r = requests.get(f"{BASE_URL}/api/vault/documents", headers=H, timeout=15)
        assert r.status_code == 200
        docs = r.json()
        if not docs:
            pytest.skip("no docs to OCR")
        doc = docs[0]
        r2 = requests.post(f"{BASE_URL}/api/vault/documents/{doc['doc_id']}/ocr",
                           headers=H, timeout=60)
        assert r2.status_code in (200, 422), r2.text
        if r2.status_code == 200:
            assert "extracted_text" in r2.json()
