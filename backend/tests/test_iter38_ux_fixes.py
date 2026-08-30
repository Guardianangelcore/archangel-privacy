"""Iter 38 — 5 UX bug fixes verification.
- BUG2 streaming (SSE)
- BUG2 non-stream regression (JSON contract)
- BUG4 family contacts CRUD + SOS + encryption at rest
- Regression: /api/triage/state
"""
import os
import time
import json
import re
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://guardian-vault-13.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/dev-bypass",
                      json={"email": "guardian.angel.core@proton.me", "name": "Guardian Angel"},
                      timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["session_token"]


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ----- BUG2 STREAMING -----
class TestStreaming:
    def test_stream_produces_progressive_tokens(self, auth_headers):
        url = f"{BASE_URL}/api/agent/chat/stream"
        t0 = time.time()
        with requests.post(url, headers=auth_headers,
                           json={"message": "Ahoj, ako sa máš?"},
                           stream=True, timeout=60) as r:
            assert r.status_code == 200, r.text
            first_byte_ts = None
            chunks = []
            done_payload = None
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if first_byte_ts is None:
                    first_byte_ts = time.time() - t0
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    if payload.get("done"):
                        done_payload = payload
                        break
                    if "t" in payload:
                        chunks.append(payload["t"])
            assert first_byte_ts is not None and first_byte_ts < 15.0, f"TTFB too slow: {first_byte_ts}"
            assert len(chunks) >= 2, f"Not progressive; only {len(chunks)} chunk(s)"
            assert done_payload is not None, "Missing done payload"
            assert done_payload.get("mood") in ("calm", "thinking", "alert", "energetic", "concerned")
            assert isinstance(done_payload.get("xp_gained"), int)
            assert isinstance(done_payload.get("level"), int)
            full_reply = "".join(chunks)
            assert "AI Content" in full_reply or "Sovereign Protocol" in full_reply, \
                f"Missing watermark. Reply tail: {full_reply[-200:]}"

    def test_non_stream_contract_unchanged(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/agent/chat", headers=auth_headers,
                          json={"message": "Ahoj Jarvis"}, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("reply", "mood", "xp_gained", "level", "level_name", "alerts"):
            assert k in data, f"Missing key {k}"
        assert "AI Content" in data["reply"] or "Sovereign Protocol" in data["reply"]


# ----- BUG4 FAMILY CONTACTS -----
class TestFamilyContacts:
    created_id = None

    def test_list_contains_maria(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/family-contacts", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "contacts" in data and "total" in data
        found = [c for c in data["contacts"] if c["contact_id"] == "d36d87633c0b4b9c9f4fa9eda888d378"]
        assert found, "Existing Mária contact missing"
        maria = found[0]
        assert maria["name"].lower().startswith("mária") or "aria" in maria["name"].lower()
        # phone must be decrypted (not gAAAA...)
        assert not maria["phone"].startswith("gAAAA")
        assert "+421" in maria["phone"] or "421" in maria["phone"]

    def test_add_valid_contact(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/family-contacts", headers=auth_headers,
                          json={"name": "TEST_Brat", "phone": "+421911222333", "relation": "surodenec"},
                          timeout=15)
        assert r.status_code in (200, 201), r.text
        data = r.json()
        assert data["phone"] == "+421911222333"
        assert data["relation"] == "surodenec"
        assert data["relation_label"] == "Súrodenec"
        assert "contact_id" in data
        TestFamilyContacts.created_id = data["contact_id"]

    def test_invalid_phone(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/family-contacts", headers=auth_headers,
                          json={"name": "Bad", "phone": "abc", "relation": "surodenec"},
                          timeout=15)
        assert r.status_code == 400, r.text

    def test_invalid_relation_falls_back(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/family-contacts", headers=auth_headers,
                          json={"name": "TEST_Fallback", "phone": "+421900111000", "relation": "xxxinvalidxxx"},
                          timeout=15)
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["relation"] == "ine"
        # cleanup
        requests.delete(f"{BASE_URL}/api/family-contacts/{data['contact_id']}",
                        headers=auth_headers, timeout=15)

    def test_sos(self, auth_headers):
        assert TestFamilyContacts.created_id, "create test must run first"
        r = requests.post(f"{BASE_URL}/api/family-contacts/{TestFamilyContacts.created_id}/sos",
                          headers=auth_headers, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert "sms_body" in data and "SOS" in data["sms_body"].upper()

    def test_encryption_at_rest(self, auth_headers):
        # Use mongo via subprocess since we cannot import backend deps here
        import subprocess
        res = subprocess.run(
            ["mongosh", "--quiet", "--eval",
             "db=db.getSiblingDB('guardian_health');"
             "printjson(db.family_contacts.findOne({contact_id:'" + TestFamilyContacts.created_id + "'}))"],
            capture_output=True, text=True, timeout=10)
        out = res.stdout
        assert "phone_enc" in out, f"phone_enc missing in doc: {out}"
        assert "gAAAA" in out, f"Fernet ciphertext prefix missing: {out}"
        # ensure no plaintext phone field
        # The doc should NOT have a "phone:" key (only phone_enc)
        assert not re.search(r"\bphone:\s*'\+?\d", out), f"plaintext phone found: {out}"

    def test_delete_and_unknown(self, auth_headers):
        assert TestFamilyContacts.created_id
        r = requests.delete(f"{BASE_URL}/api/family-contacts/{TestFamilyContacts.created_id}",
                            headers=auth_headers, timeout=15)
        assert r.status_code == 200
        # unknown id
        r2 = requests.delete(f"{BASE_URL}/api/family-contacts/nonexistent_id_xyz",
                             headers=auth_headers, timeout=15)
        assert r2.status_code == 404

    def test_maria_still_present(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/family-contacts", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        ids = [c["contact_id"] for c in r.json()["contacts"]]
        assert "d36d87633c0b4b9c9f4fa9eda888d378" in ids, "Mária must never be deleted"


# ----- REGRESSION -----
class TestRegression:
    def test_triage_state(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/triage/state", headers=auth_headers, timeout=15)
        assert r.status_code == 200

    def test_sonar_degraded(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/agent/search", headers=auth_headers,
                          json={"query": "aktuálne správy o EMA"}, timeout=60)
        assert r.status_code == 200
        data = r.json()
        assert data.get("degraded") is True  # blank key
        assert data.get("reply")
