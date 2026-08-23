import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet, ScrollView, Switch, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { useAuth } from '@/src/auth';
import { api } from '@/src/api';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';

export default function Home() {
  const { user, setUser } = useAuth();
  const router = useRouter();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const angel = !!user?.angel_mode;
  const [busy, setBusy] = useState(false);

  const toggleAngel = async () => {
    if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
    setBusy(true);
    try {
      const updated: any = await api('/me/prefs', { method: 'PATCH', body: JSON.stringify({ angel_mode: !angel }) });
      setUser(updated as any);
    } finally { setBusy(false); }
  };

  if (angel) return <AngelHome onToggle={toggleAngel} lang={lang} router={router} />;

  return (
    <SafeAreaView testID="standard-home" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <View>
          <Text style={styles.brand}>GUARDIAN</Text>
          <Text style={styles.brandSub}>{t('standard_mode', lang).toUpperCase()}</Text>
        </View>
        <Pressable testID="angel-toggle" onPress={toggleAngel} disabled={busy} style={styles.angelToggle}>
          <Ionicons name="accessibility-outline" size={18} color={C.onInverse} />
          <Text style={styles.angelToggleText}>{t('angel_mode', lang).toUpperCase()}</Text>
        </Pressable>
      </View>

      <ScrollView contentContainerStyle={styles.body}>
        <Text style={styles.greeting}>HELLO, {(user?.name || user?.email || 'GUARDIAN').toUpperCase()}</Text>
        <Text style={styles.did}>DID: {user?.did}</Text>

        <Text style={styles.section}>QUICK ACTIONS</Text>
        <View style={styles.cardGrid}>
          <ActionCard testID="action-vault" label={t('vault', lang)} icon="lock-closed-outline" onPress={() => router.push('/(tabs)/vault')} />
          <ActionCard testID="action-translate" label={t('translate', lang)} icon="language-outline" onPress={() => router.push('/translate')} />
          <ActionCard testID="action-waitlist" label={t('waitlist', lang)} icon="calendar-outline" onPress={() => router.push('/(tabs)/waitlist')} />
          <ActionCard testID="action-donor" label={t('donor_card', lang)} icon="heart-outline" onPress={() => router.push('/emergency-qr')} />
        </View>

        <Text style={styles.section}>SAFETY</Text>
        <Pressable testID="simulate-fall" onPress={() => router.push('/fall-verify')} style={styles.fallBtn}>
          <Ionicons name="warning-outline" size={22} color={C.onError} />
          <Text style={styles.fallBtnText}>{t('simulate_fall', lang).toUpperCase()}</Text>
        </Pressable>
      </ScrollView>

      <Pressable
        testID="fab-emergency-qr"
        onPress={() => router.push('/emergency-qr')}
        style={styles.fab}
      >
        <Ionicons name="qr-code-outline" size={22} color={C.onError} />
        <Text style={styles.fabText}>{t('emergency_qr', lang).toUpperCase()}</Text>
      </Pressable>
    </SafeAreaView>
  );
}

function ActionCard({ label, icon, onPress, testID }: any) {
  return (
    <Pressable testID={testID} onPress={onPress} style={({ pressed }) => [styles.card, pressed && { backgroundColor: C.surface3 }]}>
      <Ionicons name={icon} size={28} color={C.fg} />
      <Text style={styles.cardLabel}>{label.toUpperCase()}</Text>
    </Pressable>
  );
}

