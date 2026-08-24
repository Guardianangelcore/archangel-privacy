/* Copyright © 2026 Guardian Angel. All Rights Reserved. This source code and its logic are the sole property of Guardian Angel. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, FlatList, TextInput, ScrollView, Modal, RefreshControl, Switch } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import JarvisAdvice from '@/src/JarvisAdvice';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';

type Item = { item_id: string; name: string; quantity: number; unit: string; expires_on?: string; category: string; prescription: boolean; status: string };
type Ex = { exchange_id: string; user_id: string; type: string; item_name: string; quantity: number; unit: string; city: string; note?: string; owner_name: string };

const CATS = ['painkiller', 'antibiotic', 'chronic', 'supplement', 'first_aid', 'other'];

export default function MedicineCabinet() {
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const router = useRouter();
  const [tab, setTab] = useState<'stock' | 'exchange'>('stock');
  const [items, setItems] = useState<Item[]>([]);
  const [exchange, setExchange] = useState<Ex[]>([]);
  const [loading, setLoading] = useState(false);
  const [modal, setModal] = useState(false);
  const [f, setF] = useState({ name: '', quantity: '1', unit: 'ks', expires_on: '', category: 'other', prescription: false });
  const [ef, setEf] = useState({ type: 'offer', item_name: '', quantity: '1', unit: 'ks', city: 'Bratislava', note: '' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [a, b] = await Promise.all([api<Item[]>('/cabinet/items'), api<Ex[]>('/cabinet/exchange')]);
      setItems(a); setExchange(b);
    } catch (e) { console.log(e); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const addItem = async () => {
    if (!f.name) return;
    await api('/cabinet/items', { method: 'POST', body: JSON.stringify({ ...f, quantity: parseFloat(f.quantity) || 1, expires_on: f.expires_on || null }) });
    setModal(false); setF({ name: '', quantity: '1', unit: 'ks', expires_on: '', category: 'other', prescription: false }); load();
  };
  const addEx = async () => {
    if (!ef.item_name) return;
    await api('/cabinet/exchange', { method: 'POST', body: JSON.stringify({ ...ef, quantity: parseFloat(ef.quantity) || 1 }) });
    setModal(false); setEf({ type: 'offer', item_name: '', quantity: '1', unit: 'ks', city: 'Bratislava', note: '' }); load();
  };
  const adjustQty = async (it: Item, delta: number) => {
    const q = Math.max(0, (it.quantity || 0) + delta);
    const res: any = await api(`/cabinet/items/${it.item_id}`, { method: 'PATCH', body: JSON.stringify({ quantity: q }) });
    setItems(prev => prev.map(x => x.item_id === it.item_id ? res : x));
  };
  const delItem = async (it: Item) => {
    await api(`/cabinet/items/${it.item_id}`, { method: 'DELETE' });
    setItems(prev => prev.filter(x => x.item_id !== it.item_id));
  };
  const respond = async (ex: Ex) => {
    await api(`/cabinet/exchange/${ex.exchange_id}/respond`, { method: 'POST', body: JSON.stringify({ message: 'Mám záujem' }) });
    load();
  };

  const badge = (status: string) => status === 'expired'
    ? { text: t('expired', lang).toUpperCase(), bg: C.error, fg: C.onError }
    : status === 'expiring_soon'
      ? { text: t('expiring_soon', lang).toUpperCase(), bg: C.warn, fg: C.onWarn }
      : { text: 'OK', bg: C.brandTer, fg: C.brand };

  return (
    <SafeAreaView testID="cabinet-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="mc-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={styles.title}>{t('medicine_cabinet', lang).toUpperCase()}</Text>
        <Pressable testID="mc-meds-link" onPress={() => router.push('/meds')} hitSlop={12}>
          <Ionicons name="alarm-outline" size={24} color={C.onInverse} />
        </Pressable>
      </View>

      <View style={styles.tabRow}>
        {(['stock', 'exchange'] as const).map(k => (
          <Pressable testID={`mc-tab-${k}`} key={k} onPress={() => setTab(k)} style={[styles.tabBtn, tab === k && styles.tabBtnActive]}>
            <Text style={[styles.tabText, tab === k && styles.tabTextActive]}>{t(k === 'stock' ? 'my_stock' : 'p2p_exchange', lang).toUpperCase()}</Text>
          </Pressable>
        ))}
      </View>

      {tab === 'stock' ? (
        <FlatList
          data={items}
          keyExtractor={i => i.item_id}
          refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.fg} />}
          contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}
          ListHeaderComponent={<JarvisAdvice module="medicine_cabinet" lang={lang} buildContext={() => `Medicine stock: ${items.map(i => `${i.name} ${i.quantity}${i.unit} exp:${i.expires_on || '?'} status:${i.status}`).join('; ') || 'empty'}`} />}
          ListEmptyComponent={!loading ? <Text style={styles.empty}>{t('no_data', lang).toUpperCase()}</Text> : null}
          renderItem={({ item }) => {
            const b = badge(item.status);
            return (
              <View testID={`cab-${item.item_id}`} style={[styles.card, item.status === 'expired' && { borderColor: C.error }]}>
                <View style={styles.rowSpread}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.itemName}>{item.name}</Text>
                    <Text style={styles.itemMeta}>{item.category.toUpperCase()} · EXP: {item.expires_on || '—'}{item.prescription ? ' · Rx' : ''}</Text>
                  </View>
                  <View style={[styles.badge, { backgroundColor: b.bg }]}><Text style={[styles.badgeText, { color: b.fg }]}>{b.text}</Text></View>
                </View>
                <View style={styles.qtyRow}>
                  <Pressable testID={`cab-minus-${item.item_id}`} onPress={() => adjustQty(item, -1)} style={styles.qtyBtn}><Ionicons name="remove" size={18} color={C.fg} /></Pressable>
                  <Text style={styles.qtyVal}>{item.quantity} {item.unit}</Text>
                  <Pressable testID={`cab-plus-${item.item_id}`} onPress={() => adjustQty(item, 1)} style={styles.qtyBtn}><Ionicons name="add" size={18} color={C.fg} /></Pressable>
                  <View style={{ flex: 1 }} />
                  <Pressable testID={`cab-del-${item.item_id}`} onPress={() => delItem(item)} hitSlop={10}><Ionicons name="trash-outline" size={18} color={C.error} /></Pressable>
                </View>
              </View>
            );
          }}
        />
      ) : (
        <FlatList
          data={exchange}
          keyExtractor={i => i.exchange_id}
          refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.fg} />}
          contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}
          ListHeaderComponent={<Text style={styles.exNote}>KRÍZOVÝ REŽIM · LEN VOĽNOPREDAJNÉ · ŠIFROVANÁ SIEŤ</Text>}
          ListEmptyComponent={!loading ? <Text style={styles.empty}>{t('no_data', lang).toUpperCase()}</Text> : null}
          renderItem={({ item }) => (
            <View testID={`ex-${item.exchange_id}`} style={styles.card}>
              <View style={styles.rowSpread}>
                <View style={[styles.badge, { backgroundColor: item.type === 'offer' ? C.brand : C.info }]}>
                  <Text style={[styles.badgeText, { color: C.onInverse }]}>{t(item.type, lang).toUpperCase()}</Text>
                </View>
                <Text style={styles.itemMeta}>{item.city}</Text>
              </View>
              <Text style={[styles.itemName, { marginTop: 6 }]}>{item.item_name} · {item.quantity} {item.unit}</Text>
              <Text style={styles.itemMeta}>{item.owner_name}{item.note ? ` · ${item.note}` : ''}</Text>
              {item.user_id !== user?.user_id && (
                <Pressable testID={`ex-respond-${item.exchange_id}`} onPress={() => respond(item)} style={styles.respondBtn}>
                  <Ionicons name="hand-left-outline" size={16} color={C.onInverse} />
                  <Text style={styles.respondText}>{t('respond', lang).toUpperCase()}</Text>
                </Pressable>
              )}
            </View>
          )}
        />
      )}

      <Pressable testID="mc-add-btn" onPress={() => setModal(true)} style={styles.fab}>
        <Ionicons name="add" size={22} color={C.onInverse} />
        <Text style={styles.fabText}>{t('add', lang).toUpperCase()}</Text>
      </Pressable>

      <Modal visible={modal} animationType="slide" transparent>
        <View style={styles.modalRoot}>
          <View style={styles.modalCard}>
            <View style={styles.modalHead}>
              <Text style={styles.modalTitle}>{tab === 'stock' ? t('my_stock', lang).toUpperCase() : t('p2p_exchange', lang).toUpperCase()}</Text>
              <Pressable testID="mc-modal-close" onPress={() => setModal(false)}><Ionicons name="close" size={22} color={C.onInverse} /></Pressable>
            </View>
            <ScrollView contentContainerStyle={{ padding: S.lg, gap: S.md }} style={{ maxHeight: 440 }}>
              {tab === 'stock' ? (
                <>
                  <TextInput testID="cab-name" placeholder="Ibuprofen 400mg" value={f.name} onChangeText={v => setF({ ...f, name: v })} style={styles.input} placeholderTextColor="#999" />
                  <View style={{ flexDirection: 'row', gap: S.sm }}>
                    <TextInput testID="cab-qty" placeholder="20" value={f.quantity} onChangeText={v => setF({ ...f, quantity: v })} keyboardType="numeric" style={[styles.input, { flex: 1 }]} placeholderTextColor="#999" />
                    <TextInput testID="cab-unit" placeholder="ks" value={f.unit} onChangeText={v => setF({ ...f, unit: v })} style={[styles.input, { flex: 1 }]} placeholderTextColor="#999" />
                  </View>
                  <TextInput testID="cab-exp" placeholder="EXP: 2027-06-30" value={f.expires_on} onChangeText={v => setF({ ...f, expires_on: v })} style={styles.input} placeholderTextColor="#999" />
                  <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: S.sm }}>
                    {CATS.map(c => (
                      <Pressable testID={`cab-cat-${c}`} key={c} onPress={() => setF({ ...f, category: c })} style={[styles.chip, f.category === c && styles.chipActive]}>
                        <Text style={[styles.chipText, f.category === c && styles.chipTextActive]}>{c.toUpperCase()}</Text>
                      </Pressable>
                    ))}
                  </View>
                  <View style={styles.rowSpread}>
                    <Text style={styles.lbl}>NA PREDPIS (Rx)</Text>
                    <Switch testID="cab-rx" value={f.prescription} onValueChange={v => setF({ ...f, prescription: v })} trackColor={{ true: C.brand, false: C.surface3 }} />
                  </View>
                </>
              ) : (
                <>
                  <View style={{ flexDirection: 'row', gap: S.sm }}>
                    {(['offer', 'request'] as const).map(ty => (
                      <Pressable testID={`ex-type-${ty}`} key={ty} onPress={() => setEf({ ...ef, type: ty })} style={[styles.chip, { flex: 1, alignItems: 'center' }, ef.type === ty && styles.chipActive]}>
                        <Text style={[styles.chipText, ef.type === ty && styles.chipTextActive]}>{t(ty, lang).toUpperCase()}</Text>
                      </Pressable>
                    ))}
                  </View>
                  <TextInput testID="ex-name" placeholder="Paralen, obväzy…" value={ef.item_name} onChangeText={v => setEf({ ...ef, item_name: v })} style={styles.input} placeholderTextColor="#999" />
                  <View style={{ flexDirection: 'row', gap: S.sm }}>
                    <TextInput testID="ex-qty" placeholder="1" value={ef.quantity} onChangeText={v => setEf({ ...ef, quantity: v })} keyboardType="numeric" style={[styles.input, { flex: 1 }]} placeholderTextColor="#999" />
                    <TextInput testID="ex-city" placeholder="Bratislava" value={ef.city} onChangeText={v => setEf({ ...ef, city: v })} style={[styles.input, { flex: 2 }]} placeholderTextColor="#999" />
                  </View>
                  <TextInput testID="ex-note" placeholder="Poznámka" value={ef.note} onChangeText={v => setEf({ ...ef, note: v })} style={styles.input} placeholderTextColor="#999" />
                  <Text style={styles.exNote}>IBA VOĽNOPREDAJNÉ LIEKY A ZDRAVOTNÍCKY MATERIÁL</Text>
                </>
              )}
            </ScrollView>
            <Pressable testID="mc-save" onPress={tab === 'stock' ? addItem : addEx} style={styles.saveBtn}>
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
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  tabRow: { flexDirection: 'row', borderBottomWidth: 2, borderColor: C.borderStrong },
  tabBtn: { flex: 1, paddingVertical: S.md, alignItems: 'center' },
  tabBtnActive: { backgroundColor: C.inverse },
  tabText: { fontWeight: '900', letterSpacing: 1, fontSize: 12, color: C.fg },
  tabTextActive: { color: C.onInverse },
  empty: { textAlign: 'center', color: C.onS3, marginTop: 40, letterSpacing: 2, fontWeight: '800' },
  card: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginBottom: S.md, marginTop: S.sm },
  rowSpread: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  itemName: { fontWeight: '900', fontSize: 15, color: C.fg },
  itemMeta: { color: C.onS3, fontSize: 11, marginTop: 2, letterSpacing: 0.5 },
  badge: { paddingHorizontal: 8, paddingVertical: 4 },
  badgeText: { fontSize: 10, fontWeight: '900', letterSpacing: 1 },
  qtyRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, marginTop: S.md },
  qtyBtn: { width: 40, height: 40, borderWidth: 1.5, borderColor: C.borderStrong, alignItems: 'center', justifyContent: 'center' },
  qtyVal: { fontWeight: '900', fontSize: 16, color: C.fg, minWidth: 60, textAlign: 'center' },
  respondBtn: { marginTop: S.md, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.inverse, paddingVertical: S.md },
  respondText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
  exNote: { fontSize: 10, letterSpacing: 1.5, color: C.brand, fontWeight: '900', marginBottom: S.sm },
  fab: { position: 'absolute', bottom: 24, right: S.lg, flexDirection: 'row', gap: 8, alignItems: 'center', backgroundColor: C.inverse, paddingHorizontal: S.lg, paddingVertical: S.md, borderWidth: 2, borderColor: C.borderStrong },
  fabText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  modalRoot: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  modalCard: { backgroundColor: C.bg, borderTopWidth: 2, borderColor: C.borderStrong },
  modalHead: { flexDirection: 'row', justifyContent: 'space-between', padding: S.lg, backgroundColor: C.inverse },
  modalTitle: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 14 },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 15, color: C.fg },
  lbl: { fontSize: 10, letterSpacing: 2, color: C.onS3, fontWeight: '800' },
  chip: { paddingHorizontal: S.md, paddingVertical: 8, borderWidth: 1.5, borderColor: C.borderStrong },
  chipActive: { backgroundColor: C.inverse },
  chipText: { fontWeight: '800', color: C.fg, fontSize: 11, letterSpacing: 1 },
  chipTextActive: { color: C.onInverse },
  saveBtn: { backgroundColor: C.inverse, paddingVertical: S.lg, alignItems: 'center' },
  saveBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2 },
});
