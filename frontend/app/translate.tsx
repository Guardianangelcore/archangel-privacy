/* Copyright © 2026 Guardian Angel. All Rights Reserved. This source code and its logic are the sole property of Guardian Angel. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, TextInput, Pressable, ScrollView, ActivityIndicator, Platform, KeyboardAvoidingView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { createAudioPlayer, setAudioModeAsync } from 'expo-audio';
import { api, API_BASE, getToken } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';

export default function Translate() {
  const { user } = useAuth();
  const router = useRouter();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const [text, setText] = useState('');
  const [out, setOut] = useState('');
  const [busy, setBusy] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [err, setErr] = useState('');
  const playerRef = useRef<any>(null);

  useEffect(() => () => { try { playerRef.current?.remove?.(); } catch {} }, []);

  const speak = async () => {
    if (!out) return;
    setSpeaking(true);
    try {
      const res: any = await api('/voice/tts', { method: 'POST', body: JSON.stringify({ text: out, voice: 'nova', language: lang }) });
      const token = await getToken();
      const url = `${API_BASE}${res.url}`;
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false } as any);
      try { playerRef.current?.remove?.(); } catch {}
      const player = createAudioPlayer({ uri: url, headers: token ? { Authorization: `Bearer ${token}` } : {} });
      playerRef.current = player;
      player.play();
    } catch (e: any) {
      setErr(String(e.message || e));
    } finally { setTimeout(() => setSpeaking(false), 500); }
  };

  const run = async () => {
    if (!text.trim()) return;
    setBusy(true); setErr(''); setOut('');
    try {
      const res: any = await api('/ai/translate', { method: 'POST', body: JSON.stringify({ text, language: lang }) });
      setOut(res.plain_language);
    } catch (e: any) {
      setErr(String(e.message || e));
    } finally { setBusy(false); }
  };

  return (
    <SafeAreaView testID="translate-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="tr-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={styles.title}>AI HEALTH TRANSLATOR</Text>
        <View style={{ width: 26 }} />
      </View>

      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 40 }}>
          <Text style={styles.sub}>JARVIS ENGINE · CLAUDE SONNET 5</Text>
          <TextInput
            testID="tr-input"
            value={text}
            onChangeText={setText}
            multiline
            style={styles.input}
            placeholder={t('paste_medical', lang)}
            placeholderTextColor="#999"
          />
          <Pressable testID="tr-run" onPress={run} disabled={busy} style={styles.run}>
            {busy ? <ActivityIndicator color={C.onInverse} /> : (
              <>
                <Ionicons name="sparkles-outline" size={16} color={C.onInverse} />
                <Text style={styles.runText}>{t('translate', lang).toUpperCase()}</Text>
              </>
            )}
          </Pressable>

          {busy && <Text style={styles.busy}>{t('translating', lang)}</Text>}
          {!!err && <Text style={styles.err}>{err}</Text>}
          {!!out && (
            <View style={styles.outBox}>
              <Text style={styles.outLbl}>PLAIN LANGUAGE</Text>
              <Text style={styles.outText}>{out}</Text>
              <Pressable testID="tr-speak" onPress={speak} disabled={speaking} style={styles.speakBtn}>
                <Ionicons name={speaking ? 'volume-high' : 'volume-medium-outline'} size={18} color={C.brand} />
                <Text style={styles.speakBtnText}>{t('speak', lang).toUpperCase()}</Text>
              </Pressable>
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 16, fontWeight: '900', letterSpacing: 2 },
  sub: { fontSize: 10, letterSpacing: 2, color: C.onS3, fontWeight: '800' },
  input: { marginTop: S.md, minHeight: 180, borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 15, color: C.fg, textAlignVertical: 'top' },
  run: { flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.inverse, paddingVertical: S.lg, marginTop: S.md },
  runText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 14 },
  busy: { marginTop: S.md, color: C.onS3, letterSpacing: 2, fontSize: 12, fontWeight: '800' },
  err: { marginTop: S.md, color: C.error, fontSize: 12, letterSpacing: 1 },
  outBox: { marginTop: S.lg, borderWidth: 2, borderColor: C.borderStrong, padding: S.md, backgroundColor: C.brandTer },
  outLbl: { fontSize: 10, letterSpacing: 2, fontWeight: '900', color: C.brand, marginBottom: S.sm },
  outText: { color: C.fg, fontSize: 16, lineHeight: 24 },
  speakBtn: { marginTop: S.md, flexDirection: 'row', gap: 8, alignItems: 'center', alignSelf: 'flex-start', borderWidth: 1.5, borderColor: C.brand, paddingHorizontal: S.md, paddingVertical: 10, backgroundColor: C.bg },
  speakBtnText: { color: C.brand, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
});
