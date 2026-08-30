# Phase 49.1 — GALÉRIA OBRAZOV + HLASOVÝ SONAR + TTS regression
# Tests:
#  1) POST /api/agent/imagine → 200 with image_base64 + saved_to_vault:true + doc_id
#  2) GET /api/vault/documents → new art doc present (source:'jarvis_art', image/png)
#  3) GET /api/vault/documents/{doc_id}/file → 200 image/png bytes
#  4) DELETE /api/vault/documents/{doc_id} → 200 (cleanup only the doc we created)
#  5) Regression: /api/agent/search degraded:true; /api/agent/chat 200;
#     /api/voice/tts with markdown 200 with url
import os
import base64
import pytest
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL") or "https://guardian-vault-13.preview.emergentagent.com"
BASE_URL = BASE_URL.rstrip("/")
FOUNDER_EMAIL = "guardian.angel.core@proton.me"
PROTECTED_ART_DOC = "f1b50e9e705042fe92005b801de2cfc7"


@pytest.fixture(scope="module")
def founder_token():
    r = requests.post(f"{BASE_URL}/api/auth/dev-bypass",
                      json={"email": FOUNDER_EMAIL, "name": "Guardian Angel"},
                      timeout=15)
    assert r.status_code == 200, f"dev-bypass failed: {r.status_code} {r.text}"
    tok = r.json().get("session_token")
    assert tok, f"no session_token in response: {r.json()}"
    return tok


@pytest.fixture(scope="module")
def auth_headers(founder_token):
    return {"Authorization": f"Bearer {founder_token}", "Content-Type": "application/json"}


# ---- CORE FEATURE: imagine → vault ----

class TestImagineToVault:
    """POST /api/agent/imagine persists PNG to Vault; assert full round-trip."""
    created_doc_id = None

    def test_imagine_generates_and_persists(self, auth_headers):
        # Use a very safe/innocent prompt to avoid safety-rejection
        r = requests.post(
            f"{BASE_URL}/api/agent/imagine",
            headers=auth_headers,
            json={"prompt": "small golden angel wing icon"},
            timeout=180,
        )
        assert r.status_code == 200, f"imagine failed: {r.status_code} {r.text[:400]}"
        data = r.json()
        assert "image_base64" in data and data["image_base64"], "missing image_base64"
        assert data.get("saved_to_vault") is True, f"saved_to_vault not true: {data}"
        assert data.get("doc_id"), "missing doc_id"
        # Validate PNG magic bytes
        raw = base64.b64decode(data["image_base64"])
        assert raw[:8] == b"\x89PNG\r\n\x1a\n", "not a valid PNG"
        assert len(raw) > 5000, f"suspiciously small PNG: {len(raw)}"
        TestImagineToVault.created_doc_id = data["doc_id"]

    def test_vault_documents_contains_new_art(self, auth_headers):
        assert TestImagineToVault.created_doc_id, "prior test must create doc_id"
        r = requests.get(f"{BASE_URL}/api/vault/documents", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        docs = r.json()
        assert isinstance(docs, list)
        match = [d for d in docs if d.get("doc_id") == TestImagineToVault.created_doc_id]
        assert match, f"newly created art doc not in vault list (looking for {TestImagineToVault.created_doc_id})"
        d = match[0]
        assert d.get("source") == "jarvis_art", f"unexpected source: {d.get('source')}"
        assert d.get("content_type") == "image/png", f"unexpected content_type: {d.get('content_type')}"

    def test_vault_file_returns_png_bytes(self, auth_headers):
        assert TestImagineToVault.created_doc_id
        r = requests.get(
            f"{BASE_URL}/api/vault/documents/{TestImagineToVault.created_doc_id}/file",
            headers={"Authorization": auth_headers["Authorization"]},
            timeout=20,
        )
        assert r.status_code == 200, f"file fetch failed: {r.status_code}"
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n", "response is not PNG bytes"

    def test_cleanup_only_our_doc(self, auth_headers):
        # NEVER delete the protected pre-existing gallery doc.
        assert TestImagineToVault.created_doc_id != PROTECTED_ART_DOC
        assert TestImagineToVault.created_doc_id
        r = requests.delete(
            f"{BASE_URL}/api/vault/documents/{TestImagineToVault.created_doc_id}",
            headers=auth_headers,
            timeout=15,
        )
        assert r.status_code == 200, f"delete failed: {r.status_code} {r.text}"
        # Verify protected art doc still exists
        r2 = requests.get(f"{BASE_URL}/api/vault/documents", headers=auth_headers, timeout=15)
        assert r2.status_code == 200
        ids = {d.get("doc_id") for d in r2.json()}
        assert PROTECTED_ART_DOC in ids, "protected pre-existing art doc missing after cleanup"
        assert TestImagineToVault.created_doc_id not in ids, "deleted doc still present"


# ---- REGRESSION ----

class TestRegression:
    def test_agent_search_degraded(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/agent/search",
                          headers=auth_headers, json={"query": "test"}, timeout=60)
        assert r.status_code == 200, r.text[:400]
        data = r.json()
        assert data.get("degraded") is True, f"expected degraded:true, got {data.get('degraded')}"
        assert data.get("reply"), "empty reply from sonar fallback"

    def test_agent_chat(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/agent/chat",
                          headers=auth_headers, json={"message": "Ahoj"}, timeout=60)
        assert r.status_code == 200, r.text[:400]
        assert r.json().get("reply"), "empty chat reply"

    def test_voice_tts_with_markdown(self, auth_headers):
        r = requests.post(
            f"{BASE_URL}/api/voice/tts",
            headers=auth_headers,
            json={"text": "**Ahoj** [link](https://x.com)", "voice": "onyx", "language": "sk"},
            timeout=60,
        )
        assert r.status_code == 200, r.text[:400]
        assert r.json().get("url"), "TTS response missing url"
