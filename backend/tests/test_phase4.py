# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Phase 4 backend tests — Guardian Angel: Killer features batch 2.

Covers:
- AI Advice (Jarvis) — POST /api/ai/advice
- Medicine Cabinet CRUD — /api/cabinet/items + expiry status
- Medicine Exchange P2P — POST /api/cabinet/exchange, respond (403/400 own listing), delete
- Healthcare Proxy — GET/PUT /api/proxy-directive (doc_text + sha256, template)
- Emergency QR surfaces healthcare_proxy
- Marketplace — CRUD + book + bookings visible to both sides
- Scam Shield — /api/scam/check (LLM) + /api/scam/history
- Survival Auditor — items + runway (family_size aware, min(water,food))
- Barter — /barter/me initial 10 credits, offer + accept transfer, own-offer 400, insufficient 402
- Beacon — trigger + history
- Respect Map extended metrics — minority_safety, waiting_weeks, financial_transparency running avg
- family_size persistence in /api/me/prefs
"""
import os
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

BASE_URL = (os.environ.get("EXPO_PUBLIC_BACKEND_URL") or "https://global-compass-hub.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


def _mk_ids(tag):
    return {
        "session_token": f"TEST_p4_{tag}_{uuid.uuid4().hex}",
        "user_id": f"TEST_p4_{tag}_{uuid.uuid4().hex[:10]}",
        "did": f"did:guardian:TESTP4{tag}{uuid.uuid4().hex[:16]}",
        "email": f"TEST_p4_{tag}_{uuid.uuid4().hex[:6]}@example.com",
    }

USER_A = _mk_ids("A")
USER_B = _mk_ids("B")


async def _seed_user(db, u, name):
    await db.users.insert_one({
        "user_id": u["user_id"], "email": u["email"], "did": u["did"],
        "name": name, "language": "sk", "angel_mode": False,
        "created_at": datetime.now(timezone.utc),
    })
    await db.user_sessions.insert_one({
        "session_token": u["session_token"], "user_id": u["user_id"],
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
    })


async def _cleanup(db, u):
    uid = u["user_id"]
    await db.users.delete_one({"user_id": uid})
    await db.user_sessions.delete_one({"session_token": u["session_token"]})
    await db.cabinet_items.delete_many({"user_id": uid})
    await db.cabinet_exchange.delete_many({"user_id": uid})
    await db.proxy_directives.delete_many({"user_id": uid})
    await db.market_services.delete_many({"user_id": uid})
    await db.market_bookings.delete_many({"$or": [{"provider_user_id": uid}, {"client_user_id": uid}]})
    await db.scam_checks.delete_many({"user_id": uid})
    await db.survival_items.delete_many({"user_id": uid})
    await db.barter_offers.delete_many({"user_id": uid})
    await db.barter_trades.delete_many({"$or": [{"provider_user_id": uid}, {"client_user_id": uid}]})
    await db.beacon_events.delete_many({"user_id": uid})
    await db.emergency_profiles.delete_many({"user_id": uid})


@pytest.fixture(scope="module")
def seed():
    async def _seed():
        c = AsyncIOMotorClient(MONGO_URL)
        db = c[DB_NAME]
        await _seed_user(db, USER_A, "TEST Alice")
        await _seed_user(db, USER_B, "TEST Bob")
        c.close()

    async def _teardown():
        c = AsyncIOMotorClient(MONGO_URL)
        db = c[DB_NAME]
        await _cleanup(db, USER_A)
        await _cleanup(db, USER_B)
        # Cleanup providers created by A
        await db.providers.delete_many({"name": {"$regex": "^TEST_P4"}})
        await db.provider_reviews.delete_many({"user_id": USER_A["user_id"]})
        c.close()

    asyncio.get_event_loop().run_until_complete(_seed())
    yield {"A": USER_A, "B": USER_B}
    asyncio.get_event_loop().run_until_complete(_teardown())


@pytest.fixture
def auth_a(seed):
    return {"Authorization": f"Bearer {seed['A']['session_token']}"}

@pytest.fixture
def auth_b(seed):
    return {"Authorization": f"Bearer {seed['B']['session_token']}"}


# ------------------------ Prefs (family_size) ------------------------
def test_prefs_family_size_and_guards(auth_a):
    r = requests.patch(f"{BASE_URL}/api/me/prefs", headers=auth_a,
                       json={"fall_guard": True, "inactivity_guard": True, "inactivity_hours": 8, "family_size": 3})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["family_size"] == 3
    r2 = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_a)
    assert r2.json()["user"]["family_size"] == 3


# ------------------------ AI Advice (Jarvis) ------------------------
def test_ai_advice(auth_a):
    r = requests.post(f"{BASE_URL}/api/ai/advice", headers=auth_a,
                      json={"module": "survival_auditor",
                            "context": "Voda: 6l na 3 osoby, jedlo 5000 kcal.",
                            "language": "sk"}, timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "advice" in d and len(d["advice"]) > 10


# ------------------------ Medicine Cabinet ------------------------
def test_cabinet_crud_and_status(auth_a):
    past = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    soon = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%d")
    future = (datetime.now(timezone.utc) + timedelta(days=180)).strftime("%Y-%m-%d")

    r = requests.post(f"{BASE_URL}/api/cabinet/items", headers=auth_a,
                      json={"name": "TEST Paracetamol", "quantity": 20, "expires_on": past})
    assert r.status_code == 200
    assert r.json()["status"] == "expired"
    exp_id = r.json()["item_id"]

    r2 = requests.post(f"{BASE_URL}/api/cabinet/items", headers=auth_a,
                       json={"name": "TEST Ibuprofen", "quantity": 10, "expires_on": soon})
    assert r2.json()["status"] == "expiring_soon"

    r3 = requests.post(f"{BASE_URL}/api/cabinet/items", headers=auth_a,
                       json={"name": "TEST Vitamin", "quantity": 30, "expires_on": future})
    assert r3.json()["status"] == "ok"
    ok_id = r3.json()["item_id"]

    lst = requests.get(f"{BASE_URL}/api/cabinet/items", headers=auth_a).json()
    assert len(lst) >= 3

    # PATCH quantity
    rp = requests.patch(f"{BASE_URL}/api/cabinet/items/{ok_id}", headers=auth_a, json={"quantity": 25})
    assert rp.status_code == 200
    assert rp.json()["quantity"] == 25

    # DELETE
    rd = requests.delete(f"{BASE_URL}/api/cabinet/items/{exp_id}", headers=auth_a)
    assert rd.status_code == 200


def test_cabinet_exchange_p2p(auth_a, auth_b, seed):
    # A creates offer
    r = requests.post(f"{BASE_URL}/api/cabinet/exchange", headers=auth_a,
                      json={"type": "offer", "item_name": "TEST Bandage", "quantity": 5, "city": "Bratislava"})
    assert r.status_code == 200, r.text
    ex_id = r.json()["exchange_id"]

    # A cannot respond to own listing
    r_own = requests.post(f"{BASE_URL}/api/cabinet/exchange/{ex_id}/respond", headers=auth_a, json={"message": "mine"})
    assert r_own.status_code == 400

    # B responds successfully
    r_b = requests.post(f"{BASE_URL}/api/cabinet/exchange/{ex_id}/respond", headers=auth_b, json={"message": "beriem"})
    assert r_b.status_code == 200, r_b.text
    assert r_b.json()["matched"] is True

    # Already matched — B cannot respond again (status open filter)
    r_b2 = requests.post(f"{BASE_URL}/api/cabinet/exchange/{ex_id}/respond", headers=auth_b, json={"message": "x"})
    assert r_b2.status_code == 404

    # A can delete own listing
    rd = requests.delete(f"{BASE_URL}/api/cabinet/exchange/{ex_id}", headers=auth_a)
    assert rd.status_code == 200


# ------------------------ Healthcare Proxy ------------------------
def test_healthcare_proxy_and_qr(auth_a, seed):
    r = requests.put(f"{BASE_URL}/api/proxy-directive", headers=auth_a,
                     json={"proxy_full_name": "Tomáš Novák", "proxy_relationship": "partner",
                           "proxy_phone": "+421 900 111 222", "scope": "full", "language": "sk"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["proxy_full_name"] == "Tomáš Novák"
    assert "Tomáš Novák" in d["document_text"]
    assert "SPLNOMOCNENIE" in d["document_text"]
    assert len(d["doc_hash"]) == 64  # sha256 hex length

    # GET returns stored
    rg = requests.get(f"{BASE_URL}/api/proxy-directive", headers=auth_a)
    assert rg.status_code == 200
    assert rg.json()["proxy_full_name"] == "Tomáš Novák"

    # Public QR (no auth) includes healthcare_proxy
    rq = requests.get(f"{BASE_URL}/api/emergency-qr/{seed['A']['did']}")
    assert rq.status_code == 200, rq.text
    q = rq.json()
    assert q.get("healthcare_proxy"), f"missing healthcare_proxy: {q}"
    assert q["healthcare_proxy"]["name"] == "Tomáš Novák"
    assert q["healthcare_proxy"]["scope"] == "full"
    assert q["healthcare_proxy"]["doc_hash"] == d["doc_hash"]


# ------------------------ Marketplace ------------------------
def test_marketplace_flow(auth_a, auth_b):
    r = requests.post(f"{BASE_URL}/api/market/services", headers=auth_a,
                      json={"title": "TEST Masáž chrbta", "description": "60 min",
                            "category": "massage", "price": 25, "city": "Bratislava",
                            "payment_methods": ["cash", "crypto"]})
    assert r.status_code == 200, r.text
    svc_id = r.json()["service_id"]

    lst = requests.get(f"{BASE_URL}/api/market/services", headers=auth_a).json()
    assert any(s["service_id"] == svc_id for s in lst)

    # B books
    rb = requests.post(f"{BASE_URL}/api/market/services/{svc_id}/book", headers=auth_b,
                      json={"message": "Zajtra 15:00?", "payment_method": "cash"})
    assert rb.status_code == 200, rb.text
    booking_id = rb.json()["booking_id"]

    # Both sides see it
    a_bk = requests.get(f"{BASE_URL}/api/market/bookings", headers=auth_a).json()
    b_bk = requests.get(f"{BASE_URL}/api/market/bookings", headers=auth_b).json()
    assert any(x["booking_id"] == booking_id for x in a_bk)
    assert any(x["booking_id"] == booking_id for x in b_bk)

    # DELETE deactivates (soft)
    rd = requests.delete(f"{BASE_URL}/api/market/services/{svc_id}", headers=auth_a)
    assert rd.status_code == 200
    # No longer in active list
    lst2 = requests.get(f"{BASE_URL}/api/market/services", headers=auth_a).json()
    assert not any(s["service_id"] == svc_id for s in lst2)


# ------------------------ Scam Shield ------------------------
def test_scam_check_phishing(auth_a):
    phishing = "Vasa banka: klik sem a zadajte kod, ucet bude zablokovany bit.ly/xx"
    r = requests.post(f"{BASE_URL}/api/scam/check", headers=auth_a,
                      json={"text": phishing, "language": "sk"}, timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["risk"] in ("low", "medium", "high")
    # Obvious phishing should not be classified low
    assert d["risk"] in ("medium", "high"), f"unexpected risk for phishing: {d}"
    assert d["verdict"] and isinstance(d["verdict"], str)
    assert isinstance(d.get("reasons"), list)
    assert d.get("advice")

    hist = requests.get(f"{BASE_URL}/api/scam/history", headers=auth_a).json()
    assert any(x["check_id"] == d["check_id"] for x in hist)


# ------------------------ Survival Auditor ------------------------
def test_survival_runway(auth_a):
    # family_size=3 set earlier in test_prefs_family_size_and_guards
    # 12L water @ 3 L/day/person → 12 / (3*3) = 1.33 days
    r1 = requests.post(f"{BASE_URL}/api/survival/items", headers=auth_a,
                      json={"name": "TEST Voda", "category": "water", "quantity": 12, "unit": "l", "daily_need_per_person": 3})
    assert r1.status_code == 200
    # 30 units food @ 1/day/person → 30/3 = 10 days
    r2 = requests.post(f"{BASE_URL}/api/survival/items", headers=auth_a,
                      json={"name": "TEST Konzerva", "category": "food", "quantity": 30, "unit": "ks", "daily_need_per_person": 1})
    assert r2.status_code == 200

    rw = requests.get(f"{BASE_URL}/api/survival/runway", headers=auth_a)
    assert rw.status_code == 200, rw.text
    d = rw.json()
    assert d["family_size"] == 3
    assert "water" in d["category_runways"]
    assert "food" in d["category_runways"]
    # overall = min(water, food)
    expected = min(d["category_runways"]["water"], d["category_runways"]["food"])
    assert abs(d["overall_days"] - expected) < 0.5


# ------------------------ Barter ------------------------
def test_barter_flow(auth_a, auth_b):
    # A me → credits initialized to 10
    ra = requests.get(f"{BASE_URL}/api/barter/me", headers=auth_a).json()
    a_start = ra["credits"]
    # First-ever call for user B should also init to 10
    rb0 = requests.get(f"{BASE_URL}/api/barter/me", headers=auth_b).json()
    assert rb0["credits"] == 10, f"expected 10 initial, got {rb0['credits']}"

    # A creates offer worth 3 credits
    ro = requests.post(f"{BASE_URL}/api/barter/offers", headers=auth_a,
                      json={"offer_skill": "TEST Šitie", "want_in_return": "pomoc v záhrade",
                            "category": "craft", "city": "Bratislava", "credits_value": 3})
    assert ro.status_code == 200, ro.text
    offer_id = ro.json()["offer_id"]

    # A cannot accept own offer
    ra_own = requests.post(f"{BASE_URL}/api/barter/offers/{offer_id}/accept", headers=auth_a)
    assert ra_own.status_code == 400

    # B accepts → B credits 10-3=7, A credits a_start+3
    rb = requests.post(f"{BASE_URL}/api/barter/offers/{offer_id}/accept", headers=auth_b)
    assert rb.status_code == 200, rb.text
    trade = rb.json()
    assert trade["credits"] == 3

    ra2 = requests.get(f"{BASE_URL}/api/barter/me", headers=auth_a).json()
    rb2 = requests.get(f"{BASE_URL}/api/barter/me", headers=auth_b).json()
    assert ra2["credits"] == a_start + 3
    assert rb2["credits"] == 7

    # Insufficient credits → 402 (B tries to accept another expensive offer)
    ro2 = requests.post(f"{BASE_URL}/api/barter/offers", headers=auth_a,
                       json={"offer_skill": "TEST Poradenstvo", "category": "legal", "credits_value": 50})
    assert ro2.status_code == 200
    offer2_id = ro2.json()["offer_id"]
    rb_ins = requests.post(f"{BASE_URL}/api/barter/offers/{offer2_id}/accept", headers=auth_b)
    assert rb_ins.status_code == 402, f"expected 402 insufficient: {rb_ins.status_code} {rb_ins.text}"


# ------------------------ Beacon ------------------------
def test_beacon_trigger_and_history(auth_a):
    r = requests.post(f"{BASE_URL}/api/beacon/trigger", headers=auth_a,
                      json={"lat": 48.1, "lng": 17.1, "note": "TEST stealth"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["beacon_id"]
    assert d["lat"] == 48.1

    h = requests.get(f"{BASE_URL}/api/beacon/history", headers=auth_a).json()
    assert any(b["beacon_id"] == d["beacon_id"] for b in h)


# ------------------------ Respect Map extended metrics ------------------------
def test_respect_extended_metrics_aggregate(auth_a, auth_b):
    name = f"TEST_P4_Provider_{uuid.uuid4().hex[:6]}"
    city = "Bratislava"

    # 1st review from A
    r1 = requests.post(f"{BASE_URL}/api/respect/providers", headers=auth_a,
                       json={"name": name, "city": city, "specialty": "GP",
                             "respect_score": 4, "tags": ["priateľský"], "review": "OK",
                             "minority_safety": 5, "waiting_weeks": 8, "financial_transparency": 4})
    assert r1.status_code == 200, r1.text
    p1 = r1.json()
    assert p1["avg_minority_safety"] == 5.0
    assert p1["avg_waiting_weeks"] == 8.0
    assert p1["avg_financial_transparency"] == 4.0
    assert p1["minority_safety_count"] == 1

    # 2nd review from B → running average
    r2 = requests.post(f"{BASE_URL}/api/respect/providers", headers=auth_b,
                       json={"name": name, "city": city, "specialty": "GP",
                             "respect_score": 5, "tags": ["čistý"], "review": "veľmi dobrý",
                             "minority_safety": 3, "waiting_weeks": 4, "financial_transparency": 2})
    assert r2.status_code == 200, r2.text
    p2 = r2.json()
    assert p2["review_count"] == 2
    assert abs(p2["avg_minority_safety"] - 4.0) < 0.01, p2
    assert abs(p2["avg_waiting_weeks"] - 6.0) < 0.01, p2
    assert abs(p2["avg_financial_transparency"] - 3.0) < 0.01, p2
