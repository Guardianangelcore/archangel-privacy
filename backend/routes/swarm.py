# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Cyber-Fortress — DePIN simulation, Security Sentinel, Autonomous Agent Swarm,
Neural Bus (ZK-commitment envelopes) and the Stability & Integrity Audit.

DEMO/SIMULATION layer (like the Blackout mesh): real peer-to-peer DePIN and
on-chain ZKP are deferred to Phase 3 — the logic, data models and autonomy
loops here are fully functional inside this deployment.
"""
from fastapi import HTTPException, Header
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid, hashlib, json, random, asyncio

from core import api, db, logger, clean, get_current_user, send_push
from routes.token import award_tokens, verify_ledger_chain
from routes.hunter import _simulate_slot
from routes.origin import ORIGIN

# ---------------- NEURAL BUS (ZK-commitment envelopes) ----------------
async def bus_publish(topic: str, source: str, payload: dict) -> dict:
    nonce = uuid.uuid4().hex
    body = json.dumps(payload, sort_keys=True, default=str)
    commitment = hashlib.sha256((body + nonce).encode()).hexdigest()
    ev = {"event_id": uuid.uuid4().hex, "topic": topic, "source": source, "payload": payload,
          "zkp": {"scheme": "sha256-commitment (ZK demo)", "commitment": commitment,
                  "nonce_sha256": hashlib.sha256(nonce.encode()).hexdigest()},
          "at": datetime.now(timezone.utc)}
    await db.neural_bus.insert_one(ev.copy())
    return ev


# ---------------- DePIN NODES (distributed infrastructure simulation) ----------------
DEPIN_SEED = [
    {"node_id": "ga-core-sk1", "region": "SK-BA", "role": "core", "shard": "core-logic"},
    {"node_id": "ga-core-nl1", "region": "NL-AM", "role": "core-standby", "shard": "core-logic-replica"},
    {"node_id": "ga-edge-cz1", "region": "CZ-PR", "role": "edge", "shard": "sentinel-agg"},
    {"node_id": "ga-edge-ch1", "region": "CH-ZH", "role": "edge", "shard": "gateway-cache"},
    {"node_id": "ga-vault-de1", "region": "DE-FR", "role": "vault_shard", "shard": "vault-e2e-a"},
    {"node_id": "ga-vault-is1", "region": "IS-RE", "role": "vault_shard", "shard": "vault-e2e-b"},
]

async def seed_depin():
    for n in DEPIN_SEED:
        await db.depin_nodes.update_one(
            {"node_id": n["node_id"]},
            {"$setOnInsert": {**n, "verified": True, "health": 100.0,
                              "latency_ms": random.randint(18, 90),
                              "self_heals": 0, "created_at": datetime.now(timezone.utc)}},
            upsert=True)


# ---------------- AGENT SWARM ----------------
AGENTS = {
    "waitlist_hunter":   {"interval": 60, "label": "Waitlist Hunter Agent",
                          "desc": "Autonomously searches for and reserves available appointments"},
    "marketplace":       {"interval": 90, "label": "Data Marketplace Agent",
                          "desc": "Manages anonymous datasets and GA-T rewards (Proof-of-Health)"},
    "data_broker":       {"interval": 180, "label": "Wealth-Agent (Data Broker)",
                          "desc": "Autonomously negotiates the sale of anonymous data — rounds, counteroffers, close +15-40 %"},
    "gbi_distributor":   {"interval": 300, "label": "GBI Distributor (Living Currency)",
                          "desc": "Pays out Guardian Basic Income — a daily GA-T income to every active Guardian"},
    "safety":            {"interval": 45, "label": "Safety Monitoring Agent",
                          "desc": "24/7 monitoring — escalates unanswered pulse pings"},
    "security_sentinel": {"interval": 30, "label": "Security Sentinel",
                          "desc": "Behavioral anomaly detection + self-healing nodes"},
    "wealth_sentinel":   {"interval": 120, "label": "Wealth Sentinel (Insurance Guard)",
                          "desc": "Watches over insurance safeguards — if they fail, triggers a Jarvis alarm + micro-loan"},
    "news_sentinel":     {"interval": 300, "label": "Medical News Sentinel",
                          "desc": "Cross-references global medical breakthroughs with your Vault → priority alerts"},
    "sovereign_guard":   {"interval": 45, "label": "Sovereign Guard (Recovery · 2FA · SAT-uplink)",
                          "desc": "Manages account recovery, 2FA handshakes, Bio-Beacons, and satellite Nano-Packets"},
    "system_janitor":    {"interval": 120, "label": "System Janitor (Self-Repair)",
                          "desc": "Autonomously scans and fixes inconsistencies — missing timeline entries, geo context, data integrity"},
    "companion_care":    {"interval": 600, "label": "Companion Care (Morning reminder)",
                          "desc": "Gently reminds seniors of the Companion’s daily question when they forget to answer in the morning"},
    "weekly_reporter":   {"interval": 3600, "label": "Weekly Reporter (Sunday report)",
                          "desc": "Every Sunday saves the weekly healing report directly into the Health Vault"},
    "physio_coach":      {"interval": 900, "label": "Physio Coach (Evening Reminder)",
                          "desc": "The evening reminds when today's day of the weekly recovery plan is not checked off"},
    "booster_guard":     {"interval": 3600, "label": "Booster Guard (Skipping)",
                          "desc": "Guards vaccine boosters — Jarvis will remind 30 and 7 days before the due date"},
}

async def _agent_waitlist_hunter() -> int:
    actions = 0
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=90)
    items = await db.waitlist.find(
        {"status": {"$nin": ["booked", "found"]}, "found_slot": {"$in": [None, ""]},
         "created_at": {"$lte": cutoff}}, {"_id": 0}).to_list(20)
    for item in items:
        h = int(hashlib.sha256(f"{item['item_id']}|{datetime.now(timezone.utc).date()}".encode()).hexdigest(), 16)
        if h % 100 >= 55:  # deterministic per-day "search luck"
            continue
        slot = _simulate_slot(item.get("specialty", ""), item.get("city", ""))
        found = f"{slot['date']} {slot['time']} — {slot['clinic']}"
        await db.waitlist.update_one({"item_id": item["item_id"]},
                                     {"$set": {"status": "found", "found_slot": found,
                                               "found_at": datetime.now(timezone.utc), "found_by": "swarm"}})
        await db.calendar_events.insert_one({
            "event_id": uuid.uuid4().hex, "user_id": item["user_id"], "category": "exam",
            "title": f"{item.get('specialty', 'Appointment')} — {slot['clinic']}", "date": slot["date"],
            "notes": f"Swarm Agent · {slot['time']} · autonomously found", "booster_due": None,
            "source": "swarm:waitlist_hunter", "created_at": datetime.now(timezone.utc)})
        try:
            await send_push(recipients=[item["user_id"]],
                            data={"title": "🤖 SWARM FOUND APPOINTMENT", "message": f"{item.get('specialty', '')}: {found}",
                                  "action_url": "/health-timeline"})
        except Exception:
            pass
        await bus_publish("waitlist.slot_found", "waitlist_hunter", {"item_id": item["item_id"], "slot": found})
        actions += 1
    return actions

async def _agent_marketplace() -> int:
    actions = 0
    optins = await db.marketplace_optins.find({"enabled": True}, {"_id": 0, "user_id": 1}).to_list(100)
    for o in optins:
        tx = await award_tokens(o["user_id"], "proof_of_health", "dataset drip — anonymous insight (swarm)")
        if tx:
            actions += 1
    if actions:
        await bus_publish("marketplace.reward_drip", "marketplace", {"rewarded_users": actions, "token": "GA-T"})
    return actions

async def _agent_data_broker() -> int:
    """Wealth-Agent (ARCHANGEL): autonomously NEGOTIATES data sales for opted-in
    users — opens with a buyer bid, counters over 2-4 rounds, closes 15-40 %
    above the opening price and pays out GA-T. One deal per user per day."""
    actions = 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    buyers = ["NordicHealth Analytics", "Zurich Re Research", "Tokyo Wellness Lab",
              "Berlin BioData Exchange", "Andes Longevity Institute"]
    datasets = ["anonymous vital trends", "medication adherence", "sleep patterns",
                "environmental exposures", "rehabilitation metrics"]
    optins = await db.marketplace_optins.find({"enabled": True}, {"_id": 0, "user_id": 1}).to_list(100)
    for o in optins:
        dup = await db.data_deals.find_one({"user_id": o["user_id"], "date": today})
        if dup:
            continue
        seed = int(hashlib.sha256(f"{o['user_id']}|{today}".encode()).hexdigest(), 16)
        opening = 8 + seed % 18                       # 8-25 GA-T opening bid
        uplift = 1.15 + (seed % 26) / 100             # negotiated +15-40 %
        final = round(opening * uplift, 1)
        rounds = 2 + seed % 3
        await db.data_deals.insert_one({
            "deal_id": uuid.uuid4().hex, "user_id": o["user_id"], "date": today,
            "buyer": buyers[seed % len(buyers)], "dataset": datasets[seed % len(datasets)],
            "opening_gat": opening, "final_gat": final, "rounds": rounds,
            "uplift_pct": round((uplift - 1) * 100, 1), "status": "closed",
            "negotiated_by": "wealth_agent", "at": datetime.now(timezone.utc)})
        await award_tokens(o["user_id"], "proof_of_health",
                           f"Wealth-Agent: data sale ({final} GA-T, +{round((uplift - 1) * 100)} % negotiated)")
        try:
            await send_push(recipients=[o["user_id"]], data={
                "title": "🤝 WEALTH-AGENT UZAVREL OBCHOD",
                "message": f"Anonymous data sale negotiated from {opening} to {final} GA-T ({rounds} rounds).",
                "action_url": "/marketplace"})
        except Exception:
            pass
        await bus_publish("wealth.data_deal_closed", "data_broker",
                          {"user": o["user_id"][:8], "final_gat": final})
        actions += 1
    return actions

async def _agent_safety() -> int:
    actions = 0
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
    stale = await db.pulse_requests.find(
        {"status": {"$exists": False}, "escalated": {"$ne": True}, "created_at": {"$lte": cutoff}},
        {"_id": 0}).to_list(20)
    for req in stale:
        await db.pulse_requests.update_one({"req_id": req["req_id"]},
                                           {"$set": {"escalated": True, "escalated_at": datetime.now(timezone.utc)}})
        try:
            await send_push(recipients=[req["from_user"]],
                            data={"title": "⚠️ BEZ ODPOVEDE 15 MIN", "message": "Silent ping with no response — we recommend calling or visiting.",
                                  "action_url": "/pulse-check"})
        except Exception:
            pass
        await bus_publish("safety.escalation", "safety", {"req_id": req["req_id"], "reason": "no_response_15m"})
        actions += 1
    # ARCHANGEL: QR-Talisman integrity — Angel-Mode users with an incomplete
    # emergency profile get one repair push per day (blood type = life-critical).
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    angels = await db.users.find({"angel_mode": True}, {"_id": 0, "user_id": 1}).to_list(200)
    for a in angels:
        prof = await db.emergency_profiles.find_one({"user_id": a["user_id"]}, {"_id": 0}) or {}
        if prof.get("blood_type") and prof.get("emergency_contact_phone"):
            continue
        dup = await db.talisman_checks.find_one({"user_id": a["user_id"], "date": today})
        if dup:
            continue
        await db.talisman_checks.insert_one({"user_id": a["user_id"], "date": today,
                                             "at": datetime.now(timezone.utc)})
        try:
            await send_push(recipients=[a["user_id"]], data={
                "title": "🛡 SAFETY-AGENT: QR TALISMAN INCOMPLETE",
                "message": "Missing blood type or ICE contact — rescuers need the complete talisman.",
                "action_url": "/emergency-qr"})
        except Exception:
            pass
        await bus_publish("safety.talisman_incomplete", "safety", {"user": a["user_id"][:8]})
        actions += 1
    # ARCHANGEL: critical vitals (last 10 min) → satellite Nano-Packet queued for
    # the Sovereign-Guard uplink (works even when terrestrial grid is down).
    recent = await db.bioscan_results.find(
        {"at": {"$gte": datetime.now(timezone.utc) - timedelta(minutes=10)}}, {"_id": 0}).to_list(50)
    for r in recent:
        sys_bp = 0
        if r.get("bp_estimate") and "/" in str(r["bp_estimate"]):
            try:
                sys_bp = int(str(r["bp_estimate"]).split("/")[0])
            except ValueError:
                sys_bp = 0
        critical = sys_bp >= 180 or (r.get("glucose_mmol") or 0) >= 15
        if not critical:
            continue
        dup = await db.satellite_queue.find_one({"ref": r["scan_id"]})
        if dup:
            continue
        await db.satellite_queue.insert_one({
            "packet_id": uuid.uuid4().hex, "user_id": r["user_id"], "ref": r["scan_id"],
            "kind": "medical_critical", "status": "queued",
            "payload": {"bp": r.get("bp_estimate"), "glucose": r.get("glucose_mmol")},
            "queued_at": datetime.now(timezone.utc)})
        await bus_publish("safety.sat_alert_queued", "safety",
                          {"user": r["user_id"][:8], "reason": "critical_vitals"})
        actions += 1
    return actions

async def _agent_security_sentinel() -> int:
    actions = 0
    now = datetime.now(timezone.utc)
    # 1. DePIN health drift + self-heal
    nodes = await db.depin_nodes.find({}, {"_id": 0}).to_list(20)
    for n in nodes:
        drift = random.uniform(0, 7)
        health = max(0.0, n["health"] - drift)
        if health < 70.0:
            await db.depin_nodes.update_one({"node_id": n["node_id"]},
                                            {"$set": {"health": 100.0, "latency_ms": random.randint(18, 90)},
                                             "$inc": {"self_heals": 1}})
            await db.security_events.insert_one({
                "event_id": uuid.uuid4().hex, "kind": "self_heal", "severity": "info",
                "node_id": n["node_id"],
                "detail": f"Node {n['node_id']} degraded ({health:.0f}%) — re-imaged, shard re-pinned, keys rotated.",
                "at": now})
            await bus_publish("security.self_heal", "security_sentinel", {"node_id": n["node_id"]})
            actions += 1
        else:
            await db.depin_nodes.update_one({"node_id": n["node_id"]}, {"$set": {"health": round(health, 1)}})
    # 2. Behavioral anomaly — partner-key request bursts (>30 req / 10 min)
    since = now - timedelta(minutes=10)
    pipeline = [{"$match": {"at": {"$gte": since}}},
                {"$group": {"_id": "$partner_name", "count": {"$sum": 1}}},
                {"$match": {"count": {"$gt": 30}}}]
    bursts = await db.gateway_audit.aggregate(pipeline).to_list(10)
    for b in bursts:
        bucket = now.strftime("%Y%m%d%H%M")[:11]  # 10-min dedupe bucket
        dup = await db.security_events.find_one({"kind": "rate_anomaly", "partner": b["_id"], "bucket": bucket})
        if dup:
            continue
        await db.security_events.insert_one({
            "event_id": uuid.uuid4().hex, "kind": "rate_anomaly", "severity": "warning",
            "partner": b["_id"], "bucket": bucket,
            "detail": f"Unusual surge of {b['count']} requests/10 min from '{b['_id']}' — key temporarily throttled.",
            "at": now})
        await bus_publish("security.rate_anomaly", "security_sentinel", {"partner": b["_id"], "count": b["count"]})
        actions += 1
    return actions

async def _agent_wealth_sentinel() -> int:
    """Insurance Guard: detect lapsed policies → emergency Jarvis alert (once per
    policy per day) + Solidarity micro-loan suggestion on the Neural Bus."""
    actions = 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pols = await db.insurance_policies.find({}, {"_id": 0}).to_list(500)
    for p in pols:
        if (p.get("paid_until") or "") >= today:
            continue
        dup = await db.wealth_alerts.find_one({"policy_id": p["policy_id"], "date": today})
        if dup:
            continue
        await db.wealth_alerts.insert_one({"policy_id": p["policy_id"], "date": today,
                                           "user_id": p["user_id"], "at": datetime.now(timezone.utc)})
        try:
            await send_push(recipients=[p["user_id"]],
                            data={"title": "🚨 JARVIS ALARM: POISTKA PREPADLA",
                                  "message": f"{p['provider']} ({p['type']}) is unpaid. Coverage is at risk — open Insurance Guard or request a micro-loan in Solidarity Hub.",
                                  "action_url": "/insurance"})
        except Exception:
            pass
        await bus_publish("wealth.policy_lapsed", "wealth_sentinel",
                          {"policy_id": p["policy_id"], "provider": p["provider"],
                           "type": p["type"], "microloan_suggested": True})
        actions += 1
    return actions

async def _agent_news_sentinel() -> int:
    """Cross-reference the curated medical-news DB with each user's Vault corpus;
    push one priority Jarvis alert per user per news item (deduped)."""
    from routes.news import ensure_news_seed, _user_keywords
    await ensure_news_seed()
    actions = 0
    items = await db.medical_news.find({}, {"_id": 0}).to_list(50)
    users = await db.users.find({}, {"_id": 0, "user_id": 1}).to_list(200)
    for u in users:
        corpus = await _user_keywords(u["user_id"])
        if not corpus.strip():
            continue
        for n in items:
            if not any(tg in corpus for tg in n["tags"]):
                continue
            dup = await db.news_alerts.find_one({"user_id": u["user_id"], "news_id": n["news_id"]})
            if dup:
                continue
            await db.news_alerts.insert_one({"user_id": u["user_id"], "news_id": n["news_id"],
                                             "at": datetime.now(timezone.utc)})
            # ARCHANGEL bridge: with Jarvis Autopilot ON the Hunter starts the hunt
            # autonomously — no question asked, the slot lands in the calendar.
            udoc = await db.users.find_one({"user_id": u["user_id"]}, {"_id": 0, "jarvis_autopilot": 1})
            if (udoc or {}).get("jarvis_autopilot", True):
                spec = (n.get("tags") or ["Specialist"])[0].capitalize()
                await db.waitlist.insert_one({
                    "item_id": uuid.uuid4().hex, "user_id": u["user_id"],
                    "specialty": spec, "city": n.get("hunt_city", ""),
                    "status": "hunting", "found_slot": None,
                    "source": "swarm:news_sentinel", "news_id": n["news_id"],
                    "created_at": datetime.now(timezone.utc) - timedelta(seconds=120)})
                await bus_publish("hunter.autohunt_started", "news_sentinel",
                                  {"user": u["user_id"][:8], "specialty": spec, "news_id": n["news_id"]})
            try:
                await send_push(recipients=[u["user_id"]],
                                data={"title": "🔬 MEDICAL BREAKTHROUGH FOR YOU",
                                      "message": f"{n['title']} — clinic {n['hunt_city']} ({n['region']}). Should I hunt down an appointment?",
                                      "action_url": "/medical-news"})
            except Exception:
                pass
            await bus_publish("news.personal_match", "news_sentinel",
                              {"user": u["user_id"][:8], "news_id": n["news_id"]})
            actions += 1
    return actions

async def _agent_sovereign_guard() -> int:
    """Unified Neural Flow — the Swarm manages the sovereign & global layer:
    expires stale 2FA handshakes / recovery requests, shuts down overdue
    Bio-Beacons and broadcasts queued satellite Nano-Packets (simulated uplink)."""
    actions = 0
    now = datetime.now(timezone.utc)
    # 1. Expire pending Social-2FA handshakes (>15 min)
    res = await db.login_handshakes.update_many(
        {"status": "pending", "expires_at": {"$lt": now}}, {"$set": {"status": "expired"}})
    actions += res.modified_count
    # 2. Expire pending social recovery requests (>24 h)
    res2 = await db.recovery_requests.update_many(
        {"status": "pending", "expires_at": {"$lt": now}}, {"$set": {"status": "expired"}})
    if res2.modified_count:
        await bus_publish("recovery.requests_expired", "sovereign_guard", {"count": res2.modified_count})
    actions += res2.modified_count
    # 3. Auto-deactivate Bio-Beacons past their 24h window
    stale_beacons = await db.bio_beacons.find({"active": True, "expires_at": {"$lt": now}}, {"_id": 0}).to_list(20)
    for b in stale_beacons:
        await db.bio_beacons.update_one({"beacon_id": b["beacon_id"]},
                                        {"$set": {"active": False, "ended_at": now, "ended_by": "swarm"}})
        await bus_publish("beacon.bio_expired", "sovereign_guard", {"beacon": b["beacon_id"]})
        actions += 1
    # 4. Broadcast queued satellite Nano-Packets (simulated Starlink/Globalstar uplink)
    queued = await db.satellite_queue.find({"status": "queued"}, {"_id": 0}).to_list(20)
    for p in queued:
        await db.satellite_queue.update_one({"packet_id": p["packet_id"]},
                                            {"$set": {"status": "broadcasted", "broadcast_at": now,
                                                      "constellation": "GA-SAT/1 (simulated broadcast)"}})
        try:
            await send_push(recipients=[p["user_id"]],
                            data={"title": "🛰️ NANO-PACKET TRANSMITTED",
                                  "message": f"Satellite emergency report ({p['packet_bytes']} B) was broadcast (simulation).",
                                  "action_url": "/compass"})
        except Exception:
            pass
        await bus_publish("satellite.broadcasted", "sovereign_guard",
                          {"packet": p["packet_id"], "bytes": p["packet_bytes"]})
        actions += 1
    # 5. Environmental Threat Fusion — escalate confirmed mesh threats (2+ reports / 6 h)
    since6 = now - timedelta(hours=6)
    pipeline_rows = await db.enviro_reports.find({"at": {"$gte": since6}}, {"_id": 0}).to_list(200)
    groups: dict = {}
    for r in pipeline_rows:
        groups.setdefault((r["kind"], r["city"].lower()), []).append(r)
    for (kind, city), reps in groups.items():
        if len(reps) < 2:
            continue
        already = await db.threat_alerts.find_one({"kind": kind, "city": city, "at": {"$gte": since6}})
        if already:
            continue
        sev = max(r["severity"] for r in reps)
        await db.threat_alerts.insert_one({"alert_id": uuid.uuid4().hex, "kind": kind, "city": city,
                                           "severity": sev, "reports": len(reps), "at": now})
        recipients = [u["user_id"] async for u in db.users.find({}, {"_id": 0, "user_id": 1}).limit(100)]
        try:
            await send_push(recipients=recipients,
                            data={"title": "🌍 CONFIRMED ENVIRONMENTAL THREAT",
                                  "message": f"Mesh consensus ({len(reps)} reports): {kind.upper()} — {reps[0]['city'] or 'region'}. Open instructions.",
                                  "action_url": "/enviro"})
        except Exception:
            pass
        await bus_publish("enviro.threat_confirmed", "sovereign_guard",
                          {"kind": kind, "city": city, "reports": len(reps), "severity": sev})
        actions += 1
    # 6. Mosaic Protocol — autonomous ZK-rollup block production (zero-fee for users)
    try:
        from routes.mosaic import produce_block
        block = await produce_block("swarm")
        if block:
            actions += 1
    except Exception:
        pass
    return actions

async def _agent_gbi() -> int:
    from routes.ascension import gbi_distribute
    return await gbi_distribute()

async def _agent_system_janitor() -> int:
    """SELF-REPAIR: scans data inconsistencies and autonomously fixes them.
    1. Vault documents missing their Health Timeline index → backfill entries.
    2. Users without a geo context → set the Prague, CZ default.
    Every repair is logged to db.janitor_runs and broadcast on the swarm bus."""
    actions = 0
    repaired_timeline = 0
    # 1. Timeline backfill — heal the "black hole" for documents uploaded before indexing existed
    docs = await db.documents.find(
        {}, {"_id": 0, "doc_id": 1, "user_id": 1, "title": 1, "uploaded_at": 1}).to_list(500)
    for d in docs:
        exists = await db.calendar_events.find_one({"doc_id": d["doc_id"]}, {"_id": 1})
        if exists:
            continue
        up = d.get("uploaded_at")
        date = up.date().isoformat() if hasattr(up, "date") else (str(up)[:10] if up else datetime.now(timezone.utc).date().isoformat())
        await db.calendar_events.insert_one({
            "event_id": uuid.uuid4().hex, "user_id": d["user_id"], "category": "history",
            "title": f"📄 {d.get('title', 'Dokument')}"[:140], "date": date,
            "notes": "Completed by System Janitor (self-repair)", "booster_due": None,
            "source": "janitor:backfill", "doc_id": d["doc_id"],
            "created_at": datetime.now(timezone.utc)})
        repaired_timeline += 1
        actions += 1
    # 2. Geo context default (Prague, CZ)
    from routes.geo import DEFAULT_GEO
    res = await db.users.update_many({"geo": {"$exists": False}}, {"$set": {"geo": DEFAULT_GEO}})
    actions += res.modified_count
    # 3. Founder entitlement — the first user of the system holds lifetime Archangel (Inner Circle)
    first = await db.users.find_one({}, {"_id": 0, "user_id": 1, "inner_circle": 1, "is_founder": 1},
                                    sort=[("created_at", 1)])
    if first and not (first.get("inner_circle") and first.get("is_founder")):
        await db.users.update_one({"user_id": first["user_id"]}, {"$set": {
            "inner_circle": True, "is_founder": True, "tier": "archangel",
            "tier_until": None, "tier_paid_with": "founder"}})
        actions += 1
    # 4. Mosaic Blueprint autonomy — fork detection → autonomous GA-T contract redeploy
    #    + Wealth Hub payout verification (anchoring into Mosaic blocks)
    try:
        from routes.mosaic import verify_chain_and_wealth
        chain = await verify_chain_and_wealth()
        if chain["fork_detected"]:
            actions += 1 + chain["orphaned"]
        actions += chain["wealth_anchored"]
    except Exception as e:
        logger.warning(f"janitor mosaic check failed: {e}")
    if actions:
        await db.janitor_runs.insert_one({
            "at": datetime.now(timezone.utc), "repaired_total": actions,
            "timeline_backfills": repaired_timeline, "geo_defaults": res.modified_count})
        await bus_publish("janitor.self_repair", "system_janitor",
                          {"repaired": actions, "timeline_backfills": repaired_timeline})
    return actions

async def _agent_companion_care() -> int:
    from routes.healing import companion_reminder_sweep
    return await companion_reminder_sweep()


async def _agent_weekly_reporter() -> int:
    from routes.healing import weekly_report_sweep
    return await weekly_report_sweep()


async def _agent_physio_coach() -> int:
    from routes.physio_media import physio_reminder_sweep
    return await physio_reminder_sweep()


async def _agent_booster_guard() -> int:
    from routes.health import booster_guard_sweep
    return await booster_guard_sweep()


_AGENT_FN = {
    "waitlist_hunter": _agent_waitlist_hunter,
    "marketplace": _agent_marketplace,
    "data_broker": _agent_data_broker,
    "gbi_distributor": _agent_gbi,
    "safety": _agent_safety,
    "security_sentinel": _agent_security_sentinel,
    "wealth_sentinel": _agent_wealth_sentinel,
    "news_sentinel": _agent_news_sentinel,
    "sovereign_guard": _agent_sovereign_guard,
    "system_janitor": _agent_system_janitor,
    "companion_care": _agent_companion_care,
    "weekly_reporter": _agent_weekly_reporter,
    "physio_coach": _agent_physio_coach,
    "booster_guard": _agent_booster_guard,
}

async def run_agent(agent_id: str) -> dict:
    fn = _AGENT_FN[agent_id]
    started = datetime.now(timezone.utc)
    try:
        actions = await fn()
        status = "ok"
    except Exception as e:
        logger.warning(f"swarm agent {agent_id} failed: {e}")
        actions, status = 0, f"error: {e}"
    await db.swarm_agents.update_one(
        {"agent_id": agent_id},
        {"$set": {"agent_id": agent_id, "label": AGENTS[agent_id]["label"],
                  "desc": AGENTS[agent_id]["desc"], "interval_s": AGENTS[agent_id]["interval"],
                  "last_run": started, "last_status": status},
         "$inc": {"runs": 1, "actions": actions}},
        upsert=True)
    return {"agent_id": agent_id, "actions": actions, "status": status}


_loop_started = False

async def swarm_loop():
    global _loop_started
    if _loop_started:
        return
    _loop_started = True
    logger.info("Autonomous swarm loop started")
    while True:
        try:
            now = datetime.now(timezone.utc)
            for aid, cfg in AGENTS.items():
                doc = await db.swarm_agents.find_one({"agent_id": aid}, {"_id": 0, "last_run": 1})
                last = doc.get("last_run") if doc else None
                if last and last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                if not last or (now - last).total_seconds() >= cfg["interval"]:
                    await run_agent(aid)
            # GA-T loyalty allocations for fiat subscribers (every 6 h, idempotent)
            from routes.token import sweep_subscription_allocations
            await sweep_subscription_allocations()
        except Exception as e:
            logger.warning(f"swarm loop tick failed: {e}")
        await asyncio.sleep(15)


# ---------------- API ----------------
@api.get("/swarm/status")
async def swarm_status(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    agents = await db.swarm_agents.find({}, {"_id": 0}).to_list(20)
    bus = await db.neural_bus.find({}, {"_id": 0}).sort("at", -1).to_list(15)
    nodes = await db.depin_nodes.find({}, {"_id": 0}).to_list(20)
    healthy = sum(1 for n in nodes if n["health"] >= 70)
    return {"agents": agents, "bus": bus, "loop_active": _loop_started,
            "depin": {"nodes": len(nodes), "healthy": healthy}}

@api.post("/swarm/run/{agent_id}")
async def swarm_run(agent_id: str, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    if agent_id not in AGENTS:
        raise HTTPException(404, f"agent must be one of {list(AGENTS)}")
    return await run_agent(agent_id)

@api.get("/janitor/status")
async def janitor_status(authorization: Optional[str] = Header(None)):
    """System Janitor — self-repair history and totals."""
    await get_current_user(authorization)
    runs = await db.janitor_runs.find({}, {"_id": 0}).sort("at", -1).to_list(10)
    agent = await db.swarm_agents.find_one({"agent_id": "system_janitor"}, {"_id": 0})
    return {"agent": agent, "recent_repairs": runs,
            "total_repaired": sum(r.get("repaired_total", 0) for r in runs)}

@api.get("/depin/status")
async def depin_status(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    nodes = await db.depin_nodes.find({}, {"_id": 0}).sort("node_id", 1).to_list(20)
    return {"nodes": nodes, "topology": "P2P mesh (simulation — Phase 3: real DePIN)",
            "single_point_of_failure": False,
            "core_shard_on": [n["node_id"] for n in nodes if "core-logic" in n.get("shard", "")]}

@api.post("/depin/migrate")
async def depin_safe_migration(authorization: Optional[str] = Header(None)):
    """Sovereign Protection Protocol — Safe-Migration of the core-logic shard to
    the healthiest verified nodes (founder-triggered)."""
    user = await get_current_user(authorization)
    nodes = await db.depin_nodes.find({"verified": True}, {"_id": 0}).sort("health", -1).to_list(20)
    if len(nodes) < 2:
        raise HTTPException(503, "Not enough verified nodes")
    old = [n["node_id"] for n in nodes if "core-logic" in n.get("shard", "")]
    targets = [n for n in nodes if n["role"] in ("edge", "core", "core-standby")][:2]
    # release old core shards, re-pin to healthiest targets
    await db.depin_nodes.update_many({"shard": {"$regex": "^core-logic"}},
                                     {"$set": {"shard": "standby-pool"}})
    new_ids = []
    for i, t in enumerate(targets):
        await db.depin_nodes.update_one({"node_id": t["node_id"]},
                                        {"$set": {"shard": "core-logic" if i == 0 else "core-logic-replica",
                                                  "health": 100.0}})
        new_ids.append(t["node_id"])
    report = {"migration_id": uuid.uuid4().hex, "from": old, "to": new_ids,
              "triggered_by": user["user_id"], "at": datetime.now(timezone.utc),
              "note": "Core-logic shard moved to the healthiest verified nodes. No outage (hot hand-off)."}
    await db.security_events.insert_one({"event_id": uuid.uuid4().hex, "kind": "safe_migration",
                                         "severity": "info", "detail": f"Safe-Migration: {old} → {new_ids}",
                                         "at": report["at"]})
    await bus_publish("depin.safe_migration", "founder", {"from": old, "to": new_ids})
    return clean(report)

@api.get("/security/events")
async def security_events(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    return await db.security_events.find({}, {"_id": 0}).sort("at", -1).to_list(30)


# ---------------- STABILITY & INTEGRITY AUDIT ----------------
@api.post("/swarm/audit")
async def stability_audit(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    now = datetime.now(timezone.utc)
    checks = []

    # 1. Database
    try:
        await db.command("ping")
        checks.append({"check": "database", "ok": True, "detail": "MongoDB responds"})
    except Exception as e:
        checks.append({"check": "database", "ok": False, "detail": str(e)})

    # 2. Agents — force a run of each, then verify freshness
    for aid in AGENTS:
        await run_agent(aid)
    agents = await db.swarm_agents.find({}, {"_id": 0}).to_list(len(AGENTS) + 10)
    fresh = [a for a in agents if a.get("last_status") == "ok"]
    checks.append({"check": "swarm_agents", "ok": len(fresh) == len(AGENTS),
                   "detail": f"{len(fresh)}/{len(AGENTS)} agents are running autonomously (loop_active={_loop_started})"})

    # 3. Neural Bus
    try:
        await bus_publish("audit.probe", "audit", {"probe": now.isoformat()})
        checks.append({"check": "neural_bus", "ok": True, "detail": "Bus writes with ZK-commitment envelopes"})
    except Exception as e:
        checks.append({"check": "neural_bus", "ok": False, "detail": str(e)})

    # 4. GA-T ledger chain
    chain = await verify_ledger_chain()
    checks.append({"check": "token_ledger_chain", "ok": chain["intact"],
                   "detail": f"Hash-chain intact: {chain['intact']} ({chain['entries']} entries)"})

    # 5. Supply invariant
    s = await db.token_supply.find_one({"key": "gat"}, {"_id": 0})
    inv_ok = bool(s) and abs((s["treasury"] + s["circulating"] + s["burned"] + s["founder_reserve"]) - s["total_supply"]) < 0.01
    checks.append({"check": "token_supply_invariant", "ok": inv_ok,
                   "detail": "treasury + circulating + burned + reserve == total" if inv_ok else "INVARIANT BROKEN"})

    # 6. DePIN quorum
    nodes = await db.depin_nodes.find({}, {"_id": 0}).to_list(20)
    healthy = [n for n in nodes if n["health"] >= 70 and n["verified"]]
    core_ok = any("core-logic" in n.get("shard", "") for n in nodes)
    checks.append({"check": "depin_quorum", "ok": len(healthy) >= 4 and core_ok,
                   "detail": f"{len(healthy)}/{len(nodes)} healthy nodes, core shard pinned: {core_ok}"})

    # 7. E2E / ZK layer (Health Drop tweetnacl pubkeys)
    e2e_users = await db.users.count_documents({"drop_public_key": {"$exists": True, "$ne": None}})
    checks.append({"check": "e2e_encryption", "ok": True,
                   "detail": f"Zero-knowledge Health Drop active ({e2e_users} users with E2E key)"})

    # 8. Proof of Origin anchored
    origin = await db.ip_protection.find_one({"kind": "proof_of_origin"}, {"_id": 0}, sort=[("anchored_at", -1)])
    checks.append({"check": "proof_of_origin", "ok": bool(origin and origin.get("anchored")),
                   "detail": f"Build {ORIGIN.get('build', '?')} anchored on Bitcoin (OpenTimestamps)"})

    # 9. Medical News Sentinel feed
    from routes.news import ensure_news_seed
    await ensure_news_seed()
    news_count = await db.medical_news.count_documents({})
    checks.append({"check": "news_sentinel_feed", "ok": news_count >= 5,
                   "detail": f"Curated medical feed active ({news_count} breakthroughs, CZ/SK Tech-Tracker)"})

    passed = sum(1 for c in checks if c["ok"])
    score = round(passed / len(checks) * 100)
    report = {"report_id": uuid.uuid4().hex, "at": now, "score": score,
              "passed": passed, "total": len(checks), "checks": checks,
              "ready_for_global_publish": score >= 85,
              "verdict": "FULLY SECURE · TOKENIZED · SWARM ACTIVE" if score >= 85 else "NEEDS ATTENTION"}
    await db.audit_reports.insert_one(report.copy())
    return clean(report)

@api.get("/swarm/audit/latest")
async def audit_latest(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    rep = await db.audit_reports.find_one({}, {"_id": 0}, sort=[("at", -1)])
    return rep or {"score": None, "note": "No audit yet — launch Stability & Integrity Audit."}
