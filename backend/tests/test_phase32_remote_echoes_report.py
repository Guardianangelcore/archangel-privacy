"""Phase 32 — REMOTE VOICE ECHOES + WEEKLY HEALING REPORT PDF + REFERRAL BRIDGE (backend part).
Focus: light backend regression for the new endpoints
- GET  /api/family/echoes/recipients
- POST /api/family/echoes/send  (happy + 403 not-guardian + 404 unknown email + 400 self)
- GET  /api/healing/report.pdf  (with active journey + zero-state)
"""
import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://angel-os-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "guardian_health")


@pytest.fixture(scope="module")
def duo():
    """Seed:
      - SENIOR   user_ph32_senior_* (with an active healing journey + one companion check-in)
      - FAMILY   user_ph32_family_* (guardian of the senior)
      - STRANGER user_ph32_stranger_* (NOT a guardian — for 403 branch)
    """
    mc = MongoClient(MONGO_URL)
    db = mc[DB_NAME]
    now = datetime.now(timezone.utc)

    def _mk_user(prefix, name):
        uid = f"user_ph32_{prefix}_{uuid.uuid4().hex[:8]}"
        tok = f"ph32-{prefix}-{uuid.uuid4().hex[:10]}"
        db.users.insert_one({
            "user_id": uid, "email": f"{uid}@test.sk", "did": f"did:guardian:{uid}",
            "name": name, "language": "sk", "angel_mode": False, "created_at": now,
            "tier": "sovereign", "tos_accepted_version": "v2026-06.1",
        })
        db.user_sessions.insert_one({
            "session_token": tok, "user_id": uid, "created_at": now,
            "expires_at": now + timedelta(days=1),
        })
        return uid, tok

    senior_id, senior_tok = _mk_user("senior", "Jaroslav Test")
    family_id, family_tok = _mk_user("family", "Lucka Test")
    stranger_id, stranger_tok = _mk_user("stranger", "Cudzia Osoba")

    # Guardian link: family is guardian of senior
    db.guardians.insert_one({
        "user_id": senior_id, "guardian_user_id": family_id,
        "name": "Lucka Test", "email": f"{family_id}@test.sk",
        "relation": "vnučka", "created_at": now,
    })

    # Seed a disability policy so financial_shield → done
    db.insurance_policies.insert_one({
        "policy_id": uuid.uuid4().hex, "user_id": senior_id, "type": "disability",
        "provider": "Allianz Test", "premium_monthly": 25.0, "created_at": now,
    })
    # Seed a companion check-in so PDF has a mood row
    db.companion_checkins.insert_one({
        "checkin_id": uuid.uuid4().hex, "user_id": senior_id, "mood": 4,
        "mood_label": "dobre", "note": "test", "topic": "sleep", "created_at": now,
    })

    data = {
        "senior_id": senior_id, "senior_tok": senior_tok, "senior_email": f"{senior_id}@test.sk",
        "family_id": family_id, "family_tok": family_tok, "family_email": f"{family_id}@test.sk",
        "stranger_id": stranger_id, "stranger_tok": stranger_tok, "db": db,
    }
    yield data

    # Teardown
    for uid in (senior_id, family_id, stranger_id):
        for col in ("users", "user_sessions", "insurance_policies", "insurance_claims",
                    "healing_journeys", "waitlist", "calendar_events", "neural_bus",
                    "companion_checkins", "voice_echoes", "emergency_profiles",
                    "recovery", "guardians"):
            db[col].delete_many({"user_id": uid})
            db[col].delete_many({"guardian_user_id": uid})
    mc.close()


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ===================== RECIPIENTS =====================

