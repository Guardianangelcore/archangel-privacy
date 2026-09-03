/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// CRISIS PROTOCOLS — step-by-step survival checklists (blackout · medical · evacuation · heatwave ·
// pandemic · digital). Check state is saved per user. Sentinel+ (Guardian/Sovereign see the paywall).
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';
import { tap } from '@/src/ui/glass';
import Paywall from '@/src/Paywall';
import { syncSeasonalReminders } from '@/src/seasonal-reminder';

type Proto = { id: string; icon: any; title: string; steps: string[]; done: number[]; progress: number };

// OFFLINE PROTOCOLS — the checklists are cached on the device after the first successful load
// so they open during a total blackout (no internet). Ticks made offline are applied locally
// and replayed to the server on the next online load.
const CACHE_KEY = 'ga.crisis.protocols.v1';
const PENDING_KEY = 'ga.crisis.pending.v1';
type Pending = { pid: string; idx: number }[];
const saveCache = (p: Proto[]) => AsyncStorage.setItem(CACHE_KEY, JSON.stringify({ at: Date.now(), protocols: p })).catch(() => {});
const readCache = async (): Promise<{ at: number; protocols: Proto[] } | null> => {
  try { const raw = await AsyncStorage.getItem(CACHE_KEY); return raw ? JSON.parse(raw) : null; } catch { return null; }
};
const readPending = async (): Promise<Pending> => { try { return JSON.parse((await AsyncStorage.getItem(PENDING_KEY)) || '[]'); } catch { return []; } };
const writePending = (p: Pending) => AsyncStorage.setItem(PENDING_KEY, JSON.stringify(p)).catch(() => {});
const applyLocal = (list: Proto[], pid: string, idx: number) => list.map(p => {
  if (p.id !== pid) return p;
  const done = p.done.includes(idx) ? p.done.filter(i => i !== idx) : [...p.done, idx].sort((a, b) => a - b);
  return { ...p, done, progress: Math.round((done.length / p.steps.length) * 100) / 100 };
});

