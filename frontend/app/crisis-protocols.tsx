/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// CRISIS PROTOCOLS — step-by-step survival checklists (blackout · medical · evacuation · heatwave ·
// pandemic · digital). Check state is saved per user. Sentinel+ (Guardian/Sovereign see the paywall).
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';
import { tap } from '@/src/ui/glass';
import Paywall from '@/src/Paywall';

type Proto = { id: string; icon: any; title: string; steps: string[]; done: number[]; progress: number };

export default function CrisisProtocols() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const [protos, setProtos] = useState<Proto[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [locked, setLocked] = useState(false);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');

  const load = async () => {
    setErr('');
    try { const r: any = await api('/survival/protocols'); setProtos(r.protocols || []); if (!open && r.protocols?.length) setOpen(r.protocols[0].id); }
    catch (e: any) { const m = String(e?.message || e); if (/^402:/.test(m)) setLocked(true); else setErr(m); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggle = async (pid: string, idx: number) => {
    tap('light'); setBusy(`${pid}-${idx}`);
    try {
      const r: any = await api(`/survival/protocols/${pid}/steps/${idx}`, { method: 'PUT' });
      setProtos(prev => prev.map(p => (p.id === pid ? { ...p, done: r.done, progress: r.progress } : p)));
    } catch (e: any) { const m = String(e?.message || e); if (/^402:/.test(m)) setLocked(true); else setErr(m); }
    finally { setBusy(null); }
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
