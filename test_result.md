#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================
## Iteration 3 scope (main agent, June 2026)
New since iteration 2 (all need testing):
- UX batch 1: real-time fall detection (expo-sensors, frontend GuardianMonitor), OCR /api/vault/documents/{id}/ocr (gpt-5.4 vision + pypdf/pymupdf), Emergent push (/api/register-push, send_push on waitlist scan hit), Wellness module (/api/wellness/checkin, /checkins, /vitals, /inactivity-alert, /dashboard), Profile guardian toggles (fall_guard, inactivity_guard, inactivity_hours prefs), screens /wellness, /family-dashboard.
- Killer features batch 2: /api/ai/advice (Jarvis advisor), Medicine Cabinet (/api/cabinet/items CRUD + /api/cabinet/exchange P2P + respond), Healthcare Proxy (/api/proxy-directive GET/PUT, doc template + sha256 hash, surfaced in /api/emergency-qr/{did}), Marketplace (/api/market/services CRUD + book + bookings), Scam Shield (/api/scam/check + history, Claude JSON risk analysis), Survival Auditor (/api/survival/items + /api/survival/runway, family_size pref), Barter (/api/barter/offers + accept credit transfer + /api/barter/me), Beacon (/api/beacon/trigger + history). Respect Map extended metrics (minority_safety, waiting_weeks, financial_transparency aggregates).
- Frontend screens: /medicine-cabinet, /healthcare-proxy, /marketplace, /scam-shield, /survival-auditor, /barter; home reorganized into 4 sections; stealth beacon long-press on GUARDIAN logo.
- Push register returns 500 with placeholder key by design (real key injected at deploy) — treat relay 500 from register-push as EXPECTED in this environment.
- Auth: create test session directly in Mongo per /app/memory/test_credentials.md.

## Iteration 4 scope (Global Compliance & Indemnity, June 2026)
- GET /api/legal/region?country=&language= → jurisdiction (EU/UK/US/OTHER) + disclaimers (EU AI Act Art.50, GDPR, UK DPA/DUAA 2025, FDA/HIPAA) + testament_format + aml limits
- GET /api/legal/tos + POST /api/legal/accept → tos_accepted_version '2026-06.1' on user; TOS gate blocks home until accepted (testID tos-gate, tos-gate-accept)
- POST /api/aml/kyc (declaration required) → DID attestation + tamper-evident aml_ledger hash chain; GET /api/aml/status
- AML enforcement on /api/solidarity/campaigns (403 kyc_required without KYC) and donate (403 aml_limit >€150/day unverified, €5000 verified; 403 aml_velocity >10 tx/day)
- POST/GET /api/legal/testament → region formats: civil_law_holograph (SK §476), common_law_uk (Wills Act 1837 s.9, holograph invalid E&W), common_law (US 2 witnesses)
- AI prompts now append compliance note (Art. 50); frontend AI disclosure footers
- New screen /legal (country chips, disclaimers, TOS view/accept, KYC form, testament generator); Profile → legal link; Solidarity AML banner + error msgs
- NOTE: existing test users likely lack tos_accepted_version → frontend home shows TOS gate first; accept via testID tos-gate-accept or set field in Mongo.

## Iteration 5 scope (PDF export + med reminders, June 2026)
- PDF export: GET /api/legal/tos.pdf?language=, /api/legal/testament.pdf, /api/legal/proxy.pdf — auth via Bearer header OR ?token= query. fpdf2 + Liberation fonts (Slovak diacritics OK). Frontend share via src/pdf.ts (web window.open, native FileSystem legacy + expo-sharing) — buttons: lg-tos-pdf, tw-pdf (legal.tsx), hp-pdf (healthcare-proxy.tsx).
- Medication reminders: /api/meds/reminders CRUD, /api/meds/today (items + pending count), /api/meds/intake. Screen /meds: senior XL UI, big take buttons, TTS read-aloud + auto voice alert, daily LOCAL notifications via expo-notifications (native only). Angel tile "LIEKY" → /meds; alarm icon in medicine-cabinet header.
- Push logic complete (Option A) — user provides google-services.json at deploy.
- DB EMPTY after fork — smoke user recreated (see test_credentials.md). Backend verified by curl: tos.pdf 200 36KB, testament.pdf 200 33KB, meds CRUD/today OK.

## Iteration 7 scope (Premium Guardian OS UI overhaul + Survival & Trust features, June 2026)
UI OVERHAUL (untested until now):
- New 4-pillar architecture: (tabs)/index.tsx home with pillar grid (testIDs pillar-health/family/legacy/hunter), tab bar (tab-health/family/legacy/hunter), hub screens via PillarHub (hub-health/hub-family/hub-legacy/hub-hunter with hh-*/fs-*/lw-* item rows).
- Angel Mode radical reset: angel-toggle on home header → angel-home full-screen (angel-jarvis orb, angel-sos, angel-family, angel-doctor, angel-toggle-back exit). Tab bar hidden in angel mode.
- FIXED by main agent: (tabs)/index.tsx StyleSheet was missing 17 style keys (pillar*, sosPill*, angel*, jarvis*) — added premium dark/gold styles. Also fixed auth refresh(): token no longer cleared on transient network errors (only 401/403).
NEW FEATURES (all need testing):
- Border Crosser: GET /api/border/certificate (JSON: holder, meds from cabinet prescription items, did_signature, 14 languages), GET /api/border/certificate.pdf (?token= supported). Screen /border-pass (bp-pdf button), entry hh-border in Health hub.
- Emergency Wallpaper: GET /api/family/wallpaper.png (?token=) — 1080x1920 PNG with QR (offline JSON payload: blood/allergies/ICE from emergency_profiles). Screen /wallpaper (wp-preview img, wp-download), entry fs-wallpaper in Family hub.
- Mental Fortress: GET /api/mental/techniques — 6 SK techniques (box, grounding, li4, pc6, yintang, pmr) each with tts_text + disclaimer. Screen /mental-fortress (mf-item-{id} expand, mf-play-{id} TTS via existing /api/voice/tts), entry hh-mental in Health hub.
- Biometric Will: POST /api/legal/testament/biometric (multipart audio/video only, 50MB max) → sha256 + aml_ledger 'biometric_will' entry + updates legal_testaments.biometric_hash; GET same path → record; GET .../file (?token=) streams; DELETE removes. Screen /biometric-will (bw-record audio via expo-audio, bw-video picker, proof card, bw-delete), entry lw-biometric in Legacy hub.
- Backend verified by curl: border cert JSON+PDF 200, wallpaper.png 200 (49KB), biometric upload/file/delete OK, mental techniques OK.
- Auth for tests: user smoketest-user-1, Bearer smoketok-fresh-2026 (TOS accepted). Web login: localStorage.setItem('gh_session_token','smoketok-fresh-2026') then reload.

## Iteration 8 scope (Survival Extensions, June 2026)
User-reported /api/auth/me ERR_ABORTED splash bug: backend verified healthy (200 local+external); root cause was auth token being cleared on transient network errors — already fixed in iteration 7 (auth.tsx refresh only clears on 401/403). Verified: dashboard loads after token inject.
NEW (all need testing):
- Acoustic Threat Detection: POST /api/acoustic-event {kind, db_level} → logs db.acoustic_events + push attempt; GET /api/acoustic-events. Frontend: Angel Mode button testID angel-acoustic (src/acoustic.ts — local mic metering via expo-audio, threshold -8dBFS, on threat POST + route to /fall-verify). Web: metering limited, just verify button toggles without crash.
- Analog Recovery Kit: GET /api/survival/bible.pdf?token= — 8-section printable PDF (identity/meds/cabinet/waitlist/proxy/legacy/analog crisis techniques/emergency numbers). Frontend: Health hub item hh-bible (one-tap sharePdf, opens PDF in new tab on web).
- Pharmacy Stock Hunter: GET /api/pharmacy/search?med=&region=SK|CZ (simulated:true, deterministic per med+pharmacy, 6 pharmacies, statuses in/low/out sorted); POST /api/pharmacy/watch; GET /api/pharmacy/watches; POST /api/pharmacy/watches/{id}/scan (hit→status found + push attempt); DELETE watch. Screen /pharmacy-hunter (ph-input, ph-region-SK/CZ, ph-search, ph-watch, ph-scan-{id}, ph-del-{id}), entry ht-pharmacy in Hunter hub. DEMO DÁTA badge shown (no public real-time pharmacy stock API exists for SK/CZ).
- Guardian Pulse Check (STRICTLY OPT-IN): PrefIn + pulse_check_optin & acoustic_guard; POST /api/pulse/request {target_did} → 403 opt_in_required if target not opted in, 404 unknown DID, 400 self-ping; GET /api/pulse/requests (inbox); POST /api/pulse/requests/{id}/respond {status: ok|need_help} → push to sender; GET /api/pulse/sent. Screen /pulse-check (pc-optin switch, pc-did-input, pc-send, pc-ok-{id}, pc-help-{id}), entry fs-pulsecheck in Family hub, privacy toggle prof-pulse-optin in Profile.
- FIX: family.tsx enableAngel now router.navigate('/(tabs)') so AngelHome gets focus (was leaving overlapping screens intercepting clicks).
- Backend curl-verified: pharmacy search 200, bible.pdf 200 37KB, acoustic-event 200, pulse self-ping 400.
- Smoke user angel_mode reset to false. For pulse opt-in flow testing, a second user may be created in Mongo (users + user_sessions).

## Iteration 9 scope (Production polish: refactor + Health Drop + Auto-Booker + Calendar, June 2026)
REFACTOR (done, verified): server.py monolith split into core.py (db/auth/storage/push/PDF/AML-ledger helpers + shared `api` router), models.py, content.py (multilingual Mental Fortress + Physio guides), routes/{auth,health,family,hunter,legacy}.py. server.py is now a slim app entry. FULL PYTEST: 139/139 pass (run serially: `python -m pytest tests/ -o addopts=""`; xdist has known cross-worker fixture races in phase7 — NOT a code bug). test_phase2 updated: solidarity campaign now does KYC first (AML design).
NEW FEATURES (need testing):
1. HEALTH DROP (zero-knowledge referral bridge):
   - GET /api/health-drop/me (auth) → {drop_id, public_key, did}; PUT /api/health-drop/pubkey.
   - PUBLIC: GET /api/health-drop/{drop_id}/info; POST /api/health-drop/{drop_id}/upload (multipart: file=ciphertext, eph_pub, nonce, guardian_id [full DID or last-6, e.g. 'smoke1'], sender_name, doc_title, orig_type). 403 wrong GID, 404 bad drop_id, 409 if no pubkey. Referral keyword detection → is_referral + specialty_guess.
   - GET /api/health-drop/inbox, GET /api/health-drop/items/{id}/file, DELETE item.
   - Crypto: tweetnacl box, encrypt in provider browser (src/dropcrypto.ts), decrypt on device (secret in SecureStore/localStorage 'gh_drop_sk'). Node roundtrip verified.
   - Screens: /health-drop (hd-copy, hd-share, hd-open-{id}, hd-autobook-{id}, QR of link) — entry hh-drop in Health hub. PUBLIC portal /drop/{dropId} (dp-pick, dp-guardian-id, dp-sender, dp-title, dp-send) — accessible WITHOUT login (_layout allows 'drop' segment). On web DocumentPicker renders hidden <input type=file> — playwright can set_input_files.
