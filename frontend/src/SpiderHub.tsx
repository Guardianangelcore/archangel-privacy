/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// SPIDER HUB — the main screen. A web of nodes: the centre is ARCHANGEL, four modules hang on
// gold threads; tap one and its sub-modules fan out around it (the other modules stay one tap
// away in the top rail). Crisis-ready: big targets, one glance. Senior mode: fewer, larger nodes.
// Also hosts the unified JARVIS input (text · voice · photo → the multi-agent pipeline).
import React, { useMemo, useState } from 'react';
import { View, Text, StyleSheet, Pressable, TextInput, ActivityIndicator, ScrollView, Modal, Platform } from 'react-native';
import Svg, { Line, Circle } from 'react-native-svg';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { api, apiUpload } from './api';
import { useAuth } from './auth';
import { C, S, R } from './theme';
import { useUserType } from './user-type';
import { tap } from './ui/glass';
import { speak } from './voice';
import { ActiveAgents } from './ActiveAgents';

type Node = { id: string; label: string; icon: string; route?: string; action?: 'classic' | 'agents'; color?: string };
type Module = Node & { subs: Node[] };

const MODULES: Module[] = [
  { id: 'health', label: 'Health', icon: 'heart', color: '#FF6B8A', subs: [
    { id: 'card', label: 'Health Card', icon: 'id-card', route: '/health-card' },
    { id: 'meds', label: 'Meds', icon: 'medkit', route: '/meds' },
    { id: 'near', label: 'Nearby', icon: 'navigate', route: '/nearby-care' },
    { id: 'lens', label: 'Lens', icon: 'scan', route: '/lens' },
    { id: 'tl', label: 'Timeline', icon: 'time', route: '/health-timeline' },
    { id: 'fam', label: 'Family', icon: 'people', route: '/(tabs)/family' },
  ] },
  { id: 'survival', label: 'Survival', icon: 'shield', color: '#40E0D0', subs: [
    { id: 'crisis', label: 'Crisis', icon: 'warning', route: '/crisis-protocols' },
    { id: 'bunker', label: 'Bunker', icon: 'home', route: '/bunker' },
    { id: 'mesh', label: 'Mesh SMS', icon: 'radio', route: '/offline-mesh' },
    { id: 'ghost', label: 'Ghost', icon: 'eye-off', route: '/ghost-mode' },
    { id: 'blackout', label: 'Blackout', icon: 'flashlight', route: '/blackout' },
    { id: 'medic', label: 'Medic', icon: 'bandage', route: '/tactical-medic' },
  ] },
  { id: 'market', label: 'Market', icon: 'storefront', color: '#7C6CFF', subs: [
    { id: 'mkt', label: 'Data', icon: 'stats-chart', route: '/marketplace' },
    { id: 'insurance', label: 'Insurance', icon: 'shield-checkmark', route: '/insurance' },
    { id: 'gigs', label: 'Gigs', icon: 'briefcase', route: '/gigs' },
    { id: 'barter', label: 'Barter', icon: 'swap-horizontal', route: '/barter' },
    { id: 'store', label: 'Plans & Store', icon: 'ribbon', route: '/store' },
    { id: 'partners', label: 'Partners', icon: 'business', route: '/partners' },
  ] },
  { id: 'jarvis', label: 'Jarvis', icon: 'planet', color: '#D4AF37', subs: [
    { id: 'chat', label: 'Chat', icon: 'chatbubbles', route: '/jarvis' },
    { id: 'brief', label: 'Brief', icon: 'sunny', route: '/daily-brief' },
    { id: 'agents', label: 'Agents', icon: 'git-network', action: 'agents' },
    { id: 'translate', label: 'Translate', icon: 'language', route: '/translate' },
    { id: 'settings', label: 'Settings', icon: 'settings', route: '/(tabs)/profile' },
    { id: 'classic', label: 'Classic', icon: 'grid', action: 'classic' },
  ] },
];
const GOLD = C.brand;

