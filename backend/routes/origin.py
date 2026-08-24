# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
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


@api.get("/dao/manifest")
async def dao_manifest():
    """Public manifest of the anonymous sovereign foundation (DAO rebranding —
    the founder's personal identity is removed from all public metadata)."""
    return {
        "foundation": "Guardian Angel Sovereign Foundation (DAO)",
        "governance": "Decentralized Autonomous Organization — pseudonymous stewardship, "
                      "GA-T token-aligned incentives, hash-chained public ledgers.",
        "anonymity": "The founder acts solely under the pseudonym 'Guardian Angel'. "
                     "No personal identity is stored in app metadata, PDFs or public endpoints.",
        "liability": "EU AI Act Article 50 (applicable 2 Aug 2026): all AI outputs are "
                     "transparently disclosed as AI-generated, informational only, never "
                     "medical/legal/financial advice. Users act at their own risk; the "
                     "Foundation and its contributors bear no liability (see TOS v2026-06.1).",
        "proof_of_origin_did": ORIGIN.get("did"),
        "license": "Proprietary — All Rights Reserved",
    }
