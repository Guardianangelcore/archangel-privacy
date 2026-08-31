/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// GROWTH CURVE — child height & weight with WHO percentiles (P3 · P50 · P97).
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator, Dimensions } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, useLocalSearchParams } from 'expo-router';
import Svg, { Polyline, Circle, Line, Text as SvgText } from 'react-native-svg';
import { api } from '@/src/api';
import { DateField } from '@/src/ui/fields';
import { C, S, R } from '@/src/theme';

const W = Math.min(Dimensions.get('window').width, 500) - 48;
const H = 230;
const PAD = { l: 34, r: 10, t: 10, b: 22 };

function GrowthChart({ curves, logs, measure }: { curves: any[]; logs: any[]; measure: 'height' | 'weight' }) {
  const key = measure === 'height' ? 'height_cm' : 'weight_kg';
  const pts = logs.filter((l: any) => l[key] != null && l.age_months != null);
  if (!curves.length && !pts.length) return <Text style={st.hint}>No data for the chart yet.</Text>;
  const allM = [...curves.map(c => c.m), ...pts.map(p => p.age_months)];
  const allV = [...curves.flatMap(c => [c.p3, c.p97]), ...pts.map(p => p[key])];
  const mMax = Math.max(...allM, 24);
  const vMin = Math.min(...allV) * 0.94;
  const vMax = Math.max(...allV) * 1.05;
  const X = (m: number) => PAD.l + ((m / mMax) * (W - PAD.l - PAD.r));
  const Y = (v: number) => PAD.t + (1 - (v - vMin) / (vMax - vMin)) * (H - PAD.t - PAD.b);
  const line = (k: string) => curves.map(c => `${X(c.m)},${Y(c[k])}`).join(' ');
  const childLine = pts.map(p => `${X(p.age_months)},${Y(p[key])}`).join(' ');
  const yTicks = [vMin + (vMax - vMin) * 0.1, (vMin + vMax) / 2, vMax - (vMax - vMin) * 0.08];
  const xTicks = [0, Math.round(mMax / 2), Math.round(mMax)];
  const last = curves[curves.length - 1];
  return (
    <Svg width={W} height={H}>
      {yTicks.map((v, i) => (
        <React.Fragment key={i}>
          <Line x1={PAD.l} y1={Y(v)} x2={W - PAD.r} y2={Y(v)} stroke="rgba(255,255,255,0.08)" strokeWidth={1} />
          <SvgText x={2} y={Y(v) + 3} fill="#8E8E93" fontSize={9}>{v.toFixed(0)}</SvgText>
        </React.Fragment>
      ))}
      {xTicks.map((m, i) => (
        <SvgText key={`x${i}`} x={X(m) - 8} y={H - 6} fill="#8E8E93" fontSize={9}>{m >= 24 ? `${Math.round(m / 12)}r` : `${m}m`}</SvgText>
      ))}
      {curves.length > 0 && (
        <>
          <Polyline points={line('p3')} fill="none" stroke="#8E8E93" strokeWidth={1.2} strokeDasharray="4,4" />
          <Polyline points={line('p50')} fill="none" stroke="#D4AF37" strokeWidth={1.6} strokeDasharray="6,4" />
          <Polyline points={line('p97')} fill="none" stroke="#8E8E93" strokeWidth={1.2} strokeDasharray="4,4" />
          {last && (
            <>
              <SvgText x={W - PAD.r - 20} y={Y(last.p3) - 3} fill="#8E8E93" fontSize={9}>P3</SvgText>
              <SvgText x={W - PAD.r - 24} y={Y(last.p50) - 3} fill="#D4AF37" fontSize={9}>P50</SvgText>
              <SvgText x={W - PAD.r - 24} y={Y(last.p97) - 3} fill="#8E8E93" fontSize={9}>P97</SvgText>
            </>
          )}
        </>
      )}
      {pts.length > 1 && <Polyline points={childLine} fill="none" stroke="#5FA779" strokeWidth={2.5} />}
      {pts.map((p, i) => (
        <Circle key={i} cx={X(p.age_months)} cy={Y(p[key])} r={4} fill="#5FA779" stroke="#0A0A0F" strokeWidth={1.5} />
      ))}
    </Svg>
  );
}

