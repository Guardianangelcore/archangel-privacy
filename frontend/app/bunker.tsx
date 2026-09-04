/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// BUNKER MODULE — F1 Bunker Locator (nearest shelters / bunkers, OpenStreetMap) · F2 72-hour
// checklist (water, food, meds, documents, communication). Sentinel+ or one-off €1.99.
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, ActivityIndicator, Linking, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';
import { useUserType } from '@/src/user-type';
import { tap, GoldButton } from '@/src/ui/glass';
import OsmMap from '@/src/ui/OsmMap';
import FeatureGate from '@/src/FeatureGate';
import { locateDevice } from '@/src/geo';

const CHECK_KEY = 'bunker.checklist.v1';
const CHECKLIST: { cat: string; icon: string; items: string[] }[] = [
  { cat: 'WATER', icon: 'water', items: ['3 l per person per day (9 l / 72 h)', 'Purification tablets or filter', 'Collapsible containers'] },
  { cat: 'FOOD', icon: 'nutrition', items: ['Ready-to-eat food for 72 h', 'Manual can opener', 'Baby / special diet food', 'Pet food'] },
  { cat: 'MEDS', icon: 'medkit', items: ['7-day supply of prescriptions', 'First-aid kit + tourniquet', 'Iodine tablets (if advised)', 'Copies of prescriptions'] },
  { cat: 'DOCUMENTS', icon: 'document-text', items: ['ID, passport, insurance card', 'Health Card export / Emergency QR', 'Cash in small notes', 'Keys, contact list on paper'] },
  { cat: 'COMMUNICATION', icon: 'radio', items: ['Battery / crank radio (FM)', 'Power bank ≥ 20 000 mAh', 'Whistle, flashlight, spare batteries', 'Offline Mesh enabled on phones'] },
];

export default function Bunker() {
  return (
    <SafeAreaView style={st.root} edges={['top', 'bottom']}>
      <Head title="BUNKER" />
      <ScrollView contentContainerStyle={st.body}>
        <FeatureGate feature="bunker" message="Bunker Locator & 72-hour checklist are part of the Sentinel plan.">
          <BunkerBody />
        </FeatureGate>
      </ScrollView>
    </SafeAreaView>
  );
}

function Head({ title }: { title: string }) {
  const router = useRouter();
  return (
    <View style={st.head}>
      <Pressable testID="bk-back" onPress={() => router.back()} hitSlop={10} style={st.back}><Ionicons name="chevron-back" size={22} color={C.brand} /></Pressable>
      <Text style={st.title}>{title}</Text>
    </View>
  );
}

