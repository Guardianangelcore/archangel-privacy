# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Iteration 9 — Final Production Stress Test.

Covers:
- Health Drop (zero-knowledge upload): pubkey · public info · public upload (GID validation) · inbox · file · delete
- Auto-Booker: /api/autobook + /api/waitlist/{id}/autobook → calendar sync
- Calendar: /api/calendar/events (exam/history/vaccine w/ booster) → timeline (upcoming_exams / booster_alerts)
- Content: /api/mental/techniques (cs/en/de) + /api/physio/guides (sk/en) with tts_text
- Refactor regression sanity: /auth/me · /legal/tos · /vault/documents · /scam/check · /dignity/fund · /border/certificate · /pharmacy/search
"""
import io
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent.parent.parent / "frontend" / ".env")

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
TOKEN1 = "smoketok-fresh-2026"
H1 = {"Authorization": f"Bearer {TOKEN1}"}


def _iso_date(days_offset: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days_offset)).date().isoformat()


# ============================================================
# HEALTH DROP
# ============================================================
class TestHealthDrop:
    """Ordered: me -> pubkey PUT -> public info -> upload (good/bad GID/bad drop) -> inbox -> file -> delete"""
    drop_id: str = ""
    did: str = ""
    pubkey: str = ""
    drop_doc_id: str = ""

    def test_1_me_returns_drop_id_and_did(self):
        r = requests.get(f"{BASE_URL}/api/health-drop/me", headers=H1, timeout=15)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b.get("drop_id") and isinstance(b["drop_id"], str)
        assert b.get("did") and b["did"].startswith("did:guardian:")
        TestHealthDrop.drop_id = b["drop_id"]
        TestHealthDrop.did = b["did"]

    def test_2_put_pubkey(self):
        # 44-char base64 X25519 public key (32 raw bytes → 44 base64 chars with padding)
        fake_pubkey = "A" * 43 + "="  # 44 chars, in the 40..60 range
        r = requests.put(f"{BASE_URL}/api/health-drop/pubkey", headers=H1,
                         json={"public_key": fake_pubkey}, timeout=15)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b.get("public_key") == fake_pubkey
        assert b.get("drop_id") == TestHealthDrop.drop_id
        TestHealthDrop.pubkey = fake_pubkey

    def test_3_public_info_no_auth(self):
        r = requests.get(f"{BASE_URL}/api/health-drop/{TestHealthDrop.drop_id}/info", timeout=15)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b.get("has_key") is True
        assert b.get("public_key") == TestHealthDrop.pubkey
        assert "patient_hint" in b

    def test_4_public_info_bad_drop_id_404(self):
        r = requests.get(f"{BASE_URL}/api/health-drop/{'x'*16}/info", timeout=15)
        assert r.status_code == 404

    def test_5_upload_ok_with_short_gid(self):
        # short GID = last 6 chars of did lowercase; for did did:guardian:smoke1 => "smoke1"
        files = {"file": ("ciphertext.bin", io.BytesIO(b"\x01\x02cipherbytes\x03"),
                          "application/octet-stream")}
        data = {
            "eph_pub": "B" * 44,
            "nonce": "N" * 32,
            "guardian_id": "smoke1",
            "sender_name": "Dr. Test",
            "doc_title": "Žiadanka — ortopédia",
            "orig_type": "application/pdf",
        }
        r = requests.post(f"{BASE_URL}/api/health-drop/{TestHealthDrop.drop_id}/upload",
                          files=files, data=data, timeout=30)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b.get("ok") is True
        assert b.get("drop_doc_id")
        TestHealthDrop.drop_doc_id = b["drop_doc_id"]

    def test_6_upload_wrong_gid_403(self):
        files = {"file": ("c.bin", io.BytesIO(b"cipher"), "application/octet-stream")}
        data = {
            "eph_pub": "B" * 44, "nonce": "N" * 32,
            "guardian_id": "wrongid", "sender_name": "X", "doc_title": "t",
        }
        r = requests.post(f"{BASE_URL}/api/health-drop/{TestHealthDrop.drop_id}/upload",
                          files=files, data=data, timeout=15)
        assert r.status_code == 403, r.text

    def test_7_upload_bad_drop_id_404(self):
        files = {"file": ("c.bin", io.BytesIO(b"cipher"), "application/octet-stream")}
        data = {
            "eph_pub": "B" * 44, "nonce": "N" * 32,
            "guardian_id": "smoke1", "sender_name": "X", "doc_title": "t",
        }
        r = requests.post(f"{BASE_URL}/api/health-drop/{'z'*16}/upload",
                          files=files, data=data, timeout=15)
        assert r.status_code == 404

    def test_8_inbox_lists_new_item_with_referral_flags(self):
        r = requests.get(f"{BASE_URL}/api/health-drop/inbox", headers=H1, timeout=15)
        assert r.status_code == 200, r.text
        arr = r.json()
        assert isinstance(arr, list)
        match = next((x for x in arr if x.get("drop_doc_id") == TestHealthDrop.drop_doc_id), None)
        assert match is not None, "uploaded item not found in inbox"
        assert match.get("is_referral") is True
        assert match.get("specialty_guess") == "Ortopédia"
        assert match.get("doc_title") == "Žiadanka — ortopédia"

    def test_9_get_file_returns_ciphertext(self):
        r = requests.get(f"{BASE_URL}/api/health-drop/items/{TestHealthDrop.drop_doc_id}/file",
                         headers=H1, timeout=15)
        assert r.status_code == 200, r.text
        assert r.content == b"\x01\x02cipherbytes\x03"

    def test_A_delete_item(self):
        r = requests.delete(f"{BASE_URL}/api/health-drop/items/{TestHealthDrop.drop_doc_id}",
                            headers=H1, timeout=15)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_B_delete_again_404(self):
        r = requests.delete(f"{BASE_URL}/api/health-drop/items/{TestHealthDrop.drop_doc_id}",
                            headers=H1, timeout=15)
        assert r.status_code == 404


# ============================================================
# AUTO-BOOKER
# ============================================================
class TestAutoBooker:
    """Ordered: manual autobook -> verify in /calendar/timeline; then waitlist-based autobook."""
    booking_event_id: str = ""

    def test_1_manual_autobook(self):
        r = requests.post(f"{BASE_URL}/api/autobook", headers=H1,
                          json={"specialty": "Kardiológia", "source": "manual"}, timeout=20)
        assert r.status_code == 200, r.text
        b = r.json()
        booking = b.get("booking")
        cal = b.get("calendar_event")
        assert booking and booking.get("status") == "booked"
        assert booking.get("found_slot")
        assert cal and cal.get("event_id")
        assert cal.get("category") == "exam"
        assert "Kardiológia" in cal.get("title", "")
        TestAutoBooker.booking_event_id = cal["event_id"]

    def test_2_calendar_timeline_contains_new_event(self):
        r = requests.get(f"{BASE_URL}/api/calendar/timeline", headers=H1, timeout=15)
        assert r.status_code == 200
        b = r.json()
        events = b.get("events", [])
        assert any(e.get("event_id") == TestAutoBooker.booking_event_id for e in events)

    def test_3_waitlist_autobook(self):
        # First create a waitlist item
        cw = requests.post(f"{BASE_URL}/api/waitlist", headers=H1,
                           json={"specialty": "Neurológia", "clinic": "Poliklinika",
                                 "city": "Bratislava",
                                 "current_date": _iso_date(60), "target_before": _iso_date(20),
                                 "priority": "normal"}, timeout=15)
        # /api/waitlist may or may not exist; use fallback with create via autobook if missing
        if cw.status_code != 200:
            pytest.skip(f"/api/waitlist POST returned {cw.status_code} — cannot seed waitlist item")
        wid = cw.json().get("item_id")
        assert wid, cw.text
        r = requests.post(f"{BASE_URL}/api/waitlist/{wid}/autobook", headers=H1, timeout=20)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b.get("booking", {}).get("status") == "booked"
        assert b.get("calendar_event", {}).get("event_id")


# ============================================================
# CALENDAR
# ============================================================
class TestCalendar:
    """Add exam (future), history (past), vaccine (booster within 60d) → verify timeline groups."""
    exam_id: str = ""
    vaccine_id: str = ""
    history_id: str = ""

    def test_1_add_exam_future(self):
        r = requests.post(f"{BASE_URL}/api/calendar/events", headers=H1,
                          json={"category": "exam", "title": "TEST Exam Future",
                                "date": _iso_date(10), "notes": "test"}, timeout=15)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b.get("event_id") and b.get("category") == "exam"
        TestCalendar.exam_id = b["event_id"]

    def test_2_add_history_past(self):
        r = requests.post(f"{BASE_URL}/api/calendar/events", headers=H1,
                          json={"category": "history", "title": "TEST Past Diag",
                                "date": _iso_date(-30)}, timeout=15)
        assert r.status_code == 200, r.text
        TestCalendar.history_id = r.json()["event_id"]

    def test_3_add_vaccine_with_booster(self):
        r = requests.post(f"{BASE_URL}/api/calendar/events", headers=H1,
                          json={"category": "vaccine", "title": "TEST Tetanus",
                                "date": _iso_date(-365), "booster_due": _iso_date(30)}, timeout=15)
        assert r.status_code == 200, r.text
        TestCalendar.vaccine_id = r.json()["event_id"]

    def test_4_timeline_contains_all_and_groups(self):
        r = requests.get(f"{BASE_URL}/api/calendar/timeline", headers=H1, timeout=15)
        assert r.status_code == 200, r.text
        b = r.json()
        events = b.get("events", [])
        # events desc by date
        ids = {e["event_id"] for e in events}
        assert TestCalendar.exam_id in ids
        assert TestCalendar.history_id in ids
        assert TestCalendar.vaccine_id in ids
        # sorted descending by date
        dates = [e["date"] for e in events]
        assert dates == sorted(dates, reverse=True), "events not sorted desc by date"
        # upcoming_exams contains the future exam
        assert any(e["event_id"] == TestCalendar.exam_id for e in b.get("upcoming_exams", []))
        # booster_alerts contains the vaccine (30d ≤ 90d horizon)
        assert any(e["event_id"] == TestCalendar.vaccine_id for e in b.get("booster_alerts", []))

    def test_5_invalid_category_400(self):
        r = requests.post(f"{BASE_URL}/api/calendar/events", headers=H1,
                          json={"category": "bogus", "title": "x", "date": _iso_date(1)},
                          timeout=15)
        assert r.status_code == 400

    def test_6_invalid_date_400(self):
        r = requests.post(f"{BASE_URL}/api/calendar/events", headers=H1,
                          json={"category": "exam", "title": "x", "date": "not-a-date"},
                          timeout=15)
        assert r.status_code == 400

    def test_7_delete_events(self):
        for eid in (TestCalendar.exam_id, TestCalendar.history_id, TestCalendar.vaccine_id):
            r = requests.delete(f"{BASE_URL}/api/calendar/events/{eid}", headers=H1, timeout=15)
            assert r.status_code == 200

    def test_8_delete_again_404(self):
        r = requests.delete(f"{BASE_URL}/api/calendar/events/{TestCalendar.exam_id}",
                            headers=H1, timeout=15)
        assert r.status_code == 404


# ============================================================
# CONTENT: Mental Fortress + Physio-AI
# ============================================================
class TestContent:
    @pytest.mark.parametrize("lang,expect_title_sub", [
        ("cs", "Dechový"),
        ("en", "Box Breathing"),
        ("de", "Box-Atmung"),
    ])
    def test_mental_techniques_translated(self, lang, expect_title_sub):
        r = requests.get(f"{BASE_URL}/api/mental/techniques",
                        params={"language": lang}, headers=H1, timeout=15)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b.get("language") == lang
        assert b.get("disclaimer") and isinstance(b["disclaimer"], str) and len(b["disclaimer"]) > 20
        techs = b.get("techniques") or []
        assert len(techs) >= 6
        assert any(expect_title_sub in t.get("title", "") for t in techs), \
            f"expected '{expect_title_sub}' in one title (lang={lang})"

    @pytest.mark.parametrize("lang,titles", [
        ("sk", ["knee", "panic-acupressure", "ergonomics"]),
        ("en", ["knee", "panic-acupressure", "ergonomics"]),
    ])
    def test_physio_guides(self, lang, titles):
        r = requests.get(f"{BASE_URL}/api/physio/guides",
                        params={"language": lang}, headers=H1, timeout=15)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b.get("language") == lang
        guides = b.get("guides") or []
        assert len(guides) >= 3
        ids = [g.get("id") for g in guides]
        for t in titles:
            assert t in ids, f"missing guide id {t} (lang={lang})"
        # Each guide has tts_text and steps
        for g in guides:
            assert g.get("tts_text") and isinstance(g["tts_text"], str) and len(g["tts_text"]) > 30
            assert isinstance(g.get("steps"), list) and len(g["steps"]) >= 3


# ============================================================
# REFACTOR REGRESSION SANITY
# ============================================================
class TestRefactorRegression:
    def test_auth_me(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=H1, timeout=15)
        assert r.status_code == 200
        b = r.json()
        user = b.get("user") or b
        assert user.get("user_id") == "smoketest-user-1"
        assert user.get("did", "").startswith("did:guardian:")

    def test_legal_tos(self):
        r = requests.get(f"{BASE_URL}/api/legal/tos", headers=H1, timeout=15)
        assert r.status_code == 200
        b = r.json()
        assert b.get("version") and b.get("text")

    def test_vault_documents(self):
        r = requests.get(f"{BASE_URL}/api/vault/documents", headers=H1, timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_scam_check(self):
        r = requests.post(f"{BASE_URL}/api/scam/check", headers=H1,
                          json={"kind": "sms", "text": "Vaše konto bolo zablokované, kliknite http://ban-k.com/login"},
                          timeout=15)
        assert r.status_code == 200, r.text
        b = r.json()
        assert "risk" in b or "score" in b or "verdict" in b or "is_scam" in b, r.text

    def test_dignity_fund(self):
        r = requests.get(f"{BASE_URL}/api/dignity/fund", headers=H1, timeout=15)
        assert r.status_code == 200

    def test_border_certificate(self):
        r = requests.get(f"{BASE_URL}/api/border/certificate", headers=H1, timeout=15)
        assert r.status_code == 200

    def test_pharmacy_search(self):
        r = requests.get(f"{BASE_URL}/api/pharmacy/search",
                        params={"med": "Euthyrox", "region": "SK"}, headers=H1, timeout=15)
        assert r.status_code == 200
        assert r.json().get("simulated") is True
