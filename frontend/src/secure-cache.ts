/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// SECURE CACHE — sensitive offline snapshots (profile, emergency/blackout data, positions) live in the
// device Keychain / Keystore (expo-secure-store), never in plain AsyncStorage. iOS caps a single
// Keychain value at ~2 KB, so JSON is split into chunks under one namespace.
// Web has no Keychain → the storage layer falls back to AsyncStorage (index.web.ts).
import { storage } from '@/src/utils/storage';

const CHUNK = 1800;

export async function secureCacheSet(key: string, value: unknown): Promise<void> {
  const json = JSON.stringify(value);
  const parts = Math.max(1, Math.ceil(json.length / CHUNK));
  await secureCacheRemove(key);
  for (let i = 0; i < parts; i++) await storage.secureSet(`${key}.${i}`, json.slice(i * CHUNK, (i + 1) * CHUNK));
  await storage.secureSet(`${key}.n`, parts);
}

export async function secureCacheGet<T>(key: string): Promise<T | null> {
  const n = await storage.secureGet<number>(`${key}.n`, 0);
  if (!n) return null;
  let json = '';
  for (let i = 0; i < n; i++) {
    const part = await storage.secureGet<string>(`${key}.${i}`, '');
    if (!part) return null;
    json += part;
  }
  try { return JSON.parse(json) as T; } catch { return null; }
}

export async function secureCacheRemove(key: string): Promise<void> {
  const n = await storage.secureGet<number>(`${key}.n`, 0);
  for (let i = 0; i < (n || 0); i++) await storage.secureRemove(`${key}.${i}`);
  await storage.secureRemove(`${key}.n`);
}
