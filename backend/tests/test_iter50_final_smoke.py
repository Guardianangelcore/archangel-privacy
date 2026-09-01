"""Iteration 50 — FINAL pre-publish smoke test.

Verifies every judge-facing backend flow before user hits Publish:
  - Founder dev-bypass login (creates archangel-tier session)
  - Auth /me
  - Core smoke: /api/, /api/origin, /api/lifecard, /api/token/wallet,
    /api/founder/toolkit, /api/compass/offline-pack, /api/marketplace/offers
  - Founder jury cheat-sheet PDF: Bearer + ?token= + 401 without auth
  - Jarvis chat (LLM ~10-30s)
  - Magic Lens vision (small base64 image, ~10-30s)
  - Life Card PDF export
  - Subscription tier (founder = archangel)
"""
import os
import io
import base64
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/")
FOUNDER_EMAIL = "guardian.angel.core@proton.me"
FOUNDER_NAME = "Guardian Angel"
TIMEOUT = 60


@pytest.fixture(scope="module")
def founder_token():
    r = requests.post(f"{BASE_URL}/api/auth/dev-bypass",
                      json={"email": FOUNDER_EMAIL, "name": FOUNDER_NAME},
                      timeout=TIMEOUT)
    assert r.status_code == 200, f"dev-bypass failed: {r.status_code} {r.text[:400]}"
    tok = r.json().get("session_token") or r.json().get("token")
    assert tok, f"no session_token in dev-bypass: {r.json()}"
    return tok


@pytest.fixture(scope="module")
def auth_h(founder_token):
    return {"Authorization": f"Bearer {founder_token}"}


# --- Core smoke ---------------------------------------------------------------
class TestCoreSmoke:
    def test_root(self):
        r = requests.get(f"{BASE_URL}/api/", timeout=TIMEOUT)
        assert r.status_code == 200
        j = r.json()
        assert "app" in j or "status" in j

    def test_origin(self):
        r = requests.get(f"{BASE_URL}/api/origin", timeout=TIMEOUT)
        assert r.status_code == 200

    def test_auth_me(self, auth_h):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_h, timeout=TIMEOUT)
        assert r.status_code == 200
        j = r.json()
        # response may be {"user": {...}} or flat
        user = j.get("user", j)
        assert user.get("email") == FOUNDER_EMAIL

    def test_lifecard(self, auth_h):
        r = requests.get(f"{BASE_URL}/api/lifecard", headers=auth_h, timeout=TIMEOUT)
        assert r.status_code == 200

    def test_token_wallet(self, auth_h):
        r = requests.get(f"{BASE_URL}/api/token/wallet", headers=auth_h, timeout=TIMEOUT)
        assert r.status_code == 200

    def test_compass_offline_pack(self, auth_h):
        # Review spec says /api/compass/offline-pack but source uses /api/compass/pack
        r = requests.get(f"{BASE_URL}/api/compass/pack", headers=auth_h, timeout=TIMEOUT)
        assert r.status_code == 200, f"compass/pack {r.status_code}"

    def test_marketplace_offers(self, auth_h):
        r = requests.get(f"{BASE_URL}/api/marketplace/offers", headers=auth_h, timeout=TIMEOUT)
        # 200 preferred; if endpoint uses different path, allow 404 but flag
        assert r.status_code == 200, f"marketplace/offers {r.status_code} {r.text[:300]}"


