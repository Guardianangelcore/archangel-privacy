/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { DateField } from '@/src/ui/fields';
import { C, S, R } from '@/src/theme';

const CATS: any = {
  exam: { label: 'VYŠETRENIE', icon: 'medkit-outline', color: '#D4AF37' },
  history: { label: 'HISTÓRIA', icon: 'bandage-outline', color: '#8E8E93' },
  vaccine: { label: 'VAKCÍNA', icon: 'shield-checkmark-outline', color: '#5FA779' },
};

export default function HealthTimeline() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [filter, setFilter] = useState<string>('all');
  const [adding, setAdding] = useState(false);
  const [cat, setCat] = useState('exam');
  const [title, setTitle] = useState('');
  const [date, setDate] = useState('');
  const [booster, setBooster] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const load = async (f = filter) => {
    try { setData(await api(`/calendar/timeline${f !== 'all' ? `?category=${f}` : ''}`)); } catch (e: any) { setErr(String(e.message || e)); }
  };
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const setF = (f: string) => { setFilter(f); load(f); };

  const add = async () => {
    if (!title.trim() || !/^\d{4}-\d{2}-\d{2}$/.test(date)) { setErr('Zadajte názov a dátum vo formáte RRRR-MM-DD.'); return; }
    setBusy(true); setErr('');
    try {
      await api('/calendar/events', { method: 'POST', body: JSON.stringify({ category: cat, title: title.trim(), date, booster_due: cat === 'vaccine' && booster ? booster : null }) });
      setTitle(''); setDate(''); setBooster(''); setAdding(false);
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(false); }
  };

  const del = async (id: string) => {
    try { await api(`/calendar/events/${id}`, { method: 'DELETE' }); await load(); } catch {}
  };

  const events = data?.events || [];

  return (
    <SafeAreaView testID="health-timeline-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="ht-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>HEALTH TIMELINE</Text>
        <Pressable testID="ht-add" onPress={() => setAdding(!adding)} hitSlop={12}>
          <Ionicons name={adding ? 'close' : 'add'} size={26} color={C.brand} />
        </Pressable>
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
        <Text style={styles.h1}>Životný zdravotný kalendár</Text>
        <Text style={styles.sub}>Vyšetrenia, zdravotná história a očkovania na jednej časovej osi.</Text>
        {!!err && <Text style={styles.err}>{err}</Text>}

        {(data?.booster_alerts || []).length > 0 && (
          <View style={styles.alertBox}>
            <Ionicons name="alarm-outline" size={18} color={C.onWarn} />
            <View style={{ flex: 1 }}>
              <Text style={styles.alertTitle}>BLÍŽIACE SA PRESKOČKOVANIE</Text>
              {data.booster_alerts.map((b: any) => (
                <Text key={b.event_id} style={styles.alertText}>• {b.title} — booster do {b.booster_due}</Text>
              ))}
            </View>
          </View>
        )}

        {adding && (
          <View style={styles.addBox}>
            <View style={{ flexDirection: 'row', gap: S.sm }}>
              {Object.keys(CATS).map(k => (
                <Pressable key={k} testID={`ht-cat-${k}`} onPress={() => setCat(k)} style={[styles.catChip, cat === k && { backgroundColor: C.brand, borderColor: C.brand }]}>
                  <Text style={[styles.catChipText, cat === k && { color: C.onInverse }]}>{CATS[k].label}</Text>
                </Pressable>
              ))}
            </View>
            <TextInput testID="ht-title" style={styles.input} placeholder={cat === 'vaccine' ? 'Vakcína (napr. Tetanus)' : cat === 'history' ? 'Choroba / úraz (napr. Zlomenina)' : 'Vyšetrenie (napr. Kardiológia)'} placeholderTextColor={C.info} value={title} onChangeText={setTitle} />
            <DateField testID="ht-date" title="DÁTUM" value={date} onChange={setDate} placeholder="Dátum" style={styles.input} />
            {cat === 'vaccine' && (
              <DateField testID="ht-booster" title="BOOSTER DO" value={booster} onChange={setBooster} placeholder="Booster do (voliteľné)" style={styles.input} />
            )}
            <Pressable testID="ht-save" onPress={add} disabled={busy} style={styles.cta}>
              {busy ? <ActivityIndicator color={C.onInverse} /> : <Text style={styles.ctaText}>ULOŽIŤ ZÁZNAM</Text>}
            </Pressable>
          </View>
        )}

        <View style={styles.filterRow}>
          {[['all', 'VŠETKO'], ['exam', 'VYŠETRENIA'], ['history', 'HISTÓRIA'], ['vaccine', 'VAKCÍNY']].map(([k, l]) => (
            <Pressable key={k} testID={`ht-filter-${k}`} onPress={() => setF(k)} style={[styles.fChip, filter === k && { backgroundColor: C.brand, borderColor: C.brand }]}>
              <Text style={[styles.fChipText, filter === k && { color: C.onInverse }]}>{l}</Text>
            </Pressable>
          ))}
        </View>

        {!data && <ActivityIndicator color={C.brand} style={{ marginTop: 40 }} />}
        {data && events.length === 0 && <Text style={styles.hint}>Žiadne záznamy. Pridajte prvý cez + alebo nechajte Auto-Booker rezervovať termín.</Text>}

        <View style={{ marginTop: S.lg }}>
          {events.map((e: any, i: number) => {
            const ui = CATS[e.category] || CATS.exam;
            const future = e.date >= (data?.today || '');
            return (
              <View key={e.event_id} style={styles.tlRow}>
                <View style={styles.tlLeft}>
                  <View style={[styles.tlDot, { backgroundColor: ui.color }]} />
                  {i < events.length - 1 && <View style={styles.tlLine} />}
                </View>
                <View style={[styles.tlCard, future && { borderColor: C.brand }]}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.sm }}>
                    <Ionicons name={ui.icon} size={16} color={ui.color} />
                    <Text style={[styles.tlCat, { color: ui.color }]}>{ui.label}{future ? ' · NADCHÁDZA' : ''}</Text>
                    <View style={{ flex: 1 }} />
                    <Pressable testID={`ht-del-${e.event_id}`} onPress={() => del(e.event_id)} hitSlop={8}>
                      <Ionicons name="trash-outline" size={15} color={C.info} />
                    </Pressable>
                  </View>
                  <Text style={styles.tlTitle}>{e.title}</Text>
                  <Text style={styles.tlDate}>{e.date}{e.booster_due ? ` · booster: ${e.booster_due}` : ''}{e.notes ? ` · ${e.notes}` : ''}</Text>
                </View>
              </View>
            );
          })}
        </View>
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
  alertBox: { marginTop: S.lg, flexDirection: 'row', gap: S.md, backgroundColor: C.warn, borderRadius: R.md, padding: S.md },
  alertTitle: { color: C.onWarn, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  alertText: { color: C.onWarn, fontSize: 12, marginTop: 2, fontWeight: '700' },
  addBox: { marginTop: S.lg, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.brand, padding: S.md, gap: S.sm },
  catChip: { flex: 1, borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.pill, paddingVertical: 8, alignItems: 'center' },
  catChipText: { color: C.fg, fontWeight: '800', fontSize: 10, letterSpacing: 0.5 },
  input: { backgroundColor: C.bg, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, color: C.fg, paddingHorizontal: S.md, minHeight: 46, fontSize: 13 },
  cta: { backgroundColor: C.brand, borderRadius: R.sm, minHeight: 48, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
  filterRow: { flexDirection: 'row', gap: S.sm, marginTop: S.lg },
  fChip: { borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.pill, paddingHorizontal: S.md, paddingVertical: 8 },
  fChipText: { color: C.fg, fontWeight: '800', fontSize: 10, letterSpacing: 0.5 },
  hint: { marginTop: S.lg, color: C.onS3, fontSize: 12, lineHeight: 18 },
  tlRow: { flexDirection: 'row', gap: S.md },
  tlLeft: { width: 20, alignItems: 'center' },
  tlDot: { width: 12, height: 12, borderRadius: 6, marginTop: 18 },
  tlLine: { flex: 1, width: 2, backgroundColor: C.border, marginTop: 4 },
  tlCard: { flex: 1, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.md, marginBottom: S.md },
  tlCat: { fontWeight: '900', fontSize: 9, letterSpacing: 1 },
  tlTitle: { color: C.fg, fontWeight: '800', fontSize: 14, marginTop: 4 },
  tlDate: { color: C.info, fontSize: 11, marginTop: 2 },
  err: { color: C.error, marginTop: S.md, fontSize: 12 },
});
