# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""STORE-REVIEWER DEMO ACCOUNT — idempotent startup seed.

App Store Connect ("App Review Information") and Google Play ("App content → Sign-in
details") require a working demo login when the app is behind a login wall, plus access to
the subscription-gated features without a purchase. This module keeps exactly one such
account in sync:

  * e-mail  — REVIEWER_EMAIL (default appreview@archangel-os.app)
  * password— REVIEWER_PASSWORD (env only, never in the repo; ≥16 chars)
  * tier    — permanent ARCHANGEL entitlement written SERVER-SIDE (tier_paid_with
              "store_reviewer"), so no payment provider and no Demo Mode is involved
  * data    — the full showcase dataset (Life Card, waitlist hunt, €150 refund claim,
              answered family pulse, one family contact) so every screen has content

Rules:
  * The password hash is NEVER overwritten on a normal restart. Set
    REVIEWER_ROTATE_PASSWORD=true for exactly one boot to rotate it (all reviewer
    sessions are revoked in that case).
  * The account is deliberately NOT `inner_circle` and NOT `is_founder` — it must never
    reach Foundation admin surfaces (partner approval, wealth dashboard, Demo Mode).
  * Missing REVIEWER_PASSWORD ⇒ the seed is skipped with a warning (never a weak default).
"""
import os
import uuid
from datetime import datetime, timezone, timedelta

from core import db, logger, TOS_VERSION

REVIEWER_EMAIL = os.environ.get("REVIEWER_EMAIL", "appreview@archangel-os.app").strip().lower()
REVIEWER_NAME = "App Reviewer"
REVIEWER_TIER = "archangel"
_ENTITLEMENT_YEARS = 10
_MIN_PASSWORD_LEN = 16


def _rotate_requested() -> bool:
    return os.environ.get("REVIEWER_ROTATE_PASSWORD", "false").strip().lower() in ("1", "true", "yes")


async def _seed_sample_data(user: dict) -> None:
    """Full showcase dataset — every part is idempotent."""
    from routes.demo import seed_lifecard, seed_presentation_data
    uid = user["user_id"]
    await seed_lifecard(user)                       # marker in db.demo_seed
    if not await db.waitlist.find_one({"user_id": uid, "demo": True}, {"_id": 1}):
        await seed_presentation_data(uid, user["did"])
    if not await db.family_contacts.find_one({"user_id": uid}, {"_id": 1}):
        from routes.family_contacts import _enc
        await db.family_contacts.insert_one({
            "contact_id": uuid.uuid4().hex, "user_id": uid, "name": "Guardian (demo)",
            "phone_enc": _enc().encrypt(b"+421900000000").decode(), "relation": "ine",
            "demo": True, "created_at": datetime.now(timezone.utc)})


async def seed_reviewer_account() -> dict:
    """Create/refresh the store-reviewer account. Safe to call on every startup."""
    password = os.environ.get("REVIEWER_PASSWORD", "").strip()
    if not password:
        logger.warning("reviewer seed skipped — REVIEWER_PASSWORD is not set "
                       "(store reviewers would not be able to sign in)")
        return {"seeded": False, "reason": "password_not_configured"}
    if len(password) < _MIN_PASSWORD_LEN:
        logger.warning(f"reviewer seed skipped — REVIEWER_PASSWORD must be at least {_MIN_PASSWORD_LEN} characters")
        return {"seeded": False, "reason": "password_too_weak"}

    from routes.auth import FOUNDER_EMAIL, _provision_user, _hash_password
    if REVIEWER_EMAIL == FOUNDER_EMAIL:
        logger.warning("reviewer seed skipped — REVIEWER_EMAIL must differ from FOUNDER_EMAIL")
        return {"seeded": False, "reason": "email_conflict"}

    now = datetime.now(timezone.utc)
    existing = await db.users.find_one({"email": REVIEWER_EMAIL}, {"_id": 0, "user_id": 1, "password_hash": 1})
    created = existing is None
    user = await _provision_user(REVIEWER_EMAIL, REVIEWER_NAME)
    uid = user["user_id"]

    # Server-controlled entitlement — refreshed on every boot so the review window never
    # expires mid-review. `is_founder`/`inner_circle` are explicitly held down.
    update = {
        "is_reviewer": True,
        "tier": REVIEWER_TIER,
        "tier_until": now + timedelta(days=365 * _ENTITLEMENT_YEARS),
        "tier_paid_with": "store_reviewer",
        "tier_billing": "reviewer",
        "trial_used": True,
        "inner_circle": False,
        "is_founder": False,
        "language": "en",
        "auth_providers": ["password"],
        "tos_accepted_version": TOS_VERSION,
        "tos_accepted_at": user.get("tos_accepted_at") or now,
        "name": REVIEWER_NAME,
    }
    rotate = _rotate_requested()
    if created or not (existing or {}).get("password_hash") or rotate:
        update["password_hash"] = await _hash_password(password)
    await db.users.update_one({"user_id": uid}, {"$set": update})
    if rotate and not created:
        await db.user_sessions.delete_many({"user_id": uid})   # old sessions can't survive a rotation

    await _seed_sample_data(await db.users.find_one({"user_id": uid}, {"_id": 0}))
    logger.info(f"store-reviewer account ready: {REVIEWER_EMAIL} "
                f"({'created' if created else 'rotated' if rotate else 'verified'}, tier={REVIEWER_TIER})")
    return {"seeded": True, "created": created, "rotated": rotate,
            "email": REVIEWER_EMAIL, "user_id": uid, "tier": REVIEWER_TIER}
