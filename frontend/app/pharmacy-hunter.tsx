/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';

const STATUS_UI: any = {
  in_stock: { label: 'SKLADOM', color: '#5FA779' },
  low_stock: { label: 'POSLEDNÉ KUSY', color: '#E6A23C' },
  out_of_stock: { label: 'VYPREDANÉ', color: '#C25450' },
};

export default function PharmacyHunter() {
  const router = useRouter();
  const [med, setMed] = useState('');
  const [region, setRegion] = useState<'SK' | 'CZ'>('CZ');
  const [results, setResults] = useState<any[]>([]);
  const [watches, setWatches] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [scanBusy, setScanBusy] = useState<string | null>(null);
  const [err, setErr] = useState('');

  // Geographic Fluidity — region follows the user's geo context (Prague/CZ default)
  useEffect(() => {
    (async () => {
      try {
        const g: any = await api('/geo/context');
        if (g?.geo?.country === 'CZ' || g?.geo?.country === 'SK') setRegion(g.geo.country);
      } catch {}
    })();
  }, []);

  const loadWatches = async () => {
    try { setWatches(await api('/pharmacy/watches')); } catch {}
  };
  useEffect(() => { loadWatches(); }, []);

  const search = async () => {
    if (!med.trim()) return;
    setBusy(true); setErr('');
    try {
      const res: any = await api(`/pharmacy/search?med=${encodeURIComponent(med.trim())}&region=${region}`);
      setResults(res.results || []);
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(false); }
  };

  const watch = async () => {
    if (!med.trim()) return;
    try {
      await api('/pharmacy/watch', { method: 'POST', body: JSON.stringify({ med_name: med.trim(), region }) });
      await loadWatches();
    } catch (e: any) { setErr(String(e.message || e)); }
  };

  const scan = async (id: string) => {
    setScanBusy(id);
    try { await api(`/pharmacy/watches/${id}/scan`, { method: 'POST' }); await loadWatches(); }
    catch (e: any) { setErr(String(e.message || e)); }
    finally { setScanBusy(null); }
  };

  const del = async (id: string) => {
    try { await api(`/pharmacy/watches/${id}`, { method: 'DELETE' }); await loadWatches(); } catch {}
  };

  return (
    <SafeAreaView testID="pharmacy-hunter-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="ph-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>PHARMACY HUNTER</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
        <View style={styles.demoBadge}>
          <Ionicons name="flask-outline" size={13} color={C.onWarn} />
          <Text style={styles.demoText}>DEMO DÁTA — reálne napojenie na sklady lekární sa pripravuje</Text>
        </View>
        <Text style={styles.h1}>Lovec liekov v lekárňach</Text>
        <Text style={styles.sub}>Skenovanie dostupnosti kritických liekov v sieťach lekární CZ/SK regiónu.</Text>

        <View style={styles.searchRow}>
          <TextInput
            testID="ph-input"
            style={styles.input}
            placeholder="Názov lieku (napr. Euthyrox)"
            placeholderTextColor={C.info}
            value={med}
            onChangeText={setMed}
            onSubmitEditing={search}
            returnKeyType="search"
          />
        </View>
        <View style={styles.chipRow}>
          {(['SK', 'CZ'] as const).map(r => (
            <Pressable key={r} testID={`ph-region-${r}`} onPress={() => setRegion(r)} style={[styles.chip, region === r && styles.chipActive]}>
              <Text style={[styles.chipText, region === r && { color: C.onInverse }]}>{r}</Text>
            </Pressable>
          ))}
          <Pressable testID="ph-search" onPress={search} disabled={busy} style={styles.searchBtn}>
            {busy ? <ActivityIndicator size="small" color={C.onInverse} /> : <Ionicons name="search" size={16} color={C.onInverse} />}
            <Text style={styles.searchBtnText}>HĽADAŤ</Text>
          </Pressable>
          <Pressable testID="ph-watch" onPress={watch} style={styles.watchBtn}>
            <Ionicons name="eye-outline" size={16} color={C.brand} />
            <Text style={styles.watchBtnText}>SLEDOVAŤ</Text>
          </Pressable>
        </View>
        {!!err && <Text style={styles.err}>{err}</Text>}

        {results.length > 0 && (
          <>
            <Text style={styles.section}>DOSTUPNOSŤ · {region}</Text>
            {results.map((r, i) => {
              const ui = STATUS_UI[r.status] || STATUS_UI.out_of_stock;
              return (
                <View key={i} style={styles.resRow}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.resName}>{r.pharmacy} · {r.city}</Text>
                    <Text style={styles.resSub}>
                      {r.price_eur != null ? `${r.price_eur} €` : '—'}{r.pieces ? ` · ${r.pieces} ks` : ''}
                    </Text>
                  </View>
                  <View style={[styles.statusPill, { borderColor: ui.color }]}>
                    <Text style={[styles.statusText, { color: ui.color }]}>{ui.label}</Text>
                  </View>
                </View>
              );
            })}
          </>
        )}

        <Text style={styles.section}>MOJE SLEDOVANIA ({watches.length})</Text>
        {watches.length === 0 && <Text style={styles.hint}>Zatiaľ nič nesledujete. Zadajte liek a ťuknite SLEDOVAŤ.</Text>}
        {watches.map(w => (
          <View key={w.watch_id} style={styles.watchRow}>
            <View style={{ flex: 1 }}>
              <Text style={styles.resName}>{w.med_name} · {w.region}</Text>
              <Text style={styles.resSub}>
                {w.status === 'found' ? `✓ Nájdené: ${w.found_pharmacy || ''}` : 'Sledujem dostupnosť…'}
              </Text>
            </View>
            <Pressable testID={`ph-scan-${w.watch_id}`} onPress={() => scan(w.watch_id)} disabled={scanBusy === w.watch_id} style={styles.scanBtn}>
              {scanBusy === w.watch_id ? <ActivityIndicator size="small" color={C.onInverse} /> : <Text style={styles.scanText}>SKEN</Text>}
            </Pressable>
            <Pressable testID={`ph-del-${w.watch_id}`} onPress={() => del(w.watch_id)} hitSlop={8}>
              <Ionicons name="trash-outline" size={18} color={C.info} />
            </Pressable>
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 14 },
  demoBadge: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: C.warn, borderRadius: R.sm, paddingHorizontal: S.md, paddingVertical: 6, marginBottom: S.lg },
  demoText: { color: C.onWarn, fontWeight: '800', fontSize: 9.5, flex: 1 },
  h1: { fontSize: 24, fontWeight: '900', color: C.fg },
  sub: { marginTop: S.sm, fontSize: 13, color: C.onS3, lineHeight: 19 },
  searchRow: { marginTop: S.xl },
  input: { backgroundColor: C.surface2, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, color: C.fg, paddingHorizontal: S.lg, minHeight: 50, fontSize: 14 },
  chipRow: { flexDirection: 'row', alignItems: 'center', gap: S.sm, marginTop: S.md },
  chip: { borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.pill, paddingHorizontal: S.lg, paddingVertical: 10 },
  chipActive: { backgroundColor: C.brand, borderColor: C.brand },
  chipText: { color: C.fg, fontWeight: '800', fontSize: 12 },
  searchBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: C.brand, borderRadius: R.sm, paddingHorizontal: S.md, minHeight: 44, justifyContent: 'center' },
  searchBtnText: { color: C.onInverse, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  watchBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, borderWidth: 1.5, borderColor: C.brand, borderRadius: R.sm, paddingHorizontal: S.md, minHeight: 44, justifyContent: 'center' },
  watchBtnText: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  section: { marginTop: S.xl, marginBottom: S.sm, fontSize: 11, letterSpacing: 2, color: C.info, fontWeight: '800' },
  resRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.md, marginBottom: S.sm },
  resName: { color: C.fg, fontWeight: '800', fontSize: 13 },
  resSub: { color: C.info, fontSize: 11, marginTop: 2 },
  statusPill: { borderWidth: 1.5, borderRadius: R.pill, paddingHorizontal: S.md, paddingVertical: 4 },
  statusText: { fontWeight: '900', fontSize: 9.5, letterSpacing: 0.5 },
  watchRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.md, marginBottom: S.sm },
  scanBtn: { backgroundColor: C.brand, borderRadius: R.sm, paddingHorizontal: S.md, minHeight: 40, alignItems: 'center', justifyContent: 'center' },
  scanText: { color: C.onInverse, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  hint: { color: C.onS3, fontSize: 12, lineHeight: 18 },
  err: { color: C.error, marginTop: S.md, fontSize: 12 },
});
