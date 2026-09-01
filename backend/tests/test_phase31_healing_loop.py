"""Phase 31 — SOVEREIGN HEALING LOOP + Companion + Voice Echoes + Jarvis context.
Uses a FRESH seeded user to guarantee clean-state assertions (independent from
smoketest-user-1 which already has an active healing journey from main-agent curl).
"""
import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "guardian_health")


@pytest.fixture(scope="module")
def fresh_user():
    """Seed a fresh user + session directly in Mongo for isolated Phase 31 tests."""
    mc = MongoClient(MONGO_URL)
    db = mc[DB_NAME]
    uid = f"user_ph31_{uuid.uuid4().hex[:10]}"
    token = f"ph31-tok-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    db.users.insert_one({
        "user_id": uid, "email": f"{uid}@test.sk", "did": f"did:guardian:{uid}",
        "name": "Test Phase31", "language": "sk", "angel_mode": False, "created_at": now,
        "tier": "sovereign", "tos_accepted_version": "v2026-06.1",
    })
    db.user_sessions.insert_one({
        "session_token": token, "user_id": uid, "created_at": now,
        "expires_at": now + timedelta(days=1),
    })
    # Seed an insurance policy so financial_shield step becomes done (not action_needed)
    db.insurance_policies.insert_one({
        "policy_id": uuid.uuid4().hex, "user_id": uid, "type": "disability",
        "provider": "Allianz Test", "premium_monthly": 25.0, "created_at": now,
    })
    yield {"user_id": uid, "token": token, "db": db}
    # Teardown
    for col in ("users", "user_sessions", "insurance_policies", "insurance_claims",
                "healing_journeys", "waitlist", "calendar_events", "neural_bus",
                "companion_checkins", "voice_echoes", "emergency_profiles", "recovery"):
        db[col].delete_many({"user_id": uid})
    mc.close()


@pytest.fixture
def hdr(fresh_user):
    return {"Authorization": f"Bearer {fresh_user['token']}", "Content-Type": "application/json"}


# ===================== HEALING LOOP =====================

