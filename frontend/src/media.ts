/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// Zero-Stutter Media Engine — pre-caches remote audio (TTS) & video to local storage
import { Platform } from 'react-native';
import * as FileSystem from 'expo-file-system/legacy';
import { API_BASE, getToken } from './api';

const cache: Record<string, string> = {};
const vcache: Record<string, string> = {};

/** Instant lookup: returns the locally-cached file URI for a video if prefetched, else the remote URL. */
export function cachedVideo(url: string): string {
  return vcache[url] || url;
}

/** Background prefetch of a guide video to local cache (native only — web streams + HTTP-caches itself). */
export async function prefetchVideo(url: string): Promise<void> {
  if (!url || Platform.OS === 'web' || vcache[url]) return;
  const name = (url.split('/').pop() || `v${Date.now()}`).replace(/[^a-zA-Z0-9._-]/g, '');
  const dest = `${FileSystem.cacheDirectory}vid_${name}`;
  try {
    const info = await FileSystem.getInfoAsync(dest);
    if (info.exists && (info as any).size > 0) { vcache[url] = dest; return; }
    const res = await FileSystem.downloadAsync(url, dest);
    if (res.status === 200) vcache[url] = res.uri;
  } catch {}
}

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
