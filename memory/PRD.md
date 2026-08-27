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

## Phase 26: FINAL PRODUCTION HANDOVER — SEAL & DEPLOY (June 2026) — DONE ✅
1. JARVIS PRESENCE — pulsing AI Orb moved to home screen as the primary welcome interface: (tabs)/index.tsx HomeOrb component (breathing reanimated glow, mood colors from GET /api/agent/state, LVL badge, testID home-orb, tap → /jarvis). Guardian Lens FAB demoted to compact GlassCard row (testID home-lens preserved).
2. UHP PARTNERS landing (/partners) — high-end portal for clinics/insurers: live capacity stats, 3 value-prop cards, 4-step onboarding (register → HMAC sign → ingest → stats), security pills, SANDBOX button issuing real credentials via POST /api/uhp/partners/register (pt-sandbox → pt-creds), contact mailto guardian.angel.core@proton.me.
3. FOUNDER'S TOOLKIT (/founder-toolkit) — investor demo: financial forecast 2026–2030 (deterministic tier-mix model: ARPU 63.5 €, 15% Guardian Tax, 2030 ARR 392.4 M €), 22nd-century roadmap (8 milestones LAUNCH→ARCHANGEL), GitHub Release Package viewer with sha256 integrity + native Share.
4. GITHUB RELEASE PACKAGE — /app/release_package/{README.md, ARCHITECTURE.md, API_SPEC.md, LICENSE (private + evaluation grant)} for the competition submission; served by routes/founder.py: GET /api/founder/toolkit + GET /api/founder/release/{doc} (auth, 404 unknown).
5. COMMAND DECK — monolith.tsx gateway row: mono-partners + mono-founder tiles at top.
Tests: test_phase25_founder_handover.py (7) + phase24 regression (20) + full frontend E2E 14/14 — iteration_23.json ALL GREEN. STATUS: SEALED — user to press PUBLISH → Deploy → Generate iOS/Android builds.

## Phase 27: HUMAN-FIRST REPAIR + SELF-HEALING SWARM (June 2026) — DONE ✅
User halted infra work to fix core UX; all delivered and verified (iteration_24.json ALL GREEN, 12/12 backend + 39/39 frontend E2E):
1. SLOVAK SATURATION — home dashboard + all 4 pillar hubs fully Slovak (Zdravie / Rodina a ochrana / Odkaz a majetok / Lovec termínov); brand sub 'SUVERÉNNY OCHRANNÝ SYSTÉM'.
2. VAULT TRANSPARENCY — file-manager view: per-doc 'ZOBRAZIŤ / OTVORIŤ' (doc-view-*, image preview modal or native share via ?token=), '🤖 JARVIS ZHRNUTIE' (doc-jarvis-*, replaces old doc-ocr/doc-translate), delete; every upload immediately indexed into Health Timeline (calendar_events category=history, 📄 title, doc_id link).
3. AI TRANSLATOR REBUILT (/translate) — prominent ODFOTIŤ DOKUMENT (tr-camera, permission contract) + NAHRAŤ SÚBOR/FOTKU (tr-upload); flow upload→vault→OCR→plain Slovak; NEXT APPOINTMENT extraction (health.py extract_next_appointment, gpt-5.4 strict JSON) returned by /ai/translate + /ai/translate-document → big 'PRIDAŤ DO KALENDÁRA' (tr-add-calendar) → POST /calendar/events + tr-open-timeline link.
4. PRAGUE GEO CONTEXT + GEOGRAPHIC FLUIDITY — routes/geo.py: 16-city index, DEFAULT_GEO Praha/CZ; GET /geo/context, PUT /geo/travel-mode, POST /geo/locate (haversine nearest city; with travel mode ON auto-switches user language to local tongue). Weather briefing geo-aware; pharmacy search defaults region from geo (CZ, Praha first); waitlist clinics city-indexed (_CLINICS_BY_CITY, Praha default: FN Motol, VFN, Na Homolce, IKEM). Frontend: Travel Mode toggle in Profile (prof-travel-mode, contextual location permission), kernel GPS sampling in guardian.tsx every 15 min (never prompts), 📍 geo chip under home Orb.
5. SYSTEM JANITOR (self-repair swarm agent, interval 120s) — backfills missing timeline entries for legacy vault docs (healed 15 on first run), sets geo defaults; logs db.janitor_runs; GET /api/janitor/status; swarm now 10 agents.
6. SMART CHOICE MODALS — PillarHub supports choices[] (bottom-sheet modal, testID {tile}-choice-{i}); applied to hh-meds (Skenovať obal / Manuálne / Interakcie / Lekárne) and hh-vault (Trezor / Nahrať+AI / Časová os). Native date/time pickers already global (Phase 22).
7. DEAD BUTTON AUDIT — all 53 hub tiles clicked and verified working (no blanks/errors).
Known non-blocking: RN Web shadow*/pointerEvents deprecation warnings.

