/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// VOICE SIGNATURE — Inner Circle 5-second voice print.
// Each family member records their voice once. From then on, when they send a
// Voice Echo, Jarvis (Onyx) announces the sender by name to babička before the
// real recording plays. The audio itself is stored server-side so a future
// voice-ID model can match unknown callers.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ActivityIndicator, TextInput, Platform, Linking, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import Animated, { useSharedValue, useAnimatedStyle, withRepeat, withTiming, Easing, cancelAnimation } from 'react-native-reanimated';
import { useAudioRecorder, RecordingPresets, AudioModule, setAudioModeAsync } from 'expo-audio';
import { api, apiUpload } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, S, R } from '@/src/theme';
import { tap } from '@/src/ui/glass';
import { speak as jarvisSpeak } from '@/src/voice';
import { inviteFamilyToRecord } from '@/src/invite';

const RECORD_LEN_MS = 5000;

export default function VoiceSignature() {
  const router = useRouter();
  const { user } = useAuth();
  const [sig, setSig] = useState<any>(null);
  const [label, setLabel] = useState('');
  const [recording, setRecording] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [okMsg, setOkMsg] = useState('');
  const [micBlocked, setMicBlocked] = useState(false);
  const [circle, setCircle] = useState<{ members: any[]; recorded: number; total: number } | null>(null);
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const cdRef = useRef<any>(null);
  const pulse = useSharedValue(0);

  const load = useCallback(async () => {
    try {
      const [r, c]: any = await Promise.all([
        api('/family/voice-signature'),
        api('/family/voice-signature/circle'),
      ]);
      setSig(r && r.sig_id ? r : null);
      setLabel((r && r.label) || (user?.name || '').split(' ')[0] || '');
      setCircle(c);
    } catch (e) { console.log(e); }
  }, [user?.name]);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (recording) {
      pulse.value = withRepeat(withTiming(1, { duration: 800, easing: Easing.inOut(Easing.sin) }), -1, true);
    } else {
      cancelAnimation(pulse);
      pulse.value = 0;
    }
  }, [recording, pulse]);
  const pulseStyle = useAnimatedStyle(() => ({
    transform: [{ scale: 1 + pulse.value * 0.12 }],
    opacity: 0.55 + pulse.value * 0.45,
  }));

  const start = async () => {
    setErr(''); setOkMsg('');
    if (!label.trim()) { setErr('Write your name or your relationship (e.g. Guardian).'); return; }
    if (Platform.OS === 'web') { setErr('Voice-print recording works in the native app (Expo Go / build).'); return; }
    try {
      let perm = await AudioModule.getRecordingPermissionsAsync();
      if (!perm.granted) {
        if (perm.canAskAgain === false) { setMicBlocked(true); return; }
        perm = await AudioModule.requestRecordingPermissionsAsync();
        if (!perm.granted) { setMicBlocked(perm.canAskAgain === false); return; }
      }
      setMicBlocked(false);
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true } as any);
      await recorder.prepareToRecordAsync();
      recorder.record();
      setRecording(true);
      setCountdown(5);
      tap('medium');
      cdRef.current = setInterval(() => setCountdown((c) => Math.max(0, c - 1)), 1000);
      setTimeout(() => { stop(); }, RECORD_LEN_MS);
    } catch (e: any) { setErr(String(e?.message || e)); }
  };

  const stop = async () => {
    if (cdRef.current) { clearInterval(cdRef.current); cdRef.current = null; }
    setRecording(false); setCountdown(0);
    try {
      await recorder.stop();
      const uri = recorder.uri;
      if (!uri) return;
      setBusy(true);
      await apiUpload('/family/voice-signature', uri, uri.endsWith('.m4a') ? 'voice-print.m4a' : 'voice-print.webm',
        uri.endsWith('.m4a') ? 'audio/m4a' : 'audio/webm', { label: label.trim() });
      tap('success');
      setOkMsg(`Voice signature "${label.trim()}" saved. Grandma will see and hear who is writing to her.`);
      await load();
      // Confirm audibly
      jarvisSpeak(`Thank you, ${label.trim()}. Your voice signature is recorded.`,
        { voice: 'onyx', speed: 0.95, language: (user?.language as any) || 'en' });
    } catch (e: any) { setErr(String(e?.message || e)); }
    setBusy(false);
  };

  const remove = async () => {
    setBusy(true); setErr(''); setOkMsg('');
    try { await api('/family/voice-signature', { method: 'DELETE' }); await load(); setOkMsg('Voice signature removed.'); }
    catch (e: any) { setErr(String(e?.message || e)); }
    setBusy(false);
  };

  return (
    <SafeAreaView testID="voice-signature-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="vs-back" onPress={() => { tap(); router.back(); }} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>VOICE SIGNATURE</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 80 }} showsVerticalScrollIndicator={false}>
        <Text style={styles.intro}>
          Record your voice for 5 seconds. When you then send grandma a message, Jarvis announces:
          <Text style={{ color: C.brand, fontWeight: '900' }}> You have a new message from {label.trim() || 'you'}.</Text>
        </Text>

        <Text style={styles.lbl}>THE NAME JARVIS WILL USE</Text>
        <TextInput
          testID="vs-label"
          value={label}
          onChangeText={setLabel}
          style={styles.input}
          placeholder="e.g. Guardian"
          placeholderTextColor="#999"
          maxLength={40}
        />

        <View style={styles.recRing}>
          <Animated.View style={[styles.recGlow, pulseStyle]} />
          <Pressable
            testID="vs-record"
            onPress={recording ? stop : start}
            disabled={busy}
            style={[styles.recBtn, recording && styles.recBtnActive]}
          >
            {busy ? <ActivityIndicator color={C.onInverse} size="large" /> : (
              <Ionicons name={recording ? 'stop' : 'mic'} size={54} color={recording ? C.onError : C.onInverse} />
            )}
          </Pressable>
        </View>

        {recording && (
          <Text testID="vs-countdown" style={styles.countdown}>{countdown} s · hovorte prirodzene…</Text>
        )}

        {!!sig && !recording && (
          <View testID="vs-existing" style={styles.existing}>
            <Ionicons name="checkmark-circle" size={22} color={C.brand} />
            <View style={{ flex: 1 }}>
              <Text style={styles.existingLbl}>YOU HAVE A SAVED VOICE SIGNATURE</Text>
              <Text style={styles.existingText}>„{sig.label}“ · {Math.round((sig.size || 0) / 1024)} KB</Text>
            </View>
            <Pressable testID="vs-delete" onPress={remove} disabled={busy} hitSlop={10}>
              <Ionicons name="trash-outline" size={20} color={C.error} />
            </Pressable>
          </View>
        )}

        {!!okMsg && <Text testID="vs-ok" style={styles.ok}>{okMsg}</Text>}
        {!!err && <Text testID="vs-err" style={styles.err}>{err}</Text>}

        {micBlocked && (
          <Pressable onPress={() => Linking.openSettings()} style={styles.settingsBtn}>
            <Ionicons name="settings-outline" size={14} color={C.brand} />
            <Text style={styles.settingsText}>Microphone is blocked — OPEN SETTINGS</Text>
          </Pressable>
        )}

        {/* FAMILY VOICE CIRCLE — every family member's voice-print status */}
        {circle && circle.total > 1 && (
          <View testID="vs-circle" style={styles.circleWrap}>
            <View style={styles.circleHdr}>
              <Ionicons name="people-circle" size={22} color={C.brand} />
              <Text style={styles.circleTitle}>FAMILY VOICE CIRCLE</Text>
              <View style={styles.circleCount}>
                <Text style={styles.circleCountText}>{circle.recorded} / {circle.total}</Text>
              </View>
            </View>
            <Text style={styles.circleSub}>
              Every family member records their own voice — Jarvis tells grandma who each message is from.
            </Text>
            {circle.members.map((m) => (
              <View key={m.user_id} testID={`vs-circle-${m.user_id}`} style={styles.memberRow}>
                <View style={[styles.memberAvatar, m.has_signature && styles.memberAvatarDone]}>
                  <Ionicons name={m.has_signature ? 'mic-circle' : 'mic-off'} size={20} color={m.has_signature ? C.onInverse : C.info} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.memberName}>{m.name} {m.is_self && <Text style={styles.memberYou}>· TO STE VY</Text>}</Text>
                  <Text style={styles.memberStatus}>
                    {m.has_signature
                      ? `"${m.label}" · recorded`
                      : m.is_self ? 'Record above ↑' : 'has not recorded a voice yet'}
                  </Text>
                </View>
                {m.has_signature ? (
                  <Ionicons name="checkmark-circle" size={22} color={C.brand} />
                ) : m.is_self ? (
                  <Ionicons name="time-outline" size={22} color={C.info} />
                ) : (
                  <Pressable
                    testID={`vs-invite-${m.user_id}`}
                    onPress={() => { tap(); inviteFamilyToRecord(m.name); }}
                    style={styles.inviteBtn}
                    hitSlop={8}
                  >
                    <Ionicons name="paper-plane-outline" size={14} color={C.brand} />
                    <Text style={styles.inviteBtnText}>INVITE</Text>
                  </Pressable>
                )}
              </View>
            ))}
            {/* Bulk invite — one tap opens native share sheet with a generic Slovak message */}
            <Pressable
              testID="vs-invite-any"
              onPress={() => { tap(); inviteFamilyToRecord(); }}
              style={styles.inviteBulk}
            >
              <Ionicons name="share-social-outline" size={16} color={C.onInverse} />
              <Text style={styles.inviteBulkText}>INVITE ANOTHER FAMILY MEMBER</Text>
            </Pressable>
          </View>
        )}

        <Text style={styles.hint}>
          The recording is not sent to anyone — it only helps your family recognize you in messages.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.brand, fontWeight: '900', fontSize: 15, letterSpacing: 2.5 },
  body: { padding: S.xl, gap: S.md, flex: 1 },
  intro: { color: C.fg, fontSize: 14, lineHeight: 20 },
  lbl: { fontSize: 10, letterSpacing: 2, color: C.onS3, fontWeight: '900', marginTop: S.md },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.sm, padding: S.md, fontSize: 15, color: C.fg, backgroundColor: C.surface2 },
  recRing: { alignSelf: 'center', width: 200, height: 200, alignItems: 'center', justifyContent: 'center', marginTop: S.xl },
  recGlow: { position: 'absolute', width: 200, height: 200, borderRadius: 100, backgroundColor: 'rgba(212,175,55,0.28)' },
  recBtn: { width: 150, height: 150, borderRadius: 75, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center', borderWidth: 3, borderColor: C.brandSec },
  recBtnActive: { backgroundColor: C.error, borderColor: C.error },
  countdown: { color: C.brand, fontSize: 18, fontWeight: '900', letterSpacing: 1, textAlign: 'center', marginTop: S.md },
  existing: { flexDirection: 'row', gap: S.md, alignItems: 'center', borderWidth: 1.5, borderColor: C.brand, borderRadius: R.md, padding: S.md, backgroundColor: 'rgba(212,175,55,0.06)', marginTop: S.lg },
  existingLbl: { color: C.brand, fontSize: 10, fontWeight: '900', letterSpacing: 1.5 },
  existingText: { color: C.fg, fontSize: 13, marginTop: 2 },
  ok: { color: C.brand, fontSize: 13, fontWeight: '700', marginTop: S.md },
  err: { color: C.error, fontSize: 12, marginTop: S.md },
  settingsBtn: { flexDirection: 'row', gap: 6, alignItems: 'center', justifyContent: 'center', marginTop: S.md, minHeight: 44, paddingHorizontal: S.md, borderWidth: 1, borderColor: C.brand, borderRadius: R.pill },
  settingsText: { color: C.brand, fontWeight: '800', fontSize: 11 },
  hint: { color: C.info, fontSize: 11, lineHeight: 16, marginTop: S.xl, textAlign: 'center' },
  circleWrap: { marginTop: S.xl, borderWidth: 1, borderColor: C.border, borderRadius: R.md, backgroundColor: C.surface2, padding: S.md, gap: S.sm },
  circleHdr: { flexDirection: 'row', alignItems: 'center', gap: S.sm },
  circleTitle: { flex: 1, color: C.brand, fontWeight: '900', fontSize: 12, letterSpacing: 2 },
  circleCount: { backgroundColor: C.brand, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  circleCountText: { color: C.onInverse, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  circleSub: { color: C.info, fontSize: 11, lineHeight: 16, marginBottom: S.sm },
  memberRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, paddingVertical: S.sm, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: C.border },
  memberAvatar: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: C.surface3, borderWidth: 1, borderColor: C.borderStrong },
  memberAvatarDone: { backgroundColor: C.brand, borderColor: C.brand },
  memberName: { color: C.fg, fontWeight: '800', fontSize: 13 },
  memberYou: { color: C.brand, fontWeight: '900', fontSize: 9, letterSpacing: 1 },
  memberStatus: { color: C.onS3, fontSize: 11, marginTop: 2 },
  inviteBtn: { flexDirection: 'row', gap: 4, alignItems: 'center', paddingHorizontal: 10, minHeight: 34, borderRadius: 17, borderWidth: 1.5, borderColor: C.brand, backgroundColor: 'rgba(212,175,55,0.06)' },
  inviteBtnText: { color: C.brand, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  inviteBulk: { flexDirection: 'row', gap: 6, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, borderRadius: R.pill, minHeight: 48, marginTop: S.md },
  inviteBulkText: { color: C.onInverse, fontWeight: '900', fontSize: 12, letterSpacing: 1.5 },
});
