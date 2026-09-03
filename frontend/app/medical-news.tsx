/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, Platform, RefreshControl, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

export default function MedicalNews() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const [feed, setFeed] = useState<any>(null);
  const [tracker, setTracker] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  const pollRef = useRef(0);
  const load = useCallback(async (force = false) => {
    try {
      const [f, t2] = await Promise.all([api(force ? '/news/feed?force=true' : '/news/feed'), api('/news/tech-tracker')]);
      setFeed(f); setTracker(t2);
      // Live sources are fetched in the background (~25 s) — poll a few times until they land
      if (f?.pending && pollRef.current < 8) { pollRef.current += 1; setTimeout(() => load(), 10000); }
      else if (!f?.pending) pollRef.current = 0;
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
          <Text style={styles.matchText}>{tt('medical_news.matches_your_vault')} {n.matched_tags.slice(0, 3).join(', ')}</Text>
        </View>
      )}
      <Text style={styles.cardTitle}>{n.high_tech ? '⚡ ' : ''}{tx(n.title)}</Text>
      <Text style={styles.cardSummary}>{n.summary}</Text>
      <Text style={styles.cardMeta}>{n.region} · {n.specialty} · {n.source}{n.date ? ` · ${n.date}` : ''}{n.hunt_city ? ` · 🏥 ${n.hunt_city}` : ''}</Text>
      {!!n.url && (
        <Pressable testID={`news-source-${n.news_id}`} onPress={() => Linking.openURL(n.url)} hitSlop={6} style={styles.sourceBtn}>
          <Ionicons name="open-outline" size={12} color={C.brand} />
          <Text style={styles.sourceText} numberOfLines={1}>{n.url.replace(/^https?:\/\//, '')}</Text>
        </Pressable>
      )}
      {!!n.savings_note && <Text style={styles.savings}>{tt('medical_news.wealth_advisor')} {n.savings_note}</Text>}
      {personalized && !!n.jarvis_alert && <Text style={styles.jarvisAlert}>🧠 „{n.jarvis_alert}“</Text>}
      <View style={styles.actions}>
        {!!n.hunt_city && (
          <Pressable testID={`news-hunt-${n.news_id}`} onPress={() => hunt(n)} disabled={busy === n.news_id} style={styles.huntBtn}>
            <Ionicons name="search" size={14} color={C.onInverse} />
            <Text style={styles.huntText}>{busy === n.news_id ? '…' : tt('medical_news.hunt_an_appointment')}</Text>
          </Pressable>
        )}
        <Pressable testID={`news-jarvis-${n.news_id}`} onPress={() => { hap(); router.push('/jarvis'); }} style={styles.consultBtn}>
          <Ionicons name="sparkles" size={14} color={C.brand} />
          <Text style={styles.consultText}>{tt('medical_news.consult_with_jarvis')}</Text>
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
        <Text style={styles.title}>{tt('medical_news.medical_news_sentinel')}</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView
        contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(true); setRefreshing(false); }} tintColor={C.brand} />}
      >
        <Text style={styles.h1}>{tt('medical_news.breaking_medical_insights')}</Text>
        <Text style={styles.sub}>{tt('medical_news.world_breakthroughs_matched_against')}</Text>
        {feed && (
          <View testID="news-live-badge" style={[styles.liveBadge, !feed.live && { borderColor: C.border }]}>
            <View style={[styles.liveDot, { backgroundColor: feed.live ? '#5FA779' : feed.pending ? '#FFC53D' : C.info }]} />
            <Text style={styles.liveText}>
              {feed.live
                ? tt('medical_news.live', [feed.engine, feed.fetched_at ? ` · updated ${new Date(feed.fetched_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : '', feed.pending ? ' · refreshing…' : ''])
                : feed.pending ? tt('medical_news.fetching_live_sources_perplexity_son') : tt('medical_news.curated_feed_live_retrieval_offline')}
            </Text>
          </View>
        )}
        {!!msg && <Text style={styles.info}>{msg}</Text>}
        {!!err && <Text style={styles.err}>{err}</Text>}

        <Text style={styles.section}>{tt('medical_news.for_you')}{feed?.personalized?.length ?? '…'})</Text>
        {(feed?.personalized || []).map((n: any) => <NewsCard key={n.news_id} n={n} personalized />)}
        {feed && feed.personalized.length === 0 && (
          <Text style={styles.empty}>{tt('medical_news.no_personal_match_yet_upload_medical')}</Text>
        )}

        <Text style={styles.section}>{tt('medical_news.tech_tracker_cz_sk_robotika_3d')}</Text>
        <Text style={styles.trackerNote}>{tracker?.hunter_note || ''}</Text>
        {(tracker?.deployments || []).slice(0, 4).map((n: any) => (
          <View key={n.news_id} style={styles.techRow}>
            <Ionicons name="hardware-chip" size={16} color={C.brand} />
            <Text style={styles.techText} numberOfLines={2}>{tx(n.title)} · {n.hunt_city}</Text>
          </View>
        ))}

        <Text style={styles.section}>{tt('medical_news.global_feed')}</Text>
        {(feed?.general || []).map((n: any) => <NewsCard key={n.news_id} n={n} />)}

        <Text style={styles.disclaimer}>{feed?.note || ''} {tt('medical_news.informational_content_not_medical_ad')}</Text>
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
  sourceBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 6, minHeight: 28 },
  sourceText: { color: C.brand, fontSize: 10, textDecorationLine: 'underline', flex: 1 },
  liveBadge: { flexDirection: 'row', alignItems: 'center', gap: 6, alignSelf: 'flex-start', marginTop: S.md, borderWidth: 1, borderColor: '#5FA779', borderRadius: R.sm, paddingHorizontal: 10, paddingVertical: 5 },
  liveDot: { width: 7, height: 7, borderRadius: 4 },
  liveText: { color: C.fg, fontSize: 9, fontWeight: '900', letterSpacing: 0.8 },
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