## Phase 28: PREMIUM UNLOCK — STRIPE PAYMENTS + GA-T REPRICING + FOUNDER ENTITLEMENT (June 2026) — DONE ✅
User reported "premium features don't work" — root cause: no working payment path (card placeholder 503, GA-T prices unreachable). Fixes (iteration_25.json ALL GREEN, 15/15 backend + full E2E payment loop):
1. STRIPE CHECKOUT LIVE (TEST mode) — routes/billing.py via emergentintegrations StripeCheckout (STRIPE_API_KEY=sk_test_emergent in backend/.env, emergent proxy): POST /billing/checkout (server-fixed EUR prices from TIERS, metadata user/tier/billing, payment_transactions collection), GET /billing/status/{sid} (poll → idempotent _activate_tier: sets tier+tier_until 30/365d, tier_paid_with=card, record_revenue), POST /webhook/stripe, GET /billing/transactions. E2E verified with test card 4242…: pay → redirect /subscription?session_id= → auto-poll → 'GUARDIAN aktívny' + no double activation.
2. GA-T REPRICING — Guardian 50 / Sentinel 250 / Archangel 800 mesačne (ročne −20 %: 480/2400/7680) in subscription._prices + token.SPEND_ITEMS. 402 messages now cite new prices.
3. FOUNDER ENTITLEMENT — System Janitor repair #3: first-created user auto-gets inner_circle:true + is_founder + lifetime archangel (in prod DB = the real founder after deploy).
4. FRONTEND subscription.tsx — 'KARTOU {€}' buttons (web same-tab Stripe redirect + return polling via useLocalSearchParams; native openAuthSessionAsync + poll), cancelled banner, updated copy (Stripe TEST 4242 note).
subscription/upgrade card branch now 400 use_billing_checkout (GA-T path unchanged). Trial regression OK (one-time 409).

## Phase 29: SUBSCRIPTION SUITE — MANAGEMENT, RECEIPTS, FAMILY PACK, FOUNDER GIFTING (June 2026) — DONE ✅
(iteration_26 tests ALL GREEN: 12/12 backend + frontend E2E)
1. SPRÁVA PREDPLATNÉHO — POST /subscription/cancel (immediate downgrade→sovereign; inner_circle 400; repeat 409); subscription.tsx: transactions list (sb-tx-*, GET /billing/transactions) + two-step cancel (sb-cancel → sb-cancel-yes/no).
2. POTVRDENIE O PLATBE — billing._issue_receipt after every card activation: PDF (core._make_pdf) → object storage → db.documents (source billing_receipt, 'Doklad o platbe — …') + 🧾 calendar_events timeline entry; failure never breaks payment; visible in Vault with ZOBRAZIŤ/JARVIS buttons.
3. RODINNÝ BALÍK — tier 'family_sentinel' (249 €/mes, 2390 €/rok, FAMILY_PACK max 4 members): activation gives payer Sentinel (non-destructive: never downgrades archangel/inner_circle) + up to 4 db.guardians members (tier_paid_with family_pack, family_members_activated on tx); sb-family-pack card in UI.
4. FOUNDER GIFTING (user request 'daj zakladateľovi prístup na darovanie') — POST /billing/gift {email,tier,days≤3650} founder-only (403 otherwise, 404 unknown email, 409 inner_circle recipient) → grants tier + db.gifts + push; GET /billing/gifts history; UI: sb-gift box (email input, tier/days chips, history) visible only to founder.

