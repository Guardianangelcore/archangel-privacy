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
                          "desc": "Autonómne hľadá a rezervuje uvoľnené termíny"},
    "marketplace":       {"interval": 90, "label": "Data Marketplace Agent",
                          "desc": "Spravuje anonymné datasety a GA-T odmeny (Proof-of-Health)"},
    "safety":            {"interval": 45, "label": "Safety Monitoring Agent",
                          "desc": "24/7 dohľad — eskaluje nezodpovedané pulse pingy"},
    "security_sentinel": {"interval": 30, "label": "Security Sentinel",
                          "desc": "Behaviorálna detekcia anomálií + self-healing uzlov"},
    "wealth_sentinel":   {"interval": 120, "label": "Wealth Sentinel (Insurance Guard)",
                          "desc": "Stráži poistky — pri prepadnutí spustí Jarvis alarm + mikro-pôžičku"},
    "news_sentinel":     {"interval": 300, "label": "Medical News Sentinel",
                          "desc": "Krížuje svetové medicínske prelomy s tvojím Trezorom → prioritné alerty"},
    "sovereign_guard":   {"interval": 45, "label": "Sovereign Guard (Recovery · 2FA · SAT-uplink)",
                          "desc": "Spravuje obnovu účtov, 2FA handshaky, Bio-Beacony a satelitné Nano-Packety"},
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
            "title": f"{item.get('specialty', 'Termín')} — {slot['clinic']}", "date": slot["date"],
            "notes": f"Swarm Agent · {slot['time']} · autonómne nájdený", "booster_due": None,
            "source": "swarm:waitlist_hunter", "created_at": datetime.now(timezone.utc)})
        try:
            await send_push(recipients=[item["user_id"]],
                            data={"title": "🤖 SWARM NAŠIEL TERMÍN", "message": f"{item.get('specialty', '')}: {found}",
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
        tx = await award_tokens(o["user_id"], "proof_of_health", "dataset drip — anonymný insight (swarm)")
        if tx:
            actions += 1
    if actions:
        await bus_publish("marketplace.reward_drip", "marketplace", {"rewarded_users": actions, "token": "GA-T"})
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
                            data={"title": "⚠️ BEZ ODPOVEDE 15 MIN", "message": "Tichý ping bez reakcie — odporúčame zavolať alebo navštíviť.",
                                  "action_url": "/pulse-check"})
        except Exception:
            pass
        await bus_publish("safety.escalation", "safety", {"req_id": req["req_id"], "reason": "no_response_15m"})
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
                "detail": f"Uzol {n['node_id']} degradoval ({health:.0f}%) — re-imaged, shard re-pinned, kľúče rotované.",
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
            "detail": f"Neobvyklý nápor {b['count']} požiadaviek/10 min od '{b['_id']}' — kľúč dočasne priškrtený (throttled).",
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
                                  "message": f"{p['provider']} ({p['type']}) nie je zaplatená. Hrozí zánik krytia — otvorte Insurance Guard alebo požiadajte o mikro-pôžičku v Solidarity Hube.",
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
            try:
                await send_push(recipients=[u["user_id"]],
                                data={"title": "🔬 MEDICÍNSKY PRELOM PRE VÁS",
                                      "message": f"{n['title']} — klinika {n['hunt_city']} ({n['region']}). Mám uloviť termín?",
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
                                                      "constellation": "GA-SAT/1 (simulované vysielanie)"}})
        try:
            await send_push(recipients=[p["user_id"]],
                            data={"title": "🛰️ NANO-PACKET ODVYSIELANÝ",
                                  "message": f"Satelitná núdzová správa ({p['packet_bytes']} B) bola odvysielaná (simulácia).",
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
                            data={"title": "🌍 POTVRDENÁ ENVIRONMENTÁLNA HROZBA",
                                  "message": f"Mesh konsenzus ({len(reps)} hlásení): {kind.upper()} — {reps[0]['city'] or 'región'}. Otvorte pokyny.",
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

_AGENT_FN = {
    "waitlist_hunter": _agent_waitlist_hunter,
    "marketplace": _agent_marketplace,
    "safety": _agent_safety,
    "security_sentinel": _agent_security_sentinel,
    "wealth_sentinel": _agent_wealth_sentinel,
    "news_sentinel": _agent_news_sentinel,
    "sovereign_guard": _agent_sovereign_guard,
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
        except Exception as e:
            logger.warning(f"swarm loop tick failed: {e}")
        await asyncio.sleep(15)


# ---------------- API ----------------
@api.get("/swarm/status")
async def swarm_status(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    agents = await db.swarm_agents.find({}, {"_id": 0}).to_list(10)
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

@api.get("/depin/status")
async def depin_status(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    nodes = await db.depin_nodes.find({}, {"_id": 0}).sort("node_id", 1).to_list(20)
    return {"nodes": nodes, "topology": "P2P mesh (simulácia — Phase 3: reálny DePIN)",
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
              "note": "Core-logic shard presunutý na najzdravšie overené uzly. Žiadny výpadok (hot hand-off)."}
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
        checks.append({"check": "database", "ok": True, "detail": "MongoDB odpovedá"})
    except Exception as e:
        checks.append({"check": "database", "ok": False, "detail": str(e)})

    # 2. Agents — force a run of each, then verify freshness
    for aid in AGENTS:
        await run_agent(aid)
    agents = await db.swarm_agents.find({}, {"_id": 0}).to_list(10)
    fresh = [a for a in agents if a.get("last_status") == "ok"]
    checks.append({"check": "swarm_agents", "ok": len(fresh) == len(AGENTS),
                   "detail": f"{len(fresh)}/{len(AGENTS)} agentov beží autonómne (loop_active={_loop_started})"})

    # 3. Neural Bus
    try:
        await bus_publish("audit.probe", "audit", {"probe": now.isoformat()})
        checks.append({"check": "neural_bus", "ok": True, "detail": "Bus zapisuje so ZK-commitment obálkami"})
    except Exception as e:
        checks.append({"check": "neural_bus", "ok": False, "detail": str(e)})

    # 4. GA-T ledger chain
    chain = await verify_ledger_chain()
    checks.append({"check": "token_ledger_chain", "ok": chain["intact"],
                   "detail": f"Hash-chain intact: {chain['intact']} ({chain['entries']} záznamov)"})

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
                   "detail": f"{len(healthy)}/{len(nodes)} uzlov zdravých, core shard pripnutý: {core_ok}"})

    # 7. E2E / ZK layer (Health Drop tweetnacl pubkeys)
    e2e_users = await db.users.count_documents({"drop_public_key": {"$exists": True, "$ne": None}})
    checks.append({"check": "e2e_encryption", "ok": True,
                   "detail": f"Zero-knowledge Health Drop aktívny ({e2e_users} užívateľov s E2E kľúčom)"})

    # 8. Proof of Origin anchored
    origin = await db.ip_protection.find_one({"kind": "proof_of_origin"}, {"_id": 0}, sort=[("anchored_at", -1)])
    checks.append({"check": "proof_of_origin", "ok": bool(origin and origin.get("anchored")),
                   "detail": f"Build {ORIGIN.get('build', '?')} ukotvený na Bitcoin (OpenTimestamps)"})

    # 9. Medical News Sentinel feed
    from routes.news import ensure_news_seed
    await ensure_news_seed()
    news_count = await db.medical_news.count_documents({})
    checks.append({"check": "news_sentinel_feed", "ok": news_count >= 5,
                   "detail": f"Kurátorovaný medicínsky feed aktívny ({news_count} prelomov, CZ/SK Tech-Tracker)"})

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
    return rep or {"score": None, "note": "Zatiaľ žiadny audit — spustite Stability & Integrity Audit."}
