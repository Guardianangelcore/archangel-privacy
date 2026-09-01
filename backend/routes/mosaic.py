# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""The Mosaic Protocol — decentralized backbone (SIMULATED L2, Phase 3 = real RPC).

1. Mosaic Chain: ZK-Rollup Layer-2 as primary ledger for GA-T + DAO governance.
2. Hybrid data layer: on-chain = hashes only (medical records, DID credentials,
   Legacy Trigger smart contracts) · off-chain = DePIN/IPFS CIDs for heavy files.
3. Quantum-ready handshake: hybrid X25519 + ML-KEM-1024 (Kyber) + ML-DSA
   (Dilithium) placeholders.
4. Bridge-Watch: latency monitor with autonomous mirroring to Base/Polygon.
5. Zero-Fee Abstraction: all gas sponsored by the foundation treasury —
   users (especially babičky) never see a fee."""
from fastapi import HTTPException, Header
from typing import Optional
from datetime import datetime, timezone
import uuid, hashlib, base64, random

from core import api, db, clean, get_current_user

CHAIN = {
    "name": "Mosaic Chain", "layer": "ZK-Rollup L2 (validity proofs)",
    "consensus": "zkSNARK batch attestation → L1 settlement",
    "pqc_suite": "Hybrid X25519 + ML-KEM-1024 (Kyber) · signatures ML-DSA-87 (Dilithium)",
    "secondary_chains": ["Base (mirror)", "Polygon PoS (mirror)"],
    "gas_policy": "ZERO-FEE — gas sponsored by the foundation treasury (Sentinel/Archangel yields)",
    "simulated": True,
}
LATENCY_FAILOVER_MS = 800

def _cid(sha256_hex: str) -> str:
    """Simulated IPFS CIDv1 derived from the document hash."""
    raw = base64.b32encode(bytes.fromhex(sha256_hex)).decode().lower().rstrip("=")
    return f"bafy{raw[:46]}"

_LIVE = {"orphaned": {"$ne": True}}  # fork-healed blocks are soft-marked, never hard-deleted

async def _chain_head() -> dict:
    return await db.mosaic_blocks.find_one(_LIVE, {"_id": 0}, sort=[("height", -1)]) or \
        {"height": 0, "block_hash": "mosaic-genesis"}

async def produce_block(trigger: str) -> Optional[dict]:
    """Batch new GA-T ledger entries + record hashes into one ZK-rollup block."""
    head = await _chain_head()
    last_seq = head.get("ledger_seq", 0)
    entries = await db.token_ledger.find({"seq": {"$gt": last_seq}},
                                         {"_id": 0, "seq": 1, "entry_hash": 1}).sort("seq", 1).to_list(100)
    vault_count = await db.vault.count_documents({})
    did_count = await db.users.count_documents({"did": {"$exists": True}})
    if not entries and trigger not in ("manual", "wealth_anchor", "video_legacy"):
        return None
    now = datetime.now(timezone.utc)
    batch_root = hashlib.sha256("".join(e["entry_hash"] for e in entries).encode()).hexdigest()
    body = f"{head['block_hash']}|{batch_root}|{vault_count}|{did_count}|{now.isoformat()}"
    block = {"height": head["height"] + 1,
             "block_hash": hashlib.sha256(body.encode()).hexdigest(),
             "prev_hash": head["block_hash"],
             "zk_proof": "zkp-" + hashlib.sha256(("proof" + body).encode()).hexdigest()[:40],
             "tx_batched": len(entries), "ledger_seq": entries[-1]["seq"] if entries else last_seq,
             "anchored": {"medical_record_hashes": vault_count, "did_credentials": did_count},
             "gas_fee_user": 0.0, "gas_paid_by": "foundation-treasury",
             "trigger": trigger, "simulated": True, "at": now}
    await db.mosaic_blocks.insert_one(block.copy())
    try:
        from routes.swarm import bus_publish
        await bus_publish("mosaic.block_produced", "sovereign_guard",
                          {"height": block["height"], "tx": block["tx_batched"]})
    except Exception:
        pass
    return block


@api.get("/mosaic/status")
async def mosaic_status(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    head = await _chain_head()
    blocks = await db.mosaic_blocks.count_documents(_LIVE)
    bridge = await db.mosaic_bridge.find_one({"key": "bridge"}, {"_id": 0}) or \
        {"primary": "Mosaic Chain", "active": "Mosaic Chain", "latency_ms": 0, "mirrored_ops": 0}
    contracts = await db.legacy_contracts.count_documents({})
    return {**CHAIN, "block_height": head.get("height", 0), "blocks_total": blocks,
            "last_block_hash": head.get("block_hash"), "legacy_smart_contracts": contracts,
            "bridge_watch": bridge,
            "note": "SIMULATION — real RPC (Mosaic/Base/Polygon) connects in Phase 3. Architecture and hashes are production."}

@api.get("/mosaic/blocks")
async def mosaic_blocks(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    rows = await db.mosaic_blocks.find(_LIVE, {"_id": 0}).sort("height", -1).to_list(15)
    return {"blocks": rows}

@api.post("/mosaic/anchor")
async def mosaic_anchor(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    block = await produce_block("manual")
    return {"ok": True, "block": clean(block)}

@api.get("/mosaic/ipfs/manifest")
async def mosaic_ipfs_manifest(authorization: Optional[str] = Header(None)):
    """Hybrid data layer — off-chain DePIN/IPFS CIDs for the user's heavy files;
    only the SHA-256 hashes live on-chain."""
    user = await get_current_user(authorization)
    docs = await db.vault.find({"user_id": user["user_id"]},
                               {"_id": 0, "doc_id": 1, "title": 1, "sha256": 1, "created_at": 1}).to_list(50)
    out = []
    for d in docs:
        h = d.get("sha256") or hashlib.sha256(d["doc_id"].encode()).hexdigest()
        out.append({"doc_id": d["doc_id"], "title": d.get("title"),
                    "onchain_hash": h, "ipfs_cid": _cid(h), "pinned_nodes": 3,
                    "layer": "DePIN off-chain (simulated pinning)"})
    return {"files": out, "policy": "On-chain: hashes only. Off-chain: IPFS/DePIN content."}

@api.post("/mosaic/legacy-contract")
async def mosaic_legacy_contract(authorization: Optional[str] = Header(None)):
    """Registers the user's Legacy Trigger as an on-chain smart contract hash
    (dead-man switch → digital legacy execution)."""
    user = await get_current_user(authorization)
    legacy = await db.legacy_configs.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    payload = f"legacy|{user['did']}|{str(legacy)}"
    contract = {"contract_id": f"0x{hashlib.sha256(payload.encode()).hexdigest()[:40]}",
                "user_id": user["user_id"], "did": user["did"],
                "kind": "LegacyTrigger v1 (dead-man switch)",
                "onchain_hash": hashlib.sha256(payload.encode()).hexdigest(),
                "gas_fee_user": 0.0, "gas_paid_by": "foundation-treasury",
                "simulated": True, "at": datetime.now(timezone.utc)}
    await db.legacy_contracts.update_one({"user_id": user["user_id"]}, {"$set": contract}, upsert=True)
    return clean(contract)

@api.get("/mosaic/pqc-handshake")
async def mosaic_pqc_handshake(authorization: Optional[str] = Header(None)):
    """Quantum-ready connectivity check — hybrid classical+PQC session (placeholder)."""
    user = await get_current_user(authorization)
    sid = uuid.uuid4().hex
    return {"session_id": sid,
            "kem": "ML-KEM-1024 (Kyber) — encapsulation OK (simulated)",
            "classical": "X25519 ECDH — OK",
            "signature": "ML-DSA-87 (Dilithium) — verified (simulated)",
            "transcript_hash": hashlib.sha256(f"{user['did']}{sid}".encode()).hexdigest(),
            "quantum_safe": True, "simulated": True}

@api.post("/mosaic/bridge/check")
async def mosaic_bridge_check(authorization: Optional[str] = Header(None)):
    """Bridge-Watch — samples primary latency; autonomously mirrors to a
    secondary chain when the Mosaic node group is slow."""
    await get_current_user(authorization)
    latency = random.randint(40, 1200)
    failover = latency > LATENCY_FAILOVER_MS
    active = "Base (mirror)" if failover else "Mosaic Chain"
    upd = {"primary": "Mosaic Chain", "active": active, "latency_ms": latency,
           "failover": failover, "checked_at": datetime.now(timezone.utc)}
    await db.mosaic_bridge.update_one({"key": "bridge"}, {"$set": upd, "$inc": {"mirrored_ops": 1 if failover else 0}}, upsert=True)
    if failover:
        try:
            from routes.swarm import bus_publish
            await bus_publish("mosaic.bridge_failover", "sovereign_guard",
                              {"latency_ms": latency, "mirror": active})
        except Exception:
            pass
    return {**upd, "threshold_ms": LATENCY_FAILOVER_MS,
            "detail": ("Latency above threshold — critical operations mirrored to Base/Polygon." if failover
                       else "Mosaic node group within norm — primary chain active.")}

@api.post("/mosaic/stress-test")
async def mosaic_stress_test(authorization: Optional[str] = Header(None)):
    """Global node stress test — simulated multi-node TPS benchmark."""
    await get_current_user(authorization)
    rng = random.Random()
    nodes = [{"node": f"mosaic-node-{i+1}", "region": r,
              "tps": rng.randint(1800, 4200), "p95_latency_ms": rng.randint(38, 220), "status": "HEALTHY"}
             for i, r in enumerate(["eu-central", "eu-west", "us-east", "ap-south", "sa-east"])]
    total_tps = sum(n["tps"] for n in nodes)
    block = await produce_block("stress_test")
    verdict = "READY FOR PUBLISH" if total_tps > 8000 else "DEGRADED"
    return {"nodes": nodes, "total_tps": total_tps,
            "zk_batch_block": (block or {}).get("height"),
            "pqc": "quantum-safe handshake OK", "zero_fee": True,
            "verdict": verdict, "simulated": True}


# =========================================================================
# MOSAIC PROTOCOL BLUEPRINT — GA-T Token Engine (EVM-compatible L2)
# ERC-20 GA-T · Fast-Finality · Zero-Gas abstraction · ZK-Bridge stewardship
# =========================================================================
MOSAIC_CHAIN_ID = 26026
FAST_FINALITY_MS = 400


def _evm_address(seed: str) -> str:
    return "0x" + hashlib.sha256(seed.encode()).hexdigest()[:40]


async def deploy_gat_contract(reason: str) -> dict:
    """Deploy (or autonomously redeploy) the ERC-20 GA-T contract on Mosaic L2."""
    prev = await db.mosaic_contracts.find_one({"symbol": "GA-T", "status": "active"}, {"_id": 0})
    version = int((prev or {}).get("version", 0)) + 1
    now = datetime.now(timezone.utc)
    if prev:
        await db.mosaic_contracts.update_one({"contract_id": prev["contract_id"]},
                                             {"$set": {"status": "superseded", "superseded_at": now}})
    contract = {
        "contract_id": uuid.uuid4().hex,
        "address": _evm_address(f"GA-T|v{version}|{now.isoformat()}"),
        "standard": "ERC-20", "name": "Guardian Angel Token", "symbol": "GA-T", "decimals": 18,
        "chain": "Mosaic L2 (EVM-compatible)", "chain_id": MOSAIC_CHAIN_ID,
        "features": [f"fast_finality_{FAST_FINALITY_MS}ms", "zero_gas_abstraction",
                     "zk_bridge_stewardship", "algorithmic_burn_2pct"],
        "version": version, "status": "active", "deploy_reason": reason,
        "deployed_at": now, "simulated": True,
    }
    await db.mosaic_contracts.insert_one(contract.copy())
    try:
        from routes.swarm import bus_publish
        await bus_publish("mosaic.contract_deployed", "system_janitor",
                          {"address": contract["address"], "version": version, "reason": reason})
    except Exception:
        pass
    return contract


async def get_gat_contract() -> dict:
    c = await db.mosaic_contracts.find_one({"symbol": "GA-T", "status": "active"}, {"_id": 0})
    return c or await deploy_gat_contract("genesis")


@api.get("/mosaic/contract")
async def mosaic_contract(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    history = await db.mosaic_contracts.count_documents({"symbol": "GA-T"})
    return {"contract": clean(await get_gat_contract()), "deployments_total": history}


@api.get("/mosaic/explorer")
async def mosaic_explorer(authorization: Optional[str] = Header(None)):
    """Simulated Mosaic Explorer API — chain telemetry the agents (and Jarvis) monitor."""
    await get_current_user(authorization)
    head = await _chain_head()
    blocks = await db.mosaic_blocks.count_documents(_LIVE)
    supply = await db.token_supply.find_one({"key": "gat"}, {"_id": 0}) or {}
    bridge = await db.mosaic_bridge.find_one({"key": "bridge"}, {"_id": 0}) or {}
    tx_total = 0
    async for b in db.mosaic_blocks.find(_LIVE, {"_id": 0, "tx_batched": 1}):
        tx_total += b.get("tx_batched", 0)
    return {
        "chain": "Mosaic L2 (EVM-compatible)", "chain_id": MOSAIC_CHAIN_ID,
        "block_height": head.get("height", 0), "head_hash": head.get("block_hash", "genesis"),
        "blocks_total": blocks, "tx_anchored_total": tx_total,
        "finality_ms": FAST_FINALITY_MS, "gas_price_user": 0.0,
        "gas_policy": "ZERO-GAS — sponsored by foundation treasury",
        "token": {"symbol": "GA-T", "standard": "ERC-20",
                  "circulating": supply.get("circulating", 0.0),
                  "burned": supply.get("burned", 0.0),
                  "burn_rate_pct": round(float(supply.get("burn_rate", 0.02)) * 100, 2)},
        "contract": clean(await get_gat_contract()),
        "bridge_watch": clean(bridge), "simulated": True,
    }


@api.post("/mosaic/steward-proof")
async def mosaic_steward_proof(authorization: Optional[str] = Header(None)):
    """ZK-Bridge proof of asset stewardship for the Sovereign Wealth Vault:
    proves the user controls their vault assets without revealing them."""
    user = await get_current_user(authorization)
    assets = await db.wealth_assets.find({"user_id": user["user_id"]},
                                         {"_id": 0, "asset_id": 1, "kind": 1, "created_at": 1}).to_list(100)
    head = await _chain_head()
    body = "|".join(f"{a['asset_id']}:{a.get('kind','')}" for a in assets) or "empty-vault"
    state_root = hashlib.sha256(f"{user.get('did','')}|{body}|{head.get('block_hash','genesis')}".encode()).hexdigest()
    proof = {
        "proof_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "scheme": "Groth16 zkSNARK (simulated)", "state_root": state_root,
        "assets_committed": len(assets), "block_height": head.get("height", 0),
        "zk_proof": "zkb-" + hashlib.sha256(("steward" + state_root).encode()).hexdigest()[:40],
        "chain": "Mosaic L2", "mirror": None, "at": datetime.now(timezone.utc),
    }
    bridge = await db.mosaic_bridge.find_one({"key": "bridge"}, {"_id": 0}) or {}
    if bridge.get("failover_active"):
        proof["mirror"] = {"chain": "Base", "mirrored_root": hashlib.sha256(("base|" + state_root).encode()).hexdigest(),
                           "reason": "mosaic_nodes_unreachable"}
    await db.steward_proofs.insert_one(proof.copy())
    try:
        from routes.swarm import bus_publish
        await bus_publish("mosaic.steward_proof", "wealth_sentinel",
                          {"user_id": user["user_id"], "assets": len(assets),
                           "mirrored": bool(proof["mirror"])})
    except Exception:
        pass
    return clean(proof)


async def verify_chain_and_wealth() -> dict:
    """Blueprint autonomy: verify the Mosaic hash-chain (fork detection → autonomous
    GA-T contract redeploy) + anchor unverified Wealth Hub payouts into a block."""
    out = {"fork_detected": False, "orphaned": 0, "redeployed": False, "wealth_anchored": 0}
    blocks = await db.mosaic_blocks.find(_LIVE, {"_id": 0, "height": 1, "block_hash": 1, "prev_hash": 1}) \
                                   .sort("height", 1).to_list(1000)
    prev_hash = "mosaic-genesis"
    for b in blocks:
        if b["prev_hash"] != prev_hash:
            out["fork_detected"] = True
            # Non-destructive self-heal: soft-mark forked blocks as orphaned (records are preserved
            # for audit); every live-chain query filters them out via _LIVE.
            res = await db.mosaic_blocks.update_many(
                {**_LIVE, "height": {"$gte": b["height"]}},
                {"$set": {"orphaned": True, "orphaned_at": datetime.now(timezone.utc),
                          "orphaned_reason": "chain_fork_detected"}})
            out["orphaned"] = res.modified_count
            await deploy_gat_contract("chain_fork_detected_self_heal")
            out["redeployed"] = True
            try:
                from routes.swarm import bus_publish
                await bus_publish("mosaic.fork_healed", "system_janitor",
                                  {"orphaned_blocks": out["orphaned"], "from_height": b["height"]})
            except Exception:
                pass
            break
        prev_hash = b["block_hash"]
    unanchored = await db.payouts.find({"mosaic_anchor": {"$exists": False}},
                                       {"_id": 0, "payout_id": 1}).to_list(50)
    if unanchored:
        block = await produce_block("wealth_verify")
        anchor = (block or await _chain_head()).get("block_hash")
        await db.payouts.update_many({"payout_id": {"$in": [p["payout_id"] for p in unanchored]}},
                                     {"$set": {"mosaic_anchor": anchor, "chain_verified": True}})
        out["wealth_anchored"] = len(unanchored)
    return out
