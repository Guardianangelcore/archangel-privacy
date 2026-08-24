# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
"""Phase 19: Grand Finale — Investor Demo Mode + submission readiness."""
import os
import requests

BASE_URL = (os.environ.get("EXPO_BACKEND_URL")
            or os.environ.get("EXPO_PUBLIC_BACKEND_URL")
            or "https://angel-os-1.preview.emergentagent.com").rstrip("/")
H1 = {"Authorization": "Bearer smoketok-fresh-2026"}      # founder
H2 = {"Authorization": "Bearer smoketok-fresh-2026-u2"}   # regular user


def _get(path, h=H1):
    return requests.get(f"{BASE_URL}/api{path}", headers=h, timeout=30)

def _post(path, h=H1, json=None):
    return requests.post(f"{BASE_URL}/api{path}", headers=h, json=json, timeout=30)


class TestDemoMode:
    def test_status_founder_flag(self):
        d = _get("/demo/status").json()
        assert d["is_founder"] is True and "demo_mode" in d
        d2 = _get("/demo/status", h=H2).json()
        assert d2["is_founder"] is False

    def test_non_founder_403(self):
        r = _post("/demo/toggle", h=H2, json={"enabled": True})
        assert r.status_code == 403

    def test_enable_seeds_presentation_data(self):
        r = _post("/demo/toggle", json={"enabled": True})
        assert r.status_code == 200
        seeded = r.json()["seeded"]
        assert "150 €" in seeded["refund_claim"]
        assert "slot_found" in seeded["waitlist_hunt"]
        assert "Tomáš" in seeded["family_pulse"]
        # visible in real dashboards:
        wl = _get("/waitlist").json()
        assert any(w.get("demo") and w.get("status") == "slot_found" for w in wl)
        claim = _post("/refunds/claim").json()
        assert any(i["estimated_refund_eur"] == 150 for i in claim["items"])
        assert _get("/demo/status").json()["demo_mode"] is True

    def test_disable_removes_all_demo_data(self):
        r = _post("/demo/toggle", json={"enabled": False})
        assert r.status_code == 200 and r.json()["demo_mode"] is False
        wl = _get("/waitlist").json()
        assert not any(w.get("demo") for w in wl)


class TestSubmissionReadiness:
    def test_stability_audit_green(self):
        d = _post("/swarm/audit").json()
        assert d["passed"] == d["total"], f"Failed: {[c for c in d['checks'] if not c['ok']]}"
        assert d["score"] == 100

    def test_stress_test_ready_for_publish(self):
        d = _post("/mosaic/stress-test").json()
        assert d["verdict"] == "READY FOR PUBLISH" and d["total_tps"] > 8000

    def test_seven_swarm_agents_online(self):
        d = _get("/swarm/status").json()
        assert len(d["agents"]) >= 7
