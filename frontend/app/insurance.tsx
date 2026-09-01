/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { api } from '@/src/api';
import { WheelField, DateField } from '@/src/ui/fields';
import { C, S, R } from '@/src/theme';

const TYPES: [string, string][] = [['health', 'Health'], ['life', 'Life'], ['disability', 'Disability'], ['property', 'Property']];
const TYPE_ICON: Record<string, string> = { health: 'medkit', life: 'heart', disability: 'accessibility', property: 'home' };

export default function Insurance() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [provider, setProvider] = useState('');
  const [ptype, setPtype] = useState('health');
  const [premium, setPremium] = useState('');
  const [paidUntil, setPaidUntil] = useState('');
  const [ingestText, setIngestText] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    try { setData(await api('/insurance/policies')); } catch (e: any) { setErr(String(e.message || e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const hap = () => { if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {}); };

  const add = async () => {
    if (!provider.trim()) { setErr('Enter the insurer.'); return; }
    hap(); setBusy('add'); setErr(''); setMsg('');
    try {
      await api('/insurance/policies', { method: 'POST', body: JSON.stringify({ provider, type: ptype, premium_monthly: parseFloat(premium) || 0, paid_until: paidUntil || null }) });
      setProvider(''); setPremium(''); setPaidUntil(''); setMsg('Policy added ✓');
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const ingest = async () => {
    if (!ingestText.trim()) return;
    hap(); setBusy('ingest'); setErr(''); setMsg('');
    try {
      const r: any = await api('/insurance/ingest', { method: 'POST', body: JSON.stringify({ text: ingestText }) });
      if (r.found) { setMsg(`Jarvis ${r.action === 'created' ? 'created' : 'updated'} the policy: ${r.policy.provider} (${r.policy.status === 'paid' ? 'paid' : 'po splatnosti'})`); setIngestText(''); await load(); }
      else setErr(r.hint || 'Not recognized — try phrasing it differently.');
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const del = async (id: string) => {
    hap();
    try { await api(`/insurance/policies/${id}`, { method: 'DELETE' }); await load(); } catch {}
  };

  return (
    <SafeAreaView testID="insurance-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="ins-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>INSURANCE GUARD</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
        <Text style={styles.h1}>Sovereign Insurance Guardian</Text>
        <Text style={styles.sub}>Who insures you, what it covers and whether it is paid — watched by the Wealth Sentinel 24/7.</Text>
        {!!msg && <Text style={styles.info}>{msg}</Text>}
        {!!err && <Text style={styles.err}>{err}</Text>}

        {data?.hunter_warning && (
          <View testID="ins-hunter-warning" style={styles.warnBox}>
            <Ionicons name="warning" size={18} color={C.error} />
            <Text style={styles.warnText}>{data.hunter_warning}</Text>
          </View>
        )}
        {data?.microloan_suggested && (
          <Pressable testID="ins-microloan" onPress={() => { hap(); router.push('/solidarity'); }} style={styles.loanBox}>
            <Ionicons name="people" size={18} color={C.brand} />
            <Text style={styles.loanText}>Policy overdue? The Solidarity Hub offers a micro-loan so your coverage never lapses.</Text>
            <Ionicons name="chevron-forward" size={16} color={C.brand} />
          </Pressable>
        )}

        <Text style={styles.section}>MOJE POISTKY {data ? `· ${data.policies.length}` : ''}</Text>
        {(data?.policies || []).map((p: any) => (
          <View key={p.policy_id} style={[styles.polRow, p.status === 'overdue' && { borderColor: C.error, borderWidth: 1.5 }]}>
            <Ionicons name={(TYPE_ICON[p.type] || 'shield') as any} size={22} color={p.status === 'paid' ? C.brand : C.error} />
            <View style={{ flex: 1 }}>
              <Text style={styles.polTitle}>{p.provider}</Text>
              <Text style={styles.polSub}>{TYPES.find(t2 => t2[0] === p.type)?.[1] || p.type}{p.premium_monthly ? ` · ${p.premium_monthly} ${p.currency}/mo.` : ''}{p.paid_until ? ` · until ${p.paid_until}` : ' · no date'}</Text>
            </View>
            <View style={[styles.statusChip, { backgroundColor: p.status === 'paid' ? '#5FA779' : C.error }]}>
              <Text style={styles.statusText}>{p.status === 'paid' ? 'PAID' : 'OVERDUE'}</Text>
            </View>
            <Pressable testID={`ins-del-${p.policy_id}`} onPress={() => del(p.policy_id)} hitSlop={8}>
              <Ionicons name="trash-outline" size={16} color={C.info} />
            </Pressable>
          </View>
        ))}
        {data && data.policies.length === 0 && <Text style={styles.empty}>No policies yet — add one manually or just tell Jarvis below.</Text>}

        <Text style={styles.section}>🧠 POVEDZTE TO JARVISOVI</Text>
        <TextInput
          testID="ins-ingest-text"
          style={[styles.input, { minHeight: 70, textAlignVertical: 'top', paddingTop: S.md }]}
          multiline
          placeholder='E.g.: "My health insurance is with Dovera, paid until December."'
          placeholderTextColor={C.info}
          value={ingestText}
          onChangeText={setIngestText}
        />
        <Pressable testID="ins-ingest-run" onPress={ingest} disabled={busy === 'ingest'} style={styles.cta}>
          {busy === 'ingest' ? <ActivityIndicator color={C.onInverse} /> : <Text style={styles.ctaText}>PROCESS (AI)</Text>}
        </Pressable>

        <Text style={styles.section}>ADD MANUALLY</Text>
        <View style={styles.row2}>
          {TYPES.map(([k, l]) => (
            <Pressable key={k} testID={`ins-type-${k}`} onPress={() => { hap(); setPtype(k); }} style={[styles.chip, ptype === k && { backgroundColor: C.brand, borderColor: C.brand }]}>
              <Text style={[styles.chipText, ptype === k && { color: C.onInverse }]}>{l}</Text>
            </Pressable>
          ))}
        </View>
        <TextInput testID="ins-provider" style={styles.input} placeholder="Insurer (e.g. Dovera)" placeholderTextColor={C.info} value={provider} onChangeText={setProvider} />
        <View style={styles.row2}>
          <WheelField testID="ins-premium" title="PREMIUM €/MO." min={0} max={500} unit="€" value={premium} onChange={setPremium} placeholder="Premium €/mo." style={[styles.input, { flex: 1 }]} />
          <DateField testID="ins-paid-until" title="PAID UNTIL" value={paidUntil} onChange={setPaidUntil} placeholder="Paid until" style={[styles.input, { flex: 1 }]} />
        </View>
        <Pressable testID="ins-add" onPress={add} disabled={busy === 'add'} style={styles.cta}>
          {busy === 'add' ? <ActivityIndicator color={C.onInverse} /> : <Text style={styles.ctaText}>SAVE POLICY</Text>}
        </Pressable>

        <Text style={styles.section}>GLOBAL INSURER TEMPLATES</Text>
        {(data?.templates || []).map((tpl: any) => (
          <View key={tpl.region} style={{ marginBottom: S.sm }}>
            <Text style={styles.tplRegion}>{tpl.region}</Text>
            <View style={styles.tplRow}>
              {tpl.providers.map((pr: string) => (
                <Pressable key={pr} testID={`ins-tpl-${pr}`} onPress={() => { hap(); setProvider(pr); }} style={styles.tplChip}>
                  <Text style={styles.tplText}>{pr}</Text>
                </Pressable>
              ))}
            </View>
          </View>
        ))}
        <Text style={styles.disclaimer}>The Wealth Sentinel checks due dates every 2 minutes. If a policy lapses you get a Jarvis alarm and the Waitlist Hunter shows a warning during bookings.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 14 },
  h1: { fontSize: 24, fontWeight: '900', color: C.fg },
  sub: { marginTop: S.sm, fontSize: 12.5, color: C.onS3, lineHeight: 18 },
  section: { marginTop: S.xl, marginBottom: S.sm, fontSize: 11, letterSpacing: 1.5, color: C.brand, fontWeight: '900' },
  warnBox: { flexDirection: 'row', alignItems: 'center', gap: S.sm, backgroundColor: 'rgba(200,60,60,0.12)', borderWidth: 1, borderColor: C.error, borderRadius: R.sm, padding: S.md, marginTop: S.md },
  warnText: { flex: 1, color: C.error, fontSize: 11.5, lineHeight: 16, fontWeight: '700' },
  loanBox: { flexDirection: 'row', alignItems: 'center', gap: S.sm, borderWidth: 1.5, borderColor: C.brand, borderRadius: R.sm, padding: S.md, marginTop: S.sm },
  loanText: { flex: 1, color: C.fg, fontSize: 11.5, lineHeight: 16 },
  polRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, backgroundColor: C.surface2, borderRadius: R.sm, padding: S.md, marginTop: S.sm },
  polTitle: { color: C.fg, fontWeight: '800', fontSize: 13 },
  polSub: { color: C.info, fontSize: 10.5, marginTop: 2 },
  statusChip: { borderRadius: R.sm, paddingHorizontal: 8, paddingVertical: 5 },
  statusText: { color: C.onInverse, fontSize: 8.5, fontWeight: '900', letterSpacing: 0.5 },
  empty: { color: C.onS3, fontSize: 12.5, marginTop: 4 },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.sm, paddingHorizontal: S.md, minHeight: 48, color: C.fg, backgroundColor: C.surface2, marginTop: S.sm, fontSize: 13 },
  row2: { flexDirection: 'row', gap: S.sm, marginTop: S.sm, flexWrap: 'wrap' },
  chip: { borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.sm, paddingHorizontal: S.md, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  chipText: { color: C.fg, fontWeight: '800', fontSize: 11 },
  cta: { marginTop: S.md, backgroundColor: C.inverse, borderRadius: R.sm, minHeight: 50, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
  tplRegion: { color: C.info, fontSize: 10, fontWeight: '900', letterSpacing: 1, marginBottom: 4 },
  tplRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  tplChip: { borderWidth: 1, borderColor: C.border, borderRadius: R.pill, paddingHorizontal: S.md, paddingVertical: 8, backgroundColor: C.surface2 },
  tplText: { color: C.fg, fontSize: 11, fontWeight: '700' },
  info: { color: '#5FA779', marginTop: S.md, fontSize: 12 },
  err: { color: C.error, marginTop: S.md, fontSize: 12 },
  disclaimer: { marginTop: S.xl, color: C.info, fontSize: 10, lineHeight: 15, textAlign: 'center' },
});
