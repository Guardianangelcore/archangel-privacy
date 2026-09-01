/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// Offline Survival Compass — offline-cached survival pack (ICE, meds, ePN/neschopenka,
// vaccinations, guardians) + Bio-Beacon + Satellite Nano-Packet emergency handshake
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, ActivityIndicator, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import Art50 from '@/src/Art50';
import { C, S } from '@/src/theme';
import { Lang } from '@/src/i18n';

const KEY = 'gh_compass_pack';

async function getLoc(): Promise<{ lat: number | null; lng: number | null }> {
  try {
    if (Platform.OS !== 'web') {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status === 'granted') {
        const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
        return { lat: pos.coords.latitude, lng: pos.coords.longitude };
      }
    }
  } catch {}
  return { lat: null, lng: null };
}

export default function Compass() {
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'en';
  const router = useRouter();
  const [pack, setPack] = useState<any>(null);
  const [offline, setOffline] = useState(false);
  const [beacon, setBeacon] = useState<any>(null);
  const [sat, setSat] = useState<any[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState('');
  const [bearing, setBearing] = useState<any>(null);

  const loadBearing = useCallback(async () => {
    try {
      const loc = await getLoc();
      if (loc.lat == null || loc.lng == null) return;
      const r: any = await api('/compass/bearing', { method: 'POST', body: JSON.stringify(loc) });
      setBearing(r);
    } catch {}
  }, []);

  const load = useCallback(async () => {
    try {
      const p: any = await api('/compass/pack');
      setPack(p); setOffline(false);
      await AsyncStorage.setItem(KEY, JSON.stringify(p));
      const [b, q] = await Promise.all([api('/bio-beacon/status'), api('/satellite/queue')]);
      setBeacon((b as any).beacon); setSat((q as any).queue || []);
    } catch {
      const cached = await AsyncStorage.getItem(KEY);
      if (cached) { setPack(JSON.parse(cached)); setOffline(true); }
    }
  }, []);
  useEffect(() => { load(); loadBearing(); }, [load, loadBearing]);

  const toggleBeacon = async () => {
    setBusy('beacon'); setMsg('');
    try {
      if (beacon) {
        await api('/bio-beacon/deactivate', { method: 'POST' });
        setBeacon(null); setMsg('Bio-Beacon deactivated.');
      } else {
        const loc = await getLoc();
        const b: any = await api('/bio-beacon/activate', { method: 'POST', body: JSON.stringify({ ...loc, note: 'compass' }) });
        setBeacon(b); setMsg('BIO-BEACON ACTIVE — guardians received your location and vitals.');
      }
    } catch (e: any) { setMsg(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const sendSat = async () => {
    setBusy('sat'); setMsg('');
    try {
      const loc = await getLoc();
      const p: any = await api('/satellite/nano-packet', { method: 'POST', body: JSON.stringify({ ...loc, note: 'SOS' }) });
      setSat(prev => [p, ...prev]);
      setMsg(`Nano-Packet (${p.packet_bytes} B) queued for satellite uplink — the Swarm will broadcast it.`);
    } catch (e: any) { setMsg(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const sl = pack?.sick_leave;
  const vac = pack?.vaccinations;

  return (
    <SafeAreaView testID="compass-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="cp-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={st.title}>SURVIVAL COMPASS</Text>
        <Pressable testID="cp-refresh" onPress={load} hitSlop={12}>
          <Ionicons name="refresh" size={22} color={C.onInverse} />
        </Pressable>
      </View>

      {offline && <View style={st.offBanner}><Text style={st.offText}>OFFLINE MODE · SHOWING CACHED PACK · {pack?.generated_at?.slice(0, 16).replace('T', ' ')}</Text></View>}

      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        {!pack ? <ActivityIndicator color={C.brand} style={{ marginTop: 40 }} /> : (
          <>
            {/* BIO-BEACON */}
            <Pressable testID="cp-beacon" onPress={toggleBeacon} disabled={busy === 'beacon'}
              style={[st.beaconBtn, beacon && { backgroundColor: C.error }]}>
              {busy === 'beacon' ? <ActivityIndicator color={C.onError} /> : <>
                <Ionicons name={beacon ? 'radio' : 'radio-outline'} size={22} color={beacon ? C.onError : C.brand} />
                <Text style={[st.beaconText, beacon && { color: C.onError }]}>
                  {beacon ? 'BIO-BEACON BROADCASTING — TURN OFF' : 'ACTIVATE BIO-BEACON (EMERGENCY)'}
                </Text>
              </>}
            </Pressable>
            {beacon && <Text style={st.beaconMeta}>Pings: {beacon.pings} · pulse: {beacon.vitals?.heart_rate ?? '—'} · expires in 24 h · guardians watching</Text>}

            {/* SOVEREIGN COMPASS BEARING */}
            {bearing && (
              <View testID="cp-bearing" style={st.bearingBox}>
                <View style={st.bearingHead}>
                  <Ionicons name="compass" size={16} color={C.brand} />
                  <Text style={st.bearingTitle}>SOVEREIGN COMPASS — GPS ACTIVE</Text>
                  <Pressable testID="cp-bearing-refresh" onPress={loadBearing} hitSlop={8}>
                    <Ionicons name="refresh" size={16} color={C.brand} />
                  </Pressable>
                </View>
                {!!bearing.nearest_safe_city && (
                  <Text style={st.bearingLine}>NEAREST SAFE CITY · {bearing.nearest_safe_city.label} · {bearing.nearest_safe_city.direction} · {bearing.nearest_safe_city.distance_km} km</Text>
                )}
                {(bearing.beacons || []).length > 0 && bearing.beacons.map((b: any, i: number) => (
                  <Text key={`b${i}`} style={[st.bearingLine, { color: C.error }]}>🚨 {b.label} — {b.direction} · {b.distance_km} km</Text>
                ))}
                {(bearing.waitlist_proximity || []).slice(0, 3).map((w: any, i: number) => (
                  <Text key={`w${i}`} style={st.bearingLine}>📅 {w.label} — {w.direction} · {w.distance_km} km</Text>
                ))}
              </View>
            )}

            {/* SATELLITE */}
            <Pressable testID="cp-sat" onPress={sendSat} disabled={busy === 'sat'} style={st.satBtn}>
              {busy === 'sat' ? <ActivityIndicator color={C.onInverse} /> : <>
                <Ionicons name="planet-outline" size={20} color={C.onInverse} />
                <Text style={st.satText}>SATELLITE SOS — SEND NANO-PACKET</Text>
              </>}
            </Pressable>
            <Text style={st.satNote}>With no signal, Jarvis compresses critical data into a ~100 B packet for Starlink/Globalstar (SIMULATION — protocol placeholder).</Text>
            {sat.slice(0, 3).map(p => (
              <View key={p.packet_id} style={st.satRow}>
                <Ionicons name={p.status === 'broadcasted' ? 'checkmark-circle' : 'time-outline'} size={16} color={p.status === 'broadcasted' ? C.brand : C.warn} />
                <Text style={st.satRowText}>{p.packet_bytes} B · {p.status === 'broadcasted' ? 'BROADCASTED' : 'QUEUED'} · {p.protocol?.split(' ')[0]}</Text>
              </View>
            ))}
            {!!msg && <Text testID="cp-msg" style={st.msg}>{msg}</Text>}

            {/* ICE */}
            <Section title="IDENTITA · ICE">
              <Row lbl="MENO" val={pack.identity?.name || '—'} />
              <Row lbl="BLOOD TYPE" val={pack.identity?.blood_type || '—'} />
              <Row lbl="ALERGIE" val={pack.identity?.allergies || '—'} />
              <Row lbl="DIAGNOSES" val={pack.identity?.conditions || '—'} />
              <Row lbl="KONTAKT" val={`${pack.emergency_contact?.name || '—'} · ${pack.emergency_contact?.phone || '—'}`} />
            </Section>

            {/* MEDS */}
            <Section title="LIEKY DNES">
              {(pack.meds_today || []).length ? pack.meds_today.map((m: any, i: number) => (
                <Row key={i} lbl={m.time} val={`${m.name} — ${m.dose}`} />
              )) : <Text style={st.emptyLine}>— no medication reminders</Text>}
            </Section>

            {/* NESCHOPENKA / ePN */}
            <Section title="SICK LEAVE (ePN) · OUTINGS" testID="cp-sickleave">
              {sl?.active ? (
                <>
                  <Row lbl="STAV" val={`ACTIVE SICK LEAVE from ${sl.start_date}${sl.end_date ? ` to ${sl.end_date}` : ''}`} />
                  <Row lbl="CONTRACT" val={(sl.contract_type || 'fulltime').toUpperCase()} />
                  <Row lbl="PERMITTED OUTINGS" val={(sl.outings || []).map((o: any) => `${o.from_time}–${o.to_time}`).join(' · ') || 'no outings'} />
                  <Text style={st.warnLine}>⚠ Stay home outside outing windows — social insurance inspections.</Text>
                </>
              ) : <Text style={st.emptyLine}>— no active sick leave (manage in My Recovery)</Text>}
            </Section>

            {/* OČKOVANIA */}
            <Section title="VACCINATIONS · BOOSTERS" testID="cp-vaccines">
              {(vac?.booster_alerts || []).map((b: any, i: number) => (
                <Text key={`b${i}`} style={st.warnLine}>⚠ {b.title} — booster due by {b.booster_due}</Text>
              ))}
              {(vac?.history || []).length ? vac.history.map((v: any, i: number) => (
                <Row key={i} lbl={v.date} val={`${v.title}${v.booster_due ? ` (booster ${v.booster_due})` : ''}`} />
              )) : <Text style={st.emptyLine}>— no records (add in Health Timeline)</Text>}
            </Section>

            {/* GUARDIANS + NUMBERS */}
            <Section title="GUARDIANS">
              {(pack.guardians || []).length ? pack.guardians.map((g: any, i: number) => (
                <Row key={i} lbl={`#${i + 1}`} val={`${g.guardian_name} · ${g.guardian_email}`} />
              )) : <Text style={st.emptyLine}>— add guardians in Sovereign Recovery</Text>}
            </Section>
            <Section title="EMERGENCY NUMBERS">
              {Object.entries(pack.emergency_numbers || {}).map(([k, v]) => <Row key={k} lbl={k.toUpperCase()} val={String(v)} />)}
            </Section>
            <Section title="SURVIVAL HANDBOOK">
              {(pack.survival_guide || []).map((s: string, i: number) => (
                <Text key={i} style={st.tip}>{i + 1}.  {s}</Text>
              ))}
            </Section>

            <Art50 lang={lang} />
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function Section({ title, children, testID }: any) {
  return (
    <View testID={testID} style={st.section}>
      <Text style={st.sectionTitle}>{title}</Text>
      <View style={st.sectionBody}>{children}</View>
    </View>
  );
}
function Row({ lbl, val }: any) {
  return (
    <View style={st.rowKV}>
      <Text style={st.rowLbl}>{lbl}</Text>
      <Text style={st.rowVal}>{val}</Text>
    </View>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  offBanner: { backgroundColor: C.warn, paddingVertical: 6, alignItems: 'center' },
  offText: { color: C.onWarn, fontWeight: '900', letterSpacing: 1, fontSize: 9 },
  beaconBtn: { flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: C.error, paddingVertical: S.lg, minHeight: 56, backgroundColor: C.surface2 },
  beaconText: { color: C.brand, fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  beaconMeta: { color: C.error, fontWeight: '800', fontSize: 10, letterSpacing: 1, marginTop: 6, textAlign: 'center' },
  satBtn: { marginTop: S.md, flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, paddingVertical: S.lg, minHeight: 52 },
  satText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  satNote: { color: C.info, fontSize: 10, lineHeight: 15, marginTop: 6 },
  satRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 6 },
  satRowText: { color: C.onS3, fontSize: 11, fontWeight: '800', letterSpacing: 0.5 },
  bearingBox: { marginTop: S.md, borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, backgroundColor: C.surface2, borderRadius: 8 },
  bearingHead: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6 },
  bearingTitle: { color: C.brand, fontSize: 10.5, fontWeight: '900', letterSpacing: 1.5, flex: 1 },
  bearingLine: { color: C.fg, fontSize: 11, fontWeight: '700', marginTop: 3, letterSpacing: 0.3 },
  msg: { color: C.brand, fontWeight: '800', fontSize: 12, marginTop: S.md, lineHeight: 17 },
  section: { borderWidth: 1.5, borderColor: C.borderStrong, marginTop: S.lg },
  sectionTitle: { backgroundColor: C.inverse, color: C.onInverse, padding: S.md, fontWeight: '900', letterSpacing: 2, fontSize: 12 },
  sectionBody: { padding: S.md },
  rowKV: { flexDirection: 'row', gap: S.md, paddingVertical: 4 },
  rowLbl: { fontSize: 10, fontWeight: '800', letterSpacing: 1, color: C.info, width: 110 },
  rowVal: { flex: 1, color: C.fg, fontSize: 13, lineHeight: 18 },
  emptyLine: { color: C.info, fontSize: 12, fontStyle: 'italic' },
  warnLine: { color: C.warn, fontSize: 12, fontWeight: '800', marginVertical: 3, lineHeight: 17 },
  tip: { color: C.fg, fontSize: 13, marginVertical: 3, lineHeight: 19 },
});
