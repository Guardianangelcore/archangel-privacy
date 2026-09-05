# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""FOUNDER'S TOOLKIT — investor demo backend: high-end financial forecast,
22nd-century roadmap and the GitHub Release Package (README / ARCHITECTURE /
API_SPEC / private LICENSE) served from /app/release_package for the
competition submission. Readable by any authenticated user (investor demo)."""
from fastapi import HTTPException, Header
from typing import Optional
from pathlib import Path
import hashlib

from core import api, get_current_user, _auth_pdf, _pdf_response

RELEASE_DIR = Path(__file__).resolve().parents[2] / "release_package"
RELEASE_DOCS = {
    "README.md": "Project overview, modules, quickstart, quality",
    "ARCHITECTURE.md": "System architecture, subsystems, data model",
    "API_SPEC.md": "API specification + UHP/1.0 protocol with HMAC signing",
    "LICENSE": "Private proprietary license (evaluation grant)",
}

# ---- Financial forecast (deterministic, tier-mix driven) --------------------
TIER_MIX = {"guardian": (9.0, 0.80), "sentinel": (99.0, 0.17), "archangel": (299.0, 0.03)}
ARPU_PAID = round(sum(p * w for p, w in TIER_MIX.values()), 2)  # blended €/mo per paid user
GUARDIAN_TAX = 0.15  # hard-coded 15 % take on marketplace + gig GMV

FORECAST_YEARS = [
    # (year, total_users, paid_conversion, marketplace_gmv_eur_per_user_mo)
    (2026, 12_000, 0.05, 1.5),
    (2027, 85_000, 0.06, 2.5),
    (2028, 420_000, 0.07, 3.5),
    (2029, 1_600_000, 0.08, 4.5),
    (2030, 5_000_000, 0.09, 5.5),
]


def _forecast_rows():
    rows = []
    for year, users, conv, gmv in FORECAST_YEARS:
        paid = int(users * conv)
        sub_mrr = paid * ARPU_PAID
        tax_mrr = users * gmv * GUARDIAN_TAX
        mrr = sub_mrr + tax_mrr
        rows.append({
            "year": year,
            "users": users,
            "paid_users": paid,
            "subscription_mrr_eur": round(sub_mrr),
            "guardian_tax_mrr_eur": round(tax_mrr),
            "mrr_eur": round(mrr),
            "arr_eur": round(mrr * 12),
            "gross_margin_pct": 87,
        })
    return rows


ROADMAP = [
    {"year": "2026 Q3", "era": "LAUNCH", "title": "Global launch",
     "detail": "iOS/Android builds, UHP pilot SK/CZ — first 50 partner clinics, Investor Demo Mode."},
    {"year": "2027", "era": "RAILS", "title": "Real settlement rails",
     "detail": "Visa Direct / Mastercard Send replace SimulatedRails; S2 cross-border arbitrage fully automated."},
    {"year": "2028", "era": "GRID", "title": "Sentinel Grid goes live",
     "detail": "BLE mesh + satellite nano-packets on real hardware; 1M+ concurrent sensor streams."},
    {"year": "2030", "era": "TWIN", "title": "Certified Bio-Digital Twin",
     "detail": "EU MDR class IIa — simulating treatment BEFORE dosing becomes the standard of care."},
    {"year": "2035", "era": "GBI", "title": "Living currency at national scale",
     "detail": "GA-T Guardian Basic Income — data dividends for millions; sovereign ownership of health data."},
    {"year": "2040", "era": "MESH", "title": "Quantum network",
     "detail": "Post-quantum cryptography (Kyber/Dilithium) everywhere; Collective Truth ledger as public infrastructure."},
    {"year": "2075", "era": "ECHO", "title": "Cognitive handover",
     "detail": "Legally recognized digital echoes — the Personality Blueprint carries wisdom across generations."},
    {"year": "2100+", "era": "ARCHANGEL", "title": "The 22nd-century standard",
     "detail": "UHP as the default protocol of human health sovereignty — Archangel OS on every device."},
]


@api.get("/founder/toolkit")
async def founder_toolkit(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    docs = []
    for name, desc in RELEASE_DOCS.items():
        p = RELEASE_DIR / name
        if p.exists():
            raw = p.read_bytes()
            docs.append({"name": name, "desc": desc, "bytes": len(raw),
                         "sha256": hashlib.sha256(raw).hexdigest()})
    return {
        "forecast": {
            "assumptions": {
                "arpu_paid_eur_mo": ARPU_PAID,
                "tier_mix": {k: {"price_eur": p, "weight": w} for k, (p, w) in TIER_MIX.items()},
                "guardian_tax_pct": 15,
                "gross_margin_pct": 87,
                "ltv_cac": 4.8,
                "churn_mo_pct": 2.1,
            },
            "years": _forecast_rows(),
        },
        "roadmap": ROADMAP,
        "release_package": {"dir": "/release_package", "docs": docs},
    }


@api.get("/founder/release/{doc_name}")
async def founder_release_doc(doc_name: str, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    if doc_name not in RELEASE_DOCS:
        raise HTTPException(404, "unknown_doc")
    p = RELEASE_DIR / doc_name
    if not p.exists():
        raise HTTPException(404, "doc_missing")
    raw = p.read_bytes()
    return {"name": doc_name, "content": raw.decode("utf-8"),
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


@api.get("/founder/jury-cheat-sheet")
async def founder_jury_cheat_sheet(authorization: Optional[str] = Header(None), token: Optional[str] = None):
    """Printable one-page demo cheat sheet (PDF with screenshots) for the jury packet."""
    await _auth_pdf(authorization, token)
    p = RELEASE_DIR / "JURY_CHEAT_SHEET.pdf"
    if not p.exists():
        raise HTTPException(404, "cheat_sheet_missing")
    return _pdf_response(p.read_bytes(), "GUARDIAN_JURY_CHEAT_SHEET.pdf")
