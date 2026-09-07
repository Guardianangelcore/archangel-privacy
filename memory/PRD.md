# Guardian Health & Angel — Product Requirements (Feb 2026)

## Owner
Guardian Angel Sovereign Foundation (DAO). Sole steward: pseudonymous "Guardian Angel".

## Product goal
A sovereign, faceless, 22nd-century survival OS for individuals + their Guardian Circle. Zero surveillance, EU AI Act compliant, GPS-adaptive, multi-language (14).

## Immutable pillars
- **PILLAR 1 — Healing Carousel (Health)**: Bio-Scanner, Physio-AI, Kolotoč Uzdravenia, Pain Diary, Medical News, Longevity, Vault, IPS.
- **PILLAR 2 — Angel Shield (Family)**: Angel Mode senior OS, Voice Signatures, Voice Echoes, Family Pulse, Guardian Circle (native contacts, local-first), Native Calendar sync, Angel Pulse, Silent Witness, Safety Sentinel, Emergency QR.
- **PILLAR 3 — Sovereign Vault (Legacy/Wealth)**: Video Legacy Vault, Wealth Vault, GA-T Token, Digital Legacy, Testament, Biometric Will, Founder Toolkit, Archangel Chain.

## Phase 47/48 (current — DONE + tested 27/27)
1. **Guardian Eye multi-model OCR/vision** — GPT-5.4 · Claude Sonnet 5 · Gemini 3.1 Pro + Consensus mode. Send-to-Jarvis action.
2. **Guardian Circle sync** — expo-contacts, local-first, DID hashes, max 8 members.
3. **Native Calendar bridge** — expo-calendar, dedicated "Guardian Angel" calendar, meds + waitlist sync.
4. **Sovereign Compass GPS bearing** — /compass/bearing returns distance + 8-way direction to safe cities, active bio-beacons and waitlist clinics.
5. **COGNITIVE TRIAGE / Crisis HUD** — Automatic Stress UI. Backend classifies HR/SpO2/stress/voice-tremor → crisis. Frontend CrisisHUD overlay (2 giant buttons: CALL 112 + SURVIVAL INSTRUCTIONS) polls every 30s and mounts globally. 15-min cooldown after dismiss. Silent Guardian Circle push on trigger.

## Compliance
- EU AI Act Art. 50 watermark on every AI response ("AI Content · Sovereign Protocol").
- All names anonymised → "Guardian Angel", "Guardian Circle", "Inner Circle".
- DID hashes for metadata. Local-first storage for contacts/calendar (SecureStore + AsyncStorage).

