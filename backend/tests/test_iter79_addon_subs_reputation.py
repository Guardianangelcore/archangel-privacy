"""Iteration 79 — Recurring add-ons as RevenueCat subscriptions (server-side lifecycle) + helper reputation."""
import os, uuid, requests
from datetime import datetime, timezone, timedelta

BASE = os.environ.get("EXPO_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/") + "/api"
FOUNDER = "guardian.angel.core@proton.me"


def _bypass(email, name="T"):
    r = requests.post(f"{BASE}/auth/dev-bypass", json={"email": email, "name": name}, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json(); return {"token": d["session_token"], "user_id": d["user"]["user_id"], "email": email}


def _fresh(tag): return _bypass(f"iter79-{tag}-{uuid.uuid4().hex[:8]}@example.com", f"Iter79 {tag}")
def _h(u): return {"Authorization": f"Bearer {u['token']}"}
def _iso(days): return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat().replace("+00:00", "Z")


def _sync(u, subs, active=True, product=None):
    body = {"entitlement": "pro", "active": active, "product_identifier": product or (subs[0]["product_identifier"] if subs else None),
            "expires_date": subs[0].get("expires_date") if subs else None, "store": "TEST_STORE", "period_type": "NORMAL",
            "app_user_id": u["user_id"], "active_subscriptions": subs}
    return requests.post(f"{BASE}/subscription/iap-sync", headers=_h(u), json=body, timeout=15)


def test_catalog_recurring_addons_are_rc_subscriptions():
    u = _fresh("cat")
    cat = requests.get(f"{BASE}/store/catalog", headers=_h(u), timeout=15).json()
    rec = {a["id"]: a for a in cat["addons"] if a["kind"] == "recurring"}
    assert rec["perplexity_ultra"]["rc_package"] == "addon_perplexity_ultra_monthly" and rec["perplexity_ultra"]["price_gat"] is None
    assert rec["premium_voice"]["rc_package"] == "addon_premium_voice_monthly" and rec["premium_voice"]["status"] == "none"
    one = next(a for a in cat["addons"] if a["id"] == "ghost_mode")
    assert one["price_gat"] == 30.0 and one["rc_package"] is None
    r = requests.post(f"{BASE}/store/addon/buy", headers=_h(u), json={"addon_id": "premium_voice"}, timeout=15)
    assert r.status_code == 400 and "subscription_only" in r.text


def test_addon_subscription_lifecycle_activate_renew_expire():
    u = _fresh("life")
    voice = "pro.addon_premium_voice_monthly"
    # 1) activate (add-on only → NO tier granted)
    r = _sync(u, [{"product_identifier": voice, "expires_date": _iso(30), "will_renew": True}])
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["tier"] == "sovereign" and d["addons"]["premium_voice"]["active"] is True and d["addons"]["premium_voice"]["status"] == "active"
    st = requests.get(f"{BASE}/store/addons/status", headers=_h(u), timeout=15).json()["addons"]
    assert st["premium_voice"]["active"] is True and st["perplexity_ultra"]["active"] is False
    me = requests.get(f"{BASE}/auth/me", headers=_h(u), timeout=15).json()["user"]
    assert me.get("tier", "sovereign") == "sovereign"
    # 2) renewal → new expiry recorded
    r = _sync(u, [{"product_identifier": voice, "expires_date": _iso(60), "will_renew": True}])
    st = requests.get(f"{BASE}/store/addons/status", headers=_h(u), timeout=15).json()["addons"]
    assert st["premium_voice"]["until"].startswith(_iso(60)[:10])
    # 3) lapsed (not in active list any more) → expired server-side
    r = _sync(u, [], active=False, product=voice)
    assert r.status_code == 200
    st = requests.get(f"{BASE}/store/addons/status", headers=_h(u), timeout=15).json()["addons"]
    assert st["premium_voice"]["active"] is False and st["premium_voice"]["status"] == "expired"
    cat = requests.get(f"{BASE}/store/catalog", headers=_h(u), timeout=15).json()
    assert next(a for a in cat["addons"] if a["id"] == "premium_voice")["owned"] is False


def test_tier_and_addon_coexist_in_one_entitlement():
    u = _fresh("both")
    subs = [{"product_identifier": "pro.addon_perplexity_ultra_monthly", "expires_date": _iso(30), "will_renew": True},
            {"product_identifier": "pro.guardian_monthly", "expires_date": _iso(30), "will_renew": True}]
    # entitlement's productIdentifier happens to be the ADD-ON (RC aggregation) — tier must still come from guardian
    r = _sync(u, subs, product="pro.addon_perplexity_ultra_monthly")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["tier"] == "guardian" and d["addons"]["perplexity_ultra"]["active"] is True
    me = requests.get(f"{BASE}/auth/me", headers=_h(u), timeout=15).json()["user"]
    assert me["tier"] == "guardian" and me["tier_paid_with"] == "iap"
    # legacy single-product payload about the add-on must NOT touch the tier
    r = requests.post(f"{BASE}/subscription/iap-sync", headers=_h(u), json={"entitlement": "pro", "active": True, "product_identifier": "pro.addon_perplexity_ultra_monthly",
                                                                            "expires_date": _iso(30), "store": "TEST_STORE", "app_user_id": u["user_id"]}, timeout=15)
    assert r.status_code == 200 and r.json()["status"] == "addons_synced" and r.json()["tier"] == "guardian"
    # guardian lapses, add-on stays → tier downgraded, add-on active
    r = _sync(u, [subs[0]], product="pro.addon_perplexity_ultra_monthly")
    assert r.json()["tier"] == "sovereign" and r.json()["addons"]["perplexity_ultra"]["active"] is True


def test_expired_date_in_payload_is_ignored():
    u = _fresh("exp")
    r = _sync(u, [{"product_identifier": "pro.addon_premium_voice_monthly", "expires_date": _iso(-1)}], product="pro.addon_premium_voice_monthly")
    assert r.status_code == 200
    st = requests.get(f"{BASE}/store/addons/status", headers=_h(u), timeout=15).json()["addons"]
    assert st["premium_voice"]["active"] is False


# ---------- Helper reputation ----------
def _fund(u, amount):
    """Deterministic wallet funding straight in Mongo (test-only; the founder wallet may be drained by other suites)."""
    from pymongo import MongoClient
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    db.token_accounts.update_one({"user_id": u["user_id"]}, {"$inc": {"balance": float(amount)}, "$setOnInsert": {"earned_total": 0.0, "spent_total": 0.0}}, upsert=True)


def test_helper_reputation_counts_only_confirmed():
    helper = _fresh("rep")
    rep = requests.get(f"{BASE}/help/reputation/{helper['user_id']}", headers=_h(helper), timeout=15).json()
    assert rep["completed"] == 0 and rep["badge"] is None and rep["next_badge"] == {"badge": "bronze", "need": 1}
    grans = [_fresh(f"g{i}") for i in range(2)]
    ids = []
    for g in grans:
        _fund(g, 10)
        req = requests.post(f"{BASE}/help/requests", headers=_h(g), json={"title": "Carry water", "category": "household"}, timeout=15).json()["request"]
        requests.post(f"{BASE}/help/requests/{req['req_id']}/accept", headers=_h(helper), timeout=15)
        requests.post(f"{BASE}/help/requests/{req['req_id']}/done", headers=_h(helper), timeout=15)
        ids.append((g, req["req_id"]))
    # done but unconfirmed → still 0
    assert requests.get(f"{BASE}/help/reputation/{helper['user_id']}", headers=_h(helper), timeout=15).json()["completed"] == 0
    g, rid = ids[0]
    r = requests.post(f"{BASE}/help/requests/{rid}/confirm", headers=_h(g), timeout=15)
    assert r.status_code == 200
    assert r.json()["request"]["helper_reputation"]["completed"] == 1 and r.json()["request"]["helper_reputation"]["badge"] == "bronze"
    lst = requests.get(f"{BASE}/help/requests?scope=mine", headers=_h(ids[1][0]), timeout=15).json()
    card = next(x for x in lst["requests"] if x["req_id"] == ids[1][1])
    assert card["helper_reputation"] == {"completed": 1, "badge": "bronze", "earned_gat": 10.0, "last_at": card["helper_reputation"]["last_at"],
                                         "next_badge": {"badge": "silver", "need": 4}}
    mine = requests.get(f"{BASE}/help/requests?scope=helping", headers=_h(helper), timeout=15).json()
    assert mine["my_reputation"]["completed"] == 1 and mine["badges"] == {"gold": 20, "silver": 5, "bronze": 1}
