"""Iteration 77 — ChatGPT AI models (Jarvis model picker) + P0 security hardening:
SEC-001 dev-bypass gate · SEC-003 password_hash never returned · atomic GA-T debits ·
IP rate limits · iap-sync payload whitelist · no unverified fiat unlock paths."""
import os, time, uuid, requests
from concurrent.futures import ThreadPoolExecutor

BASE = os.environ.get("EXPO_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/") + "/api"
FOUNDER = "guardianangel.core@proton.me"


def _bypass(email: str, name: str = "T") -> dict:
    r = requests.post(f"{BASE}/auth/dev-bypass", json={"email": email, "name": name}, timeout=15)
    assert r.status_code == 200, f"dev-bypass failed: {r.status_code} {r.text}"
    d = r.json()
    return {"token": d["session_token"], "user_id": d["user"]["user_id"], "email": email}


def _fresh(tag: str) -> dict:
    return _bypass(f"iter77-{tag}-{uuid.uuid4().hex[:8]}@example.com", f"Iter77 {tag}")


def _h(u): return {"Authorization": f"Bearer {u['token']}"}


def _set_balance(u: dict, amount: float):
    from pymongo import MongoClient
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    db.token_accounts.update_one({"user_id": u["user_id"]}, {"$set": {"balance": float(amount)}, "$setOnInsert": {"earned_total": 0.0, "spent_total": 0.0}}, upsert=True)


# ---------- ChatGPT AI MODELS ----------
def test_models_catalog_shape():
    u = _fresh("models")
    r = requests.get(f"{BASE}/ai/models", headers=_h(u), timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    ids = [m["id"] for m in d["models"]]
    assert ids == ["gpt-5.4-mini", "gpt-5.4", "gpt-5.6-luna", "gpt-5.6-terra"]
    assert d["provider"] == "openai" and d["default"] == "gpt-5.4" and d["selected"] == "gpt-5.4"
    by = {m["id"]: m for m in d["models"]}
    # Sovereign (free) user: 5.4 family open, 5.6 gated (Luna → Guardian, Terra → Sentinel)
    assert by["gpt-5.4"]["locked"] is False and by["gpt-5.4-mini"]["locked"] is False
    assert by["gpt-5.6-luna"]["locked"] is True and by["gpt-5.6-luna"]["min_tier"] == "guardian"
    assert by["gpt-5.6-terra"]["locked"] is True and by["gpt-5.6-terra"]["min_tier"] == "sentinel"


def test_models_select_gate_and_validation():
    u = _fresh("select")
    assert requests.put(f"{BASE}/ai/models/select", headers=_h(u), json={"model": "gpt-9"}, timeout=15).status_code == 400
    r = requests.put(f"{BASE}/ai/models/select", headers=_h(u), json={"model": "gpt-5.6-terra"}, timeout=15)
    assert r.status_code == 402 and "sentinel" in r.text.lower()
    r = requests.put(f"{BASE}/ai/models/select", headers=_h(u), json={"model": "gpt-5.4-mini"}, timeout=15)
    assert r.status_code == 200 and r.json()["selected"] == "gpt-5.4-mini"
    d = requests.get(f"{BASE}/ai/models", headers=_h(u), timeout=15).json()
    assert d["selected"] == "gpt-5.4-mini"
    me = requests.get(f"{BASE}/auth/me", headers=_h(u), timeout=15).json()["user"]
    assert me["jarvis_model"] == "gpt-5.4-mini"


def test_founder_can_pick_terra_and_chat_reports_model():
    f = _bypass(FOUNDER)
    r = requests.put(f"{BASE}/ai/models/select", headers=_h(f), json={"model": "gpt-5.6-luna"}, timeout=15)
    assert r.status_code == 200
    try:
        r = requests.post(f"{BASE}/agent/chat", headers=_h(f), json={"message": "Reply with exactly: MODEL OK"}, timeout=90)
        assert r.status_code == 200, r.text
        assert r.json()["model"] == "gpt-5.6-luna"
        assert "MODEL OK" in r.json()["reply"].upper()
    finally:
        requests.put(f"{BASE}/ai/models/select", headers=_h(f), json={"model": "gpt-5.4"}, timeout=15)


def test_stream_done_event_carries_model():
    f = _bypass(FOUNDER)
    r = requests.post(f"{BASE}/agent/chat/stream", headers=_h(f), json={"message": f"Say hi ({uuid.uuid4().hex[:4]})"}, timeout=90, stream=True)
    assert r.status_code == 200
    body = r.text
    assert '"done": true' in body and '"model": "gpt-5.4"' in body, body[-400:]


# ---------- SEC-003: password_hash never leaves the server ----------
def test_password_hash_not_in_any_user_response():
    email = f"iter77-pw-{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPassw0rd!!", "name": "PW",
                                                    "tos_accepted": True, "tos_version": "2026-06.1"}, timeout=15)
    assert r.status_code == 201, r.text
    assert "password_hash" not in r.text
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPassw0rd!!"}, timeout=15)
    assert r.status_code == 200 and "password_hash" not in r.text
    tok = r.json()["session_token"]
    h = {"Authorization": f"Bearer {tok}"}
    for path in ("/auth/me",):
        r = requests.get(f"{BASE}{path}", headers=h, timeout=15)
        assert r.status_code == 200 and "password_hash" not in r.text, path
    r = requests.patch(f"{BASE}/me/prefs", headers=h, json={"language": "en"}, timeout=15)
    assert r.status_code == 200 and "password_hash" not in r.text


