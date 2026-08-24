/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, Platform, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';

export default function MedicalNews() {
  const router = useRouter();
  const [feed, setFeed] = useState<any>(null);
  const [tracker, setTracker] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const [f, t2] = await Promise.all([api('/news/feed'), api('/news/tech-tracker')]);
      setFeed(f); setTracker(t2);
    } catch (e: any) { setErr(String(e.message || e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const hap = () => { if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {}); };

  const hunt = async (n: any) => {
    hap(); setBusy(n.news_id); setErr(''); setMsg('');
    try {
      const r: any = await api(`/news/${n.news_id}/hunt`, { method: 'POST' });
      setMsg(r.message);
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const NewsCard = ({ n, personalized }: any) => (
    <View style={[styles.card, personalized && { borderColor: '#B8860B', borderWidth: 2 }]}>
      {personalized && (
        <View style={styles.matchBadge}>
          <Ionicons name="person" size={10} color={C.onInverse} />
          <Text style={styles.matchText}>ZHODA S VAŠÍM TREZOROM · {n.matched_tags.slice(0, 3).join(', ')}</Text>
        </View>
      )}
      <Text style={styles.cardTitle}>{n.high_tech ? '⚡ ' : ''}{n.title}</Text>
      <Text style={styles.cardSummary}>{n.summary}</Text>
      <Text style={styles.cardMeta}>{n.region} · {n.specialty} · {n.source}</Text>
      {!!n.savings_note && <Text style={styles.savings}>💰 Wealth Advisor: {n.savings_note}</Text>}
      {personalized && !!n.jarvis_alert && <Text style={styles.jarvisAlert}>🧠 „{n.jarvis_alert}“</Text>}
      <View style={styles.actions}>
        <Pressable testID={`news-hunt-${n.news_id}`} onPress={() => hunt(n)} disabled={busy === n.news_id} style={styles.huntBtn}>
          <Ionicons name="search" size={14} color={C.onInverse} />
          <Text style={styles.huntText}>{busy === n.news_id ? '…' : 'ULOVIŤ TERMÍN'}</Text>
        </Pressable>
        <Pressable testID={`news-jarvis-${n.news_id}`} onPress={() => { hap(); router.push('/jarvis'); }} style={styles.consultBtn}>
          <Ionicons name="sparkles" size={14} color={C.brand} />
          <Text style={styles.consultText}>KONZULTOVAŤ S JARVISOM</Text>
        </Pressable>
      </View>
    </View>
  );

  return (
    <SafeAreaView testID="medical-news-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="nw-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>MEDICAL NEWS SENTINEL</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView
        contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} tintColor={C.brand} />}
      >
        <Text style={styles.h1}>Breaking Medical Insights</Text>
        <Text style={styles.sub}>Svetové prelomy krížené s vaším Trezorom. Čo sa týka práve vás, je hore — so Jarvis alertom a tlačidlom na lov termínu.</Text>
        {!!msg && <Text style={styles.info}>{msg}</Text>}
        {!!err && <Text style={styles.err}>{err}</Text>}

        <Text style={styles.section}>🎯 PRE VÁS ({feed?.personalized?.length ?? '…'})</Text>
        {(feed?.personalized || []).map((n: any) => <NewsCard key={n.news_id} n={n} personalized />)}
        {feed && feed.personalized.length === 0 && (
          <Text style={styles.empty}>Zatiaľ žiadna osobná zhoda — nahrajte lekárske dokumenty do Trezoru a Sentinel začne párovať prelomy s vaším zdravím.</Text>
        )}

        <Text style={styles.section}>⚡ TECH-TRACKER CZ/SK — ROBOTIKA & 3D</Text>
        <Text style={styles.trackerNote}>{tracker?.hunter_note || ''}</Text>
        {(tracker?.deployments || []).slice(0, 4).map((n: any) => (
          <View key={n.news_id} style={styles.techRow}>
            <Ionicons name="hardware-chip" size={16} color={C.brand} />
            <Text style={styles.techText} numberOfLines={2}>{n.title} · {n.hunt_city}</Text>
          </View>
        ))}

        <Text style={styles.section}>🌍 GLOBÁLNY FEED</Text>
        {(feed?.general || []).map((n: any) => <NewsCard key={n.news_id} n={n} />)}

        <Text style={styles.disclaimer}>{feed?.note || ''} Informačný obsah — nejde o lekárske odporúčanie.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 2, fontSize: 13 },
  h1: { fontSize: 24, fontWeight: '900', color: C.fg },
  sub: { marginTop: S.sm, fontSize: 12.5, color: C.onS3, lineHeight: 18 },
  section: { marginTop: S.xl, marginBottom: S.sm, fontSize: 11, letterSpacing: 1.5, color: C.brand, fontWeight: '900' },
  card: { backgroundColor: C.surface2, borderRadius: R.md, padding: S.md, marginTop: S.sm, borderWidth: 1, borderColor: C.border },
  matchBadge: { flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: '#B8860B', alignSelf: 'flex-start', borderRadius: R.sm, paddingHorizontal: 8, paddingVertical: 4, marginBottom: S.sm },
  matchText: { color: C.onInverse, fontSize: 8, fontWeight: '900', letterSpacing: 0.5 },
  cardTitle: { color: C.fg, fontWeight: '900', fontSize: 14, lineHeight: 19 },
  cardSummary: { color: C.onS3, fontSize: 12, lineHeight: 17, marginTop: 4 },
  cardMeta: { color: C.info, fontSize: 9.5, marginTop: 6 },
  savings: { color: '#B8860B', fontSize: 11, fontWeight: '700', marginTop: 6 },
  jarvisAlert: { color: C.brand, fontSize: 11, fontStyle: 'italic', marginTop: 6, lineHeight: 15 },
  actions: { flexDirection: 'row', gap: S.sm, marginTop: S.md, flexWrap: 'wrap' },
  huntBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: C.inverse, borderRadius: R.sm, paddingHorizontal: S.md, minHeight: 44, justifyContent: 'center' },
  huntText: { color: C.onInverse, fontWeight: '900', fontSize: 10, letterSpacing: 0.5 },
  consultBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, borderWidth: 1.5, borderColor: C.brand, borderRadius: R.sm, paddingHorizontal: S.md, minHeight: 44, justifyContent: 'center' },
  consultText: { color: C.brand, fontWeight: '900', fontSize: 10, letterSpacing: 0.5 },
  techRow: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: C.border },
  techText: { flex: 1, color: C.fg, fontSize: 11.5 },
  trackerNote: { color: C.info, fontSize: 10.5, marginBottom: 4 },
  empty: { color: C.onS3, fontSize: 12, lineHeight: 17 },
  info: { color: '#5FA779', marginTop: S.md, fontSize: 12 },
  err: { color: C.error, marginTop: S.md, fontSize: 12 },
  disclaimer: { marginTop: S.xl, color: C.info, fontSize: 10, lineHeight: 15, textAlign: 'center' },
});
