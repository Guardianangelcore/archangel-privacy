/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator, Switch } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { createAudioPlayer, setAudioModeAsync } from 'expo-audio';
import { api, API_BASE, getToken } from '@/src/api';
import { useAuth } from '@/src/auth';
import { sharePdf } from '@/src/pdf';
import { C, S, R } from '@/src/theme';

const QUICK = [
  'Aký je môj ďalší krok zotavenia?',
  'Ako som na tom finančne počas PN?',
  'Som pripravený na núdzovú situáciu?',
];

const CHAINS = [
  { id: 'healing', icon: 'medkit-outline', title: 'Healing Chain', sub: 'Žiadanka → Hunter → Solidarity → rezervácia → kalendár → zamestnávateľ', body: { specialty: 'Ortopédia' } },
  { id: 'safety', icon: 'shield-outline', title: 'Safety Chain', sub: 'Pád/hluk → núdzová slučka → Legacy → info pre záchranárov', body: { trigger: 'manual' } },
  { id: 'recovery', icon: 'walk-outline', title: 'Recovery Chain', sub: 'Nízky pohyb → Physio-AI → kontrola vychádzok pred prechádzkou', body: {} },
  { id: 'supply', icon: 'cube-outline', title: 'Supply Chain', sub: 'Chýbajúci liek → lekárne → barter pri nízkej hotovosti → trasa', body: { med_name: 'Ibalgin' } },
];

