/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import * as Application from 'expo-application';

const KEY = 'gh_session_token';
const DEVICE_KEY = 'gh_device_id';

// DEVICE FINGERPRINT — sent as X-Device-Id on every call (Community Help farming guard: help between
// accounts on the same device is never rewarded). Android ID / iOS vendor ID, else a persisted UUID.
let _deviceId: string | null = null;
function randomId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}-${Math.random().toString(36).slice(2, 12)}`;
}
export async function getDeviceId(): Promise<string> {
  if (_deviceId) return _deviceId;
  let id: string | null = null;
  try {
    if (Platform.OS === 'android') id = Application.getAndroidId();
    else if (Platform.OS === 'ios') id = await Application.getIosIdForVendorAsync();
  } catch {}
  if (!id) {
    try {
      if (Platform.OS === 'web') {
        id = localStorage.getItem(DEVICE_KEY);
        if (!id) { id = randomId(); localStorage.setItem(DEVICE_KEY, id); }
      } else {
        id = await SecureStore.getItemAsync(DEVICE_KEY);
        if (!id) { id = randomId(); await SecureStore.setItemAsync(DEVICE_KEY, id); }
      }
    } catch { id = randomId(); }
  }
  _deviceId = `${Platform.OS}-${id}`;
  return _deviceId;
}

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

/** Human-readable message from an `api()` error ("503: {"detail":"..."}" → "..."; HTML proxy pages → generic). */
export function errMsg(e: any): string {
  const m = String(e?.message || e);
  const status = /^(\d{3}):\s/.exec(m)?.[1];
  const body = status ? m.slice(status.length + 2) : m;
  try {
    const j = JSON.parse(body);
    if (j?.detail) return typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail);
  } catch {}
  if (/<html|<!doctype/i.test(body)) return `Server error (${status || 'network'}) — please try again in a moment.`;
  return m;
}

export async function api<T = any>(path: string, opts: RequestInit = {}): Promise<T> {
  const [token, deviceId] = await Promise.all([getToken(), getDeviceId()]);
  const headers: any = { 'Content-Type': 'application/json', 'X-Device-Id': deviceId, ...(opts.headers || {}) };
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
  const [token, deviceId] = await Promise.all([getToken(), getDeviceId()]);
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
    headers: { 'X-Device-Id': deviceId, ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: form,
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return await res.json();
}
