# PROOF OF ORIGIN — Guardian Health & Angel (Sovereign Survival OS)

**Copyright © 2026 Guardian Angel. All Rights Reserved.**
Sole Visionary and Legal Owner: **Guardian Angel**
License: **Proprietary** (GNU AGPL-v3 rescinded — see `LICENSE`)

## Irrefutable Proof of Existence

| Field | Value |
|---|---|
| Codebase SHA-256 | `dd64d4a0b046d03d1495cca21a2e4a37a56ca4896336129a60a6856b85dfd5ac` |
| DID-link | `did:guardian:pex:sha256:dd64d4a0b046d03d1495cca21a2e4a37a56ca4896336129a60a6856b85dfd5ac` |
| Build fingerprint | `GA-ORIGINAL-DD64D4A0` |
| Anchored at (UTC) | `2026-08-24T16:22:58Z` (server clock) |
| Files in manifest | 91 source files |

## Blockchain Timestamp (Bitcoin via OpenTimestamps)

The raw digest file `PROOF_OF_ORIGIN.sha256` was stamped to the **Bitcoin
blockchain** through the OpenTimestamps protocol. The cryptographic proof is
stored in `PROOF_OF_ORIGIN.sha256.ots` (keep this file safe — it IS the proof).

Submitted to 4 independent calendar servers:
- https://a.pool.opentimestamps.org
- https://b.pool.opentimestamps.org
- https://a.pool.eternitywall.com
- https://ots.btc.catallaxy.com

The Bitcoin attestation finalizes automatically within a few hours. Verify any
time with:

```
ots verify PROOF_OF_ORIGIN.sha256.ots -f PROOF_OF_ORIGIN.sha256
ots upgrade PROOF_OF_ORIGIN.sha256.ots   # pulls the final Bitcoin attestation
```

## Reproducible Hash Method

`sha256(relative_path + NUL + file_bytes + NUL)` over a sorted manifest of all
`.py/.ts/.tsx` sources in `backend/`, `frontend/app/`, `frontend/src/`, plus
`LICENSE`, `frontend/package.json`, `frontend/app.json`,
`backend/requirements.txt`. Generated artifacts embedding the hash
(`origin.json`) are excluded to avoid circularity.

Recompute and verify at any time:

```
python /app/scripts/generate_proof_of_origin.py --verify
```

## Digital Watermarks (original-build identification)

1. **UI (hidden):** `frontend/src/watermark.ts` exports `GA_ORIGIN_MARK` — a
   zero-width-wrapped fingerprint string rendered invisibly in the root layout
   and compiled into every JS bundle (grep for `GA-ORIGIN`).
2. **Backend (every response):** HTTP middleware signs all API responses with
   `X-Guardian-Origin: GA-ORIGINAL-DD64D4A0` and `X-Origin-DID` headers.
3. **Public verification endpoint:** `GET /api/origin` returns the anchored
   Proof of Origin record (persisted in the `ip_protection` DB collection).
4. **Source files:** every `.py/.ts/.tsx` file carries the Guardian Angel
   copyright header (injected via `scripts/inject_headers.sh`).

Any build lacking these markers is an unauthorized copy.
