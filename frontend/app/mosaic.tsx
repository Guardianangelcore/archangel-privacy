/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// Mosaic Protocol — ZK-Rollup L2 dashboard: blocks, PQC, Bridge-Watch, zero-fee, stress test
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, ActivityIndicator, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { C, S } from '@/src/theme';

const MONO = Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' });

export default function Mosaic() {
  const router = useRouter();
  const [status, setStatus] = useState<any>(null);
  const [blocks, setBlocks] = useState<any[]>([]);
  const [stress, setStress] = useState<any>(null);
  const [pqc, setPqc] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    try {
      const [s, b] = await Promise.all([api('/mosaic/status'), api('/mosaic/blocks')]);
      setStatus(s); setBlocks((b as any).blocks || []);
    } catch (e: any) { setErr(String(e.message || e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key); setErr('');
    try { await fn(); await load(); } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };
  const anchor = () => run('anchor', async () => { await api('/mosaic/anchor', { method: 'POST' }); });
  const bridge = () => run('bridge', async () => { await api('/mosaic/bridge/check', { method: 'POST' }); });
  const handshake = () => run('pqc', async () => { setPqc(await api('/mosaic/pqc-handshake')); });
  const stressTest = () => run('stress', async () => { setStress(await api('/mosaic/stress-test', { method: 'POST' })); });

  return (
    <SafeAreaView testID="mosaic-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="mo-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color="#E5E4E2" />
        </Pressable>
        <Text style={st.title}>MOSAIC PROTOCOL</Text>
        <View style={{ width: 26 }} />
      </View>
      <View style={st.banner}><Text style={st.bannerText}>SIMULATED L2 · REAL RPC (MOSAIC / BASE / POLYGON) IN PHASE 3</Text></View>

      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        {!!err && <Text style={st.err}>{err}</Text>}
        {status && (
          <View style={st.chainCard}>
            <Text style={st.chainName}>{status.name} · {status.layer}</Text>
            <Row lbl="BLOK" val={`#${status.block_height} · ${status.blocks_total} blokov`} />
            <Row lbl="KONSENZUS" val={status.consensus} />
            <Row lbl="PQC" val={status.pqc_suite} />
            <Row lbl="GAS" val={status.gas_policy} />
            <Row lbl="LEGACY SC" val={`${status.legacy_smart_contracts} smart kontraktov (dead-man switch)`} />
            <Row lbl="BRIDGE" val={`active: ${status.bridge_watch?.active || 'Archangel Chain'} · ${status.bridge_watch?.latency_ms ?? 0} ms`} />
          </View>
        )}

        <View style={st.btnGrid}>
          <ActionBtn testID="mo-anchor" icon="cube" label="ANCHOR BLOK" busy={busy === 'anchor'} onPress={anchor} />
          <ActionBtn testID="mo-bridge" icon="git-network" label="BRIDGE-WATCH" busy={busy === 'bridge'} onPress={bridge} />
          <ActionBtn testID="mo-pqc" icon="lock-closed" label="PQC HANDSHAKE" busy={busy === 'pqc'} onPress={handshake} />
          <ActionBtn testID="mo-stress" icon="speedometer" label="STRESS TEST" busy={busy === 'stress'} onPress={stressTest} />
        </View>

        {pqc && (
          <View style={st.resultBox}>
            <Text style={st.resultTitle}>QUANTUM-READY HANDSHAKE ✓</Text>
            <Text style={st.mono}>{pqc.kem}{'\n'}{pqc.classical}{'\n'}{pqc.signature}{'\n'}hash: {pqc.transcript_hash?.slice(0, 32)}…</Text>
          </View>
        )}
        {stress && (
          <View testID="mo-stress-result" style={[st.resultBox, { borderColor: stress.verdict === 'READY FOR PUBLISH' ? C.brand : C.warn }]}>
            <Text style={[st.resultTitle, { color: C.brand }]}>GLOBAL NODE STRESS TEST · {stress.verdict}</Text>
            <Text style={st.mono}>TPS spolu: {stress.total_tps}{'\n'}{stress.nodes.map((n: any) => `${n.node} (${n.region}): ${n.tps} tps · p95 ${n.p95_latency_ms}ms`).join('\n')}</Text>
          </View>
        )}

        <Text style={st.section}>LATEST ZK-ROLLUP BLOCKS</Text>
        {blocks.map(b => (
          <View key={b.height} style={st.blockRow}>
            <Text style={st.blockH}>#{b.height}</Text>
            <View style={{ flex: 1 }}>
              <Text style={st.mono} numberOfLines={1}>{b.block_hash}</Text>
              <Text style={st.blockMeta}>tx: {b.tx_batched} · {b.zk_proof.slice(0, 18)}… · user gas: 0 (treasury)</Text>
            </View>
          </View>
        ))}
        {blocks.length === 0 && <Text style={st.emptyLine}>— no blocks yet. Tap ANCHOR BLOCK or wait for the Swarm.</Text>}

        <Text style={st.zeroFee}>👵 ZERO-FEE ABSTRACTION: grandmas never see gas or crypto — the foundation treasury pays everything from Sentinel/Archangel revenue.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

function Row({ lbl, val }: any) {
  return (
    <View style={st.rowKV}>
      <Text style={st.rowLbl}>{lbl}</Text>
      <Text style={st.rowVal}>{val}</Text>
    </View>
  );
}
function ActionBtn({ testID, icon, label, busy, onPress }: any) {
  return (
    <Pressable testID={testID} onPress={onPress} disabled={busy} style={st.actBtn}>
      {busy ? <ActivityIndicator color="#E5E4E2" size="small" /> : <Ionicons name={icon} size={18} color="#E5E4E2" />}
      <Text style={st.actText}>{label}</Text>
    </Pressable>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#0B0B0D' },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: '#000000' },
  title: { color: '#E5E4E2', fontSize: 17, fontWeight: '900', letterSpacing: 3 },
  banner: { backgroundColor: '#1C1C1E', paddingVertical: 6, alignItems: 'center' },
  bannerText: { color: '#8A8A93', fontWeight: '900', letterSpacing: 1, fontSize: 8 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginBottom: S.md },
  chainCard: { borderWidth: 1.5, borderColor: '#E5E4E2', padding: S.lg, backgroundColor: '#111114' },
  chainName: { color: '#E5E4E2', fontWeight: '900', fontSize: 14, letterSpacing: 1, marginBottom: S.sm },
  rowKV: { flexDirection: 'row', gap: S.md, paddingVertical: 4 },
  rowLbl: { fontSize: 9, fontWeight: '800', letterSpacing: 1, color: '#8A8A93', width: 84, marginTop: 2 },
  rowVal: { flex: 1, color: '#D6D6DB', fontSize: 12, lineHeight: 17 },
  btnGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: S.sm, marginTop: S.md },
  actBtn: { width: '48%', flexGrow: 1, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', borderWidth: 1.5, borderColor: '#3A3A3E', paddingVertical: S.md, minHeight: 48, backgroundColor: '#111114' },
  actText: { color: '#E5E4E2', fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  resultBox: { marginTop: S.md, borderWidth: 1.5, borderColor: '#E5E4E2', padding: S.md, backgroundColor: '#111114' },
  resultTitle: { color: '#E5E4E2', fontWeight: '900', fontSize: 11, letterSpacing: 1, marginBottom: 6 },
  mono: { color: '#B9B9C0', fontSize: 10, lineHeight: 16, fontFamily: MONO },
  section: { marginTop: S.xl, marginBottom: S.sm, fontSize: 11, letterSpacing: 2, color: '#E5E4E2', fontWeight: '900' },
  blockRow: { flexDirection: 'row', gap: S.md, borderWidth: 1, borderColor: '#2C2C2E', padding: S.md, marginBottom: 6, backgroundColor: '#111114', alignItems: 'center' },
  blockH: { color: '#E5E4E2', fontWeight: '900', fontSize: 13, width: 42 },
  blockMeta: { color: '#8A8A93', fontSize: 9.5, marginTop: 3, letterSpacing: 0.3 },
  emptyLine: { color: '#8A8A93', fontSize: 12, fontStyle: 'italic' },
  zeroFee: { marginTop: S.xl, color: '#B8860B', fontSize: 11, lineHeight: 17, fontWeight: '800' },
});
