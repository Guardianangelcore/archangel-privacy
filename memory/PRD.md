# Guardian Health & Angel — Product Requirements (Feb 2026)

## Owner
Guardian Angel Sovereign Foundation (DAO). Sole steward: pseudonymous "Guardian Angel".

## Product goal
A sovereign, faceless, 22nd-century survival OS for individuals + their Guardian Circle. Zero surveillance, EU AI Act compliant, GPS-adaptive, multi-language (14).

## Immutable pillars
- **PILLAR 1 — Healing Carousel (Health)**: Bio-Scanner, Physio-AI, Kolotoč Uzdravenia, Pain Diary, Medical News, Longevity, Vault, IPS.
- **PILLAR 2 — Angel Shield (Family)**: Angel Mode senior OS, Voice Signatures, Voice Echoes, Family Pulse, Guardian Circle (native contacts, local-first), Native Calendar sync, Angel Pulse, Silent Witness, Safety Sentinel, Emergency QR.
- **PILLAR 3 — Sovereign Vault (Legacy/Wealth)**: Video Legacy Vault, Wealth Vault, GA-T Token, Digital Legacy, Testament, Biometric Will, Founder Toolkit, Mosaic Chain.

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
