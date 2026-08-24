/* Copyright © 2026 Guardian Angel. All Rights Reserved. This source code and its logic are the sole property of Guardian Angel. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, FlatList, TextInput, ScrollView, Modal, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import JarvisAdvice from '@/src/JarvisAdvice';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';

type Offer = { offer_id: string; user_id: string; offer_skill: string; want_in_return: string; category: string; city: string; credits_value: number; owner_name: string; status: string };
type Me = { credits: number; trades: any[] };

const CATS = ['health', 'legal', 'craft', 'care', 'food', 'other'];
const CAT_LABELS: Record<string, string> = { health: 'ZDRAVIE', legal: 'PRÁVO', craft: 'REMESLO', care: 'OPATERA', food: 'JEDLO', other: 'INÉ' };

export default function Barter() {
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const router = useRouter();
  const [offers, setOffers] = useState<Offer[]>([]);
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(false);
  const [modal, setModal] = useState(false);
  const [err, setErr] = useState('');
  const [f, setF] = useState({ offer_skill: '', want_in_return: '', category: 'health', city: 'Bratislava', credits_value: 3 });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [a, b] = await Promise.all([api<Offer[]>('/barter/offers'), api<Me>('/barter/me')]);
      setOffers(a); setMe(b);
    } catch (e) { console.log(e); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const add = async () => {
    if (!f.offer_skill) return;
    await api('/barter/offers', { method: 'POST', body: JSON.stringify(f) });
    setModal(false); setF({ offer_skill: '', want_in_return: '', category: 'health', city: 'Bratislava', credits_value: 3 }); load();
  };
  const accept = async (o: Offer) => {
    setErr('');
    try {
      await api(`/barter/offers/${o.offer_id}/accept`, { method: 'POST' });
      load();
    } catch (e: any) { setErr(String(e.message || e)); }
  };
  const del = async (o: Offer) => {
    await api(`/barter/offers/${o.offer_id}`, { method: 'DELETE' });
    load();
  };

  return (
    <SafeAreaView testID="barter-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="bt-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={styles.title}>{t('barter', lang).toUpperCase()} ENGINE</Text>
        <View style={styles.creditBadge}>
          <Ionicons name="ribbon-outline" size={14} color={C.onInverse} />
          <Text testID="bt-credits" style={styles.creditText}>{me?.credits ?? '—'}</Text>
        </View>
      </View>
      <View style={styles.sub}><Text style={styles.subText}>{t('trust_credits', lang).toUpperCase()} · SLUŽBA ZA SLUŽBU · FUNGUJE AJ BEZ PEŇAZÍ</Text></View>

      <FlatList
        data={offers}
        keyExtractor={i => i.offer_id}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.fg} />}
        contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}
        ListHeaderComponent={
          <View>
            {err ? <Text style={styles.err}>{err}</Text> : null}
            <JarvisAdvice module="barter" lang={lang} buildContext={() => `Skill barter marketplace with trust credits. User has ${me?.credits ?? 10} credits. Offers: ${offers.map(o => `${o.offer_skill} for ${o.credits_value} credits`).join('; ') || 'none'}. Trades done: ${me?.trades?.length || 0}.`} />
            {me?.trades?.length ? (
              <View style={{ marginTop: S.md }}>
                <Text style={styles.section}>MOJE VÝMENY</Text>
                {me.trades.slice(0, 5).map((tr: any) => (
                  <View key={tr.trade_id} style={styles.tradeRow}>
                    <Ionicons name="swap-horizontal" size={16} color={C.brand} />
                    <Text style={styles.tradeText}>{tr.offer_skill} · {tr.provider_user_id === user?.user_id ? `+${tr.credits}` : `-${tr.credits}`} KR</Text>
                  </View>
                ))}
              </View>
            ) : null}
            <Text style={styles.section}>OTVORENÉ PONUKY</Text>
          </View>
        }
        ListEmptyComponent={!loading ? <Text style={styles.empty}>{t('no_data', lang).toUpperCase()}</Text> : null}
        renderItem={({ item }) => (
          <View testID={`bo-${item.offer_id}`} style={styles.card}>
            <View style={styles.rowSpread}>
              <View style={{ flex: 1 }}>
                <Text style={styles.skill}>{item.offer_skill}</Text>
                <Text style={styles.meta}>{CAT_LABELS[item.category] || item.category.toUpperCase()} · {item.city} · {item.owner_name}</Text>
                {item.want_in_return ? <Text style={styles.want}>↩ {item.want_in_return}</Text> : null}
              </View>
              <View style={styles.credBox}>
                <Text style={styles.credVal}>{item.credits_value}</Text>
                <Text style={styles.credLbl}>KR</Text>
              </View>
            </View>
            {item.user_id === user?.user_id ? (
              <Pressable testID={`bo-del-${item.offer_id}`} onPress={() => del(item)} style={styles.delBtn}>
                <Text style={styles.delText}>ZRUŠIŤ</Text>
              </Pressable>
            ) : (
              <Pressable testID={`bo-accept-${item.offer_id}`} onPress={() => accept(item)} style={styles.acceptBtn}>
                <Ionicons name="swap-horizontal" size={16} color={C.onInverse} />
                <Text style={styles.acceptText}>{t('accept_trade', lang).toUpperCase()} · {item.credits_value} KR</Text>
              </Pressable>
            )}
          </View>
        )}
      />

      <Pressable testID="bt-add-btn" onPress={() => setModal(true)} style={styles.fab}>
        <Ionicons name="add" size={22} color={C.onInverse} />
        <Text style={styles.fabText}>{t('add', lang).toUpperCase()}</Text>
      </Pressable>

      <Modal visible={modal} animationType="slide" transparent>
        <View style={styles.modalRoot}>
          <View style={styles.modalCard}>
            <View style={styles.modalHead}>
              <Text style={styles.modalTitle}>{t('offer', lang).toUpperCase()}</Text>
              <Pressable testID="bt-modal-close" onPress={() => setModal(false)}><Ionicons name="close" size={22} color={C.onInverse} /></Pressable>
            </View>
            <ScrollView contentContainerStyle={{ padding: S.lg, gap: S.md }} style={{ maxHeight: 440 }}>
              <TextInput testID="bt-skill" placeholder="Masáž chrbta 45 min" value={f.offer_skill} onChangeText={v => setF({ ...f, offer_skill: v })} style={styles.input} placeholderTextColor="#999" />
              <TextInput testID="bt-want" placeholder="Za čo? (právna pomoc, lieky…)" value={f.want_in_return} onChangeText={v => setF({ ...f, want_in_return: v })} style={styles.input} placeholderTextColor="#999" />
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: S.sm }}>
                {CATS.map(c => (
                  <Pressable testID={`bt-cat-${c}`} key={c} onPress={() => setF({ ...f, category: c })} style={[styles.chip, f.category === c && styles.chipActive]}>
                    <Text style={[styles.chipText, f.category === c && styles.chipTextActive]}>{CAT_LABELS[c]}</Text>
                  </Pressable>
                ))}
              </View>
              <TextInput testID="bt-city" placeholder="Bratislava" value={f.city} onChangeText={v => setF({ ...f, city: v })} style={styles.input} placeholderTextColor="#999" />
              <Text style={styles.lbl}>HODNOTA V KREDITOCH</Text>
              <View style={{ flexDirection: 'row', gap: S.sm }}>
                {[1, 2, 3, 5, 8, 10].map(n => (
                  <Pressable testID={`bt-cr-${n}`} key={n} onPress={() => setF({ ...f, credits_value: n })} style={[styles.crChip, f.credits_value === n && styles.chipActive]}>
                    <Text style={[styles.chipText, f.credits_value === n && styles.chipTextActive]}>{n}</Text>
                  </Pressable>
                ))}
              </View>
            </ScrollView>
            <Pressable testID="bt-save" onPress={add} style={styles.saveBtn}>
              <Text style={styles.saveBtnText}>{t('save', lang).toUpperCase()}</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 16, fontWeight: '900', letterSpacing: 2 },
  creditBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, borderWidth: 1.5, borderColor: C.onInverse, paddingHorizontal: 10, paddingVertical: 4 },
  creditText: { color: C.onInverse, fontWeight: '900', fontSize: 14 },
  sub: { paddingHorizontal: S.lg, paddingVertical: 6, backgroundColor: C.brandTer },
  subText: { color: C.brand, fontSize: 10, fontWeight: '900', letterSpacing: 1 },
  empty: { textAlign: 'center', color: C.onS3, marginTop: 40, letterSpacing: 2, fontWeight: '800' },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginBottom: S.sm },
  section: { marginTop: S.md, marginBottom: S.sm, fontSize: 11, letterSpacing: 2, color: C.fg, fontWeight: '900' },
  tradeRow: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 4 },
  tradeText: { fontWeight: '800', color: C.fg, fontSize: 12 },
  card: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginBottom: S.md },
  rowSpread: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  skill: { fontWeight: '900', fontSize: 15, color: C.fg },
  meta: { color: C.onS3, fontSize: 11, marginTop: 2, letterSpacing: 0.5 },
  want: { color: C.brand, fontSize: 12, marginTop: 4, fontWeight: '700' },
  credBox: { alignItems: 'center', backgroundColor: C.brand, paddingHorizontal: S.md, paddingVertical: 6 },
  credVal: { color: C.onInverse, fontWeight: '900', fontSize: 18 },
  credLbl: { color: C.onInverse, opacity: 0.7, fontSize: 9 },
  acceptBtn: { marginTop: S.md, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.inverse, paddingVertical: S.md },
  acceptText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
  delBtn: { marginTop: S.md, alignItems: 'center', borderWidth: 1.5, borderColor: C.error, paddingVertical: S.sm },
  delText: { color: C.error, fontWeight: '900', letterSpacing: 1, fontSize: 11 },
  fab: { position: 'absolute', bottom: 24, right: S.lg, flexDirection: 'row', gap: 8, alignItems: 'center', backgroundColor: C.inverse, paddingHorizontal: S.lg, paddingVertical: S.md, borderWidth: 2, borderColor: C.borderStrong },
  fabText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  modalRoot: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  modalCard: { backgroundColor: C.bg, borderTopWidth: 2, borderColor: C.borderStrong },
  modalHead: { flexDirection: 'row', justifyContent: 'space-between', padding: S.lg, backgroundColor: C.inverse },
  modalTitle: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 14 },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 15, color: C.fg },
  lbl: { fontSize: 10, letterSpacing: 2, color: C.onS3, fontWeight: '800' },
  chip: { paddingHorizontal: S.md, paddingVertical: 10, borderWidth: 1.5, borderColor: C.borderStrong },
  crChip: { width: 44, height: 44, borderWidth: 1.5, borderColor: C.borderStrong, alignItems: 'center', justifyContent: 'center' },
  chipActive: { backgroundColor: C.inverse },
  chipText: { fontWeight: '800', color: C.fg, fontSize: 11, letterSpacing: 1 },
  chipTextActive: { color: C.onInverse },
  saveBtn: { backgroundColor: C.inverse, paddingVertical: S.lg, alignItems: 'center' },
  saveBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2 },
});
