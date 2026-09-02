/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// SILENT WITNESS — decentralised evidence recorder.
// One-tap start: streams encrypted audio chunks straight into the Sovereign Vault.
// Frontend gesture (triple tap on the header) also triggers it silently.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ActivityIndicator, ScrollView, Platform, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import Animated, { useSharedValue, useAnimatedStyle, withRepeat, withTiming, Easing, cancelAnimation } from 'react-native-reanimated';
import { useAudioRecorder, RecordingPresets, AudioModule, setAudioModeAsync } from 'expo-audio';
import { api, apiUpload } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, S, R } from '@/src/theme';
import { tap } from '@/src/ui/glass';
import { speak as jarvisSpeak } from '@/src/voice';
import { useI18n } from '@/src/i18n-context';

const CHUNK_MS = 20_000; // 20 seconds per chunk — small enough to survive a broken device

type Session = { session_id: string; opened_at: string; closed_at?: string | null; chunk_count: number; total_bytes: number; status: string };

export default function SilentWitness() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const params = useLocalSearchParams<{ panic?: string; sid?: string }>();
  const { user } = useAuth();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chunkIndex, setChunkIndex] = useState(0);
  const [recording, setRecording] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [history, setHistory] = useState<Session[]>([]);
  const [err, setErr] = useState('');
  const [micBlocked, setMicBlocked] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const recorder = useAudioRecorder(RecordingPresets.LOW_QUALITY); // low bitrate for evidence, small chunks
  const timerRef = useRef<any>(null);
  const chunkTimerRef = useRef<any>(null);
  const startedAt = useRef<number>(0);
  const pulse = useSharedValue(0);

  const load = useCallback(async () => {
    try {
      const r: any = await api('/silent-witness/sessions');
      setHistory(r.sessions || []);
    } catch (e) { console.log(e); }
  }, []);
  useEffect(() => { load(); }, [load]);

  // PANIC GESTURE AUTO-START — the deep link ?panic=1 arrives when the user
  // taps 19× on the back of the phone. Start recording without another tap.
  useEffect(() => {
    if (params.panic === '1' && !recording && !sessionId) {
      // Small delay to let the screen mount before triggering mic permission
      const t = setTimeout(() => { startSession(); }, 400);
      return () => clearTimeout(t);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.panic]);

  useEffect(() => {
    if (recording) {
      pulse.value = withRepeat(withTiming(1, { duration: 900, easing: Easing.inOut(Easing.sin) }), -1, true);
      startedAt.current = Date.now();
      timerRef.current = setInterval(() => setElapsed(Math.floor((Date.now() - startedAt.current) / 1000)), 500);
    } else {
      cancelAnimation(pulse);
      pulse.value = 0;
      setElapsed(0);
      if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    }
  }, [recording, pulse]);
  const pulseStyle = useAnimatedStyle(() => ({
    transform: [{ scale: 1 + pulse.value * 0.18 }],
    opacity: 0.55 + pulse.value * 0.45,
  }));

  const startSession = async () => {
    setErr('');
    if (Platform.OS === 'web') { setErr('Silent Witness works in the native app.'); return; }
    try {
      let perm = await AudioModule.getRecordingPermissionsAsync();
      if (!perm.granted) {
        if (perm.canAskAgain === false) { setMicBlocked(true); return; }
        perm = await AudioModule.requestRecordingPermissionsAsync();
        if (!perm.granted) { setMicBlocked(perm.canAskAgain === false); return; }
      }
      setMicBlocked(false);
      const opened: any = await api('/silent-witness/session', { method: 'POST' });
      setSessionId(opened.session_id);
      setChunkIndex(0);
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true } as any);
      await recorder.prepareToRecordAsync();
      recorder.record();
      setRecording(true);
      tap('medium');
      jarvisSpeak('Silent Witness active. Evidence is streaming to your Vault.', {
        voice: 'onyx', speed: 0.95, language: (user?.language as any) || 'en',
      });
      // schedule rolling chunk uploads
      scheduleNextChunk(opened.session_id);
    } catch (e: any) { setErr(String(e?.message || e)); }
  };

  const scheduleNextChunk = (sid: string) => {
    chunkTimerRef.current = setTimeout(async () => {
      await rotateChunk(sid);
      if (recording && sessionId === sid) scheduleNextChunk(sid);
    }, CHUNK_MS);
  };

  const rotateChunk = async (sid: string) => {
    try {
      await recorder.stop();
      const uri = recorder.uri;
      if (uri) {
        setUploading(true);
        const name = uri.endsWith('.m4a') ? 'chunk.m4a' : 'chunk.webm';
        const ct = uri.endsWith('.m4a') ? 'audio/m4a' : 'audio/webm';
        await apiUpload(`/silent-witness/${sid}/chunk`, uri, name, ct, { index: String(chunkIndex) });
        setChunkIndex((i) => i + 1);
        setUploading(false);
      }
      // Immediately restart recording for the next chunk
      if (recording) {
        await recorder.prepareToRecordAsync();
        recorder.record();
      }
    } catch (e) { console.log('chunk rotate err', e); }
  };

  const stop = async () => {
    if (!sessionId) return;
    try {
      if (chunkTimerRef.current) { clearTimeout(chunkTimerRef.current); chunkTimerRef.current = null; }
      await recorder.stop();
      const uri = recorder.uri;
      if (uri) {
        setUploading(true);
        const name = uri.endsWith('.m4a') ? 'chunk.m4a' : 'chunk.webm';
        const ct = uri.endsWith('.m4a') ? 'audio/m4a' : 'audio/webm';
        await apiUpload(`/silent-witness/${sessionId}/chunk`, uri, name, ct, { index: String(chunkIndex) });
      }
      await api(`/silent-witness/${sessionId}/close`, { method: 'POST' });
      setUploading(false);
      setRecording(false);
      setSessionId(null);
      tap('success');
      jarvisSpeak('Evidence sealed and secured in your Vault.', {
        voice: 'onyx', speed: 0.95, language: (user?.language as any) || 'en',
      });
      await load();
    } catch (e: any) { setErr(String(e?.message || e)); }
  };

  return (
    <SafeAreaView testID="silent-witness-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="sw-back" onPress={() => { tap(); router.back(); }} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>{tt('silent_witness.silent_witness')}</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 120 }}>
        <Text style={styles.intro}>
          {tt('silent_witness.if_you_end_up_in_a_conflict_an_offic')} <Text style={{ color: C.brand, fontWeight: '900' }}>{tt('silent_witness.instantly_streamed_to_your_vault')}</Text> {tt('silent_witness.and_alerts_your_inner_circle_if_your')}
        </Text>

        <View style={styles.recRing}>
          <Animated.View style={[styles.recGlow, pulseStyle, recording && styles.recGlowActive]} />
          <Pressable
            testID={recording ? 'sw-stop' : 'sw-start'}
            onPress={recording ? stop : startSession}
            style={[styles.recBtn, recording && styles.recBtnActive]}
          >
            {uploading && !recording ? <ActivityIndicator color={C.onInverse} size="large" /> : (
              <Ionicons name={recording ? 'stop-circle' : 'radio'} size={60} color={recording ? C.onError : C.onInverse} />
            )}
          </Pressable>
        </View>

        {recording && (
          <View testID="sw-live" style={styles.live}>
            <View style={styles.liveDot} />
            <Text style={styles.liveText}>
              {tt('silent_witness.live')} {elapsed}s · {chunkIndex} {tt('silent_witness.chunk_s_in_the_vault')}
              {uploading ? '  ↑' : ''}
            </Text>
          </View>
        )}

        {!!err && <Text style={styles.err}>{err}</Text>}
        {micBlocked && (
          <Pressable onPress={() => Linking.openSettings()} style={styles.settingsBtn}>
            <Ionicons name="settings-outline" size={14} color={C.brand} />
            <Text style={styles.settingsText}>{tt('silent_witness.microphone_blocked_open_settings')}</Text>
          </Pressable>
        )}

        <Text style={styles.section}>{tt('silent_witness.history')} {history.length}</Text>
        {history.length === 0 && (
          <Text style={styles.empty}>{tt('silent_witness.no_recordings_that_is_a_good_thing')}</Text>
        )}
        {history.map((s) => (
          <View key={s.session_id} testID={`sw-sess-${s.session_id}`} style={styles.sessCard}>
            <Ionicons name="lock-closed" size={20} color={s.status === 'active' ? C.error : C.brand} />
            <View style={{ flex: 1 }}>
              <Text style={styles.sessDate}>{new Date(s.opened_at).toLocaleString('sk-SK')}</Text>
              <Text style={styles.sessMeta}>
                {s.chunk_count} {tt('silent_witness.chunks')} {Math.round((s.total_bytes || 0) / 1024)} {tt('silent_witness.kb')} {s.status === 'active' ? tt('silent_witness.in_progress') : tt('silent_witness.sealed')}
              </Text>
            </View>
          </View>
        ))}

        <View style={styles.hint}>
          <Ionicons name="information-circle-outline" size={14} color={C.info} />
          <Text style={styles.hintText}>
            {tt('silent_witness.recordings_are_encrypted_server_side')}
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.brand, fontWeight: '900', fontSize: 13, letterSpacing: 2.5 },
  intro: { color: C.fg, fontSize: 13, lineHeight: 20 },
  recRing: { alignSelf: 'center', width: 220, height: 220, alignItems: 'center', justifyContent: 'center', marginTop: S.xxl },
  recGlow: { position: 'absolute', width: 220, height: 220, borderRadius: 110, backgroundColor: 'rgba(212,175,55,0.14)' },
  recGlowActive: { backgroundColor: 'rgba(239,68,68,0.28)' },
  recBtn: { width: 160, height: 160, borderRadius: 80, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center', borderWidth: 3, borderColor: C.brandSec },
  recBtnActive: { backgroundColor: C.error, borderColor: C.error },
  live: { flexDirection: 'row', alignItems: 'center', gap: 8, alignSelf: 'center', marginTop: S.lg },
  liveDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: C.error },
  liveText: { color: C.fg, fontSize: 13, fontWeight: '900', letterSpacing: 1 },
  err: { color: C.error, fontSize: 12, textAlign: 'center', marginTop: S.md },
  settingsBtn: { flexDirection: 'row', gap: 6, alignItems: 'center', justifyContent: 'center', marginTop: S.md, minHeight: 44, paddingHorizontal: S.md, borderWidth: 1, borderColor: C.brand, borderRadius: R.pill },
  settingsText: { color: C.brand, fontWeight: '800', fontSize: 11 },
  section: { color: C.brand, fontWeight: '900', fontSize: 10, letterSpacing: 2, marginTop: S.xxl, marginBottom: S.sm },
  empty: { color: C.info, fontSize: 12, fontStyle: 'italic' },
  sessCard: { flexDirection: 'row', gap: S.md, alignItems: 'center', backgroundColor: C.surface2, borderRadius: R.md, padding: S.md, marginBottom: S.sm, borderWidth: 1, borderColor: C.border },
  sessDate: { color: C.fg, fontSize: 13, fontWeight: '800' },
  sessMeta: { color: C.onS3, fontSize: 11, marginTop: 2 },
  hint: { flexDirection: 'row', gap: 6, alignItems: 'flex-start', marginTop: S.xl, padding: S.md, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, backgroundColor: C.surface2 },
  hintText: { color: C.info, fontSize: 11, lineHeight: 16, flex: 1 },
});
