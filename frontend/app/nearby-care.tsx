/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// NEARBY CARE — GPS locator: pharmacies · doctors/GP · emergency. OpenStreetMap (keyless).
// Guardian+ only (Sovereign sees the paywall). Location: device GPS (locateDevice) → stored geo fallback.
import React, { useEffect, useMemo, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator, Linking, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import * as Location from 'expo-location';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';
import { tap } from '@/src/ui/glass';
import { locateDevice } from '@/src/geo';
import Paywall from '@/src/Paywall';
import OsmMap from '@/src/ui/OsmMap';

type Kind = 'pharmacy' | 'doctor' | 'emergency';
type Place = { id: string; name: string; lat: number; lng: number; distance_km: number; opening_hours: string; phone: string; address: string; emergency: boolean };

const KIND_UI: Record<Kind, { icon: any; color: string; key: string }> = {
  pharmacy: { icon: 'medkit-outline', color: '#5FA779', key: 'nearby_care.pharmacy' },
  doctor: { icon: 'person-outline', color: '#7C6CFF', key: 'nearby_care.doctor_gp' },
  emergency: { icon: 'alert-circle-outline', color: '#FF453A', key: 'nearby_care.emergency' },
};

export default function NearbyCare() {
  const { t: tt } = useI18n();
  const router = useRouter();
  const [kind, setKind] = useState<Kind>('pharmacy');
  const [center, setCenter] = useState<{ lat: number; lng: number } | null>(null);
  const [results, setResults] = useState<Place[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [locked, setLocked] = useState(false);
  const [locSource, setLocSource] = useState<'gps' | 'ip' | 'saved' | ''>('');

  // Proactive tier check (Sovereign → paywall), then resolve GPS once.
  useEffect(() => {
    api<any>('/subscription').then(s => setLocked(s?.tier === 'sovereign')).catch(() => {});
  }, []);

  const locate = async (): Promise<{ lat: number; lng: number } | null> => {
    try {
      const res = await locateDevice({ askPermission: true });
      if (res.source === 'gps') {
        const pos = await Location.getLastKnownPositionAsync({}) || await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
        if (pos) { setLocSource('gps'); return { lat: pos.coords.latitude, lng: pos.coords.longitude }; }
      }
      setLocSource(res.source === 'ip' ? 'ip' : 'saved');
    } catch {}
    try {
      const g: any = await api('/geo/context');
      if (typeof g?.geo?.lat === 'number') return { lat: g.geo.lat, lng: g.geo.lng };
    } catch {}
    return null;
  };

  const search = async (k: Kind, c?: { lat: number; lng: number } | null) => {
    setBusy(true); setErr('');
    try {
      let pos = c ?? center;
      if (!pos) { pos = await locate(); if (pos) setCenter(pos); }
      const q = pos ? `&lat=${pos.lat}&lng=${pos.lng}` : '';
      const res: any = await api(`/nearby/care?kind=${k}${q}`);
      setResults(res.results || []);
      if (!pos && res.center) setCenter(res.center);
    } catch (e: any) {
      const m = String(e?.message || e);
      if (/^402:/.test(m)) { setLocked(true); return; }
      setErr(m.replace(/^\d+:\s*/, ''));
    } finally { setBusy(false); }
  };

  useEffect(() => { if (!locked) search(kind); // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locked]);

  const pick = (k: Kind) => { tap('light'); setKind(k); setResults([]); search(k); };
  const refreshGps = async () => { tap('light'); setBusy(true); const p = await locate(); if (p) setCenter(p); await search(kind, p); };

  const ui = KIND_UI[kind];
  const pins = useMemo(() => results.slice(0, 15).map(r => ({ lat: r.lat, lng: r.lng, label: r.name, color: ui.color })), [results, ui.color]);

  const openDirections = (p: Place) => {
    tap('light');
    const url = Platform.OS === 'ios'
      ? `maps:0,0?q=${encodeURIComponent(p.name)}@${p.lat},${p.lng}`
      : `geo:${p.lat},${p.lng}?q=${p.lat},${p.lng}(${encodeURIComponent(p.name)})`;
    Linking.openURL(url).catch(() => Linking.openURL(`https://www.openstreetmap.org/?mlat=${p.lat}&mlon=${p.lng}#map=17/${p.lat}/${p.lng}`));
  };

  return (
    <SafeAreaView testID="nearby-care-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="nc-back" onPress={() => { tap(); router.back(); }} hitSlop={12}><Ionicons name="chevron-back" size={24} color={C.fg} /></Pressable>
        <Text style={st.title}>{tt('nearby_care.find_care_nearby')}</Text>
        <Pressable testID="nc-gps" onPress={refreshGps} hitSlop={12}><Ionicons name="locate-outline" size={22} color={C.brand} /></Pressable>
      </View>

      {locked ? (
        <View testID="nc-paywall" style={{ padding: S.lg }}>
          <Paywall tier="guardian" message={tt('nearby_care.find_care_nearby') + ' — Guardian Plan'} onUnlocked={() => setLocked(false)} />
        </View>
      ) : (
        <ScrollView contentContainerStyle={st.body}>
          {/* FILTERS */}
          <View style={st.filters}>
            {(Object.keys(KIND_UI) as Kind[]).map(k => {
              const on = k === kind; const u = KIND_UI[k];
              return (
                <Pressable key={k} testID={`nc-f-${k}`} onPress={() => pick(k)} style={[st.chip, on && { borderColor: u.color, backgroundColor: u.color + '22' }]}>
                  <Ionicons name={u.icon} size={16} color={on ? u.color : C.info} />
                  <Text style={[st.chipText, on && { color: u.color }]}>{tt(u.key)}</Text>
                </Pressable>
              );
            })}
          </View>

          {/* MAP */}
          {center && <OsmMap testID="nc-map" center={center} pins={pins} accent={ui.color} height={240} />}
          {!!locSource && (
            <Text style={st.src}>
              {locSource === 'gps' ? tt('nearby_care.device_gps') : locSource === 'ip' ? tt('nearby_care.approximate_network_location') : tt('nearby_care.saved_location')}
            </Text>
          )}

          {busy && <ActivityIndicator color={ui.color} style={{ marginTop: S.xl }} />}
          {!!err && <Text testID="nc-error" style={st.err}>{err}</Text>}
          {!busy && !err && results.length === 0 && <Text style={st.empty}>{tt('nearby_care.nothing_found_within_5_km')}</Text>}

          {/* LIST */}
          {results.map((p, i) => (
            <Pressable key={p.id} testID={`nc-item-${i}`} onPress={() => openDirections(p)} style={st.row}>
              <View style={[st.num, { backgroundColor: ui.color }]}><Text style={st.numText}>{i + 1}</Text></View>
              <View style={{ flex: 1 }}>
                <Text style={st.name} numberOfLines={1}>{p.name}</Text>
                {!!p.address && <Text style={st.sub} numberOfLines={1}>{p.address}</Text>}
                <Text style={st.hours} numberOfLines={1}>
                  {p.opening_hours ? `🕒 ${p.opening_hours}` : (p.emergency ? tt('nearby_care.24_7_emergency') : tt('nearby_care.hours_unknown'))}
                </Text>
              </View>
              <View style={{ alignItems: 'flex-end', gap: 4 }}>
                <Text style={[st.dist, { color: ui.color }]}>{p.distance_km < 1 ? `${Math.round(p.distance_km * 1000)} m` : `${p.distance_km.toFixed(1)} km`}</Text>
                {!!p.phone && (
                  <Pressable testID={`nc-call-${i}`} onPress={() => { tap('light'); Linking.openURL(`tel:${p.phone.replace(/\s+/g, '')}`); }} hitSlop={8}>
                    <Ionicons name="call-outline" size={18} color={C.info} />
                  </Pressable>
                )}
              </View>
            </Pressable>
          ))}
          <Text style={st.credit}>© OpenStreetMap contributors</Text>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', fontSize: 16, letterSpacing: 1 },
  body: { padding: S.lg, paddingBottom: S.xxxl, gap: S.md },
  filters: { flexDirection: 'row', gap: S.sm },
  chip: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, minHeight: 44, borderRadius: R.pill, borderWidth: 1, borderColor: C.border, backgroundColor: 'rgba(255,255,255,0.04)' },
  chipText: { color: C.info, fontWeight: '800', fontSize: 11, letterSpacing: 0.5 },
  src: { color: C.info, fontSize: 11, textAlign: 'center' },
  err: { color: C.error, textAlign: 'center', marginTop: S.md },
  empty: { color: C.info, textAlign: 'center', marginTop: S.xl },
  row: { flexDirection: 'row', alignItems: 'center', gap: S.md, padding: S.md, borderRadius: R.md, borderWidth: 1, borderColor: C.border, backgroundColor: 'rgba(255,255,255,0.04)', minHeight: 64 },
  num: { width: 28, height: 28, borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  numText: { color: '#fff', fontWeight: '900', fontSize: 12 },
  name: { color: C.fg, fontWeight: '800', fontSize: 14 },
  sub: { color: C.info, fontSize: 12, marginTop: 2 },
  hours: { color: C.brandSec, fontSize: 12, marginTop: 2 },
  dist: { fontWeight: '900', fontSize: 13 },
  credit: { color: C.info, fontSize: 10, textAlign: 'center', marginTop: S.md, opacity: 0.6 },
});
