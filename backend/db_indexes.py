# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Central MongoDB index registry — split out of server.py (final refactor).
Every collection index powering the 16k+ TPS simulated benchmark lives here."""
from core import db, logger


async def ensure_indexes() -> None:
    try:
        await db.users.create_index("email", unique=True)
        await db.users.create_index("user_id", unique=True)
        await db.users.create_index("did", unique=True)
        await db.user_sessions.create_index("session_token", unique=True)
        await db.user_sessions.create_index("expires_at", expireAfterSeconds=0)
        await db.documents.create_index([("user_id", 1), ("uploaded_at", -1)])
        await db.waitlist.create_index([("user_id", 1), ("created_at", -1)])
        # High-velocity performance indexes (global scale prep)
        await db.calendar_events.create_index([("user_id", 1), ("date", -1)])
        await db.health_drops.create_index([("user_id", 1), ("created_at", -1)])
        await db.recovery.create_index("user_id")
        await db.pulse_requests.create_index([("target_user", 1), ("created_at", -1)])
        await db.pharmacy_watches.create_index("user_id")
        await db.gateway_grants.create_index("token", unique=True)
        await db.gateway_audit.create_index([("user_id", 1), ("at", -1)])
        await db.sentinel_signals.create_index([("at", -1)])
        await db.sentinel_signals.create_index([("anon", 1), ("kind", 1), ("at", -1)])
        await db.stripe_donations.create_index("session_id", unique=True)
        await db.marketplace_sales.create_index([("user_id", 1), ("offer_id", 1)], unique=True)
        # Tokenized ecosystem + swarm
        await db.token_ledger.create_index("seq", unique=True)
        await db.token_ledger.create_index([("account", 1), ("kind", 1), ("at", -1)])
        await db.token_accounts.create_index("user_id", unique=True)
        await db.neural_bus.create_index([("at", -1)])
        await db.security_events.create_index([("at", -1)])
        await db.depin_nodes.create_index("node_id", unique=True)
        # Master-Seal: sovereign recovery + global layer
        await db.guardians.create_index([("user_id", 1), ("guardian_user_id", 1)], unique=True)
        await db.login_handshakes.create_index([("status", 1), ("expires_at", 1)])
        await db.recovery_requests.create_index("req_id", unique=True)
        await db.talismans.create_index("user_id", unique=True)
        await db.truth_claims.create_index([("created_at", -1)])
        await db.truth_votes.create_index([("claim_id", 1), ("voter_id", 1)], unique=True)
        await db.bio_beacons.create_index([("did", 1), ("active", 1)])
        await db.satellite_queue.create_index([("status", 1), ("created_at", -1)])
        # World-Class Finale + Mosaic Protocol
        await db.bioscan_results.create_index([("user_id", 1), ("at", -1)])
        await db.enviro_reports.create_index([("at", -1)])
        await db.revenue_events.create_index([("at", -1)])
        await db.longevity_scores.create_index([("user_id", 1), ("at", -1)])
        await db.mosaic_blocks.create_index("height", unique=True)
    except Exception as e:
        logger.warning(f"index setup: {e}")
