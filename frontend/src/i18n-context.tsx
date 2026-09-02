/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// I18N CONTEXT — single source of truth for the UI language.
// • `lang` flips IMMEDIATELY on setLang() (optimistic) so every screen using
//   useI18n() re-renders at once; the account preference is persisted in the
//   background (PATCH /me/prefs → setUser).
// • A language picked BEFORE login (login screen) is remembered on the device and
//   applied to the account the moment the user signs in.
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useAuth } from './auth';
import { api } from './api';
import { t as translate, tx as translateText, Lang, LANG_NAMES, isRTL, TVars } from './i18n';

const LANG_KEY = 'ga.lang.v1';            // last language shown on this device
const PENDING_KEY = 'ga.lang.pending.v1'; // picked while logged out → apply on sign-in

type I18nCtx = {
  lang: Lang;
  rtl: boolean;
  t: (key: string, vars?: TVars) => string;
  /** translate a backend-provided English text (tier features, taglines) when known */
  tx: (text: string | null | undefined) => string;
  setLang: (l: Lang) => Promise<void>;
};

const Ctx = createContext<I18nCtx | null>(null);

const isLang = (v: any): v is Lang => typeof v === 'string' && v in LANG_NAMES;

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const { user, setUser } = useAuth();
  const [lang, setLangState] = useState<Lang>(isLang(user?.language) ? (user!.language as Lang) : 'en');
  const pending = useRef<Lang | null>(null);

  // Boot: restore the last device language + any pre-login pick.
  useEffect(() => {
    (async () => {
      try {
        const [saved, pend] = await Promise.all([AsyncStorage.getItem(LANG_KEY), AsyncStorage.getItem(PENDING_KEY)]);
        if (isLang(pend)) pending.current = pend;
        if (!user && isLang(saved)) setLangState(saved);
      } catch {}
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Account loaded/changed → apply a pre-login pick once, otherwise follow the account.
  useEffect(() => {
    if (!user) return;
    const acct: Lang = isLang(user.language) ? user.language : 'en';
    const p = pending.current;
    if (p && p !== acct) {
      pending.current = null;
      AsyncStorage.removeItem(PENDING_KEY).catch(() => {});
      setLangState(p);
      api('/me/prefs', { method: 'PATCH', body: JSON.stringify({ language: p }) })
        .then((u: any) => setUser(u)).catch(() => {});
      return;
    }
    if (p) { pending.current = null; AsyncStorage.removeItem(PENDING_KEY).catch(() => {}); }
    setLangState(acct);
    AsyncStorage.setItem(LANG_KEY, acct).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.user_id, user?.language]);

  const setLang = useCallback(async (l: Lang) => {
    setLangState(l);                                   // instant re-render everywhere
    AsyncStorage.setItem(LANG_KEY, l).catch(() => {});
    if (!user) {
      pending.current = l;
      AsyncStorage.setItem(PENDING_KEY, l).catch(() => {});
      return;
    }
    try {
      const u: any = await api('/me/prefs', { method: 'PATCH', body: JSON.stringify({ language: l }) });
      setUser(u);
    } catch (e) {
      console.log('language persist failed', e);
    }
  }, [user, setUser]);

  const value = useMemo<I18nCtx>(() => ({
    lang,
    rtl: isRTL(lang),
    t: (key: string, vars?: TVars) => translate(key, lang, vars),
    tx: (text: string | null | undefined) => translateText(text, lang),
    setLang,
  }), [lang, setLang]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useI18n(): I18nCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error('useI18n must be inside I18nProvider');
  return c;
}
