"""Manual check of the GA-T subscription loyalty allocation (run: python tests/manual_loyalty_check.py)."""
import os, asyncio, httpx
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
from motor.motor_asyncio import AsyncIOMotorClient

B = "https://physio-lang-fix.preview.emergentagent.com/api"


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    em = "loyalty-test@example.com"
    tok = httpx.post(f"{B}/auth/dev-bypass", json={"email": em}, timeout=30).json()["session_token"]
    h = {"Authorization": f"Bearer {tok}"}
    uid = (await db.users.find_one({"email": em}, {"user_id": 1}))["user_id"]
    await db.token_ledger.delete_many({"account": uid})
    await db.token_accounts.delete_many({"user_id": uid})
    now = datetime.now(timezone.utc)
    await db.users.update_one({"user_id": uid}, {"$set": {"tier": "sovereign", "tier_paid_with": None},
                                                 "$unset": {"gat_alloc_anchor": "", "gat_alloc_count": ""}})
    w = httpx.get(f"{B}/token/wallet", headers=h, timeout=30).json()
    print("free:", w["subscription_allocation"]["eligible"], w["subscription_allocation"]["reason"], "bal", w["balance"])
    await db.users.update_one({"user_id": uid}, {"$set": {"tier": "guardian", "tier_paid_with": "card",
                                                          "tier_until": now + timedelta(days=30)}})
    w = httpx.get(f"{B}/token/wallet", headers=h, timeout=30).json(); a = w["subscription_allocation"]
    print("card fresh:", a["eligible"], a["months_collected"], a["credited_now"], "bal", w["balance"], "next", a["next_amount"], a["next_bonus_pct"])
    w = httpx.get(f"{B}/token/wallet", headers=h, timeout=30).json(); print("idempotent bal:", w["balance"])
    await db.users.update_one({"user_id": uid}, {"$set": {"gat_alloc_anchor": now - timedelta(days=65),
                                                          "tier_until": now + timedelta(days=300)}})
    w = httpx.get(f"{B}/token/wallet", headers=h, timeout=30).json(); a = w["subscription_allocation"]
    print("65d later:", a["months_collected"], a["credited_now"], "bal", w["balance"], "next", a["next_amount"], a["next_bonus_pct"], a["next_at"][:10])
    await db.users.update_one({"user_id": uid}, {"$set": {"tier_paid_with": "GA-T"}})
    w = httpx.get(f"{B}/token/wallet", headers=h, timeout=30).json()
    print("gat-paid:", w["subscription_allocation"]["eligible"], w["subscription_allocation"]["reason"])
    s = httpx.get(f"{B}/subscription", headers=h, timeout=30).json()
    print("guardian price:", s["tiers"]["guardian"]["price_eur"], s["tiers"]["guardian"]["price_gat"], "| alloc:", s["gat_allocation"]["eligible"])
    print("ledger kinds:", [t["kind"] for t in w["txs"]][:4], "| chain:",
          httpx.get(f"{B}/token/ledger?verify=1&limit=5", headers=h, timeout=30).json()["chain"])
    # leave the test user as a card-paid guardian for UI checks
    await db.users.update_one({"user_id": uid}, {"$set": {"tier_paid_with": "card"}})


asyncio.run(main())