export default function CrisisProtocols() {
  const { t: tt, tx, lang } = useI18n();
  const router = useRouter();
  const [protos, setProtos] = useState<Proto[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [locked, setLocked] = useState(false);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');
  const [offline, setOffline] = useState<'cached' | 'serving' | null>(null);   // ✓ available offline · serving from cache

  const load = async () => {
    setErr('');
    try {
      // replay ticks made while offline, then fetch fresh state
      const pending = await readPending();
      for (const t of pending) { try { await api(`/survival/protocols/${t.pid}/steps/${t.idx}`, { method: 'PUT' }); } catch {} }
      if (pending.length) await writePending([]);
      const r: any = await api('/survival/protocols');
      const list: Proto[] = r.protocols || [];
      setProtos(list); if (!open && list.length) setOpen(list[0].id);
      await saveCache(list); setOffline('cached');
      syncSeasonalReminders(list, lang);
    } catch (e: any) {
      const m = String(e?.message || e);
      if (/^402:/.test(m)) { setLocked(true); return; }
      const c = await readCache();   // blackout / no network → serve the local copy
      if (c?.protocols?.length) { setProtos(c.protocols); if (!open) setOpen(c.protocols[0].id); setOffline('serving'); }
      else setErr(m);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggle = async (pid: string, idx: number) => {
    tap('light'); setBusy(`${pid}-${idx}`);
    try {
      const r: any = await api(`/survival/protocols/${pid}/steps/${idx}`, { method: 'PUT' });
      setProtos(prev => { const next = prev.map(p => (p.id === pid ? { ...p, done: r.done, progress: r.progress } : p)); saveCache(next); syncSeasonalReminders(next, lang); return next; });
    } catch (e: any) {
      const m = String(e?.message || e);
      if (/^402:/.test(m)) { setLocked(true); return; }
      // offline → tick locally, persist, queue for replay
      setProtos(prev => { const next = applyLocal(prev, pid, idx); saveCache(next); return next; });
      const pending = await readPending(); await writePending([...pending, { pid, idx }]); setOffline('serving');
    } finally { setBusy(null); }
  };

  return (
    <SafeAreaView testID="crisis-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="cp-back" onPress={() => { tap(); router.back(); }} hitSlop={12}><Ionicons name="chevron-back" size={24} color={C.fg} /></Pressable>
        <Text style={st.title}>{tt('crisis.crisis_protocols')}</Text>
        <View style={{ width: 24 }} />
      </View>

      {locked ? (
        <View testID="cp-paywall" style={{ padding: S.lg }}>
          <Paywall tier="sentinel" message={tt('crisis.crisis_protocols') + ' — Sentinel'} onUnlocked={() => { setLocked(false); load(); }} />
        </View>
      ) : (
        <ScrollView contentContainerStyle={st.body}>
          <Text style={st.sub}>{tt('crisis.tick_each_step_as_you_prepare')}</Text>
          {!!offline && (
            <View testID="cp-offline" style={[st.offline, offline === 'serving' && st.offlineServing]}>
              <Ionicons name={offline === 'serving' ? 'cloud-offline-outline' : 'cloud-done-outline'} size={14} color={offline === 'serving' ? C.warn : '#5FA779'} />
              <Text style={[st.offlineText, offline === 'serving' && { color: C.warn }]}>
                {offline === 'serving' ? tt('crisis.offline_showing_saved_copy') : tt('crisis.offline_available')}
              </Text>
            </View>
          )}
          {loading && <ActivityIndicator color={C.brand} style={{ marginTop: S.xl }} />}
          {!!err && <Text style={st.err}>{err}</Text>}
          {protos.map(p => {
            const isOpen = open === p.id;
            const pct = Math.round(p.progress * 100);
            return (
              <View key={p.id} testID={`cp-proto-${p.id}`} style={[st.card, pct === 100 && { borderColor: '#5FA779' }]}>
                <Pressable testID={`cp-toggle-${p.id}`} onPress={() => { tap('light'); setOpen(isOpen ? null : p.id); }} style={st.cardHead}>
                  <Ionicons name={p.icon} size={20} color={pct === 100 ? '#5FA779' : C.brand} />
                  <View style={{ flex: 1 }}>
                    <Text style={st.cardTitle}>{tx(p.title)}</Text>
                    <View style={st.bar}><View style={[st.barFill, { width: `${pct}%` as any, backgroundColor: pct === 100 ? '#5FA779' : C.brand }]} /></View>
                  </View>
                  <Text style={st.pct}>{p.done.length}/{p.steps.length}</Text>
                  <Ionicons name={isOpen ? 'chevron-up' : 'chevron-down'} size={18} color={C.info} />
                </Pressable>
                {isOpen && p.steps.map((s, i) => {
                  const on = p.done.includes(i);
                  return (
                    <Pressable key={i} testID={`cp-step-${p.id}-${i}`} onPress={() => toggle(p.id, i)} disabled={busy === `${p.id}-${i}`} style={st.step}>
                      <Ionicons name={on ? 'checkbox' : 'square-outline'} size={22} color={on ? '#5FA779' : C.info} />
                      <Text style={[st.stepText, on && st.stepDone]}>{tx(s)}</Text>
                    </Pressable>
                  );
                })}
              </View>
            );
          })}
          <Text style={st.footer}>{tt('crisis.emergency_112_ambulance_155_police')}</Text>
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
  sub: { color: C.info, fontSize: 12, marginBottom: S.xs },
  offline: { flexDirection: 'row', alignItems: 'center', gap: 6, alignSelf: 'flex-start', paddingHorizontal: S.md, paddingVertical: 6, borderRadius: R.pill, borderWidth: 1, borderColor: '#5FA779', backgroundColor: 'rgba(95,167,121,0.10)' },
  offlineServing: { borderColor: C.warn, backgroundColor: 'rgba(255,183,77,0.10)' },
  offlineText: { color: '#5FA779', fontWeight: '800', fontSize: 11 },
  err: { color: C.error, textAlign: 'center' },
  card: { borderRadius: R.md, borderWidth: 1, borderColor: C.border, backgroundColor: 'rgba(255,255,255,0.04)', overflow: 'hidden' },
  cardHead: { flexDirection: 'row', alignItems: 'center', gap: S.md, padding: S.md, minHeight: 56 },
  cardTitle: { color: C.fg, fontWeight: '800', fontSize: 14 },
  bar: { height: 4, borderRadius: 2, backgroundColor: 'rgba(255,255,255,0.08)', marginTop: 6, overflow: 'hidden' },
  barFill: { height: 4, borderRadius: 2 },
  pct: { color: C.info, fontWeight: '800', fontSize: 12 },
  step: { flexDirection: 'row', alignItems: 'flex-start', gap: S.md, paddingHorizontal: S.md, paddingVertical: S.sm, minHeight: 44, borderTopWidth: 1, borderTopColor: C.border },
  stepText: { flex: 1, color: C.fg, fontSize: 13, lineHeight: 19 },
  stepDone: { color: C.info, textDecorationLine: 'line-through' },
  footer: { color: C.warn, fontWeight: '800', fontSize: 12, textAlign: 'center', marginTop: S.md },
});
