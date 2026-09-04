# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
"""GA-T ON-CHAIN BRIDGE — Base L2 (chain id 8453; Sepolia testnet 84532).

The in-app ledger stays the source of truth. Every GA-T credited from a VERIFIED subscription
(RevenueCat sync → loyalty allocation) is queued as an on-chain mint for users who linked an EVM
wallet. The swarm loop drains the queue with `GAT.mintFromLedger(to, amount, ledgerTx)` (idempotent
on-chain by ledger tx id). Without BASE_RPC_URL / GAT_CONTRACT_ADDRESS / GAT_MINTER_PRIVATE_KEY the
bridge runs in "not configured" mode: mints stay `queued` and are visible in the app.

Contract source: /app/contracts/GAT.sol · Founder wallet 0x0E6693153961c01CEa3e73e4e9596aCF35315567
"""
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import asyncio
import hashlib
import os
import uuid

from core import api, db, logger, clean, get_current_user
from routes.origin import ORIGIN

FOUNDER_WALLET = os.environ.get("GAT_FOUNDER_WALLET", "0x0E6693153961c01CEa3e73e4e9596aCF35315567")
CHAIN_ID = int(os.environ.get("GAT_CHAIN_ID", "8453"))
NETWORK = {8453: "Base Mainnet", 84532: "Base Sepolia"}.get(CHAIN_ID, f"chain {CHAIN_ID}")
EXPLORER = {8453: "https://basescan.org", 84532: "https://sepolia.basescan.org"}.get(CHAIN_ID, "https://basescan.org")
DECIMALS = 18
MINT_ABI = [{"inputs": [{"name": "to", "type": "address"}, {"name": "value", "type": "uint256"}, {"name": "ledgerTx", "type": "bytes32"}],
             "name": "mintFromLedger", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}]


def _cfg() -> dict:
    return {"rpc": os.environ.get("BASE_RPC_URL", "").strip(), "contract": os.environ.get("GAT_CONTRACT_ADDRESS", "").strip(),
            "key": os.environ.get("GAT_MINTER_PRIVATE_KEY", "").strip()}


def configured() -> bool:
    c = _cfg()
    return bool(c["rpc"] and c["contract"] and c["key"])


def is_address(a: Optional[str]) -> bool:
    try:
        from web3 import Web3
        return bool(a) and Web3.is_address(a)
    except Exception:
        return False


def ledger_tx_hash(tx_id: str) -> bytes:
    return hashlib.sha256(f"gat-ledger:{tx_id}".encode()).digest()


async def queue_mint(user_id: str, amount: float, ledger_tx_id: str, reason: str) -> Optional[dict]:
    """Enqueue an on-chain mint for a wallet-linked user (idempotent per ledger tx)."""
    if amount <= 0:
        return None
    u = await db.users.find_one({"user_id": user_id}, {"_id": 0, "wallet_address": 1}) or {}
    if not is_address(u.get("wallet_address")):
        return None
    if await db.onchain_mints.find_one({"ledger_tx_id": ledger_tx_id}, {"_id": 1}):
        return None
    rec = {"mint_id": uuid.uuid4().hex[:16], "user_id": user_id, "to": u["wallet_address"], "amount": round(float(amount), 6),
           "ledger_tx_id": ledger_tx_id, "reason": reason, "status": "queued", "chain_id": CHAIN_ID,
           "tx_hash": None, "error": None, "created_at": datetime.now(timezone.utc), "attempts": 0}
    await db.onchain_mints.insert_one(rec.copy())
    return clean(rec)


