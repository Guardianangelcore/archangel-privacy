/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// BLAZING CEREMONY — the 30-day Sovereign Blazing Guardian moment.
// A single-purpose full-screen overlay: gold pulsing orb + Onyx-narrated title.
// Auto-persists "seen" state so it never plays twice.
import React, { useEffect } from 'react';
import { View, Text, StyleSheet, Pressable, Platform } from 'react-native';
import Animated, { useSharedValue, useAnimatedStyle, withRepeat, withTiming, Easing, cancelAnimation } from 'react-native-reanimated';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { api } from './api';
import { useAuth } from './auth';
import { speak as jarvisSpeak, stopSpeaking } from './voice';
import { C, S, R, GOLD } from './theme';
import { useI18n } from '@/src/i18n-context';

const NARRATION = 'Thirty days. Sovereign Blazing Guardian. You are at the peak of your habit.';

export function BlazingCeremony({ onClose }: { onClose: () => void }) {
  const { t: tt, tx } = useI18n();
  const { user } = useAuth();
  const orb = useSharedValue(0);

  useEffect(() => {
    orb.value = withRepeat(withTiming(1, { duration: 2200, easing: Easing.inOut(Easing.sin) }), -1, true);
    jarvisSpeak(NARRATION, {
      voice: 'onyx', speed: 0.92, language: (user?.language as any) || 'en',
    });
    return () => { cancelAnimation(orb); stopSpeaking(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const orbStyle = useAnimatedStyle(() => ({
    transform: [{ scale: 1 + orb.value * 0.22 }],
    opacity: 0.7 + orb.value * 0.3,
  }));
  const ringStyle = useAnimatedStyle(() => ({
    transform: [{ scale: 1 + orb.value * 0.4 }],
    opacity: 0.35 - orb.value * 0.3,
  }));

  const acknowledge = async () => {
    try { await api('/streaks/blazing/celebrated', { method: 'POST' }); } catch {}
    onClose();
  };

  return (
    <View testID="blazing-ceremony" style={styles.overlay}>
      <View style={styles.stage}>
        <Animated.View style={[styles.ring, ringStyle]} />
        <Animated.View style={[styles.orb, orbStyle]}>
          <LinearGradient colors={GOLD as any} start={{ x: 0.2, y: 0 }} end={{ x: 1, y: 1 }} style={styles.orbBg}>
            <Ionicons name="flame" size={78} color={C.onInverse} />
          </LinearGradient>
        </Animated.View>
      </View>

      <Text style={styles.days}>{tt('c_blazing_ceremony.30_days')}</Text>
      <Text style={styles.title}>{tt('c_blazing_ceremony.sovereign_blazing_guardian')}</Text>
      <Text style={styles.tag}>
        {tt('c_blazing_ceremony.the_peak_of_a_habit_jarvis_congratul')}
      </Text>

      <Pressable testID="blazing-ack" onPress={acknowledge} style={styles.ctaWrap}>
        <LinearGradient colors={GOLD as any} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.cta}>
          <Ionicons name="checkmark" size={20} color={C.onInverse} />
          <Text style={styles.ctaText}>{tt('c_blazing_ceremony.i_accept_the_honour')}</Text>
        </LinearGradient>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: 'rgba(6,6,10,0.97)',
    alignItems: 'center', justifyContent: 'center', padding: S.xl,
    zIndex: 12000,
    ...(Platform.OS === 'web' ? { position: 'fixed' as any } : {}),
  },
  stage: { alignItems: 'center', justifyContent: 'center', width: 260, height: 260, marginBottom: S.xxl },
  ring: { position: 'absolute', width: 260, height: 260, borderRadius: 130, borderWidth: 3, borderColor: C.brand },
  orb: { alignItems: 'center', justifyContent: 'center', shadowColor: C.brand, shadowOpacity: 0.85, shadowRadius: 40, shadowOffset: { width: 0, height: 0 }, elevation: 24 },
  orbBg: { width: 180, height: 180, borderRadius: 90, alignItems: 'center', justifyContent: 'center' },
  days: { color: C.brand, fontWeight: '900', fontSize: 46, letterSpacing: 3, marginTop: S.md },
  title: { color: C.fg, fontWeight: '900', fontSize: 15, letterSpacing: 3, marginTop: S.sm, textAlign: 'center' },
  tag: { color: C.onS3, fontSize: 13, lineHeight: 20, textAlign: 'center', marginTop: S.md, paddingHorizontal: S.md },
  ctaWrap: { marginTop: S.xxl, borderRadius: R.pill, overflow: 'hidden', shadowColor: C.brand, shadowOpacity: 0.55, shadowRadius: 18, shadowOffset: { width: 0, height: 6 }, elevation: 14 },
  cta: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, paddingHorizontal: S.xxl, minHeight: 60 },
  ctaText: { color: C.onInverse, fontWeight: '900', fontSize: 14, letterSpacing: 3 },
});
