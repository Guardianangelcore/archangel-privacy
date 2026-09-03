/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// Reusable premium paywall — Sentinel trial / GA-T micropayment / upgrade
import React, { useState } from 'react';
import { View, Text, StyleSheet, Pressable, ActivityIndicator } from 'react-native';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from './api';
import { C, S } from './theme';
import { IapBuyButton } from './IapPurchase';
import { startDemoMode } from './DemoMode';   // DEMO_ONLY
import { useAuth } from './auth';
import { useI18n } from '@/src/i18n-context';

type Props = {
  message: string;
  tier?: 'guardian' | 'sentinel';   // minimum plan being advertised (default Sentinel)
  gatLabel?: string;          // e.g. "PAY 5 GA-T PER SCAN"
  onPayGat?: () => void;      // retry with pay_gat
  onUnlocked: () => void;     // called after successful trial
};

const TIER_UI = {
  guardian: { title: 'GUARDIAN PLAN', color: '#B8860B', icon: 'shield-checkmark' as const, tiers: 'VIEW PLANS (GUARDIAN €9 / SENTINEL €149)' },
  sentinel: { title: 'SENTINEL EXCLUSIVE', color: '#E5E4E2', icon: 'diamond' as const, tiers: 'VIEW TIERS (SENTINEL €149 / ARCHANGEL €499)' },
};

export default function Paywall({ message, tier = 'sentinel', gatLabel, onPayGat, onUnlocked }: Props) {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const ui = TIER_UI[tier];
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const { refresh } = useAuth();
  // DEMO_ONLY — competition judges: 30-min full access without payment
  const demo = async () => { setBusy(true); const ok = await startDemoMode(refresh); setBusy(false); if (ok) onUnlocked(); else setErr('Demo mode unavailable'); };

  const trial = async () => {
    setBusy(true); setErr('');
    try {
      await api('/subscription/trial', { method: 'POST' });
      onUnlocked();
    } catch (e: any) {
      const m = String(e.message || e);
      setErr(m.includes('trial_used') ? 'The trial has already been used — continue with an upgrade or a GA-T payment.' : m);
    } finally { setBusy(false); }
  };

  return (
    <View testID="paywall" style={[st.box, { borderColor: ui.color }]}>
      <Ionicons name={ui.icon} size={30} color={ui.color} />
      <Text style={[st.title, { color: ui.color }]}>{tx(ui.title)}</Text>
      <Text style={st.msg}>{message}</Text>
      {!!err && <Text style={st.err}>{err}</Text>}
      <Pressable testID="pw-trial" onPress={trial} disabled={busy} style={st.trialBtn}>
        {busy ? <ActivityIndicator color="#0B0B0D" /> : <Text style={st.trialText}>{tt('c_Paywall.activate_a_free_7_day_trial')}</Text>}
      </Pressable>
      {/* Guardian plan → native App Store / Google Play subscription (RevenueCat); unlocks immediately after tier mirror */}
      <View style={{ alignSelf: 'stretch' }}>
        <IapBuyButton tier={tier} period="monthly" accent={ui.color} onSynced={(r) => { if (r && r.status !== 'noop' && r.status !== 'downgraded') onUnlocked(); }} />
      </View>
      {!!gatLabel && onPayGat && (
        <Pressable testID="pw-gat" onPress={onPayGat} style={st.gatBtn}>
          <Text style={st.gatText}>💎 {gatLabel}</Text>
        </Pressable>
      )}
      <Pressable testID="pw-upgrade" onPress={() => router.push('/subscription')} style={st.upBtn}>
        <Text style={st.upText}>{ui.tiers}</Text>
      </Pressable>
      {/* DEMO_ONLY */}
      <Pressable testID="pw-demo" onPress={demo} disabled={busy} style={st.demoBtn}>
        <Ionicons name="flask-outline" size={14} color="#FFD60A" />
        <Text style={st.demoText}>DEMO MODE · 30 MIN</Text>
      </Pressable>
    </View>
  );
}

const st = StyleSheet.create({
  box: { marginTop: S.lg, borderWidth: 2, borderColor: '#E5E4E2', backgroundColor: '#0B0B0D', padding: S.xl, alignItems: 'center', gap: S.sm },
  title: { color: '#E5E4E2', fontWeight: '900', letterSpacing: 3, fontSize: 13 },
  msg: { color: '#B9B9C0', fontSize: 12, lineHeight: 18, textAlign: 'center' },
  err: { color: C.error, fontSize: 11, fontWeight: '800', textAlign: 'center' },
  trialBtn: { alignSelf: 'stretch', backgroundColor: '#E5E4E2', paddingVertical: S.md, alignItems: 'center', minHeight: 48, justifyContent: 'center', marginTop: S.sm },
  trialText: { color: '#0B0B0D', fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  demoBtn: { alignSelf: 'stretch', flexDirection: 'row', gap: 6, borderWidth: 1, borderStyle: 'dashed', borderColor: '#FFD60A', paddingVertical: S.sm, alignItems: 'center', justifyContent: 'center', minHeight: 44 },
  demoText: { color: '#FFD60A', fontWeight: '900', letterSpacing: 1.5, fontSize: 11 },
  gatBtn: { alignSelf: 'stretch', borderWidth: 1.5, borderColor: '#B8860B', paddingVertical: S.md, alignItems: 'center', minHeight: 44, justifyContent: 'center' },
  gatText: { color: '#B8860B', fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  upBtn: { paddingVertical: S.sm, minHeight: 40, justifyContent: 'center' },
  upText: { color: '#8A8A93', fontWeight: '800', fontSize: 9.5, letterSpacing: 1 },
});
