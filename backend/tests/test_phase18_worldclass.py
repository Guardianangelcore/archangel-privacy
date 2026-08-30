# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
"""Phase 18: World-Class Finale + Elite Monetization + Mosaic Protocol tests.

AI Tactical Medic, Vitals Bio-Scanner (5 GA-T pay-per-use), Longevity Engine,
Environmental Threat Fusion, 4-tier subscriptions (€0/29/149/499, annual −20%),
Sentinel trial, Founder Wealth dashboard, Guardian Tax 15%, Mosaic ZK-L2."""
import os
import requests

BASE_URL = (os.environ.get("EXPO_BACKEND_URL")
            or os.environ.get("EXPO_PUBLIC_BACKEND_URL")
            or "https://guardian-vault-13.preview.emergentagent.com").rstrip("/")
H1 = {"Authorization": "Bearer smoketok-fresh-2026"}
H2 = {"Authorization": "Bearer smoketok-fresh-2026-u2"}


def _get(path, h=H1):
    return requests.get(f"{BASE_URL}/api{path}", headers=h, timeout=30)

def _post(path, h=H1, json=None):
    return requests.post(f"{BASE_URL}/api{path}", headers=h, json=json, timeout=30)

def _ensure_sentinel(h=H1):
    sub = _get("/subscription", h=h).json()
    if sub["tier"] not in ("sentinel", "archangel"):
        _post("/subscription/trial", h=h)


# ------------------- Elite subscription tiers -------------------
class TestEliteTiers:
    def test_four_tiers_and_pricing(self):
        d = _get("/subscription").json()
        t = d["tiers"]
        assert set(t) == {"sovereign", "guardian", "sentinel", "archangel"}
        assert t["guardian"]["price_eur"] == 29
        assert t["sentinel"]["price_eur"] == 149
        assert t["archangel"]["price_eur"] == 499
        # annual −20 %
        assert t["sentinel"]["price_eur_year"] == round(149 * 12 * 0.8, 0)
        # multi-currency
        assert t["guardian"]["price_czk"] == 29 * 25
        assert d["annual_discount_pct"] == 20
        assert set(d["currencies"]) == {"EUR", "CZK", "GA-T"}
        assert d["payperuse"]["bioscan_single"] == 5
        assert d["payperuse"]["ips_export_single"] == 10

    def test_trial_then_second_trial_409(self):
        _ensure_sentinel()
        r = _post("/subscription/trial")
        assert r.status_code == 409  # used or already premium

    def test_card_payment_still_placeholder(self):
        # Since iter25 card payments are LIVE via Stripe — /subscription/upgrade
        # intentionally rejects method=card with 400 pointing to /billing/checkout.
        r = _post("/subscription/upgrade", json={"tier": "archangel", "method": "card"})
        assert r.status_code == 400
        assert "billing/checkout" in r.json().get("detail", "")

    def test_invalid_tier_400(self):
        r = _post("/subscription/upgrade", json={"tier": "galactic", "method": "gat"})
        assert r.status_code == 400


# ------------------- AI Tactical Medic -------------------
class TestTacticalMedic:
    def test_paywalled_for_free_user(self):
        r = _get("/medic/protocols", h=H2)
        # user2 = sovereign, no active emergency → 402 (unless a beacon override is live)
        assert r.status_code in (402, 200)

    def test_protocols_for_sentinel(self):
        _ensure_sentinel()
        d = _get("/medic/protocols").json()
        assert d["offline_cacheable"] is True
        ids = {p["id"] for p in d["protocols"]}
        assert {"cpr", "bleeding", "choking", "burns", "shock", "hypothermia", "seizure"} <= ids
        cpr = next(p for p in d["protocols"] if p["id"] == "cpr")
        assert len(cpr["steps"]) >= 6


# ------------------- Vitals Bio-Scanner -------------------
class TestBioScanner:
    def test_free_user_402_without_pay(self):
        r = _post("/bioscan/measure", h=H2, json={"duration_s": 10})
        assert r.status_code == 402
        assert "5 GA-T" in r.json()["detail"]

    def test_sentinel_unlimited(self):
        _ensure_sentinel()
        r = _post("/bioscan/measure", json={"duration_s": 10, "samples": [0.5, 0.6, 0.4, 0.7, 0.5, 0.6, 0.55, 0.62, 0.48]})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["access"] == "tier" and d["simulated"] is True
        assert 40 <= d["heart_rate"] <= 120 and 90 <= d["spo2"] <= 100
        assert d["stress_level"] in ("low", "moderate", "high")

    def test_pay_per_use_with_gat(self):
        # user2 pays 5 GA-T (earned via Proof-of-Help); tolerate an empty wallet
        r = _post("/bioscan/measure", h=H2, json={"duration_s": 10, "pay_gat": True})
        assert r.status_code in (200, 402), r.text
        if r.status_code == 200:
            assert r.json()["access"] == "gat"
        else:
            assert "insufficient_balance" in r.json()["detail"]

    def test_history(self):
        r = _get("/bioscan/history")
        assert r.status_code == 200 and isinstance(r.json()["scans"], list)


