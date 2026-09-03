/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// JUDGE QUICK TOUR — a guided 3-minute demo script for competition judges.
// 9 stops × 20 s. Starting the tour activates DEMO MODE (every gate open), navigates to each
// feature in order, narrates a one-line pitch (Jarvis voice) and auto-advances with a visible
// countdown. Judges can pause, step back/forward or end at any time. Overlay lives in _layout.
import React, { useEffect, useRef, useSyncExternalStore } from 'react';
import { View, Text, StyleSheet, Pressable, Platform } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { useI18n } from './i18n-context';
import { speak, stopSpeaking } from './voice';
import { startDemoMode } from './DemoMode';
import { tap } from './ui/glass';

export const JUDGE_TOUR_STEPS: { key: string; route: string; icon: any; ms: number }[] = [
  { key: 'jarvis', route: '/jarvis', icon: 'planet-outline', ms: 20000 },
  { key: 'magic_lens', route: '/magic-lens', icon: 'scan-outline', ms: 20000 },
  { key: 'nearby_care', route: '/nearby-care', icon: 'navigate-outline', ms: 20000 },
  { key: 'crisis', route: '/crisis-protocols', icon: 'list-outline', ms: 20000 },
  { key: 'family_shield', route: '/(tabs)/family', icon: 'people-outline', ms: 20000 },
  { key: 'bioscan', route: '/bioscan', icon: 'pulse-outline', ms: 20000 },
  { key: 'marketplace', route: '/protocol', icon: 'lock-closed-outline', ms: 20000 },
  { key: 'timeline', route: '/health-timeline', icon: 'analytics-outline', ms: 20000 },
  { key: 'subscription', route: '/subscription', icon: 'diamond-outline', ms: 20000 },
];
export const JUDGE_TOUR_TOTAL_MS = JUDGE_TOUR_STEPS.reduce((a, s) => a + s.ms, 0);   // 3:00

// ---- tiny external store (survives screen navigation; overlay is mounted once in _layout) ----
type State = { active: boolean; step: number; paused: boolean; stepStartedAt: number; elapsedBefore: number };
let state: State = { active: false, step: 0, paused: false, stepStartedAt: 0, elapsedBefore: 0 };
const subs = new Set<() => void>();
const set = (patch: Partial<State>) => { state = { ...state, ...patch }; subs.forEach(fn => fn()); };
const subscribe = (fn: () => void) => { subs.add(fn); return () => { subs.delete(fn); }; };
const getSnapshot = () => state;
export const useJudgeTour = () => useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

let navigate: ((route: string) => void) | null = null;

export async function startJudgeTour(refreshUser?: () => Promise<void> | void) {
  await startDemoMode(refreshUser);          // DEMO_ONLY — unlock every tier gate for the walkthrough
  set({ active: true, step: 0, paused: false, stepStartedAt: Date.now(), elapsedBefore: 0 });
  navigate?.(JUDGE_TOUR_STEPS[0].route);
}
export function stopJudgeTour() { stopSpeaking(); set({ active: false, paused: false }); }