class TestRecipients:
    def test_family_sees_senior_in_recipients(self, duo):
        r = requests.get(f"{API}/family/echoes/recipients", headers=_hdr(duo["family_tok"]))
        assert r.status_code == 200, r.text
        data = r.json()
        assert "recipients" in data and isinstance(data["recipients"], list)
        assert "inner_circle_member" in data
        emails = [x["email"] for x in data["recipients"]]
        assert duo["senior_email"] in emails, f"expected {duo['senior_email']} in {emails}"
        # payload shape
        me = next(x for x in data["recipients"] if x["email"] == duo["senior_email"])
        assert me["user_id"] == duo["senior_id"]
        assert me["name"]  # not empty

    def test_stranger_has_empty_recipients(self, duo):
        r = requests.get(f"{API}/family/echoes/recipients", headers=_hdr(duo["stranger_tok"]))
        assert r.status_code == 200, r.text
        assert r.json()["recipients"] == []

    def test_senior_has_empty_recipients(self, duo):
        # Senior is not a guardian of anyone
        r = requests.get(f"{API}/family/echoes/recipients", headers=_hdr(duo["senior_tok"]))
        assert r.status_code == 200
        assert r.json()["recipients"] == []


# ===================== REMOTE SEND =====================

class TestRemoteEchoSend:
    def test_family_sends_remote_echo_happy(self, duo):
        payload = {"to_email": duo["senior_email"], "message": "Babička, ľúbime ťa! ❤️"}
        r = requests.post(f"{API}/family/echoes/send", headers=_hdr(duo["family_tok"]), json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert "echo" in data and "to" in data
        e = data["echo"]
        assert e["user_id"] == duo["senior_id"]
        assert e["remote"] is True
        assert e["sender_user_id"] == duo["family_id"]
        assert "Babička" in e["message"]
        # Senior should now see it in /family/echoes
        rl = requests.get(f"{API}/family/echoes", headers=_hdr(duo["senior_tok"]))
        assert rl.status_code == 200
        ids = [x["echo_id"] for x in rl.json()["echoes"]]
        assert e["echo_id"] in ids
        # DB side effect
        db = duo["db"]
        assert db.voice_echoes.count_documents(
            {"echo_id": e["echo_id"], "remote": True, "sender_user_id": duo["family_id"]}) == 1

    def test_stranger_send_403_not_guardian(self, duo):
        payload = {"to_email": duo["senior_email"], "message": "hi"}
        r = requests.post(f"{API}/family/echoes/send", headers=_hdr(duo["stranger_tok"]), json=payload)
        assert r.status_code == 403, r.text
        assert "oprávnenie" in r.text.lower() or "guardian" in r.text.lower() or "strážc" in r.text.lower()

    def test_send_404_unknown_email(self, duo):
        payload = {"to_email": f"ghost-{uuid.uuid4().hex[:6]}@nowhere.sk", "message": "hi"}
        r = requests.post(f"{API}/family/echoes/send", headers=_hdr(duo["family_tok"]), json=payload)
        assert r.status_code == 404, r.text

    def test_send_400_empty_message(self, duo):
        payload = {"to_email": duo["senior_email"], "message": "   "}
        r = requests.post(f"{API}/family/echoes/send", headers=_hdr(duo["family_tok"]), json=payload)
        assert r.status_code == 400, r.text

    def test_send_400_to_self(self, duo):
        payload = {"to_email": duo["family_email"], "message": "test"}
        r = requests.post(f"{API}/family/echoes/send", headers=_hdr(duo["family_tok"]), json=payload)
        assert r.status_code == 400, r.text


# ===================== WEEKLY HEALING REPORT PDF =====================

class TestHealingReportPdf:
    def test_report_zero_state_returns_pdf(self, duo):
        # stranger has no journey, no checkin — still must return a PDF
        r = requests.get(f"{API}/healing/report.pdf", headers=_hdr(duo["stranger_tok"]))
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 500  # non-empty PDF
        assert r.content[:4] == b"%PDF"

    def test_report_with_active_journey(self, duo):
        # First create an active journey for senior
        rj = requests.post(f"{API}/healing/injury-event", headers=_hdr(duo["senior_tok"]),
                           json={"kind": "injury", "specialty": "Ortopéd", "body_part": "Koleno"})
        assert rj.status_code == 200
        r = requests.get(f"{API}/healing/report.pdf", headers=_hdr(duo["senior_tok"]))
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        assert len(r.content) > 1000

    def test_report_via_token_query_param(self, duo):
        # PDF endpoint should also accept ?token= (for browser window.open)
        r = requests.get(f"{API}/healing/report.pdf?token={duo['senior_tok']}")
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_report_unauth_401(self):
        r = requests.get(f"{API}/healing/report.pdf")
        assert r.status_code in (401, 403), r.text
