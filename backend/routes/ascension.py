# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""ASCENSION PROTOCOL — 22nd-century layer of the Sovereign Survival OS.

1. BIO-DIGITAL TWIN     — simulates treatments/drugs against the user's
   historical bio-profile BEFORE real administration; predictive trajectories.
2. PREDICTIVE SENTINEL  — behavioural forecasting (tremor / gait / stress)
   → warns the Inner Circle BEFORE an event occurs.
3. LIVING CURRENCY      — GA-T earned by donating idle device compute to the
   decentralized medical-research swarm + Guardian Basic Income.
4. COLLECTIVE TRUTH     — SHA3-512 hash-chained sovereign record (post-quantum
   safe hashing), self-verifying, mesh-replicated.
5. COGNITIVE HANDOVER   — Personality Blueprint: Jarvis assists survivors with
   the founder's decision logic and tone (clearly framed as a digital echo).
"""
from fastapi import HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid, hashlib, json, statistics, re

from emergentintegrations.llm.chat import LlmChat, UserMessage
from core import api, db, clean, get_current_user, send_push, logger, AI_COMPLIANCE_NOTE, EMERGENT_LLM_KEY

def _llm(session: str, system: str) -> LlmChat:
    return LlmChat(api_key=EMERGENT_LLM_KEY, session_id=session,
                   system_message=system).with_model("openai", "gpt-5.4")

def _parse_json(text: str) -> dict:
    """Robust LLM JSON extraction — tolerates fences and trailing prose."""
    raw = re.sub(r"^```(json)?|```$", "", str(text).strip(), flags=re.M).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        if start < 0:
            raise
        obj, _end = json.JSONDecoder().raw_decode(raw[start:])
        return obj

# =========================================================================
# 1) BIO-DIGITAL TWIN
# =========================================================================
async def _twin_profile(uid: str) -> dict:
    prof = await db.emergency_profiles.find_one({"user_id": uid}, {"_id": 0}) or {}
    lng = await db.longevity_profiles.find_one({"user_id": uid}, {"_id": 0}) or {}
    meds = await db.med_reminders.find({"user_id": uid}, {"_id": 0, "name": 1, "dose": 1}).to_list(30)
    scans = await db.bioscan_results.find({"user_id": uid}, {"_id": 0}).sort("at", -1).to_list(20)
    bps, glus, hrs = [], [], []
    for s in scans:
        if s.get("bp_estimate") and "/" in str(s["bp_estimate"]):
            try:
                a, b = str(s["bp_estimate"]).split("/")
                bps.append((int(a), int(b)))
            except ValueError:
                pass
        if s.get("glucose_mmol"):
            glus.append(float(s["glucose_mmol"]))
        if s.get("heart_rate"):
            hrs.append(int(s["heart_rate"]))
    year = datetime.now(timezone.utc).year
    return {
        "age": (year - int(lng["birth_year"])) if lng.get("birth_year") else None,
        "height_cm": lng.get("height_cm"), "weight_kg": lng.get("weight_kg"),
        "conditions": prof.get("conditions") or "", "allergies": prof.get("allergies") or "",
        "blood_type": prof.get("blood_type") or "",
        "active_meds": [f"{m.get('name')} ({m.get('dose', '')})" for m in meds],
        "bp_series": [f"{a}/{b}" for a, b in bps[:10]],
        "bp_avg_systolic": round(statistics.mean(a for a, _ in bps), 1) if bps else None,
        "glucose_series": glus[:10],
        "glucose_avg": round(statistics.mean(glus), 1) if glus else None,
        "hr_avg": round(statistics.mean(hrs)) if hrs else None,
        "samples": len(scans),
    }

@api.get("/twin/profile")
async def twin_profile(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return {"twin": await _twin_profile(user["user_id"]),
            "fidelity_pct": min(100, (await db.bioscan_results.count_documents({"user_id": user["user_id"]})) * 5
                                + (await db.agent_memories.count_documents({"user_id": user["user_id"]})) * 2)}

class TwinSimIn(BaseModel):
    treatment: str = Field(min_length=2, max_length=200)   # drug or procedure
    dosage: Optional[str] = None
    language: str = "sk"

@api.post("/twin/simulate")
async def twin_simulate(body: TwinSimIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    twin = await _twin_profile(uid)
    sys = (
        "You are the BIO-DIGITAL TWIN engine of a sovereign health OS. Simulate the proposed treatment "
        "against the patient's digital twin BEFORE real administration. Respond ONLY with strict JSON "
        '(no fences): {"compatibility_pct": 0-100, "expected_benefit": "<1-2 sentences Slovak>", '
        '"risks": ["<risk Slovak>", ...max 4], "interactions": ["<interaction with active meds/conditions>", ...max 4], '
        '"monitoring": ["<what to watch>", ...max 3], "verdict": "simulate_pass|caution|simulate_fail"} '
        "Base everything ONLY on the twin profile given. Be conservative — flag allergy or condition conflicts hard."
        + AI_COMPLIANCE_NOTE
    )
    try:
        resp = await _llm(f"twin-{uid[:8]}-{uuid.uuid4().hex[:6]}", sys).send_message(UserMessage(
            text=json.dumps({"treatment": body.treatment, "dosage": body.dosage, "twin": twin},
                            ensure_ascii=False)))
        sim = _parse_json(resp)
    except Exception as e:
        logger.error(f"twin sim error: {e}")
        raise HTTPException(502, "Twin simulation engine unavailable")
    rec = {"sim_id": uuid.uuid4().hex, "user_id": uid, "treatment": body.treatment,
           "dosage": body.dosage, "result": sim, "at": datetime.now(timezone.utc)}
    await db.twin_simulations.insert_one(rec.copy())
    return clean(rec)

@api.get("/twin/trajectory")
async def twin_trajectory(authorization: Optional[str] = Header(None)):
    """Predictive Health Trajectories — deterministic linear projection of vitals
    (6/12/24 months) with risk bands. Pure math, auditable."""
    user = await get_current_user(authorization)
    uid = user["user_id"]
    scans = await db.bioscan_results.find({"user_id": uid}, {"_id": 0}).sort("at", 1).to_list(60)
    series = {"systolic": [], "glucose": []}
    for s in scans:
        if s.get("bp_estimate") and "/" in str(s["bp_estimate"]):
            try:
                series["systolic"].append(int(str(s["bp_estimate"]).split("/")[0]))
            except ValueError:
                pass
        if s.get("glucose_mmol"):
            series["glucose"].append(float(s["glucose_mmol"]))

    def project(vals: List[float], horizon_steps: int, lo: float, hi: float) -> Optional[float]:
        if len(vals) < 2:
            return None
        n = len(vals)
        xs = list(range(n))
        mx, my = sum(xs) / n, sum(vals) / n
        denom = sum((x - mx) ** 2 for x in xs) or 1
        slope = sum((xs[i] - mx) * (vals[i] - my) for i in range(n)) / denom
        # dampen slope for small samples + clamp to physiological bounds
        damp = min(1.0, n / 10)
        return round(min(hi, max(lo, vals[-1] + slope * damp * horizon_steps)), 1)

    def band(metric: str, v: Optional[float]) -> str:
        if v is None:
            return "insufficient_data"
        if metric == "systolic":
            return "critical" if v >= 160 else "elevated" if v >= 140 else "optimal"
        return "critical" if v >= 11 else "elevated" if v >= 7 else "optimal"

    traj = {}
    bounds = {"systolic": (70, 260), "glucose": (2, 35)}
    for metric, vals in series.items():
        lo, hi = bounds[metric]
        cur = vals[-1] if vals else None
        traj[metric] = {
            "current": cur, "history_points": len(vals),
            "m6": project(vals, 6, lo, hi), "m12": project(vals, 12, lo, hi), "m24": project(vals, 24, lo, hi),
            "band_now": band(metric, cur), "band_m12": band(metric, project(vals, 12, lo, hi)),
        }
    risk = 0
    for m in traj.values():
        risk += {"critical": 40, "elevated": 20, "optimal": 0, "insufficient_data": 5}[m["band_m12"]]
    return {"trajectories": traj, "composite_risk_12m": min(100, risk),
            "method": "least-squares linear projection over measurement index",
            "disclaimer": "Prediktívny model — informačný obsah, nie zdravotná starostlivosť (EU AI Act čl. 50)."}

# =========================================================================
# 2) PREDICTIVE SENTINEL (behavioural forecasting)
# =========================================================================
class GaitIn(BaseModel):
    tremor_index: float = Field(ge=0, le=10)     # variance of accel magnitude ×100
    gait_regularity: float = Field(ge=0, le=1)   # 1 = perfectly regular steps
    voice_tremor: Optional[float] = Field(None, ge=0, le=10)

@api.post("/sentinel/gait")
async def sentinel_gait(body: GaitIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    await db.gait_samples.insert_one({
        "sample_id": uuid.uuid4().hex, "user_id": uid,
        "tremor_index": body.tremor_index, "gait_regularity": body.gait_regularity,
        "voice_tremor": body.voice_tremor, "at": datetime.now(timezone.utc)})
    return await _sentinel_predict(uid)

async def _sentinel_predict(uid: str) -> dict:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    samples = await db.gait_samples.find({"user_id": uid, "at": {"$gte": since}}, {"_id": 0}).to_list(200)
    scans = await db.bioscan_results.find({"user_id": uid}, {"_id": 0}).sort("at", -1).to_list(5)
    risk = 0.0
    factors = []
    if samples:
        tremor = statistics.mean(s["tremor_index"] for s in samples)
        gait = statistics.mean(s["gait_regularity"] for s in samples)
        if tremor > 3.5:
            risk += min(35, (tremor - 3.5) * 12)
            factors.append(f"Zvýšené mikro-vibrácie rúk (index {tremor:.1f})")
        if gait < 0.6:
            risk += min(30, (0.6 - gait) * 80)
            factors.append(f"Nepravidelná chôdza (pravidelnosť {gait:.2f})")
        vt = [s["voice_tremor"] for s in samples if s.get("voice_tremor") is not None]
        if vt and statistics.mean(vt) > 4:
            risk += 15
            factors.append("Chvenie hlasu nad normou")
    if scans and scans[0].get("stress_level") == "high":
        risk += 15
        factors.append("Vysoký stres v poslednom skene")
    bps = [s for s in scans if s.get("bp_estimate")]
    if bps:
        try:
            if int(str(bps[0]["bp_estimate"]).split("/")[0]) >= 150:
                risk += 15
                factors.append(f"Tlak {bps[0]['bp_estimate']} nad bezpečným pásmom")
        except ValueError:
            pass
    risk = round(min(100, risk), 1)
    level = "high" if risk >= 70 else "medium" if risk >= 40 else "low"
    result = {"risk_score": risk, "level": level, "factors": factors,
              "samples_24h": len(samples), "at": datetime.now(timezone.utc)}
    if level == "high":
        dup = await db.sentinel_alerts.find_one({
            "user_id": uid, "at": {"$gte": datetime.now(timezone.utc) - timedelta(hours=6)}})
        if not dup:
            await db.sentinel_alerts.insert_one({"alert_id": uuid.uuid4().hex, "user_id": uid,
                                                 "risk": risk, "factors": factors,
                                                 "at": datetime.now(timezone.utc)})
            circle = await db.family_links.find({"owner_id": uid, "status": "active"},
                                                {"_id": 0, "member_id": 1}).to_list(10)
            recipients = [uid] + [c["member_id"] for c in circle if c.get("member_id")]
            try:
                await send_push(recipients=recipients, data={
                    "title": "🔮 PREDIKTÍVNY SENTINEL — ZVÝŠENÉ RIZIKO",
                    "message": f"Vzorce správania signalizujú riziko {risk}/100 PRED udalosťou: {'; '.join(factors[:2])}",
                    "action_url": "/inner-circle"})
            except Exception:
                pass
    return result

@api.get("/sentinel/predict")
async def sentinel_predict(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await _sentinel_predict(user["user_id"])

# =========================================================================
# 3) LIVING CURRENCY — Edge Computing + Guardian Basic Income
# =========================================================================
EDGE_RATE_GAT_PER_MTASK = 0.8          # GA-T per 1M research hash-tasks
EDGE_MAX_TASKS_PER_REPORT = 5_000_000
GBI_DAILY_GAT = 0.5

class EdgeIn(BaseModel):
    device_id: str = Field(min_length=4, max_length=64)
    tasks_completed: int = Field(gt=0)
    ms_contributed: int = Field(gt=0)

@api.post("/edge/contribute")
async def edge_contribute(body: EdgeIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    if body.tasks_completed > EDGE_MAX_TASKS_PER_REPORT:
        raise HTTPException(400, "Implausible task count for one report")
    if body.tasks_completed / max(1, body.ms_contributed) > 5000:  # >5M tasks/s = fraud
        raise HTTPException(400, "Task rate exceeds physical device limits")
    gat = round(body.tasks_completed / 1_000_000 * EDGE_RATE_GAT_PER_MTASK, 4)
    await db.edge_nodes.update_one(
        {"user_id": uid, "device_id": body.device_id},
        {"$inc": {"tasks_total": body.tasks_completed, "ms_total": body.ms_contributed,
                  "gat_earned": gat},
         "$set": {"last_report": datetime.now(timezone.utc)},
         "$setOnInsert": {"joined_at": datetime.now(timezone.utc)}},
        upsert=True)
    if gat >= 0.0001:
        from routes.token import award_tokens
        await award_tokens(uid, "proof_of_health",
                           f"Edge Computing — {body.tasks_completed:,} research úloh (+{gat} GA-T)")
    return {"accepted": True, "gat_earned": gat,
            "note": "Zariadenie počítalo úlohy pre decentralizovaný medicínsky výskumný swarm."}

@api.get("/edge/status")
async def edge_status(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    mine = await db.edge_nodes.find({"user_id": uid}, {"_id": 0}).to_list(5)
    agg = await db.edge_nodes.aggregate([
        {"$group": {"_id": None, "nodes": {"$sum": 1}, "tasks": {"$sum": "$tasks_total"},
                    "gat": {"$sum": "$gat_earned"}}}]).to_list(1)
    net = agg[0] if agg else {"nodes": 0, "tasks": 0, "gat": 0}
    gbi = await db.gbi_payments.find({"user_id": uid}, {"_id": 0}).sort("date", -1).to_list(7)
    return {"my_devices": clean(mine),
            "network": {"nodes": net["nodes"], "tasks_total": net["tasks"],
                        "gat_distributed": round(net["gat"], 2)},
            "rate": f"{EDGE_RATE_GAT_PER_MTASK} GA-T / 1M úloh",
            "gbi": {"daily_gat": GBI_DAILY_GAT, "recent_payments": clean(gbi),
                    "rule": "Guardian Basic Income — každý aktívny Guardian dostáva denný základný príjem; Swarm ho vypláca autonómne."}}

async def gbi_distribute() -> int:
    """Swarm task: pay Guardian Basic Income once per day to every user active
    in the last 72 h (any XP event, scan or edge report)."""
    from routes.token import award_tokens
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    since = datetime.now(timezone.utc) - timedelta(hours=72)
    active_ids = set()
    for coll, field in ((db.agent_xp_events, "at"), (db.bioscan_results, "at"), (db.edge_nodes, "last_report")):
        rows = await coll.find({field: {"$gte": since}}, {"_id": 0, "user_id": 1}).to_list(500)
        active_ids.update(r["user_id"] for r in rows if r.get("user_id"))
    paid = 0
    for uid in active_ids:
        dup = await db.gbi_payments.find_one({"user_id": uid, "date": today})
        if dup:
            continue
        await db.gbi_payments.insert_one({"user_id": uid, "date": today,
                                          "amount_gat": GBI_DAILY_GAT,
                                          "at": datetime.now(timezone.utc)})
        await award_tokens(uid, "proof_of_health", f"Guardian Basic Income {today} (+{GBI_DAILY_GAT} GA-T)")
        paid += 1
    return paid

# =========================================================================
# 4) COLLECTIVE HUMAN TRUTH — SHA3-512 hash-chain (post-quantum-safe hashing)
# =========================================================================
class TruthIn(BaseModel):
    kind: str = Field(min_length=2, max_length=40)     # observation|vital|event|testimony
    content: str = Field(min_length=1, max_length=2000)

@api.post("/mesh/truth")
async def truth_append(body: TruthIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    last = await db.collective_truth.find_one(sort=[("seq", -1)])
    prev_hash = last["hash"] if last else "GENESIS"
    seq = (last["seq"] + 1) if last else 1
    payload = {"seq": seq, "kind": body.kind, "content": body.content,
               "author_did": user.get("did", ""), "at": datetime.now(timezone.utc).isoformat()}
    h = hashlib.sha3_512((prev_hash + json.dumps(payload, sort_keys=True)).encode()).hexdigest()
    rec = {**payload, "prev_hash": prev_hash, "hash": h}
    await db.collective_truth.insert_one(rec.copy())
    return {"seq": seq, "hash": h, "prev_hash": prev_hash,
            "algo": "SHA3-512 (post-quantum-safe hashing)"}

@api.get("/mesh/truth/verify")
async def truth_verify(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    rows = await db.collective_truth.find({}, {"_id": 0}).sort("seq", 1).to_list(5000)
    prev = "GENESIS"
    for r in rows:
        payload = {k: r[k] for k in ("seq", "kind", "content", "author_did", "at")}
        expect = hashlib.sha3_512((prev + json.dumps(payload, sort_keys=True)).encode()).hexdigest()
        if r["prev_hash"] != prev or r["hash"] != expect:
            return {"valid": False, "broken_at_seq": r["seq"], "records": len(rows)}
        prev = r["hash"]
    return {"valid": True, "records": len(rows), "head": prev,
            "algo": "SHA3-512", "replication": "mesh + satellite Nano-Packet (simulated radio)"}

# =========================================================================
# 5) COGNITIVE HANDOVER — Personality Blueprint
# =========================================================================
@api.post("/legacy/blueprint/train")
async def blueprint_train(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    mems = await db.agent_memories.find({"user_id": uid}, {"_id": 0}).sort("importance", -1).to_list(40)
    convs = await db.agent_conversations.find({"user_id": uid, "role": "user"},
                                              {"_id": 0, "text": 1}).sort("at", -1).to_list(30)
    deals = await db.data_deals.count_documents({"user_id": uid})
    wisdom = await db.legacy_messages.find({"user_id": uid}, {"_id": 0}).to_list(10)
    corpus = {
        "memories": [m["text"] for m in mems],
        "own_words": [c["text"][:200] for c in convs],
        "legacy_notes": [w.get("message", "")[:200] for w in wisdom],
        "traits_hint": {"data_deals": deals, "language": user.get("language", "sk")},
    }
    if not corpus["memories"] and not corpus["own_words"]:
        raise HTTPException(400, "Nedostatok dát — porozprávajte sa najprv s Jarvisom, aby spoznal vašu osobnosť.")
    sys = (
        "You are building a PERSONALITY BLUEPRINT for a cognitive-handover system. From the user's own words, "
        "memories and notes, extract their decision-making style and tone. Respond ONLY with strict JSON "
        '(no fences): {"tone": "<2-3 sentence Slovak description of how they speak>", '
        '"values": ["<core value>", ...max 5], "decision_rules": ["<if-then rule they follow>", ...max 5], '
        '"catchphrases": ["<typical phrase>", ...max 4]}' + AI_COMPLIANCE_NOTE
    )
    try:
        resp = await _llm(f"bp-{uid[:8]}-{uuid.uuid4().hex[:6]}", sys).send_message(
            UserMessage(text=json.dumps(corpus, ensure_ascii=False)[:6000]))
        bp = _parse_json(resp)
    except Exception as e:
        logger.error(f"blueprint train error: {e}")
        raise HTTPException(502, "Blueprint engine unavailable")
    doc = {"user_id": uid, "blueprint": bp, "sources": {k: len(v) for k, v in corpus.items() if isinstance(v, list)},
           "trained_at": datetime.now(timezone.utc), "version": 1}
    old = await db.personality_blueprints.find_one({"user_id": uid})
    if old:
        doc["version"] = old.get("version", 1) + 1
    await db.personality_blueprints.update_one({"user_id": uid}, {"$set": doc}, upsert=True)
    return clean(doc)

@api.get("/legacy/blueprint")
async def blueprint_get(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    bp = await db.personality_blueprints.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return {"trained": bool(bp), "blueprint": clean(bp) if bp else None}

class BlueprintAskIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    asker_name: str = "Tomáš"

@api.post("/legacy/blueprint/ask")
async def blueprint_ask(body: BlueprintAskIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    bp = await db.personality_blueprints.find_one({"user_id": uid}, {"_id": 0})
    if not bp:
        raise HTTPException(400, "Blueprint ešte nie je natrénovaný — spustite /legacy/blueprint/train")
    mems = await db.agent_memories.find({"user_id": uid}, {"_id": 0}).sort("importance", -1).to_list(20)
    sys = (
        f"You are the DIGITAL ECHO of {user.get('name', 'the founder')} — a cognitive-handover assistant for their "
        f"survivor {body.asker_name}. Answer in Slovak USING the founder's tone, values, decision rules and "
        "catchphrases from the blueprint. ALWAYS open with a gentle reminder that you are a digital echo, "
        "not the person. Max 5 sentences. Blueprint: "
        + json.dumps(bp.get("blueprint", {}), ensure_ascii=False)
        + " Memories: " + json.dumps([m["text"] for m in mems], ensure_ascii=False)
        + AI_COMPLIANCE_NOTE
    )
    try:
        resp = await _llm(f"echo-{uid[:8]}-{uuid.uuid4().hex[:6]}", sys).send_message(
            UserMessage(text=body.question))
    except Exception as e:
        logger.error(f"blueprint ask error: {e}")
        raise HTTPException(502, "Echo engine unavailable")
    await db.blueprint_dialogues.insert_one({
        "dialogue_id": uuid.uuid4().hex, "user_id": uid, "asker": body.asker_name,
        "question": body.question, "answer": str(resp)[:2000], "at": datetime.now(timezone.utc)})
    return {"answer": str(resp), "framing": "digital_echo",
            "voice_note": "Hlasový klon vyžaduje ElevenLabs kľúč — zatiaľ hovorí najbližší OpenAI hlas."}
