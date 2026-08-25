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

from core import api, get_current_user

RELEASE_DIR = Path(__file__).resolve().parents[2] / "release_package"
RELEASE_DOCS = {
    "README.md": "Projektový prehľad, moduly, quickstart, kvalita",
    "ARCHITECTURE.md": "Systémová architektúra, subsystémy, dátový model",
    "API_SPEC.md": "Špecifikácia API + UHP/1.0 protokol s HMAC podpisom",
    "LICENSE": "Súkromná proprietárna licencia (evaluation grant)",
}

# ---- Financial forecast (deterministic, tier-mix driven) --------------------
TIER_MIX = {"guardian": (29.0, 0.80), "sentinel": (149.0, 0.17), "archangel": (499.0, 0.03)}
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
    {"year": "2026 Q3", "era": "LAUNCH", "title": "Globálne spustenie",
     "detail": "iOS/Android buildy, UHP pilot SK/CZ — prvých 50 partnerských kliník, Investor Demo Mode."},
    {"year": "2027", "era": "RAILS", "title": "Skutočné settlement rails",
     "detail": "Visa Direct / Mastercard Send nahrádzajú SimulatedRails; S2 cezhraničná arbitráž plne automatizovaná."},
    {"year": "2028", "era": "GRID", "title": "Sentinel Grid naživo",
     "detail": "BLE mesh + satelitné nano-pakety na reálnom hardvéri; 1M+ súbežných senzor-streamov."},
    {"year": "2030", "era": "TWIN", "title": "Certifikované Bio-Digitálne Dvojča",
     "detail": "EU MDR trieda IIa — simulácia liečby PRED podaním sa stáva štandardom starostlivosti."},
    {"year": "2035", "era": "GBI", "title": "Živá mena v národnom meradle",
     "detail": "GA-T Guardian Basic Income — dátové dividendy pre milióny; suverénne vlastníctvo zdravotných dát."},
    {"year": "2040", "era": "MESH", "title": "Kvantová sieť",
     "detail": "Post-kvantová kryptografia (Kyber/Dilithium) všade; Collective Truth ledger ako verejná infraštruktúra."},
    {"year": "2075", "era": "ECHO", "title": "Kognitívne odovzdanie",
     "detail": "Právne uznané digitálne echá — Personality Blueprint prenáša múdrosť generácií."},
    {"year": "2100+", "era": "ARCHANGEL", "title": "Štandard 22. storočia",
     "detail": "UHP ako predvolený protokol ľudskej zdravotnej suverenity — Archangel OS na každom zariadení."},
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
