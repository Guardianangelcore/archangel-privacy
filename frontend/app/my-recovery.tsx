/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useEffect, useMemo, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as Notifications from 'expo-notifications';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { sharePdf } from '@/src/pdf';
import { WheelField, DateField, TimeField } from '@/src/ui/fields';
import { EmptyState } from '@/src/ui/EmptyState';
import { t, Lang } from '@/src/i18n';
import { C, S, R } from '@/src/theme';

const CONTRACTS = [['fulltime', 'TPP'], ['dpp', 'DPP'], ['dpc', 'DPČ']];

function outingStatus(outings: any[]) {
  const now = new Date();
  const mins = now.getHours() * 60 + now.getMinutes();
  for (const o of outings) {
    const [fh, fm] = o.from_time.split(':').map(Number);
    const [th, tm] = o.to_time.split(':').map(Number);
    const from = fh * 60 + fm, to = th * 60 + tm;
    if (mins >= from && mins <= to) {
      const left = to - mins;
      return { active: true, left, window: `${o.from_time}–${o.to_time}` };
    }
  }
  const next = outings
    .map(o => { const [fh, fm] = o.from_time.split(':').map(Number); return { start: fh * 60 + fm, o }; })
    .filter(x => x.start > mins).sort((a, b) => a.start - b.start)[0];
  return { active: false, next: next ? `${next.o.from_time}–${next.o.to_time}` : null };
}

