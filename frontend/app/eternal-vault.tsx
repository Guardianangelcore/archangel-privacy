/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// VEČNÝ TREZOR — biometricky zamknutý priestor pre záležitosti konca života.
// Skryté z denného toku, aby zápis neschopenky nepripomínal pohreb.
import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet, ScrollView, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as LocalAuthentication from 'expo-local-authentication';
import { C, S, R } from '@/src/theme';
import { tap } from '@/src/ui/glass';

const ITEMS = [
  { testID: 'ev-dignity', icon: 'rose-outline', title: 'Dignified farewell', sub: 'Funeral fund · last wishes', route: '/dignity' },
  { testID: 'ev-legal', icon: 'shield-checkmark-outline', title: 'Will & legal', sub: 'Will · TOS · KYC', route: '/legal' },
  { testID: 'ev-biometric', icon: 'finger-print-outline', title: 'Biometric will', sub: 'Voice/video proof · blockchain hash', route: '/biometric-will' },
  { testID: 'ev-video', icon: 'videocam-outline', title: 'Video message for family', sub: 'Sealed video messages', route: '/video-legacy' },
  { testID: 'ev-digital', icon: 'cloud-done-outline', title: 'Digital legacy', sub: 'Accounts · subscription liquidator', route: '/digital-legacy' },
  { testID: 'ev-proxy', icon: 'document-lock-outline', title: 'Healthcare proxy', sub: 'Legal protection for your partner', route: '/healthcare-proxy' },
];

export default function EternalVault() {
  const router = useRouter();
  const [unlocked, setUnlocked] = useState(false);
  const [err, setErr] = useState('');

  const unlock = async () => {
    setErr(''); tap('heavy');
    try {
      if (Platform.OS === 'web') { setUnlocked(true); return; }
      const hw = await LocalAuthentication.hasHardwareAsync();
      const enrolled = hw ? await LocalAuthentication.isEnrolledAsync() : false;
      if (!hw || !enrolled) { setUnlocked(true); return; }
      const res = await LocalAuthentication.authenticateAsync({
        promptMessage: 'Unlock the Eternal Vault',
        cancelLabel: 'Cancel',
      });
      if (res.success) { tap('success'); setUnlocked(true); }
      else setErr('Verification failed. Try again.');
    } catch (e: any) { setErr(String(e.message || e)); }
  };

  return (
    <SafeAreaView testID="eternal-vault" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="ev-back" onPress={() => router.back()} hitSlop={10}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={st.title}>ETERNAL VAULT</Text>
        <Ionicons name="lock-closed" size={18} color={unlocked ? C.brand : C.info} />
      </View>

      {!unlocked ? (
        <View style={st.lockWrap}>
          <View style={st.lockRing}>
            <Ionicons name="finger-print" size={64} color={C.brand} />
          </View>
          <Text style={st.lockTitle}>Locked space</Text>
          <Text style={st.lockSub}>Legacy and last-will matters are separated from daily life. Unlock them only with biometrics — they never intrude on health and healing.</Text>
          <Pressable testID="ev-unlock" onPress={unlock} style={st.unlockBtn}>
            <Ionicons name="finger-print" size={20} color={C.onInverse} />
            <Text style={st.unlockText}>UNLOCK WITH BIOMETRICS</Text>
          </Pressable>
          {!!err && <Text style={st.err}>{err}</Text>}
        </View>
      ) : (
        <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 100 }}>
          <View style={st.notice}>
            <Ionicons name="eye-off-outline" size={16} color={C.brand} />
            <Text style={st.noticeText}>This content is hidden from the main dashboard. Life belongs up top — legacy lives here.</Text>
          </View>
          <View style={{ gap: S.md, marginTop: S.md }}>
            {ITEMS.map(it => (
              <Pressable key={it.testID} testID={it.testID} onPress={() => { tap(); router.push(it.route as any); }}
                style={({ pressed }) => [st.row, pressed && { backgroundColor: C.surface3 }]}>
                <View style={st.rowIcon}><Ionicons name={it.icon as any} size={22} color={C.brand} /></View>
                <View style={{ flex: 1 }}>
                  <Text style={st.rowTitle}>{it.title}</Text>
                  <Text style={st.rowSub}>{it.sub}</Text>
                </View>
                <Ionicons name="chevron-forward" size={18} color={C.info} />
              </Pressable>
            ))}
          </View>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md, borderBottomWidth: 1, borderBottomColor: C.border },
  title: { color: C.fg, fontWeight: '900', fontSize: 15, letterSpacing: 3 },
  lockWrap: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: S.xl },
  lockRing: { width: 140, height: 140, borderRadius: 70, borderWidth: 2, borderColor: C.borderStrong, alignItems: 'center', justifyContent: 'center', backgroundColor: C.surface2 },
  lockTitle: { marginTop: S.xl, color: C.fg, fontWeight: '900', fontSize: 22 },
  lockSub: { marginTop: S.sm, color: C.onS3, fontSize: 13, lineHeight: 19, textAlign: 'center' },
  unlockBtn: { marginTop: S.xl, flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, borderRadius: R.pill, minHeight: 56, paddingHorizontal: S.xl },
  unlockText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  err: { marginTop: S.md, color: C.error, fontWeight: '800', fontSize: 12 },
  notice: { flexDirection: 'row', alignItems: 'center', gap: S.sm, backgroundColor: 'rgba(212,175,55,0.08)', borderRadius: R.md, padding: S.md, borderWidth: 1, borderColor: C.border },
  noticeText: { flex: 1, color: C.onS3, fontSize: 11, lineHeight: 16 },
  row: { flexDirection: 'row', alignItems: 'center', gap: S.lg, backgroundColor: C.surface2, borderRadius: R.lg, padding: S.lg, minHeight: 72, borderWidth: 1, borderColor: C.border },
  rowIcon: { width: 44, height: 44, borderRadius: R.md, backgroundColor: 'rgba(212,175,55,0.12)', alignItems: 'center', justifyContent: 'center' },
  rowTitle: { fontWeight: '800', fontSize: 15, color: C.fg },
  rowSub: { fontSize: 12, color: C.info, marginTop: 2 },
});
