# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# SURVIVAL PANTRY — Guardian Lens for the bunker.
# Track food, water filters, batteries, gas canisters, ammo, meds.
# Jarvis issues Rotation Alerts when items near expiration.
import uuid
from datetime import datetime, timezone, timedelta, date
from typing import Optional, List
from fastapi import Header, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from core import api, db, clean, get_current_user, logger

_CATEGORIES = {"food", "water", "battery", "gas", "med", "ammo", "filter", "tool", "other"}

# Sensible default shelf-lives (in days) — used when OCR cannot read an expiry.
_DEFAULT_SHELF_LIFE = {
    "food": 730,       # canned goods ~ 2 years
    "water": 365,      # bottled water ~ 1 year
    "battery": 365 * 5,  # lithium AA ~ 5 years
    "gas": 365 * 10,   # sealed propane canister ~ 10 years
    "med": 365,        # OTC medicine
    "filter": 365 * 2, # water filter cartridge ~ 2 years
    "ammo": 365 * 10,
    "tool": 365 * 20,
    "other": 365,
}


class PantryIn(BaseModel):
    name: str
    category: str
    expiration_date: Optional[str] = None  # ISO date "YYYY-MM-DD"
    quantity: Optional[int] = 1
    notes: Optional[str] = None
    location: Optional[str] = None  # e.g. "Bunker A · polica 2"