2. AUTO-BOOKER: POST /api/autobook {specialty, city?, source, source_id} → simulated booking (status booked, found_slot) + calendar event + push attempt; POST /api/waitlist/{item_id}/autobook for existing items. Jarvis prompt card on /health-drop for is_referral items → ÁNO REZERVUJ button.
3. LIFE-HEALTH CALENDAR: POST /api/calendar/events {category exam|history|vaccine, title, date YYYY-MM-DD, booster_due?}; GET /api/calendar/timeline?category= → events + upcoming_exams + booster_alerts (within 90d); DELETE event. Screen /health-timeline (ht-add, ht-cat-*, ht-title, ht-date, ht-booster, ht-save, ht-filter-*, ht-del-{id}) — entry hh-timeline in Health hub.
4. MULTILINGUAL CONTENT: GET /api/mental/techniques?language=sk|cs|en|de and NEW GET /api/physio/guides?language= (3 founder guides: knee, panic-acupressure, ergonomics). UI: mental-fortress language chips mf-lang-{sk,cs,en,de}; physio.tsx guides section (guide-{id}, guide-play-{id} TTS).
5. WALLPAPER ONE-TAP SHARE: wp-share button on /wallpaper (web: navigator.share/copy; native share sheet).
- Backend curl-verified: pubkey PUT, portal upload 200 + 403 wrong GID, inbox referral detection, autobook → calendar sync, timeline, mental de/en, physio guides en.
- Smoke user pubkey currently set to a node-test key; app regenerates its own on /health-drop open (expected: old seeded ciphertext then fails decrypt with friendly error — re-upload via portal for decrypt tests).

## Iteration 10 scope (Sick Leave & Recovery Module — Hustle Recovery Guard, June 2026)
NEW (needs testing), all in routes/health.py + /app/frontend/app/my-recovery.tsx (entry hh-recovery in Health hub):
- PUT /api/recovery/epn {start_date YYYY-MM-DD (req), end_date?, note?, contract_type fulltime|dpp|dpc, monthly_gross, outings:[{from_time HH:MM, to_time HH:MM}]} → upsert db.recovery; 400 on bad dates/times/contract. GET /api/recovery/epn.
- POST /api/recovery/extract-outings {text} → Claude extracts outing windows from SK/CZ ePN text → {outings:[], found} (verified working: extracted 10:00-12:00 + 16:00-18:00 from Slovak sample).
- POST /api/recovery/sickpay {contract_type, monthly_gross, days} → simplified SK 2026 estimate: DVZ=gross*12/365; day1-3 25%, day4-10 55% (employer), day11+ 55% (Sociálna poisťovňa); shortfall vs normal income; solidarity_suggested if shortfall>=30%; DPP/DPČ warning; 400 on invalid input. Marked simulated with disclaimer.
- GET /api/recovery/report.pdf?kind=employer|social (&token=) → one-tap PDF status report; 404 if no ePN record.
- UI testIDs: mr-start, mr-end, mr-contract-{fulltime,dpp,dpc}, mr-gross, mr-note, mr-out-from/to/add, mr-out-del-{i}, mr-ai-toggle, mr-ai-text, mr-ai-run, mr-save, mr-alerts (local notifications — native only, web shows info), mr-days, mr-calc, mr-solidarity (link to /solidarity when shortfall>=30%), mr-pdf-employer, mr-pdf-social. Live outing status card with countdown + 15-min warning highlight.
- Smoke user has seeded ePN (2026-06-20→2026-07-15, DPP 850€, outings 10-12 & 16-18).
- Backend curl-verified: epn PUT/GET, sickpay math, report.pdf 200, AI extraction 200.

## Iteration 11 scope (NEURAL LINK — Jarvis orchestrator, June 2026)
NEW backend module /app/backend/routes/neural.py (registered in server.py):
- GET /api/jarvis/context — unified cross-module snapshot (health/wealth/safety from all collections).
- POST /api/jarvis/ask {question, language} — Claude answers with FULL cross-module context injected (verified: combines recovery + calendar + waitlist data in one Slovak answer). 400 empty question; allow 60s timeout.
- POST /api/chains/healing {specialty | drop_doc_id} — referral→hunter→solidarity check→autobook (simulated)→calendar→employer notice. Loop-safe: already-autobooked drop → skipped step + no rebooking. Returns {chain, steps[{step,status,detail}], summary, simulated}.
- POST /api/chains/safety {trigger} — beacon event insert + legacy check (donor/testament/proxy) + wallpaper info release.
- POST /api/chains/recovery {} — wellness activity check → physio guide proposal → outing-hours check (walk now vs wait vs no PN).
- POST /api/chains/supply {med_name, region} — pharmacy scan (DEMO) → solidarity+dignity cash check → barter suggestion when cash low → logistics note. 400 empty med_name.
- GET /api/reports/weekly.pdf (?token=) — Guardian Pulse Report PDF (Health/Wealth/Safety sections). Verified 200 34KB.
Frontend /app/frontend/app/jarvis.tsx (testIDs: jv-back, jv-quick-{0,1,2}, jv-input, jv-ask, jv-speak, jv-chain-{healing,safety,recovery,supply}, jv-weekly). Entry points: home header sparkles button testID home-jarvis; Angel Mode orb angel-jarvis now routes to /jarvis (was /wellness).
All backend endpoints curl-verified. Chains are one-shot request/response — no recursion possible.

## Iteration 12 scope (GLOBAL INFRASTRUCTURE — Gateway · Marketplace · Sentinel · Stripe, June 2026)
NEW backend module /app/backend/routes/gateway.py (registered in server.py) + performance indexes at startup:
1. PARTNER API GATEWAY (fully functional): POST /api/gateway/grants {partner_name, scopes subset of [emergency_profile, vault_list, recovery_status], expires_days 1-365} → returns one-time token gwk_*; GET /api/gateway/grants (token_preview only); DELETE /api/gateway/grants/{id} (revoke); GET /api/gateway/audit. Partner endpoints authed via X-Partner-Key header: GET /api/partner/v1/profile, /vault (metadata only), /recovery — 401 no key, 403 invalid/revoked/expired/scope-not-granted; every access audit-logged. Verified: profile 200 with granted scope, vault 403 without scope.
2. DATA MARKETPLACE (payouts SIMULATED, badged): PUT /api/marketplace/optin {enabled, categories}; GET /api/marketplace/me (earnings + sales); GET /api/marketplace/offers (3 demo research offers); POST /api/marketplace/offers/{id}/accept → 403 optin_required without opt-in, 409 duplicate, else earnings_eur incremented.
3. SENTINEL NETWORK: PUT /api/sentinel/node {enabled}; POST /api/sentinel/report {kind in supply_shortage|grid_down|pharmacy_out|water_issue, region} → anonymized (salted hash only), 429 after 5 same-kind/hour, 400 bad kind; GET /api/sentinel/aggregate → 7d counts by kind+region + active_nodes.
4. STRIPE ONRAMP (code-complete, awaiting real key): POST /api/solidarity/campaigns/{cid}/checkout {amount_eur 1-10000} → 503 stripe_key_missing with current placeholder key (EXPECTED — env STRIPE_API_KEY=sk_test_emergent is invalid); GET /api/solidarity/checkout/status/{session_id} idempotently records paid donations after server-side Stripe verification. UI: donate-card button in solidarity donate modal shows friendly message on 503.
5. PERFORMANCE: 12 new Mongo indexes; load test done by main agent: 200 concurrent requests 0.58s, 0 errors, p50 451ms / p95 536ms / p99 551ms.
Frontend: /app/frontend/app/protocol.tsx (testIDs: pr-partner, pr-scope-*, pr-grant, pr-token, pr-revoke-{id}, pr-market-optin, pr-offer-{id}, pr-signal-{kind}) — entry lw-protocol in Legacy hub. solidarity.tsx gained donateCard (donate-card).

## Iteration 17+18 scope (MASTER-SEAL + GIGA-LAYER + WORLD-CLASS FINALE + MOSAIC, June 2026)
NEW backend modules (all registered in server.py, indexes added at startup):
- routes/recovery_suite.py — Sovereign Recovery Suite: guardians CRUD (/api/recovery-suite/guardians), Social 2FA toggle (PATCH /api/recovery-suite/social-2fa; non-blocking login handshake push via notify_login_handshake hook in auth.py), 2FA guardian inbox (/2fa/pending, /2fa/{id}/confirm), Social Recovery public flow (/social/initiate → guardian /social/{id}/approve → public /social/{id}/status delivers one-time recov- session token exactly once), QR Talisman (POST /talisman one-time payload GA-TALISMAN|did|secret; public /talisman/redeem → talis- session; single-use 409 on reuse), Passkey placeholder register/delete.
- routes/compass.py — GET /api/compass/pack (offline survival bundle incl. sick_leave ePN outings + vaccinations booster_alerts), Truth-Validator (/api/truth/claims CRUD + votes; consensus verified when verify>=2>dispute; own-claim vote 400; dup vote 409), Bio-Beacon (/api/bio-beacon/activate|ping|deactivate|status + public /api/bio-beacon/public/{did}).
- routes/globalnet.py — Satellite Nano-Packet (POST /api/satellite/nano-packet — SENTINEL-gated, zlib<=140B, swarm broadcasts queue), IPS HL7 FHIR export (GET /api/ips/summary + .pdf — Sentinel free / auto-charge 10 GA-T), Humanitarian Shield (/api/humanitarian/verify|profile|status|card.pdf).
- routes/medic.py — AI Tactical Medic GET /api/medic/protocols (7 protocols; SENTINEL-gated with verified-emergency override).
- routes/bioscan.py — POST /api/bioscan/measure (Sentinel unlimited / pay_gat:true = 5 GA-T; 402 otherwise), GET /api/bioscan/history.
- routes/longevity.py — PUT /api/longevity/profile, GET /api/longevity/bioage (SENTINEL; 409 profile_missing).
- routes/enviro.py — POST /api/enviro/report, GET /api/enviro/threats (CONFIRMED at 2+ reports; swarm escalates + broadcast push).
- routes/mosaic.py — /api/mosaic/status|blocks|anchor|ipfs/manifest|legacy-contract|pqc-handshake|bridge/check|stress-test (ALL SIMULATED, zero-fee).
- paramedic.py += POST /api/paramedic/verify-registry (NCZI/ÚZIS deterministic mock: even digit-sum=valid), GET /api/paramedic/registry-info; active bio-beacon now counts as verified emergency.
- subscription.py REWRITTEN: 4 tiers €0/29/149/499, annual −20%, CZK/EUR/GA-T, POST /api/subscription/trial (one-time 7d Sentinel), require_tier/get_active_tier helpers, record_revenue, GET /api/wealth/founder-dashboard (founder-only: earliest user or is_founder flag).
- token.py: SPEND_ITEMS extended (tier_*_30d/365d, bioscan_single 5, ips_export_single 10); generic tier_ spend branch.
- 15% Guardian Tax hard-coded: market_book (legacy.py) + gig complete cash rewards → revenue_events.
- swarm.py: 7th agent sovereign_guard (expires handshakes/recovery reqs, kills stale beacons, broadcasts satellite queue, escalates enviro threats, produces Mosaic blocks).
- DAO REBRAND: /api/ author = "Guardian Angel Sovereign Foundation (DAO)"; GET /api/dao/manifest; all file headers + PDF footers rebranded; Article 50 waivers.
Frontend NEW screens (expo-router): /recovery-suite, /compass, /truth-validator, /paramedic, /gigs, /refunds, /humanitarian, /tactical-medic, /bioscan, /longevity, /enviro, /mosaic. Components: src/Art50.tsx (čl. 50 waiver footer), src/Paywall.tsx (trial/GA-T/upgrade). subscription.tsx rewritten (4 tiers, annual toggle, trial btn, founder box). Hubs wired: health(hh-bioscan,hh-longevity,hh-ips), family(fs-medic,fs-paramedic,fs-gigs), hunter(ht-compass,ht-truth,ht-humanitarian,ht-enviro), legacy(lw-mosaic,lw-refunds). profile: recovery-suite-btn + DAO about. medicine-cabinet: mc-ddi-scan interaction guard.
Backend fully tested: 52/52 new tests (test_phase17_masterseal.py, test_phase18_worldclass.py) + full regression green (stale asserts in phase10/15 updated to >=).

