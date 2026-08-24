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