export default function ChildGrowth() {
  const router = useRouter();
  const { child_id } = useLocalSearchParams<{ child_id: string }>();
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState('');
  const [measure, setMeasure] = useState<'height' | 'weight'>('height');
  const [date, setDate] = useState('');
  const [height, setHeight] = useState('');
  const [weight, setWeight] = useState('');
  const [busy, setBusy] = useState(false);
  const [sexBusy, setSexBusy] = useState(false);

  const load = async () => {
    try { setData(await api(`/lifecard/children/${child_id}/growth`)); }
    catch (e: any) { setErr(String(e.message || e)); }
  };
  useEffect(() => { if (child_id) load(); }, [child_id]); // eslint-disable-line react-hooks/exhaustive-deps

  const setSex = async (sex: 'm' | 'f') => {
    setSexBusy(true); setErr('');
    try { await api(`/lifecard/children/${child_id}`, { method: 'PUT', body: JSON.stringify({ sex }) }); await load(); }
    catch (e: any) { setErr(String(e.message || e)); }
    finally { setSexBusy(false); }
  };

  const add = async () => {
    const h = height ? parseFloat(height.replace(',', '.')) : null;
    const w = weight ? parseFloat(weight.replace(',', '.')) : null;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || (!h && !w)) { setErr('Pick a date and enter height or weight.'); return; }
    setBusy(true); setErr('');
    try {
      await api(`/lifecard/children/${child_id}/growth`, { method: 'POST', body: JSON.stringify({ date, height_cm: h, weight_kg: w }) });
      setDate(''); setHeight(''); setWeight('');
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(false); }
  };

  const del = async (id: string) => {
    try { await api(`/lifecard/growth/${id}`, { method: 'DELETE' }); await load(); } catch {}
  };

  const logs = data?.logs || [];
  const curves = data?.curves?.[measure] || [];

  return (
    <SafeAreaView testID="child-growth-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="gr-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={st.title}>GROWTH CURVE</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
        {!data && <ActivityIndicator color={C.brand} style={{ marginTop: 40 }} />}
        {data && (
          <>
            <Text style={st.h1}>{data.child.name}</Text>
            <Text style={st.sub}>Height and weight with indicative percentiles based on WHO standards.</Text>
            {!!err && <Text style={st.err}>{err}</Text>}

            {data.sex_required && (
              <View style={st.sexBox}>
                <Text style={st.sexTitle}>Select the sex for WHO percentiles:</Text>
                <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.sm }}>
                  <Pressable testID="gr-sex-m" onPress={() => setSex('m')} disabled={sexBusy} style={st.sexChip}>
                    <Text style={st.sexChipText}>👦 CHLAPEC</Text>
                  </Pressable>
                  <Pressable testID="gr-sex-f" onPress={() => setSex('f')} disabled={sexBusy} style={st.sexChip}>
                    <Text style={st.sexChipText}>👧 GIRL</Text>
                  </Pressable>
                </View>
              </View>
            )}

            {/* ZÁPIS MERANIA */}
            <View style={st.addBox}>
              <DateField testID="gr-date" title="MEASUREMENT DATE" value={date} onChange={setDate} placeholder="Measurement date" style={st.input} />
              <View style={{ flexDirection: 'row', gap: S.sm }}>
                <TextInput testID="gr-height" style={[st.input, { flex: 1 }]} placeholder="Height (cm)" placeholderTextColor={C.info} keyboardType="decimal-pad" value={height} onChangeText={setHeight} />
                <TextInput testID="gr-weight" style={[st.input, { flex: 1 }]} placeholder="Weight (kg)" placeholderTextColor={C.info} keyboardType="decimal-pad" value={weight} onChangeText={setWeight} />
              </View>
              <Pressable testID="gr-save" onPress={add} disabled={busy} style={st.cta}>
                {busy ? <ActivityIndicator color={C.onInverse} /> : <Text style={st.ctaText}>LOG MEASUREMENT</Text>}
              </Pressable>
            </View>

            {/* GRAF */}
            <View style={st.chartBox}>
              <View style={{ flexDirection: 'row', gap: S.sm, marginBottom: S.md }}>
                <Pressable testID="gr-m-height" onPress={() => setMeasure('height')} style={[st.mChip, measure === 'height' && st.mChipOn]}>
                  <Text style={[st.mChipText, measure === 'height' && { color: C.onInverse }]}>HEIGHT</Text>
                </Pressable>
                <Pressable testID="gr-m-weight" onPress={() => setMeasure('weight')} style={[st.mChip, measure === 'weight' && st.mChipOn]}>
                  <Text style={[st.mChipText, measure === 'weight' && { color: C.onInverse }]}>WEIGHT</Text>
                </Pressable>
              </View>
              <GrowthChart curves={curves} logs={logs} measure={measure} />
              <Text style={st.note}>{data.note}</Text>
            </View>

            {/* MERANIA */}
            <Text style={st.section}>MERANIA ({logs.length})</Text>
            {logs.length === 0 && <Text style={st.hint}>No measurements yet. Log the first one above.</Text>}
            {[...logs].reverse().map((l: any) => (
              <View key={l.log_id} testID={`gr-log-${l.log_id}`} style={st.logRow}>
                <View style={{ flex: 1 }}>
                  <Text style={st.logDate}>{l.date}{l.age_months != null ? ` · ${l.age_months < 24 ? `${Math.round(l.age_months)} mes.` : `${(l.age_months / 12).toFixed(1)} r.`}` : ''}</Text>
                  <Text style={st.logVals}>
                    {l.height_cm != null ? `📏 ${l.height_cm} cm${l.height_percentile != null ? ` (P${Math.round(l.height_percentile)})` : ''}` : ''}
                    {l.height_cm != null && l.weight_kg != null ? '   ' : ''}
                    {l.weight_kg != null ? `⚖️ ${l.weight_kg} kg${l.weight_percentile != null ? ` (P${Math.round(l.weight_percentile)})` : ''}` : ''}
                  </Text>
                </View>
                <Pressable testID={`gr-del-${l.log_id}`} onPress={() => del(l.log_id)} hitSlop={8}>
                  <Ionicons name="trash-outline" size={16} color={C.info} />
                </Pressable>
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
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 14 },
  h1: { fontSize: 24, fontWeight: '900', color: C.fg },
  sub: { marginTop: S.sm, fontSize: 13, color: C.onS3, lineHeight: 19 },
  err: { color: C.error, marginTop: S.md, fontSize: 12 },
  sexBox: { marginTop: S.lg, backgroundColor: 'rgba(212,175,55,0.10)', borderRadius: R.md, borderWidth: 1.5, borderColor: C.brand, padding: S.md },
  sexTitle: { color: C.fg, fontWeight: '700', fontSize: 13 },
  sexChip: { flex: 1, borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.pill, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  sexChipText: { color: C.brand, fontWeight: '900', fontSize: 12, letterSpacing: 1 },
  addBox: { marginTop: S.lg, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.brand, padding: S.md, gap: S.sm },
  input: { backgroundColor: C.bg, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, color: C.fg, paddingHorizontal: S.md, minHeight: 46, fontSize: 13 },
  cta: { backgroundColor: C.brand, borderRadius: R.sm, minHeight: 48, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
  chartBox: { marginTop: S.lg, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.md },
  mChip: { borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.pill, paddingHorizontal: 16, paddingVertical: 8 },
  mChipOn: { backgroundColor: C.brand, borderColor: C.brand },
  mChipText: { color: C.fg, fontWeight: '900', fontSize: 10.5, letterSpacing: 1 },
  note: { color: C.info, fontSize: 9.5, marginTop: S.sm, lineHeight: 14, fontStyle: 'italic' },
  section: { marginTop: S.xl, color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 2 },
  hint: { marginTop: S.md, color: C.onS3, fontSize: 12 },
  logRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, backgroundColor: C.surface2, borderRadius: R.sm, borderWidth: 1, borderColor: C.border, padding: S.md, marginTop: S.sm, minHeight: 56 },
  logDate: { color: C.info, fontSize: 11, fontWeight: '700' },
  logVals: { color: C.fg, fontSize: 13.5, fontWeight: '800', marginTop: 3 },
});
