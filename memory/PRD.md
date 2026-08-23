# Guardian Health & Angel — Product Requirements (MVP)

## Vision
A sovereign, AI-driven mobile OS for medical dignity, senior safety, and community solidarity. Zero-knowledge storage, dual-mode UX (Standard vs. Angel), multi-lingual (SK/CZ/EN/DE).

## MVP Modules
1. **Onboarding & Google Auth** — Emergent Google OAuth, language picker (SK/CZ/EN/DE), Guardian Angel author credit.
2. **Standard Mode Home** — 4 quick actions (Vault, Translate, Waitlist, Donor), floating Emergency QR button, "Simulate Fall" safety.
3. **Angel Mode Home** — 2×2 huge tiles (SOS, Call Family, Medications, Documents), tabs hidden, oversized type. Toggle in header, haptic on switch.
4. **Health Vault** — Upload/list/delete encrypted documents (Emergent Object Storage). Per-doc AI translation with Claude Sonnet 5.
5. **AI Health Translator (Jarvis)** — Paste any medical text → structured plain-language explanation in user's language.
6. **Waitlist Hunter** — Add tracked appointment (specialty, clinic, city, dates), one-tap "Scan now" (simulated 35% hit rate). Chip-row filter Hunting/Found/All.
7. **Emergency QR & Donor Card** — Full-screen scannable QR encoding DID + critical fields, tabular donor + testament layout. Public read endpoint `/api/emergency-qr/{did}`.
8. **Fall-Verify-Notify** — 30 s countdown with rhythmic haptics, huge "I'M OK" cancel, auto-escalate on timeout, `POST /api/fall-event` logs it.
9. **Profile** — DID display, language picker, emergency profile CRUD (blood, allergies, meds, EC, donor consent, life testament), Guardian Angel About credit.

## Integrations
- **Auth**: Emergent Google Auth (`/api/auth/session`, `/api/auth/me`, `/api/auth/logout`)
- **Storage**: Emergent Managed Object Storage (via `/objstore/api/v1/storage`)
- **LLM**: Claude Sonnet 5 via `emergentintegrations` (Emergent LLM Key)

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
| POST | `/api/waitlist/{id}/scan` | Simulated slot scan |
| POST | `/api/fall-event` | Log fall verify/cancel |

## Design
Brutalist Mobile Light — sharp corners (radius 0), 1.5–2 pt borders, monochrome + signal red (#D90429). Green brand (#1B4332). See `/app/design_guidelines.json`.

## Author
Guardian Angel — sole original Visionary and Author. AGPL-v3.
