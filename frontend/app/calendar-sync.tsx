/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// CALENDAR SYNC — local-first bridge to the native device calendar.
// Reads upcoming meds + Waitlist exams from the Guardian backend, then writes
// them into a dedicated on-device "Guardian Angel" calendar (read + write).
// Follows the handle_permissions_contract: contextual, canAskAgain-aware, "Open Settings" fallback.
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, ActivityIndicator, Platform, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as Calendar from 'expo-calendar';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { api } from '@/src/api';
import { ensureGuardianCalendar } from '@/src/native-calendar';
import { C, S, R } from '@/src/theme';
import { tap } from '@/src/ui/glass';

const SYNCED_KEY = 'gh_native_calendar_synced_v1';

type SyncedMap = Record<string, string>; // guardian-key -> native event id

async function getSynced(): Promise<SyncedMap> {
  try { const raw = await AsyncStorage.getItem(SYNCED_KEY); return raw ? JSON.parse(raw) : {}; } catch { return {}; }
}
async function saveSynced(m: SyncedMap) { try { await AsyncStorage.setItem(SYNCED_KEY, JSON.stringify(m)); } catch {} }

type Item = {
  key: string;
  kind: 'med' | 'exam';
  title: string;
  subtitle: string;
  startISO: string;
  endISO: string;
  notes: string;
};

function buildTodayMedsItems(meds: any[]): Item[] {
  const today = new Date();
  const y = today.getFullYear(), mo = today.getMonth(), d = today.getDate();
  const out: Item[] = [];
  meds.forEach(m => {
    (m.times || []).forEach((t: string) => {
      const [h, mm] = t.split(':').map((x: string) => parseInt(x, 10));
      if (isFinite(h) && isFinite(mm)) {
        const start = new Date(y, mo, d, h, mm, 0);
        const end = new Date(start.getTime() + 10 * 60 * 1000);
        out.push({
          key: `med-${m.reminder_id || m.name}-${t}`,
          kind: 'med',
          title: `💊 ${m.name}${m.dose ? ` (${m.dose})` : ''}`,
          subtitle: `Liek · ${t}`,
          startISO: start.toISOString(),
          endISO: end.toISOString(),
          notes: `Guardian Angel · Sovereign Protocol${m.dose ? `\nDávka: ${m.dose}` : ''}`,
        });
      }
    });
  });
  return out;
}

function buildExamsItems(events: any[]): Item[] {
  return events.map(e => {
    const start = new Date(`${e.date}T09:00:00`);
    const end = new Date(start.getTime() + 60 * 60 * 1000);
    return {
      key: `exam-${e.event_id || e.date}-${e.title}`,
      kind: 'exam' as const,
      title: `📅 ${e.title}`,
      subtitle: `Vyšetrenie · ${e.date}`,
      startISO: start.toISOString(),
      endISO: end.toISOString(),
      notes: `Guardian Angel · Sovereign Protocol\n${e.notes || ''}`,
    };
  });
}

