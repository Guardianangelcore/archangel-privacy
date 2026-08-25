# API SPECIFICATION — Guardian Sovereign OS

**Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). Proprietary & Confidential.**

Base URL: `https://<deployment>/api` · Auth: `Authorization: Bearer <session_token>`
All responses carry `X-Guardian-Origin` + `X-Origin-DID` watermark headers.

## 1. Conventions

- JSON in/out, UTC ISO-8601 timestamps, IDs are prefixed UUIDs (`uhp_…`, `pay_…`).
- Errors: FastAPI shape `{"detail": "reason_code"}` with proper HTTP status.
- Idempotency: mutation endpoints accept `Idempotency-Key` header or `idempotency_key` body field.

## 2. Endpoint groups (selected)

| Group | Endpoints | Notes |
|---|---|---|
| Auth | `POST /auth/session`, `GET /auth/me`, `POST /auth/logout`, `PATCH /me/prefs` | Emergent Google OAuth exchange |
| Vault | `GET/POST/DELETE /vault/documents…`, `POST /vault/documents/{id}/ocr` | encrypted object storage, gpt-5.4 vision OCR |
| Jarvis | `POST /agent/chat`, `GET /agent/state|briefing|memories|anomalies`, `POST /agent/analyze|transcribe` | Soul Engine |
| Voice | `POST /voice/tts` (voice, speed 0.7–1.3), `POST /voice/liveness` | OpenAI TTS / Whisper |
| Lens | `POST /lens/analyze`, `GET /lens/history`, `POST /lens/{id}/save-to-vault` | photo → structured AI verdict |
| UHP | see §3 | partner gateway |
| Arbitrage | `POST /arbitrage/analyze`, `GET /arbitrage/stats|procedures`, `POST /arbitrage/quote` | global clinic index |
| Liquidity | `POST /liquidity/payout`, `GET /liquidity/balance|payouts|ledger`, `POST /liquidity/credit/score|draw` | double-entry ledger |
| Twin | `GET /twin/profile|trajectory`, `POST /twin/simulate` | Bio-Digital Twin |
| Sentinel | `POST /sentinel/gait`, `GET /sentinel/predict` | pre-event risk |
| Tokens | `POST /edge/contribute`, `GET /edge/status`, `GET /token/…` | GA-T + GBI |
| Truth | `POST /mesh/truth`, `GET /mesh/truth/verify` | SHA3-512 chain |
| Blueprint | `POST /legacy/blueprint/train|ask`, `GET /legacy/blueprint` | cognitive handover |
| Founder | `GET /founder/toolkit`, `GET /founder/release/{doc}` | investor demo + this package |
| Legal | `GET /legal/region|tos`, `POST /legal/accept|testament`, `GET /legal/*.pdf` | Art. 50 compliance |
| Safety | `POST /fall-event|beacon/trigger|acoustic-event`, `GET /emergency-qr/{did}` | public emergency read |

## 3. UHP/1.0 — Universal Health Protocol

### 3.1 Register partner
```
POST /api/uhp/partners/register
{ "org_name": "Clinic X", "org_type": "clinic|insurer|lab|sensor_network|government|pharmacy",
  "country": "SK", "contact_email": "ops@clinic.x" }
→ { "partner_id", "api_key", "hmac_secret", "protocol": "UHP/1.0" }   // secret shown ONCE
```

### 3.2 Signed ingest
```
POST /api/uhp/ingest
Headers:
  X-UHP-Key:       <api_key>
  X-UHP-Timestamp: <unix seconds>          // ±300 s replay window
  X-UHP-Signature: HMAC_SHA256(hmac_secret, "{ts}.{raw_body}")   // hex
Body (envelope):
{ "kind": "vitals|lab_result|document|insurance_claim|sensor|threat_mesh",
  "subject_did": "did:guardian:…",
  "idempotency_key": "unique-per-message",
  "payload": { … kind-specific … } }
→ 200 { "accepted": true, "event_id" } · 401 bad signature · 409 replay · 429 rate limit (240/min)
```

### 3.3 Introspection
```
GET /api/uhp/standard            // machine-readable protocol spec
GET /api/uhp/capacity            // topology + live counters (1.02B stream fan-out)
GET /api/uhp/partners/{id}/stats // X-UHP-Key required
GET /api/uhp/feed                // subject-side audit of received events
```

## 4. Liquidity payout state machine

```
POST /api/liquidity/payout
{ "amount": 50, "currency": "EUR", "card_last4": "4242",
  "network": "visa|mc", "idempotency_key": "…" }
→ { "payout": { "state": "settled",
     "timeline": [ {"state":"initiated"},{"state":"authorized"},{"state":"settled"} ],
     "fee_eur": 0.85, "trace_id": "…" } }
Guards: insufficient_funds, PAYOUT_LIMIT 10 000 €, idempotent replays return original.
```

## 5. Founder's Toolkit

```
GET /api/founder/toolkit
→ { "forecast": { "assumptions": {…}, "years": [ {year, users, mrr_eur, arr_eur, …} ] },
    "roadmap":  [ {year, era, title, detail} ],
    "release_package": { "docs": [ {name, bytes, sha256} ] } }

GET /api/founder/release/{README.md|ARCHITECTURE.md|API_SPEC.md|LICENSE}
→ { "name", "content", "sha256", "bytes" }
```

## 6. Rate limits & SLOs

- UHP ingest: 240 msg/min/partner, p95 < 4 s at 60 concurrent (verified by test suite)
- Global: 300 concurrent authenticated requests → 300/300 OK (load sanity)
- Test coverage: 432 backend tests across 24 phases, all green.
