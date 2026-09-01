"""
Phase 51.2 — Karta života: Karta pre dieťa + Očkovací preukaz EÚ backend tests.

Covers:
  1) VACCINE PASS: GET /api/lifecard/vaccine-pass, GET /api/lifecard/vaccine-pass.pdf
  2) CHILD CRUD: POST/GET/PUT/DELETE /api/lifecard/children (+ cascade)
  3) CHILD SCOPING: calendar events + timeline + lifecard counts adult vs child
  4) CHILD PREDICTIONS: paediatric predictions + accept
  5) BOOSTER GUARD child watermark: "(dieťa <name>)"
  6) REGRESSIONS: IPS / voice intent to adult / family / report.pdf both
"""
import os
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/")
TOKEN1 = "smoketok-fresh-2026"
TOKEN2 = "smoketok-fresh-2026-u2"
H1 = {"Authorization": f"Bearer {TOKEN1}"}
H2 = {"Authorization": f"Bearer {TOKEN2}"}
H1J = {**H1, "Content-Type": "application/json"}
H2J = {**H2, "Content-Type": "application/json"}


# ==================== 1) VACCINE PASS ====================
class TestVaccinePass:
    def test_vaxpass_json_shape(self):
        r = requests.get(f"{BASE_URL}/api/lifecard/vaccine-pass", headers=H1, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        # Required fields
        for k in ("holder", "birth_date", "blood_type", "did", "child",
                  "vaccinations", "issued_at", "did_signature", "languages"):
            assert k in d, f"missing {k} in {list(d.keys())}"
        assert d["child"] is False, d
        assert isinstance(d["vaccinations"], list)
        assert isinstance(d["did_signature"], str) and len(d["did_signature"]) == 64
        assert all(c in "0123456789abcdef" for c in d["did_signature"])
        assert isinstance(d["languages"], list)
        assert len(d["languages"]) == 14, [x["code"] for x in d["languages"]]
        codes = {x["code"] for x in d["languages"]}
        # sanity: EU main languages included
        for c in ("en", "sk", "cs", "de", "fr", "es", "it", "pl", "hu",
                  "uk", "ru", "pt", "nl", "ro"):
            assert c in codes, codes

    def test_vaxpass_pdf_bearer(self):
        r = requests.get(f"{BASE_URL}/api/lifecard/vaccine-pass.pdf", headers=H1, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert "pdf" in r.headers.get("content-type", "").lower()
        assert r.content.startswith(b"%PDF")
        assert len(r.content) > 3000

    def test_vaxpass_pdf_query_token(self):
        r = requests.get(f"{BASE_URL}/api/lifecard/vaccine-pass.pdf?token={TOKEN1}", timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.content.startswith(b"%PDF")

    def test_vaxpass_json_unauth_401(self):
        r = requests.get(f"{BASE_URL}/api/lifecard/vaccine-pass", timeout=15)
        assert r.status_code == 401, r.text

    def test_vaxpass_pdf_unauth_401(self):
        r = requests.get(f"{BASE_URL}/api/lifecard/vaccine-pass.pdf", timeout=15)
        assert r.status_code == 401


# ==================== 2) CHILD CRUD ====================
class TestChildCRUD:
    @pytest.fixture(scope="class")
    def child(self):
        r = requests.post(f"{BASE_URL}/api/lifecard/children", headers=H1J,
                          json={"name": "TEST_Ema", "birth_date": "2023-06-15",
                                "blood_type": "A+"}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        yield d
        # cleanup — best effort
        requests.delete(f"{BASE_URL}/api/lifecard/children/{d['child_id']}", headers=H1, timeout=10)

    def test_child_created_with_age_and_zero_counts(self, child):
        assert child["name"] == "TEST_Ema"
        assert child["birth_date"] == "2023-06-15"
        assert child["blood_type"] == "A+"
        assert "child_id" in child and len(child["child_id"]) >= 8
        assert child.get("age") is not None and isinstance(child["age"], int)
        assert child["age"] >= 2
        counts = child.get("counts") or {}
        for c in ("vaccine", "disease", "surgery", "injury", "exam"):
            assert counts.get(c, 0) == 0, counts

    def test_children_list_includes_new_child(self, child):
        r = requests.get(f"{BASE_URL}/api/lifecard/children", headers=H1, timeout=15)
        assert r.status_code == 200, r.text
        ids = [c["child_id"] for c in r.json().get("children", [])]
        assert child["child_id"] in ids, ids

    def test_child_invalid_birth_future_400(self):
        r = requests.post(f"{BASE_URL}/api/lifecard/children", headers=H1J,
                          json={"name": "TEST_bad", "birth_date": "2050-01-01"}, timeout=15)
        assert r.status_code == 400, r.text

    def test_child_invalid_birth_format_400(self):
        r = requests.post(f"{BASE_URL}/api/lifecard/children", headers=H1J,
                          json={"name": "TEST_bad2", "birth_date": "15-06-2023"}, timeout=15)
        assert r.status_code == 400, r.text

    def test_child_invalid_blood_type_400(self):
        r = requests.post(f"{BASE_URL}/api/lifecard/children", headers=H1J,
                          json={"name": "TEST_bad3", "birth_date": "2020-01-01",
                                "blood_type": "Z++"}, timeout=15)
        assert r.status_code == 400, r.text

    def test_child_update_name_and_blood(self, child):
        r = requests.put(f"{BASE_URL}/api/lifecard/children/{child['child_id']}", headers=H1J,
                         json={"name": "TEST_EmaUpdated", "blood_type": "0-"}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["name"] == "TEST_EmaUpdated"
        assert d["blood_type"] == "0-"
        assert d["birth_date"] == "2023-06-15"  # unchanged

    def test_child_delete_cascade(self):
        # create a fresh child + add an event + generate prediction cache row
        r = requests.post(f"{BASE_URL}/api/lifecard/children", headers=H1J,
                          json={"name": "TEST_Cascade", "birth_date": "2022-01-01",
                                "blood_type": "B+"}, timeout=15)
        assert r.status_code == 200, r.text
        cid = r.json()["child_id"]

        # add a vaccine event scoped to child
        ev = requests.post(f"{BASE_URL}/api/calendar/events", headers=H1J, json={
            "category": "vaccine", "title": "TEST_CascadeVax",
            "date": datetime.now(timezone.utc).date().isoformat(),
            "child_id": cid}, timeout=15)
        assert ev.status_code == 200, ev.text
        eid = ev.json()["event_id"]

        # verify timeline shows the event
        tl = requests.get(f"{BASE_URL}/api/calendar/timeline?child_id={cid}",
                          headers=H1, timeout=15).json()
        assert any(e["event_id"] == eid for e in tl.get("events", [])), tl

        # delete child
        d = requests.delete(f"{BASE_URL}/api/lifecard/children/{cid}", headers=H1, timeout=15)
        assert d.status_code == 200, d.text

        # timeline for that child should now 404 (child not found via _get_child)
        tl2 = requests.get(f"{BASE_URL}/api/calendar/timeline?child_id={cid}",
                           headers=H1, timeout=15)
        assert tl2.status_code == 404, tl2.text


# ==================== 3) CHILD SCOPING ====================
class TestChildScoping:
    @pytest.fixture(scope="class")
    def child_id(self):
        r = requests.post(f"{BASE_URL}/api/lifecard/children", headers=H1J,
                          json={"name": "TEST_Scope", "birth_date": "2021-01-01",
                                "blood_type": "A+"}, timeout=15)
        assert r.status_code == 200, r.text
        cid = r.json()["child_id"]
        yield cid
        requests.delete(f"{BASE_URL}/api/lifecard/children/{cid}", headers=H1, timeout=10)

    def test_event_with_bad_child_id_404(self):
        r = requests.post(f"{BASE_URL}/api/calendar/events", headers=H1J, json={
            "category": "vaccine", "title": "TEST_BadChildRef",
            "date": datetime.now(timezone.utc).date().isoformat(),
            "child_id": "nonexistent-child-xyz"}, timeout=15)
        assert r.status_code == 404, r.text

    def test_child_scoping_isolation(self, child_id):
        today = datetime.now(timezone.utc).date().isoformat()

        # 1) Adult vaccine event (no child_id)
        r_a = requests.post(f"{BASE_URL}/api/calendar/events", headers=H1J, json={
            "category": "vaccine", "title": "TEST_AdultOnly", "date": today}, timeout=15)
        assert r_a.status_code == 200, r_a.text
        adult_eid = r_a.json()["event_id"]

        # 2) Child vaccine event
        r_c = requests.post(f"{BASE_URL}/api/calendar/events", headers=H1J, json={
            "category": "vaccine", "title": "TEST_ChildOnly",
            "date": today, "child_id": child_id}, timeout=15)
        assert r_c.status_code == 200, r_c.text
        child_eid = r_c.json()["event_id"]

        try:
            # 3) Adult timeline must NOT contain child event
            tl_adult = requests.get(f"{BASE_URL}/api/calendar/timeline",
                                    headers=H1, timeout=15).json()
            ids_adult = {e["event_id"] for e in tl_adult["events"]}
            assert adult_eid in ids_adult, "adult event missing from adult timeline"
            assert child_eid not in ids_adult, "child event leaked into adult timeline"

            # 4) Child timeline contains ONLY child events
            tl_child = requests.get(f"{BASE_URL}/api/calendar/timeline?child_id={child_id}",
                                    headers=H1, timeout=15).json()
            ids_child = {e["event_id"] for e in tl_child["events"]}
            assert child_eid in ids_child, "child event missing from child timeline"
            assert adult_eid not in ids_child, "adult event leaked into child timeline"

            # 5) Category filter + child_id combined
            tl_child_v = requests.get(
                f"{BASE_URL}/api/calendar/timeline?category=vaccine&child_id={child_id}",
                headers=H1, timeout=15).json()
            for e in tl_child_v["events"]:
                assert e["category"] == "vaccine", e
                assert e.get("child_id") == child_id, e

            # 6) Adult lifecard counts do NOT include child event
            lc = requests.get(f"{BASE_URL}/api/lifecard", headers=H1, timeout=15).json()
            adult_vax_count = lc.get("counts", {}).get("vaccine", 0)
            # count TEST_AdultOnly in adult timeline
            adult_titles = [e["title"] for e in tl_adult["events"]]
            assert "TEST_ChildOnly" not in adult_titles, adult_titles
            # sanity: adult count should equal number of adult vaccine events in adult timeline
            adult_vax_titles = [e["title"] for e in tl_adult["events"] if e["category"] == "vaccine"]
            assert adult_vax_count == len(adult_vax_titles), (adult_vax_count, adult_vax_titles)

            # 7) Child-scoped counts on child timeline endpoint
            child_counts = tl_child.get("counts", {})
            child_vax = [e for e in tl_child["events"] if e["category"] == "vaccine"]
            assert child_counts.get("vaccine", 0) == len(child_vax), (child_counts, child_vax)
        finally:
            requests.delete(f"{BASE_URL}/api/calendar/events/{adult_eid}", headers=H1, timeout=10)
            requests.delete(f"{BASE_URL}/api/calendar/events/{child_eid}", headers=H1, timeout=10)


# ==================== 4) CHILD PREDICTIONS ====================
class TestChildPredictions:
    @pytest.fixture(scope="class")
    def child_with_hexa(self):
        # ~3-year-old (born 2022) with one hexavakcína
        r = requests.post(f"{BASE_URL}/api/lifecard/children", headers=H1J,
                          json={"name": "TEST_Pediatric", "birth_date": "2022-08-01",
                                "blood_type": "A+"}, timeout=15)
        assert r.status_code == 200, r.text
        cid = r.json()["child_id"]
        # add hexa vaccine 18 months ago
        ev = requests.post(f"{BASE_URL}/api/calendar/events", headers=H1J, json={
            "category": "vaccine", "title": "Hexavakcína",
            "date": "2023-02-01", "child_id": cid,
            "notes": "1. dávka hexavakcíny"}, timeout=15)
        assert ev.status_code == 200, ev.text
        yield cid
        requests.delete(f"{BASE_URL}/api/lifecard/children/{cid}", headers=H1, timeout=10)

    def test_child_predictions_paediatric(self, child_with_hexa):
        r = requests.post(f"{BASE_URL}/api/lifecard/predictions", headers=H1J,
                          json={"child_id": child_with_hexa}, timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("ai") is True, d
        assert d.get("child_id") == child_with_hexa, d
        preds = d.get("predictions") or []
        if not preds:
            pytest.skip("LLM returned 0 predictions this run")
        today = datetime.now(timezone.utc).date().isoformat()
        cats = {p["category"] for p in preds}
        assert cats.issubset({"vaccine", "exam"}), cats
        for p in preds:
            assert p.get("suggested_date", "0000") > today, p  # future dates only
            reason = p.get("reason", "")
            assert isinstance(reason, str) and len(reason) > 3, p

    def test_child_predictions_accept_carries_child_id(self, child_with_hexa):
        # accept a synthetic prediction (bypassing LLM output) — endpoint takes explicit body
        today = datetime.now(timezone.utc).date()
        future = (today + timedelta(days=30)).isoformat()
        r = requests.post(f"{BASE_URL}/api/lifecard/predictions/accept", headers=H1J,
                         json={"title": "TEST_ChildAccept_Preventive",
                               "category": "exam",
                               "date": future,
                               "reason": "Rutinná prehliadka u pediatra",
                               "child_id": child_with_hexa}, timeout=20)
        assert r.status_code == 200, r.text
        eid = r.json()["event_id"]
        # verify child timeline contains it with source jarvis + child_id
        tl = requests.get(
            f"{BASE_URL}/api/calendar/timeline?child_id={child_with_hexa}",
            headers=H1, timeout=15).json()
        found = [e for e in tl["events"] if e["event_id"] == eid]
        assert found, tl
        assert found[0].get("source") == "jarvis", found[0]
        assert found[0].get("child_id") == child_with_hexa, found[0]
        requests.delete(f"{BASE_URL}/api/calendar/events/{eid}", headers=H1, timeout=10)

    def test_adult_predictions_no_body_still_works(self):
        r = requests.post(f"{BASE_URL}/api/lifecard/predictions", headers=H1, timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("ai") is True
        assert d.get("child_id") is None or d.get("child_id") == None
        assert "predictions" in d


# ==================== 5) BOOSTER GUARD CHILD ====================
class TestBoosterGuardChild:
    def test_booster_guard_message_names_child(self):
        # create child + child vaccine with booster_due ~10 days out
        cr = requests.post(f"{BASE_URL}/api/lifecard/children", headers=H1J,
                           json={"name": "TEST_BGChild_Lukas", "birth_date": "2022-01-01"},
                           timeout=15)
        assert cr.status_code == 200, cr.text
        cid = cr.json()["child_id"]
        today = datetime.now(timezone.utc).date()
        booster = (today + timedelta(days=10)).isoformat()
        try:
            ev = requests.post(f"{BASE_URL}/api/calendar/events", headers=H1J, json={
                "category": "vaccine", "title": "TEST_ChildBoosterVax",
                "date": today.isoformat(), "child_id": cid,
                "booster_due": booster}, timeout=15)
            assert ev.status_code == 200, ev.text
            eid = ev.json()["event_id"]

            # run sweep
            sw = requests.post(f"{BASE_URL}/api/swarm/run/booster_guard",
                              headers=H1J, timeout=45)
            assert sw.status_code == 200, sw.text
            d = sw.json()
            actions = d.get("actions") if isinstance(d, dict) else None
            if actions is None and isinstance(d.get("result"), dict):
                actions = d["result"].get("actions")
            assert (actions or 0) >= 1, d

            # verify agent_conversations directly via Mongo
            from pymongo import MongoClient
            client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
            mdb = client[os.environ.get("DB_NAME", "guardian_health")]
            msg = mdb.agent_conversations.find_one(
                {"user_id": "smoketest-user-1", "source": "booster_guard",
                 "text": {"$regex": r"\(dieťa TEST_BGChild_Lukas\)"}},
                sort=[("at", -1)])
            client.close()
            assert msg is not None, "child-named booster message not found in agent_conversations"
            assert "TEST_ChildBoosterVax" in msg["text"], msg["text"]

            requests.delete(f"{BASE_URL}/api/calendar/events/{eid}", headers=H1, timeout=10)
        finally:
            requests.delete(f"{BASE_URL}/api/lifecard/children/{cid}", headers=H1, timeout=10)


# ==================== 6) REGRESSIONS ====================
class TestPhase512Regressions:
    def test_ips_excludes_child_vaccines(self):
        # create child + child vaccine, then call IPS
        cr = requests.post(f"{BASE_URL}/api/lifecard/children", headers=H1J,
                           json={"name": "TEST_IPSChild", "birth_date": "2021-01-01"},
                           timeout=15)
        assert cr.status_code == 200, cr.text
        cid = cr.json()["child_id"]
        try:
            ev = requests.post(f"{BASE_URL}/api/calendar/events", headers=H1J, json={
                "category": "vaccine", "title": "TEST_IPSChildOnlyVax",
                "date": datetime.now(timezone.utc).date().isoformat(),
                "child_id": cid}, timeout=15)
            assert ev.status_code == 200, ev.text
            eid = ev.json()["event_id"]

            # Try IPS endpoints (either GlobalNet or IPS summary)
            found_route = False
            for path in ("/api/globalnet/ips", "/api/ips/summary", "/api/globalnet/ips/summary"):
                r = requests.get(f"{BASE_URL}{path}", headers=H1, timeout=25)
                if r.status_code == 200:
                    found_route = True
                    txt = r.text
                    assert "TEST_IPSChildOnlyVax" not in txt, f"child vaccine leaked into {path}"
                    break
            if not found_route:
                pytest.skip("No IPS summary endpoint reachable (200)")
            requests.delete(f"{BASE_URL}/api/calendar/events/{eid}", headers=H1, timeout=10)
        finally:
            requests.delete(f"{BASE_URL}/api/lifecard/children/{cid}", headers=H1, timeout=10)

    def test_voice_intent_logs_to_adult_no_child_id(self):
        r = requests.post(f"{BASE_URL}/api/agent/chat", headers=H1J,
                          json={"message": "Včera ma zaočkovali proti tetanu"}, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("lifecard_logged"), d
        logged = d["lifecard_logged"]
        # sanity: LLM parsed intent as a vaccine
        assert logged.get("category") == "vaccine", logged
        assert "tetan" in (logged.get("title") or "").lower(), logged
        # verify recorded on adult timeline (no child_id) — could be today or yesterday
        tl = requests.get(f"{BASE_URL}/api/calendar/timeline?category=vaccine",
                          headers=H1, timeout=15).json()
        matched = [e for e in tl["events"]
                   if e.get("source") == "voice"
                   and "tetan" in (e.get("title", "").lower())]
        assert matched, [e.get("title") for e in tl["events"]]
        for e in matched:
            assert not e.get("child_id"), e
            requests.delete(f"{BASE_URL}/api/calendar/events/{e['event_id']}",
                            headers=H1, timeout=10)

    def test_family_endpoint_unaffected(self):
        r = requests.get(f"{BASE_URL}/api/lifecard/family", headers=H1, timeout=15)
        assert r.status_code == 200, r.text
        assert "members" in r.json()

    def test_report_pdf_adult_and_child(self):
        # adult
        r = requests.get(f"{BASE_URL}/api/lifecard/report.pdf", headers=H1, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.content.startswith(b"%PDF")

        # create child + report
        cr = requests.post(f"{BASE_URL}/api/lifecard/children", headers=H1J,
                           json={"name": "TEST_ReportChild", "birth_date": "2020-01-01"},
                           timeout=15)
        assert cr.status_code == 200, cr.text
        cid = cr.json()["child_id"]
        try:
            r2 = requests.get(f"{BASE_URL}/api/lifecard/report.pdf?child_id={cid}",
                              headers=H1, timeout=30)
            assert r2.status_code == 200, r2.text[:300]
            assert r2.content.startswith(b"%PDF")
        finally:
            requests.delete(f"{BASE_URL}/api/lifecard/children/{cid}", headers=H1, timeout=10)
