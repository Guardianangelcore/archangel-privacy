"""Iteration 88 — subscription gating rules (user addendum).
Bunker Mode + Mesh SMS: Sentinel+, subscription-only (no one-off), 90-day grace after expiry.
Bio-Digital Twin: Archangel only, 14-day grace. Sovereign always keeps SOS + basic Jarvis (daily free quota).
"""
import os, uuid
from datetime import datetime, timezone, timedelta
import pytest, requests
from dotenv import dotenv_values
from pymongo import MongoClient

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FE = dotenv_values(os.path.join(ROOT, "frontend", ".env")); BE = dotenv_values(os.path.join(ROOT, "backend", ".env"))
BASE = FE["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") + "/api"
users = MongoClient(BE["MONGO_URL"])[BE["DB_NAME"]]["users"]


def _user(tag, **fields):
    r = requests.post(f"{BASE}/auth/dev-bypass", json={"email": f"iter88-{tag}-{uuid.uuid4().hex[:6]}@example.com", "name": tag}, timeout=15)
    if r.status_code == 429:
        pytest.skip("dev-bypass rate limited")
    d = r.json(); uid = d["user"]["user_id"]
    if fields:
        users.update_one({"user_id": uid}, {"$set": fields})
    return uid, {"Authorization": f"Bearer {d['session_token']}"}


def _cat(h):
    return {f["id"]: f for f in requests.get(f"{BASE}/features/catalog", headers=h, timeout=15).json()["features"]}


def test_free_user_sees_locked_subscription_only_features():
    _, h = _user("free")
    c = _cat(h)
    for k in ("bunker", "mesh_sms", "twin"):
        assert c[k]["unlocked"] is False and c[k]["purchasable"] is False
    assert c["bunker"]["grace_days"] == 90 and c["twin"]["grace_days"] == 14
    assert requests.post(f"{BASE}/features/buy", headers=h, json={"feature": "bunker", "currency": "gat"}, timeout=15).status_code == 400
    assert requests.get(f"{BASE}/mesh/status", headers=h, timeout=15).status_code == 402
    assert requests.get(f"{BASE}/twin/trajectory", headers=h, timeout=15).status_code == 402


def test_sentinel_grace_90_days_then_locked():
    now = datetime.now(timezone.utc)
    _, h = _user("s10", tier="sentinel", tier_until=now - timedelta(days=10))
    c = _cat(h)
    assert c["bunker"]["unlocked"] and c["bunker"]["in_grace"] and c["mesh_sms"]["unlocked"] and not c["twin"]["unlocked"]
    assert requests.get(f"{BASE}/mesh/status", headers=h, timeout=15).status_code == 200
    _, h2 = _user("s100", tier="sentinel", tier_until=now - timedelta(days=100))
    c2 = _cat(h2)
    assert not c2["bunker"]["unlocked"] and not c2["mesh_sms"]["unlocked"]


def test_archangel_twin_grace_14_days():
    now = datetime.now(timezone.utc)
    _, h = _user("a10", tier="archangel", tier_until=now - timedelta(days=10))
    assert _cat(h)["twin"]["unlocked"] is True
    _, h2 = _user("a20", tier="archangel", tier_until=now - timedelta(days=20))
    c = _cat(h2)
    assert c["twin"]["unlocked"] is False and c["bunker"]["unlocked"] is True   # emergency core still in its 90-day grace


def test_sovereign_basic_jarvis_never_locked():
    _, h = _user("jarvis")
    r = requests.post(f"{BASE}/agent/chat", headers=h, json={"message": "Say hello in three words."}, timeout=90)
    assert r.status_code == 200, r.text
