/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// SYSTEM CAMERA with Android process-death recovery.
//
// Android may kill the app while the system camera is in the foreground. The activity is then
// recreated from scratch (navigation state lost → the user would land on the start/home screen)
// and the captured photo is only reachable through ImagePicker.getPendingResultAsync(). We remember
// which screen launched the camera so RootNav can put the user straight back there and the screen
// can pick the photo up with takeRecoveredAsset().
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as ImagePicker from 'expo-image-picker';

const KEY = 'camera.pendingRoute';
const MAX_AGE_MS = 15 * 60 * 1000;
let recovered: ImagePicker.ImagePickerAsset | null = null;

/** Drop-in replacement for ImagePicker.launchCameraAsync — `route` is the screen to return to. */
export async function launchCamera(route: string, options: ImagePicker.ImagePickerOptions): Promise<ImagePicker.ImagePickerResult> {
  const remember = Platform.OS === 'android';
  if (remember) await AsyncStorage.setItem(KEY, JSON.stringify({ route, at: Date.now() })).catch(() => {});
  try {
    return await ImagePicker.launchCameraAsync(options);
  } finally {
    if (remember) AsyncStorage.removeItem(KEY).catch(() => {});
  }
}

/** Cold start: the route to reopen when a camera launch was cut short by process death (else null). */
export async function restorePendingCamera(): Promise<string | null> {
  if (Platform.OS !== 'android') return null;
  try {
    const raw = await AsyncStorage.getItem(KEY);
    if (!raw) return null;
    await AsyncStorage.removeItem(KEY);
    const { route, at } = JSON.parse(raw);
    if (typeof route !== 'string' || Date.now() - Number(at) > MAX_AGE_MS) return null;
    const pending = await ImagePicker.getPendingResultAsync();
    const shot = pending && !('code' in pending) && !pending.canceled ? pending.assets?.[0] : null;
    recovered = shot ?? null;
    return route;
  } catch { return null; }
}

/** Screens call this on mount: the photo captured right before a process restart (once). */
export function takeRecoveredAsset(): ImagePicker.ImagePickerAsset | null {
  const a = recovered;
  recovered = null;
  return a;
}
