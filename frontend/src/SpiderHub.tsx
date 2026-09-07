/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// SPIDER HUB — the main screen. A web of nodes: the centre is ARCHANGEL, four modules hang on
// gold threads; tap one and its sub-modules fan out around it (the other modules stay one tap
// away in the top rail). Crisis-ready: big targets, one glance. Senior mode: fewer, larger nodes.
// Also hosts the unified JARVIS input (text · voice · photo → the multi-agent pipeline).
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { View, Text, StyleSheet, Pressable, TextInput, ActivityIndicator, ScrollView, Modal, Platform, Animated, Easing } from 'react-native';
import { BlurView } from 'expo-blur';
import { ARMS, Arm, FeatureNode, AngelMark, GOLD } from './feature-map';
import { Cascade, Breathe } from './ui/Cascade';
import Svg, { Line, Circle } from 'react-native-svg';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { launchCamera, takeRecoveredAsset } from './camera';
import { api, apiUpload } from './api';
import { useAuth } from './auth';
import { C, S, R } from './theme';
import { useUserType } from './user-type';
import { tap } from './ui/glass';
import { speak } from './voice';
import { ActiveAgents } from './ActiveAgents';


type Node = FeatureNode;

/** Glass node — translucent blur card with a gold hairline (falls back to rgba on web). */
function Glass({ children, style, radius }: { children: React.ReactNode; style?: any; radius: number }) {
  if (Platform.OS === 'web') return <View style={[style, { borderRadius: radius, backgroundColor: 'rgba(16,16,28,0.72)' }]}>{children}</View>;
  return <BlurView intensity={28} tint="dark" style={[style, { borderRadius: radius, overflow: 'hidden', backgroundColor: 'rgba(16,16,28,0.45)' }]}>{children}</BlurView>;
}

