/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// Bottom sheets — Sheet (base), OptionSheet (selections), DateSheet (calendar picker)
import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet, Modal, ScrollView, Platform } from 'react-native';
import { BlurView } from 'expo-blur';
import { Ionicons } from '@expo/vector-icons';
import { C, S, R, GLASS } from '@/src/theme';
import { tap } from '@/src/ui/glass';

export function Sheet({ visible, onClose, title, children, testID }: {
  visible: boolean; onClose: () => void; title?: string; children: React.ReactNode; testID?: string;
}) {
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View style={st.backdrop}>
        <Pressable testID={testID ? `${testID}-backdrop` : undefined} style={{ flex: 1 }} onPress={() => { tap(); onClose(); }} />
        <View testID={testID} style={st.card}>
          {Platform.OS !== 'android' && <BlurView intensity={30} tint="dark" style={StyleSheet.absoluteFill} />}
          <View style={st.grabber} />
          {!!title && <Text style={st.title}>{title}</Text>}
          <View style={{ maxHeight: 480 }}>{children}</View>
        </View>
      </View>
    </Modal>
  );
}

export type SheetOption = { label: string; value: string; icon?: any; sub?: string };

export function OptionSheet({ visible, onClose, title, options, selected, onSelect, testID }: {
  visible: boolean; onClose: () => void; title: string; options: SheetOption[]; selected?: string;
  onSelect: (v: string) => void; testID?: string;
}) {
  return (
    <Sheet visible={visible} onClose={onClose} title={title} testID={testID}>
      <ScrollView contentContainerStyle={{ paddingBottom: S.xl }}>
        {options.map(o => {
          const act = o.value === selected;
          return (
            <Pressable key={o.value} testID={testID ? `${testID}-opt-${o.value}` : undefined}
              onPress={() => { tap('light'); onSelect(o.value); onClose(); }}
              style={({ pressed }) => [st.opt, act && st.optActive, pressed && { opacity: 0.85 }]}>
              {o.icon && <Ionicons name={o.icon} size={22} color={act ? C.brand : C.onS3} />}
              <View style={{ flex: 1 }}>
                <Text style={[st.optLabel, act && { color: C.brand }]}>{o.label}</Text>
                {!!o.sub && <Text style={st.optSub}>{o.sub}</Text>}
              </View>
              {act && <Ionicons name="checkmark-circle" size={22} color={C.brand} />}
            </Pressable>
          );
        })}
      </ScrollView>
    </Sheet>
  );
}

const MONTHS_SK = ['Január', 'Február', 'Marec', 'Apríl', 'Máj', 'Jún', 'Júl', 'August', 'September', 'Október', 'November', 'December'];
const DAYS_SK = ['Po', 'Ut', 'St', 'Št', 'Pi', 'So', 'Ne'];

export function DateSheet({ visible, onClose, title, initial, onSelect, testID }: {
  visible: boolean; onClose: () => void; title: string; initial?: string;
  onSelect: (iso: string) => void; testID?: string;
}) {
  const init = initial && /^\d{4}-\d{2}/.test(initial) ? new Date(initial) : new Date();
  const [y, setY] = useState(init.getFullYear());
  const [m, setM] = useState(init.getMonth());
  const first = new Date(y, m, 1);
  const startIdx = (first.getDay() + 6) % 7; // Monday-first
  const daysInMonth = new Date(y, m + 1, 0).getDate();
  const cells: (number | null)[] = [...Array(startIdx).fill(null), ...Array.from({ length: daysInMonth }, (_, i) => i + 1)];
  const nav = (d: number) => { tap(); const nm = m + d; if (nm < 0) { setM(11); setY(y - 1); } else if (nm > 11) { setM(0); setY(y + 1); } else setM(nm); };
  const todayIso = new Date().toISOString().slice(0, 10);
  return (
    <Sheet visible={visible} onClose={onClose} title={title} testID={testID}>
      <View style={st.calHead}>
        <Pressable testID={testID ? `${testID}-prev` : undefined} onPress={() => nav(-1)} hitSlop={12} style={st.calNav}>
          <Ionicons name="chevron-back" size={22} color={C.brand} />
        </Pressable>
        <Text style={st.calMonth}>{MONTHS_SK[m]} {y}</Text>
        <Pressable testID={testID ? `${testID}-next` : undefined} onPress={() => nav(1)} hitSlop={12} style={st.calNav}>
          <Ionicons name="chevron-forward" size={22} color={C.brand} />
        </Pressable>
      </View>
      <View style={st.calRow}>
        {DAYS_SK.map(d => <Text key={d} style={st.calDow}>{d}</Text>)}
      </View>
      <View style={st.calGrid}>
        {cells.map((d, i) => {
          if (d === null) return <View key={`e${i}`} style={st.calCell} />;
          const iso = `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
          const isToday = iso === todayIso;
          const isSel = iso === initial;
          return (
            <Pressable key={iso} testID={testID ? `${testID}-day-${d}` : undefined}
              onPress={() => { tap('light'); onSelect(iso); onClose(); }}
              style={({ pressed }) => [st.calCell, isSel && st.calSel, isToday && !isSel && st.calToday, pressed && { opacity: 0.7 }]}>
              <Text style={[st.calDay, isSel && { color: C.onInverse, fontWeight: '900' }, isToday && !isSel && { color: C.brand }]}>{d}</Text>
            </Pressable>
          );
        })}
      </View>
      <View style={{ height: S.xxl }} />
    </Sheet>
  );
}

const st = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.62)', justifyContent: 'flex-end' },
  card: { backgroundColor: GLASS.bgStrong, borderTopLeftRadius: R.xl, borderTopRightRadius: R.xl, borderWidth: 1.5, borderColor: C.borderStrong, borderBottomWidth: 0, paddingHorizontal: S.lg, paddingTop: S.sm, paddingBottom: Platform.OS === 'ios' ? S.xxl : S.xl, overflow: 'hidden' },
  grabber: { alignSelf: 'center', width: 44, height: 5, borderRadius: 3, backgroundColor: 'rgba(255,255,255,0.25)', marginVertical: S.sm },
  title: { color: C.fg, fontWeight: '900', fontSize: 15, letterSpacing: 1.5, marginBottom: S.md, textAlign: 'center' },
  opt: { flexDirection: 'row', alignItems: 'center', gap: S.md, minHeight: 58, paddingHorizontal: S.md, borderRadius: R.sm, marginBottom: 4 },
  optActive: { backgroundColor: 'rgba(212,175,55,0.12)', borderWidth: 1, borderColor: C.borderStrong },
  optLabel: { color: C.fg, fontWeight: '800', fontSize: 15 },
  optSub: { color: C.info, fontSize: 11, marginTop: 2 },
  calHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: S.md },
  calNav: { width: 48, height: 48, borderRadius: R.pill, backgroundColor: 'rgba(212,175,55,0.10)', alignItems: 'center', justifyContent: 'center' },
  calMonth: { color: C.fg, fontWeight: '900', fontSize: 16, letterSpacing: 1 },
  calRow: { flexDirection: 'row', marginBottom: S.xs },
  calDow: { flex: 1, textAlign: 'center', color: C.info, fontWeight: '800', fontSize: 11 },
  calGrid: { flexDirection: 'row', flexWrap: 'wrap' },
  calCell: { width: `${100 / 7}%`, aspectRatio: 1.15, alignItems: 'center', justifyContent: 'center', borderRadius: R.sm },
  calSel: { backgroundColor: C.brand },
  calToday: { borderWidth: 1.5, borderColor: C.borderStrong },
  calDay: { color: C.onS3, fontSize: 15, fontWeight: '700' },
});