# ---------- SEC-001: dev-bypass only on preview/local hosts ----------
def test_dev_bypass_rejected_for_production_host():
    # The ingress overwrites Host/X-Forwarded-Host, so a spoof can only be simulated by
    # talking to uvicorn directly (inside the pod) with a production-looking Host header.
    try:
        r = requests.post("http://localhost:8001/api/auth/dev-bypass", json={"email": FOUNDER},
                          headers={"Host": "archangel.emergent.host"}, timeout=10)
    except requests.ConnectionError:
        import pytest
        pytest.skip("backend not reachable on localhost:8001 from this runner")
    assert r.status_code == 403, r.text
    r = requests.post("http://localhost:8001/api/auth/dev-bypass", json={"email": FOUNDER},
                      headers={"Host": "archangel.emergent.host", "X-Forwarded-Host": "x.preview.emergentagent.com"}, timeout=10)
    assert r.status_code == 403, r.text


def test_dev_bypass_works_on_preview_host():
    r = requests.post(f"{BASE}/auth/dev-bypass", json={"email": FOUNDER}, timeout=15)
    assert r.status_code == 200


# ---------- Rate limiting ----------
def test_login_rate_limited_per_ip():
    ip = f"203.0.113.{uuid.uuid4().int % 250 + 1}"
    codes = []
    for _ in range(25):
        r = requests.post(f"{BASE}/auth/login", json={"email": f"nobody-{uuid.uuid4().hex[:6]}@x.io", "password": "wrongpass"},
                          headers={"X-Forwarded-For": ip}, timeout=15)
        codes.append(r.status_code)
    assert codes[0] == 401 and 429 in codes, codes
    first429 = codes.index(429)
    assert first429 >= 15, codes            # generous for real users
    r = requests.post(f"{BASE}/auth/login", json={"email": "x@x.io", "password": "wrongpass"}, headers={"X-Forwarded-For": ip}, timeout=15)
    assert r.status_code == 429 and r.headers.get("Retry-After")


def test_tts_rate_limited_per_ip():
    f = _bypass(FOUNDER)
    ip = f"198.51.100.{uuid.uuid4().int % 250 + 1}"
    codes = [requests.post(f"{BASE}/voice/tts", headers={**_h(f), "X-Forwarded-For": ip}, json={"text": "hi"}, timeout=30).status_code
             for _ in range(35)]
    assert 429 in codes and codes.index(429) >= 25, codes


