import React from 'react';
import { View, Text, Pressable, StyleSheet, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { C, S, R } from './theme';

export type HubItem = { testID: string; icon: any; title: string; subtitle: string; route?: string; onPress?: () => void };

export default function PillarHub({ title, subtitle, icon, items, testID }: { title: string; subtitle: string; icon: any; items: HubItem[]; testID: string }) {
  const router = useRouter();
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
        <View style={{ marginTop: S.xl, gap: S.md }}>
          {items.map(it => (
            <Pressable
              key={it.testID}
              testID={it.testID}
              onPress={it.onPress || (() => it.route && router.push(it.route as any))}
              style={({ pressed }) => [styles.row, pressed && { backgroundColor: C.surface3 }]}
            >
              <View style={styles.rowIcon}>
                <Ionicons name={it.icon} size={22} color={C.brand} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.rowTitle}>{it.title}</Text>
                <Text style={styles.rowSub}>{it.subtitle}</Text>
              </View>
              <Ionicons name="chevron-forward" size={18} color={C.info} />
            </Pressable>
          ))}
        </View>
      </ScrollView>
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
  row: { flexDirection: 'row', alignItems: 'center', gap: S.lg, backgroundColor: C.surface2, borderRadius: R.lg, padding: S.lg, minHeight: 72, borderWidth: 1, borderColor: C.border },
  rowIcon: { width: 44, height: 44, borderRadius: R.md, backgroundColor: C.brandTer, alignItems: 'center', justifyContent: 'center' },
  rowTitle: { fontWeight: '800', fontSize: 15, color: C.fg },
  rowSub: { fontSize: 12, color: C.info, marginTop: 2 },
});
