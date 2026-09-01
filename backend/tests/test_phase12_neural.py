# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""
Iteration 12 — NEURAL LINK (Jarvis orchestrator) integrity tests.
- unified /api/jarvis/context snapshot
- /api/jarvis/ask (Claude, Slovak) — 60s timeout
- /api/chains/{healing,safety,recovery,supply} — including loop-safety re-run
- /api/reports/weekly.pdf — Bearer + ?token= + unauth
- Stress: 3x rapid chain runs, no 5xx.
"""
import os
import time
import base64
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/")
TOKEN = "smoketok-fresh-2026"
HEAD = {"Authorization": f"Bearer {TOKEN}"}
JSON_HEAD = {**HEAD, "Content-Type": "application/json"}


# ---------- /jarvis/context ----------
class TestJarvisContext:
    def test_context_returns_unified_snapshot(self):
        r = requests.get(f"{BASE_URL}/api/jarvis/context", headers=HEAD, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert set(["health", "wealth", "safety"]).issubset(data.keys())
        assert "recovery" in data["health"]
        assert "solidarity_campaigns" in data["wealth"]
        assert "falls_7d" in data["safety"]

    def test_context_unauthorized(self):
        r = requests.get(f"{BASE_URL}/api/jarvis/context", timeout=15)
        assert r.status_code in (401, 403)


# ---------- /jarvis/ask ----------
class TestJarvisAsk:
    def test_ask_slovak_recovery_question(self):
        payload = {"question": "Aký je môj ďalší krok zotavenia?", "language": "sk"}
        r = requests.post(f"{BASE_URL}/api/jarvis/ask", headers=JSON_HEAD, json=payload, timeout=90)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("context_used") is True
        assert isinstance(data.get("answer"), str) and len(data["answer"]) > 20

    def test_ask_empty_400(self):
        r = requests.post(f"{BASE_URL}/api/jarvis/ask", headers=JSON_HEAD, json={"question": "  ", "language": "sk"}, timeout=15)
        assert r.status_code == 400


# ---------- helpers ----------
def _timeline_counts():
    r = requests.get(f"{BASE_URL}/api/calendar/timeline", headers=HEAD, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


def _upload_drop(title="Žiadanka ortopédia"):
    # get drop_id
    r = requests.get(f"{BASE_URL}/api/health-drop/me", headers=HEAD, timeout=15)
    assert r.status_code == 200
    drop_id = r.json()["drop_id"]
    fake_bin = b"%PDF-1.4\n%TEST\n1 0 obj<<>>endobj\ntrailer<<>>%%EOF"
    files = {"file": (f"drop_{int(time.time())}.bin", fake_bin, "application/octet-stream")}
    data = {
        "eph_pub": base64.b64encode(b"x" * 32).decode(),
        "nonce": base64.b64encode(b"n" * 12).decode(),
        "guardian_id": "smoke1",
        "sender_name": "Poliklinika Test",
        "doc_title": title,
        "orig_type": "application/pdf",
    }
    r2 = requests.post(f"{BASE_URL}/api/health-drop/{drop_id}/upload", files=files, data=data, timeout=30)
    assert r2.status_code == 200, r2.text
    return r2.json()["drop_doc_id"]


# ---------- healing chain + LOOP SAFETY ----------
class TestHealingChain:
    def test_healing_by_specialty_creates_waitlist_and_calendar(self):
        pre = _timeline_counts()
        pre_events = len(pre.get("events", []))

        r = requests.post(f"{BASE_URL}/api/chains/healing", headers=JSON_HEAD,
                          json={"specialty": "Reumatológia"}, timeout=45)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["chain"] == "healing"
        step_names = [s["step"] for s in data["steps"]]
        for expected in ["Waitlist Hunter", "Solidarity Hub", "Auto-Booker", "Health Calendar", "Sick Leave Manager"]:
            assert expected in step_names, f"missing step {expected} in {step_names}"

        # verify calendar event actually created with source=chain:healing
        post = _timeline_counts()
        assert len(post.get("events", [])) >= pre_events + 1
        chain_events = [e for e in post["events"] if e.get("source") == "chain:healing"]
        assert len(chain_events) >= 1, "No chain:healing event found in timeline"

        # verify waitlist has an item with status=booked for Reumatológia
        wl = requests.get(f"{BASE_URL}/api/waitlist", headers=HEAD, timeout=15)
        # /api/waitlist may or may not exist; if not, skip this side
        if wl.status_code == 200:
            items = wl.json() if isinstance(wl.json(), list) else wl.json().get("items", [])
            booked = [i for i in items if i.get("specialty") == "Reumatológia" and i.get("status") == "booked"]
            assert len(booked) >= 1

    def test_healing_loop_safety_second_run_skipped(self):
        """CRITICAL: re-running the same drop must NOT create duplicate booking/calendar entry."""
        drop_doc_id = _upload_drop("Žiadanka ortopédia")

        pre = _timeline_counts()
        pre_events = len(pre.get("events", []))

        r1 = requests.post(f"{BASE_URL}/api/chains/healing", headers=JSON_HEAD,
                           json={"drop_doc_id": drop_doc_id}, timeout=45)
        assert r1.status_code == 200, r1.text
        d1 = r1.json()
        # first run — Referral Bridge status ok
        assert d1["steps"][0]["step"] == "Referral Bridge"
        assert d1["steps"][0]["status"] == "ok"

        mid = _timeline_counts()
        mid_events = len(mid.get("events", []))
        assert mid_events == pre_events + 1, "First run must create exactly 1 calendar event"

        # Second run — must be skipped
        r2 = requests.post(f"{BASE_URL}/api/chains/healing", headers=JSON_HEAD,
                           json={"drop_doc_id": drop_doc_id}, timeout=45)
        assert r2.status_code == 200, r2.text
        d2 = r2.json()
        assert d2["steps"][0]["status"] == "skipped", f"Loop safety broken: {d2}"

        post = _timeline_counts()
        assert len(post.get("events", [])) == mid_events, "Second (skipped) run must NOT add calendar event"


# ---------- safety chain ----------
class TestSafetyChain:
    def test_safety_chain_creates_beacon(self):
        r = requests.post(f"{BASE_URL}/api/chains/safety", headers=JSON_HEAD,
                          json={"trigger": "fall"}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        step_names = [s["step"] for s in data["steps"]]
        assert "Legacy Module" in step_names
        assert "Emergency Loop" in step_names
        assert "Emergency Wallpaper" in step_names
        assert len(data["steps"]) >= 4


# ---------- recovery chain ----------
class TestRecoveryChain:
    def test_recovery_chain_outing_aware(self):
        r = requests.post(f"{BASE_URL}/api/chains/recovery", headers=JSON_HEAD,
                          json={}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # smoke user has outings 10-12 and 16-18 — summary should reference an outing window OR "TERAZ"/"vychádzku"
        summary = (data.get("summary") or "").lower()
        assert any(k in summary for k in ["vychádzk", "prechádzk", "cvič"])


# ---------- supply chain ----------
class TestSupplyChain:
    def test_supply_paralen(self):
        r = requests.post(f"{BASE_URL}/api/chains/supply", headers=JSON_HEAD,
                          json={"med_name": "Paralen"}, timeout=30)
        assert r.status_code == 200, r.text
        step_names = [s["step"] for s in r.json()["steps"]]
        assert "Pharmacy Hunter" in step_names
        assert "Solidarity Hub" in step_names
        assert "Skill Barter" in step_names
        assert "Logistics Engine" in step_names

    def test_supply_empty_med_name_400(self):
        r = requests.post(f"{BASE_URL}/api/chains/supply", headers=JSON_HEAD,
                          json={"med_name": "   "}, timeout=15)
        assert r.status_code == 400


# ---------- weekly PDF ----------
class TestWeeklyReport:
    def test_weekly_pdf_bearer(self):
        r = requests.get(f"{BASE_URL}/api/reports/weekly.pdf", headers=HEAD, timeout=30)
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_weekly_pdf_token_query(self):
        r = requests.get(f"{BASE_URL}/api/reports/weekly.pdf?token={TOKEN}", timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")

    def test_weekly_pdf_unauthorized(self):
        r = requests.get(f"{BASE_URL}/api/reports/weekly.pdf", timeout=15)
        assert r.status_code in (401, 403)


# ---------- stress / stability ----------
class TestChainStress:
    def test_three_rapid_chains_no_5xx(self):
        codes = []
        codes.append(requests.post(f"{BASE_URL}/api/chains/safety", headers=JSON_HEAD, json={"trigger": "manual"}, timeout=30).status_code)
        codes.append(requests.post(f"{BASE_URL}/api/chains/recovery", headers=JSON_HEAD, json={}, timeout=30).status_code)
        codes.append(requests.post(f"{BASE_URL}/api/chains/supply", headers=JSON_HEAD, json={"med_name": "Ibalgin"}, timeout=30).status_code)
        assert all(c == 200 for c in codes), codes

    def test_backend_still_up_after_stress(self):
        r = requests.get(f"{BASE_URL}/api/jarvis/context", headers=HEAD, timeout=15)
        assert r.status_code == 200
