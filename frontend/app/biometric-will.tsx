/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator, Platform, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { useAudioRecorder, RecordingPresets, AudioModule, setAudioModeAsync } from 'expo-audio';
import * as ImagePicker from 'expo-image-picker';
import { api, apiUpload } from '@/src/api';
import { C, S, R } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

export default function BiometricWill() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const [rec, setRec] = useState<any>(null);
  const [recording, setRecording] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [err, setErr] = useState('');
  const [permBlocked, setPermBlocked] = useState(false);

  const load = async () => {
    try { setRec(await api('/legal/testament/biometric')); } catch {}
  };
  useEffect(() => { load(); }, []);

  const startRecording = async () => {
    setErr('');
    try {
      const cur = await AudioModule.getRecordingPermissionsAsync();
      if (!cur.granted) {
        if (!cur.canAskAgain) { setPermBlocked(true); return; }
        const res = await AudioModule.requestRecordingPermissionsAsync();
        if (!res.granted) { if (!res.canAskAgain) setPermBlocked(true); return; }
      }
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true } as any);
      await recorder.prepareToRecordAsync();
      recorder.record();
      setRecording(true);
    } catch (e: any) { setErr(String(e.message || e)); }
  };

  const stopAndUpload = async () => {
    setRecording(false); setUploading(true);
    try {
      await recorder.stop();
      const uri = recorder.uri;
      if (!uri) throw new Error('Recording failed.');
      const saved = await apiUpload('/legal/testament/biometric', uri, 'biometric_statement.m4a', 'audio/mp4');
      setRec(saved);
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setUploading(false); }
  };

  const pickVideo = async () => {
    setErr('');
    try {
      const perm = await ImagePicker.getMediaLibraryPermissionsAsync();
      if (!perm.granted && Platform.OS !== 'web') {
        if (!perm.canAskAgain) { setPermBlocked(true); return; }
        const res = await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (!res.granted) { if (!res.canAskAgain) setPermBlocked(true); return; }
      }
      const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['videos'], quality: 0.7, videoMaxDuration: 60 });
      if (result.canceled || !result.assets?.length) return;
      const a = result.assets[0];
      setUploading(true);
      const saved = await apiUpload('/legal/testament/biometric', a.uri, a.fileName || 'biometric_statement.mp4', a.mimeType || 'video/mp4');
      setRec(saved);
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setUploading(false); }
  };

  const remove = async () => {
    try { await api('/legal/testament/biometric', { method: 'DELETE' }); setRec({}); } catch (e: any) { setErr(String(e.message || e)); }
  };

  const hasProof = !!rec?.sha256;

  return (
    <SafeAreaView testID="biometric-will-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="bw-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>{tt('biometric_will.biometric_will')}</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }}>
        <View style={styles.heroIcon}><Ionicons name="finger-print-outline" size={28} color={C.brand} /></View>
        <Text style={styles.h1}>{tt('biometric_will.biometric_will_confirmation')}</Text>
        <Text style={styles.sub}>
          {tt('biometric_will.record_a_short_voice_or_video_statem')}
        </Text>

        {permBlocked && (
          <View style={styles.permBox}>
            <Text style={styles.permText}>{tt('biometric_will.microphone_gallery_access_is_blocked')}</Text>
            <Pressable testID="bw-settings" onPress={() => Linking.openSettings()} style={styles.permBtn}>
              <Text style={styles.permBtnText}>{tt('biometric_will.open_settings')}</Text>
            </Pressable>
          </View>
        )}
        {!!err && <Text style={styles.err}>{err}</Text>}

        {hasProof ? (
          <View style={styles.proofCard}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.sm }}>
              <Ionicons name="shield-checkmark" size={20} color={C.brand} />
              <Text style={styles.proofTitle}>{tt('biometric_will.statement_notarized')}</Text>
            </View>
            <Proof label={tt('biometric_will.typ')} value={rec.media_type} />
            <Proof label={tt('biometric_will.recorded')} value={(rec.recorded_at || '').replace('T', ' ').slice(0, 16) + ' UTC'} />
            <Proof label={tt('biometric_will.sha_256_file_fingerprint')} value={rec.sha256} mono />
            <Proof label={tt('biometric_will.ledger_hash_proof_chain')} value={rec.ledger_hash} mono />
            <Proof label={tt('biometric_will.did')} value={rec.did} mono />
            <Pressable testID="bw-delete" onPress={remove} style={styles.deleteBtn}>
              <Ionicons name="trash-outline" size={16} color={C.error} />
              <Text style={styles.deleteText}>{tt('biometric_will.delete_record_again')}</Text>
            </Pressable>
          </View>
        ) : (
          <>
            {recording ? (
              <Pressable testID="bw-stop" onPress={stopAndUpload} style={[styles.cta, { backgroundColor: C.error }]}>
                <Ionicons name="stop" size={18} color={C.onError} />
                <Text style={[styles.ctaText, { color: C.onError }]}>{tt('biometric_will.stop_notarize')}</Text>
              </Pressable>
            ) : (
              <Pressable testID="bw-record" onPress={startRecording} disabled={uploading} style={styles.cta}>
                <Ionicons name="mic" size={18} color={C.onInverse} />
                <Text style={styles.ctaText}>{tt('biometric_will.record_voice_statement')}</Text>
              </Pressable>
            )}
            <Pressable testID="bw-video" onPress={pickVideo} disabled={uploading || recording} style={styles.ctaOutline}>
              <Ionicons name="videocam-outline" size={18} color={C.brand} />
              <Text style={styles.ctaOutlineText}>{tt('biometric_will.pick_video_from_gallery')}</Text>
            </Pressable>
            {uploading && (
              <View style={{ marginTop: S.lg, alignItems: 'center' }}>
                <ActivityIndicator color={C.brand} />
                <Text style={styles.hint}>{tt('biometric_will.recording_and_notarizing')}</Text>
              </View>
            )}
            {recording && <Text style={[styles.hint, { color: C.error }]}>{tt('biometric_will.recording_speak_your_statement')}</Text>}
          </>
        )}

        <Text style={styles.disclaimer}>
          {tt('biometric_will.the_hash_is_written_to_a_tamper_evid')}
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

