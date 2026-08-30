# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
"""Phase 20: OMNIPOTENT ARCHANGEL FINAL SEAL — Video Legacy, Sovereign Wealth
Vault, Foundation Identity + Ghost Mode, Inner Circle, Medical Arbitrage,
Genomic Bio-Identity, Duress Protocol, Mesh-Messenger, Power-Saver."""
import os
import uuid
import requests

BASE_URL = (os.environ.get("EXPO_BACKEND_URL")
            or os.environ.get("EXPO_PUBLIC_BACKEND_URL")
            or "https://guardian-vault-13.preview.emergentagent.com").rstrip("/")
H1 = {"Authorization": "Bearer smoketok-fresh-2026"}      # founder
H2 = {"Authorization": "Bearer smoketok-fresh-2026-u2"}   # regular user


def _get(path, h=H1):
    return requests.get(f"{BASE_URL}/api{path}", headers=h, timeout=30)

def _post(path, h=H1, json=None, **kw):
    return requests.post(f"{BASE_URL}/api{path}", headers=h, json=json, timeout=60, **kw)

def _put(path, h=H1, json=None):
    return requests.put(f"{BASE_URL}/api{path}", headers=h, json=json, timeout=30)

def _delete(path, h=H1):
    return requests.delete(f"{BASE_URL}/api{path}", headers=h, timeout=30)


# ---------- FOUNDATION IDENTITY ----------
class TestFoundationIdentity:
    def test_hardcoded_protonmail(self):
        d = _get("/foundation/identity").json()
        assert d["official_email"] == "guardian.angel.core@proton.me"
        assert d["immutable"] is True
        assert "ProtonMail" in d["provider"]

    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/foundation/identity", timeout=30)
        assert r.status_code == 401


# ---------- GHOST MODE ----------
class TestGhostMode:
    def test_enable_generates_patient_token(self):
        d = _post("/ghost/toggle", json={"enabled": True}).json()
        assert d["ghost_mode"] is True
        assert d["patient_token"].startswith("GHOST-")
        s = _get("/ghost/status").json()
        assert s["ghost_mode"] is True and s["patient_token"] == d["patient_token"]

    def test_disable_clears_token(self):
        d = _post("/ghost/toggle", json={"enabled": False}).json()
        assert d["ghost_mode"] is False
        s = _get("/ghost/status").json()
        assert s["ghost_mode"] is False and s["patient_token"] is None


# ---------- VIDEO LEGACY VAULT ----------
class TestVideoLegacy:
    def test_upload_seal_release_delete(self):
        r = _post("/legacy/video",
                  files={"file": ("odkaz.mp4", b"\x00\x00\x00\x18ftypmp42" + b"G" * 2048, "video/mp4")},
                  data={"recipient_name": "Dcéra Anna", "relationship": "dcéra",
                        "title": "Testovací odkaz", "unlock_condition": "death_verified"})
        assert r.status_code == 200, r.text
        v = r.json()
        assert v["sha256"] and v["ledger_hash"] and v["released"] is False
        vid = v["video_id"]
        # sealed unless the life-status registry already verified death
        death_verified = bool(_get("/dignity/fund").json().get("death_verified"))
        lst = _get("/legacy/video").json()
        mine = next(x for x in lst["videos"] if x["video_id"] == vid)
        assert mine["unlocked_for_family"] is death_verified
        # owner can stream own file
        f = requests.get(f"{BASE_URL}/api/legacy/video/{vid}/file",
                         params={"token": "smoketok-fresh-2026"}, timeout=30)
        assert f.status_code == 200 and len(f.content) > 2000
        # manual release unlocks
        assert _post(f"/legacy/video/{vid}/release").json()["released"] is True
        lst = _get("/legacy/video").json()
        mine = next(x for x in lst["videos"] if x["video_id"] == vid)
        assert mine["unlocked_for_family"] is True
        assert _delete(f"/legacy/video/{vid}").json()["ok"] is True

    def test_rejects_non_video(self):
        r = _post("/legacy/video",
                  files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
                  data={"recipient_name": "X"})
        assert r.status_code == 400

    def test_invalid_unlock_condition(self):
        r = _post("/legacy/video",
                  files={"file": ("v.mp4", b"xx", "video/mp4")},
                  data={"recipient_name": "X", "unlock_condition": "whenever"})
        assert r.status_code == 400


