/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// OFFLINE MESH — Mesh SMS without internet: nearby Archangel devices (BLE / WiFi Direct in the
// native build, simulated in Expo Go & web), ≤160-char messages, store-and-forward relay.
import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, Pressable, TextInput, ScrollView, KeyboardAvoidingView, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { useAuth } from '@/src/auth';
import { C, S, R } from '@/src/theme';
import { useUserType } from '@/src/user-type';
import { tap } from '@/src/ui/glass';
import FeatureGate from '@/src/FeatureGate';
import * as Mesh from '@/src/mesh-radio';

export default function OfflineMesh() {
  const router = useRouter();
  return (
    <SafeAreaView style={st.root} edges={['top']}>
      <View style={st.head}>
        <Pressable testID="mesh-back" onPress={() => router.back()} hitSlop={10} style={st.back}><Ionicons name="chevron-back" size={22} color={C.brand} /></Pressable>
        <Text style={st.title}>OFFLINE MESH</Text>
      </View>
      <FeatureGate feature="mesh_sms" message="Mesh SMS — messages without internet via nearby Archangel devices — is part of the Sentinel plan.">
        <MeshChat />
      </FeatureGate>
    </SafeAreaView>
  );
}

function MeshChat() {
  const { user } = useAuth() as any;
  const { fs } = useUserType();
  const [, force] = useState(0);
  const [text, setText] = useState('');
  const scroll = useRef<ScrollView>(null);
  useEffect(() => {
    const un = Mesh.subscribe(() => force(n => n + 1));
    Mesh.start();
    return () => { un(); Mesh.stop(); };
  }, []);
  const peers = Mesh.peers(); const msgs = Mesh.messages();
  const info = Mesh.transportInfo();
  const send = async () => {
    if (!text.trim()) return;
    tap('medium');
    await Mesh.send(text, user?.name || 'Me');
    setText('');
    setTimeout(() => scroll.current?.scrollToEnd({ animated: true }), 50);
  };
  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={st.status}>
        <View style={st.statusRow}>
          <Ionicons name="radio" size={16} color={C.accent} />
          <Text testID="mesh-peers" style={st.statusText}>{peers.length} nearby device{peers.length === 1 ? '' : 's'}</Text>
          <Text style={st.transport}>{info.label}</Text>
        </View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 6 }}>
          {peers.map(p => (
            <View key={p.id} testID={`mesh-peer-${p.id}`} style={st.peer}><View style={[st.dot, { backgroundColor: p.rssi > -60 ? C.accent : p.rssi > -75 ? C.warn : C.error }]} /><Text style={st.peerText}>{p.name} · {p.rssi} dBm</Text></View>
          ))}
        </ScrollView>
      </View>
      <ScrollView ref={scroll} contentContainerStyle={st.msgs} onContentSizeChange={() => scroll.current?.scrollToEnd({ animated: false })}>
        {msgs.length === 0 && <Text style={st.empty}>No messages yet. Everything you send is flooded to every visible device and relayed onward (up to 6 hops) — even without any network.</Text>}
        {msgs.map(m => (
          <View key={m.id} testID={m.mine ? 'mesh-msg-mine' : 'mesh-msg-in'} style={[st.bubble, m.mine ? st.mine : st.theirs]}>
            {!m.mine && <Text style={st.from}>{m.from} · {m.hops} hop{m.hops === 1 ? '' : 's'}</Text>}
            <Text style={[st.msgText, { fontSize: fs(14) }]}>{m.text}</Text>
            <Text style={st.meta}>{new Date(m.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}{m.mine ? ` · delivered to ${m.delivered}/${peers.length}` : ''}</Text>
          </View>
        ))}
      </ScrollView>
      <View style={st.inputRow}>
        <TextInput testID="mesh-input" value={text} onChangeText={t => setText(t.slice(0, Mesh.MESH_MAX_LEN))} placeholder="Message (max 160 chars)" placeholderTextColor={C.info} style={[st.input, { fontSize: fs(13) }]} onSubmitEditing={send} returnKeyType="send" />
        <Text style={st.count}>{Mesh.MESH_MAX_LEN - text.length}</Text>
        <Pressable testID="mesh-send" onPress={send} style={st.sendBtn}><Ionicons name="send" size={18} color={C.onInverse} /></Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  head: { flexDirection: 'row', alignItems: 'center', gap: S.sm, paddingHorizontal: S.md, minHeight: 52 },
  back: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  title: { color: C.brand, fontWeight: '900', letterSpacing: 3, fontSize: 16 },
  status: { marginHorizontal: S.lg, padding: S.md, gap: S.sm, borderWidth: 1, borderColor: 'rgba(64,224,208,0.4)', borderRadius: R.sm, backgroundColor: 'rgba(64,224,208,0.05)' },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap' },
  statusText: { color: C.fg, fontWeight: '900', fontSize: 13 },
  transport: { color: C.info, fontSize: 10, flex: 1, textAlign: 'right' },
  peer: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 10, minHeight: 30, borderWidth: 1, borderColor: C.border, borderRadius: R.pill },
  dot: { width: 8, height: 8, borderRadius: 4 },
  peerText: { color: C.onS3, fontSize: 10.5 },
  msgs: { padding: S.lg, gap: S.sm, paddingBottom: S.xl },
  empty: { color: C.info, fontSize: 12, lineHeight: 18, textAlign: 'center', marginTop: S.xl },
  bubble: { maxWidth: '84%', padding: S.md, borderRadius: R.md, gap: 3 },
  mine: { alignSelf: 'flex-end', backgroundColor: 'rgba(212,175,55,0.16)', borderWidth: 1, borderColor: 'rgba(212,175,55,0.5)' },
  theirs: { alignSelf: 'flex-start', backgroundColor: C.surface2, borderWidth: 1, borderColor: C.border },
  from: { color: C.accent, fontSize: 10, fontWeight: '900' },
  msgText: { color: C.fg, lineHeight: 20 },
  meta: { color: C.info, fontSize: 9.5 },
  inputRow: { flexDirection: 'row', alignItems: 'center', gap: S.sm, padding: S.md, borderTopWidth: 1, borderTopColor: C.border },
  input: { flex: 1, minHeight: 48, color: C.fg, paddingHorizontal: S.md, borderWidth: 1, borderColor: C.border, borderRadius: R.pill, backgroundColor: C.surface2 },
  count: { color: C.info, fontSize: 10, width: 28, textAlign: 'center' },
  sendBtn: { width: 48, height: 48, borderRadius: 24, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center' },
});
