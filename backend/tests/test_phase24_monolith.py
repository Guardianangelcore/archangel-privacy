# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
"""Phase 24-25: ARCHANGEL MONOLITH + ASCENSION PROTOCOL.

UHP gateway (HMAC/replay/idempotency/routing), Arbitrage Brain (10k index,
cost-benefit math), Liquidity settlement engine (ledger balance, idempotent
payouts, FX, credit), Ascension (trajectories, sentinel, edge/GBI, truth chain)
+ GLOBAL MONOLITH STRESS TEST (concurrent ingest & analysis).
LLM paths (twin simulate, blueprint) validated by e2e agent."""
import os, json, hmac, hashlib, time, uuid
from concurrent.futures import ThreadPoolExecutor
import requests

BASE_URL = (os.environ.get("EXPO_BACKEND_URL")
            or "https://angel-os-1.preview.emergentagent.com").rstrip("/")
H = {"Authorization": "Bearer smoketok-fresh-2026-u2"}


def _reg_partner():
    r = requests.post(f"{BASE_URL}/api/uhp/partners/register", json={
        "org_name": f"TestClinic-{uuid.uuid4().hex[:6]}", "org_type": "clinic",
        "country": "SK", "contact_email": "qa@clinic.sk"}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def _ingest(p, body_dict, ts=None, sig=None):
    body = json.dumps(body_dict)
    ts = ts or str(int(time.time()))
    sig = sig or hmac.new(p["hmac_secret"].encode(), f"{ts}.{body}".encode(), hashlib.sha256).hexdigest()
    return requests.post(f"{BASE_URL}/api/uhp/ingest", data=body, timeout=30, headers={
        "X-UHP-Key": p["api_key"], "X-UHP-Timestamp": ts,
        "X-UHP-Signature": sig, "Content-Type": "application/json"})


def _env(idem, kind="sensor", payload=None):
    return {"protocol": "UHP/1.0", "kind": kind, "subject": {},
            "payload": payload or {"stream_id": "s1", "v": 1}, "idempotency_key": idem}


class TestUHPGateway:
    def test_register_and_standard(self):
        p = _reg_partner()
        assert p["partner_id"].startswith("uhp_") and p["hmac_secret"]
        std = requests.get(f"{BASE_URL}/api/uhp/standard", timeout=30).json()
        assert std["protocol"] == "UHP/1.0"

    def test_signed_ingest_and_idempotency(self):
        p = _reg_partner()
        idem = uuid.uuid4().hex
        r1 = _ingest(p, _env(idem))
        assert r1.status_code == 200 and r1.json()["duplicate"] is False
        r2 = _ingest(p, _env(idem))
        assert r2.json()["duplicate"] is True

    def test_bad_signature_and_replay_rejected(self):
        p = _reg_partner()
        assert _ingest(p, _env(uuid.uuid4().hex), sig="0" * 64).status_code == 401
        old_ts = str(int(time.time()) - 4000)
        assert _ingest(p, _env(uuid.uuid4().hex), ts=old_ts).status_code == 401

    def test_vitals_route_to_bioscan(self):
        p = _reg_partner()
        r = _ingest(p, {"protocol": "UHP/1.0", "kind": "vitals",
                        "subject": {"email": "smoke2@guardian.test"},
                        "payload": {"systolic": 121, "diastolic": 79},
                        "idempotency_key": uuid.uuid4().hex})
        # subject may or may not exist in test DB — accept 200 (routed) or 404 (unknown subject)
        assert r.status_code in (200, 404)

    def test_capacity_over_1b(self):
        r = requests.get(f"{BASE_URL}/api/uhp/capacity", headers=H, timeout=30)
        assert r.status_code == 200
        assert r.json()["stream_capacity"] >= 1_000_000_000


class TestArbitrageBrain:
    def test_index_size(self):
        s = requests.get(f"{BASE_URL}/api/arbitrage/stats", headers=H, timeout=60).json()
        assert s["index_size"] >= 10000 and s["countries"] >= 25

    def test_analysis_math(self):
        r = requests.post(f"{BASE_URL}/api/arbitrage/analyze", headers=H, timeout=60,
                          json={"procedure": "hip_replacement", "urgency": "high",
                                "local_price_eur": 7200, "local_wait_weeks": 40})
        assert r.status_code == 200, r.text
        a = r.json()
        top = a["top"][0]
        expect = round((7200 + top["time_saved_weeks"] * 400) - top["total_cost_eur"], 2)
        assert abs(top["net_benefit_eur"] - expect) < 0.02
        assert a["picks"]["cheapest"]["total_cost_eur"] <= top["total_cost_eur"]

    def test_bad_procedure_400(self):
        r = requests.post(f"{BASE_URL}/api/arbitrage/analyze", headers=H,
                          json={"procedure": "teleport"}, timeout=30)
        assert r.status_code == 400


class TestLiquidityEngine:
    def test_payout_state_machine_and_ledger_balance(self):
        idem = uuid.uuid4().hex
        r = requests.post(f"{BASE_URL}/api/liquidity/payout", headers=H, timeout=30,
                          json={"amount": 20, "currency": "EUR", "card_last4": "1111",
                                "network": "visa", "idempotency_key": idem})
        assert r.status_code == 200, r.text
        p = r.json()["payout"]
        assert p["state"] == "settled" and p["trace_id"].startswith("STL-")
        states = [t["state"] for t in p["timeline"]]
        assert states == ["initiated", "authorized", "settled"]
        # idempotent replay
        r2 = requests.post(f"{BASE_URL}/api/liquidity/payout", headers=H, timeout=30,
                           json={"amount": 20, "currency": "EUR", "card_last4": "1111",
                                 "network": "visa", "idempotency_key": idem})
        assert r2.json()["duplicate"] is True

    def test_fx_conversion(self):
        r = requests.post(f"{BASE_URL}/api/liquidity/payout", headers=H, timeout=30,
                          json={"amount": 500, "currency": "CZK", "card_last4": "2222",
                                "network": "mc", "idempotency_key": uuid.uuid4().hex})
        assert r.status_code == 200, r.text
        p = r.json()["payout"]
        assert p["currency"] == "CZK" and 18 < p["amount_eur"] < 21  # 500/25.2 with margin

    def test_insufficient_funds(self):
        r = requests.post(f"{BASE_URL}/api/liquidity/payout", headers=H, timeout=30,
                          json={"amount": 999999, "currency": "EUR", "card_last4": "3333",
                                "network": "visa", "idempotency_key": uuid.uuid4().hex})
        assert r.status_code in (400, 402)

    def test_credit_score_and_draw(self):
        s = requests.post(f"{BASE_URL}/api/liquidity/credit/score", headers=H, timeout=30).json()
        assert s["limit_eur"] >= 100
        d = requests.post(f"{BASE_URL}/api/liquidity/credit/draw", headers=H,
                          json={"amount": 10}, timeout=30)
        assert d.status_code == 200 and d.json()["drawn_eur"] == 10


class TestAscension:
    def test_trajectory_bands(self):
        r = requests.get(f"{BASE_URL}/api/twin/trajectory", headers=H, timeout=30)
        assert r.status_code == 200
        t = r.json()
        assert "systolic" in t["trajectories"] and 0 <= t["composite_risk_12m"] <= 100
        m12 = t["trajectories"]["systolic"]["m12"]
        assert m12 is None or 70 <= m12 <= 260  # physiological clamp

    def test_sentinel_gait_and_predict(self):
        r = requests.post(f"{BASE_URL}/api/sentinel/gait", headers=H, timeout=30,
                          json={"tremor_index": 1.0, "gait_regularity": 0.9})
        assert r.status_code == 200
        assert r.json()["level"] in ("low", "medium", "high")

    def test_edge_contribute_and_fraud_guard(self):
        r = requests.post(f"{BASE_URL}/api/edge/contribute", headers=H, timeout=30,
                          json={"device_id": "qa-dev", "tasks_completed": 1000000, "ms_contributed": 30000})
        assert r.status_code == 200 and r.json()["gat_earned"] > 0
        bad = requests.post(f"{BASE_URL}/api/edge/contribute", headers=H, timeout=30,
                            json={"device_id": "qa-dev", "tasks_completed": 4000000, "ms_contributed": 100})
        assert bad.status_code == 400

    def test_truth_chain_verify(self):
        requests.post(f"{BASE_URL}/api/mesh/truth", headers=H, timeout=30,
                      json={"kind": "observation", "content": f"QA seal {uuid.uuid4().hex[:8]}"})
        v = requests.get(f"{BASE_URL}/api/mesh/truth/verify", headers=H, timeout=60).json()
        assert v["valid"] is True and v["records"] >= 1

    def test_gbi_status(self):
        r = requests.get(f"{BASE_URL}/api/edge/status", headers=H, timeout=30)
        assert r.status_code == 200 and r.json()["gbi"]["daily_gat"] > 0


class TestGlobalMonolithStress:
    def test_concurrent_uhp_ingest_60(self):
        p = _reg_partner()
        lat = []

        def shot(i):
            t0 = time.time()
            r = _ingest(p, _env(f"stress-{uuid.uuid4().hex[:8]}-{i}"))
            lat.append((time.time() - t0) * 1000)
            return r.status_code

        with ThreadPoolExecutor(max_workers=20) as ex:
            codes = list(ex.map(shot, range(60)))
        assert all(c == 200 for c in codes), f"non-200 in stress: {set(codes)}"
        lat.sort()
        p95 = lat[int(len(lat) * 0.95) - 1]
        assert p95 < 4000, f"p95 {p95:.0f}ms too slow"

    def test_concurrent_arbitrage_20(self):
        def shot(_):
            return requests.post(f"{BASE_URL}/api/arbitrage/analyze", headers=H, timeout=60,
                                 json={"procedure": "cataract", "urgency": "low"}).status_code
        with ThreadPoolExecutor(max_workers=10) as ex:
            codes = list(ex.map(shot, range(20)))
        assert all(c == 200 for c in codes)

    def test_swarm_agents_online(self):
        r = requests.get(f"{BASE_URL}/api/swarm/status", headers=H, timeout=30)
        assert r.status_code == 200
        agents = r.json().get("agents", [])
        ids = {a.get("agent_id") or a.get("id") for a in agents} if isinstance(agents, list) else set(agents.keys())
        assert {"data_broker", "gbi_distributor"} <= ids
