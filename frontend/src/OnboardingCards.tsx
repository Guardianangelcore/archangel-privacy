/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// ONBOARDING FLOW — FIRST launch only (AsyncStorage flag), right after the Cinematic Intro.
// 4 swipeable cards, progress dots, Skip always visible top-right, black canvas + gold accents.
import React, { useRef, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, NativeSyntheticEvent, NativeScrollEvent, useWindowDimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { useI18n } from './i18n-context';

export const FIRST_LAUNCH_KEY = 'ga.first_launch.done.v1';
const GOLD = '#D4AF37';

/** First-launch check with a 3 s safety timeout — if storage does not answer, behave as NOT first
 *  launch so the app never waits on it. */
export async function isFirstLaunch(): Promise<boolean> {
  try {
    const read = AsyncStorage.getItem(FIRST_LAUNCH_KEY).then(v => !v);
    const timeout = new Promise<boolean>(res => setTimeout(() => res(false), 3000));
    return await Promise.race([read, timeout]);
  } catch { return false; }
}

const CARDS: { key: string; icon: any }[] = [
  { key: 'health', icon: 'heart' },
  { key: 'survive', icon: 'shield-checkmark' },
  { key: 'earn', icon: 'logo-bitcoin' },
  { key: 'join', icon: 'planet' },
];

export function OnboardingCards({ onDone }: { onDone: () => void }) {
  const { t: tt } = useI18n();
  const { width } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const [page, setPage] = useState(0);
  const scroll = useRef<ScrollView>(null);

  const finish = async (goLogin: boolean) => {
    try { await AsyncStorage.setItem(FIRST_LAUNCH_KEY, new Date().toISOString()); } catch {}
    onDone();
    if (goLogin) router.replace('/login' as any);
  };
  const onScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => setPage(Math.round(e.nativeEvent.contentOffset.x / width));
  const next = () => { const p = Math.min(page + 1, CARDS.length - 1); setPage(p); scroll.current?.scrollTo({ x: width * p, animated: true }); };

  return (
    <View testID="onboarding-cards" style={[st.root, { paddingTop: insets.top + 12, paddingBottom: insets.bottom + 20 }]}>
      <Pressable testID="ob-skip" onPress={() => finish(false)} style={st.skip} hitSlop={10}>
        <Text style={st.skipText}>{tt('onboarding.skip')}</Text>
      </Pressable>

      <ScrollView ref={scroll} horizontal pagingEnabled showsHorizontalScrollIndicator={false} onMomentumScrollEnd={onScroll} onScrollEndDrag={onScroll} onScroll={onScroll} scrollEventThrottle={32} style={{ flex: 1 }}>
        {CARDS.map((c, i) => (
          <View key={c.key} testID={`ob-card-${i}`} style={[st.card, { width }]}>
            <View style={st.iconRing}><Ionicons name={c.icon} size={56} color={GOLD} /></View>
            <Text style={st.title}>{tt(`onboarding.${c.key}_title`)}</Text>
            <Text style={st.desc}>{tt(`onboarding.${c.key}_desc`)}</Text>
            {i === CARDS.length - 1 && (
              <View style={st.ctaWrap}>
                <Pressable testID="ob-get-started" onPress={() => finish(true)} style={st.primary}>
                  <Text style={st.primaryText}>{tt('onboarding.get_started_free')}</Text>
                </Pressable>
                <Pressable testID="ob-have-account" onPress={() => finish(true)} style={st.secondary}>
                  <Text style={st.secondaryText}>{tt('onboarding.i_already_have_an_account')}</Text>
                </Pressable>
              </View>
            )}
          </View>
        ))}
      </ScrollView>

      <View style={st.footer}>
        <View style={st.dots}>
          {CARDS.map((_, i) => <View key={i} testID={`ob-dot-${i}`} style={[st.dot, i === page && st.dotOn]} />)}
        </View>
        {page < CARDS.length - 1 && (
          <Pressable testID="ob-next" onPress={next} style={st.nextBtn} hitSlop={8}>
            <Text style={st.nextText}>{tt('onboarding.next')}</Text>
            <Ionicons name="arrow-forward" size={16} color={GOLD} />
          </Pressable>
        )}
      </View>
    </View>
  );
}

const st = StyleSheet.create({
  root: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: '#050507', zIndex: 1900 },
  skip: { position: 'absolute', right: 20, top: 56, zIndex: 5, minHeight: 44, justifyContent: 'center', paddingHorizontal: 8 },
  skipText: { color: '#9A9AA5', fontWeight: '800', letterSpacing: 2, fontSize: 12 },
  card: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, gap: 18 },
  iconRing: { width: 120, height: 120, borderRadius: 60, borderWidth: 1.5, borderColor: GOLD, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(212,175,55,0.06)', marginBottom: 8 },
  title: { color: '#FFFFFF', fontSize: 26, lineHeight: 33, fontWeight: '900', textAlign: 'center', letterSpacing: 0.3 },
  desc: { color: '#B9B9C0', fontSize: 15, lineHeight: 23, textAlign: 'center' },
  ctaWrap: { alignSelf: 'stretch', gap: 12, marginTop: 16 },
  primary: { backgroundColor: GOLD, minHeight: 54, alignItems: 'center', justifyContent: 'center' },
  primaryText: { color: '#0B0B0D', fontWeight: '900', letterSpacing: 2, fontSize: 13 },
  secondary: { borderWidth: 1.5, borderColor: GOLD, minHeight: 54, alignItems: 'center', justifyContent: 'center' },
  secondaryText: { color: GOLD, fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  footer: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 28, minHeight: 48 },
  dots: { flexDirection: 'row', gap: 8 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#2E2E38' },
  dotOn: { backgroundColor: GOLD, width: 22 },
  nextBtn: { flexDirection: 'row', alignItems: 'center', gap: 8, minHeight: 44, paddingHorizontal: 8 },
  nextText: { color: GOLD, fontWeight: '900', letterSpacing: 2, fontSize: 12 },
});
