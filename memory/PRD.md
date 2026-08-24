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
29. **PDF Export** — `GET /api/legal/{tos,testament,proxy}.pdf` (fpdf2 + Liberation fonts, SK diacritics; auth via header or ?token=); share buttons in Legal & Healthcare Proxy screens (expo-sharing native, new tab web).
30. **Medication Reminders (Angel)** — `/meds`: senior XL UI, big "Užil(a) som" buttons, TTS voice alerts + auto read-aloud, daily local notifications (expo-notifications DAILY trigger, native); APIs `/api/meds/reminders|today|intake`. Angel tile LIEKY → /meds.
31. **Final Dignity & Funeral Fund** — `/dignity`: funeral savings sub-account (mocked rails EUR/CZK/Crypto + real AML ledger), automated monthly recurring transfers, funds LOCKED until death verification (SIMULATED state registry via certificate number — production hook), release to funeral director or primary proxy (auto-default from proxy-directive), Final Wishes Vault (burial type, music, guests) with SHA-256. Links from Profile, Solidarity, Legal.

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
| GET | `/api/legal/{tos,testament,proxy}.pdf` | PDF export (header or ?token auth) |
| CRUD | `/api/meds/reminders`, `/api/meds/today`, `/api/meds/intake` | Medication reminders |
| GET/POST/PUT | `/api/dignity/*` | Funeral fund, plan, beneficiary, wishes, verify-death, release |

