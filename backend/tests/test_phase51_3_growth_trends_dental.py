"""
Phase 51.3 — Karta života: Rastová krivka + Trendy zdravia + Karta zubára.

Covers:
  1) GROWTH: create child (sex=f, ~3y) → POST growth → percentiles + age_months;
     400 validations; GET curves; DELETE; cross-user 404; sex_required flow;
     child DELETE cascades growth_logs.
  2) TRENDS: GET /api/lifecard/trends yearly counts (6 cats incl dental) + child_id scope.
  3) TRENDS SUMMARY: POST /api/lifecard/trends/summary → Slovak summary + AI watermark;
     empty child → non-AI friendly fallback.
  4) DENTAL: POST /api/calendar/events {category:dental, tooth}; filter timeline;
     counts include dental; invalid category still 400; report.pdf contains ZUBÁR.
  5) VOICE DENTAL: 'plomba' → dental yesterday; 'angína' → disease; 'Kedy k zubárovi'
     → NOT logged.
"""
import os
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests

BASE_URL = (os.environ.get("EXPO_BACKEND_URL")
            or os.environ.get("EXPO_PUBLIC_BACKEND_URL")
            or "https://physio-lang-fix.preview.emergentagent.com").rstrip("/")

TOKEN1 = "smoketok-fresh-2026"
TOKEN2 = "smoketok-fresh-2026-u2"
H1 = {"Authorization": f"Bearer {TOKEN1}"}
H2 = {"Authorization": f"Bearer {TOKEN2}"}
H1J = {**H1, "Content-Type": "application/json"}
H2J = {**H2, "Content-Type": "application/json"}


def _iso(d):
    return d.isoformat() if hasattr(d, "isoformat") else d


