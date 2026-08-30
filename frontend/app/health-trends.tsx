/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// TRENDY ZDRAVIA — ročné súhrny záznamov Karty života + Jarvisov AI súhrn.
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';

const CATS: any = {
  vaccine: { label: 'Očkovania', color: '#5FA779' },
  disease: { label: 'Choroby', color: '#BF5AF2' },
  surgery: { label: 'Operácie', color: '#FF453A' },
  injury: { label: 'Úrazy', color: '#FF9F0A' },
  exam: { label: 'Prehliadky', color: '#D4AF37' },
  dental: { label: 'Zubár', color: '#64D2FF' },
};
const KEYS = Object.keys(CATS);

export default function HealthTrends() {
  const router = useRouter();
  const { child_id, name } = useLocalSearchParams<{ child_id?: string; name?: string }>();
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState('');
  const [summary, setSummary] = useState('');
  const [sumBusy, setSumBusy] = useState(false);

  useEffect(() => {
    api(`/lifecard/trends${child_id ? `?child_id=${child_id}` : ''}`)
      .then(setData).catch((e: any) => setErr(String(e.message || e)));
  }, [child_id]);

  const genSummary = async () => {
    setSumBusy(true); setErr('');
    try {
      const r = await api('/lifecard/trends/summary', { method: 'POST', body: JSON.stringify({ child_id: child_id || null }) });
      setSummary(r.summary);
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setSumBusy(false); }
  };

  const years = data?.years || [];
  const maxTotal = Math.max(1, ...years.map((y: any) => y.total));

  return (
    <SafeAreaView testID="health-trends-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="tr-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={st.title}>TRENDY ZDRAVIA</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }}>
        <Text style={st.h1}>{name ? String(name) : 'Moja karta'}</Text>
        <Text style={st.sub}>Ako sa vyvíjajú choroby, úrazy, prehliadky a očkovania v čase — rok po roku.</Text>
        {!!err && <Text style={st.err}>{err}</Text>}

        {/* JARVIS SÚHRN */}
        <View testID="tr-summary-box" style={st.sumBox}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.sm }}>
            <Ionicons name="sparkles" size={16} color={C.brand} />
            <Text style={st.sumTitle}>ROČNÝ SÚHRN · JARVIS</Text>
            <View style={{ flex: 1 }} />
            <Pressable testID="tr-summarize" onPress={genSummary} disabled={sumBusy} style={st.sumBtn}>
              {sumBusy ? <ActivityIndicator size="small" color={C.onInverse} /> : <Text style={st.sumBtnText}>{summary ? 'OBNOVIŤ' : 'VYHODNOTIŤ'}</Text>}
            </Pressable>
          </View>
          {!!summary && <Text testID="tr-summary" style={st.sumText}>{summary}</Text>}
          {!summary && <Text style={st.sumHint}>Jarvis vyhodnotí trendy a dá jedno praktické odporúčanie.</Text>}
        </View>

        {/* LEGENDA */}
        <View style={st.legend}>
          {KEYS.map(k => (
            <View key={k} style={st.legendItem}>
              <View style={[st.legendDot, { backgroundColor: CATS[k].color }]} />
              <Text style={st.legendText}>{CATS[k].label}</Text>
            </View>
          ))}
        </View>

        {/* ROČNÉ STĹPCE */}
        {!data && <ActivityIndicator color={C.brand} style={{ marginTop: 30 }} />}
        {data && years.length === 0 && <Text style={st.hint}>Žiadne záznamy. Pridajte ich do Karty života a trendy sa vykreslia.</Text>}
        {[...years].reverse().map((y: any) => (
          <View key={y.year} testID={`tr-year-${y.year}`} style={st.yearRow}>
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <Text style={st.yearLabel}>{y.year}</Text>
              <View style={st.barTrack}>
                <View style={{ flexDirection: 'row', width: `${Math.max(6, (y.total / maxTotal) * 100)}%`, height: '100%', borderRadius: 6, overflow: 'hidden' }}>
                  {KEYS.filter(k => y.counts[k] > 0).map(k => (
                    <View key={k} style={{ flex: y.counts[k], backgroundColor: CATS[k].color }} />
                  ))}
                </View>
              </View>
              <Text style={st.yearTotal}>{y.total}×</Text>
            </View>
            <Text style={st.yearBreakdown}>
              {KEYS.filter(k => y.counts[k] > 0).map(k => `${y.counts[k]}× ${CATS[k].label.toLowerCase()}`).join(' · ') || '—'}
            </Text>
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 14 },
  h1: { fontSize: 24, fontWeight: '900', color: C.fg },
  sub: { marginTop: S.sm, fontSize: 13, color: C.onS3, lineHeight: 19 },
  err: { color: C.error, marginTop: S.md, fontSize: 12 },
  sumBox: { marginTop: S.lg, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md },
  sumTitle: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 2 },
  sumBtn: { backgroundColor: C.brand, borderRadius: R.pill, paddingHorizontal: 14, minHeight: 32, alignItems: 'center', justifyContent: 'center' },
  sumBtnText: { color: C.onInverse, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  sumText: { color: C.fg, fontSize: 13.5, lineHeight: 20, marginTop: S.md },
  sumHint: { color: C.info, fontSize: 11, marginTop: S.sm },
  legend: { flexDirection: 'row', flexWrap: 'wrap', gap: S.md, marginTop: S.lg },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  legendDot: { width: 9, height: 9, borderRadius: 5 },
  legendText: { color: C.onS3, fontSize: 10.5, fontWeight: '700' },
  hint: { marginTop: S.lg, color: C.onS3, fontSize: 12 },
  yearRow: { marginTop: S.md, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.md },
  yearLabel: { color: C.fg, fontWeight: '900', fontSize: 15, width: 52 },
  barTrack: { flex: 1, height: 16, backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: 6, justifyContent: 'center' },
  yearTotal: { color: C.brand, fontWeight: '900', fontSize: 13, width: 40, textAlign: 'right' },
  yearBreakdown: { color: C.info, fontSize: 11, marginTop: 6, marginLeft: 52 },
});
