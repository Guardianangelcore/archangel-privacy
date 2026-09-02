/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// SENTIENT ONBOARDING — the 30-second Sovereign Tour narrated by Jarvis (Onyx).
// Auto-runs ONCE after the very first biometric unlock (or first login on web).
// Stores `onboarding_completed: true` in user prefs so it never runs again.
import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, Pressable, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import Animated, { useSharedValue, useAnimatedStyle, withRepeat, withTiming, Easing } from 'react-native-reanimated';
import { useAuth } from './auth';
import { api } from './api';
import { speak, stopSpeaking } from './voice';
import { C, S, R } from './theme';
import { useI18n } from '@/src/i18n-context';

// The founder's exact narrative — one warm, patient sentence per pillar + a JARVIS reveal.
const TOUR_STEPS = [
  {
    icon: 'sync-circle' as const,
    title: 'MY HEALING',
    subtitle: 'Loop: referral → money → doctor → physio.',
    tts: 'On the left is your Healing.',
    duration: 5000,
  },
  {
    icon: 'people' as const,
    title: 'FAMILY SHIELD',
    subtitle: 'Angel Mode, Magic Lens, voice messages, SOS.',
    tts: 'In the middle, your Family Shield.',
    duration: 5000,
  },
  {
    icon: 'shield-checkmark' as const,
    title: 'SOVEREIGN VAULT',
    subtitle: 'Wealth, eternal legacy and bunker mode.',
    tts: 'And on the right, your Sovereign Vault.',
    duration: 5500,
  },
  {
    icon: 'mic-circle' as const,
    title: 'JUST SAY MY NAME',
    subtitle: 'Say JARVIS any time and I am ready.',
    tts: 'If anything is unclear, just call me by my name, Jarvis.',
    duration: 6500,
  },
];

export function OnboardingTour() {
  const { t: tt, tx } = useI18n();
  const { user, setUser } = useAuth();
  const [step, setStep] = useState(0);
  const [done, setDone] = useState(false);
  const startedRef = useRef(false);
  const pulse = useSharedValue(0);

  const shouldRun =
    !!user &&
    (user as any).tos_accepted_version === '2026-06.1' &&
    !(user as any).onboarding_completed;

  useEffect(() => {
    if (!shouldRun || startedRef.current) return;
    startedRef.current = true;
    pulse.value = withRepeat(withTiming(1, { duration: 1400, easing: Easing.inOut(Easing.sin) }), -1, true);

    // Founder directive: use "Guardian Angel" as the default fallback name.
    const displayName = (user?.name && user.name.trim() && user.name.trim() !== user?.email)
      ? user.name.split(' ')[0]
      : 'Guardian Angel';
    const lang = ((user?.language as any) || 'en');

    // Speak the intro line then walk through the pillars.
    (async () => {
      await speak(`Welcome home, ${displayName}. I am your Jarvis.`, { mood: 'onboarding', language: lang });
      for (let i = 0; i < TOUR_STEPS.length; i++) {
        // Slight delay before advancing so the previous line finishes.
        await new Promise((r) => setTimeout(r, i === 0 ? 2500 : 300));
        setStep(i);
        speak(TOUR_STEPS[i].tts, { mood: 'onboarding', language: lang });
        await new Promise((r) => setTimeout(r, TOUR_STEPS[i].duration));
      }
      finish();
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shouldRun]);

  const finish = async () => {
    stopSpeaking();
    setDone(true);
    try {
      const u: any = await api('/me/prefs', {
        method: 'PATCH',
        body: JSON.stringify({ onboarding_completed: true }),
      });
      setUser(u);
    } catch {
      // Non-blocking — the flag can be set later; the user still sees the app.
    }
  };

  const skip = () => finish();

  const pulseStyle = useAnimatedStyle(() => ({
    transform: [{ scale: 1 + pulse.value * 0.08 }],
    opacity: 0.6 + pulse.value * 0.4,
  }));

  if (!shouldRun || done) return null;

  const current = TOUR_STEPS[step];

  return (
    <View testID="onboarding-tour" style={styles.overlay} pointerEvents="box-none">
      <View style={styles.card} pointerEvents="auto">
        <View style={styles.crown}>
          <Text style={styles.crownText}>{tt('c_onboarding_tour.sovereign_tour')} {step + 1} / {TOUR_STEPS.length}</Text>
          <Pressable testID="onboarding-skip" onPress={skip} hitSlop={12}>
            <Ionicons name="close" size={22} color={C.info} />
          </Pressable>
        </View>

        <Animated.View style={[styles.iconRing, pulseStyle]}>
          <Ionicons name={current.icon} size={72} color={C.brand} />
        </Animated.View>

        <Text style={styles.title}>{tx(current.title)}</Text>
        <Text style={styles.subtitle}>{tx(current.subtitle)}</Text>

        {/* Progress dots */}
        <View style={styles.dots}>
          {TOUR_STEPS.map((_, i) => (
            <View key={i} style={[styles.dot, i <= step && styles.dotActive]} />
          ))}
        </View>

        {step === TOUR_STEPS.length - 1 ? (
          <Pressable testID="onboarding-done" onPress={finish} style={styles.cta}>
            <Ionicons name="checkmark" size={18} color={C.onInverse} />
            <Text style={styles.ctaText}>{tt('c_onboarding_tour.got_it_continue')}</Text>
          </Pressable>
        ) : (
          <Text style={styles.hint}>{tt('c_onboarding_tour.jarvis_is_guiding_you_tap_to_skip')}</Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: 'rgba(6,6,10,0.94)',
    alignItems: 'center', justifyContent: 'center',
    padding: S.xl,
    zIndex: 9999,
    ...(Platform.OS === 'web' ? { position: 'fixed' as any } : {}),
  },
  card: {
    alignSelf: 'stretch',
    backgroundColor: C.surface2,
    borderWidth: 2, borderColor: C.brand, borderRadius: R.lg,
    padding: S.xl, gap: S.md,
    shadowColor: C.brand, shadowOpacity: 0.4, shadowRadius: 24, shadowOffset: { width: 0, height: 6 }, elevation: 14,
  },
  crown: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  crownText: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 2 },
  iconRing: {
    alignSelf: 'center',
    width: 150, height: 150, borderRadius: 75,
    borderWidth: 2, borderColor: 'rgba(212,175,55,0.5)',
    alignItems: 'center', justifyContent: 'center',
    backgroundColor: 'rgba(212,175,55,0.08)',
    marginVertical: S.lg,
  },
  title: { color: C.fg, fontWeight: '900', fontSize: 22, letterSpacing: 2, textAlign: 'center' },
  subtitle: { color: C.onS3, fontSize: 14, lineHeight: 20, textAlign: 'center', marginTop: 4 },
  dots: { flexDirection: 'row', gap: 8, alignSelf: 'center', marginTop: S.lg },
  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: C.borderStrong },
  dotActive: { backgroundColor: C.brand },
  cta: { marginTop: S.lg, flexDirection: 'row', gap: 8, backgroundColor: C.brand, borderRadius: R.pill, minHeight: 54, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  hint: { color: C.info, fontSize: 11, textAlign: 'center', marginTop: S.md },
});
