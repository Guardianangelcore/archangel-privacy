/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// GUARDIAN LENS — one tap: photograph any medical artefact → AI identifies → instant workflow
import React, { useRef, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, Image, Platform, Linking, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { createAudioPlayer, setAudioModeAsync } from 'expo-audio';
import { api, apiUpload } from '@/src/api';
import { cachedAudioUri } from '@/src/media';
import { useAuth } from '@/src/auth';
import { C, S, R } from '@/src/theme';
import { GlassCard, GoldButton, Pulse, tap } from '@/src/ui/glass';
import { useI18n } from '@/src/i18n-context';

const KIND_LABEL: Record<string, string> = {
  medication: '💊 MEDICATION', medical_report: '📄 MEDICAL REPORT', prescription: '📝 PRESCRIPTION',
  lab_results: '🧪 LAB RESULTS', other: '❔ OTHER ARTIFACT',
};

export default function Lens() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const { user } = useAuth();
  const [photo, setPhoto] = useState<{ uri: string; name: string; type: string } | null>(null);
  const [scan, setScan] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [camBlocked, setCamBlocked] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [modelKey, setModelKey] = useState<'gpt' | 'claude' | 'gemini' | 'consensus'>('gpt');
  const [jarvisReply, setJarvisReply] = useState('');
  const playerRef = useRef<any>(null);

  const MODEL_CHIPS = [
    { key: 'gpt', label: 'GPT-5.4', icon: 'flash' },
    { key: 'gemini', label: 'GEMINI 3.1', icon: 'sparkles' },
    { key: 'claude', label: 'CLAUDE 5', icon: 'shield-checkmark' },
    { key: 'consensus', label: 'KONSENZUS ×3', icon: 'infinite' },
  ] as const;

  // MAGIC LENS — Jarvis reads the label aloud (high-fidelity TTS for seniors)
  const speak = async (result: any) => {
    const text = `${result.name}. ${result.summary_sk || ''} ${(result.warnings || []).join('. ')}`.trim();
    if (!text) return;
    setSpeaking(true);
    try {
      const res: any = await api('/voice/tts', { method: 'POST', body: JSON.stringify({ text: text.slice(0, 1500), voice: 'nova', speed: 0.92, language: user?.language || 'en' }) });
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false } as any);
      const src = await cachedAudioUri(res.url.replace(/^\/api/, ''));
      try { playerRef.current?.remove?.(); } catch {}
      const p = createAudioPlayer(src.headers ? { uri: src.uri, headers: src.headers } : { uri: src.uri });
      playerRef.current = p; p.play();
    } catch (e) { console.log('lens tts err', e); }
    setSpeaking(false);
  };

  const takePhoto = async () => {
    setErr(''); setScan(null); tap('medium');
    try {
      if (Platform.OS !== 'web') {
        const p = await ImagePicker.getCameraPermissionsAsync();
        if (!p.granted) {
          if (!p.canAskAgain) { setCamBlocked(true); return; }
          const r = await ImagePicker.requestCameraPermissionsAsync();
          if (!r.granted) { if (!r.canAskAgain) setCamBlocked(true); return; }
        }
      }
      const res = await ImagePicker.launchCameraAsync({ quality: 0.7, allowsEditing: false });
      if (!res.canceled && res.assets?.length) {
        const a = res.assets[0];
        setPhoto({ uri: a.uri, name: a.fileName || 'scan.jpg', type: a.mimeType || 'image/jpeg' });
      }
    } catch (e: any) { setErr(String(e.message || e)); }
  };

  const pickPhoto = async () => {
    setErr(''); setScan(null); tap();
    try {
      const res = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.7 });
      if (!res.canceled && res.assets?.length) {
        const a = res.assets[0];
        setPhoto({ uri: a.uri, name: a.fileName || 'scan.jpg', type: a.mimeType || 'image/jpeg' });
      }
    } catch (e: any) { setErr(String(e.message || e)); }
  };

  const analyze = async () => {
    if (!photo) return;
    setBusy('analyze'); setErr(''); setMsg(''); setJarvisReply('');
    try {
      const endpoint = modelKey === 'consensus' ? '/lens/analyze-consensus' : '/lens/analyze';
      const extra: Record<string, string> = modelKey === 'consensus' ? {} : { model: modelKey };
      const r: any = await apiUpload(endpoint, photo.uri, photo.name, photo.type, extra);
      setScan(r);
      tap('success');
      speak(r); // Magic Lens: automatically read the result aloud
    } catch (e: any) { setErr(String(e.message || e)); tap('error'); }
    finally { setBusy(null); }
  };

  const askJarvis = async () => {
    if (!scan?.scan_id) return;
    setBusy('jarvis'); setMsg('');
    try {
      const r: any = await api(`/lens/${scan.scan_id}/to-jarvis`, { method: 'POST' });
      setJarvisReply(r?.jarvis?.reply || '');
      setMsg('🤖 Jarvis analyzed the scan and replied below.');
      tap('success');
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const addMed = async () => {
    setBusy('med'); setMsg('');
    try {
      await api('/meds/reminders', { method: 'POST', body: JSON.stringify({ name: scan.name, dose: '', times: ['08:00'], slots: ['breakfast'] }) });
      setMsg('💊 Medication added to the calendar (With breakfast · 08:00). Adjust slots in Meds.');
      tap('success');
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const saveVault = async () => {
    setBusy('vault'); setMsg('');
    try {
      await api(`/lens/${scan.scan_id}/save-to-vault`, { method: 'POST' });
      setMsg('🔐 Photo saved to your Health Vault (SHA-256 seal).');
      tap('success');
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const has = (a: string) => (scan?.suggested_actions || []).includes(a);

  return (
    <SafeAreaView testID="lens-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="ln-back" onPress={() => { tap(); router.back(); }} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.fg} />
        </Pressable>
        <Text style={st.title}>{tt('lens.guardian_lens')}</Text>
        <View style={{ width: 26 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        <Text style={st.tag}>{tt('lens.snap_know_act_with_one_tap')}</Text>

        <GlassCard glow pad={S.lg} style={{ marginTop: S.md }}>
          {photo ? (
            <Image source={{ uri: photo.uri }} style={st.preview} resizeMode="cover" />
          ) : (
            <View style={st.placeholder}>
              <Pulse><Ionicons name="scan-circle-outline" size={72} color={C.brand} /></Pulse>
              <Text style={st.placeholderText}>{tt('lens.photograph_a_medicine_box_prescripti')}{'\n'}{tt('lens.jarvis_instantly_recognizes_the_cont')}</Text>
            </View>
          )}
          <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.md }}>
            {Platform.OS !== 'web' && (
              <Pressable testID="ln-camera" onPress={takePhoto} style={st.srcBtn}>
                <Ionicons name="camera" size={20} color={C.brand} />
                <Text style={st.srcText}>{tt('lens.take_photo')}</Text>
              </Pressable>
            )}
            <Pressable testID="ln-gallery" onPress={pickPhoto} style={st.srcBtn}>
              <Ionicons name="images-outline" size={20} color={C.brand} />
              <Text style={st.srcText}>{tt('lens.from_gallery')}</Text>
            </Pressable>
          </View>
          {camBlocked && (
            <Pressable testID="ln-settings" onPress={() => Linking.openSettings()} style={st.permBtn}>
              <Text style={st.permText}>{tt('lens.camera_is_blocked_open_settings')}</Text>
            </Pressable>
          )}
          <Text style={st.modelLbl}>{tt('lens.vision_model')}</Text>
          <View style={st.modelRow}>
            {MODEL_CHIPS.map(m => (
              <Pressable key={m.key} testID={`ln-model-${m.key}`}
                onPress={() => { tap('light'); setModelKey(m.key as any); }}
                style={[st.modelChip, modelKey === m.key && st.modelChipActive]}>
                <Ionicons name={m.icon as any} size={13} color={modelKey === m.key ? C.onInverse : C.brand} />
                <Text style={[st.modelChipText, modelKey === m.key && { color: C.onInverse }]}>{tx(m.label)}</Text>
              </Pressable>
            ))}
          </View>
          <GoldButton testID="ln-analyze" title={tt('lens.analyze_with_lens')} icon="aperture"
            onPress={analyze} disabled={!photo} loading={busy === 'analyze'} style={{ marginTop: S.md }} />
        </GlassCard>

        {busy === 'analyze' && (
          <View style={st.scanning}>
            <ActivityIndicator color={C.brand} />
            <Text style={st.scanningText}>{tt('lens.jarvis_is_reading_the_artifact')}</Text>
          </View>
        )}
        {!!err && <Text testID="ln-err" style={st.err}>{err}</Text>}

        {scan && (
          <GlassCard pad={S.lg} style={{ marginTop: S.lg }} testID="ln-result">
            <View style={st.kindBadge}><Text style={st.kindText}>{KIND_LABEL[scan.kind] || KIND_LABEL.other}</Text></View>
            {!!scan.consensus && (
              <View style={st.consensusBadge}>
                <Ionicons name="infinite" size={12} color={C.info} />
                <Text style={st.consensusText}>{tt('lens.konsenzus_3_modelov_zhoda')} {scan.consensus.agreement_pct}%</Text>
              </View>
            )}
            {!!scan.model && !scan.consensus && (
              <Text style={st.modelUsed}>{String(scan.model).toUpperCase()}</Text>
            )}
            <Text style={st.name}>{scan.name}</Text>
            <Text style={st.summary}>{scan.summary_sk}</Text>
            {(scan.warnings || []).map((w: string, i: number) => (
              <View key={i} style={st.warnRow}>
                <Ionicons name="warning-outline" size={16} color={C.warn} />
                <Text style={st.warnText}>{w}</Text>
              </View>
            ))}
            <Text style={st.aiNote}>{tt('lens.ai_output_informational_only_eu_ai_a')}</Text>

            <Text style={st.actLbl}>{tt('lens.instant_actions')}</Text>
            <View style={st.actGrid}>
              <ActionBtn testID="ln-act-jarvis" icon="chatbubble-ellipses" label={tt('lens.send_to_jarvis')} busy={busy === 'jarvis'} onPress={askJarvis} />
              <ActionBtn testID="ln-act-speak" icon="volume-high" label={tt('lens.read_aloud')} busy={speaking} onPress={() => speak(scan)} />
              {(['medical_report', 'prescription', 'lab_results'].includes(scan.kind) || !!scan.specialty) && (
                <ActionBtn testID="ln-act-healing" icon="sync" label={tt('lens.start_healing_loop')}
                  onPress={() => router.push(`/healing?specialty=${encodeURIComponent(scan.specialty || '')}&auto=1` as any)} />
              )}
              {has('add_med_reminder') && (
                <ActionBtn testID="ln-act-med" icon="alarm" label={tt('lens.add_to_med_calendar')} busy={busy === 'med'} onPress={addMed} />
              )}
              {has('check_interactions') && (
                <ActionBtn testID="ln-act-inter" icon="git-compare" label={tt('lens.interaction_guard')} onPress={() => router.push('/medicine-cabinet')} />
              )}
              {(has('book_specialist') || !!scan.specialty) && (
                <ActionBtn testID="ln-act-book" icon="calendar" label={tt('lens.appointment', [scan.specialty ? `: ${scan.specialty.toUpperCase()}` : ''])} onPress={() => router.push('/(tabs)/waitlist')} />
              )}
              {has('translate') && (
                <ActionBtn testID="ln-act-translate" icon="language" label={tt('lens.ai_translator')} onPress={() => router.push('/translate')} />
              )}
              <ActionBtn testID="ln-act-vault" icon="lock-closed" label={tt('lens.save_to_vault')} busy={busy === 'vault'} onPress={saveVault} />
            </View>
            {!!msg && <Text testID="ln-msg" style={st.msg}>{msg}</Text>}
            {!!jarvisReply && (
              <View testID="ln-jarvis-reply" style={st.jarvisBox}>
                <View style={st.jarvisHead}>
                  <Ionicons name="sparkles" size={14} color={C.brand} />
                  <Text style={st.jarvisTitle}>{tt('lens.jarvis_replies')}</Text>
                </View>
                <Text style={st.jarvisText}>{jarvisReply}</Text>
                <Pressable testID="ln-jarvis-open" onPress={() => router.push('/jarvis')} style={st.jarvisMore}>
                  <Text style={st.jarvisMoreText}>{tt('lens.open_conversation')}</Text>
                </Pressable>
              </View>
            )}
          </GlassCard>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function ActionBtn({ testID, icon, label, onPress, busy }: any) {
  return (
    <Pressable testID={testID} onPress={() => { tap('light'); onPress(); }} disabled={busy}
      style={({ pressed }) => [st.actBtn, pressed && { backgroundColor: 'rgba(212,175,55,0.18)' }]}>
      {busy ? <ActivityIndicator size="small" color={C.brand} /> : <Ionicons name={icon} size={20} color={C.brand} />}
      <Text style={st.actText}>{label}</Text>
    </Pressable>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.brand, fontSize: 18, fontWeight: '900', letterSpacing: 3 },
  tag: { color: C.info, fontSize: 11, letterSpacing: 1.5, fontWeight: '800', textAlign: 'center' },
  preview: { width: '100%', height: 240, borderRadius: R.sm },
  placeholder: { alignItems: 'center', paddingVertical: S.xl, gap: S.md },
  placeholderText: { color: C.onS3, fontSize: 12.5, lineHeight: 19, textAlign: 'center' },
  srcBtn: { flex: 1, flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', minHeight: 52, borderRadius: R.pill, borderWidth: 1.5, borderColor: C.borderStrong, backgroundColor: 'rgba(212,175,55,0.06)' },
  srcText: { color: C.brand, fontWeight: '900', fontSize: 12, letterSpacing: 1 },
  permBtn: { marginTop: S.md, minHeight: 48, alignItems: 'center', justifyContent: 'center', borderRadius: R.sm, backgroundColor: C.warn },
  permText: { color: C.onWarn, fontWeight: '900', fontSize: 11, letterSpacing: 0.5 },
  scanning: { flexDirection: 'row', gap: S.md, alignItems: 'center', justifyContent: 'center', marginTop: S.lg },
  scanningText: { color: C.brand, fontWeight: '800', fontSize: 13, letterSpacing: 1 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginTop: S.md, textAlign: 'center' },
  kindBadge: { alignSelf: 'flex-start', backgroundColor: 'rgba(212,175,55,0.14)', borderRadius: R.pill, paddingHorizontal: S.md, paddingVertical: 6 },
  kindText: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  name: { color: C.fg, fontSize: 22, fontWeight: '900', marginTop: S.md },
  summary: { color: C.onS3, fontSize: 14.5, lineHeight: 22, marginTop: S.sm },
  warnRow: { flexDirection: 'row', gap: S.sm, alignItems: 'flex-start', marginTop: S.sm },
  warnText: { color: C.warn, fontSize: 12.5, lineHeight: 18, flex: 1, fontWeight: '600' },
  aiNote: { color: C.info, fontSize: 9.5, marginTop: S.md, letterSpacing: 0.3 },
  actLbl: { color: C.info, fontSize: 10, fontWeight: '900', letterSpacing: 2, marginTop: S.lg },
  actGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: S.sm, marginTop: S.sm },
  actBtn: { flexDirection: 'row', gap: S.sm, alignItems: 'center', minHeight: 52, paddingHorizontal: S.md, borderRadius: R.pill, borderWidth: 1.5, borderColor: C.borderStrong, flexGrow: 1, justifyContent: 'center' },
  actText: { color: C.fg, fontWeight: '800', fontSize: 11, letterSpacing: 0.5 },
  msg: { color: C.brand, fontWeight: '800', fontSize: 12.5, marginTop: S.md, lineHeight: 18 },
  modelLbl: { color: C.info, fontSize: 9.5, letterSpacing: 2, fontWeight: '900', marginTop: S.md },
  modelRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 6 },
  modelChip: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 8, borderRadius: R.pill, borderWidth: 1.2, borderColor: C.borderStrong, backgroundColor: 'rgba(212,175,55,0.05)' },
  modelChipActive: { backgroundColor: C.brand, borderColor: C.brand },
  modelChipText: { color: C.brand, fontSize: 10, fontWeight: '900', letterSpacing: 0.5 },
  modelUsed: { color: C.info, fontSize: 9, letterSpacing: 1, fontWeight: '800', marginTop: 4 },
  consensusBadge: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 6, alignSelf: 'flex-start', backgroundColor: 'rgba(90,140,220,0.12)', borderRadius: R.pill, paddingHorizontal: 10, paddingVertical: 4 },
  consensusText: { color: C.info, fontSize: 9.5, fontWeight: '900', letterSpacing: 1 },
  jarvisBox: { marginTop: S.lg, padding: S.md, borderRadius: R.sm, backgroundColor: 'rgba(212,175,55,0.06)', borderWidth: 1, borderColor: C.borderStrong },
  jarvisHead: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6 },
  jarvisTitle: { color: C.brand, fontSize: 10, fontWeight: '900', letterSpacing: 2 },
  jarvisText: { color: C.fg, fontSize: 13.5, lineHeight: 20 },
  jarvisMore: { marginTop: 8, alignSelf: 'flex-end' },
  jarvisMoreText: { color: C.brand, fontSize: 10.5, fontWeight: '900', letterSpacing: 1.2 },
});