## Iteration 19 (GRAND FINALE): routes/demo.py (founder-only Investor Demo Mode: GET /api/demo/status, POST /api/demo/toggle — seeds/wipes demo:true docs in waitlist/jarvis_actions/pulse_requests), /app/frontend/app/onboarding.tsx (3-step senior guide), /app/frontend/app/launch.tsx (Launch Control checklist + DEPLOY card), profile.tsx FOUNDER ADMIN box (demo-toggle, launch-btn, onboarding-btn), family hub fs-onboarding. server.py indexes → db_indexes.py. Tests: test_phase19_grand_finale.py; FULL suite 346/346; frontend iteration_18.json 10/10 green. Demo mode left OFF (clean state).

## Iteration 20 (OMNIPOTENT ARCHANGEL FINAL SEAL, June 2026)
NEW backend: routes/wealth.py (Video Legacy Vault: POST/GET /api/legacy/video, /{id}/release, /{id}/file, DELETE; Sovereign Wealth Vault: GET /api/wealth/vault, POST /api/wealth/assets (crypto sealed zero-knowledge / bank IBAN-validated), POST /api/wealth/anchor (Mosaic), POST /api/wealth/payout (Instant Card Payout SIMULATED)), routes/seal.py (GET /api/foundation/identity hardcoded guardianangel.core@proton.me; /api/ghost/toggle|status 24h patient tokens; founder-only /api/inner-circle CRUD → permanent archangel via user.inner_circle checked in subscription.current_tier + auth signup whitelist; /api/arbitrage/procedures|quote|quotes PL/HU/TR; /api/bioidentity + PUT /api/bioidentity/genomic; /api/duress/pin|verify|status (decoy → silent alarm); /api/mesh/status|messages; /api/power-saver).
Frontend NEW screens: /video-legacy, /wealth-vault, /arbitrage (+genomic), /inner-circle, /duress, /mesh, /ghost-mode (foundation identity + ghost + power-saver). Hubs wired: legacy(lw-video-legacy, lw-wealth, lw-inner-circle), hunter(ht-arbitrage, ht-mesh, ht-ghost), family(fs-duress).
Backend tests: test_phase20_final_seal.py 30/30; FULL suite 376/376 PASS. NOTE for future agents: pytest runs with xdist `-n 2 --dist loadscope` → classes of the SAME module can land on DIFFERENT workers; never write cross-class shared-state tests (phase5/phase7 were fixed to be self-sufficient after adding phase20 reshuffled worker assignment).
Frontend smoke: login screen renders OK. Auth for frontend testing: seed session per /app/memory/test_credentials.md (insert users + user_sessions in Mongo, set token in AsyncStorage key used by src/api.ts).

## Iteration 21 (ULTRA MODE UI/UX Revolution, June 2026)
Glass/Luxe theme overhaul (theme.ts values changed globally), new UI kit src/ui/{glass,sheets,ContactSheet}. New screens: /lens (Guardian Lens AI vision — REAL gpt-5.4 vision verified), /clinic-sync (QR handshake real, BLE radar simulated). Rewrites: home (tabs)/index.tsx (Lens FAB pulsing), fall-verify.tsx (120s + /api/voice/liveness Whisper hands-free cancel — verified via TTS roundtrip), meds.tsx (day-part slots w/ sun/moon), waitlist (DateSheet/OptionSheet), recovery-suite (contact picker), tab bar Slovak+haptics. Backend: routes/lens.py, routes/clinic_sync.py, MedReminderIn.slots. Suite 390/390 PASS (test_phase21_ultra.py added).

## Iteration 27 (LIFE-FIRST REORGANIZATION / Phase 31, June 2026)
Sovereign Healing Loop: routes/healing.py (injury-event → asyncio.gather fires insurance claim prefill + waitlist booking; neural_bus event; state/step-complete/claim-submit/close), Companion (/companion/greeting|checkin|trends), Voice Echoes (/family/echoes CRUD + heard). neural.py context += healing_loop + companion. Frontend: /healing (zero-typing wizard + 5-step timeline + claim submit), /eternal-vault (expo-local-authentication biometric lock; dignity/legal/biometric-will/video-legacy/digital-legacy/healthcare-proxy moved OUT of daily flow), /voice-echoes (TTS playback cards), home HealingStrip (home-healing), AngelHome 2.0 (angel-companion mood buttons, angel-magic-lens, angel-voice-echoes), lens.tsx auto TTS read-aloud, legacy tab → 'Majetok a príjem' (MAJETOK/wallet). Tests: test_phase31_healing_loop.py 19/19 PASS + frontend E2E green (iteration_27.json). Note: companion mood buttons render only when answered_today=false (intentional).

## Iteration 28 (Phase 32: Remote Echoes + Referral Bridge + Healing Report PDF, June 2026)
Backend: /family/echoes/recipients + /family/echoes/send (guardian/inner_circle authz) + /healing/report.pdf. Frontend: voice-echoes KOMU? remote targeting, lens ln-act-healing → /healing?specialty&auto=1 wizard prefill, healing-report PDF button. Tests: test_phase32_remote_echoes_report.py 12/12 + frontend E2E 20/20 (iteration_28.json). ALL GREEN.

## Iteration 29 (Phase 33: SOVEREIGN TRIANGLE, June 2026)
3-pillar restructure (UZDRAVOVANIE / RODINNÝ ŠTÍT / TREZOR), PillarHub sections+hero props, hunter tab hidden, gold pulsing Angel hero, Eternal Vault entry in pillar 3B. Also Phase 32.5: audio voice echoes (record+stream), companion morning reminder sweep + weekly vault report sweep (swarm agents companion_care/weekly_reporter). Frontend audit 60/60 GREEN, 0 dead buttons, 0 console errors (iteration_29.json). Optional note: /fall-verify countdown starts on mount (by design).

## Iteration 30 (Phase 34: Physio Expert Videos, June 2026)
physio_media.py CRUD + stream (curl 6/6 OK: upload/list/privacy/global-founder/stream/delete), physio.tsx ExpertVideos per guide (screenshot OK: section+FOUNDER badge+web note), app.json camera/mic/photo permissions added. Video upload/record is native-only (web shows note).

## Iteration 31 (Phase 35: Auto-captions + Weekly plan, June 2026)
Whisper→Claude caption pipeline (E2E s reálnou rečou OK), 7-day plan s dennou kotvou z Kolotoča (anchor knee OK), day-complete cez UI klik OK (done flag zapísaný), CC toggle zobrazuje kroky. Curl + screenshot verified. Video >24MB → too_large (bez titulkov, video funguje).

## Iteration 32 (Phase 36: Evening plan reminder + Pain diary, June 2026)
physio_reminder_sweep + swarm physio_coach (curl: 1 sent, dedup OK; push 401 v dev = expected, placeholder key). Pain diary POST/trends + report section 5 s bar grafom (PDF 200). PainLogger UI klik → reply + trend (screenshot OK). Validácia level 11 → 400.

## Iteration 33 (Phase 37: Pain curve in Carousel + voice pain logging, June 2026)
PainCurve v /healing (screenshot OK: stĺpce+trend+hint), agent.py pain intent (4/4 curl variants correct, žiadny false positive na bežnú otázku). pain_diary entries source:'voice'.

## Iteration 34 (Phase 38: Recovery pulse for family, June 2026)
/api/family/recovery-pulse (curl OK ako fam-token: pain_levels/trend/kolotoč/nálada) + fd-loved sekcia v Rodinnom pulze (screenshot E2E OK ako Lucka). Bez blízkych sa sekcia nerenderuje.

## Iteration 35 (Phase 39: One-tap encouragement + recovery milestones, June 2026)
fd-encourage E2E OK (Lucka→Jaroslav echo remote:true), milestone check curl OK (floor 4→3 → 🎉), voice path integruje míľnik do reply. ConfettiBurst RN Animated (native driver, bez novej závislosti).


## Iteration 36 (SENTIENT UX FORK — the human soul, June 2026)
NEW backend (routes/auth.py):
- PrefIn extended: birth_year (1900-2030), biometric_enabled (bool), wake_word_enabled (bool).
- PATCH /api/me/prefs now accepts these fields; birth_year outside 1900-2030 → 400.
- Verified curl (Bearer smoketok-fresh-2026):
  - PATCH {"birth_year":1958,"biometric_enabled":true,"wake_word_enabled":true} → 200 with fields persisted.
  - PATCH {"birth_year":1800} → 400.
  - POST /api/voice/tts {"voice":"onyx","language":"sk","speed":0.95} → 200 (11.9KB mp3 cached, key deterministic).
NEW frontend modules:
- src/voice.ts — unified Jarvis voice utility, default voice 'onyx' (deep human, Tony-Stark-Jarvis).
  Single module-level createAudioPlayer instance (no overlap), auto-cleans on stopSpeaking().
- src/age.ts — Bio-Timeline (Growth Engine): 5 stages infant/child/teen/adult/senior derived from birth_year.
  Helpers: stageFromUser(), suggestAngelMode(), jarvisToneFor().
- src/biometric-gate.tsx — full-screen FaceID/Fingerprint gate wrapping the app after login.
  Soft-fails on web + hardware-less devices. Re-locks on app background >60s.
  Warm voice greeting on first unlock ("Vitajte späť, {name}. Som Jarvis…") via onyx.
- src/wake-word.ts — Alexa-style "JARVIS" listener scaffold (metering-based; native only).
  Auto-pauses in app background. NOTE for founder: full 24/7 background wake-word requires a
  native build with Porcupine/Snowboy — will not fully work in Expo Go.
EXISTING files upgraded:
- app/_layout.tsx — wraps <Stack/> in <BiometricGate>.
- app/(tabs)/index.tsx — angel-toggle now includes 'SENIOR' label + gold glow when suggested.
  NEW testID hub-guardian-gold: prominent LinearGradient card under pillar grid, shows
  "ETAPA ŽIVOTA" chip when birth_year set, senior-adaptive copy.
  AngelHome auto-starts wake-word listener when wake_word_enabled=true (native only).
- app/(tabs)/profile.tsx — new SENTIENT UX section with testIDs:
  - prof-voice-preview (Onyx voice sample button)
  - prof-birth-year + prof-birth-year-save (Bio-Timeline)
  - prof-stage-label (auto-computed etapa)
  - prof-biometric switch (triggers LocalAuthentication.authenticateAsync before enabling)
  - prof-wake-word switch
- app/jarvis.tsx — MOOD_VOICE now always 'onyx' (speed modulates emotion). speak() delegates
  to src/voice.ts. Removed local playerRef (voice.ts owns the player).
- app/physio.tsx — speakText() delegates to jarvisSpeak with onyx (previously coral).
Screenshots verified: home shows SENIOR pill + Guardian Gold card with ETAPA ŽIVOTA: SENIOR (65+) after
birth_year=1958 seed. Profile Sentient UX section renders all four controls in Slovak.
NEEDS TESTING: all backend PrefIn field flows + TTS onyx roundtrip via testing_agent.

