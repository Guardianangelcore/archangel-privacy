# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
"""Phase 17: Master-Seal + Giga-Layer tests.

Sovereign Recovery Suite (guardians / Social 2FA / QR Talisman / passkeys /
social recovery), Offline Compass (ePN + vaccinations), Truth-Validator,
Bio-Beacon, Paramedic registry (NCZI/ÚZIS), Satellite Nano-Packet,
IPS export (HL7 FHIR), Humanitarian Shield, Gigs, Refunds, DAO rebranding."""
import os
import requests

BASE_URL = (os.environ.get("EXPO_BACKEND_URL")
            or os.environ.get("EXPO_PUBLIC_BACKEND_URL")
            or "https://guardian-vault-13.preview.emergentagent.com").rstrip("/")
T1 = "smoketok-fresh-2026"
T2 = "smoketok-fresh-2026-u2"
H1 = {"Authorization": f"Bearer {T1}"}
H2 = {"Authorization": f"Bearer {T2}"}
U1_EMAIL = "smoke@test.sk"


def _get(path, h=H1, **kw):
    return requests.get(f"{BASE_URL}/api{path}", headers=h, timeout=30, **kw)

def _post(path, h=H1, json=None):
    return requests.post(f"{BASE_URL}/api{path}", headers=h, json=json, timeout=30)


def _ensure_sentinel(h=H1):
    """Premium gating (Monetization Lockdown): make sure the smoke user has
    Sentinel access — via the one-time 7-day trial if needed."""
    sub = _get("/subscription", h=h).json()
    if sub["tier"] in ("sentinel", "archangel"):
        return
    _post("/subscription/trial", h=h)


