# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
"""Phase 21: ULTRA MODE — UI/UX Revolution backend: Guardian Lens, Voice
Liveness, Clinic Sync (Doctor Link), flexible med slots (Angel Mode 2.0).

NOTE: Real vision/STT calls (LLM credits) are validated manually; here we
test contracts, validation and the full Clinic Sync flow."""
import os
import requests

BASE_URL = (os.environ.get("EXPO_BACKEND_URL")
            or os.environ.get("EXPO_PUBLIC_BACKEND_URL")
            or "https://guardian-vault-13.preview.emergentagent.com").rstrip("/")
H1 = {"Authorization": "Bearer smoketok-fresh-2026"}
H2 = {"Authorization": "Bearer smoketok-fresh-2026-u2"}


def _get(path, h=H1):
    return requests.get(f"{BASE_URL}/api{path}", headers=h, timeout=30)

def _post(path, h=H1, json=None, **kw):
    return requests.post(f"{BASE_URL}/api{path}", headers=h, json=json, timeout=60, **kw)

def _delete(path, h=H1):
    return requests.delete(f"{BASE_URL}/api{path}", headers=h, timeout=30)


class TestClinicSync:
    def test_full_handshake_beam_flow(self):
        sess = _post("/clinic-sync/session", h=H2).json()
        assert sess["status"] == "waiting" and len(sess["code"]) == 6
        assert sess["qr_payload"] == f"GA-CLINIC-SYNC|{sess['code']}"
        # doctor-side beam (public, no auth)
        r = requests.post(f"{BASE_URL}/api/clinic-sync/beam/{sess['code']}", json={
            "clinic_name": "Test Klinika", "doctor_name": "MUDr. Test",
            "title": "Testovací nález", "report_text": "Pacient v dobrom stave, kontrola o rok."}, timeout=30)
        assert r.status_code == 200, r.text
        beamed = r.json()
        assert beamed["beamed"] is True
        # session shows received doc
        st = _get("/clinic-sync/session", h=H2).json()
        assert st["status"] == "received"
        assert any(d["doc_id"] == beamed["doc_id"] for d in st["received_docs"])
        # document landed in the vault
        docs = _get("/vault/documents", h=H2).json()
        mine = next((d for d in docs if d["doc_id"] == beamed["doc_id"]), None)
        assert mine and mine["title"].startswith("🏥")
        _delete(f"/vault/documents/{beamed['doc_id']}", h=H2)

    def test_beam_invalid_code(self):
        r = requests.post(f"{BASE_URL}/api/clinic-sync/beam/XXXXXX", json={
            "clinic_name": "X", "title": "Y", "report_text": "Z" * 20}, timeout=30)
        assert r.status_code == 404

    def test_simulate_beam_requires_session(self):
        # exhaust any active session first
        _post("/clinic-sync/session", h=H2)
        _post("/clinic-sync/simulate-beam", h=H2, json={})
        r = _post("/clinic-sync/simulate-beam", h=H2, json={})
        assert r.status_code == 404  # session already consumed (status=received)

    def test_radar_simulated(self):
        d = _get("/clinic-sync/radar").json()
        assert d["simulated"] is True and 2 <= len(d["nearby"]) <= 4
        assert all("clinic" in n and "distance_m" in n for n in d["nearby"])


class TestMedSlots:
    def test_slots_with_times(self):
        r = _post("/meds/reminders", json={"name": "TEST Vitamín D", "dose": "1 tbl",
                                           "times": ["08:00", "22:00"], "slots": ["breakfast", "night"]})
        assert r.status_code == 200, r.text
        rem = r.json()
        assert rem["slots"] == ["breakfast", "night"] and rem["times"] == ["08:00", "22:00"]
        _delete(f"/meds/reminders/{rem['reminder_id']}")

    def test_as_needed_without_times(self):
        r = _post("/meds/reminders", json={"name": "TEST Ibalgin", "times": [], "slots": ["as_needed"]})
        assert r.status_code == 200, r.text
        rem = r.json()
        assert rem["times"] == [] and rem["slots"] == ["as_needed"]
        _delete(f"/meds/reminders/{rem['reminder_id']}")

    def test_no_times_no_slots_rejected(self):
        assert _post("/meds/reminders", json={"name": "X", "times": [], "slots": []}).status_code == 400


class TestGuardianLensContracts:
    def test_analyze_rejects_non_image(self):
        r = _post("/lens/analyze", files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")})
        assert r.status_code == 400

    def test_analyze_rejects_empty(self):
        r = _post("/lens/analyze", files={"file": ("a.jpg", b"", "image/jpeg")})
        assert r.status_code == 400

    def test_analyze_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/lens/analyze",
                          files={"file": ("a.jpg", b"xx", "image/jpeg")}, timeout=30)
        assert r.status_code == 401

    def test_history(self):
        d = _get("/lens/history").json()
        assert "scans" in d

    def test_save_to_vault_unknown_scan(self):
        assert _post("/lens/nonexistent/save-to-vault").status_code == 404


class TestVoiceLiveness:
    def test_rejects_empty_audio(self):
        r = _post("/voice/liveness", files={"file": ("a.m4a", b"", "audio/mp4")})
        assert r.status_code == 400

    def test_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/voice/liveness",
                          files={"file": ("a.m4a", b"xx", "audio/mp4")}, timeout=30)
        assert r.status_code == 401
