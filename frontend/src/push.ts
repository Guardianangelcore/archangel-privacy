/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import { Platform } from 'react-native';
import { getToken } from '@/src/api';
import { API_BASE } from './api';
import { getNotifications } from './notifications';

export async function registerForPush(user_id: string) {
  if (Platform.OS === 'web') return;
  try {
    const N = await getNotifications();
    if (!N) return;   // Expo Go / web — push works only in dev/production builds
    const { status } = await N.requestPermissionsAsync();
    if (status !== 'granted') return;
    const tokenResp = await N.getDevicePushTokenAsync();
    const tok = await getToken();
    await fetch(`${API_BASE}/api/register-push`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(tok ? { Authorization: `Bearer ${tok}` } : {}) },
      body: JSON.stringify({ user_id, platform: Platform.OS, device_token: tokenResp.data }),
    });
  } catch (e) {
    console.log('push register skipped', e);
  }
}
