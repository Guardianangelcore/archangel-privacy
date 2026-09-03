/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { sharePdf } from '@/src/pdf';
import { C, S, R } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

export default function BorderPass() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const [cert, setCert] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    (async () => {
      try { setCert(await api('/border/certificate')); } catch (e: any) { setErr(String(e.message || e)); }
    })();
  }, []);

  const exportPdf = async () => {
    setBusy(true);
    try { await sharePdf('/border/certificate.pdf', 'guardian_border_certificate.pdf'); }
    catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(false); }
  };

  return (
    <SafeAreaView testID="border-pass-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="bp-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>{tt('border_pass.border_crosser')}</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }}>
        <View style={styles.heroIcon}><Ionicons name="airplane-outline" size={28} color={C.brand} /></View>
        <Text style={styles.h1}>{tt('border_pass.international_medication_certificate')}</Text>
        <Text style={styles.sub}>
          {tt('border_pass.a_certificate_in_14_languages_signed')}
        </Text>

        {!cert && !err && <ActivityIndicator color={C.brand} style={{ marginTop: 40 }} />}
        {!!err && <Text style={styles.err}>{err}</Text>}

        {cert && (
          <>
            <View style={styles.card}>
              <Row label={tt('border_pass.holder')} value={cert.holder || '—'} />
              <Row label={tt('border_pass.blood_type')} value={cert.blood_type || '—'} />
              <Row label={tt('border_pass.alergie')} value={cert.allergies || '—'} />
              <Row label={tt('border_pass.did_podpis')} value={`${(cert.did_signature || '').slice(0, 20)}…`} mono />
            </View>

            <Text style={styles.section}>{tt('border_pass.medications_in_certificate')}{cert.medications?.length || 0})</Text>
            {(cert.medications || []).length === 0 ? (
              <Text style={styles.hint}>
                {tt('border_pass.no_prescription_medications_in_the_m')} {tt('border_pass.prescription')}{tt('border_pass.they_appear_here_automatically')}
              </Text>
            ) : (
              cert.medications.map((m: any, i: number) => (
                <View key={i} style={styles.medRow}>
                  <Ionicons name="medkit-outline" size={16} color={C.brand} />
                  <Text style={styles.medText}>{m.name} — {m.quantity} {m.unit}{m.prescription ? '  ' + tt('border_pass.rx') : ''}</Text>
                </View>
              ))
            )}

            <Text style={styles.section}>{tt('border_pass.certificate_languages')}</Text>
            <View style={styles.langWrap}>
              {(cert.languages || []).map((l: any) => (
                <View key={l.code} style={styles.langChip}><Text style={styles.langText}>{l.name}</Text></View>
              ))}
            </View>

            <Pressable testID="bp-pdf" onPress={exportPdf} disabled={busy} style={styles.cta}>
              {busy ? <ActivityIndicator color={C.onInverse} /> : (
                <>
                  <Ionicons name="document-text-outline" size={18} color={C.onInverse} />
                  <Text style={styles.ctaText}>{tt('border_pass.download_pdf_certificate')}</Text>
                </>
              )}
            </Pressable>
            <Text style={styles.disclaimer}>
              {tt('border_pass.this_document_is_an_informational_te')}
            </Text>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function Row({ label, value, mono }: any) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={[styles.rowValue, mono && { fontFamily: 'monospace', fontSize: 11 }]} numberOfLines={1}>{value}</Text>
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
  card: { marginTop: S.xl, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.lg, gap: S.md },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: S.md },
  rowLabel: { color: C.info, fontSize: 12, fontWeight: '700' },
  rowValue: { color: C.fg, fontSize: 13, fontWeight: '700', flexShrink: 1 },
  section: { marginTop: S.xl, marginBottom: S.sm, fontSize: 11, letterSpacing: 2, color: C.info, fontWeight: '800' },
  hint: { color: C.onS3, fontSize: 12, lineHeight: 18, backgroundColor: C.surface2, borderRadius: R.sm, padding: S.md },
  medRow: { flexDirection: 'row', alignItems: 'center', gap: S.sm, paddingVertical: 6 },
  medText: { color: C.fg, fontSize: 13 },
  langWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: S.sm },
  langChip: { borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.pill, paddingHorizontal: S.md, paddingVertical: 5 },
  langText: { color: C.onS3, fontSize: 11, fontWeight: '700' },
  cta: { marginTop: S.xxl, flexDirection: 'row', gap: S.sm, backgroundColor: C.brand, borderRadius: R.sm, minHeight: 52, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  err: { color: C.error, marginTop: S.lg, fontSize: 12 },
  disclaimer: { marginTop: S.lg, color: C.info, fontSize: 10, lineHeight: 15, textAlign: 'center' },
});
