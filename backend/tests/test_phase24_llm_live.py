"""Phase 24 LIVE LLM smoke tests — Twin Simulate + Blueprint Train/Ask.
Focus: exercise gpt-5.4 endpoints not covered by phase24 fake-LLM pytest suite.
Uses smoketest-user-1 (has memories) and falls back to test-token-abc.
"""
import os
import requests
import pytest

BASE = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/")
TOKEN = "test-token-abc"
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


# ---------- Bio-Digital Twin (LLM) ----------
def test_twin_simulate_ibuprofen():
    r = requests.post(f"{BASE}/api/twin/simulate",
                      headers=H, json={"treatment": "Ibuprofen 400 mg"}, timeout=90)
    assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
    body = r.json()
    assert "result" in body, body
    res = body["result"]
    assert 0 <= int(res["compatibility_pct"]) <= 100
    assert res["verdict"] in ("simulate_pass", "caution", "simulate_fail")
    assert isinstance(res.get("risks"), list)
    assert isinstance(res.get("interactions"), list)


# ---------- Personality Blueprint (LLM) ----------
def test_blueprint_train_then_ask():
    # ensure memories exist — attempt one chat if needed
    tr = requests.post(f"{BASE}/api/legacy/blueprint/train", headers=H, timeout=90)
    if tr.status_code == 400:
        # bootstrap: talk to Jarvis once, then retry
        requests.post(f"{BASE}/api/agent/chat", headers=H,
                      json={"text": "Volám sa Jaroslav, mám 68 rokov a vždy robím rozhodnutia po dlhom uvažovaní s manželkou."},
                      timeout=60)
        tr = requests.post(f"{BASE}/api/legacy/blueprint/train", headers=H, timeout=90)
    assert tr.status_code == 200, f"train {tr.status_code} {tr.text[:400]}"
    doc = tr.json()
    bp = doc.get("blueprint", {})
    assert "tone" in bp and isinstance(bp["tone"], str) and len(bp["tone"]) > 5
    assert isinstance(bp.get("values"), list)
    assert isinstance(bp.get("decision_rules"), list)

    q = requests.post(f"{BASE}/api/legacy/blueprint/ask", headers=H,
                     json={"question": "Ako mám rozhodnúť o oprave strechy?", "asker_name": "Tomáš"},
                     timeout=90)
    assert q.status_code == 200, f"ask {q.status_code} {q.text[:400]}"
    ans = q.json()
    assert ans.get("framing") == "digital_echo"
    txt = ans.get("answer", "")
    assert isinstance(txt, str) and len(txt) > 20
    # opening should reference digital-echo framing (Slovak). Loose check for any of the expected words.
    lower = txt.lower()
    assert any(w in lower for w in ["digitálna", "digitálny", "ozvena", "echo", "nie som"]), \
        f"opening framing missing: {txt[:200]}"


# ---------- Regression: swarm status includes new agents ----------
def test_swarm_status_has_new_agents():
    r = requests.get(f"{BASE}/api/swarm/status", headers=H, timeout=15)
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    # find agents list
    agents = data.get("agents", data)
    names = []
    if isinstance(agents, list):
        for a in agents:
            names.append(a.get("agent_id") or a.get("name") or a.get("id"))
    elif isinstance(agents, dict):
        names = list(agents.keys())
    joined = " ".join(str(n) for n in names).lower()
    assert "data_broker" in joined, f"data_broker missing in {names}"
    assert "gbi_distributor" in joined, f"gbi_distributor missing in {names}"
