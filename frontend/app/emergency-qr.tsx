/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, Platform, Share } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import QRCode from 'react-native-qrcode-svg';
import { useRouter } from 'expo-router';
import { useAuth } from '@/src/auth';
import { api } from '@/src/api';
import { C, S } from '@/src/theme';

export default function EmergencyQR() {
  const { user } = useAuth();
  const router = useRouter();
  const [prof, setProf] = useState<any>({});

  useEffect(() => {
    (async () => {
      try { setProf(await api('/emergency-profile')); } catch {}
    })();
  }, []);

  const qrPayload = JSON.stringify({
    did: user?.did,
    name: prof.full_name || user?.name,
    blood_type: prof.blood_type,
    allergies: prof.allergies,
    ec: `${prof.emergency_contact_name || ''} ${prof.emergency_contact_phone || ''}`.trim(),
    donor: prof.is_donor ? (prof.donor_organs || 'yes') : 'no',
  });

  const shareProfile = async () => {
    const msg = [
      '🛡 GUARDIAN ANGEL — NÚDZOVÝ PROFIL',
      `Meno: ${prof.full_name || user?.name || '—'}`,
      `Krvná skupina: ${prof.blood_type || '—'}`,
      `Alergie: ${prof.allergies || '—'}`,
      `Diagnózy: ${prof.conditions || '—'}`,
      `Lieky: ${prof.medications || '—'}`,
      `ICE kontakt: ${`${prof.emergency_contact_name || ''} ${prof.emergency_contact_phone || ''}`.trim() || '—'}`,
    ].join('\n');
    try {
      if (Platform.OS === 'web') {
        if ((navigator as any).share) await (navigator as any).share({ title: 'Guardian núdzový profil', text: msg });
      } else {
        await Share.share({ message: msg, title: 'Guardian núdzový profil' });
      }
    } catch {}
  };

  return (
    <SafeAreaView testID="emergency-qr-screen" style={styles.root} edges={['top', 'bottom']}>
      <View style={styles.header}>
        <Pressable testID="qr-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={styles.title}>EMERGENCY QR</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView contentContainerStyle={{ padding: S.lg }}>
        {prof.is_donor && (
          <View style={styles.donorBadge}>
            <Ionicons name="heart" size={16} color={C.onError} />
            <Text style={styles.donorBadgeText}>ORGAN DONOR</Text>
          </View>
        )}

        <View style={styles.qrBox}>
          <QRCode value={qrPayload} size={240} backgroundColor="#ffffff" color="#000000" />
        </View>

        <Text style={styles.name}>{(prof.full_name || user?.name || 'GUARDIAN').toUpperCase()}</Text>
        <Text style={styles.did}>{user?.did}</Text>

        <View style={styles.table}>
          <Row label="BLOOD TYPE" value={prof.blood_type || '—'} big />
          <Row label="ALLERGIES" value={prof.allergies || '—'} />
          <Row label="CONDITIONS" value={prof.conditions || '—'} />
          <Row label="MEDICATIONS" value={prof.medications || '—'} />
          <Row label="EMERGENCY CONTACT" value={`${prof.emergency_contact_name || ''}\n${prof.emergency_contact_phone || ''}`.trim() || '—'} />
          {prof.is_donor && <Row label="DONOR ORGANS" value={prof.donor_organs || 'All'} />}
          {!!prof.life_testament && <Row label="LIFE TESTAMENT" value={prof.life_testament} />}
        </View>

        <Pressable testID="qr-share" onPress={shareProfile} style={styles.shareBtn}>
          <Ionicons name="share-outline" size={18} color="#FFF" />
          <Text style={styles.shareText}>ZDIEĽAŤ NÚDZOVÝ PROFIL</Text>
        </Pressable>

        <Text style={styles.footer}>OFFLINE-CAPABLE · SCANNABLE BY FIRST RESPONDERS</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

function Row({ label, value, big }: any) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLbl}>{label}</Text>
      <Text style={[styles.rowVal, big && styles.rowBig]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#FFFFFF' },
  header: { paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  donorBadge: { flexDirection: 'row', alignSelf: 'flex-start', backgroundColor: C.error, paddingHorizontal: S.md, paddingVertical: 6, gap: 6, alignItems: 'center', marginBottom: S.md },
  donorBadgeText: { color: C.onError, fontWeight: '900', letterSpacing: 2, fontSize: 12 },
  qrBox: { alignSelf: 'center', padding: S.md, borderWidth: 2, borderColor: '#000' },
  name: { textAlign: 'center', fontSize: 20, fontWeight: '900', color: '#000', marginTop: S.lg, letterSpacing: 1 },
  did: { textAlign: 'center', color: '#333', marginTop: 4, fontSize: 11, fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }) },
  table: { marginTop: S.xl, borderWidth: 2, borderColor: '#000' },
  row: { borderBottomWidth: 1.5, borderColor: '#000', padding: S.md },
  rowLbl: { fontSize: 10, letterSpacing: 2, fontWeight: '900', color: '#000' },
  rowVal: { fontSize: 15, color: '#000', marginTop: 4 },
  rowBig: { fontSize: 28, fontWeight: '900', letterSpacing: 2 },
  footer: { textAlign: 'center', marginTop: S.lg, fontSize: 10, letterSpacing: 2, color: '#000' },
  shareBtn: { marginTop: S.xl, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: '#000', paddingVertical: S.lg, minHeight: 52 },
  shareText: { color: '#FFF', fontWeight: '900', letterSpacing: 2, fontSize: 13 },
});
