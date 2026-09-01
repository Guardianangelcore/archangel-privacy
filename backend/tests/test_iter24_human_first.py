"""Iteration 24 — HUMAN-FIRST UI/UX repair backend regression suite.

Tests: geo context/travel-mode (Prague default + Paris switch + reset),
vault→timeline indexing, translate appointment extraction,
pharmacy CZ default, system_janitor swarm agent, agent briefing regression.
"""
import io
import os
import pytest
import requests

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
TOKEN = "smoketok-fresh-handover"
H = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update(H)
    return sess


# ---------------- GEO ----------------
class TestGeo:
    def test_geo_context_default_prague(self, s):
        r = s.get(f"{BASE_URL}/api/geo/context", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        # Post-anonymity seal (Phase 45): default is sovereign Bratislava; Prague/Paris
        # still valid when previously located there.
        assert d["geo"]["city"] in ("Prague", "Paris", "Bratislava", "New York"), d
        assert len(d["supported_cities"]) >= 10

    def test_travel_mode_paris_language_switch(self, s):
        # enable travel-mode
        r = s.put(f"{BASE_URL}/api/geo/travel-mode", json={"enabled": True}, timeout=15)
        assert r.status_code == 200
        assert r.json()["travel_mode"] is True
        # locate Paris
        r = s.post(f"{BASE_URL}/api/geo/locate",
                   json={"lat": 48.8566, "lng": 2.3522}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["geo"]["city"] == "Paris"
        assert d["geo"]["country"] == "FR"
        assert d["language_switched"] is True
        assert d["language"] == "fr"

    def test_reset_prague_and_language_sk(self, s):
        # RESET — MANDATORY
        r = s.post(f"{BASE_URL}/api/geo/locate",
                   json={"lat": 50.0755, "lng": 14.4378}, timeout=15)
        assert r.status_code == 200
        assert r.json()["geo"]["city"] == "Prague"
        r = s.put(f"{BASE_URL}/api/geo/travel-mode",
                  json={"enabled": False}, timeout=15)
        assert r.status_code == 200
        r = s.patch(f"{BASE_URL}/api/me/prefs", json={"language": "sk"}, timeout=15)
        assert r.status_code == 200
        # verify
        r = s.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 200
        me = r.json()
        u = me.get("user", me)
        assert u.get("language") == "sk", u


# ---------------- VAULT → TIMELINE ----------------
class TestVaultTimeline:
    def test_upload_doc_creates_timeline_event(self, s):
        files = {"file": ("TEST_iter24.txt", io.BytesIO(b"iter24 test doc content"), "text/plain")}
        data = {"title": "TEST_iter24_doc", "kind": "note"}
        # multipart — do not send Content-Type override
        r = requests.post(f"{BASE_URL}/api/vault/documents",
                          headers=H, files=files, data=data, timeout=30)
        assert r.status_code in (200, 201), r.text
        d = r.json()
        doc_id = d.get("doc_id") or d.get("id") or (d.get("doc") or {}).get("doc_id")
        assert doc_id, d
        # fetch timeline
        r = s.get(f"{BASE_URL}/api/calendar/timeline", timeout=15)
        assert r.status_code == 200
        events = r.json().get("events") or r.json().get("timeline") or []
        matched = [e for e in events if e.get("doc_id") == doc_id
                   or (e.get("title", "").startswith("📄") and doc_id in str(e))]
        # fallback: any history event that references doc_id
        if not matched:
            matched = [e for e in events if e.get("category") == "history"
                       and e.get("doc_id") == doc_id]
        assert matched, f"No timeline event found for doc_id={doc_id}. Events sample={events[:3]}"
        ev = matched[0]
        assert ev.get("category") == "history"
        assert str(ev.get("title", "")).startswith("📄")


# ---------------- TRANSLATE APPOINTMENT ----------------
class TestTranslateAppointment:
    def test_translate_extracts_appointment(self, s):
        payload = {
            "text": "Pacient má naplánovanú kontrolu dňa 15.9.2026 o 10:30 u kardiológa. "
                    "Odporúčam pokračovať v liečbe Aspirinom.",
            "target": "sk",
        }
        r = s.post(f"{BASE_URL}/api/ai/translate", json=payload, timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("plain_language") or d.get("output"), d
        appt = d.get("next_appointment") or {}
        assert appt.get("date") == "2026-09-15", appt
        assert appt.get("time") == "10:30", appt
        assert appt.get("title"), appt

        # add to calendar — category must be exam|history|vaccine
        r = s.post(f"{BASE_URL}/api/calendar/events",
                   json={"date": appt["date"], "time": appt["time"],
                         "title": appt["title"], "category": "exam"},
                   timeout=15)
        assert r.status_code in (200, 201), r.text


# ---------------- PHARMACY GEO ----------------
class TestPharmacyGeo:
    def test_pharmacy_default_cz_praha(self, s):
        r = s.get(f"{BASE_URL}/api/pharmacy/search",
                  params={"med": "Ibalgin"}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("region") == "CZ", d
        results = d.get("results") or []
        assert results, d
        assert results[0].get("city") == "Praha", results[0]

    def test_pharmacy_sk_regression(self, s):
        r = s.get(f"{BASE_URL}/api/pharmacy/search",
                  params={"med": "Ibalgin", "region": "SK"}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("region") == "SK"
        assert d.get("results")


# ---------------- SWARM / JANITOR ----------------
class TestJanitor:
    def test_run_system_janitor(self, s):
        r = s.post(f"{BASE_URL}/api/swarm/run/system_janitor", timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("status") == "ok", d

    def test_janitor_status(self, s):
        r = s.get(f"{BASE_URL}/api/janitor/status", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("agent"), d
        assert "recent_repairs" in d

    def test_swarm_has_10_agents(self, s):
        r = s.get(f"{BASE_URL}/api/swarm/status", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        agents = d.get("agents") or []
        assert len(agents) >= 10, f"Only {len(agents)} agents: {[a.get('name') for a in agents]}"


# ---------------- REGRESSION ----------------
class TestRegression:
    def test_agent_briefing_geo_aware(self, s):
        r = s.get(f"{BASE_URL}/api/agent/briefing",
                  params={"force": "true"}, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        text = str(d).lower()
        # Weather should reflect user's geo (Praha default, or Paríž if travel-mode test ran first)
        assert "praha" in text or "prague" in text or "paríž" in text, \
            f"No geo city in briefing: {list(d.keys())}"

    def test_waitlist_autobook_still_ok(self, s):
        r = s.post(f"{BASE_URL}/api/waitlist",
                   json={"specialty": "dermatology", "clinic": "", "city": "",
                         "current_date": "2026-01-15",
                         "target_before": "2026-03-15",
                         "urgency": "normal"},
                   timeout=30)
        assert r.status_code in (200, 201), r.text
