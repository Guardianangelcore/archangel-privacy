# Guardian Health & Angel — Product Requirements (MVP)

## Vision
A sovereign, AI-driven mobile OS for medical dignity, senior safety, and community solidarity. Zero-knowledge storage, dual-mode UX (Standard vs. Angel), multi-lingual (SK/CZ/EN/DE).

## MVP Modules
1. **Onboarding & Google Auth** — Emergent Google OAuth, language picker (SK/CZ/EN/DE), Guardian Angel author credit.
2. **Standard Mode Home** — quick actions (Vault, Translate, Waitlist, Donor, Solidarity, Respect Map, Physio, Blackout, Wellness Check, Family Dashboard), floating Emergency QR button, "Simulate Fall" safety.
3. **Angel Mode Home** — 2×2 huge tiles (SOS, Call Family, Medications, Documents) + Wellness Check banner, tabs hidden, oversized type. Toggle in header, haptic on switch.
4. **Health Vault** — Upload/list/delete encrypted documents (Emergent Object Storage). Per-doc AI translation with Claude Sonnet 5. **OCR (gpt-5.4 vision + pypdf/pymupdf)** for photos & PDFs → "Read + translate" one-tap flow.
5. **AI Health Translator (Jarvis)** — Paste any medical text → structured plain-language explanation in user's language. Voice TTS playback.
6. **Waitlist Hunter** — Add tracked appointment, one-tap "Scan now" (simulated 35% hit rate). **Push notification on slot found (Emergent managed push)**.
7. **Emergency QR & Donor Card** — Full-screen scannable QR encoding DID + critical fields. Public read endpoint `/api/emergency-qr/{did}`.
8. **Fall-Verify-Notify** — 30 s countdown with rhythmic haptics, huge "I'M OK" cancel, auto-escalate on timeout, `POST /api/fall-event` logs it.
9. **Real-time Fall Detection (Fall Guard)** — expo-sensors accelerometer heuristic (free-fall <0.35g → impact >2.7g within 1.2s) auto-opens Fall-Verify. Toggle in Profile. Native only, while app open.
10. **Inactivity Guard** — no device movement for configurable 4/6/8/12h during daytime (08–21h) → `POST /api/wellness/inactivity-alert` + push. Toggle in Profile.
11. **Daily AI Wellness Check (Jarvis)** — `/wellness` screen: voice-prompted mood check (TTS), mood chips 1–5 + free text → Claude sentiment {reply, score, summary}, logged for family.
12. **Family Dashboard** — `/family-dashboard`: 7-day mood trend, steps (Pedometer sync, iOS; Android needs Health Connect after native build), manual heart rate, anomaly flags (low steps/HR deviation/low mood), fall & inactivity alerts.
13. **Profile** — DID, language, Guardian Monitoring toggles (Fall Guard, Inactivity Guard + hours), emergency profile CRUD, About credit.
14. **Phase 2** — Solidarity Hub (mocked P2P), Respect Map (**enhanced: minority safety, real waiting weeks, financial transparency metrics**), Blackout snapshot, Physio-AI.
15. **Survival Medicine Cabinet** — `/medicine-cabinet`: med stock CRUD with expiry statuses (expired / <30 days / ok), qty +/-, P2P crisis exchange (offer/request, non-prescription only, respond → push to owner).
16. **Digital Healthcare Proxy** — `/healthcare-proxy`: legally formatted Power of Attorney / healthcare proxy document (SK/EN templates, § 576/2004 reference), SHA-256 hash + DID anchor, surfaced in public emergency QR payload. Optimized for partners.
17. **Direct Service Marketplace** — `/marketplace`: vetted experts list services (massage/consult/physio/care), cash/crypto direct payment (no middleman), booking flow + push to provider, bookings tab.
18. **AI Scam Shield** — `/scam-shield`: paste/clipboard SMS or link → Claude risk analysis (low/medium/high, verdict, reasons, advice), auto voice warning (TTS) on high risk + push alert, history. NOTE: auto-scanning incoming SMS is not technically possible on iOS/Android via Expo.
19. **Survival Auditor** — `/survival-auditor`: supplies inventory (water/food/power/meds/tools), family size setting, computed Survival Runway in days per category + overall (min of water/food).
20. **Skill Barter Engine** — `/barter`: trust-credit P2P skill exchange (start 10 credits), offers with credit value, accept → credits transfer + trade log + push.
21. **Emergency Beacon (Stealth)** — long-press GUARDIAN logo (standard or Angel header) 0.7s → silent signal with GPS location → `POST /api/beacon/trigger` + push. Discreet red dot confirmation only.
22. **Jarvis Advisor cross-link** — `POST /api/ai/advice` — reusable JarvisAdvice component on Cabinet, Survival, Marketplace, Barter, Healthcare Proxy screens for proactive module-aware advice.
23. **Home UI** — reorganized into 4 sections: Zdravie / Angel starostlivosť / Komunita / Prežitie (4 cards each) + Safety row.
24. **Global Legal Engine (2026)** — `/legal` + `GET /api/legal/region`: jurisdiction resolution (EU/UK/US/OTHER) with adaptive disclaimers (EU AI Act Art. 50 eff. 2 Aug 2026, GDPR, UK DPA 2018/DUAA 2025, US FDA general wellness/HIPAA), GPS country detect.
25. **TOS Liability Shield** — versioned TOS v2026-06.1 with total founder ("Guardian Angel") liability waiver; mandatory acceptance gate blocks home until accepted (`POST /api/legal/accept`, stored on user).
26. **Decentralized AML** — DID-anchored KYC attestation (`POST /api/aml/kyc`), tamper-evident hash-chain ledger (`aml_ledger`, smart-contract simulation), enforced in Solidarity Hub: €150/day unverified, €5000/day verified, max 10 tx/day, campaigns require KYC.
27. **International Testament Engine** — `POST /api/legal/testament`: civil_law_holograph (SK § 476 OZ, handwritten), common_law_uk (Wills Act 1837 s.9, 2 witnesses, holograph invalid in E&W), common_law (US, 2 witnesses); SHA-256 anchored.
28. **AI Compliance (2026)** — Art. 50 compliance note appended to all LLM system prompts (translator, physio, wellness, advice); AI disclosure footers in UI.

