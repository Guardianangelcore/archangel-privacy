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

const MONTHS_SK = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const DAYS_SK = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];

const ITEM_H = 52;

/** Premium Wheel-Picker for numeric calibration (BP, glucose, quantities) — no typing. */
export function WheelSheet({ visible, onClose, title, min, max, step = 1, unit = '', initial, decimals = 0, onSelect, testID }: {
  visible: boolean; onClose: () => void; title: string; min: number; max: number; step?: number;
  unit?: string; initial?: number; decimals?: number; onSelect: (v: number) => void; testID?: string;
}) {
  const values: number[] = [];
  for (let v = min; v <= max + 1e-9; v += step) values.push(Number(v.toFixed(decimals)));
  const initIdx = Math.max(0, values.findIndex(v => v >= (initial ?? values[Math.floor(values.length / 2)])));
  const [idx, setIdx] = useState(initIdx === -1 ? 0 : initIdx);
  const scrollRef = React.useRef<ScrollView>(null);
  const fmt = (v: number) => v.toFixed(decimals);

  React.useEffect(() => {
    if (visible) {
      setIdx(initIdx === -1 ? 0 : initIdx);
      setTimeout(() => scrollRef.current?.scrollTo({ y: (initIdx === -1 ? 0 : initIdx) * ITEM_H, animated: false }), 60);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible]);

  const snap = (e: any) => {
    const i = Math.min(values.length - 1, Math.max(0, Math.round(e.nativeEvent.contentOffset.y / ITEM_H)));
    if (i !== idx) { setIdx(i); tap('light'); }
  };
  const nudge = (d: number) => {
    const i = Math.min(values.length - 1, Math.max(0, idx + d));
    setIdx(i); tap('light');
    scrollRef.current?.scrollTo({ y: i * ITEM_H, animated: true });
  };

  return (
    <Sheet visible={visible} onClose={onClose} title={title} testID={testID}>
      <View style={st.wheelRow}>
        <Pressable testID={testID ? `${testID}-minus` : undefined} onPress={() => nudge(-1)} style={st.wheelBtn}>
          <Ionicons name="remove" size={28} color={C.brand} />
        </Pressable>
        <View style={st.wheelBox}>
          <View pointerEvents="none" style={st.wheelHighlight} />
          <ScrollView ref={scrollRef} showsVerticalScrollIndicator={false}
            snapToInterval={ITEM_H} decelerationRate="fast"
            onMomentumScrollEnd={snap} onScrollEndDrag={snap}
            contentContainerStyle={{ paddingVertical: ITEM_H }}>
            {values.map((v, i) => (
              <View key={i} style={st.wheelItem}>
                <Text style={[st.wheelVal, i === idx && st.wheelValActive]}>{fmt(v)}</Text>
              </View>
            ))}
          </ScrollView>
        </View>
        <Pressable testID={testID ? `${testID}-plus` : undefined} onPress={() => nudge(1)} style={st.wheelBtn}>
          <Ionicons name="add" size={28} color={C.brand} />
        </Pressable>
      </View>
      {!!unit && <Text style={st.wheelUnit}>{unit}</Text>}
      <Pressable testID={testID ? `${testID}-confirm` : undefined}
        onPress={() => { tap('medium'); onSelect(values[idx]); onClose(); }} style={st.wheelConfirm}>
        <Text style={st.wheelConfirmText}>CONFIRM {fmt(values[idx])}{unit ? ` ${unit}` : ''}</Text>
      </Pressable>
      <View style={{ height: S.xl }} />
    </Sheet>
  );
}

/** Native-style time picker — two snap wheels (hours & 5-minute steps). No typing. */
export function TimeSheet({ visible, onClose, title, initial, onSelect, testID }: {
  visible: boolean; onClose: () => void; title: string; initial?: string;
  onSelect: (hhmm: string) => void; testID?: string;
}) {
  const HOURS = Array.from({ length: 24 }, (_, i) => i);
  const MINS = Array.from({ length: 12 }, (_, i) => i * 5);
  const valid = initial && /^\d{1,2}:\d{2}$/.test(initial);
  const ih = valid ? Math.min(23, parseInt(initial!.split(':')[0], 10)) : 8;
  const im = valid ? Math.min(11, Math.round(parseInt(initial!.split(':')[1], 10) / 5)) : 0;
  const [h, setH] = useState(ih);
  const [mi, setMi] = useState(im);
  const hRef = React.useRef<ScrollView>(null);
  const mRef = React.useRef<ScrollView>(null);

  React.useEffect(() => {
    if (visible) {
      setH(ih); setMi(im);
      setTimeout(() => {
        hRef.current?.scrollTo({ y: ih * ITEM_H, animated: false });
        mRef.current?.scrollTo({ y: im * ITEM_H, animated: false });
      }, 60);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible]);

  const snap = (set: (i: number) => void, max: number) => (e: any) => {
    const i = Math.min(max, Math.max(0, Math.round(e.nativeEvent.contentOffset.y / ITEM_H)));
    set(i); tap('light');
  };
  const val = `${String(h).padStart(2, '0')}:${String(MINS[mi]).padStart(2, '0')}`;

  return (
    <Sheet visible={visible} onClose={onClose} title={title} testID={testID}>
      <View style={st.wheelRow}>
        <View style={st.wheelBox}>
          <View pointerEvents="none" style={st.wheelHighlight} />
          <ScrollView ref={hRef} showsVerticalScrollIndicator={false} snapToInterval={ITEM_H} decelerationRate="fast"
            onMomentumScrollEnd={snap(setH, 23)} onScrollEndDrag={snap(setH, 23)}
            contentContainerStyle={{ paddingVertical: ITEM_H }}>
            {HOURS.map(x => (
              <View key={x} style={st.wheelItem}>
                <Text style={[st.wheelVal, x === h && st.wheelValActive]}>{String(x).padStart(2, '0')}</Text>
              </View>
            ))}
          </ScrollView>
        </View>
        <Text style={st.timeColon}>:</Text>
        <View style={st.wheelBox}>
          <View pointerEvents="none" style={st.wheelHighlight} />
          <ScrollView ref={mRef} showsVerticalScrollIndicator={false} snapToInterval={ITEM_H} decelerationRate="fast"
            onMomentumScrollEnd={snap(setMi, 11)} onScrollEndDrag={snap(setMi, 11)}
            contentContainerStyle={{ paddingVertical: ITEM_H }}>
            {MINS.map((x, i) => (
              <View key={x} style={st.wheelItem}>
                <Text style={[st.wheelVal, i === mi && st.wheelValActive]}>{String(x).padStart(2, '0')}</Text>
              </View>
            ))}
          </ScrollView>
        </View>
      </View>
      <Pressable testID={testID ? `${testID}-confirm` : undefined}
        onPress={() => { tap('medium'); onSelect(val); onClose(); }} style={st.wheelConfirm}>
        <Text style={st.wheelConfirmText}>CONFIRM {val}</Text>
      </Pressable>
      <View style={{ height: S.xl }} />
    </Sheet>
  );
}

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
        <Pressable testID={testID ? `${testID}-prev-year` : undefined} onPress={() => { tap(); setY(y - 1); }} hitSlop={8} style={st.calNavSm}>
          <Ionicons name="play-back" size={15} color={C.info} />
        </Pressable>
        <Pressable testID={testID ? `${testID}-prev` : undefined} onPress={() => nav(-1)} hitSlop={12} style={st.calNav}>
          <Ionicons name="chevron-back" size={22} color={C.brand} />
        </Pressable>
        <Text style={st.calMonth}>{MONTHS_SK[m]} {y}</Text>
        <Pressable testID={testID ? `${testID}-next` : undefined} onPress={() => nav(1)} hitSlop={12} style={st.calNav}>
          <Ionicons name="chevron-forward" size={22} color={C.brand} />
        </Pressable>
        <Pressable testID={testID ? `${testID}-next-year` : undefined} onPress={() => { tap(); setY(y + 1); }} hitSlop={8} style={st.calNavSm}>
          <Ionicons name="play-forward" size={15} color={C.info} />
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
  calNavSm: { width: 40, height: 40, borderRadius: R.pill, alignItems: 'center', justifyContent: 'center' },
  timeColon: { color: C.brand, fontSize: 30, fontWeight: '900' },
  calMonth: { color: C.fg, fontWeight: '900', fontSize: 16, letterSpacing: 1 },
  calRow: { flexDirection: 'row', marginBottom: S.xs },
  calDow: { flex: 1, textAlign: 'center', color: C.info, fontWeight: '800', fontSize: 11 },
  calGrid: { flexDirection: 'row', flexWrap: 'wrap' },
  calCell: { width: `${100 / 7}%`, aspectRatio: 1.15, alignItems: 'center', justifyContent: 'center', borderRadius: R.sm },
  calSel: { backgroundColor: C.brand },
  calToday: { borderWidth: 1.5, borderColor: C.borderStrong },
  calDay: { color: C.onS3, fontSize: 15, fontWeight: '700' },
  wheelRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, justifyContent: 'center' },
  wheelBtn: { width: 60, height: 60, borderRadius: R.pill, borderWidth: 1.5, borderColor: C.borderStrong, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(212,175,55,0.08)' },
  wheelBox: { height: ITEM_H * 3, width: 150, overflow: 'hidden' },
  wheelHighlight: { position: 'absolute', top: ITEM_H, left: 0, right: 0, height: ITEM_H, borderTopWidth: 1.5, borderBottomWidth: 1.5, borderColor: C.borderStrong, backgroundColor: 'rgba(212,175,55,0.08)', borderRadius: R.sm, zIndex: 1 },
  wheelItem: { height: ITEM_H, alignItems: 'center', justifyContent: 'center' },
  wheelVal: { color: C.info, fontSize: 22, fontWeight: '700' },
  wheelValActive: { color: C.brand, fontSize: 30, fontWeight: '900' },
  wheelUnit: { textAlign: 'center', color: C.info, fontSize: 12, fontWeight: '800', letterSpacing: 1, marginTop: S.sm },
  wheelConfirm: { marginTop: S.lg, minHeight: 56, borderRadius: R.pill, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center' },
  wheelConfirmText: { color: C.onInverse, fontWeight: '900', fontSize: 14, letterSpacing: 1.5 },
});
