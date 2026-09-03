/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, FlatList, TextInput, ScrollView, Modal, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { WheelField } from '@/src/ui/fields';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';
import { useI18n } from '@/src/i18n-context';

type Provider = { provider_id: string; name: string; city: string; specialty: string; avg_score: number; review_count: number; tags: string[]; avg_minority_safety?: number | null; avg_waiting_weeks?: number | null; avg_financial_transparency?: number | null };
const TAGS = ['LGBTI+', 'SENIOR-FRIENDLY', 'DISABILITY', 'ROMA', 'MULTILINGUAL', 'RESPECT'];

export default function RespectMap() {
  const { t: tt, tx } = useI18n();
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'en';
  const router = useRouter();
  const [items, setItems] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(false);
  const [modal, setModal] = useState(false);
  const [f, setF] = useState({ name: '', city: 'Bratislava', specialty: '', respect_score: 5, tags: [] as string[], review: '', minority_safety: 0, waiting_weeks: '', financial_transparency: 0 });

  const load = useCallback(async () => {
    setLoading(true);
    try { setItems(await api<Provider[]>('/respect/providers')); } catch {}
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    if (!f.name || !f.specialty) return;
    await api('/respect/providers', { method: 'POST', body: JSON.stringify({
      name: f.name, city: f.city, specialty: f.specialty, respect_score: f.respect_score,
      tags: f.tags, review: f.review,
      minority_safety: f.minority_safety || null,
      waiting_weeks: f.waiting_weeks !== '' ? parseInt(f.waiting_weeks, 10) : null,
      financial_transparency: f.financial_transparency || null,
    }) });
    setModal(false); setF({ name: '', city: 'Bratislava', specialty: '', respect_score: 5, tags: [], review: '', minority_safety: 0, waiting_weeks: '', financial_transparency: 0 }); load();
  };

  const toggleTag = (tg: string) => setF(v => ({ ...v, tags: v.tags.includes(tg) ? v.tags.filter(x => x !== tg) : [...v.tags, tg] }));

  return (
    <SafeAreaView testID="respect-map-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="rm-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={styles.title}>{tt('respect_map.respect_map')}</Text>
        <View style={{ width: 26 }} />
      </View>
      <View style={styles.sub}><Text style={styles.subText}>{tt('respect_map.crowd_sourced_lgbti_senior_disabilit')}</Text></View>

      <FlatList
        data={items}
        keyExtractor={i => i.provider_id}
        contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.fg} />}
        ListEmptyComponent={!loading ? <Text style={styles.empty}>{tt('respect_map.no_providers_rated_yet')}</Text> : null}
        renderItem={({ item }) => (
          <View testID={`prov-${item.provider_id}`} style={styles.card}>
            <View style={styles.rowSpread}>
              <View style={{ flex: 1 }}>
                <Text style={styles.provName}>{item.name}</Text>
                <Text style={styles.provMeta}>{item.specialty} · {item.city}</Text>
              </View>
              <View style={styles.scoreBox}>
                <Text style={styles.scoreVal}>{item.avg_score.toFixed(1)}</Text>
                <Text style={styles.scoreLbl}>/ 5</Text>
              </View>
            </View>
            <View style={styles.tagRow}>
              {item.tags?.slice(0,4).map(tg => <View key={tg} style={styles.tagChip}><Text style={styles.tagText}>{tg}</Text></View>)}
            </View>
            <View style={styles.metricsRow}>
              <View style={styles.metricBox}>
                <Ionicons name="heart-outline" size={14} color={C.brand} />
                <Text style={styles.metricVal}>{item.avg_minority_safety ? item.avg_minority_safety.toFixed(1) : '—'}</Text>
                <Text style={styles.metricLbl}>{t('minority_safety', lang).toUpperCase()}</Text>
              </View>
              <View style={styles.metricBox}>
                <Ionicons name="time-outline" size={14} color={C.brand} />
                <Text style={styles.metricVal}>{item.avg_waiting_weeks != null ? `${Math.round(item.avg_waiting_weeks)} t.` : '—'}</Text>
                <Text style={styles.metricLbl}>{t('real_wait', lang).toUpperCase()}</Text>
              </View>
              <View style={styles.metricBox}>
                <Ionicons name="cash-outline" size={14} color={C.brand} />
                <Text style={styles.metricVal}>{item.avg_financial_transparency ? item.avg_financial_transparency.toFixed(1) : '—'}</Text>
                <Text style={styles.metricLbl}>{t('fin_transparency', lang).toUpperCase()}</Text>
              </View>
            </View>
            <Text style={styles.reviewCount}>{item.review_count} {tt('respect_map.review')}{item.review_count > 1 ? 'S' : ''}</Text>
          </View>
        )}
      />

      <Pressable testID="rm-rate-btn" onPress={() => setModal(true)} style={styles.fab}>
        <Ionicons name="add" size={22} color={C.onInverse} />
        <Text style={styles.fabText}>{t('rate_provider', lang).toUpperCase()}</Text>
      </Pressable>

      <Modal visible={modal} animationType="slide" transparent>
        <View style={styles.modalRoot}>
          <View style={styles.modalCard}>
            <View style={styles.modalHead}><Text style={styles.modalTitle}>{tt('respect_map.rate_provider')}</Text>
              <Pressable onPress={() => setModal(false)}><Ionicons name="close" size={22} color={C.onInverse} /></Pressable></View>
            <ScrollView contentContainerStyle={{ padding: S.lg, gap: S.md }}>
              <TextInput testID="rm-name" placeholder={tt('respect_map.provider_name')} value={f.name} onChangeText={v => setF({ ...f, name: v })} style={styles.input} placeholderTextColor="#999" />
              <TextInput testID="rm-spec" placeholder={tt('respect_map.specialty')} value={f.specialty} onChangeText={v => setF({ ...f, specialty: v })} style={styles.input} placeholderTextColor="#999" />
              <TextInput testID="rm-city" placeholder={tt('respect_map.city')} value={f.city} onChangeText={v => setF({ ...f, city: v })} style={styles.input} placeholderTextColor="#999" />
              <Text style={styles.lbl}>{t('respect_score', lang).toUpperCase()}</Text>
              <View style={{ flexDirection: 'row', gap: S.sm }}>
                {[1,2,3,4,5].map(n => (
                  <Pressable testID={`score-${n}`} key={n} onPress={() => setF({ ...f, respect_score: n })} style={[styles.starChip, f.respect_score === n && styles.starChipActive]}>
                    <Text style={[styles.starText, f.respect_score === n && styles.starTextActive]}>{n}</Text>
                  </Pressable>
                ))}
              </View>
              <Text style={styles.lbl}>{tt('respect_map.tags')}</Text>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: S.sm }}>
                {TAGS.map(tg => (
                  <Pressable testID={`tag-${tg}`} key={tg} onPress={() => toggleTag(tg)} style={[styles.chip, f.tags.includes(tg) && styles.chipActive]}>
                    <Text style={[styles.chipText, f.tags.includes(tg) && styles.chipTextActive]}>{tg}</Text>
                  </Pressable>
                ))}
              </View>
              <Text style={styles.lbl}>{t('minority_safety', lang).toUpperCase()} {tt('respect_map.lgbti')}</Text>
              <View style={{ flexDirection: 'row', gap: S.sm }}>
                {[1,2,3,4,5].map(n => (
                  <Pressable testID={`ms-${n}`} key={n} onPress={() => setF({ ...f, minority_safety: f.minority_safety === n ? 0 : n })} style={[styles.starChip, f.minority_safety === n && styles.starChipActive]}>
                    <Text style={[styles.starText, f.minority_safety === n && styles.starTextActive]}>{n}</Text>
                  </Pressable>
                ))}
              </View>
              <Text style={styles.lbl}>{t('real_wait', lang).toUpperCase()}</Text>
              <WheelField testID="rm-wait" title={tt('respect_map.waiting_weeks')} min={0} max={104} unit="wks" value={f.waiting_weeks} onChange={v => setF({ ...f, waiting_weeks: v })} placeholder="8" style={styles.input} />
              <Text style={styles.lbl}>{t('fin_transparency', lang).toUpperCase()}</Text>
              <View style={{ flexDirection: 'row', gap: S.sm }}>
                {[1,2,3,4,5].map(n => (
                  <Pressable testID={`ft-${n}`} key={n} onPress={() => setF({ ...f, financial_transparency: f.financial_transparency === n ? 0 : n })} style={[styles.starChip, f.financial_transparency === n && styles.starChipActive]}>
                    <Text style={[styles.starText, f.financial_transparency === n && styles.starTextActive]}>{n}</Text>
                  </Pressable>
                ))}
              </View>
              <TextInput testID="rm-review" placeholder={tt('respect_map.review_optional')} value={f.review} onChangeText={v => setF({ ...f, review: v })} multiline style={[styles.input, { minHeight: 80 }]} placeholderTextColor="#999" />
            </ScrollView>
            <Pressable testID="rm-submit" onPress={submit} style={styles.saveBtn}><Text style={styles.saveBtnText}>{tt('respect_map.submit')}</Text></Pressable>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  sub: { paddingHorizontal: S.lg, paddingVertical: 6, backgroundColor: C.brandTer },
  subText: { color: C.brand, fontSize: 11, fontWeight: '900', letterSpacing: 1.5 },
  empty: { textAlign: 'center', color: C.onS3, marginTop: 60, letterSpacing: 2, fontWeight: '800' },
  card: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginBottom: S.md },
  rowSpread: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  provName: { fontWeight: '900', fontSize: 16, color: C.fg },
  provMeta: { color: C.onS3, fontSize: 12, marginTop: 2 },
  scoreBox: { alignItems: 'center', backgroundColor: C.brand, paddingHorizontal: S.md, paddingVertical: 6 },
  scoreVal: { color: C.onInverse, fontWeight: '900', fontSize: 20 },
  scoreLbl: { color: C.onInverse, opacity: 0.7, fontSize: 10 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: S.sm },
  tagChip: { borderWidth: 1, borderColor: C.borderStrong, paddingHorizontal: 8, paddingVertical: 3 },
  tagText: { fontSize: 10, fontWeight: '800', letterSpacing: 1 },
  metricsRow: { flexDirection: 'row', gap: S.sm, marginTop: S.sm },
  metricBox: { flex: 1, alignItems: 'center', gap: 2, borderWidth: 1, borderColor: C.border, paddingVertical: 6, paddingHorizontal: 2 },
  metricVal: { fontWeight: '900', fontSize: 13, color: C.fg },
  metricLbl: { fontSize: 7, letterSpacing: 0.5, color: C.onS3, fontWeight: '800', textAlign: 'center' },
  reviewCount: { fontSize: 10, letterSpacing: 2, color: C.onS3, marginTop: S.sm, fontWeight: '800' },
  fab: { position: 'absolute', bottom: 24, right: S.lg, flexDirection: 'row', gap: 8, alignItems: 'center', backgroundColor: C.inverse, paddingHorizontal: S.lg, paddingVertical: S.md, borderWidth: 2, borderColor: C.borderStrong },
  fabText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  modalRoot: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  modalCard: { backgroundColor: C.bg, borderTopWidth: 2, borderColor: C.borderStrong, maxHeight: '85%' },
  modalHead: { flexDirection: 'row', justifyContent: 'space-between', padding: S.lg, backgroundColor: C.inverse },
  modalTitle: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 16 },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 15, color: C.fg, backgroundColor: C.bg },
  lbl: { fontSize: 10, letterSpacing: 2, color: C.onS3, fontWeight: '800' },
  starChip: { width: 48, height: 48, borderWidth: 1.5, borderColor: C.borderStrong, alignItems: 'center', justifyContent: 'center' },
  starChipActive: { backgroundColor: C.brand },
  starText: { fontWeight: '900', fontSize: 18, color: C.fg },
  starTextActive: { color: C.onInverse },
  chip: { paddingHorizontal: S.md, paddingVertical: 8, borderWidth: 1.5, borderColor: C.borderStrong },
  chipActive: { backgroundColor: C.inverse },
  chipText: { fontWeight: '800', color: C.fg, fontSize: 11, letterSpacing: 1 },
  chipTextActive: { color: C.onInverse },
  saveBtn: { backgroundColor: C.inverse, paddingVertical: S.lg, alignItems: 'center' },
  saveBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2 },
});
