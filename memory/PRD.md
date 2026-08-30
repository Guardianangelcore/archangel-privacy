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

## Integrations
- Emergent LLM Key (OpenAI, Anthropic, Gemini text/vision, TTS, Whisper STT, GPT Image 1).
- Perplexity Sonar (`PERPLEXITY_API_KEY` in backend/.env — blank = graceful fallback).
- Stripe test keys (Payments).
- Emergent Push (native builds only).
- Emergent Google Auth + Sovereign dev-bypass.
