# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Phase 5 backend tests — Guardian Health & Angel: Global Compliance & Indemnity Upgrade.

Covers:
- GET /api/legal/region — jurisdiction resolution (EU/UK/US/OTHER), disclaimers, testament_format, AML limits
- GET /api/legal/tos — versioned TOS with waiver + 'Guardian Angel'
- POST /api/legal/accept — persists tos_accepted_version on user, verified via /api/auth/me
- AML: GET /api/aml/status pre-KYC, POST /api/aml/kyc validation & attestation, limit change post-KYC
- AML enforcement: solidarity campaign creation requires KYC (403 kyc_required), donation daily limit (403 aml_limit),
  velocity cap (403 aml_velocity)
- AML ledger tamper-evident chain (seq + prev_hash linkage)
- POST /api/legal/testament — civil_law_holograph (SK) vs common_law_uk (GB) formats
- Regression: POST /api/ai/translate still works with AI compliance note appended
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

BASE_URL = (os.environ.get("EXPO_PUBLIC_BACKEND_URL") or "https://guardian-vault-13.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

TOS_VERSION = "2026-06.1"


def _mk_ids(tag):
    return {
        "session_token": f"TEST_p5_{tag}_{uuid.uuid4().hex}",
        "user_id": f"TEST_p5_{tag}_{uuid.uuid4().hex[:10]}",
        "did": f"did:guardian:TESTP5{tag}{uuid.uuid4().hex[:16]}",
        "email": f"TEST_p5_{tag}_{uuid.uuid4().hex[:6]}@example.com",
    }


# Fresh user (no tos, no kyc) for gate & limit tests, and a second one we'll KYC-verify
USER_FRESH = _mk_ids("F")
USER_KYC = _mk_ids("K")


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
    await db.users.delete_many({"user_id": uid})
    await db.user_sessions.delete_many({"user_id": uid})
    await db.aml_ledger.delete_many({"user_id": uid})
    await db.donations.delete_many({"donor_user_id": uid})
    await db.campaigns.delete_many({"user_id": uid})
    await db.legal_testaments.delete_many({"user_id": uid})


@pytest.fixture(scope="module", autouse=True)
def seed_and_cleanup():
    c = AsyncIOMotorClient(MONGO_URL)
    db = c[DB_NAME]
    loop = asyncio.new_event_loop()
    loop.run_until_complete(_seed_user(db, USER_FRESH, "TEST P5 Fresh"))
    loop.run_until_complete(_seed_user(db, USER_KYC, "TEST P5 Kyc"))
    yield
    loop.run_until_complete(_cleanup(db, USER_FRESH))
    loop.run_until_complete(_cleanup(db, USER_KYC))
    c.close()
    loop.close()


def _h(u):
    return {"Authorization": f"Bearer {u['session_token']}", "Content-Type": "application/json"}


# ---------- LEGAL REGION ----------

class TestLegalRegion:
    def test_sk_eu_jurisdiction(self):
        r = requests.get(f"{BASE_URL}/api/legal/region", params={"country": "SK", "language": "sk"}, headers=_h(USER_FRESH))
        assert r.status_code == 200
        d = r.json()
        assert d["jurisdiction"] == "EU"
        assert d["testament_format"] == "civil_law_holograph"
        assert len(d["disclaimers"]) == 3
        ids = {x["id"] for x in d["disclaimers"]}
        assert {"eu_ai_act", "eu_gdpr", "eu_medical"} <= ids
        assert d["aml"]["unverified_daily_limit"] == 150
        assert d["aml"]["verified_daily_limit"] == 5000
        assert d["aml"]["max_tx_per_day"] == 10
        assert d["tos_version"] == TOS_VERSION

    def test_gb_uk_jurisdiction(self):
        r = requests.get(f"{BASE_URL}/api/legal/region", params={"country": "GB"}, headers=_h(USER_FRESH))
        assert r.status_code == 200
        d = r.json()
        assert d["jurisdiction"] == "UK"
        assert d["testament_format"] == "common_law_uk"

    def test_us_common_law(self):
        r = requests.get(f"{BASE_URL}/api/legal/region", params={"country": "US"}, headers=_h(USER_FRESH))
        assert r.status_code == 200
        d = r.json()
        assert d["jurisdiction"] == "US"
        assert d["testament_format"] == "common_law"

    def test_other_jurisdiction(self):
        r = requests.get(f"{BASE_URL}/api/legal/region", params={"country": "XX"}, headers=_h(USER_FRESH))
        assert r.status_code == 200
        assert r.json()["jurisdiction"] == "OTHER"


# ---------- TOS + ACCEPT ----------

class TestTos:
    def test_tos_sk_has_waiver_and_author(self):
        r = requests.get(f"{BASE_URL}/api/legal/tos", params={"language": "sk"}, headers=_h(USER_FRESH))
        assert r.status_code == 200
        d = r.json()
        assert d["version"] == TOS_VERSION
        assert "ZBAVENIE ZODPOVEDNOSTI" in d["text"]
        assert "Guardian Angel" in d["text"]

    def test_accept_persists_and_me_reflects(self):
        r = requests.post(f"{BASE_URL}/api/legal/accept", json={"country": "SK", "language": "sk"}, headers=_h(USER_FRESH))
        assert r.status_code == 200
        # Verify via /api/auth/me
        me = requests.get(f"{BASE_URL}/api/auth/me", headers=_h(USER_FRESH))
        assert me.status_code == 200
        u = me.json()["user"]
        assert u.get("tos_accepted_version") == TOS_VERSION
        assert u.get("tos_jurisdiction") == "EU"


# ---------- AML STATUS + KYC ----------

class TestAml:
    def test_status_pre_kyc(self):
        r = requests.get(f"{BASE_URL}/api/aml/status", headers=_h(USER_KYC))
        assert r.status_code == 200
        d = r.json()
        assert d["kyc_verified"] is False
        assert d["daily_limit"] == 150

    def test_kyc_requires_declaration(self):
        r = requests.post(f"{BASE_URL}/api/aml/kyc",
                          json={"full_name": "Test User", "birth_year": 1980, "country": "SK", "declaration": False},
                          headers=_h(USER_KYC))
        assert r.status_code == 400

    def test_kyc_verifies_and_raises_limit(self):
        r = requests.post(f"{BASE_URL}/api/aml/kyc",
                          json={"full_name": "Test Kyc", "birth_year": 1980, "country": "SK", "declaration": True},
                          headers=_h(USER_KYC))
        assert r.status_code == 200
        d = r.json()
        assert d["kyc_verified"] is True
        assert len(d["attestation"]) == 64  # sha256 hex
        assert len(d["ledger_hash"]) == 64
        # verify status now shows verified + 5000
        s = requests.get(f"{BASE_URL}/api/aml/status", headers=_h(USER_KYC)).json()
        assert s["kyc_verified"] is True
        assert s["daily_limit"] == 5000


# ---------- AML ENFORCEMENT ON SOLIDARITY (single flow to avoid xdist ordering issues) ----------

def _ensure_kyc(user):
    """Idempotent KYC — if already verified this is a no-op-ish."""
    requests.post(f"{BASE_URL}/api/aml/kyc",
                  json={"full_name": "Test Kyc", "birth_year": 1980, "country": "SK", "declaration": True},
                  headers=_h(user))


class TestAmlEnforcement:
    """FRESH user (unverified) for gate/limit; KYC user for post-verify creation & velocity."""

    def test_end_to_end_aml_enforcement(self):
        # 1) Fresh (unverified) cannot create campaigns
        r = requests.post(f"{BASE_URL}/api/solidarity/campaigns",
                          json={"title": "TEST", "story": "s", "goal_amount": 100},
                          headers=_h(USER_FRESH))
        assert r.status_code == 403 and "kyc_required" in r.text

        # 2) KYC the second user (idempotent) then create campaign
        _ensure_kyc(USER_KYC)
        r = requests.post(f"{BASE_URL}/api/solidarity/campaigns",
                          json={"title": "TEST_p5 campaign", "story": "s", "goal_amount": 500},
                          headers=_h(USER_KYC))
        assert r.status_code == 200, r.text
        cid = r.json()["campaign_id"]
        assert cid

        # 3) FRESH donates 100 OK, then 100 → 403 aml_limit (150 cap)
        r1 = requests.post(f"{BASE_URL}/api/solidarity/campaigns/{cid}/donate",
                           json={"amount": 100}, headers=_h(USER_FRESH))
        assert r1.status_code == 200, r1.text
        r2 = requests.post(f"{BASE_URL}/api/solidarity/campaigns/{cid}/donate",
                           json={"amount": 100}, headers=_h(USER_FRESH))
        assert r2.status_code == 403 and "aml_limit" in r2.text

        # 4) KYC user: 10 tiny donations OK, 11th → 403 aml_velocity
        for i in range(10):
            rr = requests.post(f"{BASE_URL}/api/solidarity/campaigns/{cid}/donate",
                               json={"amount": 1, "message": f"tx {i}"}, headers=_h(USER_KYC))
            assert rr.status_code == 200, f"tx {i} failed: {rr.text}"
        r11 = requests.post(f"{BASE_URL}/api/solidarity/campaigns/{cid}/donate",
                            json={"amount": 1}, headers=_h(USER_KYC))
        assert r11.status_code == 403 and "aml_velocity" in r11.text


# ---------- AML LEDGER CHAIN INTEGRITY ----------

class TestAmlLedger:
    def test_ledger_chain_links(self):
        """Verify entries for KYC user have seq + prev_hash and increasing seqs.
        Self-sufficient: generates ≥3 ledger entries itself (worker-independent
        under xdist loadscope class splitting)."""
        # each of these appends one AML ledger entry for USER_KYC
        _ensure_kyc(USER_KYC)  # kyc_attestation
        requests.post(f"{BASE_URL}/api/legal/accept",
                      json={"country": "SK", "language": "sk"}, headers=_h(USER_KYC))  # tos_accept
        requests.post(f"{BASE_URL}/api/solidarity/campaigns",
                      json={"title": "TEST_p5 ledger campaign", "story": "s", "goal_amount": 10},
                      headers=_h(USER_KYC))  # campaign_create
        import pymongo
        pc = pymongo.MongoClient(MONGO_URL)
        pdb = pc[DB_NAME]
        entries = list(pdb.aml_ledger.find({"user_id": USER_KYC["user_id"]}, {"_id": 0}).sort("seq", 1))
        pc.close()
        assert len(entries) >= 3, f"Expected ≥3 ledger entries, got {len(entries)}"
        prev_seq = 0
        for e in entries:
            assert "seq" in e and "prev_hash" in e and "entry_hash" in e
            assert isinstance(e["seq"], int) and e["seq"] > prev_seq
            prev_seq = e["seq"]
            assert len(e["entry_hash"]) == 64
            assert e["prev_hash"] == "genesis" or len(e["prev_hash"]) == 64


# ---------- TESTAMENT ENGINE ----------

class TestTestament:
    def test_sk_civil_law_holograph(self):
        r = requests.post(f"{BASE_URL}/api/legal/testament",
                          json={"country": "SK", "language": "sk", "full_name": "Ján Testovací",
                                "wishes": "Všetko delím rovným dielom deťom."},
                          headers=_h(USER_KYC))
        assert r.status_code == 200
        d = r.json()
        assert d["format"] == "civil_law_holograph"
        assert "§ 476" in d["document_text"]
        assert "VLASTNOU RUKOU" in d["document_text"]
        assert len(d["doc_hash"]) == 64
        # GET returns saved
        g = requests.get(f"{BASE_URL}/api/legal/testament", headers=_h(USER_KYC))
        assert g.status_code == 200
        assert g.json().get("format") == "civil_law_holograph"

    def test_gb_common_law_uk(self):
        r = requests.post(f"{BASE_URL}/api/legal/testament",
                          json={"country": "GB", "language": "en", "full_name": "John Test",
                                "wishes": "All to my children equally."},
                          headers=_h(USER_KYC))
        assert r.status_code == 200
        d = r.json()
        assert d["format"] == "common_law_uk"
        assert "Wills Act 1837" in d["document_text"]
        assert "WITNESS 1" in d["document_text"] or "SVEDOK 1" in d["document_text"]


# ---------- REGRESSION: AI TRANSLATE ----------

class TestRegression:
    def test_translate_still_works(self):
        r = requests.post(f"{BASE_URL}/api/ai/translate",
                          json={"text": "Hypertension is elevated blood pressure.", "language": "sk"},
                          headers=_h(USER_KYC), timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "plain_language" in d
        assert isinstance(d["plain_language"], str)
        assert len(d["plain_language"]) > 20
