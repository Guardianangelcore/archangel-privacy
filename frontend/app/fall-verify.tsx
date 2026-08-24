/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// ANGEL MODE 2.0 — Fall verification: 120s empathetic loop + hands-free voice "Som v poriadku" (Whisper)
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, Pressable, Platform, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { useRouter } from 'expo-router';
import Svg, { Circle } from 'react-native-svg';
import { AudioModule, RecordingPresets, setAudioModeAsync, useAudioRecorder } from 'expo-audio';
import { api, API_BASE, getToken } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, S, R } from '@/src/theme';
import { t, Lang } from '@/src/i18n';

const TOTAL = 120; // Angel Mode 2.0 — seniors get 2 full minutes
const RING = 150;
const STROKE = 10;

export default function FallVerify() {
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const router = useRouter();
  const [remain, setRemain] = useState(TOTAL);
  const [phase, setPhase] = useState<'countdown' | 'sent' | 'ok'>('countdown');
  const [voiceState, setVoiceState] = useState<'idle' | 'recording' | 'checking' | 'failed'>('idle');
  const [heard, setHeard] = useState('');
  const timer = useRef<any>(null);
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const cancelledRef = useRef(false);

  useEffect(() => {
    timer.current = setInterval(() => {
      setRemain(r => {
        if (r <= 1) { clearInterval(timer.current); triggerSent(); return 0; }
        if (Platform.OS !== 'web') {
          if (r <= 15) Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy).catch(() => {});
          else if (r <= 45) Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
          else if (r % 5 === 0) Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
        }
        return r - 1;
      });
    }, 1000);
    return () => clearInterval(timer.current);
  }, []);

  const triggerSent = async () => {
    if (cancelledRef.current) return;
    setPhase('sent');
    try { await api('/fall-event', { method: 'POST', body: JSON.stringify({ verified: true, cancelled: false }) }); } catch {}
  };

  const cancel = useCallback(async (viaVoice = false) => {
    cancelledRef.current = true;
    clearInterval(timer.current);
    setPhase('ok');
    if (Platform.OS !== 'web') Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    if (!viaVoice) {
      try { await api('/fall-event', { method: 'POST', body: JSON.stringify({ verified: false, cancelled: true }) }); } catch {}
    }
    setTimeout(() => router.back(), 1200);
  }, [router]);

  const helpNow = async () => {
    clearInterval(timer.current);
    triggerSent();
  };

  // ---- VOICE-OFF: senior says "Som v poriadku" — hands-free cancel ----
  const listen = async () => {
    setHeard('');
    try {
      const perm = await AudioModule.getRecordingPermissionsAsync();
      if (!perm.granted) {
        if (!perm.canAskAgain) { setHeard('Mikrofón je zablokovaný v nastaveniach.'); setVoiceState('failed'); return; }
        const r = await AudioModule.requestRecordingPermissionsAsync();
        if (!r.granted) { setVoiceState('failed'); setHeard('Mikrofón nepovolený — použite tlačidlo SOM V PORIADKU.'); return; }
      }
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true } as any);
      setVoiceState('recording');
      await recorder.prepareToRecordAsync();
      recorder.record();
      setTimeout(async () => {
        try {
          await recorder.stop();
          setVoiceState('checking');
          const uri = recorder.uri;
          if (!uri) { setVoiceState('failed'); return; }
          const form = new FormData();
          if (Platform.OS === 'web') {
            const blob = await fetch(uri).then(r2 => r2.blob());
            form.append('file', blob, 'liveness.webm');
          } else {
            form.append('file', { uri, name: uri.endsWith('.m4a') ? 'liveness.m4a' : 'liveness.webm', type: uri.endsWith('.m4a') ? 'audio/mp4' : 'audio/webm' } as any);
          }
          const token = await getToken();
          const res = await fetch(`${API_BASE}/api/voice/liveness`, {
            method: 'POST', body: form,
            headers: token ? { Authorization: `Bearer ${token}` } : {},
          });
          const body = await res.json();
          if (!res.ok) throw new Error(body?.detail || 'STT failed');
          setHeard(body.transcript ? `Počul som: „${body.transcript}"` : '');
          if (body.ok_detected) cancel(true);
          else setVoiceState('failed');
        } catch (e: any) {
          console.log('liveness err', e);
          setVoiceState('failed');
          setHeard('Nepodarilo sa rozpoznať hlas — skúste znova alebo stlačte tlačidlo.');
        }
      }, 4000);
    } catch (e) {
      console.log('rec err', e);
      setVoiceState('failed');
    }
  };

  const urgent = remain <= 15;
  const bg = urgent ? C.error : '#1A1206';
  const accent = urgent ? C.onError : C.brand;
  const mm = Math.floor(remain / 60);
  const ss = remain % 60;
  const progress = remain / TOTAL;

  if (phase === 'ok') {
    return (
      <View testID="fall-ok" style={[st.root, { backgroundColor: C.brandPri }]}>
        <Ionicons name="checkmark-circle" size={90} color={C.onInverse} />
        <Text style={[st.big, { color: C.onInverse }]}>STE V PORIADKU ✓</Text>
        <Text style={[st.subBig, { color: C.onInverse }]}>ALARM ZRUŠENÝ</Text>
      </View>
    );
  }
  if (phase === 'sent') {
    return (
      <SafeAreaView testID="fall-sent" style={[st.root, { backgroundColor: C.error }]}>
        <Ionicons name="alert" size={90} color={C.onError} />
        <Text style={[st.big, { color: C.onError }]}>{t('get_help_now', lang).toUpperCase()}</Text>
        <Text style={[st.subBig, { color: C.onError }]}>UPOZORŇUJEM RODINU A KONTAKTY…</Text>
        <Pressable testID="fall-back" onPress={() => router.back()} style={st.exitBtn}>
          <Text style={st.exitBtnText}>ZAVRIEŤ</Text>
        </Pressable>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView testID="fall-verify-screen" style={[st.root, { backgroundColor: bg }]}>
      <Pressable testID="fall-help-now" onPress={helpNow} style={[st.topBtn, { borderColor: accent }]}>
        <Ionicons name="alert-circle-outline" size={22} color={accent} />
        <Text style={[st.topBtnText, { color: accent }]}>{t('get_help_now', lang).toUpperCase()}</Text>
      </Pressable>

      <View style={st.center}>
        <Text style={[st.fallLabel, { color: accent }]}>{t('fall_detected', lang).toUpperCase()}</Text>
        <View style={{ width: RING + 60, height: RING + 60, alignItems: 'center', justifyContent: 'center' }}>
          <Svg width={RING + 60} height={RING + 60} style={StyleSheet.absoluteFill as any}>
            <Circle cx={(RING + 60) / 2} cy={(RING + 60) / 2} r={RING / 2 - STROKE / 2 + 30}
              stroke="rgba(255,255,255,0.12)" strokeWidth={STROKE} fill="none" />
            <Circle cx={(RING + 60) / 2} cy={(RING + 60) / 2} r={RING / 2 - STROKE / 2 + 30}
              stroke={urgent ? '#FFFFFF' : C.brand} strokeWidth={STROKE} fill="none"
              strokeLinecap="round"
              strokeDasharray={`${2 * Math.PI * (RING / 2 - STROKE / 2 + 30)}`}
              strokeDashoffset={`${2 * Math.PI * (RING / 2 - STROKE / 2 + 30) * (1 - progress)}`}
              transform={`rotate(-90 ${(RING + 60) / 2} ${(RING + 60) / 2})`} />
          </Svg>
          <Text testID="fall-countdown" style={[st.countdown, { color: accent }]}>{mm}:{String(ss).padStart(2, '0')}</Text>
        </View>
        <Text style={[st.subBig, { color: accent }]}>DO ODOSLANIA ALARMU</Text>

        <Pressable testID="fall-voice" onPress={listen} disabled={voiceState === 'recording' || voiceState === 'checking'}
          style={[st.voiceBtn, voiceState === 'recording' && { backgroundColor: C.error, borderColor: C.error }]}>
          {voiceState === 'checking' ? <ActivityIndicator color={C.brand} /> : (
            <Ionicons name={voiceState === 'recording' ? 'mic' : 'mic-outline'} size={30} color={voiceState === 'recording' ? '#FFF' : C.brand} />
          )}
          <Text style={[st.voiceText, voiceState === 'recording' && { color: '#FFF' }]}>
            {voiceState === 'recording' ? 'POČÚVAM… HOVORTE TERAZ' : voiceState === 'checking' ? 'OVERUJEM HLAS…' : 'POVEDZTE: „SOM V PORIADKU!"'}
          </Text>
        </Pressable>
        {!!heard && <Text testID="fall-heard" style={st.heard}>{heard}</Text>}
      </View>

      <Pressable testID="fall-im-ok" onPress={() => cancel(false)} style={st.okBtn}>
        <Text style={st.okBtnText}>{t('im_ok', lang).toUpperCase()}</Text>
      </Pressable>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, justifyContent: 'space-between', alignItems: 'center', padding: S.lg },
  topBtn: { flexDirection: 'row', alignItems: 'center', gap: 8, borderWidth: 2, borderRadius: R.pill, paddingHorizontal: S.lg, minHeight: 56, alignSelf: 'stretch', justifyContent: 'center', marginTop: S.md },
  topBtnText: { fontWeight: '900', letterSpacing: 2, fontSize: 15 },
  center: { alignItems: 'center', gap: S.md },
  fallLabel: { fontSize: 19, fontWeight: '900', letterSpacing: 3 },
  countdown: { fontSize: 56, fontWeight: '900', fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }), letterSpacing: 2 },
  subBig: { fontSize: 13, letterSpacing: 3, fontWeight: '800' },
  big: { fontSize: 32, fontWeight: '900', letterSpacing: 2, marginTop: S.lg, textAlign: 'center' },
  voiceBtn: { flexDirection: 'row', gap: S.md, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: C.brand, borderRadius: R.pill, paddingHorizontal: S.xl, minHeight: 64, marginTop: S.md, backgroundColor: 'rgba(212,175,55,0.10)' },
  voiceText: { color: C.brand, fontWeight: '900', fontSize: 14, letterSpacing: 1 },
  heard: { color: 'rgba(255,255,255,0.8)', fontSize: 12, marginTop: S.sm, textAlign: 'center' },
  okBtn: { alignSelf: 'stretch', backgroundColor: C.brand, borderRadius: R.lg, paddingVertical: 36, alignItems: 'center', marginBottom: S.md },
  okBtnText: { color: C.onInverse, fontSize: 32, fontWeight: '900', letterSpacing: 3 },
  exitBtn: { marginTop: S.xl, borderWidth: 2, borderColor: C.onError, borderRadius: R.pill, paddingHorizontal: S.xl, minHeight: 52, justifyContent: 'center' },
  exitBtnText: { color: C.onError, fontWeight: '900', letterSpacing: 2 },
});
