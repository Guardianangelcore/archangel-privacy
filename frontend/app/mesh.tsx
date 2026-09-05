/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// MESH-MESSENGER — P2P store-and-forward messaging (BLE mesh radio in native build)
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, TextInput, FlatList, RefreshControl, ActivityIndicator, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { C, S } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';
import FeatureGate, { useFeature } from '@/src/FeatureGate';

export default function Mesh() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const [status, setStatus] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [myDid, setMyDid] = useState('');
  const [toDid, setToDid] = useState('');
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');
  // TIER GATE — Mesh SMS (offline P2P) is Sentinel+ (or a one-off feature purchase). Free users see the
  // screen and get the upgrade prompt instead of the messenger; nothing is fetched while locked.
  const mesh = useFeature('mesh_sms');

  const load = useCallback(async () => {
    if (!mesh.unlocked) return;
    setLoading(true);
    try {
      const [s, m]: any[] = await Promise.all([api('/mesh/status'), api('/mesh/messages')]);
      setStatus(s); setMessages(m.messages || []); setMyDid(m.my_did || '');
    } catch (e: any) { setErr(String(e.message || e)); }
    setLoading(false);
  }, [mesh.unlocked]);
  useEffect(() => { load(); }, [load]);

  const send = async () => {
    setBusy(true); setErr('');
    try {
      await api('/mesh/messages', { method: 'POST', body: JSON.stringify({ to_did: toDid, text }) });
      setText('');
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(false); }
  };

  return (
    <SafeAreaView testID="mesh-screen" style={st.root} edges={['top', 'bottom']}>
      <View style={st.header}>
        <Pressable testID="me-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={st.title}>{tt('mesh.mesh_messenger')}</Text>
        <View style={{ width: 26 }} />
      </View>
      {!mesh.loading && !mesh.unlocked ? (
        <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
          <Text style={st.intro}>{tt('mesh.p2p_communication_independent_of_car')}</Text>
          <FeatureGate feature="mesh_sms" message="Mesh SMS — offline P2P messages via nearby Archangel devices — is part of the Sentinel plan and above."><></></FeatureGate>
        </ScrollView>
      ) : (
      <FlatList
        data={messages}
        keyExtractor={m => m.msg_id}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.fg} />}
        contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}
        ListHeaderComponent={
          <View>
            <Text style={st.intro}>
              {tt('mesh.p2p_communication_independent_of_car')}
            </Text>
            {status && (
              <View style={st.statusCard}>
                <Text style={st.statusLine}>📡 {status.protocol}</Text>
                <Text style={st.statusLine}>{tt('mesh.nodes_in_range')} {status.reachable_peers} {tt('mesh.queued_outbox')} {status.queued_outbox}</Text>
              </View>
            )}
            <Text style={st.section}>{tt('mesh.my_did_share_with_family')}</Text>
            <Text testID="me-my-did" style={st.didText} selectable>{myDid}</Text>
            <Text style={st.section}>{tt('mesh.send_message')}</Text>
            <TextInput testID="me-to" value={toDid} onChangeText={setToDid} autoCapitalize="none"
              placeholder={tt('mesh.recipient_did_did_guardian')} placeholderTextColor="#777" style={st.input} />
            <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.sm }}>
              <TextInput testID="me-text" value={text} onChangeText={setText} placeholder={tt('mesh.message')}
                placeholderTextColor="#777" style={[st.input, { flex: 1, marginTop: 0 }]} />
              <Pressable testID="me-send" onPress={send} disabled={busy || !toDid.trim() || !text.trim()} style={st.sendBtn}>
                {busy ? <ActivityIndicator size="small" color={C.onInverse} /> : <Ionicons name="send" size={18} color={C.onInverse} />}
              </Pressable>
            </View>
            {!!err && <Text testID="me-err" style={st.err}>{err}</Text>}
            <Text style={st.section}>{tt('mesh.messages')}{messages.length})</Text>
          </View>
        }
        ListEmptyComponent={!loading ? <Text style={st.empty}>{tt('mesh.no_mesh_messages_yet')}</Text> : null}
        renderItem={({ item }) => {
          const mine = item.from_did === myDid;
          return (
            <View testID={`me-msg-${item.msg_id}`} style={[st.msgCard, mine ? st.msgMine : st.msgTheirs]}>
              <Text style={st.msgFrom}>{mine ? `→ ${item.to_did.slice(0, 24)}…` : `${item.from_name}`}</Text>
              <Text style={st.msgText}>{tx(item.text)}</Text>
              <Text style={st.msgMeta}>{item.status === 'delivered' ? tt('mesh.delivered') : tt('mesh.in_mesh_queue')} {tt('mesh.hop')} {item.hops} · #{item.sha256?.slice(0, 8)}</Text>
            </View>
          );
        }}
      />
      )}
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  intro: { color: C.onS3, fontSize: 12, lineHeight: 18 },
  statusCard: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginTop: S.md, backgroundColor: C.surface2 },
  statusLine: { color: C.onS3, fontSize: 11, lineHeight: 17 },
  section: { color: C.info, fontSize: 11, fontWeight: '900', letterSpacing: 2, marginTop: S.xl, marginBottom: S.sm },
  didText: { color: C.brand, fontSize: 12, fontWeight: '800' },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 14, color: C.fg, backgroundColor: C.surface2 },
  sendBtn: { backgroundColor: C.brand, width: 52, alignItems: 'center', justifyContent: 'center', minHeight: 48 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginTop: S.sm },
  empty: { textAlign: 'center', color: C.info, marginTop: S.lg, letterSpacing: 2, fontWeight: '800', fontSize: 11 },
  msgCard: { borderWidth: 1.5, padding: S.md, marginTop: S.sm, backgroundColor: C.surface2, maxWidth: '88%' },
  msgMine: { alignSelf: 'flex-end', borderColor: C.brand },
  msgTheirs: { alignSelf: 'flex-start', borderColor: C.borderStrong },
  msgFrom: { color: C.info, fontSize: 9, letterSpacing: 0.5 },
  msgText: { color: C.fg, fontSize: 14, marginTop: 4, lineHeight: 20 },
  msgMeta: { color: C.info, fontSize: 9, marginTop: 6 },
});