## Iteration 31 (SENTIENT UX FINALE — Zero-Friction & Voice Signatures, Feb 2026)
NEW backend:
- routes/auth.py PrefIn: onboarding_completed added.
- routes/health.py: _detect_birth_year() with 5 regex patterns (RČ, SK/CS/EN/DE DOB labels, ISO,
  loose "narodený"). ocr_document endpoint now returns birth_year_detected + birth_year_applied.
  Never overwrites an existing birth_year.
- routes/family.py: 4 new voice-signature endpoints (POST multipart, GET meta, GET /file streamed,
  DELETE). 3MB size limit, upsert-by-user_id, storage under {APP}/voice-signatures/{user_id}.
NEW frontend:
- src/onboarding-tour.tsx: 30-second Sovereign Tour, Onyx-narrated, auto-runs when
  onboarding_completed=false, sets flag on finish/skip.
- app/voice-signature.tsx: recorder screen (5s countdown, mic permission handling, upload,
  delete, Onyx confirmation "Ďakujem, {label}. Váš hlasový podpis je zaznamenaný.").
UPGRADED frontend:
- app/(tabs)/index.tsx: greeting fallback name "Guardian Angel" (was "Guardian").
- app/(tabs)/family.tsx: new fs-voice-signature tile (Hlasový podpis).
- app/(tabs)/vault.tsx: OCR pipeline now shows "✨ Bio-Timeline aktualizovaná: {stage}" toast +
  Jarvis Onyx confirmation + auto-refreshes user (birth_year applied silently).
- app/voice-echoes.tsx: Jarvis (Onyx) now announces sender name before playback:
  "Máte novú správu od {label}." 2.2s pause then real audio.
- src/biometric-gate.tsx: greeting text updated to "Vitajte doma, {name}. Som váš Jarvis."
  and fallback to "Guardian Angel" (never uses raw email).
- app/_layout.tsx: OnboardingTour wired inside BiometricGate wrapper.
Backend tests: 17/17 GREEN (test_iter31_sentient_finale.py) — onboarding flag, OCR autofill,
voice-signature CRUD, idempotency, edge cases.
Frontend screenshots verified: Sovereign Tour renders card 1/4 with pillar icon + progress dots;
Voice-Signature screen renders label, big golden mic button, and Jarvis intro line.

## Iteration 32 (SOVEREIGN EXTENSIONS — Voice Circle, OCR Onboarding, Achievements, Feb 2026)
NEW backend:
- routes/achievements.py: /api/achievements returns 8 badges (sovereign_onboarded, bio_timeline_set,
  biometric_gate, voice_print_first, angel_first_contact, physio_first_series, healing_loop_first,
  vault_first_doc) with progress %. Field-based badges (birth_year, onboarding_completed,
  biometric_enabled) + collection-based (voice_signatures, guardians, physio_videos, healing_events,
  documents). Idempotent, no new collections.
- routes/family.py: /api/family/voice-signature/circle returns full family voice-circle
  (guardian links both directions + self). Members carry has_signature + label so the frontend
  can render "Tomáš ✓" / "Mama ⌛" tiles.
- routes/health.py: cached OCR branch now returns birth_year_applied=false (consistency).
NEW frontend:
- app/achievements.tsx: full-screen badge grid — zlatý hero baner s progress bar, unlocked
  section (gold gradient badges), locked section (dashed grey with red lock dot). Tap any
  badge → Jarvis onyx voice reads the title/hint.
- app/(tabs)/index.tsx: home nav now has home-achievements chip (🏆 5/8) — one-tap into
  the Sovereign badges screen. Auto-refreshes when user prefs change.
UPGRADED frontend:
- app/voice-signature.tsx: below the recorder, a Family Voice Circle panel lists every
  circle member (self first) with mic-on/off avatar + status: "Tomáš — nahrané" / "Mama — ešte
  nenahral svoj hlas". Counter chip in header (0/2, 3/3 …).
- app/(tabs)/vault.tsx: first-visit banner "NASKENUJTE OBČIANKU · Jarvis vyplní Vek, Bio-Timeline
  a poistkové polia" (only shows when docs.length==0 && birth_year==null). Gold linear card,
  one-tap → document picker.
Backend tests: 13/13 GREEN (test_iter32_sovereign_extensions.py). Overall Sentient UX suite:
30 (iter30) + 17 (iter31) + 13 (iter32) = 60 tests green.
Frontend screenshots verified: home 🏆 5/8 chip, Achievements hero + grid, Voice Circle tiles.

## Iteration 33 (SOVEREIGN POLISH — Invite · Confetti · Streaks, Feb 2026)
NEW backend:
- routes/achievements.py: /api/streaks/physio — 60-day rolling window computes current
  streak (with grace day rule) + best + tier (0..3 flame). Handles naive Motor-stripped
  datetimes safely (assumes UTC).
- routes/health.py: OCR cache branch now returns birth_year_applied:false for shape parity.
NEW frontend:
- src/ui/ConfettiBurst.tsx: 42-piece gold particle system, ~2.4s cascade,
  100% react-native-reanimated (no new deps). Works on native and web.
- src/invite.ts: inviteFamilyToRecord() + inviteFamilyViaSMS() — native Share sheet
  with Slovak pre-filled message + deep link to /voice-signature. Web falls back to
  navigator.share or mailto.
UPGRADED frontend:
- app/(tabs)/index.tsx: home-streak chip (🔥 X) next to home-achievements (🏆 X/Y).
  Tier 2+ turns solid gold with brand glow; opens /physio on tap.
- app/achievements.tsx: on load, diffs current unlocked keys vs. AsyncStorage
  ga.achievements.seen.v1 → for a fresh badge shows a gold LinearGradient "ČERSTVO
  ODOMKNUTÉ" banner + ConfettiBurst overlay + Onyx voice "{Title}. Odomknuté.".
  Prevents replay by persisting the current key set.
- app/voice-signature.tsx: per-member POZVAŤ button in Family Voice Circle for members
  without a signature; a large POZVAŤ ĎALŠIEHO ČLENA RODINY primary CTA below the list.
  Both use the native Share sheet with pre-composed Slovak invite + /voice-signature URL.
Backend tests: 12/12 GREEN (test_iter33_streaks_polish.py). Overall Sentient UX: 72 tests.
Frontend screenshots verified: home shows 🔥4 + 🏆6/8; achievements shows fresh-unlock
banner + gold confetti cascade + progress 75%; voice-signature shows per-member POZVAŤ
buttons + bulk invite CTA.

## Iteration 34 (1% PERFECTION FINALE — 6 features, Feb 2026)
NEW backend routes (all registered in server.py):
- routes/pantry.py — Survival Pantry (list/counts/CRUD/alerts/scan). 9 item categories,
  urgency tiers (expired/critical/soon/healthy/fresh/unknown), OCR expiry regex (SK/EN/DE
  BB/MHD/Spotreba do/Best before). Reuses vault OCR pipeline via extract_doc_text.
- routes/impact.py — /impact/dashboard aggregates physio/pain/scam/wellness/vitals/documents,
  computes people_helped (capped 120k), research_hours, tokens_earned, 4-week timeline,
  top_thread with Slovak Jarvis narration line. Safe-count helper avoids hasattr trap.
- routes/silent_witness.py — session open/close + chunked audio upload (5MB cap), auto push
  to Inner Circle when session starts. Stored under {APP}/silent-witness/{uid}/{sid}/NNNN.
- routes/family.py extended — /angel/pulse (send, guardian-link enforced, self-pulse blocked),
  /angel/pulse/inbox, /angel/pulse/{id}/felt (acks sender). Push carries pattern+bpm.
- routes/achievements.py extended — /streaks/freeze (weekly cap, phantom physio_video record
  keeps the streak alive), /streaks/blazing/celebrated (marks 30-day ceremony as seen).
  Streak GET now also returns freeze_available + blazing_celebrated flags.

NEW frontend screens:
- app/pantry.tsx — full pantry manager: color-coded urgency chips, Jarvis-narrated top alert
  line, scan CTA via document picker → OCR pipeline, manual add modal, 9 categories.
- app/impact.tsx — gold hero (people_helped), 3 KPIs, top research thread (Onyx-narrated
  on tap), 4-week bar chart, category breakdown grid, Slovak CTA line.
- app/silent-witness.tsx — big radio button, rolling 20s chunk uploads to Vault, live counter
  (elapsed + chunks uploaded), history list, mic permission handling.
- app/angel-pulse.tsx — inbox of received pulses + send composer (target chips, 4 patterns,
  40-120 bpm). Playing a pulse triggers a full-screen animated heart + haptic pattern via
  src/haptic-heartbeat.ts + auto-ack after 8s.

NEW frontend src/:
- src/haptic-heartbeat.ts — 4 patterns (heartbeat/soft/strong/sos) using expo-haptics.
  Returns a stop() function; caps at 15s to avoid runaway vibration.
- src/blazing-ceremony.tsx — full-screen ceremonial overlay: pulsing gold orb + Onyx
  narration "Tridsať dní. Sovereign Blazing Guardian." + PRIJÍMAM CTU button that
  POSTs /streaks/blazing/celebrated.

UPGRADED frontend:
- app/(tabs)/index.tsx — streak chip long-press protects the day via /streaks/freeze; a small
  ❄ snowflake dot on the chip indicates freeze_available. Auto-mounts <BlazingCeremony/>
  when current>=30 and blazing_celebrated=false. Slovak freeze toast.
- app/(tabs)/family.tsx — new tiles fs-angel-pulse, fs-silent-witness.
- app/(tabs)/legacy.tsx — new tiles lw-impact, lw-pantry.

Backend tests: 25/25 GREEN (test_iter34_perfection.py). Total Sentient UX suite: 97 tests
(iter30 30 + iter31 17 + iter32 13 + iter33 12 + iter34 25).
Screenshots verified: pantry list + scan CTA, impact hero + timeline, home nav chips.
Code review note applied: replaced hasattr(motor_db, name) (always True) with a safe try/except
_safe_count helper in impact.py.

## Iteration 36 (Phase 45+46 GPS & Anonymity, Jun 2026)
NEW backend (all curl-verifiable, no key required):
- routes/geo.py rebuilt: DEFAULT_GEO=Bratislava/SK (no more static Prague). NEW endpoints:
  * POST /api/geo/ip-locate — IP fallback via free ip-api.com (X-Forwarded-For / x-real-ip),
    24h in-memory IP cache. Private IPs → ip-fallback with default city + prompt manual pick.
  * POST /api/geo/set-city — manual city override from CITIES index (400 on unsupported).
  * POST /api/geo/locate now also returns `language_suggestion` when country changes AND
    travel_mode is off (never auto-switches without consent).
- backend/core.py NEW: `apply_watermark(text)` idempotent EU AI Act Art. 50 watermark
  ("— AI Content · Sovereign Protocol"), `did_hash(user_id)` SHA-256 log helper.
- routes/agent.py: watermark applied to chat/pain/briefing/analyze; NEW _edge_get/set
  in-memory hot-cache (600s TTL) fast-path for /agent/briefing (target p95 <500ms).

NEW frontend:
- src/GuardianEye.tsx — always-visible camera FAB, opens /lens with haptic. Mounted in
  PillarHub → appears on every hub (health/family/legacy/hunter). testID `{testID}-eye`.
- src/CityPicker.tsx — bottom-sheet city selector + LanguageSuggestionBanner component.
- src/voice.ts — strips watermark suffix before TTS (Onyx never reads watermark aloud).
- app/(tabs)/profile.tsx — CESTOVNÝ REŽIM upgraded: tryIpFallback() when GPS denied,
  `prof-geo-ip` + `prof-geo-manual` buttons, LanguageSuggestionBanner shown on
  country change even without travel-mode.

