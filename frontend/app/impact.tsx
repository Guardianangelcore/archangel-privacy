/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// IMPACT DASHBOARD — "Môj svetový odtlačok".
// Shows the user exactly how their anonymized data helps global research.
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

type ImpactData = {
  people_helped: number;
  research_hours: number;
  tokens_earned: number;
  contributions_total: number;
  top_thread: { title: string; contributions: number; message_sk: string } | null;
  timeline_weeks: { week_ago: number; contributions: number }[];
  breakdown: { physio: number; pain_logs: number; scam_reports: number; wellness: number; vitals: number; documents: number };
  cta_sk: string;
};

export default function Impact() {
  const router = useRouter();
  const { user } = useAuth();
  const [data, setData] = useState<ImpactData | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r: any = await api('/impact/dashboard');
      setData(r);
    } catch (e) { console.log(e); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const speakThread = () => {
    if (!data?.top_thread) return;
    jarvisSpeak(data.top_thread.message_sk, {
      voice: 'onyx', speed: 0.95, language: (user?.language as any) || 'sk',
    });
  };

  if (loading || !data) {
    return (
      <SafeAreaView style={styles.root} edges={['top']}>
        <View style={styles.center}><ActivityIndicator color={C.brand} size="large" /></View>
      </SafeAreaView>
    );
  }

  const maxWeek = Math.max(1, ...data.timeline_weeks.map((w) => w.contributions));

  return (
    <SafeAreaView testID="impact-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="impact-back" onPress={() => { tap(); router.back(); }} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>MÔJ SVETOVÝ ODTLAČOK</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView
        contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.brand} />}
      >
        {/* HERO — the "wow" line */}
        <View style={styles.hero}>
          <LinearGradient colors={GOLD as any} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.heroBg}>
            <Ionicons name="planet" size={40} color={C.onInverse} />
            <View style={{ flex: 1 }}>
              <Text style={styles.heroNumber}>{data.people_helped.toLocaleString('sk-SK')}</Text>
              <Text style={styles.heroLbl}>ĽUDÍ JE VĎAKA VÁM O KROK BLIŽŠIE K LIEČBE</Text>
            </View>
          </LinearGradient>
        </View>

        {/* KPI row */}
        <View style={styles.kpiRow}>
          <View style={styles.kpi}>
            <Ionicons name="hourglass" size={20} color={C.brand} />
            <Text style={styles.kpiVal}>{data.research_hours} h</Text>
            <Text style={styles.kpiLbl}>ZRÝCHLENIE VÝSKUMU</Text>
          </View>
          <View style={styles.kpi}>
            <Ionicons name="cash" size={20} color={C.brand} />
            <Text style={styles.kpiVal}>{data.tokens_earned}</Text>
            <Text style={styles.kpiLbl}>GA-T ZAROBENÉ</Text>
          </View>
          <View style={styles.kpi}>
            <Ionicons name="pulse" size={20} color={C.brand} />
            <Text style={styles.kpiVal}>{data.contributions_total}</Text>
            <Text style={styles.kpiLbl}>PRÍSPEVKOV</Text>
          </View>
        </View>

        {/* Top research thread */}
        {data.top_thread && (
          <Pressable testID="impact-top-thread" onPress={speakThread} style={styles.thread}>
            <View style={styles.threadRing}>
              <Ionicons name="mic-circle" size={22} color={C.brand} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.threadTitle}>{data.top_thread.title.toUpperCase()}</Text>
              <Text style={styles.threadMsg}>{data.top_thread.message_sk}</Text>
              <Text style={styles.threadTap}>▸ ŤUKNITE — JARVIS TO PREČÍTA</Text>
            </View>
          </Pressable>
        )}

        {/* 4-week timeline */}
        <Text style={styles.section}>POSLEDNÉ 4 TÝŽDNE</Text>
        <View style={styles.timeline}>
          {data.timeline_weeks.map((w) => (
            <View key={w.week_ago} style={styles.tlCol}>
              <View style={styles.tlBarWrap}>
                <View style={[styles.tlBar, { height: Math.max(4, (w.contributions / maxWeek) * 80) }]} />
              </View>
              <Text style={styles.tlLbl}>{w.week_ago === 0 ? 'T-4' : w.week_ago === 3 ? 'TENTO' : `T-${3 - w.week_ago}`}</Text>
              <Text style={styles.tlCount}>{w.contributions}</Text>
            </View>
          ))}
        </View>

        {/* Breakdown */}
        <Text style={styles.section}>KDE PRISPIEVATE</Text>
        <View style={styles.breakGrid}>
          {[
            { key: 'physio', label: 'Physio-AI', icon: 'fitness', val: data.breakdown.physio },
            { key: 'pain', label: 'Pain-Signal', icon: 'thermometer', val: data.breakdown.pain_logs },
            { key: 'wellness', label: 'Wellness', icon: 'happy', val: data.breakdown.wellness },
            { key: 'scam', label: 'Scam-Shield', icon: 'shield-checkmark', val: data.breakdown.scam_reports },
            { key: 'vitals', label: 'Vitálne funkcie', icon: 'heart', val: data.breakdown.vitals },
            { key: 'docs', label: 'Dokumenty', icon: 'documents', val: data.breakdown.documents },
          ].map((b) => (
            <View key={b.key} style={styles.breakCard}>
              <Ionicons name={b.icon as any} size={20} color={b.val > 0 ? C.brand : C.info} />
              <Text style={[styles.breakVal, { color: b.val > 0 ? C.brand : C.info }]}>{b.val}</Text>
              <Text style={styles.breakLbl}>{b.label}</Text>
            </View>
          ))}
        </View>

        <Text style={styles.cta}>{data.cta_sk}</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.brand, fontWeight: '900', fontSize: 13, letterSpacing: 2 },
  hero: { borderRadius: R.lg, overflow: 'hidden', marginBottom: S.xl, shadowColor: C.brand, shadowOpacity: 0.4, shadowRadius: 20, shadowOffset: { width: 0, height: 6 }, elevation: 12 },
  heroBg: { flexDirection: 'row', alignItems: 'center', gap: S.lg, padding: S.xl },
  heroNumber: { color: C.onInverse, fontWeight: '900', fontSize: 32, letterSpacing: 1 },
  heroLbl: { color: 'rgba(255,255,255,0.9)', fontWeight: '900', fontSize: 10, letterSpacing: 1.5, marginTop: 2 },
  kpiRow: { flexDirection: 'row', gap: S.md, marginBottom: S.lg },
  kpi: { flex: 1, alignItems: 'center', gap: 4, backgroundColor: C.surface2, borderRadius: R.md, padding: S.md, borderWidth: 1, borderColor: C.border },
  kpiVal: { color: C.fg, fontWeight: '900', fontSize: 18 },
  kpiLbl: { color: C.onS3, fontSize: 8, letterSpacing: 1.5, textAlign: 'center', fontWeight: '900' },
  thread: { flexDirection: 'row', gap: S.md, padding: S.md, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1.5, borderColor: C.brand, marginBottom: S.xl },
  threadRing: { width: 48, height: 48, borderRadius: 24, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(212,175,55,0.1)', borderWidth: 1.5, borderColor: C.brand },
  threadTitle: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 2 },
  threadMsg: { color: C.fg, fontSize: 12, lineHeight: 16, marginTop: 4 },
  threadTap: { color: C.info, fontSize: 9, letterSpacing: 1.5, fontWeight: '900', marginTop: 6 },
  section: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 2, marginBottom: S.md, marginTop: S.md },
  timeline: { flexDirection: 'row', alignItems: 'flex-end', gap: 8, height: 130, backgroundColor: C.surface2, borderRadius: R.md, padding: S.md, borderWidth: 1, borderColor: C.border },
  tlCol: { flex: 1, alignItems: 'center', gap: 4, justifyContent: 'flex-end' },
  tlBarWrap: { justifyContent: 'flex-end', height: 80 },
  tlBar: { width: 24, borderRadius: 4, backgroundColor: C.brand },
  tlLbl: { color: C.onS3, fontSize: 9, fontWeight: '900', letterSpacing: 1 },
  tlCount: { color: C.brand, fontWeight: '900', fontSize: 11 },
  breakGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: S.sm },
  breakCard: { width: '31%', alignItems: 'center', gap: 4, backgroundColor: C.surface2, borderRadius: R.md, padding: S.md, borderWidth: 1, borderColor: C.border, minHeight: 100 },
  breakVal: { fontWeight: '900', fontSize: 18 },
  breakLbl: { color: C.onS3, fontSize: 9, letterSpacing: 0.8, textAlign: 'center', fontWeight: '900' },
  cta: { color: C.brand, fontSize: 13, fontWeight: '900', letterSpacing: 1, textAlign: 'center', marginTop: S.xl, fontStyle: 'italic' },
});
