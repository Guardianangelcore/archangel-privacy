# Guardian Health & Angel — Sovereign Survival OS (Archangel)

**Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.**
Proprietary & Confidential — see `LICENSE`. This package is prepared for jury/investor evaluation only.

---

## What it is

A sovereign, AI-driven mobile operating system for medical dignity, senior safety and
community solidarity — built as a full-stack Expo (React Native) + FastAPI + MongoDB product.

The system has grown from a health companion into a **Sovereign Survival OS**:

| Layer | Capability |
|---|---|
| **Jarvis 2.0 Soul Engine** | Levels 1→10 AI companion (gpt-5.4), self-teaching memory, full voice loop (Whisper STT → reasoning → emotional TTS), morning briefings, anomaly alarms |
| **Guardian Lens** | One photo of a pill/report → instant AI analysis + actions (reminders, booking, vault) |
| **Universal Health Protocol (UHP/1.0)** | Sovereign API gateway for clinics/insurers/labs — HMAC-SHA256 signed, replay-protected, idempotent, 1.02B-stream topology |
| **Arbitrage Brain** | 10 500+ clinic index, 32 countries — net-benefit optimization (price + time-value of waiting) |
| **Liquidity Bank** | Double-entry ledger, instant card payout state machine (Visa Direct / MC Send adapter-ready), data-backed credit |
| **Ascension Protocol** | Bio-Digital Twin (treatment simulation + trajectories), Predictive Sentinel, GA-T Living Currency + GBI, SHA3-512 Collective Truth chain, Cognitive Handover (Personality Blueprint) |
| **Safety Stack** | Fall detection, acoustic guard, stealth beacon, duress PIN, mesh messenger, emergency QR, offline compass |
| **Legal Engine** | EU AI Act Art. 50 compliance, versioned TOS gate, international testaments, healthcare proxy, PDF exports |

## Tech stack

- **Frontend**: Expo SDK / React Native, expo-router, Reanimated (60 FPS glass UI), expo-audio/video, 14-language i18n
- **Backend**: FastAPI micro-router architecture (35+ route modules), Motor (MongoDB), `emergentintegrations` (gpt-5.4, Claude, Whisper, TTS)
- **Security**: zero-knowledge vault encryption, DID identity, HMAC gateway, tamper-evident hash-chain ledgers, Proof-of-Origin (SHA-256 anchored via OpenTimestamps on Bitcoin)

## Quickstart (evaluation)

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001

# Frontend
cd frontend && yarn install && yarn start
```

Environment: `backend/.env` requires `MONGO_URL`, `EMERGENT_LLM_KEY`. Frontend uses `EXPO_PUBLIC_BACKEND_URL`.

## Quality

- **432/432 backend tests green** (24 pytest phases: protocol, ledger math, HMAC/replay, LLM-live, 60-concurrent ingest p95 < 4 s)
- Full E2E frontend passes via automated testing agent (20+ iterations)
- Stability audit 9/9 · score 100 · Mosaic global stress test: **READY FOR PUBLISH**

## Proof of Origin

The authoritative build is fingerprinted (SHA-256 of the entire codebase), DID-linked
(`did:guardian:pex:sha256:…`) and anchored on the Bitcoin blockchain via OpenTimestamps.
Hidden watermarks exist in the UI bundle and in every API response header (`X-Guardian-Origin`).

## Contact

Guardian Angel Sovereign Foundation (DAO) — `guardianangel.core@proton.me`