ANONYMITY (Phase 45): all visible occurrences of Tomáš/Lucka/Jaroslav removed from
frontend (onboarding, monolith, voice-signature, voice-echoes, healthcare-proxy, dignity,
panic-gesture) and backend routes (demo.py family_pulse, agent.py briefing example).
test_phase19_grand_finale.py assert updated to "Strážca". test_iter24_human_first.py
default-city assert accepts Bratislava.

NEEDS TESTING (backend + frontend):
- /api/geo/ip-locate happy path (private IP → default), /geo/set-city (200 valid, 400 invalid),
  /geo/locate language_suggestion when country changes without travel_mode.
- /agent/briefing hot cache (2nd request faster than 1st, force=true bypasses cache).
- Every Jarvis response (chat, briefing, analyze, pain) contains "AI Content · Sovereign Protocol".
- Frontend: Guardian Eye FAB visible on all 4 pillar hubs → tap navigates to /lens.
  Profile: CityPicker opens, "Bratislava" pick works; IP button triggers /geo/ip-locate.

Auth for tests: user smoketest-user-1, Bearer smoketok-fresh-2026 (as before).

## Iteration 37 (Phase 47 GUARDIAN EYE MULTI-MODEL + Contacts/Calendar + GPS Bearing, Feb 2026)
NEW backend (all curl-verifiable, no key required for /lens/models):
- routes/lens.py: multi-model Guardian Eye vision analysis. VISION_MODELS = {gpt: openai/gpt-5.4, claude: anthropic/claude-sonnet-5, gemini: gemini/gemini-3.1-pro-preview}.
  * GET /api/lens/models — returns model chip list + default. NO AUTH REQUIRED.
  * POST /api/lens/analyze now accepts optional `model` form field (gpt|claude|gemini, default=gpt) + `pillar` (health|hunter|legacy).
    Returns scan doc with `model` field + summary watermarked with EU AI Act.
  * POST /api/lens/analyze-consensus — runs all 3 vision providers in parallel via asyncio.gather,
    merges by majority-vote on `kind`, longest coherent `summary_sk`, dedup warnings + actions.
    Returns scan doc with `consensus: {agreement_pct, kind_votes, per_model}` block.
  * POST /api/lens/{scan_id}/to-jarvis — synthesises a Guardian Eye brief into an agent_chat
    UserMessage, invokes agent_chat() directly (preserves memory + XP), returns Jarvis reply.
    404 on unknown scan_id/user mismatch. Updates lens_scans with jarvis_sent_at + jarvis_reply.
- routes/compass.py: SOVEREIGN COMPASS BEARING — GPS wiring for Waitlist Hunter proximity + Bio-Beacon direction.
  * POST /api/compass/bearing {lat,lng} → distance_km + bearing_deg + 8-way direction (S/SV/V/JV/J/JZ/Z/SZ)
    to (a) supported safe-cities (top-5 nearest), (b) active guardian bio-beacons, (c) waitlist clinics
    in known cities (top-8 nearest). 400 on out-of-range coords.

NEW frontend:
- app/guardian-circle-sync.tsx — Guardian Circle local-first contacts screen:
  * expo-contacts with contextual permission per handle_permissions_contract (canAskAgain-aware,
    Open Settings fallback via Linking).
  * SecureStore-persisted PickedContact ring, max 8, DID = sha-256(name|phone). Search + add/remove.
  * Zero cloud sync — never leaves device.
- app/calendar-sync.tsx — Native Calendar bridge (read + write):
  * expo-calendar with contextual permission. Creates a dedicated "Guardian Angel" calendar
    (LOCAL source on Android, default source on iOS). Cached calendar id in AsyncStorage.
  * Reads today's meds from /api/meds/reminders + booked exams from /api/waitlist, builds Items,
    lets user add/remove each into the native calendar with 10-min alarm.
  * Bulk "SYNCHRONIZOVAŤ VŠETKY" + 30-day preview of Guardian Angel calendar events.
- app/lens.tsx: MODEL SELECTOR chips (GPT-5.4 · GEMINI 3.1 · CLAUDE 5 · KONSENZUS ×3) +
  "POSLAŤ JARVISOVI" action + Jarvis reply block with "OTVORIŤ ROZHOVOR →". Consensus badge
  shows agreement_pct. `apiUpload` extras pass `model` form field.
- app/compass.tsx: SOVEREIGN COMPASS section shows nearest safe city + active beacons +
  waitlist proximity with direction + km. Auto-fetched via getLoc() on mount + refresh button.
- app/(tabs)/family.tsx: two new tiles in RODINNÁ SYNCHRONIZÁCIA — fs-guardian-circle,
  fs-calendar-sync. Route to the new screens.
- app.json: expo-contacts + expo-calendar plugins with iOS usage descriptions (Contacts,
  Calendars, CalendarsFullAccess, Reminders) + Android permissions (READ_CONTACTS,
  READ_CALENDAR, WRITE_CALENDAR). Pending native rebuild.

NEEDS TESTING (backend only for testing_agent — frontend contacts/calendar require native build):
- GET /api/lens/models → 200 with 4 entries + default=gpt.
- POST /api/lens/analyze with model=gpt|claude|gemini + a small JPEG → 200 with `model` field
  and watermarked summary_sk. Invalid model → 400.
- POST /api/lens/analyze-consensus with JPEG → 200 with `consensus.agreement_pct` 0-100 and
  `consensus.per_model` for all 3 keys.
- POST /api/lens/{scan_id}/to-jarvis after an analyze → 200 with jarvis.reply present + watermark.
  Unknown scan_id → 404.
- POST /api/compass/bearing {lat:48.15,lng:17.10} → 200 with nearest_safe_city + safe_cities[5]
  + beacons[] + waitlist_proximity[]. Bad coords → 400.

Auth for tests: user smoketest-user-1, Bearer smoketok-fresh-2026 (as before).

## Iteration 38 (Phase 48 COGNITIVE TRIAGE — Crisis HUD, Feb 2026)
NEW backend routes/triage.py (registered in server.py):
- GET /api/triage/state — poll-safe crisis snapshot. Classifies bioscan_results (last 15 min)
  + triage_voice tremor into {calm|elevated|crisis}. Thresholds: HR>=120 or SpO2<92 or
  voice_tremor>=0.75 → crisis. HR>=100 or stress_level=='high' → elevated. Returns
  auto_open_hud (bool), instructions[] (5-step SK/CS/EN survival guide), emergency_numbers,
  reasons[], latest_vitals.
- POST /api/triage/trigger {reason?,hr?,spo2?,voice_tremor?} — manually raise HUD (persists
  manual_trigger flag in triage_state collection). Best-effort silent push to Guardian Circle
  (guardians collection). Bus event triage.crisis.
- POST /api/triage/dismiss — puts user in 15-min cooldown (manual_dismiss_until in triage_state);
  during cooldown /triage/state returns crisis_level=calm + source=dismissed regardless of vitals.
- POST /api/triage/voice {tremor_score,sample_ms} — ingest voice tremor 0..1 into triage_voice
  collection. 400 out-of-range. Returns state.
- GET /api/triage/instructions?language=sk|cs|en — localized 5-step instructions + emergency
  numbers + watermarked header.

NEW frontend src/CrisisHUD.tsx:
- Full-screen high-contrast overlay (obsidian bg + gold accents). Mounted globally in
  _layout.tsx inside BiometricGate. Polls /triage/state every 30s and on AppState 'active'.
- Auto-visible when auto_open_hud=true. Two giant buttons: hud-call (dials 112 via
  Linking.openURL('tel:112')) + hud-instr (opens instructions sheet with hud-num-EU etc).
- hud-dismiss calls /triage/dismiss and sets 15-min cooldown. Warning haptic on open.
- No dependency on frontend polling of bioscans — bioscan_measure already inserts into
  bioscan_results collection, /triage/state autoscans latest.

NEEDS TESTING (backend):
- GET /api/triage/state without prior signals → 200 {crisis_level:'calm', auto_open_hud:false}.
- POST /api/triage/trigger {reason:'test'} → 200 {crisis_level:'crisis', auto_open_hud:true,
  source:'manual', instructions[5], emergency_numbers}.
- POST /api/triage/dismiss → 200 {ok:true, cooldown_until:<iso>}; subsequent /triage/state
  returns source:'dismissed', auto_open_hud:false for ~15 minutes.
- POST /api/triage/voice {tremor_score:0.9} → 200 (may be 'dismissed' if cooldown active).
- POST /api/triage/voice {tremor_score:1.5} → 400.
- GET /api/triage/instructions?language=sk → SK 5 steps. ?language=cs → CS 5 steps.
  ?language=en → EN 5 steps.
- Regression: existing bioscan_measure still 200 with vitals; agent chat/briefing still
  watermarked; lens/models still returns 4 entries.

Auth for tests: user smoketest-user-1, Bearer smoketok-fresh-2026.

## Iteration 39 (Phase 49 TIMELINE MERGE — Auth Repair + Jarvis Ultra, Jun 2026)
FIXED P0: Expo bundler crash was caused by corrupted /root/.expo/state.json (empty JSON) — repaired.
login.tsx code was intact. Sovereign Bypass verified E2E in preview.

NEW backend (routes/agent.py):
- POST /api/agent/search {query} — JARVIS ULTRA Sonar. Perplexity sonar-reasoning-pro
  (medicine+EU system prompt, strips <think>, citations[]). PERPLEXITY_API_KEY in backend/.env
  is BLANK → gracefully degrades to gpt-5.4 offline knowledge, returns degraded:true (EXPECTED).
  Awards 6 XP. Stores convo with source:'sonar'.
- POST /api/agent/imagine {prompt} — GPT Image 1 via Emergent LLM key, returns image_base64
  (PNG, ~2.6MB b64). Can take up to 60s — use long timeouts. Awards 8 XP.

NEW frontend (app/jarvis.tsx):
- Mode chips above input: jv-mode-chat / jv-mode-sonar / jv-mode-imagine.
- SONAR mode → /agent/search; renders citations (jv-cite-{i}-{j}, tappable) + degraded notice.
- OBRAZ mode → /agent/imagine; renders generated image bubble (expo-image, base64 data URI).
- CHAT mode unchanged (regression-sensitive).

FIXED (full 661-test suite → all green):
- routes/pantry.py: 'filter' keywords now precede 'water' ("filtre na vodu" → filter).
- routes/swarm.py stability_audit: to_list(10) capped 13 agents → to_list(len(AGENTS)+10).
- tests updated to current API contracts: test_iter33 streaks empty-state subset,
  test_phase18 card payment now 400→/billing/checkout (Stripe live since iter25).
- DB cleanup: test users named 'Smoke*' renamed to 'Guardian Test' (tokens unchanged).

Auth for FE testing: login screen → founder-bypass-btn (POST /api/auth/dev-bypass,
guardianangel.core@proton.me). Backend tests: Bearer smoketok-fresh-2026.

## Iteration 40 (Phase 49.1 — Vault Art Gallery + Voice Sonar, Jun 2026)
BACKEND (routes/agent.py /agent/imagine enhanced):
- Generated PNG now also uploaded to Emergent Object Storage at
  guardian-health-angel/jarvis_art/{uid}/{doc_id}.png and inserted into db.documents with
  source:'jarvis_art', prompt, title '🎨 {prompt}'. Response adds doc_id + saved_to_vault:true.
- OpenAI safety rejections now map to 400 with Slovak-friendly message (was generic 502).
- VERIFIED via curl: imagine → saved_to_vault:true, GET /vault/documents lists art doc,
  GET /vault/documents/{id}/file returns 200 PNG (1.9MB).

