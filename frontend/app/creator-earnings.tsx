/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// CREATOR EARNINGS — 5 % royalty from every GA-T sale and pay-per-feature purchase (creator/admin only).
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, RefreshControl, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';

export default function CreatorEarnings() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    setBusy(true); setErr('');
    try { setData(await api('/creator/earnings')); } catch (e: any) { setErr(String(e.message || e).replace(/^\d+:\s*/, '')); }
    finally { setBusy(false); }
  }, []);
  useEffect(() => { load(); }, [load]);
  return (
    <SafeAreaView style={st.root} edges={['top', 'bottom']}>
      <View style={st.head}>
        <Pressable testID="ce-back" onPress={() => router.back()} hitSlop={10} style={st.back}><Ionicons name="chevron-back" size={22} color={C.brand} /></Pressable>
        <Text style={st.title}>CREATOR EARNINGS</Text>
      </View>
      <ScrollView contentContainerStyle={st.body} refreshControl={<RefreshControl refreshing={busy} onRefresh={load} tintColor={C.brand} />}>
        {!!err && <Text style={st.err}>{err}</Text>}
        {!data && !err && <ActivityIndicator color={C.brand} />}
        {data && (
          <>
            <View style={st.cards}>
              <View style={st.card}><Text style={st.num}>{data.total_gat.toFixed(2)}</Text><Text style={st.lbl}>GA-T EARNED</Text></View>
              <View style={st.card}><Text style={st.num}>€{data.total_eur.toFixed(2)}</Text><Text style={st.lbl}>EUR EARNED</Text></View>
              <View style={st.card}><Text style={st.num}>{Math.round(data.rate * 100)}%</Text><Text style={st.lbl}>ROYALTY RATE</Text></View>
            </View>
            <Text style={st.section}>TRANSACTION LOG · {data.count}</Text>
            {data.log.length === 0 && <Text style={st.lbl}>No royalty events yet.</Text>}
            {data.log.map((r: any) => (
              <View key={r.royalty_id} testID="ce-row" style={st.row}>
                <Ionicons name={r.currency === 'gat' ? 'diamond' : 'card'} size={18} color={C.brand} />
                <View style={{ flex: 1 }}>
                  <Text style={st.rowTitle}>{r.source === 'gat_sale' ? 'GA-T sale' : 'Pay-per-feature'} · {r.meta?.feature || r.meta?.item || ''}</Text>
                  <Text style={st.rowSub}>{String(r.at).slice(0, 16).replace('T', ' ')} · gross {r.gross} {r.currency.toUpperCase()}</Text>
                </View>
                <Text style={st.cut}>+{r.cut} {r.currency === 'gat' ? 'GA-T' : '€'}</Text>
              </View>
            ))}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  head: { flexDirection: 'row', alignItems: 'center', gap: S.sm, paddingHorizontal: S.md, minHeight: 52 },
  back: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  title: { color: C.brand, fontWeight: '900', letterSpacing: 3, fontSize: 16 },
  body: { padding: S.lg, gap: S.md, paddingBottom: S.xxxl },
  err: { color: C.error, fontWeight: '800' },
  cards: { flexDirection: 'row', gap: S.sm },
  card: { flex: 1, padding: S.md, borderWidth: 1, borderColor: 'rgba(212,175,55,0.45)', borderRadius: R.md, alignItems: 'center', gap: 4, backgroundColor: 'rgba(212,175,55,0.06)' },
  num: { color: C.brand, fontWeight: '900', fontSize: 18 },
  lbl: { color: C.info, fontSize: 9, fontWeight: '900', letterSpacing: 1.5 },
  section: { color: C.brand, fontWeight: '900', letterSpacing: 2.5, fontSize: 11, marginTop: S.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: S.md, padding: S.md, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, backgroundColor: C.surface2 },
  rowTitle: { color: C.fg, fontWeight: '800', fontSize: 13 },
  rowSub: { color: C.info, fontSize: 11, marginTop: 2 },
  cut: { color: C.accent, fontWeight: '900' },
});
