# Iter 66 — MEGA-BATCH backend regression
# Tests: agents/status, agents/run, features/catalog, features/buy,
#        me/user-type, health-card GET/PUT, nearby/care?kind=shelter, creator/earnings
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL") or os.environ.get("EXPO_BACKEND_URL")
if not BASE_URL:
    # Fall back to reading /app/frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
                BASE_URL = line.strip().split("=", 1)[1].strip('"')
                break
BASE_URL = BASE_URL.rstrip("/")
TOKEN = "smoketok-fresh-2026"


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"})
    return s


# ---------------- Multi-agent
class TestAgents:
    def test_status(self, api):
        r = api.get(f"{BASE_URL}/api/agents/status", timeout=15)
        assert r.status_code == 200, r.text
        j = r.json()
        assert "agents" in j and isinstance(j["agents"], list)
        ids = {a["id"] for a in j["agents"]}
        assert ids == {"jarvis", "lens", "scribe", "analyst", "guardian"}, ids
        for a in j["agents"]:
            assert isinstance(a.get("active"), bool)
        # smoketok is archangel tier per test_credentials
        assert j.get("tier") == "archangel", j.get("tier")
        assert j.get("priority") is True
        assert all(a["active"] for a in j["agents"]), j["agents"]

    def test_run_text_slovak(self, api):
        body = {"input_type": "text",
                "text": "Beriem ibuprofen a warfarín, je to v poriadku?",
                "language": "sk"}
        r = api.post(f"{BASE_URL}/api/agents/run", json=body, timeout=90)
        assert r.status_code == 200, r.text
        j = r.json()
        reply = j.get("reply") or ""
        assert isinstance(reply, str) and len(reply.strip()) > 0
        trace = j.get("trace") or []
        agents_in_trace = {t.get("agent") for t in trace}
        # scribe / analyst / jarvis expected present
        for aid in ("scribe", "analyst", "jarvis"):
            assert aid in agents_in_trace, f"{aid} missing in trace: {trace}"
        # done status for those three
        done = {t.get("agent") for t in trace if t.get("status") == "done"}
        for aid in ("scribe", "analyst", "jarvis"):
            assert aid in done, f"{aid} not done: {trace}"


# ---------------- Features catalog / buy
class TestFeatures:
    def test_catalog(self, api):
        r = api.get(f"{BASE_URL}/api/features/catalog", timeout=15)
        assert r.status_code == 200, r.text
        j = r.json()
        assert "features" in j and len(j["features"]) == 4
        by_id = {f["id"]: f for f in j["features"]}
        assert by_id["ghost_mode"]["eur"] == 2.99 and by_id["ghost_mode"]["gat"] == 30.0
        assert by_id["bunker"]["eur"] == 1.99 and by_id["bunker"]["gat"] == 20.0
        assert by_id["analyst"]["eur"] == 3.99 and by_id["analyst"]["gat"] == 40.0
        assert by_id["mesh_sms"]["eur"] == 1.49 and by_id["mesh_sms"]["gat"] == 15.0
        for f in j["features"]:
            assert "unlocked" in f

    def test_buy_bunker_gat(self, api):
        r = api.post(f"{BASE_URL}/api/features/buy",
                     json={"feature": "bunker", "currency": "gat"}, timeout=15)
        # Acceptable: 200 ok:true or 402 insufficient
        assert r.status_code in (200, 402), r.text
        if r.status_code == 200:
            j = r.json()
            assert j.get("ok") is True

    def test_buy_bad_feature(self, api):
        r = api.post(f"{BASE_URL}/api/features/buy",
                     json={"feature": "nope", "currency": "gat"}, timeout=15)
        assert r.status_code == 400, r.text

    def test_buy_bad_currency(self, api):
        r = api.post(f"{BASE_URL}/api/features/buy",
                     json={"feature": "ghost_mode", "currency": "xyz"}, timeout=15)
        assert r.status_code == 400, r.text


# ---------------- User type
class TestUserType:
    def test_set_clinician_then_reflected_in_me(self, api):
        r = api.put(f"{BASE_URL}/api/me/user-type",
                    json={"user_type": "clinician"}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("user_type") == "clinician"

        me = api.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert me.status_code == 200, me.text
        j = me.json()
        # /api/auth/me returns {user: {...}} or user itself; handle both
        user = j.get("user") if isinstance(j, dict) and "user" in j else j
        assert user.get("user_type") == "clinician", j

    def test_invalid_user_type(self, api):
        r = api.put(f"{BASE_URL}/api/me/user-type",
                    json={"user_type": "alien"}, timeout=15)
        assert r.status_code == 400, r.text

    def test_set_back_to_adult(self, api):
        r = api.put(f"{BASE_URL}/api/me/user-type",
                    json={"user_type": "adult"}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("user_type") == "adult"


# ---------------- Health card
class TestHealthCard:
    def test_get_baseline(self, api):
        r = api.get(f"{BASE_URL}/api/health-card", timeout=15)
        assert r.status_code == 200, r.text
        j = r.json()
        for k in ("contracts", "documents", "claims", "birth_cert", "eu_card"):
            assert k in j, f"missing {k}"
        assert isinstance(j["documents"], list)
        assert isinstance(j["claims"], list)

    def test_put_and_read(self, api):
        payload = {
            "insurance_number": "1234567890",
            "insurer": "VšZP",
            "contracts": [{"title": "Life", "insurer": "Allianz",
                           "number": "A1", "valid_until": "2030-01-01"}],
        }
        r = api.put(f"{BASE_URL}/api/health-card", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("insurance_number") == "1234567890"
        assert j.get("insurer") == "VšZP"
        assert any(c.get("title") == "Life" for c in (j.get("contracts") or []))

        r2 = api.get(f"{BASE_URL}/api/health-card", timeout=15)
        assert r2.status_code == 200
        j2 = r2.json()
        assert j2.get("insurance_number") == "1234567890"
        assert j2.get("insurer") == "VšZP"


# ---------------- Nearby shelter
class TestNearby:
    def test_shelter(self, api):
        r = api.get(
            f"{BASE_URL}/api/nearby/care",
            params={"kind": "shelter", "lat": 48.1486, "lng": 17.1077, "radius": 15000},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        j = r.json()
        assert "results" in j and isinstance(j["results"], list)

    def test_kind_bogus(self, api):
        r = api.get(
            f"{BASE_URL}/api/nearby/care",
            params={"kind": "bogus", "lat": 48.1486, "lng": 17.1077},
            timeout=15,
        )
        assert r.status_code == 400, r.text


# ---------------- Creator earnings (smoketok is not creator → 403)
class TestCreator:
    def test_forbidden_for_smoketok(self, api):
        r = api.get(f"{BASE_URL}/api/creator/earnings", timeout=15)
        assert r.status_code == 403, r.text
        detail = (r.json().get("detail") or "").lower()
        assert "creator" in detail, detail
