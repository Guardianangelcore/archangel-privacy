/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, Pressable, StyleSheet, TextInput, ScrollView, Modal, ActivityIndicator, Platform, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import * as Notifications from 'expo-notifications';
import * as Haptics from 'expo-haptics';
import { createAudioPlayer, setAudioModeAsync } from 'expo-audio';
import { api, API_BASE, getToken } from '@/src/api';
import { useAuth } from '@/src/auth';
import { EmptyState } from '@/src/ui/EmptyState';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';
import { useI18n } from '@/src/i18n-context';

type TodayItem = { reminder_id: string; name: string; dose: string; time: string; taken: boolean };
type Reminder = { reminder_id: string; name: string; dose: string; times: string[]; slots?: string[] };

const TIME_CHIPS = ['06:00', '08:00', '12:00', '15:00', '18:00', '20:00', '22:00'];

// Angel Mode 2.0 — flexible day-part slots with big Sun/Moon icons
const SLOTS: { key: string; label: string; icon: any; time: string | null }[] = [
  { key: 'upon_waking', label: 'UPON WAKING', icon: 'partly-sunny', time: '07:00' },
  { key: 'breakfast', label: 'WITH BREAKFAST', icon: 'sunny-outline', time: '08:00' },
  { key: 'lunch', label: 'NA OBED', icon: 'sunny', time: '12:00' },
  { key: 'evening', label: 'EVENING', icon: 'moon-outline', time: '18:00' },
  { key: 'night', label: 'BEFORE SLEEP', icon: 'moon', time: '22:00' },
  { key: 'as_needed', label: 'AS NEEDED', icon: 'medkit', time: null },
];
const SLOT_LABEL: Record<string, string> = Object.fromEntries(SLOTS.map(s => [s.key, s.label]));

async function rescheduleLocal(reminders: Reminder[]) {
  if (Platform.OS === 'web') return;
  try {
    const { status } = await Notifications.requestPermissionsAsync();
    await Notifications.cancelAllScheduledNotificationsAsync();
    if (status !== 'granted') return;
    for (const r of reminders) {
      for (const tm of r.times) {
        const [hour, minute] = tm.split(':').map(Number);
        await Notifications.scheduleNotificationAsync({
          content: { title: '💊 GUARDIAN ANGEL — LIEKY', body: `${r.name}${r.dose ? ` (${r.dose})` : ''} · ${tm}`, sound: 'default', data: { action_url: '/meds' } },
          trigger: { type: Notifications.SchedulableTriggerInputTypes.DAILY, hour, minute },
        });
      }
    }
  } catch (e) { console.log('sched err', e); }
}

