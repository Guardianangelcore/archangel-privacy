/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// Zero-Stutter Media Engine — pre-caches remote audio (TTS) to local storage before playback
import { Platform } from 'react-native';
import * as FileSystem from 'expo-file-system/legacy';
import { API_BASE, getToken } from './api';

const cache: Record<string, string> = {};

/** Returns a locally-cached URI for a backend audio path (e.g. /voice/tts/{id}).
 *  On web returns the authorized remote URL (browser streams + caches itself). */
export async function cachedAudioUri(apiPath: string): Promise<{ uri: string; headers?: Record<string, string> }> {
  const token = await getToken();
  const remote = `${API_BASE}/api${apiPath.replace(/^\/api/, '')}`;
  if (Platform.OS === 'web') {
    return { uri: remote, headers: token ? { Authorization: `Bearer ${token}` } : undefined };
  }
  if (cache[apiPath]) return { uri: cache[apiPath] };
  const name = apiPath.split('/').pop() || `a${Date.now()}`;
  const dest = `${FileSystem.cacheDirectory}tts_${name}.mp3`;
  try {
    const res = await FileSystem.downloadAsync(remote, dest, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    cache[apiPath] = res.uri;
    return { uri: res.uri };
  } catch {
    // fall back to direct streaming
    return { uri: remote, headers: token ? { Authorization: `Bearer ${token}` } : undefined };
  }
}