export function SpiderHub({ onClassic }: { onClassic: () => void }) {
  const router = useRouter();
  const { user } = useAuth() as any;
  const { senior, fs } = useUserType();
  const [focus, setFocus] = useState<Module | null>(null);
  const [area, setArea] = useState({ w: 0, h: 0 });
  const [agentsOpen, setAgentsOpen] = useState(false);
  const [q, setQ] = useState('');
  const [photoBusy, setPhotoBusy] = useState(false);
  const [result, setResult] = useState<any>(null);

  const nodeSize = senior ? 112 : 88;
  const ring: Node[] = focus ? (senior ? focus.subs.slice(0, 4) : focus.subs) : MODULES;
  const layout = useMemo(() => {
    const cx = area.w / 2, cy = area.h / 2;
    const r = Math.max(60, Math.min(area.w, area.h) / 2 - nodeSize / 2 - 6);
    return { cx, cy, r, pts: ring.map((_, i) => { const a = (i / ring.length) * Math.PI * 2 - Math.PI / 2; return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) }; }) };
  }, [area, ring, nodeSize]);

  const go = (n: Node) => {
    tap('light');
    if (n.action === 'classic') return onClassic();
    if (n.action === 'agents') return setAgentsOpen(true);
    if ((n as Module).subs) return setFocus(n as Module);
    if (n.route) router.push(n.route as any);
  };

  const askText = () => { const t = q.trim(); if (!t) return; tap('medium'); setQ(''); router.push({ pathname: '/jarvis', params: { q: t } } as any); };
  const askVoice = () => { tap('medium'); router.push({ pathname: '/jarvis', params: { voice: '1' } } as any); };
  const askPhoto = async () => {
    tap('medium');
    try {
      let perm = await ImagePicker.getCameraPermissionsAsync();
      if (!perm.granted && perm.canAskAgain) perm = await ImagePicker.requestCameraPermissionsAsync();
      const res = perm.granted && Platform.OS !== 'web'
        ? await ImagePicker.launchCameraAsync({ quality: 0.7 })
        : await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.7 });
      if (res.canceled || !res.assets?.length) return;
      const a = res.assets[0];
      setPhotoBusy(true); setResult(null);
      const doc: any = await apiUpload('/vault/documents', a.uri, a.fileName || 'scan.jpg', a.mimeType || 'image/jpeg', { title: 'Jarvis scan' });
      const r: any = await api('/agents/run', { method: 'POST', body: JSON.stringify({ input_type: 'photo', doc_id: doc.doc_id, text: q.trim(), language: user?.language || 'sk' }) });
      setResult(r); setQ('');
      speak(r.reply, { mood: 'calm', language: user?.language || 'en' });
    } catch (e: any) { setResult({ error: String(e.message || e) }); }
    finally { setPhotoBusy(false); }
  };

  const centre = focus || { id: 'hub', label: 'ARCHANGEL', icon: 'planet', color: GOLD } as Node;
  return (
    <View style={st.root} testID="spider-hub">
      {/* Neighbour rail — every module is one tap away from anywhere */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={st.railScroll} contentContainerStyle={st.rail}>
        <Pressable testID="hub-root" onPress={() => { tap('light'); setFocus(null); }} style={[st.chip, !focus && st.chipOn]}>
          <Ionicons name="apps" size={14} color={!focus ? C.onInverse : GOLD} /><Text style={[st.chipText, !focus && { color: C.onInverse }]}>HUB</Text>
        </Pressable>
        {MODULES.map(m => (
          <Pressable key={m.id} testID={`rail-${m.id}`} onPress={() => { tap('light'); setFocus(m); }} style={[st.chip, focus?.id === m.id && st.chipOn]}>
            <Ionicons name={m.icon as any} size={14} color={focus?.id === m.id ? C.onInverse : (m.color || GOLD)} />
            <Text style={[st.chipText, focus?.id === m.id && { color: C.onInverse }]}>{m.label.toUpperCase()}</Text>
          </Pressable>
        ))}
      </ScrollView>
      <ActiveAgents onPress={() => setAgentsOpen(true)} />

      {/* The web */}
      <View style={st.web} onLayout={e => setArea({ w: e.nativeEvent.layout.width, h: e.nativeEvent.layout.height })}>
        {area.w > 0 && (
          <Svg width={area.w} height={area.h} style={StyleSheet.absoluteFill} pointerEvents="none">
            {layout.pts.map((p, i) => <Line key={`c${i}`} x1={layout.cx} y1={layout.cy} x2={p.x} y2={p.y} stroke={GOLD} strokeWidth={1.4} strokeOpacity={0.75} />)}
            {layout.pts.map((p, i) => { const n = layout.pts[(i + 1) % layout.pts.length]; return <Line key={`r${i}`} x1={p.x} y1={p.y} x2={n.x} y2={n.y} stroke={GOLD} strokeWidth={0.8} strokeOpacity={0.28} strokeDasharray="4 6" />; })}
            <Circle cx={layout.cx} cy={layout.cy} r={layout.r} stroke={GOLD} strokeOpacity={0.12} strokeWidth={1} fill="none" />
          </Svg>
        )}
        {area.w > 0 && (
          <Pressable testID="hub-centre" onPress={() => { tap('light'); if (focus) { if (focus.id === 'jarvis') router.push('/jarvis'); else setFocus(null); } }}
            style={[st.centre, { width: nodeSize + 12, height: nodeSize + 12, borderRadius: (nodeSize + 12) / 2, left: layout.cx - (nodeSize + 12) / 2, top: layout.cy - (nodeSize + 12) / 2, borderColor: centre.color || GOLD }]}>
            <Ionicons name={centre.icon as any} size={senior ? 40 : 30} color={centre.color || GOLD} />
            <Text style={[st.centreText, { fontSize: fs(9.5) }]} numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.65}>{focus ? focus.label.toUpperCase() : 'ARCHANGEL'}</Text>
            {!!focus && <Text style={st.centreHint}>{focus.id === 'jarvis' ? 'OPEN' : '← HUB'}</Text>}
          </Pressable>
        )}
        {area.w > 0 && ring.map((n, i) => {
          const p = layout.pts[i];
          const col = focus ? (focus.color || GOLD) : ((n as Module).color || GOLD);
          return (
            <Pressable key={n.id} testID={`node-${n.id}`} onPress={() => go(n)}
              style={[st.node, { width: nodeSize, height: nodeSize, borderRadius: nodeSize / 2, left: p.x - nodeSize / 2, top: p.y - nodeSize / 2, borderColor: col }]}>
              <Ionicons name={n.icon as any} size={senior ? 38 : 26} color={col} />
              <Text style={[st.nodeText, { fontSize: fs(9) }]} numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.65}>{n.label.toUpperCase()}</Text>
            </Pressable>
          );
        })}
      </View>

      {/* Unified JARVIS input — text · voice · photo */}
      <View style={st.inputRow}>
        <Pressable testID="hub-photo" onPress={askPhoto} disabled={photoBusy} style={st.iconBtn}>
          {photoBusy ? <ActivityIndicator color={GOLD} /> : <Ionicons name="camera" size={22} color={GOLD} />}
        </Pressable>
        <TextInput testID="hub-input" value={q} onChangeText={setQ} onSubmitEditing={askText} returnKeyType="send"
          placeholder={senior ? 'Ask Jarvis…' : 'Ask Jarvis · type, speak or photograph a document'} placeholderTextColor={C.info}
          style={[st.input, { fontSize: fs(13) }]} />
        <Pressable testID="hub-mic" onPress={askVoice} style={st.iconBtn}><Ionicons name="mic" size={22} color={GOLD} /></Pressable>
        <Pressable testID="hub-send" onPress={askText} style={[st.iconBtn, st.send]}><Ionicons name="arrow-up" size={20} color={C.onInverse} /></Pressable>
      </View>

      {/* Multi-agent result */}
      <Modal visible={!!result} transparent animationType="slide" onRequestClose={() => setResult(null)}>
        <Pressable style={st.backdrop} onPress={() => setResult(null)} />
        <View style={st.sheet}>
          <Text style={st.sheetTitle}>AGENTS · RESULT</Text>
          {result?.error ? <Text style={st.err}>{result.error}</Text> : (
            <ScrollView style={{ maxHeight: 420 }}>
              <View style={st.trace}>
                {(result?.trace || []).map((t: any, i: number) => (
                  <View key={i} style={st.traceRow}>
                    <Ionicons name={t.status === 'done' ? 'checkmark-circle' : t.status === 'locked' ? 'lock-closed' : 'alert-circle'} size={14} color={t.status === 'done' ? C.accent : t.status === 'locked' ? C.warn : C.error} />
                    <Text style={st.traceText}><Text style={{ color: GOLD, fontWeight: '900' }}>{String(t.agent).toUpperCase()}</Text> · {t.detail}</Text>
                  </View>
                ))}
              </View>
              <Text testID="agents-reply" style={[st.reply, { fontSize: fs(14) }]}>{result?.reply}</Text>
            </ScrollView>
          )}
          <Pressable testID="agents-close" onPress={() => setResult(null)} style={st.closeBtn}><Text style={st.closeText}>CLOSE</Text></Pressable>
        </View>
      </Modal>
      <Modal visible={agentsOpen} transparent animationType="fade" onRequestClose={() => setAgentsOpen(false)}>
        <Pressable style={st.backdrop} onPress={() => setAgentsOpen(false)} />
        <View style={st.sheet}>
          <Text style={st.sheetTitle}>AUTONOMOUS AGENTS</Text>
          <ActiveAgents detailed />
          <Pressable testID="agents-sheet-close" onPress={() => setAgentsOpen(false)} style={st.closeBtn}><Text style={st.closeText}>CLOSE</Text></Pressable>
        </View>
      </Modal>
    </View>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#000' },
  railScroll: { flexGrow: 0, flexShrink: 0 },
  rail: { gap: S.sm, paddingHorizontal: S.lg, paddingVertical: S.sm, alignItems: 'center' },
  chip: { flexDirection: 'row', gap: 6, alignItems: 'center', minHeight: 40, paddingHorizontal: S.md, borderWidth: 1, borderColor: 'rgba(212,175,55,0.45)', borderRadius: R.pill },
  chipOn: { backgroundColor: GOLD, borderColor: GOLD },
  chipText: { color: GOLD, fontWeight: '900', fontSize: 10.5, letterSpacing: 1.5 },
  web: { flex: 1, margin: S.sm },
  centre: { position: 'absolute', borderWidth: 2, backgroundColor: '#0B0B12', alignItems: 'center', justifyContent: 'center', gap: 2 },
  centreText: { color: C.fg, fontWeight: '900', letterSpacing: 1.5, textAlign: 'center' },
  centreHint: { color: C.info, fontSize: 8, letterSpacing: 1 },
  node: { position: 'absolute', borderWidth: 1.5, backgroundColor: '#0B0B12', alignItems: 'center', justifyContent: 'center', gap: 4, paddingHorizontal: 8 },
  nodeText: { color: C.fg, fontWeight: '800', letterSpacing: 0.8, textAlign: 'center' },
  inputRow: { flexDirection: 'row', alignItems: 'center', gap: S.sm, padding: S.md, borderTopWidth: 1, borderTopColor: 'rgba(212,175,55,0.3)' },
  iconBtn: { width: 48, height: 48, borderRadius: 24, borderWidth: 1, borderColor: 'rgba(212,175,55,0.5)', alignItems: 'center', justifyContent: 'center' },
  send: { backgroundColor: GOLD, borderColor: GOLD },
  input: { flex: 1, minHeight: 48, color: C.fg, paddingHorizontal: S.md, borderWidth: 1, borderColor: C.border, borderRadius: R.pill, backgroundColor: C.surface2 },
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)' },
  sheet: { backgroundColor: '#0B0B12', borderTopLeftRadius: R.lg, borderTopRightRadius: R.lg, padding: S.xl, gap: S.md, borderTopWidth: 1, borderColor: 'rgba(212,175,55,0.4)' },
  sheetTitle: { color: GOLD, fontWeight: '900', letterSpacing: 3, fontSize: 12 },
  trace: { gap: 6, marginBottom: S.md },
  traceRow: { flexDirection: 'row', gap: 8, alignItems: 'center' },
  traceText: { color: C.info, fontSize: 12, flex: 1 },
  reply: { color: C.fg, lineHeight: 22 },
  err: { color: C.error, fontWeight: '800' },
  closeBtn: { minHeight: 48, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: GOLD, borderRadius: R.sm },
  closeText: { color: GOLD, fontWeight: '900', letterSpacing: 2 },
});
