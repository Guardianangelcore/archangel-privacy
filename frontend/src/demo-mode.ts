/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// DEMO MODE — global toggle (AsyncStorage) + tiny pub/sub so the DEMO badge
// in the root layout reacts instantly to the Settings switch. Default: ON.
import { useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY = 'gh_demo_mode_v1';
let current = true;
const listeners = new Set<(v: boolean) => void>();

export async function initDemoMode(): Promise<boolean> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    current = raw === null ? true : raw === '1';
  } catch { current = true; }
  listeners.forEach(l => l(current));
  return current;
}

export function getDemoMode(): boolean { return current; }

export async function setDemoMode(v: boolean) {
  current = v;
  listeners.forEach(l => l(v));
  try { await AsyncStorage.setItem(KEY, v ? '1' : '0'); } catch {}
}

export function useDemoMode(): boolean {
  const [v, setV] = useState(current);
  useEffect(() => {
    const l = (nv: boolean) => setV(nv);
    listeners.add(l);
    initDemoMode();
    return () => { listeners.delete(l); };
  }, []);
  return v;
}
