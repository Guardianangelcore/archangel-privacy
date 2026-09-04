/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { Platform, Linking } from 'react-native';
import { createURL } from 'expo-linking';
import * as WebBrowser from 'expo-web-browser';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { secureCacheSet, secureCacheGet, secureCacheRemove } from '@/src/secure-cache';
import { api, saveToken, getToken, clearToken } from './api';
import { LEGAL_VERSION } from './legal';
import type { Lang } from './i18n';

WebBrowser.maybeCompleteAuthSession();

const USER_CACHE_KEY = 'ga.user.cache.v2';   // SecureStore (Keychain/Keystore) — see src/secure-cache.ts
const LEGACY_USER_CACHE_KEY = 'ga.user.cache.v1';

export type User = {
  user_id: string;
  email: string;
  name?: string;
  picture?: string;
  did: string;
  language: Lang;
  angel_mode: boolean;
  birth_year?: number | null;
  biometric_enabled?: boolean;
  onboarding_completed?: boolean;
  tier?: string;
  [extra: string]: any;
};

type Ctx = {
  user: User | null;
  loading: boolean;
  authError: string | null;
  signIn: () => Promise<void>;
  signInDev: (email: string, name?: string) => Promise<void>;
  signInPassword: (email: string, password: string) => Promise<void>;
  registerPassword: (email: string, password: string, tosAccepted: boolean, name?: string) => Promise<void>;
  signOut: () => Promise<void>;
  refresh: () => Promise<void>;
  setUser: (u: User | null) => void;
};

const AuthCtx = createContext<Ctx | null>(null);

export function useAuth() {
  const c = useContext(AuthCtx);
  if (!c) throw new Error('useAuth must be inside AuthProvider');
  return c;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const handledIds = useRef<Set<string>>(new Set());

  const exchangeSessionId = useCallback(async (session_id: string): Promise<boolean> => {
    if (handledIds.current.has(session_id)) return false;
    handledIds.current.add(session_id);
    try {
      const res: any = await api('/auth/session', {
        method: 'POST',
        body: JSON.stringify({ session_id }),
      });
      await saveToken(res.session_token);
      setUser(res.user);
      setAuthError(null);
      return true;
    } catch (e: any) {
      console.log('session exchange failed', e);
      // Surface the failure — a silent logged-out state looks like "nothing happened".
      setAuthError('Google sign-in failed. Please try again, or use e-mail & password below.');
      return false;
    }
  }, []);

  const extractSessionId = (url: string | null): string | null => {
    if (!url) return null;
    const m = url.match(/[?#&]session_id=([^&#]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  };

  const refresh = useCallback(async () => {
    try {
      const tok = await getToken();
      if (!tok) { setUser(null); return; }
      const res: any = await api('/auth/me');
      setUser(res.user);
      secureCacheSet(USER_CACHE_KEY, res.user).catch(() => {});   // offline/blackout snapshot (encrypted at rest)
      AsyncStorage.removeItem(LEGACY_USER_CACHE_KEY).catch(() => {});   // purge the old plaintext copy
    } catch (e: any) {
      // Only clear the session on a real auth rejection — never on transient
      // network failures (offline, aborted request, server restart).
      const msg = String(e?.message || '');
      if (msg.startsWith('401') || msg.startsWith('403')) {
        await clearToken();
        setUser(null);
        secureCacheRemove(USER_CACHE_KEY).catch(() => {});
      } else {
        // BLACKOUT — no network at cold start: restore the last known profile so offline
        // features (cached Crisis Protocols, Blackout snapshot) stay reachable.
        try {
          const cached = await secureCacheGet<any>(USER_CACHE_KEY);
          if (cached) setUser(prev => prev ?? cached);
        } catch {}
      }
    }
  }, []);

  useEffect(() => {
    (async () => {
      // Web: check URL for session_id first
      if (Platform.OS === 'web') {
        try {
          const url = typeof window !== 'undefined' ? (window.location.hash + '&' + window.location.search) : '';
          const sid = extractSessionId(url);
          if (sid) {
            const ok = await exchangeSessionId(sid);
            // Clean the URL fragment only after the exchange SUCCEEDS.
            if (ok) {
              try {
                const u = new URL(window.location.href);
                u.hash = ''; u.searchParams.delete('session_id');
                window.history.replaceState(window.history.state, '', u.toString());
              } catch {}
            }
          }
        } catch {}
      } else {
        const initial = await Linking.getInitialURL();
        const sid = extractSessionId(initial);
        if (sid) await exchangeSessionId(sid);
      }
      await refresh();
      setLoading(false);
    })();

    if (Platform.OS !== 'web') {
      const sub = Linking.addEventListener('url', ({ url }) => {
        const sid = extractSessionId(url);
        if (sid) exchangeSessionId(sid);
      });
      return () => sub.remove();
    }
  }, [exchangeSessionId, refresh]);

  const signIn = useCallback(async () => {
    const redirect = Platform.OS === 'web'
      ? (typeof window !== 'undefined' ? window.location.origin + '/' : '')
      : createURL('');
    const authUrl = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirect)}`;

    if (Platform.OS === 'web') {
      if (typeof window !== 'undefined') window.location.href = authUrl;
      return;
    }
    let captured: string | null = null;
    const listener = Linking.addEventListener('url', ({ url }) => { captured = url; });
    try {
      const result = await WebBrowser.openAuthSessionAsync(authUrl, redirect);
      let url: string | null = null;
      if (result.type === 'success' && (result as any).url) url = (result as any).url;
      if (!url && captured) url = captured;
      if (!url) url = await Linking.getInitialURL();
      const sid = extractSessionId(url);
      if (sid) await exchangeSessionId(sid);
    } finally {
      listener.remove();
    }
  }, [exchangeSessionId]);

  const signOut = useCallback(async () => {
    secureCacheRemove(USER_CACHE_KEY).catch(() => {});
    AsyncStorage.removeItem(LEGACY_USER_CACHE_KEY).catch(() => {});
    try { await api('/auth/logout', { method: 'POST' }); } catch {}
    await clearToken();
    setUser(null);
  }, []);

  // Sovereign Bypass — Founder / preview builds only. Skips Google OAuth.
  const signInDev = useCallback(async (email: string, name?: string) => {
    const res: any = await api('/auth/dev-bypass', {
      method: 'POST',
      body: JSON.stringify({ email, name }),
    });
    await saveToken(res.session_token);
    setUser(res.user);
  }, []);

  // Classic e-mail & password auth (coexists with Google OAuth).
  const signInPassword = useCallback(async (email: string, password: string) => {
    const res: any = await api('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
    });
    await saveToken(res.session_token);
    setAuthError(null);
    setUser(res.user);
  }, []);

  const registerPassword = useCallback(async (email: string, password: string, tosAccepted: boolean, name?: string) => {
    // tos_accepted + tos_version become the user's GDPR consent receipt (server-timestamped).
    const res: any = await api('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email: email.trim().toLowerCase(), password, name,
        tos_accepted: tosAccepted, tos_version: LEGAL_VERSION }),
    });
    await saveToken(res.session_token);
    setAuthError(null);
    setUser(res.user);
  }, []);

  return (
    <AuthCtx.Provider value={{ user, loading, authError, signIn, signInDev, signInPassword, registerPassword, signOut, refresh, setUser }}>
      {children}
    </AuthCtx.Provider>
  );
}
