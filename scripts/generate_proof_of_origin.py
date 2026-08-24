# Copyright © 2026 Guardian Angel. All Rights Reserved.
# This source code and its logic are the sole property of Guardian Angel.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Generate the Guardian Angel Proof of Origin: deterministic SHA-256 over the
entire source codebase, DID-link, origin.json artifacts and PROOF_OF_ORIGIN.md.

Reproducible verification: run this script with --verify to recompute the hash
and compare against origin.json.
"""
import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/app")
INCLUDE_DIRS = [ROOT / "backend", ROOT / "frontend" / "app", ROOT / "frontend" / "src"]
EXTRA_FILES = [ROOT / "LICENSE", ROOT / "frontend" / "package.json",
               ROOT / "frontend" / "app.json", ROOT / "backend" / "requirements.txt"]
EXTS = {".py", ".ts", ".tsx"}
# Generated artifacts that embed the hash itself are excluded (avoids circularity)
EXCLUDE_NAMES = {"origin.json"}
EXCLUDE_PARTS = {"node_modules", ".expo", "__pycache__", ".git", ".pytest_cache"}


def manifest():
    files = []
    for d in INCLUDE_DIRS:
        for p in sorted(d.rglob("*")):
            if not p.is_file() or p.suffix not in EXTS:
                continue
            if p.name in EXCLUDE_NAMES or EXCLUDE_PARTS & set(p.parts):
                continue
            files.append(p)
    files.extend(f for f in EXTRA_FILES if f.exists())
    return sorted(set(files))


def codebase_sha256():
    h = hashlib.sha256()
    files = manifest()
    for p in files:
        rel = str(p.relative_to(ROOT))
        h.update(rel.encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest(), len(files)


def main():
    digest, nfiles = codebase_sha256()
    if "--verify" in sys.argv:
        rec = json.loads((ROOT / "backend" / "origin.json").read_text())
        ok = rec["codebase_sha256"] == digest
        print(f"recorded: {rec['codebase_sha256']}\ncurrent:  {digest}\nmatch: {ok}")
        sys.exit(0 if ok else 1)

    now = datetime.now(timezone.utc).isoformat()
    short = digest[:8].upper()
    record = {
        "owner": "Guardian Angel",
        "role": "Sole Visionary and Legal Owner",
        "license": "Proprietary — All Rights Reserved (AGPL-v3 rescinded)",
        "build": f"GA-ORIGINAL-{short}",
        "codebase_sha256": digest,
        "did": f"did:guardian:pex:sha256:{digest}",
        "anchored_at": now,
        "files_in_manifest": nfiles,
        "method": "sha256(relpath + NUL + bytes + NUL, sorted manifest)",
    }
    payload = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    (ROOT / "backend" / "origin.json").write_text(payload)
    (ROOT / "frontend" / "src" / "origin.json").write_text(payload)
    # Raw digest file for external blockchain timestamping (e.g. OpenTimestamps)
    (ROOT / "PROOF_OF_ORIGIN.sha256").write_text(digest + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
