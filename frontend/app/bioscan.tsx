/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// Vitals Bio-Scanner — rPPG camera/flash vitals (placeholder CV) · Sentinel / 5 GA-T
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import Paywall from '@/src/Paywall';
import Art50 from '@/src/Art50';
import { C, S } from '@/src/theme';
import { Lang } from '@/src/i18n';

export default function BioScan() {
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const router = useRouter();
  const [phase, setPhase] = useState<'idle' | 'scanning' | 'done'>('idle');
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [locked, setLocked] = useState<string | null>(null);
  const [err, setErr] = useState('');
  const samplesRef = useRef<number[]>([]);
  const timerRef = useRef<any>(null);

  const loadHistory = useCallback(async () => {
    try { const h: any = await api('/bioscan/history'); setHistory(h.scans || []); } catch {}
  }, []);
  useEffect(() => { loadHistory(); return () => clearInterval(timerRef.current); }, [loadHistory]);

  const submit = async (payGat: boolean) => {
    try {
      const r: any = await api('/bioscan/measure', {
        method: 'POST',
        body: JSON.stringify({ duration_s: 10, samples: samplesRef.current, pay_gat: payGat }),
      });
      setResult(r); setPhase('done'); setLocked(null); loadHistory();
    } catch (e: any) {
      const m = String(e.message || e);
      setPhase('idle');
      if (m.includes('payment_required')) setLocked(m.replace('payment_required:', '').trim());
      else if (m.includes('insufficient_balance')) setErr('Nedostatok GA-T — zarobte tokeny pomocou komunite (Proof-of-Help) alebo aktivujte Sentinel.');
      else setErr(m);
    }
  };

  const startScan = (payGat = false) => {
    setErr(''); setLocked(null); setResult(null); setPhase('scanning'); setProgress(0);
    samplesRef.current = [];
    timerRef.current = setInterval(() => {
      samplesRef.current.push(0.5 + Math.random() * 0.3); // luminance placeholder (rPPG)
      setProgress(p => {
        if (p >= 100) { clearInterval(timerRef.current); submit(payGat); return 100; }
        return p + 4;
      });
    }, 400);
  };

  return (
    <SafeAreaView testID="bioscan-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="bs-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={st.title}>VITALS BIO-SCANNER</Text>
        <View style={{ width: 26 }} />
      </View>
      <View style={st.banner}><Text style={st.bannerText}>rPPG PLACEHOLDER · REÁLNA KAMERA-CV V NATÍVNOM BUILDE (PHASE 3) · NIE JE DIAGNÓZA</Text></View>

      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        <Text style={st.intro}>Prilož prst na kameru a blesk. Jarvis analyzuje mikropulzácie svetla (fotopletyzmografia) a odhadne tep, SpO2, tlak a stres — bez hodiniek, bez tlakomeru.</Text>

        {locked ? (
          <Paywall message={locked} gatLabel="ZAPLATIŤ 5 GA-T ZA 1 SKEN" onPayGat={() => startScan(true)} onUnlocked={() => startScan(false)} />
        ) : phase === 'scanning' ? (
          <View style={st.scanBox}>
            <Ionicons name="finger-print" size={64} color={C.brand} />
            <Text style={st.scanText}>DRŽTE PRST NA KAMERE…</Text>
            <View style={st.progBg}><View style={[st.prog, { width: `${progress}%` }]} /></View>
            <Text style={st.scanPct}>{progress} %</Text>
          </View>
        ) : (
          <Pressable testID="bs-start" onPress={() => startScan(false)} style={st.startBtn}>
            <Ionicons name="scan" size={22} color={C.onInverse} />
            <Text style={st.startText}>SPUSTIŤ BIO-SCAN (10 s)</Text>
          </Pressable>
        )}
        {!!err && <Text testID="bs-err" style={st.err}>{err}</Text>}

        {result && (
          <View testID="bs-result" style={st.resultCard}>
            <Text style={st.resultTitle}>VÝSLEDOK · {result.access === 'tier' ? 'SENTINEL' : '5 GA-T'} · SIMULÁCIA</Text>
            <View style={st.grid}>
              <Metric icon="heart" label="TEP" value={`${result.heart_rate} bpm`} />
              <Metric icon="water" label="SpO2" value={`${result.spo2} %`} />
              <Metric icon="speedometer" label="TLAK (ODHAD)" value={result.bp_estimate} />
              <Metric icon="pulse" label="HRV" value={`${result.hrv_ms} ms`} />
            </View>
            <Text style={[st.stress, result.stress_level === 'high' && { color: C.error }, result.stress_level === 'low' && { color: C.brand }]}>
              STRES: {result.stress_index}/100 · {result.stress_level === 'low' ? 'NÍZKY 🟢' : result.stress_level === 'moderate' ? 'STREDNÝ 🟡' : 'VYSOKÝ 🔴'}
            </Text>
          </View>
        )}

        {history.length > 0 && (
          <>
            <Text style={st.section}>HISTÓRIA MERANÍ</Text>
            {history.slice(0, 6).map(h => (
              <View key={h.scan_id} style={st.histRow}>
                <Text style={st.histText}>{String(h.at).slice(5, 16).replace('T', ' ')} · ♥ {h.heart_rate} · SpO2 {h.spo2}% · stres {h.stress_level}</Text>
              </View>
            ))}
          </>
        )}
        <Art50 lang={lang} />
      </ScrollView>
    </SafeAreaView>
  );
}

