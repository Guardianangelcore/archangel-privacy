/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// ACTIVE AGENTS — the 5 autonomous agents (JARVIS · LENS · SCRIBE · ANALYST · GUARDIAN) and
// which of them the user's plan / purchases have switched on. Compact strip or detailed list.
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from './api';
import { useAuth } from './auth';
import { C, S, R } from './theme';

type Agent = { id: string; name: string; role: string; tier: string; icon: string; active: boolean };

export function ActiveAgents({ detailed, onPress }: { detailed?: boolean; onPress?: () => void }) {
  const { user } = useAuth() as any;
  const router = useRouter();
  const [data, setData] = useState<{ tier: string; priority: boolean; agents: Agent[] } | null>(null);
  useEffect(() => { api('/agents/status').then(setData as any).catch(() => {}); }, [user?.tier, user?.demo_until, user?.features_owned?.length]);
  if (!data) return null;
  const on = data.agents.filter(a => a.active).length;

  if (!detailed) {
    return (
      <Pressable testID="active-agents" onPress={onPress} style={st.strip}>
        <Text style={st.stripLabel}>ACTIVE AGENTS {on}/{data.agents.length}</Text>
        <View style={st.dots}>
          {data.agents.map(a => (
            <View key={a.id} style={st.dotWrap}>
              <View style={[st.dot, a.active && st.dotOn]} />
              <Text style={[st.dotText, a.active && { color: C.brand }]}>{a.name}</Text>
            </View>
          ))}
        </View>
        {data.priority && <Text style={st.prio}>PRIORITY</Text>}
      </Pressable>
    );
  }
  return (
    <View style={{ gap: S.sm }}>
      {data.agents.map(a => (
        <View key={a.id} testID={`agent-${a.id}`} style={[st.row, a.active && st.rowOn]}>
          <Ionicons name={a.icon as any} size={22} color={a.active ? C.brand : C.info} />
          <View style={{ flex: 1 }}>
            <Text style={[st.name, !a.active && { color: C.info }]}>{a.name}</Text>
            <Text style={st.role}>{a.role}</Text>
          </View>
          {a.active ? <Ionicons name="checkmark-circle" size={20} color={C.accent} />
            : <Pressable onPress={() => router.push(a.id === 'analyst' ? '/bunker' : '/subscription')} hitSlop={8}><Text style={st.lock}>🔒 {a.tier.toUpperCase()}</Text></Pressable>}
        </View>
      ))}
      <Text style={st.foot}>Free: Jarvis · Guardian: + Lens · Sentinel: + Scribe + Analyst · Archangel: all 5 + priority + strongest models</Text>
    </View>
  );
}

const st = StyleSheet.create({
  strip: { marginHorizontal: S.lg, marginTop: 2, padding: S.sm, borderWidth: 1, borderColor: 'rgba(212,175,55,0.3)', borderRadius: R.sm, gap: 6 },
  stripLabel: { color: C.info, fontSize: 9, fontWeight: '900', letterSpacing: 2 },
  dots: { flexDirection: 'row', justifyContent: 'space-between' },
  dotWrap: { alignItems: 'center', gap: 3 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: C.surface3 },
  dotOn: { backgroundColor: C.brand, shadowColor: C.brand, shadowOpacity: 0.9, shadowRadius: 6 },
  dotText: { color: C.info, fontSize: 8, fontWeight: '900', letterSpacing: 1 },
  prio: { position: 'absolute', right: 8, top: 6, color: C.accent, fontSize: 8, fontWeight: '900', letterSpacing: 1.5 },
  row: { flexDirection: 'row', alignItems: 'center', gap: S.md, padding: S.md, borderWidth: 1, borderColor: C.border, borderRadius: R.sm },
  rowOn: { borderColor: 'rgba(212,175,55,0.5)', backgroundColor: 'rgba(212,175,55,0.06)' },
  name: { color: C.fg, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
  role: { color: C.info, fontSize: 11, marginTop: 2 },
  lock: { color: C.warn, fontSize: 10, fontWeight: '900' },
  foot: { color: C.info, fontSize: 10, lineHeight: 15, marginTop: S.xs },
});
