/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// Environmental Threat Fusion — device sensors × P2P mesh hazard consensus
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, TextInput, ActivityIndicator, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import Art50 from '@/src/Art50';
import { C, S } from '@/src/theme';
import { Lang } from '@/src/i18n';

export default function Enviro() {
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const router = useRouter();
  const [threats, setThreats] = useState<any[]>([]);
  const [kinds, setKinds] = useState<Record<string, any>>({});
  const [kind, setKind] = useState('heat');
  const [severity, setSeverity] = useState(3);
  const [city, setCity] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d: any = await api('/enviro/threats');
      setThreats(d.threats || []); setKinds(d.kinds || {});
    } catch (e: any) { setErr(String(e.message || e)); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const report = async () => {
    setBusy(true); setErr(''); setMsg('');
    try {
      await api('/enviro/report', { method: 'POST', body: JSON.stringify({ kind, severity, city }) });
      setMsg('Hlásenie odoslané do mesh siete — konsenzus vzniká pri 2+ nezávislých hláseniach.');
      setCity(''); await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(false); }
  };

  return (
    <SafeAreaView testID="enviro-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="en-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={st.title}>THREAT FUSION</Text>
        <Pressable testID="en-blackout" onPress={() => router.push('/blackout')} hitSlop={12}>
          <Ionicons name="flash-off-outline" size={22} color={C.onInverse} />
        </Pressable>
      </View>
      <View style={st.banner}><Text style={st.bannerText}>SENZORY ZARIADENIA × P2P MESH · SIMULOVANÉ ŠÍRENIE · SWARM ESKALUJE KONSENZUS</Text></View>

      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.fg} />}>

        <Text style={st.section}>AKTÍVNE HROZBY (24 h)</Text>
        {threats.length === 0 && <Text style={st.emptyLine}>— žiadne hlásené hrozby v okolí. Prostredie je stabilné.</Text>}
        {threats.map((t, i) => (
          <View key={i} style={[st.threatCard, t.status === 'CONFIRMED' && { borderColor: C.error }]}>
            <View style={st.rowSpread}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                <Ionicons name={t.icon as any} size={20} color={t.status === 'CONFIRMED' ? C.error : C.warn} />
                <Text style={st.threatTitle}>{t.label.toUpperCase()}{t.city ? ` · ${t.city.toUpperCase()}` : ''}</Text>
              </View>
              <Text style={[st.statusBadge, t.status === 'CONFIRMED' ? { backgroundColor: C.error, color: C.onError } : { backgroundColor: C.surface3, color: C.onS3 }]}>
                {t.status === 'CONFIRMED' ? 'POTVRDENÉ MESHOM' : 'NEOVERENÉ'}
              </Text>
            </View>
            <Text style={st.threatMeta}>Hlásenia: {t.reports} · závažnosť {t.max_severity}/5 · senzor: {t.sensor}</Text>
            <Text style={st.guidance}>▶ {t.guidance}</Text>
          </View>
        ))}

        <Text style={st.section}>NAHLÁSIŤ HROZBU</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: S.sm }}>
          {Object.entries(kinds).map(([k, v]: any) => (
            <Pressable testID={`en-kind-${k}`} key={k} onPress={() => setKind(k)} style={[st.chip, kind === k && st.chipActive]}>
              <Text style={[st.chipText, kind === k && st.chipTextActive]}>{v.label.toUpperCase()}</Text>
            </Pressable>
          ))}
        </View>
        <Text style={st.lbl}>ZÁVAŽNOSŤ: {severity}/5</Text>
        <View style={{ flexDirection: 'row', gap: S.sm }}>
          {[1, 2, 3, 4, 5].map(n => (
            <Pressable testID={`en-sev-${n}`} key={n} onPress={() => setSeverity(n)}
              style={[st.sevBtn, severity >= n && { backgroundColor: n >= 4 ? C.error : C.warn, borderColor: 'transparent' }]}>
              <Text style={[st.sevText, severity >= n && { color: C.onError }]}>{n}</Text>
            </Pressable>
          ))}
        </View>
        <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.sm }}>
          <TextInput testID="en-city" value={city} onChangeText={setCity} placeholder="Mesto / oblasť"
            placeholderTextColor="#777" style={[st.input, { flex: 1 }]} />
          <Pressable testID="en-report" onPress={report} disabled={busy} style={st.reportBtn}>
            {busy ? <ActivityIndicator color={C.onError} size="small" /> : <Ionicons name="megaphone" size={20} color={C.onError} />}
          </Pressable>
        </View>
        {!!msg && <Text testID="en-msg" style={st.msg}>{msg}</Text>}
        {!!err && <Text style={st.err}>{err}</Text>}

        <Art50 lang={lang} />
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  banner: { backgroundColor: C.warn, paddingVertical: 6, alignItems: 'center' },
  bannerText: { color: C.onWarn, fontWeight: '900', letterSpacing: 0.5, fontSize: 8 },
  section: { marginTop: S.lg, marginBottom: S.sm, fontSize: 11, letterSpacing: 2, color: C.fg, fontWeight: '900' },
  emptyLine: { color: C.info, fontSize: 12, fontStyle: 'italic' },
  threatCard: { borderWidth: 2, borderColor: C.borderStrong, padding: S.md, marginBottom: S.sm, backgroundColor: C.surface2 },
  rowSpread: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 6 },
  threatTitle: { color: C.fg, fontWeight: '900', fontSize: 12, letterSpacing: 0.5 },
  statusBadge: { fontSize: 8, fontWeight: '900', letterSpacing: 1, paddingHorizontal: 6, paddingVertical: 3, overflow: 'hidden' },
  threatMeta: { color: C.info, fontSize: 10, marginTop: 6, lineHeight: 14 },
  guidance: { color: C.fg, fontSize: 12, marginTop: 6, lineHeight: 17, fontWeight: '600' },
  chip: { paddingHorizontal: S.md, paddingVertical: 8, borderWidth: 1.5, borderColor: C.borderStrong, minHeight: 36, justifyContent: 'center' },
  chipActive: { backgroundColor: C.error, borderColor: C.error },
  chipText: { fontWeight: '800', color: C.fg, fontSize: 10, letterSpacing: 0.5 },
  chipTextActive: { color: C.onError },
  lbl: { fontSize: 9, letterSpacing: 1.5, color: C.info, fontWeight: '800', marginTop: S.md, marginBottom: 4 },
  sevBtn: { flex: 1, borderWidth: 1.5, borderColor: C.borderStrong, alignItems: 'center', paddingVertical: 10, minHeight: 40, justifyContent: 'center' },
  sevText: { color: C.fg, fontWeight: '900' },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 14, color: C.fg, backgroundColor: C.surface2 },
  reportBtn: { width: 50, backgroundColor: C.error, alignItems: 'center', justifyContent: 'center' },
  msg: { color: C.brand, fontWeight: '800', fontSize: 12, marginTop: S.md, lineHeight: 17 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginTop: S.md },
});