# ---------- SOVEREIGN WEALTH VAULT ----------
class TestWealthVault:
    def test_bank_iban_validation(self):
        r = _post("/wealth/assets", json={"type": "bank", "label": "Zlá banka", "iban": "NOT-AN-IBAN"})
        assert r.status_code == 400

    def test_crypto_secret_sealed_never_plaintext(self):
        r = _post("/wealth/assets", json={
            "type": "crypto", "label": "TEST BTC wallet", "chain": "BTC",
            "address": "bc1qtestaddr9999", "secret": "seed words never stored plaintext",
            "est_value_eur": 1000})
        assert r.status_code == 200, r.text
        a = r.json()
        assert a["has_sealed_secret"] is True and len(a["secret_sha256"]) == 64
        assert "sealed_secret" not in a and "secret" not in a
        assert "…" in a["address_masked"]
        vault = _get("/wealth/vault").json()
        mine = next(x for x in vault["assets"] if x["asset_id"] == a["asset_id"])
        assert "sealed_secret" not in mine
        _delete(f"/wealth/assets/{a['asset_id']}")

    def test_bank_add_anchor_payout(self):
        a = _post("/wealth/assets", json={
            "type": "bank", "label": "TEST Tatra", "iban": "SK31 1200 0000 1987 4263 7541",
            "bank_name": "Tatra banka", "est_value_eur": 5000}).json()
        assert a["iban_masked"].startswith("SK31")
        anchor = _post("/wealth/anchor").json()
        assert len(anchor["manifest_sha256"]) == 64
        assert anchor["kind"] == "Proof of Asset Stewardship"
        assert anchor["gas_fee_user"] == 0.0
        pay = _post("/wealth/payout", json={"amount_eur": 250, "card_last4": "4242"}).json()
        assert pay["status"] == "instant_sent" and pay["simulated"] is True
        assert "Visa Direct" in pay["rail"]
        vault = _get("/wealth/vault").json()
        assert any(p["payout_id"] == pay["payout_id"] for p in vault["payouts"])
        _delete(f"/wealth/assets/{a['asset_id']}")

    def test_anchor_requires_assets(self):
        # user 2 has no assets
        r = _post("/wealth/anchor", h=H2)
        assert r.status_code == 400

    def test_payout_validation(self):
        assert _post("/wealth/payout", json={"amount_eur": 100, "card_last4": "abcd"}).status_code == 400
        assert _post("/wealth/payout", json={"amount_eur": -5, "card_last4": "4242"}).status_code == 422


# ---------- INNER CIRCLE ----------
class TestInnerCircle:
    def test_non_founder_403(self):
        assert _get("/inner-circle", h=H2).status_code == 403
        assert _post("/inner-circle", h=H2, json={"email": "x@y.sk"}).status_code == 403

    def test_add_grants_permanent_archangel(self):
        me2 = _get("/auth/me", h=H2).json()["user"]
        email = me2["email"]
        # clean slate
        for m in _get("/inner-circle").json()["members"]:
            if m["email"] == email:
                _delete(f"/inner-circle/{m['member_id']}")
        m = _post("/inner-circle", json={"email": email, "name": "Test rodina", "relationship": "sestra"}).json()
        assert m["status"] == "archangel_permanent"
        assert m.get("linked_user_id") == me2["user_id"]
        sub = _get("/subscription", h=H2).json()
        assert sub["tier"] == "archangel" and sub["inner_circle"] is True
        # duplicate rejected
        assert _post("/inner-circle", json={"email": email}).status_code == 409
        # removal downgrades
        assert _delete(f"/inner-circle/{m['member_id']}").json()["ok"] is True
        sub = _get("/subscription", h=H2).json()
        assert sub["tier"] == "sovereign" and sub["inner_circle"] is False

    def test_whitelist_pre_signup(self):
        email = f"pending-{uuid.uuid4().hex[:8]}@family.sk"
        m = _post("/inner-circle", json={"email": email, "name": "Budúci člen"}).json()
        assert "linked_user_id" not in m
        _delete(f"/inner-circle/{m['member_id']}")