FRONTEND:
- app/jarvis.tsx: imagine bubble shows chip 'ULOŽENÉ V TREZORE · OTVORIŤ GALÉRIU'
  (testID jv-vault-open-{i}) → routes to /(tabs)/vault. Voice Sonar: when Orb voice input is
  used in sonar mode, reply is spoken in Onyx + appends '...Našiel som N overených zdrojov'.
  Imagine via voice also announces vault save.
- src/voice.ts speak(): strips markdown (**, #, links, URLs, code fences) before TTS so Onyx
  never reads 'asterisk asterisk' — applies to ALL TTS calls (regression-sensitive but safe).
- app/(tabs)/vault.tsx: new GALÉRIA OBRAZOV · JARVIS section (gold-bordered) above documents.
  3-col thumbnail grid (art-thumb-{doc_id}), tap → full-screen preview modal (existing
  doc-preview-image), delete via art-del-{doc_id}. Art docs excluded from document list below.
- VERIFIED via screenshots: gallery grid renders with thumbnail, preview modal opens full-screen.

Existing art doc for tests: doc_id f1b50e9e705042fe92005b801de2cfc7 (founder user_ac98119726d0).

## Iteration 41 (Phase 49.2 — Sonar História, Jun 2026)
BACKEND (routes/agent.py):
- /agent/search agent-row now also stores query + degraded fields.
- GET /api/agent/search/history?limit=30 → {items:[{conv_id,query,reply,citations,degraded,at}], total}.
  Legacy rows (no query field) pair with the user message at the identical timestamp.
- DELETE /api/agent/search/history/{conv_id} → deletes agent row + paired user question. 404 unknown.
- SELF-TESTED via curl: list OK (5 items), delete OK (total decreased), unknown id → 404.

FRONTEND (app/jarvis.tsx):
- In SONAR mode: collapsible '🌐 SONAR HISTÓRIA (n)' section (jv-hist-toggle) under the input.
  Rows jv-hist-{conv_id}: query + date + source count (Slovak declension). Tap (jv-hist-open-*) →
  re-injects question+answer+citations into the chat. Trash (jv-hist-del-*) deletes.
- History auto-refreshes when entering sonar mode and after each new sonar search.
- SELF-TESTED via screenshot: toggle visible, entry tap re-injected 'Aké je počasie v Bratislave?' Q&A.

## Iteration 42 (Phase 50 — CRITICAL UX BUG FIXES, Jun 2026)
BUG 1 (settings gear everywhere): Home + PillarHub (health/family/legacy) already had gear.
ADDED: jarvis.tsx header (testID jv-settings), vault.tsx header (vault-settings),
family-contacts.tsx (fc-settings). All route to /(tabs)/profile.

BUG 2 (Jarvis streaming): NEW POST /api/agent/chat/stream (SSE). Refactored shared
_chat_system() prompt builder (json_mode flag) — /agent/chat behavior unchanged (regression-
sensitive: CHAT_JSON_RULE path). Stream: TextDelta chunks as `data:{"t":...}`, final
`data:{"done":true,mood,xp_gained,level,...}`. Pain-diary intent reuses agent_chat, streamed
as one chunk. Frontend jarvis.tsx: expo/fetch ReadableStream reader, TypingDots (jv-typing,
3 breathing dots) mounts instantly on send, streaming bubble updates per chunk, graceful
fallback to classic /agent/chat on transport error. VERIFIED via curl: token-by-token SSE.

BUG 3 (phone icon → QR Profil): Angel Mode bottom trio: angel-family (call icon → own
emergency card) REPLACED by angel-qr-profile (qr-code-outline, label 'QR PROFIL'
→ /emergency-qr). Labels added: SOS / QR PROFIL / DOKTOR. callFamily removed.

BUG 4 (family contacts): NEW backend routes/family_contacts.py (registered in server.py):
POST/GET /api/family-contacts, DELETE /api/family-contacts/{id},
POST /api/family-contacts/{id}/sos. Phones encrypted at rest (Fernet, CONTACTS_ENC_KEY in
backend/.env). Relations: partner/rodic/surodenec/dieta/priatel/lekar/ine. Max 20. Phone
regex validated. VERIFIED via curl + mongo (ciphertext at rest, decrypted in API).
NEW screen app/family-contacts.tsx: fc-add button → modal (fc-name, fc-phone, fc-rel-{id},
fc-save, fc-cancel), cards fc-card-{id} with fc-call- (tel:), fc-sos- (POST sos + prefilled
SMS), fc-del- → inline confirm fc-del-yes-/fc-del-no-. LayoutAnimation on add/remove.
family.tsx hub: prominent gold 'fs-contacts' hero button '+ PRIDAŤ ČLENA RODINY' under Angel hero.
Existing test contact: Mária +421 900 123 456 (rodic), contact_id d36d87633c0b4b9c9f4fa9eda888d378 (founder).

BUG 5 (duplicates removed on Home): header 'home-jarvis' sparkles (dup of Home Orb) and
header 'angel-toggle' SENIOR chip (dup of hub-guardian-gold tile) REMOVED. Audited
health/family/legacy hubs — no same-screen duplicates found. No TODO/Lorem placeholders exist.

Auth: founder-bypass-btn / POST /api/auth/dev-bypass guardianangel.core@proton.me.

## Iteration 43 (Phase 50.1 — Twilio SOS SMS ready + GPS in SOS, Jun 2026)
- routes/family_contacts.py /sos: when TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN/TWILIO_FROM_NUMBER
  in backend/.env are set (currently BLANK — user will paste keys later), a REAL SMS is sent
  via Twilio (twilio lib, run_in_threadpool). Response adds sms_sent/channel/sms_error.
  Fallback (no keys): channel:'device', frontend opens prefilled SMS composer (unchanged UX).
- SOS sms_body now includes Google Maps link from user.geo.lat/lng
  ('Moja poloha: https://maps.google.com/?q=lat,lng'). VERIFIED via curl.
- frontend family-contacts.tsx: opens device composer ONLY when sms_sent:false.
- twilio added to requirements.txt. Perplexity key still pending from user (sonar degraded).

## Iteration 44 (Phase 51 — KARTA ŽIVOTA, Jun 2026)
User directive: reorganize existing modules only — Life Card = core of the app.
BACKEND (routes/health.py — replaced LIFE-HEALTH CALENDAR section):
- calendar_events categories extended: vaccine|disease|surgery|injury|exam ('history' alias→disease
  on POST; legacy manual 'history' rows lazily migrated to 'disease' on first timeline GET;
  system 'history' rows from vault/billing kept, displayed as DOKUMENT).
- GET /calendar/timeline adds counts{} per category; filter supports all 5 + history.
- NEW GET /api/lifecard → {full_name, birth_date, birth_year, blood_type, age, counts,
  predictions (cached), predictions_at, today}. full_name/blood_type come from
  emergency_profiles (shared with Emergency QR); birth_date stored on users (+birth_year sync).
- NEW PUT /api/lifecard {full_name?, birth_date? (YYYY-MM-DD 1900..today), blood_type? (A+..0-)}.
- NEW POST /api/lifecard/predictions — gpt-5.4 JSON: max 4 {title, category vaccine|exam,
  suggested_date>today ≤24mo, reason SK}; cached in db.lifecard_predictions; +6 XP. ~10-20 s.
- NEW POST /api/lifecard/predictions/accept {title,category,date,reason} → calendar_events
  (source 'jarvis', notes 'Jarvis predikcia · …') + $pull from cached predictions.
BACKEND (routes/agent.py):
- Voice Life-Card intent: LIFECARD_TRIGGER regex (doktor/očkovan/operáci/úraz/choroba/…)
  → _classify_lifecard (gpt-5.4 JSON {is_record, category, title, date, note}; resolves
  'včera' etc.) → insert calendar_events (source 'voice') → deterministic SK reply
  'Zapísal som do Karty života: …' + watermark + 5 XP; response has lifecard_logged{}.
  Questions/advice → is_record=false → falls through to normal chat (VERIFIED).
  Stream endpoint: trigger check added next to pain check → one-chunk SSE with
  lifecard_logged in done-meta (VERIFIED via curl, 'Včera ma zaočkovali proti tetanu'
  → vaccine, date today-1).
FRONTEND:
- app/health-timeline.tsx rebuilt as KARTA ŽIVOTA (same Obsidian/gold design language):
  identity hero (meno/dátum narodenia SK format/vek/krvná skupina, edit inline via lc-edit →
  lc-name + lc-birth DateField + lc-blood-{type} chips + lc-save-card), voice hint row →
  /jarvis, quick-add '+' with 5 category chips + popis (lc-notes), PREDIKCIE·JARVIS box
  (lc-predict → POST predictions; lc-accept-{i} → accept + native calendar via
  addToGuardianCalendar), filter chips with counts, timeline rows (5 colors + gray DOKUMENT;
  source badges 🎙 JARVIS / ✨ PREDIKCIA).
- NEW src/native-calendar.ts: ensureGuardianCalendar + addToGuardianCalendar (permission
  contract: contextual ask, canAskAgain-aware, web no-op). calendar-sync.tsx refactored to
  import it (local copy removed, behavior unchanged).
- app/(tabs)/health.tsx: gold hero hh-lifecard-hero 'KARTA ŽIVOTA' on top (PillarHub hero
  prop); duplicate hh-timeline tile removed; vault-choice label renamed to 'Karta života'.
SELF-TESTED via curl: lifecard GET/PUT, add surgery, invalid category 400, counts,
voice log (kiahne→disease today), question not logged, predictions (2 SK suggestions),
accept (source jarvis + pulled from cache), SSE stream intent. Screenshots: hub hero +
full Life Card screen render correctly.
Auth: founder-bypass (guardianangel.core@proton.me). Backend tests: Bearer smoketok-fresh-2026.

## Iteration 45 (Phase 51.1 — Life Card Extensions, Jun 2026)
4 features on top of Karta života:
1) OCR RODNÉHO LISTU — POST /api/lifecard/ocr (multipart file, max 15MB) → gpt-5.4 vision
   returns {found, full_name, birth_date (validated 1900..today), blood_type (A+..0- or null), ai:true}.
   Frontend: in identity edit box two buttons lc-ocr-cam (camera, permission-contract with
   canAskAgain + lc-ocr-settings Open Settings when blocked) and lc-ocr-pick (gallery) →
   apiUpload → PREFILLS lc-name/lc-birth/lc-blood (user must press ULOŽIŤ ÚDAJE to save);
   lc-ocr-msg shows result. VERIFIED via curl with synthetic rodný list JPG (PIL) →
   found:true, Jan Novak, 1980-05-14, blood null.
2) PDF KARTY ŽIVOTA — GET /api/lifecard/report.pdf (auth or ?token=) → fpdf via _make_pdf:
   identity block + 5 sections (OČKOVANIA/CHOROBY/OPERÁCIE/ÚRAZY/PREHLIADKY) with
   date·title·notes·booster. Frontend gold-outline button lc-pdf under identity card →
   sharePdf. VERIFIED 200 application/pdf 35KB.
3) RODINNÉ KARTY — GET /api/lifecard/family → members[] from db.guardians (BOTH directions,
   like voice_circle) with counts{vaccine,exam} + booster_soon (≤30d); GET
   /api/lifecard/family/{member_id}/timeline → ONLY vaccine+exam events (privacy) or 403 if
   not in circle. Frontend section lc-family under predictions: member rows lc-fam-{uid}
   (avatar initial, counts) → inline expand with events + privacy note; empty state
   lc-fam-empty links to /recovery-suite (where guardians are added). VERIFIED: user-1 sees
   user-2 ('Smoke Two', vaccine 1, booster_soon 1), reverse works, founder gets 403.
