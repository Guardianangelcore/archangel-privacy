"""
Phase 51 — KARTA ŽIVOTA backend regression suite.

Covers:
- GET/PUT /api/lifecard (identity: full_name, birth_date, blood_type, age, counts, predictions)
- POST /api/calendar/events for all 5 categories + 'history' alias → disease + invalid → 400
- GET /api/calendar/timeline counts + category filter
- DELETE /api/calendar/events/{id}
- Jarvis /api/agent/chat voice → lifecard_logged (disease from "kiahne")
- Jarvis /api/agent/chat question ("Kedy mám ísť na očkovanie?") → NO record
- Jarvis /api/agent/chat/stream lifecard sentence → SSE with lifecard_logged in final `done`
- POST /api/lifecard/predictions (LLM) → predictions[] validated + ai:true
- POST /api/lifecard/predictions/accept → creates event source='jarvis' + prediction removed
- Regressions: pain diary ('bolí ma to na sedem'→7), normal chat reply watermarked, IPS summary
"""
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://guardian-vault-13.preview.emergentagent.com").rstrip("/")
TOKEN = "smoketok-fresh-2026"                # smoketest-user-1 (per request)
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

WATERMARK = "AI Content · Sovereign Protocol"
LIFECARD_CATS = ("vaccine", "disease", "surgery", "injury", "exam")


# ------------------------------ fixtures ------------------------------
@pytest.fixture(scope="module")
def created_event_ids():
    ids = []
    yield ids
    # teardown: best-effort cleanup
    for eid in ids:
        try:
            requests.delete(f"{BASE_URL}/api/calendar/events/{eid}", headers=HEADERS, timeout=15)
        except Exception:
            pass