# ---------- MEDICAL ARBITRAGE ----------
class TestMedicalArbitrage:
    def test_procedures_catalog(self):
        d = _get("/arbitrage/procedures").json()
        assert len(d["procedures"]) == 6
        assert set(d["countries"]) == {"PL", "HU", "TR"}
        hip = next(p for p in d["procedures"] if p["procedure_id"] == "hip-replacement")
        assert hip["best_saving_eur"] > 0 and hip["best_wait_cut_days"] > 0
        assert "2011/24" in d["legal_note"]

    def test_quote_eu_s2_refund(self):
        q = _post("/arbitrage/quote", json={"procedure_id": "hip-replacement", "country": "PL"}).json()
        b = q["breakdown"]
        assert b["s2_predicted_refund_eur"] > 0
        assert b["net_out_of_pocket_eur"] == b["total_eur"] - b["s2_predicted_refund_eur"]
        assert q["saving_vs_sk_eur"] > 0 and q["ghost_mode_compatible"] is True

    def test_quote_turkey_no_s2(self):
        q = _post("/arbitrage/quote", json={"procedure_id": "cataract", "country": "TR"}).json()
        assert q["breakdown"]["s2_predicted_refund_eur"] == 0
        assert "Samoplatba" in q["legal_route"]

    def test_quote_validation(self):
        assert _post("/arbitrage/quote", json={"procedure_id": "nonexistent", "country": "PL"}).status_code == 404
        assert _post("/arbitrage/quote", json={"procedure_id": "cataract", "country": "DE"}).status_code == 400

    def test_quotes_history(self):
        d = _get("/arbitrage/quotes").json()
        assert len(d["quotes"]) >= 1


# ---------- GENOMIC BIO-IDENTITY ----------
class TestGenomicBioIdentity:
    def test_put_and_hash_anchor(self):
        d = _put("/bioidentity/genomic", json={
            "provider": "Dante Labs", "markers": ["BRCA1: negatívny", "APOE: e3/e3"],
            "blood_type_confirmed": "A+", "notes": "test"}).json()
        assert len(d["genomic_sha256"]) == 64
        assert "zero-knowledge" in d["storage_policy"]
        g = _get("/bioidentity").json()
        assert g["markers"] == ["BRCA1: negatívny", "APOE: e3/e3"]


# ---------- DURESS PROTOCOL ----------
class TestDuressProtocol:
    def test_pins_must_differ(self):
        assert _put("/duress/pin", json={"real_pin": "1234", "duress_pin": "1234"}).status_code == 400

    def test_numeric_only(self):
        assert _put("/duress/pin", json={"real_pin": "abcd", "duress_pin": "9999"}).status_code == 400

    def test_full_decoy_invalid_flow(self):
        assert _put("/duress/pin", json={"real_pin": "1234", "duress_pin": "9999"}).json()["ok"] is True
        assert _post("/duress/verify", json={"pin": "1234"}).json()["vault_mode"] == "full"
        d = _post("/duress/verify", json={"pin": "9999"}).json()
        assert d["ok"] is True and d["vault_mode"] == "decoy"  # looks like a normal unlock
        assert _post("/duress/verify", json={"pin": "0000"}).json()["vault_mode"] == "invalid"
        s = _get("/duress/status").json()
        assert s["configured"] is True and len(s["alarms"]) >= 1

    def test_verify_without_config_404(self):
        assert _post("/duress/verify", h=H2, json={"pin": "1111"}).status_code == 404


# ---------- MESH-MESSENGER ----------
class TestMeshMessenger:
    def test_status(self):
        d = _get("/mesh/status").json()
        assert d["reachable_peers"] >= 2 and "Guardian Mesh" in d["protocol"]

    def test_send_delivered_to_known_did(self):
        did2 = _get("/auth/me", h=H2).json()["user"]["did"]
        m = _post("/mesh/messages", json={"to_did": did2, "text": "Mesh test — stretneme sa pri studni."}).json()
        assert m["status"] == "delivered" and m["hops"] == 1 and len(m["sha256"]) == 64
        inbox2 = _get("/mesh/messages", h=H2).json()
        assert any(x["msg_id"] == m["msg_id"] for x in inbox2["messages"])

    def test_send_queued_for_unknown_did(self):
        m = _post("/mesh/messages", json={"to_did": "did:guardian:unknownnode123", "text": "offline relay"}).json()
        assert m["status"] == "queued" and m["hops"] == 0

    def test_text_limits(self):
        assert _post("/mesh/messages", json={"to_did": "did:guardian:x", "text": ""}).status_code == 422


# ---------- POWER-SAVER ----------
class TestPowerSaver:
    def test_toggle_profile(self):
        d = _put("/power-saver", json={"enabled": True}).json()
        assert d["power_saver"] is True
        assert d["profile"]["theme"] == "pure_black"
        assert d["profile"]["estimated_battery_gain_pct"] > 0
        g = _get("/power-saver").json()
        assert g["power_saver"] is True
        d = _put("/power-saver", json={"enabled": False}).json()
        assert d["power_saver"] is False and d["profile"] is None