const fmt = (ms: number) => { const s = Math.max(0, Math.ceil(ms / 1000)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };

export function JudgeTourOverlay() {
  const { active, step, paused, stepStartedAt, elapsedBefore } = useJudgeTour();
  const { t: tt, lang } = useI18n();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [, force] = React.useState(0);
  const pausedAt = useRef(0);
  useEffect(() => { navigate = (r) => router.push(r as any); return () => { navigate = null; }; }, [router]);

  const goTo = (i: number) => {
    if (i < 0) return;
    if (i >= JUDGE_TOUR_STEPS.length) { stopJudgeTour(); router.push('/(tabs)' as any); return; }
    stopSpeaking();
    const spent = paused ? pausedAt.current - stepStartedAt : Date.now() - stepStartedAt;
    set({ step: i, stepStartedAt: Date.now(), paused: false, elapsedBefore: elapsedBefore + Math.min(spent, JUDGE_TOUR_STEPS[step].ms) });
    router.push(JUDGE_TOUR_STEPS[i].route as any);
  };

  // narration + auto-advance ticker
  useEffect(() => {
    if (!active) return;
    speak(tt(`judge_tour.${JUDGE_TOUR_STEPS[step].key}_pitch`), { language: lang, speed: 1.05 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, step]);
  useEffect(() => {
    if (!active || paused) return;
    const id = setInterval(() => {
      force(x => x + 1);
      if (Date.now() - state.stepStartedAt >= JUDGE_TOUR_STEPS[state.step].ms) goTo(state.step + 1);
    }, 250);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, paused, step, stepStartedAt]);

  if (!active) return null;
  const cur = JUDGE_TOUR_STEPS[step];
  const spent = paused ? pausedAt.current - stepStartedAt : Date.now() - stepStartedAt;
  const left = JUDGE_TOUR_TOTAL_MS - elapsedBefore - Math.min(spent, cur.ms);
  const pct = Math.min(1, spent / cur.ms);

  const togglePause = () => {
    tap('light');
    if (paused) set({ paused: false, stepStartedAt: Date.now() - (pausedAt.current - stepStartedAt) });
    else { pausedAt.current = Date.now(); stopSpeaking(); set({ paused: true }); }
  };

  return (
    <View testID="judge-tour" pointerEvents="box-none" style={[st.wrap, { bottom: (Platform.OS === 'web' ? 96 : 92) + insets.bottom }]}>
      <View style={st.card}>
        <View style={st.head}>
          <Ionicons name={cur.icon} size={16} color="#FFD60A" />
          <Text style={st.kicker}>{tt('judge_tour.judge_tour')} · {step + 1}/{JUDGE_TOUR_STEPS.length}</Text>
          <Text testID="jt-timer" style={st.timer}>{fmt(left)}</Text>
          <Pressable testID="jt-end" onPress={() => { tap('light'); stopJudgeTour(); }} hitSlop={10}><Ionicons name="close" size={18} color="#B9B9C0" /></Pressable>
        </View>
        <Text testID="jt-title" style={st.title}>{tt(`judge_tour.${cur.key}_title`)}</Text>
        <Text style={st.pitch}>{tt(`judge_tour.${cur.key}_pitch`)}</Text>
        <View style={st.bar}><View style={[st.barFill, { width: `${pct * 100}%` as any }]} /></View>
        <View style={st.row}>
          <Pressable testID="jt-prev" onPress={() => { tap('light'); goTo(step - 1); }} disabled={step === 0} style={[st.btn, step === 0 && { opacity: 0.35 }]}><Ionicons name="play-back" size={16} color="#E5E4E2" /></Pressable>
          <Pressable testID="jt-pause" onPress={togglePause} style={st.btn}><Ionicons name={paused ? 'play' : 'pause'} size={16} color="#E5E4E2" /></Pressable>
          <Pressable testID="jt-next" onPress={() => { tap('light'); goTo(step + 1); }} style={[st.btn, st.btnPrimary]}>
            <Text style={st.btnPrimaryText}>{step === JUDGE_TOUR_STEPS.length - 1 ? tt('judge_tour.finish') : tt('judge_tour.next')}</Text>
            <Ionicons name="play-forward" size={14} color="#0B0B0D" />
          </Pressable>
        </View>
      </View>
    </View>
  );
}

const st = StyleSheet.create({
  wrap: { position: 'absolute', left: 12, right: 12, zIndex: 900 },
  card: { backgroundColor: 'rgba(11,11,13,0.96)', borderWidth: 1.5, borderColor: '#FFD60A', padding: 12, gap: 6, borderRadius: 4 },
  head: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  kicker: { flex: 1, color: '#FFD60A', fontWeight: '900', fontSize: 10, letterSpacing: 2 },
  timer: { color: '#E5E4E2', fontWeight: '900', fontSize: 12, fontVariant: ['tabular-nums'] },
  title: { color: '#E5E4E2', fontWeight: '900', fontSize: 14, letterSpacing: 0.5 },
  pitch: { color: '#B9B9C0', fontSize: 12, lineHeight: 17 },
  bar: { height: 3, backgroundColor: 'rgba(255,255,255,0.10)', overflow: 'hidden' },
  barFill: { height: 3, backgroundColor: '#FFD60A' },
  row: { flexDirection: 'row', gap: 8, marginTop: 4 },
  btn: { minHeight: 40, minWidth: 44, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: '#3A3A44', paddingHorizontal: 12 },
  btnPrimary: { flex: 1, flexDirection: 'row', gap: 8, backgroundColor: '#FFD60A', borderColor: '#FFD60A' },
  btnPrimaryText: { color: '#0B0B0D', fontWeight: '900', fontSize: 12, letterSpacing: 1.5 },
});