export function SpiderHub({ onClassic }: { onClassic: () => void }) {
  const router = useRouter();
  const { user } = useAuth() as any;
  const { senior, fs } = useUserType();
  const [focus, setFocus] = useState<Arm | null>(null);
  const [area, setArea] = useState({ w: 0, h: 0 });
  const [agentsOpen, setAgentsOpen] = useState(false);
  const [q, setQ] = useState('');
  const [photoBusy, setPhotoBusy] = useState(false);
  const [result, setResult] = useState<any>(null);
  // arms draw themselves slowly from the centre on every focus change (premium, unhurried)
  const grow = useRef(new Animated.Value(0)).current;
  useEffect(() => { grow.setValue(0); Animated.timing(grow, { toValue: 1, duration: 700, easing: Easing.out(Easing.cubic), useNativeDriver: false }).start(); }, [focus, grow]);
  const [growV, setGrowV] = useState(0);
  useEffect(() => { const id = grow.addListener(({ value }) => setGrowV(value)); return () => grow.removeListener(id); }, [grow]);

  const nodeSize = senior ? 108 : 84;
  const ring: Node[] = focus ? (senior ? focus.subs.slice(0, 4) : focus.subs) : ARMS;
  const layout = useMemo(() => {
    const cx = area.w / 2, cy = area.h / 2;
    const r = Math.max(70, Math.min(area.w, area.h) / 2 - nodeSize / 2 - 4);
    return { cx, cy, r, pts: ring.map((_, i) => { const a = (i / ring.length) * Math.PI * 2 - Math.PI / 2; return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) }; }) };
  }, [area, ring, nodeSize]);

  const go = (n: Node) => {
    tap('light');
    if (n.action === 'classic') return onClassic();
    if (n.action === 'agents') return setAgentsOpen(true);
    if (n.action === 'web') return router.push('/web-map' as any);
    if ((n as Arm).subs) return setFocus(n as Arm);
    if (n.route) router.push(n.route as any);
  };

  const askText = () => { const t = q.trim(); if (!t) return; tap('medium'); setQ(''); router.push({ pathname: '/jarvis', params: { q: t } } as any); };
  const askVoice = () => { tap('medium'); router.push({ pathname: '/jarvis', params: { voice: '1' } } as any); };
  const analyzeAsset = async (a: ImagePicker.ImagePickerAsset) => {
    setPhotoBusy(true); setResult(null);
    try {
      const doc: any = await apiUpload('/vault/documents', a.uri, a.fileName || 'scan.jpg', a.mimeType || 'image/jpeg', { title: 'Jarvis scan' });
      const r: any = await api('/agents/run', { method: 'POST', body: JSON.stringify({ input_type: 'photo', doc_id: doc.doc_id, text: q.trim(), language: user?.language || 'sk' }) });
      setResult(r); setQ('');
      speak(r.reply, { mood: 'calm', language: user?.language || 'en' });
    } catch (e: any) { setResult({ error: String(e.message || e) }); }
    finally { setPhotoBusy(false); }
  };
  // Photo captured right before an Android process restart (see src/camera.ts)
  useEffect(() => {
    const a = takeRecoveredAsset();
    if (a) analyzeAsset(a);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const askPhoto = async () => {
    tap('medium');
    try {
      let perm = await ImagePicker.getCameraPermissionsAsync();
      if (!perm.granted && perm.canAskAgain) perm = await ImagePicker.requestCameraPermissionsAsync();
      const res = perm.granted && Platform.OS !== 'web'
        ? await launchCamera('/(tabs)', { quality: 0.7 })
        : await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.7 });
      if (res.canceled || !res.assets?.length) return;
      await analyzeAsset(res.assets[0]);
    } catch (e: any) { setResult({ error: String(e.message || e) }); }
  };

  const accent = focus?.color || GOLD;
  return (
    <View style={st.root} testID="spider-hub">
      {/* Neighbour rail — every arm one tap away · Web View opens the full Pavučina */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={st.railScroll} contentContainerStyle={st.rail}>
        <Pressable testID="hub-root" onPress={() => { tap('light'); setFocus(null); }} style={[st.chip, !focus && st.chipOn]}>
          <Ionicons name="apps-outline" size={14} color={!focus ? C.onInverse : GOLD} /><Text style={[st.chipText, !focus && { color: C.onInverse }]}>HUB</Text>
        </Pressable>
        {ARMS.map(m => (
          <Pressable key={m.id} testID={`rail-${m.id}`} onPress={() => { tap('light'); setFocus(m); }} style={[st.chip, focus?.id === m.id && { backgroundColor: m.color, borderColor: m.color }]}>
            <Ionicons name={m.icon as any} size={14} color={focus?.id === m.id ? C.onInverse : m.color} />
            <Text style={[st.chipText, focus?.id === m.id && { color: C.onInverse }]}>{m.label.toUpperCase()}</Text>
          </Pressable>
        ))}
        <Pressable testID="hub-web-view" onPress={() => { tap('medium'); router.push('/web-map' as any); }} style={[st.chip, st.chipWeb]}>
          <Ionicons name="git-network-outline" size={14} color={GOLD} /><Text style={st.chipText}>WEB VIEW</Text>
        </Pressable>
      </ScrollView>
      <ActiveAgents onPress={() => setAgentsOpen(true)} />

      {/* The web */}
      <View style={st.web} onLayout={e => setArea({ w: e.nativeEvent.layout.width, h: e.nativeEvent.layout.height })}>
        {area.w > 0 && (
          <Svg width={area.w} height={area.h} style={StyleSheet.absoluteFill} pointerEvents="none">
            <Circle cx={layout.cx} cy={layout.cy} r={layout.r * growV} stroke={accent} strokeOpacity={0.14} strokeWidth={1} fill="none" />
            <Circle cx={layout.cx} cy={layout.cy} r={layout.r * 0.55 * growV} stroke={accent} strokeOpacity={0.08} strokeWidth={1} fill="none" strokeDasharray="3 7" />
            {layout.pts.map((p, i) => <Line key={`c${i}`} x1={layout.cx} y1={layout.cy} x2={layout.cx + (p.x - layout.cx) * growV} y2={layout.cy + (p.y - layout.cy) * growV} stroke={accent} strokeWidth={1.3} strokeOpacity={0.7} />)}
            {layout.pts.map((p, i) => { const n = layout.pts[(i + 1) % layout.pts.length]; return <Line key={`r${i}`} x1={p.x} y1={p.y} x2={n.x} y2={n.y} stroke={accent} strokeWidth={0.8} strokeOpacity={0.22 * growV} strokeDasharray="4 6" />; })}
          </Svg>
        )}
        {area.w > 0 && (
          <Pressable testID="hub-centre" onPress={() => { tap('light'); if (focus) setFocus(null); else router.push('/jarvis'); }}
            style={[st.centreWrap, { width: nodeSize + 22, height: nodeSize + 22, left: layout.cx - (nodeSize + 22) / 2, top: layout.cy - (nodeSize + 22) / 2 }]}>
            <Breathe style={[st.halo, { width: nodeSize + 22, height: nodeSize + 22, borderRadius: (nodeSize + 22) / 2, borderColor: accent, shadowColor: accent }]} />
            <Glass radius={(nodeSize + 22) / 2} style={[st.centre, { width: nodeSize + 22, height: nodeSize + 22, borderColor: accent }]}>
              {focus ? <Ionicons name={focus.icon as any} size={senior ? 40 : 30} color={accent} /> : <AngelMark size={senior ? 54 : 42} />}
              <Text style={[st.centreText, { fontSize: fs(8.5) }]} numberOfLines={2}>{focus ? focus.label.toUpperCase() : 'GUARDIAN\nANGEL'}</Text>
              <Text style={st.centreHint}>{focus ? '← HUB' : 'ASK JARVIS'}</Text>
            </Glass>
          </Pressable>
        )}
        {area.w > 0 && ring.map((n, i) => {
          const p = layout.pts[i];
          const col = focus ? focus.color : (n as Arm).color;
          return (
            <Cascade key={`${focus?.id || 'hub'}-${n.id}`} index={i} style={[st.nodeWrap, { width: nodeSize, height: nodeSize, left: p.x - nodeSize / 2, top: p.y - nodeSize / 2 }]}>
              <Pressable testID={`node-${n.id}`} onPress={() => go(n)} style={{ flex: 1 }}>
                <Glass radius={nodeSize / 2} style={[st.node, { borderColor: col }]}>
                  <Ionicons name={n.icon as any} size={senior ? 36 : 25} color={col} />
                  <Text style={[st.nodeText, { fontSize: fs(8) }]} numberOfLines={2}>{n.label.toUpperCase()}</Text>
                </Glass>
              </Pressable>
            </Cascade>
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
  root: { flex: 1, backgroundColor: '#03030A' },
  railScroll: { flexGrow: 0, flexShrink: 0 },
  rail: { gap: S.sm, paddingHorizontal: S.lg, paddingVertical: S.sm, alignItems: 'center' },
  chip: { flexDirection: 'row', gap: 6, alignItems: 'center', minHeight: 40, paddingHorizontal: S.md, borderWidth: 1, borderColor: 'rgba(212,175,55,0.4)', borderRadius: R.pill, backgroundColor: 'rgba(255,255,255,0.03)' },
  chipOn: { backgroundColor: GOLD, borderColor: GOLD },
  chipWeb: { borderStyle: 'dashed' },
  chipText: { color: GOLD, fontWeight: '800', fontSize: 10.5, letterSpacing: 1.6 },
  web: { flex: 1, margin: S.sm },
  centreWrap: { position: 'absolute', alignItems: 'center', justifyContent: 'center' },
  halo: { position: 'absolute', borderWidth: 1, shadowOpacity: 0.9, shadowRadius: 22, shadowOffset: { width: 0, height: 0 }, elevation: 12 },
  centre: { borderWidth: 1.5, alignItems: 'center', justifyContent: 'center', gap: 3 },
  centreText: { color: C.fg, fontWeight: '800', letterSpacing: 1.2, textAlign: 'center', paddingHorizontal: 6, lineHeight: 11 },
  centreHint: { color: C.info, fontSize: 7.5, letterSpacing: 1.2 },
  nodeWrap: { position: 'absolute' },
  node: { flex: 1, borderWidth: 1, alignItems: 'center', justifyContent: 'center', gap: 4, paddingHorizontal: 8 },
  nodeText: { color: C.fg, fontWeight: '700', letterSpacing: 0.6, textAlign: 'center', lineHeight: 10 },

  inputRow: { flexDirection: 'row', alignItems: 'center', gap: S.sm, padding: S.md, borderTopWidth: 1, borderTopColor: 'rgba(212,175,55,0.25)', backgroundColor: 'rgba(255,255,255,0.02)' },
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
