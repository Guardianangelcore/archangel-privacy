/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// MESH-MESSENGER — P2P store-and-forward messaging (BLE mesh radio in native build)
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, TextInput, FlatList, RefreshControl, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { C, S } from '@/src/theme';

export default function Mesh() {
  const router = useRouter();
  const [status, setStatus] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [myDid, setMyDid] = useState('');
  const [toDid, setToDid] = useState('');
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, m]: any[] = await Promise.all([api('/mesh/status'), api('/mesh/messages')]);
      setStatus(s); setMessages(m.messages || []); setMyDid(m.my_did || '');
    } catch (e: any) { setErr(String(e.message || e)); }
    setLoading(false);
  }, []);
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
    <SafeAreaView testID="mesh-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="me-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={st.title}>MESH-MESSENGER</Text>
        <View style={{ width: 26 }} />
      </View>
      <FlatList
        data={messages}
        keyExtractor={m => m.msg_id}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.fg} />}
        contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}
        ListHeaderComponent={
          <View>
            <Text style={st.intro}>
              P2P communication independent of carriers — messages spread store-and-forward via the Guardian relay.
              Real BLE mesh radio (phone-to-phone without internet) activates in the native build.
            </Text>
            {status && (
              <View style={st.statusCard}>
                <Text style={st.statusLine}>📡 {status.protocol}</Text>
                <Text style={st.statusLine}>Nodes in range: {status.reachable_peers} · Queued outbox: {status.queued_outbox}</Text>
              </View>
            )}
            <Text style={st.section}>MY DID (share with family)</Text>
            <Text testID="me-my-did" style={st.didText} selectable>{myDid}</Text>
            <Text style={st.section}>SEND MESSAGE</Text>
            <TextInput testID="me-to" value={toDid} onChangeText={setToDid} autoCapitalize="none"
              placeholder="Recipient DID (did:guardian:…)" placeholderTextColor="#777" style={st.input} />
            <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.sm }}>
              <TextInput testID="me-text" value={text} onChangeText={setText} placeholder="Message…"
                placeholderTextColor="#777" style={[st.input, { flex: 1, marginTop: 0 }]} />
              <Pressable testID="me-send" onPress={send} disabled={busy || !toDid.trim() || !text.trim()} style={st.sendBtn}>
                {busy ? <ActivityIndicator size="small" color={C.onInverse} /> : <Ionicons name="send" size={18} color={C.onInverse} />}
              </Pressable>
            </View>
            {!!err && <Text testID="me-err" style={st.err}>{err}</Text>}
            <Text style={st.section}>MESSAGES ({messages.length})</Text>
          </View>
        }
        ListEmptyComponent={!loading ? <Text style={st.empty}>NO MESH MESSAGES YET</Text> : null}
        renderItem={({ item }) => {
          const mine = item.from_did === myDid;
          return (
            <View testID={`me-msg-${item.msg_id}`} style={[st.msgCard, mine ? st.msgMine : st.msgTheirs]}>
              <Text style={st.msgFrom}>{mine ? `→ ${item.to_did.slice(0, 24)}…` : `${item.from_name}`}</Text>
              <Text style={st.msgText}>{item.text}</Text>
              <Text style={st.msgMeta}>{item.status === 'delivered' ? '✓ delivered' : '⏳ in mesh queue'} · hop {item.hops} · #{item.sha256?.slice(0, 8)}</Text>
            </View>
          );
        }}
      />
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