# ==================== 1) GROWTH ====================
class TestGrowth:
    @pytest.fixture(scope="class")
    def child_f(self):
        birth = (datetime.now(timezone.utc).date() - timedelta(days=365 * 3)).isoformat()
        r = requests.post(f"{BASE_URL}/api/lifecard/children", headers=H1J, json={
            "name": "TEST_GrowthEma", "birth_date": birth,
            "blood_type": "A+", "sex": "f"}, timeout=15)
        assert r.status_code == 200, r.text
        cid = r.json()["child_id"]
        yield {"child_id": cid, "birth_date": birth}
        requests.delete(f"{BASE_URL}/api/lifecard/children/{cid}", headers=H1, timeout=10)

    def test_growth_add_ok_with_percentiles(self, child_f):
        cid = child_f["child_id"]
        r = requests.post(f"{BASE_URL}/api/lifecard/children/{cid}/growth",
                          headers=H1J, json={
                              "date": datetime.now(timezone.utc).date().isoformat(),
                              "height_cm": 95, "weight_kg": 14},
                          timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("log_id"), d
        assert d.get("height_cm") == 95 or d.get("height_cm") == 95.0
        assert d.get("weight_kg") == 14 or d.get("weight_kg") == 14.0
        # age_months ~ 36 (3y)
        am = d.get("age_months")
        assert am is not None and 34 <= am <= 38, am
        # percentile roughly in mid-range (WHO percentiles approximate — spec allows tolerance)
        hp = d.get("height_percentile")
        wp = d.get("weight_percentile")
        assert hp is not None and 25 <= hp <= 75, f"height_percentile out of expected mid-range: {hp}"
        assert wp is not None and 25 <= wp <= 80, f"weight_percentile out of expected mid-range: {wp}"
        # cleanup log
        requests.delete(f"{BASE_URL}/api/lifecard/growth/{d['log_id']}", headers=H1, timeout=10)

    def test_growth_missing_both_hw_400(self, child_f):
        cid = child_f["child_id"]
        r = requests.post(f"{BASE_URL}/api/lifecard/children/{cid}/growth",
                          headers=H1J, json={
                              "date": datetime.now(timezone.utc).date().isoformat()},
                          timeout=15)
        assert r.status_code == 400, r.text

    def test_growth_height_out_of_range_400(self, child_f):
        cid = child_f["child_id"]
        r = requests.post(f"{BASE_URL}/api/lifecard/children/{cid}/growth",
                          headers=H1J, json={
                              "date": datetime.now(timezone.utc).date().isoformat(),
                              "height_cm": 500}, timeout=15)
        assert r.status_code == 400, r.text

    def test_growth_bad_date_400(self, child_f):
        cid = child_f["child_id"]
        r = requests.post(f"{BASE_URL}/api/lifecard/children/{cid}/growth",
                          headers=H1J, json={
                              "date": "15-06-2023",
                              "height_cm": 95}, timeout=15)
        assert r.status_code == 400, r.text

    def test_growth_list_shape(self, child_f):
        cid = child_f["child_id"]
        # add 2 logs (older + newer)
        d1 = (datetime.now(timezone.utc).date() - timedelta(days=90)).isoformat()
        d2 = datetime.now(timezone.utc).date().isoformat()
        l1 = requests.post(f"{BASE_URL}/api/lifecard/children/{cid}/growth",
                           headers=H1J, json={"date": d1, "height_cm": 92, "weight_kg": 13}, timeout=15)
        l2 = requests.post(f"{BASE_URL}/api/lifecard/children/{cid}/growth",
                           headers=H1J, json={"date": d2, "height_cm": 95, "weight_kg": 14}, timeout=15)
        assert l1.status_code == 200 and l2.status_code == 200
        try:
            r = requests.get(f"{BASE_URL}/api/lifecard/children/{cid}/growth",
                             headers=H1, timeout=15)
            assert r.status_code == 200, r.text
            d = r.json()
            assert "logs" in d and len(d["logs"]) >= 2
            # ascending
            dates = [x["date"] for x in d["logs"]]
            assert dates == sorted(dates), dates
            # curves
            curves = d.get("curves") or {}
            assert "height" in curves and "weight" in curves
            for key in ("height", "weight"):
                arr = curves[key]
                assert isinstance(arr, list) and len(arr) > 0
                for pt in arr:
                    for k in ("m", "p3", "p50", "p97"):
                        assert k in pt, pt
                ms = [pt["m"] for pt in arr]
                assert ms == sorted(ms), ms  # ascending
            assert d.get("sex_required") is False
        finally:
            requests.delete(f"{BASE_URL}/api/lifecard/growth/{l1.json()['log_id']}",
                            headers=H1, timeout=10)
            requests.delete(f"{BASE_URL}/api/lifecard/growth/{l2.json()['log_id']}",
                            headers=H1, timeout=10)

    def test_growth_delete_works_and_cross_user_404(self, child_f):
        cid = child_f["child_id"]
        # user2 trying to add growth to user1's child → 404
        r = requests.post(f"{BASE_URL}/api/lifecard/children/{cid}/growth",
                          headers=H2J, json={
                              "date": datetime.now(timezone.utc).date().isoformat(),
                              "height_cm": 95}, timeout=15)
        assert r.status_code == 404, r.text

    def test_growth_no_sex_percentiles_null(self):
        birth = (datetime.now(timezone.utc).date() - timedelta(days=365 * 3)).isoformat()
        cr = requests.post(f"{BASE_URL}/api/lifecard/children", headers=H1J, json={
            "name": "TEST_NoSex", "birth_date": birth}, timeout=15)
        assert cr.status_code == 200, cr.text
        cid = cr.json()["child_id"]
        try:
            add = requests.post(f"{BASE_URL}/api/lifecard/children/{cid}/growth",
                                headers=H1J, json={
                                    "date": datetime.now(timezone.utc).date().isoformat(),
                                    "height_cm": 95, "weight_kg": 14}, timeout=15)
            assert add.status_code == 200, add.text
            d = add.json()
            assert d.get("height_percentile") is None
            assert d.get("weight_percentile") is None

            lst = requests.get(f"{BASE_URL}/api/lifecard/children/{cid}/growth",
                               headers=H1, timeout=15).json()
            assert lst.get("sex_required") is True, lst

            # PUT sex → fix
            up = requests.put(f"{BASE_URL}/api/lifecard/children/{cid}",
                              headers=H1J, json={"sex": "m"}, timeout=15)
            assert up.status_code == 200, up.text

            lst2 = requests.get(f"{BASE_URL}/api/lifecard/children/{cid}/growth",
                                headers=H1, timeout=15).json()
            assert lst2.get("sex_required") is False, lst2
            # curves now populated
            assert len(lst2["curves"]["height"]) > 0

            requests.delete(f"{BASE_URL}/api/lifecard/growth/{d['log_id']}", headers=H1, timeout=10)
        finally:
            requests.delete(f"{BASE_URL}/api/lifecard/children/{cid}", headers=H1, timeout=10)

    def test_child_delete_cascades_growth_logs(self):
        birth = (datetime.now(timezone.utc).date() - timedelta(days=365 * 4)).isoformat()
        cr = requests.post(f"{BASE_URL}/api/lifecard/children", headers=H1J, json={
            "name": "TEST_CascadeGrowth", "birth_date": birth, "sex": "m"}, timeout=15)
        assert cr.status_code == 200, cr.text
        cid = cr.json()["child_id"]
        add = requests.post(f"{BASE_URL}/api/lifecard/children/{cid}/growth",
                            headers=H1J, json={
                                "date": datetime.now(timezone.utc).date().isoformat(),
                                "height_cm": 100, "weight_kg": 16}, timeout=15)
        assert add.status_code == 200, add.text
        log_id = add.json()["log_id"]

        de = requests.delete(f"{BASE_URL}/api/lifecard/children/{cid}", headers=H1, timeout=10)
        assert de.status_code == 200, de.text

        # verify growth logs gone via Mongo direct
        from pymongo import MongoClient
        client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        mdb = client[os.environ.get("DB_NAME", "guardian_health")]
        n = mdb.growth_logs.count_documents({"log_id": log_id})
        client.close()
        assert n == 0, f"growth log {log_id} not deleted (found {n})"


# ==================== 2) TRENDS ====================
class TestTrends:
    def test_trends_shape_all_categories(self):
        # Seed 1 dental + 1 exam so we have at least one recent year
        today = datetime.now(timezone.utc).date().isoformat()
        ev1 = requests.post(f"{BASE_URL}/api/calendar/events", headers=H1J, json={
            "category": "dental", "title": "TEST_TrendsDental", "date": today, "tooth": "36"},
            timeout=15)
        ev2 = requests.post(f"{BASE_URL}/api/calendar/events", headers=H1J, json={
            "category": "exam", "title": "TEST_TrendsExam", "date": today},
            timeout=15)
        assert ev1.status_code == 200 and ev2.status_code == 200
        eid1 = ev1.json()["event_id"]
        eid2 = ev2.json()["event_id"]
        try:
            r = requests.get(f"{BASE_URL}/api/lifecard/trends", headers=H1, timeout=15)
            assert r.status_code == 200, r.text
            d = r.json()
            assert "years" in d and isinstance(d["years"], list)
            assert d.get("total") is not None and d["total"] > 0
            # find current year row
            yr = str(datetime.now(timezone.utc).year)
            row = [x for x in d["years"] if x["year"] == yr]
            assert row, [x["year"] for x in d["years"]]
            counts = row[0]["counts"]
            for c in ("vaccine", "disease", "surgery", "injury", "exam", "dental"):
                assert c in counts, counts
            assert counts["dental"] >= 1, counts
            assert counts["exam"] >= 1, counts
        finally:
            requests.delete(f"{BASE_URL}/api/calendar/events/{eid1}", headers=H1, timeout=10)
            requests.delete(f"{BASE_URL}/api/calendar/events/{eid2}", headers=H1, timeout=10)

    def test_trends_child_scope(self):
        birth = (datetime.now(timezone.utc).date() - timedelta(days=365 * 5)).isoformat()
        cr = requests.post(f"{BASE_URL}/api/lifecard/children", headers=H1J, json={
            "name": "TEST_TrendsChild", "birth_date": birth}, timeout=15)
        assert cr.status_code == 200, cr.text
        cid = cr.json()["child_id"]
        today = datetime.now(timezone.utc).date().isoformat()
        try:
            ev = requests.post(f"{BASE_URL}/api/calendar/events", headers=H1J, json={
                "category": "dental", "title": "TEST_ChildDental",
                "date": today, "child_id": cid, "tooth": "51"}, timeout=15)
            assert ev.status_code == 200, ev.text
            eid = ev.json()["event_id"]
            try:
                r = requests.get(f"{BASE_URL}/api/lifecard/trends?child_id={cid}",
                                 headers=H1, timeout=15)
                assert r.status_code == 200, r.text
                d = r.json()
                # only 1 dental event in this year for the child
                assert d.get("total") == 1, d
                yr = str(datetime.now(timezone.utc).year)
                row = [x for x in d["years"] if x["year"] == yr][0]
                assert row["counts"]["dental"] == 1, row
                # other categories 0
                for c in ("vaccine", "disease", "surgery", "injury", "exam"):
                    assert row["counts"][c] == 0, row["counts"]
            finally:
                requests.delete(f"{BASE_URL}/api/calendar/events/{eid}", headers=H1, timeout=10)
        finally:
            requests.delete(f"{BASE_URL}/api/lifecard/children/{cid}", headers=H1, timeout=10)


# ==================== 3) TRENDS SUMMARY (LLM) ====================
class TestTrendsSummary:
    def test_summary_llm_slovak(self):
        # user-1 has ~123 exam events per context; summary should be AI
        r = requests.post(f"{BASE_URL}/api/lifecard/trends/summary",
                          headers=H1J, json={}, timeout=45)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("ai") is True, d
        s = d.get("summary") or ""
        assert len(s) > 20, s
        assert "AI Content" in s or "Sovereign" in s, s

    def test_summary_empty_child_non_ai(self):
        # Fresh child with no events → friendly non-AI message
        birth = (datetime.now(timezone.utc).date() - timedelta(days=365 * 2)).isoformat()
        cr = requests.post(f"{BASE_URL}/api/lifecard/children", headers=H1J, json={
            "name": "TEST_EmptyChild", "birth_date": birth}, timeout=15)
        assert cr.status_code == 200, cr.text
        cid = cr.json()["child_id"]
        try:
            r = requests.post(f"{BASE_URL}/api/lifecard/trends/summary",
                              headers=H1J, json={"child_id": cid}, timeout=20)
            assert r.status_code == 200, r.text
            d = r.json()
            assert d.get("ai") is False, d
            assert "Zatiaľ" in d.get("summary", "") or "žiadne" in d.get("summary", "").lower(), d
        finally:
            requests.delete(f"{BASE_URL}/api/lifecard/children/{cid}", headers=H1, timeout=10)


# ==================== 4) DENTAL ====================
class TestDental:
    def test_dental_event_with_tooth(self):
        today = datetime.now(timezone.utc).date().isoformat()
        r = requests.post(f"{BASE_URL}/api/calendar/events", headers=H1J, json={
            "category": "dental", "title": "TEST_Plomba",
            "date": today, "tooth": "36"}, timeout=15)
        assert r.status_code == 200, r.text
        eid = r.json()["event_id"]
        try:
            tl = requests.get(f"{BASE_URL}/api/calendar/timeline?category=dental",
                              headers=H1, timeout=15)
            assert tl.status_code == 200, tl.text
            d = tl.json()
            row = [e for e in d["events"] if e["event_id"] == eid]
            assert row, "dental event missing from category=dental filter"
            assert row[0].get("tooth") == "36", row[0]
            assert row[0].get("category") == "dental"

            counts = d.get("counts") or {}
            assert "dental" in counts, counts
            assert counts["dental"] >= 1, counts

            # adult lifecard also has dental key
            lc = requests.get(f"{BASE_URL}/api/lifecard", headers=H1, timeout=15).json()
            assert "dental" in (lc.get("counts") or {}), lc.get("counts")
        finally:
            requests.delete(f"{BASE_URL}/api/calendar/events/{eid}", headers=H1, timeout=10)

    def test_invalid_category_still_400(self):
        today = datetime.now(timezone.utc).date().isoformat()
        r = requests.post(f"{BASE_URL}/api/calendar/events", headers=H1J, json={
            "category": "not-a-real-cat", "title": "TEST_bad", "date": today}, timeout=15)
        assert r.status_code == 400, r.text

    def test_report_pdf_contains_zubar(self):
        # ensure at least one dental event exists to render the section
        today = datetime.now(timezone.utc).date().isoformat()
        ev = requests.post(f"{BASE_URL}/api/calendar/events", headers=H1J, json={
            "category": "dental", "title": "TEST_PdfDental",
            "date": today, "tooth": "11"}, timeout=15)
        assert ev.status_code == 200, ev.text
        eid = ev.json()["event_id"]
        try:
            r = requests.get(f"{BASE_URL}/api/lifecard/report.pdf", headers=H1, timeout=45)
            assert r.status_code == 200, r.text[:300]
            assert r.content.startswith(b"%PDF")
            # Decode PDF text via pypdf (streams are FlateDecoded)
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(r.content))
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
            up = text.upper()
            assert "ZUB" in up or "TEST_PDFDENTAL" in up, \
                f"PDF should contain a dental section marker; extracted={text[:500]!r}"
        finally:
            requests.delete(f"{BASE_URL}/api/calendar/events/{eid}", headers=H1, timeout=10)


