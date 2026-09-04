/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

const AGENT_ICONS: Record<string, string> = {
  waitlist_hunter: 'search', marketplace: 'analytics', safety: 'heart-circle', security_sentinel: 'shield-half',
};

export default function Fortress() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const [status, setStatus] = useState<any>(null);
  const [depin, setDepin] = useState<any>(null);
  const [secEvents, setSecEvents] = useState<any[]>([]);
  const [audit, setAudit] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    try {
      const [st, dp, se, au] = await Promise.all([
        api('/swarm/status'), api('/depin/status'), api('/security/events'), api('/swarm/audit/latest'),
      ]);
      setStatus(st); setDepin(dp); setSecEvents(se); if (au?.score != null) setAudit(au);
    } catch (e: any) { setErr(String(e.message || e)); }
  };
  useEffect(() => { load(); }, []);

  const runAudit = async () => {
    setBusy('audit'); setErr(''); setMsg('');
    try {
      const rep: any = await api('/swarm/audit', { method: 'POST' });
      setAudit(rep);
      setMsg(rep.ready_for_global_publish ? 'SYSTEM FULLY SECURED — ready for Global Publish ✓' : 'Audit complete — some checks need attention.');
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const migrate = async () => {
    setBusy('migrate'); setErr(''); setMsg('');
    try {
      const rep: any = await api('/depin/migrate', { method: 'POST' });
      setMsg(`Safe-Migration ✓ core shard: ${rep.from.join(', ') || '—'} → ${rep.to.join(', ')}`);
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const runAgent = async (id: string) => {
    setBusy(id);
    try { const r: any = await api(`/swarm/run/${id}`, { method: 'POST' }); setMsg(`${id}: ${r.actions} actions executed`); await load(); }
    catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  return (
    <SafeAreaView testID="fortress-screen" style={styles.root} edges={['top', 'bottom']}>
      <View style={styles.header}>
        <Pressable testID="ft-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>{tt('fortress.cyber_fortress')}</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView
        contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} tintColor={C.brand} />}
      >
        <Text style={styles.h1}>{tt('fortress.sovereign_protection_autonomy')}</Text>
        <Text style={styles.sub}>{tt('fortress.depin_infrastructure_security_sentin')}</Text>
        {!!msg && <Text style={styles.info}>{msg}</Text>}
        {!!err && <Text style={styles.err}>{err}</Text>}

        <Pressable testID="ft-audit" onPress={runAudit} disabled={busy === 'audit'} style={styles.cta}>
          {busy === 'audit' ? <ActivityIndicator color={C.onInverse} /> : <Text style={styles.ctaText}>{tt('fortress.stability_integrity_audit')}</Text>}
        </Pressable>

        {audit && (
          <View testID="ft-audit-report" style={[styles.auditBox, { borderColor: audit.ready_for_global_publish ? C.brand : C.error }]}>
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
              <Text style={styles.auditScore}>{audit.score}/100</Text>
              <Text style={[styles.auditVerdict, { color: audit.ready_for_global_publish ? C.brand : C.error }]}>{audit.verdict}</Text>
            </View>
            {(audit.checks || []).map((c: any, i: number) => (
              <View key={i} style={styles.checkRow}>
                <Ionicons name={c.ok ? 'checkmark-circle' : 'close-circle'} size={15} color={c.ok ? '#5FA779' : C.error} />
                <Text style={styles.checkText} numberOfLines={2}>{c.check}: {c.detail}</Text>
              </View>
            ))}
          </View>
        )}

        <Text style={styles.section}>{tt('fortress.autonomous_swarm')} {status?.loop_active ? tt('fortress.active') : tt('fortress.starting')}</Text>
        {(status?.agents || []).map((a: any) => (
          <View key={a.agent_id} style={styles.row}>
            <Ionicons name={(AGENT_ICONS[a.agent_id] || 'hardware-chip') as any} size={20} color={C.brand} />
            <View style={{ flex: 1 }}>
              <Text style={styles.rowTitle}>{tx(a.label)}</Text>
              <Text style={styles.rowSub}>{tx(a.desc)}</Text>
              <Text style={styles.rowMeta}>{tt('fortress.run')}{a.runs} · {a.actions} {tt('fortress.actions')} {a.last_status === 'ok' ? tt('fortress.ok') : a.last_status} {tt('fortress.every')} {a.interval_s}s</Text>
            </View>
            <Pressable testID={`ft-run-${a.agent_id}`} onPress={() => runAgent(a.agent_id)} disabled={busy === a.agent_id} style={styles.runBtn}>
              {busy === a.agent_id ? <ActivityIndicator size="small" color={C.brand} /> : <Ionicons name="play" size={16} color={C.brand} />}
            </Pressable>
          </View>
        ))}
        {(!status?.agents || status.agents.length === 0) && <Text style={styles.rowSub}>{tt('fortress.agents_register_on_the_first_loop_ru')}</Text>}

        <Text style={styles.section}>{tt('fortress.depin_nodes_no_single_point_of_failu')}</Text>
        <View style={styles.nodeGrid}>
          {(depin?.nodes || []).map((n: any) => (
            <View key={n.node_id} style={[styles.node, n.health < 70 && { borderColor: C.error }]}>
              <Text style={styles.nodeId}>{n.node_id}</Text>
              <Text style={styles.nodeMeta}>{n.region} · {n.role}</Text>
              <Text style={styles.nodeMeta}>{tt('fortress.shard')} {n.shard}</Text>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 4 }}>
                <View style={[styles.dot, { backgroundColor: n.health >= 70 ? '#5FA779' : C.error }]} />
                <Text style={styles.nodeHealth}>{Math.round(n.health)}% · {n.latency_ms}{tt('fortress.ms_heals')} {n.self_heals}</Text>
              </View>
            </View>
          ))}
        </View>
        <Pressable testID="ft-migrate" onPress={migrate} disabled={busy === 'migrate'} style={styles.migrateBtn}>
          {busy === 'migrate' ? <ActivityIndicator color={C.error} /> : <Text style={styles.migrateText}>{tt('fortress.safe_migration_move_core_to_safe_nod')}</Text>}
        </Pressable>

        <Text style={styles.section}>{tt('fortress.security_sentinel_udalosti')}</Text>
        {secEvents.slice(0, 8).map((e: any) => (
          <View key={e.event_id} style={styles.evRow}>
            <Ionicons name={e.kind === 'self_heal' ? 'bandage' : e.kind === 'safe_migration' ? 'swap-horizontal' : 'warning'} size={15} color={e.severity === 'warning' ? C.error : C.brand} />
            <Text style={styles.evText} numberOfLines={2}>{e.detail}</Text>
          </View>
        ))}
        {secEvents.length === 0 && <Text style={styles.rowSub}>{tt('fortress.no_security_events_the_system_is_cle')}</Text>}

        <Text style={styles.section}>{tt('fortress.neural_bus_zk_commitment_envelopes')}</Text>
        {(status?.bus || []).slice(0, 8).map((b: any) => (
          <View key={b.event_id} style={styles.evRow}>
            <Ionicons name="git-network" size={14} color={C.info} />
            <Text style={styles.evText} numberOfLines={1}>{b.topic} ← {b.source} {tt('fortress.zk')}{(b.zkp?.commitment || '').slice(0, 12)}…</Text>
          </View>
        ))}

        <Text style={styles.disclaimer}>{tt('fortress.depin_zkp_and_security_sentinel_run')}</Text>
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
  cta: { marginTop: S.lg, backgroundColor: C.inverse, borderRadius: R.sm, minHeight: 52, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
  auditBox: { marginTop: S.md, borderWidth: 2, borderRadius: R.md, padding: S.md, backgroundColor: C.surface2 },
  auditScore: { fontSize: 30, fontWeight: '900', color: C.fg },
  auditVerdict: { fontSize: 10, fontWeight: '900', letterSpacing: 1, maxWidth: '60%', textAlign: 'right' },
  checkRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 6, marginTop: 6 },
  checkText: { flex: 1, color: C.onS3, fontSize: 10.5, lineHeight: 14 },
  row: { flexDirection: 'row', alignItems: 'center', gap: S.md, backgroundColor: C.surface2, borderRadius: R.sm, padding: S.md, marginTop: S.sm },
  rowTitle: { color: C.fg, fontWeight: '800', fontSize: 12.5 },
  rowSub: { color: C.info, fontSize: 10.5, marginTop: 2 },
  rowMeta: { color: C.brand, fontSize: 9.5, marginTop: 3, fontWeight: '700' },
  runBtn: { borderWidth: 1.5, borderColor: C.brand, borderRadius: R.sm, width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  nodeGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: S.sm },
  node: { width: '48%', flexGrow: 1, borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.sm, padding: S.md, backgroundColor: C.surface2 },
  nodeId: { color: C.fg, fontWeight: '900', fontSize: 11, fontFamily: 'monospace' },
  nodeMeta: { color: C.info, fontSize: 9.5, marginTop: 2 },
  nodeHealth: { color: C.onS3, fontSize: 9.5 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  migrateBtn: { marginTop: S.md, borderWidth: 2, borderColor: C.error, borderRadius: R.sm, minHeight: 48, alignItems: 'center', justifyContent: 'center', paddingHorizontal: S.md },
  migrateText: { color: C.error, fontWeight: '900', fontSize: 10.5, letterSpacing: 0.5 },
  evRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, paddingVertical: 7, borderBottomWidth: 1, borderBottomColor: C.border },
  evText: { flex: 1, color: C.onS3, fontSize: 10.5, lineHeight: 14 },
  info: { color: '#5FA779', marginTop: S.md, fontSize: 12 },
  err: { color: C.error, marginTop: S.md, fontSize: 12 },
  disclaimer: { marginTop: S.xl, color: C.info, fontSize: 10, lineHeight: 15, textAlign: 'center' },
});
