/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator, Image, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { API_BASE, getToken } from '@/src/api';
import { shareFile } from '@/src/pdf';
import { C, S, R } from '@/src/theme';

export default function Wallpaper() {
  const router = useRouter();
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');

  useEffect(() => {
    (async () => {
      const token = await getToken();
      setUrl(`${API_BASE}/api/family/wallpaper.png?token=${token}&ts=${Date.now()}`);
    })();
  }, []);

  const download = async () => {
    setBusy(true);
    try { await shareFile('/family/wallpaper.png', 'guardian_emergency_wallpaper.png', 'image/png'); }
    catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(false); }
  };

  return (
    <SafeAreaView testID="wallpaper-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="wp-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>EMERGENCY WALLPAPER</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60, alignItems: 'center' }}>
        <Text style={styles.h1}>Emergency Lock-Screen Wallpaper</Text>
        <Text style={styles.sub}>
          A QR code with blood type, allergies and an ICE contact — paramedics scan it without unlocking your phone.
          The data comes from your Emergency Profile.
        </Text>

        <View style={styles.previewBox}>
          {url ? (
            <Image
              testID="wp-preview"
              source={{ uri: url }}
              style={styles.preview}
              resizeMode="contain"
              onLoadEnd={() => setLoading(false)}
              onError={() => { setLoading(false); setErr('The preview failed to load.'); }}
            />
          ) : null}
          {loading && <ActivityIndicator color={C.brand} style={StyleSheet.absoluteFill} />}
        </View>
        {!!err && <Text style={styles.err}>{err}</Text>}

        <Pressable testID="wp-download" onPress={download} disabled={busy || !url} style={styles.cta}>
          {busy ? <ActivityIndicator color={C.onInverse} /> : (
            <>
              <Ionicons name="download-outline" size={18} color={C.onInverse} />
              <Text style={styles.ctaText}>DOWNLOAD WALLPAPER</Text>
            </>
          )}
        </Pressable>
        <Pressable
          testID="wp-share"
          onPress={async () => {
            try {
              if (Platform.OS === 'web' && (navigator as any).share) await (navigator as any).share({ title: 'Guardian emergency wallpaper', url });
              else await shareFile('/family/wallpaper.png', 'guardian_emergency_wallpaper.png', 'image/png');
            } catch {}
          }}
          disabled={!url}
          style={styles.ctaOutline}
        >
          <Ionicons name="people-outline" size={18} color={C.brand} />
          <Text style={styles.ctaOutlineText}>SEND TO FAMILY WITH ONE TAP</Text>
        </Pressable>

        <View style={styles.steps}>
          <Text style={styles.stepTitle}>HOW TO SET IT UP</Text>
          <Text style={styles.step}>1. Download the wallpaper to your gallery.</Text>
          <Text style={styles.step}>2. Settings → Wallpaper → Lock screen.</Text>
          <Text style={styles.step}>3. Done — critical info is available without unlocking.</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 14 },
  h1: { fontSize: 22, fontWeight: '900', color: C.fg, textAlign: 'center' },
  sub: { marginTop: S.sm, fontSize: 12, color: C.onS3, lineHeight: 18, textAlign: 'center' },
  previewBox: { marginTop: S.xl, width: 234, height: 416, borderRadius: R.md, borderWidth: 1, borderColor: C.borderStrong, overflow: 'hidden', backgroundColor: C.surface2 },
  preview: { width: '100%', height: '100%' },
  cta: { marginTop: S.xl, alignSelf: 'stretch', flexDirection: 'row', gap: S.sm, backgroundColor: C.brand, borderRadius: R.sm, minHeight: 52, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  ctaOutline: { marginTop: S.md, alignSelf: 'stretch', flexDirection: 'row', gap: S.sm, borderWidth: 1.5, borderColor: C.brand, borderRadius: R.sm, minHeight: 52, alignItems: 'center', justifyContent: 'center' },
  ctaOutlineText: { color: C.brand, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  steps: { marginTop: S.xl, alignSelf: 'stretch', backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.lg, gap: 6 },
  stepTitle: { fontSize: 10, letterSpacing: 2, color: C.info, fontWeight: '800', marginBottom: 4 },
  step: { color: C.fg, fontSize: 13, lineHeight: 19 },
  err: { color: C.error, marginTop: S.md, fontSize: 12 },
});
