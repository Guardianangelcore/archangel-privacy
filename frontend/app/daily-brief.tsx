/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, Switch, Platform, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import * as Notifications from 'expo-notifications';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

const NOTIF_KEY = 'dailyBriefNotifOn';

export default function DailyBrief() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const { t } = useI18n();
  const [brief, setBrief] = useState<any>(null);
  const [err, setErr] = useState('');
  const [notifOn, setNotifOn] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try { setBrief(await api('/daily-brief')); } catch (e: any) { setErr(String(e.message || e)); }
  }, []);
  useEffect(() => {
    load();
    AsyncStorage.getItem(NOTIF_KEY).then(v => setNotifOn(v === '1')).catch(() => {});
  }, [load]);

  const toggleNotif = async (v: boolean) => {
    setNotifOn(v);
    await AsyncStorage.setItem(NOTIF_KEY, v ? '1' : '0');
    if (Platform.OS === 'web') return;
    try {
      await Notifications.cancelScheduledNotificationAsync('daily-brief-8am').catch(() => {});
      if (v) {
        const { status, canAskAgain } = await Notifications.getPermissionsAsync();
        if (status !== 'granted' && canAskAgain) {
          const r = await Notifications.requestPermissionsAsync();
          if (r.status !== 'granted') { setNotifOn(false); await AsyncStorage.setItem(NOTIF_KEY, '0'); return; }
        }
        await Notifications.scheduleNotificationAsync({
          identifier: 'daily-brief-8am',
          content: { title: '☀️ Good morning', body: 'Your daily briefing is ready — meds, appointments and family messages.', data: { deeplink: '/daily-brief' } },
          trigger: { type: Notifications.SchedulableTriggerInputTypes.DAILY, hour: 8, minute: 0 } as any,
        });
      }
    } catch (e) { console.log('daily brief notif', e); }
  };

  const takeMed = async (m: any) => {
    try { await api('/meds/intake', { method: 'POST', body: JSON.stringify({ reminder_id: m.reminder_id, time: m.time }) }); await load(); } catch {}
  };

  const answerPulse = async (req: any) => {
    try { await api(`/pulse/requests/${req.req_id}/respond`, { method: 'POST', body: JSON.stringify({ status: 'ok' }) }); await load(); } catch {}
  };

  const today = new Date().toLocaleDateString('sk-SK', { weekday: 'long', day: 'numeric', month: 'long' });

  return (
    <SafeAreaView testID="daily-brief-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="db-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>{t('daily_briefing')}</Text>
        <View style={{ width: 26 }} />
      </View>
      <ScrollView
        contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} tintColor={C.brand} />}
      >
        <Text style={styles.greet}>{t('good_morning')}{'\n'}{brief?.name || '…'}.</Text>
        <Text style={styles.date}>{today}</Text>
        {!!err && <Text style={styles.err}>{err}</Text>}

        <View style={styles.notifRow}>
          <Ionicons name="sunny" size={20} color="#B8860B" />
          <Text style={styles.notifText}>{tt('daily_brief.morning_reminder_at_8_00')}</Text>
          <Switch testID="db-notif" value={notifOn} onValueChange={toggleNotif} trackColor={{ true: C.brand, false: C.surface3 }} />
        </View>

        <Text style={styles.section}>💊 {t('meds_today')} {brief ? tt('daily_brief.pending', [brief.meds.pending]) : ''}</Text>
        {(brief?.meds?.items || []).map((m: any, i: number) => (
          <Pressable key={i} testID={`db-med-${i}`} onPress={() => !m.taken && takeMed(m)} style={[styles.bigRow, m.taken && { opacity: 0.45 }]}>
            <Ionicons name={m.taken ? 'checkmark-circle' : 'ellipse-outline'} size={30} color={m.taken ? '#5FA779' : C.brand} />
            <View style={{ flex: 1 }}>
              <Text style={styles.bigTitle}>{m.name}{m.dose ? ` · ${m.dose}` : ''}</Text>
              <Text style={styles.bigSub}>{m.taken ? tt('daily_brief.taken') : tt('daily_brief.tap_when_taken')}</Text>
            </View>
            <Text style={styles.bigTime}>{m.time}</Text>
          </Pressable>
        ))}
        {brief && brief.meds.items.length === 0 && <Text style={styles.empty}>{tt('daily_brief.no_meds_for_today_add_reminders_in_t')}</Text>}

        <Text style={styles.section}>📅 {t('appointments')}</Text>
        {(brief?.events_today || []).map((e: any) => (
          <View key={e.event_id} style={[styles.bigRow, { borderColor: C.error, borderWidth: 2 }]}>
            <Ionicons name="alarm" size={28} color={C.error} />
            <View style={{ flex: 1 }}>
              <Text style={styles.bigTitle}>{tt('daily_brief.dnes')} {tx(e.title)}</Text>
              <Text style={styles.bigSub}>{e.notes || ''}</Text>
            </View>
          </View>
        ))}
        {(brief?.events_upcoming || []).map((e: any) => (
          <View key={e.event_id} style={styles.bigRow}>
            <Ionicons name="calendar" size={26} color={C.brand} />
            <View style={{ flex: 1 }}>
              <Text style={styles.bigTitle}>{tx(e.title)}</Text>
              <Text style={styles.bigSub}>{e.date}{e.notes ? ` · ${e.notes}` : ''}</Text>
            </View>
          </View>
        ))}
        {brief && brief.events_today.length === 0 && brief.events_upcoming.length === 0 && (
          <Text style={styles.empty}>{tt('daily_brief.no_appointments_in_the_next_3_days_r')}</Text>
        )}

        <Text style={styles.section}>👪 {t('family')}</Text>
        {(brief?.family?.pending_pulse || []).map((p: any) => (
          <Pressable key={p.req_id} testID={`db-pulse-${p.req_id}`} onPress={() => answerPulse(p)} style={[styles.bigRow, { backgroundColor: C.brandTer }]}>
            <Ionicons name="heart" size={28} color={C.brand} />
            <View style={{ flex: 1 }}>
              <Text style={styles.bigTitle}>{p.from_name} {tt('daily_brief.is_asking_if_you_are_ok')}</Text>
              <Text style={styles.bigSub}>{tt('daily_brief.tap_to_reply_i_am_ok')}</Text>
            </View>
          </Pressable>
        ))}
        {brief && brief.family.pending_pulse.length === 0 && (
          <Text style={styles.empty}>{tt('daily_brief.no_new_family_messages')}{brief.family.emergency_contact ? tt('daily_brief.emergency_contact', [brief.family.emergency_contact]) : ''}</Text>
        )}

        {brief?.jarvis_last_action && (
          <>
            <Text style={styles.section}>{tt('daily_brief.jarvis_handled_for_you')}</Text>
            <View style={styles.bigRow}>
              <Ionicons name="sparkles" size={26} color={C.brand} />
              <View style={{ flex: 1 }}>
                <Text style={styles.bigTitle}>{brief.jarvis_last_action.booked_slot ? tt('daily_brief.appointment', [brief.jarvis_last_action.booked_slot]) : tt('daily_brief.document_processed')}</Text>
                <Text style={styles.bigSub}>{brief.jarvis_last_action.doc_title}</Text>
              </View>
            </View>
          </>
        )}

        {brief?.recovery?.status === 'active' && (
          <Text style={styles.recovery}>{tt('daily_brief.active_sick_leave_until')} {brief.recovery.end_date || '—'} {tt('daily_brief.respect_your_outing_windows')}</Text>
        )}
        {brief && <Text style={styles.gat}>{tt('daily_brief.ga_t_zostatok')} {Number(brief.gat_balance).toFixed(1)}</Text>}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 15 },
  greet: { fontSize: 34, fontWeight: '900', color: C.fg, lineHeight: 42 },
  date: { marginTop: 6, fontSize: 15, color: C.onS3, textTransform: 'capitalize' },
  notifRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, marginTop: S.lg, backgroundColor: C.surface2, borderRadius: R.md, padding: S.md },
  notifText: { flex: 1, color: C.fg, fontWeight: '700', fontSize: 14 },
  section: { marginTop: S.xl, marginBottom: S.sm, fontSize: 13, letterSpacing: 1.5, color: C.brand, fontWeight: '900' },
  bigRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, backgroundColor: C.surface2, borderRadius: R.md, padding: S.lg, marginTop: S.sm, minHeight: 64 },
  bigTitle: { color: C.fg, fontWeight: '800', fontSize: 16, lineHeight: 21 },
  bigSub: { color: C.info, fontSize: 12.5, marginTop: 3 },
  bigTime: { color: C.brand, fontWeight: '900', fontSize: 18 },
  empty: { color: C.onS3, fontSize: 14, lineHeight: 20, marginTop: 4 },
  recovery: { marginTop: S.xl, color: C.error, fontWeight: '700', fontSize: 13 },
  gat: { marginTop: S.md, color: '#B8860B', fontWeight: '800', fontSize: 12 },
  err: { color: C.error, marginTop: S.md, fontSize: 13 },
});
