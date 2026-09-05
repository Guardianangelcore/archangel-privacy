# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
"""GA-T ON-CHAIN BRIDGE — Base L2 (chain id 8453; Sepolia testnet 84532).

The in-app ledger stays the source of truth. Every GA-T credited from a VERIFIED subscription
(RevenueCat sync → loyalty allocation) is stored in `onchain_mints` as `status: "queued"` for users
who linked an EVM wallet. The app itself NEVER talks to the chain (no chain library in the app — Emergent
deployments ship Expo + FastAPI + MongoDB only). An external worker — `export/gat-mint-worker.zip` (mint_worker.py — Foundation VPS),
run on a VPS/laptop with RPC + minter key — drains the queue with `GAT.mintFromLedger(to, amount,
ledgerTx)` (idempotent on-chain by ledger tx id) and writes `sent` / `confirmed` / `failed` back.

Address validation is pure Python: 0x + 40 hex chars, EIP-55 checksum verified when mixed-case,
stored checksummed (keccak-256 implemented below — no external library).

Contract source: /app/contracts/GAT.sol · Founder wallet 0x0E6693153961c01CEa3e73e4e9596aCF35315567
"""
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import hashlib
import os
import re
import uuid

from core import api, db, clean, get_current_user
from routes.origin import ORIGIN

FOUNDER_WALLET = os.environ.get("GAT_FOUNDER_WALLET", "0x0E6693153961c01CEa3e73e4e9596aCF35315567")
CHAIN_ID = int(os.environ.get("GAT_CHAIN_ID", "8453"))
NETWORK = {8453: "Base Mainnet", 84532: "Base Sepolia"}.get(CHAIN_ID, f"chain {CHAIN_ID}")
EXPLORER = {8453: "https://basescan.org", 84532: "https://sepolia.basescan.org"}.get(CHAIN_ID, "https://basescan.org")
DECIMALS = 18
_HEX40 = re.compile(r"^0x[0-9a-fA-F]{40}$")


# ---------------- keccak-256 (pure Python, EIP-55 only — a few calls per wallet link) ----------------
_RC = [0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000, 0x000000000000808B, 0x0000000080000001,
       0x8000000080008081, 0x8000000000008009, 0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
       0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003, 0x8000000000008002, 0x8000000000000080,
       0x000000000000800A, 0x800000008000000A, 0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008]
_ROT = [[0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61], [28, 55, 25, 21, 56], [27, 20, 39, 8, 14]]
_M64 = (1 << 64) - 1


def _rotl(x: int, n: int) -> int:
    return ((x << n) | (x >> (64 - n))) & _M64


