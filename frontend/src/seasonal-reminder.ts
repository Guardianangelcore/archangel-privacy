/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// SEASONAL REMINDER — local yearly notifications (1 Mar · 1 Jun · 1 Sep · 1 Dec, 09:00):
// "Check your crisis protocols before <season>." Scheduled ONLY while at least one protocol is
// unfinished; all four are cancelled when everything is ticked. Localized via i18n keys.
import { Platform } from 'react-native';
import * as Notifications from 'expo-notifications';
import { t, Lang } from './i18n';

const CATEGORY = 'crisis-seasonal';
// month is 1-based (expo-notifications YEARLY trigger)
const SEASONS: { key: string; month: number }[] = [
  { key: 'spring', month: 3 },
  { key: 'summer', month: 6 },
  { key: 'autumn', month: 9 },
  { key: 'winter', month: 12 },
];

async function cancelAll() {
  const all = await Notifications.getAllScheduledNotificationsAsync();
  await Promise.all(all.filter(n => n.content?.data?.category === CATEGORY)
    .map(n => Notifications.cancelScheduledNotificationAsync(n.identifier)));
}

/** Re-sync the 4 yearly reminders with the current checklist state. Safe to call often. */
export async function syncSeasonalReminders(protocols: { progress: number }[], lang: Lang): Promise<'scheduled' | 'cancelled' | 'skipped'> {
  if (Platform.OS === 'web') return 'skipped';
  try {
    const unfinished = protocols.some(p => p.progress < 1);
    await cancelAll();
    if (!unfinished) return 'cancelled';
    let perm = await Notifications.getPermissionsAsync();
    if (!perm.granted && perm.canAskAgain) perm = await Notifications.requestPermissionsAsync();
    if (!perm.granted) return 'skipped';
    for (const s of SEASONS) {
      await Notifications.scheduleNotificationAsync({
        content: {
          title: t('crisis.crisis_protocols', lang),
          body: t(`crisis.seasonal_reminder_${s.key}`, lang),
          data: { category: CATEGORY, route: '/crisis-protocols', season: s.key },
          sound: 'default',
        },
        trigger: { type: Notifications.SchedulableTriggerInputTypes.YEARLY, month: s.month, day: 1, hour: 9, minute: 0 },
      });
    }
    return 'scheduled';
  } catch {
    return 'skipped';
  }
}