function Proof({ label, value, mono }: any) {
  return (
    <View style={{ marginTop: S.md }}>
      <Text style={styles.proofLabel}>{label}</Text>
      <Text style={[styles.proofValue, mono && { fontFamily: 'monospace', fontSize: 10 }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 14 },
  heroIcon: { width: 56, height: 56, borderRadius: R.lg, backgroundColor: C.brandTer, alignItems: 'center', justifyContent: 'center' },
  h1: { marginTop: S.lg, fontSize: 24, fontWeight: '900', color: C.fg },
  sub: { marginTop: S.sm, fontSize: 13, color: C.onS3, lineHeight: 19 },
  cta: { marginTop: S.xxl, flexDirection: 'row', gap: S.sm, backgroundColor: C.brand, borderRadius: R.sm, minHeight: 52, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  ctaOutline: { marginTop: S.md, flexDirection: 'row', gap: S.sm, borderWidth: 1.5, borderColor: C.brand, borderRadius: R.sm, minHeight: 52, alignItems: 'center', justifyContent: 'center' },
  ctaOutlineText: { color: C.brand, fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  proofCard: { marginTop: S.xl, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.brand, padding: S.lg },
  proofTitle: { color: C.brand, fontWeight: '900', letterSpacing: 2, fontSize: 12 },
  proofLabel: { color: C.info, fontSize: 10, letterSpacing: 1, fontWeight: '800' },
  proofValue: { color: C.fg, fontSize: 12, marginTop: 2 },
  deleteBtn: { marginTop: S.xl, flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', minHeight: 44 },
  deleteText: { color: C.error, fontWeight: '800', fontSize: 11, letterSpacing: 1 },
  permBox: { marginTop: S.lg, backgroundColor: C.surface2, borderRadius: R.sm, padding: S.md, borderWidth: 1, borderColor: C.warn },
  permText: { color: C.fg, fontSize: 12, lineHeight: 18 },
  permBtn: { marginTop: S.md, backgroundColor: C.warn, borderRadius: R.sm, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  permBtnText: { color: C.onWarn, fontWeight: '900', fontSize: 12, letterSpacing: 1 },
  hint: { marginTop: S.md, color: C.onS3, fontSize: 12, textAlign: 'center' },
  err: { color: C.error, marginTop: S.md, fontSize: 12 },
  disclaimer: { marginTop: S.xl, color: C.info, fontSize: 10, lineHeight: 15, textAlign: 'center' },
});
