"""Iteration 78 — GA-T Community Help (peer-verified Proof-of-Help, escrow) + self-claim block."""
import os, uuid, requests
from datetime import datetime, timezone, timedelta

BASE = os.environ.get("EXPO_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/") + "/api"
FOUNDER = "guardianangel.core@proton.me"


def _bypass(email, name="T"):
    r = requests.post(f"{BASE}/auth/dev-bypass", json={"email": email, "name": name}, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json(); return {"token": d["session_token"], "user_id": d["user"]["user_id"], "email": email, "name": name}


def _fresh(tag): return _bypass(f"iter78-{tag}-{uuid.uuid4().hex[:8]}@example.com", f"Iter78 {tag}")
def _h(u): return {"Authorization": f"Bearer {u['token']}"}


def _founder():
    """Founder signs in with password (dev-bypass refuses privileged accounts since Iter 82)."""
    r = requests.post(f"{BASE}/auth/login", json={"email": FOUNDER, "password": os.environ.get("FOUNDER_TEST_PASSWORD", "GA-v=#2!WKkktgyW1u7bdqt")}, timeout=15)
    assert r.status_code == 200, f"founder login failed: {r.status_code} {r.text}"
    d = r.json(); return {"token": d["session_token"], "user_id": d["user"]["user_id"], "email": FOUNDER, "user": d["user"], "name": "Guardian Angel"}
def _bal(u): return requests.get(f"{BASE}/token/wallet", headers=_h(u), timeout=15).json()["balance"]


def _fund(u, amount):
    """Deterministic wallet funding straight in Mongo (test-only; the founder wallet may be drained by other suites)."""
    from pymongo import MongoClient
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    db.token_accounts.update_one({"user_id": u["user_id"]}, {"$inc": {"balance": float(amount)}, "$setOnInsert": {"earned_total": 0.0, "spent_total": 0.0}}, upsert=True)


def _create(u, title="Buy my medication"):
    r = requests.post(f"{BASE}/help/requests", headers=_h(u), json={"title": title, "details": "Pharmacy on the corner", "category": "medication"}, timeout=15)
    assert r.status_code == 201, r.text
    return r.json()["request"]


def test_self_claim_blocked():
    u = _fresh("self")
    r = requests.post(f"{BASE}/token/earn", headers=_h(u), json={"activity": "proof_of_help"}, timeout=15)
    assert r.status_code == 403 and "verified_only" in r.text
    r = requests.post(f"{BASE}/token/earn", headers=_h(u), json={"activity": "community_support"}, timeout=15)
    assert r.status_code == 403


def test_full_flow_wallet_escrow_to_helper():
    grandma, helper = _fresh("gran"), _fresh("help")
    _fund(grandma, 25)
    req = _create(grandma)
    assert req["status"] == "open" and req["reserved"] == {"wallet": 10.0, "fund": 0.0} and req["reward"] == 10
    assert _bal(grandma) == 15.0                                             # escrowed immediately
    # helper sees it in OPEN, grandma does not see her own in OPEN
    open_ids = [r["req_id"] for r in requests.get(f"{BASE}/help/requests?scope=open", headers=_h(helper), timeout=15).json()["requests"]]
    assert req["req_id"] in open_ids
    assert req["req_id"] not in [r["req_id"] for r in requests.get(f"{BASE}/help/requests?scope=open", headers=_h(grandma), timeout=15).json()["requests"]]
    # grandma cannot accept her own; helper accepts; second accept → 409
    assert requests.post(f"{BASE}/help/requests/{req['req_id']}/accept", headers=_h(grandma), timeout=15).status_code == 400
    assert requests.post(f"{BASE}/help/requests/{req['req_id']}/accept", headers=_h(helper), timeout=15).status_code == 200
    assert requests.post(f"{BASE}/help/requests/{req['req_id']}/accept", headers=_h(_fresh("late")), timeout=15).status_code == 409
    # confirm before done → 409 ; done by non-helper → 409
    assert requests.post(f"{BASE}/help/requests/{req['req_id']}/confirm", headers=_h(grandma), timeout=15).status_code == 409
    assert requests.post(f"{BASE}/help/requests/{req['req_id']}/done", headers=_h(grandma), timeout=15).status_code == 409
    r = requests.post(f"{BASE}/help/requests/{req['req_id']}/done", headers=_h(helper), timeout=15)
    assert r.status_code == 200 and r.json()["request"]["status"] == "done"
    # only requester confirms
    assert requests.post(f"{BASE}/help/requests/{req['req_id']}/confirm", headers=_h(helper), timeout=15).status_code == 403
    before = _bal(helper)
    r = requests.post(f"{BASE}/help/requests/{req['req_id']}/confirm", headers=_h(grandma), timeout=15)
    assert r.status_code == 200 and r.json()["request"]["status"] == "confirmed"
    assert _bal(helper) == before + 10.0
    assert _bal(grandma) == 15.0                                             # nothing more taken
    # double confirm → 409 (no double payout)
    assert requests.post(f"{BASE}/help/requests/{req['req_id']}/confirm", headers=_h(grandma), timeout=15).status_code == 409
    assert _bal(helper) == before + 10.0
    ledger = requests.get(f"{BASE}/token/wallet", headers=_h(helper), timeout=15).json()["txs"]
    assert any(t["kind"] == "help_reward" and t["amount"] == 10.0 for t in ledger)


def test_community_fund_tops_up_poor_requester():
    grandma = _fresh("poor")
    _fund(grandma, 4)
    req = _create(grandma, "Walk with me to the doctor")
    assert req["reserved"] == {"wallet": 4.0, "fund": 6.0} and req["reward"] == 10
    assert _bal(grandma) == 0.0
    # cancel while open → wallet part refunded, fund part back to treasury
    r = requests.post(f"{BASE}/help/requests/{req['req_id']}/cancel", headers=_h(grandma), timeout=15)
    assert r.status_code == 200 and r.json()["request"]["status"] == "cancelled"
    assert _bal(grandma) == 4.0
    # zero-balance requester: fully fund-covered
    broke = _fresh("broke")
    req2 = _create(broke, "Change a light bulb")
    assert req2["reserved"] == {"wallet": 0.0, "fund": 10.0}


def test_daily_request_cap():
    u = _fresh("cap")
    for i in range(5):
        _create(u, f"Task {i}")
    r = requests.post(f"{BASE}/help/requests", headers=_h(u), json={"title": "Task 6", "category": "other"}, timeout=15)
    assert r.status_code == 429 and "daily_limit" in r.text
    lim = requests.get(f"{BASE}/help/requests?scope=mine", headers=_h(u), timeout=15).json()["limits"]
    assert lim["requests_today"] == 5 and lim["daily_max"] == 5


def test_expiry_refunds_after_24h_unconfirmed():
    """Simulate the 24 h window by rewinding expires_at in Mongo, then trigger the sweep via a list call."""
    from pymongo import MongoClient
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    grandma, helper = _fresh("exp"), _fresh("exph")
    _fund(grandma, 10)
    req = _create(grandma, "Carry groceries")
    requests.post(f"{BASE}/help/requests/{req['req_id']}/accept", headers=_h(helper), timeout=15)
    requests.post(f"{BASE}/help/requests/{req['req_id']}/done", headers=_h(helper), timeout=15)
    assert _bal(grandma) == 0.0
    db.help_requests.update_one({"req_id": req["req_id"]}, {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(minutes=1)}})
    rows = requests.get(f"{BASE}/help/requests?scope=mine", headers=_h(grandma), timeout=15).json()["requests"]
    mine = next(r for r in rows if r["req_id"] == req["req_id"])
    assert mine["status"] == "expired"
    assert _bal(grandma) == 10.0                                             # escrow returned
    assert _bal(helper) == 0.0
    # late confirm impossible
    assert requests.post(f"{BASE}/help/requests/{req['req_id']}/confirm", headers=_h(grandma), timeout=15).status_code == 409
