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

## Integrations
- Emergent LLM Key (OpenAI, Anthropic, Gemini text/vision, TTS, Whisper STT).
- Stripe test keys (Payments).
- Emergent Push (native builds only).
- Emergent Google Auth.
