/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// VOICE ECHOES — rodinný hlasový prúd pre seniorov. Jeden ťuk = Jarvis prečíta odkaz nahlas.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, Pressable, StyleSheet, ScrollView, Modal, TextInput, ActivityIndicator, Platform, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { createAudioPlayer, setAudioModeAsync, useAudioRecorder, RecordingPresets, AudioModule } from 'expo-audio';
import { api, apiUpload } from '@/src/api';
import { cachedAudioUri } from '@/src/media';
import { useAuth } from '@/src/auth';
import { C, S, R } from '@/src/theme';
import { tap } from '@/src/ui/glass';
import { speak as jarvisSpeak } from '@/src/voice';
import { useI18n } from '@/src/i18n-context';

const PRESETS = [
  'We love you, Grandma! Thinking of you. ❤️',
  'Grandpa, we are coming for lunch on Sunday!',
  'Do not forget your meds at eight. Kisses!',
  'The grandkids say hi and cannot wait to see you!',
];

export default function VoiceEchoes() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const { user } = useAuth();
  const [echoes, setEchoes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [playing, setPlaying] = useState<string | null>(null);
  const [add, setAdd] = useState(false);
  const [fromName, setFromName] = useState('');
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const [recipients, setRecipients] = useState<any[]>([]);
  const [target, setTarget] = useState<any>(null); // null = this device (self)
  const [sentMsg, setSentMsg] = useState('');
  const [recording, setRecording] = useState(false);
  const [micBlocked, setMicBlocked] = useState(false);
  const playerRef = useRef<any>(null);
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);

  const load = useCallback(async () => {
    try { const r: any = await api('/family/echoes'); setEchoes(r.echoes || []); } catch (e) { console.log(e); }
    try { const rc: any = await api('/family/echoes/recipients'); setRecipients(rc.recipients || []); } catch {}
    setLoading(false);
  }, []);
  useEffect(() => {
    load();
    return () => { try { playerRef.current?.remove?.(); } catch {} };
  }, [load]);

  const play = async (e: any) => {
    tap('medium');
    setPlaying(e.echo_id);
    try {
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false } as any);
      // SENTIENT ANNOUNCEMENT — Jarvis (Onyx) says the sender's name FIRST, so babička
      // knows who is speaking before their real voice starts playing.
      const senderLabel = (e.from_name || 'a family member').trim();
      const langNow = (user?.language as any) || 'en';
      await jarvisSpeak(`You have a new message from ${senderLabel}.`, { voice: 'onyx', speed: 0.95, language: langNow });
      // Small pause so the intro is clearly heard before the real echo starts.
      await new Promise(r => setTimeout(r, 2200));

      let src: { uri: string; headers?: Record<string, string> };
      if (e.audio) {
        // REAL family voice recording — stream the original audio
        src = await cachedAudioUri(`/family/echoes/${e.echo_id}/audio`);
      } else {
        // Text-only echo — Onyx reads it (unified with Jarvis timbre)
        const res: any = await api('/voice/tts', { method: 'POST', body: JSON.stringify({ text: (e.message || '').slice(0, 1000), voice: 'onyx', speed: 0.95, language: langNow }) });
        src = await cachedAudioUri(res.url.replace(/^\/api/, ''));
      }
      try { playerRef.current?.remove?.(); } catch {}
      const p = createAudioPlayer(src.headers ? { uri: src.uri, headers: src.headers } : { uri: src.uri });
      playerRef.current = p; p.play();
      if (!e.heard) {
        await api(`/family/echoes/${e.echo_id}/heard`, { method: 'POST' });
        setEchoes(prev => prev.map(x => x.echo_id === e.echo_id ? { ...x, heard: true } : x));
      }
    } catch (err) { console.log('echo play err', err); }
    setPlaying(null);
  };

  // 🎙 RECORD A REAL VOICE MESSAGE — own voice instead of Jarvis TTS
  const toggleRecord = async () => {
    if (recording) {
      try {
        await recorder.stop();
        setRecording(false);
        const uri = recorder.uri;
        if (!uri) return;
        setBusy(true); setSentMsg('');
        const extra: Record<string, string> = { from_name: fromName.trim() || 'Rodina' };
        if (target) extra.to_email = target.email;
        const r: any = await apiUpload('/family/echoes/audio', uri, 'echo.m4a', 'audio/m4a', extra);
        tap('success');
        setSentMsg(target
          ? `🎙 Voice recording sent remotely — ${r.to} will hear your real voice.`
          : '🎙 Voice recording saved — tap the card to listen.');
        setAdd(false);
        await load();
      } catch (e: any) { setSentMsg(String(e.message || e)); }
      setBusy(false);
      return;
    }
    try {
      let perm = await AudioModule.getRecordingPermissionsAsync();
      if (!perm.granted) {
        if (perm.canAskAgain === false) { setMicBlocked(true); return; }
        perm = await AudioModule.requestRecordingPermissionsAsync();
        if (!perm.granted) { if (perm.canAskAgain === false) setMicBlocked(true); return; }
      }
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: true } as any);
      await recorder.prepareToRecordAsync();
      recorder.record();
      tap('heavy');
      setRecording(true);
    } catch (e) { console.log('rec err', e); }
  };

  const send = async (text?: string) => {
    const message = (text || msg).trim();
    if (!message) return;
    setBusy(true); setSentMsg('');
    try {
      tap('success');
      if (target) {
        // REMOTE FAMILY ACCESS — send from my own account to the senior's device
        const r: any = await api('/family/echoes/send', { method: 'POST', body: JSON.stringify({ to_email: target.email, message }) });
        setSentMsg(`💌 Message sent remotely — ${r.to} will hear it on their device.`);
      } else {
        await api('/family/echoes', { method: 'POST', body: JSON.stringify({ from_name: fromName.trim() || 'Rodina', message }) });
        await load();
      }
      setAdd(false); setMsg('');
    } catch (e: any) { setSentMsg(String(e.message || e)); }
    setBusy(false);
  };

  return (
    <SafeAreaView testID="voice-echoes" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="ve-back" onPress={() => router.back()} hitSlop={10}>
          <Ionicons name="chevron-back" size={28} color={C.fg} />
        </Pressable>
        <Text style={st.title}>{tt('voice_echoes.odkazy_od_rodiny')}</Text>
        <Pressable testID="ve-add" onPress={() => setAdd(true)} hitSlop={10}>
          <Ionicons name="add-circle" size={28} color={C.brand} />
        </Pressable>
      </View>

      {loading ? <ActivityIndicator color={C.brand} style={{ marginTop: 60 }} /> : (
        <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 100, gap: S.md }}>
          <Text style={st.hint}>{tt('voice_echoes.tap_a_card_jarvis_reads_the_message')}</Text>
          {!!sentMsg && <View style={st.sentBox}><Text testID="ve-sent-msg" style={st.sentText}>{sentMsg}</Text></View>}
          {echoes.length === 0 && (
            <View style={st.empty}>
              <Ionicons name="heart" size={44} color={C.brand} />
              <Text style={st.emptyTitle}>{tt('voice_echoes.no_messages_yet')}</Text>
              <Text style={st.emptySub}>{tt('voice_echoes.family_can_send_a_message_via_the_bu')}</Text>
              <Pressable testID="ve-empty-add" onPress={() => setAdd(true)} style={st.emptyBtn}>
                <Text style={st.emptyBtnText}>{tt('voice_echoes.send_the_first_message')}</Text>
              </Pressable>
            </View>
          )}
          {echoes.map(e => (
            <Pressable key={e.echo_id} testID={`echo-${e.echo_id}`} onPress={() => play(e)}
              style={({ pressed }) => [st.card, !e.heard && st.cardNew, pressed && { opacity: 0.85 }]}>
              <View style={st.playCircle}>
                {playing === e.echo_id ? <ActivityIndicator color={C.onInverse} /> : <Ionicons name={e.audio ? 'mic' : 'play'} size={30} color={C.onInverse} />}
              </View>
              <View style={{ flex: 1 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  <Text style={st.from}>{e.from_name}</Text>
                  {!e.heard && <View style={st.newBadge}><Text style={st.newBadgeText}>{tt('voice_echoes.new')}</Text></View>}
                </View>
                <Text style={st.msgText} numberOfLines={3}>{tx(e.message)}</Text>
              </View>
            </Pressable>
          ))}
        </ScrollView>
      )}

      <Modal visible={add} transparent animationType="fade" onRequestClose={() => setAdd(false)}>
        <Pressable style={st.overlay} onPress={() => setAdd(false)}>
          <Pressable style={st.sheet} onPress={() => {}}>
            <View style={st.sheetHandle} />
            <Text style={st.sheetTitle}>{tt('voice_echoes.send_a_voice_message')}</Text>
            {recipients.length > 0 && (<>
              <Text style={st.lbl}>{tt('voice_echoes.to_whom')}</Text>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: S.sm }}>
                <Pressable testID="ve-target-self" onPress={() => { tap(); setTarget(null); }} style={[st.targetChip, !target && st.targetChipOn]}>
                  <Ionicons name="phone-portrait-outline" size={14} color={!target ? C.onInverse : C.fg} />
                  <Text style={[st.targetText, !target && { color: C.onInverse }]}>{tt('voice_echoes.toto_zariadenie')}</Text>
                </Pressable>
                {recipients.map(r => (
                  <Pressable testID={`ve-target-${r.user_id}`} key={r.user_id} onPress={() => { tap(); setTarget(r); }}
                    style={[st.targetChip, target?.user_id === r.user_id && st.targetChipOn]}>
                    <Ionicons name="heart-outline" size={14} color={target?.user_id === r.user_id ? C.onInverse : C.brand} />
                    <Text style={[st.targetText, target?.user_id === r.user_id && { color: C.onInverse }]}>{r.name}</Text>
                  </Pressable>
                ))}
              </View>
              {!!target && <Text style={st.remoteHint}>{tt('voice_echoes.the_message_goes_remotely_to')} {target.name} ({target.email})</Text>}
            </>)}
            {!target && (<>
              <Text style={st.lbl}>{tt('voice_echoes.kto_posiela')}</Text>
              <TextInput testID="ve-from" value={fromName} onChangeText={setFromName} style={st.input} placeholder={tt('voice_echoes.e_g_granddaughter_inner_circle')} placeholderTextColor="#888" />
            </>)}

            {/* 🎙 REAL VOICE RECORDING — own voice instead of Jarvis */}
            <Text style={st.lbl}>{tt('voice_echoes.in_your_own_voice_1_tap')}</Text>
            {Platform.OS === 'web' ? (
              <Text style={st.webNote}>{tt('voice_echoes.own_voice_recording_works_in_the_mob')}</Text>
            ) : (
              <Pressable testID="ve-record" onPress={toggleRecord} disabled={busy}
                style={[st.recBtn, recording && st.recBtnOn]}>
                {busy ? <ActivityIndicator color={recording ? C.onError : C.onInverse} /> : (<>
                  <Ionicons name={recording ? 'stop-circle' : 'mic'} size={26} color={recording ? C.onError : C.onInverse} />
                  <Text style={[st.recText, recording && { color: C.onError }]}>
                    {recording ? tt('voice_echoes.recording_tap_to_send') : tt('voice_echoes.record_in_your_own_voice')}
                  </Text>
                </>)}
              </Pressable>
            )}
            {micBlocked && (
              <Pressable testID="ve-mic-settings" onPress={() => Linking.openSettings()} style={st.micSettings}>
                <Text style={st.micSettingsText}>{tt('voice_echoes.microphone_is_blocked_open_settings')}</Text>
              </Pressable>
            )}

            <Text style={st.lbl}>{tt('voice_echoes.quick_messages_1_tap')}</Text>
            <View style={{ gap: S.sm }}>
              {PRESETS.map((p, i) => (
                <Pressable testID={`ve-preset-${i}`} key={i} onPress={() => send(p)} disabled={busy}
                  style={({ pressed }) => [st.preset, pressed && { backgroundColor: C.surface3 }]}>
                  <Text style={st.presetText}>{p}</Text>
                </Pressable>
              ))}
            </View>
            <Text style={st.lbl}>{tt('voice_echoes.or_your_own_text')}</Text>
            <TextInput testID="ve-msg" value={msg} onChangeText={setMsg} style={[st.input, { minHeight: 60 }]} multiline placeholder={tt('voice_echoes.write_a_message')} placeholderTextColor="#888" />
            <Pressable testID="ve-send" onPress={() => send()} disabled={busy || !msg.trim()} style={[st.sendBtn, !msg.trim() && { opacity: 0.5 }]}>
              {busy ? <ActivityIndicator color={C.onInverse} /> : <Text style={st.sendText}>{tt('voice_echoes.send_message')}</Text>}
            </Pressable>
          </Pressable>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md, borderBottomWidth: 1, borderBottomColor: C.border },
  title: { color: C.fg, fontWeight: '900', fontSize: 16, letterSpacing: 2 },
  hint: { color: C.info, fontSize: 13, textAlign: 'center', marginBottom: S.sm },
  sentBox: { backgroundColor: 'rgba(212,175,55,0.1)', borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.md, padding: S.md },
  sentText: { color: C.brand, fontWeight: '800', fontSize: 12, lineHeight: 17 },
  targetChip: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: S.md, minHeight: 44, borderRadius: R.pill, borderWidth: 1.5, borderColor: C.borderStrong },
  targetChipOn: { backgroundColor: C.brand, borderColor: C.brand },
  targetText: { color: C.fg, fontWeight: '800', fontSize: 12.5 },
  remoteHint: { marginTop: S.sm, color: C.brand, fontSize: 11, fontWeight: '700' },
  recBtn: { flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, borderRadius: R.pill, minHeight: 60 },
  recBtnOn: { backgroundColor: C.error },
  recText: { color: C.onInverse, fontWeight: '900', fontSize: 13, letterSpacing: 1 },
  webNote: { color: C.info, fontSize: 11.5, lineHeight: 16, borderWidth: 1, borderColor: C.border, borderRadius: R.md, padding: S.md },
  micSettings: { marginTop: S.sm, minHeight: 46, alignItems: 'center', justifyContent: 'center', borderRadius: R.md, backgroundColor: C.warn },
  micSettingsText: { color: C.onWarn, fontWeight: '900', fontSize: 11 },
  empty: { alignItems: 'center', padding: S.xl, gap: S.sm, backgroundColor: C.surface2, borderRadius: R.lg, borderWidth: 1, borderColor: C.border },
  emptyTitle: { color: C.fg, fontWeight: '900', fontSize: 18 },
  emptySub: { color: C.onS3, fontSize: 13, textAlign: 'center', lineHeight: 19 },
  emptyBtn: { marginTop: S.sm, backgroundColor: C.brand, borderRadius: R.pill, paddingHorizontal: S.xl, minHeight: 50, alignItems: 'center', justifyContent: 'center' },
  emptyBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 13 },
  card: { flexDirection: 'row', alignItems: 'center', gap: S.lg, backgroundColor: C.surface2, borderRadius: R.lg, padding: S.lg, minHeight: 96, borderWidth: 1.5, borderColor: C.border },
  cardNew: { borderColor: C.brand, backgroundColor: 'rgba(212,175,55,0.08)' },
  playCircle: { width: 64, height: 64, borderRadius: 32, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center' },
  from: { color: C.fg, fontWeight: '900', fontSize: 17 },
  newBadge: { backgroundColor: C.brand, borderRadius: R.pill, paddingHorizontal: 8, paddingVertical: 2 },
  newBadgeText: { color: C.onInverse, fontWeight: '900', fontSize: 9, letterSpacing: 1 },
  msgText: { color: C.onS3, fontSize: 14, lineHeight: 20, marginTop: 4 },
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.72)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: C.surface2, borderTopLeftRadius: R.lg, borderTopRightRadius: R.lg, padding: S.xl, paddingBottom: 34, borderWidth: 1, borderColor: C.borderStrong },
  sheetHandle: { alignSelf: 'center', width: 44, height: 5, borderRadius: 3, backgroundColor: C.surface3, marginBottom: S.md },
  sheetTitle: { color: C.fg, fontWeight: '900', fontSize: 20 },
  lbl: { marginTop: S.lg, marginBottom: 6, color: C.info, fontWeight: '900', fontSize: 10, letterSpacing: 2 },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.md, padding: S.md, fontSize: 15, color: C.fg, backgroundColor: C.bg },
  preset: { borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.md, padding: S.md, minHeight: 50, justifyContent: 'center' },
  presetText: { color: C.fg, fontWeight: '700', fontSize: 14 },
  sendBtn: { marginTop: S.lg, backgroundColor: C.brand, borderRadius: R.pill, alignItems: 'center', justifyContent: 'center', minHeight: 54 },
  sendText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 14 },
});
