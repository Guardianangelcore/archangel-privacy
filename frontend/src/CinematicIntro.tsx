/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// CINEMATIC INTRO — GOLDEN SUPERNOVA. Pure black; a single 2 px gold point in the centre
// explodes outward (gold → white light wave) and floods the screen; out of the light emerge
// "ARCHANGEL OS" · "VISION BY GUARDIAN ANGEL" · gold subtitle; fade to black; enter the app.
// JARVIS narrates (public /api/voice/intro.mp3). Auto-skip 5 s (or with the narration, cap 14 s),
// "Skip" / "Enter the System". React Native Animated API only — no external animation libraries.
import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, Pressable, Animated, Easing, useWindowDimensions } from 'react-native';
import { useI18n } from './i18n-context';
import { API_BASE } from './api';
import { speakUri, stopSpeaking } from './voice';

const GOLD = '#D4AF37';
const AUTO_SKIP_MS = 5000;      // silent fallback (narration never started)
const NARRATION_CAP_MS = 14000; // never hold the user longer than this

export function CinematicIntro({ onDone }: { onDone: () => void }) {
  const { t: tt, lang } = useI18n();
  const { width, height } = useWindowDimensions();
  const [gone, setGone] = useState(false);
  const [narrating, setNarrating] = useState(false);
  const nova = useRef(new Animated.Value(0)).current;      // 0 → 1 : point → full-screen wave
  const flash = useRef(new Animated.Value(0)).current;     // white flood
  const textOp = useRef(new Animated.Value(0)).current;
  const subOp = useRef(new Animated.Value(0)).current;
  const fade = useRef(new Animated.Value(1)).current;
  const finished = useRef(false);

  const finish = () => {
    if (finished.current) return;
    finished.current = true;
    stopSpeaking();
    Animated.timing(fade, { toValue: 0, duration: 450, useNativeDriver: true }).start(() => { setGone(true); onDone(); });
  };

  useEffect(() => {
    Animated.sequence([
      Animated.delay(500),                                                                                    // a lone point in the dark
      Animated.timing(nova, { toValue: 1, duration: 1400, easing: Easing.out(Easing.exp), useNativeDriver: true }),   // explosion
    ]).start();
    Animated.sequence([
      Animated.delay(900),
      Animated.timing(flash, { toValue: 1, duration: 500, easing: Easing.out(Easing.quad), useNativeDriver: true }),  // white flood
      Animated.timing(flash, { toValue: 0, duration: 1300, easing: Easing.in(Easing.quad), useNativeDriver: true }),  // light recedes…
    ]).start();
    Animated.timing(textOp, { toValue: 1, duration: 1100, delay: 1500, useNativeDriver: true }).start();     // …and the name emerges
    Animated.timing(subOp, { toValue: 1, duration: 900, delay: 2300, useNativeDriver: true }).start();

    let started = false;
    const silentSkip = setTimeout(() => { if (!started) finish(); }, AUTO_SKIP_MS);
    const cap = setTimeout(finish, NARRATION_CAP_MS);
    speakUri(`${API_BASE}/api/voice/intro.mp3?lang=${lang}`, () => { started = true; setNarrating(true); })
      .then(() => { if (started) finish(); })
      .catch(() => {});
    return () => { clearTimeout(silentSkip); clearTimeout(cap); stopSpeaking(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (gone) return null;
  const D = Math.sqrt(width * width + height * height) * 1.1;       // wave diameter that covers the corners
  const scale = nova.interpolate({ inputRange: [0, 1], outputRange: [2 / D, 1] });
  const coreScale = nova.interpolate({ inputRange: [0, 0.6, 1], outputRange: [2 / D, 0.55, 0.9] });
  const waveOp = nova.interpolate({ inputRange: [0, 0.7, 1], outputRange: [1, 0.85, 0] });

  return (
    <Animated.View testID="cinematic-intro" style={[st.root, { opacity: fade }]}>
      {/* gold light wave */}
      <Animated.View pointerEvents="none" style={[st.disc, { width: D, height: D, borderRadius: D / 2, left: width / 2 - D / 2, top: height / 2 - D / 2, backgroundColor: GOLD, opacity: waveOp, transform: [{ scale }] }]} />
      {/* white core */}
      <Animated.View pointerEvents="none" style={[st.disc, { width: D, height: D, borderRadius: D / 2, left: width / 2 - D / 2, top: height / 2 - D / 2, backgroundColor: '#FFF6D5', opacity: waveOp, transform: [{ scale: coreScale }] }]} />
      {/* full-screen flash */}
      <Animated.View pointerEvents="none" style={[StyleSheet.absoluteFill, { backgroundColor: '#FFFFFF', opacity: flash }]} />

      <View style={st.center}>
        <Animated.Text testID="intro-headline" style={[st.title, { opacity: textOp }]}>ARCHANGEL OS</Animated.Text>
        <Animated.Text style={[st.vision, { opacity: textOp }]}>VISION BY GUARDIAN ANGEL</Animated.Text>
        <Animated.Text style={[st.subtitle, { opacity: subOp }]}>Sovereign Health & Survival OS</Animated.Text>
      </View>

      {narrating && (
        <Pressable testID="intro-skip" onPress={finish} style={st.skipBtn} hitSlop={10}>
          <Text style={st.skipText}>⏭ {tt('intro.skip_narration')}</Text>
        </Pressable>
      )}
      <Pressable testID="intro-enter" onPress={finish} style={st.enterBtn} hitSlop={8}>
        <Text style={st.enterText}>{tt('intro.enter_the_system')}</Text>
      </Pressable>
    </Animated.View>
  );
}

const st = StyleSheet.create({
  root: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: '#000000', zIndex: 2000, elevation: 2000, alignItems: 'center', justifyContent: 'center', overflow: 'hidden' },
  disc: { position: 'absolute' },
  center: { alignItems: 'center', gap: 10, paddingHorizontal: 24 },
  title: { color: '#FFFFFF', fontSize: 34, fontWeight: '900', letterSpacing: 6, textAlign: 'center', textShadowColor: 'rgba(212,175,55,0.9)', textShadowRadius: 24, textShadowOffset: { width: 0, height: 0 } },
  vision: { color: 'rgba(255,255,255,0.75)', fontSize: 11, fontWeight: '800', letterSpacing: 4, textAlign: 'center' },
  subtitle: { color: GOLD, fontSize: 13, fontWeight: '800', letterSpacing: 2.5, textAlign: 'center', marginTop: 8 },
  enterBtn: { position: 'absolute', bottom: 64, minHeight: 52, paddingHorizontal: 32, borderWidth: 1.5, borderColor: GOLD, justifyContent: 'center', alignItems: 'center', backgroundColor: 'rgba(212,175,55,0.08)' },
  enterText: { color: GOLD, fontWeight: '900', letterSpacing: 2.5, fontSize: 13 },
  skipBtn: { position: 'absolute', top: 56, right: 20, minHeight: 44, paddingHorizontal: 14, justifyContent: 'center', alignItems: 'center' },
  skipText: { color: 'rgba(255,255,255,0.7)', fontWeight: '800', letterSpacing: 2, fontSize: 11 },
});
