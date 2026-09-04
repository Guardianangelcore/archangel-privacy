/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// CINEMATIC INTRO — shown on EVERY app start before the main screen. Black canvas, a white/gold
// archangel silhouette sweeps left → right, headline fades in, logo + gold subtitle. JARVIS narrates
// a short welcome (public /api/voice/intro.mp3, app language); the intro ends with the narration
// (hard cap 14 s), or after 5 s when the voice cannot start (offline). "Skip" / "Enter" stop it.
import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, Pressable, Animated, Easing, useWindowDimensions } from 'react-native';
import Svg, { Path, Circle } from 'react-native-svg';
import { useI18n } from './i18n-context';
import { API_BASE } from './api';
import { speakUri, stopSpeaking } from './voice';

const GOLD = '#D4AF37';
const AUTO_SKIP_MS = 5000;      // silent fallback (narration never started)
const NARRATION_CAP_MS = 14000; // never hold the user longer than this

function Archangel({ size }: { size: number }) {
  // Minimal silhouette: head, body, two wings — white body, gold wing edges.
  return (
    <Svg width={size} height={size * 0.75} viewBox="0 0 200 150">
      <Path d="M100 60 C 80 95, 78 120, 100 140 C 122 120, 120 95, 100 60 Z" fill="#FFFFFF" opacity={0.95} />
      <Circle cx="100" cy="46" r="11" fill="#FFFFFF" />
      <Path d="M96 75 C 60 40, 25 45, 5 70 C 30 68, 50 80, 60 96 C 40 92, 20 100, 8 118 C 35 108, 60 112, 92 120 Z" fill={GOLD} opacity={0.92} />
      <Path d="M104 75 C 140 40, 175 45, 195 70 C 170 68, 150 80, 140 96 C 160 92, 180 100, 192 118 C 165 108, 140 112, 108 120 Z" fill={GOLD} opacity={0.92} />
      <Path d="M96 75 C 66 50, 40 52, 22 70 C 44 70, 62 82, 72 98 Z" fill="#FFFFFF" opacity={0.55} />
      <Path d="M104 75 C 134 50, 160 52, 178 70 C 156 70, 138 82, 128 98 Z" fill="#FFFFFF" opacity={0.55} />
    </Svg>
  );
}

function LogoMark({ size }: { size: number }) {
  // Archangel OS mark (gold ring + wing arcs + "A"), drawn for the black canvas.
  return (
    <Svg width={size} height={size} viewBox="0 0 120 120">
      <Circle cx="60" cy="62" r="46" stroke={GOLD} strokeWidth="1" fill="none" opacity={0.35} />
      <Circle cx="60" cy="62" r="34" stroke={GOLD} strokeWidth="4" fill="none" />
      <Path d="M6 66 C 18 44, 40 42, 56 58" stroke={GOLD} strokeWidth="4" fill="none" strokeLinecap="round" />
      <Path d="M114 66 C 102 44, 80 42, 64 58" stroke={GOLD} strokeWidth="4" fill="none" strokeLinecap="round" />
      <Path d="M48 78 L 60 44 L 72 78 M 53 67 L 67 67" stroke="#FFFFFF" strokeWidth="4" fill="none" strokeLinejoin="round" strokeLinecap="round" />
    </Svg>
  );
}

export function CinematicIntro({ onDone }: { onDone: () => void }) {
  const { t: tt, lang } = useI18n();
  const { width, height } = useWindowDimensions();
  const [gone, setGone] = useState(false);
  const [narrating, setNarrating] = useState(false);
  const fly = useRef(new Animated.Value(0)).current;      // 0 → 1 : left → right
  const textOp = useRef(new Animated.Value(0)).current;
  const logoOp = useRef(new Animated.Value(0)).current;
  const fade = useRef(new Animated.Value(1)).current;
  const finished = useRef(false);

  const finish = () => {
    if (finished.current) return;
    finished.current = true;
    stopSpeaking();
    Animated.timing(fade, { toValue: 0, duration: 350, useNativeDriver: true }).start(() => { setGone(true); onDone(); });
  };

  useEffect(() => {
    Animated.sequence([
      Animated.timing(fly, { toValue: 1, duration: 2200, easing: Easing.inOut(Easing.cubic), useNativeDriver: true }),
    ]).start();
    Animated.timing(textOp, { toValue: 1, duration: 1200, delay: 900, useNativeDriver: true }).start();
    Animated.timing(logoOp, { toValue: 1, duration: 900, delay: 2000, useNativeDriver: true }).start();

    // JARVIS NARRATION — the intro lasts as long as the voice (capped); if the voice never
    // starts (offline / TTS down) the classic 5 s auto-skip applies.
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
  const size = Math.min(220, width * 0.6);
  const translateX = fly.interpolate({ inputRange: [0, 1], outputRange: [-size, width] });
  const translateY = fly.interpolate({ inputRange: [0, 0.5, 1], outputRange: [height * 0.30, height * 0.16, height * 0.26] });
  const wingOp = fly.interpolate({ inputRange: [0, 0.15, 0.85, 1], outputRange: [0, 1, 1, 0] });

  return (
    <Animated.View testID="cinematic-intro" style={[st.root, { opacity: fade }]}>
      <Animated.View pointerEvents="none" style={[st.angel, { transform: [{ translateX }, { translateY }], opacity: wingOp }]}>
        <Archangel size={size} />
      </Animated.View>

      <View style={st.center}>
        <Animated.Text testID="intro-headline" style={[st.headline, { opacity: textOp }]}>{tt('intro.the_world_is_changing_are_you_ready')}</Animated.Text>
        <Animated.View style={[st.brand, { opacity: logoOp }]}>
          <LogoMark size={84} />
          <Text style={st.appName}>GUARDIAN ANGEL</Text>
          <Text style={st.subtitle}>{tt('intro.sovereign_health_survival_os')}</Text>
        </Animated.View>
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
  root: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: '#000000', zIndex: 2000, justifyContent: 'center', alignItems: 'center' },
  angel: { position: 'absolute', top: 0, left: 0 },
  center: { alignItems: 'center', paddingHorizontal: 32, gap: 28, marginTop: 40 },
  headline: { color: '#FFFFFF', fontSize: 30, lineHeight: 38, fontWeight: '900', textAlign: 'center', letterSpacing: 0.5 },
  brand: { alignItems: 'center', gap: 8 },
  appName: { color: '#FFFFFF', fontWeight: '900', letterSpacing: 4, fontSize: 13, marginTop: 4 },
  subtitle: { color: GOLD, fontWeight: '800', letterSpacing: 1.5, fontSize: 12, textAlign: 'center' },
  enterBtn: { position: 'absolute', bottom: 64, minHeight: 52, paddingHorizontal: 32, borderWidth: 1.5, borderColor: GOLD, justifyContent: 'center', alignItems: 'center', backgroundColor: 'rgba(212,175,55,0.08)' },
  enterText: { color: GOLD, fontWeight: '900', letterSpacing: 2.5, fontSize: 13 },
  skipBtn: { position: 'absolute', top: 56, right: 20, minHeight: 44, paddingHorizontal: 14, justifyContent: 'center', alignItems: 'center' },
  skipText: { color: 'rgba(255,255,255,0.7)', fontWeight: '800', letterSpacing: 2, fontSize: 11 },
});
