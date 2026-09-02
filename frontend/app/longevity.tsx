/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// Longevity Engine — Bio-Age Dashboard + AI Bio-Hacks (Sentinel tier)
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, Switch, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { WheelField } from '@/src/ui/fields';
import Paywall from '@/src/Paywall';
import Art50 from '@/src/Art50';
import { C, S } from '@/src/theme';
import { Lang } from '@/src/i18n';
import { useI18n } from '@/src/i18n-context';

export default function Longevity() {
  const { t: tt, tx } = useI18n();
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'en';
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [locked, setLocked] = useState<string | null>(null);
  const [needProfile, setNeedProfile] = useState(false);
  const [f, setF] = useState({ birth_year: '', height_cm: '', weight_kg: '', smoker: false, activity_level: 'medium' });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    setErr('');
    try {
      const d: any = await api('/longevity/bioage');
      setData(d); setLocked(null); setNeedProfile(false);
    } catch (e: any) {
      const m = String(e.message || e);
      if (m.includes('sentinel_required')) setLocked(m.replace('sentinel_required:', '').trim());
      else if (m.includes('profile_missing')) setNeedProfile(true);
      else setErr(m);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const saveProfile = async () => {
    setBusy(true); setErr('');
    try {
      await api('/longevity/profile', {
        method: 'PUT',
        body: JSON.stringify({
          birth_year: parseInt(f.birth_year, 10),
          height_cm: parseFloat(f.height_cm) || null,
          weight_kg: parseFloat(f.weight_kg) || null,
          smoker: f.smoker, activity_level: f.activity_level,
        }),
      });
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(false); }
  };

  return (
    <SafeAreaView testID="longevity-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="lg-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={st.title}>{tt('longevity.longevity_engine')}</Text>
        <Pressable testID="lg-refresh" onPress={load} hitSlop={12}>
          <Ionicons name="refresh" size={22} color={C.onInverse} />
        </Pressable>
      </View>

      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        {locked ? (
          <Paywall message={locked} onUnlocked={load} />
        ) : needProfile ? (
          <View>
            <Text style={st.intro}>{tt('longevity.jarvis_computes_your_biological_age')}</Text>
            <Text style={st.lbl}>{tt('longevity.birth_year')}</Text>
            <WheelField testID="lg-birth" title={tt('longevity.birth_year')} min={1920} max={2012} value={f.birth_year} onChange={v => setF({ ...f, birth_year: v })} placeholder="1971" style={st.input} />
            <View style={{ flexDirection: 'row', gap: S.sm }}>
              <View style={{ flex: 1 }}>
                <Text style={st.lbl}>{tt('longevity.height_cm')}</Text>
                <WheelField testID="lg-height" title={tt('longevity.height')} min={120} max={220} unit="cm" value={f.height_cm} onChange={v => setF({ ...f, height_cm: v })} placeholder="178" style={st.input} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={st.lbl}>{tt('longevity.weight_kg')}</Text>
                <WheelField testID="lg-weight" title={tt('longevity.weight')} min={35} max={200} unit="kg" value={f.weight_kg} onChange={v => setF({ ...f, weight_kg: v })} placeholder="85" style={st.input} />
              </View>
            </View>
            <View style={st.switchRow}>
              <Text style={st.switchLbl}>{tt('longevity.smoker')}</Text>
              <Switch testID="lg-smoker" value={f.smoker} onValueChange={v => setF({ ...f, smoker: v })} trackColor={{ true: C.error, false: C.surface3 }} />
            </View>
            <Text style={st.lbl}>{tt('longevity.activity')}</Text>
            <View style={{ flexDirection: 'row', gap: S.sm }}>
              {[['low', 'LOW'], ['medium', 'MEDIUM'], ['high', 'HIGH']].map(([k, v]) => (
                <Pressable testID={`lg-act-${k}`} key={k} onPress={() => setF({ ...f, activity_level: k })} style={[st.chip, f.activity_level === k && st.chipActive]}>
                  <Text style={[st.chipText, f.activity_level === k && st.chipTextActive]}>{v}</Text>
                </Pressable>
              ))}
            </View>
            <Pressable testID="lg-save" onPress={saveProfile} disabled={busy || !f.birth_year} style={st.saveBtn}>
              {busy ? <ActivityIndicator color={C.onInverse} /> : <Text style={st.saveText}>{tt('longevity.calculate_bio_age')}</Text>}
            </Pressable>
            {!!err && <Text style={st.err}>{err}</Text>}
          </View>
        ) : data ? (
          <>
            <View style={st.ageCard}>
              <View style={st.ageCol}>
                <Text style={st.ageLbl}>{tt('longevity.calendar_age')}</Text>
                <Text style={st.ageVal}>{data.chronological_age}</Text>
              </View>
              <Ionicons name={data.delta_years > 0.5 ? 'trending-up' : data.delta_years < -0.5 ? 'trending-down' : 'remove'} size={30}
                color={data.delta_years > 0.5 ? C.error : data.delta_years < -0.5 ? C.brand : C.info} />
              <View style={st.ageCol}>
                <Text style={st.ageLbl}>{tt('longevity.biological_age')}</Text>
                <Text testID="lg-bioage" style={[st.ageVal, { color: data.delta_years > 0.5 ? C.error : C.brand }]}>{data.biological_age}</Text>
              </View>
            </View>
            <Text style={st.verdict}>{data.verdict} · Δ {data.delta_years > 0 ? '+' : ''}{data.delta_years} {tt('longevity.yrs')}</Text>

            <Text style={st.section}>{tt('longevity.factors')}</Text>
            {data.factors.map((fa: any, i: number) => (
              <View key={i} style={st.factorRow}>
                <Text style={[st.factorImpact, { color: fa.impact_years > 0 ? C.error : C.brand }]}>
                  {fa.impact_years > 0 ? '+' : ''}{fa.impact_years}y
                </Text>
                <View style={{ flex: 1 }}>
                  <Text style={st.factorName}>{fa.factor.toUpperCase()}</Text>
                  <Text style={st.factorNote}>{tx(fa.note)}</Text>
                </View>
              </View>
            ))}
            {data.factors.length === 0 && <Text style={st.emptyLine}>{tt('longevity.not_enough_data_yet_log_steps_pulse')}</Text>}

            <Text style={st.section}>{tt('longevity.ai_bio_hacks')}</Text>
            {data.bio_hacks.map((h: string, i: number) => (
              <View key={i} style={st.hackRow}>
                <Ionicons name="flash" size={16} color="#B8860B" />
                <Text style={st.hackText}>{h}</Text>
              </View>
            ))}
            <Pressable testID="lg-edit" onPress={() => setNeedProfile(true)} style={st.editBtn}>
              <Text style={st.editText}>{tt('longevity.edit_profile_height_weight_activity')}</Text>
            </Pressable>
            <Text style={st.disc}>{data.disclaimer}</Text>
            <Art50 lang={lang} />
          </>
        ) : <ActivityIndicator color={C.brand} style={{ marginTop: 40 }} />}
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 17, fontWeight: '900', letterSpacing: 2 },
  intro: { color: C.onS3, fontSize: 12, lineHeight: 18, marginBottom: S.md },
  lbl: { fontSize: 9, letterSpacing: 1.5, color: C.info, fontWeight: '800', marginTop: S.md, marginBottom: 4 },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 15, color: C.fg, backgroundColor: C.surface2 },
  switchRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: S.md, borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, backgroundColor: C.surface2 },
  switchLbl: { color: C.fg, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  chip: { flex: 1, paddingVertical: 10, borderWidth: 1.5, borderColor: C.borderStrong, alignItems: 'center', minHeight: 40, justifyContent: 'center' },
  chipActive: { backgroundColor: C.brand, borderColor: C.brand },
  chipText: { fontWeight: '800', color: C.fg, fontSize: 10, letterSpacing: 1 },
  chipTextActive: { color: C.onInverse },
  saveBtn: { marginTop: S.lg, backgroundColor: C.brand, paddingVertical: S.lg, alignItems: 'center', minHeight: 56, justifyContent: 'center' },
  saveText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 13 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginTop: S.md },
  ageCard: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-around', borderWidth: 2, borderColor: C.borderStrong, padding: S.lg, backgroundColor: C.surface2 },
  ageCol: { alignItems: 'center' },
  ageLbl: { color: C.info, fontSize: 9, letterSpacing: 1.5, fontWeight: '800' },
  ageVal: { color: C.fg, fontSize: 44, fontWeight: '900', marginTop: 4 },
  verdict: { textAlign: 'center', marginTop: S.md, color: C.fg, fontWeight: '900', letterSpacing: 1, fontSize: 13 },
  section: { marginTop: S.xl, marginBottom: S.sm, fontSize: 11, letterSpacing: 2, color: C.fg, fontWeight: '900' },
  factorRow: { flexDirection: 'row', gap: S.md, borderWidth: 1, borderColor: C.border, padding: S.md, marginBottom: 6, backgroundColor: C.surface2, alignItems: 'center' },
  factorImpact: { fontWeight: '900', fontSize: 16, width: 52 },
  factorName: { color: C.fg, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  factorNote: { color: C.info, fontSize: 11, marginTop: 2, lineHeight: 15 },
  emptyLine: { color: C.info, fontSize: 12, fontStyle: 'italic' },
  hackRow: { flexDirection: 'row', gap: S.sm, alignItems: 'flex-start', borderWidth: 1.5, borderColor: '#B8860B', padding: S.md, marginBottom: 6, backgroundColor: C.surface2 },
  hackText: { flex: 1, color: C.fg, fontSize: 12.5, lineHeight: 18 },
  editBtn: { marginTop: S.md, borderWidth: 1.5, borderColor: C.borderStrong, paddingVertical: S.md, alignItems: 'center', minHeight: 44, justifyContent: 'center' },
  editText: { color: C.onS3, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  disc: { color: C.info, fontSize: 9, marginTop: S.md, lineHeight: 13 },
});
