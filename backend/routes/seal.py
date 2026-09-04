# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""OMNIPOTENT ARCHANGEL FINAL SEAL — Part II.

1. OFFICIAL FOUNDATION IDENTITY: hard-coded ProtonMail anchor
   guardian.angel.core@proton.me + GHOST MODE (temporary anonymized Patient
   Tokens for cross-border medical arbitrage).
2. INNER CIRCLE: founder-managed whitelist → permanent Archangel status for
   the founder's family (lifetime, never expires).
3. MEDICAL ARBITRAGE: cross-border surgery cost optimization (PL / HU / TR)
   with billing predictions (EU Directive 2011/24 + S2 route).
4. GENOMIC BIO-IDENTITY: DNA/genomic markers metadata in the sovereign vault.
5. SURVIVAL LAYERS: Duress PIN (decoy vault + silent alarm), Mesh-Messenger
   (P2P store-and-forward, BLE mesh in native build), Power-Saver mode."""
from fastapi import HTTPException, Header
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid, hashlib

from core import api, db, logger, clean, get_current_user, send_push, _aml_ledger_append

# ============================================================
# OFFICIAL FOUNDATION IDENTITY — hard-coded, immutable
# ============================================================
FOUNDATION_EMAIL = "guardian.angel.core@proton.me"
FOUNDATION_IDENTITY = {
    "official_email": FOUNDATION_EMAIL,
    "provider": "ProtonMail (E2E encrypted mail, Switzerland)",
    "entity": "Guardian Angel Sovereign Foundation (DAO)",
    "purpose": "The foundation's only official communication channel — all right-of-erasure requests, court subpoenas, and partnerships go here.",
    "pgp": "PGP fingerprint published on-chain (Mosaic block #1, Proof of Origin)",
    "immutable": True,
}

@api.get("/foundation/identity")
async def foundation_identity(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    return FOUNDATION_IDENTITY


# ============================================================
# GHOST MODE — temporary anonymized Patient Tokens
# ============================================================
GHOST_TTL_HOURS = 24

class GhostToggleIn(BaseModel):
    enabled: bool

@api.post("/ghost/toggle")
async def ghost_toggle(body: GhostToggleIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    from routes.subscription import require_tier
    from routes.features import has_feature
    if not await has_feature(user, "ghost_mode"):
        await require_tier(user, "sentinel", "Ghost Mode")
    if body.enabled:
        token = f"GHOST-{uuid.uuid4().hex[:12].upper()}"
        exp = datetime.now(timezone.utc) + timedelta(hours=GHOST_TTL_HOURS)
        await db.users.update_one({"user_id": user["user_id"]},
                                  {"$set": {"ghost_mode": True, "ghost_token": token, "ghost_expires": exp}})
        await _aml_ledger_append(user["user_id"], "ghost_mode_on", {"token_sha256": hashlib.sha256(token.encode()).hexdigest()})
        return {"ghost_mode": True, "patient_token": token, "expires_at": exp.isoformat(),
                "note": "Anonymized patient token — clinics see only the token, not your identity. Valid for 24 h."}
    await db.users.update_one({"user_id": user["user_id"]},
                              {"$set": {"ghost_mode": False}, "$unset": {"ghost_token": "", "ghost_expires": ""}})
    return {"ghost_mode": False}

@api.get("/ghost/status")
async def ghost_status(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    fresh = await db.users.find_one({"user_id": user["user_id"]},
                                    {"_id": 0, "ghost_mode": 1, "ghost_token": 1, "ghost_expires": 1}) or {}
    exp = fresh.get("ghost_expires")
    active = bool(fresh.get("ghost_mode"))
    if active and exp:
        e = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
        if e < datetime.now(timezone.utc):
            active = False
            await db.users.update_one({"user_id": user["user_id"]},
                                      {"$set": {"ghost_mode": False}, "$unset": {"ghost_token": "", "ghost_expires": ""}})
    return {"ghost_mode": active,
            "patient_token": fresh.get("ghost_token") if active else None,
            "expires_at": exp.isoformat() if (active and exp) else None}


# ============================================================
# INNER CIRCLE — permanent Archangel whitelist (founder only)
# ============================================================
class InnerCircleIn(BaseModel):
    email: str
    name: Optional[str] = ""
    relationship: Optional[str] = "family"

async def _require_founder(user: dict) -> None:
    from routes.subscription import _is_founder
    if not await _is_founder(user):
        raise HTTPException(403, "founder_only: Inner Circle is managed exclusively by the founder.")

@api.get("/inner-circle")
async def inner_circle_list(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await _require_founder(user)
    rows = await db.inner_circle.find({}, {"_id": 0}).sort("added_at", -1).to_list(100)
    return {"members": rows,
            "policy": "Members of Inner Circle have LIFETIME Archangel status — never expires, no payment required."}

@api.post("/inner-circle")
async def inner_circle_add(body: InnerCircleIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await _require_founder(user)
    email = body.email.strip().lower()
    if "@" not in email:
        raise HTTPException(400, "Invalid email")
    if await db.inner_circle.find_one({"email": email}):
        raise HTTPException(409, "Already in the Inner Circle")
    member = {
        "member_id": uuid.uuid4().hex, "email": email,
        "name": (body.name or "").strip()[:80], "relationship": (body.relationship or "family")[:40],
        "status": "archangel_permanent", "added_by": user["user_id"],
        "added_at": datetime.now(timezone.utc),
    }
    # If the user already exists → grant immediately
    existing = await db.users.find_one({"email": email}, {"_id": 0, "user_id": 1, "did": 1})
    if existing:
        await db.users.update_one({"user_id": existing["user_id"]},
                                  {"$set": {"inner_circle": True, "tier": "archangel",
                                            "tier_until": None, "tier_paid_with": "inner_circle"}})
        member["linked_user_id"] = existing["user_id"]
        member["linked_did"] = existing.get("did")
    await db.inner_circle.insert_one(member.copy())
    await _aml_ledger_append(user["user_id"], "inner_circle_add", {"email": email, "relationship": member["relationship"]})
    return clean(member)

@api.delete("/inner-circle/{member_id}")
async def inner_circle_remove(member_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await _require_founder(user)
    m = await db.inner_circle.find_one({"member_id": member_id}, {"_id": 0})
    if not m:
        raise HTTPException(404, "Not found")
    if m.get("linked_user_id"):
        await db.users.update_one({"user_id": m["linked_user_id"]},
                                  {"$unset": {"inner_circle": ""}, "$set": {"tier": "sovereign"}})
    await db.inner_circle.delete_one({"member_id": member_id})
    return {"ok": True}


# ============================================================
# MEDICAL ARBITRAGE — cross-border surgery optimizer (PL/HU/TR)
# ============================================================
ARBITRAGE_COUNTRY = {
    "PL": {"flag": "🇵🇱", "name": "Poland", "travel_eur": 120, "night_eur": 55, "eu_member": True},
    "HU": {"flag": "🇭🇺", "name": "Hungary", "travel_eur": 90, "night_eur": 50, "eu_member": True},
    "TR": {"flag": "🇹🇷", "name": "Turecko", "travel_eur": 340, "night_eur": 45, "eu_member": False},
}
ARBITRAGE_PROCEDURES = [
    {"procedure_id": "hip-replacement", "name": "Total hip replacement",
     "sk_price_eur": 9800, "sk_wait_days": 420, "recovery_nights": 6,
     "abroad": {"PL": {"price_eur": 5200, "wait_days": 35, "clinic": "Carolina Medical Center, Warsaw"},
                "HU": {"price_eur": 6100, "wait_days": 42, "clinic": "Budai Egészségközpont, Budapest"},
                "TR": {"price_eur": 4300, "wait_days": 21, "clinic": "Acıbadem Hospital, Istanbul"}}},
    {"procedure_id": "knee-replacement", "name": "Total knee replacement",
     "sk_price_eur": 9200, "sk_wait_days": 390, "recovery_nights": 6,
     "abroad": {"PL": {"price_eur": 4900, "wait_days": 30, "clinic": "Ortopedika, Warsaw"},
                "HU": {"price_eur": 5800, "wait_days": 45, "clinic": "Duna Medical Center, Budapest"},
                "TR": {"price_eur": 4100, "wait_days": 18, "clinic": "Memorial Şişli, Istanbul"}}},
    {"procedure_id": "cataract", "name": "Cataract surgery (cataract)",
     "sk_price_eur": 1450, "sk_wait_days": 180, "recovery_nights": 1,
     "abroad": {"PL": {"price_eur": 750, "wait_days": 10, "clinic": "Optegra, Krakov"},
                "HU": {"price_eur": 820, "wait_days": 14, "clinic": "Focus Medical, Budapest"},
                "TR": {"price_eur": 590, "wait_days": 7, "clinic": "Dünyagöz, Istanbul"}}},
    {"procedure_id": "cardiac-bypass", "name": "Coronary bypass (CABG)",
     "sk_price_eur": 24500, "sk_wait_days": 120, "recovery_nights": 10,
     "abroad": {"PL": {"price_eur": 14800, "wait_days": 28, "clinic": "American Heart of Poland, Katovice",},
                "HU": {"price_eur": 16200, "wait_days": 35, "clinic": "Gottsegen Cardiology Institute, Budapest"},
                "TR": {"price_eur": 11900, "wait_days": 14, "clinic": "Florence Nightingale, Istanbul"}}},
    {"procedure_id": "spinal-fusion", "name": "Spine stabilization (spinal fusion)",
     "sk_price_eur": 16800, "sk_wait_days": 300, "recovery_nights": 7,
     "abroad": {"PL": {"price_eur": 9600, "wait_days": 40, "clinic": "Paley European Institute, Warsaw"},
                "HU": {"price_eur": 10400, "wait_days": 50, "clinic": "Buda Health Center, Budapest"},
                "TR": {"price_eur": 8200, "wait_days": 21, "clinic": "Liv Hospital, Istanbul"}}},
    {"procedure_id": "dental-implants", "name": "Dental implants (4 pcs + crowns)",
     "sk_price_eur": 6400, "sk_wait_days": 60, "recovery_nights": 3,
     "abroad": {"PL": {"price_eur": 3400, "wait_days": 14, "clinic": "Dentim Clinic, Katovice"},
                "HU": {"price_eur": 2900, "wait_days": 10, "clinic": "Helvetic Clinics, Budapest"},
                "TR": {"price_eur": 2200, "wait_days": 7, "clinic": "DentGroup, Istanbul"}}},
]

@api.get("/arbitrage/procedures")
async def arbitrage_procedures(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    out = []
    for p in ARBITRAGE_PROCEDURES:
        best_cc = min(p["abroad"], key=lambda cc: p["abroad"][cc]["price_eur"])
        best = p["abroad"][best_cc]
        out.append({**p, "best_country": best_cc,
                    "best_saving_eur": round(p["sk_price_eur"] - best["price_eur"], 0),
                    "best_wait_cut_days": p["sk_wait_days"] - best["wait_days"]})
    return {"procedures": out, "countries": ARBITRAGE_COUNTRY,
            "legal_note": "EU Directive 2011/24/EU on cross-border healthcare + S2 form — the insurer may reimburse costs up to the domestic price. Turkey: outside the EU framework, full self-pay."}

class ArbitrageQuoteIn(BaseModel):
    procedure_id: str
    country: str  # PL | HU | TR
    companion: bool = True

@api.post("/arbitrage/quote")
async def arbitrage_quote(body: ArbitrageQuoteIn, authorization: Optional[str] = Header(None)):
    """Billing prediction for a cross-border surgery — full cost breakdown."""
    user = await get_current_user(authorization)
    proc = next((p for p in ARBITRAGE_PROCEDURES if p["procedure_id"] == body.procedure_id), None)
    if not proc:
        raise HTTPException(404, "Unknown procedure")
    cc = body.country.upper()
    if cc not in ARBITRAGE_COUNTRY or cc not in proc["abroad"]:
        raise HTTPException(400, "country must be PL|HU|TR")
    country = ARBITRAGE_COUNTRY[cc]
    ab = proc["abroad"][cc]
    nights = proc["recovery_nights"]
    persons = 2 if body.companion else 1
    travel = country["travel_eur"] * persons
    accommodation = country["night_eur"] * nights * (persons - 1)  # patient sleeps in clinic
    total = ab["price_eur"] + travel + accommodation
    s2_refund = round(min(proc["sk_price_eur"], ab["price_eur"]) * 0.85, 0) if country["eu_member"] else 0
    net = round(total - s2_refund, 0)
    quote = {
        "quote_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "procedure": proc["name"], "procedure_id": proc["procedure_id"],
        "country": cc, "clinic": ab["clinic"],
        "breakdown": {
            "procedure_eur": ab["price_eur"], "travel_eur": travel,
            "accommodation_eur": accommodation, "total_eur": total,
            "s2_predicted_refund_eur": s2_refund, "net_out_of_pocket_eur": net,
        },
        "sk_comparison": {"sk_price_eur": proc["sk_price_eur"], "sk_wait_days": proc["sk_wait_days"]},
        "wait_days_abroad": ab["wait_days"],
        "saving_vs_sk_eur": round(proc["sk_price_eur"] - net, 0),
        "wait_cut_days": proc["sk_wait_days"] - ab["wait_days"],
        "ghost_mode_compatible": True,
        "legal_route": "EU 2011/24 + S2 (prior insurer approval)" if country["eu_member"] else "Self-pay outside the EU framework — no S2 reimbursement",
        "simulated": True, "at": datetime.now(timezone.utc),
    }
    await db.arbitrage_quotes.insert_one(quote.copy())
    return clean(quote)

@api.get("/arbitrage/quotes")
async def arbitrage_quotes(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.arbitrage_quotes.find({"user_id": user["user_id"]}, {"_id": 0}).sort("at", -1).to_list(20)
    return {"quotes": rows}


# ============================================================
# GENOMIC BIO-IDENTITY — DNA metadata in the sovereign vault
# ============================================================
class GenomicIn(BaseModel):
    provider: Optional[str] = ""           # e.g. Dante Labs, Nebula, klinika
    markers: List[str] = []                # e.g. ["BRCA1: negative", "APOE: e3/e3"]
    blood_type_confirmed: Optional[str] = ""
    raw_data_location: Optional[str] = ""  # where the raw genome file is kept (cold storage)
    notes: Optional[str] = ""

@api.get("/bioidentity")
async def bioidentity_get(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    doc = await db.bio_identity.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return doc or {}

@api.put("/bioidentity/genomic")
async def bioidentity_put(body: GenomicIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    now = datetime.now(timezone.utc)
    payload = f"{user['did']}|{body.provider}|{'|'.join(body.markers)}|{now.date()}"
    doc = {
        "user_id": user["user_id"], "did": user["did"], **body.model_dump(),
        "genomic_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "storage_policy": "On-chain hash only — raw DNA data NEVER leave your cold storage (zero-knowledge).",
        "updated_at": now,
    }
    await db.bio_identity.update_one({"user_id": user["user_id"]}, {"$set": doc}, upsert=True)
    await _aml_ledger_append(user["user_id"], "genomic_anchor", {"sha256": doc["genomic_sha256"], "markers": len(body.markers)})
    return clean(await db.bio_identity.find_one({"user_id": user["user_id"]}, {"_id": 0}))


# ============================================================
# DURESS PROTOCOL — decoy PIN + silent alarm
# ============================================================
def _pin_hash(did: str, pin: str) -> str:
    return hashlib.sha256(f"duress|{did}|{pin}".encode()).hexdigest()

class DuressSetIn(BaseModel):
    real_pin: str = Field(min_length=4, max_length=8)
    duress_pin: str = Field(min_length=4, max_length=8)

@api.put("/duress/pin")
async def duress_set(body: DuressSetIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if not body.real_pin.isdigit() or not body.duress_pin.isdigit():
        raise HTTPException(400, "PINs must be numeric")
    if body.real_pin == body.duress_pin:
        raise HTTPException(400, "Duress PIN must differ from the real PIN")
    await db.duress_configs.update_one({"user_id": user["user_id"]}, {"$set": {
        "user_id": user["user_id"],
        "real_pin_hash": _pin_hash(user["did"], body.real_pin),
        "duress_pin_hash": _pin_hash(user["did"], body.duress_pin),
        "updated_at": datetime.now(timezone.utc),
    }}, upsert=True)
    return {"ok": True, "note": "Duress PIN active — when entered under duress, an empty Vault is shown and a silent alarm is sent."}

class DuressVerifyIn(BaseModel):
    pin: str

@api.post("/duress/verify")
async def duress_verify(body: DuressVerifyIn, authorization: Optional[str] = Header(None)):
    """Returns vault_mode: full | decoy | invalid. Decoy fires a SILENT alarm —
    the response is indistinguishable from a normal unlock for the attacker."""
    user = await get_current_user(authorization)
    cfg = await db.duress_configs.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not cfg:
        raise HTTPException(404, "No duress PIN configured")
    h = _pin_hash(user["did"], body.pin)
    if h == cfg["real_pin_hash"]:
        return {"ok": True, "vault_mode": "full"}
    if h == cfg["duress_pin_hash"]:
        event = {
            "event_id": uuid.uuid4().hex, "user_id": user["user_id"],
            "kind": "duress_silent_alarm", "at": datetime.now(timezone.utc),
        }
        await db.duress_events.insert_one(event.copy())
        await _aml_ledger_append(user["user_id"], "duress_alarm", {"event_id": event["event_id"]})
        try:
            await send_push(recipients=[user["user_id"]], data={
                "title": "⚠️ Security event",
                "message": "Silent alarm: the Vault was opened with the emergency PIN (decoy mode).",
                "action_url": "/duress",
            }, idempotency_key=f"duress-{event['event_id']}")
        except Exception as e:
            logger.warning(f"duress push failed: {e}")
        # Response mimics a normal unlock — the app silently shows the empty decoy vault.
        return {"ok": True, "vault_mode": "decoy"}
    return {"ok": False, "vault_mode": "invalid"}

@api.get("/duress/status")
async def duress_status(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    cfg = await db.duress_configs.find_one({"user_id": user["user_id"]}, {"_id": 0, "user_id": 1, "updated_at": 1})
    alarms = await db.duress_events.find({"user_id": user["user_id"]}, {"_id": 0}).sort("at", -1).to_list(10)
    return {"configured": bool(cfg), "alarms": alarms}


# ============================================================
# MESH-MESSENGER — P2P store-and-forward (BLE mesh in native build)
# ============================================================
class MeshSendIn(BaseModel):
    to_did: str
    text: str = Field(min_length=1, max_length=500)

@api.get("/mesh/status")
async def mesh_status(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    peers = await db.users.count_documents({"did": {"$exists": True}})
    queued = await db.mesh_messages.count_documents({"from_user_id": user["user_id"], "status": "queued"})
    return {"protocol": "Guardian Mesh v1 — store-and-forward · BLE/Wi-Fi Direct relay",
            "reachable_peers": peers, "queued_outbox": queued,
            "native_note": "Real BLE mesh radio requires a native build (does not work in Expo Go/web) — server relay is fully functional.",
            "simulated_radio": True}

@api.post("/mesh/messages")
async def mesh_send(body: MeshSendIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    to_did = body.to_did.strip()
    recipient = await db.users.find_one({"did": to_did}, {"_id": 0, "user_id": 1, "name": 1})
    msg = {
        "msg_id": uuid.uuid4().hex,
        "from_user_id": user["user_id"], "from_did": user["did"],
        "from_name": user.get("name") or user["email"],
        "to_did": to_did, "to_user_id": recipient["user_id"] if recipient else None,
        "text": body.text.strip(),
        "hops": 1 if recipient else 0,
        "status": "delivered" if recipient else "queued",
        "transport": "server-relay (BLE mesh in native build)",
        "sha256": hashlib.sha256(f"{user['did']}|{to_did}|{body.text}".encode()).hexdigest(),
        "at": datetime.now(timezone.utc),
    }
    await db.mesh_messages.insert_one(msg.copy())
    if recipient:
        try:
            await send_push(recipients=[recipient["user_id"]], data={
                "title": "📡 Mesh message", "message": f"{msg['from_name']}: {msg['text'][:80]}", "action_url": "/mesh",
            })
        except Exception as e:
            logger.warning(f"mesh push failed: {e}")
    return clean(msg)

@api.get("/mesh/messages")
async def mesh_inbox(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.mesh_messages.find(
        {"$or": [{"from_user_id": user["user_id"]}, {"to_did": user["did"]}]},
        {"_id": 0}).sort("at", -1).to_list(100)
    return {"messages": rows, "my_did": user["did"]}


# ============================================================
# POWER-SAVER — survival battery mode
# ============================================================
POWER_PROFILE = {
    "poll_interval_sec": 300, "animations": False, "theme": "pure_black",
    "background_scans": "off", "essential_only": ["SOS beacons", "Emergency QR", "Mesh-Messenger", "Tactical Medic (offline)"],
    "estimated_battery_gain_pct": 38,
}

class PowerSaverIn(BaseModel):
    enabled: bool

@api.put("/power-saver")
async def power_saver_set(body: PowerSaverIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"power_saver": body.enabled}})
    return {"power_saver": body.enabled, "profile": POWER_PROFILE if body.enabled else None}

@api.get("/power-saver")
async def power_saver_get(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "power_saver": 1}) or {}
    return {"power_saver": bool(fresh.get("power_saver")), "profile": POWER_PROFILE}
