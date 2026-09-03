/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, FlatList, TextInput, ScrollView, Modal, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { WheelField } from '@/src/ui/fields';
import JarvisAdvice from '@/src/JarvisAdvice';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';
import { useI18n } from '@/src/i18n-context';

type Item = { item_id: string; name: string; category: string; quantity: number; unit: string; daily_need_per_person: number };
type Runway = { family_size: number; category_runways: Record<string, number>; overall_days: number; items_count: number };

const CATS: { key: string; icon: any; label: string }[] = [
  { key: 'water', icon: 'water-outline', label: 'VODA' },
  { key: 'food', icon: 'restaurant-outline', label: 'JEDLO' },
  { key: 'power', icon: 'battery-charging-outline', label: 'ENERGIA' },
  { key: 'meds', icon: 'medkit-outline', label: 'LIEKY' },
  { key: 'tools', icon: 'construct-outline', label: 'TOOLS' },
];

export default function SurvivalAuditor() {
  const { t: tt, tx } = useI18n();
  const { user, setUser } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'en';
  const router = useRouter();
  const [items, setItems] = useState<Item[]>([]);
  const [runway, setRunway] = useState<Runway | null>(null);
  const [loading, setLoading] = useState(false);
  const [modal, setModal] = useState(false);
  const [f, setF] = useState({ name: '', category: 'water', quantity: '1', unit: 'l', daily_need_per_person: '1' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [a, b] = await Promise.all([api<Item[]>('/survival/items'), api<Runway>('/survival/runway')]);
      setItems(a); setRunway(b);
    } catch (e) { console.log(e); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const add = async () => {
    if (!f.name) return;
    await api('/survival/items', { method: 'POST', body: JSON.stringify({ ...f, quantity: parseFloat(f.quantity) || 1, daily_need_per_person: parseFloat(f.daily_need_per_person) || 1 }) });
    setModal(false); setF({ name: '', category: 'water', quantity: '1', unit: 'l', daily_need_per_person: '1' }); load();
  };
  const del = async (it: Item) => {
    await api(`/survival/items/${it.item_id}`, { method: 'DELETE' });
    load();
  };
  const setFamily = async (n: number) => {
    const u: any = await api('/me/prefs', { method: 'PATCH', body: JSON.stringify({ family_size: n }) });
    setUser(u); load();
  };

  const familySize = (user as any)?.family_size || 2;
  const overall = runway?.overall_days ?? 0;
  const overallColor = overall < 3 ? C.error : overall < 7 ? C.warn : C.brand;

  return (
    <SafeAreaView testID="survival-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="sa-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={styles.title}>{t('survival_auditor', lang).toUpperCase()}</Text>
        <View style={{ width: 26 }} />
      </View>

      <FlatList
        data={items}
        keyExtractor={i => i.item_id}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.fg} />}
        contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}
        ListHeaderComponent={
          <View>
            <View style={[styles.runwayCard, { borderColor: overallColor }]}>
              <Text style={styles.runwayLbl}>{t('survival_runway', lang).toUpperCase()}</Text>
              <Text testID="sa-overall" style={[styles.runwayVal, { color: overallColor }]}>{overall}</Text>
              <Text style={styles.runwayUnit}>{tt('survival_auditor.days')} {familySize} {tt('survival_auditor.people')}</Text>
              <View style={styles.catRow}>
                {CATS.map(c => (
                  <View key={c.key} style={styles.catBox}>
                    <Ionicons name={c.icon} size={18} color={C.fg} />
                    <Text style={styles.catVal}>{runway?.category_runways?.[c.key]?.toFixed(0) ?? '—'}</Text>
                    <Text style={styles.catLbl}>{tx(c.label)}</Text>
                  </View>
                ))}
              </View>
            </View>

            <Text style={styles.lbl}>{t('family_size', lang).toUpperCase()}</Text>
            <View style={{ flexDirection: 'row', gap: S.sm }}>
              {[1, 2, 3, 4, 5, 6].map(n => (
                <Pressable testID={`fam-${n}`} key={n} onPress={() => setFamily(n)} style={[styles.famChip, familySize === n && styles.famChipActive]}>
                  <Text style={[styles.famText, familySize === n && { color: C.onInverse }]}>{n}</Text>
                </Pressable>
              ))}
            </View>

            <JarvisAdvice module="survival_auditor" lang={lang} buildContext={() => `Survival runway: overall ${overall} days for ${familySize} people. Categories: ${JSON.stringify(runway?.category_runways || {})}. Items: ${items.map(i => `${i.name} ${i.quantity}${i.unit}`).join(', ') || 'none'}`} />
            <Text style={styles.section}>{tt('survival_auditor.inventory')}</Text>
          </View>
        }
        ListEmptyComponent={!loading ? <Text style={styles.noData}>{t('no_data', lang).toUpperCase()}</Text> : null}
        renderItem={({ item }) => (
          <View testID={`sv-${item.item_id}`} style={styles.card}>
            <Ionicons name={(CATS.find(c => c.key === item.category)?.icon) || 'cube-outline'} size={20} color={C.fg} />
            <View style={{ flex: 1 }}>
              <Text style={styles.itemName}>{item.name}</Text>
              <Text style={styles.itemMeta}>{item.quantity} {item.unit} · {item.daily_need_per_person}{tt('survival_auditor.person_day')}</Text>
            </View>
            <Pressable testID={`sv-del-${item.item_id}`} onPress={() => del(item)} hitSlop={10}>
              <Ionicons name="trash-outline" size={18} color={C.error} />
            </Pressable>
          </View>
        )}
      />

      <Pressable testID="sa-add-btn" onPress={() => setModal(true)} style={styles.fab}>
        <Ionicons name="add" size={22} color={C.onInverse} />
        <Text style={styles.fabText}>{t('add', lang).toUpperCase()}</Text>
      </Pressable>

      <Modal visible={modal} animationType="slide" transparent>
        <View style={styles.modalRoot}>
          <View style={styles.modalCard}>
            <View style={styles.modalHead}>
              <Text style={styles.modalTitle}>{tt('survival_auditor.inventory_gj0y')}</Text>
              <Pressable testID="sa-modal-close" onPress={() => setModal(false)}><Ionicons name="close" size={22} color={C.onInverse} /></Pressable>
            </View>
            <ScrollView contentContainerStyle={{ padding: S.lg, gap: S.md }} style={{ maxHeight: 420 }}>
              <TextInput testID="sv-name" placeholder={tt('survival_auditor.bottled_water_1_5l')} value={f.name} onChangeText={v => setF({ ...f, name: v })} style={styles.input} placeholderTextColor="#999" />
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: S.sm }}>
                {CATS.map(c => (
                  <Pressable testID={`sv-cat-${c.key}`} key={c.key} onPress={() => setF({ ...f, category: c.key })} style={[styles.chip, f.category === c.key && styles.chipActive]}>
                    <Text style={[styles.chipText, f.category === c.key && styles.chipTextActive]}>{tx(c.label)}</Text>
                  </Pressable>
                ))}
              </View>
              <View style={{ flexDirection: 'row', gap: S.sm }}>
                <WheelField testID="sv-qty" title={tt('survival_auditor.quantity')} min={1} max={500} value={f.quantity} onChange={v => setF({ ...f, quantity: v })} placeholder="12" style={[styles.input, { flex: 1 }]} />
                <TextInput testID="sv-unit" placeholder={tt('survival_auditor.l_ks_kg')} value={f.unit} onChangeText={v => setF({ ...f, unit: v })} style={[styles.input, { flex: 1 }]} placeholderTextColor="#999" />
              </View>
              <Text style={styles.lbl}>{tt('survival_auditor.consumption_person_day')}</Text>
              <WheelField testID="sv-need" title={tt('survival_auditor.daily_need_person')} min={1} max={20} value={f.daily_need_per_person} onChange={v => setF({ ...f, daily_need_per_person: v })} placeholder="3" style={styles.input} />
            </ScrollView>
            <Pressable testID="sa-save" onPress={add} style={styles.saveBtn}>
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
  runwayCard: { borderWidth: 2.5, padding: S.lg, alignItems: 'center' },
  runwayLbl: { fontSize: 11, letterSpacing: 2, color: C.onS3, fontWeight: '900' },
  runwayVal: { fontSize: 64, fontWeight: '900', marginTop: 4 },
  runwayUnit: { fontSize: 11, letterSpacing: 2, color: C.onS3, fontWeight: '800' },
  catRow: { flexDirection: 'row', gap: S.sm, marginTop: S.lg },
  catBox: { flex: 1, alignItems: 'center', gap: 2, borderWidth: 1, borderColor: C.border, paddingVertical: 8 },
  catVal: { fontWeight: '900', fontSize: 14, color: C.fg },
  catLbl: { fontSize: 8, letterSpacing: 1, color: C.onS3, fontWeight: '800' },
  lbl: { fontSize: 10, letterSpacing: 2, color: C.onS3, fontWeight: '800', marginTop: S.lg, marginBottom: 6 },
  famChip: { width: 44, height: 44, borderWidth: 1.5, borderColor: C.borderStrong, alignItems: 'center', justifyContent: 'center' },
  famChipActive: { backgroundColor: C.inverse },
  famText: { fontWeight: '900', fontSize: 16, color: C.fg },
  section: { marginTop: S.lg, marginBottom: S.md, fontSize: 11, letterSpacing: 2, color: C.fg, fontWeight: '900' },
  noData: { color: C.onS3, fontSize: 12, letterSpacing: 1 },
  card: { flexDirection: 'row', alignItems: 'center', gap: S.md, borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginBottom: S.sm },
  itemName: { fontWeight: '900', fontSize: 14, color: C.fg },
  itemMeta: { color: C.onS3, fontSize: 11, marginTop: 2 },
  fab: { position: 'absolute', bottom: 24, right: S.lg, flexDirection: 'row', gap: 8, alignItems: 'center', backgroundColor: C.inverse, paddingHorizontal: S.lg, paddingVertical: S.md, borderWidth: 2, borderColor: C.borderStrong },
  fabText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  modalRoot: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  modalCard: { backgroundColor: C.bg, borderTopWidth: 2, borderColor: C.borderStrong },
  modalHead: { flexDirection: 'row', justifyContent: 'space-between', padding: S.lg, backgroundColor: C.inverse },
  modalTitle: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 14 },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 15, color: C.fg },
  chip: { paddingHorizontal: S.md, paddingVertical: 8, borderWidth: 1.5, borderColor: C.borderStrong },
  chipActive: { backgroundColor: C.inverse },
  chipText: { fontWeight: '800', color: C.fg, fontSize: 11, letterSpacing: 1 },
  chipTextActive: { color: C.onInverse },
  saveBtn: { backgroundColor: C.inverse, paddingVertical: S.lg, alignItems: 'center' },
  saveBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2 },
});
