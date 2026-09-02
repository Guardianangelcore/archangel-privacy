"""Iter 62 — three-tier IAP mapping via ONE RevenueCat entitlement ("pro") + price list.

Product identifier → tier: pro.guardian_* → guardian, pro.sentinel_* → sentinel,
pro.archangel_* → archangel (legacy pro.monthly → guardian). Store-paid tiers follow the store
(upgrade AND downgrade between IAP products); GA-T loyalty allocation follows the tier
(Guardian 100 · Sentinel 300 · Archangel 1000)."""
import os
import time
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _hdr(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _fresh_user():
    r = requests.post(f"{API}/auth/dev-bypass", json={"email": f"iap3-{int(time.time()*1000)}@example.com", "name": "Tier Tester"}, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    return d["session_token"], d["user"]["user_id"]


def _sync(token, uid, product, active=True, days=30, period_type="NORMAL"):
    exp = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat().replace("+00:00", "Z")
    body = {"entitlement": "pro", "active": active, "product_identifier": product, "expires_date": exp,
            "store": "TEST_STORE", "period_type": period_type, "app_user_id": uid, "will_renew": True}
    return requests.post(f"{API}/subscription/iap-sync", json=body, headers=_hdr(token), timeout=30)


def test_price_list_matches_store():
    tok, _ = _fresh_user()
    t = requests.get(f"{API}/subscription", headers=_hdr(tok), timeout=30).json()["tiers"]
    assert (t["sovereign"]["price_eur"], t["sovereign"]["price_eur_year"]) == (0, 0)
    assert (t["guardian"]["price_eur"], t["guardian"]["price_eur_year"]) == (9, 86)
    assert (t["sentinel"]["price_eur"], t["sentinel"]["price_eur_year"]) == (149, 1490)
    assert (t["archangel"]["price_eur"], t["archangel"]["price_eur_year"]) == (499, 4990)


def test_sentinel_product_maps_to_sentinel_and_300_gat():
    tok, uid = _fresh_user()
    r = _sync(tok, uid, "pro.sentinel_monthly")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "synced" and d["tier"] == "sentinel"
    assert sum(t["amount"] for t in d["gat_allocation"]["credited_txs"]) == 300
    sub = requests.get(f"{API}/subscription", headers=_hdr(tok), timeout=30).json()
    assert sub["tier"] == "sentinel" and sub["paid_with"] == "iap"


def test_archangel_product_maps_to_archangel():
    tok, uid = _fresh_user()
    d = _sync(tok, uid, "pro.archangel_annual", days=365).json()
    assert d["status"] == "synced" and d["tier"] == "archangel"
    assert sum(t["amount"] for t in d["gat_allocation"]["credited_txs"]) == 1000


def test_legacy_and_new_guardian_products_map_to_guardian():
    tok, uid = _fresh_user()
    assert _sync(tok, uid, "pro.monthly").json()["tier"] == "guardian"
    tok2, uid2 = _fresh_user()
    assert _sync(tok2, uid2, "pro.guardian_annual", days=365).json()["tier"] == "guardian"


def test_store_paid_tier_follows_store_up_and_down():
    tok, uid = _fresh_user()
    assert _sync(tok, uid, "pro.guardian_monthly").json()["tier"] == "guardian"
    up = _sync(tok, uid, "pro.archangel_monthly").json()
    assert up["status"] == "synced" and up["tier"] == "archangel"
    down = _sync(tok, uid, "pro.sentinel_monthly").json()          # store-side downgrade → mirrored
    assert down["status"] == "synced" and down["tier"] == "sentinel"
    lapse = _sync(tok, uid, "pro.sentinel_monthly", active=False).json()
    assert lapse["status"] == "downgraded" and lapse["tier"] == "sovereign"


def test_same_product_twice_is_unchanged():
    tok, uid = _fresh_user()
    _sync(tok, uid, "pro.sentinel_annual", days=365)
    d = _sync(tok, uid, "pro.sentinel_annual", days=365)
    # expires_date differs by milliseconds between calls → treat either as valid idempotency outcome
    assert d.status_code == 200 and d.json()["tier"] == "sentinel"
    w = requests.get(f"{API}/token/wallet", headers=_hdr(tok), timeout=30).json()
    assert float(w.get("balance", 0)) == 300.0     # no double credit
