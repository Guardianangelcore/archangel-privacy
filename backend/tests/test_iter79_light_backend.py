"""Iteration 79 — Light backend regression:
- Device integrity report + security events
- POST /store/addon/buy premium_voice → 400 subscription_only
- POST /voice/tts remains 200 for a fresh user (Premium Voice gate falls back silently)
"""
import os, uuid, requests

BASE = os.environ.get("EXPO_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/") + "/api"


def _fresh(tag: str):
    email = f"iter79light-{tag}-{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{BASE}/auth/dev-bypass", json={"email": email, "name": f"L79 {tag}"}, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    return {"token": d["session_token"], "user_id": d["user"]["user_id"], "email": email}


def _h(u): return {"Authorization": f"Bearer {u['token']}"}


# --- Device integrity (rooted device reporting) ---
def test_device_integrity_reports_rooted_and_shows_up_in_events():
    u = _fresh("dev")
    r = requests.post(f"{BASE}/security/device-integrity", headers=_h(u),
                      json={"rooted": True, "platform": "android", "model": "Test"}, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    di = body.get("device_integrity") or body
    assert di.get("rooted") is True, body
    ev = requests.get(f"{BASE}/security/events", headers=_h(u), timeout=15)
    assert ev.status_code == 200, ev.text
    payload = ev.json()
    events = payload if isinstance(payload, list) else payload.get("events", [])
    kinds = [e.get("kind") or e.get("type") or e.get("event") for e in events]
    assert "rooted_device" in kinds, kinds


# --- Add-on buy: recurring add-ons are subscription-only ---
def test_addon_buy_premium_voice_subscription_only():
    u = _fresh("addon")
    r = requests.post(f"{BASE}/store/addon/buy", headers=_h(u),
                      json={"addon_id": "premium_voice"}, timeout=15)
    assert r.status_code == 400, r.text
    assert "subscription_only" in r.text, r.text


# --- Voice TTS still works for fresh (no add-on) user ---
def test_voice_tts_falls_back_for_fresh_user():
    u = _fresh("tts")
    r = requests.post(f"{BASE}/voice/tts", headers=_h(u),
                      json={"text": "Hello guardian", "voice": "alloy"}, timeout=30)
    assert r.status_code == 200, r.text
