/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, FlatList, TextInput, ScrollView, Modal, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { WheelField } from '@/src/ui/fields';
import { EmptyState } from '@/src/ui/EmptyState';
import JarvisAdvice from '@/src/JarvisAdvice';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';

type Svc = { service_id: string; user_id: string; title: string; description: string; category: string; price: number; currency: string; payment_methods: string[]; city: string; contact: string; provider_name: string; bookings: number };
type Booking = { booking_id: string; service_id: string; provider_user_id: string; client_user_id: string; client_name: string; message: string; payment_method: string; status: string; created_at: string };

const CATS = ['massage', 'consultation', 'physio', 'care', 'other'];
const CAT_LABELS: Record<string, string> = { massage: 'MASÁŽ', consultation: 'KONZULTÁCIA', physio: 'FYZIO', care: 'STAROSTLIVOSŤ', other: 'INÉ' };

export default function Marketplace() {
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const router = useRouter();
  const [tab, setTab] = useState<'services' | 'bookings'>('services');
  const [items, setItems] = useState<Svc[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(false);
  const [modal, setModal] = useState(false);
  const [bookSvc, setBookSvc] = useState<Svc | null>(null);
  const [bookMsg, setBookMsg] = useState('');
  const [bookPay, setBookPay] = useState('cash');
  const [f, setF] = useState({ title: '', description: '', category: 'massage', price: '30', city: 'Bratislava', contact: '', payment_methods: ['cash'] as string[] });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [a, b] = await Promise.all([api<Svc[]>('/market/services'), api<Booking[]>('/market/bookings')]);
      setItems(a); setBookings(b);
    } catch (e) { console.log(e); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const add = async () => {
    if (!f.title) return;
    await api('/market/services', { method: 'POST', body: JSON.stringify({ ...f, price: parseFloat(f.price) || 0 }) });
    setModal(false); setF({ title: '', description: '', category: 'massage', price: '30', city: 'Bratislava', contact: '', payment_methods: ['cash'] }); load();
  };
  const book = async () => {
    if (!bookSvc) return;
    await api(`/market/services/${bookSvc.service_id}/book`, { method: 'POST', body: JSON.stringify({ message: bookMsg, payment_method: bookPay }) });
    setBookSvc(null); setBookMsg(''); load();
  };
  const del = async (s: Svc) => {
    await api(`/market/services/${s.service_id}`, { method: 'DELETE' });
    load();
  };
  const togglePay = (m: string) => setF(v => ({ ...v, payment_methods: v.payment_methods.includes(m) ? v.payment_methods.filter(x => x !== m) : [...v.payment_methods, m] }));

  return (
    <SafeAreaView testID="marketplace-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="mk-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={styles.title}>{t('marketplace', lang).toUpperCase()}</Text>
        <View style={{ width: 26 }} />
      </View>
      <View style={styles.sub}><Text style={styles.subText}>PRIAMO OD EXPERTOV · CASH / CRYPTO · BEZ SPROSTREDKOVATEĽOV</Text></View>

      <View style={styles.tabRow}>
        {(['services', 'bookings'] as const).map(k => (
          <Pressable testID={`mk-tab-${k}`} key={k} onPress={() => setTab(k)} style={[styles.tabBtn, tab === k && styles.tabBtnActive]}>
            <Text style={[styles.tabText, tab === k && styles.tabTextActive]}>{k === 'services' ? 'PONUKY' : 'OBJEDNÁVKY'}</Text>
          </Pressable>
        ))}
      </View>

      {tab === 'services' ? (
        <FlatList
          data={items}
          keyExtractor={i => i.service_id}
          refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.fg} />}
          contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}
          ListHeaderComponent={<JarvisAdvice module="marketplace" lang={lang} buildContext={() => `Direct service marketplace. Available: ${items.map(i => `${i.title} ${i.price}${i.currency} in ${i.city}`).join('; ') || 'none yet'}. User may be a service provider (masseur) wanting income tips.`} />}
          ListEmptyComponent={!loading ? <EmptyState testID="mk-empty" icon="storefront-outline" title={t('empty_market_title', lang)} sub={t('empty_market_sub', lang)} /> : null}
          renderItem={({ item }) => (
            <View testID={`svc-${item.service_id}`} style={styles.card}>
              <View style={styles.rowSpread}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.svcTitle}>{item.title}</Text>
                  <Text style={styles.svcMeta}>{CAT_LABELS[item.category] || item.category.toUpperCase()} · {item.city} · {item.provider_name}</Text>
                </View>
                <View style={styles.priceBox}>
                  <Text style={styles.priceVal}>{item.price}</Text>
                  <Text style={styles.priceCur}>{item.currency}</Text>
                </View>
              </View>
              {item.description ? <Text style={styles.svcDesc}>{item.description}</Text> : null}
              <View style={styles.payRow}>
                {item.payment_methods?.map(m => (
                  <View key={m} style={styles.payChip}>
                    <Ionicons name={m === 'crypto' ? 'logo-bitcoin' : 'cash-outline'} size={12} color={C.fg} />
                    <Text style={styles.payText}>{m.toUpperCase()}</Text>
                  </View>
                ))}
              </View>
              {item.user_id === user?.user_id ? (
                <Pressable testID={`svc-del-${item.service_id}`} onPress={() => del(item)} style={styles.delBtn}>
                  <Ionicons name="trash-outline" size={14} color={C.error} />
                  <Text style={styles.delText}>DEAKTIVOVAŤ</Text>
                </Pressable>
              ) : (
                <Pressable testID={`svc-book-${item.service_id}`} onPress={() => { setBookSvc(item); setBookPay(item.payment_methods?.[0] || 'cash'); }} style={styles.bookBtn}>
                  <Ionicons name="calendar-outline" size={16} color={C.onInverse} />
                  <Text style={styles.bookText}>{t('book_now', lang).toUpperCase()}</Text>
                </Pressable>
              )}
            </View>
          )}
        />
      ) : (
        <FlatList
          data={bookings}
          keyExtractor={i => i.booking_id}
          refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.fg} />}
          contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}
          ListEmptyComponent={!loading ? <EmptyState testID="bk-empty" icon="calendar-clear-outline" title={t('empty_bookings_title', lang)} sub={t('empty_bookings_sub', lang)} /> : null}
          renderItem={({ item }) => (
            <View testID={`bk-${item.booking_id}`} style={styles.card}>
              <View style={styles.rowSpread}>
                <Text style={styles.svcTitle}>{item.provider_user_id === user?.user_id ? `⬅ ${item.client_name}` : '➡ Moja objednávka'}</Text>
                <Text style={styles.svcMeta}>{item.payment_method.toUpperCase()}</Text>
              </View>
              {item.message ? <Text style={styles.svcDesc}>{item.message}</Text> : null}
              <Text style={styles.svcMeta}>{item.status.toUpperCase()} · {String(item.created_at).slice(0, 16).replace('T', ' ')}</Text>
            </View>
          )}
        />
      )}

      <Pressable testID="mk-add-btn" onPress={() => setModal(true)} style={styles.fab}>
        <Ionicons name="add" size={22} color={C.onInverse} />
        <Text style={styles.fabText}>{t('new_service', lang).toUpperCase()}</Text>
      </Pressable>

      {/* New service modal */}
      <Modal visible={modal} animationType="slide" transparent>
        <View style={styles.modalRoot}>
          <View style={styles.modalCard}>
            <View style={styles.modalHead}>
              <Text style={styles.modalTitle}>{t('new_service', lang).toUpperCase()}</Text>
              <Pressable testID="mk-modal-close" onPress={() => setModal(false)}><Ionicons name="close" size={22} color={C.onInverse} /></Pressable>
            </View>
            <ScrollView contentContainerStyle={{ padding: S.lg, gap: S.md }} style={{ maxHeight: 460 }}>
              <TextInput testID="mk-title" placeholder="Klasická masáž 60 min" value={f.title} onChangeText={v => setF({ ...f, title: v })} style={styles.input} placeholderTextColor="#999" />
              <TextInput testID="mk-desc" placeholder="Popis" value={f.description} onChangeText={v => setF({ ...f, description: v })} multiline style={[styles.input, { minHeight: 60 }]} placeholderTextColor="#999" />
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: S.sm }}>
                {CATS.map(c => (
                  <Pressable testID={`mk-cat-${c}`} key={c} onPress={() => setF({ ...f, category: c })} style={[styles.chip, f.category === c && styles.chipActive]}>
                    <Text style={[styles.chipText, f.category === c && styles.chipTextActive]}>{CAT_LABELS[c]}</Text>
                  </Pressable>
                ))}
              </View>
              <View style={{ flexDirection: 'row', gap: S.sm }}>
                <WheelField testID="mk-price" title="CENA €" min={0} max={500} unit="€" value={f.price} onChange={v => setF({ ...f, price: v })} placeholder="30" style={[styles.input, { flex: 1 }]} />
                <TextInput testID="mk-city" placeholder="Bratislava" value={f.city} onChangeText={v => setF({ ...f, city: v })} style={[styles.input, { flex: 2 }]} placeholderTextColor="#999" />
              </View>
              <TextInput testID="mk-contact" placeholder="Kontakt (tel./telegram)" value={f.contact} onChangeText={v => setF({ ...f, contact: v })} style={styles.input} placeholderTextColor="#999" />
              <View style={{ flexDirection: 'row', gap: S.sm }}>
                {['cash', 'crypto'].map(m => (
                  <Pressable testID={`mk-pay-${m}`} key={m} onPress={() => togglePay(m)} style={[styles.chip, { flex: 1, alignItems: 'center' }, f.payment_methods.includes(m) && styles.chipActive]}>
                    <Text style={[styles.chipText, f.payment_methods.includes(m) && styles.chipTextActive]}>{m.toUpperCase()}</Text>
                  </Pressable>
                ))}
              </View>
            </ScrollView>
            <Pressable testID="mk-save" onPress={add} style={styles.saveBtn}>
              <Text style={styles.saveBtnText}>{t('save', lang).toUpperCase()}</Text>
            </Pressable>
          </View>
        </View>
      </Modal>

      {/* Booking modal */}
      <Modal visible={!!bookSvc} animationType="slide" transparent>
        <View style={styles.modalRoot}>
          <View style={styles.modalCard}>
            <View style={styles.modalHead}>
              <Text style={styles.modalTitle}>{bookSvc?.title?.toUpperCase()}</Text>
              <Pressable testID="bk-modal-close" onPress={() => setBookSvc(null)}><Ionicons name="close" size={22} color={C.onInverse} /></Pressable>
            </View>
            <View style={{ padding: S.lg, gap: S.md }}>
              <TextInput testID="bk-msg" placeholder="Správa poskytovateľovi…" value={bookMsg} onChangeText={setBookMsg} multiline style={[styles.input, { minHeight: 60 }]} placeholderTextColor="#999" />
              <View style={{ flexDirection: 'row', gap: S.sm }}>
                {(bookSvc?.payment_methods || ['cash']).map(m => (
                  <Pressable testID={`bk-pay-${m}`} key={m} onPress={() => setBookPay(m)} style={[styles.chip, { flex: 1, alignItems: 'center' }, bookPay === m && styles.chipActive]}>
                    <Text style={[styles.chipText, bookPay === m && styles.chipTextActive]}>{m.toUpperCase()}</Text>
                  </Pressable>
                ))}
              </View>
            </View>
            <Pressable testID="bk-confirm" onPress={book} style={styles.saveBtn}>
              <Text style={styles.saveBtnText}>{t('book_now', lang).toUpperCase()} · {bookSvc?.price} {bookSvc?.currency}</Text>
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
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  sub: { paddingHorizontal: S.lg, paddingVertical: 6, backgroundColor: C.brandTer },
  subText: { color: C.brand, fontSize: 10, fontWeight: '900', letterSpacing: 1 },
  tabRow: { flexDirection: 'row', borderBottomWidth: 2, borderColor: C.borderStrong },
  tabBtn: { flex: 1, paddingVertical: S.md, alignItems: 'center' },
  tabBtnActive: { backgroundColor: C.inverse },
  tabText: { fontWeight: '900', letterSpacing: 1, fontSize: 12, color: C.fg },
  tabTextActive: { color: C.onInverse },
  empty: { textAlign: 'center', color: C.onS3, marginTop: 40, letterSpacing: 2, fontWeight: '800' },
  card: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginBottom: S.md, marginTop: S.sm },
  rowSpread: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  svcTitle: { fontWeight: '900', fontSize: 15, color: C.fg },
  svcMeta: { color: C.onS3, fontSize: 11, marginTop: 2, letterSpacing: 0.5 },
  svcDesc: { color: C.fg, fontSize: 13, marginTop: 6, lineHeight: 18 },
  priceBox: { alignItems: 'center', backgroundColor: C.brand, paddingHorizontal: S.md, paddingVertical: 6 },
  priceVal: { color: C.onInverse, fontWeight: '900', fontSize: 18 },
  priceCur: { color: C.onInverse, opacity: 0.7, fontSize: 10 },
  payRow: { flexDirection: 'row', gap: 6, marginTop: S.sm },
  payChip: { flexDirection: 'row', alignItems: 'center', gap: 4, borderWidth: 1, borderColor: C.borderStrong, paddingHorizontal: 8, paddingVertical: 3 },
  payText: { fontSize: 10, fontWeight: '800', letterSpacing: 1, color: C.fg },
  bookBtn: { marginTop: S.md, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.inverse, paddingVertical: S.md },
  bookText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
  delBtn: { marginTop: S.md, flexDirection: 'row', gap: 6, alignItems: 'center', justifyContent: 'center', borderWidth: 1.5, borderColor: C.error, paddingVertical: S.sm },
  delText: { color: C.error, fontWeight: '900', letterSpacing: 1, fontSize: 11 },
  fab: { position: 'absolute', bottom: 24, right: S.lg, flexDirection: 'row', gap: 8, alignItems: 'center', backgroundColor: C.inverse, paddingHorizontal: S.lg, paddingVertical: S.md, borderWidth: 2, borderColor: C.borderStrong },
  fabText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  modalRoot: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  modalCard: { backgroundColor: C.bg, borderTopWidth: 2, borderColor: C.borderStrong },
  modalHead: { flexDirection: 'row', justifyContent: 'space-between', padding: S.lg, backgroundColor: C.inverse },
  modalTitle: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 13, flex: 1, marginRight: 8 },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 15, color: C.fg },
  chip: { paddingHorizontal: S.md, paddingVertical: 10, borderWidth: 1.5, borderColor: C.borderStrong },
  chipActive: { backgroundColor: C.inverse },
  chipText: { fontWeight: '800', color: C.fg, fontSize: 11, letterSpacing: 1 },
  chipTextActive: { color: C.onInverse },
  saveBtn: { backgroundColor: C.inverse, paddingVertical: S.lg, alignItems: 'center' },
  saveBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2 },
});