class TestHealingLoop:
    def test_01_injury_event_neural_bus(self, fresh_user, hdr):
        r = requests.post(f"{API}/healing/injury-event", headers=hdr,
                          json={"kind": "injury", "specialty": "Ortopéd", "body_part": "Koleno"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert "journey" in data and "claim" in data and "access" in data
        j, c, a = data["journey"], data["claim"], data["access"]
        assert j["status"] == "active"
        assert j["steps"]["intake"] == "done"
        assert j["steps"]["access"] == "done"
        # policy seeded → financial_shield should be done
        assert j["steps"]["financial_shield"] == "done"
        assert c["policy_found"] is True
        assert c["daily_benefit_eur"] > 0
        assert c["estimated_total_eur"] == round(c["daily_benefit_eur"] * 21, 2)
        assert a["slot"] and a["clinic"]
        # DB side-effects
        db = fresh_user["db"]
        uid = fresh_user["user_id"]
        assert db.insurance_claims.count_documents({"user_id": uid, "claim_id": c["claim_id"]}) == 1
        assert db.waitlist.count_documents({"user_id": uid, "source": "healing_loop"}) >= 1
        bus = db.neural_bus.find_one({"user_id": uid, "type": "injury_event",
                                       "journey_id": j["journey_id"]})
        assert bus is not None
        assert set(bus["triggered"]) == {"insurance_claim", "waitlist_hunter"}

    def test_02_state_active(self, hdr):
        r = requests.get(f"{API}/healing/state", headers=hdr)
        assert r.status_code == 200
        d = r.json()
        assert d["active"] is True
        assert d["progress_pct"] >= 60  # intake+shield+access = 3/5 = 60
        assert d["claim"] is not None
        assert "steps_meta" in d
        assert d["step_keys"] == ["intake", "financial_shield", "access", "bureaucracy", "recovery"]

    def test_03_claim_submit_once_then_404(self, fresh_user, hdr):
        st = requests.get(f"{API}/healing/state", headers=hdr).json()
        claim_id = st["claim"]["claim_id"]
        r1 = requests.post(f"{API}/healing/claim/{claim_id}/submit", headers=hdr)
        assert r1.status_code == 200, r1.text
        assert r1.json()["claim"]["status"] == "submitted"
        r2 = requests.post(f"{API}/healing/claim/{claim_id}/submit", headers=hdr)
        assert r2.status_code == 404

    def test_04_step_recovery_complete(self, hdr):
        r = requests.post(f"{API}/healing/step/recovery/complete", headers=hdr)
        assert r.status_code == 200
        assert r.json() == {"ok": True, "step": "recovery"}

    def test_05_close_and_state_inactive(self, hdr):
        r = requests.post(f"{API}/healing/close", headers=hdr)
        assert r.status_code == 200
        assert "100" in r.json()["message"] or "fit" in r.json()["message"].lower()
        s = requests.get(f"{API}/healing/state", headers=hdr).json()
        assert s["active"] is False
        assert s["last_recovered"] is not None
        assert s["last_recovered"]["status"] == "recovered"

    # -------- Validation branches --------
    def test_06_injury_bad_kind(self, hdr):
        r = requests.post(f"{API}/healing/injury-event", headers=hdr,
                          json={"kind": "xyz", "specialty": "Ortopéd"})
        assert r.status_code == 400

    def test_07_step_bad_key(self, hdr):
        # need active journey to reach the step-key validator? actually check ordering:
        # code checks step_key FIRST, so no active journey required. But we already closed.
        r = requests.post(f"{API}/healing/step/badkey/complete", headers=hdr)
        assert r.status_code == 400

    def test_08_close_no_active(self, hdr):
        r = requests.post(f"{API}/healing/close", headers=hdr)
        assert r.status_code == 404


# ===================== COMPANION =====================

class TestCompanion:
    def test_01_greeting(self, hdr):
        r = requests.get(f"{API}/companion/greeting", headers=hdr)
        assert r.status_code == 200
        d = r.json()
        for k in ("question", "topic", "answered_today"):
            assert k in d
        assert isinstance(d["answered_today"], bool)

    def test_02_checkin_low_mood(self, hdr):
        r = requests.post(f"{API}/companion/checkin", headers=hdr, json={"mood": 1, "note": "test"})
        assert r.status_code == 200
        assert "reply" in r.json() and r.json()["reply"]
        # verify answered_today flips true
        g = requests.get(f"{API}/companion/greeting", headers=hdr).json()
        assert g["answered_today"] is True

    def test_03_checkin_invalid(self, hdr):
        r = requests.post(f"{API}/companion/checkin", headers=hdr, json={"mood": 7})
        assert r.status_code == 400

    def test_04_trends(self, hdr):
        r = requests.get(f"{API}/companion/trends", headers=hdr)
        assert r.status_code == 200
        d = r.json()
        assert "avg_mood_14d" in d and "trend" in d and "count" in d
        assert d["count"] >= 1


# ===================== VOICE ECHOES =====================

class TestEchoes:
    def test_01_add(self, fresh_user, hdr):
        r = requests.post(f"{API}/family/echoes", headers=hdr,
                          json={"from_name": "Mama", "message": "Ahoj otec, mysli na seba."})
        assert r.status_code == 200
        eid = r.json()["echo"]["echo_id"]
        # stash on the fixture-shared object for later
        fresh_user["_echo_id"] = eid

    def test_02_empty_message(self, hdr):
        r = requests.post(f"{API}/family/echoes", headers=hdr,
                          json={"from_name": "X", "message": "   "})
        assert r.status_code == 400

    def test_03_list_unheard(self, hdr):
        r = requests.get(f"{API}/family/echoes", headers=hdr)
        assert r.status_code == 200
        d = r.json()
        assert d["unheard"] >= 1
        assert len(d["echoes"]) >= 1

    def test_04_mark_heard_decrements(self, fresh_user, hdr):
        eid = fresh_user["_echo_id"]
        before = requests.get(f"{API}/family/echoes", headers=hdr).json()["unheard"]
        r = requests.post(f"{API}/family/echoes/{eid}/heard", headers=hdr)
        assert r.status_code == 200
        after = requests.get(f"{API}/family/echoes", headers=hdr).json()
        assert after["unheard"] == before - 1
        # verify the specific echo has heard=true
        target = next((e for e in after["echoes"] if e["echo_id"] == eid), None)
        assert target and target["heard"] is True


# ===================== JARVIS CONTEXT =====================

class TestJarvisContext:
    def test_01_shape(self, hdr):
        r = requests.get(f"{API}/jarvis/context", headers=hdr)
        assert r.status_code == 200
        d = r.json()
        assert "healing_loop" in d and "companion" in d
        hl = d["healing_loop"]
        assert set(["active", "kind", "specialty", "steps", "booked_slot", "insurance_claim"]).issubset(hl.keys())
        # after closing, journey should be inactive
        assert hl["active"] is False
        # companion avg is populated only if a checkin exists in the last 7d;
        # trigger one to make the assertion deterministic across parallel workers
        requests.post(f"{API}/companion/checkin", headers=hdr, json={"mood": 4})
        d2 = requests.get(f"{API}/jarvis/context", headers=hdr).json()
        assert d2["companion"]["avg_mood_7d"] is not None
        assert d2["companion"]["checkins_7d"] >= 1


# ===================== REGRESSION =====================

class TestRegression:
    def test_insurance_policies_get_post(self, hdr):
        g = requests.get(f"{API}/insurance/policies", headers=hdr)
        assert g.status_code == 200
        body = g.json()
        # API returns wrapper object; policies list must exist
        assert isinstance(body, dict) and "policies" in body and isinstance(body["policies"], list)
        p = requests.post(f"{API}/insurance/policies", headers=hdr, json={
            "provider": "Test Ins", "policy_id": "TEST123", "type": "health",
            "premium_monthly": 15.0,
        })
        assert p.status_code in (200, 201), p.text

    def test_chains_healing(self, hdr):
        r = requests.post(f"{API}/chains/healing", headers=hdr, json={"specialty": "Kardiológ"})
        assert r.status_code == 200
        d = r.json()
        assert d["chain"] == "healing"
        assert len(d["steps"]) >= 4
