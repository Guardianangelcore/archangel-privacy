/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// ENTRY FLOW state — "has the user chosen a language yet?" Synchronous in memory (so the router
// guard never races the async storage write) and persisted for the next start.
import { useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

export const LANG_CHOSEN_KEY = 'ga.lang.chosen.v1';
let _chosen: boolean | null = null;
const _subs = new Set<(v: boolean) => void>();

export async function loadLangChosen(): Promise<boolean> {
  if (_chosen !== null) return _chosen;
  try { _chosen = !!(await AsyncStorage.getItem(LANG_CHOSEN_KEY)); } catch { _chosen = false; }
  return _chosen;
}

export function markLangChosen(lang: string) {
  _chosen = true;
  AsyncStorage.setItem(LANG_CHOSEN_KEY, lang).catch(() => {});
  _subs.forEach(f => { try { f(true); } catch {} });
}

/** null while loading, then true/false. */
export function useLangChosen(): boolean | null {
  const [v, setV] = useState<boolean | null>(_chosen);
  useEffect(() => {
    loadLangChosen().then(setV);
    _subs.add(setV);
    return () => { _subs.delete(setV); };
  }, []);
  return v;
}
