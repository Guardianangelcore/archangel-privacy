/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// AI Tactical Medic — voice-guided trauma protocols (ERC/AHA 2026), 100% offline cache
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { createAudioPlayer, setAudioModeAsync } from 'expo-audio';
import { api, API_BASE, getToken } from '@/src/api';
import { useAuth } from '@/src/auth';
import Paywall from '@/src/Paywall';
import Art50 from '@/src/Art50';
import { C, S } from '@/src/theme';
import { Lang } from '@/src/i18n';

const KEY = 'gh_medic_protocols';

export default function TacticalMedic() {
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'en';
  const router = useRouter();
  const [protocols, setProtocols] = useState<any[]>([]);
  const [locked, setLocked] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  const [active, setActive] = useState<any>(null);
  const [step, setStep] = useState(0);
  const [speaking, setSpeaking] = useState(false);
  const playerRef = useRef<any>(null);

  const load = useCallback(async () => {
    try {
      const res: any = await api('/medic/protocols');
      setProtocols(res.protocols || []); setLocked(null); setOffline(false);
      await AsyncStorage.setItem(KEY, JSON.stringify(res.protocols || []));
    } catch (e: any) {
      const m = String(e.message || e);
      if (m.includes('sentinel_required')) { setLocked(m.replace('sentinel_required:', '').trim()); return; }
      const cached = await AsyncStorage.getItem(KEY);
      if (cached) { setProtocols(JSON.parse(cached)); setOffline(true); }
      else setLocked(m);
    }
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => () => { try { playerRef.current?.remove?.(); } catch {} }, []);

  const speak = async (text: string) => {
    setSpeaking(true);
    try {
      const res: any = await api('/voice/tts', { method: 'POST', body: JSON.stringify({ text, voice: 'nova', language: lang }) });
      const token = await getToken();
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false } as any);
      try { playerRef.current?.remove?.(); } catch {}
      const player = createAudioPlayer({ uri: `${API_BASE}${res.url}`, headers: token ? { Authorization: `Bearer ${token}` } : {} });
      playerRef.current = player;
      player.play();
    } catch {}
    setTimeout(() => setSpeaking(false), 800);
  };

  return (
    <SafeAreaView testID="medic-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="md-back" onPress={() => (active ? setActive(null) : router.back())} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onError} />
        </Pressable>
        <Text style={st.title}>AI TACTICAL MEDIC</Text>
        <View style={{ width: 26 }} />
      </View>
      {offline && <View style={st.offBanner}><Text style={st.offText}>OFFLINE MODE · PROTOCOLS FROM LOCAL CACHE</Text></View>}

      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        {locked ? (
          <Paywall message={locked} onUnlocked={load} />
        ) : !active ? (
          <>
            <Text style={st.intro}>A field medic in your pocket — step-by-step voice guidance for life-saving procedures (ERC/AHA 2026). Works offline. In an emergency always call 112 first.</Text>
            {protocols.map(p => (
              <Pressable testID={`md-${p.id}`} key={p.id} onPress={() => { setActive(p); setStep(0); }} style={st.protoCard}>
                <Ionicons name={p.icon as any} size={26} color={C.error} />
                <View style={{ flex: 1 }}>
                  <Text style={st.protoTitle}>{p.title.toUpperCase()}</Text>
                  <Text style={st.protoWhen}>{p.when}</Text>
                </View>
                <Ionicons name="chevron-forward" size={20} color={C.info} />
              </Pressable>
            ))}
            <Art50 lang={lang} />
          </>
        ) : (
          <>
            <Text style={st.activeTitle}>{active.title.toUpperCase()}</Text>
            <Text style={st.source}>{active.source} · krok {step + 1}/{active.steps.length}</Text>
            <View style={st.stepBox}>
              <Text testID="md-step-text" style={st.stepText}>{active.steps[step]}</Text>
            </View>
            <Pressable testID="md-speak" onPress={() => speak(active.steps[step])} disabled={speaking} style={st.voiceBtn}>
              <Ionicons name={speaking ? 'volume-high' : 'volume-high-outline'} size={22} color={C.onInverse} />
              <Text style={st.voiceText}>{speaking ? 'JARVIS SPEAKING…' : 'READ ALOUD (JARVIS)'}</Text>
            </Pressable>
            <View style={st.navRow}>
              <Pressable testID="md-prev" onPress={() => setStep(Math.max(0, step - 1))} disabled={step === 0}
                style={[st.navBtn, step === 0 && { opacity: 0.3 }]}>
                <Ionicons name="arrow-back" size={20} color={C.fg} />
                <Text style={st.navText}>BACK</Text>
              </Pressable>
              <Pressable testID="md-next" onPress={() => setStep(Math.min(active.steps.length - 1, step + 1))}
                disabled={step >= active.steps.length - 1}
                style={[st.navBtn, { backgroundColor: C.error, borderColor: C.error }, step >= active.steps.length - 1 && { opacity: 0.3 }]}>
                <Text style={[st.navText, { color: C.onError }]}>NEXT STEP</Text>
                <Ionicons name="arrow-forward" size={20} color={C.onError} />
              </Pressable>
            </View>
            <Text style={st.call112}>☎ AT ANY TIME: CALL 112</Text>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.error },
  title: { color: C.onError, fontSize: 17, fontWeight: '900', letterSpacing: 2 },
  offBanner: { backgroundColor: C.warn, paddingVertical: 6, alignItems: 'center' },
  offText: { color: C.onWarn, fontWeight: '900', letterSpacing: 1, fontSize: 9 },
  intro: { color: C.onS3, fontSize: 12, lineHeight: 18, marginBottom: S.md },
  protoCard: { flexDirection: 'row', alignItems: 'center', gap: S.md, borderWidth: 2, borderColor: C.borderStrong, padding: S.lg, marginBottom: S.sm, backgroundColor: C.surface2, minHeight: 72 },
  protoTitle: { color: C.fg, fontWeight: '900', fontSize: 14, letterSpacing: 1 },
  protoWhen: { color: C.info, fontSize: 11, marginTop: 3, lineHeight: 15 },
  activeTitle: { color: C.error, fontWeight: '900', fontSize: 20, letterSpacing: 1 },
  source: { color: C.info, fontSize: 10, letterSpacing: 1, marginTop: 4 },
  stepBox: { marginTop: S.lg, borderWidth: 3, borderColor: C.error, padding: S.xl, backgroundColor: C.surface2, minHeight: 180, justifyContent: 'center' },
  stepText: { color: C.fg, fontSize: 22, lineHeight: 32, fontWeight: '800' },
  voiceBtn: { marginTop: S.md, flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', backgroundColor: C.inverse, paddingVertical: S.lg, minHeight: 56 },
  voiceText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  navRow: { flexDirection: 'row', gap: S.sm, marginTop: S.md },
  navBtn: { flex: 1, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: C.borderStrong, paddingVertical: S.lg, minHeight: 56 },
  navText: { fontWeight: '900', letterSpacing: 1, fontSize: 13, color: C.fg },
  call112: { marginTop: S.xl, textAlign: 'center', color: C.error, fontWeight: '900', letterSpacing: 2, fontSize: 12 },
});
