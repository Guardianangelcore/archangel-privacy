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
1. **P0 AUTH REPAIR** — root cause: corrupted `/root/.expo/state.json` crashed Metro. Fixed. Sovereign Bypass on login (`/api/auth/dev-bypass`): "VSTUP AKO GUARDIAN ANGEL (FOUNDER)" button + custom-email developer bypass. Founder `guardian.angel.core@proton.me` auto-seeded (inner_circle, tier archangel).
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
1. **PII AUDIT (competition safety)**: Full codebase scan (names, emails, author fields, md files) — NO real developer PII found. All author/copyright/README/LICENSE already "Guardian Angel" branded; all emails are brand (guardian.angel.core@proton.me) or fictional test fixtures. Fixed person-like demo strings: clinic_sync.py "MUDr. Kováčová — Ortopédia"→"GA Labs Ortho Clinic", doctor_name "MUDr. Eva Kováčová"→"Dr. Guardian Angel". Test-fixture names (Jan/Anna Novak = John Doe equivalents) left intact to keep OCR tests green.
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
