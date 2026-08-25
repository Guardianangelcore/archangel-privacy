# ARCHITECTURE — Sovereign Survival OS

**Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). Proprietary & Confidential.**

## 1. System overview

```
┌────────────────────────────────────────────────────────────────────┐
│  MOBILE CLIENT (Expo / React Native, expo-router)                  │
│  Home Orb · Jarvis 2.0 · Guardian Lens · Command Deck (Monolith)   │
│  Angel Mode 2.0 · Health/Family/Legacy/Hunter hubs · 14 languages  │
└──────────────┬─────────────────────────────────────────────────────┘
               │ HTTPS  /api/*  (Bearer session token)
┌──────────────▼─────────────────────────────────────────────────────┐
│  FASTAPI MICRO-ROUTER BACKEND (35+ modules, shared `api` router)   │
│                                                                    │
│  core.py ── db / auth / storage / push / PDF / AML helpers         │
│  routes/                                                           │
│   ├─ auth, health, family, hunter, legacy      (product pillars)   │
│   ├─ agent (Jarvis Soul Engine)  lens  clinic_sync                 │
│   ├─ uhp (UHP/1.0 gateway)  arbitrage  liquidity                   │
│   ├─ ascension (Twin·Sentinel·GBI·Truth·Blueprint)  swarm          │
│   ├─ wealth  seal  subscription  token  mosaic  founder            │
│   └─ …legal, recovery, insurance, medic, compass, globalnet        │
│                                                                    │
│  ASGI middleware: X-Guardian-Origin watermark on every response    │
└──────┬───────────────┬──────────────────────┬──────────────────────┘
       │               │                      │
┌──────▼─────┐  ┌──────▼───────────┐  ┌───────▼────────────────┐
│  MongoDB   │  │ Emergent LLM Key │  │ Emergent Object Storage│
│  (Motor)   │  │ gpt-5.4 · Claude │  │ (encrypted vault docs) │
│  60+ colls │  │ Whisper · TTS    │  │                        │
└────────────┘  └──────────────────┘  └────────────────────────┘
```

## 2. Key subsystems

### 2.1 Jarvis Soul Engine (`routes/agent.py`)
XP/level state machine (10 levels, ability unlocks), LLM memory extraction after each chat
(topics, importance, dedup), daily cached briefing (weather + meds + follow-up questions),
anomaly detection (BP/glucose trends → push), visual-thinking analysis, Whisper transcription,
emotional TTS (voice + speed mapped to mood).

### 2.2 UHP/1.0 Gateway (`routes/uhp.py`)
Partner registration issues `api_key` + `hmac_secret`. Every ingest is signed
`HMAC-SHA256("{ts}.{body}")`, replay window ±300 s, `idempotency_key` dedup,
240 msg/min sliding-window rate limit. Envelope kinds route to internal engines
(vitals → bioscan + push; sensor/threat_mesh → sentinel streams). Topology:
12 regions × 4096 shards × 32 nodes × 650 streams ≈ **1.02 B concurrent streams**.

### 2.3 Arbitrage Brain (`routes/arbitrage.py`)
Deterministic index (seed 2026) of 10 500 clinics / 32 countries / 14 procedures.
`net_benefit = (local_price + time_saved_weeks × week_value[urgency]) − (price + travel + lodging)`.
Picks: best_value / cheapest / fastest / best_quality.

### 2.4 Liquidity Bank (`routes/liquidity.py`)
Double-entry `ledger_entries` with enforced balance. Payout state machine
initiated → authorized → settled with timeline + trace id, Idempotency-Key dedup,
fee 1.2 % + 0.25 (min 0.50), FX table + 0.6 % margin. Rails adapter pattern:
`SimulatedRails` swaps for Visa Direct / Mastercard Send via `RAILS_MODE` env.
Data-Backed Credit: limit scored from data wealth (docs, bioscans, GA-T), 9.9 % APR.

### 2.5 Ascension Protocol (`routes/ascension.py`)
- **Bio-Digital Twin** — gpt-5.4 treatment simulation (strict JSON verdict) + least-squares
  trajectory projection (6/12/24 mo, physiological clamps, composite risk).
- **Predictive Sentinel** — gait/tremor sampling → 0-100 risk, pushes Inner Circle PRE-event.
- **Living Currency (GA-T)** — edge compute contributions (fraud-guarded) → tokens; daily GBI.
- **Collective Truth** — SHA3-512 hash-chain with full re-verification.
- **Cognitive Handover** — Personality Blueprint trained from memories; digital-echo Q&A.

### 2.6 Agent Swarm (`swarm.py`)
7 autonomous agents: hunter, wealth, safety, sovereign_guard, data_broker, gbi_distributor,
news_sentinel — periodic orchestration (waitlist auto-hunts, data-sale negotiation,
talisman integrity, satellite nano-packet queue, Mosaic block production).

## 3. Data model (principal collections)

`users, sessions, vault_documents, waitlist, health_metrics, agent_state/memories/conversations,
uhp_partners/events, sentinel_streams/alerts, arb_clinics/analyses, payouts, ledger_entries,
liq_balances, credit_lines, edge_nodes, gbi_payments, collective_truth, personality_blueprints,
aml_ledger, mosaic_blocks, subscription/inner_circle flags, family_links, autopilot`

## 4. Security layers

1. Bearer session auth (Emergent Google OAuth exchange) + founder/Inner-Circle gating
2. Zero-knowledge vault (X25519 client-side encryption for Health Drop portal)
3. HMAC partner gateway + replay/idempotency/rate-limits
4. Tamper-evident hash-chains (AML ledger, Collective Truth SHA3-512, Mosaic L2 anchors)
5. Duress PIN (decoy vault, silent alarm), Ghost Mode anonymized tokens
6. Proof-of-Origin: codebase SHA-256 → OpenTimestamps (Bitcoin), watermark headers

## 5. Simulated-by-design (adapter-ready)

Card settlement rails, satellite uplink, BLE mesh radio, rPPG camera vitals,
NCZI/ÚZIS registry, DNA sequencing (hash-anchored metadata only). Each has a clean
adapter seam for production integration without touching business logic.
