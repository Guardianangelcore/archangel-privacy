/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// PAVUČINA — the full web: every feature as a node on a golden, breathing spider web.
// Centre = Guardian Angel · inner ring = 5 arms · outer ring = all sub-features clustered by arm.
// Tap any node to open it. Pinch/scroll: horizontal + vertical ScrollView for small phones.
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { View, Text, StyleSheet, Pressable, Animated, Easing, useWindowDimensions, ScrollView, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Svg, { Line, Circle, Polygon } from 'react-native-svg';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { ARMS, AngelMark, GOLD } from '@/src/feature-map';
import { Cascade, Breathe } from '@/src/ui/Cascade';
import { C, S, R } from '@/src/theme';
import { tap } from '@/src/ui/glass';

const ARM_NODE = 62;
const SUB_NODE = 52;

export default function WebMap() {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const size = Math.max(width, 720);                 // the web is at least 720 px wide → scrollable on phones
  const cx = size / 2, cy = size / 2;
  const r1 = size * 0.20, r2 = size * 0.42;
  const hRef = useRef<ScrollView>(null); const vRef = useRef<ScrollView>(null);
  const spin = useRef(new Animated.Value(0)).current; // slow shimmer travelling along the web
  const [shimmer, setShimmer] = useState(0);
  useEffect(() => {
    const loop = Animated.loop(Animated.timing(spin, { toValue: 1, duration: 6000, easing: Easing.linear, useNativeDriver: false }));
    loop.start();
    const id = spin.addListener(({ value }) => setShimmer(value));
    return () => { loop.stop(); spin.removeListener(id); };
  }, [spin]);

  const nodes = useMemo(() => {
    const arms = ARMS.map((a, i) => {
      const ang = (i / ARMS.length) * Math.PI * 2 - Math.PI / 2;
      const subs = a.subs.map((s, j) => {
        const spread = (Math.PI * 2 / ARMS.length) * 0.82;               // each arm owns a sector of the outer ring
        const sa = ang - spread / 2 + (spread * (j + 0.5)) / a.subs.length;
        return { ...s, x: cx + r2 * Math.cos(sa), y: cy + r2 * Math.sin(sa), color: a.color };
      });
      return { ...a, x: cx + r1 * Math.cos(ang), y: cy + r1 * Math.sin(ang), subs };
    });
    return arms;
  }, [cx, cy, r1, r2]);

  const open = (n: { route?: string; action?: string }) => {
    tap('light');
    if (n.action === 'agents') return router.push('/jarvis');
    if (n.route) router.push(n.route as any);
  };
  const polygon = (r: number) => ARMS.map((_, i) => { const a = (i / ARMS.length) * Math.PI * 2 - Math.PI / 2; return `${cx + r * Math.cos(a)},${cy + r * Math.sin(a)}`; }).join(' ');
  const glow = 0.35 + 0.35 * Math.sin(shimmer * Math.PI * 2);

  return (
    <SafeAreaView style={st.root} edges={['top']}>
      <View style={st.head}>
        <Pressable testID="web-back" onPress={() => router.back()} hitSlop={10} style={st.back}><Ionicons name="chevron-back" size={22} color={GOLD} /></Pressable>
        <Text style={st.title}>PAVUČINA · WEB VIEW</Text>
        <Text style={st.count}>{ARMS.reduce((n, a) => n + a.subs.length, 0)} FEATURES</Text>
      </View>
      <ScrollView ref={hRef} horizontal showsHorizontalScrollIndicator={false} onLayout={() => hRef.current?.scrollTo({ x: Math.max(0, (size - width) / 2), animated: false })}>
        <ScrollView ref={vRef} showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: S.xxl }} onLayout={(e) => vRef.current?.scrollTo({ y: Math.max(0, (size - e.nativeEvent.layout.height) / 2), animated: false })}>
          <View testID="web-map" style={{ width: size, height: size }}>
            <Svg width={size} height={size} style={StyleSheet.absoluteFill} pointerEvents="none">
              {/* concentric web + radial spokes */}
              {[0.35, 0.55, 0.75, 1].map((k, i) => <Polygon key={i} points={polygon(r2 * k)} stroke={GOLD} strokeOpacity={0.10 + 0.05 * i} strokeWidth={1} fill="none" />)}
              <Polygon points={polygon(r2 * 1.06)} stroke={GOLD} strokeOpacity={glow * 0.5} strokeWidth={1.2} fill="none" strokeDasharray="2 10" />
              {nodes.map((a, i) => (
                <React.Fragment key={a.id}>
                  <Line x1={cx} y1={cy} x2={a.x} y2={a.y} stroke={a.color} strokeWidth={1.6} strokeOpacity={0.85} />
                  {a.subs.map(s => <Line key={s.id} x1={a.x} y1={a.y} x2={s.x} y2={s.y} stroke={a.color} strokeWidth={1} strokeOpacity={0.55} />)}
                  {a.subs.slice(1).map((s, j) => <Line key={`w${s.id}`} x1={a.subs[j].x} y1={a.subs[j].y} x2={s.x} y2={s.y} stroke={GOLD} strokeWidth={0.7} strokeOpacity={0.25} strokeDasharray="3 5" />)}
                  <Circle cx={a.x} cy={a.y} r={ARM_NODE / 2 + 6} stroke={a.color} strokeOpacity={glow} strokeWidth={1} fill="none" />
                  {i > 0 && <Line x1={nodes[i - 1].x} y1={nodes[i - 1].y} x2={a.x} y2={a.y} stroke={GOLD} strokeWidth={0.8} strokeOpacity={0.3} />}
                </React.Fragment>
              ))}
              <Line x1={nodes[nodes.length - 1].x} y1={nodes[nodes.length - 1].y} x2={nodes[0].x} y2={nodes[0].y} stroke={GOLD} strokeWidth={0.8} strokeOpacity={0.3} />
              <Circle cx={cx} cy={cy} r={54} stroke={GOLD} strokeOpacity={glow} strokeWidth={1.5} fill="rgba(212,175,55,0.06)" />
            </Svg>

            {/* centre — the spider */}
            <Pressable testID="web-centre" onPress={() => { tap('medium'); router.back(); }} style={[st.centre, { left: cx - 48, top: cy - 48 }]}>
              <Breathe><AngelMark size={46} /></Breathe>
              <Text style={st.centreText}>GUARDIAN{'\n'}ANGEL</Text>
            </Pressable>

            {nodes.map((a, i) => (
              <React.Fragment key={a.id}>
                <Cascade index={i} from={-40}>
                  <Pressable testID={`web-arm-${a.id}`} onPress={() => open({ route: a.subs[0].route, action: a.subs[0].action })}
                    style={[st.arm, { left: a.x - ARM_NODE / 2, top: a.y - ARM_NODE / 2, borderColor: a.color }]}>
                    <Ionicons name={a.icon as any} size={22} color={a.color} />
                    <Text style={[st.armText, { color: a.color }]}>{a.label.toUpperCase()}</Text>
                  </Pressable>
                </Cascade>
                {a.subs.map((s, j) => (
                  <Cascade key={s.id} index={ARMS.length + i * 6 + j} delayStep={45} from={-30}>
                    <Pressable testID={`web-node-${s.id}`} onPress={() => open(s)} style={[st.sub, { left: s.x - SUB_NODE / 2, top: s.y - SUB_NODE / 2, borderColor: a.color }]}>
                      <Ionicons name={s.icon as any} size={18} color={a.color} />
                      <Text style={st.subText} numberOfLines={2}>{s.label}</Text>
                    </Pressable>
                  </Cascade>
                ))}
              </React.Fragment>
            ))}
          </View>
        </ScrollView>
      </ScrollView>
      <Text style={st.hint}>{Platform.OS === 'web' ? 'Scroll to explore · tap a node to open it' : 'Drag to explore · tap a node to open it'}</Text>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#03030A' },
  head: { flexDirection: 'row', alignItems: 'center', gap: S.sm, paddingHorizontal: S.md, minHeight: 52 },
  back: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  title: { color: GOLD, fontWeight: '800', letterSpacing: 3, fontSize: 14, flex: 1 },
  count: { color: C.info, fontSize: 9, letterSpacing: 1.5, fontWeight: '800' },
  centre: { position: 'absolute', width: 96, height: 96, alignItems: 'center', justifyContent: 'center', gap: 2 },
  centreText: { color: C.fg, fontSize: 8, fontWeight: '800', letterSpacing: 1.5, textAlign: 'center', lineHeight: 11 },
  arm: { position: 'absolute', width: ARM_NODE, height: ARM_NODE, borderRadius: ARM_NODE / 2, borderWidth: 1.5, backgroundColor: 'rgba(16,16,28,0.85)', alignItems: 'center', justifyContent: 'center', gap: 2 },
  armText: { fontSize: 7.5, fontWeight: '800', letterSpacing: 1 },
  sub: { position: 'absolute', width: SUB_NODE, height: SUB_NODE, borderRadius: R.sm, borderWidth: 1, backgroundColor: 'rgba(16,16,28,0.8)', alignItems: 'center', justifyContent: 'center', gap: 2, paddingHorizontal: 2 },
  subText: { color: C.fg, fontSize: 6.5, fontWeight: '700', textAlign: 'center', letterSpacing: 0.3, lineHeight: 8 },
  hint: { color: C.info, fontSize: 10, textAlign: 'center', paddingVertical: S.sm, letterSpacing: 1 },
});
