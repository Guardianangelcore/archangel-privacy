# Copyright © 2026 Guardian Angel. All Rights Reserved.
# This source code and its logic are the sole property of Guardian Angel.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
from fastapi import HTTPException, Header, UploadFile, File, Form
from fastapi.responses import Response, StreamingResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import os, uuid, hashlib, json, io, re, base64, httpx

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

from core import (
    api, db, logger, clean, get_current_user, send_push, _push_client,
    AI_COMPLIANCE_NOTE, _aml_ledger_append,
    AML_UNVERIFIED_DAILY, AML_VERIFIED_DAILY, AML_MAX_TX_PER_DAY,
    _FONT_R, _FONT_B, _make_pdf, _auth_pdf, _pdf_footer, _pdf_response,
    APP_NAME, put_object_sync, get_object_sync, init_storage,
    EMERGENT_LLM_KEY, AUTH_SESSION_URL,
)
from models import User, EmergencyProfile, Document, WaitlistItem, FallEvent

from content import MENTAL_TECHNIQUES
MENTAL_TECHNIQUES_SK = MENTAL_TECHNIQUES['sk']

# Pharmacy Hunter real-data config (future integration — currently DEMO simulation)
PHARMACY_API_URL = os.environ.get('PHARMACY_API_URL', '')
PHARMACY_API_KEY = os.environ.get('PHARMACY_API_KEY', '')

# --------- WAITLIST HUNTER ---------
class WaitlistIn(BaseModel):
    specialty: str
    clinic: str
    city: str
    current_date: str
    target_before: str
    priority: str = "normal"