4) BOOSTER GUARD — new swarm agent booster_guard (interval 3600) → routes/health.py
   booster_guard_sweep(): vaccine events with booster_due within 30d (stage 30d) or 7d
   (stage 7d) → push + PROACTIVE Jarvis chat message (agent_conversations role:agent,
   mood:alert, source:booster_guard, watermarked) once per stage per event
   (flags booster_notified_30d/_7d on the event). VERIFIED: POST /api/swarm/run/booster_guard
   → actions:1 then actions:0; Jarvis msg present for user-2.
Test data left in DB: smoketest-user-2 has vaccine 'Tetanus TEST' (booster_due +20d,
booster_notified_30d:true) + booster_guard convo. Guardians link user-1↔user-2 pre-existing.
Founder account is CLEAN (identity reset, no test events).

## Iteration 46 (Phase 51.2 — Očkovací preukaz EÚ + Karta pre dieťa, Jun 2026)
1) OČKOVACÍ PREUKAZ EÚ:
- GET /api/lifecard/vaccine-pass (JSON: holder, birth_date, blood_type, did, child flag,
  vaccinations[], issued_at, did_signature SHA-256, languages[14]) and
  GET /api/lifecard/vaccine-pass.pdf (?child_id=, ?token=) → bilingual data block +
  vaccination list + 14-language statements (en sk cs de fr es it pl hu uk ru pt nl ro) +
  DID signature in footer. VERIFIED: 200 PDF 47KB, JSON holder/langs/sig ok.
- Frontend: lc-vaxpass button (airplane icon) next to lc-pdf under identity card; works for
  active child too (child_id query).
2) KARTA PRE DIEŤA:
- db.lifecard_children {child_id, user_id(parent), name, birth_date, blood_type, created_at}.
  CRUD: GET/POST /api/lifecard/children (max 10, birth 1900..today), PUT/DELETE
  /api/lifecard/children/{child_id} (DELETE cascades child calendar_events + predictions).
- calendar_events now carry child_id (None for adult). POST /calendar/events accepts
  child_id (404 if not owner's child); GET /calendar/timeline?child_id= scopes everything
  (events, counts, boosters); adult timeline EXCLUDES child rows ({"child_id": None} matches
  missing+null). Data hygiene: IPS/humanitarian/border vaccine queries (globalnet.py),
  compass boosters/vaccines, agent briefing exams all now filter child_id: None.
- Predictions child-aware: POST /lifecard/predictions body {child_id} → childhood
  immunization schedule rule in prompt (VERIFIED: hexa booster + MMR + pediater for
  4-year-old); accept accepts child_id; caches keyed {user_id, child_id}.
- Booster Guard includes child name: '⏰ Blíži sa preskočkovanie (dieťa Lukáš): …' VERIFIED.
- PDF report supports ?child_id= (identity from child doc, '(karta dieťaťa)' marker).
- Frontend /health-timeline: horizontal card switcher (lc-card-me, lc-card-{child_id},
  lc-add-child); child identity card (happy icon, KARTA DIEŤAŤA label); new-child form
  (VYTVORIŤ KARTU DIEŤAŤA via lc-save-card); child edit + delete with inline confirm
  (lc-del-child, lc-del-child-yes/no); quick-add/+ filters/predictions/PDF/vax-pass all
  child-scoped; voice hint + RODINNÉ KARTY section hidden on child cards.
SELF-TESTED via curl (smoketest-user-1): child CRUD, child vaccine add, child timeline
counts, adult excludes child, bad child 404, vaccine-pass JSON+PDF, child report PDF,
child predictions (paediatric), accept child, booster guard child msg, cascade delete.
Test child deleted; founder untouched. Frontend smoke: switcher + child form + both PDF
buttons render (screenshot).

## Iteration 47 (Phase 51.3 — Rastová krivka + Trendy zdravia + Karta zubára, Jun 2026)
1) RASTOVÁ KRIVKA (WHO percentily):
- db.growth_logs {log_id, user_id, child_id, date, height_cm, weight_kg}. Endpoints:
  POST /api/lifecard/children/{child_id}/growth (validates date, h 30-220, w 1-150, at least
  one), GET .../growth → logs with age_months + height_percentile (0-18y) +
  weight_percentile (0-10y only, WHO limit) + curves{height,weight} P3/P50/P97 points +
  sex_required flag, DELETE /api/lifecard/growth/{log_id}.
- WHO approx tables in health.py (WHO_HEIGHT normal z=(v-M)/SD, WHO_WEIGHT lognormal
  z=ln(v/M)/S, erf CDF). Sanity-verified: 36mo girl 95cm/14kg → P48.8/P52.2; 102cm → P97.2.
- children now have sex ('m'|'f'|'') — ChildIn/ChildUpdateIn validated; child delete cascades
  growth_logs too.
- NEW screen /child-growth?child_id= (app/child-growth.tsx): react-native-svg chart
  (P3 dashed gray, P50 dashed gold, P97 dashed gray, child polyline+dots green), toggle
  gr-m-height/gr-m-weight, add form gr-date/gr-height/gr-weight/gr-save, sex picker
  gr-sex-m/gr-sex-f shown when sex_required, log list with P-values + gr-del-{id}.
  Opened via lc-growth button on child card (only when child active).
2) TRENDY ZDRAVIA:
- GET /api/lifecard/trends[?child_id=] → years[{year, counts per 6 cats, total}].
- POST /api/lifecard/trends/summary {child_id?} → gpt-5.4 Slovak yearly trend summary
  (max 5 sentences + 1 recommendation) with AI watermark appended. VERIFIED.
- NEW screen /health-trends[?child_id=&name=] (app/health-trends.tsx): Jarvis summary box
  (tr-summarize/tr-summary), legend, stacked yearly bars (tr-year-{year}) + breakdown text.
  Opened via lc-trends button (both my card and child card, passes child params).
3) KARTA ZUBÁRA:
- 6th category 'dental' (ZUBÁR, cyan #64D2FF, MaterialCommunityIcons tooth-outline via
  CatIcon wrapper). Everywhere: validation, counts, filters, PDF section ZUBÁR, predictions
  (category vaccine|exam|dental), trends. calendar_events new optional field tooth (FDI č.,
  max 4 chars) — input lc-tooth shown when dental selected; timeline shows '· zub 36'.
- Voice intent: zubár/zubné/plomb/dentist triggers + classifier category dental. VERIFIED:
  'Včera som bol u zubára, dostal som plombu' → dental/Plomba/yesterday.
- KARTA ZUBÁRA box (lc-dental-card) on dental filter: history grouped by tooth number.
SELF-TESTED via curl: child with sex, growth add/percentiles/invalid 400s/list+curves,
dental+tooth event, dental filter+counts, trends, trends summary LLM, voice dental.
Test data cleaned (Nina TEST child cascade, dental events). Founder untouched.
Screenshots: Karta života with 3 buttons + TRENDY ZDRAVIA screen render correctly.
NOTE: smoketest-user-1 has ~123 exam events from previous suites (pollution, harmless).

## Iteration 55 (3 urgent bug fixes — SOS false trigger · Jarvis 502 · Briefing location, Jun 2026)
1) SOS NEVER auto-triggers from noise (frontend/src/acoustic.ts + app/(tabs)/index.tsx AngelHome):
- Loud noise (> -8 dBFS) now ONLY shows an in-place card testID noise-alert ("LOUD NOISE DETECTED — ARE YOU OK?")
  and records 5 s → POST /api/voice/sos-keyword (Whisper) → opens /fall-verify ONLY if an explicit keyword
  ("SOS", "help", "pomoc", …) is detected. Otherwise status text (noise-status) says nothing was sent; card
  auto-dismisses after 30 s. Buttons: noise-fine (dismiss) / noise-sos (HOLD 1.5 s → /fall-verify; tap = hint only).
- Angel Mode SOS button (angel-sos): tap shows "HOLD 1.5 S" hint; only onLongPress (1500 ms) opens /fall-verify.
- Backend: POST /api/voice/sos-keyword (lens.py) → {sos_detected, transcript}; logs kind=sos_keyword_check in acoustic_events.
  NOTE: Whisper needs the LLM key → currently 503/502 while budget is exhausted; keyword gate then returns sos=false (safe).
2) Jarvis 502 root cause = EMERGENT_LLM_KEY budget exceeded ("Budget has been exceeded… Max budget: 7.4"). Code fix:
  core.ai_http_error() → 503 JSON {"detail": "AI budget exhausted — the Universal LLM key needs a top-up (...)"} instead of
  502 (which Cloudflare replaced with an HTML "error code: 502" page). Applied to /agent/chat, /agent/chat/stream (SSE error
  payload), /agent/transcribe. Frontend src/api.ts errMsg() extracts detail; jarvis.tsx shows it in the err line.
3) Briefing location: geo.py geo_resolved()/ensure_geo(); DEFAULT_GEO (New York) is now treated as "unknown": _weather returns
  None when unresolved; GET /agent/briefing + GET /geo/context call ensure_geo (IP-locate via X-Forwarded-For) for never-located
  users; /geo/locate stores REAL GPS coords + reverse-geocoded city (BigDataCloud keyless) with nearest_city kept as label;
  weather uses timezone=auto and returns {city,country,source}. /geo/context returns resolved flag; home pin hidden if not.
  Frontend: guardian.tsx startup effect — GPS silently if permission already granted, else IP-locate for unresolved users;
  jarvis.tsx briefing card button jv-use-location (asks location permission contextually, IP fallback on web, then
  /agent/briefing?force=true). Weather text testID jv-weather.
Self-tested: /agent/chat → 503 with budget detail; /geo/locate 48.72,21.26 → Kosice (gps); /agent/briefing?force=true →
weather Kosice; fresh user + X-Forwarded-For 195.28.64.1 → Bratislava (ip). Founder geo reset to unset afterwards.

## Iteration 56 (Language switching fix · Guardian tier gate for Jarvis/Briefing · Guardian SOS Alert · Tour EN)
1) LANGUAGE SWITCH: new src/i18n-context.tsx (I18nProvider in app/_layout.tsx inside AuthProvider; useI18n() → {lang,t,setLang,rtl}).
   setLang flips lang instantly (optimistic) + PATCH /me/prefs + setUser; a pick on the LOGIN screen (lang-<code> chips) is stored
   (AsyncStorage ga.lang.pending.v1) and applied to the account right after sign-in. Screens converted: login.tsx, (tabs)/_layout.tsx
   tab titles, (tabs)/index.tsx (home + Angel home incl. SOS/noise card), (tabs)/profile.tsx (chips prof-lang-<code>, section headers,
   testID prof-lang-title), fall-verify.tsx, daily-brief.tsx. ~55 new keys in src/i18n.ts T (sk/cs/en/de) + CORE block for pl/hu/ru/es/fr/it/uk/zh/ja/ar.
   Backend /companion/greeting?language=xx localized (sk/cs/de/en) — Angel home greeting re-fetches on language change.
2) GUARDIAN TIER GATE (existing 4-tier system in routes/subscription.py: sovereign/guardian €29/sentinel/archangel): agent.py now calls
   require_tier(user,"guardian",…) on POST /api/agent/chat, /api/agent/chat/stream, /api/agent/transcribe and GET /api/agent/briefing →
   402 {"detail":"guardian_required: … requires the Guardian Plan (€29/mo or 50 GA-T) — upgrade to unlock, …"}. Founder/inner_circle = archangel
   (unlocked). Free (sovereign) users: jarvis.tsx shows Paywall tier="guardian" (testID jv-guardian-gate, title "GUARDIAN PLAN", message
   "Jarvis AI requires the Guardian Plan — upgrade to unlock…", buttons pw-trial / pw-upgrade → /subscription); briefing card hidden while locked.