function BunkerBody() {
  const { fs } = useUserType();
  const [tab, setTab] = useState<'map' | 'list'>('map');
  const [center, setCenter] = useState<{ lat: number; lng: number } | null>(null);
  const [results, setResults] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [done, setDone] = useState<Record<string, boolean>>({});

  useEffect(() => { AsyncStorage.getItem(CHECK_KEY).then(v => { if (v) setDone(JSON.parse(v)); }).catch(() => {}); }, []);
  const toggle = (k: string) => { tap('light'); const n = { ...done, [k]: !done[k] }; setDone(n); AsyncStorage.setItem(CHECK_KEY, JSON.stringify(n)).catch(() => {}); };

  const locate = async () => {
    try {
      const res = await locateDevice({ askPermission: true });
      if (res.source === 'gps') {
        const pos = await Location.getLastKnownPositionAsync({}) || await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
        if (pos) return { lat: pos.coords.latitude, lng: pos.coords.longitude };
      }
    } catch {}
    try { const g: any = await api('/geo/context'); if (typeof g?.geo?.lat === 'number') return { lat: g.geo.lat, lng: g.geo.lng }; } catch {}
    return null;
  };
  const search = useCallback(async () => {
    setBusy(true); setErr('');
    try {
      let pos = center; if (!pos) { pos = await locate(); if (pos) setCenter(pos); }
      const r: any = await api(`/nearby/care?kind=shelter&radius=15000${pos ? `&lat=${pos.lat}&lng=${pos.lng}` : ''}`);
      setResults(r.results || []); if (!pos && r.center) setCenter(r.center);
    } catch (e: any) { setErr(String(e.message || e).replace(/^\d+:\s*/, '')); }
    finally { setBusy(false); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [center]);
  useEffect(() => { search(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const total = CHECKLIST.reduce((n, c) => n + c.items.length, 0);
  const ok = Object.values(done).filter(Boolean).length;
  const navigate = (p: any) => Linking.openURL(Platform.OS === 'ios' ? `maps://?daddr=${p.lat},${p.lng}` : `geo:${p.lat},${p.lng}?q=${p.lat},${p.lng}(${encodeURIComponent(p.name)})`);

  return (
    <>
      <View style={st.tabs}>
        <Pressable testID="bk-tab-map" onPress={() => setTab('map')} style={[st.tab, tab === 'map' && st.tabOn]}><Ionicons name="map" size={14} color={tab === 'map' ? C.onInverse : C.brand} /><Text style={[st.tabText, tab === 'map' && { color: C.onInverse }]}>LOCATOR</Text></Pressable>
        <Pressable testID="bk-tab-list" onPress={() => setTab('list')} style={[st.tab, tab === 'list' && st.tabOn]}><Ionicons name="checkbox" size={14} color={tab === 'list' ? C.onInverse : C.brand} /><Text style={[st.tabText, tab === 'list' && { color: C.onInverse }]}>72 H CHECKLIST · {ok}/{total}</Text></Pressable>
      </View>
      {tab === 'map' && (
        <>
          {center && <OsmMap testID="bk-map" center={center} accent="#40E0D0" height={260} pins={results.slice(0, 30).map(p => ({ lat: p.lat, lng: p.lng, label: p.name }))} />}
          <GoldButton testID="bk-refresh" title="FIND NEAREST SHELTERS" icon="locate" onPress={search} loading={busy} />
          {!!err && <Text style={st.err}>{err}</Text>}
          {!busy && results.length === 0 && !err && <Text style={st.hint}>No mapped shelter within 15 km. In an emergency: basements, underground garages and metro stations count as improvised shelters.</Text>}
          {results.slice(0, 20).map((p, i) => (
            <Pressable key={i} testID={`bk-shelter-${i}`} onPress={() => navigate(p)} style={st.row}>
              <Ionicons name="home" size={20} color="#40E0D0" />
              <View style={{ flex: 1 }}><Text style={[st.rowTitle, { fontSize: fs(14) }]}>{p.name}</Text><Text style={st.rowSub}>{p.address || ''} {p.distance_km != null ? `· ${p.distance_km.toFixed(1)} km` : ''}</Text></View>
              <Ionicons name="navigate" size={18} color={C.brand} />
            </Pressable>
          ))}
        </>
      )}
      {tab === 'list' && CHECKLIST.map(c => (
        <View key={c.cat} style={st.cat}>
          <View style={st.catHead}><Ionicons name={c.icon as any} size={18} color={C.brand} /><Text style={st.catTitle}>{c.cat}</Text></View>
          {c.items.map(it => { const k = `${c.cat}:${it}`; return (
            <Pressable key={k} testID={`bk-item-${c.cat}-${c.items.indexOf(it)}`} onPress={() => toggle(k)} style={st.item}>
              <Ionicons name={done[k] ? 'checkbox' : 'square-outline'} size={24} color={done[k] ? C.accent : C.info} />
              <Text style={[st.itemText, { fontSize: fs(13) }, done[k] && { color: C.info, textDecorationLine: 'line-through' }]}>{it}</Text>
            </Pressable>); })}
        </View>
      ))}
    </>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  head: { flexDirection: 'row', alignItems: 'center', gap: S.sm, paddingHorizontal: S.md, minHeight: 52 },
  back: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  title: { color: C.brand, fontWeight: '900', letterSpacing: 3, fontSize: 16 },
  body: { padding: S.lg, gap: S.md, paddingBottom: S.xxxl },
  tabs: { flexDirection: 'row', gap: S.sm },
  tab: { flex: 1, flexDirection: 'row', gap: 6, alignItems: 'center', justifyContent: 'center', minHeight: 44, borderWidth: 1, borderColor: 'rgba(212,175,55,0.45)', borderRadius: R.sm },
  tabOn: { backgroundColor: C.brand, borderColor: C.brand },
  tabText: { color: C.brand, fontWeight: '900', fontSize: 10, letterSpacing: 1.2 },
  err: { color: C.error, fontWeight: '800', fontSize: 12 },
  hint: { color: C.info, fontSize: 12, lineHeight: 18 },
  row: { flexDirection: 'row', alignItems: 'center', gap: S.md, padding: S.md, minHeight: 56, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, backgroundColor: C.surface2 },
  rowTitle: { color: C.fg, fontWeight: '800' },
  rowSub: { color: C.info, fontSize: 11, marginTop: 2 },
  cat: { borderWidth: 1, borderColor: C.border, borderRadius: R.md, padding: S.md, gap: 4, backgroundColor: C.surface2 },
  catHead: { flexDirection: 'row', alignItems: 'center', gap: S.sm, marginBottom: 4 },
  catTitle: { color: C.brand, fontWeight: '900', letterSpacing: 2, fontSize: 11 },
  item: { flexDirection: 'row', alignItems: 'center', gap: S.md, minHeight: 48 },
  itemText: { color: C.fg, flex: 1, lineHeight: 19 },
});
