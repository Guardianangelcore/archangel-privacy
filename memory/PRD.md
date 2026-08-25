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

## Phase 20: OMNIPOTENT ARCHANGEL FINAL SEAL — Complete Sovereign Legacy (June 2026) — DONE
User's absolute final requirement block, implemented in full:
1. VIDEO LEGACY VAULT (Family Peace Treaty) — routes/wealth.py: POST/GET /api/legacy/video (multipart upload → object storage, SHA-256 + AML ledger anchor + Mosaic block), unlock via life-status registry (dignity death_verified) or manual /release; owner streams own file; /app/frontend/app/video-legacy.tsx (ImagePicker video upload). Hub: legacy lw-video-legacy.
2. SOVEREIGN WEALTH VAULT — routes/wealth.py: /api/wealth/vault|assets (crypto seed/keys sealed zero-knowledge — DID-derived keystream, plaintext NEVER stored/returned, only masked + sha256; bank IBAN validated + masked), /api/wealth/anchor (manifest hash → Mosaic block, "Proof of Asset Stewardship"), /api/wealth/payout (Instant Card Payout — SIMULATED Visa Direct/Mastercard Send, status instant_sent). UI: wealth-vault.tsx. Hub: lw-wealth.
3. FOUNDATION IDENTITY + GHOST MODE — routes/seal.py: GET /api/foundation/identity (HARDCODED guardian.angel.core@proton.me, immutable), /api/ghost/toggle|status (24h anonymized GHOST-XXXX patient tokens). UI: ghost-mode.tsx (also hosts Power-Saver). Hub: hunter ht-ghost.
4. INNER CIRCLE — routes/seal.py: founder-only GET/POST/DELETE /api/inner-circle; grants PERMANENT archangel (subscription.current_tier returns archangel when user.inner_circle; whitelist applied at signup in auth.py). /api/subscription returns inner_circle flag. UI: inner-circle.tsx (founder mgmt, non-founder graceful lock). Hub: lw-inner-circle.
5. MEDICAL ARBITRAGE (PL/HU/TR) — routes/seal.py: GET /api/arbitrage/procedures (6 surgeries, SK vs PL/HU/TR prices+waits), POST /api/arbitrage/quote (billing prediction: travel+accommodation+S2 refund 85% for EU, TR=self-pay), GET /api/arbitrage/quotes. GENOMIC BIO-IDENTITY: PUT /api/bioidentity/genomic + GET /api/bioidentity (markers metadata, on-chain hash only). UI: arbitrage.tsx (quotes + genomic section). Hub: ht-arbitrage.
6. SURVIVAL LAYERS — routes/seal.py: DURESS PROTOCOL (PUT /api/duress/pin real+decoy hashed with DID salt; POST /api/duress/verify → vault_mode full|decoy|invalid, decoy fires silent alarm push + duress_events, response indistinguishable from normal unlock; GET /api/duress/status) UI duress.tsx, hub family fs-duress. MESH-MESSENGER (POST/GET /api/mesh/messages store-and-forward by DID, delivered/queued + push; GET /api/mesh/status; real BLE mesh needs native build — noted in UI) UI mesh.tsx, hub ht-mesh. POWER-SAVER (PUT/GET /api/power-saver → pure_black profile, essential-only) in ghost-mode.tsx.
7. Account deletion extended with new collections (legacy_videos, wealth_*, arbitrage_quotes, bio_identity, duress_*).
Tests: test_phase20_final_seal.py (30 tests). FULL suite 376/376 green. FIXED test infra: phase5 TestAmlLedger + phase7 TestAmlLedgerDignityChain/RecurringPlan made self-sufficient (xdist loadscope splits classes of one module across workers — cross-class shared state was flaky; adding any new test module reshuffles assignments).
Mocked (per user's approval): push-to-card rail, BLE mesh radio, DNA sequencing (metadata+hash only), S2 refund prediction (deterministic).

## Phase 21: ULTRA MODE — UI/UX Revolution 2026 (June 2026) — DONE
User directive: Apple-level quality + Wow factor. Implemented:
1. GLASS/LUXE THEME — src/theme.ts overhauled (bg #0A0A0F, glass surfaces, gold-alpha borders, radius 12-32, GOLD gradient + GLASS tokens). New UI kit: src/ui/glass.tsx (GlassCard w/ gradient edge+blur, GoldButton, Pulse breathing anim, tap() haptic helper), src/ui/sheets.tsx (Sheet base, OptionSheet, DateSheet Slovak calendar), src/ui/ContactSheet.tsx (expo-contacts native picker w/ full permission contract + web manual fallback).
2. GUARDIAN LENS (One-Lens System) — backend routes/lens.py: POST /api/lens/analyze (gpt-5.4 vision, strict JSON: kind/name/summary_sk/warnings/specialty/suggested_actions; photo stored; verified live with real pill photo), GET /api/lens/history, POST /api/lens/{id}/save-to-vault. Frontend /lens screen (camera+gallery w/ permission contract, glass result card, instant actions: add med reminder, interaction guard, book specialist, translator, save to vault). HUGE pulsing gold Lens FAB centered on Home (testID home-lens) + Angel Mode ŠOŠOVKA button + hh-lens hub tile.
3. ANGEL MODE 2.0 — fall-verify.tsx rewritten: 120s timer (was 30s), SVG progress ring, escalating haptics, VOICE-OFF: POST /api/voice/liveness (Whisper STT via emergentintegrations OpenAISpeechToText, diacritic-normalized OK_PATTERNS 'v poriadku/i am ok/...'; verified live via TTS→STT roundtrip); expo-audio 4s recording, hands-free alarm cancel. Meds slots: SLOTS upon_waking/breakfast/lunch/evening/night/as_needed w/ big Sun/Moon icons in meds.tsx modal; backend MedReminderIn.slots (as_needed allows empty times).
4. NATIVE INTEGRATION — ContactSheet wired into recovery-suite guardians (rs-guardian-contacts); waitlist dates → DateSheet calendar bottom sheets (wl-current/wl-target), specialty → OptionSheet (wl-spec-open). Tab bar: Slovak labels (ZDRAVIE/RODINA/ODKAZ/LOVEC), filled icons on focus, haptics on tabPress, gold-tinted glass bar.
5. CLINIC SYNC — backend routes/clinic_sync.py: POST/GET /api/clinic-sync/session (one-time 6-char QR code, 10min TTL), PUBLIC POST /api/clinic-sync/beam/{code} (doctor beams report → vault document + push), GET /api/clinic-sync/radar (SIMULATED BLE/NFC nearby clinics), POST /api/clinic-sync/simulate-beam (demo). Frontend /clinic-sync: reanimated radar rings, Radar/QR toggle, QR + code display, received docs → vault. hh-clinic-sync hub tile.
Tests: test_phase21_ultra.py (14) — FULL suite 390/390 green. Mocked: BLE/NFC radar (native build needed for real radio).

## Phase 22: SUPREME FINALE + JARVIS 2.0 SOUL ENGINE (June 2026) — DONE
A) SMART-PICKERS (Zero-Typing policy — NO manual typing for numbers/dates/times):
- New src/ui/fields.tsx: WheelField / DateField / TimeField (pressable fields opening bottom-sheet pickers).
- sheets.tsx += TimeSheet (two HH:MM snap wheels) + DateSheet year-nav (« » buttons).
- Rolled out to 16 screens: longevity (rok/výška/váha), family-dashboard (tep), my-recovery (dátumy PN, mzda, vychádzky HH:MM, dni PN), insurance (poistné, zaplatené do), health-timeline (dátum, booster), respect-map (čakanie), digital-legacy (€/mes), solidarity (goal, dar), survival-auditor (qty, need), gigs (GA-T, €), marketplace (cena), legal (rok narodenia), medicine-cabinet (qty, expirácia DateField), wealth-vault (hodnota, payout suma), dignity (sumy), bioscan.
- bioscan.tsx += MANUÁLNA KALIBRÁCIA section (bs-sys/bs-dia/bs-glu/bs-hr WheelFields + bs-calibrate → POST /api/bioscan/calibrate, history shows 📏 MANUÁL rows). PIN inputs (duress) and card-last-4 intentionally remain keyboard (secrets/identifiers).
B) NATIVE SHARING: emergency-qr.tsx += qr-share button (Share.share native sheet, web navigator.share fallback). Wallpaper + IPS already use expo-sharing native sheet (verified).
C) PHYSIO VIDEOS: all 7 Mixkit HD URLs verified 200 OK; expo-video renders in guides (VIDEO-NÁVOD · HD badge).
D) JARVIS 2.0 — SOUL ENGINE (backend routes/agent.py, registered in server.py):
- Levels 1→10 (ISKRA…ARCHANJEL), XP thresholds [0,100,250,450,700,1000,1400,1900,2500,3200], abilities unlock per level, streak days. award_xp() hooks: chat +5, briefing +10/day, deep analysis +15/day, med intake +10, bioscan +15, calibration +10, physio +10. Level-up push notification.
- Self-teaching memory: agent_memories (LLM extraction gpt-5.4 after each chat, dedup, topics health/family/habit/preference/event, importance 1-5). GET/DELETE /api/agent/memories.
- POST /api/agent/chat (gpt-5.4, persona tone grows with level, strict JSON {reply,mood}, context = neural._gather_context + memories + last 6 turns + anomalies). Moods: calm|thinking|alert|energetic|concerned.
- GET /api/agent/briefing (cached per day, force=true to regen): weather (open-meteo keyless, Bratislava, graceful fallback), meds today, upcoming exams, memory follow-ups ("Včera si spomínal, že Tomáša boleli žily — ako mu je dnes?" — VERIFIED live), anomaly warnings.
- GET /api/agent/anomalies: BP >=160 critical / >=140 elevated / 3-rising trend, glucose >=13 / >=11 / <=3.5, high stress; HIGH severity → immediate push (12h dedup in agent_alarms).
- POST /api/agent/analyze: visual-thinking steps (real data counts) + gpt-5.4 insight.
- POST /api/agent/transcribe: generic Whisper STT (sk).
- /api/voice/tts += speed param (0.7-1.3) for emotional pacing; frontend maps mood→voice/speed (calm coral 0.95, concerned sage 0.9, energetic nova 1.08, alert onyx).
E) JARVIS 2.0 UI (jarvis.tsx REWRITTEN): breathing Orb (reanimated, mood colors gold/violet/blue/red, speed by mood) + SVG XP ring + LVL badge; tap Orb = full voice conversation (record → Whisper → chat → emotional TTS auto-reply); morning briefing card w/ weather + play; chat bubbles + text input; HĹBKOVÁ ANALÝZA visual thinking (animated steps + rays + insight); abilities list; memories list w/ delete; level-up gold burst modal; XP toast; mic permission contract w/ openSettings. Autopilot + chains + weekly PDF preserved.
Tests: test_phase22_soul.py (14) — suite 404 tests green (phase13 stress passes solo; xdist contention noise only). Live-verified: chat (concerned mood + BP alert), memory extraction, briefing follow-up question, weather, analyze insight, wheel-picker e2e, TTS speed.
Collections added: agent_state, agent_xp_events, agent_xp_days, agent_memories, agent_conversations, agent_briefings, agent_alarms.

