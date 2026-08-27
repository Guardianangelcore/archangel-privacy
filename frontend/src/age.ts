/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// BIO-TIMELINE — the Growth Engine.
// The OS quietly adapts its UI, tone, and medical logic to the user's life stage:
//   infant  (0-3)   → the app is a *parent's dashboard* (vaccines, milestones)
//   child   (4-12)  → simplified language, guardian-first
//   teen    (13-17) → privacy-first, mental fortress prominent
//   adult   (18-64) → full sovereign stack (default)
//   senior  (65+)   → Angel Mode auto-suggested, XL type, icons+voice
export type AgeStage = 'infant' | 'child' | 'teen' | 'adult' | 'senior';

export const AGE_STAGES: AgeStage[] = ['infant', 'child', 'teen', 'adult', 'senior'];

export const AGE_LABEL_SK: Record<AgeStage, string> = {
  infant: 'Dojča (0–3)',
  child:  'Dieťa (4–12)',
  teen:   'Teenager (13–17)',
  adult:  'Dospelý (18–64)',
  senior: 'Senior (65+)',
};

export const AGE_LABEL_EN: Record<AgeStage, string> = {
  infant: 'Infant (0–3)',
  child:  'Child (4–12)',
  teen:   'Teen (13–17)',
  adult:  'Adult (18–64)',
  senior: 'Senior (65+)',
};

export function ageFromBirthYear(birthYear?: number | null): number | null {
  if (!birthYear || birthYear < 1900 || birthYear > 2100) return null;
  const now = new Date().getUTCFullYear();
  const a = now - birthYear;
  return a >= 0 && a <= 130 ? a : null;
}

export function stageFromAge(age: number | null): AgeStage {
  if (age === null || age === undefined) return 'adult';
  if (age <= 3)  return 'infant';
  if (age <= 12) return 'child';
  if (age <= 17) return 'teen';
  if (age <= 64) return 'adult';
  return 'senior';
}

export function stageFromUser(user: any): AgeStage {
  return stageFromAge(ageFromBirthYear(user?.birth_year));
}

/**
 * Should the Guardian Gold "Angel Mode" toggle be prominent for this user?
 * - Seniors: YES, front-and-center (their whole UX depends on it).
 * - Everyone else: subtle in header, but still one tap away.
 */
export function suggestAngelMode(stage: AgeStage): boolean {
  return stage === 'senior';
}

/**
 * How urgent/warm should Jarvis be with this stage?
 * Feeds into the TTS mood + text tone.
 */
export function jarvisToneFor(stage: AgeStage): 'onboarding' | 'calm' | 'energetic' | 'concerned' {
  switch (stage) {
    case 'infant': return 'concerned';   // caregiver context — attentive, cautious
    case 'child':  return 'energetic';   // playful, encouraging
    case 'teen':   return 'calm';        // low-key, respectful of autonomy
    case 'adult':  return 'calm';
    case 'senior': return 'onboarding';  // slow, warm, patient
  }
}
