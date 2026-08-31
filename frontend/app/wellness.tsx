/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, Pressable, TextInput, ScrollView, ActivityIndicator, Platform, KeyboardAvoidingView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { createAudioPlayer, setAudioModeAsync } from 'expo-audio';
import { api, API_BASE, getToken } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';

type Checkin = { checkin_id: string; mood?: number; feeling_text?: string; sentiment_score: number; summary: string; reply: string; created_at: string };

const MOOD_ICONS: Record<number, any> = { 5: 'sunny', 4: 'partly-sunny', 3: 'cloud-outline', 2: 'rainy-outline', 1: 'thunderstorm-outline' };

export default function Wellness() {
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'en';
  const router = useRouter();
  const [mood, setMood] = useState<number | null>(null);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [reply, setReply] = useState('');
  const [history, setHistory] = useState<Checkin[]>([]);
  const playerRef = useRef<any>(null);

  const load = useCallback(async () => {
    try { setHistory(await api<Checkin[]>('/wellness/checkins')); } catch (e) { console.log(e); }
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => () => { try { playerRef.current?.remove?.(); } catch {} }, []);

  const speak = async (msg: string) => {
    try {
      const res: any = await api('/voice/tts', { method: 'POST', body: JSON.stringify({ text: msg, voice: 'nova', language: lang }) });
      const token = await getToken();
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false } as any);
      try { playerRef.current?.remove?.(); } catch {}
      const player = createAudioPlayer({ uri: `${API_BASE}${res.url}`, headers: token ? { Authorization: `Bearer ${token}` } : {} });
      playerRef.current = player;
      player.play();
    } catch (e) { console.log('tts err', e); }
  };

  const submit = async () => {
    if (!mood && !text.trim()) return;
    setBusy(true); setReply('');
    try {
      const res: any = await api('/wellness/checkin', {
        method: 'POST',
        body: JSON.stringify({ mood, feeling_text: text, language: lang }),
      });
      setReply(res.reply);
      setMood(null); setText('');
      load();
      speak(res.reply);
    } catch (e) { console.log(e); } finally { setBusy(false); }
  };

  return (
    <SafeAreaView testID="wellness-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="wl-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={styles.title}>{t('wellness_check', lang).toUpperCase()}</Text>
        <View style={{ width: 26 }} />
      </View>

      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
          <View style={styles.jarvisCard}>
            <View style={styles.jarvisRow}>
              <Ionicons name="sparkles" size={20} color={C.brand} />
              <Text style={styles.jarvisName}>JARVIS</Text>
              <Pressable testID="wellness-speak-q" onPress={() => speak(t('how_feel_today', lang))} hitSlop={10}>
                <Ionicons name="volume-high-outline" size={22} color={C.brand} />
              </Pressable>
            </View>
            <Text style={styles.question}>{t('how_feel_today', lang).toUpperCase()}</Text>
          </View>

          <View style={styles.moodRow}>
            {[5, 4, 3, 2, 1].map(m => (
              <Pressable
                testID={`mood-${m}`}
                key={m}
                onPress={() => setMood(m)}
                style={[styles.moodBtn, mood === m && styles.moodBtnActive, m <= 2 && mood === m && { backgroundColor: C.error, borderColor: C.error }]}
              >
                <Ionicons name={MOOD_ICONS[m]} size={28} color={mood === m ? C.onInverse : C.fg} />
                <Text style={[styles.moodLabel, mood === m && { color: C.onInverse }]}>{t(`mood_${m}`, lang).toUpperCase()}</Text>
              </Pressable>
            ))}
          </View>

          <Text style={styles.lbl}>{t('tell_more', lang).toUpperCase()}</Text>
          <TextInput
            testID="wellness-text"
            value={text}
            onChangeText={setText}
            multiline
            style={styles.input}
            placeholder="…"
            placeholderTextColor="#999"
          />

          <Pressable testID="wellness-submit" onPress={submit} disabled={busy || (!mood && !text.trim())} style={[styles.sendBtn, (!mood && !text.trim()) && { opacity: 0.4 }]}>
            {busy ? <ActivityIndicator color={C.onInverse} /> : <>
              <Ionicons name="paper-plane-outline" size={18} color={C.onInverse} />
              <Text style={styles.sendBtnText}>{t('send', lang).toUpperCase()}</Text>
            </>}
          </Pressable>

          {reply ? (
            <View testID="wellness-reply" style={styles.replyCard}>
              <Text style={styles.replyLabel}>JARVIS</Text>
              <Text style={styles.replyText}>{reply}</Text>
            </View>
          ) : null}

          <Text style={styles.section}>{t('mood_trend', lang).toUpperCase()}</Text>
          {history.length === 0 ? (
            <Text style={styles.noData}>{t('no_data', lang).toUpperCase()}</Text>
          ) : history.slice(0, 10).map(c => (
            <View key={c.checkin_id} style={styles.histRow}>
              <Ionicons name={MOOD_ICONS[c.sentiment_score] || 'cloud-outline'} size={22} color={c.sentiment_score <= 2 ? C.error : C.brand} />
              <View style={{ flex: 1 }}>
                <Text style={styles.histSummary}>{c.summary}</Text>
                <Text style={styles.histDate}>{String(c.created_at).slice(0, 16).replace('T', ' · ')}</Text>
              </View>
              <Text style={[styles.histScore, c.sentiment_score <= 2 && { color: C.error }]}>{c.sentiment_score}/5</Text>
            </View>
          ))}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.lg, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  jarvisCard: { borderWidth: 2, borderColor: C.brand, padding: S.lg, backgroundColor: C.brandTer },
  jarvisRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  jarvisName: { flex: 1, fontWeight: '900', letterSpacing: 2, color: C.brand, fontSize: 12 },
  question: { marginTop: S.md, fontSize: 22, fontWeight: '900', color: C.fg, letterSpacing: 1 },
  moodRow: { flexDirection: 'row', flexWrap: 'wrap', gap: S.sm, marginTop: S.lg },
  moodBtn: { width: '31%', aspectRatio: 1.1, borderWidth: 1.5, borderColor: C.borderStrong, alignItems: 'center', justifyContent: 'center', gap: 6, backgroundColor: C.bg },
  moodBtnActive: { backgroundColor: C.inverse, borderColor: C.inverse },
  moodLabel: { fontSize: 10, fontWeight: '900', letterSpacing: 1, color: C.fg, textAlign: 'center' },
  lbl: { fontSize: 10, letterSpacing: 2, color: C.onS3, fontWeight: '800', marginTop: S.lg, marginBottom: 6 },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 16, color: C.fg, minHeight: 70, textAlignVertical: 'top' },
  sendBtn: { marginTop: S.md, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.inverse, paddingVertical: S.lg },
  sendBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 14 },
  replyCard: { marginTop: S.lg, borderWidth: 2, borderColor: C.brand, padding: S.md, backgroundColor: C.bg },
  replyLabel: { fontSize: 10, letterSpacing: 2, color: C.brand, fontWeight: '900', marginBottom: 6 },
  replyText: { color: C.fg, fontSize: 16, lineHeight: 24 },
  section: { marginTop: S.xl, marginBottom: S.md, fontSize: 11, letterSpacing: 2, color: C.fg, fontWeight: '900' },
  noData: { color: C.onS3, fontSize: 12, letterSpacing: 1 },
  histRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, borderWidth: 1.5, borderColor: C.border, padding: S.md, marginBottom: S.sm },
  histSummary: { fontWeight: '800', color: C.fg, fontSize: 13 },
  histDate: { color: C.onS3, fontSize: 10, marginTop: 2, letterSpacing: 1 },
  histScore: { fontWeight: '900', color: C.brand, fontSize: 14 },
});