## Phase 23: EFFICIENCY & QUALITY CONSOLIDATION (June 2026) — DONE
1) PERFORMANCE: physio videos now hardware-accelerated + double-cached — expo-video native `useCaching:true` + FS prefetch (media.ts: prefetchVideo/cachedVideo warm all guide videos on load; local file:// playback when cached). bufferOptions 10s + waitsToMinimizeStalling.
2) CONTENT: EmptyState component (src/ui/EmptyState.tsx) + professional 14-language empty-state copy in i18n.ts (T + all 10 EXT blocks): meds (md-empty + CTA opens add modal), my-recovery PN intro (mr-empty), gigs (gg-empty per tab). No blank screens remain.
3) FLUIDITY: 60FPS native transitions in _layout.tsx (slide_from_right, 240ms, freezeOnBlur, gestures; web=none). ContactSheet wired into healthcare-proxy (hp-pick-contact), profile ICE (prof-ec-pick), dignity beneficiary (dg-ben-pick) — key `pick_from_contacts` in 14 langs. Date-format error texts updated (no RRRR-MM-DD wording).
Fixed during pass: gigs.tsx missing `t` import (crash caught by smoke test). Smoke-verified: meds/PN empty states, proxy pick button, gigs list. Backend untouched.

## Phase 24-25: ARCHANGEL MONOLITH + ASCENSION PROTOCOL (June 2026) — DONE, 432/432 + 20 monolith + 3 LLM-live tests green
BACKEND (new modules, registered in server.py):
- routes/uhp.py — UNIVERSAL HEALTH PROTOCOL (UHP/1.0): POST /api/uhp/partners/register (api_key+hmac_secret), POST /api/uhp/ingest (HMAC-SHA256 '{ts}.{body}', ±300s replay window, idempotency_key dedup, 240/min rate-limit, kind routing: vitals→bioscan_results + push, sensor/threat_mesh→sentinel_streams), GET /uhp/standard (machine-readable spec), GET /uhp/capacity (topology 12×4096×32×650 = 1.02B streams), GET /uhp/feed (subject audit), GET /uhp/partners/{id}/stats.
- routes/arbitrage.py — GLOBAL ARBITRAGE BRAIN: deterministic seed=2026 index of 10,500 clinics / 32 countries / 14 procedures (arb_clinics, lazy ensure_arb_seed). POST /api/arbitrage/analyze → net_benefit = (local_price + time_saved_weeks×week_value[urgency 40/120/400€]) − (price+travel+lodging); picks best_value/cheapest/fastest/best_quality. GET /arbitrage/stats.
- routes/liquidity.py — SETTLEMENT ENGINE (bank-grade shape, user-approved SimulatedRails adapter, RAILS_MODE env swap for Visa Direct/MC Send): double-entry ledger_entries (balance enforced), POST /api/liquidity/payout state machine initiated→authorized→settled with timeline+trace, Idempotency-Key dedup, fees 1.2%+0.25 min 0.50, FX table + 0.6% margin, insufficient_funds guard, PAYOUT_LIMIT 10k. /liquidity/balance|payouts|ledger. Data-Backed Credit: /credit/score (limit from data wealth, cap 5000€, 9.9% APR) + /credit/draw (credit_lines + ledger).
- routes/ascension.py — 22nd-century layer: (1) BIO-DIGITAL TWIN: GET /twin/profile, POST /twin/simulate (gpt-5.4 strict JSON: compatibility_pct/risks/interactions/verdict), GET /twin/trajectory (least-squares projection m6/12/24, slope damped n/10, physiological clamps 70-260 / 2-35, composite_risk_12m). (2) PREDICTIVE SENTINEL: POST /sentinel/gait (tremor_index/gait_regularity), GET /sentinel/predict → risk 0-100, level high → push Inner Circle (family_links) PRE-event, 6h dedup sentinel_alerts. (3) LIVING CURRENCY: POST /edge/contribute (fraud guards: ≤5M tasks, ≤5000 tasks/ms; 0.8 GA-T/1M via award_tokens), GET /edge/status, gbi_distribute() 0.5 GA-T/day to 72h-active users. (4) COLLECTIVE TRUTH: POST /mesh/truth + GET /mesh/truth/verify — SHA3-512 hash-chain, full re-verification. (5) COGNITIVE HANDOVER: POST /legacy/blueprint/train (personality_blueprints from memories+own words, versioned), GET /legacy/blueprint, POST /legacy/blueprint/ask (digital-echo answers in founder's tone for Tomáš; voice clone needs ElevenLabs key — noted to user).
- swarm.py extended: data_broker agent (autonomous data-sale negotiation +15-40% uplift, 1 deal/user/day, GA-T award + push), gbi_distributor agent, news_sentinel→hunter autopilot bridge (auto-creates waitlist hunt when users.jarvis_autopilot != false), safety agent += QR-Talisman integrity daily push + critical-vitals satellite_queue Nano-Packets.
- Robust LLM JSON parsing (_parse_json raw_decode) in ascension.py + agent.py chat (fixes intermittent 502 when gpt-5.4 appends prose after JSON — found by testing agent).
FRONTEND:
- app/monolith.tsx — SOVEREIGN OS COMMAND DECK: 8 collapsible sections (UHP capacity 1.02B, Arbitrage with procedure/urgency chips + WheelFields, Liquidity payout timeline animation + credit, Twin trajectories + simulate, Sentinel risk gauge, Edge compute button doing REAL ~3s JS work → GA-T, Truth chain append/verify, Blueprint train/ask). Tile fs-monolith in family tab.
- src/guardian.tsx — KERNEL: grid watchdog (2 failed pings → auto-navigate /blackout PRIMARY NODE, 15min cooldown) + tremor sampling (accel variance → POST /sentinel/gait every 10 min).
- marketplace.tsx empty-states (mk-empty, bk-empty) + i18n keys empty_market_*/empty_bookings_* (sk/cs/en/de + en-fallback for EXT).
Tests: test_phase24_monolith.py (20: HMAC/replay/idempotency, arbitrage math exact, ledger states, FX, credit, trajectory clamp, sentinel, edge fraud, truth verify, 60-concurrent ingest p95<4s, swarm agents), test_phase24_llm_live.py (3, by testing agent). FULL SUITE 432/432.
New collections: uhp_partners, uhp_events, sentinel_streams, arb_clinics, arb_analyses, payouts, ledger_entries, liq_balances, credit_scores, credit_lines, gait_samples, sentinel_alerts, edge_nodes, gbi_payments, collective_truth, personality_blueprints, blueprint_dialogues, twin_simulations, data_deals, talisman_checks, satellite_queue.
Simulated (user-approved): card rails adapter, satellite radio, BLE mesh radio, rPPG.
