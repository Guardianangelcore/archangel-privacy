import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { Platform, Linking } from 'react-native';
import * as WebBrowser from 'expo-web-browser';
import { api, saveToken, getToken, clearToken } from './api';
import type { Lang } from './i18n';

WebBrowser.maybeCompleteAuthSession();

export type User = {
  user_id: string;
  email: string;
  name?: string;
  picture?: string;
  did: string;
  language: Lang;
  angel_mode: boolean;
};

type Ctx = {
  user: User | null;
  loading: boolean;
  signIn: () => Promise<void>;
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
  const handledIds = useRef<Set<string>>(new Set());

  const exchangeSessionId = useCallback(async (session_id: string) => {
    if (handledIds.current.has(session_id)) return;
    handledIds.current.add(session_id);
    try {
      const res: any = await api('/auth/session', {
        method: 'POST',
        body: JSON.stringify({ session_id }),
      });
      await saveToken(res.session_token);
      setUser(res.user);
    } catch (e) {
      console.log('session exchange failed', e);
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
    } catch {
      await clearToken();
      setUser(null);
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
            await exchangeSessionId(sid);
            try {
              const u = new URL(window.location.href);
              u.hash = ''; u.searchParams.delete('session_id');
              window.history.replaceState(window.history.state, '', u.toString());
            } catch {}
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
      : Linking.createURL('');
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
    try { await api('/auth/logout', { method: 'POST' }); } catch {}
    await clearToken();
    setUser(null);
  }, []);

  return (
    <AuthCtx.Provider value={{ user, loading, signIn, signOut, refresh, setUser }}>
      {children}
    </AuthCtx.Provider>
  );
}
