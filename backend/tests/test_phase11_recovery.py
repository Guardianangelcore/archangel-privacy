# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""
Iteration 10 — My Recovery (Hustle Recovery Guard) module tests.
Covers: /api/recovery/epn PUT+GET, /api/recovery/sickpay, /api/recovery/extract-outings,
        /api/recovery/report.pdf, plus quick stability sanity endpoints.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://global-compass-hub.preview.emergentagent.com").rstrip("/")
TOKEN = "smoketok-fresh-2026"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- ePN PUT + GET ----------
class TestRecoveryEpn:
    def test_01_put_epn_happy_path(self, sess):
        payload = {
            "start_date": "2026-06-20",
            "end_date": "2026-07-15",
            "note": "TEST recovery — smoke test",
            "contract_type": "dpp",
            "monthly_gross": 850,
            "country": "SK",
            "outings": [
                {"from_time": "10:00", "to_time": "12:00"},
                {"from_time": "16:00", "to_time": "18:00"},
            ],
        }
        r = sess.put(f"{BASE_URL}/api/recovery/epn", json=payload, headers=HEADERS)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["start_date"] == "2026-06-20"
        assert data["contract_type"] == "dpp"
        assert data["monthly_gross"] == 850
        assert len(data["outings"]) == 2

    def test_02_get_epn_returns_saved(self, sess):
        r = sess.get(f"{BASE_URL}/api/recovery/epn", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert data.get("start_date") == "2026-06-20"
        assert data.get("contract_type") == "dpp"
        outs = data.get("outings", [])
        assert len(outs) == 2
        assert outs[0]["from_time"] == "10:00"
        assert outs[1]["to_time"] == "18:00"

    def test_03_bad_date_format(self, sess):
        r = sess.put(
            f"{BASE_URL}/api/recovery/epn",
            json={"start_date": "20-06-2026", "contract_type": "dpp"},
            headers=HEADERS,
        )
        assert r.status_code == 400

    def test_04_bad_outing_time(self, sess):
        r = sess.put(
            f"{BASE_URL}/api/recovery/epn",
            json={
                "start_date": "2026-06-20",
                "contract_type": "dpp",
                "outings": [{"from_time": "25:00", "to_time": "12:00"}],
            },
            headers=HEADERS,
        )
        assert r.status_code == 400

    def test_05_invalid_contract_type(self, sess):
        r = sess.put(
            f"{BASE_URL}/api/recovery/epn",
            json={"start_date": "2026-06-20", "contract_type": "bogus"},
            headers=HEADERS,
        )
        assert r.status_code == 400


# ---------- SICK PAY ----------
class TestSickPay:
    def test_06_dpp_30d_math(self, sess):
        r = sess.post(
            f"{BASE_URL}/api/recovery/sickpay",
            json={"contract_type": "dpp", "monthly_gross": 850, "days": 30},
            headers=HEADERS,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        # DVZ ≈ 850*12/365 = 27.945...
        assert 27.9 <= d["dvz"] <= 28.0, f"dvz={d['dvz']}"
        # breakdown structure
        assert len(d["breakdown"]) == 3
        assert d["breakdown"][0]["days"] == 3
        assert d["breakdown"][1]["days"] == 7
        assert d["breakdown"][2]["days"] == 20
        # total ≈ 435.95
        assert 430 <= d["total_estimate"] <= 442, f"total={d['total_estimate']}"
        assert "shortfall_pct" in d
        # DPP warning
        assert any("DPP" in w or "DPČ" in w for w in d["warnings"])

    def test_07_days_5_no_day11_amount(self, sess):
        r = sess.post(
            f"{BASE_URL}/api/recovery/sickpay",
            json={"contract_type": "fulltime", "monthly_gross": 850, "days": 5},
            headers=HEADERS,
        )
        assert r.status_code == 200
        d = r.json()
        # day11+ amount == 0
        assert d["breakdown"][2]["amount"] == 0
        assert d["breakdown"][2]["days"] == 0

    def test_08_invalid_gross(self, sess):
        r = sess.post(
            f"{BASE_URL}/api/recovery/sickpay",
            json={"contract_type": "fulltime", "monthly_gross": 0, "days": 30},
            headers=HEADERS,
        )
        assert r.status_code == 400

    def test_09_invalid_days(self, sess):
        r = sess.post(
            f"{BASE_URL}/api/recovery/sickpay",
            json={"contract_type": "fulltime", "monthly_gross": 850, "days": 0},
            headers=HEADERS,
        )
        assert r.status_code == 400

    def test_10_shortfall_triggers_solidarity(self, sess):
        # 30d DPP with 850 gross → shortfall ~ 850-436 = 414 (48%) → solidarity_suggested true
        r = sess.post(
            f"{BASE_URL}/api/recovery/sickpay",
            json={"contract_type": "dpp", "monthly_gross": 850, "days": 30},
            headers=HEADERS,
        )
        d = r.json()
        assert d["shortfall_pct"] >= 30
        assert d["solidarity_suggested"] is True


# ---------- AI OUTING EXTRACTION ----------
class TestOutingExtract:
    def test_11_extract_slovak_epn(self, sess):
        text = (
            "Pacient: Ján Novák, ePN vydaný lekárom dňa 20.6.2026. "
            "Vychádzky povolené od 10:00 do 12:00 a od 16:00 do 18:00. "
            "Kľud na lôžku mimo týchto hodín."
        )
        r = sess.post(
            f"{BASE_URL}/api/recovery/extract-outings",
            json={"text": text},
            headers=HEADERS,
            timeout=90,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["found"] is True
        assert len(d["outings"]) == 2
        times = sorted([o["from_time"] for o in d["outings"]])
        assert "10:00" in times
        assert "16:00" in times

    def test_12_extract_gibberish_no_hours(self, sess):
        r = sess.post(
            f"{BASE_URL}/api/recovery/extract-outings",
            json={"text": "Lorem ipsum dolor sit amet, no outing information here."},
            headers=HEADERS,
            timeout=90,
        )
        assert r.status_code == 200
        d = r.json()
        assert d["found"] is False


# ---------- PDF REPORT ----------
class TestRecoveryPdf:
    def test_13_pdf_employer_header(self, sess):
        r = sess.get(f"{BASE_URL}/api/recovery/report.pdf?kind=employer", headers=HEADERS)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")
        assert len(r.content) > 500
        assert r.content[:4] == b"%PDF"

    def test_14_pdf_social(self, sess):
        r = sess.get(f"{BASE_URL}/api/recovery/report.pdf?kind=social", headers=HEADERS)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")

    def test_15_pdf_token_query_param(self, sess):
        # No Authorization header, only ?token=
        r = requests.get(f"{BASE_URL}/api/recovery/report.pdf?kind=employer&token={TOKEN}")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")

    def test_16_pdf_403_without_auth(self, sess):
        r = requests.get(f"{BASE_URL}/api/recovery/report.pdf?kind=employer")
        # backend uses _auth_pdf → 401 or 403 without any token
        assert r.status_code in (401, 403)


# ---------- STABILITY SANITY (do not run full pytest) ----------
class TestStabilitySanity:
    def test_17_auth_me(self, sess):
        r = sess.get(f"{BASE_URL}/api/auth/me", headers=HEADERS)
        assert r.status_code == 200
        d = r.json()
        # /api/auth/me returns {"user": {...}}
        assert d["user"]["user_id"] == "smoketest-user-1"
        assert d["user"]["tos_accepted_version"]

    def test_18_health_drop_me(self, sess):
        r = sess.get(f"{BASE_URL}/api/health-drop/me", headers=HEADERS)
        assert r.status_code == 200
        assert "drop_id" in r.json()

    def test_19_calendar_timeline(self, sess):
        r = sess.get(f"{BASE_URL}/api/calendar/timeline", headers=HEADERS)
        assert r.status_code == 200
        d = r.json()
        assert "events" in d
        assert "upcoming_exams" in d
        assert "booster_alerts" in d

    def test_20_autobook_one_call(self, sess):
        r = sess.post(
            f"{BASE_URL}/api/autobook",
            json={"specialty": "Kardiológia", "source": "manual"},
            headers=HEADERS,
        )
        assert r.status_code == 200
        d = r.json()
        assert d.get("booking", {}).get("status") == "booked"
        assert d.get("calendar_event") is not None
        assert d.get("simulated") is True

    def test_21_mental_techniques_en(self, sess):
        r = sess.get(f"{BASE_URL}/api/mental/techniques?language=en", headers=HEADERS)
        assert r.status_code == 200
        d = r.json()
        assert "techniques" in d
        assert len(d["techniques"]) == 6


# ---------- RESTORE ORIGINAL EPN STATE ----------
class TestRestoreState:
    def test_99_restore_epn_to_original(self, sess):
        """Leave smoke user with outings 10-12 & 16-18 as instructed."""
        payload = {
            "start_date": "2026-06-20",
            "end_date": "2026-07-15",
            "note": "",
            "contract_type": "dpp",
            "monthly_gross": 850,
            "country": "SK",
            "outings": [
                {"from_time": "10:00", "to_time": "12:00"},
                {"from_time": "16:00", "to_time": "18:00"},
            ],
        }
        r = sess.put(f"{BASE_URL}/api/recovery/epn", json=payload, headers=HEADERS)
        assert r.status_code == 200