3) GUARDIAN SOS ALERT: POST /api/sos/broadcast {lat,lng,source} (family_contacts.py) → texts every family contact (Twilio if configured,
   else channel "device"), pushes linked guardians (db.guardians), logs sos_events kind sos_broadcast; returns {contacts[], sms_sent, push_sent,
   maps_url, sms_body}. fall-verify.tsx: when the loop is CONFIRMED (countdown end / GET HELP NOW) → GPS (asks permission) → /sos/broadcast →
   'sent' screen lists contacts (sos-contact-<id>), map link (sos-maps), button sos-text-guardians opens device SMS composer pre-filled.
4) Sovereign Tour step 1 title → "MY HEALING" (src/onboarding-tour.tsx).
Self-tested: founder /sos/broadcast 200 (1 contact, maps_url ok); free user /agent/chat + /agent/briefing → 402 guardian_required;
UI: login lang-sk → SIGN IN → Angel home in Slovak; profile de/en switch instant.

## Iteration 57 (GA-T loyalty allocation wired to subscription · Guardian price €9)
- NO new token system: reused token.py (token_accounts, hash-chained token_ledger, treasury). New in token.py: SUBSCRIPTION_GAT
  {guardian:100, sentinel:300, archangel:1000}/30 days, loyalty bonus +10%/consecutive month (cap +50%),
  settle_subscription_allocations(uid) (idempotent per anchor+period_index, ledger kind "subscription_allocation", treasury→user),
  start_subscription_allocation(uid, prev) (keeps streak if previous paid period active/lapsed <7d), sweep_subscription_allocations()
  (every 6h in swarm_loop). ONLY fiat-paid plans qualify: tier_paid_with in card/iap/apple_iap/google_iap/family_pack — GA-T-paid and
  trial never (circular mint). NOTE: Apple/Google IAP (RevenueCat) is NOT integrated in the app — only Stripe card + GA-T exist; the hook
  is channel-agnostic (IAP just needs to set tier/tier_until/tier_paid_with="iap").
- Hooks: GET /api/token/wallet → settles + returns subscription_allocation {...}; GET /api/subscription → settles + gat_allocation +
  gat_monthly_by_tier; billing._activate_tier (Stripe paid) → start_subscription_allocation (first 100 GA-T instantly).
- Guardian price: €29 → €9 (GA-T 50 → 15; tier_guardian_30d 15, 365d 144; founder TIER_MIX, Paywall text, founder-toolkit updated).
- Frontend: token.tsx card testID tk-loyalty (tk-loyalty-status / tk-loyalty-credited / tk-loyalty-upgrade), ledger rows "LOYALTY";
  subscription.tsx line testID sb-loyalty; TIERS features mention the monthly GA-T.
- Self-test (backend/tests/manual_loyalty_check.py): free → not eligible; card guardian → +100 instantly; idempotent; anchor 65d ago →
  +110 +120 (bal 330, next 130 @ +30%); GA-T-paid → not eligible; ledger chain intact; guardian price 9 €/15 GA-T.
  Test user loyalty-test@example.com left as card-paid guardian (dev-bypass).

## Iteration 58 (Rename → "Archangel OS")
- Public app name "Guardian Health & Angel" / "Guardian Angel OS" → "Archangel OS" everywhere user-facing: app.json name/description (+ extra.appStoreSubtitle
  "Your sovereign health & safety companion"), login hero (testID app-title "ARCHANGEL" / "OS"), i18n app_name + tagline (14 langs → "Your sovereign
  health & safety companion."), home welcome title, profile credit, ToS/Privacy pages, launch.tsx, backend PDFs/receipts/IPS/QR card/SOS SMS body/
  Jarvis prompts/FastAPI title/root endpoint {"app":"Archangel OS"}, EMAIL_FROM_NAME="Archangel OS". Brand identity kept: "Guardian Angel Sovereign
  Foundation (DAO)" copyright, "ENTER AS GUARDIAN ANGEL (FOUNDER)", GA-T "GUARDIAN TOKEN", Guardian/Sentinel tiers, Guardian Gold, Guardian Lens.
- New branded splash image assets/images/splash-image.png (gold halo/wings mark + ARCHANGEL OS + subtitle, transparent bg; imageWidth 280).
- Smoke: GET /api/ → Archangel OS; login page title "Archangel OS", hero ARCHANGEL/OS, tagline shown, no "HEALTH & ANGEL".
- RevenueCat (previous request) is PAUSED: connection_state not connected — user must click "Connect RevenueCat" in the payments panel first.

## Iteration 59 (Disclaimer audit — consolidated legal disclaimer in 14 languages)
- New src/i18n-legal.ts: LEGAL[lang] with keys 'disclaimer.general' (consolidated text incl. personal-liability sentence), 'disclaimer.title',
  'disclaimer.card_title', 'disclaimer.medical_short', 'disclaimer.emergency_short', 'disclaimer.i_understand', 'disclaimer.read_terms', 'ai_label'
  for all 14 langs; t() falls back T → EXT → CORE → LEGAL → en.
- Placement: terms-of-service.tsx top box testID tos-disclaimer / tos-disclaimer-text (bold, replaces the old medical box); privacy-policy.tsx footer
  testID privacy-disclaimer-text; login.tsx registration consent → reg-disclaimer under the checkbox text. All switch instantly with lang chips.
- ToS body (EN) now also covers: AI Act Art. 50 label, medication reference-only, health data not a medical measurement, does not replace
  112/999/911, fall detection/Acoustic Guardian may fail, GA-T not financial instruments/legal tender, personal limitation of liability.
- First-launch dismissible card src/FirstLaunchDisclaimer.tsx (testID first-launch-disclaimer; buttons disclaimer-ok / disclaimer-terms) rendered on
  home (standard + Angel) once per device per LEGAL_VERSION (AsyncStorage ga.disclaimer.seen.2026-06.1).
- EU AI Act Art. 50: jarvis.tsx shows label "🤖 AI-generated content · EU AI Act Art. 50 · informational only" under every finished agent bubble
  (testID jv-ai-label-<i>) and under the Morning Briefing (jv-ai-label-briefing); server-side apply_watermark kept.
- Smoke: reg-disclaimer switches sk→en; first-launch card shows after founder login and dismisses.
- Iter 59 testing (iteration_58.json): 92% pass; HIGH bug fixed — streamed agent bubbles never left `streaming:true`, hiding the AI label.
  jarvis.tsx now flips the last bubble to streaming:false when the SSE finishes. Self-verified: 2 labels (briefing + reply) render.
- RevenueCat: status check → connection_state "disconnected" / project_state "oauth_pending" → BLOCKED until user clicks Connect RevenueCat.

## Iter 60 — RevenueCat IAP (Sept 2026)
- iteration_60.json: backend 11/11 (tests/test_iter60_iap_sync.py) + UI flows green. HIGH bug (ledger seq race → 500, double iap-sync POST) FIXED (retry-on-DuplicateKey in token._ledger_append; shared in-flight promise in src/iap-mirror.ts). Also fixed: success message unmount (sb-msg), Browser-Mode cancel code (numeric 1). Self-verified E2E: cancel silent, failed purchase → iap-error, valid purchase → sb-msg "+100 GA-T", tier GUARDIAN.
- Real store purchases need a native build — untestable here.

## Iter 61 — Perplexity live news + briefing
- iteration_61.json: backend 9/9 (tests/test_iter61_perplexity_news.py), UI green (news-live-badge LIVE, source links, jv-news rows). Post-test fixes: live-item tags now ≥4 chars (no "ai"/"rna" false Vault matches), swarm News Sentinel uses item specialty for auto-hunts, stale Czech general:en:SG cache purged (language rule enforced in prompt), 16 noise auto-hunts from live news removed. Verified founder feed: live:true, 4 personal + 5 general, English.

## Iter 62 — audit & fix
- Backend: tests/test_iter62_iap_tiers.py 6/6 + iter60 18/18 pass. Manual E2E in preview: all 6 EUR prices render from offerings, Sentinel simulated purchase → CURRENT TIER: SENTINEL + 300 GA-T.
- iteration_62.json: backend 17/17, UI green (4 tiers, Archangel simulated purchase → +1000 GA-T, rename verified). No blockers.

## Iter 63
- iteration_63.json: 7/8 → fixed POST /waitlist 422→402 via Depends gate; now 8/8. UI: paywalls on waitlist/magic-lens/jarvis for Sovereign, pw-upgrade → /subscription, no raw i18n keys, Slovak renders.

## Iter 64 (fork physio-lang-fix) — startup freeze fix
- iteration_64.json: intro/onboarding/second-launch/logged-in/slow-CDN all pass on web; static review: all startup async paths time-boxed. Expo Go path (CDN fonts) now unblocked by 3 s RootLayout timeout.

## Iter 77 (fork physio-lang-fix) — ChatGPT AI models + P0 security
- Backend pytest tests/test_iter77_models_security.py 15/15 (models catalog/select/gates, chat+stream report model, password_hash never returned,
  dev-bypass host gate (localhost spoof), login+tts 429, atomic spend/feature/transfer, addon GA-T, iap-sync whitelist).
- Pre-existing unrelated failures: test_password_auth register (missing tos fields), phase15 wallet earn-rule count / royalty-to-self, iter66 creator 403.
- Live verified: gpt-5.6-luna + gpt-5.6-terra reply through /agent/chat; Jarvis pill switches GPT-5.4 → GPT-5.6 Luna on web.

## Iter 79 — add-on RC subscriptions · helper reputation · SecureStore/remove-console/root detection
- pytest tests/test_iter79_addon_subs_reputation.py 5/5 + tests/test_iter79_light_backend.py 3/3; testing agent iteration_69.json all green (frontend store RC buttons, addon lifecycle via iap-sync, reputation badges, boot with babel.config.js, secure cache web fallback).
- Known: RC Test Store in-dialog purchase not drivable in headless Playwright (works on device); founder has perplexity_ultra active.

## Iter 81 — founder e-mail rename · live STT · GA-T on-chain bridge
- pytest tests/test_iter81_chain_stt_email.py 3/3; testing-agent light backend 4/5 (5th = strict assertion on /auth/me lacking `tier` for free users — pre-existing shape, frontend defaults to sovereign). Frontend verified by main agent via Playwright: /blockchain wallet link (checksummed) / unlink, queued mode text; /jarvis renders with live-STT wiring (web Speech API path needs mic → device/dev-build test).

## Iter 83 — Partner Approval Panel
- Frontend-only addition: `/partners-admin` (Founder). Backend endpoints `GET /uhp/partners/admin`, `POST /uhp/partners/{id}/approve|suspend` pre-existing (Founder/inner-circle gate).
- Main-agent smoke (Playwright, founder password login, Slovak): counts 2/102/1 → approve BioLab Praha → 1/103/1, `pa-msg` "BioLab Praha → AKTÍVNI". Web preview shows first-launch intro ("VSTÚPIŤ DO SYSTÉMU") + onboarding ("PRESKOČIŤ") overlays on fresh storage — dismiss before interacting.

## Iter 84 — Price update
- pytest tests/test_iter62_iap_tiers.py 6/6 (new prices). test_iter60 `test_founder_archangel_kept_on_iap_activate` fails for a PRE-EXISTING reason (uses removed dev-bypass for founder) — unrelated.
- Web preview verified: /store Sentinel €99 (backend) + RC button €99.00 monthly / €950.00 yearly; /subscription Sentinel 99 €/mo · 2475 Kč · 250 GA-T, Archangel 299 €; no stale 149/499 anywhere (only a DID hash contains "149").
