"""
Iteration 57 — Rename verification: Guardian Health & Angel → Archangel OS
Public-facing rename only. Brand identity (Guardian Angel DAO/founder) preserved.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://physio-lang-fix.preview.emergentagent.com').rstrip('/')
FOUNDER_EMAIL = "guardian.angel.core@proton.me"

FORBIDDEN_USER_FACING = "Guardian Health & Angel"


@pytest.fixture(scope="module")
def founder_token():
    r = requests.post(f"{BASE_URL}/api/auth/dev-bypass",
                      json={"email": FOUNDER_EMAIL, "name": "Guardian Angel"},
                      timeout=15)
    assert r.status_code == 200, r.text
    tok = r.json().get("session_token")
    assert tok, r.text
    return tok


# Public root — app name renamed
class TestRootRename:
    def test_root_app_name_archangel_os(self):
        r = requests.get(f"{BASE_URL}/api/", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data.get("app") == "Archangel OS", f"expected 'Archangel OS', got {data.get('app')!r}"
        assert data.get("author") == "Guardian Angel Sovereign Foundation (DAO)"

    def test_root_has_no_old_name(self):
        r = requests.get(f"{BASE_URL}/api/", timeout=15)
        assert FORBIDDEN_USER_FACING not in r.text


# ToS — must reference ARCHANGEL OS, not the old name
class TestTosRename:
    @pytest.mark.parametrize("lang", ["en", "sk"])
    def test_tos_contains_archangel_os(self, founder_token, lang):
        r = requests.get(f"{BASE_URL}/api/legal/tos", params={"language": lang},
                         headers={"Authorization": f"Bearer {founder_token}"}, timeout=15)
        assert r.status_code == 200, r.text
        text = r.json().get("text", "")
        assert "ARCHANGEL OS" in text.upper(), f"[{lang}] ARCHANGEL OS missing from ToS"
        assert "GUARDIAN HEALTH & ANGEL" not in text.upper(), \
            f"[{lang}] old brand present in ToS"

    def test_privacy_no_old_name(self, founder_token):
        # Best-effort — if privacy endpoint exists, check it too
        r = requests.get(f"{BASE_URL}/api/legal/privacy", params={"language": "en"},
                         headers={"Authorization": f"Bearer {founder_token}"}, timeout=15)
        if r.status_code == 200:
            assert FORBIDDEN_USER_FACING not in r.text


# SOS broadcast — sms_body must end with (Archangel OS)
class TestSosRename:
    def test_sos_broadcast_sms_body_suffix(self, founder_token):
        r = requests.post(f"{BASE_URL}/api/sos/broadcast",
                          json={"source": "manual"},
                          headers={"Authorization": f"Bearer {founder_token}"},
                          timeout=15)
        assert r.status_code == 200, r.text
        body = r.json().get("sms_body", "")
        assert body.endswith("(Archangel OS)"), \
            f"sms_body should end with '(Archangel OS)', got: ...{body[-60:]!r}"
        assert FORBIDDEN_USER_FACING not in body


# Grep across a broad set of user-facing endpoints for the forbidden string
class TestNoOldNameLeaks:
    ENDPOINTS = [
        ("GET", "/api/"),
        ("GET", "/api/legal/tos?language=en"),
        ("GET", "/api/legal/tos?language=sk"),
        ("GET", "/api/legal/privacy?language=en"),
        ("GET", "/api/auth/me"),
        ("GET", "/api/subscription"),
        ("GET", "/api/token/wallet"),
    ]

    def test_no_old_name_leaks(self, founder_token):
        leaks = []
        headers = {"Authorization": f"Bearer {founder_token}"}
        for method, path in self.ENDPOINTS:
            try:
                r = requests.request(method, f"{BASE_URL}{path}",
                                     headers=headers, timeout=15)
                if FORBIDDEN_USER_FACING in r.text:
                    leaks.append(f"{method} {path} → contains {FORBIDDEN_USER_FACING!r}")
            except Exception as e:
                leaks.append(f"{method} {path} → error {e}")
        assert not leaks, "Forbidden old brand leaked: " + "; ".join(leaks)
