/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// NATIVE CALENDAR BRIDGE — shared helper for the dedicated on-device
// "Guardian Angel" calendar (used by /calendar-sync and Karta života).
import { Platform } from 'react-native';
import * as Calendar from 'expo-calendar';
import AsyncStorage from '@react-native-async-storage/async-storage';

const CAL_ID_KEY = 'gh_native_calendar_id_v1';

export async function ensureGuardianCalendar(): Promise<string> {
  const cached = await AsyncStorage.getItem(CAL_ID_KEY);
  if (cached) {
    try {
      const all = await Calendar.getCalendarsAsync(Calendar.EntityTypes.EVENT);
      if (all.some(c => c.id === cached)) return cached;
    } catch {}
  }
  const all = await Calendar.getCalendarsAsync(Calendar.EntityTypes.EVENT);
  const existing = all.find(c => c.title === 'Guardian Angel');
  if (existing) { await AsyncStorage.setItem(CAL_ID_KEY, existing.id); return existing.id; }
  const defaultCalendarSource = Platform.OS === 'ios'
    ? (await Calendar.getDefaultCalendarAsync()).source
    : { isLocalAccount: true, name: 'Guardian Angel', type: Calendar.SourceType.LOCAL } as any;
  const id = await Calendar.createCalendarAsync({
    title: 'Guardian Angel',
    color: '#D4AF37',
    entityType: Calendar.EntityTypes.EVENT,
    sourceId: (defaultCalendarSource as any).id,
    source: defaultCalendarSource as any,
    name: 'guardian-angel',
    ownerAccount: 'guardian-angel',
    accessLevel: Calendar.CalendarAccessLevel.OWNER,
  });
  await AsyncStorage.setItem(CAL_ID_KEY, id);
  return id;
}

// One-shot add (contextual permission ask — caller invokes only on explicit user intent).
export async function addToGuardianCalendar(title: string, dateISO: string, notes: string):
  Promise<{ ok: boolean; reason?: 'web' | 'denied' | 'blocked' | 'error' }> {
  if (Platform.OS === 'web') return { ok: false, reason: 'web' };
  try {
    let perm = await Calendar.getCalendarPermissionsAsync();
    if (perm.status !== 'granted' && perm.canAskAgain) {
      perm = await Calendar.requestCalendarPermissionsAsync();
    }
    if (perm.status !== 'granted') return { ok: false, reason: perm.canAskAgain ? 'denied' : 'blocked' };
    const calId = await ensureGuardianCalendar();
    const start = new Date(`${dateISO}T09:00:00`);
    const end = new Date(start.getTime() + 60 * 60 * 1000);
    await Calendar.createEventAsync(calId, {
      title, notes, startDate: start, endDate: end,
      alarms: [{ relativeOffset: -60 }],
    });
    return { ok: true };
  } catch {
    return { ok: false, reason: 'error' };
  }
}
