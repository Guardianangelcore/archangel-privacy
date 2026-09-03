/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// LAUNCH SEQUENCE — Cinematic Intro (every start) → Onboarding cards (first launch only).
import React, { useEffect, useState } from 'react';
import { CinematicIntro } from './CinematicIntro';
import { OnboardingCards, isFirstLaunch } from './OnboardingCards';

export function LaunchSequence() {
  const [phase, setPhase] = useState<'intro' | 'onboarding' | 'done'>('intro');
  const [first, setFirst] = useState<boolean | null>(null);
  useEffect(() => {
    let alive = true;
    isFirstLaunch().then(v => { if (alive) setFirst(v); }).catch(() => { if (alive) setFirst(false); });
    return () => { alive = false; };
  }, []);

  // Intro runs on every start; when it ends we show onboarding ONLY if the flag resolved to
  // "first launch". Unknown (storage slow/unavailable) counts as NOT first — never block.
  if (phase === 'intro') return <CinematicIntro onDone={() => setPhase(first === true ? 'onboarding' : 'done')} />;
  if (phase === 'onboarding') return <OnboardingCards onDone={() => setPhase('done')} />;
  return null;
}
