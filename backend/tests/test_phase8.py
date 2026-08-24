# Copyright © 2026 Guardian Angel. All Rights Reserved.
# This source code and its logic are the sole property of Guardian Angel.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Iteration 7 — Survival & Trust module (Border/Wallpaper/Mental/Biometric-Will) + regression sanity.

Uses the pre-provisioned smoke user (token=smoketok-fresh-2026, valid 7 days, TOS accepted).
"""
import io
import os
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent.parent.parent / "frontend" / ".env")

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
TOKEN = "smoketok-fresh-2026"
H = {"Authorization": f"Bearer {TOKEN}"}


# ================== BORDER CROSSER ==================

class TestBorderCertificate:
    def test_certificate_json(self):
        r = requests.get(f"{BASE_URL}/api/border/certificate", headers=H, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "did" in body and body["did"]
        assert "holder" in body
        assert isinstance(body.get("medications"), list)
        assert "did_signature" in body and len(body["did_signature"]) == 64
        assert isinstance(body.get("languages"), list)
        assert len(body["languages"]) == 14, f"expected 14 langs got {len(body['languages'])}"
        codes = [lg["code"] for lg in body["languages"]]
        for expected in ("en", "sk", "cs", "de", "fr", "es", "it", "pl", "hu", "uk", "ru", "pt", "nl", "ro"):
            assert expected in codes, f"missing lang {expected}"

    def test_certificate_pdf_with_token_query(self):
        r = requests.get(f"{BASE_URL}/api/border/certificate.pdf", params={"token": TOKEN}, timeout=30)
        assert r.status_code == 200, r.text[:400]
        assert r.headers.get("content-type", "").startswith("application/pdf"), r.headers
        assert len(r.content) > 500, f"pdf too small: {len(r.content)} bytes"
        assert r.content[:4] == b"%PDF", "not a PDF file"

    def test_certificate_pdf_unauthorized(self):
        r = requests.get(f"{BASE_URL}/api/border/certificate.pdf", timeout=15)
        assert r.status_code in (401, 403), r.status_code


# ================== EMERGENCY WALLPAPER ==================

class TestFamilyWallpaper:
    def test_wallpaper_png_returns_image(self):
        r = requests.get(f"{BASE_URL}/api/family/wallpaper.png", params={"token": TOKEN}, timeout=30)
        assert r.status_code == 200, r.text[:400]
        assert r.headers.get("content-type", "").startswith("image/png"), r.headers
        # PNG magic + non-trivial size for 1080x1920 render
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG file"
        assert len(r.content) > 5_000, f"png too small: {len(r.content)} bytes"

    def test_wallpaper_png_unauthorized(self):
        r = requests.get(f"{BASE_URL}/api/family/wallpaper.png", timeout=15)
        assert r.status_code in (401, 403)


# ================== MENTAL FORTRESS ==================

class TestMentalTechniques:
    def test_techniques_shape_and_count(self):
        r = requests.get(f"{BASE_URL}/api/mental/techniques", headers=H, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        techniques = body.get("techniques")
        assert isinstance(techniques, list)
        assert len(techniques) == 6, f"expected 6 got {len(techniques)}"
        ids = [t["id"] for t in techniques]
        for expected in ("box", "grounding", "li4", "pc6", "yintang", "pmr"):
            assert expected in ids, f"missing technique {expected}"
        for t in techniques:
            assert t.get("tts_text"), f"missing tts_text for {t['id']}"
            assert isinstance(t.get("steps"), list) and len(t["steps"]) >= 3
        assert body.get("disclaimer") and "112" in body["disclaimer"]


# ================== BIOMETRIC WILL ==================

class TestBiometricWill:
    """Full CRUD lifecycle for biometric statement upload."""

    def test_reject_non_audio_video(self):
        # Upload a plain text file → should 400
        files = {"file": ("statement.txt", b"hello world", "text/plain")}
        r = requests.post(f"{BASE_URL}/api/legal/testament/biometric", headers=H, files=files, timeout=20)
        assert r.status_code == 400, r.text
        assert "audio" in r.text.lower() or "video" in r.text.lower()

    def test_upload_audio_returns_hashes(self):
        # Minimal fake audio bytes (not a real m4a, but content_type=audio/* is what matters)
        content = b"FAKEAUDIOBYTES" + os.urandom(256)
        files = {"file": ("statement.m4a", content, "audio/mp4")}
        r = requests.post(f"{BASE_URL}/api/legal/testament/biometric", headers=H, files=files, timeout=30)
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert body.get("sha256") and len(body["sha256"]) == 64
        assert body.get("ledger_hash") and len(body["ledger_hash"]) == 64
        assert body.get("media_type", "").startswith("audio/")
        assert body.get("size") == len(content)
        assert body.get("rec_id")

    def test_get_biometric_returns_current(self):
        r = requests.get(f"{BASE_URL}/api/legal/testament/biometric", headers=H, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("sha256"), "expected latest recording to be present"
        assert body.get("ledger_hash")

    def test_get_file_stream_with_token(self):
        r = requests.get(f"{BASE_URL}/api/legal/testament/biometric/file",
                         params={"token": TOKEN}, timeout=30)
        assert r.status_code == 200, r.text[:200]
        assert r.headers.get("content-type", "").startswith("audio/")
        assert len(r.content) > 0

    def test_delete_biometric(self):
        r = requests.delete(f"{BASE_URL}/api/legal/testament/biometric", headers=H, timeout=15)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_delete_again_404(self):
        r = requests.delete(f"{BASE_URL}/api/legal/testament/biometric", headers=H, timeout=15)
        assert r.status_code == 404


# ================== REGRESSION SANITY ==================

class TestRegressionSanity:
    def test_auth_me(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=H, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        user = body.get("user") or body
        assert user.get("user_id") == "smoketest-user-1"

    def test_waitlist_get(self):
        r = requests.get(f"{BASE_URL}/api/waitlist", headers=H, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        # accept either list or object-with-list
        if isinstance(body, dict):
            assert isinstance(body.get("items") or body.get("waitlist") or [], list)
        else:
            assert isinstance(body, list)

    def test_physio_session(self):
        # POST session with minimal payload — accept 200/201/422 (schema-dependent) but never 500
        r = requests.post(f"{BASE_URL}/api/physio/session", headers=H,
                          json={"complaint": "back pain", "language": "sk"}, timeout=60)
        assert r.status_code < 500, r.text[:400]

    def test_scam_check(self):
        r = requests.post(f"{BASE_URL}/api/scam/check", headers=H,
                          json={"text": "Vyhrali ste 10000 EUR. Kliknite: http://scam.example",
                                "language": "sk"}, timeout=45)
        assert r.status_code == 200, r.text[:400]
        # response should be JSON with some verdict/score
        body = r.json()
        assert isinstance(body, dict)

    def test_legal_tos(self):
        r = requests.get(f"{BASE_URL}/api/legal/tos", headers=H, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("version"), body
