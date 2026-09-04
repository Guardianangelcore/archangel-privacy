/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// MEDICAL ARBITRAGE — cross-border surgery cost optimizer (PL / HU / TR) + genomic Bio-Identity
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { C, S } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

export default function Arbitrage() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [quote, setQuote] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState('');
  const [genomic, setGenomic] = useState<any>(null);
  const [marker, setMarker] = useState('');
  const [provider, setProvider] = useState('');

  const load = useCallback(async () => {
    try { setData(await api('/arbitrage/procedures')); } catch (e) { console.log(e); }
    try { setGenomic(await api('/bioidentity')); } catch { }
  }, []);
  useEffect(() => { load(); }, [load]);

  const getQuote = async (pid: string, cc: string) => {
    setBusy(`${pid}-${cc}`); setErr('');
    try { setQuote(await api('/arbitrage/quote', { method: 'POST', body: JSON.stringify({ procedure_id: pid, country: cc }) })); }
    catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const saveGenomic = async () => {
    setBusy('genomic'); setErr('');
    try {
      const markers = [...(genomic?.markers || []), marker.trim()].filter(Boolean);
      setGenomic(await api('/bioidentity/genomic', { method: 'PUT', body: JSON.stringify({ provider: provider || genomic?.provider || '', markers }) }));
      setMarker('');
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const countries = data?.countries || {};

  return (
    <SafeAreaView testID="arbitrage-screen" style={st.root} edges={['top', 'bottom']}>
      <View style={st.header}>
        <Pressable testID="ar-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={st.title}>{tt('arbitrage.medical_arbitrage')}</Text>
        <View style={{ width: 26 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        <Text style={st.intro}>
          {tt('arbitrage.cross_border_surgery_cost_optimizati')}
        </Text>

        {quote && (
          <View testID="ar-quote" style={st.quoteCard}>
            <View style={st.rowSpread}>
              <Text style={st.quoteTitle}>{countries[quote.country]?.flag} {tt('arbitrage.bill_prediction')}</Text>
              <Pressable testID="ar-quote-close" onPress={() => setQuote(null)} hitSlop={10}>
                <Ionicons name="close" size={20} color={C.fg} />
              </Pressable>
            </View>
            <Text style={st.quoteProc}>{quote.procedure}</Text>
            <Text style={st.meta}>{quote.clinic} {tt('arbitrage.wait')} {quote.wait_days_abroad} {tt('arbitrage.days')}</Text>
            <View style={st.qRow}><Text style={st.qLbl}>{tt('arbitrage.procedure')}</Text><Text style={st.qVal}>{quote.breakdown.procedure_eur.toLocaleString('sk-SK')} €</Text></View>
            <View style={st.qRow}><Text style={st.qLbl}>{tt('arbitrage.cesta_2_os')}</Text><Text style={st.qVal}>{quote.breakdown.travel_eur} €</Text></View>
            <View style={st.qRow}><Text style={st.qLbl}>{tt('arbitrage.ubytovanie_sprievodu')}</Text><Text style={st.qVal}>{quote.breakdown.accommodation_eur} €</Text></View>
            <View style={st.qRow}><Text style={st.qLbl}>{tt('arbitrage.spolu')}</Text><Text style={[st.qVal, { color: C.fg }]}>{quote.breakdown.total_eur.toLocaleString('sk-SK')} €</Text></View>
            <View style={st.qRow}><Text style={st.qLbl}>{tt('arbitrage.s2_refund_prediction')}</Text><Text style={[st.qVal, { color: '#5FA779' }]}>−{quote.breakdown.s2_predicted_refund_eur.toLocaleString('sk-SK')} €</Text></View>
            <View style={[st.qRow, { borderTopWidth: 1, borderColor: C.borderStrong, paddingTop: S.sm }]}>
              <Text style={[st.qLbl, { fontWeight: '900', color: C.fg }]}>{tt('arbitrage.z_vrecka')}</Text>
              <Text style={[st.qVal, { color: C.brand, fontSize: 18 }]}>{quote.breakdown.net_out_of_pocket_eur.toLocaleString('sk-SK')} €</Text>
            </View>
            <Text style={st.saving}>{tt('arbitrage.savings_vs_sk')} {quote.saving_vs_sk_eur.toLocaleString('sk-SK')} {tt('arbitrage.wait_shorter_by')} {quote.wait_cut_days} {tt('arbitrage.days')}</Text>
            <Text style={st.meta}>{quote.legal_route} {tt('arbitrage.ghost_mode_compatible_anonymous_pati')}</Text>
          </View>
        )}
        {!!err && <Text testID="ar-err" style={st.err}>{err}</Text>}

        <Text style={st.section}>{tt('arbitrage.procedures')}{data?.procedures?.length ?? 0})</Text>
        {(data?.procedures ?? []).map((p: any) => (
          <View testID={`ar-proc-${p.procedure_id}`} key={p.procedure_id} style={st.card}>
            <Text style={st.cardTitle}>{p.name}</Text>
            <Text style={st.meta}>{tt('arbitrage.sk')} {p.sk_price_eur.toLocaleString('sk-SK')} {tt('arbitrage.wait_1h21')} {p.sk_wait_days} {tt('arbitrage.days')}</Text>
            <Text style={st.best}>{tt('arbitrage.best')} {countries[p.best_country]?.flag} −{p.best_saving_eur.toLocaleString('sk-SK')} € · −{p.best_wait_cut_days} {tt('arbitrage.days_of_waiting')}</Text>
            <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.md }}>
              {Object.entries(p.abroad).map(([cc, ab]: [string, any]) => (
                <Pressable testID={`ar-cc-${p.procedure_id}-${cc}`} key={cc} onPress={() => getQuote(p.procedure_id, cc)}
                  disabled={busy === `${p.procedure_id}-${cc}`} style={st.ccBtn}>
                  {busy === `${p.procedure_id}-${cc}` ? <ActivityIndicator size="small" color={C.fg} /> : (
                    <>
                      <Text style={st.ccFlag}>{countries[cc]?.flag} {cc}</Text>
                      <Text style={st.ccPrice}>{ab.price_eur.toLocaleString('sk-SK')} €</Text>
                      <Text style={st.ccWait}>{ab.wait_days} {tt('arbitrage.days')}</Text>
                    </>
                  )}
                </Pressable>
              ))}
            </View>
          </View>
        ))}
        <Text style={st.legal}>{data?.legal_note}</Text>

        <Text style={st.section}>{tt('arbitrage.genomic_bio_identity')}</Text>
        <Text style={st.intro}>
          {tt('arbitrage.dna_markers_in_your_sovereign_vault')}
        </Text>
        {!!genomic?.genomic_sha256 && (
          <View style={st.card}>
            <Text style={st.meta}>{tt('arbitrage.provider')} {genomic.provider || '—'} {tt('arbitrage.sha_256')}{genomic.genomic_sha256.slice(0, 14)}…</Text>
            {(genomic.markers || []).map((m: string, i: number) => (
              <Text key={i} style={st.markerText}>• {m}</Text>
            ))}
          </View>
        )}
        <TextInput testID="ar-genomic-provider" value={provider} onChangeText={setProvider} placeholder={tt('arbitrage.sequencing_provider_e_g_dante_labs')}
          placeholderTextColor="#777" style={st.input} />
        <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.sm }}>
          <TextInput testID="ar-genomic-marker" value={marker} onChangeText={setMarker} placeholder={tt('arbitrage.marker_e_g_brca1_negative')}
            placeholderTextColor="#777" style={[st.input, { flex: 1, marginTop: 0 }]} />
          <Pressable testID="ar-genomic-save" onPress={saveGenomic} disabled={busy === 'genomic' || !marker.trim()} style={st.addBtn}>
            {busy === 'genomic' ? <ActivityIndicator size="small" color={C.onInverse} /> : <Text style={st.addText}>{tt('arbitrage.save')}</Text>}
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  intro: { color: C.onS3, fontSize: 12, lineHeight: 18 },
  section: { color: C.info, fontSize: 11, fontWeight: '900', letterSpacing: 2, marginTop: S.xl, marginBottom: S.sm },
  card: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginTop: S.sm, backgroundColor: C.surface2 },
  cardTitle: { color: C.fg, fontSize: 14, fontWeight: '800' },
  meta: { color: C.info, fontSize: 10, marginTop: 4, letterSpacing: 0.3, lineHeight: 15 },
  best: { color: '#5FA779', fontSize: 11, fontWeight: '800', marginTop: 6 },
  ccBtn: { flex: 1, borderWidth: 1.5, borderColor: C.borderStrong, alignItems: 'center', paddingVertical: S.sm, minHeight: 60, justifyContent: 'center' },
  ccFlag: { color: C.fg, fontSize: 11, fontWeight: '900' },
  ccPrice: { color: C.brand, fontSize: 13, fontWeight: '900', marginTop: 2 },
  ccWait: { color: C.info, fontSize: 9, marginTop: 2 },
  legal: { color: C.info, fontSize: 10, lineHeight: 15, marginTop: S.md },
  quoteCard: { borderWidth: 2, borderColor: C.brand, padding: S.lg, marginTop: S.md, backgroundColor: C.surface2 },
  quoteTitle: { color: C.brand, fontSize: 12, fontWeight: '900', letterSpacing: 2 },
  quoteProc: { color: C.fg, fontSize: 16, fontWeight: '900', marginTop: S.sm },
  rowSpread: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  qRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: S.sm },
  qLbl: { color: C.onS3, fontSize: 12 },
  qVal: { color: C.onS3, fontSize: 13, fontWeight: '800' },
  saving: { color: C.brand, fontSize: 12, fontWeight: '900', marginTop: S.md },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginTop: S.sm },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 14, color: C.fg, backgroundColor: C.surface2, marginTop: S.sm },
  addBtn: { backgroundColor: C.brand, paddingHorizontal: S.lg, justifyContent: 'center', minHeight: 48 },
  addText: { color: C.onInverse, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  markerText: { color: C.fg, fontSize: 12, marginTop: 4 },
});