class PantryPatch(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    expiration_date: Optional[str] = None
    quantity: Optional[int] = None
    notes: Optional[str] = None
    location: Optional[str] = None


def _parse_iso_date(d: Optional[str]) -> Optional[date]:
    if not d:
        return None
    try:
        return datetime.fromisoformat(d).date()
    except Exception:
        try:
            return datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            return None


def _days_left(exp: Optional[date]) -> Optional[int]:
    if not exp:
        return None
    return (exp - date.today()).days


def _urgency(days: Optional[int]) -> str:
    if days is None:
        return "unknown"
    if days < 0:
        return "expired"
    if days <= 14:
        return "critical"   # rotate now
    if days <= 60:
        return "soon"       # start shopping
    if days <= 180:
        return "healthy"
    return "fresh"


@api.get("/pantry")
async def pantry_list(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.pantry.find({"user_id": user["user_id"]}, {"_id": 0}).sort("expiration_date", 1).to_list(500)
    for r in rows:
        exp = _parse_iso_date(r.get("expiration_date"))
        d = _days_left(exp)
        r["days_left"] = d
        r["urgency"] = _urgency(d)
    # Group counters for the header pill row.
    counts = {"critical": 0, "soon": 0, "healthy": 0, "fresh": 0, "expired": 0, "unknown": 0}
    for r in rows:
        counts[r["urgency"]] = counts.get(r["urgency"], 0) + 1
    return {"items": clean(rows), "counts": counts, "total": len(rows)}


@api.post("/pantry")
async def pantry_add(body: PantryIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    cat = (body.category or "other").lower()
    if cat not in _CATEGORIES:
        raise HTTPException(400, f"category must be one of {sorted(_CATEGORIES)}")
    exp_d = _parse_iso_date(body.expiration_date)
    if not exp_d:
        # Fallback: today + default shelf-life for the category.
        exp_d = date.today() + timedelta(days=_DEFAULT_SHELF_LIFE.get(cat, 365))
    doc = {
        "pantry_id": uuid.uuid4().hex,
        "user_id": user["user_id"],
        "did": user.get("did"),
        "name": body.name.strip()[:120],
        "category": cat,
        "expiration_date": exp_d.isoformat(),
        "quantity": max(1, int(body.quantity or 1)),
        "notes": (body.notes or "").strip()[:400],
        "location": (body.location or "").strip()[:80],
        "created_at": datetime.now(timezone.utc),
    }
    await db.pantry.insert_one(doc.copy())
    doc["days_left"] = _days_left(exp_d)
    doc["urgency"] = _urgency(doc["days_left"])
    return clean(doc)


@api.patch("/pantry/{pantry_id}")
async def pantry_patch(pantry_id: str, body: PantryPatch, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if "category" in upd and upd["category"] not in _CATEGORIES:
        raise HTTPException(400, "invalid category")
    if "name" in upd:
        upd["name"] = upd["name"].strip()[:120]
    if "expiration_date" in upd:
        parsed = _parse_iso_date(upd["expiration_date"])
        if not parsed:
            raise HTTPException(400, "expiration_date must be YYYY-MM-DD")
        upd["expiration_date"] = parsed.isoformat()
    if "quantity" in upd:
        upd["quantity"] = max(1, int(upd["quantity"]))
    r = await db.pantry.update_one({"pantry_id": pantry_id, "user_id": user["user_id"]}, {"$set": upd})
    if not r.matched_count:
        raise HTTPException(404, "Not found")
    doc = await db.pantry.find_one({"pantry_id": pantry_id}, {"_id": 0})
    exp = _parse_iso_date(doc.get("expiration_date"))
    doc["days_left"] = _days_left(exp)
    doc["urgency"] = _urgency(doc["days_left"])
    return clean(doc)


@api.delete("/pantry/{pantry_id}")
async def pantry_delete(pantry_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    r = await db.pantry.delete_one({"pantry_id": pantry_id, "user_id": user["user_id"]})
    if not r.deleted_count:
        raise HTTPException(404, "Not found")
    return {"ok": True}


@api.get("/pantry/alerts")
async def pantry_alerts(authorization: Optional[str] = Header(None)):
    """Items that will expire within 30 days OR already expired — for Jarvis rotation alerts."""
    user = await get_current_user(authorization)
    today = date.today()
    cutoff = today + timedelta(days=30)
    rows = await db.pantry.find(
        {
            "user_id": user["user_id"],
            "expiration_date": {"$lte": cutoff.isoformat()},
        },
        {"_id": 0},
    ).sort("expiration_date", 1).to_list(50)
    alerts = []
    for r in rows:
        exp = _parse_iso_date(r.get("expiration_date"))
        d = _days_left(exp)
        alerts.append({**r, "days_left": d, "urgency": _urgency(d)})
    # Deterministic Slovak alert line for the first item — the UI uses it verbatim.
    top_line = None
    if alerts:
        top = alerts[0]
        if top["urgency"] == "expired":
            top_line = f"{top['name']} v {top.get('location') or 'sklade'} má prekročenú spotrebu o {abs(top['days_left'])} dní."
        else:
            top_line = f"{top['name']} v {top.get('location') or 'sklade'} vyprší o {top['days_left']} dní. Odporúčam rotovať."
    return {"alerts": clean(alerts), "count": len(alerts), "top_line": top_line}


# --------- SCAN via Guardian Lens (reuse OCR pipeline) ----------
class PantryScanIn(BaseModel):
    doc_id: str            # a document already uploaded to /vault/documents
    hint_category: Optional[str] = None
    location: Optional[str] = None

import re
_EXPIRY_PATTERNS = [
    # "Best before: 12.03.2028" / "EXP 2028-03-12" / "Spotreba do 12/03/2028"
    re.compile(r"(?:best\s*before|exp(?:iry|iration)?|spotr(?:eb[au])(?:\s+do)?|use\s*by|minim[aá]lna\s+trvanlivos[tť]|do\s+d[aá]tumu)[^0-9]{0,10}(\d{1,2})\s*[.\-/]\s*(\d{1,2})\s*[.\-/]\s*(\d{2,4})\b", re.I),
    # ISO YYYY-MM-DD label-less (rare but common on batteries)
    re.compile(r"(?:best\s*before|exp|use\s*by)[^0-9]{0,10}(\d{4})-(\d{1,2})-(\d{1,2})\b", re.I),
    # "MHD 12/2028"  (month/year only)
    re.compile(r"\b(?:MHD|MDD|MHT|BB|EXP)[^0-9]{0,5}(\d{1,2})[.\-/](\d{2,4})\b", re.I),
]


def _detect_expiry(text: str) -> Optional[str]:
    if not text:
        return None
    t = text[:6000]
    for i, pat in enumerate(_EXPIRY_PATTERNS):
        m = pat.search(t)
        if not m:
            continue
        try:
            groups = m.groups()
            if i == 1:
                y, mo, d = int(groups[0]), int(groups[1]), int(groups[2])
            elif i == 2:
                mo = int(groups[0])
                y = int(groups[1])
                if y < 100: y += 2000
                # Month-only → last day of month
                if mo == 12:
                    d = 31
                else:
                    d = (date(y, mo + 1, 1) - timedelta(days=1)).day
            else:
                d, mo, y = int(groups[0]), int(groups[1]), int(groups[2])
                if y < 100: y += 2000
            if not (1 <= mo <= 12 and 1 <= d <= 31 and 2020 <= y <= 2060):
                continue
            return date(y, mo, d).isoformat()
        except Exception:
            continue
    return None


@api.post("/pantry/scan")
async def pantry_scan(body: PantryScanIn, authorization: Optional[str] = Header(None)):
    """Take a document that was already uploaded via the Lens (OCR pipeline) and
    turn it into a pantry entry. Detects expiry date + suggests a name from the
    first bold-ish line of the OCR text."""
    user = await get_current_user(authorization)
    doc = await db.documents.find_one({"doc_id": body.doc_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Document not found (upload via Lens first)")

    # Reuse the shared OCR helper — falls back to cached text if already extracted.
    from routes.health import extract_doc_text
    text = doc.get("extracted_text")
    if not text:
        try:
            text = await extract_doc_text(doc)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"pantry scan OCR error: {e}")
            text = ""

    # Suggest a name from the first non-numeric line
    name = ""
    for ln in (text or "").splitlines():
        ln = ln.strip()
        if len(ln) >= 3 and not ln.replace(" ", "").isdigit():
            name = ln[:80]
            break
    name = name or doc.get("title") or "Zásoba"

    expiry_iso = _detect_expiry(text or "")
    cat = (body.hint_category or "other").lower()
    if cat not in _CATEGORIES:
        cat = "other"
    if not expiry_iso:
        expiry_iso = (date.today() + timedelta(days=_DEFAULT_SHELF_LIFE.get(cat, 365))).isoformat()

    pdoc = {
        "pantry_id": uuid.uuid4().hex,
        "user_id": user["user_id"],
        "did": user.get("did"),
        "name": name,
        "category": cat,
        "expiration_date": expiry_iso,
        "quantity": 1,
        "notes": "",
        "location": (body.location or "").strip()[:80],
        "source_doc_id": body.doc_id,
        "created_at": datetime.now(timezone.utc),
    }
    await db.pantry.insert_one(pdoc.copy())
    pdoc["days_left"] = _days_left(_parse_iso_date(expiry_iso))
    pdoc["urgency"] = _urgency(pdoc["days_left"])
    pdoc["extracted_expiry"] = expiry_iso if _detect_expiry(text or "") else None
    return clean(pdoc)