export default function MyRecovery() {
  const router = useRouter();
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const [rec, setRec] = useState<any>(null);
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [note, setNote] = useState('');
  const [contract, setContract] = useState('fulltime');
  const [gross, setGross] = useState('');
  const [outings, setOutings] = useState<any[]>([]);
  const [oFrom, setOFrom] = useState('');
  const [oTo, setOTo] = useState('');
  const [aiText, setAiText] = useState('');
  const [showAi, setShowAi] = useState(false);
  const [calc, setCalc] = useState<any>(null);
  const [days, setDays] = useState('30');
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState('');
  const [info, setInfo] = useState('');
  const [tick, setTick] = useState(0);

  useEffect(() => {
    (async () => {
      try {
        const r: any = await api('/recovery/epn');
        if (r.start_date) {
          setRec(r); setStart(r.start_date); setEnd(r.end_date || ''); setNote(r.note || '');
          setContract(r.contract_type || 'fulltime'); setGross(String(r.monthly_gross || ''));
          setOutings(r.outings || []);
        }
      } catch {}
    })();
    const t = setInterval(() => setTick(x => x + 1), 30000);
    return () => clearInterval(t);
  }, []);

  const status = useMemo(() => outingStatus(outings), [outings, tick]); // eslint-disable-line react-hooks/exhaustive-deps

  const save = async () => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(start)) { setErr('Vyberte začiatok PN v kalendári.'); return; }
    setBusy('save'); setErr(''); setInfo('');
    try {
      const r: any = await api('/recovery/epn', {
        method: 'PUT',
        body: JSON.stringify({ start_date: start, end_date: end || null, note, contract_type: contract, monthly_gross: parseFloat(gross) || 0, outings }),
      });
      setRec(r); setInfo('ePN uložená.');
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const addOuting = () => {
    if (!/^\d{2}:\d{2}$/.test(oFrom) || !/^\d{2}:\d{2}$/.test(oTo)) { setErr('Vyberte čas vychádzky Od a Do.'); return; }
    setOutings([...outings, { from_time: oFrom, to_time: oTo }]);
    setOFrom(''); setOTo(''); setErr('');
  };

  const extractAi = async () => {
    if (!aiText.trim()) return;
    setBusy('ai'); setErr('');
    try {
      const r: any = await api('/recovery/extract-outings', { method: 'POST', body: JSON.stringify({ text: aiText }) });
      if (r.found) { setOutings(r.outings); setInfo(`Jarvis našiel ${r.outings.length} vychádzky — skontrolujte a uložte.`); setShowAi(false); }
      else setErr('Vo vloženom texte sa nenašli žiadne vychádzky.');
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const scheduleAlerts = async () => {
    if (Platform.OS === 'web') { setInfo('Upozornenia fungujú na telefóne (Expo Go / natívny build).'); return; }
    try {
      const perm = await Notifications.requestPermissionsAsync();
      if (!perm.granted) { setErr('Povolenie na upozornenia zamietnuté.'); return; }
      let n = 0;
      const now = new Date();
      for (const o of outings) {
        const [th, tm] = o.to_time.split(':').map(Number);
        const fire = new Date(now); fire.setHours(th, tm - 15, 0, 0);
        if (fire > now) {
          await Notifications.scheduleNotificationAsync({
            content: { title: '⏰ Vychádzka sa končí o 15 minút', body: `Okno ${o.from_time}–${o.to_time}. Vráťte sa domov — možná kontrola zo Sociálnej poisťovne.` },
            trigger: fire as any,
          });
          n++;
        }
      }
      setInfo(n ? `Nastavené ${n} upozornenia na dnešné vychádzky (15 min pred koncom).` : 'Dnešné vychádzky už prebehli — upozornenia sa nastavia zajtra.');
    } catch (e: any) { setErr(String(e.message || e)); }
  };

  const runCalc = async () => {
    setBusy('calc'); setErr('');
    try {
      const r: any = await api('/recovery/sickpay', {
        method: 'POST',
        body: JSON.stringify({ contract_type: contract, monthly_gross: parseFloat(gross) || 0, days: parseInt(days) || 30 }),
      });
      setCalc(r);
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const pdf = async (kind: string) => {
    setBusy(`pdf-${kind}`);
    try { await sharePdf(`/recovery/report.pdf?kind=${kind}`, `guardian_pn_${kind}.pdf`); }
    catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  return (
    <SafeAreaView testID="my-recovery-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="mr-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>MOJE ZOTAVENIE</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
        <Text style={styles.h1}>Hustle Recovery Guard</Text>
        <Text style={styles.sub}>PN/ePN pod kontrolou: vychádzky, nemocenské a hlásenia úradom — bez papierovačiek.</Text>
        {!!err && <Text style={styles.err}>{err}</Text>}
        {!!info && <Text style={styles.info}>{info}</Text>}

        {outings.length === 0 && !calc && !start && (
          <EmptyState testID="mr-empty" icon="shield-checkmark-outline" title={t('empty_pn_title', lang)} sub={t('empty_pn_sub', lang)} />
        )}

        {outings.length > 0 && (
          <View style={[styles.statusCard, status.active && (status as any).left <= 15 && { borderColor: C.error }]}>
            <Ionicons name={status.active ? 'walk' : 'home'} size={22} color={status.active ? ((status as any).left <= 15 ? C.error : '#5FA779') : C.brand} />
            <View style={{ flex: 1 }}>
              <Text style={styles.statusTitle}>
                {status.active
                  ? (status as any).left <= 15 ? `VRÁŤTE SA DOMOV — koniec o ${(status as any).left} min` : `VYCHÁDZKA AKTÍVNA · zostáva ${(status as any).left} min`
                  : 'STE V REŽIME DOMA'}
              </Text>
              <Text style={styles.statusSub}>
                {status.active ? `Okno ${(status as any).window}` : (status as any).next ? `Najbližšia vychádzka: ${(status as any).next}` : 'Dnes už žiadna vychádzka'}
              </Text>
            </View>
          </View>
        )}

        <Text style={styles.section}>ePN ZÁZNAM</Text>
        <View style={styles.row2}>
          <DateField testID="mr-start" title="ZAČIATOK PN" value={start} onChange={setStart} placeholder="Začiatok PN" style={[styles.input, { flex: 1 }]} />
          <DateField testID="mr-end" title="KONIEC PN (ODHAD)" value={end} onChange={setEnd} placeholder="Koniec (odhad)" style={[styles.input, { flex: 1 }]} />
        </View>
        <View style={styles.row2}>
          {CONTRACTS.map(([k, l]) => (
            <Pressable key={k} testID={`mr-contract-${k}`} onPress={() => setContract(k)} style={[styles.chip, contract === k && { backgroundColor: C.brand, borderColor: C.brand }]}>
              <Text style={[styles.chipText, contract === k && { color: C.onInverse }]}>{l}</Text>
            </Pressable>
          ))}
          <WheelField testID="mr-gross" title="HRUBÁ MZDA €" min={300} max={5000} step={10} unit="€" value={gross} onChange={setGross} placeholder="Hrubá mzda €" style={[styles.input, { flex: 1 }]} />
        </View>
        <TextInput testID="mr-note" style={styles.input} placeholder="Poznámka o zotavení (napr. koleno po artroskopii)" placeholderTextColor={C.info} value={note} onChangeText={setNote} />

        <Text style={styles.section}>VYCHÁDZKY (POVOLENÉ HODINY)</Text>
        {outings.map((o, i) => (
          <View key={i} style={styles.outRow}>
            <Ionicons name="time-outline" size={16} color={C.brand} />
            <Text style={styles.outText}>{o.from_time} – {o.to_time}</Text>
            <View style={{ flex: 1 }} />
            <Pressable testID={`mr-out-del-${i}`} onPress={() => setOutings(outings.filter((_, j) => j !== i))} hitSlop={8}>
              <Ionicons name="trash-outline" size={16} color={C.info} />
            </Pressable>
          </View>
        ))}
        <View style={styles.row2}>
          <TimeField testID="mr-out-from" title="VYCHÁDZKA OD" value={oFrom} onChange={setOFrom} placeholder="Od" style={[styles.input, { flex: 1 }]} />
          <TimeField testID="mr-out-to" title="VYCHÁDZKA DO" value={oTo} onChange={setOTo} placeholder="Do" style={[styles.input, { flex: 1 }]} />
          <Pressable testID="mr-out-add" onPress={addOuting} style={styles.addBtn}><Ionicons name="add" size={20} color={C.onInverse} /></Pressable>
        </View>
        <Pressable testID="mr-ai-toggle" onPress={() => setShowAi(!showAi)} style={styles.aiToggle}>
          <Ionicons name="sparkles-outline" size={15} color={C.brand} />
          <Text style={styles.aiToggleText}>JARVIS: VYČÍTAŤ VYCHÁDZKY Z POTVRDENIA</Text>
        </Pressable>
        {showAi && (
          <View style={{ gap: S.sm }}>
            <TextInput testID="mr-ai-text" style={[styles.input, { minHeight: 90, textAlignVertical: 'top', paddingTop: S.md }]} multiline placeholder="Vložte text z ePN / potvrdenia lekára…" placeholderTextColor={C.info} value={aiText} onChangeText={setAiText} />
            <Pressable testID="mr-ai-run" onPress={extractAi} disabled={busy === 'ai'} style={styles.ctaOutline}>
              {busy === 'ai' ? <ActivityIndicator color={C.brand} /> : <Text style={styles.ctaOutlineText}>EXTRAHOVAŤ (AI)</Text>}
            </Pressable>
          </View>
        )}

        <View style={styles.row2}>
          <Pressable testID="mr-save" onPress={save} disabled={busy === 'save'} style={[styles.cta, { flex: 1 }]}>
            {busy === 'save' ? <ActivityIndicator color={C.onInverse} /> : <Text style={styles.ctaText}>ULOŽIŤ ePN</Text>}
          </Pressable>
          <Pressable testID="mr-alerts" onPress={scheduleAlerts} style={[styles.ctaOutline, { flex: 1 }]}>
            <Ionicons name="alarm-outline" size={15} color={C.brand} />
            <Text style={styles.ctaOutlineText}>UPOZORNENIA</Text>
          </Pressable>
        </View>

        <Text style={styles.section}>KALKULAČKA NEMOCENSKÉHO</Text>
        <View style={styles.row2}>
          <WheelField testID="mr-days" title="POČET DNÍ PN" min={1} max={365} unit="dní" value={days} onChange={setDays} placeholder="Počet dní PN" style={[styles.input, { flex: 1 }]} />
          <Pressable testID="mr-calc" onPress={runCalc} disabled={busy === 'calc'} style={[styles.cta, { flex: 1 }]}>
            {busy === 'calc' ? <ActivityIndicator color={C.onInverse} /> : <Text style={styles.ctaText}>VYPOČÍTAŤ</Text>}
          </Pressable>
        </View>
        {calc && (
          <View style={styles.calcBox}>
            {calc.breakdown.map((b: any, i: number) => (
              <View key={i} style={styles.calcRow}>
                <Text style={styles.calcLabel}>{b.period}</Text>
                <Text style={styles.calcVal}>{b.amount} €</Text>
              </View>
            ))}
            <View style={[styles.calcRow, { borderTopWidth: 1, borderTopColor: C.border, paddingTop: S.sm }]}>
              <Text style={[styles.calcLabel, { fontWeight: '900', color: C.fg }]}>ODHAD SPOLU ({calc.days} dní)</Text>
              <Text style={[styles.calcVal, { color: C.brand, fontSize: 15 }]}>{calc.total_estimate} €</Text>
            </View>
            <View style={styles.calcRow}>
              <Text style={styles.calcLabel}>Výpadok príjmu</Text>
              <Text style={[styles.calcVal, { color: calc.shortfall_pct >= 30 ? C.error : C.fg }]}>−{calc.shortfall} € ({calc.shortfall_pct} %)</Text>
            </View>
            {calc.solidarity_suggested && (
              <Pressable testID="mr-solidarity" onPress={() => router.push('/solidarity')} style={styles.solBox}>
                <Ionicons name="people-outline" size={16} color={C.onWarn} />
                <Text style={styles.solText}>Výpadok nad 30 % — zvážte kampaň v Solidarity Hub</Text>
              </Pressable>
            )}
            {calc.warnings.map((w: string, i: number) => <Text key={i} style={styles.warn}>⚠ {w}</Text>)}
            <Text style={styles.disclaimer}>{calc.disclaimer}</Text>
          </View>
        )}

        <Text style={styles.section}>HLÁSENIA JEDNÝM ŤUKOM (PDF)</Text>
        <View style={styles.row2}>
          <Pressable testID="mr-pdf-employer" onPress={() => pdf('employer')} disabled={!rec || busy === 'pdf-employer'} style={[styles.ctaOutline, { flex: 1 }, !rec && { opacity: 0.5 }]}>
            {busy === 'pdf-employer' ? <ActivityIndicator color={C.brand} /> : <Text style={styles.ctaOutlineText}>ZAMESTNÁVATEĽ</Text>}
          </Pressable>
          <Pressable testID="mr-pdf-social" onPress={() => pdf('social')} disabled={!rec || busy === 'pdf-social'} style={[styles.ctaOutline, { flex: 1 }, !rec && { opacity: 0.5 }]}>
            {busy === 'pdf-social' ? <ActivityIndicator color={C.brand} /> : <Text style={styles.ctaOutlineText}>SOC. POISŤOVŇA</Text>}
          </Pressable>
        </View>
        <Text style={styles.disclaimer}>Hlásenia sú informačné dokumenty — nenahrádzajú oficiálne tlačivá, kým ich úrad neakceptuje.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 14 },
  h1: { fontSize: 24, fontWeight: '900', color: C.fg },
  sub: { marginTop: S.sm, fontSize: 13, color: C.onS3, lineHeight: 19 },
  section: { marginTop: S.xl, marginBottom: S.sm, fontSize: 11, letterSpacing: 2, color: C.info, fontWeight: '800' },
  statusCard: { marginTop: S.lg, flexDirection: 'row', alignItems: 'center', gap: S.md, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1.5, borderColor: C.brand, padding: S.lg },
  statusTitle: { color: C.fg, fontWeight: '900', fontSize: 13, letterSpacing: 0.5 },
  statusSub: { color: C.info, fontSize: 11, marginTop: 2 },
  row2: { flexDirection: 'row', gap: S.sm, marginBottom: S.sm, alignItems: 'center' },
  input: { backgroundColor: C.surface2, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, color: C.fg, paddingHorizontal: S.md, minHeight: 46, fontSize: 13, marginBottom: S.sm },
  chip: { borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.pill, paddingHorizontal: S.md, paddingVertical: 12, marginBottom: S.sm },
  chipText: { color: C.fg, fontWeight: '800', fontSize: 11 },
  outRow: { flexDirection: 'row', alignItems: 'center', gap: S.sm, backgroundColor: C.surface2, borderRadius: R.sm, padding: S.md, marginBottom: 6 },
  outText: { color: C.fg, fontWeight: '800', fontSize: 13 },
  addBtn: { width: 46, height: 46, borderRadius: R.sm, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center', marginBottom: S.sm },
  aiToggle: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: S.sm, minHeight: 44 },
  aiToggleText: { color: C.brand, fontWeight: '900', fontSize: 10.5, letterSpacing: 1 },
  cta: { flexDirection: 'row', gap: 6, backgroundColor: C.brand, borderRadius: R.sm, minHeight: 48, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  ctaOutline: { flexDirection: 'row', gap: 6, borderWidth: 1.5, borderColor: C.brand, borderRadius: R.sm, minHeight: 48, alignItems: 'center', justifyContent: 'center' },
  ctaOutlineText: { color: C.brand, fontWeight: '900', letterSpacing: 1, fontSize: 11 },
  calcBox: { backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.lg, gap: S.sm },
  calcRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: S.md },
  calcLabel: { color: C.onS3, fontSize: 12, flex: 1 },
  calcVal: { color: C.fg, fontWeight: '900', fontSize: 13 },
  solBox: { flexDirection: 'row', alignItems: 'center', gap: S.sm, backgroundColor: C.warn, borderRadius: R.sm, padding: S.md, minHeight: 44 },
  solText: { color: C.onWarn, fontWeight: '800', fontSize: 11, flex: 1 },
  warn: { color: C.warn, fontSize: 11, lineHeight: 16 },
  disclaimer: { marginTop: S.md, color: C.info, fontSize: 10, lineHeight: 15 },
  err: { color: C.error, marginTop: S.md, fontSize: 12 },
  info: { color: '#5FA779', marginTop: S.md, fontSize: 12 },
});