## Phase 30: LANGUAGE-AWARE OS — "the app speaks whatever language you set" (June 2026) — DONE ✅
User demand: UI + Jarvis must follow the user's language setting (incl. German). Verified with language=de (screenshot + live LLM calls):
1. JARVIS SPEAKS YOUR LANGUAGE — agent.py: LANG_FULL map + _lang_name(user); chat system prompt 'Answer STRICTLY in {lang}' + CRITICAL LANGUAGE RULE appended at the end (overrides conversation-language bias — required, model ignored the earlier instruction alone); briefing + insight prompts language-aware; Whisper STT language = user.language (was hardcoded sk); memory extraction language-neutral. Verified: chat reply + morning briefing in German ('Guten Morgen… In Prag ist es gerade…').
2. UI LANGUAGE-AWARE — new i18n keys (sk/cs/en/de, others fall back to en): greeting_hello, brand_sub, orb_sub, daily_brief(_sub), lens_sub, pillar_*(_sub), gat_wallet, cyber_fortress, beacon_hint, tab_legacy, tab_hunter; wired in (tabs)/index.tsx (greeting, Orb, brief, lens, pillars, eco row, beacon hint) and (tabs)/_layout.tsx tab titles. Language switch in Profile (existing picker) or automatic via Travel Mode.
Note: deep screens (hub item lists, monolith, partners) remain Slovak-first — translate on demand.