# ------------------- DAO rebranding -------------------
class TestDAORebranding:
    def test_root_author_is_dao(self):
        r = requests.get(f"{BASE_URL}/api/", timeout=15)
        assert r.status_code == 200
        assert r.json()["author"] == "Guardian Angel Sovereign Foundation (DAO)"

    def test_dao_manifest_public(self):
        r = requests.get(f"{BASE_URL}/api/dao/manifest", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["foundation"] == "Guardian Angel Sovereign Foundation (DAO)"
        assert "Article 50" in d["liability"]


# ------------------- Recovery Suite -------------------
class TestRecoverySuite:
    def test_guardian_add_and_status(self):
        r = _post("/recovery-suite/guardians", json={"contact": "smoke2@example.com"})
        assert r.status_code in (200, 409), r.text  # 409 = already added (idempotent runs)
        st = _get("/recovery-suite/status").json()
        assert st["guardians"] >= 1 and st["social_recovery_ready"] is True

    def test_guardian_unknown_contact_404(self):
        r = _post("/recovery-suite/guardians", json={"contact": "ghost@nowhere.xx"})
        assert r.status_code == 404

    def test_social_2fa_toggle(self):
        r = requests.patch(f"{BASE_URL}/api/recovery-suite/social-2fa", headers=H1,
                           json={"enabled": True}, timeout=30)
        assert r.status_code == 200 and r.json()["social_2fa_enabled"] is True

    def test_talisman_generate_and_redeem_once(self):
        gen = _post("/recovery-suite/talisman").json()
        assert gen["payload"].startswith("GA-TALISMAN|")
        _, did, secret = gen["payload"].split("|")
        red = _post("/recovery-suite/talisman/redeem", h={}, json={"did": did, "secret": secret})
        assert red.status_code == 200 and red.json()["session_token"].startswith("talis-")
        again = _post("/recovery-suite/talisman/redeem", h={}, json={"did": did, "secret": secret})
        assert again.status_code == 409  # one-time use

    def test_talisman_redeem_invalid_401(self):
        r = _post("/recovery-suite/talisman/redeem", h={},
                  json={"did": "did:guardian:smoke1", "secret": "wrong"})
        assert r.status_code == 401

    def test_passkey_register(self):
        r = _post("/recovery-suite/passkey/register", json={"device_name": "Pytest Device"})
        assert r.status_code == 200 and r.json()["simulated"] is True
        st = _get("/recovery-suite/status").json()
        assert st["passkey_ready"] is True and st["security_score"] >= 75

    def test_social_recovery_full_flow(self):
        init = _post("/recovery-suite/social/initiate", h={}, json={"identifier": U1_EMAIL})
        assert init.status_code == 200, init.text
        rid = init.json()["req_id"]
        reqs = _get("/recovery-suite/social/requests", h=H2).json()["requests"]
        assert any(x["req_id"] == rid for x in reqs)
        ap = _post(f"/recovery-suite/social/{rid}/approve", h=H2)
        assert ap.status_code == 200 and ap.json()["status"] == "approved"
        poll = requests.get(f"{BASE_URL}/api/recovery-suite/social/{rid}/status", timeout=15).json()
        assert poll["status"] == "approved" and poll["session_token"].startswith("recov-")
        poll2 = requests.get(f"{BASE_URL}/api/recovery-suite/social/{rid}/status", timeout=15).json()
        assert "session_token" not in poll2  # delivered exactly once

    def test_social_recovery_unknown_404(self):
        r = _post("/recovery-suite/social/initiate", h={}, json={"identifier": "ghost@nowhere.xx"})
        assert r.status_code == 404


# ------------------- Compass (ePN + vaccinations) -------------------
class TestCompass:
    def test_pack_contains_sickleave_and_vaccinations(self):
        r = _get("/compass/pack")
        assert r.status_code == 200
        d = r.json()
        for key in ("identity", "meds_today", "sick_leave", "vaccinations",
                    "survival_guide", "emergency_numbers", "integrity_sha256"):
            assert key in d, f"missing {key}"
        assert "outings" in d["sick_leave"]
        assert "booster_alerts" in d["vaccinations"] and "history" in d["vaccinations"]
        assert d["emergency_numbers"].get("EU / SK / CZ") == "112"

    def test_pack_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/compass/pack", timeout=15)
        assert r.status_code == 401


# ------------------- Truth-Validator -------------------
class TestTruthValidator:
    def test_submit_vote_consensus(self):
        c = _post("/truth/claims", json={"text": "PYTEST: lekáreň má Ibalgin skladom dnes",
                                         "category": "shortage", "city": "BA"}).json()
        cid = c["claim_id"]
        assert c["status"] == "pending" and len(c["claim_sha256"]) == 64
        own = _post(f"/truth/claims/{cid}/vote", json={"vote": "verify"})
        assert own.status_code == 400  # cannot vote own claim
        v = _post(f"/truth/claims/{cid}/vote", h=H2, json={"vote": "verify"})
        assert v.status_code == 200 and v.json()["verify_votes"] == 1
        dup = _post(f"/truth/claims/{cid}/vote", h=H2, json={"vote": "verify"})
        assert dup.status_code == 409

    def test_short_claim_rejected(self):
        r = _post("/truth/claims", json={"text": "krátke", "category": "other"})
        assert r.status_code == 400


# ------------------- Bio-Beacon -------------------
class TestBioBeacon:
    def test_lifecycle_and_public_read(self):
        b = _post("/bio-beacon/activate", json={"lat": 48.15, "lng": 17.11, "note": "pytest"}).json()
        assert b["active"] is True
        did = b["did"]
        pub = requests.get(f"{BASE_URL}/api/bio-beacon/public/{did}", timeout=15)
        assert pub.status_code == 200 and pub.json()["active"] is True
        ping = _post("/bio-beacon/ping", json={"heart_rate": 88})
        assert ping.status_code == 200
        off = _post("/bio-beacon/deactivate").json()
        assert off["deactivated"] >= 1
        gone = requests.get(f"{BASE_URL}/api/bio-beacon/public/{did}", timeout=15)
        assert gone.status_code == 404


# ------------------- Paramedic registry -------------------
class TestParamedicRegistry:
    def test_registry_verify_deterministic(self):
        ok = _post("/paramedic/verify-registry", json={"license_number": "A1234567", "country": "SK"}).json()
        # digit sum 1+2+3+4+5+6+7 = 28 → even → valid
        assert ok["valid"] is True and ok["simulated"] is True and "NCZI" in ok["registry"]
        bad = _post("/paramedic/verify-registry", json={"license_number": "A1234568", "country": "CZ"}).json()
        assert bad["valid"] is False and "ÚZIS" in bad["registry"]

    def test_registry_bad_input_400(self):
        r = _post("/paramedic/verify-registry", json={"license_number": "AB", "country": "SK"})
        assert r.status_code == 400


# ------------------- Satellite Nano-Packet -------------------
class TestSatellite:
    def test_nano_packet_queued_and_compressed(self):
        _ensure_sentinel()
        p = _post("/satellite/nano-packet", json={"lat": 48.15, "lng": 17.11, "note": "SOS"}).json()
        assert p["status"] == "queued" and p["simulated"] is True
        assert p["packet_bytes"] <= 140 and p["fits_sat_sms"] is True
        q = _get("/satellite/queue").json()
        assert any(x["packet_id"] == p["packet_id"] for x in q["queue"])

    def test_swarm_broadcasts_queue(self):
        run = _post("/swarm/run/sovereign_guard").json()
        assert run["status"] == "ok"
        q = _get("/satellite/queue").json()["queue"]
        assert q and all(x["status"] == "broadcasted" for x in q[:3])


# ------------------- IPS (Universal Health Resume) -------------------
class TestIPS:
    def test_fhir_bundle_structure(self):
        _ensure_sentinel()
        d = _get("/ips/summary").json()
        b = d["bundle"]
        assert b["resourceType"] == "Bundle" and b["type"] == "document"
        assert "Bundle-uv-ips" in b["meta"]["profile"][0]
        comp = b["entry"][0]["resource"]
        assert comp["resourceType"] == "Composition"
        assert comp["type"]["coding"][0]["code"] == "60591-5"
        section_codes = {s["code"]["coding"][0]["code"] for s in comp["section"]}
        assert {"48765-2", "10160-0", "11450-4", "11369-6"} <= section_codes
        assert len(d["interoperability"]) == 3

    def test_ips_pdf(self):
        r = _get(f"/ips/summary.pdf?token={T1}", h={})
        assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"


# ------------------- Humanitarian Shield -------------------
class TestHumanitarian:
    def test_verify_then_profile_and_pdf(self):
        ev = _post("/humanitarian/verify", json={"kind": "blackout", "region": "PYTEST"}).json()
        assert ev["verified"] is True and ev["simulated"] is True
        p = _post("/humanitarian/profile").json()
        assert p["hum_id"].startswith("GA-HUM-") and p["qr_payload"].startswith("GA-HUM|")
        assert "UNHCR PRIMES-compatible" in p["standards"]
        st = _get("/humanitarian/status").json()
        assert st["catastrophe_verified"] is True and st["profile"]["hum_id"] == p["hum_id"]
        pdf = _get(f"/humanitarian/card.pdf?token={T1}", h={})
        assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"


# ------------------- Gigs + Refunds -------------------
class TestGigsRefunds:
    def test_gig_lifecycle(self):
        g = _post("/gigs", json={"kind": "grocery", "title": "PYTEST nákup", "city": "BA",
                                 "reward_gat": 10}).json()
        gid = g["gig_id"]
        own = _post(f"/gigs/{gid}/accept")
        assert own.status_code == 400  # cannot accept own gig
        acc = _post(f"/gigs/{gid}/accept", h=H2)
        assert acc.status_code == 200
        done = _post(f"/gigs/{gid}/complete").json()
        assert done["status"] == "done"

    def test_refund_claim(self):
        c = _post("/refunds/claim").json()
        assert "estimated_refund_eur" in c and isinstance(c["items"], list)
        pdf = _get(f"/refunds/claim.pdf?token={T1}", h={})
        assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"


# ------------------- Daily Brief (neschopenka + vaccinations) -------------------
class TestDailyBriefMasterSeal:
    def test_brief_has_boosters_and_recovery_outings(self):
        d = _get("/daily-brief").json()
        assert "vaccine_boosters" in d
        rec = d.get("recovery")
        if rec:  # active ePN present in smoke data
            assert "outings" in rec


# ------------------- Swarm integration -------------------
class TestSwarmIntegration:
    def test_sovereign_guard_registered(self):
        st = _get("/swarm/status").json()
        ids = [a["agent_id"] for a in st["agents"]]
        assert "sovereign_guard" in ids and len(ids) >= 7
