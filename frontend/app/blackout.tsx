/* Copyright © 2026 Guardian Angel. All Rights Reserved. This source code and its logic are the sole property of Guardian Angel. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, ActivityIndicator, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';

const KEY = 'gh_blackout_snapshot';

export default function Blackout() {
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const router = useRouter();
  const [snap, setSnap] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const cached = await AsyncStorage.getItem(KEY);
      if (cached) { setSnap(JSON.parse(cached)); setSaved(JSON.parse(cached).generated_at); }
    })();
  }, []);

  const refresh = async () => {
    setLoading(true);
    try {
      const s = await api('/blackout/snapshot');
      setSnap(s); setSaved((s as any).generated_at);
      await AsyncStorage.setItem(KEY, JSON.stringify(s));
    } catch (e) { console.log(e); }
    setLoading(false);
  };

  return (
    <SafeAreaView testID="blackout-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="bo-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={styles.title}>BLACKOUT PROTOCOL</Text>
        <View style={{ width: 26 }} />
      </View>

      <View style={styles.banner}><Text style={styles.bannerText}>MOCKED · BLE MESH DEFERRED · SNAPSHOT WORKS</Text></View>

      <ScrollView contentContainerStyle={{ padding: S.lg }}>
        <View style={styles.hero}>
          <Ionicons name="flash-off" size={40} color={C.onInverse} />
          <Text style={styles.heroText}>SURVIVAL MODE READY</Text>
          <Text style={styles.heroSub}>Sync a signed snapshot to survive internet loss. In the future the phone will exchange it over Bluetooth mesh with nearby Guardian devices.</Text>
        </View>

        <Pressable testID="bo-refresh" onPress={refresh} disabled={loading} style={styles.refreshBtn}>
          {loading ? <ActivityIndicator color={C.onInverse} /> : <>
            <Ionicons name="cloud-download-outline" size={18} color={C.onInverse} />
            <Text style={styles.refreshText}>SYNC SNAPSHOT NOW</Text>
          </>}
        </Pressable>

        {saved && <Text style={styles.saved}>{t('snapshot_saved', lang).toUpperCase()} · {saved.slice(0, 19).replace('T', ' ')}</Text>}

        {snap && (
          <View style={{ marginTop: S.lg, gap: S.md }}>
            <Section title="IDENTITY">
              <Row lbl="NAME" val={snap.user?.name || snap.user?.email} />
              <Row lbl="DID" val={snap.user?.did} mono />
            </Section>
            <Section title="EMERGENCY PROFILE">
              <Row lbl="BLOOD" val={snap.emergency_profile?.blood_type || '—'} />
              <Row lbl="ALLERGIES" val={snap.emergency_profile?.allergies || '—'} />
              <Row lbl="MEDS" val={snap.emergency_profile?.medications || '—'} />
              <Row lbl="CONDITIONS" val={snap.emergency_profile?.conditions || '—'} />
            </Section>
            <Section title="CONTACT">
              <Row lbl="NAME" val={snap.emergency_profile?.emergency_contact_name || '—'} />
              <Row lbl="PHONE" val={snap.emergency_profile?.emergency_contact_phone || '—'} />
            </Section>
            <Section title="DOCUMENTS CACHED">
              {(snap.documents_meta || []).slice(0, 10).map((d: any) => (
                <Row key={d.doc_id} lbl={d.title.toUpperCase()} val={`${Math.round(d.size/1024)} KB`} />
              ))}
            </Section>
            <Section title="SURVIVAL TIPS">
              {(snap.survival_tips || []).map((s: string, i: number) => (
                <Text key={i} style={styles.tip}>{'•  '}{s}</Text>
              ))}
            </Section>
            <Section title="MESH STATUS">
              <View style={styles.meshRow}>
                <View style={styles.meshDot} />
                <Text style={styles.meshText}>BLE MESH SIMULATOR · 0 PEERS DISCOVERED (MOCKED)</Text>
              </View>
            </Section>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function Section({ title, children }: any) { return (<View style={styles.section}><Text style={styles.sectionTitle}>{title}</Text><View style={styles.sectionBody}>{children}</View></View>); }
function Row({ lbl, val, mono }: any) { return (<View style={styles.rowKV}><Text style={styles.rowLbl}>{lbl}</Text><Text style={[styles.rowVal, mono && styles.mono]}>{val}</Text></View>); }

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  banner: { backgroundColor: C.warn, paddingVertical: 6, alignItems: 'center' },
  bannerText: { color: C.onWarn, fontWeight: '900', letterSpacing: 2, fontSize: 10 },
  hero: { backgroundColor: C.inverse, padding: S.xl, alignItems: 'center', gap: S.sm, borderWidth: 2, borderColor: C.borderStrong },
  heroText: { color: C.onInverse, fontWeight: '900', letterSpacing: 3, fontSize: 18 },
  heroSub: { color: C.onInverse, opacity: 0.8, fontSize: 13, textAlign: 'center', lineHeight: 18 },
  refreshBtn: { marginTop: S.lg, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, paddingVertical: S.lg, borderWidth: 2, borderColor: C.borderStrong },
  refreshText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 14 },
  saved: { marginTop: S.sm, color: C.brand, letterSpacing: 1.5, fontWeight: '800', fontSize: 11, textAlign: 'center' },
  section: { borderWidth: 1.5, borderColor: C.borderStrong },
  sectionTitle: { backgroundColor: C.inverse, color: C.onInverse, padding: S.md, fontWeight: '900', letterSpacing: 2, fontSize: 12 },
  sectionBody: { padding: S.md },
  rowKV: { flexDirection: 'row', gap: S.md, paddingVertical: 4 },
  rowLbl: { fontSize: 10, fontWeight: '800', letterSpacing: 1.5, color: C.onS3, width: 100 },
  rowVal: { flex: 1, color: C.fg, fontSize: 13 },
  mono: { fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }), fontSize: 11 },
  tip: { color: C.fg, fontSize: 13, marginVertical: 2, lineHeight: 18 },
  meshRow: { flexDirection: 'row', alignItems: 'center', gap: S.sm },
  meshDot: { width: 10, height: 10, backgroundColor: C.warn, borderWidth: 1.5, borderColor: C.borderStrong },
  meshText: { color: C.fg, fontSize: 11, letterSpacing: 1, fontWeight: '800' },
});
