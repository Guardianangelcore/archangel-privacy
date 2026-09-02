"""Iteration 63 — Tier gates (Sovereign paywall) + IAP unlocks + Perplexity sonar-reasoning-pro."""
import os, time, requests
from datetime import datetime, timezone, timedelta

BASE = os.environ.get("EXPO_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/") + "/api"


def _fresh_user(tag: str) -> dict:
    email = f"iter63-{tag}-{int(time.time()*1000)}@example.com"
    r = requests.post(f"{BASE}/auth/dev-bypass", json={"email": email, "name": f"Iter63 {tag}"}, timeout=15)
    assert r.status_code == 200, f"dev-bypass failed: {r.status_code} {r.text}"
    d = r.json()
    return {"token": d["session_token"], "user_id": d["user"]["user_id"], "email": email}


def _h(u): return {"Authorization": f"Bearer {u['token']}"}


# ---------- Sovereign gates ----------
def test_sovereign_gate_waitlist_get():
    u = _fresh_user("sov1")
    r = requests.get(f"{BASE}/waitlist", headers=_h(u), timeout=15)
    assert r.status_code == 402, f"expected 402 got {r.status_code}: {r.text[:200]}"
    assert "guardian" in r.text.lower()


def test_sovereign_gate_waitlist_post():
    u = _fresh_user("sov2")
    # Note: WaitlistIn requires clinic/current_date/target_before — if gate runs before body validation
    # this returns 402, otherwise 422. The task spec REQUIRES 402.
    r = requests.post(f"{BASE}/waitlist", headers=_h(u), json={"specialty": "Cardiology", "city": "Bratislava"}, timeout=15)
    assert r.status_code == 402, f"expected 402 got {r.status_code}: {r.text[:200]}"


def test_sovereign_gate_lens_analyze():
    u = _fresh_user("sov3")
    # tiny 1x1 png bytes
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    r = requests.post(f"{BASE}/lens/analyze", headers=_h(u), files={"file": ("t.png", png, "image/png")}, timeout=15)
    assert r.status_code == 402, f"expected 402 got {r.status_code}: {r.text[:200]}"


def test_sovereign_gate_agent_search():
    u = _fresh_user("sov4")
    r = requests.post(f"{BASE}/agent/search", headers=_h(u), json={"query": "flu vaccination 2026"}, timeout=15)
    assert r.status_code == 402, f"expected 402 got {r.status_code}: {r.text[:200]}"


def test_sovereign_gate_agent_chat():
    u = _fresh_user("sov5")
    r = requests.post(f"{BASE}/agent/chat", headers=_h(u), json={"message": "hi"}, timeout=15)
    assert r.status_code == 402, f"expected 402 got {r.status_code}: {r.text[:200]}"


# ---------- IAP unlocks per tier ----------
def _iap_sync(u, product):
    expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat().replace("+00:00", "Z")
    body = {
        "entitlement": "pro", "active": True, "product_identifier": product,
        "expires_date": expires, "store": "TEST_STORE", "period_type": "NORMAL",
        "app_user_id": u["user_id"], "will_renew": True,
    }
    return requests.post(f"{BASE}/subscription/iap-sync", headers=_h(u), json=body, timeout=20)


def test_iap_guardian_unlocks_waitlist():
    u = _fresh_user("g")
    r = _iap_sync(u, "pro.guardian_monthly")
    assert r.status_code == 200, r.text[:300]
    assert r.json().get("tier") == "guardian"
    # check subscription info
    s = requests.get(f"{BASE}/subscription", headers=_h(u), timeout=15).json()
    assert s.get("tier") == "guardian", s
    assert s.get("paid_with") == "iap", s
    # waitlist opens
    lg = requests.get(f"{BASE}/waitlist", headers=_h(u), timeout=15)
    assert lg.status_code == 200, f"waitlist GET after guardian: {lg.status_code} {lg.text[:200]}"
    # POST waitlist with full body
    body = {"specialty": "Cardiology", "clinic": "Nemocnica Bory", "city": "Bratislava",
            "current_date": "2027-05-01", "target_before": "2026-03-01", "priority": "normal"}
    pw = requests.post(f"{BASE}/waitlist", headers=_h(u), json=body, timeout=15)
    assert pw.status_code in (200, 201), f"waitlist POST: {pw.status_code} {pw.text[:200]}"


def test_iap_sentinel_unlocks_and_sonar():
    u = _fresh_user("s")
    r = _iap_sync(u, "pro.sentinel_monthly")
    assert r.status_code == 200 and r.json().get("tier") == "sentinel"
    # agent/search — this exercises sonar-reasoning-pro (max_tokens=6000 fix)
    sr = requests.post(f"{BASE}/agent/search", headers=_h(u),
                       json={"query": "ECDC influenza vaccination recommendations 2026"}, timeout=90)
    assert sr.status_code == 200, f"agent/search: {sr.status_code} {sr.text[:300]}"
    j = sr.json()
    assert j.get("reply"), f"empty reply: {j}"
    # if degraded=true, backend log should show perplexity http error; not strictly checked here
    if not j.get("degraded"):
        assert j.get("live_search") is True, j
        assert len(j.get("citations") or []) >= 1, f"no citations: {j}"
    # agent/chat also not 402 (200 or 503 if LLM budget)
    ac = requests.post(f"{BASE}/agent/chat", headers=_h(u), json={"message": "hi"}, timeout=60)
    assert ac.status_code != 402, f"chat still gated: {ac.status_code} {ac.text[:200]}"


def test_iap_archangel_unlocks():
    u = _fresh_user("a")
    r = _iap_sync(u, "pro.archangel_annual")
    assert r.status_code == 200, r.text[:300]
    assert r.json().get("tier") == "archangel"
    s = requests.get(f"{BASE}/subscription", headers=_h(u), timeout=15).json()
    assert s.get("tier") == "archangel"
    ml = requests.get(f"{BASE}/waitlist", headers=_h(u), timeout=15)
    assert ml.status_code == 200