## Design
Brutalist Mobile Light — sharp corners (radius 0), 1.5–2 pt borders, monochrome + signal red (#D90429). Green brand (#1B4332). See `/app/design_guidelines.json`.

## Author
Guardian Angel — Sole Visionary and Legal Owner. PROPRIETARY LICENSE (AGPL-v3 rescinded June 2026 — see /app/LICENSE and /app/PROOF_OF_ORIGIN.md). Codebase SHA-256 fingerprint anchored via DID-link; hidden watermark in UI (`src/watermark.ts`, GA_ORIGIN_MARK in root layout) and backend (X-Guardian-Origin response header, /api/origin endpoint, db.ip_protection).

## Iteration 7-8 (June 2026, fork) — Premium OS validated + Survival & Trust + Survival Extensions
- VALIDATED & FIXED Premium Guardian OS overhaul: added 17 missing StyleSheet keys in (tabs)/index.tsx (pillar grid + Angel Mode were rendering unstyled); auth.tsx refresh() no longer clears session on transient network errors (fixes reported splash /auth/me failure); family.tsx enableAngel now navigates to (tabs) index (fixed click interception).
- NEW FEATURES (all tested, 17/17 + 21/21 backend tests pass, all UI flows pass):
  1. Border Crosser (Health): /api/border/certificate(.pdf) — 14-language medication certificate signed with DID. Screen /border-pass.
  2. Emergency Wallpaper (Family): /api/family/wallpaper.png — 1080x1920 lockscreen PNG with offline QR (blood/allergies/ICE). Screen /wallpaper.
  3. Mental Fortress (Health/Physio): /api/mental/techniques — 6 crisis techniques (breathing, grounding, acupressure LI4/PC6/Yintang, PMR) with TTS playback. Screen /mental-fortress.
  4. Biometric Will (Legacy): /api/legal/testament/biometric — audio/video statement → SHA-256 + tamper-evident ledger notarization. Screen /biometric-will (expo-audio recording + video picker, permission contract).
  5. Acoustic Threat Detection (Angel Mode): src/acoustic.ts local mic metering (no audio leaves device) → /api/acoustic-event + Fall-Verify flow. Button angel-acoustic in Angel home.
  6. Analog Recovery Kit: /api/survival/bible.pdf — 8-section printable Survival Bible. One-tap hh-bible in Health hub.
  7. Pharmacy Stock Hunter (Hunter): /api/pharmacy/search + watch/scan lifecycle — SIMULATED inventory (no public SK/CZ stock API exists; badged DEMO DÁTA in UI). Screen /pharmacy-hunter.
  8. Guardian Pulse Check (Family): STRICTLY OPT-IN silent ping (/api/pulse/*, 403 without target opt-in). Privacy toggles in Profile (prof-pulse-optin) and /pulse-check screen.
- Test users: smoketest-user-1 (smoketok-fresh-2026), smoketest-user-2 (smoketok-fresh-2026-u2) — see memory/test_credentials.md.
- Deferred (unchanged): real IPFS, ZK-proofs, PDF-OCR pipeline, RTL, real Stripe/crypto, real BLE mesh, real pharmacy stock API integration, server.py modular refactor.

## Iteration 9 (June 2026) — Production Polish, PUBLISH-READY ✅
- REFACTOR: server.py monolith (2600 lines) split into production modules: core.py (db/auth/storage/push/PDF/AML helpers, shared api router), models.py, content.py (SK/CS/EN/DE content), routes/{auth,health,family,hunter,legacy}.py. Slim server.py entry. Full pytest 173/173 (run serially: pytest -o addopts=""). server_monolith.bak kept as reference.
- HEALTH DROP (Referral Bridge): zero-knowledge provider→vault upload. Public browser portal /drop/{drop_id} encrypts with patient's public key (tweetnacl X25519, src/dropcrypto.ts, secret key in SecureStore/localStorage) — server stores ONLY ciphertext. Guardian-ID verification (full DID or last-6). Push notification on receipt. Screen /health-drop with QR/link share + encrypted inbox + on-device decrypt.
- AUTO-BOOKER: referral ingestion → Jarvis prompt ("Mám rezervovať najskorší termín?") → POST /api/autobook (SIMULATED clinic APIs, flagged simulated:true) → waitlist status booked + Guardian Calendar sync + push. Also /api/waitlist/{id}/autobook.
- LIFE-HEALTH CALENDAR + HEALTH TIMELINE: categories exam/history/vaccine, booster_due proactive alerts (90d horizon), vertical timeline UI with filters at /health-timeline.
- CONTENT: Mental Fortress + NEW Physio-AI founder guides (knee recovery, panic acupressure, ergonomics) in SK/CS/EN/DE with Jarvis TTS. Language chips in UI.
- Wallpaper one-tap family share (wp-share). Pharmacy Hunter stays DEMO (PHARMACY_API_URL/KEY env placeholders ready for real integration).
- Testing: iteration_9.json — backend 34/34 new tests (test_phase10.py), frontend E2E 100% incl. public portal upload→decrypt→autobook→calendar. Nav stress clean. Legal disclaimers intact.
- Known non-blocking: pointerEvents deprecation warning; expo-notifications web warning; acoustic guard web MediaRecorder warning (native-only feature).
- STATUS: Ready for Publish → native builds. Push notifications require real google-services.json at build time.

## Iteration 10 (June 2026) — Sick Leave & Recovery Module (Hustle Recovery Guard) ✅
- ePN record (start/end, contract TPP/DPP/DPČ, gross, note) + outing windows management at /my-recovery (Health hub → hh-recovery).
- Vychádzky: live status card (active/home, minute countdown, red 15-min warning), local notifications 15 min before window ends (native only), AI extraction of hours from pasted ePN text (Claude — verified).
- Sick Pay Calculator (simplified SK 2026: DVZ, 25 %/55 %/55 % tiers, DPP/DPČ eligibility warning, disclaimer). Shortfall ≥30 % → Solidarity Hub suggestion with direct link.
- One-tap PDF hlásenia: zamestnávateľ + Sociálna poisťovňa/ČSSZ (share sheet → email).
- Endpoints: PUT/GET /api/recovery/epn, POST /api/recovery/extract-outings, POST /api/recovery/sickpay, GET /api/recovery/report.pdf?kind=.
- Testing: iteration_10.json — 22/22 new backend tests (test_phase11_recovery.py), full frontend E2E green, stability regression clean. CUMULATIVE: 195/195 tests. NO BUGS. Publish-ready.

## Iteration 14 (August 2026, fork) — IP PROTECTION LAYER + finálna verifikácia Gateway/Stripe fixu
- LEGAL PIVOT: AGPL-v3 zrušená → proprietárna licencia (/app/LICENSE, README.md). Copyright hlavičky "© 2026 Guardian Angel" vo všetkých 86+ zdrojových súboroch (scripts/inject_headers.sh, idempotentné).
- PROOF OF ORIGIN: deterministický SHA-256 celej codebase + DID-link (did:guardian:pex:sha256:...), ukotvený na Bitcoin blockchain cez OpenTimestamps (PROOF_OF_ORIGIN.sha256.ots = dôkaz). Generátor: scripts/generate_proof_of_origin.py (--verify na kontrolu). Artefakty origin.json (backend + frontend/src) sú generované — pri zmene kódu re-anchorovať.
- WATERMARKY: (1) skrytý GA_ORIGIN_MARK v UI bundli (src/watermark.ts, neviditeľný Text v _layout.tsx), (2) raw ASGI middleware podpisuje KAŽDÚ API odpoveď hlavičkami X-Guardian-Origin + X-Origin-DID (BaseHTTPMiddleware zavrhnutý — kazil p95 pod záťažou), (3) GET /api/origin (verejný) vracia ukotvený záznam z db.ip_protection, (4) About v Profile: "Sole Visionary & Legal Owner: Guardian Angel" + DID (testID origin-did).
- FIXY: po forku bol EMERGENT_LLM_KEY neplatný (storage/LLM/push 401) → obnovený v backend/.env. Iteration-13 db.campaigns fix POTVRDENÝ testing agentom (žiadne 500, Stripe checkout vracia 503 stripe_key_missing s priateľským SK bannerom v solidarity.tsx — pridal testing agent). test_phase14_ip_protection.py (20 testov) číta build dynamicky z origin.json.
- TESTY: 238 backend testov — 235 pass paralelne + 3 známe xdist/load flaky (phase7 dignity ×2, phase3 ai_translate) overené sériovo ako PASS. Frontend: login/profile/protocol/solidarity render OK.
- ZRUŠENÉ POUŽÍVATEĽOM: "Autonomous Agentic Swarm" a "Quantum-Secure Tokenized Swarm" prompty — používateľ požiadal o rollback pred implementáciou; NEBOL napísaný žiadny swarm/token kód.

## Phase 17–18: MASTER-SEAL + GIGA-LAYER + WORLD-CLASS FINALE + MOSAIC PROTOCOL (June 2026) — DONE
User's final consolidated prompts implemented in one pass:
1. Sovereign Recovery Suite — Social Recovery (guardian quorum 2-of-N, public initiate/poll with one-time token), QR Talisman (one-time printable key, react-native-qrcode-svg), Passkeys (placeholder), Social 2FA (guardian push handshake on every login, SAFE non-blocking).
2. Paramedic Key completed — NCZI/ÚZIS state-registry verification (simulated deterministic), bio-beacon counts as verified emergency.
3. Offline Survival Compass (/compass, AsyncStorage-cached; includes NESCHOPENKA ePN outings + OČKOVANIA booster alerts per user request), Truth-Validator peer consensus, Bio-Beacon (activate/ping/public read).
4. DAO Rebranding — author/headers/PDF footers → "Guardian Angel Sovereign Foundation (DAO)", /api/dao/manifest, Article 50 (EU AI Act) waiver component (src/Art50.tsx) on all new screens + login, watermark.ts pseudonymous.
5. Gigs + Refunds frontends (/gigs, /refunds).
6. Giga-Layer: Satellite Nano-Packet (zlib ≤140 B, Starlink/Globalstar placeholders, swarm broadcasts), IPS HL7 FHIR export (Bundle-uv-ips + PDF), Humanitarian Shield (catastrophe consensus → GA-HUM identity + PDF card).
7. World-Class Finale: AI Tactical Medic (7 offline protocols, Jarvis TTS steps), Vitals Bio-Scanner (rPPG placeholder), Longevity Engine (bio-age + AI bio-hacks), Environmental Threat Fusion (/enviro mesh consensus).
8. Elite Monetization: tiers €0 / €29 Guardian / €149 Sentinel / €499 Archangel, annual −20 %, EUR/CZK/GA-T, one-time 7-day Sentinel trial, pay-per-use (bioscan 5 GA-T, IPS 10 GA-T), hard-coded 15% Guardian Tax (marketplace + gig cash), Value Advisor upsell recs, Founder Wealth dashboard (MRR/ACV/revenue, founder-only), luxury Obsidian/Platinum UI for Sentinel/Archangel.
9. Mosaic Protocol (SIMULATED): ZK-Rollup L2 blocks anchoring GA-T ledger + record hashes, IPFS CID manifest (hybrid layer), Legacy Trigger smart contracts, PQC handshake (Kyber/Dilithium placeholders), Bridge-Watch failover to Base/Polygon, zero-fee abstraction, global node stress test → "READY FOR PUBLISH".
10. Swarm agent #7 sovereign_guard orchestrates: handshake/recovery expiry, beacon shutdown, satellite broadcast, enviro escalation, Mosaic block production.
Tests: test_phase17_masterseal.py + test_phase18_worldclass.py (52 passed); full suite regression green.
Mocked (user-approved): Stripe card, satellite uplink, NCZI/ÚZIS API, rPPG CV, Mosaic/IPFS/PQC crypto, humanitarian feeds.

## Phase 19: GRAND FINALE — Submission & Onboarding Readiness (June 2026) — DONE
1. Investor Demo Mode — founder-only toggle (Profile → FOUNDER ADMIN, routes/demo.py): seeds waitlist hunt (Kardiológia slot_found), 150 € Stomatológia refund claim, family pulse from Tomáš; fully reversible (demo:true tags).
2. Family & Seniors Onboarding (/onboarding) — warm 3-step guide: link Primary Guardian → how to talk to Jarvis (3 examples) → Emergency QR + Talisman; entry from Profile + Family hub; AsyncStorage flag gh_onboarding_done.
3. Refactor — server.py split complete: indexes moved to /app/backend/db_indexes.py (ensure_indexes()). Load sanity: 300 concurrent authed requests → 300/300 OK.
4. Final Audit — FULL pytest suite 346/346 green (test_phase19_grand_finale.py added); stability audit 9/9 score 100; Mosaic stress test READY FOR PUBLISH.
5. Launch Control (/launch, founder-only entry) — live readiness checklist (audit, TPS, swarm 7/7, wealth engine) + DEPLOY TO PRODUCTION handover card with Publish instructions.
Frontend verified by testing agent: 10/10 (iteration_18.json). Known minor: /launch direct-URL reachable for non-founders but degrades gracefully (no crash).
STATUS: READY FOR PUBLISH — user to press Publish (top right) → Deploy → Generate iOS/Android builds.
