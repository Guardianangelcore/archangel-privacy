/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams } from 'expo-router';
import * as DocumentPicker from 'expo-document-picker';
import * as FileSystem from 'expo-file-system/legacy';
import { API_BASE } from '@/src/api';
import { encryptForRecipient, b64decode } from '@/src/dropcrypto';
import { C, S, R } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

/** PUBLIC provider portal — no login. File is encrypted IN THIS BROWSER with the
 *  patient's public key before upload. The server never sees the plaintext. */
export default function DropPortal() {
  const { t: tt, tx } = useI18n();
  const { dropId } = useLocalSearchParams<{ dropId: string }>();
  const [info, setInfo] = useState<any>(null);
  const [err, setErr] = useState('');
  const [file, setFile] = useState<any>(null);
  const [guardianId, setGuardianId] = useState('');
  const [senderName, setSenderName] = useState('');
  const [docTitle, setDocTitle] = useState('');
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API_BASE}/api/health-drop/${dropId}/info`);
        if (!r.ok) throw new Error('This Drop link does not exist or was revoked.');
        setInfo(await r.json());
      } catch (e: any) { setErr(String(e.message || e)); }
    })();
  }, [dropId]);

  const pick = async () => {
    const res = await DocumentPicker.getDocumentAsync({ type: ['application/pdf', 'image/*'], copyToCacheDirectory: true });
    if (!res.canceled && res.assets?.length) setFile(res.assets[0]);
  };

  const send = async () => {
    if (!file || !guardianId.trim() || !info?.public_key) return;
    setBusy(true); setErr('');
    try {
      let bytes: Uint8Array;
      if (Platform.OS === 'web') {
        const buf = await (await fetch(file.uri)).arrayBuffer();
        bytes = new Uint8Array(buf);
      } else {
        const b64 = await FileSystem.readAsStringAsync(file.uri, { encoding: 'base64' as any });
        bytes = b64decode(b64);
      }
      if (bytes.length > 14 * 1024 * 1024) throw new Error('The file is too large (max 14MB).');
      const { ciphertext, nonce, ephPub } = encryptForRecipient(bytes, info.public_key);

      const form = new FormData();
      if (Platform.OS === 'web') {
        form.append('file', new Blob([ciphertext as any]), 'encrypted.bin');
      } else {
        const tmp = `${FileSystem.cacheDirectory}drop_ct.bin`;
        let b64ct = '';
        // encode in chunks to avoid stack limits
        const CH = 0x8000;
        let bin = '';
        for (let i = 0; i < ciphertext.length; i += CH) bin += String.fromCharCode.apply(null, Array.from(ciphertext.subarray(i, i + CH)) as any);
        b64ct = (global as any).btoa ? (global as any).btoa(bin) : '';
        await FileSystem.writeAsStringAsync(tmp, b64ct, { encoding: 'base64' as any });
        form.append('file', { uri: tmp, name: 'encrypted.bin', type: 'application/octet-stream' } as any);
      }
      form.append('eph_pub', ephPub);
      form.append('nonce', nonce);
      form.append('guardian_id', guardianId.trim());
      form.append('sender_name', senderName.trim());
      form.append('doc_title', docTitle.trim() || file.name || 'Medical document');
      form.append('orig_type', file.mimeType || 'application/pdf');

      const r = await fetch(`${API_BASE}/api/health-drop/${dropId}/upload`, { method: 'POST', body: form });
      if (!r.ok) {
        const txt = await r.text();
        throw new Error(txt.includes('Guardian-ID') || txt.includes('does not match') ? 'The Guardian-ID does not match this Drop link.' : txt);
      }
      setDone(true);
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(false); }
  };

  return (
    <SafeAreaView testID="drop-portal" style={styles.root} edges={['top']}>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60, maxWidth: 560, width: '100%', alignSelf: 'center' }} keyboardShouldPersistTaps="handled">
        <Text style={styles.brand}>{tt('drop_dropId_.guardian_health_drop')}</Text>
        <Text style={styles.h1}>{tt('drop_dropId_.provider_portal')}</Text>
        <Text style={styles.sub}>
          {tt('drop_dropId_.securely_send_a_report_referral_stra')}
          {info?.patient_hint ? ` (${info.patient_hint})` : ''}{tt('drop_dropId_.the_file_is_encrypted_in_your_browse')}
        </Text>

        {!!err && <Text style={styles.err}>{err}</Text>}

        {done ? (
          <View style={styles.doneBox}>
            <Ionicons name="checkmark-circle" size={44} color="#5FA779" />
            <Text style={styles.doneTitle}>{tt('drop_dropId_.sent_encrypted')}</Text>
            <Text style={styles.doneSub}>{tt('drop_dropId_.the_patient_was_notified_only_they_c')}</Text>
            <Pressable testID="dp-again" onPress={() => { setDone(false); setFile(null); setDocTitle(''); }} style={styles.ctaOutline}>
              <Text style={styles.ctaOutlineText}>{tt('drop_dropId_.send_another_document')}</Text>
            </Pressable>
          </View>
        ) : info && (
          <>
            {!info.has_key && (
              <View style={styles.warnBox}>
                <Text style={styles.warnText}>{tt('drop_dropId_.the_patient_has_not_generated_encryp')}</Text>
              </View>
            )}
            <Pressable testID="dp-pick" onPress={pick} style={styles.dropZone}>
              <Ionicons name={file ? 'document-attach' : 'cloud-upload-outline'} size={34} color={C.brand} />
              <Text style={styles.dropText}>{file ? file.name : tt('drop_dropId_.choose_a_pdf_or_a_photo_of_the_repor')}</Text>
              {!!file && <Text style={styles.dropSub}>{Math.round((file.size || 0) / 1024)} {tt('drop_dropId_.kb_ready_for_encryption')}</Text>}
            </Pressable>

            <Text style={styles.lbl}>{tt('drop_dropId_.guardian_id_pacienta_overenie')}</Text>
            <TextInput testID="dp-guardian-id" style={styles.input} placeholder={tt('drop_dropId_.did_guardian_or_the_last_6_character')} placeholderTextColor={C.info} value={guardianId} onChangeText={setGuardianId} autoCapitalize="none" />
            <Text style={styles.lbl}>{tt('drop_dropId_.your_name_practice')}</Text>
            <TextInput testID="dp-sender" style={styles.input} placeholder={tt('drop_dropId_.dr_smith_orthopedics')} placeholderTextColor={C.info} value={senderName} onChangeText={setSenderName} />
            <Text style={styles.lbl}>{tt('drop_dropId_.document_title')}</Text>
            <TextInput testID="dp-title" style={styles.input} placeholder={tt('drop_dropId_.referral_orthopedics_transfer_slip')} placeholderTextColor={C.info} value={docTitle} onChangeText={setDocTitle} />

            <Pressable testID="dp-send" onPress={send} disabled={busy || !file || !guardianId.trim() || !info.has_key} style={[styles.cta, (busy || !file || !guardianId.trim() || !info.has_key) && { opacity: 0.5 }]}>
              {busy ? <ActivityIndicator color={C.onInverse} /> : (
                <>
                  <Ionicons name="lock-closed" size={16} color={C.onInverse} />
                  <Text style={styles.ctaText}>{tt('drop_dropId_.encrypt_send')}</Text>
                </>
              )}
            </Pressable>
            <Text style={styles.foot}>{tt('drop_dropId_.zero_knowledge_the_server_stores_onl')}</Text>
          </>
        )}
        {!info && !err && <ActivityIndicator color={C.brand} style={{ marginTop: 40 }} />}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  brand: { color: C.brand, fontWeight: '900', letterSpacing: 3, fontSize: 12 },
  h1: { marginTop: S.md, fontSize: 26, fontWeight: '900', color: C.fg },
  sub: { marginTop: S.sm, fontSize: 13, color: C.onS3, lineHeight: 19 },
  dropZone: { marginTop: S.xl, borderWidth: 2, borderColor: C.brand, borderStyle: 'dashed', borderRadius: R.md, alignItems: 'center', justifyContent: 'center', paddingVertical: S.xxl, gap: S.sm, backgroundColor: C.surface2 },
  dropText: { color: C.fg, fontWeight: '800', fontSize: 14, textAlign: 'center', paddingHorizontal: S.lg },
  dropSub: { color: C.info, fontSize: 11 },
  lbl: { marginTop: S.lg, marginBottom: 6, fontSize: 10, letterSpacing: 2, color: C.info, fontWeight: '800' },
  input: { backgroundColor: C.surface2, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, color: C.fg, paddingHorizontal: S.lg, minHeight: 48, fontSize: 13 },
  cta: { marginTop: S.xl, flexDirection: 'row', gap: S.sm, backgroundColor: C.brand, borderRadius: R.sm, minHeight: 52, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  ctaOutline: { marginTop: S.lg, borderWidth: 1.5, borderColor: C.brand, borderRadius: R.sm, minHeight: 48, alignItems: 'center', justifyContent: 'center', paddingHorizontal: S.lg },
  ctaOutlineText: { color: C.brand, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  warnBox: { marginTop: S.lg, backgroundColor: C.warn, borderRadius: R.sm, padding: S.md },
  warnText: { color: C.onWarn, fontWeight: '700', fontSize: 12, lineHeight: 17 },
  doneBox: { marginTop: S.xxl, alignItems: 'center', gap: S.md, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: '#5FA779', padding: S.xl },
  doneTitle: { color: '#5FA779', fontWeight: '900', letterSpacing: 2, fontSize: 14 },
  doneSub: { color: C.onS3, fontSize: 12, textAlign: 'center', lineHeight: 18 },
  err: { color: C.error, marginTop: S.lg, fontSize: 12 },
  foot: { marginTop: S.lg, color: C.info, fontSize: 10, textAlign: 'center', lineHeight: 15 },
});