export default function Jarvis() {
  const router = useRouter();
  const { user } = useAuth();
  const [q, setQ] = useState('');
  const [answer, setAnswer] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [traces, setTraces] = useState<Record<string, any>>({});
  const [err, setErr] = useState('');
  const [auto, setAuto] = useState<any>(null);
  const playerRef = useRef<any>(null);

  const loadAuto = async () => {
    try { setAuto(await api('/jarvis/actions')); } catch {}
  };
  useEffect(() => { loadAuto(); }, []);

  const toggleAutopilot = async (v: boolean) => {
    setAuto({ ...(auto || {}), autopilot: v });
    try { await api('/jarvis/autopilot', { method: 'PUT', body: JSON.stringify({ enabled: v }) }); } catch { loadAuto(); }
  };

  const ask = async (question: string) => {
    if (!question.trim()) return;
    setBusy('ask'); setErr(''); setAnswer('');
    try {
      const res: any = await api('/jarvis/ask', { method: 'POST', body: JSON.stringify({ question, language: user?.language || 'sk' }) });
      setAnswer(res.answer);
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const speak = async () => {
    if (!answer) return;
    try {
      const res: any = await api('/voice/tts', { method: 'POST', body: JSON.stringify({ text: answer.slice(0, 2000), voice: 'nova', language: user?.language || 'sk' }) });
      const token = await getToken();
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false } as any);
      try { playerRef.current?.remove?.(); } catch {}
      const p = createAudioPlayer({ uri: `${API_BASE}${res.url}`, headers: token ? { Authorization: `Bearer ${token}` } : {} });
      playerRef.current = p; p.play();
    } catch {}
  };

  const runChain = async (c: any) => {
    setBusy(c.id); setErr('');
    try {
      const res: any = await api(`/chains/${c.id}`, { method: 'POST', body: JSON.stringify(c.body) });
      setTraces({ ...traces, [c.id]: res });
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  return (
    <SafeAreaView testID="jarvis-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="jv-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>NEURAL LINK · JARVIS</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
        <View style={styles.orb}><Ionicons name="sparkles" size={30} color={C.onInverse} /></View>
        <Text style={styles.h1}>Spýtajte sa na čokoľvek</Text>
        <Text style={styles.sub}>Jarvis vidí všetky 4 piliere naraz — zotavenie, financie, bezpečnosť aj odkaz — a odpovie jednou kombinovanou radou.</Text>

        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: S.sm, marginTop: S.lg }}>
          {QUICK.map((s, i) => (
            <Pressable key={i} testID={`jv-quick-${i}`} onPress={() => { setQ(s); ask(s); }} style={styles.quick}>
              <Text style={styles.quickText}>{s}</Text>
            </Pressable>
          ))}
        </View>

        <View style={styles.askRow}>
          <TextInput testID="jv-input" style={styles.input} placeholder="Napíšte otázku pre Jarvisa…" placeholderTextColor={C.info} value={q} onChangeText={setQ} onSubmitEditing={() => ask(q)} returnKeyType="send" />
          <Pressable testID="jv-ask" onPress={() => ask(q)} disabled={busy === 'ask'} style={styles.askBtn}>
            {busy === 'ask' ? <ActivityIndicator size="small" color={C.onInverse} /> : <Ionicons name="arrow-up" size={20} color={C.onInverse} />}
          </Pressable>
        </View>
        {!!err && <Text style={styles.err}>{err}</Text>}
        {!!answer && (
          <View style={styles.answerBox}>
            <Text style={styles.answerText}>{answer}</Text>
            <Pressable testID="jv-speak" onPress={speak} style={styles.speakBtn}>
              <Ionicons name="volume-medium-outline" size={16} color={C.brand} />
              <Text style={styles.speakText}>PREHRAŤ HLASOM</Text>
            </Pressable>
          </View>
        )}

        <Text style={styles.section}>AUTOPILOT — MEDICAL SENTINEL</Text>
        <View style={styles.autoRow}>
          <Ionicons name="infinite" size={20} color={C.brand} />
          <View style={{ flex: 1 }}>
            <Text style={styles.chainTitle}>Automatické spracovanie Trezoru</Text>
            <Text style={styles.chainSub}>Nový dokument → OCR → AI preklad → kalendár → rezervácia termínu. Bez pýtania — dostanete len potvrdenie.</Text>
          </View>
          <Switch testID="jv-autopilot" value={auto?.autopilot !== false} onValueChange={toggleAutopilot} trackColor={{ true: C.brand, false: C.surface3 }} />
        </View>
        {(auto?.actions || []).slice(0, 4).map((a: any) => (
          <View key={a.action_id} style={styles.chainCard}>
            <Text style={styles.chainTitle}>📄 {a.doc_title || 'Dokument'}{a.booked_slot ? '  ·  ✅ ZAREZERVOVANÉ' : ''}</Text>
            {(a.steps || []).map((s: any, i: number) => (
              <View key={i} style={styles.traceRow}>
                <Ionicons name={s.status === 'ok' ? 'checkmark-circle' : 'remove-circle-outline'} size={14} color={s.status === 'ok' ? '#5FA779' : C.info} />
                <Text style={styles.traceText}><Text style={{ fontWeight: '900' }}>{s.step}:</Text> {s.detail}</Text>
              </View>
            ))}
          </View>
        ))}

        <Text style={styles.section}>SENTIENT REŤAZE (AUTOMATIZÁCIE)</Text>
        {CHAINS.map(c => {
          const tr = traces[c.id];
          return (
            <View key={c.id} style={styles.chainCard}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.md }}>
                <View style={styles.chainIcon}><Ionicons name={c.icon as any} size={18} color={C.brand} /></View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.chainTitle}>{c.title}</Text>
                  <Text style={styles.chainSub}>{c.sub}</Text>
                </View>
                <Pressable testID={`jv-chain-${c.id}`} onPress={() => runChain(c)} disabled={busy === c.id} style={styles.runBtn}>
                  {busy === c.id ? <ActivityIndicator size="small" color={C.onInverse} /> : <Text style={styles.runText}>SPUSTIŤ</Text>}
                </Pressable>
              </View>
              {tr && (
                <View style={styles.traceBox}>
                  {tr.steps.map((s: any, i: number) => (
                    <View key={i} style={styles.traceRow}>
                      <Ionicons name={s.status === 'ok' ? 'checkmark-circle' : 'remove-circle-outline'} size={14} color={s.status === 'ok' ? '#5FA779' : C.info} />
                      <Text style={styles.traceText}><Text style={{ fontWeight: '900' }}>{s.step}:</Text> {s.detail}</Text>
                    </View>
                  ))}
                  <Text style={styles.traceSummary}>▶ {tr.summary}{tr.simulated ? '  (simulované API)' : ''}</Text>
                </View>
              )}
            </View>
          );
        })}

        <Text style={styles.section}>TÝŽDENNÝ GUARDIAN PULSE REPORT</Text>
        <Pressable
          testID="jv-weekly"
          onPress={async () => { setBusy('pdf'); try { await sharePdf('/reports/weekly.pdf', 'guardian_pulse_report.pdf'); } catch (e: any) { setErr(String(e.message || e)); } finally { setBusy(null); } }}
          disabled={busy === 'pdf'}
          style={styles.cta}
        >
          {busy === 'pdf' ? <ActivityIndicator color={C.onInverse} /> : (
            <>
              <Ionicons name="document-text-outline" size={16} color={C.onInverse} />
              <Text style={styles.ctaText}>STIAHNUŤ PREHĽAD: ZDRAVIE · FINANCIE · BEZPEČNOSŤ</Text>
            </>
          )}
        </Pressable>
        <Text style={styles.disclaimer}>AI asistent — informačný obsah, nie zdravotná starostlivosť (EU AI Act čl. 50). Reťaze sú jednorazové a chránené proti slučkám.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 14 },
  orb: { width: 64, height: 64, borderRadius: 32, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center' },
  h1: { marginTop: S.lg, fontSize: 24, fontWeight: '900', color: C.fg },
  sub: { marginTop: S.sm, fontSize: 13, color: C.onS3, lineHeight: 19 },
  quick: { borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.pill, paddingHorizontal: S.md, paddingVertical: 10 },
  quickText: { color: C.onS3, fontSize: 11, fontWeight: '700' },
  askRow: { flexDirection: 'row', gap: S.sm, marginTop: S.lg, alignItems: 'center' },
  input: { flex: 1, backgroundColor: C.surface2, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, color: C.fg, paddingHorizontal: S.lg, minHeight: 50, fontSize: 14 },
  askBtn: { width: 50, height: 50, borderRadius: R.sm, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center' },
  answerBox: { marginTop: S.lg, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.brand, padding: S.lg },
  answerText: { color: C.fg, fontSize: 14, lineHeight: 21 },
  speakBtn: { marginTop: S.md, flexDirection: 'row', gap: 6, alignItems: 'center', alignSelf: 'flex-start', minHeight: 44 },
  speakText: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  section: { marginTop: S.xl, marginBottom: S.sm, fontSize: 11, letterSpacing: 2, color: C.info, fontWeight: '800' },
  autoRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.brand, padding: S.md, marginBottom: S.sm },
  chainCard: { backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.md, marginBottom: S.sm },
  chainIcon: { width: 38, height: 38, borderRadius: R.sm, backgroundColor: C.brandTer, alignItems: 'center', justifyContent: 'center' },
  chainTitle: { color: C.fg, fontWeight: '900', fontSize: 13 },
  chainSub: { color: C.info, fontSize: 10, marginTop: 2, lineHeight: 14 },
  runBtn: { backgroundColor: C.brand, borderRadius: R.sm, paddingHorizontal: S.md, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  runText: { color: C.onInverse, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  traceBox: { marginTop: S.md, borderTopWidth: 1, borderTopColor: C.border, paddingTop: S.md, gap: 6 },
  traceRow: { flexDirection: 'row', gap: 8, alignItems: 'flex-start' },
  traceText: { flex: 1, color: C.onS3, fontSize: 11.5, lineHeight: 16 },
  traceSummary: { marginTop: 4, color: C.brand, fontWeight: '800', fontSize: 12 },
  cta: { flexDirection: 'row', gap: S.sm, backgroundColor: C.brand, borderRadius: R.sm, minHeight: 52, alignItems: 'center', justifyContent: 'center', paddingHorizontal: S.md },
  ctaText: { color: C.onInverse, fontWeight: '900', letterSpacing: 0.5, fontSize: 11 },
  disclaimer: { marginTop: S.lg, color: C.info, fontSize: 10, lineHeight: 15, textAlign: 'center' },
  err: { color: C.error, marginTop: S.md, fontSize: 12 },
});
