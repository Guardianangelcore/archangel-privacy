import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

const KEY = 'gh_session_token';

export async function saveToken(token: string) {
  if (Platform.OS === 'web') {
    try { localStorage.setItem(KEY, token); } catch {}
  } else {
    await SecureStore.setItemAsync(KEY, token);
  }
}
export async function getToken(): Promise<string | null> {
  if (Platform.OS === 'web') {
    try { return localStorage.getItem(KEY); } catch { return null; }
  }
  return await SecureStore.getItemAsync(KEY);
}
export async function clearToken() {
  if (Platform.OS === 'web') {
    try { localStorage.removeItem(KEY); } catch {}
  } else {
    await SecureStore.deleteItemAsync(KEY);
  }
}

export const API_BASE = process.env.EXPO_PUBLIC_BACKEND_URL;

export async function api<T = any>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = await getToken();
  const headers: any = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}/api${path}`, { ...opts, headers });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`${res.status}: ${txt}`);
  }
  const ct = res.headers.get('content-type') || '';
  return ct.includes('json') ? await res.json() : (await res.text() as any);
}

export async function apiUpload(path: string, uri: string, name: string, type: string, extra: Record<string, string> = {}) {
  const token = await getToken();
  const form = new FormData();
  if (Platform.OS === 'web') {
    const blob = await (await fetch(uri)).blob();
    form.append('file', blob, name);
  } else {
    form.append('file', { uri, name, type } as any);
  }
  for (const [k, v] of Object.entries(extra)) form.append(k, v);
  const res = await fetch(`${API_BASE}/api${path}`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return await res.json();
}
