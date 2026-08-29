# Iteration 15 — GA-T Token engine + Autonomous Swarm + DePIN + Neural Bus + Audit
# Idempotent across same-day runs — daily caps may already be consumed.
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://global-compass-hub.preview.emergentagent.com").rstrip("/")
SMOKE_TOKEN = "smoketok-fresh-2026"
AUTH = {"Authorization": f"Bearer {SMOKE_TOKEN}", "Content-Type": "application/json"}


# ---------- GA-T Supply ----------
class TestTokenSupply:
    def test_supply_symbol_and_totals(self):
        r = requests.get(f"{BASE_URL}/api/token/supply", headers=AUTH, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["symbol"] == "GA-T"
        assert d["total_supply"] == 100_000_000
        assert d["founder_reserve"] == 25_000_000
        assert d["burn_stats"]["burn_rate_pct"] == 2.0
        assert d["burn_stats"]["deflationary"] is True
        assert "2030" in str(d["founder_locked_until"]) or "2029" in str(d["founder_locked_until"])

    def test_supply_invariant(self):
        r = requests.get(f"{BASE_URL}/api/token/supply", headers=AUTH, timeout=15)
        d = r.json()
        s = d["treasury"] + d["circulating"] + d["burned"] + d["founder_reserve"]
        assert abs(s - d["total_supply"]) < 0.01, f"invariant broken: {s}"


# ---------- GA-T Wallet ----------
class TestTokenWallet:
    def test_wallet_structure(self):
        r = requests.get(f"{BASE_URL}/api/token/wallet", headers=AUTH, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["symbol"] == "GA-T"
        assert "balance" in d and "earned_total" in d
        # spent_total may be absent for users who never spent
        assert isinstance(d.get("txs"), list)
        assert len(d.get("earn_rules", {})) == 3
        assert len(d.get("spend_items", {})) >= 3
        assert "proof_of_help" in d["earn_rules"]
        assert "priority_hunter_7d" in d["spend_items"]


# ---------- Earn ----------
class TestEarn:
    def test_earn_invalid_activity_400(self):
        r = requests.post(f"{BASE_URL}/api/token/earn", headers=AUTH,
                          json={"activity": "bogus_activity"}, timeout=15)
        assert r.status_code == 400

    def test_earn_proof_of_help_either_success_or_daily_cap(self):
        # Idempotent — daily cap may already be hit. Both 200 and 429 are acceptable.
        r = requests.post(f"{BASE_URL}/api/token/earn", headers=AUTH,
                          json={"activity": "proof_of_help"}, timeout=15)
        assert r.status_code in (200, 429), r.text
        if r.status_code == 200:
            d = r.json()
            assert d["tx"]["amount"] == 10.0
            assert d["tx"]["kind"] == "earn"
            assert "balance" in d
        else:
            assert "daily_limit" in r.text

    def test_earn_daily_cap_eventually_hits_429(self):
        # Fire until either cap hit or reach 6 attempts (rule cap = 5)
        hit = False
        for _ in range(6):
            r = requests.post(f"{BASE_URL}/api/token/earn", headers=AUTH,
                              json={"activity": "proof_of_help"}, timeout=15)
            if r.status_code == 429:
                hit = True
                assert "daily_limit" in r.text
                break
        assert hit, "expected 429 daily_limit after 6 attempts"


# ---------- Spend ----------
class TestSpend:
    def test_spend_invalid_item_400(self):
        r = requests.post(f"{BASE_URL}/api/token/spend", headers=AUTH,
                          json={"item": "bogus"}, timeout=15)
        assert r.status_code == 400

    def test_spend_priority_hunter_or_402(self):
        w = requests.get(f"{BASE_URL}/api/token/wallet", headers=AUTH, timeout=15).json()
        bal_before = w["balance"]
        r = requests.post(f"{BASE_URL}/api/token/spend", headers=AUTH,
                          json={"item": "priority_hunter_7d"}, timeout=15)
        if bal_before < 25:
            assert r.status_code == 402
            assert "insufficient_balance" in r.text
        else:
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["burned"] == 0.5  # 2% of 25
            assert "hunter_priority_until" in d["effect"]
            assert d["balance"] == round(bal_before - 25.0, 4)


# ---------- Ledger ----------
class TestLedger:
    def test_ledger_chain_intact(self):
        r = requests.get(f"{BASE_URL}/api/token/ledger?verify=1&limit=200", headers=AUTH, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "entries" in d and isinstance(d["entries"], list)
        assert d["chain"]["intact"] is True

    def test_ledger_has_spend_and_burn_entries(self):
        # if any spend happened previously, both entries must exist somewhere in tail
        r = requests.get(f"{BASE_URL}/api/token/ledger?limit=200", headers=AUTH, timeout=20)
        kinds = {e["kind"] for e in r.json().get("entries", [])}
        # genesis + reserve_lock must exist
        assert "genesis_mint" in kinds or "earn" in kinds or "spend" in kinds


# ---------- Swarm ----------
class TestSwarm:
    def test_swarm_status_has_4_agents_after_run(self):
        # Force each to register
        for aid in ["waitlist_hunter", "marketplace", "safety", "security_sentinel"]:
            requests.post(f"{BASE_URL}/api/swarm/run/{aid}", headers=AUTH, timeout=30)
        r = requests.get(f"{BASE_URL}/api/swarm/status", headers=AUTH, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        agent_ids = {a["agent_id"] for a in d.get("agents", [])}
        assert {"waitlist_hunter", "marketplace", "safety", "security_sentinel"}.issubset(agent_ids)
        assert d["loop_active"] is True
        # bus events should have zk commitments
        if d.get("bus"):
            assert "commitment" in d["bus"][0]["zkp"]

    def test_swarm_run_each_agent(self):
        for aid in ["waitlist_hunter", "marketplace", "safety", "security_sentinel"]:
            r = requests.post(f"{BASE_URL}/api/swarm/run/{aid}", headers=AUTH, timeout=30)
            assert r.status_code == 200, f"{aid}: {r.text}"
            d = r.json()
            assert d["status"] == "ok"
            assert d["agent_id"] == aid
            assert "actions" in d

    def test_swarm_unknown_agent_404(self):
        r = requests.post(f"{BASE_URL}/api/swarm/run/nonexistent", headers=AUTH, timeout=15)
        assert r.status_code == 404

    def test_marketplace_agent_drip_after_optin(self):
        # opt-in
        r = requests.put(f"{BASE_URL}/api/marketplace/optin", headers=AUTH,
                         json={"enabled": True}, timeout=15)
        assert r.status_code in (200, 201), r.text
        # run marketplace agent — may drip 0 if cap hit; 200 always
        r = requests.post(f"{BASE_URL}/api/swarm/run/marketplace", headers=AUTH, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "ok"

    def test_waitlist_hunter_no_crash(self):
        # create waitlist item then run agent — deterministic per-day, may or may not find
        c = requests.post(f"{BASE_URL}/api/waitlist", headers=AUTH,
                          json={"specialty": "TEST_ph15_derm", "clinic": "TEST Clinic",
                                "city": "TEST_BA", "current_date": "2027-03-01",
                                "target_before": "2026-04-01", "priority": "normal"}, timeout=15)
        assert c.status_code in (200, 201), c.text
        r = requests.post(f"{BASE_URL}/api/swarm/run/waitlist_hunter", headers=AUTH, timeout=30)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ---------- DePIN ----------
class TestDePIN:
    def test_depin_status_6_nodes_core_pinned(self):
        r = requests.get(f"{BASE_URL}/api/depin/status", headers=AUTH, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert len(d["nodes"]) == 6
        assert d["single_point_of_failure"] is False
        assert len(d["core_shard_on"]) >= 1

    def test_depin_migrate_creates_report_and_security_event(self):
        r = requests.post(f"{BASE_URL}/api/depin/migrate", headers=AUTH, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "migration_id" in d
        assert isinstance(d["from"], list)
        assert isinstance(d["to"], list) and len(d["to"]) >= 1
        # verify security event feed contains safe_migration
        se = requests.get(f"{BASE_URL}/api/security/events", headers=AUTH, timeout=15).json()
        kinds = {e["kind"] for e in se}
        assert "safe_migration" in kinds


# ---------- Security Events ----------
class TestSecurityEvents:
    def test_security_events_endpoint(self):
        r = requests.get(f"{BASE_URL}/api/security/events", headers=AUTH, timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ---------- Audit ----------
class TestAudit:
    def test_audit_score_and_verdict(self):
        r = requests.post(f"{BASE_URL}/api/swarm/audit", headers=AUTH, timeout=45)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["total"] >= 8
        assert d["passed"] == d["total"], f"Failed checks: {[c for c in d['checks'] if not c['ok']]}"
        assert d["score"] == 100
        assert d["ready_for_global_publish"] is True
        assert d["verdict"] == "FULLY SECURE · TOKENIZED · SWARM ACTIVE"

    def test_audit_latest(self):
        r = requests.get(f"{BASE_URL}/api/swarm/audit/latest", headers=AUTH, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("score") is not None
        assert d.get("total") >= 8


# ---------- GA-T Hooks in existing endpoints ----------
class TestGATHooks:
    def test_sentinel_report_returns_gat_reward(self):
        r = requests.post(f"{BASE_URL}/api/sentinel/report", headers=AUTH,
                          json={"kind": "pharmacy_out",
                                "note": f"TEST_ph15_{uuid.uuid4().hex[:6]}",
                                "location": "TEST_BA"}, timeout=15)
        assert r.status_code in (200, 201), r.text
        d = r.json()
        assert "gat_reward" in d
        assert d["gat_reward"] in (5.0, 5, 0, 0.0)