## Phase 31: LIFE-FIRST REORGANIZATION — Sovereign Healing Loop + Angel Shield 2.0 + Eternal Vault (June 2026) — DONE ✅
Founder directive: separate 'Life' from 'Legacy'; insurance = money NOW at injury (belongs in the loop, not the grave).
1. KOLOTOČ UZDRAVENIA (backend routes/healing.py + frontend /healing):
   - POST /api/healing/injury-event — NEURAL BUS: asyncio.gather fires Insurance Claim prefill (insurance_claims, daily benefit + 21d estimate from user's policies) AND Waitlist Hunter booking (Prague) SIMULTANEOUSLY; neural_bus event logged.
   - GET /api/healing/state (5 steps: intake→financial_shield→access→bureaucracy→recovery; auto-completes bureaucracy when PN active; progress_pct), POST /healing/step/{k}/complete, POST /healing/claim/{id}/submit, POST /healing/close (100% fit).
   - /healing screen: zero-typing smart wizard (kind/body-part/specialty chips), step timeline with claim card (ODOSLAŤ ŽIADOSŤ O ODŠKODNÉ), booked slot, CTAs → /translate /insurance /(tabs)/hunter /my-recovery /physio.
   - Home: HealingStrip card (engine) under Jarvis orb; health hub top item hh-healing.
2. ANGEL SHIELD 2.0 (senior suite, AngelHome rewritten with ScrollView):
   - THE COMPANION: GET /api/companion/greeting (Prague-time empathetic question: sleep/meal/pain/evening + care_note on low mood), POST /api/companion/checkin (mood 1-5, warm reply, push to family on mood≤2), GET /api/companion/trends (14d avg + improving/declining). 3 huge emoji buttons on Angel home.
   - MAGIC LENS (Kúzelná lupa): lens.tsx auto-reads analysis aloud after scan (TTS nova 0.92) + PREČÍTAŤ NAHLAS action; big Angel card → /lens.
   - VOICE ECHOES: /api/family/echoes GET/POST + /{id}/heard; /voice-echoes screen (huge play cards, TTS 'Odkaz od…', unheard badge, preset quick messages); Angel card with unheard count.
3. ETERNAL VAULT (/eternal-vault, expo-local-authentication@17.0.9 installed): biometric lock (web/no-hw fallback opens), contains dignity/legal/biometric-will/video-legacy/digital-legacy/healthcare-proxy. REMOVED from daily flow: legacy tab stripped of end-of-life items → renamed 'Majetok a príjem' (wallet icon, MAJETOK tab); profile dignity-btn → eternal-vault-btn; home pillar 'Odkaz' → 'Majetok'.
4. JARVIS AWARENESS: neural._gather_context now includes healing_loop (steps, booked slot, claim status/€) + companion (avg mood 7d) — verified via /api/jarvis/context.
Backend verified by curl: injury-event → 40% progress, claim 315 € prefilled, slot booked; companion greeting/checkin; echoes CRUD; jarvis context.

## Phase 32: REMOTE ECHOES + REFERRAL BRIDGE + HEALING REPORT (June 2026) — DONE ✅
(iteration_28 ALL GREEN: 12/12 backend + 20/20 frontend E2E)
1. RODINNÝ PRÍSTUP — GET /api/family/echoes/recipients (users where I'm guardian via db.guardians + inner_circle flag); POST /api/family/echoes/send {to_email,message} (auth: guardian link OR inner_circle member; 403/404/400 branches; push to senior; echo has remote:true + sender_user_id). voice-echoes.tsx: 'KOMU?' chips (ve-target-self / ve-target-<uid>), remote hint, ve-sent-msg confirmation.
2. SKEN VÝMENNÉHO LÍSTKA — lens.tsx result adds 'SPUSTIŤ KOLOTOČ UZDRAVENIA' (ln-act-healing) when kind∈{medical_report,prescription,lab_results} or specialty → /healing?specialty=X&auto=1; healing.tsx useLocalSearchParams auto-opens wizard (only when no active journey), sets kind=illness, injects specialty as extra selected chip.
3. TÝŽDENNÝ REPORT — GET /api/healing/report.pdf (_auth_pdf token support): carousel steps [X]/[!]/[ ], claim €, PN/vychádzky, 14d mood bar graph (█ blocks) + avg + trend SK; healing-report button on /healing (both states) via sharePdf.
Test users: senior test@example.com/test-token-abc, family lucka@example.com/fam-token-abc (guardian of senior).

## Phase 32.5: VOICE RECORDINGS + CARE SWEEPS (June 2026) — DONE ✅ (backend curl-verified; UI audited in iteration_29)
1. HLASOVÉ NAHRÁVKY — POST /api/family/echoes/audio (multipart, max 15MB, self alebo to_email s guardian/inner-circle authz, object storage APP_NAME/echoes/{uid}/{id}.m4a, echo audio:true) + GET /api/family/echoes/{id}/audio (stream, token query, recipient OR sender). voice-echoes.tsx: useAudioRecorder(HIGH_QUALITY) + AudioModule permission contract (canAskAgain → Linking.openSettings), ve-record (native only; web note), playback plays real audio via cachedAudioUri, mic icon on audio cards.
2. RANNÁ PRIPOMIENKA — companion_reminder_sweep (Praha 9–12h, users s checkinmi alebo angel_mode, skip ak dnes odpovedali, dedup db.companion_reminders per deň, push '💛 JARVIS SA PÝTA') + POST /api/companion/remind-sweep (force). Swarm agent 'companion_care' (600s).
3. NEDEĽNÝ AUTO-REPORT — _report_parts(uid) refaktor; _save_report_to_vault → PDF do object storage + db.documents (source healing_report) + calendar event; weekly_report_sweep (nedeľa Praha, dedup db.healing_report_runs per ISO week, push) + POST /api/healing/report/save-to-vault; swarm agent 'weekly_reporter' (3600s); healing.tsx button healing-report-vault ('AUTO: každú nedeľu').
Curl-verified: audio upload+stream 200, remind sweep 1 sent + dedup, vault doc saved (36kB), weekly sweep saved 1.

## Phase 33: SOVEREIGN TRIANGLE — 3-Pillar Permanent Architecture (June 2026) — DONE ✅
(iteration_29: 60/60 frontend audit GREEN, zero dead buttons, zero console errors)
Founder's final blueprint: 4 taby → 3 piliere so 100% zachovaním funkcií.
- PillarHub.tsx: nové props `sections: {title, items[]}[]` + `hero: ReactNode` (spätne kompatibilné s items).
- PILIER 1 (tabs)/health.tsx 'Moje uzdravovanie' (icon sync-circle): sekcie KOLOTOČ (hh-healing/translate/waitlist/arbitrage/recovery/physio — absorboval medicínske položky Huntera), ZDRAVOTNÉ DÁTA (vault/timeline/lens/drop/clinic-sync/news/border/ips/bible), LIEKY A TELO (meds/cabinet/pharmacy/bioscan/longevity/mental).
- PILIER 2 (tabs)/family.tsx 'Rodinný štít': zlatý pulzujúci ANGEL MODE hero (fs-angel, Pulse), sekcie HEROIC SENIOR SUITE (fs-magic-lens/echoes/wellness/fallverify/onboarding), RODINNÁ SYNCHRONIZÁCIA (pulse/pulsecheck/respect/fs-2fa→recovery-suite/monolith/gigs), OCHRANA (scam/duress/medic/paramedic/qr/wallpaper).
- PILIER 3 (tabs)/legacy.tsx 'Suverénny trezor' (icon shield-checkmark, tab TREZOR): A·MAJETOK A POISTKY (wealth/insurance/healing/refunds/lw-token/subscription/protocol/market/barter/solidarity/inner-circle), B·ODKAZ (lw-eternal→/eternal-vault biometria), C·PREŽITIE BUNKER MODE (compass/mesh/blackout/survival/enviro/humanitarian/truth/ghost/fortress/recovery-suite/mosaic — absorboval survival položky Huntera).
- _layout.tsx: 3 taby UZDRAVOVANIE/RODINNÝ ŠTÍT/TREZOR; hunter tab hidden (href:null, routy /(tabs)/hunter a /(tabs)/waitlist fungujú ďalej). Home: 3 pillar tiles.

## Phase 34: PHYSIO EXPERT VIDEOS + NATIVE PERMISSIONS (June 2026) — DONE ✅
1. VLASTNÉ EXPERTNÉ VIDEÁ — routes/physio_media.py: POST /api/physio/videos (multipart, max 100MB, object storage APP_NAME/physio/{uid}/{id}.mp4; is_global=True ak uploader is_founder → Founder's Expert Series viditeľné všetkým, inak súkromné), GET /api/physio/videos?guide_id= (vlastné + globálne, flag mine), GET /{id}/file (stream + token query, Accept-Ranges), DELETE (len vlastné). Curl-verified: upload, privacy izolácia (Lucka nevidí súkromné), founder-global viditeľnosť, stream 200, delete. user_test123 má teraz is_founder:true.
2. physio.tsx: ExpertVideos komponent v každom otvorenom sprievodcovi — sekcia '🎬 EXPERTNÉ VIDEÁ', prehrávanie so zvukom (GuideVideo prop muted=false, URL ${API_BASE}/api/physio/videos/{id}/file?token=), FOUNDER badge, ev-record-{guide} (kamera, permission contract s canAskAgain→openSettings), ev-pick-{guide} (galéria, ImagePicker mediaTypes:['videos']), ev-del pre vlastné, web note (upload len mobil). Screenshot-verified na /physio (guide lymph).
3. app.json NATÍVNE PERMISSIONS doplnené: iOS NSCamera/NSMicrophone/NSPhotoLibrary UsageDescription; Android CAMERA + RECORD_AUDIO — nutné pre Expo Go/native test Kúzelnej lupy, hlasových nahrávok a video uploadu.

## Phase 35: AUTO-CAPTIONS + WEEKLY RECOVERY PLAYLIST (June 2026) — DONE ✅
1. TITULKY PRE NEPOČUJÚCICH — physio_media.py: _transcribe_video_task (Whisper whisper-1 na video ≤24MB z object storage → transcript; Claude claude-sonnet-5 štruktúruje na 3–10 očíslovaných krokov v jazyku usera; statusy pending/processing/done/failed/too_large + transcript_error). Auto background task pri uploade (asyncio.create_task) + manuálny POST /api/physio/videos/{id}/transcribe (owner, retry). E2E overené s reálnou TTS naráciou: 'Sadnite si na stoličku / vystrite koleno 5 s / 10× na nohu' → presné 3 kroky.
2. TÝŽDENNÝ PLÁN — POST /api/physio/plan/generate: 7 dní (Po–Ne, témy body/expert/stress/recap v 4 jazykoch sk/cs/en/de), 2 návody/deň rotačne + expertné videá priradené k svojim návodom (zvyšok na dni 2/5); DENNÁ KOTVA z aktívneho Kolotoča (ANCHOR_MAP kolen→knee, chrbt→spine, ramen→shoulders, zápäst→wrists, krk→cervical) — overené: úraz Koleno → anchor knee ⭐ v každom dni. GET /api/physio/plan (progress_pct), POST /api/physio/plan/day/{n}/complete (push gratulácia pri 7/7). Kolekcia db.physio_plans (1 plán/user, regenerate nahradí).
3. physio.tsx: WeeklyPlan komponent navrchu (ph-plan-generate, horizontálne day karty, plan-item-{d}-{ix} tap → otvorí guide, ph-plan-done-{n} — klik overený screenshotom, ph-plan-regen); ExpertVideos: ev-cc-{id} toggle TITULKY (CC) so zoznamom krokov, ev-cc-retry-{id} pri failed, ev-refresh-{guide}, stavové poznámky (processing/too_large).
Poznámka: testovacie artefakty v DB — founder video 'Lymfodrenáž' (lymph, global) a 'Koleno — narácia test' (knee, s hotovými titulkami) — slúžia ako demo, user ich vie zmazať v UI.

## Phase 36: VEČERNÁ PRIPOMIENKA + BOLESŤOVÝ DENNÍK (June 2026) — DONE ✅
1. PRIPOMIENKA CVIČENIA — physio_media.py: physio_reminder_sweep (Praha 18–21h, plány kde dnešný deň date==today a done:false, dedup db.physio_reminders/deň, push '🧘 VEČERNÁ PRIPOMIENKA' s témou dňa; sent počítaný nezávisle od push transportu — v dev push 401 lebo EMERGENT_PUSH_KEY placeholder, funguje po deployi). Manuálny POST /api/physio/plan/remind-sweep (force). Swarm agent 'physio_coach' (900s). Curl: 1 sent → dedup 0.
2. BOLESŤOVÝ DENNÍK — POST /api/physio/pain {level 1-10, guide_id} (validácia 400, Jarvis odpoveď podľa úrovne: ≥8 STOP+lekár, 5-7 znížiť intenzitu, <5 pochvala) → db.pain_diary; GET /api/physio/pain/trends (14d, avg, improving=klesá/worsening/stable). REPORT PRE LEKÁRA: healing._report_parts sekcia '5. BOLESŤOVÝ DENNÍK' s 10-blokovým bar grafom (█░), guide_id, priemer + tendencia SK ('BOLESŤ KLESÁ ↘ (hojenie)' / 'RASTIE ↗ (konzultujte lekára)'). physio.tsx: PainLogger v každom otvorenom cviku (pain-{guide}-{1..10} kruhy, 8-10 červené, 5-7 žlté; pain-reply-{guide}; trend riadok 'ide do reportu pre lekára'). Screenshot E2E OK.

## Phase 37: BOLESŤ V KOLOTOČI + HLASOVÝ ZÁPIS BOLESTI (June 2026) — DONE ✅
1. KRIVKA BOLESTI V KOLOTOČI — healing.tsx PainCurve (testID healing-pain-curve) pod progress kartou aktívneho kolotoča: 14 posledných záznamov ako farebné stĺpce (≥8 červená, 5-7 warn, <5 zlatá), trend label (↘ HOJENIE / ↗ POZOR / → STABILNÁ), priemer + počet, hint '🎙 Stačí povedať Jarvisovi: „Bolí ma to na sedem“'. Skryté ak žiadne záznamy. Screenshot E2E OK.
2. HLASOVÝ ZÁPIS — agent.py _detect_pain_level (deterministický intent PRED LLM: koreň bol-/pain + číslo 1-10 ako digit, 'X z 10', alebo slovné číslovky sk/cs/en; správy >120 znakov ignorované). Pri zhode: insert db.pain_diary (source:'voice', note=veta), okamžitá odpoveď bez LLM (≥8 STOP+concerned, 5-7 thinking, <5 calm), konverzácia uložená, XP 'pain_log', response má pain_logged. Curl overené: 'bolí ma to na sedem'→7, 'bolest je tak 3 z 10'→3, 'bolí koleno na deväť'→9, 'aké je počasie'→None (normálny LLM Jarvis, bez false positive). Funguje pre text aj hlas (STT→/agent/chat).

## Phase 38: ZDIEĽANIE KRIVKY RODINE (June 2026) — DONE ✅
GET /api/family/recovery-pulse (healing.py): pre každého seniora, ktorého som strážca (db.guardians) → name, pain_levels (posledných 7), pain_avg_14d, pain_trend + správa ('Bolesť klesá — zotavenie ide dobre 💛' / 'rastie — zavolajte 📞' / 'stabilný 💪'), healing_active + progress_pct + label, posledná nálada Spoločníka. family-dashboard.tsx: sekcia '💛 ZOTAVENIE BLÍZKYCH' (fd-loved-{uid}) s farebnými mini stĺpcami, KOLOTOČ % pill, správou a náladou — skrytá ak žiadni blízki. E2E overené ako Lucka (vidí Jaroslava: KOLOTOČ 40 %, Ø 5.3/10, stabilný).
Pozn.: Hlasový okruh 'bolí ma to na sedem' (Phase 37) je pripravený na test v Expo Go — QR + mikrofón.

## Phase 39: POVZBUDENIE JEDNÝM ŤUKOM + MÍĽNIKY S KONFETAMI (June 2026) — DONE ✅
1. POVZBUDENIE — /api/family/recovery-pulse teraz vracia aj email; family-dashboard.tsx karta blízkeho má tlačidlo fd-encourage-{uid} 'POSLAŤ POVZBUDENIE (VOICE ECHO)' → POST /family/echoes/send s prednastavenou správou podľa trendu (worsening: 'Drž sa! zajtra bude lepšie ❤️' / inak: 'Sme na teba hrdí ❤️') → potvrdenie fd-enc-sent. E2E overené ako Lucka (screenshot) + echo doručené seniorovi (remote:true, unheard).
2. MÍĽNIKY — physio_media.check_pain_milestone: min 3 záznamy/14d, int(avg) porovnaný s db.pain_milestones.best_floor (baseline pri prvom checku); pokles o celý bod → milestone True + správa '🎉 MÍĽNIK ZOTAVENIA! Priemer klesol na X/10'. Napojené na POST /physio/pain (response milestone+milestone_message) AJ hlasový zápis v agent.py (pripojí sa k reply). physio.tsx: ConfettiBurst (18 kúskov, RN Animated bez závislostí, useNativeDriver) + pain-milestone-{guide} text v PainLoggeri. Curl overené: avg 3.8 → milestone True.
Pozn.: ARCHANGEL MONOLIT (Sovereign Triangle) bol kompletne implementovaný vo Phase 33 (audit 60/60) — user ho re-poslal, žiadne chýbajúce časti nenájdené.

## Phase 40: SENTIENT UX FORK — ULTRA MODE (Feb 2026) — DONE ✅
Founder command: merge Sovereign Triangle with the Sentient UX Soul — biometric onboarding,
Onyx voice (no more robot), Guardian Gold Senior Switch on hub+topbar, JARVIS wake-word,
Bio-Timeline (5 stages).

1. BACKEND (routes/auth.py): PrefIn + birth_year (1900-2030, else 400), biometric_enabled, wake_word_enabled.
   Fully covered by 30 pytest cases (test_iter30_sentient_ux.py — GREEN).
2. SENTIENT VOICE (src/voice.ts): unified Jarvis voice utility, DEFAULT_VOICE='onyx' (deep, human, Tony-Stark).
   Single module-level createAudioPlayer (never doubles up), stopSpeaking() global. jarvis.tsx and physio.tsx
   both migrated (were on 'coral' / 'nova' — replaced with 'onyx'). TTS onyx roundtrip verified server-side.
3. BIOMETRIC GATE (src/biometric-gate.tsx): full-screen FaceID/Fingerprint/Iris gate wrapping <Stack/>
   in _layout.tsx. Soft-fails on web + hardware-less. Re-locks after 60s background. Warm onyx greeting
   on first unlock ('Vitajte späť, {name}. Som Jarvis, váš anjel-strážca.').
4. GUARDIAN GOLD (app/(tabs)/index.tsx): angel-toggle in top nav now shows 'SENIOR' pill (gold-glow when
   suggested). NEW hub-guardian-gold: prominent LinearGradient card under pillar grid — ETAPA ŽIVOTA chip
   auto-adapts to birth_year (infant→child→teen→adult→senior).
5. BIO-TIMELINE (src/age.ts): 5 stages derived from birth_year. suggestAngelMode(senior)=true auto-lights
   the Guardian Gold card. jarvisToneFor() feeds Onyx speed presets per stage.
6. WAKE-WORD (src/wake-word.ts): Alexa-style 'JARVIS' listener scaffold, activated in AngelHome only when
   wake_word_enabled. Native only. Auto-pauses in background. Founder must know: real 24/7 wake-word needs
   Porcupine/Snowboy in a native build; scaffold uses metering threshold until then.
7. PROFILE (app/(tabs)/profile.tsx): new SENTIENT UX section with 4 controls (voice preview, birth year,
   biometric switch, wake-word switch) — all persist via PATCH /me/prefs.
Verified: Home screenshot shows SENIOR pill + Guardian Gold card 'ETAPA ŽIVOTA: SENIOR (65+)' after
setting birth_year=1958. Profile screenshot shows all four Sentient controls in Slovak.
Backend: 30/30 pytest green (test_iter30_sentient_ux.py).
