/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { api } from '@/src/api';
import { WheelField } from '@/src/ui/fields';
import { C, S, R } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

const CAT_ICON: Record<string, string> = { financial: 'card', social: 'share-social', property: 'home', digital: 'cloud' };
const SUB_ACTIONS: [string, string][] = [['cancel', 'CANCEL'], ['transfer', 'TRANSFER'], ['memorialize', 'MEMORIALIZE']];

export default function DigitalLegacy() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const [list, setList] = useState<any>(null);
  const [subs, setSubs] = useState<any>(null);
  const [name, setName] = useState('');
  const [cost, setCost] = useState('');
  const [action, setAction] = useState('cancel');
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    try {
      const [c, s] = await Promise.all([api('/legacy/checklist'), api('/legacy/subscriptions')]);
      setList(c); setSubs(s);
    } catch (e: any) { setErr(String(e.message || e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const hap = () => { if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {}); };

  const toggle = async (item: any) => {
    hap();
    setList({ ...list, items: list.items.map((i: any) => i.item_id === item.item_id ? { ...i, checked: !i.checked } : i) });
    try { await api(`/legacy/checklist/${item.item_id}`, { method: 'PUT', body: JSON.stringify({ checked: !item.checked }) }); await load(); }
    catch { await load(); }
  };

  const addSub = async () => {
    if (!name.trim()) return;
    hap();
    try {
      await api('/legacy/subscriptions', { method: 'POST', body: JSON.stringify({ name, cost_monthly: parseFloat(cost) || 0, action }) });
      setName(''); setCost(''); await load();
    } catch (e: any) { setErr(String(e.message || e)); }
  };

  const delSub = async (id: string) => {
    hap();
    try { await api(`/legacy/subscriptions/${id}`, { method: 'DELETE' }); await load(); } catch {}
  };

  const cats: string[] = list ? Object.keys(list.categories) : [];

  return (
    <SafeAreaView testID="digital-legacy-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="dl-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>{tt('digital_legacy.digital_executor')}</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
        <Text style={styles.h1}>{tt('digital_legacy.digital_legacy')}</Text>
        <Text style={styles.sub}>{tt('digital_legacy.a_global_checklist_nothing_important')}</Text>
        {!!err && <Text style={styles.err}>{err}</Text>}

        {list && (
          <View style={styles.progressBox}>
            <View style={styles.progressTrack}>
              <View style={[styles.progressFill, { width: `${list.progress.pct}%` }]} />
            </View>
            <Text testID="dl-progress" style={styles.progressText}>{list.progress.done}/{list.progress.total} {tt('digital_legacy.ready')} {list.progress.pct} %</Text>
          </View>
        )}

        {cats.map(cat => (
          <View key={cat}>
            <View style={styles.catHead}>
              <Ionicons name={(CAT_ICON[cat] || 'list') as any} size={16} color={C.brand} />
              <Text style={styles.section}>{list.categories[cat]}</Text>
            </View>
            {list.items.filter((i: any) => i.cat === cat).map((i: any) => (
              <Pressable key={i.item_id} testID={`dl-item-${i.item_id}`} onPress={() => toggle(i)} style={styles.itemRow}>
                <Ionicons name={i.checked ? 'checkbox' : 'square-outline'} size={24} color={i.checked ? '#5FA779' : C.borderStrong} />
                <Text style={[styles.itemText, i.checked && { opacity: 0.55, textDecorationLine: 'line-through' }]}>{tx(i.title)}</Text>
              </Pressable>
            ))}
          </View>
        ))}

        <Text style={[styles.section, { marginTop: S.xl }]}>{tt('digital_legacy.subscription_liquidator')}</Text>
        <Text style={styles.subSmall}>{tt('digital_legacy.what_should_be_cancelled_transferred')} {subs ? tt('digital_legacy.monthly_saving_from_liquidation', [subs.monthly_liquidation_saving]) : ''}</Text>
        {(subs?.subscriptions || []).map((s: any) => (
          <View key={s.sub_id} style={styles.subRow}>
            <Ionicons name={s.action === 'cancel' ? 'close-circle' : s.action === 'transfer' ? 'swap-horizontal' : 'flower'} size={18} color={s.action === 'cancel' ? C.error : C.brand} />
            <Text style={styles.subName}>{s.name}</Text>
            <Text style={styles.subCost}>{s.cost_monthly ? tt('digital_legacy.mes', [s.cost_monthly, s.currency]) : ''}</Text>
            <Text style={styles.subAction}>{SUB_ACTIONS.find(a => a[0] === s.action)?.[1]}</Text>
            <Pressable testID={`dl-sub-del-${s.sub_id}`} onPress={() => delSub(s.sub_id)} hitSlop={8}>
              <Ionicons name="trash-outline" size={15} color={C.info} />
            </Pressable>
          </View>
        ))}
        <View style={styles.row2}>
          <TextInput testID="dl-sub-name" style={[styles.input, { flex: 2 }]} placeholder={tt('digital_legacy.netflix_spotify_icloud')} placeholderTextColor={C.info} value={name} onChangeText={setName} />
          <WheelField testID="dl-sub-cost" title={tt('digital_legacy.cena_mesiac')} min={0} max={100} step={0.5} decimals={1} unit="€" value={cost} onChange={setCost} placeholder={tt('digital_legacy.mes_i8ji')} style={[styles.input, { flex: 1 }]} />
        </View>
        <View style={styles.row2}>
          {SUB_ACTIONS.map(([k, l]) => (
            <Pressable key={k} testID={`dl-sub-action-${k}`} onPress={() => { hap(); setAction(k); }} style={[styles.chip, action === k && { backgroundColor: C.brand, borderColor: C.brand }]}>
              <Text style={[styles.chipText, action === k && { color: C.onInverse }]}>{l}</Text>
            </Pressable>
          ))}
          <Pressable testID="dl-sub-add" onPress={addSub} style={styles.addBtn}>
            <Ionicons name="add" size={20} color={C.onInverse} />
          </Pressable>
        </View>
        <Text style={styles.disclaimer}>{subs?.note || ''}</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 14 },
  h1: { fontSize: 24, fontWeight: '900', color: C.fg },
  sub: { marginTop: S.sm, fontSize: 12.5, color: C.onS3, lineHeight: 18 },
  subSmall: { fontSize: 11, color: C.info, marginBottom: S.sm, lineHeight: 15 },
  section: { fontSize: 11, letterSpacing: 1.5, color: C.brand, fontWeight: '900' },
  catHead: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: S.xl, marginBottom: S.sm },
  progressBox: { marginTop: S.lg },
  progressTrack: { height: 10, backgroundColor: C.surface3, borderRadius: 5, overflow: 'hidden' },
  progressFill: { height: 10, backgroundColor: '#B8860B', borderRadius: 5 },
  progressText: { color: C.fg, fontWeight: '800', fontSize: 11, marginTop: 6 },
  itemRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, paddingVertical: 10, minHeight: 48, borderBottomWidth: 1, borderBottomColor: C.border },
  itemText: { flex: 1, color: C.fg, fontSize: 13, lineHeight: 18 },
  subRow: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: C.surface2, borderRadius: R.sm, padding: S.md, marginTop: S.sm },
  subName: { flex: 1, color: C.fg, fontWeight: '700', fontSize: 12 },
  subCost: { color: C.info, fontSize: 10.5 },
  subAction: { color: C.brand, fontWeight: '900', fontSize: 9 },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.sm, paddingHorizontal: S.md, minHeight: 48, color: C.fg, backgroundColor: C.surface2, marginTop: S.sm, fontSize: 13 },
  row2: { flexDirection: 'row', gap: S.sm, marginTop: S.sm, alignItems: 'center' },
  chip: { borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.sm, paddingHorizontal: S.md, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  chipText: { color: C.fg, fontWeight: '800', fontSize: 10.5 },
  addBtn: { backgroundColor: C.brand, borderRadius: R.sm, width: 48, height: 44, alignItems: 'center', justifyContent: 'center' },
  err: { color: C.error, marginTop: S.md, fontSize: 12 },
  disclaimer: { marginTop: S.lg, color: C.info, fontSize: 10, lineHeight: 15, textAlign: 'center' },
});
