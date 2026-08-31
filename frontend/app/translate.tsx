/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// AI PREKLADAČ (Jarvis) — odfoťte / nahrajte dokument alebo vložte text →
// AI OCR (gpt-5.4) → ľudské vysvetlenie v slovenčine → extrakcia najbližšieho
// termínu → jedno ťuknutie „Pridať do kalendára“. Dokument sa uloží do Trezora
// a okamžite sa zapíše do Zdravotnej časovej osi.
import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, TextInput, Pressable, ScrollView, ActivityIndicator, Platform, KeyboardAvoidingView, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';
import { createAudioPlayer, setAudioModeAsync } from 'expo-audio';
import { api, apiUpload, API_BASE, getToken } from '@/src/api';
import { useAuth } from '@/src/auth';
import { tap } from '@/src/ui/glass';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';

export default function Translate() {
  const { user } = useAuth();
  const router = useRouter();
  const lang: Lang = (user?.language as Lang) || 'en';
  const [text, setText] = useState('');
  const [out, setOut] = useState('');
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState('');
  const [speaking, setSpeaking] = useState(false);
  const [err, setErr] = useState('');
  const [appt, setAppt] = useState<any>(null);
  const [apptAdded, setApptAdded] = useState(false);
  const [camBlocked, setCamBlocked] = useState(false);
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

  const reset = () => { setErr(''); setOut(''); setAppt(null); setApptAdded(false); };

  // Upload → save to Vault (auto-indexed into Health Timeline) → OCR → plain-language SK
  const processDoc = async (uri: string, name: string, mime: string) => {
    reset(); setBusy(true);
    try {
      setStage('Saving to your Health Vault…');
      const doc: any = await apiUpload('/vault/documents', uri, name, mime, { title: name });
      setStage('Reading the document (AI OCR)…');
      try { await api(`/vault/documents/${doc.doc_id}/ocr`, { method: 'POST' }); } catch {}
      setStage('Translating into plain language…');
      const res: any = await api('/ai/translate-document', { method: 'POST', body: JSON.stringify({ doc_id: doc.doc_id, language: lang }) });
      setOut(res.plain_language);
      setAppt(res.next_appointment || null);
      tap('success');
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(false); setStage(''); }
  };

  const takePhoto = async () => {
    tap('medium');
    try {
      if (Platform.OS !== 'web') {
        const p = await ImagePicker.getCameraPermissionsAsync();
        if (!p.granted) {
          if (!p.canAskAgain) { setCamBlocked(true); return; }
          const r = await ImagePicker.requestCameraPermissionsAsync();
          if (!r.granted) { if (!r.canAskAgain) setCamBlocked(true); return; }
        }
      }
      const res = await ImagePicker.launchCameraAsync({ quality: 0.8, allowsEditing: false });
      if (!res.canceled && res.assets?.length) {
        const a = res.assets[0];
        await processDoc(a.uri, a.fileName || 'lekarska_sprava.jpg', a.mimeType || 'image/jpeg');
      }
    } catch (e: any) { setErr(String(e.message || e)); }
  };

  const pickFile = async () => {
    tap();
    try {
      const res = await DocumentPicker.getDocumentAsync({ type: ['image/*', 'application/pdf'], copyToCacheDirectory: true });
      if (!res.canceled && res.assets?.length) {
        const a = res.assets[0];
        await processDoc(a.uri, a.name, a.mimeType || 'application/octet-stream');
      }
    } catch (e: any) { setErr(String(e.message || e)); }
  };

  const run = async () => {
    if (!text.trim()) return;
    reset(); setBusy(true); setStage('Translating into plain language…');
    try {
      const res: any = await api('/ai/translate', { method: 'POST', body: JSON.stringify({ text, language: lang }) });
      setOut(res.plain_language);
      setAppt(res.next_appointment || null);
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(false); setStage(''); }
  };

  const addToCalendar = async () => {
    if (!appt?.date) return;
    tap('medium');
    try {
      await api('/calendar/events', {
        method: 'POST',
        body: JSON.stringify({
          category: 'exam', title: appt.title || 'Doctor check-up', date: appt.date,
          notes: appt.time ? `Time: ${appt.time}` : 'Found by AI translator',
        }),
      });
      setApptAdded(true); tap('success');
    } catch (e: any) { setErr(String(e.message || e)); }
  };

  return (
    <SafeAreaView testID="translate-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="tr-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={styles.title}>AI TRANSLATOR · JARVIS</Text>
        <View style={{ width: 26 }} />
      </View>

      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 40 }} keyboardShouldPersistTaps="handled">
          {/* UPLOAD HERO — prominent document/photo entry */}
          <View style={styles.uploadCard}>
            <Text style={styles.uploadLbl}>UPLOAD A DOCTOR REPORT</Text>
            <Text style={styles.uploadSub}>Jarvis reads it and explains it in plain language.</Text>
            <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.md }}>
              <Pressable testID="tr-camera" onPress={takePhoto} disabled={busy} style={[styles.upBtn, styles.upBtnPri]}>
                <Ionicons name="camera" size={22} color={C.onInverse} />
                <Text style={styles.upBtnPriText}>PHOTOGRAPH{'\n'}DOCUMENT</Text>
              </Pressable>
              <Pressable testID="tr-upload" onPress={pickFile} disabled={busy} style={[styles.upBtn, styles.upBtnSec]}>
                <Ionicons name="cloud-upload-outline" size={22} color={C.brand} />
                <Text style={styles.upBtnSecText}>UPLOAD FILE{'\n'}/ PHOTO</Text>
              </Pressable>
            </View>
            {camBlocked && (
              <Pressable testID="tr-cam-settings" onPress={() => Linking.openSettings()} style={styles.settingsRow}>
                <Ionicons name="settings-outline" size={14} color={C.brand} />
                <Text style={styles.settingsText}>Camera is blocked — open Settings</Text>
              </Pressable>
            )}
            <Text style={styles.uploadNote}>The document is saved to your Vault and instantly logged in your Health Timeline.</Text>
          </View>

          <Text style={styles.divider}>— OR PASTE TEXT —</Text>

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
            {busy && !stage ? <ActivityIndicator color={C.onInverse} /> : (
              <>
                <Ionicons name="sparkles-outline" size={16} color={C.onInverse} />
                <Text style={styles.runText}>TRANSLATE INTO PLAIN LANGUAGE</Text>
              </>
            )}
          </Pressable>

          {busy && !!stage && (
            <View style={styles.stageRow}>
              <ActivityIndicator color={C.brand} size="small" />
              <Text style={styles.stageText}>{stage}</Text>
            </View>
          )}
          {!!err && <Text style={styles.err}>{err}</Text>}

          {!!out && (
            <View style={styles.outBox}>
              <Text style={styles.outLbl}>HUMAN EXPLANATION</Text>
              <Text style={styles.outText}>{out}</Text>
              <Pressable testID="tr-speak" onPress={speak} disabled={speaking} style={styles.speakBtn}>
                <Ionicons name={speaking ? 'volume-high' : 'volume-medium-outline'} size={18} color={C.brand} />
                <Text style={styles.speakBtnText}>PLAY ALOUD</Text>
              </Pressable>
            </View>
          )}

          {/* NEXT APPOINTMENT — flagged by AI, one tap to calendar */}
          {appt?.date && (
            <View testID="tr-appt" style={styles.apptBox}>
              <Text style={styles.apptLbl}>📅 NEXT APPOINTMENT FOUND</Text>
              <Text style={styles.apptDate}>{appt.date}{appt.time ? ` · ${appt.time}` : ''}</Text>
              <Text style={styles.apptTitle}>{appt.title}</Text>
              {apptAdded ? (
                <>
                  <View style={styles.apptDone}>
                    <Ionicons name="checkmark-circle" size={20} color={C.brand} />
                    <Text style={styles.apptDoneText}>SAVED IN CALENDAR</Text>
                  </View>
                  <Pressable testID="tr-open-timeline" onPress={() => router.push('/health-timeline')} style={styles.timelineLink}>
                    <Ionicons name="time-outline" size={16} color={C.brand} />
                    <Text style={styles.timelineLinkText}>Open Health Timeline</Text>
                  </Pressable>
                </>
              ) : (
                <Pressable testID="tr-add-calendar" onPress={addToCalendar} style={styles.apptBtn}>
                  <Ionicons name="calendar" size={20} color={C.onInverse} />
                  <Text style={styles.apptBtnText}>ADD TO CALENDAR</Text>
                </Pressable>
              )}
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
  uploadCard: { borderWidth: 2, borderColor: C.borderStrong, backgroundColor: 'rgba(212,175,55,0.06)', padding: S.lg },
  uploadLbl: { color: C.brand, fontWeight: '900', fontSize: 13, letterSpacing: 1.5 },
  uploadSub: { color: C.onS3, fontSize: 12, marginTop: 4 },
  upBtn: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 6, minHeight: 88, borderWidth: 2 },
  upBtnPri: { backgroundColor: C.brand, borderColor: C.brand },
  upBtnPriText: { color: C.onInverse, fontWeight: '900', fontSize: 12, letterSpacing: 1, textAlign: 'center' },
  upBtnSec: { backgroundColor: C.bg, borderColor: C.brand },
  upBtnSecText: { color: C.brand, fontWeight: '900', fontSize: 12, letterSpacing: 1, textAlign: 'center' },
  settingsRow: { flexDirection: 'row', gap: 6, alignItems: 'center', marginTop: S.md, minHeight: 44 },
  settingsText: { color: C.brand, fontWeight: '800', fontSize: 11 },
  uploadNote: { color: C.info, fontSize: 10.5, marginTop: S.md, lineHeight: 14 },
  divider: { textAlign: 'center', color: C.info, fontWeight: '800', fontSize: 10, letterSpacing: 2, marginVertical: S.lg },
  input: { minHeight: 140, borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 15, color: C.fg, textAlignVertical: 'top' },
  run: { flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.inverse, paddingVertical: S.lg, marginTop: S.md, minHeight: 54 },
  runText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  stageRow: { flexDirection: 'row', gap: S.sm, alignItems: 'center', marginTop: S.md },
  stageText: { color: C.brand, letterSpacing: 1, fontSize: 12, fontWeight: '800' },
  err: { marginTop: S.md, color: C.error, fontSize: 12, letterSpacing: 1 },
  outBox: { marginTop: S.lg, borderWidth: 2, borderColor: C.borderStrong, padding: S.md, backgroundColor: C.brandTer },
  outLbl: { fontSize: 10, letterSpacing: 2, fontWeight: '900', color: C.brand, marginBottom: S.sm },
  outText: { color: C.fg, fontSize: 16, lineHeight: 24 },
  speakBtn: { marginTop: S.md, flexDirection: 'row', gap: 8, alignItems: 'center', alignSelf: 'flex-start', borderWidth: 1.5, borderColor: C.brand, paddingHorizontal: S.md, paddingVertical: 10, backgroundColor: C.bg },
  speakBtnText: { color: C.brand, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
  apptBox: { marginTop: S.lg, borderWidth: 2, borderColor: C.brand, padding: S.lg, backgroundColor: 'rgba(212,175,55,0.08)' },
  apptLbl: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 2 },
  apptDate: { color: C.fg, fontWeight: '900', fontSize: 24, marginTop: 6 },
  apptTitle: { color: C.onS3, fontSize: 13, marginTop: 2 },
  apptBtn: { marginTop: S.md, flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, minHeight: 58 },
  apptBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 14 },
  apptDone: { marginTop: S.md, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', minHeight: 44 },
  apptDoneText: { color: C.brand, fontWeight: '900', letterSpacing: 2, fontSize: 13 },
  timelineLink: { flexDirection: 'row', gap: 6, alignItems: 'center', justifyContent: 'center', minHeight: 44, borderWidth: 1.5, borderColor: C.brand },
  timelineLinkText: { color: C.brand, fontWeight: '800', fontSize: 12 },
});
