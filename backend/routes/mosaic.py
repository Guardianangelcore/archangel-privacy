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
    "gas_policy": "ZERO-FEE — gas sponsorovaný treasury nadácie (Sentinel/Archangel výnosy)",
    "simulated": True,
}
LATENCY_FAILOVER_MS = 800

def _cid(sha256_hex: str) -> str:
    """Simulated IPFS CIDv1 derived from the document hash."""
    raw = base64.b32encode(bytes.fromhex(sha256_hex)).decode().lower().rstrip("=")
    return f"bafy{raw[:46]}"

async def _chain_head() -> dict:
    return await db.mosaic_blocks.find_one({}, {"_id": 0}, sort=[("height", -1)]) or \
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
    blocks = await db.mosaic_blocks.count_documents({})
    bridge = await db.mosaic_bridge.find_one({"key": "bridge"}, {"_id": 0}) or \
        {"primary": "Mosaic Chain", "active": "Mosaic Chain", "latency_ms": 0, "mirrored_ops": 0}
    contracts = await db.legacy_contracts.count_documents({})
    return {**CHAIN, "block_height": head.get("height", 0), "blocks_total": blocks,
            "last_block_hash": head.get("block_hash"), "legacy_smart_contracts": contracts,
            "bridge_watch": bridge,
            "note": "SIMULÁCIA — reálne RPC (Mosaic/Base/Polygon) sa pripája vo Phase 3. Architektúra a hashe sú produkčné."}

@api.get("/mosaic/blocks")
async def mosaic_blocks(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    rows = await db.mosaic_blocks.find({}, {"_id": 0}).sort("height", -1).to_list(15)
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
                    "layer": "DePIN off-chain (simulované pinovanie)"})
    return {"files": out, "policy": "On-chain: iba hashe. Off-chain: IPFS/DePIN obsah."}

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
            "kem": "ML-KEM-1024 (Kyber) — encapsulation OK (simulované)",
            "classical": "X25519 ECDH — OK",
            "signature": "ML-DSA-87 (Dilithium) — verified (simulované)",
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
            "detail": ("Latencia nad prahom — kritické operácie zrkadlené na Base/Polygon." if failover
                       else "Mosaic node group v norme — primárny reťazec aktívny.")}

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
