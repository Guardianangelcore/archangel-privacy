/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// SOVEREIGN ACHIEVEMENTS — the gold-badge dopamine layer.
// Each milestone in the Guardian journey lights a Sovereign badge.
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, S, R, GOLD } from '@/src/theme';
import { tap } from '@/src/ui/glass';
import { speak as jarvisSpeak } from '@/src/voice';

type Badge = {
  key: string;
  title: string;
  hint: string;
  icon: any;
  unlocked: boolean;
  unlocked_at?: string | null;
};

export default function Achievements() {
  const router = useRouter();
  const { user } = useAuth();
  const [data, setData] = useState<{ unlocked: Badge[]; locked: Badge[]; unlocked_count: number; total: number; progress: number } | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r: any = await api('/achievements');
      setData(r);
    } catch (e) { console.log('ach err', e); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const celebrate = (b: Badge) => {
    tap('success');
    if (b.unlocked) {
      jarvisSpeak(`${b.title}. Odomknuté.`, {
        voice: 'onyx', speed: 0.95, language: (user?.language as any) || 'sk',
      });
    } else {
      jarvisSpeak(b.hint, {
        voice: 'onyx', speed: 0.95, language: (user?.language as any) || 'sk',
      });
    }
  };

  if (loading || !data) {
    return (
      <SafeAreaView style={styles.root} edges={['top']}>
        <View style={styles.center}><ActivityIndicator color={C.brand} size="large" /></View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView testID="achievements-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="ach-back" onPress={() => { tap(); router.back(); }} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>SOVEREIGN ODZNAKY</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView
        contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.brand} />}
      >
        {/* Hero progress */}
        <View style={styles.hero}>
          <LinearGradient colors={GOLD as any} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.heroBg}>
            <Ionicons name="trophy" size={40} color={C.onInverse} />
            <View style={{ flex: 1 }}>
              <Text style={styles.heroCount}>{data.unlocked_count} / {data.total}</Text>
              <Text style={styles.heroSub}>ODZNAKOV ODOMKNUTÝCH · {data.progress} %</Text>
              <View style={styles.progBar}>
                <View style={[styles.progFill, { width: `${data.progress}%` }]} />
              </View>
            </View>
          </LinearGradient>
        </View>

        {data.unlocked.length > 0 && (
          <>
            <Text style={styles.section}>ZÍSKANÉ</Text>
            <View style={styles.grid}>
              {data.unlocked.map((b) => (
                <Pressable
                  key={b.key}
                  testID={`ach-badge-${b.key}`}
                  onPress={() => celebrate(b)}
                  style={styles.card}
                >
                  <LinearGradient colors={GOLD as any} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.badgeGold}>
                    <Ionicons name={b.icon} size={30} color={C.onInverse} />
                  </LinearGradient>
                  <Text style={styles.badgeTitle} numberOfLines={2}>{b.title}</Text>
                  <Text style={styles.badgeState}>✓ ODOMKNUTÉ</Text>
                </Pressable>
              ))}
            </View>
          </>
        )}

        <Text style={styles.section}>ZAMKNUTÉ</Text>
        <View style={styles.grid}>
          {data.locked.map((b) => (
            <Pressable
              key={b.key}
              testID={`ach-badge-${b.key}`}
              onPress={() => celebrate(b)}
              style={styles.card}
            >
              <View style={styles.badgeLocked}>
                <Ionicons name={b.icon} size={30} color={C.info} />
                <View style={styles.lockDot}>
                  <Ionicons name="lock-closed" size={12} color={C.onInverse} />
                </View>
              </View>
              <Text style={[styles.badgeTitle, { color: C.onS3 }]} numberOfLines={2}>{b.title}</Text>
              <Text style={styles.badgeHint} numberOfLines={3}>{b.hint}</Text>
            </Pressable>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.brand, fontWeight: '900', fontSize: 14, letterSpacing: 2.5 },
  hero: { borderRadius: R.lg, overflow: 'hidden', marginBottom: S.xl, shadowColor: C.brand, shadowOpacity: 0.4, shadowRadius: 20, shadowOffset: { width: 0, height: 6 }, elevation: 12 },
  heroBg: { flexDirection: 'row', alignItems: 'center', gap: S.lg, padding: S.xl },
  heroCount: { color: C.onInverse, fontWeight: '900', fontSize: 30, letterSpacing: 1 },
  heroSub: { color: 'rgba(255,255,255,0.9)', fontWeight: '900', fontSize: 10, letterSpacing: 2, marginTop: 2 },
  progBar: { marginTop: 8, height: 6, backgroundColor: 'rgba(0,0,0,0.25)', borderRadius: 3, overflow: 'hidden' },
  progFill: { height: '100%', backgroundColor: C.onInverse },
  section: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 2.5, marginBottom: S.md, marginTop: S.md },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: S.md },
  card: { width: '47%', backgroundColor: C.surface2, borderRadius: R.md, padding: S.md, alignItems: 'center', gap: 8, minHeight: 170, borderWidth: 1, borderColor: C.border },
  badgeGold: { width: 68, height: 68, borderRadius: 34, alignItems: 'center', justifyContent: 'center', shadowColor: C.brand, shadowOpacity: 0.5, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 8 },
  badgeLocked: { width: 68, height: 68, borderRadius: 34, alignItems: 'center', justifyContent: 'center', backgroundColor: C.surface3, borderWidth: 1.5, borderStyle: 'dashed', borderColor: C.borderStrong },
  lockDot: { position: 'absolute', bottom: -2, right: -2, width: 22, height: 22, borderRadius: 11, backgroundColor: C.error, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: C.bg },
  badgeTitle: { color: C.fg, fontWeight: '900', fontSize: 12, letterSpacing: 0.5, textAlign: 'center' },
  badgeState: { color: C.brand, fontSize: 9, letterSpacing: 1.5, fontWeight: '900' },
  badgeHint: { color: C.info, fontSize: 10, lineHeight: 14, textAlign: 'center' },
});