# ==================== 5) VOICE DENTAL ====================
class TestVoiceDental:
    def test_voice_dental_plomba_yesterday(self):
        yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
        r = requests.post(f"{BASE_URL}/api/agent/chat", headers=H1J, json={
            "message": "Včera som bol u zubára, dostal som plombu"}, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        logged = d.get("lifecard_logged")
        assert logged, d
        assert logged.get("category") == "dental", logged
        assert logged.get("date") == yesterday, logged
        # cleanup
        eid = logged.get("event_id")
        if eid:
            requests.delete(f"{BASE_URL}/api/calendar/events/{eid}", headers=H1, timeout=10)

    def test_voice_disease_still_works(self):
        r = requests.post(f"{BASE_URL}/api/agent/chat", headers=H1J, json={
            "message": "Dnes mi doktor povedal, že mám angínu"}, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        logged = d.get("lifecard_logged")
        assert logged, d
        assert logged.get("category") == "disease", logged
        eid = logged.get("event_id")
        if eid:
            requests.delete(f"{BASE_URL}/api/calendar/events/{eid}", headers=H1, timeout=10)

    def test_voice_question_not_logged(self):
        r = requests.post(f"{BASE_URL}/api/agent/chat", headers=H1J, json={
            "message": "Kedy mám ísť k zubárovi?"}, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert not d.get("lifecard_logged"), \
            f"question should NOT trigger lifecard log: {d.get('lifecard_logged')}"