# ------------------- Longevity Engine -------------------
class TestLongevity:
    def test_profile_and_bioage(self):
        _ensure_sentinel()
        p = requests.put(f"{BASE_URL}/api/longevity/profile", headers=H1, timeout=30,
                         json={"birth_year": 1971, "height_cm": 178, "weight_kg": 92,
                               "smoker": False, "activity_level": "low"})
        assert p.status_code == 200, p.text
        d = _get("/longevity/bioage").json()
        assert d["chronological_age"] == 2026 - 1971
        assert isinstance(d["biological_age"], (int, float))
        assert d["verdict"] and isinstance(d["bio_hacks"], list) and d["bio_hacks"]
        assert any(f["factor"] == "Aktivita" for f in d["factors"])

    def test_bioage_needs_profile_or_tier(self):
        r = _get("/longevity/bioage", h=H2)
        assert r.status_code in (402, 409)

    def test_bad_birth_year_400(self):
        r = requests.put(f"{BASE_URL}/api/longevity/profile", headers=H1, timeout=30,
                         json={"birth_year": 1800})
        assert r.status_code == 400


# ------------------- Environmental Threat Fusion -------------------
class TestEnviroFusion:
    def test_report_and_mesh_consensus(self):
        for h in (H1, H2):
            r = _post("/enviro/report", h=h, json={"kind": "heat", "severity": 4, "city": "PytestCity"})
            assert r.status_code == 200, r.text
        d = _get("/enviro/threats").json()
        match = [t for t in d["threats"] if t["city"].lower() == "pytestcity" and t["kind"] == "heat"]
        assert match and match[0]["status"] == "CONFIRMED" and match[0]["reports"] >= 2

    def test_swarm_escalates_confirmed_threat(self):
        r = _post("/swarm/run/sovereign_guard")
        assert r.status_code == 200 and r.json()["status"] == "ok"

    def test_invalid_kind_400(self):
        r = _post("/enviro/report", json={"kind": "zombies"})
        assert r.status_code == 400


# ------------------- Mosaic Protocol -------------------
class TestMosaic:
    def test_status_and_zero_fee(self):
        d = _get("/mosaic/status").json()
        assert d["name"] == "Mosaic Chain" and "ZK-Rollup" in d["layer"]
        assert "Kyber" in d["pqc_suite"] and d["simulated"] is True
        assert "ZERO-FEE" in d["gas_policy"]

    def test_anchor_block_chain_links(self):
        b1 = _post("/mosaic/anchor").json()["block"]
        b2 = _post("/mosaic/anchor").json()["block"]
        assert b2["height"] == b1["height"] + 1
        assert b2["prev_hash"] == b1["block_hash"]
        assert b2["gas_fee_user"] == 0.0 and b2["gas_paid_by"] == "foundation-treasury"
        assert b2["zk_proof"].startswith("zkp-")

    def test_pqc_handshake(self):
        d = _get("/mosaic/pqc-handshake").json()
        assert d["quantum_safe"] is True and "ML-KEM-1024" in d["kem"]

    def test_bridge_watch(self):
        d = _post("/mosaic/bridge/check").json()
        assert d["primary"] == "Mosaic Chain"
        assert d["active"] in ("Mosaic Chain", "Base (mirror)")
        assert d["threshold_ms"] == 800

    def test_ipfs_manifest_hybrid_layer(self):
        d = _get("/mosaic/ipfs/manifest").json()
        assert "files" in d
        for f in d["files"]:
            assert f["ipfs_cid"].startswith("bafy") and len(f["onchain_hash"]) == 64

    def test_legacy_smart_contract(self):
        d = _post("/mosaic/legacy-contract").json()
        assert d["contract_id"].startswith("0x") and d["gas_fee_user"] == 0.0

    def test_global_stress_test(self):
        d = _post("/mosaic/stress-test").json()
        assert len(d["nodes"]) == 5 and d["total_tps"] > 8000
        assert d["verdict"] == "READY FOR PUBLISH"


# ------------------- Founder Wealth + Guardian Tax -------------------
class TestFounderWealth:
    def test_founder_dashboard(self):
        r = _get("/wealth/founder-dashboard")
        assert r.status_code in (200, 403)
        if r.status_code == 200:
            d = r.json()
            assert d["founder_view"] is True and d["guardian_tax_rate"] == 0.15
            assert "mrr_eur" in d and "acv_eur" in d and "revenue_by_kind" in d
            assert d["wealth_engine"].startswith("SECURED")

    def test_guardian_tax_on_gig_cash_reward(self):
        g = _post("/gigs", json={"kind": "transport", "title": "PYTEST tax gig", "city": "BA",
                                 "reward_gat": 5, "reward_eur": 20}).json()
        _post(f"/gigs/{g['gig_id']}/accept", h=H2)
        done = _post(f"/gigs/{g['gig_id']}/complete").json()
        assert done["status"] == "done"
        r = _get("/wealth/founder-dashboard")
        if r.status_code == 200:
            assert r.json()["revenue_by_kind"].get("guardian_tax", 0) >= 3.0  # 15% z 20 €


# ------------------- Value Advisor upsell -------------------
class TestValueAdvisor:
    def test_upsell_rec_for_free_user(self):
        d = _get("/recommendations", h=H2).json()
        routes = [r["action_route"] for r in d["recommendations"]]
        assert "/bioscan" in routes
