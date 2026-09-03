/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, FlatList, TextInput, ScrollView, Modal, ActivityIndicator, Platform, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, S } from '@/src/theme';
import { DateSheet, OptionSheet } from '@/src/ui/sheets';
import { t, Lang } from '@/src/i18n';
import { useI18n } from '@/src/i18n-context';
import Paywall from '@/src/Paywall';

type Item = { item_id: string; specialty: string; clinic: string; city: string; current_date: string; target_before: string; status: string; found_slot?: string; last_check?: string };

const SPECIALTIES = ['Cardiology', 'Orthopedics', 'Oncology', 'MRI/CT', 'Neurology', 'Dermatology', 'Ophthalmology'];

export default function Waitlist() {
  const { t: tt, tx } = useI18n();
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'en';
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(false);
  const [modal, setModal] = useState(false);
  const [scanId, setScanId] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('ALL');

  const [f, setF] = useState({ specialty: 'Cardiology', clinic: '', city: 'Bratislava', current_date: '', target_before: '' });
  const [sheet, setSheet] = useState<'spec' | 'current' | 'target' | null>(null);

  // TIER GATE — Waitlist Hunter is Guardian+; the backend answers 402 for Sovereign, we show the paywall.
  const [locked, setLocked] = useState(false);
  const load = useCallback(async () => {
    setLoading(true);
    try { setItems(await api<Item[]>('/waitlist')); setLocked(false); }
    catch (e: any) { if (/^402:/.test(String(e?.message))) setLocked(true); else console.log(e); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const add = async () => {
    if (!f.clinic || !f.current_date || !f.target_before) return;
    await api('/waitlist', { method: 'POST', body: JSON.stringify(f) });
    setModal(false);
    setF({ specialty: 'Cardiology', clinic: '', city: 'Bratislava', current_date: '', target_before: '' });
    load();
  };

  const scan = async (item: Item) => {
    setScanId(item.item_id);
    try {
      await api(`/waitlist/${item.item_id}/scan`, { method: 'POST' });
      load();
    } finally { setScanId(null); }
  };

  const del = async (item: Item) => {
    await api(`/waitlist/${item.item_id}`, { method: 'DELETE' });
    setItems(prev => prev.filter(i => i.item_id !== item.item_id));
  };

  const filtered = filter === 'ALL' ? items : items.filter(i => (filter === 'FOUND' ? i.status === 'slot_found' : i.status !== 'slot_found'));

  return (
    <SafeAreaView testID="waitlist-screen" style={styles.root} edges={['top']}>
      {locked && (
        <View testID="waitlist-paywall" style={{ padding: S.lg }}>
          <Paywall tier="guardian" message={tt('tabs_waitlist.waitlist_hunter') + ' — Guardian Plan'} onUnlocked={load} />
        </View>
      )}
      <View style={styles.header}>
        <Text style={styles.title}>{tt('tabs_waitlist.waitlist_hunter')}</Text>
        <Text style={styles.sub}>{tt('tabs_waitlist.cz_sk_zk_proof')}</Text>
      </View>

      <View style={styles.chipRow}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: S.lg, gap: S.sm }}>
          {['ALL', 'HUNTING', 'FOUND'].map(k => {
            const active = filter === k;
            return (
              <Pressable testID={`chip-${k}`} key={k} onPress={() => setFilter(k === 'HUNTING' ? 'HUNTING' : k)} style={[styles.chip, active && styles.chipActive]}>
                <Text style={[styles.chipText, active && styles.chipTextActive]}>{k}</Text>
              </Pressable>
            );
          })}
        </ScrollView>
      </View>

      <FlatList
        data={filtered}
        keyExtractor={i => i.item_id}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.fg} />}
        contentContainerStyle={{ padding: S.lg, paddingBottom: 160 }}
        ListEmptyComponent={!loading ? (
          <View style={styles.empty}>
            <Ionicons name="calendar-outline" size={48} color={C.fg} />
            <Text style={styles.emptyText}>{t('no_waitlist', lang).toUpperCase()}</Text>
          </View>
        ) : null}
        renderItem={({ item }) => (
          <View testID={`wl-${item.item_id}`} style={[styles.card, item.status === 'slot_found' && styles.cardFound]}>
            <View style={styles.cardHead}>
              <Text style={styles.cardSpec}>{item.specialty.toUpperCase()}</Text>
              <Pressable testID={`wl-del-${item.item_id}`} onPress={() => del(item)} hitSlop={10}>
                <Ionicons name="close" size={18} color={C.fg} />
              </Pressable>
            </View>
            <Text style={styles.cardClinic}>{item.clinic} · {item.city}</Text>
            <View style={styles.rowSpread}>
              <View><Text style={styles.rowLabel}>{tt('tabs_waitlist.current')}</Text><Text style={styles.rowVal}>{item.current_date}</Text></View>
              <Ionicons name="arrow-forward" size={16} color={C.fg} />
              <View><Text style={styles.rowLabel}>{tt('tabs_waitlist.target')}</Text><Text style={styles.rowVal}>{item.target_before}</Text></View>
            </View>
            {item.status === 'slot_found' && item.found_slot && (
              <View style={styles.foundBox}>
                <Ionicons name="checkmark-circle" size={18} color={C.onError} />
                <Text style={styles.foundText}>{t('slot_found', lang).toUpperCase()}: {item.found_slot}</Text>
              </View>
            )}
            <Pressable testID={`wl-scan-${item.item_id}`} onPress={() => scan(item)} style={styles.scanBtn}>
              {scanId === item.item_id ? <ActivityIndicator color={C.onInverse} /> : <>
                <Ionicons name="radio-outline" size={16} color={C.onInverse} />
                <Text style={styles.scanBtnText}>{t('scan', lang).toUpperCase()}</Text>
              </>}
            </Pressable>
          </View>
        )}
      />

      <Pressable testID="wl-add-btn" onPress={() => setModal(true)} style={styles.fab}>
        <Ionicons name="add" size={24} color={C.onInverse} />
        <Text style={styles.fabText}>{t('add', lang).toUpperCase()}</Text>
      </Pressable>

      <Modal visible={modal} animationType="slide" transparent>
        <View style={styles.modalRoot}>
          <View style={styles.modalCard}>
            <View style={styles.modalHead}>
              <Text style={styles.modalTitle}>{tt('tabs_waitlist.add_waitlist')}</Text>
              <Pressable testID="wl-modal-close" onPress={() => setModal(false)}><Ionicons name="close" size={22} color={C.onInverse} /></Pressable>
            </View>
            <ScrollView style={{ maxHeight: 480 }} contentContainerStyle={{ padding: S.lg, gap: S.md }}>
              <Text style={styles.lbl}>{t('specialty', lang).toUpperCase()}</Text>
              <Pressable testID="wl-spec-open" onPress={() => setSheet('spec')} style={styles.pickerField}>
                <Ionicons name="medkit-outline" size={18} color={C.brand} />
                <Text style={styles.pickerValue}>{f.specialty}</Text>
                <Ionicons name="chevron-down" size={18} color={C.info} />
              </Pressable>
              <Text style={styles.lbl}>{t('clinic', lang).toUpperCase()}</Text>
              <TextInput testID="wl-clinic" value={f.clinic} onChangeText={v => setF({ ...f, clinic: v })} style={styles.input} placeholder={tt('tabs_waitlist.university_hospital')} placeholderTextColor="#999" />
              <Text style={styles.lbl}>{t('city', lang).toUpperCase()}</Text>
              <TextInput testID="wl-city" value={f.city} onChangeText={v => setF({ ...f, city: v })} style={styles.input} placeholder={tt('tabs_waitlist.bratislava')} placeholderTextColor="#999" />
              <Text style={styles.lbl}>{t('current_date', lang).toUpperCase()}</Text>
              <Pressable testID="wl-current" onPress={() => setSheet('current')} style={styles.pickerField}>
                <Ionicons name="calendar-outline" size={18} color={C.brand} />
                <Text style={[styles.pickerValue, !f.current_date && { color: '#999' }]}>{f.current_date || tt('tabs_waitlist.pick_a_date')}</Text>
                <Ionicons name="chevron-down" size={18} color={C.info} />
              </Pressable>
              <Text style={styles.lbl}>{t('target_before', lang).toUpperCase()}</Text>
              <Pressable testID="wl-target" onPress={() => setSheet('target')} style={styles.pickerField}>
                <Ionicons name="flag-outline" size={18} color={C.brand} />
                <Text style={[styles.pickerValue, !f.target_before && { color: '#999' }]}>{f.target_before || tt('tabs_waitlist.pick_a_date')}</Text>
                <Ionicons name="chevron-down" size={18} color={C.info} />
              </Pressable>
            </ScrollView>
            <Pressable testID="wl-save" onPress={add} style={styles.saveBtn}>
              <Text style={styles.saveBtnText}>{t('save', lang).toUpperCase()}</Text>
            </Pressable>
          </View>
        </View>
      </Modal>

      <OptionSheet testID="wl-spec-sheet" visible={sheet === 'spec'} onClose={() => setSheet(null)} title={tt('tabs_waitlist.specialty')}
        options={SPECIALTIES.map(s => ({ label: s, value: s, icon: 'medkit-outline' }))}
        selected={f.specialty} onSelect={v => setF({ ...f, specialty: v })} />
      <DateSheet testID="wl-current-sheet" visible={sheet === 'current'} onClose={() => setSheet(null)}
        title={tt('tabs_waitlist.current_appointment')} initial={f.current_date} onSelect={v => setF({ ...f, current_date: v })} />
      <DateSheet testID="wl-target-sheet" visible={sheet === 'target'} onClose={() => setSheet(null)}
        title={tt('tabs_waitlist.want_a_slot_before')} initial={f.target_before} onSelect={v => setF({ ...f, target_before: v })} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { paddingHorizontal: S.lg, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 22, fontWeight: '900', letterSpacing: 2 },
  sub: { color: C.onInverse, opacity: 0.6, fontSize: 10, letterSpacing: 2, marginTop: 2 },
  chipRow: { height: 56, borderBottomWidth: 1.5, borderColor: C.borderStrong, justifyContent: 'center' },
  chip: { height: 36, paddingHorizontal: S.md, borderWidth: 1.5, borderColor: C.borderStrong, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  chipActive: { backgroundColor: C.inverse, borderColor: C.inverse },
  chipText: { fontWeight: '800', color: C.fg, fontSize: 12, letterSpacing: 1 },
  chipTextActive: { color: C.onInverse },
  empty: { alignItems: 'center', paddingVertical: 60, gap: S.md },
  emptyText: { color: C.fg, fontWeight: '800', letterSpacing: 1, fontSize: 13, textAlign: 'center' },
  card: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginBottom: S.md, backgroundColor: C.bg },
  cardFound: { borderColor: C.error, borderWidth: 2 },
  cardHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  cardSpec: { fontSize: 14, fontWeight: '900', letterSpacing: 1.5, color: C.fg },
  cardClinic: { color: C.onS3, marginTop: 4, fontSize: 12 },
  rowSpread: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: S.md, paddingTop: S.md, borderTopWidth: 1, borderColor: C.border },
  rowLabel: { fontSize: 10, letterSpacing: 1.5, color: C.onS3 },
  rowVal: { fontSize: 16, fontWeight: '900', color: C.fg, marginTop: 2 },
  foundBox: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: C.error, padding: S.md, marginTop: S.md },
  foundText: { color: C.onError, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  scanBtn: { marginTop: S.md, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.inverse, paddingVertical: S.md },
  scanBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
  fab: { position: 'absolute', bottom: Platform.OS === 'ios' ? 100 : 80, right: S.lg, flexDirection: 'row', gap: 8, alignItems: 'center', backgroundColor: C.inverse, paddingHorizontal: S.lg, paddingVertical: S.md, borderWidth: 2, borderColor: C.borderStrong },
  fabText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  modalRoot: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  modalCard: { backgroundColor: C.bg, borderTopWidth: 2, borderColor: C.borderStrong },
  modalHead: { flexDirection: 'row', justifyContent: 'space-between', padding: S.lg, backgroundColor: C.inverse },
  modalTitle: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 16 },
  pickerField: { flexDirection: 'row', alignItems: 'center', gap: S.md, borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: 14, padding: S.lg, minHeight: 56, backgroundColor: 'rgba(212,175,55,0.05)' },
  pickerValue: { flex: 1, color: C.fg, fontSize: 15, fontWeight: '700' },
  lbl: { fontSize: 10, letterSpacing: 2, color: C.onS3, fontWeight: '800' },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 15, color: C.fg, backgroundColor: C.bg },
  saveBtn: { backgroundColor: C.inverse, paddingVertical: S.lg, alignItems: 'center' },
  saveBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 15 },
});
