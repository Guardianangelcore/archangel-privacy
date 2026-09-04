/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// SAFE NOTIFICATIONS LOADER — `expo-notifications` was removed from Expo Go (SDK 53+) and a
// static import hard-crashes the app at startup. This is the ONLY place the module is loaded:
// lazily, never inside Expo Go / web, and every failure degrades to "notifications off".
import { Platform } from 'react-native';
import Constants, { ExecutionEnvironment } from 'expo-constants';

export const isExpoGo =
  Constants.executionEnvironment === ExecutionEnvironment.StoreClient || Constants.appOwnership === 'expo';

/** True when local/push notifications can work at all (native dev/production build). */
export const notificationsAvailable = Platform.OS !== 'web' && !isExpoGo;

type NotificationsModule = typeof import('expo-notifications');
let _mod: NotificationsModule | null = null;
let _failed = false;

/** Resolve the module, or null when unavailable (Expo Go, web, load failure). Never throws. */
export async function getNotifications(): Promise<NotificationsModule | null> {
  if (!notificationsAvailable || _failed) return null;
  if (_mod) return _mod;
  try {
    _mod = await import('expo-notifications');
    return _mod;
  } catch (e) {
    _failed = true;
    console.warn('expo-notifications unavailable — notifications disabled', e);
    return null;
  }
}
