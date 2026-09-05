# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""UNIVERSAL HEALTH PROTOCOL (UHP/1.0) — The Mandatory Gate.

Sovereign API Gateway: any clinic, insurer, lab or sensor network can push
data into the Monolith using the proprietary UHP v1 envelope — HMAC-SHA256
signed, replay-protected, idempotent, per-partner rate-limited.
Global Sentinel Network topology is engineered for 1B+ concurrent streams
(region × shard × node fan-out); radio/fleet hardware is simulated in this
deployment, the protocol + routing logic are fully functional.
"""
from fastapi import HTTPException, Header, Request
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
from collections import deque
import uuid, hmac, hashlib, json, time, secrets

from core import api, db, logger, clean, get_current_user, send_push

UHP_VERSION = "UHP/1.0"
VALID_KINDS = ("vitals", "lab_result", "document", "insurance_claim", "sensor", "threat_mesh")
VALID_ORG_TYPES = ("clinic", "insurer", "lab", "sensor_network", "government", "pharmacy")
REPLAY_WINDOW_S = 300
RATE_LIMIT_PER_MIN = 240

# in-memory sliding-window rate limiter (per partner)
_rate: dict = {}

def _rate_ok(partner_id: str) -> bool:
    now = time.time()
    q = _rate.setdefault(partner_id, deque())
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE_LIMIT_PER_MIN:
        return False
    q.append(now)
    return True

# ---------------------------------------------------------------- partners
class PartnerIn(BaseModel):
    org_name: str = Field(min_length=3, max_length=120)
    org_type: str
    country: str = Field(min_length=2, max_length=2)
    contact_email: str

@api.post("/uhp/partners/register")
async def uhp_register(body: PartnerIn):
    if body.org_type not in VALID_ORG_TYPES:
        raise HTTPException(400, f"org_type must be one of {VALID_ORG_TYPES}")
    if "@" not in body.contact_email:
        raise HTTPException(400, "Invalid contact_email")
    partner = {
        "partner_id": f"uhp_{uuid.uuid4().hex[:12]}",
        "api_key": f"uhpk_{secrets.token_hex(16)}",
        "hmac_secret": secrets.token_hex(32),
        "org_name": body.org_name, "org_type": body.org_type,
        "country": body.country.upper(), "contact_email": body.contact_email,
        # SEC: self-registered partners start PENDING — the Foundation approves them before any ingest.
        "status": "pending", "ingested_total": 0,
        "created_at": datetime.now(timezone.utc),
    }
    await db.uhp_partners.insert_one(partner.copy())
    logger.info(f"UHP partner registered: {partner['org_name']} ({partner['partner_id']})")
    return {
        "partner_id": partner["partner_id"], "api_key": partner["api_key"],
        "hmac_secret": partner["hmac_secret"], "protocol": UHP_VERSION,
        "docs": "/api/uhp/standard",
        "note": "Store the hmac_secret securely — it is shown only once.",
    }

# ---------------------------------------------------------------- the standard
@api.get("/uhp/standard")
async def uhp_standard():
    return {
        "protocol": UHP_VERSION,
        "transport": "HTTPS POST /api/uhp/ingest",
        "auth_headers": {
            "X-UHP-Key": "partner api_key",
            "X-UHP-Timestamp": "unix seconds (±300s window, replay-protected)",
            "X-UHP-Signature": "hex(HMAC_SHA256(hmac_secret, '{timestamp}.{raw_body}'))",
        },
        "envelope": {
            "protocol": UHP_VERSION,
            "kind": list(VALID_KINDS),
            "subject": {"email": "patient e-mail OR", "did": "did:guardian:… sovereign ID"},
            "payload": "kind-specific object (vitals: systolic/diastolic/glucose_mmol/heart_rate/spo2)",
            "idempotency_key": "unique per event — duplicates are acknowledged, not re-processed",
            "issued_at": "ISO-8601",
        },
        "rate_limit": f"{RATE_LIMIT_PER_MIN}/min per partner",
        "governance": "Guardian Angel Sovereign Foundation (DAO) — data belongs to the patient; every ingest is auditable by the subject via /api/uhp/feed.",
    }

# ---------------------------------------------------------------- ingest
@api.post("/uhp/ingest")
async def uhp_ingest(request: Request,
                     x_uhp_key: Optional[str] = Header(None),
                     x_uhp_timestamp: Optional[str] = Header(None),
                     x_uhp_signature: Optional[str] = Header(None)):
    if not (x_uhp_key and x_uhp_timestamp and x_uhp_signature):
        raise HTTPException(401, "Missing UHP auth headers")
    partner = await db.uhp_partners.find_one({"api_key": x_uhp_key, "status": "active"}, {"_id": 0})
    if not partner:
        raise HTTPException(401, "Unknown or suspended partner key")
    # replay protection
    try:
        ts = int(x_uhp_timestamp)
    except ValueError:
        raise HTTPException(401, "Invalid timestamp")
    if abs(time.time() - ts) > REPLAY_WINDOW_S:
        raise HTTPException(401, "Timestamp outside replay window")
    raw = await request.body()
    expected = hmac.new(partner["hmac_secret"].encode(),
                        f"{x_uhp_timestamp}.".encode() + raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, x_uhp_signature):
        raise HTTPException(401, "Invalid HMAC signature")
    if not _rate_ok(partner["partner_id"]):
        raise HTTPException(429, f"Rate limit {RATE_LIMIT_PER_MIN}/min exceeded")
    # envelope validation
    try:
        env = json.loads(raw)
    except Exception:
        raise HTTPException(400, "Body must be JSON")
    if env.get("protocol") != UHP_VERSION:
        raise HTTPException(400, f"protocol must be '{UHP_VERSION}'")
    kind = env.get("kind")
    if kind not in VALID_KINDS:
        raise HTTPException(400, f"kind must be one of {VALID_KINDS}")
    subject = env.get("subject") or {}
    payload = env.get("payload") or {}
    idem = str(env.get("idempotency_key") or "")
    if not idem:
        raise HTTPException(400, "idempotency_key required")
    # idempotency — acknowledge duplicates without reprocessing
    dup = await db.uhp_events.find_one({"partner_id": partner["partner_id"], "idempotency_key": idem}, {"_id": 0})
    if dup:
        return {"accepted": True, "duplicate": True, "event_id": dup["event_id"], "protocol": UHP_VERSION}
    # subject resolution (optional for sensor/threat_mesh streams)
    user = None
    if subject.get("email"):
        user = await db.users.find_one({"email": subject["email"]}, {"_id": 0, "user_id": 1})
    elif subject.get("did"):
        user = await db.users.find_one({"did": subject["did"]}, {"_id": 0, "user_id": 1})
    if kind in ("vitals", "lab_result", "document", "insurance_claim"):
        # SEC: uniform error (no account enumeration) + explicit PATIENT CONSENT for this partner.
        consent = user and await db.uhp_consents.find_one({"user_id": user["user_id"], "partner_id": partner["partner_id"], "active": True}, {"_id": 1})
        if not user or not consent:
            raise HTTPException(403, "consent_required: the patient has not linked this partner in Guardian (Settings → Health partners)")
    event = {
        "event_id": f"uhpe_{uuid.uuid4().hex[:16]}",
        "partner_id": partner["partner_id"], "partner_name": partner["org_name"],
        "kind": kind, "user_id": user["user_id"] if user else None,
        "payload": payload, "idempotency_key": idem,
        "issued_at": env.get("issued_at"), "at": datetime.now(timezone.utc),
    }
    await db.uhp_events.insert_one(event.copy())
    await db.uhp_partners.update_one({"partner_id": partner["partner_id"]}, {"$inc": {"ingested_total": 1}})
    routed = "uhp_events"
    # kind-specific routing into the sovereign data plane
    if kind == "vitals" and user:
        rec = {"scan_id": f"uhp-{uuid.uuid4().hex[:10]}", "user_id": user["user_id"],
               "method": f"uhp_partner:{partner['org_name']}", "at": datetime.now(timezone.utc)}
        if payload.get("systolic") and payload.get("diastolic"):
            rec["bp_estimate"] = f"{int(payload['systolic'])}/{int(payload['diastolic'])}"
        for k in ("glucose_mmol", "heart_rate", "spo2"):
            if payload.get(k) is not None:
                rec[k] = payload[k]
        await db.bioscan_results.insert_one(rec)
        routed = "bioscan_results"
        try:
            await send_push(recipients=[user["user_id"]], data={
                "title": f"🏥 {partner['org_name']} — new vital data",
                "message": "The clinic securely inserted the measurement via Universal Health Protocol.",
                "action_url": "/bioscan"})
        except Exception:
            pass
    elif kind in ("sensor", "threat_mesh"):
        await db.sentinel_streams.update_one(
            {"stream_key": f"{partner['partner_id']}:{payload.get('stream_id', 'default')}"},
            {"$set": {"kind": kind, "last_at": datetime.now(timezone.utc)},
             "$inc": {"events": 1},
             "$setOnInsert": {"partner_id": partner["partner_id"], "opened_at": datetime.now(timezone.utc)}},
            upsert=True)
        routed = "sentinel_streams"
    return {"accepted": True, "duplicate": False, "event_id": event["event_id"],
            "routed_to": routed, "protocol": UHP_VERSION}

# ---------------------------------------------------------------- telemetry
@api.get("/uhp/partners/{partner_id}/stats")
async def uhp_partner_stats(partner_id: str, x_uhp_key: Optional[str] = Header(None)):
    partner = await db.uhp_partners.find_one({"partner_id": partner_id}, {"_id": 0, "hmac_secret": 0})
    if not partner or partner.get("api_key") != x_uhp_key:
        raise HTTPException(401, "Partner key mismatch")
    partner.pop("api_key", None)
    by_kind = await db.uhp_events.aggregate([
        {"$match": {"partner_id": partner_id}},
        {"$group": {"_id": "$kind", "count": {"$sum": 1}}}]).to_list(10)
    return {"partner": clean(partner), "by_kind": {b["_id"]: b["count"] for b in by_kind}}

# Global Sentinel Network capacity — region × shard × node fan-out (≥ 1B streams)
TOPOLOGY = {"regions": 12, "shards_per_region": 4096, "nodes_per_shard": 32, "streams_per_node": 650}

@api.get("/uhp/capacity")
async def uhp_capacity(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    cap = (TOPOLOGY["regions"] * TOPOLOGY["shards_per_region"]
           * TOPOLOGY["nodes_per_shard"] * TOPOLOGY["streams_per_node"])
    partners = await db.uhp_partners.count_documents({"status": "active"})
    events = await db.uhp_events.count_documents({})
    streams = await db.sentinel_streams.count_documents({})
    return {
        "protocol": UHP_VERSION, "topology": TOPOLOGY,
        "stream_capacity": cap,                      # 1 022 361 600 concurrent streams
        "stream_capacity_human": f"{cap / 1e9:.2f} B",
        "active_partners": partners, "open_streams": streams,
        "events_ingested_total": events,
        "utilization_pct": round(streams / cap * 100, 8),
        "replication_factor": 3, "consensus": "Raft per shard, CRDT edge-merge",
        "note": "Fleet hardware simulated in this deployment — protocol, routing and auth are production logic.",
    }

@api.get("/uhp/feed")
async def uhp_feed(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.uhp_events.find({"user_id": user["user_id"]}, {"_id": 0}).sort("at", -1).to_list(30)
    return {"events": clean(rows)}



# ---------------------------------------------------------------- vetting & consent (SEC re-audit)
async def _require_foundation(authorization: Optional[str]) -> dict:
    user = await get_current_user(authorization)
    if not (user.get("is_founder") or user.get("inner_circle")):
        raise HTTPException(403, "foundation only")
    return user


@api.get("/uhp/partners/pending")
async def uhp_partners_pending(authorization: Optional[str] = Header(None)):
    await _require_foundation(authorization)
    rows = await db.uhp_partners.find({"status": "pending"}, {"_id": 0, "api_key": 0, "hmac_secret": 0}).sort("created_at", -1).to_list(100)
    return {"partners": rows}


@api.post("/uhp/partners/{partner_id}/approve")
async def uhp_partner_approve(partner_id: str, authorization: Optional[str] = Header(None)):
    admin = await _require_foundation(authorization)
    res = await db.uhp_partners.update_one({"partner_id": partner_id, "status": "pending"},
                                           {"$set": {"status": "active", "approved_at": datetime.now(timezone.utc), "approved_by": admin["user_id"]}})
    if not res.modified_count:
        raise HTTPException(404, "no pending partner with this id")
    return {"ok": True, "partner_id": partner_id, "status": "active"}


@api.post("/uhp/partners/{partner_id}/suspend")
async def uhp_partner_suspend(partner_id: str, authorization: Optional[str] = Header(None)):
    await _require_foundation(authorization)
    res = await db.uhp_partners.update_one({"partner_id": partner_id}, {"$set": {"status": "suspended", "suspended_at": datetime.now(timezone.utc)}})
    if not res.matched_count:
        raise HTTPException(404, "partner not found")
    return {"ok": True, "partner_id": partner_id, "status": "suspended"}


class ConsentIn(BaseModel):
    partner_id: str


@api.get("/uhp/consents")
async def uhp_consents_list(authorization: Optional[str] = Header(None)):
    """Patient view: which approved partners may write into my health record."""
    user = await get_current_user(authorization)
    rows = await db.uhp_consents.find({"user_id": user["user_id"], "active": True}, {"_id": 0}).to_list(50)
    partners = await db.uhp_partners.find({"status": "active"}, {"_id": 0, "partner_id": 1, "org_name": 1, "org_type": 1, "country": 1}).to_list(200)
    return {"consents": rows, "partners": partners}


@api.post("/uhp/consents", status_code=201)
async def uhp_consent_grant(body: ConsentIn, authorization: Optional[str] = Header(None)):
    """Patient explicitly links an APPROVED partner — only then may that partner ingest data for them."""
    user = await get_current_user(authorization)
    partner = await db.uhp_partners.find_one({"partner_id": body.partner_id, "status": "active"}, {"_id": 0, "org_name": 1})
    if not partner:
        raise HTTPException(404, "partner not found or not approved")
    now = datetime.now(timezone.utc)
    await db.uhp_consents.update_one({"user_id": user["user_id"], "partner_id": body.partner_id},
                                     {"$set": {"active": True, "granted_at": now, "partner_name": partner["org_name"]}}, upsert=True)
    return {"ok": True, "partner_id": body.partner_id, "partner_name": partner["org_name"]}


@api.delete("/uhp/consents/{partner_id}")
async def uhp_consent_revoke(partner_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await db.uhp_consents.update_one({"user_id": user["user_id"], "partner_id": partner_id},
                                     {"$set": {"active": False, "revoked_at": datetime.now(timezone.utc)}})
    return {"ok": True}
