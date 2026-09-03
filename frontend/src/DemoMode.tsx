/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// DEMO_ONLY — PAYMENT DEMO MODE banner for competition judges. Shows while `user.demo_until`
// is in the future: "DEMO MODE — Sovereign Access (mm:ss)". When the countdown reaches 0 the
// user is refreshed → backend already treats the session as expired → free tier restored.
// Remove together with backend/routes/demo_mode.py for production.
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useAuth } from './auth';
import { api } from './api';

export const DEMO_ONLY = true;

const fmt = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

export function DemoBanner() {
  const { user, refresh } = useAuth() as any;
  const insets = useSafeAreaInsets();
  const until = user?.demo_until ? new Date(user.demo_until).getTime() : 0;
  const [left, setLeft] = useState(0);

  useEffect(() => {
    if (!until) { setLeft(0); return; }
    const tick = () => {
      const s = Math.max(0, Math.floor((until - Date.now()) / 1000));
      setLeft(s);
      if (s === 0) { refresh?.(); }   // expired → real (free) tier again
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [until]);

  if (!until || left <= 0) return null;
  return (
    <View testID="demo-banner" style={[st.bar, { paddingTop: Math.max(insets.top, 6) }]}>
      <Ionicons name="flask-outline" size={14} color="#0B0B0D" />
      <Text style={st.text}>DEMO MODE — Sovereign Access ({fmt(left)})</Text>
      <Pressable testID="demo-stop" hitSlop={8} onPress={async () => { try { await api('/demo-mode/stop', { method: 'POST' }); } catch {} refresh?.(); }}>
        <Ionicons name="close-circle" size={16} color="#0B0B0D" />
      </Pressable>
    </View>
  );
}

/** DEMO_ONLY — start a 30-minute full-access session (no payment). Returns true on success. */
export async function startDemoMode(refresh?: () => Promise<any> | void): Promise<boolean> {
  try { await api('/demo-mode/start', { method: 'POST' }); await refresh?.(); return true; } catch { return false; }
}

const st = StyleSheet.create({
  bar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, backgroundColor: '#FFD60A', paddingBottom: 6, paddingHorizontal: 12 },
  text: { color: '#0B0B0D', fontWeight: '900', fontSize: 12, letterSpacing: 1 },
});
