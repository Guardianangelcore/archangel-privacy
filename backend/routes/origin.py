# Copyright © 2026 Guardian Angel. All Rights Reserved.
# This source code and its logic are the sole property of Guardian Angel.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Proof of Origin — DID-linked SHA-256 codebase anchor (IP protection layer)."""
import json
from pathlib import Path

from core import api, db

_ORIGIN_PATH = Path(__file__).resolve().parent.parent / "origin.json"

def load_origin() -> dict:
    try:
        return json.loads(_ORIGIN_PATH.read_text())
    except Exception:
        return {}

ORIGIN = load_origin()

@api.get("/origin")
async def proof_of_origin():
    """Public, verifiable Proof of Existence for the original Guardian Angel build."""
    rec = await db.ip_protection.find_one(
        {"kind": "proof_of_origin"}, {"_id": 0}, sort=[("anchored_at", -1)]
    )
    if rec:
        return rec
    return {**ORIGIN, "kind": "proof_of_origin", "anchored": False}
