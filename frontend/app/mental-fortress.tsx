/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { createAudioPlayer, setAudioModeAsync } from 'expo-audio';
import { useAuth } from '@/src/auth';
import { api, API_BASE, getToken } from '@/src/api';
import { C, S, R } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

const LANGS = [['sk', 'SK'], ['cs', 'CZ'], ['en', 'EN'], ['de', 'DE']];

export default function MentalFortress() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const { user } = useAuth();
  const [lang, setLang] = useState<string>(['sk', 'cs', 'en', 'de'].includes(user?.language || '') ? (user?.language as string) : 'en');
  const [data, setData] = useState<any>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [speaking, setSpeaking] = useState<string | null>(null);
  const [err, setErr] = useState('');
  const playerRef = useRef<any>(null);

  useEffect(() => {
    (async () => {
      try { setData(await api(`/mental/techniques?language=${lang}`)); } catch (e: any) { setErr(String(e.message || e)); }
    })();
  }, [lang]);

  useEffect(() => () => { try { playerRef.current?.remove?.(); } catch {} }, []);

  const speak = async (t: any) => {
    setSpeaking(t.id); setErr('');
    try {
      const res: any = await api('/voice/tts', { method: 'POST', body: JSON.stringify({ text: t.tts_text, voice: 'onyx', language: lang }) });
      const token = await getToken();
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false } as any);
      try { playerRef.current?.remove?.(); } catch {}
      const player = createAudioPlayer({ uri: `${API_BASE}${res.url}`, headers: token ? { Authorization: `Bearer ${token}` } : {} });
      playerRef.current = player;
      player.play();
    } catch (e: any) {
      setErr(String(e.message || e));
    } finally { setTimeout(() => setSpeaking(null), 800); }
  };

  return (
    <SafeAreaView testID="mental-fortress-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="mf-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>{tt('mental_fortress.mental_fortress')}</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }}>
        <View style={styles.heroIcon}><Ionicons name="shield-outline" size={28} color={C.brand} /></View>
        <Text style={styles.h1}>{tt('mental_fortress.crisis_audio_guide')}</Text>
        <Text style={styles.sub}>
          {tt('mental_fortress.voice_guided_techniques_against_pani')}
        </Text>
        {!!err && <Text style={styles.err}>{err}</Text>}
        <View style={styles.langRow}>
          {LANGS.map(([code, label]) => (
            <Pressable key={code} testID={`mf-lang-${code}`} onPress={() => setLang(code)} style={[styles.langChip, lang === code && { backgroundColor: C.brand, borderColor: C.brand }]}>
              <Text style={[styles.langChipText, lang === code && { color: C.onInverse }]}>{label}</Text>
            </Pressable>
          ))}
        </View>
        {!data && !err && <ActivityIndicator color={C.brand} style={{ marginTop: 40 }} />}

        <View style={{ marginTop: S.xl, gap: S.md }}>
          {(data?.techniques || []).map((t: any) => {
            const expanded = open === t.id;
            return (
              <View key={t.id} style={styles.card}>
                <Pressable testID={`mf-item-${t.id}`} onPress={() => setOpen(expanded ? null : t.id)} style={styles.cardHead}>
                  <View style={styles.cardIcon}><Ionicons name={t.icon} size={20} color={C.brand} /></View>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.cardTitle}>{tx(t.title)}</Text>
                    <Text style={styles.cardSub}>{tx(t.subtitle)}</Text>
                  </View>
                  <Pressable
                    testID={`mf-play-${t.id}`}
                    onPress={() => speak(t)}
                    disabled={speaking === t.id}
                    hitSlop={8}
                    style={styles.playBtn}
                  >
                    {speaking === t.id
                      ? <ActivityIndicator size="small" color={C.onInverse} />
                      : <Ionicons name="play" size={18} color={C.onInverse} />}
                  </Pressable>
                </Pressable>
                {expanded && (
                  <View style={styles.stepsBox}>
                    {t.steps.map((s: string, i: number) => (
                      <View key={i} style={styles.stepRow}>
                        <Text style={styles.stepNum}>{i + 1}</Text>
                        <Text style={styles.stepText}>{s}</Text>
                      </View>
                    ))}
                  </View>
                )}
              </View>
            );
          })}
        </View>

        {data?.disclaimer && <Text style={styles.disclaimer}>{data.disclaimer}</Text>}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 14 },
  heroIcon: { width: 56, height: 56, borderRadius: R.lg, backgroundColor: C.brandTer, alignItems: 'center', justifyContent: 'center' },
  h1: { marginTop: S.lg, fontSize: 24, fontWeight: '900', color: C.fg },
  sub: { marginTop: S.sm, fontSize: 13, color: C.onS3, lineHeight: 19 },
  card: { backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border },
  cardHead: { flexDirection: 'row', alignItems: 'center', gap: S.md, padding: S.lg },
  cardIcon: { width: 40, height: 40, borderRadius: R.sm, backgroundColor: C.brandTer, alignItems: 'center', justifyContent: 'center' },
  cardTitle: { color: C.fg, fontWeight: '800', fontSize: 14 },
  cardSub: { color: C.info, fontSize: 11, marginTop: 2, lineHeight: 15 },
  playBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center' },
  stepsBox: { borderTopWidth: 1, borderTopColor: C.border, padding: S.lg, gap: S.md },
  stepRow: { flexDirection: 'row', gap: S.md },
  stepNum: { width: 22, height: 22, borderRadius: 11, backgroundColor: C.brandTer, color: C.brand, textAlign: 'center', fontWeight: '900', fontSize: 12, lineHeight: 22, overflow: 'hidden' },
  stepText: { flex: 1, color: C.fg, fontSize: 13, lineHeight: 19 },
  disclaimer: { marginTop: S.xl, color: C.info, fontSize: 10, lineHeight: 15, textAlign: 'center' },
  err: { color: C.error, marginTop: S.md, fontSize: 12 },
  langRow: { flexDirection: 'row', gap: S.sm, marginTop: S.lg },
  langChip: { borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.pill, paddingHorizontal: S.lg, paddingVertical: 8 },
  langChipText: { color: C.fg, fontWeight: '800', fontSize: 11, letterSpacing: 0.5 },
});