def _keccak_f(a: list) -> None:
    for rc in _RC:
        c = [a[x] ^ a[x + 5] ^ a[x + 10] ^ a[x + 15] ^ a[x + 20] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rotl(c[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                a[x + 5 * y] ^= d[x]
        b = [0] * 25
        for x in range(5):
            for y in range(5):
                b[y + 5 * ((2 * x + 3 * y) % 5)] = _rotl(a[x + 5 * y], _ROT[x][y])
        for x in range(5):
            for y in range(5):
                a[x + 5 * y] = b[x + 5 * y] ^ ((~b[(x + 1) % 5 + 5 * y]) & b[(x + 2) % 5 + 5 * y])
        a[0] ^= rc


def keccak256(data: bytes) -> bytes:
    rate = 136  # 1088-bit rate for a 256-bit digest
    padded = bytearray(data) + b"\x01"
    padded += b"\x00" * ((-len(padded)) % rate)
    padded[-1] |= 0x80
    state = [0] * 25
    for off in range(0, len(padded), rate):
        for i in range(rate // 8):
            state[i] ^= int.from_bytes(padded[off + 8 * i: off + 8 * i + 8], "little")
        _keccak_f(state)
    return b"".join(state[i].to_bytes(8, "little") for i in range(4))


def to_checksum_address(addr: str) -> str:
    """EIP-55 mixed-case checksum encoding."""
    body = addr[2:].lower()
    h = keccak256(body.encode("ascii")).hex()
    return "0x" + "".join(ch.upper() if int(h[i], 16) >= 8 else ch for i, ch in enumerate(body))


def is_address(a: Optional[str]) -> bool:
    """0x + 40 hex chars; all-lower / all-upper accepted, mixed case must satisfy the EIP-55 checksum."""
    if not a or not _HEX40.match(a):
        return False
    body = a[2:]
    if body == body.lower() or body == body.upper():
        return True
    return to_checksum_address(a) == a


def ledger_tx_hash(tx_id: str) -> bytes:
    return hashlib.sha256(f"gat-ledger:{tx_id}".encode()).digest()


def contract_address() -> str:
    return os.environ.get("GAT_CONTRACT_ADDRESS", "").strip()


def configured() -> bool:
    """Contract deployed (address known) — the external worker can start settling the queue."""
    return bool(contract_address())


async def queue_mint(user_id: str, amount: float, ledger_tx_id: str, reason: str) -> Optional[dict]:
    """Enqueue an on-chain mint for a wallet-linked user (idempotent per ledger tx). Settled by export/gat-mint-worker.zip."""
    if amount <= 0:
        return None
    u = await db.users.find_one({"user_id": user_id}, {"_id": 0, "wallet_address": 1}) or {}
    if not is_address(u.get("wallet_address")):
        return None
    if await db.onchain_mints.find_one({"ledger_tx_id": ledger_tx_id}, {"_id": 1}):
        return None
    rec = {"mint_id": uuid.uuid4().hex[:16], "user_id": user_id, "to": u["wallet_address"], "amount": round(float(amount), 6),
           "ledger_tx_id": ledger_tx_id, "ledger_tx_hash": ledger_tx_hash(ledger_tx_id).hex(), "reason": reason,
           "status": "queued", "chain_id": CHAIN_ID, "tx_hash": None, "error": None,
           "created_at": datetime.now(timezone.utc), "attempts": 0}
    await db.onchain_mints.insert_one(rec.copy())
    return clean(rec)


# ---------------- API ----------------
class WalletIn(BaseModel):
    address: str


@api.get("/chain/status")
async def chain_status(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    queued = await db.onchain_mints.count_documents({"status": {"$in": ["queued", "sending", "sent"]}})
    mine = await db.onchain_mints.count_documents({"user_id": user["user_id"]})
    last = await db.onchain_mints.find_one({"status": {"$in": ["sent", "confirmed"]}}, {"_id": 0, "sent_at": 1}, sort=[("sent_at", -1)])
    return {"token": {"name": "Guardian Angel Token", "symbol": "GA-T", "decimals": DECIMALS, "cap": 1_000_000_000,
                      "genesis_founder_pct": 25, "standard": "ERC-20"},
            "network": NETWORK, "chain_id": CHAIN_ID, "explorer": EXPLORER, "founder_wallet": FOUNDER_WALLET,
            "contract_address": contract_address() or None, "configured": configured(),
            "mode": "live" if configured() else "queued_until_deploy",
            "settlement": "external_worker (export/gat-mint-worker.zip)", "last_settled_at": (last or {}).get("sent_at"),
            "contract_source": "contracts/GAT.sol", "origin_build": ORIGIN.get("build"),
            "wallet_address": user.get("wallet_address"), "queue_total": queued, "my_mints": mine}


@api.post("/chain/wallet")
async def chain_link_wallet(body: WalletIn, authorization: Optional[str] = Header(None)):
    """Link the user's EVM address (Base) — future verified-purchase GA-T is minted there."""
    user = await get_current_user(authorization)
    addr = body.address.strip()
    if not is_address(addr):
        raise HTTPException(400, "invalid EVM address (expected 0x… 40 hex chars, EIP-55 checksum when mixed-case)")
    addr = to_checksum_address(addr)
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