## Integrations
- **Auth**: Emergent Google Auth (`/api/auth/session`, `/api/auth/me`, `/api/auth/logout`)
- **Storage**: Emergent Managed Object Storage (via `/objstore/api/v1/storage`)
- **LLM**: Claude Sonnet 5 (translate/wellness/physio), gpt-5.4 vision (OCR) via `emergentintegrations` (Emergent LLM Key)
- **TTS**: Emergent OpenAI TTS (`/api/voice/tts`)
- **Push**: Emergent managed push (SuprSend relay) — `EMERGENT_PUSH_KEY=placeholder` until deploy; needs `google-services.json` from user before Android build; works only in native builds (not Expo Go/web).

## Backend Routes
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/session` | Exchange OAuth session_id → session_token |
| GET | `/api/auth/me` | Current user |
| POST | `/api/auth/logout` | Local + server session delete |
| PATCH | `/api/me/prefs` | Update language, angel_mode |
| GET/PUT | `/api/emergency-profile` | CRUD emergency profile |
| GET | `/api/emergency-qr/{did}` | Public emergency read-only |
| GET/POST/DELETE | `/api/vault/documents[...]` | Vault CRUD |
| GET | `/api/vault/documents/{id}/file` | Encrypted download |
| POST | `/api/ai/translate` | Free-text AI translation |
| POST | `/api/ai/translate-document` | Doc AI translation persisted |
| GET/POST/DELETE | `/api/waitlist[...]` | Waitlist CRUD |
| POST | `/api/waitlist/{id}/scan` | Simulated slot scan (+push on hit) |
| POST | `/api/fall-event` | Log fall verify/cancel |
| POST | `/api/register-push` | Register device push token (relay) |
| POST | `/api/vault/documents/{id}/ocr` | OCR image/PDF → extracted_text |
| POST | `/api/wellness/checkin` | Daily AI wellness check-in |
| GET | `/api/wellness/checkins` | Check-in history |
| POST | `/api/wellness/vitals` | Upsert daily steps/heart rate |
| POST | `/api/wellness/inactivity-alert` | Log inactivity + push |
| GET | `/api/wellness/dashboard` | Family dashboard aggregate |
| POST | `/api/ai/advice` | Jarvis cross-module advisor |
| GET/POST/PATCH/DELETE | `/api/cabinet/items[...]` | Medicine cabinet CRUD |
| GET/POST/DELETE | `/api/cabinet/exchange[...]` | P2P exchange, `/respond` to match |
| GET/PUT | `/api/proxy-directive` | Healthcare proxy document |
| GET/POST/DELETE | `/api/market/services[...]` | Marketplace, `/{id}/book`, `/api/market/bookings` |
| POST | `/api/scam/check` | AI scam analysis (+`/api/scam/history`) |
| GET/POST/DELETE | `/api/survival/items[...]` | Survival inventory, `/api/survival/runway` |
| GET/POST/DELETE | `/api/barter/offers[...]` | Barter, `/{id}/accept`, `/api/barter/me` |
| POST | `/api/beacon/trigger` | Stealth emergency beacon (+`/api/beacon/history`) |
| GET | `/api/legal/region`, `/api/legal/tos` | Jurisdiction disclaimers + versioned TOS |
| POST | `/api/legal/accept` | TOS acceptance (gate) |
| POST/GET | `/api/aml/kyc`, `/api/aml/status` | DID KYC attestation + AML status |
| POST/GET | `/api/legal/testament` | International will generator |

## Design
Brutalist Mobile Light — sharp corners (radius 0), 1.5–2 pt borders, monochrome + signal red (#D90429). Green brand (#1B4332). See `/app/design_guidelines.json`.

## Author
Guardian Angel — sole original Visionary and Author. AGPL-v3.
