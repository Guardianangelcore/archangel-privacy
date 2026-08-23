import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { createAudioPlayer, setAudioModeAsync } from 'expo-audio';
import { api, API_BASE, getToken } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';

const REGIONS = [
  { id: 'neck', tKey: 'region_neck', icon: 'body-outline' },
  { id: 'back', tKey: 'region_back', icon: 'walk-outline' },
  { id: 'shoulders', tKey: 'region_shoulders', icon: 'accessibility-outline' },
  { id: 'hips', tKey: 'region_hips', icon: 'body-outline' },
  { id: 'knees', tKey: 'region_knees', icon: 'walk-outline' },
  { id: 'hands', tKey: 'region_hands', icon: 'hand-left-outline' },
];
const INTENSITY = ['light', 'medium', 'firm'];

export default function Physio() {
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const router = useRouter();
  const [region, setRegion] = useState('neck');
  const [intensity, setIntensity] = useState('light');
  const [routine, setRoutine] = useState('');
  const [busy, setBusy] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const playerRef = useRef<any>(null);

  useEffect(() => () => { try { playerRef.current?.remove?.(); } catch {} }, []);

  const run = async () => {
    setBusy(true); setRoutine('');
    try {
      const res: any = await api('/physio/session', { method: 'POST', body: JSON.stringify({ region, intensity, language: lang }) });
      setRoutine(res.routine);
    } catch (e) { console.log(e); }
    setBusy(false);
  };

  const speak = async () => {
    if (!routine) return;
    setSpeaking(true);
    try {
      const res: any = await api('/voice/tts', { method: 'POST', body: JSON.stringify({ text: routine, voice: 'coral', language: lang }) });
      const token = await getToken();
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false } as any);
      try { playerRef.current?.remove?.(); } catch {}
      const p = createAudioPlayer({ uri: `${API_BASE}${res.url}`, headers: token ? { Authorization: `Bearer ${token}` } : {} });
      playerRef.current = p; p.play();
    } catch (e) {}
    setTimeout(() => setSpeaking(false), 400);
  };

  return (
    <SafeAreaView testID="physio-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="ph-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={styles.title}>PHYSIO-AI</Text>
        <View style={{ width: 26 }} />
      </View>
      <View style={styles.sub}><Text style={styles.subText}>FOUNDER'S LEGACY · SELF-MASSAGE & ERGONOMICS</Text></View>

      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 60 }}>
        <Text style={styles.lbl}>REGION</Text>
        <View style={styles.grid}>
          {REGIONS.map(r => (
            <Pressable testID={`region-${r.id}`} key={r.id} onPress={() => setRegion(r.id)} style={[styles.regTile, region === r.id && styles.regTileActive]}>
              <Ionicons name={r.icon as any} size={26} color={region === r.id ? C.onInverse : C.fg} />
              <Text style={[styles.regText, region === r.id && styles.regTextActive]}>{t(r.tKey, lang).toUpperCase()}</Text>
            </Pressable>
          ))}
        </View>

        <Text style={styles.lbl}>INTENSITY</Text>
        <View style={{ flexDirection: 'row', gap: S.sm }}>
          {INTENSITY.map(i => (
            <Pressable testID={`int-${i}`} key={i} onPress={() => setIntensity(i)} style={[styles.chip, intensity === i && styles.chipActive]}>
              <Text style={[styles.chipText, intensity === i && styles.chipTextActive]}>{i.toUpperCase()}</Text>
            </Pressable>
          ))}
        </View>

        <Pressable testID="ph-generate" onPress={run} disabled={busy} style={styles.runBtn}>
          {busy ? <ActivityIndicator color={C.onInverse} /> : <>
            <Ionicons name="sparkles-outline" size={16} color={C.onInverse} />
            <Text style={styles.runText}>GENERATE ROUTINE</Text>
          </>}
        </Pressable>

        {!!routine && (
          <View style={styles.outBox}>
            <Text style={styles.outLbl}>ROUTINE</Text>
            <Text style={styles.outText}>{routine}</Text>
            <Pressable testID="ph-speak" onPress={speak} disabled={speaking} style={styles.speakBtn}>
              <Ionicons name={speaking ? 'volume-high' : 'volume-medium-outline'} size={18} color={C.brand} />
              <Text style={styles.speakBtnText}>{t('speak', lang).toUpperCase()}</Text>
            </Pressable>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  sub: { paddingHorizontal: S.lg, paddingVertical: 6, backgroundColor: C.brandTer },
  subText: { color: C.brand, fontSize: 11, fontWeight: '900', letterSpacing: 1.5 },
  lbl: { fontSize: 11, letterSpacing: 2, color: C.fg, fontWeight: '900', marginTop: S.lg, marginBottom: S.sm },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: S.sm },
  regTile: { width: '31.5%', aspectRatio: 1, borderWidth: 1.5, borderColor: C.borderStrong, alignItems: 'center', justifyContent: 'center', gap: 6 },
  regTileActive: { backgroundColor: C.inverse },
  regText: { fontWeight: '900', fontSize: 11, letterSpacing: 1, color: C.fg },
  regTextActive: { color: C.onInverse },
  chip: { paddingHorizontal: S.md, paddingVertical: 10, borderWidth: 1.5, borderColor: C.borderStrong, flex: 1, alignItems: 'center' },
  chipActive: { backgroundColor: C.inverse },
  chipText: { fontWeight: '900', color: C.fg, letterSpacing: 1, fontSize: 12 },
  chipTextActive: { color: C.onInverse },
  runBtn: { marginTop: S.lg, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, paddingVertical: S.lg, borderWidth: 2, borderColor: C.borderStrong },
  runText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 14 },
  outBox: { marginTop: S.lg, borderWidth: 2, borderColor: C.borderStrong, padding: S.md, backgroundColor: C.brandTer },
  outLbl: { fontSize: 10, letterSpacing: 2, fontWeight: '900', color: C.brand, marginBottom: S.sm },
  outText: { color: C.fg, fontSize: 15, lineHeight: 22 },
  speakBtn: { marginTop: S.md, flexDirection: 'row', gap: 8, alignItems: 'center', alignSelf: 'flex-start', borderWidth: 1.5, borderColor: C.brand, paddingHorizontal: S.md, paddingVertical: 10, backgroundColor: C.bg },
  speakBtnText: { color: C.brand, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
});