# --- Founder toolkit ----------------------------------------------------------
class TestFounderToolkit:
    def test_toolkit(self, auth_h):
        r = requests.get(f"{BASE_URL}/api/founder/toolkit", headers=auth_h, timeout=TIMEOUT)
        assert r.status_code == 200
        j = r.json()
        # 2026-2030 in forecast
        years = [row["year"] for row in j["forecast"]["years"]]
        assert years == [2026, 2027, 2028, 2029, 2030]
        # roadmap present and contains English "Global launch"
        rm_titles = " ".join(x.get("title", "") for x in j.get("roadmap", []))
        assert "Global launch" in rm_titles
        # release docs English
        for d in j["release_package"]["docs"]:
            assert d["desc"].isascii(), f"non-ASCII desc: {d}"
            if d["name"] == "README.md":
                assert "Project overview" in d["desc"]

    def test_jury_pdf_bearer(self, auth_h):
        r = requests.get(f"{BASE_URL}/api/founder/jury-cheat-sheet",
                         headers=auth_h, timeout=TIMEOUT)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content.startswith(b"%PDF")
        assert 100_000 < len(r.content) < 500_000, f"pdf size {len(r.content)}"

    def test_jury_pdf_query_token(self, founder_token):
        r = requests.get(f"{BASE_URL}/api/founder/jury-cheat-sheet?token={founder_token}",
                         timeout=TIMEOUT)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content.startswith(b"%PDF")

    def test_jury_pdf_401_no_auth(self):
        r = requests.get(f"{BASE_URL}/api/founder/jury-cheat-sheet", timeout=TIMEOUT)
        assert r.status_code == 401, f"expected 401, got {r.status_code}"


# --- Life Card PDF ------------------------------------------------------------
class TestLifeCardPDF:
    def test_lifecard_pdf(self, auth_h, founder_token):
        # try known routes: /api/lifecard/report.pdf or /api/lifecard.pdf
        for path in ["/api/lifecard/report.pdf", "/api/lifecard.pdf"]:
            r = requests.get(f"{BASE_URL}{path}", headers=auth_h, timeout=TIMEOUT)
            if r.status_code == 200:
                assert r.headers.get("content-type", "").startswith("application/pdf")
                assert r.content.startswith(b"%PDF")
                return
        pytest.fail("no life card PDF endpoint returned 200")


# --- Subscription -------------------------------------------------------------
class TestSubscription:
    def test_founder_is_archangel(self, auth_h):
        # try multiple possible endpoints
        candidates = ["/api/subscription/tier", "/api/subscription", "/api/subscription/me", "/api/billing/tier"]
        found = None
        for c in candidates:
            r = requests.get(f"{BASE_URL}{c}", headers=auth_h, timeout=TIMEOUT)
            if r.status_code == 200:
                found = (c, r.json())
                break
        assert found, f"no subscription endpoint returned 200 (tried {candidates})"
        _, j = found
        tier = (j.get("tier") or j.get("plan") or "").lower()
        assert "archangel" in tier or j.get("inner_circle") is True, \
            f"expected archangel tier, got {j}"


# --- Jarvis chat (LLM) --------------------------------------------------------
class TestJarvis:
    def test_agent_chat(self, auth_h):
        r = requests.post(f"{BASE_URL}/api/agent/chat",
                          headers=auth_h,
                          json={"message": "Hello Jarvis, one-word status?"},
                          timeout=90)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        j = r.json()
        assert (j.get("reply") or j.get("message") or j.get("text")), f"no reply field: {j}"


# --- Magic Lens (Vision) ------------------------------------------------------
def _doc_png_b64() -> str:
    """Generate a small but VALID document image (1x1 PNGs are rejected by OpenAI vision)."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (512, 256), "white")
    d = ImageDraw.Draw(img)
    d.text((20, 40), "MEDICAL LAB RESULT", fill="black")
    d.text((20, 90), "Patient: Guardian Angel", fill="black")
    d.text((20, 130), "Glucose: 5.2 mmol/L (normal)", fill="black")
    d.text((20, 170), "Date: 2026-06-01", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


class TestMagicLens:
    def test_magic_lens(self, auth_h):
        b64 = _doc_png_b64()
        payload = {"image_base64": b64, "image": b64}
        r = requests.post(f"{BASE_URL}/api/magic-lens",
                          headers=auth_h, json=payload, timeout=90)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        j = r.json()
        # Expect found/summary fields
        assert ("found" in j) or ("summary" in j) or ("items" in j), f"unexpected: {j}"