export default function Meds() {
  const { t: tt, tx } = useI18n();
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'en';
  const router = useRouter();
  const [today, setToday] = useState<TodayItem[]>([]);
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(false);
  const [modal, setModal] = useState(false);
  const [f, setF] = useState({ name: '', dose: '', times: [] as string[], slots: [] as string[] });
  const playerRef = useRef<any>(null);
  const spokeRef = useRef(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [td, rs] = await Promise.all([api<any>('/meds/today'), api<Reminder[]>('/meds/reminders')]);
      setToday(td.items); setReminders(rs);
      rescheduleLocal(rs);
    } catch (e) { console.log(e); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => () => { try { playerRef.current?.remove?.(); } catch {} }, []);

  const speak = useCallback(async (msg: string) => {
    try {
      const res: any = await api('/voice/tts', { method: 'POST', body: JSON.stringify({ text: msg, voice: 'nova', language: lang }) });
      const token = await getToken();
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false } as any);
      try { playerRef.current?.remove?.(); } catch {}
      const player = createAudioPlayer({ uri: `${API_BASE}${res.url}`, headers: token ? { Authorization: `Bearer ${token}` } : {} });
      playerRef.current = player;
      player.play();
    } catch (e) { console.log('tts err', e); }
  }, [lang]);

  const speakToday = useCallback((items: TodayItem[]) => {
    const pending = items.filter(i => !i.taken);
    const msg = pending.length === 0
      ? (lang === 'sk' ? 'Great! All medications for today are taken.' : 'Great! All medications for today are taken.')
      : (lang === 'sk'
        ? `Still ahead today: ${pending.map(p => `${p.name} at ${p.time.replace(':', ' ')}`).join(', ')}.`
        : `Still pending today: ${pending.map(p => `${p.name} at ${p.time}`).join(', ')}.`);
    speak(msg);
  }, [lang, speak]);

  // Voice alert on open (native, once) if something is pending
  useEffect(() => {
    if (Platform.OS === 'web' || spokeRef.current || today.length === 0) return;
    if (today.some(i => !i.taken)) { spokeRef.current = true; speakToday(today); }
  }, [today, speakToday]);

  const take = async (item: TodayItem) => {
    if (Platform.OS !== 'web') Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    setToday(prev => prev.map(x => (x.reminder_id === item.reminder_id && x.time === item.time) ? { ...x, taken: true } : x));
    try { await api('/meds/intake', { method: 'POST', body: JSON.stringify({ reminder_id: item.reminder_id, time: item.time }) }); } catch (e) { console.log(e); load(); }
  };

  const canSave = !!f.name && (f.times.length > 0 || f.slots.length > 0);
  const add = async () => {
    if (!canSave) return;
    const slotTimes = SLOTS.filter(s => f.slots.includes(s.key) && s.time).map(s => s.time as string);
    const times = [...new Set([...slotTimes, ...f.times])].sort();
    await api('/meds/reminders', { method: 'POST', body: JSON.stringify({ name: f.name, dose: f.dose, times, slots: f.slots }) });
    setModal(false); setF({ name: '', dose: '', times: [], slots: [] }); load();
  };
  const del = async (r: Reminder) => {
    await api(`/meds/reminders/${r.reminder_id}`, { method: 'DELETE' });
    load();
  };
  const toggleTime = (tm: string) => setF(v => ({ ...v, times: v.times.includes(tm) ? v.times.filter(x => x !== tm) : [...v.times, tm] }));
  const toggleSlot = (key: string) => {
    if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
    setF(v => ({ ...v, slots: v.slots.includes(key) ? v.slots.filter(x => x !== key) : [...v.slots, key] }));
  };

  const pending = today.filter(i => !i.taken).length;

  return (
    <SafeAreaView testID="meds-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="md-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={30} color={C.onInverse} />
        </Pressable>
        <Text style={styles.title}>{t('meds_reminders', lang).toUpperCase()}</Text>
        <Pressable testID="md-speak" onPress={() => speakToday(today)} hitSlop={12}>
          <Ionicons name="volume-high" size={28} color={C.onInverse} />
        </Pressable>
      </View>

      <ScrollView
        contentContainerStyle={{ padding: S.lg, paddingBottom: 140 }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.fg} />}
      >
        {today.length > 0 && (
          <View style={[styles.statusBanner, pending === 0 && { backgroundColor: C.brandTer, borderColor: C.brand }]}>
            <Ionicons name={pending === 0 ? 'checkmark-circle' : 'time'} size={26} color={pending === 0 ? C.brand : C.onWarn} />
            <Text style={[styles.statusText, pending === 0 && { color: C.brand }]}>
              {pending === 0 ? t('all_taken', lang).toUpperCase() + ' ✓' : tt('meds.still_to_take_today', [pending])}
            </Text>
          </View>
        )}

        {today.length === 0 && !loading ? (
          <EmptyState testID="md-empty" icon="medkit-outline" title={t('empty_meds_title', lang)} sub={t('empty_meds_sub', lang)}
            ctaLabel={t('empty_meds_cta', lang)} onCta={() => setModal(true)} />
        ) : today.map(item => (
          <View key={`${item.reminder_id}-${item.time}`} testID={`med-${item.reminder_id}-${item.time}`} style={[styles.medCard, item.taken && styles.medCardDone]}>
            <View style={styles.medRow}>
              <View style={styles.timeBox}>
                <Text style={styles.timeText}>{item.time}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.medName}>{item.name.toUpperCase()}</Text>
                {item.dose ? <Text style={styles.medDose}>{item.dose}</Text> : null}
              </View>
            </View>
            {item.taken ? (
              <View style={styles.doneBtn}>
                <Ionicons name="checkmark-circle" size={26} color={C.brand} />
                <Text style={styles.doneText}>{t('done_taken', lang).toUpperCase()} ✓</Text>
              </View>
            ) : (
              <Pressable testID={`med-take-${item.reminder_id}-${item.time}`} onPress={() => take(item)} style={styles.takeBtn}>
                <Ionicons name="checkmark" size={30} color={C.onInverse} />
                <Text style={styles.takeText}>{t('taken_btn', lang).toUpperCase()}</Text>
              </Pressable>
            )}
          </View>
        ))}

        {reminders.length > 0 && (
          <>
            <Text style={styles.section}>{tt('meds.moje_lieky')}</Text>
            {reminders.map(r => (
              <View key={r.reminder_id} style={styles.remRow}>
                <Ionicons name="medkit-outline" size={20} color={C.fg} />
                <View style={{ flex: 1 }}>
                  <Text style={styles.remName}>{r.name}{r.dose ? ` · ${r.dose}` : ''}</Text>
                  <Text style={styles.remTimes}>
                    {(r.slots || []).length > 0 ? (r.slots || []).map(sl => SLOT_LABEL[sl] || sl).join(' · ') : r.times.join(' · ')}
                    {(r.slots || []).length > 0 && r.times.length > 0 ? ` · ${r.times.join(' · ')}` : ''}
                  </Text>
                </View>
                <Pressable testID={`med-del-${r.reminder_id}`} onPress={() => del(r)} hitSlop={12}>
                  <Ionicons name="trash-outline" size={22} color={C.error} />
                </Pressable>
              </View>
            ))}
          </>
        )}
        {Platform.OS !== 'web' && <Text style={styles.hint}>{tt('meds.reminders_arrive_as_daily_notificati')}</Text>}
      </ScrollView>

      <Pressable testID="md-add-btn" onPress={() => setModal(true)} style={styles.fab}>
        <Ionicons name="add" size={26} color={C.onInverse} />
        <Text style={styles.fabText}>{t('add_reminder', lang).toUpperCase()}</Text>
      </Pressable>

      <Modal visible={modal} animationType="slide" transparent>
        <View style={styles.modalRoot}>
          <View style={styles.modalCard}>
            <View style={styles.modalHead}>
              <Text style={styles.modalTitle}>{t('add_reminder', lang).toUpperCase()}</Text>
              <Pressable testID="md-modal-close" onPress={() => setModal(false)}><Ionicons name="close" size={24} color={C.onInverse} /></Pressable>
            </View>
            <ScrollView contentContainerStyle={{ padding: S.lg, gap: S.md }} style={{ maxHeight: 460 }}>
              <TextInput testID="md-name" placeholder={tt('meds.euthyrox')} value={f.name} onChangeText={v => setF({ ...f, name: v })} style={styles.input} placeholderTextColor="#999" />
              <TextInput testID="md-dose" placeholder={tt('meds.1_tbl_50_mg', [t('dose', lang)])} value={f.dose} onChangeText={v => setF({ ...f, dose: v })} style={styles.input} placeholderTextColor="#999" />
              <Text style={styles.lbl}>{tt('meds.when_to_take')}</Text>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: S.sm }}>
                {SLOTS.map(sl => {
                  const on = f.slots.includes(sl.key);
                  return (
                    <Pressable testID={`md-slot-${sl.key}`} key={sl.key} onPress={() => toggleSlot(sl.key)}
                      style={[styles.slotCard, on && styles.slotCardOn]}>
                      <Ionicons name={sl.icon} size={34} color={on ? C.onInverse : C.brand} />
                      <Text style={[styles.slotLabel, on && { color: C.onInverse }]}>{tx(sl.label)}</Text>
                      {sl.time && <Text style={[styles.slotTime, on && { color: C.onInverse }]}>{sl.time}</Text>}
                    </Pressable>
                  );
                })}
              </View>
              <Text style={styles.lbl}>{tt('meds.custom_times_optional')}</Text>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: S.sm }}>
                {TIME_CHIPS.map(tm => (
                  <Pressable testID={`md-time-${tm}`} key={tm} onPress={() => toggleTime(tm)} style={[styles.chip, f.times.includes(tm) && styles.chipActive]}>
                    <Text style={[styles.chipText, f.times.includes(tm) && styles.chipTextActive]}>{tm}</Text>
                  </Pressable>
                ))}
              </View>
            </ScrollView>
            <Pressable testID="md-save" onPress={add} disabled={!canSave} style={[styles.saveBtn, !canSave && { opacity: 0.4 }]}>
              {loading ? <ActivityIndicator color={C.onInverse} /> : <Text style={styles.saveBtnText}>{t('save', lang).toUpperCase()}</Text>}
            </Pressable>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.lg, paddingVertical: S.lg, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 20, fontWeight: '900', letterSpacing: 2 },
  statusBanner: { flexDirection: 'row', alignItems: 'center', gap: S.md, borderWidth: 2, borderColor: C.warn, backgroundColor: C.warn, padding: S.md, marginBottom: S.lg },
  statusText: { fontWeight: '900', fontSize: 16, letterSpacing: 1, color: C.onWarn },
  empty: { textAlign: 'center', color: C.onS3, marginTop: 40, letterSpacing: 2, fontWeight: '800', fontSize: 14 },
  medCard: { borderWidth: 2.5, borderColor: C.borderStrong, marginBottom: S.md },
  medCardDone: { borderColor: C.border, opacity: 0.75 },
  medRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, padding: S.md },
  timeBox: { backgroundColor: C.inverse, paddingHorizontal: S.md, paddingVertical: 10 },
  timeText: { color: C.onInverse, fontWeight: '900', fontSize: 22 },
  medName: { fontWeight: '900', fontSize: 20, color: C.fg, letterSpacing: 1 },
  medDose: { color: C.onS3, fontSize: 15, marginTop: 2 },
  takeBtn: { flexDirection: 'row', gap: 10, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, paddingVertical: 18 },
  takeText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 18 },
  doneBtn: { flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', paddingVertical: 14, borderTopWidth: 1.5, borderColor: C.border },
  doneText: { color: C.brand, fontWeight: '900', letterSpacing: 2, fontSize: 15 },
  section: { marginTop: S.xl, marginBottom: S.md, fontSize: 12, letterSpacing: 2, color: C.fg, fontWeight: '900' },
  remRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, borderWidth: 1.5, borderColor: C.border, padding: S.md, marginBottom: S.sm },
  remName: { fontWeight: '900', fontSize: 15, color: C.fg },
  remTimes: { color: C.onS3, fontSize: 12, marginTop: 2, letterSpacing: 1 },
  hint: { marginTop: S.lg, fontSize: 10, letterSpacing: 1, color: C.onS3, fontWeight: '700' },
  fab: { position: 'absolute', bottom: 24, right: S.lg, flexDirection: 'row', gap: 8, alignItems: 'center', backgroundColor: C.inverse, paddingHorizontal: S.lg, paddingVertical: S.lg, borderWidth: 2, borderColor: C.borderStrong },
  fabText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 14 },
  modalRoot: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  modalCard: { backgroundColor: C.bg, borderTopWidth: 2, borderColor: C.borderStrong },
  modalHead: { flexDirection: 'row', justifyContent: 'space-between', padding: S.lg, backgroundColor: C.inverse },
  modalTitle: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 15 },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.lg, fontSize: 18, color: C.fg },
  lbl: { fontSize: 11, letterSpacing: 2, color: C.onS3, fontWeight: '800' },
  chip: { paddingHorizontal: S.lg, paddingVertical: 12, borderWidth: 1.5, borderColor: C.borderStrong },
  chipActive: { backgroundColor: C.inverse },
  chipText: { fontWeight: '900', color: C.fg, fontSize: 15, letterSpacing: 1 },
  chipTextActive: { color: C.onInverse },
  slotCard: { width: '31%', flexGrow: 1, minHeight: 96, alignItems: 'center', justifyContent: 'center', gap: 6, borderWidth: 2, borderColor: C.borderStrong, borderRadius: 16, backgroundColor: 'rgba(212,175,55,0.06)', paddingVertical: S.md },
  slotCardOn: { backgroundColor: C.brand, borderColor: C.brand },
  slotLabel: { fontWeight: '900', color: C.fg, fontSize: 10, letterSpacing: 0.5, textAlign: 'center' },
  slotTime: { fontWeight: '800', color: C.info, fontSize: 11 },
  saveBtn: { backgroundColor: C.brand, paddingVertical: 20, alignItems: 'center' },
  saveBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 16 },
});
