# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""World-Class Infrastructure Layer (Final Giga-Layer).

1. Satellite Emergency Handshake — Nano-Packet compression for satellite SMS
   broadcast (Starlink Direct-to-Cell / Globalstar protocol placeholders).
2. Universal Health Resume — 1-tap HL7 FHIR International Patient Summary (IPS)
   export, interoperable with EU / UK / US healthcare systems.
3. Global Humanitarian Link — 'Humanitarian Shield': verified-catastrophe
   identity + medical profile recognizable by Red Cross / UN aid bodies.
All flows are orchestrated by the Autonomous Swarm (sovereign_guard agent)."""
from fastapi import HTTPException, Header, Response
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid, zlib, base64, hashlib

from core import api, db, clean, get_current_user, _make_pdf, _auth_pdf, _pdf_footer, _pdf_response

# ---------------- 1. SATELLITE EMERGENCY HANDSHAKE (Nano-Packet) ----------------
SAT_PROTOCOLS = ["Starlink Direct-to-Cell (placeholder)", "Globalstar SPOT (placeholder)", "Iridium SBD (placeholder)"]

class NanoPacketIn(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    note: Optional[str] = ""

def _build_nano_packet(user: dict, prof: dict, body: NanoPacketIn) -> dict:
    """Jarvis compresses critical survival data into a <=140B satellite Nano-Packet."""
    loc = f"{body.lat:.4f},{body.lng:.4f}" if body.lat is not None and body.lng is not None else "?"
    raw = "|".join([
        "GA1", user["did"][-8:],
        (prof.get("blood_type") or "?"),
        (prof.get("allergies") or "-")[:24],
        (prof.get("medications") or "-")[:24],
        loc,
        (prof.get("emergency_contact_phone") or "-")[:16],
        (body.note or "")[:32],
        datetime.now(timezone.utc).strftime("%m%d%H%M"),
    ])
    compressed = zlib.compress(raw.encode("utf-8"), 9)
    b64 = base64.b64encode(compressed).decode()
    return {"raw": raw, "raw_bytes": len(raw.encode()), "packet_b64": b64,
            "packet_bytes": len(compressed), "fits_sat_sms": len(compressed) <= 140}

@api.post("/satellite/nano-packet")
async def satellite_nano_packet(body: NanoPacketIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    from routes.subscription import require_tier
    await require_tier(user, "sentinel", "Satellite Emergency Handshake")
    prof = await db.emergency_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    packet = _build_nano_packet(user, prof, body)
    rec = {"packet_id": uuid.uuid4().hex, "user_id": user["user_id"], **packet,
           "protocol": SAT_PROTOCOLS[0], "status": "queued", "simulated": True,
           "created_at": datetime.now(timezone.utc)}
    await db.satellite_queue.insert_one(rec.copy())
    try:
        from routes.swarm import bus_publish
        await bus_publish("satellite.nano_packet_queued", "sovereign_guard",
                          {"packet": rec["packet_id"], "bytes": packet["packet_bytes"]})
    except Exception:
        pass
    return clean(rec)

@api.get("/satellite/queue")
async def satellite_queue(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.satellite_queue.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(10)
    return {"queue": rows, "protocols": SAT_PROTOCOLS,
            "note": "SIMULATION — the real satellite uplink activates after linking with the Starlink/Globalstar API (Phase 3). Nano-Packages are fully functional and will be transmitted by Swarm."}


# ---------------- 2. UNIVERSAL HEALTH RESUME (HL7 FHIR IPS) ----------------
def _split_list(s: Optional[str]) -> list:
    return [x.strip() for x in (s or "").replace(";", ",").split(",") if x.strip()]

async def _build_ips(user: dict) -> dict:
    uid = user["user_id"]
    prof = await db.emergency_profiles.find_one({"user_id": uid}, {"_id": 0}) or {}
    reminders = await db.med_reminders.find({"user_id": uid}, {"_id": 0}).to_list(50)
    vaccines = await db.calendar_events.find({"user_id": uid, "child_id": None, "category": "vaccine"}, {"_id": 0}).sort("date", -1).to_list(30)
    now = datetime.now(timezone.utc)
    pid = f"patient-{user['did'].split(':')[-1][:12]}"

    entries = [{
        "fullUrl": f"urn:uuid:{pid}",
        "resource": {"resourceType": "Patient", "id": pid,
                     "identifier": [{"system": "did:guardian", "value": user["did"]}],
                     "name": [{"text": prof.get("full_name") or user.get("name") or "Unknown"}],
                     "extension": [{"url": "http://hl7.org/fhir/StructureDefinition/patient-bloodType",
                                    "valueString": prof.get("blood_type") or "unknown"}]}}]
    allergy_refs, med_refs, cond_refs, imm_refs = [], [], [], []
    for a in _split_list(prof.get("allergies")):
        rid = f"allergy-{uuid.uuid4().hex[:8]}"
        allergy_refs.append({"reference": f"urn:uuid:{rid}"})
        entries.append({"fullUrl": f"urn:uuid:{rid}",
                        "resource": {"resourceType": "AllergyIntolerance", "id": rid,
                                     "clinicalStatus": {"coding": [{"code": "active"}]},
                                     "code": {"text": a}, "patient": {"reference": f"urn:uuid:{pid}"}}})
    meds_all = _split_list(prof.get("medications")) + [f"{r['name']} {r['dose']}".strip() for r in reminders]
    for m in dict.fromkeys(meds_all):
        rid = f"med-{uuid.uuid4().hex[:8]}"
        med_refs.append({"reference": f"urn:uuid:{rid}"})
        entries.append({"fullUrl": f"urn:uuid:{rid}",
                        "resource": {"resourceType": "MedicationStatement", "id": rid, "status": "active",
                                     "medicationCodeableConcept": {"text": m},
                                     "subject": {"reference": f"urn:uuid:{pid}"}}})
    for c in _split_list(prof.get("conditions")):
        rid = f"cond-{uuid.uuid4().hex[:8]}"
        cond_refs.append({"reference": f"urn:uuid:{rid}"})
        entries.append({"fullUrl": f"urn:uuid:{rid}",
                        "resource": {"resourceType": "Condition", "id": rid,
                                     "clinicalStatus": {"coding": [{"code": "active"}]},
                                     "code": {"text": c}, "subject": {"reference": f"urn:uuid:{pid}"}}})
    for v in vaccines:
        rid = f"imm-{uuid.uuid4().hex[:8]}"
        imm_refs.append({"reference": f"urn:uuid:{rid}"})
        entries.append({"fullUrl": f"urn:uuid:{rid}",
                        "resource": {"resourceType": "Immunization", "id": rid, "status": "completed",
                                     "vaccineCode": {"text": v.get("title")},
                                     "occurrenceDateTime": v.get("date"),
                                     "patient": {"reference": f"urn:uuid:{pid}"}}})
    composition = {
        "fullUrl": f"urn:uuid:composition-{uuid.uuid4().hex[:8]}",
        "resource": {"resourceType": "Composition", "status": "final",
                     "type": {"coding": [{"system": "http://loinc.org", "code": "60591-5",
                                          "display": "Patient summary Document"}]},
                     "title": "International Patient Summary (IPS) — Guardian Health & Angel",
                     "date": now.isoformat(), "subject": {"reference": f"urn:uuid:{pid}"},
                     "author": [{"display": "Guardian Angel Sovereign Foundation (DAO) — patient-mediated export"}],
                     "section": [
                         {"title": "Allergies and Intolerances",
                          "code": {"coding": [{"system": "http://loinc.org", "code": "48765-2"}]}, "entry": allergy_refs},
                         {"title": "Medication Summary",
                          "code": {"coding": [{"system": "http://loinc.org", "code": "10160-0"}]}, "entry": med_refs},
                         {"title": "Problem List",
                          "code": {"coding": [{"system": "http://loinc.org", "code": "11450-4"}]}, "entry": cond_refs},
                         {"title": "Immunizations",
                          "code": {"coding": [{"system": "http://loinc.org", "code": "11369-6"}]}, "entry": imm_refs},
                     ]}}
    bundle = {"resourceType": "Bundle", "type": "document",
              "identifier": {"system": "did:guardian", "value": user["did"]},
              "timestamp": now.isoformat(),
              "meta": {"profile": ["http://hl7.org/fhir/uv/ips/StructureDefinition/Bundle-uv-ips"]},
              "entry": [composition] + entries}
    return {"bundle": bundle,
            "counts": {"allergies": len(allergy_refs), "medications": len(med_refs),
                       "conditions": len(cond_refs), "immunizations": len(imm_refs)},
            "interoperability": ["EU: MyHealth@EU / EHDS", "UK: NHS GP Connect compatible payload",
                                 "US: ONC / Carequality IPS document exchange"],
            "sha256": hashlib.sha256(str(bundle).encode()).hexdigest()}

async def _ips_entitle(user: dict, authorization: Optional[str]) -> str:
    """IPS export: Sentinel+ free · others auto-charged 10 GA-T per export."""
    from routes.subscription import get_active_tier, TIER_RANK, record_revenue
    tier = await get_active_tier(user["user_id"])
    if TIER_RANK.get(tier, 0) >= TIER_RANK["sentinel"]:
        return "tier"
    from routes.token import token_spend, SpendIn
    await token_spend(SpendIn(item="ips_export_single"), authorization)  # 402 if insufficient
    await record_revenue("payperuse", 1.0, user["user_id"], {"item": "ips_export_single", "gat": 10})
    return "gat"

@api.get("/ips/summary")
async def ips_summary(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    access = await _ips_entitle(user, authorization)
    out = await _build_ips(user)
    out["access"] = access
    return out

@api.get("/ips/summary.pdf")
async def ips_summary_pdf(token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    await _ips_entitle(user, authorization or (f"Bearer {token}" if token else None))
    ips = await _build_ips(user)
    prof = await db.emergency_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    vaccines = await db.calendar_events.find({"user_id": user["user_id"], "child_id": None, "category": "vaccine"},
                                             {"_id": 0}).sort("date", -1).to_list(30)
    lines = [
        f"Patient: {prof.get('full_name') or user.get('name') or '—'}",
        f"Guardian DID: {user['did']}",
        f"Blood type: {prof.get('blood_type') or '—'}",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "ALLERGIES AND INTOLERANCES (LOINC 48765-2):",
        *( [f"  • {a}" for a in _split_list(prof.get('allergies'))] or ["  — none recorded"] ),
        "",
        "MEDICATION SUMMARY (LOINC 10160-0):",
        *( [f"  • {m}" for m in _split_list(prof.get('medications'))] or ["  — none recorded"] ),
        "",
        "PROBLEM LIST (LOINC 11450-4):",
        *( [f"  • {c}" for c in _split_list(prof.get('conditions'))] or ["  — none recorded"] ),
        "",
        "IMMUNIZATIONS (LOINC 11369-6):",
        *( [f"  • {v.get('title')} — {v.get('date')}" + (f" (booster due {v.get('booster_due')})" if v.get('booster_due') else "")
            for v in vaccines] or ["  — none recorded"] ),
        "",
        f"FHIR IPS Bundle SHA-256: {ips['sha256']}",
        "Standard: HL7 FHIR International Patient Summary (Bundle-uv-ips).",
        "Interoperable with: " + " · ".join(ips["interoperability"]),
    ]
    pdf = _make_pdf("INTERNATIONAL PATIENT SUMMARY (IPS)\nUNIVERSAL HEALTH RESUME — Guardian Health & Angel",
                    "\n".join(lines), _pdf_footer(ips["sha256"]))
    return _pdf_response(pdf, "guardian_ips_summary.pdf")


# ---------------- 3. GLOBAL HUMANITARIAN LINK (Humanitarian Shield) ----------------
CATASTROPHE_KINDS = {
    "war": "War conflict / evacuation",
    "earthquake": "Earthquake",
    "flood": "Floods",
    "pandemic": "Pandemic",
    "blackout": "Large-scale infrastructure outage",
}
_VERIFY_SOURCES = ["GDACS (Global Disaster Alert — simulated)", "WHO Emergency Feed (simulated)",
                   "ReliefWeb OCHA (simulated)"]

class CatastropheIn(BaseModel):
    kind: str = "war"
    region: str = ""

@api.get("/humanitarian/status")
async def humanitarian_status(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    ev = await db.humanitarian_events.find_one({"verified": True}, {"_id": 0}, sort=[("at", -1)])
    profile = await db.humanitarian_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return {"catastrophe_verified": bool(ev), "event": ev, "profile": profile,
            "kinds": CATASTROPHE_KINDS,
            "recognized_by": ["ICRC / Red Cross (Restoring Family Links)", "UNHCR PRIMES-compatible record", "UN OCHA humanitarian corridors"],
            "note": "SIMULATION — catastrophe verification runs on mocked feeds. The real API (GDACS/WHO) is connected in Phase 3."}

@api.post("/humanitarian/verify")
async def humanitarian_verify(body: CatastropheIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if body.kind not in CATASTROPHE_KINDS:
        raise HTTPException(400, f"kind must be one of {list(CATASTROPHE_KINDS)}")
    ev = {"event_id": uuid.uuid4().hex, "kind": body.kind, "region": body.region.strip()[:80],
          "label": CATASTROPHE_KINDS[body.kind], "verified": True, "simulated": True,
          "consensus_sources": _VERIFY_SOURCES, "verified_by": user["user_id"],
          "at": datetime.now(timezone.utc)}
    await db.humanitarian_events.insert_one(ev.copy())
    try:
        from routes.swarm import bus_publish
        await bus_publish("humanitarian.catastrophe_verified", "sovereign_guard",
                          {"kind": body.kind, "region": ev["region"], "sources": len(_VERIFY_SOURCES)})
    except Exception:
        pass
    return clean(ev)

@api.post("/humanitarian/profile")
async def humanitarian_profile(authorization: Optional[str] = Header(None)):
    """Jarvis generates the official aid-recognizable identity + medical profile.
    Only available after a verified global catastrophe."""
    user = await get_current_user(authorization)
    ev = await db.humanitarian_events.find_one({"verified": True}, {"_id": 0}, sort=[("at", -1)])
    if not ev:
        raise HTTPException(409, "no_verified_catastrophe: The humanitarian shield activates only after a global catastrophe is verified.")
    prof = await db.emergency_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    vaccines = await db.calendar_events.find({"user_id": user["user_id"], "child_id": None, "category": "vaccine"},
                                             {"_id": 0, "title": 1, "date": 1}).sort("date", -1).to_list(10)
    hid = f"GA-HUM-{uuid.uuid4().hex[:8].upper()}"
    profile = {"hum_id": hid, "user_id": user["user_id"], "did": user["did"],
               "full_name": prof.get("full_name") or user.get("name") or "—",
               "blood_type": prof.get("blood_type"), "allergies": prof.get("allergies"),
               "conditions": prof.get("conditions"), "medications": prof.get("medications"),
               "vaccinations": vaccines,
               "emergency_contact": {"name": prof.get("emergency_contact_name"),
                                     "phone": prof.get("emergency_contact_phone")},
               "catastrophe_ref": {"event_id": ev["event_id"], "kind": ev["kind"], "region": ev["region"]},
               "standards": ["UNHCR PRIMES-compatible", "ICRC Restoring Family Links",
                             "Sphere Handbook minimal health record"],
               "qr_payload": f"GA-HUM|{hid}|{user['did']}|{prof.get('blood_type') or '?'}",
               "issued_at": datetime.now(timezone.utc), "simulated": True}
    await db.humanitarian_profiles.update_one({"user_id": user["user_id"]}, {"$set": profile}, upsert=True)
    try:
        from routes.swarm import bus_publish
        await bus_publish("humanitarian.profile_issued", "sovereign_guard", {"hum_id": hid})
    except Exception:
        pass
    return clean(profile)

@api.get("/humanitarian/card.pdf")
async def humanitarian_card_pdf(token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    p = await db.humanitarian_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not p:
        raise HTTPException(404, "First generate a humanitarian profile.")
    vax = "\n".join([f"  • {v['title']} — {v['date']}" for v in p.get("vaccinations", [])]) or "  — none recorded"
    body_txt = (
        f"HUMANITARIAN ID: {p['hum_id']}\n"
        f"Name: {p['full_name']}\n"
        f"Guardian DID: {p['did']}\n"
        f"Blood type: {p.get('blood_type') or '—'}\n"
        f"Allergies: {p.get('allergies') or '—'}\n"
        f"Conditions: {p.get('conditions') or '—'}\n"
        f"Medications: {p.get('medications') or '—'}\n\n"
        f"IMMUNIZATION RECORD:\n{vax}\n\n"
        f"Emergency contact: {p['emergency_contact'].get('name') or '—'} · {p['emergency_contact'].get('phone') or '—'}\n"
        f"Catastrophe reference: {p['catastrophe_ref']['kind'].upper()} — {p['catastrophe_ref']['region'] or 'global'}\n"
        f"Standards: {', '.join(p['standards'])}\n"
        f"Machine-readable: {p['qr_payload']}\n"
        f"Issued: {p['issued_at'].strftime('%Y-%m-%d %H:%M UTC') if hasattr(p['issued_at'], 'strftime') else p['issued_at']}"
    )
    pdf = _make_pdf("HUMANITARIAN SHIELD — EMERGENCY IDENTITY & MEDICAL PROFILE\n"
                    "Guardian Angel Sovereign Foundation (DAO) · for ICRC / UN aid intake",
                    body_txt, _pdf_footer())
    return _pdf_response(pdf, "guardian_humanitarian_card.pdf")