## Phase 49 (TIMELINE MERGE — June 2026)
1. **P0 AUTH REPAIR** — root cause: corrupted `/root/.expo/state.json` crashed Metro. Fixed. Sovereign Bypass on login (`/api/auth/dev-bypass`): "VSTUP AKO GUARDIAN ANGEL (FOUNDER)" button + custom-email developer bypass. Founder `guardianangel.core@proton.me` auto-seeded (inner_circle, tier archangel).
2. **JARVIS ULTRA — SONAR** (`/api/agent/search`): Perplexity `sonar-reasoning-pro` (sonar-reasoning deprecated 12/2025), medicine+EU prompt, citations, `<think>` stripped. Graceful degrade → gpt-5.4 offline knowledge when `PERPLEXITY_API_KEY` is blank (it currently IS blank — user must obtain key at https://console.perplexity.ai/api).
3. **JARVIS ULTRA — VISION FORGE** (`/api/agent/imagine`): GPT Image 1 via Emergent LLM key, returns base64 PNG.
4. Jarvis UI: mode chips CHAT · SONAR·WEB · OBRAZ, tappable citations, generated-image bubbles.
5. Integrity audit: Onyx voice, wake-word JARVIS, 3-pillar triangle, Mosaic 16k TPS, UHP, Bio-Digital Twin, Longevity, Satellite Handshake — all confirmed present. No "Smoke" naming found (only "smoker" in Longevity = legit).

## Phase 49.1 (Galéria Obrazov + Hlasový Sonar — June 2026)
1. **Vault Art Gallery** — every `/api/agent/imagine` PNG is uploaded to Emergent Object Storage (`jarvis_art/{uid}/`) + inserted into `documents` (source: `jarvis_art`). Vault tab shows gold-bordered "GALÉRIA OBRAZOV · JARVIS" 3-col grid → full-screen preview, delete. Jarvis image bubble shows "ULOŽENÉ V TREZORE · OTVORIŤ GALÉRIU" chip.
2. **Voice Sonar** — Orb voice in Sonar mode speaks the reply in Onyx + announces source count (Slovak declension). `voice.ts` strips markdown/URLs before all TTS.
3. OpenAI safety rejections on imagine → 400 with friendly Slovak message.
4. **Sonar História** — `GET/DELETE /api/agent/search/history` + collapsible section in Jarvis (SONAR mode): past searches with source counts, tap re-injects Q&A+citations into chat.

## Phase 50 (CRITICAL UX FIXES — June 2026)
1. Settings gear (⚙️) visible top-right on ALL main screens: Home, 3 pillar hubs, Jarvis (`jv-settings`), Trezor (`vault-settings`), Rodinné kontakty (`fc-settings`).
2. **Jarvis LIVE STREAM** — `POST /api/agent/chat/stream` (SSE, gpt-5.4 via `stream_message`); shared `_chat_system()` builder. Frontend: typing dots (51 ms), first tokens ~1 s, progressive bubble, fallback to classic call. Pain-diary intent streams deterministically.
3. Angel Mode: phone icon → **QR PROFIL** (`angel-qr-profile` → /emergency-qr); labeled trio SOS / QR PROFIL / DOKTOR.
4. **Rodinné kontakty** — `routes/family_contacts.py`: POST/GET/DELETE + `/sos`; phones Fernet-encrypted at rest (`CONTACTS_ENC_KEY`). Screen `/family-contacts`: add modal (meno/telefón/vzťah chips), cards with Zavolať (tel:), Poslať SOS (event+push+prefilled SMS), delete with inline confirm. Gold `fs-contacts` hero in Family hub.
5. Duplicates removed on Home header: `home-jarvis` sparkles (dup of Orb) + `angel-toggle` SENIOR chip (dup of GUARDIAN GOLD tile).
6. **Twilio SOS SMS (pripravené)** — `/family-contacts/{id}/sos` posiela reálnu SMS cez Twilio, keď sú v backend/.env vyplnené `TWILIO_ACCOUNT_SID/AUTH_TOKEN/FROM_NUMBER` (zatiaľ prázdne — čaká na kľúče od usera). Fallback: zariadenie otvorí predvyplnenú SMS. SOS správa obsahuje GPS Google Maps odkaz.

## Phase 51 (KARTA ŽIVOTA — June 2026)
Reorganizácia existujúcich modulov (žiadny nový dizajn) — jadro appky je Životná karta:
1. **Karta života** (`/health-timeline` prestavaná): identity hero (meno · dátum narodenia · krvná skupina — zdroj rodný list; edit inline, PUT /api/lifecard; blood_type zdieľaný s emergency_profiles/QR). GET /api/lifecard (age, counts, cached predictions).
2. **5 podkategórií** (rozšírené calendar_events): vaccine=Očkovania · disease=Choroby · surgery=Operácie · injury=Úrazy · exam=Prehliadky. Každý záznam: dátum + typ + popis (notes). Legacy manuálne 'history' lazy-migrované na 'disease'; systémové 'history' (vault/billing doklady) ostávajú ako DOKUMENT. Timeline vracia counts.
3. **Predikcie** — POST /api/lifecard/predictions (gpt-5.4, JSON, max 4, SK): navrhne ďalšie očkovanie/prehliadku podľa histórie a veku; POST /lifecard/predictions/accept → zapíše do calendar_events (source jarvis) + frontend pridá aj do natívneho kalendára „Guardian Angel“ (zdieľaný helper src/native-calendar.ts, permission-contract).
4. **Hlasové pridávanie** — Jarvis chat/stream intent: trigger regex → LLM klasifikácia → záznam do správnej kategórie s dnešným/relatívnym dátumom („včera“). Otázky nezapíše (is_record=false → normálny chat). Odpoveď: „Zapísal som do Karty života: …“.
5. Health hub: zlatý hero KARTA ŽIVOTA (hh-lifecard-hero) navrchu; duplicitná dlaždica hh-timeline odstránená; '+' na obrazovke slúži len na rýchle pridanie do 5 kategórií.

## Phase 51.1 (Life Card Extensions — June 2026)
1. **OCR rodného listu** — POST /api/lifecard/ocr (gpt-5.4 vision): fotka dokladu → predvyplní meno/dátum narodenia/krvnú skupinu v edit boxe (user potvrdí uložením). Kamera s permission-contract + Open Settings.
2. **PDF Karty života** — GET /api/lifecard/report.pdf: identita + 5 sekcií záznamov; tlačidlo lc-pdf (sharePdf) na obrazovke.
3. **Rodinné karty** — GET /api/lifecard/family (+/{member}/timeline): členovia Guardian Circle (db.guardians, obojsmerne) — zo súkromia len očkovania+prehliadky (403 mimo kruhu). Sekcia lc-family; empty state → /recovery-suite.
4. **Booster Guard** — nový swarm agent (1h interval): booster_due o 30 a 7 dní → push + proaktívna Jarvis správa (raz na fázu, flagy na evente).

## Phase 51.2 (Očkovací preukaz EÚ + Karta pre dieťa — June 2026)
1. **Očkovací preukaz EÚ** — GET /api/lifecard/vaccine-pass(.pdf): bilingválny datablok + zoznam očkovaní + vyhlásenia v 14 jazykoch + SHA-256 DID podpis; tlačidlo lc-vaxpass (funguje aj pre kartu dieťaťa cez ?child_id=).
2. **Karta pre dieťa** — db.lifecard_children (max 10, CRUD, DELETE kaskáduje záznamy+predikcie). calendar_events nesú child_id; detská karta má vlastnú časovú os/počty/filtre, pediatrické Jarvis predikcie (detský očkovací kalendár), PDF aj preukaz. Booster Guard menuje dieťa. Adult dáta (IPS, border, kompas, briefing, rodinné karty) child záznamy vylučujú. UI: horizontálny prepínač kariet (lc-card-me / lc-card-{id} / lc-add-child), formulár novej karty, mazanie s potvrdením; hlasový hint a Rodinné karty len na mojej karte.

## Phase 51.3 (Rastová krivka + Trendy zdravia + Karta zubára — June 2026)
1. **Rastová krivka** — db.growth_logs + WHO percentily (výška 0-18r normal, váha 0-10r lognormal, orientačné tabuľky v health.py); deti majú pohlavie (m/f); obrazovka /child-growth (SVG graf P3/P50/P97 + merania s percentilmi), tlačidlo lc-growth na detskej karte.
2. **Trendy zdravia** — GET /api/lifecard/trends (ročné počty 6 kategórií, aj pre dieťa) + POST /trends/summary (Jarvis SK súhrn s watermarkom); obrazovka /health-trends (stacked ročné stĺpce + legenda + Jarvis súhrn), tlačidlo lc-trends.
3. **Karta zubára** — 6. kategória dental (ZUBÁR, cyan, tooth ikona) všade (validácie, filtre, počty, PDF sekcia, predikcie, hlasový intent „bol som u zubára"); voliteľné číslo zuba (FDI) pri zázname; box KARTA ZUBÁRA (história podľa zubov) pri dental filtri.

## Integrations
- Emergent LLM Key (OpenAI, Anthropic, Gemini text/vision, TTS, Whisper STT, GPT Image 1).
- Perplexity Sonar (`PERPLEXITY_API_KEY` in backend/.env — blank = graceful fallback).
- Stripe test keys (Payments).
- Emergent Push (native builds only).
- Emergent Google Auth + Sovereign dev-bypass.

## Competition Demo Prep (June 2026)
1. **Demo seed** — POST /api/demo/seed (idempotent, marker db.demo_seed): founder Life Card = DOB 1985-03-15, blood A+, 3 vaccinations (Flu 2023-10-15, Tetanus 2021-05-20, COVID-19 booster 2022-04-10), 2 surgeries (Knee arthroscopy 2019-08-12, Appendectomy 2012-03-25), 2 labs 2024-01-15 (glucose 5.2, cholesterol 4.8 — normal), Jarvis prediction "Annual physical examination due September 2026". SEEDED for founder; sets founder language=en.
2. **English UI polish** — default lang fallback 'sk'→'en' globally; hardcoded Slovak translated to English in: tabs layout, home, profile, health/family/legacy hubs, health-timeline, jarvis, healing, lens, daily-brief, child-growth, health-trends, my-recovery, translate, meds, login, hunter, vault, waitlist, emergency-qr, family-dashboard, CrisisHUD, onboarding-tour, biometric-gate + backend routes/healing.py (steps meta, companion, KIND_LABEL). Long-tail secondary screens (monolith, subscription, pantry, partners, compass, protocol, dignity, legal, token…) still contain Slovak strings.
3. **Welcome banner** — home testID home-welcome-banner: "Guardian Angel OS — Your Personal Health Guardian".
4. **DEMO badge** — global gold pill top-right (testID demo-badge, src/demo-mode.ts AsyncStorage pub/sub, default ON) + Settings toggle testID prof-demo-badge in profile (visible to all users).

## Achievements Removal (June 2026)
- Achievement badge system removed entirely per user request: deleted /app/frontend/app/achievements.tsx, home trophy chip (home-achievements), backend routes/achievements.py (catalog + GET /api/achievements → now 404). Streaks endpoints moved intact to routes/streaks.py (/api/streaks/*). Achievement tests removed from test_iter32/33/34 (41 pass). No DB collections existed (derived on-demand). Kept: DEMO badge (demo requirement), unread-count/label badges, streak flame, Jarvis ability unlocks (separate systems).

## Magic Lens + Dead-Button/Picker Audit (June 2026)
- **Magic Lens (#1 senior wow feature)**: POST /api/magic-lens (routes/health.py, gpt-5.4 vision via Emergent key) accepts {image_base64} → {found, extracted_text, summary (3-4 plain sentences), detected_category (10 types), suggested_title, lifecard_category (mapped to vaccine/disease/surgery/exam/injury/dental)}. Frontend /app/frontend/app/magic-lens.tsx: expo-camera CameraView viewfinder with SCAN DOCUMENT overlay + gallery fallback + full permission contract; result shows "This looks like X — save to Y?" with YES (saves to /api/calendar/events, today's date) and EDIT (title/category chips/notes form). Entry points: home tile testID home-magic-lens (gold, under welcome banner), Life Card button testID lc-magic-lens (health-timeline actions row).
- **Dead-button audit**: 0 dead buttons found — all Pressable/TouchableOpacity have onPress; all router.push targets resolve to existing routes; the 4 onPress={()=>{}} hits are intentional modal backdrop-blockers.
- **Picker audit**: all pickers functional (DateField calendar sheets, waitlist specialty/date sheets, blood type chips A+..0-, sex chips). No non-opening dropdowns found. Fixed leftover Slovak "CHLAPEC"→"BOY".

## Final Bug-Fix Pass (June 2026)
1. **English UI**: ~200 more strings translated (fall-verify, voice-echoes, family-contacts, onboarding, insurance, physio, pulse-check, calendar-sync, health-drop, paramedic, ContactSheet, CityPicker, sheets months/days, age.ts, _layout alerts, acoustic, invite, Paywall, blazing-ceremony, scam-shield, mental-fortress + global button-label dictionary). Backend geo city names → English. PROTECTED (untouched per user): mosaic.tsx, subscription.tsx, arbitrage.tsx, barter.tsx, billing.py, i18n.ts (sk locale values legit). Remaining Slovak: deep secondary screens (monolith, pantry, partners, compass, dignity, protocol, token, legal, wealth-vault, recovery-suite, drop/, voice-signature, duress, bioscan, eternal-vault, video-legacy, gigs, silent-witness, guardian-circle-sync, biometric-will, healthcare-proxy, fortress, humanitarian, inner-circle, longevity + backend LLM prompts/simulated data).
2. **Jarvis voice**: onyx confirmed default (src/voice.ts MOOD_VOICE all onyx); wake-word "JARVIS" now ALSO armed inside jarvis.tsx across all 3 modes (chat/sonar/imagine) via startWakeWord effect (native only, one-shot → orbPress).
3. **Fall detection** (src/guardian.tsx): freefall < 0.3g sustained >= 80ms THEN impact > 2.5g within 1.2s; 30s cooldown (was 60s, single-sample 0.35/2.7). Manual SOS flows unchanged/independent.
4. **GPS**: backend DEFAULT_GEO → New York (40.7128, -74.0060); New York added to CITIES; stale Bratislava/Praha user geo docs reset in DB. Live mode = Location.getCurrentPositionAsync with permission fallback (profile.tsx, pre-existing).
5. **Security**: login.tsx dev-bypass (founder btn + email bypass) gated to __DEV__ / preview / localhost hostnames only (isDevEnv). GDPR consent checkbox (testID lc-gdpr-consent) required before saving Life Card identity (saveCard blocks without it). JWT already header-based (src/api.ts).
6. **Tests updated**: iter24/phase45-46 geo expectations → English names + New York; phase51 allows 'dental' prediction category. Founder demo prediction restored in DB. Full suite: 785→795 pass (2 billing failures were xdist flakes — pass serially).

## PII Audit + Final English Sweep (Iter 49-50, June 2026)
1. **PII AUDIT (competition safety)**: Full codebase scan (names, emails, author fields, md files) — NO real developer PII found. All author/copyright/README/LICENSE already "Guardian Angel" branded; all emails are brand (guardianangel.core@proton.me) or fictional test fixtures. Fixed person-like demo strings: clinic_sync.py "MUDr. Kováčová — Ortopédia"→"GA Labs Ortho Clinic", doctor_name "MUDr. Eva Kováčová"→"Dr. Guardian Angel". Test-fixture names (Jan/Anna Novak = John Doe equivalents) left intact to keep OCR tests green.
2. **English sweep COMPLETE**: ~500 replacements across 40+ frontend screens (pass 1: lowercase-diacritic strings; pass 2: UPPERCASE headers/buttons; pass 3: diacritic-free leftovers MÔJ KRUH/HOTOVO/KROK/POTVRDZUJEM/Stav PN). Backend user-visible strings translated: routes/token.py (earn/spend catalog), compass.py (survival tips, Ambulance SK, claim kinds, errors), demo.py (seed labels), gateway.py (marketplace offers + disclaimer + errors), wealth.py (policies, video statuses, eta). PROTECTED (still Slovak per user): mosaic.tsx, subscription.tsx, arbitrage.tsx, barter.tsx, billing.py, i18n.ts, language-picker names.
3. **Cleanup**: all temp translation scripts (tr*.py) removed from /app root.
4. **Testing**: iter_48 (8/9 backend + frontend smoke) & iter_49 (11 pass/1 skip backend; 7/9 screens English-clean, last 2 fixed after) — test_iter48_translation_regression.py + test_iter49_english_retest.py. Known infra issue: preview objstore 401 → clinic-sync simulate-beam 502 (upload-dependent, unrelated).

## Jury Cheat Sheet PDF (June 2026)
- One-page A4 printable demo script PDF with 4 live app screenshots (Home, Jarvis, Magic Lens, Fall-verify) at /app/release_package/JURY_CHEAT_SHEET.pdf. Generator scripts + assets in /app/release_package/tools/ (regenerate: jury_capture.py needs `pip install playwright`, uses /usr/bin/google-chrome + localhost:3000; then jury_pdf.py).
- Backend: GET /api/founder/jury-cheat-sheet (founder.py) — auth via Bearer header or ?token= (uses _auth_pdf/_pdf_response). Verified 200 auth / 401 unauth.
- Frontend: gold download row testID ft-jury-pdf in founder-toolkit COMPETITION ENTRY section (sharePdf → web opens tab, native shares file).
- Bonus: translated founder.py ROADMAP (8 eras) + RELEASE_DOCS descriptions to English (was Slovak on judge-facing screen).

## Investor Page + Final Smoke + Deploy Readiness (Iter 50, June 2026)
1. **Jury PDF page 2** — INVESTOR ONE-PAGER: forecast table 2026-2030 (mirrors founder.py formulas: ARPU €63.5, Guardian Tax 15%, margin 87%), ARR bar chart, 8-era roadmap timeline. Same endpoint /api/founder/jury-cheat-sheet (now 2 pages, ~244 kB). Generator: /app/release_package/tools/jury_pdf.py.
2. **Final smoke test (iter 50)** — 15/15 pytest (test_iter50_final_smoke.py) + 10/10 frontend screens green. CRITICAL FIX: EMERGENT_LLM_KEY had expired → rotated in backend/.env (Jarvis chat + Magic Lens 502 → 200). Test's 1x1 PNG replaced with valid PIL-generated document image (OpenAI vision rejects tiny images). Testing agent also fixed agent.py:646 Slovak weather fallback.
3. **Deploy readiness fixes** — removed unused python-bitcoinlib from requirements.txt (deploy blocker); added NSFaceIDUsageDescription to app.json infoPlist; added ACCESS_FINE/COARSE_LOCATION to android permissions; added unauthenticated GET /health (root level, 200) in server.py for deploy probes.
4. **Remaining user decision** — push notifications: frontend/google-services.json is a placeholder; real Firebase file needed only if push should work on Android builds. AUTH_SESSION_URL fallback in core.py = standard Emergent auth playbook URL (intentional).

## Email/Password Auth + Google Sign-in Fix (Iter 51, June 2026)
- User reported Google login failing + missing classic login. ADDED playbook-compliant email/password auth: POST /api/auth/register (201, min 12 chars/max 72 bytes, bcrypt-12 threadpool, generic 409) + POST /api/auth/login (generic 401, timing-safe dummy hash, case-insensitive email). Opaque gs-* tokens in user_sessions (30d) — get_current_user untouched; coexists with Google + dev-bypass.
- Login screen: SIGN IN/CREATE ACCOUNT tabs, email+password+eye, OR divider, Google button, founder bypass (preview only). testIDs pw-*.
- Google fix: exchangeSessionId no longer swallows errors (authError surfaced on login screen); web URL fragment cleaned only on success (playbook rules 7+8). Backend logs showed exchange 200s — failures were silent UI state.
- models.py User.language default sk→en (new users get English TOS gate; en TOS existed in legacy.py TOS_TEXT).
- Tested iter 51: 11/11 backend + full UI E2E green. Test account: demo.judge@guardian.app / guardian-demo-2026 (in test_credentials.md).

## Phase 53 (Legal Pages + Final English Sweep — June 2026)
1. **English sweep (7 remaining screens)**: monolith, pantry, compass, token, legal, wealth-vault, longevity — all user-visible Slovak translated to English (Konsenzus/SUMA/poplatok/teraz/kompatibilita/riziko/HODNOTY, pantry categories+urgency labels, IDENTITA/MENO/ALERGIE/LIEKY DNES/STAV, TOKENOMIKA/odmeny, ROK NARODENIA/Svedok/HOLOGRAF, KRYPTO/blok/Karta, AKTIVITA/FAKTORY). wealth-vault number locale sk-SK→en-US. Backend routes/longevity.py factors Aktivita→Activity, Kroky→Steps. Bug fix: pantry.tsx missing Platform import (crashed voice add).
2. **Terms of Service page** (`/terms-of-service`, public route, testIDs tos-screen/tos-back/tos-medical-disclaimer/tos-privacy-link): prominent gold medical-disclaimer box ("Guardian Angel OS is NOT a medical device, does NOT replace medical care, always consult a physician; emergencies → 112/911") + 10 sections (service, emergency features, account, acceptable use, subscriptions/GA-T, IP, liability, termination, changes/law). v2026-06.1.
3. **Privacy Policy page** (`/privacy-policy`, public route, testIDs privacy-screen/privacy-back/privacy-local-first/privacy-tos-link): GDPR-compliant — local-first promise box (data stays on device, zero surveillance, no ads/sale), what we process, opt-in sharing, GDPR legal bases Art.6/9, AI processing (Art.50 watermark), retention, GDPR rights, security, children, changes.
4. **Registration consent gate**: CREATE ACCOUNT tab on login has mandatory checkbox (reg-agree) with links reg-tos-link/reg-privacy-link; pw-submit disabled + onPassword throws until agreed. SIGN IN tab unaffected. Both legal routes added to isPublic in _layout.tsx (reachable without login).
5. Tested iter 53: backend 5/5 auth regression + full frontend E2E green (consent gate, public pages, registration, sign-in, 7-screen English regression). Founder language switched to en by tests (matches demo default).

## Forgot Password Flow (Iter 52, June 2026)
- Emergent-managed Resend integration: /app/backend/emailer.py (EMAIL_BASE_URL constant, X-Email-Key, from_name=EMAIL_FROM_NAME env, full G2/G3 guardrail gate on every send). .env: EMERGENT_EMAIL_KEY + EMAIL_FROM_NAME added.
- POST /api/auth/forgot-password: generic 200 always (no enumeration); 6-digit code sha256-hashed at rest, 15-min TTL, 3 requests/hour/email (old codes soft-invalidated via used:true — delete_many defeated the rate limit, FIXED after testing agent caught it), fixed HTML template (no links/forms).
- POST /api/auth/reset-password: generic 400, 5 attempts max, single-use, bcrypt rehash, ALL sessions revoked.
- Login UI: FORGOT PASSWORD? link → email → SEND RESET CODE → code + new password → RESET PASSWORD; RESEND CODE / BACK TO SIGN IN links. testIDs: forgot-link, reset-submit, reset-code, reset-new-password, resend-code, back-to-login, login-info.
- Tested iter 52: 20/20 pytest (test_password_reset.py self-healing fixture added) + 7/7 UI E2E flows. Reset-test account: delivered@resend.dev / reset-password-2026-01.

## Consent Receipt + Deploy Health + Login Contrast Fix (Iter 54, June 2026)
1. **GDPR consent receipt** — POST /api/auth/register now REQUIRES `tos_accepted: true` (422 otherwise) and validates `tos_version` against core.TOS_VERSION ("2026-06.1", single source of truth; legacy.py imports it; frontend mirror in src/legal.ts LEGAL_VERSION used by ToS/Privacy pages + auth.tsx). On success stores `users.consent_receipt` {receipt_id, accepted_at (ISO UTC "Z"), tos_version, privacy_policy_version, documents, method: registration_checkbox, ip_hash (sha256), user_agent, ledger_hash} + `tos_accepted_version` / `tos_accepted_at`, and appends a tamper-evident `consent_receipt` entry to aml_ledger. GET /api/auth/consent-receipt returns it. Frontend: registerPassword(email, password, tosAccepted) sends tos_accepted + tos_version.
2. **Bug fix — 422 "must accept terms" with checkbox checked**: caused by stale client bundle (old auth.tsx sent no tos fields) hitting the new backend. Verified via Playwright: payload contains tos_accepted:true → 201. A reload of the app fixes stale clients.
3. **Bug fix — invisible text on login**: login.tsx still used the OLD token semantics (inverse=dark/onInverse=white, changed in ULTRA MODE redesign to inverse=#F5F5F5/onInverse=#050510) → near-black text on dark gradient. Replaced C.onInverse→C.fg for all text on the dark background; CREATE ACCOUNT/SIGN IN button = C.inverse bg + C.onInverse text; active language chip likewise. Verified visually.
4. **Deploy health check** — fixed: backend/.env EMAIL_FROM_NAME quoted (was unquoted with spaces = BLOCKER); mosaic.py verify_chain_and_wealth() no longer hard-deletes mosaic_blocks on fork detection (soft-marks `orphaned:true`, all live-chain queries filter via _LIVE) = BLOCKER removed. Remaining WARN (user decision): frontend/google-services.json is a Firebase placeholder (Android push won't deliver until real file), no iOS GoogleService-Info.plist; frontend/package-lock.json coexists with yarn.lock (remove package-lock to avoid drift). AUTH_SESSION_URL fallback = intentional Emergent playbook URL.
5. Observed (not fixed, out of scope): Sovereign Tour step 1 title still Slovak ("MOJE UZDRAVOVANIE") in src/onboarding-tour.tsx.

## Iter 55 — 3 urgent bug fixes (June 2026) — tested (iteration_54.json, 9/9 backend + UI green)
1. **SOS false trigger (P0)**: Acoustic Guardian loud-noise (> -8 dBFS) NO LONGER opens /fall-verify. It shows a card (noise-alert) + records 5 s → POST /api/voice/sos-keyword (Whisper) → only explicit keyword ("SOS"/"help"/"pomoc"/"hilfe"…) opens the emergency loop; otherwise "Nothing was sent", auto-dismiss 30 s. Angel Mode SOS button = HOLD 1.5 s only (tap → hint). Accelerometer fall detection (two-phase free-fall+impact) unchanged.
2. **Jarvis 502**: root cause = EMERGENT_LLM_KEY budget exhausted (Max budget 7.4 reached) → USER MUST TOP UP (Profile → Manage plan → Universal Key → Add Balance / auto top-up). Code: core.ai_http_error → 503 JSON with readable detail (Cloudflare was replacing 502 with HTML "error code: 502"); src/api.ts errMsg() shows detail in Jarvis.
3. **Briefing "New York"**: DEFAULT_GEO now = "unknown" (geo_resolved/ensure_geo in geo.py); _weather returns None when unresolved; /agent/briefing + /geo/context IP-locate never-located users server-side; /geo/locate stores real GPS coords + reverse-geocoded city (BigDataCloud keyless) and nearest_city label; frontend startup locate (GPS if permission already granted, else IP) in guardian.tsx; jv-use-location button on briefing card; home pin hidden until resolved. NOTE: on web preview the IP is the cloud egress (e.g. Singapore) — real devices use GPS.

## Iter 56 — Language switching fix · Guardian tier gate · Guardian SOS Alert · Tour EN (tested iteration_55.json, all green)
1. **i18n context** (`src/i18n-context.tsx`, provider in `_layout.tsx`): `useI18n()` → instant app-wide re-render on `setLang`; login-screen pick persisted (AsyncStorage) and applied to the account on sign-in; ~55 new core keys × 14 langs (T + CORE block in i18n.ts); converted login, tabs, home/Angel home, profile, fall-verify, daily-brief; `/companion/greeting?language=` localized sk/cs/de/en. Remaining deep screens still English (fallback) — full 100+ screen i18n is a separate task.
2. **Guardian tier gate** — existing system (subscription.py: sovereign free / guardian €29 / sentinel €149 / archangel €499; user's memo said ~9€ — price NOT changed). `require_tier(user,"guardian")` on /agent/chat, /agent/chat/stream, /agent/transcribe, /agent/briefing → 402 `guardian_required`. Jarvis screen shows `Paywall tier="guardian"` (jv-guardian-gate) with trial + /subscription buttons. Founder/inner_circle = archangel.
3. **Guardian SOS Alert** — POST /api/sos/broadcast (family_contacts.py): live GPS → SMS all family contacts (Twilio when TWILIO_* set, else device SMS composer via `sms:` URL), push linked guardians, sos_events log. fall-verify 'sent' screen lists contacts + TEXT GUARDIANS NOW.
4. Sovereign Tour step 1 → "MY HEALING".
OPEN: LLM key budget exhausted (user must top up). SOS voice keyword must be validated on a real phone (mic).

## Iter 57 — GA-T loyalty allocation wired to subscriptions · Guardian €9 (tested iteration_56.json: backend 6/6 + UI green)
- Existing GA-T engine reused (no new token system). token.py: SUBSCRIPTION_GAT guardian 100 / sentinel 300 / archangel 1000 per 30 days,
  loyalty bonus +10%/consecutive month (cap +50%); settle_subscription_allocations (idempotent, ledger kind subscription_allocation,
  treasury→user), start_subscription_allocation (Stripe activation → first credit instantly, streak kept if renewal within 7 days),
  sweep every 6h in swarm_loop. Only FIAT-paid plans (card / iap / apple_iap / google_iap / family_pack) qualify — GA-T-paid & trial excluded.
- Surfaces: /token/wallet.subscription_allocation, /subscription.gat_allocation + gat_monthly_by_tier; Token screen loyalty card (tk-loyalty),
  Subscription screen sb-loyalty + tier features.
- Guardian price €29 → €9 (15 GA-T; yearly 86 €/144 GA-T). Founder projections TIER_MIX updated.
- GAP: Apple/Google IAP (RevenueCat) is NOT integrated — only Stripe card (test mode) + GA-T. Hook is channel-agnostic: IAP must set
  tier/tier_until/tier_paid_with="iap" and call start_subscription_allocation. Ask user whether to add Emergent-managed RevenueCat.
- Testing agent fixed: settle_subscription_allocations `if not u` → `if u is None` (empty projection dict for free users).

## Iter 58 — Rename to "Archangel OS" (June 2026)
- Public-facing name changed everywhere (frontend, backend documents/emails/SMS/prompts, app.json + App Store subtitle in extra.appStoreSubtitle,
  branded splash). Brand identity unchanged (Guardian Angel founder/DAO, GA-T, Sovereign/Guardian/Sentinel/Archangel tiers).
- RevenueCat IAP: BLOCKED until the user connects RevenueCat in the Emergent payments panel (integration_expert playbook fetched; do /setup then).

## Iter 59 — Legal disclaimer audit (tested iteration_58.json + fix verified)
- Consolidated disclaimer key `disclaimer.general` (src/i18n-legal.ts, 14 langs, incl. personal limitation-of-liability sentence) on ToS top (bold),
  Privacy footer, registration consent; first-launch dismissible card (medical + 112) once per device per LEGAL_VERSION; EU AI Act Art. 50 label
  under every Jarvis reply + briefing; ToS body extended (112/999/911, fall detection, medication reference-only, data accuracy, GA-T not
  financial instrument, personal liability).
- RevenueCat IAP still BLOCKED: proxy status disconnected/oauth_pending — user must click "Connect RevenueCat" (Preview → manage → payments).
  Plan once connected: /setup with bundle com.emergent.angelos.qvqss9 → keys to frontend/.env → lib/revenuecat.tsx (SubscriptionProvider,
  logIn(user_id) on auth paths) → subscription.tsx buys via offerings → POST /subscription/iap-sync mirrors the active `pro` entitlement into
  tier/tier_until/tier_paid_with="iap" so Jarvis gate + GA-T loyalty allocation fire (client entitlement remains source of truth; no webhooks).

## Iter 60 — RevenueCat IAP LIVE in app (Sept 2026) — see /app/memory/revenuecat.md
- RevenueCat connected (proj10bfa652, entitlement `pro`, offering `default`, $rc_monthly $9.99 / $rc_annual $79.99 USD — prices unchanged, Guardian only).
- Wiring: QueryClientProvider + SubscriptionProvider in _layout (SDK init module scope); identity logIn/logOut inside provider; IapBuyButton in Guardian tier card
  (sb-iap-guardian) + Jarvis Paywall (tier guardian); RestorePurchasesButton (iap-restore) in MANAGE SUBSCRIPTION; useIapMirror auto-syncs renewals/lapses.
- Backend POST /api/subscription/iap-sync (fixed missing `_aml_ledger_append` import; identity check = app_user_id == user_id): active pro → tier guardian,
  tier_paid_with iap → GA-T loyalty (verified E2E in preview Test Store: user iap-test-1 got tier guardian + 100 GA-T ledger entry). Lapse → sovereign.
- Fixed corrupted frontend/.env (TEST key glued to EXPO_PACKAGER_PROXY_URL); removed duplicate package-lock.json (deploy warn).
- Real App Store / Google Play purchases require a native store build + store-side products/credentials (FAQ in payments panel) — cannot be tested in Expo Go/web.
- Testing agent (iteration_60.json): backend 11/11 (tests/test_iter60_iap_sync.py), UI green. Found+fixed: (a) token.py `_ledger_append` race
  (concurrent GA-T writes → DuplicateKeyError 500) → retry-on-duplicate loop; (b) buy button + useIapMirror double-POSTed iap-sync → shared
  in-flight promise per entitlement snapshot; (c) success text was unmounted when the Guardian card flipped to ACTIVE → message lifted to screen
  level (testID sb-msg); (d) Browser-Mode cancel code is numeric 1 (native "1") → isUserCancelled() handles both, cancel stays silent.

## Iter 61 — Perplexity Sonar everywhere (Sept 2026)
- Shared helper backend/perplexity.py: sonar(messages, model=sonar-pro, recency, context_size, json_schema) → {content, citations, search_results}; 429 → one retry; None on failure (callers degrade). Key = PERPLEXITY_API_KEY (backend/.env, valid, live).
- Jarvis SONAR·WEB (routes/agent.py agent_search, sonar-reasoning-pro) — unchanged, verified live (15 citations).
- Medical News Sentinel LIVE (routes/news.py): GET /news/feed → general query per language+country (6 items) + personal query per user focus (waitlist/jarvis_actions specialties excl. swarm-spawned + disease/surgery events; 3 items), structured JSON (title/summary/specialty/region/tech/source/url/date/hunt_city/savings_note/keywords) in the user's language. Cache db.medical_news_live 12 h; misses refresh in BACKGROUND (asyncio task, response never waits; `pending: true`, frontend polls every 10 s ≤8×); force=true (pull-to-refresh) ≥1 h; failure → 3 min backoff; swarm news sentinel warms the general cache for active users' lang/country combos. Live items upserted into db.medical_news (live:true, pruned after 14 d) so Hunt + swarm sentinel work; fallback = curated seed (live:false). Response: live, pending, fetched_at, engine, note. UI: news-live-badge, news-source-{id} link, hunt only when hunt_city.
- Morning Briefing (GET /agent/briefing): `news` = 3 real regional health headlines (sonar-pro, recency week, context low, 1 call per lang/country/day cached key brief-news:*; empty never cached), LLM mentions the first headline; fallback text includes it. UI: jv-news / jv-news-{i} tappable rows in the briefing card.
- Cost guard: ~$0.03 per news query, ~$0.01 per briefing headlines call; all cached.
- Post-test hardening: keyword tags ≥4 chars; swarm auto-hunt specialty = item specialty; language rule enforced in prompt; noise hunts purged.

## Iter 62 — AUDIT & FIX (Sept 2026): Archangel Chain · 4-tier price list · 3-tier IAP
- Rename: every "Mosaic Chain" → "Archangel Chain" (frontend mosaic/wealth-vault/video-legacy, backend wealth/mosaic, tests, PRD). Route names/identifiers (routes/mosaic.py, /mosaic, mosaic_block) unchanged on purpose.
- Prices (backend TIERS, _prices(eur_year=…)): Sovereign FREE · Guardian €9/€86 · Sentinel €149/€1490 · Archangel €499/€4990 (annual no longer a generic −20 %).
- RevenueCat (integration proxy, entitlement "pro", offering "default"): EUR-only Test Store packages guardian_monthly/annual, sentinel_monthly/annual, archangel_monthly/annual (product ids pro.<tier>_<period>). Legacy USD $rc_monthly/$rc_annual removed from the offering (mixing USD+EUR made RC hide EUR-only products in en-US locales). User-supplied key test_AKjD… is INVALID (RC: "Invalid API Key") → kept the connected project's working test key.
- Tier from product id (one entitlement): backend iap_tier() in routes/subscription.py; frontend iapTierOf()/IAP_PACKAGES/activeTier in src/revenuecat.tsx. IapBuyButton takes `tier`; subscription.tsx renders Sovereign "FREE / Your current plan" + IAP buttons on all 3 paid tiers (testIDs sb-iap-{tier}, iap-buy-{tier}-{monthly|annual}); Paywall passes its tier. iap-sync: store-paid tier follows the store (upgrade+downgrade), lapse → sovereign; GA-T per tier (100/300/1000). Tests: tests/test_iter62_iap_tiers.py (6/6).
- Perplexity: sonar-reasoning-pro verified for Jarvis SONAR; for the structured feed/briefing it returns EMPTY content (0 completion tokens) on JSON/list prompts (3 probes) → kept sonar-pro (+json_schema) there. Expo SDK upgrade to 57 deferred by user (stay on SDK 54).

## Iter 63 — Full i18n of deeper screens · tier gates · sonar-reasoning-pro fix (Sept 2026)
- i18n: scripts/i18n-codemod.js (babel AST, range edits) externalised 2037 strings from ~100 screens/components into src/locales/en.json (keys "<screen>.<slug>", {0} placeholders) and rewrote them to tt()/tx() (useI18n aliases, hook injected per component). backend/scripts/translate_locales.py (gpt-5.4, incremental, placeholder check) generated sk/cs/de/pl/hu/ru/es/fr/it/uk/zh/ja/ar (2037 keys each). t() now supports vars; tx(text) translates backend-provided English strings (tier features/taglines, seeded as srv.* keys). Module-level constant labels rendered via tx(). Re-run: `node scripts/i18n-codemod.js --write <files>` then `python scripts/translate_locales.py`.
- Tier gates (Guardian+): backend require_tier on /waitlist (GET/POST via Depends → 402 before body validation)/scan, /lens/analyze*, /magic-lens, /agent/search (+ existing Jarvis). Frontend Paywall (pw-upgrade → /subscription) on Waitlist tab (waitlist-paywall), Magic Lens (ml-paywall), Jarvis (paywall).
- sonar-reasoning-pro EMPTY content root cause: max_tokens ≲2500 → hidden reasoning exhausts budget → API returns empty content (0 completion tokens, finish=stop). Fix: perplexity.sonar() enforces max_tokens ≥ 6000 for reasoning models and treats empty content as failure; Jarvis agent_search max_tokens 2200 → 6000. Verified live (JSON prompt now returns parseable content).
- Tests: tests/test_iter63_gates.py 8/8 (gates 402, unlock per tier, Sonar live). iteration_63.json UI green (paywalls, no raw i18n keys, Slovak render).

## Iter 64 — Jarvis weather location fix (Sept 2026)
- Root cause of "Singapore" weather: (a) on web the app never used browser GPS (Platform.OS!=='web' guard), (b) server-side IP fallback saw the cloud ingress/egress IP (SG) via X-Forwarded-For and persisted it as source "ip" (= resolved → never re-located).
- Fix: shared `src/geo.ts locateDevice({askPermission})` — expo-location GPS on native AND web (asks permission once when geo is not gps/manual), fallback = client-side HTTPS IP lookup on the DEVICE (ipapi.co → ipwho.is) posted to POST /geo/ip-locate {lat,lng,city,country}; server X-Forwarded-For lookup remains last resort. Used by GuardianMonitor startup (every session) and Jarvis `jv-use-location`.
- Backend: /geo/ip-locate accepts optional body coords; `_apply_geo` invalidates today's cached briefing (db.agent_briefings + edge cache) when the city changes so weather follows the new place immediately.
- Verified: web GPS Singapore→Košice (source gps), denied-permission → ipapi.co path, briefing weather Vienna→Rome after move.

## Iter 65 — Jarvis STOP + self-trigger loop fix (Sept 2026)
- Root cause of "Jarvis repeats itself / can't be stopped" (native): wake-word poll used `status.metering ?? status.durationMillis` — presets have no metering, so durationMillis (always > -18) fired the wake-word ~600 ms after every arming → orbPress auto-opened the mic after each reply (recording Jarvis's own loudspeaker output → answering himself). Angel Home with wake_word_enabled auto-spoke "Yes, I am listening" + jumped to /jarvis on mount.
- Fix: wake-word.ts only honours real `metering` (dBFS) and ignores hits while `isSpeaking()`; wake recorders created with `isMeteringEnabled: true` (jarvis.tsx + AngelHome). Jarvis wake-word armed only when idle (not recording/busy/speaking); orbPress ignores taps while busy/speaking.
- voice.ts: `isSpeaking()` / `onSpeakingChange()`; player `loop=false`, `playbackStatusUpdate.didJustFinish` → stop + notify (plays exactly once).
- Jarvis STOP button (testID jv-stop, visible while speaking/busy/recording): stopSpeaking + AbortController on /agent/chat/stream (no classic fallback when aborted; partial bubble kept) + cancels analysis step loop + stops open mic without sending + stopWakeWord. Verified on web: play→STOP stops; play again→runs once and ends; mid-stream STOP freezes output.
- Real wake-word/mic behaviour must be validated on a physical device (Expo Go / native build).

## Iter 66 — Expo SDK 54 → 57 upgrade (Sept 2026)
- `yarn expo install expo@^57 --fix` → React Native 0.86.3, React 19.2.3, reanimated 4.5, worklets 0.10, gesture-handler 2.32, screens 4.26, TypeScript 6.0.3, all expo-* on ~57.x. expo-doctor 21/21 pass.
- app.json: removed `newArchEnabled` + android `edgeToEdgeEnabled` (removed from schema in SDK55). Added missing peer dep expo-asset.
- Breaking-change fixes: (1) `@expo/vector-icons` removed from expo core → migrated all 104 files to `@react-native-vector-icons/ionicons` + `/material-design-icons` (config plugins added, old pkg removed). (2) expo-calendar & expo-contacts legacy APIs now THROW at runtime unless imported from `/legacy` → switched imports in calendar-sync.tsx, native-calendar.ts, guardian-circle-sync.tsx, ContactSheet.tsx (Contacts.Contact → Contacts.ExistingContact). (3) expo-video removed `allowsFullscreen` → `fullscreenOptions={{enable:true}}` (physio.tsx). (4) Notifications.setNotificationHandler needs shouldShowBanner/shouldShowList (NotificationBehavior). (5) StyleSheet.absoluteFillObject → absoluteFill. (6) expo-linking createURL now named import. (7) `global` → `globalThis` in drop/[dropId].tsx. Widened User type (birth_year/biometric_enabled/onboarding_completed/tier).
- eslint-plugin-react-hooks v7 ships React-Compiler rules as errors (set-state-in-effect etc., 93 advisory) → downgraded those 5 rules to `warn` in eslint.config.js (0 errors, 163 warnings). TypeScript `tsc --noEmit` = 0 errors.
- Verified: web bundle builds (Metro 1780 modules), Home + Jarvis render, briefing/weather/STOP intact; RevenueCat IAP + tier-gate pytest 25/25 green (backend untouched). RevenueCat SDK (react-native-purchases 10.8.1) unchanged & compatible.
- NOT tested (needs native build/EAS): actual store purchases, push, mic/wake-word, calendar/contacts native writes. Expo Go for SDK 57 is not on stores — use `eas go`/dev build.
- use-icon-fonts.ts still references @expo/vector-icons CDN for Expo-Go font fallback (harmless; native/web use autolinked fonts). Left as-is.

## Iter 67 — ToS/Privacy Settings links (Sept 2026)
- ToS/Privacy requirement was already satisfied by earlier phases: standalone screens /terms-of-service (tos-screen) + /privacy-policy (privacy-screen), first-launch blocking modal src/FirstLaunchDisclaimer.tsx (AsyncStorage key ga.disclaimer.seen.<LEGAL_VERSION>, "I understand", shown once), and full 14-lang legal text (medical disclaimer, GDPR bases, local-first/zero-surveillance, operator = Guardian Angel Sovereign Foundation (DAO) — NOT renamed to "GA Labs" to preserve established brand).
- ONLY change this task: added two direct Settings rows in app/(tabs)/profile.tsx — testID prof-tos-btn → /terms-of-service, prof-privacy-btn → /privacy-policy (reusing i18n keys terms_of_service.terms_of_service / privacy_policy.privacy_policy). Verified on web: both render under the Legal Hub button and navigate to the Slovak screens.

## Iter 68 — Nearby Care GPS locator (Sept 2026)
- Backend: routes/nearby.py — GET /api/nearby/care?kind=pharmacy|doctor|emergency&lat&lng&radius (500–20000 m, default 5 km). Guardian+ (`require_tier`) → Sovereign 402. Keyless OpenStreetMap: Overpass mirrors (osm.ch, mail.ru, overpass-api.de; some blocked from this pod) with automatic Nominatim bounded-search fallback (`extratags=1` → opening_hours/phone). Falls back to user's stored geo when no coords. Sorted by haversine distance, max 30, 30-min in-memory cache. Response: {center, kind, results[{name,lat,lng,distance_km,opening_hours,phone,address,emergency}], source}.
- Frontend: app/nearby-care.tsx (testIDs nearby-care-screen, nc-f-pharmacy|doctor|emergency, nc-map, nc-item-N, nc-call-N, nc-gps, nc-paywall). Uses locateDevice() (GPS → IP) then /geo/context fallback; tap row → native maps directions; call button. Map = src/ui/OsmMap.tsx (WebView + Leaflet) with OsmMap.web.tsx (iframe srcDoc) — shared HTML in osm-map-html.ts, numbered pins + blue "me" dot. Entry tile hh-nearby-care in Health hub. 11 i18n keys nearby_care.* in all 14 locales (sk hand-written: "NÁJDI LEKÁRA / LEKÁREŇ").
- Tests: backend/tests/test_iter68_nearby_care.py (5 pass). Web verified: Guardian 30 pharmacies Bratislava w/ hours+distance, filters, Sovereign paywall, hub navigation. Native WebView map + maps: deep links need a device.

## Iter 69 — Cross-fork file "copy" request (Sept 2026) — resolved without changes
- User asked to copy agent.py / calendar.py / GuardianEye / medsearch.py / Twilio SOS / billing+subscription from other forks. Forks are isolated containers → no access. Audit showed everything already exists here except routes/medsearch.py; user decided nearby.py (Nearby Care locator) fully replaces it. No code changes made. Env note: Twilio sender var is TWILIO_FROM_NUMBER (not TWILIO_PHONE_NUMBER).

## Iter 70 — Opt-in Data Marketplace audit + gaps filled (Sept 2026)
- Location: NOT routes/marketplace.py (that name doesn't exist; app/marketplace.tsx is the *services* marketplace). The opt-in DATA marketplace is routes/gateway.py §2 (PUT /marketplace/optin, GET /marketplace/me, GET /marketplace/offers, POST /marketplace/offers/{id}/accept) + app/protocol.tsx §2.
- Already present: consent Switch (pr-market-optin), anonymization (GDPR Art. 9 wording, offers are anonymized aggregates, payouts simulated), GA-T award on accept (proof_of_health = 5 GA-T via award_tokens).
- Added: (1) Guardian+ tier gate on optin + accept (402; GET endpoints left open so the screen still loads → frontend shows Paywall pr-market-paywall on 402); (2) per-category "WHAT YOU SHARE" chips pr-cat-medication|wellness|vaccination saved via PUT optin, backend whitelists categories and rejects accept with 403 category_not_shared when the offer's category isn't shared; (3) GA-T visibility: offers carry reward_gat, /me returns earnings_gat (sum of sale.gat_reward, now persisted on the sale doc), UI shows "X € · Y GA-T" (pr-market-gat), "+5 GA-T" per offer and in the sold toast. Chips/switch disabled until /marketplace/me loads (race fix). 5 new i18n keys in 14 locales.

## Iter 71 — Survival/Bunker audit + gaps (Sept 2026)
- routes/survival.py does not exist; survival features live in routes/hunter.py (blackout snapshot, survival items/runway, bible.pdf) and routes/seal.py (ghost). Audit: (2) Survival Bible PDF works (200, 36 KB); (3) Ghost Mode exists (ghost-mode.tsx, /ghost/toggle anonymized patient token); (4) Blackout screen exists (blackout.tsx, offline snapshot cached in AsyncStorage); (5) Panic Gesture exists (src/panic-gesture.ts back-tap accelerometer → Silent Witness SOS, configurable taps in profile) — deliberately NOT tier-gated (life-safety).
- Added (1) Crisis Protocols: GET /survival/protocols (6 protocols: blackout, medical, evacuation, heatwave, pandemic, cyber; per-user done[] + progress from db.crisis_checks) + PUT /survival/protocols/{pid}/steps/{idx} toggle. Screen app/crisis-protocols.tsx (accordion, checkboxes, progress bars; testIDs crisis-screen, cp-proto-*, cp-toggle-*, cp-step-<pid>-<i>, cp-paywall). Tiles lw-crisis (Legacy tab) + ht-crisis (Hunter tab). 4 i18n keys crisis.* in 14 locales.
- Sentinel+ gates added: /survival/protocols, /survival/bible.pdf, /blackout/snapshot, POST /ghost/toggle (402). Frontend Paywall tier="sentinel" on 402 in crisis-protocols (cp-paywall), blackout (bo-paywall), ghost-mode (gh-paywall); Health-hub bible tile → /subscription on 402.

## Iter 72 — Jarvis voice picker + ElevenLabs (Sept 2026)
- Emergent-managed OpenAI TTS was already integrated (tts-1 via EMERGENT_LLM_KEY). Added: GET /voice/voices (9 OpenAI voices + ElevenLabs account voices), user prefs voice_engine / jarvis_voice / eleven_voice_id (PATCH /me/prefs), /voice/tts resolves the user's Settings voice server-side (request `override:true` = exact engine/voice for previews). ElevenLabs engine (eleven_multilingual_v2, AsyncElevenLabs, ELEVENLABS_API_KEY in backend/.env) with automatic fallback to OpenAI. Settings UI: "HLAS JARVISA" chips prof-voice-<id> (tap = preview + save), ElevenLabs switch prof-voice-engine + voice chips prof-eleven-<id>.
- KNOWN: ElevenLabs Free Tier blocks TTS from datacenter IPs ("detected_unusual_activity … Free Tier access has been disabled") → falls back to OpenAI; voices listing works (21). Needs a paid ElevenLabs plan (Starter) to work from the server.

## Iter 73 — Offline protocols · Seasonal reminder · Loyalty milestones · Demo mode (Sept 2026)
- (1) crisis-protocols.tsx caches protocols in AsyncStorage (ga.crisis.protocols.v1), serves cache when API fails, offline ticks applied locally + queued (ga.crisis.pending.v1) and replayed on next online load; indicator cp-offline ("Available offline ✓" / "Offline — showing your saved copy"). auth.tsx now caches the user profile (ga.user.cache.v1) and restores it on cold start without network (otherwise blackout → login screen).
- (2) src/seasonal-reminder.ts: 4 yearly local notifications (1 Mar/Jun/Sep/Dec 09:00, expo-notifications YEARLY trigger, data.category crisis-seasonal) scheduled only while ≥1 protocol unfinished, cancelled when all complete; re-synced on every load/tick; i18n crisis.seasonal_reminder_<season> in 14 langs. Native only (web skipped).
- (3) routes/loyalty.py: 3/6/12 months on paid tier (from tier_started_at; set now if missing) → 50/150/500 GA-T (ledger activity loyalty_milestone) + badge Loyal Guardian / Sentinel Veteran / Archangel Legend stored in users.loyalty_milestones[] + loyalty_badge. GET /loyalty, POST /loyalty/seen; check runs inside GET /subscription (response.loyalty). Profile: badge prof-loyalty-badge + one-time congratulation (Alert / web alert) → seen.
- (4) DEMO_ONLY routes/demo_mode.py: POST /demo-mode/start (30 min), /stop, GET status; users.demo_until honoured by current_tier() → archangel while active → every gate open; auto reset on expiry. Frontend src/DemoMode.tsx banner "DEMO MODE — Sovereign Access (mm:ss)" (demo-banner, demo-stop) mounted in _layout; buttons pw-demo (Paywall) + sb-demo (subscription.tsx). Verified: paywall → demo → protocols unlocked → 402 again after expiry.

## Iter 74 — Judge Quick Tour (Sept 2026)
- src/judge-tour.tsx (DEMO_ONLY): external store + JudgeTourOverlay mounted in _layout. startJudgeTour(refresh) → activates DEMO MODE, navigates through 9 stops × 20 s = 3:00 (jarvis, magic-lens, nearby-care, crisis-protocols, (tabs)/family, bioscan, protocol, health-timeline, subscription), narrates each pitch with the user's Jarvis voice, auto-advances with countdown; controls jt-prev / jt-pause / jt-next / jt-end; testIDs judge-tour, jt-title, jt-timer. Entry points: Profile → Demo mode section prof-judge-tour; subscription.tsx sb-judge-tour. 23 i18n keys judge_tour.* in 14 locales.

## Iter 75 — Cinematic Intro + Onboarding cards (Sept 2026)
- src/LaunchSequence.tsx mounted in _layout: CinematicIntro (EVERY start) → OnboardingCards (FIRST launch only, AsyncStorage ga.first_launch.done.v1).
- src/CinematicIntro.tsx: #000 canvas, SVG archangel silhouette (white body, gold wings) sweeps L→R via Animated, headline "The world is changing. Are you ready?" fades in, SVG Archangel logo mark + "GUARDIAN ANGEL" + gold "Sovereign Health & Survival OS", gold-border "ENTER THE SYSTEM", auto-skip 5 s. Ambient sound intentionally not shipped (default OFF per spec). testIDs cinematic-intro, intro-headline, intro-enter.
- src/OnboardingCards.tsx: 4 paged cards (heart / shield / coin / join), progress dots, SKIP top-right, NEXT, card 4 "GET STARTED FREE" + "I ALREADY HAVE AN ACCOUNT" (both set flag → /login). testIDs onboarding-cards, ob-card-N, ob-dot-N, ob-next, ob-skip, ob-get-started, ob-have-account. 16 i18n keys intro.* / onboarding.* in 14 locales.

## Iter 76 — Expo Go startup freeze fix (Sept 2026)
- Root cause (Expo Go only): RootLayout returned null until `useIconFonts()` downloaded ~20 icon TTFs from cdn.jsdelivr.net (StoreClient path) — slow/blocked CDN = splash forever. Web never runs that path (hence worked). Fix: `ready = loaded || error || timedOut(3 s)` then SplashScreen.hideAsync().catch. Also isFirstLaunch() 3 s AsyncStorage race → false; LaunchSequence treats unknown flag as not-first (never null-locks). No Lottie/expo-av anywhere. testing_agent iteration_64.json: all startup scenarios pass, no regressions.

## Fork physio-lang-fix — Jarvis voice + latency (June 2026)
- **ONE voice preset app-wide**: OpenAI TTS-1 `onyx`, speed 0.9 (deep, slow, authoritative). Backend `_resolve_voice` now ignores per-screen `voice` hints (only Settings preview `override` wins); founder's DB pref reset sage→onyx. ElevenLabs settings tuned (stability 0.7, style 0.1, timeout 15s). Frontend `JARVIS_PRESET` in `src/voice.ts`; `jarvis.tsx` MOOD_VOICE removed (uses `mood` pacing from voice.ts); remaining hardcoded `nova` callers switched to `onyx`.
- **Streaming TTS**: `speakStream()` in `src/voice.ts` — sentences cut from the SSE token stream, audio prefetched in parallel, played in order; used for voice turns in `jarvis.tsx`.
- **Latency**: `_gather_context` (17 queries) + `_chat_system` (4 lookups) now `asyncio.gather`; LLM stream timeout 12s first token / 20s per token; 5-min in-memory reply cache for identical questions (`/agent/chat/stream`, `cached: true`); "JARVIS is processing… Ns" liveness status after 1s in `jarvis.tsx`.
- Pending (user deferred): expo-notifications static imports still crash Expo Go (6 files) — NOT touched per user instruction.

## Fork physio-lang-fix — batch 2 (June 2026): Expo Go crash · full-duplex · live TTS · intro voice
- **Expo Go crash fixed**: `src/notifications.ts` = the only loader of `expo-notifications` (lazy `await import`, null in Expo Go via `Constants.executionEnvironment === 'storeClient'`/`appOwnership === 'expo'` and on web). Rewired `_layout.tsx` (handler + Android channel + tap listener now inside a guarded effect), `push.ts`, `seasonal-reminder.ts`, `meds.tsx`, `daily-brief.tsx`, `my-recovery.tsx`. Zero static imports remain.
- **Full-duplex hands-free** (`src/duplex.ts` + `jarvis.tsx`, native only, Expo Go-compatible): barge-in monitor meters the mic while Jarvis speaks (learns loudspeaker echo level over first 700 ms of real playback, triggers at echo+8 dB / ≥ -26 dBFS for 2 polls) → stops narration, aborts stream, opens mic; end-of-turn = 1.3 s silence after speech → auto-send; 7 s no speech → mic closes. After each voice reply the mic reopens automatically. Toggle chip `jv-duplex` (persisted `jarvis.duplex`, default ON). `voice.ts` exposes `isPlayingNow()/playedMs()`. Wake-word start race guarded (`_startSeq`).
- **Live TTS relay**: `POST /voice/tts {stream:true}` → ticket URL `/api/voice/tts/live/{id}.mp3` streamed while ElevenLabs Flash v2.5 (`optimize_streaming_latency=3`, `language_code`) / OpenAI proxy render; finished bytes cached under the normal key. `speak()` and the first clip of `speakStream()` use it (no second download round-trip). ⚠️ ElevenLabs account currently returns `detected_unusual_activity` (free tier disabled) → automatic OpenAI fallback; needs a paid ElevenLabs plan to hear ElevenLabs voices.
- **Intro narration**: public `GET /api/voice/intro.mp3?lang=xx` (fixed JARVIS script in 11 languages, cached); `CinematicIntro` plays it via `speakUri()`, shows ⏭ SKIP (`intro-skip`) while narrating, ends with the voice (cap 14 s) or 5 s if voice never starts. New i18n keys in all 14 locales.

## Fork physio-lang-fix — MEGA BATCH A–K (June 2026)
- **A Spider Hub** (`src/SpiderHub.tsx`, rendered by `(tabs)/index.tsx`; "Classic" node → old dashboard, `back-to-hub` chip returns): centre ARCHANGEL + 4 module nodes (Health/Survival/Market/Jarvis) on gold SVG threads; tap → sub-modules fan out; top rail = neighbours. Senior mode: 4 subs, 112px nodes.
- **B User type** (`app/user-type.tsx`, `src/user-type.ts`, `PUT /me/user-type`; adult/senior/clinician/responder/child). Home redirects to it when `user.user_type` missing; Settings row `user-type-btn`. `useUserType().fs()` scales fonts (senior 1.6×, headlines 3×).
- **C Health Card** (`app/health-card.tsx`, `GET/PUT /health-card` → `health_cards`): tabs ID & CARDS (birth cert, EU card + insurance no./insurer) · RECORDS (vault docs, OCR summary, expandable) · INSURANCE (contracts CRUD + claims from `insurance_claims`); "Scan Document" → `/lens?category=`.
- **D Jarvis+Lens merge**: hub unified input (text → `/jarvis?q=`, mic → `/jarvis?voice=1`, photo → upload `/vault/documents` → `POST /agents/run`), result sheet with agent trace; jarvis.tsx consumes `q`/`voice` params.
- **E Multi-agent** (`routes/features.py`): `GET /agents/status`, `POST /agents/run` pipeline LENS(OCR)→SCRIBE(archive to calendar_events)→ANALYST(LLM)→GUARDIAN(crisis keywords)→JARVIS(reply). Tier map (app tiers): sovereign=Jarvis · guardian=+Lens · sentinel=+Scribe+Analyst · archangel=all 5 + priority (gpt-5.4 vs mini). `ActiveAgents` strip on hub.
- **F Bunker** (`app/bunker.tsx`): OSM shelters (`/nearby/care?kind=shelter`, new Overpass filters) + 72h checklist (AsyncStorage). Gate: sentinel or `bunker` purchase.
- **G Offline Mesh** (`app/offline-mesh.tsx`, `src/mesh-radio.ts`): ≤160 chars, store-and-forward, hop/TTL, peers strip. Transport = SIMULATION in Expo Go/web; native build registers BleManager on `globalThis.__archangelBle` (react-native-ble-plx not installed — needs dev build). Gate `mesh_sms`.
- **H Pay-per-feature** (`GET /features/catalog`, `POST /features/buy {feature, currency gat|eur}` → `users.features_owned`, `feature_purchases`): ghost_mode €2.99/30 GA-T, bunker €1.99/20, analyst €3.99/40, mesh_sms €1.49/15. `src/FeatureGate.tsx` = Paywall + "buy only this feature". EUR path records revenue (no card sheet yet).
- **I Creator royalty**: `creator_royalty()` 5% on `/token/spend` and `/features/buy` → `creator_royalties` log + GA-T credit to `users.creator_account=true` (founder flagged). `GET /creator/earnings`, `app/creator-earnings.tsx` (profile row for creator/admin).
- **J Demo fix**: DemoBadge removed from `_layout`, badge switch removed from profile; demo only via Paywall "DEMO MODE · 30 MIN"; `DemoBanner` countdown + auto refresh on expiry (backend `demo_until`).
- **K Golden Supernova intro**: `CinematicIntro.tsx` rewritten with Animated API only (2px gold point → gold/white wave → white flash → "ARCHANGEL OS / VISION BY GUARDIAN ANGEL / Sovereign Health & Survival OS" → fade); narration + skip kept.

## Entry-flow fix (June 2026)
- 4 standalone screens: `app/choose-language.tsx` (step 1, `markLangChosen` in `src/entry-flow.ts`, persisted `ga.lang.chosen.v1`) → `/login` (language chips removed; `change-language` link) → `/user-type` (guard in `_layout.tsx` when `user.user_type` missing) → `/(tabs)` Spider Hub. Router guard in `_layout.tsx` RootNav uses `useLangChosen()` (in-memory + AsyncStorage, no race).

## Plans & Store (June 2026)
- `app/store.tsx` (PLANS: 4 tiers + Duo/Family/Family XL with monthly/yearly toggle, RevenueCat `IapBuyButton` per plan — packages `duo_monthly`… added to `IAP_PACKAGES`/`iapTierOf`; backend `iap_family_plan()` sets `users.family_plan` on sync; promo `ARCHANGEL2026` → 1 month Sentinel via `POST /store/promo` (no downgrade of higher tiers); ADD-ONS: one-time + monthly boosts `POST /store/addon/buy` → unlock + hidden GA-T mint + revenue + creator royalty). No Stripe.
- Hidden crypto layer: Settings → Advanced → Blockchain & Tokens (`app/blockchain.tsx`: balance, ledger, transfer `POST /store/transfer`, link to /token marketplace).
- Navigation: hub Market node "Plans & Store", profile row `store-btn`. Catalog hides GA-T bullets.
- Note: family packages appear as "unavailable" until they exist in the RevenueCat current offering.

## Spider → Cascade → Pavučina + visual lift (June 2026)
- `src/feature-map.tsx`: single source of 5 arms (Health, Safety, AI, Community, Store × 6 sub-features) + `AngelMark` SVG (halo + wings). `src/ui/Cascade.tsx`: `Cascade` (staggered fall-in 560 ms, 90 ms step) + `Breathe` (slow glow loop).
- `src/SpiderHub.tsx` rewritten: Guardian Angel centre with breathing halo, glass nodes (`expo-blur` BlurView, rgba fallback on web), arms grow from centre on focus change, sub-features cascade in; rail includes "WEB VIEW". Unified Jarvis input + agents sheets kept.
- `app/web-map.tsx` (Pavučina): fullscreen 720px+ scrollable golden web — centre, 5 arms on inner ring, 30 sub-features on outer ring by sector, concentric polygons, shimmer glow loop, cascade entrance; tap = open. Centred on load.
- Theme already midnight (#050510) + gold; hub/web use #03030A deep-space bg.
- PENDING user answer: GA-T on-chain deploy (deployer key, Base Sepolia vs mainnet, supply, migration) — asked, no reply yet.

## Iter 77 — ChatGPT AI Models + P0 security hardening (June 2026)
- **ChatGPT models for Jarvis** (`routes/ai_models.py`): catalog gpt-5.4-mini · gpt-5.4 (default) · gpt-5.6-luna (Guardian+) · gpt-5.6-terra (Sentinel+), Emergent LLM key. `GET /ai/models` (locked/active per tier), `PUT /ai/models/select` (400 unknown / 402 tier gate) → `users.jarvis_model`. `resolve_model(user)` used by /agent/chat, /agent/chat/stream (reply cache keyed by model; `model` in response + SSE done event), /agent/briefing and the multi-agent pipeline (priority tiers only; others gpt-5.4-mini). Lapsed tier → silent fallback to default. Frontend `src/ModelPicker.tsx`: Settings section "JARVIS AI MODEL" (`prof-model-<id>`, `prof-model-msg/upgrade`) + Jarvis pill `jv-model` → sheet `jv-model-sheet` / `jv-model-<id>` (CHAT mode). i18n keys `ai_models.*` (en+sk; others fall back to en). Verified live: Luna + Terra answer.
- **SEC-001 dev-bypass**: `dev_bypass_allowed()` = `DEV_BYPASS_ENABLED=true` in backend/.env AND Host + X-Forwarded-Host on a preview/local domain (`DEV_BYPASS_HOSTS` default preview.emergentagent.com, preview.emergentcf.cloud, localhost, 127.0.0.1). Founder e-mail NO LONGER exempt. Production (any other host) → 403 automatically even if the env flag is left on.
- **SEC-003 password_hash**: `core.clean()` strips it, `get_current_user` uses `USER_PRIVATE_PROJECTION`, /auth/session + /me/prefs + recovery_suite session returns sanitised.
- **Atomic GA-T**: `token.debit_balance(user_id, amount)` = single conditional `$inc` (`balance >= amount`); used by /token/spend (royalty now AFTER a successful debit), charge_tokens, /features/buy, /store/addon/buy, /store/transfer; award_tokens treasury decrement conditional. Verified 40 concurrent spends on 12 GA-T → exactly 24 succeed, balance 0.0.
- **No unverified fiat unlocks**: /features/buy `currency=eur` → 400; /store/addon/buy now costs GA-T (`price_gat` = EUR×10, 2 % burn, 5 % creator royalty, ledger spend+burn), catalog exposes `price_gat`; store.tsx shows GA-T price, FeatureGate EUR button removed.
- **IP rate limits** (`core.rate_limit`, in-memory sliding window, env override `RATE_LIMIT_<BUCKET>_PER_MIN`): login 20/min/IP + 20/min/e-mail, register 10, dev-bypass 30, forgot-password 5, reset-password 10, /voice/tts 30/min/IP + per user, /voice/intro.mp3 10, iap-sync 60/user. 429 + Retry-After.
- **RevenueCat server-side verification — NOT POSSIBLE via Emergent-managed RC**: playbook forbids backend RC REST/webhooks (no secret key exposed) and the proxy `/products` requires `period` (subscriptions only → one-time add-on products rejected with 400). Applied instead: iap-sync payload whitelist (product id must start with `pro.`, store whitelist, app_user_id required, identity match 409), per-user rate limit, AML ledger with IP. Add-ons sold for GA-T only.
- Tests: `tests/test_iter77_models_security.py` (15 pass). Pre-existing unrelated failures: test_password_auth register (no tos fields), phase15 wallet earn-rule count / royalty-to-self, iter66 creator 403 (founder is creator).

## Iter 78 — SafeArea fix + GA-T Community Help (peer-verified)
- **SafeArea**: tab bar height = 60 + max(insets.bottom, 20 iOS / 10 Android) with matching paddingBottom (`(tabs)/_layout.tsx`), GuardianEyeFAB offset follows; all 85 standalone screens switched `edges={['top']}` → `['top','bottom']` so scroll content and absolute FABs (meds, marketplace, gigs…) stay above the home indicator / gesture bar. Tab screens keep top-only (tab bar owns the bottom).
- **Community Help** (`routes/community_help.py`, collection `help_requests`): POST /help/requests (escrow 10 GA-T: wallet first via atomic debit, Community Fund = treasury covers the rest → `token_supply.community_escrow`), GET /help/requests?scope=open|mine|helping|all (+limits, community_fund), /accept (409 if taken, 400 own), /done (helper only, starts 24 h window + push to requester), /confirm (requester only, 5/day, pays helper — ledger `help_reward`, push to helper), /cancel (own open only → refund). `expire_help_requests()` sweeps (list call + swarm loop every 15 s): open > 7 d or done > 24 h → `expired` + refund (`help_refund`). Daily caps: 5 requests, 5 confirmations.
- **Self-claim blocked**: POST /token/earn with `proof_of_help` / `community_support` → 403 `verified_only` (system-triggered awards from gigs completion-by-requester and pulse-check replies remain). Wallet screen shows "OPEN" → /community-help for those rules.
- Frontend `app/community-help.tsx` (testIDs help-new, help-new-title/details/cat-*/submit, help-tab-open|mine|helping, help-accept/done/confirm/cancel-<id>, help-msg), feature-map Community arm → 'Community Help' first sub. i18n `help.*` en+sk.
- Tests: `tests/test_iter78_community_help.py` 5/5 (self-claim 403, full flow + double-confirm safe, fund top-up + cancel refund, daily cap 429, 24 h expiry refund).

## Iter 79 — Recurring add-ons as RC subscriptions · Helper reputation · Security (SecureStore, remove-console, root detection)
- **Add-on subscriptions**: RC packages `addon_perplexity_ultra_monthly` (€5/P1M) + `addon_premium_voice_monthly` (€3/P1M) created via proxy (product ids `pro.addon_*`). Same single "pro" entitlement → frontend `iap-mirror.ts` now sends `active_subscriptions` (CustomerInfo.activeSubscriptions + allExpirationDates); `revenuecat.tsx` activeTier ignores addon products (add-on-only ⇒ activeTier null, isSubscribed false), exposes `activeAddonPackages`. Backend `subscription.py` iap-sync: add-ons → `store.sync_addon_subscriptions` (users.addon_subs[id]={status active|expired, expires_date, will_renew, source iap}, addons_active[id]=expiry), tier from best non-addon product; legacy single add-on payload → `addons_synced` without touching tier; add-on-only active ⇒ IAP tier lapses. `store.addon_active()` = server-side lifecycle (expiry + 72 h grace) — used by catalog, `GET /store/addons/status`, and `/voice/tts` (ElevenLabs only with Premium Voice add-on or Sentinel+, else silent OpenAI fallback). `/store/addon/buy` for recurring → 400 subscription_only. `IapBuyButton` gained `pkgId/label/active` props (testIDs `iap-buy-<pkgId>` / `iap-active-<pkgId>`); store.tsx MONTHLY BOOSTS render RC buttons with Renews/Expires date.
- Limitation unchanged: no RC secret key/webhook in Emergent-managed RC → "server-side" = server-enforced lifecycle of client-reported RC data (whitelisted, identity-matched, rate-limited), not receipt validation.
- **Helper reputation** (`community_help.py`): `helper_reputation()` aggregates CONFIRMED requests per helper → {completed, badge bronze≥1/silver≥5/gold≥20, earned_gat, next_badge}; attached as `helper_reputation` on every request with a helper, `my_reputation` + `badges` in list response, `GET /help/reputation/{user_id}`. UI: `HelperBadge` on cards (`help-badge-<req_id>`) + header (`help-my-badge`).
- **Security**: `src/secure-cache.ts` (chunked SecureStore JSON, web → AsyncStorage fallback) now holds the offline user snapshot (auth.tsx, key ga.user.cache.v2, legacy plaintext purged), blackout snapshot, compass pack. Session token was already in SecureStore. `babel.config.js` strips console.* (except error) in production builds via babel-plugin-transform-remove-console (devDependency). `src/DeviceIntegrity.tsx` runs `Device.isRootedExperimentalAsync()` at startup → warning modal (`device-integrity-warning` / `-continue`) + `POST /security/device-integrity` (users.device_integrity, security_events `rooted_device`). Play Integrity / App Attest = follow-up needing native build + Google Cloud project number / Apple App Attest config.
- Tests: `tests/test_iter79_addon_subs_reputation.py` 5/5; test wallet funding now writes Mongo directly (founder wallet can be drained).

## Iter 80 — Deployment readiness (pre-publish)
- deployment_agent fixes: `.gitignore` no longer excludes `.env` files; `frontend/.env` METRO_CACHE_ROOT quoted; `news.py` background retention soft-archives (`archived: true`) instead of delete_many; `arbitrage.py` seed upserts deterministic clinic_ids (no delete_many({})).
- Remaining agent finding "add react-native-purchases config plugin to app.json" is a FALSE POSITIVE (package ships no Expo config plugin; adding it breaks prebuild) — intentionally not applied.
- Known warnings: google-services.json placeholder + no iOS GoogleService-Info.plist (push not configured — needs user's Firebase files); AUTH_SESSION_URL env fallback (Emergent auth default). `/api/voice/stt` is mocked (native STT pending).
- Deployment itself is done by the user via Publish → Deploy your app (agent cannot deploy). Production: DEV_BYPASS host gate makes /auth/dev-bypass 403 on non-preview hosts.

## Iter 81 — Founder e-mail rename · Native live STT under the orb · GA-T on-chain bridge (Base L2)
- **Founder e-mail** → `guardianangel.core@proton.me` everywhere (36 files incl. backend/.env FOUNDER_EMAIL, seal.py FOUNDATION_EMAIL, tests, memory). DB migrated in place (`backend/scripts/migrate_founder_email.py --apply`): same user_id `user_ac98119726d0`, `inner_circle` updated; old address is now an ordinary account.
- **Live STT** (`src/live-stt.ts` + jarvis.tsx): `expo-speech-recognition` (57.0.0, config plugin + NSSpeechRecognitionUsageDescription in app.json). When the native module is available (dev/prod build, or web Chrome via Web Speech API) the orb uses on-device recognition: partial words render under the orb (`jv-live-transcript`), `continuous:false` auto-ends on silence → final transcript → sendMessage; orb tap = stop() flush; STOP/cancel = abort(). Permission flow: check → ask once → blocked ⇒ existing mic-denied UI with Open Settings. Expo Go (module absent) ⇒ unchanged recorder → Whisper path. i18n `jarvis.live_stt_*`.
- **GA-T on-chain** (`contracts/GAT.sol`, `routes/chain.py`): ERC-20 "Guardian Angel Token" GA-T, cap 1 000 000 000, constructor mints 25 % to founder wallet `0x0E6693153961c01CEa3e73e4e9596aCF35315567`, `mintFromLedger(to, value, ledgerTx)` (onlyMinter, idempotent per ledger tx). Backend: env `BASE_RPC_URL`, `GAT_CONTRACT_ADDRESS`, `GAT_MINTER_PRIVATE_KEY`, `GAT_CHAIN_ID` (8453/84532) — empty ⇒ `mode: queued_until_deploy`. `queue_mint()` is called from `settle_subscription_allocations` (verified RC subscription loyalty GA-T) for users with a linked wallet; `process_mint_queue()` runs in the swarm loop (web3.py 8, EIP-1559, `onchain_mints` status queued→sending→sent). Endpoints: GET /chain/status, POST/DELETE /chain/wallet (checksum validation), GET /chain/mints. UI: blockchain.tsx "ON-CHAIN · BASE L2" card (`bc-chain-mode`, `bc-addr`, `bc-link`, `bc-wallet`, `bc-unlink`, `bc-mint-<id>`).
- To go live: deploy `contracts/GAT.sol` on Base (constructor: founder wallet, backend minter address), then fill the 3 env vars (minter key funded with a little ETH on Base) — queued mints start flowing automatically.
- Tests: `tests/test_iter81_chain_stt_email.py` 3/3. requirements.txt refreshed (web3 8.0.0).

## Iter 82 — Security audit remediation (audit verdict was FAIL → fixed)
- **SEC-001 (Critical)**: `/auth/dev-bypass` now refuses Founder / inner-circle / archangel accounts (403) in addition to the env+host gate → the bypass can never mint a privileged session. Founder signs in with a password (bcrypt hash set in DB, credential in memory/test_credentials.md; changeable via Forgot password) or Google. login.tsx founder button only prefills the e-mail into the password form. Tests use `_founder()` (password login) instead of `_bypass(FOUNDER)`.
- **SEC-002 (High)**: temporary `/api/export/*` source endpoints REMOVED from server.py (zip export remains at /app/export/archangel-os-source.zip for GitHub export).
- **SEC-003 (Medium)**: `/register-push` requires a session and `user_id` must equal the caller (frontend push.ts sends the bearer). Notification hijack closed.
- Hardening: CORS `allow_credentials=False` with wildcard origins (bearer-only API); social recovery requires ≥2 guardians and always 2 approvals.
- Password-hash leakage (previous SEC-003) confirmed PASS by the audit.

## Iter 82b — Second security audit (all previous findings PASS) → new findings fixed
- **UHP partner injection (High)**: `/uhp/partners/register` now creates PENDING partners; ingest requires an ACTIVE partner (Foundation approves via `POST /uhp/partners/{id}/approve`, `GET /uhp/partners/pending`, `POST …/suspend`; founder/inner-circle only) AND explicit patient consent (`uhp_consents`: `GET/POST /uhp/consents`, `DELETE /uhp/consents/{partner_id}`); missing subject or consent → uniform 403 `consent_required` (no enumeration). UI: Settings → "HEALTH PARTNERS" (`src/HealthPartnerConsents.tsx`, `uhp-consent-<partner_id>`), partners.tsx shows `pt-pending` notice.
- **Founder auto-assign (Medium)**: swarm janitor binds `is_founder`/`inner_circle`/archangel ONLY to FOUNDER_EMAIL and strips `is_founder` from any other account (DB cleaned).
- **Clinic beam brute force (Low)**: code is now 12 hex (48 bit) + `rate_limit(..., "clinic_beam")` 10/min per IP.
- Founder password is user-chosen; stored only as bcrypt in DB and as `FOUNDER_TEST_PASSWORD` in backend/.env (tests read via dotenv; no plaintext in memory/ files).
- Tests: `tests/test_iter82_reaudit.py` 3/3.

## Iter 83 — Partner Approval Panel (Founder)
- New Founder-only screen `frontend/app/partners-admin.tsx` (route `/partners-admin`, entry: Profile → FOUNDER ADMIN box → `partners-admin-btn`). Loads `GET /uhp/partners/admin` (already Founder/inner-circle gated, secrets never returned; buckets pending/active/suspended + counts + consent counts).
- Tabs `pa-tab-{pending|active|suspended}` with live counts (`pa-count-*`), search box `pa-search` (name / e-mail / country / type / id), pull-to-refresh, empty states (`pa-empty`), 403 → "FOUNDATION ONLY" (`pa-forbidden`).
- One-tap actions per card `pa-row-<partner_id>`: pending → APPROVE (`pa-approve-<id>` → POST …/approve) / REJECT (`pa-suspend-<id>` → POST …/suspend); active → SUSPEND; suspended → REACTIVATE (approve endpoint). Optimistic bucket move + `pa-msg` confirmation; errors via `pa-err` and silent reload.
- i18n `partners_admin.*` in en.json + sk.json (other languages fall back to English). Business rule confirmed by user: self-registered partners = PENDING until approved.
- Backend unchanged (endpoints from Iter 82b). Note: handoff claimed `/api/export/*` still exist — they were already removed in Iter 82.

## Iter 84 — Subscription price update (Sentinel €99/€950 · Archangel €299/€2990)
- User request: Sentinel €149→€99/mo, €1,490→€950/yr; Archangel €499→€299/mo, €4,990→€2,990/yr. GA-T prices unchanged (250 / 800).
- Backend: `routes/subscription.py` TIERS (`_prices(99,250,eur_year=950)`, `_prices(299,800,eur_year=2990)`; CZK derived), `recommend.py`, `bioscan.py` 402 text, `founder.py` TIER_MIX (forecast ARPU now €33). Tests updated: test_iter62_iap_tiers (6/6), test_phase18, test_iter25.
- Frontend: `src/Paywall.tsx` tier strings; 14 locales `founder_toolkit.tier_mix_*` text; store/subscription/paywall prices come from `/subscription` + RevenueCat offerings (no other hardcodes). `release_package/tools/jury_pdf.py` text updated (PDF not regenerated).
- RevenueCat: Test Store products are immutable → new packages `sentinel_monthly_v2 / sentinel_annual_v2 / archangel_monthly_v2 / archangel_annual_v2` (products `pro.*_v2`, EUR, attached to `pro`); old packages detached from the `default` offering (products with test transactions can't be deleted → 422, harmless). `src/revenuecat.tsx` IAP_PACKAGES → v2 keys. Verified in web preview: store buttons €99.00 / €950.00 (monthly / yearly).
- Store-side (user, before real purchases): create App Store Connect / Google Play products with the NEW ids `pro.sentinel_monthly_v2`, `pro.sentinel_annual_v2`, `pro.archangel_monthly_v2`, `pro.archangel_annual_v2`.

## Iter 85 — Deployment readiness fixes (deployment_agent blockers)
- **On-chain library removed from the app** (Emergent stack policy): `routes/chain.py` has no chain-library import — EIP-55 validation/checksum via a pure-Python keccak-256; the app only writes `onchain_mints` with `status: "queued"`. In-app sender + swarm drain deleted. External worker packaged as `export/gat-mint-worker.zip` (mint_worker.py + README + requirements; pymongo + web3 installed on the Foundation VPS; env MONGO_URL, DB_NAME, BASE_RPC_URL, GAT_CONTRACT_ADDRESS, GAT_MINTER_PRIVATE_KEY, GAT_CHAIN_ID; lifecycle queued→sending→sent→confirmed/failed). `external/` plain-text folder removed at user request; `.dockerignore` excludes `export/`.
- **AUTH_SESSION_URL**: `core.py` reads it exclusively from backend/.env (empty ⇒ startup warning, no hardcoded fallback). Other Emergent integration constants (email/push/storage/Perplexity) intentionally untouched.
- tests/test_iter81_chain_stt_email.py 3/3 still green.

## Iter 86 — Security audit remediation (round 3)
- **SEC-001 (HIGH) fixed — server-side IAP verification.** `/subscription/iap-sync` now treats the device payload only as a trigger: `rc_verified_subscriptions()` (routes/subscription.py) GETs `https://api.revenuecat.com/v1/subscribers/{uid}` with the PUBLIC SDK keys (`REVENUECAT_PUBLIC_KEY_TEST/IOS/ANDROID` in backend/.env — same values as the frontend EXPO_PUBLIC_* keys; read-only, no secret key, no provisioning) and replaces product/expiry/store/period claims with RevenueCat's data (`pro.*` whitelist + entitlement `pro` must be active). RC unreachable → 503 `iap_verification_unavailable` (never falls back to the client). Verified: forged archangel claim → `noop`, tier sovereign, GA-T unchanged; real Test Store purchase (web preview, RC dialog) → GUARDIAN granted with RC expiry. Legacy tests relying on forged payloads are skipped with reason (iter60, iter62, parts of 63/79/81); new `tests/test_iter86_security.py` 6/6.
- **SEC-002 (HIGH) fixed — secrets hygiene.** `FOUNDER_TEST_PASSWORD` removed from backend/.env (tests read it from the process env / skip). `CONTACTS_ENC_KEY` rotated: new primary + `CONTACTS_ENC_KEY_PREV` decrypt-only via `MultiFernet`; `family_contacts.rotate_contact_keys()` runs at startup and re-encrypted all 5 stored phones (old key can no longer decrypt them) — remove `*_PREV` from .env after the first production boot. `export/archangel-os-source.zip` regenerated from current source WITHOUT `.env`, `memory/`, `google-services.json`, caches. User should rotate the founder password (old value was inside the previous ZIP).

## Iter 87 — Deployment "Building Package" failure: root cause + fixes
- ROOT CAUSE (most likely): committed `frontend/yarn.lock` was stale vs committed `package.json` (expo-speech-recognition + babel-plugin-transform-remove-console added 2026-09-04 without the lockfile) → `yarn install --frozen-lockfile` fails in CI. Fixed: `yarn expo install --fix` (expo ~57.0.20, expo-router ~57.0.19, expo-notifications ~57.0.17, expo-location/image-picker ~57.0.16, expo-sharing ~57.0.18), lockfile + package.json committed (4e023b2). `--frozen-lockfile` verified green; `npx expo export --platform web` passes locally (8.4 MB bundle).
- Also: stray `backend/*.whl` (incl. py_solc_x) + `server_monolith.bak` deleted; `.dockerignore` now excludes export/, frontend/node_modules, frontend/.metro-cache (542 MB), frontend/.expo, **/__pycache__, test_reports/, *.whl; dev tools removed from `backend/requirements.txt` (playwright, black, mypy, flake8, isort, pytest*) → `backend/requirements-dev.txt` holds pytest/pytest-asyncio/pytest-xdist for local runs (`pip install -r requirements-dev.txt`; NEVER `pip freeze` straight into requirements.txt while dev tools are installed — regenerate with them uninstalled or filter them out).
- Health check after fixes: status WARN (no blockers): stack ok, compile ok, manifests valid, .dockerignore ok. Warnings = Firebase placeholders (user files pending), Emergent integration base URLs as constants (per playbooks), reviewer credentials doc.
- Secondary risk noted for support if it still fails: project moved Expo SDK 54 → 57 on 2026-09-04 (RN 0.86.3 needs Node ≥ 20.19.4); pod env image is `expo_mongo_base_image_cloud_arm:release-19082026-1`.

## Iter 88 — Jarvis mic fix + subscription gating rules (user request + addendum)
**Fix 1 — Jarvis "always listening"** (`app/jarvis.tsx`, `src/live-stt.ts`)
- Root causes: hands-free duplex defaulted ON (mic re-opened after every reply) and the wake-word monitor kept the mic open whenever idle. Now BOTH are opt-in (default OFF, persisted `jarvis.duplex` / `jarvis.wakeword`; new chip `jv-wakeword`).
- `releaseMic()` = single mic-release path (abort live STT, stop recorder + wake recorder, stop barge-in, `setAudioModeAsync({allowsRecording:false})`) — called after every finished reply (unless duplex is on), on STOP (`stopAll`), on silence, on unmount. live-stt `stop()` now hard-aborts if the engine emits no 'end' within 3 s; 'error' cleans up listeners (no double onEnd).
- State badge under the orb `jv-state-{listening|processing|speaking|idle}` (i18n `jarvis.state_*`, en+sk).
**Fix 2 + addendum — tier gating** (`backend/routes/features.py`, `seal.py`, `ascension.py`, `subscription.py`, `agent.py`; `src/FeatureGate.tsx`, `src/Paywall.tsx`, `app/mesh.tsx`, `app/monolith.tsx`)
- `TIER_FEATURES`: bunker + mesh_sms → Sentinel+, 90-day grace, emergency; twin → Archangel, 14-day grace. Removed bunker/mesh_sms from one-off `FEATURES` (buy → 400 "subscription-only"; previously bought one-offs grandfathered). `tier_feature_states()` computes unlocked/in_grace/grace_until/offline_until from tier, tier_until (or `tier_last_paid`/`tier_last_until`, now written on IAP downgrade + cancel). `require_feature()` gates `/mesh/*` (402 sentinel_required) and `/twin/*` (402 archangel_required). `/features/catalog` returns both lists (`purchasable` flag).
- Frontend `FeatureGate`: no one-off box for `purchasable:false` (explanatory note instead), Paywall tier archangel for twin (Paywall got `archangel` variant; 7-day Sentinel trial button hidden there), grace banner, **offline cache** (`feature_cache.<id>` in AsyncStorage with server `offline_until`; used when the catalog call fails → Bunker/Mesh work without internet or payment check; cleared when the server says grace is over). `app/mesh.tsx` (Hunter/Legacy "Mesh Messages") now gated like `/offline-mesh`; `app/monolith.tsx` Twin section wrapped in `FeatureGate feature="twin"`.
- Free tier never locks: `agent.py` `jarvis_access()` — Sovereign gets `JARVIS_FREE_DAILY` (default 10) chat/stream messages per day (collection `jarvis_free_quota`), 402 guardian_required only after the quota; premium (voice, Sonar, briefing, premium models) stays Guardian+. `jarvis.tsx` no longer locks the whole screen when the Guardian-only Morning Briefing returns 402; paywall text comes from the server message. SOS (`/sos/broadcast`) has no tier gate.
- Tests: `tests/test_iter88_gating.py` 4/4. Verified in web preview with a free user: /bunker, /mesh, /monolith Twin show the correct paywalls (no one-off), Jarvis chat works with IDLE badge.

## Iter 89 — Public privacy policy URL
- `src/legal.ts` `PRIVACY_POLICY_URL = https://guardianangelcore.github.io/archangel-privacy/` (single source). Linked: in-app Privacy Policy screen (`privacy-public-link` "PUBLIC VERSION · OPEN IN BROWSER"), Profile (`prof-privacy-web`), registration consent (`reg-privacy-web` "(web)"). `app.json` → `expo.extra.privacyPolicyUrl` for store metadata (enter the same URL in App Store Connect "Privacy Policy URL" and Play Console "Privacy policy").

## Iter 90 — Lock Demo Mode · Store-reviewer account · Production billing note (user request)
- **Lock Demo Mode (security).** `POST /api/demo-mode/start` was callable by ANY signed-in account → free 30-min Archangel.
  It is now Founder-only (`_is_founder`) and returns a uniform 403 `not_available` (no role disclosure). Status + `/stop`
  stay open (they can only reduce access). UI: the DEMO MODE / JUDGE TOUR entry points render only for the Founder —
  `subscription.tsx` (`sb-judge-tour`, `sb-demo`, gated on the founder-only `/wealth/founder-dashboard` response),
  `(tabs)/profile.tsx` (`prof-judge-tour`, gated on `admin.is_founder` from `/demo/status`), `src/Paywall.tsx`
  (`pw-demo`, gated on a `/demo/status` lookup).
- **Store-reviewer demo account.** New `backend/reviewer_seed.py`, called from the `server.py` startup hook (idempotent,
  non-fatal). Env: `REVIEWER_EMAIL` (default `appreview@archangel-os.app`), `REVIEWER_PASSWORD` (≥16 chars, env only —
  seed is skipped with a warning when unset), `REVIEWER_ROTATE_PASSWORD` (one-boot rotation, revokes reviewer sessions).
  Grants a permanent server-side entitlement: `tier: archangel`, `tier_until` +10 y, `tier_paid_with: store_reviewer`,
  `is_reviewer: true`, `trial_used: true`, TOS accepted, `language: en`. Explicitly holds `inner_circle`/`is_founder` false
  so no Foundation admin surface (Partner Approval, Wealth Dashboard, Demo Mode) opens for it.
  Sample data (full set, idempotent): `routes/demo.py` was refactored into reusable `seed_lifecard(user)` +
  `seed_presentation_data(uid, did)` helpers (used by `/demo/seed` and `/demo/toggle` too) → Life Card identity
  (DOB 1985-03-15, A+), 7 timeline records + Jarvis prediction, waitlist `slot_found`, €150 dental refund claim,
  answered family pulse, plus one encrypted placeholder family contact.
  Store submission copy: `memory/store_reviewer_access.md`.
- **Production billing note.** `GET /api/subscription` → `billing_note` no longer mentions Stripe TEST mode or card
  4242 ("Subscriptions renew automatically and can be cancelled anytime…"). `app/monolith.tsx` Liquidity Bank card field
  no longer prefills `4242`. `tests/test_iter25_premium.py::test_billing_note_is_production_safe` asserts no test hints.
- **Bonus fix:** `swarm.py` stability audit `token_supply_invariant` was RED because `community_escrow` (carved out of the
  treasury by Community Help) was missing from the invariant → now included; `/swarm/audit` is 9/9 again.
- Tests: `backend/tests/test_iter90_reviewer_demo.py` 8/8. Pre-existing stale assertions in `test_iter25_premium.py`
  (old Guardian GA-T price 50 vs current 15) remain untouched.

## Iter 91 — Real Firebase push config files (user upload)
- User uploaded two pairs of Firebase files (project `archangelos-34c8a`, sender `351191506495`): one pair for
  `com.guardianangelcore.archangelos`, one for `com.emergent.angelos.qvqss9`. The app's `bundleIdentifier`/`package` is
  `com.emergent.angelos.qvqss9`, so that pair was installed:
  - `frontend/google-services.json` — placeholder replaced (Android app id `…android:78518b262c3fb9e3eca28a`).
  - `frontend/GoogleService-Info.plist` — NEW (iOS app id `…ios:4f9114c0d018a048eca28a`); `app.json` → `ios.googleServicesFile`.
- The `com.guardianangelcore.archangelos` pair was NOT used (would only apply if the bundle/package ID is renamed later).
- Push delivery still requires a native build via Emergent **Publish** (not testable in Expo Go / web preview).


## Iter 92 — Security audit fixes (SEC-001 dev-bypass · SEC-002 founder fallback · /docs)
- **SEC-001 (CRITICAL) fixed.** `backend/.env` → `DEV_BYPASS_ENABLED=false`; `routes/auth.py` default `DEV_BYPASS_HOSTS`
  is now `localhost,127.0.0.1` only (preview domains removed) → `POST /api/auth/dev-bypass` is 403 from the preview
  URL and from localhost while the flag is off. Frontend: the "other e-mail / developer bypass" form and `signInDev`
  were removed (`app/login.tsx`, `src/auth.tsx`); the Founder key button only prefills the e-mail for the password form.
- **SEC-002 (HIGH) fixed.** `routes/subscription.py::_is_founder` = `bool(user["is_founder"])` only — the
  "oldest account is founder" fallback is gone (on this DB the oldest account was `smoke@test.sk`; on a fresh production
  DB it would have been the store-reviewer seed). Guards: wealth dashboard, inner-circle, demo-mode, demo/seed, seal.
  Verified: oldest account → 403 on all founder routes; Founder (flag) → 200; reviewer → 403 + tier archangel intact.
- **Hardening.** `server.py` → `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)` (schema not published).
- **Known consequence:** 34 backend test files mint sessions via `/auth/dev-bypass` and now fail with 403 against the
  preview URL (`test_iter90_reviewer_demo.py` 7/7 still green). To run them locally: `DEV_BYPASS_ENABLED=true` +
  hit `http://localhost:8001` — or migrate the tests to password registration (backlog).
- SEC-003 (MEDIUM, GA-T earn farming / self-dealing Community Help) intentionally NOT changed — business-logic decision pending.

## Iter 93 — Camera bug: "tap camera → app jumps to the start/home screen" (user report)
- **Root cause (confirmed, Founder account has `biometric_enabled: true`).** `src/biometric-gate.tsx` re-locked on EVERY
  AppState background→active cycle (the 60 s `UNLOCK_GRACE_MS` existed but was unused) and rendered the lock screen
  INSTEAD of its children → the whole `<Stack>` + `LaunchSequence` unmounted → navigation state destroyed, pending
  `launchCameraAsync` promise orphaned → after unlock the cinematic intro ("start screen") replayed and the Stack
  restarted at `/` → `/(tabs)`. On Android the camera permission dialog and the system camera Activity both report
  'background', hence "immediately … instead of opening the camera".
- **Fix 1 — BiometricGate.** Children are ALWAYS mounted; the probing splash / lock screen are an opaque absolute
  overlay (`styles.overlay`, zIndex 1000) on top. Re-lock only when the app was away > `UNLOCK_GRACE_MS` (60 s);
  short camera/picker/permission trips never re-lock. Navigation state + in-flight work survive.
- **Fix 2 — Android process death while the camera is open** (secondary cause, per Expo docs). New `src/camera.ts`:
  `launchCamera(route, opts)` (drop-in for `ImagePicker.launchCameraAsync`, remembers the launching route in
  AsyncStorage on Android), `restorePendingCamera()` (cold start → route + `ImagePicker.getPendingResultAsync()`),
  `takeRecoveredAsset()` (screen picks the photo up on mount). `RootNav` (`app/_layout.tsx`) waits for the check on
  Android and, after `/(tabs)`, pushes the remembered route. Wired into `app/lens.tsx`, `app/translate.tsx`,
  `app/health-timeline.tsx` (OCR extracted to `ocrAsset`), `src/SpiderHub.tsx` (`analyzeAsset`), `app/physio.tsx`
  (route return only — video upload needs the selected guide). `magic-lens.tsx` uses in-app `CameraView` (unaffected).
- Not reproducible on web (gate is pass-through without biometry hardware; camera button hidden on web) — needs a
  device check in Expo Go / build: Lens → camera → photo → still on Lens with the photo attached.

## Iter 94 — Data Deletion page · GA-T Farming Guard · Wallet one-tap link (user picks: 1a, 2a, 3c)
- **Data Deletion (Google Play "Data deletion" URL).** Public route `app/delete-account.tsx` (`isPublic` in
  `_layout.tsx`, no login): Option 1 in-app steps, Option 2 e-mail (+reason) form → `POST /api/account/deletion-request`
  (202, rate bucket `deletion_request` 5/min, 24 h de-dupe, never reveals whether the account exists), what-is-erased /
  retained lists from `GET /api/account/deletion-policy`. Founder queue: `GET /api/account/deletion-requests`,
  `POST …/{req_id}/process` (runs `routes.auth.purge_user_data` — same purge as in-app deletion; founder accounts are
  never purged), `POST …/{req_id}/reject`. Links: login footer (`login-privacy-link` · `login-delete-link`), Profile
  (`prof-delete-page`), Privacy Policy page (`privacy-delete-link`). i18n keys `delete_account.*` (en + sk; others fall
  back to English). **Play Console URL:** `https://<your-deployed-domain>/delete-account`.
- **GA-T Farming Guard.** `token.py`: `UNVERIFIED_DAILY_CAP_GAT = 20` — `proof_of_health` + `document_scan` share one
  combined 20 GA-T/day ceiling (was 70) checked in `award_tokens`; `/token/wallet` exposes `unverified_daily_cap`.
  `community_help.py`: `_touch_origin()` records `X-Device-Id` + IP (`users.device_ids`, `users.ip_log` ≤30, both hidden
  from clients via `USER_PRIVATE_PROJECTION`) on create/accept/confirm; `_guard_pair()` → 403 `same_origin` when the two
  accounts share a device id or an IP seen in the last 7 days, 429 `pair_limit` when the same two people already had a
  confirmed help in the last 24 h (checked at accept AND confirm; either direction). `/help/requests` limits now carry
  `pair_window_h`, `same_origin_blocked`. Frontend `src/api.ts` sends `X-Device-Id` (Android ID / iOS vendor ID /
  persisted UUID via `getDeviceId()`) on every `api()`/`apiUpload()` call.
- **Wallet one-tap link (no WalletConnect).** `src/WalletLink.tsx`: MetaMask / Coinbase Wallet buttons (deep link
  `metamask://` / `cbwallet://`, fallback universal links → app or store), PASTE ADDRESS (expo-clipboard, extracts
  `0x…40`), manual input, LINK WALLET → existing `POST /chain/wallet`. Used in `app/blockchain.tsx` (testIDs `bc-*`).
  `app.json` ios `LSApplicationQueriesSchemes: [metamask, cbwallet]`. WalletConnect (Reown) deferred until the user
  sends a Project ID.
- Tests: `backend/tests/test_iter94_guard_deletion.py` 8/8 (runs against localhost with spoofed X-Forwarded-For /
  X-Device-Id; founder test needs `FOUNDER_TEST_PASSWORD`). `/swarm/audit` 9/9 after the flows.

## Iter 95 — Security re-audit fixes (CONDITIONAL PASS → hardened)
- Re-audit confirmed SEC-001/002 (dev-bypass, founder fallback) + /docs closed. Remaining findings fixed:
- **Trusted proxy hops (LOW → fixed).** Probe showed the ingress chain `client, cloudflare, google-lb` in X-Forwarded-For
  (attacker can only PREPEND). `core.client_ip()` now takes the (TRUSTED_PROXY_HOPS+1)-th entry from the RIGHT
  (`TRUSTED_PROXY_HOPS` env, default 2); short chains (direct/local calls) fall back to the first entry so local tests
  can still spoof. Affects rate limits, consent-receipt IP, deletion-request IP, Community Help network guard.
- **Community Help farming (MEDIUM → fixed).** `_require_device()` — accept/confirm return 400 `device_required` when
  the `X-Device-Id` header is missing (the app always sends it); `_guard_fund_velocity()` — a helper may receive max
  `FUND_DAILY_MAX_PER_HELPER=3` Community-Fund-sourced rewards per day (429 `fund_limit`; wallet-funded requests
  unaffected). `clean()` now also strips `ip_log`/`device_ids` everywhere.
- **Deletion request ownership proof (MEDIUM → fixed).** `POST /account/deletion-request` e-mails a 6-digit one-time
  code (sha256(req_id:code) stored, 30 min TTL, 5 attempts) when the account exists — identical 202 response either
  way; new public `POST /account/deletion-request/{req_id}/verify` (rate bucket `deletion_verify` 10/min) marks
  `verified`. Founder `process` returns 412 `unverified` until then (override `?force=true` is recorded as `forced`).
  Founder list never returns `code_hash`. Page `/delete-account` has the code step (`da-verify-step`, `da-code`, `da-verify`).
  Note: the e-mail provider blocks undeliverable test domains (example.com) — real addresses work like password reset.
- Tests: `tests/test_iter94_guard_deletion.py` 11/11 (device-required, fund cap, spoofed-XFF-hop ignored, code verify →
  founder purge). Test deletion requests are cleaned from the DB after runs.
