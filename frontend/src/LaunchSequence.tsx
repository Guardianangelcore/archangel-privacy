/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// LAUNCH SEQUENCE — Cinematic Intro (every start) → Onboarding cards (first launch only).
import React, { useEffect, useState } from 'react';
import { CinematicIntro } from './CinematicIntro';
import { OnboardingCards, isFirstLaunch } from './OnboardingCards';

export function LaunchSequence() {
  const [phase, setPhase] = useState<'intro' | 'onboarding' | 'done'>('intro');
  const [first, setFirst] = useState<boolean | null>(null);
  useEffect(() => { isFirstLaunch().then(setFirst); }, []);

  if (phase === 'intro') return <CinematicIntro onDone={() => setPhase(first === false ? 'done' : 'onboarding')} />;
  if (phase === 'onboarding') {
    if (first === null) return null;                 // flag still loading (rare) — wait
    if (!first) { setPhase('done'); return null; }
    return <OnboardingCards onDone={() => setPhase('done')} />;
  }
  return null;
}