# ---------- Atomic GA-T ----------
def test_concurrent_spends_never_go_negative():
    u = _fresh("atomic")
    _set_balance(u, 12.0)   # jarvis_query = 0.5 GA-T → at most 24 of 40 concurrent spends may succeed
    with ThreadPoolExecutor(max_workers=40) as ex:
        codes = list(ex.map(lambda _: requests.post(f"{BASE}/token/spend", headers=_h(u), json={"item": "jarvis_query"}, timeout=30).status_code, range(40)))
    assert codes.count(200) == 24 and codes.count(402) == 16, codes
    bal = requests.get(f"{BASE}/token/wallet", headers=_h(u), timeout=15).json()["balance"]
    assert bal >= 0 and abs(bal) < 1e-6, bal


def test_concurrent_feature_buys_single_success():
    u = _fresh("featbuy")
    _set_balance(u, 25.0)   # bunker = 20 GA-T
    with ThreadPoolExecutor(max_workers=10) as ex:
        rs = list(ex.map(lambda _: requests.post(f"{BASE}/features/buy", headers=_h(u), json={"feature": "bunker", "currency": "gat"}, timeout=30), range(10)))
    bought = [r for r in rs if r.status_code == 200 and not r.json().get("already_owned")]
    assert len(bought) == 1, [(r.status_code, r.text[:60]) for r in rs]          # exactly ONE debit
    assert all(r.status_code in (200, 402) for r in rs)
    assert requests.get(f"{BASE}/token/wallet", headers=_h(u), timeout=15).json()["balance"] == 5.0


def test_feature_eur_path_blocked():
    u = _fresh("eur")
    r = requests.post(f"{BASE}/features/buy", headers=_h(u), json={"feature": "ghost_mode", "currency": "eur"}, timeout=15)
    assert r.status_code == 400


def test_addon_requires_gat_and_unlocks():
    u = _fresh("addon")
    r = requests.post(f"{BASE}/store/addon/buy", headers=_h(u), json={"addon_id": "ghost_mode"}, timeout=15)
    assert r.status_code == 402, r.text
    _set_balance(u, 30.0)   # ghost_mode €2.99 → 30 GA-T
    r = requests.post(f"{BASE}/store/addon/buy", headers=_h(u), json={"addon_id": "ghost_mode"}, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json()["balance"] == 0.0 and r.json()["purchase"]["currency"] == "gat"
    cat = requests.get(f"{BASE}/store/catalog", headers=_h(u), timeout=15).json()
    ghost = next(a for a in cat["addons"] if a["id"] == "ghost_mode")
    assert ghost["owned"] is True and ghost["price_gat"] == 30.0


def test_transfer_insufficient_is_402_and_atomic():
    u = _fresh("xfer")
    _set_balance(u, 5.0)
    with ThreadPoolExecutor(max_workers=10) as ex:
        codes = list(ex.map(lambda _: requests.post(f"{BASE}/store/transfer", headers=_h(u), json={"to_email": FOUNDER, "amount": 3}, timeout=30).status_code, range(10)))
    assert codes.count(200) == 1 and codes.count(402) == 9, codes


# ---------- iap-sync hardening ----------
def test_iap_sync_rejects_unknown_product_or_missing_identity():
    u = _fresh("iap")
    r = requests.post(f"{BASE}/subscription/iap-sync", headers=_h(u), json={"entitlement": "pro", "active": True, "product_identifier": "hack.archangel",
                                                                            "app_user_id": u["user_id"], "store": "TEST_STORE"}, timeout=15)
    assert r.status_code == 422
    r = requests.post(f"{BASE}/subscription/iap-sync", headers=_h(u), json={"entitlement": "pro", "active": True, "product_identifier": "pro.archangel_monthly"}, timeout=15)
    assert r.status_code == 422
    r = requests.post(f"{BASE}/subscription/iap-sync", headers=_h(u), json={"entitlement": "pro", "active": True, "product_identifier": "pro.archangel_monthly",
                                                                            "app_user_id": "someone-else", "store": "TEST_STORE"}, timeout=15)
    assert r.status_code == 409
    me = requests.get(f"{BASE}/auth/me", headers=_h(u), timeout=15).json()["user"]
    assert me.get("tier", "sovereign") == "sovereign"
