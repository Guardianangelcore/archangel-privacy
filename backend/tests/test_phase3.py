# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Phase 3 backend tests — Guardian Angel: OCR, Wellness, Push, extended prefs.

Covers:
- PATCH /api/me/prefs with new guard fields
- OCR (image + text-PDF)
- AI translate-document uses stored extracted_text
- Wellness: checkin, vitals upsert, inactivity-alert, dashboard
- /api/register-push (placeholder key -> 500 expected)
- Waitlist scan (push failure must be non-blocking)
"""
import io
import os
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
import requests
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import A4
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") if os.environ.get("EXPO_PUBLIC_BACKEND_URL") else "https://angel-os-1.preview.emergentagent.com"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

SESSION_TOKEN = f"TEST_p3_{uuid.uuid4().hex}"
USER_ID = f"TEST_p3_user_{uuid.uuid4().hex[:10]}"
DID = f"did:guardian:TESTP3{uuid.uuid4().hex[:18]}"
EMAIL = f"TEST_p3_{uuid.uuid4().hex[:6]}@example.com"


@pytest.fixture(scope="module")
def seed():
    async def _seed():
        c = AsyncIOMotorClient(MONGO_URL)
        db = c[DB_NAME]
        await db.users.insert_one({
            "user_id": USER_ID, "email": EMAIL, "did": DID,
            "name": "TEST Phase3", "language": "sk", "angel_mode": False,
            "fall_guard": False, "inactivity_guard": False, "inactivity_hours": 6,
            "created_at": datetime.now(timezone.utc),
        })
        await db.user_sessions.insert_one({
            "session_token": SESSION_TOKEN, "user_id": USER_ID,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        })
        c.close()

    async def _teardown():
        c = AsyncIOMotorClient(MONGO_URL)
        db = c[DB_NAME]
        await db.users.delete_one({"user_id": USER_ID})
        await db.user_sessions.delete_one({"session_token": SESSION_TOKEN})
        await db.documents.delete_many({"user_id": USER_ID})
        await db.wellness_checkins.delete_many({"user_id": USER_ID})
        await db.wellness_vitals.delete_many({"user_id": USER_ID})
        await db.inactivity_alerts.delete_many({"user_id": USER_ID})
        await db.waitlist.delete_many({"user_id": USER_ID})
        await db.fall_events.delete_many({"user_id": USER_ID})
        c.close()

    asyncio.get_event_loop().run_until_complete(_seed())
    yield {"token": SESSION_TOKEN, "user_id": USER_ID, "did": DID}
    asyncio.get_event_loop().run_until_complete(_teardown())


@pytest.fixture
def auth(seed):
    return {"Authorization": f"Bearer {seed['token']}"}


# ---------------- prefs (fall_guard / inactivity) ----------------
def test_prefs_guard_fields_persist(auth):
    r = requests.patch(f"{BASE_URL}/api/me/prefs", headers=auth,
                       json={"fall_guard": True, "inactivity_guard": True, "inactivity_hours": 8})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["fall_guard"] is True
    assert d["inactivity_guard"] is True
    assert d["inactivity_hours"] == 8
    # verify persistence via /auth/me
    r2 = requests.get(f"{BASE_URL}/api/auth/me", headers=auth)
    assert r2.status_code == 200
    u = r2.json()["user"]
    assert u["fall_guard"] is True
    assert u["inactivity_guard"] is True
    assert u["inactivity_hours"] == 8


# ---------------- OCR: image ----------------
def _make_text_png(text_lines):
    img = Image.new("RGB", (900, 500), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
    except Exception:
        font = ImageFont.load_default()
    y = 40
    for line in text_lines:
        d.text((40, y), line, fill=(0, 0, 0), font=font)
        y += 60
    # add a light box to give visual features (non-uniform variance)
    d.rectangle([20, 20, 880, 480], outline=(20, 60, 120), width=3)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def uploaded_image_doc(seed):
    png = _make_text_png(["PATIENT: John Smith", "Blood Pressure: 138/85 mmHg", "Cholesterol LDL: 4.2"])
    files = {"file": ("labs.png", io.BytesIO(png), "image/png")}
    r = requests.post(f"{BASE_URL}/api/vault/documents",
                      headers={"Authorization": f"Bearer {seed['token']}"},
                      files=files, data={"title": "TEST Labs PNG"}, timeout=60)
    assert r.status_code == 200, r.text
    return r.json()


def test_ocr_image_extracts_text(auth, uploaded_image_doc):
    doc_id = uploaded_image_doc["doc_id"]
    r = requests.post(f"{BASE_URL}/api/vault/documents/{doc_id}/ocr", headers=auth, timeout=120)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "extracted_text" in d
    text = d["extracted_text"].lower()
    # Expect at least one of the drawn strings to appear (allow OCR variance)
    assert any(k in text for k in ["patient", "john smith", "blood pressure", "138", "cholesterol", "ldl"]), f"OCR text unexpected: {d['extracted_text'][:400]}"


def test_ocr_image_cached_second_call(auth, uploaded_image_doc):
    doc_id = uploaded_image_doc["doc_id"]
    r = requests.post(f"{BASE_URL}/api/vault/documents/{doc_id}/ocr", headers=auth, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d.get("cached") is True
    assert d.get("extracted_text")


# ---------------- OCR: text PDF via pypdf ----------------
def _make_text_pdf():
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica", 14)
    c.drawString(60, 780, "MEDICAL REPORT")
    c.drawString(60, 750, "Patient: Anna Novak")
    c.drawString(60, 720, "Diagnosis: mild hypertension, LDL 3.8 mmol/L")
    c.drawString(60, 690, "Recommendation: repeat blood test in 3 months.")
    c.showPage()
    c.save()
    return buf.getvalue()


@pytest.fixture(scope="module")
def uploaded_pdf_doc(seed):
    pdf = _make_text_pdf()
    files = {"file": ("report.pdf", io.BytesIO(pdf), "application/pdf")}
    r = requests.post(f"{BASE_URL}/api/vault/documents",
                      headers={"Authorization": f"Bearer {seed['token']}"},
                      files=files, data={"title": "TEST Report PDF"}, timeout=60)
    assert r.status_code == 200, r.text
    return r.json()


def test_ocr_pdf_extracts_text(auth, uploaded_pdf_doc):
    doc_id = uploaded_pdf_doc["doc_id"]
    r = requests.post(f"{BASE_URL}/api/vault/documents/{doc_id}/ocr", headers=auth, timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    text = d["extracted_text"].lower()
    assert "anna novak" in text or "hypertension" in text or "medical report" in text, f"PDF OCR unexpected: {d['extracted_text'][:400]}"


# ---------------- translate-document uses stored extracted_text ----------------
def test_translate_document_uses_extracted_text(auth, uploaded_pdf_doc):
    doc_id = uploaded_pdf_doc["doc_id"]
    r = requests.post(f"{BASE_URL}/api/ai/translate-document", headers=auth,
                      json={"doc_id": doc_id, "language": "sk"}, timeout=120)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "plain_language" in body
    reply = body["plain_language"].lower()
    # Should reference concrete document contents (hypertension/LDL/anna) not just generic guidance
    assert any(k in reply for k in ["hypertenz", "ldl", "3.8", "anna", "novak", "krv", "cholester"]), f"Reply looks generic: {body['plain_language'][:400]}"


# ---------------- Wellness check-in ----------------
def test_wellness_checkin_and_list(auth):
    r = requests.post(f"{BASE_URL}/api/wellness/checkin", headers=auth,
                      json={"mood": 4, "feeling_text": "Cítim sa dobre, trochu ma bolí koleno", "language": "sk"},
                      timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("reply") and len(d["reply"]) > 5
    assert isinstance(d.get("sentiment_score"), int) and 1 <= d["sentiment_score"] <= 5
    assert d.get("summary")

    r2 = requests.get(f"{BASE_URL}/api/wellness/checkins", headers=auth)
    assert r2.status_code == 200
    lst = r2.json()
    assert any(c["checkin_id"] == d["checkin_id"] for c in lst)


# ---------------- Wellness vitals upsert ----------------
def test_wellness_vitals_upsert_same_day(auth):
    r1 = requests.post(f"{BASE_URL}/api/wellness/vitals", headers=auth, json={"steps": 4200})
    assert r1.status_code == 200, r1.text
    assert r1.json().get("steps") == 4200

    r2 = requests.post(f"{BASE_URL}/api/wellness/vitals", headers=auth, json={"heart_rate": 72})
    assert r2.status_code == 200, r2.text
    d = r2.json()
    assert d.get("steps") == 4200, f"steps lost on 2nd upsert: {d}"
    assert d.get("heart_rate") == 72


# ---------------- Wellness inactivity alert (push failure non-blocking) ----------------
def test_wellness_inactivity_alert_nonblocking(auth):
    r = requests.post(f"{BASE_URL}/api/wellness/inactivity-alert", headers=auth,
                      json={"hours_inactive": 6})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("hours_inactive") == 6
    assert d.get("alert_id")


# ---------------- Wellness dashboard ----------------
def test_wellness_dashboard_shape(auth):
    r = requests.get(f"{BASE_URL}/api/wellness/dashboard", headers=auth)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ["checkins", "vitals", "fall_events", "inactivity_alerts",
              "avg_steps", "avg_heart_rate", "anomalies", "checked_in_today"]:
        assert k in d, f"missing key {k}"
    assert isinstance(d["checkins"], list)
    assert isinstance(d["vitals"], list)
    assert isinstance(d["anomalies"], list)
    assert isinstance(d["checked_in_today"], bool)


# ---------------- register-push placeholder key ----------------
def test_register_push_placeholder_returns_500():
    r = requests.post(f"{BASE_URL}/api/register-push",
                      json={"user_id": USER_ID, "platform": "android", "device_token": "TEST_tok"},
                      timeout=30)
    # Expected: 500 with explicit message when EMERGENT_PUSH_KEY is 'placeholder'
    assert r.status_code in (500, 502), f"got {r.status_code}: {r.text}"
    if r.status_code == 500:
        assert "EMERGENT_PUSH_KEY" in r.text or "missing" in r.text.lower()


# ---------------- waitlist scan still works (push failure non-blocking) ----------------
def test_waitlist_scan_nonblocking_push(auth):
    p = {"specialty": "Cardiology", "clinic": "TEST P3 Clinic", "city": "Bratislava",
         "current_date": "2026-08-01", "target_before": "2026-05-01", "priority": "high"}
    r = requests.post(f"{BASE_URL}/api/waitlist", headers=auth, json=p)
    assert r.status_code == 200, r.text
    item_id = r.json()["item_id"]

    # Loop a few scans to hit the 35% found branch (which triggers push send)
    got_found = False
    for _ in range(12):
        rs = requests.post(f"{BASE_URL}/api/waitlist/{item_id}/scan", headers=auth, timeout=30)
        assert rs.status_code == 200, rs.text
        if rs.json().get("found"):
            got_found = True
            break
    # cleanup
    requests.delete(f"{BASE_URL}/api/waitlist/{item_id}", headers=auth)
    # We don't require found=True to happen (probabilistic), but every call must have been 200
    assert True


# ---------------- Regression: /auth/me + fall-event + translate ----------------
def test_regression_auth_me_and_fall_event(auth, seed):
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=auth)
    assert r.status_code == 200
    assert r.json()["user"]["did"] == seed["did"]

    r2 = requests.post(f"{BASE_URL}/api/fall-event", headers=auth,
                       json={"verified": True, "cancelled": False})
    assert r2.status_code == 200, r2.text
    assert r2.json()["verified"] is True


def test_regression_ai_translate(auth):
    r = requests.post(f"{BASE_URL}/api/ai/translate", headers=auth,
                      json={"text": "Elevated blood glucose 8.2 mmol/L.", "language": "sk"},
                      timeout=90)
    assert r.status_code == 200, r.text
    assert len(r.json().get("plain_language", "")) > 20
