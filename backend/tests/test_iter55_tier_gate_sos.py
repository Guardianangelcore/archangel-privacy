"""Iter 55 regression suite:

  (A) Language i18n backend — /api/companion/greeting?language=sk|en|de
  (B) Tier gate — free-tier sovereign user gets 402 on jarvis endpoints;
      founder (archangel) gets 200 on /agent/briefing and 503 (budget) on chat.
  (C) SOS broadcast — POST /api/sos/broadcast writes an sos_events doc and
      returns contacts + maps_url shape.
"""
import os
import io
import uuid
import requests
import pytest

BASE = (os.environ.get("EXPO_BACKEND_URL")
        or os.environ.get("EXPO_PUBLIC_BACKEND_URL")
        or "https://physio-lang-fix.preview.emergentagent.com").rstrip("/")


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def founder_token():
    r = requests.post(f"{BASE}/api/auth/dev-bypass",
                      json={"email": "guardian.angel.core@proton.me",
                            "name": "Guardian Angel"}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["session_token"]


@pytest.fixture(scope="module")
def free_token():
    r = requests.post(f"{BASE}/api/auth/dev-bypass",
                      json={"email": "free-tier-test@example.com",
                            "name": "Free Tier Test"}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["session_token"]


# ------------- (A) i18n greeting -------------
class TestGreetingI18n:
    def test_sk(self, founder_token):
        r = requests.get(f"{BASE}/api/companion/greeting?language=sk",
                         headers=H(founder_token), timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        q = body.get("question", "")
        assert "Dobr" in q, f"expected Slovak greeting: {q!r}"

    def test_en(self, founder_token):
        r = requests.get(f"{BASE}/api/companion/greeting?language=en",
                         headers=H(founder_token), timeout=15)
        assert r.status_code == 200, r.text
        q = r.json().get("question", "")
        assert "Good" in q, f"expected English greeting: {q!r}"

    def test_de(self, founder_token):
        r = requests.get(f"{BASE}/api/companion/greeting?language=de",
                         headers=H(founder_token), timeout=15)
        assert r.status_code == 200, r.text
        q = r.json().get("question", "")
        assert "Guten" in q, f"expected German greeting: {q!r}"


# ------------- (B) Tier gate -------------
class TestTierGate:
    def test_free_subscription_tier(self, free_token):
        r = requests.get(f"{BASE}/api/subscription", headers=H(free_token), timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("tier") == "sovereign", body
        # verify guardian price
        tiers = body.get("tiers") or {}
        assert tiers.get("guardian", {}).get("price_eur") == 29, tiers

    def test_free_chat_402_guardian_required(self, free_token):
        r = requests.post(f"{BASE}/api/agent/chat",
                          headers={**H(free_token), "Content-Type": "application/json"},
                          json={"message": "hi", "language": "en"}, timeout=30)
        assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text[:300]}"
        detail = r.json().get("detail", "")
        assert detail.startswith("guardian_required:"), detail
        assert "Guardian Plan" in detail, detail

    def test_free_briefing_402(self, free_token):
        r = requests.get(f"{BASE}/api/agent/briefing", headers=H(free_token), timeout=30)
        assert r.status_code == 402, r.text
        detail = r.json().get("detail", "")
        assert detail.startswith("guardian_required:"), detail
        assert "Guardian Plan" in detail, detail

    def test_free_chat_stream_402(self, free_token):
        r = requests.post(f"{BASE}/api/agent/chat/stream",
                          headers={**H(free_token), "Content-Type": "application/json"},
                          json={"message": "hi", "language": "en"}, timeout=30)
        assert r.status_code == 402, f"got {r.status_code} body={r.text[:200]}"

    def test_free_transcribe_402(self, free_token):
        files = {"file": ("fake.webm", b"\x1a\x45\xdf\xa3" + b"\x00" * 64, "audio/webm")}
        r = requests.post(f"{BASE}/api/agent/transcribe",
                          headers=H(free_token), files=files, timeout=30)
        assert r.status_code == 402, f"got {r.status_code} body={r.text[:200]}"

    def test_founder_subscription_archangel(self, founder_token):
        r = requests.get(f"{BASE}/api/subscription", headers=H(founder_token), timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("tier") == "archangel", body
        assert body.get("tiers", {}).get("guardian", {}).get("price_eur") == 29

    def test_founder_briefing_200_not_402(self, founder_token):
        r = requests.get(f"{BASE}/api/agent/briefing", headers=H(founder_token), timeout=60)
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text[:300]}"

    def test_founder_chat_503_not_402(self, founder_token):
        # LLM budget exhausted → 503 expected. Must NOT be 402.
        r = requests.post(f"{BASE}/api/agent/chat",
                          headers={**H(founder_token), "Content-Type": "application/json"},
                          json={"message": "hi", "language": "en"}, timeout=60)
        assert r.status_code != 402, f"founder must not be gated: {r.text[:300]}"
        assert r.status_code == 503, f"expected 503 (budget), got {r.status_code}: {r.text[:200]}"


# ------------- (C) SOS broadcast -------------
class TestSosBroadcast:
    def test_broadcast_with_coords(self, founder_token):
        r = requests.post(f"{BASE}/api/sos/broadcast",
                          headers={**H(founder_token), "Content-Type": "application/json"},
                          json={"lat": 48.15, "lng": 17.11, "source": "hold"}, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True, body
        assert body.get("maps_url") == "https://maps.google.com/?q=48.15,17.11", body
        sms_body = body.get("sms_body") or ""
        assert "https://maps.google.com/?q=48.15,17.11" in sms_body, sms_body
        contacts = body.get("contacts") or []
        assert len(contacts) >= 1, body
        for c in contacts:
            assert "name" in c
            assert "phone" in c
            assert c.get("sms_sent") is False
            assert c.get("channel") == "device"
        assert body.get("sms_sent") == 0, body
        assert isinstance(body.get("push_sent"), int), body

    def test_broadcast_without_coords(self, founder_token):
        r = requests.post(f"{BASE}/api/sos/broadcast",
                          headers={**H(founder_token), "Content-Type": "application/json"},
                          json={"source": "fall_verify"}, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        assert body.get("maps_url") is None, body

    def test_family_contacts_still_present(self, founder_token):
        r = requests.get(f"{BASE}/api/family-contacts", headers=H(founder_token), timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        # response may be either {contacts:[...]} or a list; accept both
        contacts = body if isinstance(body, list) else body.get("contacts") or body.get("items") or []
        assert len(contacts) >= 1, body
