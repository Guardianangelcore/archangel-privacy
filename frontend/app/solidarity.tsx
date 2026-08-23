import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, FlatList, TextInput, ScrollView, Modal, ActivityIndicator, Platform, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';

type Camp = { campaign_id: string; title: string; story: string; goal_amount: number; raised_amount: number; supporters: number; owner_name: string; currency: string };

export default function Solidarity() {
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const router = useRouter();
  const [items, setItems] = useState<Camp[]>([]);
  const [loading, setLoading] = useState(false);
  const [modal, setModal] = useState(false);
  const [donateFor, setDonateFor] = useState<Camp | null>(null);
  const [form, setForm] = useState({ title: '', story: '', goal_amount: '', currency: 'EUR' });
  const [amount, setAmount] = useState('10');

  const load = useCallback(async () => {
    setLoading(true);
    try { setItems(await api<Camp[]>('/solidarity/campaigns')); } catch (e) {}
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const create = async () => {
    if (!form.title || !form.story || !form.goal_amount) return;
    await api('/solidarity/campaigns', { method: 'POST', body: JSON.stringify({
      title: form.title, story: form.story, goal_amount: parseFloat(form.goal_amount), currency: form.currency,
    }) });
    setModal(false); setForm({ title: '', story: '', goal_amount: '', currency: 'EUR' }); load();
  };

  const donate = async () => {
    if (!donateFor) return;
    await api(`/solidarity/campaigns/${donateFor.campaign_id}/donate`, { method: 'POST', body: JSON.stringify({ amount: parseFloat(amount) || 0 }) });
    setDonateFor(null); setAmount('10'); load();
  };

  return (
    <SafeAreaView testID="solidarity-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="sol-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={styles.title}>SOLIDARITY HUB</Text>
        <View style={{ width: 26 }} />
      </View>
      <View style={styles.banner}><Text style={styles.bannerText}>MOCKED · P2P PAYMENTS DEFERRED</Text></View>
      <FlatList
        data={items}
        keyExtractor={i => i.campaign_id}
        contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.fg} />}
        ListEmptyComponent={!loading ? <Text style={styles.empty}>NO CAMPAIGNS YET</Text> : null}
        renderItem={({ item }) => {
          const pct = Math.min(100, (item.raised_amount / item.goal_amount) * 100 || 0);
          return (
            <View testID={`camp-${item.campaign_id}`} style={styles.card}>
              <Text style={styles.cardTitle}>{item.title}</Text>
              <Text style={styles.cardBy}>{item.owner_name}</Text>
              <Text style={styles.cardStory} numberOfLines={3}>{item.story}</Text>
              <View style={styles.progressWrap}>
                <View style={[styles.progressFill, { width: `${pct}%` }]} />
              </View>
              <View style={styles.rowSpread}>
                <Text style={styles.statVal}>{item.raised_amount.toFixed(0)} / {item.goal_amount.toFixed(0)} {item.currency}</Text>
                <Text style={styles.statSup}>{item.supporters} SUPPORTERS</Text>
              </View>
              <Pressable testID={`donate-${item.campaign_id}`} onPress={() => setDonateFor(item)} style={styles.donateBtn}>
                <Ionicons name="heart" size={16} color={C.onInverse} />
                <Text style={styles.donateBtnText}>{t('donate', lang).toUpperCase()}</Text>
              </Pressable>
            </View>
          );
        }}
      />
      <Pressable testID="new-campaign-btn" onPress={() => setModal(true)} style={styles.fab}>
        <Ionicons name="add" size={22} color={C.onInverse} />
        <Text style={styles.fabText}>{t('new_campaign', lang).toUpperCase()}</Text>
      </Pressable>

      <Modal visible={modal} animationType="slide" transparent>
        <View style={styles.modalRoot}>
          <View style={styles.modalCard}>
            <View style={styles.modalHead}><Text style={styles.modalTitle}>NEW CAMPAIGN</Text>
              <Pressable onPress={() => setModal(false)}><Ionicons name="close" size={22} color={C.onInverse} /></Pressable></View>
            <ScrollView contentContainerStyle={{ padding: S.lg, gap: S.md }}>
              <TextInput testID="sol-title" placeholder="TITLE" value={form.title} onChangeText={v => setForm({ ...form, title: v })} style={styles.input} placeholderTextColor="#999" />
              <TextInput testID="sol-story" placeholder="STORY" value={form.story} onChangeText={v => setForm({ ...form, story: v })} style={[styles.input, { minHeight: 100 }]} multiline placeholderTextColor="#999" />
              <TextInput testID="sol-goal" placeholder="GOAL AMOUNT" keyboardType="numeric" value={form.goal_amount} onChangeText={v => setForm({ ...form, goal_amount: v })} style={styles.input} placeholderTextColor="#999" />
              <View style={{ flexDirection: 'row', gap: S.sm }}>
                {['EUR','CZK','USD'].map(c => (
                  <Pressable testID={`cur-${c}`} key={c} onPress={() => setForm({ ...form, currency: c })} style={[styles.chip, form.currency === c && styles.chipActive]}><Text style={[styles.chipText, form.currency === c && styles.chipTextActive]}>{c}</Text></Pressable>
                ))}
              </View>
            </ScrollView>
            <Pressable testID="sol-create" onPress={create} style={styles.saveBtn}><Text style={styles.saveBtnText}>CREATE</Text></Pressable>
          </View>
        </View>
      </Modal>

      <Modal visible={!!donateFor} animationType="slide" transparent>
        <View style={styles.modalRoot}>
          <View style={styles.modalCard}>
            <View style={styles.modalHead}><Text style={styles.modalTitle}>DONATE (MOCKED)</Text>
              <Pressable onPress={() => setDonateFor(null)}><Ionicons name="close" size={22} color={C.onInverse} /></Pressable></View>
            <View style={{ padding: S.lg, gap: S.md }}>
              <Text style={styles.cardTitle}>{donateFor?.title}</Text>
              <TextInput testID="donate-amount" placeholder="Amount" keyboardType="numeric" value={amount} onChangeText={setAmount} style={styles.input} placeholderTextColor="#999" />
              <View style={{ flexDirection: 'row', gap: S.sm }}>
                {['5','10','25','50'].map(a => <Pressable testID={`amt-${a}`} key={a} onPress={() => setAmount(a)} style={styles.chip}><Text style={styles.chipText}>{a} {donateFor?.currency}</Text></Pressable>)}
              </View>
            </View>
            <Pressable testID="donate-confirm" onPress={donate} style={styles.saveBtn}><Text style={styles.saveBtnText}>DONATE {amount} {donateFor?.currency}</Text></Pressable>
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
  banner: { backgroundColor: C.warn, paddingVertical: 6, alignItems: 'center' },
  bannerText: { color: C.onWarn, fontWeight: '900', letterSpacing: 2, fontSize: 11 },
  empty: { textAlign: 'center', color: C.onS3, marginTop: 60, letterSpacing: 2, fontWeight: '800' },
  card: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginBottom: S.md },
  cardTitle: { fontSize: 17, fontWeight: '900', color: C.fg, letterSpacing: 1 },
  cardBy: { color: C.onS3, fontSize: 12, marginTop: 2 },
  cardStory: { color: C.fg, marginTop: S.sm, fontSize: 14, lineHeight: 20 },
  progressWrap: { height: 8, backgroundColor: C.surface3, marginTop: S.md, borderWidth: 1, borderColor: C.borderStrong },
  progressFill: { height: '100%', backgroundColor: C.brand },
  rowSpread: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 8 },
  statVal: { fontWeight: '900', color: C.fg },
  statSup: { color: C.onS3, fontSize: 12, letterSpacing: 1 },
  donateBtn: { marginTop: S.md, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.error, paddingVertical: S.md },
  donateBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 12 },
  fab: { position: 'absolute', bottom: 24, right: S.lg, flexDirection: 'row', gap: 8, alignItems: 'center', backgroundColor: C.inverse, paddingHorizontal: S.lg, paddingVertical: S.md, borderWidth: 2, borderColor: C.borderStrong },
  fabText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  modalRoot: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  modalCard: { backgroundColor: C.bg, borderTopWidth: 2, borderColor: C.borderStrong },
  modalHead: { flexDirection: 'row', justifyContent: 'space-between', padding: S.lg, backgroundColor: C.inverse },
  modalTitle: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 16 },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 15, color: C.fg, backgroundColor: C.bg },
  chip: { paddingHorizontal: S.md, paddingVertical: 8, borderWidth: 1.5, borderColor: C.borderStrong },
  chipActive: { backgroundColor: C.inverse },
  chipText: { fontWeight: '800', color: C.fg, letterSpacing: 1 },
  chipTextActive: { color: C.onInverse },
  saveBtn: { backgroundColor: C.inverse, paddingVertical: S.lg, alignItems: 'center' },
  saveBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2 },
});
