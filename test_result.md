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
