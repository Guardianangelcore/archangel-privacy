/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// FOUNDER'S TOOLKIT — investor demo: high-end financial forecast 2026–2030,
// 22nd-century roadmap and the GitHub Release Package (README / ARCHITECTURE /
// API_SPEC / private LICENSE) ready for the competition submission.
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator, Modal, Share, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { tap } from '@/src/ui/glass';
import { sharePdf } from '@/src/pdf';
import { C, S, R } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

const fmt = (n: number) => n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)} M` : n >= 1000 ? `${(n / 1000).toFixed(0)} k` : String(n);

export default function FounderToolkit() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState('');
  const [doc, setDoc] = useState<any>(null);
  const [docBusy, setDocBusy] = useState('');

  useEffect(() => {
    (async () => {
      try { setData(await api('/founder/toolkit')); } catch (e: any) { setErr(String(e.message || e)); }
    })();
  }, []);

  const openDoc = async (name: string) => {
    setDocBusy(name);
    try { setDoc(await api(`/founder/release/${name}`)); } catch (e: any) { setErr(String(e.message || e)); }
    setDocBusy('');
  };

  const shareDoc = async () => {
    if (!doc) return;
    try { await Share.share({ message: doc.content, title: doc.name }); } catch {}
  };

  const years = data?.forecast?.years || [];
  const maxArr = Math.max(1, ...years.map((y: any) => y.arr_eur));
  const a = data?.forecast?.assumptions;

  return (
    <SafeAreaView testID="founder-toolkit-screen" style={st.root} edges={['top', 'bottom']}>
      <View style={st.header}>
        <Pressable testID="ft-back" onPress={() => { tap(); router.back(); }} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={st.headTitle}>{tt('founder_toolkit.founder_s_toolkit')}</Text>
        <Ionicons name="briefcase-outline" size={20} color={C.brand} />
      </View>

      <ScrollView contentContainerStyle={{ paddingBottom: 80 }}>
        {!data && !err && <ActivityIndicator color={C.brand} style={{ marginTop: 60 }} />}
        {!!err && <Text style={st.err}>{err}</Text>}

        {data && (
          <>
            {/* FORECAST */}
            <Text style={st.kicker}>{tt('founder_toolkit.investor_demo')}</Text>
            <Text style={st.title}>{tt('founder_toolkit.financial_forecast')}{'\n'}2026 – 2030</Text>

            <View style={st.assumpRow}>
              <View style={st.assumpBox}><Text style={st.assumpVal}>{a?.arpu_paid_eur_mo} €</Text><Text style={st.assumpLbl}>{tt('founder_toolkit.arpu_mes')}</Text></View>
              <View style={st.assumpBox}><Text style={st.assumpVal}>{a?.guardian_tax_pct} %</Text><Text style={st.assumpLbl}>{tt('founder_toolkit.guardian_tax')}</Text></View>
              <View style={st.assumpBox}><Text style={st.assumpVal}>{a?.ltv_cac}×</Text><Text style={st.assumpLbl}>{tt('founder_toolkit.ltv_cac')}</Text></View>
              <View style={st.assumpBox}><Text style={st.assumpVal}>{a?.gross_margin_pct} %</Text><Text style={st.assumpLbl}>{tt('founder_toolkit.gross_margin')}</Text></View>
            </View>

            {years.map((y: any) => (
              <View key={y.year} testID={`ft-year-${y.year}`} style={st.yearCard}>
                <View style={st.yearHead}>
                  <Text style={st.yearNum}>{y.year}</Text>
                  <Text style={st.yearArr}>{fmt(y.arr_eur)} {tt('founder_toolkit.arr')}</Text>
                </View>
                <View style={st.barBg}>
                  <View style={[st.bar, { width: `${Math.max(4, (y.arr_eur / maxArr) * 100)}%` }]} />
                </View>
                <Text style={st.yearLine}>
                  {fmt(y.users)} {tt('founder_toolkit.users')} {fmt(y.paid_users)} {tt('founder_toolkit.paying_mrr')} {fmt(y.mrr_eur)} €
                </Text>
                <Text style={st.yearSub}>
                  {tt('founder_toolkit.subscriptions')} {fmt(y.subscription_mrr_eur)} {tt('founder_toolkit.guardian_tax_14y7')} {fmt(y.guardian_tax_mrr_eur)} {tt('founder_toolkit.mo')}
                </Text>
              </View>
            ))}
            <Text style={st.note}>{tt('founder_toolkit.tier_mix_guardian_9_80_sentinel_149')} {a?.churn_mo_pct} {tt('founder_toolkit.mes')}</Text>

            {/* ROADMAP */}
            <Text style={st.kicker2}>{tt('founder_toolkit.vision')}</Text>
            <Text style={st.title}>{tt('founder_toolkit.22nd_century_roadmap')}</Text>
            <View style={st.timeline}>
              {(data.roadmap || []).map((m: any, i: number) => (
                <View key={i} testID={`ft-road-${i}`} style={st.roadRow}>
                  <View style={st.roadRail}>
                    <View style={st.roadDot} />
                    {i < data.roadmap.length - 1 && <View style={st.roadLine} />}
                  </View>
                  <View style={st.roadCard}>
                    <View style={st.roadHead}>
                      <Text style={st.roadYear}>{m.year}</Text>
                      <View style={st.roadEra}><Text style={st.roadEraText}>{m.era}</Text></View>
                    </View>
                    <Text style={st.roadTitle}>{tx(m.title)}</Text>
                    <Text style={st.roadDetail}>{m.detail}</Text>
                  </View>
                </View>
              ))}
            </View>

            {/* RELEASE PACKAGE */}
            <Text style={st.kicker2}>{tt('founder_toolkit.competition_entry')}</Text>
            <Text style={st.title}>{tt('founder_toolkit.github_release_package')}</Text>
            <Text style={st.note}>{tt('founder_toolkit.complete_documentation_in_release_pa')}</Text>
            <Pressable testID="ft-jury-pdf" onPress={() => { tap('light'); sharePdf('/founder/jury-cheat-sheet', 'GUARDIAN_JURY_CHEAT_SHEET.pdf'); }} style={[st.docRow, { borderColor: C.brand }]}>
              <View style={st.docIcon}>
                <Ionicons name="ribbon-outline" size={18} color={C.brand} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={st.docName}>{tt('founder_toolkit.jury_cheat_sheet_pdf')}</Text>
                <Text style={st.docDesc}>{tt('founder_toolkit.printable_2_pager_demo_script_with_s')}</Text>
              </View>
              <Ionicons name="download-outline" size={18} color={C.brand} />
            </Pressable>
            {(data.release_package?.docs || []).map((d: any) => (
              <Pressable key={d.name} testID={`ft-doc-${d.name}`} onPress={() => { tap('light'); openDoc(d.name); }} style={st.docRow}>
                <View style={st.docIcon}>
                  <Ionicons name={d.name === 'LICENSE' ? 'lock-closed-outline' : 'document-text-outline'} size={18} color={C.brand} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={st.docName}>{d.name}</Text>
                  <Text style={st.docDesc}>{tx(d.desc)}</Text>
                  <Text style={st.docMeta}>{(d.bytes / 1024).toFixed(1)} {tt('founder_toolkit.kb_sha256')} {String(d.sha256).slice(0, 12)}…</Text>
                </View>
                {docBusy === d.name ? <ActivityIndicator size="small" color={C.brand} /> : <Ionicons name="chevron-forward" size={16} color={C.info} />}
              </Pressable>
            ))}

            <Text style={st.footer}>{tt('founder_toolkit.guardian_angel_sovereign_foundation')}</Text>
          </>
        )}
      </ScrollView>

      {/* DOC VIEWER */}
      <Modal visible={!!doc} animationType="slide" onRequestClose={() => setDoc(null)}>
        <SafeAreaView style={st.root} edges={['top', 'bottom']}>
          <View style={st.header}>
            <Pressable testID="ft-doc-close" onPress={() => { tap(); setDoc(null); }} hitSlop={12}>
              <Ionicons name="close" size={24} color={C.fg} />
            </Pressable>
            <Text style={st.headTitle}>{doc?.name}</Text>
            <Pressable testID="ft-doc-share" onPress={() => { tap('light'); shareDoc(); }} hitSlop={12}>
              <Ionicons name="share-outline" size={22} color={C.brand} />
            </Pressable>
          </View>
          <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 60 }}>
            <Text style={st.docBody}>{doc?.content}</Text>
            <Text style={st.docMeta}>{tt('founder_toolkit.sha256')} {doc?.sha256}</Text>
          </ScrollView>
        </SafeAreaView>
      </Modal>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  headTitle: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 14 },
  kicker: { color: C.brand, fontWeight: '900', fontSize: 10, letterSpacing: 3, paddingHorizontal: S.lg, marginTop: S.md },
  kicker2: { color: C.brand, fontWeight: '900', fontSize: 10, letterSpacing: 3, paddingHorizontal: S.lg, marginTop: S.xxl },
  title: { color: C.fg, fontWeight: '900', fontSize: 24, lineHeight: 30, paddingHorizontal: S.lg, marginTop: 6 },
  assumpRow: { flexDirection: 'row', gap: S.sm, paddingHorizontal: S.lg, marginTop: S.lg },
  assumpBox: { flex: 1, borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.md, backgroundColor: 'rgba(212,175,55,0.06)', paddingVertical: S.md, alignItems: 'center' },
  assumpVal: { color: C.brand, fontWeight: '900', fontSize: 15 },
  assumpLbl: { color: C.info, fontWeight: '800', fontSize: 7.5, letterSpacing: 1, marginTop: 3 },
  yearCard: { marginHorizontal: S.lg, marginTop: S.md, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.lg },
  yearHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  yearNum: { color: C.fg, fontWeight: '900', fontSize: 18, letterSpacing: 1 },
  yearArr: { color: C.brand, fontWeight: '900', fontSize: 16 },
  barBg: { height: 8, backgroundColor: 'rgba(255,255,255,0.07)', borderRadius: 4, marginTop: S.sm, overflow: 'hidden' },
  bar: { height: 8, backgroundColor: C.brand, borderRadius: 4 },
  yearLine: { color: C.onS3, fontSize: 12, marginTop: S.sm, fontWeight: '700' },
  yearSub: { color: C.info, fontSize: 10.5, marginTop: 3 },
  note: { color: C.info, fontSize: 10.5, lineHeight: 15, paddingHorizontal: S.lg, marginTop: S.md },
  timeline: { marginTop: S.lg },
  roadRow: { flexDirection: 'row', paddingHorizontal: S.lg },
  roadRail: { width: 24, alignItems: 'center' },
  roadDot: { width: 12, height: 12, borderRadius: 6, backgroundColor: C.brand, marginTop: 6 },
  roadLine: { flex: 1, width: 2, backgroundColor: 'rgba(212,175,55,0.3)', marginVertical: 2 },
  roadCard: { flex: 1, marginLeft: S.md, marginBottom: S.md, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.md },
  roadHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  roadYear: { color: C.brand, fontWeight: '900', fontSize: 13, letterSpacing: 1 },
  roadEra: { borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.pill, paddingHorizontal: 8, paddingVertical: 2 },
  roadEraText: { color: C.brand, fontWeight: '900', fontSize: 8, letterSpacing: 1.5 },
  roadTitle: { color: C.fg, fontWeight: '900', fontSize: 14, marginTop: 4 },
  roadDetail: { color: C.info, fontSize: 11, lineHeight: 16, marginTop: 3 },
  docRow: { flexDirection: 'row', gap: S.md, alignItems: 'center', marginHorizontal: S.lg, marginTop: S.sm, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.md, minHeight: 64 },
  docIcon: { width: 40, height: 40, borderRadius: R.pill, backgroundColor: 'rgba(212,175,55,0.14)', alignItems: 'center', justifyContent: 'center' },
  docName: { color: C.fg, fontWeight: '900', fontSize: 13 },
  docDesc: { color: C.info, fontSize: 10.5, marginTop: 1 },
  docMeta: { color: C.info, fontSize: 9, marginTop: 3, fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }) },
  docBody: { color: C.fg, fontSize: 12, lineHeight: 18, fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }) },
  err: { color: C.error, fontSize: 12, paddingHorizontal: S.lg, marginTop: S.md },
  footer: { textAlign: 'center', color: C.info, fontSize: 9, letterSpacing: 1.5, marginTop: S.xl, paddingHorizontal: S.lg },
});