export default function CalendarSync() {
  const router = useRouter();
  const [permStatus, setPermStatus] = useState<'undetermined' | 'granted' | 'denied' | 'blocked'>('undetermined');
  const [items, setItems] = useState<Item[]>([]);
  const [synced, setSynced] = useState<SyncedMap>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [nativeUpcoming, setNativeUpcoming] = useState<Calendar.Event[]>([]);

  const loadSourceItems = useCallback(async () => {
    try {
      // Bring meds + upcoming exams from the Guardian backend
      const [meds, list]: any = await Promise.all([
        api('/meds/reminders').catch(() => []),
        api('/waitlist').catch(() => []),
      ]);
      const medItems = buildTodayMedsItems(Array.isArray(meds) ? meds : (meds?.reminders || []));
      const exams = (Array.isArray(list) ? list : []).filter((w: any) => w.status === 'booked' && w.target_before).map((w: any) => ({
        event_id: w.item_id, title: w.specialty || w.title, date: w.target_before, notes: w.clinic || '',
      }));
      setItems([...medItems, ...buildExamsItems(exams)]);
    } catch (e: any) { setErr(String(e.message || e)); }
  }, []);

  const askPermission = async (): Promise<boolean> => {
    if (Platform.OS === 'web') { setErr('Kalendár je dostupný len na mobilnom zariadení.'); return false; }
    const cur = await Calendar.getCalendarPermissionsAsync();
    let status = cur.status; let canAskAgain = cur.canAskAgain;
    if (status !== 'granted') {
      if (!canAskAgain) { setPermStatus('blocked'); return false; }
      const r = await Calendar.requestCalendarPermissionsAsync();
      status = r.status; canAskAgain = r.canAskAgain;
      if (status !== 'granted') { setPermStatus(canAskAgain ? 'denied' : 'blocked'); return false; }
    }
    setPermStatus('granted');
    return true;
  };

  const refreshNative = useCallback(async () => {
    try {
      const ok = permStatus === 'granted' || (await askPermission());
      if (!ok) return;
      const calId = await ensureGuardianCalendar();
      const start = new Date();
      const end = new Date(start.getTime() + 30 * 24 * 3600 * 1000);
      const rows = await Calendar.getEventsAsync([calId], start, end);
      setNativeUpcoming(rows);
    } catch {}
  }, [permStatus]);

  useEffect(() => {
    loadSourceItems();
    (async () => setSynced(await getSynced()))();
  }, [loadSourceItems]);

  useEffect(() => { if (permStatus === 'granted') refreshNative(); }, [permStatus, refreshNative]);

  const syncOne = async (it: Item) => {
    setErr(''); setMsg(''); tap('medium');
    const ok = await askPermission();
    if (!ok) return;
    setBusy(it.key);
    try {
      const calId = await ensureGuardianCalendar();
      const eventId = await Calendar.createEventAsync(calId, {
        title: it.title, notes: it.notes,
        startDate: new Date(it.startISO), endDate: new Date(it.endISO),
        alarms: [{ relativeOffset: -10 }],
        timeZone: undefined,
      });
      const next = { ...synced, [it.key]: eventId };
      setSynced(next); await saveSynced(next);
      setMsg(`✅ Pridané do kalendára: ${it.title}`);
      await refreshNative();
      tap('success');
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const removeOne = async (it: Item) => {
    setErr(''); setMsg('');
    const nativeId = synced[it.key];
    if (!nativeId) return;
    setBusy(`del-${it.key}`);
    try {
      try { await Calendar.deleteEventAsync(nativeId); } catch {}
      const next = { ...synced }; delete next[it.key];
      setSynced(next); await saveSynced(next);
      setMsg(`Odstránené z kalendára: ${it.title}`);
      await refreshNative();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const syncAll = async () => {
    const ok = await askPermission(); if (!ok) return;
    setBusy('all'); setErr(''); setMsg('');
    try {
      const calId = await ensureGuardianCalendar();
      const next: SyncedMap = { ...synced };
      let added = 0;
      for (const it of items) {
        if (next[it.key]) continue;
        const id = await Calendar.createEventAsync(calId, {
          title: it.title, notes: it.notes,
          startDate: new Date(it.startISO), endDate: new Date(it.endISO),
          alarms: [{ relativeOffset: -10 }],
        });
        next[it.key] = id; added += 1;
      }
      setSynced(next); await saveSynced(next);
      setMsg(`✅ Synchronizovaných ${added} udalostí do kalendára Guardian Angel.`);
      await refreshNative();
      tap('success');
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const remaining = items.filter(i => !synced[i.key]).length;

  return (
    <SafeAreaView testID="cal-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="cal-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.fg} />
        </Pressable>
        <Text style={st.title}>NATÍVNY KALENDÁR</Text>
        <Pressable testID="cal-refresh" onPress={() => { loadSourceItems(); refreshNative(); }} hitSlop={12}>
          <Ionicons name="refresh" size={22} color={C.fg} />
        </Pressable>
      </View>

      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        <Text style={st.tag}>LOKÁLNY MOST · ČÍTA A ZAPISUJE DO KALENDÁRA VÁŠHO TELEFÓNU</Text>

        {permStatus !== 'granted' && (
          <View style={st.card}>
            <Text style={st.cardTitle}>POVOLENIE KALENDÁRA</Text>
            <Text style={st.explain}>
              Guardian Angel potrebuje jednorazový prístup k vášmu kalendáru, aby zobrazoval a pridával
              pripomienky liekov a termíny vyšetrení. Dáta zostávajú vo vašom telefóne v samostatnom
              kalendári „Guardian Angel“.
            </Text>
            <Pressable testID="cal-perm" onPress={askPermission} style={st.primaryBtn}>
              <Ionicons name="calendar" size={18} color={C.onInverse} />
              <Text style={st.primaryText}>POVOLIŤ KALENDÁR</Text>
            </Pressable>
            {permStatus === 'blocked' && (
              <Pressable testID="cal-settings" onPress={() => Linking.openSettings()} style={st.warnBtn}>
                <Text style={st.warnBtnText}>KALENDÁR JE ZABLOKOVANÝ — OTVORIŤ NASTAVENIA</Text>
              </Pressable>
            )}
          </View>
        )}

        {/* Native upcoming events preview (read) */}
        {permStatus === 'granted' && (
          <View style={st.card}>
            <Text style={st.cardTitle}>NAJBLIŽŠIE UDALOSTI (30 DNÍ)</Text>
            {nativeUpcoming.length === 0
              ? <Text style={st.empty}>Guardian Angel kalendár je zatiaľ prázdny.</Text>
              : nativeUpcoming.slice(0, 10).map((e) => (
                <View key={e.id} style={st.row}>
                  <Ionicons name="calendar-clear-outline" size={16} color={C.brand} />
                  <View style={{ flex: 1 }}>
                    <Text style={st.rowName}>{e.title}</Text>
                    <Text style={st.rowSub}>{new Date(e.startDate as any).toLocaleString('sk-SK')}</Text>
                  </View>
                </View>
              ))}
          </View>
        )}

        {/* Items to sync */}
        <View style={st.card}>
          <View style={st.cardHead}>
            <Text style={st.cardTitle}>NA SYNCHRONIZÁCIU</Text>
            <Text style={st.cardMeta}>{remaining}/{items.length}</Text>
          </View>
          {items.length === 0 && <Text style={st.empty}>Žiadne položky. Pridajte lieky alebo termíny v aplikácii.</Text>}
          {items.length > 0 && (
            <Pressable testID="cal-sync-all" onPress={syncAll} disabled={busy === 'all' || remaining === 0} style={[st.primaryBtn, remaining === 0 && { opacity: 0.5 }]}>
              {busy === 'all' ? <ActivityIndicator color={C.onInverse} /> : (
                <>
                  <Ionicons name="sync" size={18} color={C.onInverse} />
                  <Text style={st.primaryText}>SYNCHRONIZOVAŤ VŠETKY ({remaining})</Text>
                </>
              )}
            </Pressable>
          )}
          {items.map(it => {
            const isSynced = !!synced[it.key];
            const rowBusy = busy === it.key || busy === `del-${it.key}`;
            return (
              <View key={it.key} style={st.itemRow}>
                <View style={{ flex: 1 }}>
                  <Text style={st.rowName}>{it.title}</Text>
                  <Text style={st.rowSub}>{it.subtitle}</Text>
                </View>
                {rowBusy ? <ActivityIndicator color={C.brand} /> : isSynced ? (
                  <Pressable testID={`cal-del-${it.key}`} onPress={() => removeOne(it)} style={st.iconBtn}>
                    <Ionicons name="checkmark-circle" size={22} color={C.brand} />
                  </Pressable>
                ) : (
                  <Pressable testID={`cal-add-${it.key}`} onPress={() => syncOne(it)} style={st.iconBtn}>
                    <Ionicons name="add-circle-outline" size={22} color={C.brand} />
                  </Pressable>
                )}
              </View>
            );
          })}
        </View>

        {!!msg && <Text testID="cal-msg" style={st.msg}>{msg}</Text>}
        {!!err && <Text testID="cal-err" style={st.err}>{err}</Text>}
        <Text style={st.footer}>Kalendár Guardian Angel je samostatný v natívnom kalendári zariadenia. Kedykoľvek ho môžete zrušiť aj tam.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.brand, fontSize: 18, fontWeight: '900', letterSpacing: 3 },
  tag: { color: C.info, fontSize: 10, letterSpacing: 1.5, fontWeight: '800', textAlign: 'center' },
  card: { marginTop: S.md, borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.sm, padding: S.md, backgroundColor: C.surface2 },
  cardHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  cardTitle: { color: C.brand, fontSize: 12, letterSpacing: 2, fontWeight: '900' },
  cardMeta: { color: C.info, fontSize: 11, fontWeight: '800' },
  empty: { color: C.info, fontSize: 12, fontStyle: 'italic', marginTop: 6 },
  explain: { color: C.onS3, fontSize: 12.5, lineHeight: 19, marginTop: 6 },
  primaryBtn: { flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, minHeight: 50, borderRadius: R.pill, marginTop: S.md, paddingHorizontal: 12 },
  primaryText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  warnBtn: { marginTop: S.sm, minHeight: 48, alignItems: 'center', justifyContent: 'center', borderRadius: R.sm, backgroundColor: C.warn },
  warnBtnText: { color: C.onWarn, fontWeight: '900', fontSize: 11, letterSpacing: 0.5 },
  row: { flexDirection: 'row', gap: 10, alignItems: 'center', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: 'rgba(212,175,55,0.10)' },
  itemRow: { flexDirection: 'row', gap: 10, alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: 'rgba(212,175,55,0.10)' },
  iconBtn: { padding: 4 },
  rowName: { color: C.fg, fontSize: 14, fontWeight: '700' },
  rowSub: { color: C.info, fontSize: 11, marginTop: 2 },
  msg: { color: C.brand, fontWeight: '800', fontSize: 12.5, marginTop: S.md, lineHeight: 18 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginTop: S.md, textAlign: 'center' },
  footer: { color: C.info, fontSize: 10, lineHeight: 15, marginTop: S.lg, textAlign: 'center' },
});