function Metric({ icon, label, value }: any) {
  return (
    <View style={st.metric}>
      <Ionicons name={icon} size={20} color={C.brand} />
      <Text style={st.metricVal}>{value}</Text>
      <Text style={st.metricLbl}>{label}</Text>
    </View>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 17, fontWeight: '900', letterSpacing: 2 },
  banner: { backgroundColor: C.warn, paddingVertical: 6, alignItems: 'center' },
  bannerText: { color: C.onWarn, fontWeight: '900', letterSpacing: 0.5, fontSize: 8 },
  intro: { color: C.onS3, fontSize: 12, lineHeight: 18 },
  startBtn: { marginTop: S.lg, flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, paddingVertical: S.xl, minHeight: 64 },
  startText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 14 },
  scanBox: { marginTop: S.lg, borderWidth: 2, borderColor: C.brand, padding: S.xl, alignItems: 'center', gap: S.md, backgroundColor: C.surface2 },
  scanText: { color: C.fg, fontWeight: '900', letterSpacing: 2, fontSize: 12 },
  progBg: { alignSelf: 'stretch', height: 10, backgroundColor: C.surface3 },
  prog: { height: 10, backgroundColor: C.brand },
  scanPct: { color: C.brand, fontWeight: '900', fontSize: 18 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginTop: S.md, lineHeight: 17 },
  resultCard: { marginTop: S.lg, borderWidth: 2, borderColor: C.brand, padding: S.lg, backgroundColor: C.surface2 },
  resultTitle: { color: C.info, fontSize: 9, letterSpacing: 2, fontWeight: '800', textAlign: 'center' },
  grid: { flexDirection: 'row', flexWrap: 'wrap', marginTop: S.md },
  metric: { width: '50%', alignItems: 'center', paddingVertical: S.md, gap: 4 },
  metricVal: { color: C.fg, fontWeight: '900', fontSize: 22 },
  metricLbl: { color: C.info, fontSize: 9, letterSpacing: 1.5, fontWeight: '800' },
  stress: { textAlign: 'center', fontWeight: '900', fontSize: 13, letterSpacing: 1, marginTop: S.sm, color: C.warn },
  section: { marginTop: S.xl, marginBottom: S.sm, fontSize: 11, letterSpacing: 2, color: C.fg, fontWeight: '900' },
  histRow: { borderWidth: 1, borderColor: C.border, padding: S.md, marginBottom: 6, backgroundColor: C.surface2 },
  histText: { color: C.onS3, fontSize: 11, letterSpacing: 0.3 },
});
