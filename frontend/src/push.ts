import { Platform } from 'react-native';
import * as Notifications from 'expo-notifications';
import { API_BASE } from './api';

export async function registerForPush(user_id: string) {
  if (Platform.OS === 'web') return;
  try {
    const { status } = await Notifications.requestPermissionsAsync();
    if (status !== 'granted') return;
    const tokenResp = await Notifications.getDevicePushTokenAsync();
    await fetch(`${API_BASE}/api/register-push`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id, platform: Platform.OS, device_token: tokenResp.data }),
    });
  } catch (e) {
    // Expo Go has no native FCM/APNs token — works only in dev/production builds
    console.log('push register skipped', e);
  }
}
