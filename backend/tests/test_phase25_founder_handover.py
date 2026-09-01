# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
"""Phase 25 — FINAL HANDOVER: Founder's Toolkit + UHP partner regression.

Covers:
- GET /api/founder/toolkit (auth required) -> forecast/roadmap/release_package
- GET /api/founder/release/{doc} for 4 docs -> content+sha256, unknown->404, no-auth->401
- Regression: POST /api/uhp/partners/register (public) still works
- Regression: GET /api/uhp/capacity (auth) still returns >=1B
"""
import os
import hashlib
import uuid
import requests

BASE_URL = (os.environ.get("EXPO_PUBLIC_BACKEND_URL")
            or os.environ.get("EXPO_BACKEND_URL")
            or "https://physio-lang-fix.preview.emergentagent.com").rstrip("/")

TOKEN = "smoketok-fresh-handover"
H = {"Authorization": f"Bearer {TOKEN}"}
DOCS = ["README.md", "ARCHITECTURE.md", "API_SPEC.md", "LICENSE"]


class TestFounderToolkit:
    def test_toolkit_shape(self):
        r = requests.get(f"{BASE_URL}/api/founder/toolkit", headers=H, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # forecast
        assert "forecast" in data
        years = data["forecast"]["years"]
        assert isinstance(years, list) and len(years) == 5
        year_nums = [y["year"] for y in years]
        assert year_nums == [2026, 2027, 2028, 2029, 2030]
        for y in years:
            assert y["mrr_eur"] > 0
            assert y["arr_eur"] == y["mrr_eur"] * 12 or abs(y["arr_eur"] - y["mrr_eur"] * 12) <= 12
            assert y["gross_margin_pct"] == 87
        # assumptions
        a = data["forecast"]["assumptions"]
        assert a["guardian_tax_pct"] == 15
        assert "arpu_paid_eur_mo" in a and a["arpu_paid_eur_mo"] > 0
        assert set(a["tier_mix"].keys()) == {"guardian", "sentinel", "archangel"}
        # roadmap
        assert isinstance(data["roadmap"], list) and len(data["roadmap"]) == 8
        for item in data["roadmap"]:
            assert {"year", "era", "title", "detail"} <= set(item.keys())
        # release package
        docs = data["release_package"]["docs"]
        assert isinstance(docs, list) and len(docs) == 4
        names = {d["name"] for d in docs}
        assert names == set(DOCS)
        for d in docs:
            assert d["bytes"] > 0
            assert len(d["sha256"]) == 64

    def test_toolkit_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/founder/toolkit", timeout=30)
        assert r.status_code in (401, 403), r.text


class TestFounderRelease:
    def test_all_docs_return_content_and_sha256_matches(self):
        for name in DOCS:
            r = requests.get(f"{BASE_URL}/api/founder/release/{name}", headers=H, timeout=30)
            assert r.status_code == 200, f"{name}: {r.text}"
            j = r.json()
            assert j["name"] == name
            assert j["bytes"] > 0
            assert j["content"], f"{name} content empty"
            expected_sha = hashlib.sha256(j["content"].encode("utf-8")).hexdigest()
            assert expected_sha == j["sha256"], f"{name} sha256 mismatch"

    def test_unknown_doc_404(self):
        r = requests.get(f"{BASE_URL}/api/founder/release/UNKNOWN.md", headers=H, timeout=30)
        assert r.status_code == 404

    def test_no_auth_401(self):
        r = requests.get(f"{BASE_URL}/api/founder/release/README.md", timeout=30)
        assert r.status_code in (401, 403)


class TestUHPRegression:
    def test_partner_register_public(self):
        payload = {
            "org_name": f"TEST_QA-{uuid.uuid4().hex[:6]}",
            "org_type": "clinic",
            "country": "SK",
            "contact_email": "qa@handover.sk",
        }
        r = requests.post(f"{BASE_URL}/api/uhp/partners/register", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["partner_id"].startswith("uhp_")
        assert j["api_key"].startswith("uhpk_")
        assert len(j["hmac_secret"]) == 64
        assert j["protocol"] == "UHP/1.0"

    def test_capacity_over_1b(self):
        r = requests.get(f"{BASE_URL}/api/uhp/capacity", headers=H, timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["stream_capacity"] >= 1_000_000_000
        assert j["protocol"] == "UHP/1.0"
        assert "active_partners" in j