def _send_mint_sync(to: str, amount: float, ledger_tx_id: str) -> str:
    from web3 import Web3
    c = _cfg()
    w3 = Web3(Web3.HTTPProvider(c["rpc"], request_kwargs={"timeout": 30}))
    acct = w3.eth.account.from_key(c["key"])
    contract = w3.eth.contract(address=Web3.to_checksum_address(c["contract"]), abi=MINT_ABI)
    value = int(round(amount * (10 ** DECIMALS)))
    tx = contract.functions.mintFromLedger(Web3.to_checksum_address(to), value, ledger_tx_hash(ledger_tx_id)).build_transaction({
        "from": acct.address, "nonce": w3.eth.get_transaction_count(acct.address, "pending"), "chainId": CHAIN_ID,
        "maxFeePerGas": w3.eth.gas_price * 2, "maxPriorityFeePerGas": w3.to_wei(0.001, "gwei")})
    tx["gas"] = int(w3.eth.estimate_gas(tx) * 1.2)
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    return h.hex()


async def process_mint_queue(limit: int = 5) -> int:
    """Swarm-loop worker: sends queued mints when the bridge is configured."""
    if not configured():
        return 0
    n = 0
    async for m in db.onchain_mints.find({"status": "queued", "attempts": {"$lt": 5}}, {"_id": 0}).limit(limit):
        claim = await db.onchain_mints.update_one({"mint_id": m["mint_id"], "status": "queued"},
                                                  {"$set": {"status": "sending"}, "$inc": {"attempts": 1}})
        if not claim.modified_count:
            continue
        try:
            tx_hash = await asyncio.to_thread(_send_mint_sync, m["to"], m["amount"], m["ledger_tx_id"])
            await db.onchain_mints.update_one({"mint_id": m["mint_id"]}, {"$set": {"status": "sent", "tx_hash": tx_hash, "sent_at": datetime.now(timezone.utc)}})
            n += 1
        except Exception as e:
            logger.warning(f"GA-T mint {m['mint_id']} failed: {e}")
            await db.onchain_mints.update_one({"mint_id": m["mint_id"]}, {"$set": {"status": "queued", "error": str(e)[:300]}})
    return n


# ---------------- API ----------------
class WalletIn(BaseModel):
    address: str


@api.get("/chain/status")
async def chain_status(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    c = _cfg()
    queued = await db.onchain_mints.count_documents({"status": {"$in": ["queued", "sending"]}})
    mine = await db.onchain_mints.count_documents({"user_id": user["user_id"]})
    return {"token": {"name": "Guardian Angel Token", "symbol": "GA-T", "decimals": DECIMALS, "cap": 1_000_000_000,
                      "genesis_founder_pct": 25, "standard": "ERC-20"},
            "network": NETWORK, "chain_id": CHAIN_ID, "explorer": EXPLORER, "founder_wallet": FOUNDER_WALLET,
            "contract_address": c["contract"] or None, "configured": configured(),
            "mode": "live" if configured() else "queued_until_deploy",
            "contract_source": "contracts/GAT.sol", "origin_build": ORIGIN.get("build"),
            "wallet_address": user.get("wallet_address"), "queue_total": queued, "my_mints": mine}


@api.post("/chain/wallet")
async def chain_link_wallet(body: WalletIn, authorization: Optional[str] = Header(None)):
    """Link the user's EVM address (Base) — future verified-purchase GA-T is minted there."""
    user = await get_current_user(authorization)
    addr = body.address.strip()
    if not is_address(addr):
        raise HTTPException(400, "invalid EVM address (expected 0x… 40 hex chars)")
    from web3 import Web3
    addr = Web3.to_checksum_address(addr)
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"wallet_address": addr, "wallet_linked_at": datetime.now(timezone.utc)}})
    return {"ok": True, "wallet_address": addr, "network": NETWORK}


@api.delete("/chain/wallet")
async def chain_unlink_wallet(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await db.users.update_one({"user_id": user["user_id"]}, {"$unset": {"wallet_address": "", "wallet_linked_at": ""}})
    return {"ok": True}


@api.get("/chain/mints")
async def chain_my_mints(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.onchain_mints.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"mints": rows, "configured": configured(), "explorer": EXPLORER}