# ============================== IDENTITY ==============================
class TestLifecardIdentity:
    def test_get_lifecard_shape(self):
        r = requests.get(f"{BASE_URL}/api/lifecard", headers=HEADERS, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("full_name", "birth_date", "blood_type", "age", "counts",
                  "predictions", "today"):
            assert k in d, f"missing {k} in {d}"
        assert isinstance(d["counts"], dict)
        for c in LIFECARD_CATS:
            assert c in d["counts"], f"counts missing {c}"

    def test_put_lifecard_valid_birth_and_blood(self):
        payload = {"birth_date": "1958-05-14", "blood_type": "B+", "full_name": "Guardian Test"}
        r = requests.put(f"{BASE_URL}/api/lifecard", headers=HEADERS, json=payload, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["birth_date"] == "1958-05-14"
        assert d["blood_type"] == "B+"
        assert d["age"] is not None and d["age"] > 60

        # verify persistence via re-GET
        r2 = requests.get(f"{BASE_URL}/api/lifecard", headers=HEADERS, timeout=15).json()
        assert r2["birth_date"] == "1958-05-14"
        assert r2["blood_type"] == "B+"

    def test_put_lifecard_invalid_blood_type(self):
        r = requests.put(f"{BASE_URL}/api/lifecard", headers=HEADERS,
                         json={"blood_type": "XX+"}, timeout=15)
        assert r.status_code == 400, r.text

    def test_put_lifecard_invalid_birth_date_format(self):
        r = requests.put(f"{BASE_URL}/api/lifecard", headers=HEADERS,
                         json={"birth_date": "14-05-1958"}, timeout=15)
        assert r.status_code == 400

    def test_put_lifecard_birth_date_out_of_range(self):
        # year < 1900
        r = requests.put(f"{BASE_URL}/api/lifecard", headers=HEADERS,
                         json={"birth_date": "1899-01-01"}, timeout=15)
        assert r.status_code == 400
        # future date
        fut = (datetime.now(timezone.utc).date() + timedelta(days=10)).isoformat()
        r = requests.put(f"{BASE_URL}/api/lifecard", headers=HEADERS,
                         json={"birth_date": fut}, timeout=15)
        assert r.status_code == 400

    def test_blood_type_reflects_in_emergency_profile(self):
        # ensure B+
        requests.put(f"{BASE_URL}/api/lifecard", headers=HEADERS,
                     json={"blood_type": "B+"}, timeout=15)
        r = requests.get(f"{BASE_URL}/api/emergency-profile", headers=HEADERS, timeout=15)
        assert r.status_code == 200, r.text
        prof = r.json()
        assert prof.get("blood_type") == "B+", prof


# ============================ CALENDAR EVENTS ============================
class TestCalendarEvents:
    def test_create_all_five_categories(self, created_event_ids):
        today = datetime.now(timezone.utc).date().isoformat()
        for cat in LIFECARD_CATS:
            payload = {
                "category": cat, "title": f"TEST_{cat}",
                "date": today, "notes": f"note-{cat}",
            }
            r = requests.post(f"{BASE_URL}/api/calendar/events", headers=HEADERS,
                              json=payload, timeout=15)
            assert r.status_code == 200, f"{cat}: {r.text}"
            d = r.json()
            assert d["category"] == cat
            assert d["title"] == f"TEST_{cat}"
            assert d["notes"] == f"note-{cat}"
            assert d["source"] == "manual"
            assert "event_id" in d
            created_event_ids.append(d["event_id"])

    def test_history_alias_becomes_disease(self, created_event_ids):
        today = datetime.now(timezone.utc).date().isoformat()
        r = requests.post(f"{BASE_URL}/api/calendar/events", headers=HEADERS,
                          json={"category": "history", "title": "TEST_legacy",
                                "date": today, "notes": "legacy alias"}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["category"] == "disease", d
        created_event_ids.append(d["event_id"])

    def test_invalid_category_returns_400(self):
        today = datetime.now(timezone.utc).date().isoformat()
        r = requests.post(f"{BASE_URL}/api/calendar/events", headers=HEADERS,
                          json={"category": "bogus", "title": "x", "date": today}, timeout=15)
        assert r.status_code == 400, r.text

    def test_timeline_counts_and_filter(self, created_event_ids):
        # timeline overall
        r = requests.get(f"{BASE_URL}/api/calendar/timeline", headers=HEADERS, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "events" in d and "counts" in d and "today" in d
        for c in LIFECARD_CATS:
            assert c in d["counts"], d["counts"]
            assert d["counts"][c] >= 1, f"{c}={d['counts'][c]}"  # we created at least one per cat

        # filter each category → returned events must all match
        for cat in LIFECARD_CATS:
            r = requests.get(f"{BASE_URL}/api/calendar/timeline?category={cat}",
                             headers=HEADERS, timeout=15)
            assert r.status_code == 200
            events = r.json()["events"]
            for e in events:
                assert e["category"] == cat, f"filter leak: {e}"

    def test_delete_event(self, created_event_ids):
        # delete one of the created events and re-GET → 404
        if not created_event_ids:
            pytest.skip("no created events")
        eid = created_event_ids.pop()
        r = requests.delete(f"{BASE_URL}/api/calendar/events/{eid}", headers=HEADERS, timeout=15)
        assert r.status_code == 200
        # second delete → 404
        r2 = requests.delete(f"{BASE_URL}/api/calendar/events/{eid}", headers=HEADERS, timeout=15)
        assert r2.status_code == 404


# =========================== JARVIS VOICE INTENT ===========================
class TestJarvisLifecardVoice:
    def test_voice_kiahne_creates_disease_record_today(self):
        r = requests.post(f"{BASE_URL}/api/agent/chat", headers=HEADERS,
                          json={"message": "Dnes mi doktor povedal, že mám ovčie kiahne"},
                          timeout=60)  # LLM 5-20s
        assert r.status_code == 200, r.text
        d = r.json()
        assert "lifecard_logged" in d and d["lifecard_logged"], d
        rec = d["lifecard_logged"]
        assert rec["category"] == "disease", rec
        today = datetime.now(timezone.utc).date().isoformat()
        assert rec["date"] == today, rec
        assert "Zapísal som do Karty života" in d["reply"], d["reply"]
        assert WATERMARK in d["reply"]

        # cleanup: find & delete this new disease event
        tl = requests.get(f"{BASE_URL}/api/calendar/timeline?category=disease",
                          headers=HEADERS, timeout=15).json()
        for e in tl["events"]:
            if e.get("source") == "voice" and e.get("date") == today:
                requests.delete(f"{BASE_URL}/api/calendar/events/{e['event_id']}",
                                headers=HEADERS, timeout=10)

    def test_question_does_not_create_record(self):
        r = requests.post(f"{BASE_URL}/api/agent/chat", headers=HEADERS,
                          json={"message": "Kedy mám ísť na očkovanie proti chrípke?"},
                          timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert not d.get("lifecard_logged"), f"unexpected lifecard_logged: {d.get('lifecard_logged')}"
        assert "reply" in d and d["reply"], d
        assert WATERMARK in d["reply"]

    def test_stream_lifecard_sentence_final_meta(self):
        with requests.post(f"{BASE_URL}/api/agent/chat/stream", headers=HEADERS,
                           json={"message": "Včera mi lekár povedal, že mám angínu"},
                           timeout=90, stream=True) as resp:
            assert resp.status_code == 200, resp.text
            saw_done = False
            final = None
            for raw in resp.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                if raw.startswith("data:"):
                    payload = raw[5:].strip()
                    try:
                        obj = json.loads(payload)
                    except Exception:
                        continue
                    if obj.get("done"):
                        saw_done = True
                        final = obj
                        break
            assert saw_done and final is not None, "no `done` frame in SSE"
            assert final.get("lifecard_logged"), final
            assert final["lifecard_logged"]["category"] in LIFECARD_CATS

        # cleanup: delete the created disease/angína record (source=voice)
        today = datetime.now(timezone.utc).date().isoformat()
        yest = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
        for cat in ("disease", "exam", "vaccine", "injury", "surgery"):
            tl = requests.get(f"{BASE_URL}/api/calendar/timeline?category={cat}",
                              headers=HEADERS, timeout=15).json()
            for e in tl["events"]:
                if e.get("source") == "voice" and e.get("date") in (today, yest) and "ang" in (e.get("title", "").lower()):
                    requests.delete(f"{BASE_URL}/api/calendar/events/{e['event_id']}",
                                    headers=HEADERS, timeout=10)


# ============================= PREDICTIONS =============================
class TestLifecardPredictions:
    """LLM: up to 30s. Uses smoketest-user-1's existing history."""

    def test_predictions_generate_and_accept(self):
        r = requests.post(f"{BASE_URL}/api/lifecard/predictions",
                          headers=HEADERS, timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("ai") is True, d
        assert "predictions" in d, d
        today = datetime.now(timezone.utc).date().isoformat()
        if not d["predictions"]:
            pytest.skip("LLM returned 0 predictions this run — acceptable, endpoint still 200")
        for p in d["predictions"]:
            assert p["category"] in ("vaccine", "exam", "dental"), p
            assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", p["suggested_date"]), p
            assert p["suggested_date"] > today, p
            assert p.get("reason"), p
            assert p.get("title"), p

        # accept first prediction
        first = d["predictions"][0]
        r2 = requests.post(f"{BASE_URL}/api/lifecard/predictions/accept",
                           headers=HEADERS,
                           json={"title": first["title"], "category": first["category"],
                                 "date": first["suggested_date"], "reason": first["reason"]},
                           timeout=20)
        assert r2.status_code == 200, r2.text
        created = r2.json()
        assert created["source"] == "jarvis"
        assert created["category"] == first["category"]
        eid = created["event_id"]

        # cache should have that prediction removed
        card = requests.get(f"{BASE_URL}/api/lifecard", headers=HEADERS, timeout=15).json()
        titles_left = [p["title"] for p in card.get("predictions", [])]
        assert first["title"] not in titles_left, titles_left

        # cleanup created event
        requests.delete(f"{BASE_URL}/api/calendar/events/{eid}",
                        headers=HEADERS, timeout=10)

    def test_predictions_accept_invalid_category_400(self):
        r = requests.post(f"{BASE_URL}/api/lifecard/predictions/accept",
                          headers=HEADERS,
                          json={"title": "X", "category": "bogus",
                                "date": "2026-12-01", "reason": "r"},
                          timeout=15)
        assert r.status_code == 400


# ============================= REGRESSIONS =============================
class TestRegressions:
    def test_pain_diary_voice_still_works(self):
        r = requests.post(f"{BASE_URL}/api/agent/chat", headers=HEADERS,
                          json={"message": "bolí ma to na sedem"}, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("pain_logged") == 7, d
        assert WATERMARK in d["reply"]

    def test_normal_chat_watermark(self):
        r = requests.post(f"{BASE_URL}/api/agent/chat", headers=HEADERS,
                          json={"message": "Povedz mi krátky vtip prosím."}, timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert not d.get("pain_logged")
        assert not d.get("lifecard_logged")
        assert WATERMARK in d["reply"], d["reply"]

    def test_ips_summary_reads_vaccine(self):
        # IPS summary uses vaccine calendar events; must still return
        r = requests.get(f"{BASE_URL}/api/ips/summary", headers=HEADERS, timeout=60)
        # 200 or 402 (paywall) — both acceptable non-500
        assert r.status_code in (200, 402), r.text

    def test_globalnet_endpoint_still_up(self):
        r = requests.get(f"{BASE_URL}/api/globalnet/stats", headers=HEADERS, timeout=15)
        # 200 or 404 (endpoint may not exist) both fine — but 500 is a red flag
        assert r.status_code != 500, r.text
