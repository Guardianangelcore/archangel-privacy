/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// Reusable premium paywall — Sentinel trial / GA-T micropayment / upgrade
import React, { useState } from 'react';
import { View, Text, StyleSheet, Pressable, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from './api';
import { C, S } from './theme';
import { IapBuyButton } from './IapPurchase';

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
  const router = useRouter();
  const ui = TIER_UI[tier];
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

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
      <Text style={[st.title, { color: ui.color }]}>{ui.title}</Text>
      <Text style={st.msg}>{message}</Text>
      {!!err && <Text style={st.err}>{err}</Text>}
      <Pressable testID="pw-trial" onPress={trial} disabled={busy} style={st.trialBtn}>
        {busy ? <ActivityIndicator color="#0B0B0D" /> : <Text style={st.trialText}>ACTIVATE A FREE 7-DAY TRIAL</Text>}
      </Pressable>
      {/* Guardian plan → native App Store / Google Play subscription (RevenueCat); unlocks immediately after tier mirror */}
      {tier === 'guardian' && (
        <View style={{ alignSelf: 'stretch' }}>
          <IapBuyButton period="monthly" accent={ui.color} onSynced={(r) => { if (r && r.status !== 'noop' && r.status !== 'downgraded') onUnlocked(); }} />
        </View>
      )}
      {!!gatLabel && onPayGat && (
        <Pressable testID="pw-gat" onPress={onPayGat} style={st.gatBtn}>
          <Text style={st.gatText}>💎 {gatLabel}</Text>
        </Pressable>
      )}
      <Pressable testID="pw-upgrade" onPress={() => router.push('/subscription')} style={st.upBtn}>
        <Text style={st.upText}>{ui.tiers}</Text>
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
  gatBtn: { alignSelf: 'stretch', borderWidth: 1.5, borderColor: '#B8860B', paddingVertical: S.md, alignItems: 'center', minHeight: 44, justifyContent: 'center' },
  gatText: { color: '#B8860B', fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  upBtn: { paddingVertical: S.sm, minHeight: 40, justifyContent: 'center' },
  upText: { color: '#8A8A93', fontWeight: '800', fontSize: 9.5, letterSpacing: 1 },
});