@api.get("/waitlist")
async def list_waitlist(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    items = await db.waitlist.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return items

@api.post("/waitlist")
async def add_waitlist(body: WaitlistIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    item = WaitlistItem(
        item_id=uuid.uuid4().hex,
        user_id=user["user_id"],
        **body.model_dump(),
    ).model_dump()
    await db.waitlist.insert_one(item.copy())
    return clean(item)

@api.post("/waitlist/{item_id}/scan")
async def scan_waitlist(item_id: str, authorization: Optional[str] = Header(None)):
    """Simulated scan — in production integrates with clinic booking systems via ZK-proofs."""
    import random
    user = await get_current_user(authorization)
    item = await db.waitlist.find_one({"item_id": item_id, "user_id": user["user_id"]}, {"_id": 0})
    if not item:
        raise HTTPException(404, "Not found")
    found = random.random() < 0.35
    upd = {"last_check": datetime.now(timezone.utc)}
    if found:
        earlier_days = random.randint(7, 45)
        found_date = (datetime.now(timezone.utc) + timedelta(days=earlier_days)).strftime("%Y-%m-%d")
        upd["found_slot"] = found_date
        upd["status"] = "slot_found"
    await db.waitlist.update_one({"item_id": item_id}, {"$set": upd})
    if found:
        try:
            await send_push(
                recipients=[user["user_id"]],
                data={
                    "title": "Termín nájdený! 🎯",
                    "message": f"{item['specialty']} · {item['clinic']} — voľný termín {upd['found_slot']}",
                    "action_url": "/(tabs)/waitlist",
                },
                idempotency_key=f"slot-{item_id}-{upd['found_slot']}",
            )
        except Exception as e:
            logger.warning(f"Push failed (non-blocking): {e}")
    return {"found": found, "slot": upd.get("found_slot")}

@api.delete("/waitlist/{item_id}")
async def del_waitlist(item_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.waitlist.delete_one({"item_id": item_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}


# --------- BLACKOUT PROTOCOL (Survival Snapshot) ---------
@api.get("/blackout/snapshot")
async def blackout_snapshot(authorization: Optional[str] = Header(None)):
    """Returns everything the phone needs to survive an internet outage — cache locally."""
    user = await get_current_user(authorization)
    prof = await db.emergency_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    docs = await db.documents.find({"user_id": user["user_id"]}, {"_id": 0}).sort("uploaded_at", -1).limit(20).to_list(20)
    contacts = [{
        "name": prof.get("emergency_contact_name"),
        "phone": prof.get("emergency_contact_phone"),
    }]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user": {"name": user.get("name"), "did": user["did"], "email": user["email"]},
        "emergency_profile": prof,
        "contacts": contacts,
        "documents_meta": [{"doc_id": d["doc_id"], "title": d["title"], "size": d["size"]} for d in docs],
        "survival_tips": [
            "SK: Pri výpadku sietí zdieľajte tento snapshot cez Bluetooth s dôveryhodným zariadením.",
            "SK: Núdzové čísla: 112 · Záchranná služba 155 · Polícia 158 · Hasiči 150",
            "SK: QR kód s DID je čitateľný aj bez internetu.",
        ],
    }


# --------- SURVIVAL AUDITOR ---------
class SurvivalItemIn(BaseModel):
    name: str
    category: str = "food"  # water | food | power | meds | tools
    quantity: float = 1
    unit: str = "ks"
    daily_need_per_person: float = 1.0

@api.get("/survival/items")
async def survival_list(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.survival_items.find({"user_id": user["user_id"]}, {"_id": 0}).sort("category", 1).to_list(300)

@api.post("/survival/items")
async def survival_add(body: SurvivalItemIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    doc = {"item_id": uuid.uuid4().hex, "user_id": user["user_id"], **body.model_dump(), "created_at": datetime.now(timezone.utc)}
    await db.survival_items.insert_one(doc.copy())
    return clean(doc)

@api.delete("/survival/items/{item_id}")
async def survival_del(item_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.survival_items.delete_one({"item_id": item_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}

@api.get("/survival/runway")
async def survival_runway(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    family = max(1, int(user.get("family_size") or 2))
    items = await db.survival_items.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(300)
    cats: dict = {}
    for it in items:
        need = max(0.01, float(it.get("daily_need_per_person") or 1)) * family
        days = float(it.get("quantity") or 0) / need
        cats.setdefault(it["category"], 0.0)
        cats[it["category"]] += days
    category_runways = {k: round(v, 1) for k, v in cats.items()}
    essential = [category_runways.get(c) for c in ("water", "food") if c in category_runways]
    overall = round(min(essential), 1) if essential else 0.0
    return {
        "family_size": family,
        "category_runways": category_runways,
        "overall_days": overall,
        "items_count": len(items),
    }


# --------- ANALOG RECOVERY KIT (Survival Bible PDF) ---------
@api.get("/survival/bible.pdf")
async def survival_bible_pdf(token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    uid = user["user_id"]
    prof = await db.emergency_profiles.find_one({"user_id": uid}, {"_id": 0}) or {}
    proxy = await db.proxy_directives.find_one({"user_id": uid}, {"_id": 0}) or {}
    testament = await db.legal_testaments.find_one({"user_id": uid}, {"_id": 0}) or {}
    meds = await db.med_reminders.find({"user_id": uid}, {"_id": 0}).to_list(50)
    cabinet = await db.cabinet.find({"user_id": uid}, {"_id": 0}).to_list(100)
    waitlist = await db.waitlist.find({"user_id": uid}, {"_id": 0}).to_list(50)
    bio = await db.biometric_wills.find_one({"user_id": uid}, {"_id": 0}) or {}

    parts = []
    parts.append("1. IDENTITA A NÚDZOVÉ INFO / IDENTITY & EMERGENCY")
    parts.append(f"Meno: {prof.get('full_name') or user.get('name') or '—'}")
    parts.append(f"DID: {user['did']}")
    parts.append(f"Krvná skupina: {prof.get('blood_type') or '—'}  ·  Alergie: {prof.get('allergies') or '—'}")
    parts.append(f"Diagnózy: {prof.get('conditions') or '—'}")
    parts.append(f"Lieky (voľný text): {prof.get('medications') or '—'}")
    parts.append(f"ICE kontakt: {prof.get('emergency_contact_name') or '—'} · {prof.get('emergency_contact_phone') or '—'}")
    parts.append(f"Darca orgánov: {'ÁNO — ' + str(prof.get('donor_organs') or 'všetky') if prof.get('is_donor') else 'NIE'}")

    parts.append("\n2. DENNÉ LIEKY / DAILY MEDICATION")
    if meds:
        for m in meds:
            parts.append(f"  • {m.get('name')} {m.get('dose') or ''} — časy: {', '.join(m.get('times') or [])}")
    else:
        parts.append("  — žiadne pripomienky liekov")

    parts.append("\n3. LEKÁRNIČKA A ZÁSOBY / MEDICINE CABINET")
    if cabinet:
        for c in cabinet[:40]:
            parts.append(f"  • {c.get('name')} — {c.get('quantity')} {c.get('unit')}" + (f" · exp. {c.get('expires_on')}" if c.get('expires_on') else ""))
    else:
        parts.append("  — lekárnička je prázdna")

    parts.append("\n4. ČAKACIE LISTINY / WAITLIST HUNTER")
    if waitlist:
        for w in waitlist[:20]:
            parts.append(f"  • {w.get('specialty') or w.get('title') or '—'} · {w.get('city') or ''} · stav: {w.get('status') or 'hunting'}")
    else:
        parts.append("  — žiadne aktívne čakacie listiny")

    parts.append("\n5. SPLNOMOCNENEC / HEALTHCARE PROXY")
    if proxy.get("proxy_full_name"):
        parts.append(f"  {proxy.get('proxy_full_name')} ({proxy.get('proxy_relationship') or '—'}) · {proxy.get('proxy_phone') or '—'}")
        parts.append(f"  Rozsah: {proxy.get('scope') or '—'}  ·  SHA-256: {proxy.get('doc_hash') or '—'}")
    else:
        parts.append("  — splnomocnenec nie je určený")

    parts.append("\n6. ODKAZ A ZÁVET / LEGACY")
    if testament.get("document_text"):
        t = testament["document_text"]
        parts.append(t[:1200] + ("…" if len(t) > 1200 else ""))
        parts.append(f"  SHA-256 závetu: {testament.get('doc_hash') or '—'}")
    else:
        parts.append("  — závet zatiaľ nevygenerovaný")
    if bio.get("sha256"):
        parts.append(f"  Biometrické potvrdenie: {bio.get('media_type')} · {bio.get('recorded_at', '')[:16]} · SHA-256 {bio.get('sha256')}")

    parts.append("\n7. KRÍZOVÉ TECHNIKY BEZ TECHNOLÓGIÍ / ANALOG CRISIS TECHNIQUES")
    for t in MENTAL_TECHNIQUES_SK:
        parts.append(f"  ▶ {t['title']} — {t['subtitle']}")
        for i, s in enumerate(t["steps"]):
            parts.append(f"     {i+1}. {s}")

    parts.append("\n8. NÚDZOVÉ ČÍSLA / EMERGENCY NUMBERS")
    parts.append("  112 — tieseň EÚ · 155 — záchranka (SK/CZ) · 158 — polícia CZ · 0800 800 566 — Linka dôvery Nezábudka")

    body = "\n".join(parts)
    pdf = await run_in_threadpool(_make_pdf, "SURVIVAL BIBLE — ANALOG RECOVERY KIT\nVYTLAČTE A ULOŽTE NA BEZPEČNÉ MIESTO", body, _pdf_footer())
    return _pdf_response(pdf, "guardian_survival_bible.pdf")


# --------- PHARMACY STOCK HUNTER (CZ/SK) ---------
# NOTE: No public real-time stock API exists for SK/CZ pharmacy chains — results are a
# DETERMINISTIC SIMULATION of the aggregator engine (clearly flagged simulated=True).
_PHARMACIES = {
    "SK": [("Dr. Max", "Bratislava"), ("BENU", "Bratislava"), ("Schneider", "Košice"), ("Dr. Max", "Žilina"), ("BENU", "Nitra"), ("Plus Lekáreň", "Prešov")],
    "CZ": [("Dr. Max", "Praha"), ("BENU", "Praha"), ("Pilulka", "Brno"), ("Dr. Max", "Ostrava"), ("BENU", "Plzeň"), ("Magistra", "Olomouc")],
}

def _simulate_stock(med: str, region: str) -> list:
    region = region.upper() if region.upper() in _PHARMACIES else "SK"
    out = []
    for i, (chain, city) in enumerate(_PHARMACIES[region]):
        h = int(hashlib.sha256(f"{med.lower()}|{chain}|{city}".encode()).hexdigest(), 16)
        status = ["in_stock", "low_stock", "out_of_stock"][h % 3]
        price = round(3.5 + (h % 4200) / 100, 2)
        out.append({
            "pharmacy": chain, "city": city, "region": region,
            "status": status, "price_eur": price if status != "out_of_stock" else None,
            "pieces": (h % 14) + 1 if status == "in_stock" else ((h % 3) + 1 if status == "low_stock" else 0),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    out.sort(key=lambda x: {"in_stock": 0, "low_stock": 1, "out_of_stock": 2}[x["status"]])
    return out

@api.get("/pharmacy/search")
async def pharmacy_search(med: str, region: str = "SK", authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    if not med.strip():
        raise HTTPException(400, "med required")
    return {"med": med.strip(), "region": region.upper(), "simulated": True, "results": _simulate_stock(med.strip(), region)}

class PharmacyWatchIn(BaseModel):
    med_name: str
    region: str = "SK"

@api.post("/pharmacy/watch")
async def pharmacy_watch_add(body: PharmacyWatchIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    doc = {
        "watch_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "med_name": body.med_name.strip(), "region": body.region.upper(),
        "status": "watching", "last_scan": None, "found_at": None,
        "created_at": datetime.now(timezone.utc),
    }
    await db.pharmacy_watches.insert_one(doc.copy())
    return clean(doc)

@api.get("/pharmacy/watches")
async def pharmacy_watches(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.pharmacy_watches.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)

@api.post("/pharmacy/watches/{watch_id}/scan")
async def pharmacy_watch_scan(watch_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    w = await db.pharmacy_watches.find_one({"watch_id": watch_id, "user_id": user["user_id"]}, {"_id": 0})
    if not w:
        raise HTTPException(404, "Not found")
    results = _simulate_stock(w["med_name"], w["region"])
    hit = next((r for r in results if r["status"] == "in_stock"), None)
    now = datetime.now(timezone.utc)
    upd = {"last_scan": now}
    if hit:
        upd.update({"status": "found", "found_at": now, "found_pharmacy": f"{hit['pharmacy']} {hit['city']}"})
        try:
            await send_push(recipients=[user["user_id"]], data={"title": "💊 LIEK NÁJDENÝ", "message": f"{w['med_name']} skladom: {hit['pharmacy']} {hit['city']}", "action_url": "/pharmacy-hunter"})
        except Exception as e:
            logger.warning(f"pharmacy push failed: {e}")
    await db.pharmacy_watches.update_one({"watch_id": watch_id}, {"$set": upd})
    return {"scanned": True, "simulated": True, "hit": hit, "results": results}

@api.delete("/pharmacy/watches/{watch_id}")
async def pharmacy_watch_del(watch_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.pharmacy_watches.delete_one({"watch_id": watch_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}


# --------- AUTONOMOUS AUTO-BOOKER (Waitlist Hunter → booking + Guardian Calendar sync) ---------
# NOTE: clinic booking APIs are SIMULATED (deterministic) until real integrations are provided.

_CLINICS = ["Poliklinika Ružinov", "Nemocnica Bory", "ProCare Central", "Klinika Kramáre", "MedPark Košice"]

def _simulate_slot(specialty: str, city: str) -> dict:
    h = int(hashlib.sha256(f"{specialty.lower()}|{city.lower()}".encode()).hexdigest(), 16)
    slot_date = (datetime.now(timezone.utc) + timedelta(days=(h % 12) + 3)).date().isoformat()
    slot_time = f"{8 + (h % 9):02d}:{['00','15','30','45'][h % 4]}"
    return {"clinic": _CLINICS[h % len(_CLINICS)], "date": slot_date, "time": slot_time}

class AutobookIn(BaseModel):
    specialty: str
    city: Optional[str] = ""
    source: Optional[str] = "manual"   # manual | health_drop | ocr
    source_id: Optional[str] = None    # e.g. drop_doc_id

@api.post("/autobook")
async def autobook(body: AutobookIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if not body.specialty.strip():
        raise HTTPException(400, "specialty required")
    slot = _simulate_slot(body.specialty, body.city or "")
    now = datetime.now(timezone.utc)
    item = {
        "item_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "specialty": body.specialty.strip(), "clinic": slot["clinic"], "city": body.city or "",
        "current_date": "", "target_before": slot["date"], "priority": "auto",
        "status": "booked", "last_check": now,
        "found_slot": f"{slot['date']} {slot['time']} — {slot['clinic']}",
        "created_at": now,
    }
    await db.waitlist.insert_one(item.copy())
    cal = {
        "event_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "category": "exam", "title": f"{item['specialty']} — {slot['clinic']}",
        "date": slot["date"], "notes": f"Auto-Booker · {slot['time']} · zdroj: {body.source}",
        "booster_due": None, "source": f"autobook:{body.source}",
        "created_at": now,
    }
    await db.calendar_events.insert_one(cal.copy())
    if body.source == "health_drop" and body.source_id:
        await db.health_drops.update_one({"drop_doc_id": body.source_id, "user_id": user["user_id"]}, {"$set": {"autobooked": True}})
    try:
        await send_push(recipients=[user["user_id"]],
                        data={"title": "✅ TERMÍN ZAREZERVOVANÝ", "message": f"{item['specialty']}: {item['found_slot']}", "action_url": "/health-timeline"})
    except Exception as e:
        logger.warning(f"autobook push failed: {e}")
    return {"booking": clean(item), "calendar_event": clean(cal), "simulated": True}

@api.post("/waitlist/{item_id}/autobook")
async def waitlist_autobook(item_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    w = await db.waitlist.find_one({"item_id": item_id, "user_id": user["user_id"]}, {"_id": 0})
    if not w:
        raise HTTPException(404, "Not found")
    slot = _simulate_slot(w["specialty"], w.get("city") or "")
    now = datetime.now(timezone.utc)
    found = f"{slot['date']} {slot['time']} — {slot['clinic']}"
    await db.waitlist.update_one({"item_id": item_id}, {"$set": {"status": "booked", "found_slot": found, "last_check": now}})
    cal = {
        "event_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "category": "exam", "title": f"{w['specialty']} — {slot['clinic']}",
        "date": slot["date"], "notes": f"Auto-Booker · {slot['time']}",
        "booster_due": None, "source": "autobook:waitlist",
        "created_at": now,
    }
    await db.calendar_events.insert_one(cal.copy())
    try:
        await send_push(recipients=[user["user_id"]],
                        data={"title": "✅ TERMÍN ZAREZERVOVANÝ", "message": f"{w['specialty']}: {found}", "action_url": "/health-timeline"})
    except Exception as e:
        logger.warning(f"autobook push failed: {e}")
    return {"booking": {"item_id": item_id, "status": "booked", "found_slot": found}, "calendar_event": clean(cal), "simulated": True}
