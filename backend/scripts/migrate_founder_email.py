"""One-off migration: founder e-mail guardian.angel.core@proton.me → guardianangel.core@proton.me (Iter 81)."""
import asyncio, os, sys
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from motor.motor_asyncio import AsyncIOMotorClient

db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
OLD, NEW = "guardian.angel.core@proton.me", "guardianangel.core@proton.me"
APPLY = "--apply" in sys.argv


async def main():
    old = await db.users.find_one({"email": OLD}, {"_id": 0})
    new = await db.users.find_one({"email": NEW}, {"_id": 0, "user_id": 1, "tier": 1})
    print("old founder doc:", {k: old.get(k) for k in ("user_id", "email", "tier", "inner_circle")} if old else None)
    print("new e-mail already used by:", new)
    print("e-mail-ish fields on founder:", [k for k in (old or {}) if "mail" in k])
    cols = await db.list_collection_names()
    hits = []
    for c in cols:
        for f in ("email", "to_email", "requester_email", "owner_email", "founder_email", "contact_email", "emails"):
            n = await db[c].count_documents({f: OLD})
            if n:
                hits.append((c, f, n))
    print("references:", hits)
    if not APPLY:
        print("dry run — pass --apply to migrate")
        return
    if old and not new:
        for c, f, n in hits:
            r = await db[c].update_many({f: OLD}, {"$set": {f: NEW}})
            print(f"  {c}.{f}: {r.modified_count} updated")
        # sessions keyed by user_id keep working; nothing else to do
        print("migrated")
    elif old and new:
        print("CONFLICT: both accounts exist — merge manually")
    else:
        print("no old founder doc — nothing to migrate")

asyncio.run(main())