function AngelHome({ onToggle, lang, router }: any) {
  return (
    <SafeAreaView testID="angel-home" style={{ flex: 1, backgroundColor: C.bg }} edges={['top']}>
      <View style={styles.angelHeader}>
        <Text style={styles.angelHeaderText}>{t('angel_mode', lang).toUpperCase()}</Text>
        <Pressable testID="angel-toggle-back" onPress={onToggle} style={styles.angelToggleBack}>
          <Text style={styles.angelToggleBackText}>{t('standard_mode', lang).toUpperCase()}</Text>
        </Pressable>
      </View>
      <View style={styles.angelGrid}>
        <AngelTile testID="angel-sos" label={t('sos', lang)} icon="alert" bg={C.error} fg={C.onError} onPress={() => router.push('/fall-verify')} />
        <AngelTile testID="angel-family" label={t('call_family', lang)} icon="call" bg={C.brand} fg={C.onInverse} onPress={() => router.push('/emergency-qr')} />
        <AngelTile testID="angel-meds" label={t('medications', lang)} icon="medkit" bg={C.inverse} fg={C.onInverse} onPress={() => router.push('/(tabs)/profile')} />
        <AngelTile testID="angel-docs" label={t('documents', lang)} icon="document" bg={C.warn} fg={C.onWarn} onPress={() => router.push('/(tabs)/vault')} />
      </View>
    </SafeAreaView>
  );
}

function AngelTile({ label, icon, bg, fg, onPress, testID }: any) {
  return (
    <Pressable testID={testID} onPress={onPress} style={[styles.angelTile, { backgroundColor: bg }]}>
      <Ionicons name={icon} size={56} color={fg} />
      <Text style={[styles.angelTileText, { color: fg }]}>{label.toUpperCase()}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.lg, paddingVertical: S.md, backgroundColor: C.inverse, borderBottomWidth: 2, borderBottomColor: C.inverse },
  brand: { color: C.onInverse, fontSize: 22, fontWeight: '900', letterSpacing: 2 },
  brandSub: { color: C.onInverse, opacity: 0.6, fontSize: 10, letterSpacing: 2, marginTop: 2 },
  angelToggle: { flexDirection: 'row', alignItems: 'center', gap: 6, borderWidth: 1.5, borderColor: C.onInverse, paddingHorizontal: S.md, paddingVertical: 8 },
  angelToggleText: { color: C.onInverse, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  body: { padding: S.lg, paddingBottom: 120 },
  greeting: { fontSize: 20, fontWeight: '900', color: C.fg, letterSpacing: 1 },
  did: { fontSize: 10, color: C.onS3, marginTop: 4, fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }), letterSpacing: 0.5 },
  section: { marginTop: S.xl, marginBottom: S.md, fontSize: 11, letterSpacing: 2, color: C.fg, fontWeight: '800' },
  cardGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: S.md },
  card: { width: '48%', aspectRatio: 1.2, padding: S.md, borderWidth: 1.5, borderColor: C.borderStrong, backgroundColor: C.bg, justifyContent: 'space-between' },
  cardLabel: { fontWeight: '900', letterSpacing: 1.5, fontSize: 13, color: C.fg },
  fallBtn: { flexDirection: 'row', alignItems: 'center', gap: S.sm, backgroundColor: C.error, paddingHorizontal: S.lg, paddingVertical: S.lg, borderWidth: 2, borderColor: C.borderStrong },
  fallBtnText: { color: C.onError, fontWeight: '900', letterSpacing: 1.5, fontSize: 14 },
  fab: { position: 'absolute', bottom: 88, right: S.lg, backgroundColor: C.error, paddingHorizontal: S.lg, paddingVertical: S.md, flexDirection: 'row', alignItems: 'center', gap: S.sm, borderWidth: 2, borderColor: C.borderStrong },
  fabText: { color: C.onError, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  // Angel
  angelHeader: { paddingHorizontal: S.lg, paddingVertical: S.lg, backgroundColor: C.inverse, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  angelHeaderText: { color: C.onInverse, fontWeight: '900', fontSize: 20, letterSpacing: 2 },
  angelToggleBack: { borderWidth: 2, borderColor: C.onInverse, paddingHorizontal: S.md, paddingVertical: 10 },
  angelToggleBackText: { color: C.onInverse, fontWeight: '900', fontSize: 12, letterSpacing: 1 },
  angelGrid: { flex: 1, flexDirection: 'row', flexWrap: 'wrap' },
  angelTile: { width: '50%', height: '50%', alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: C.borderStrong, gap: S.md, padding: S.md },
  angelTileText: { fontSize: 24, fontWeight: '900', letterSpacing: 2, textAlign: 'center' },
});
