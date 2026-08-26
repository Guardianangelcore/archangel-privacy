/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet, ScrollView, Modal } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { C, S, R } from './theme';

export type HubChoice = { icon: any; label: string; sub?: string; route?: string; onPress?: () => void };
export type HubItem = { testID: string; icon: any; title: string; subtitle: string; route?: string; onPress?: () => void; choices?: HubChoice[] };
export type HubSection = { title: string; items: HubItem[] };

export default function PillarHub({ title, subtitle, icon, items, sections, hero, testID }: {
  title: string; subtitle: string; icon: any; items?: HubItem[]; sections?: HubSection[]; hero?: React.ReactNode; testID: string;
}) {
  const router = useRouter();
  const [sheet, setSheet] = useState<HubItem | null>(null);

  const open = (it: HubItem) => {
    if (it.choices?.length) { setSheet(it); return; }
    if (it.onPress) { it.onPress(); return; }
    if (it.route) router.push(it.route as any);
  };

  const pick = (c: HubChoice) => {
    setSheet(null);
    if (c.onPress) { c.onPress(); return; }
    if (c.route) router.push(c.route as any);
  };

  const renderItem = (it: HubItem) => (
    <Pressable
      key={it.testID}
      testID={it.testID}
      onPress={() => open(it)}
      style={({ pressed }) => [styles.row, pressed && { backgroundColor: C.surface3 }]}
    >
      <View style={styles.rowIcon}>
        <Ionicons name={it.icon} size={22} color={C.brand} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.rowTitle}>{it.title}</Text>
        <Text style={styles.rowSub}>{it.subtitle}</Text>
      </View>
      <Ionicons name={it.choices?.length ? 'apps-outline' : 'chevron-forward'} size={18} color={C.info} />
    </Pressable>
  );

  return (
    <SafeAreaView testID={testID} style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID={`${testID}-home`} onPress={() => router.navigate('/(tabs)')} hitSlop={10}>
          <Text style={styles.wordmark}>GUARDIAN</Text>
        </Pressable>
        <Pressable testID={`${testID}-profile`} onPress={() => router.push('/(tabs)/profile')} hitSlop={10}>
          <Ionicons name="settings-outline" size={22} color={C.onS3} />
        </Pressable>
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 120 }}>
        <View style={styles.heroIcon}>
          <Ionicons name={icon} size={30} color={C.brand} />
        </View>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.subtitle}>{subtitle}</Text>
        {hero}
        {!!items?.length && (
          <View style={{ marginTop: S.xl, gap: S.md }}>
            {items.map(renderItem)}
          </View>
        )}
        {(sections || []).map((sec, i) => (
          <View key={i}>
            <Text style={styles.sectionTitle}>{sec.title}</Text>
            <View style={{ gap: S.md }}>
              {sec.items.map(renderItem)}
            </View>
          </View>
        ))}
      </ScrollView>

      {/* SMART CHOICE MODAL — interactive options instead of a static jump */}
      <Modal visible={!!sheet} transparent animationType="fade" onRequestClose={() => setSheet(null)}>
        <Pressable style={styles.overlay} onPress={() => setSheet(null)}>
          <Pressable style={styles.sheet} onPress={() => {}}>
            <View style={styles.sheetHandle} />
            <Text style={styles.sheetTitle}>{sheet?.title}</Text>
            <Text style={styles.sheetSub}>Čo chcete urobiť?</Text>
            {(sheet?.choices || []).map((c, i) => (
              <Pressable key={i} testID={`${sheet?.testID}-choice-${i}`} onPress={() => pick(c)}
                style={({ pressed }) => [styles.choiceRow, pressed && { backgroundColor: C.surface3 }]}>
                <View style={styles.choiceIcon}><Ionicons name={c.icon} size={20} color={C.brand} /></View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.choiceLabel}>{c.label}</Text>
                  {!!c.sub && <Text style={styles.choiceSub}>{c.sub}</Text>}
                </View>
                <Ionicons name="chevron-forward" size={16} color={C.info} />
              </Pressable>
            ))}
            <Pressable testID={`${sheet?.testID}-choice-cancel`} onPress={() => setSheet(null)} style={styles.cancelBtn}>
              <Text style={styles.cancelText}>ZRUŠIŤ</Text>
            </Pressable>
          </Pressable>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.xl, paddingVertical: S.md },
  wordmark: { color: C.brand, fontSize: 15, fontWeight: '900', letterSpacing: 4 },
  heroIcon: { width: 60, height: 60, borderRadius: R.lg, backgroundColor: C.brandTer, alignItems: 'center', justifyContent: 'center' },
  title: { marginTop: S.lg, fontSize: 28, fontWeight: '900', color: C.fg, letterSpacing: 0.5 },
  subtitle: { marginTop: 4, fontSize: 14, color: C.onS3, lineHeight: 20 },
  sectionTitle: { marginTop: S.xl, marginBottom: S.md, fontSize: 11, letterSpacing: 2.5, color: C.brand, fontWeight: '900' },
  row: { flexDirection: 'row', alignItems: 'center', gap: S.lg, backgroundColor: C.surface2, borderRadius: R.lg, padding: S.lg, minHeight: 72, borderWidth: 1, borderColor: C.border },
  rowIcon: { width: 44, height: 44, borderRadius: R.md, backgroundColor: C.brandTer, alignItems: 'center', justifyContent: 'center' },
  rowTitle: { fontWeight: '800', fontSize: 15, color: C.fg },
  rowSub: { fontSize: 12, color: C.info, marginTop: 2 },
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.72)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: C.surface2, borderTopLeftRadius: R.lg, borderTopRightRadius: R.lg, padding: S.xl, paddingBottom: 34, borderWidth: 1, borderColor: C.borderStrong },
  sheetHandle: { alignSelf: 'center', width: 44, height: 5, borderRadius: 3, backgroundColor: C.surface3, marginBottom: S.md },
  sheetTitle: { color: C.fg, fontWeight: '900', fontSize: 18 },
  sheetSub: { color: C.info, fontSize: 12, marginTop: 2, marginBottom: S.md },
  choiceRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, paddingVertical: S.md, paddingHorizontal: S.sm, borderRadius: R.md, minHeight: 56 },
  choiceIcon: { width: 40, height: 40, borderRadius: R.pill, backgroundColor: C.brandTer, alignItems: 'center', justifyContent: 'center' },
  choiceLabel: { color: C.fg, fontWeight: '800', fontSize: 14 },
  choiceSub: { color: C.info, fontSize: 11, marginTop: 1 },
  cancelBtn: { marginTop: S.md, alignItems: 'center', justifyContent: 'center', minHeight: 48, borderWidth: 1.5, borderColor: C.border, borderRadius: R.pill },
  cancelText: { color: C.info, fontWeight: '900', letterSpacing: 2, fontSize: 12 },
});
