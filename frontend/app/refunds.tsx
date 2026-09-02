/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// One-Click Refund Engine — "Claim My Benefits": AI-prepopulated insurance refunds + tax summary
import React, { useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { sharePdf } from '@/src/pdf';
import Art50 from '@/src/Art50';
import { C, S } from '@/src/theme';
import { Lang } from '@/src/i18n';
import { useI18n } from '@/src/i18n-context';

export default function Refunds() {
  const { t: tt, tx } = useI18n();
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'en';
  const router = useRouter();
  const [claim, setClaim] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState('');

  const build = async () => {
    setBusy('build'); setErr('');
    try { setClaim(await api('/refunds/claim', { method: 'POST' })); }
    catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };
  const share = async () => {
    setBusy('pdf');
    try { await sharePdf('/refunds/claim.pdf', 'guardian_refund_claim.pdf'); } catch {}
    setBusy(null);
  };

  return (
    <SafeAreaView testID="refunds-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="rf-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={st.title}>{tt('refunds.claim_my_benefits')}</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        <Text style={st.intro}>{tt('refunds.jarvis_prefills_a_health_expense_ref')}</Text>

        <Pressable testID="rf-build" onPress={build} disabled={busy === 'build'} style={st.buildBtn}>
          {busy === 'build' ? <ActivityIndicator color={C.onInverse} /> : <>
            <Ionicons name="cash-outline" size={20} color={C.onInverse} />
            <Text style={st.buildText}>{tt('refunds.prepare_the_claim_with_one_tap')}</Text>
          </>}
        </Pressable>
        {!!err && <Text testID="rf-err" style={st.err}>{err}</Text>}

        {claim && (
          <View testID="rf-claim">
            <View style={st.totalCard}>
              <Text style={st.totalLbl}>{tt('refunds.estimated_refund')}</Text>
              <Text testID="rf-total" style={st.totalVal}>{claim.estimated_refund_eur} €</Text>
              <Text style={st.totalMeta}>{tt('refunds.insurer')} {claim.insurer} {tt('refunds.policy')} {claim.policy_paid ? tt('refunds.paid') : tt('refunds.unpaid')}</Text>
            </View>

            <Text style={st.section}>{tt('refunds.claim_items')}{claim.items?.length || 0})</Text>
            {(claim.items || []).length ? claim.items.map((it: any, i: number) => (
              <View key={i} style={st.row}>
                <Ionicons name="document-text-outline" size={18} color={C.brand} />
                <View style={{ flex: 1 }}>
                  <Text style={st.rowTitle}>{it.specialty}</Text>
                  <Text style={st.rowSub}>{it.source_doc || tt('refunds.doklad_z_trezoru')}{it.booked_slot ? ` · ${it.booked_slot}` : ''}</Text>
                </View>
                <Text style={st.rowVal}>{it.estimated_refund_eur} €</Text>
              </View>
            )) : (
              <Text style={st.emptyLine}>{tt('refunds.no_refundable_procedures_yet_upload')}</Text>
            )}

            <View style={st.taxCard}>
              <Text style={st.taxTitle}>{tt('refunds.tax_deduction')}</Text>
              <Text style={st.taxText}>{claim.tax_note}</Text>
              <Text style={st.taxText}>{tt('refunds.dokladov_v_trezore')} {claim.vault_docs}</Text>
            </View>

            <Pressable testID="rf-pdf" onPress={share} disabled={busy === 'pdf'} style={st.pdfBtn}>
              {busy === 'pdf' ? <ActivityIndicator color={C.fg} /> : <>
                <Ionicons name="share-outline" size={18} color={C.fg} />
                <Text style={st.pdfText}>{tt('refunds.share_pdf_claim_insurer_taxes')}</Text>
              </>}
            </Pressable>
          </View>
        )}

        <Art50 lang={lang} />
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  intro: { color: C.onS3, fontSize: 12, lineHeight: 18 },
  buildBtn: { marginTop: S.lg, flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, paddingVertical: S.lg, minHeight: 56 },
  buildText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginTop: S.md },
  totalCard: { marginTop: S.lg, borderWidth: 2, borderColor: C.brand, padding: S.lg, alignItems: 'center', backgroundColor: C.surface2 },
  totalLbl: { color: C.info, fontSize: 10, letterSpacing: 2, fontWeight: '800' },
  totalVal: { color: C.brand, fontSize: 42, fontWeight: '900', marginVertical: 4 },
  totalMeta: { color: C.onS3, fontSize: 11, textAlign: 'center', lineHeight: 16 },
  section: { marginTop: S.xl, marginBottom: S.sm, fontSize: 11, letterSpacing: 2, color: C.fg, fontWeight: '900' },
  row: { flexDirection: 'row', alignItems: 'center', gap: S.md, borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginBottom: S.sm, backgroundColor: C.surface2 },
  rowTitle: { fontWeight: '900', color: C.fg, fontSize: 13 },
  rowSub: { color: C.info, fontSize: 11, marginTop: 2 },
  rowVal: { color: C.brand, fontWeight: '900', fontSize: 14 },
  emptyLine: { color: C.info, fontSize: 12, fontStyle: 'italic', lineHeight: 18 },
  taxCard: { marginTop: S.md, borderWidth: 1.5, borderColor: '#B8860B', padding: S.md, backgroundColor: C.surface2 },
  taxTitle: { color: '#B8860B', fontWeight: '900', fontSize: 11, letterSpacing: 1.5 },
  taxText: { color: C.onS3, fontSize: 12, lineHeight: 17, marginTop: 4 },
  pdfBtn: { marginTop: S.lg, flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: C.borderStrong, paddingVertical: S.md, minHeight: 52 },
  pdfText: { color: C.fg, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
});
