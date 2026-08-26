/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// VOICE ECHOES — rodinný hlasový prúd pre seniorov. Jeden ťuk = Jarvis prečíta odkaz nahlas.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, Pressable, StyleSheet, ScrollView, Modal, TextInput, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { createAudioPlayer, setAudioModeAsync } from 'expo-audio';
import { api } from '@/src/api';
import { cachedAudioUri } from '@/src/media';
import { useAuth } from '@/src/auth';
import { C, S, R } from '@/src/theme';
import { tap } from '@/src/ui/glass';

const PRESETS = [
  'Ľúbime ťa, babička! Mysli na nás. ❤️',
  'Dedko, v nedeľu prídeme na obed!',
  'Nezabudni na lieky o ôsmej. Pusinky!',
  'Vnúčatá ťa pozdravujú a tešia sa na teba!',
];

export default function VoiceEchoes() {
  const router = useRouter();
  const { user } = useAuth();
  const [echoes, setEchoes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [playing, setPlaying] = useState<string | null>(null);
  const [add, setAdd] = useState(false);
  const [fromName, setFromName] = useState('');
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const playerRef = useRef<any>(null);

  const load = useCallback(async () => {
    try { const r: any = await api('/family/echoes'); setEchoes(r.echoes || []); } catch (e) { console.log(e); }
    setLoading(false);
  }, []);
  useEffect(() => {
    load();
    return () => { try { playerRef.current?.remove?.(); } catch {} };
  }, [load]);

  const play = async (e: any) => {
    tap('medium');
    setPlaying(e.echo_id);
    try {
      const text = `Odkaz od: ${e.from_name}. ${e.message}`;
      const res: any = await api('/voice/tts', { method: 'POST', body: JSON.stringify({ text: text.slice(0, 1000), voice: 'nova', speed: 0.95, language: user?.language || 'sk' }) });
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false } as any);
      const src = await cachedAudioUri(res.url.replace(/^\/api/, ''));
      try { playerRef.current?.remove?.(); } catch {}
      const p = createAudioPlayer(src.headers ? { uri: src.uri, headers: src.headers } : { uri: src.uri });
      playerRef.current = p; p.play();
      if (!e.heard) {
        await api(`/family/echoes/${e.echo_id}/heard`, { method: 'POST' });
        setEchoes(prev => prev.map(x => x.echo_id === e.echo_id ? { ...x, heard: true } : x));
      }
    } catch (err) { console.log('echo tts err', err); }
    setPlaying(null);
  };

  const send = async (text?: string) => {
    const message = (text || msg).trim();
    if (!message) return;
    setBusy(true);
    try {
      tap('success');
      await api('/family/echoes', { method: 'POST', body: JSON.stringify({ from_name: fromName.trim() || 'Rodina', message }) });
      setAdd(false); setMsg('');
      await load();
    } catch (e) { console.log(e); }
    setBusy(false);
  };

  return (
    <SafeAreaView testID="voice-echoes" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="ve-back" onPress={() => router.back()} hitSlop={10}>
          <Ionicons name="chevron-back" size={28} color={C.fg} />
        </Pressable>
        <Text style={st.title}>ODKAZY OD RODINY</Text>
        <Pressable testID="ve-add" onPress={() => setAdd(true)} hitSlop={10}>
          <Ionicons name="add-circle" size={28} color={C.brand} />
        </Pressable>
      </View>

      {loading ? <ActivityIndicator color={C.brand} style={{ marginTop: 60 }} /> : (
        <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 100, gap: S.md }}>
          <Text style={st.hint}>Ťuknite na kartu — Jarvis vám odkaz prečíta nahlas. 🔊</Text>
          {echoes.length === 0 && (
            <View style={st.empty}>
              <Ionicons name="heart" size={44} color={C.brand} />
              <Text style={st.emptyTitle}>Zatiaľ žiadne odkazy</Text>
              <Text style={st.emptySub}>Rodina môže poslať odkaz cez tlačidlo + hore. Prvý odkaz poteší najviac.</Text>
              <Pressable testID="ve-empty-add" onPress={() => setAdd(true)} style={st.emptyBtn}>
                <Text style={st.emptyBtnText}>POSLAŤ PRVÝ ODKAZ</Text>
              </Pressable>
            </View>
          )}
          {echoes.map(e => (
            <Pressable key={e.echo_id} testID={`echo-${e.echo_id}`} onPress={() => play(e)}
              style={({ pressed }) => [st.card, !e.heard && st.cardNew, pressed && { opacity: 0.85 }]}>
              <View style={st.playCircle}>
                {playing === e.echo_id ? <ActivityIndicator color={C.onInverse} /> : <Ionicons name="play" size={30} color={C.onInverse} />}
              </View>
              <View style={{ flex: 1 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  <Text style={st.from}>{e.from_name}</Text>
                  {!e.heard && <View style={st.newBadge}><Text style={st.newBadgeText}>NOVÝ</Text></View>}
                </View>
                <Text style={st.msgText} numberOfLines={3}>{e.message}</Text>
              </View>
            </Pressable>
          ))}
        </ScrollView>
      )}

      <Modal visible={add} transparent animationType="fade" onRequestClose={() => setAdd(false)}>
        <Pressable style={st.overlay} onPress={() => setAdd(false)}>
          <Pressable style={st.sheet} onPress={() => {}}>
            <View style={st.sheetHandle} />
            <Text style={st.sheetTitle}>Poslať hlasový odkaz</Text>
            <Text style={st.lbl}>KTO POSIELA?</Text>
            <TextInput testID="ve-from" value={fromName} onChangeText={setFromName} style={st.input} placeholder="Napr. Vnučka Lucka" placeholderTextColor="#888" />
            <Text style={st.lbl}>RÝCHLE ODKAZY — 1 ŤUK</Text>
            <View style={{ gap: S.sm }}>
              {PRESETS.map((p, i) => (
                <Pressable testID={`ve-preset-${i}`} key={i} onPress={() => send(p)} disabled={busy}
                  style={({ pressed }) => [st.preset, pressed && { backgroundColor: C.surface3 }]}>
                  <Text style={st.presetText}>{p}</Text>
                </Pressable>
              ))}
            </View>
            <Text style={st.lbl}>ALEBO VLASTNÝ TEXT</Text>
            <TextInput testID="ve-msg" value={msg} onChangeText={setMsg} style={[st.input, { minHeight: 60 }]} multiline placeholder="Napíšte odkaz…" placeholderTextColor="#888" />
            <Pressable testID="ve-send" onPress={() => send()} disabled={busy || !msg.trim()} style={[st.sendBtn, !msg.trim() && { opacity: 0.5 }]}>
              {busy ? <ActivityIndicator color={C.onInverse} /> : <Text style={st.sendText}>ODOSLAŤ ODKAZ</Text>}
            </Pressable>
          </Pressable>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md, borderBottomWidth: 1, borderBottomColor: C.border },
  title: { color: C.fg, fontWeight: '900', fontSize: 16, letterSpacing: 2 },
  hint: { color: C.info, fontSize: 13, textAlign: 'center', marginBottom: S.sm },
  empty: { alignItems: 'center', padding: S.xl, gap: S.sm, backgroundColor: C.surface2, borderRadius: R.lg, borderWidth: 1, borderColor: C.border },
  emptyTitle: { color: C.fg, fontWeight: '900', fontSize: 18 },
  emptySub: { color: C.onS3, fontSize: 13, textAlign: 'center', lineHeight: 19 },
  emptyBtn: { marginTop: S.sm, backgroundColor: C.brand, borderRadius: R.pill, paddingHorizontal: S.xl, minHeight: 50, alignItems: 'center', justifyContent: 'center' },
  emptyBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 13 },
  card: { flexDirection: 'row', alignItems: 'center', gap: S.lg, backgroundColor: C.surface2, borderRadius: R.lg, padding: S.lg, minHeight: 96, borderWidth: 1.5, borderColor: C.border },
  cardNew: { borderColor: C.brand, backgroundColor: 'rgba(212,175,55,0.08)' },
  playCircle: { width: 64, height: 64, borderRadius: 32, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center' },
  from: { color: C.fg, fontWeight: '900', fontSize: 17 },
  newBadge: { backgroundColor: C.brand, borderRadius: R.pill, paddingHorizontal: 8, paddingVertical: 2 },
  newBadgeText: { color: C.onInverse, fontWeight: '900', fontSize: 9, letterSpacing: 1 },
  msgText: { color: C.onS3, fontSize: 14, lineHeight: 20, marginTop: 4 },
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.72)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: C.surface2, borderTopLeftRadius: R.lg, borderTopRightRadius: R.lg, padding: S.xl, paddingBottom: 34, borderWidth: 1, borderColor: C.borderStrong },
  sheetHandle: { alignSelf: 'center', width: 44, height: 5, borderRadius: 3, backgroundColor: C.surface3, marginBottom: S.md },
  sheetTitle: { color: C.fg, fontWeight: '900', fontSize: 20 },
  lbl: { marginTop: S.lg, marginBottom: 6, color: C.info, fontWeight: '900', fontSize: 10, letterSpacing: 2 },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.md, padding: S.md, fontSize: 15, color: C.fg, backgroundColor: C.bg },
  preset: { borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.md, padding: S.md, minHeight: 50, justifyContent: 'center' },
  presetText: { color: C.fg, fontWeight: '700', fontSize: 14 },
  sendBtn: { marginTop: S.lg, backgroundColor: C.brand, borderRadius: R.pill, alignItems: 'center', justifyContent: 'center', minHeight: 54 },
  sendText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 14 },
});
