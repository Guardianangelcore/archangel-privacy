/* Copyright © 2026 Guardian Angel. All Rights Reserved. This source code and its logic are the sole property of Guardian Angel. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet, ScrollView, Platform } from 'react-native';
import { Image } from 'expo-image';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/src/auth';
import { C, S, F } from '@/src/theme';
import { t, LANG_NAMES, Lang } from '@/src/i18n';

const BG = 'https://images.pexels.com/photos/18459247/pexels-photo-18459247.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=1200&w=940';

export default function Login() {
  const { signIn } = useAuth();
  const [lang, setLang] = useState<Lang>('sk');
  const [busy, setBusy] = useState(false);

  const onSignIn = async () => {
    setBusy(true);
    try { await signIn(); } finally { setBusy(false); }
  };

  return (
    <View testID="login-screen" style={styles.root}>
      <Image source={BG} style={StyleSheet.absoluteFill} contentFit="cover" />
      <LinearGradient
        colors={['rgba(0,0,0,0.2)', 'rgba(17,17,17,0.85)', 'rgba(17,17,17,0.98)']}
        style={StyleSheet.absoluteFill}
      />
      <SafeAreaView style={{ flex: 1 }}>
        <View style={styles.creditRow}>
          <Text testID="guardian-credit" style={styles.credit}>{t('author_credit', lang).toUpperCase()}</Text>
        </View>
        <ScrollView contentContainerStyle={styles.body} showsVerticalScrollIndicator={false}>
          <View style={{ flex: 1 }} />
          <Text style={styles.hero}>GUARDIAN</Text>
          <Text style={styles.hero2}>HEALTH & ANGEL</Text>
          <View style={styles.divider} />
          <Text style={styles.tagline}>
            {lang === 'sk' && 'Suverénny operačný systém pre zdravie a bezpečnosť.'}
            {lang === 'cs' && 'Suverénní operační systém pro zdraví a bezpečí.'}
            {lang === 'en' && 'A sovereign OS for medical dignity and safety.'}
            {lang === 'de' && 'Souveränes Betriebssystem für Gesundheit und Sicherheit.'}
          </Text>

          <Text style={styles.langLabel}>{t('choose_language', lang).toUpperCase()}</Text>
          <View style={styles.langRow}>
            {(Object.keys(LANG_NAMES) as Lang[]).map(l => {
              const active = l === lang;
              return (
                <Pressable
                  testID={`lang-${l}`}
                  key={l}
                  onPress={() => setLang(l)}
                  style={[styles.langChip, active && styles.langChipActive]}
                >
                  <Text style={[styles.langChipText, active && styles.langChipTextActive]}>{LANG_NAMES[l]}</Text>
                </Pressable>
              );
            })}
          </View>
        </ScrollView>

        <View style={styles.bottom}>
          <Pressable
            testID="google-signin-button"
            onPress={onSignIn}
            disabled={busy}
            style={({ pressed }) => [styles.signBtn, pressed && { opacity: 0.85 }]}
          >
            <Text style={styles.signBtnText}>{busy ? '...' : t('sign_in_google', lang).toUpperCase()}</Text>
          </Pressable>
          <Text style={styles.footer}>© 2026 GUARDIAN ANGEL · PROPRIETARY · ZERO-KNOWLEDGE</Text>
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#000' },
  creditRow: { paddingHorizontal: S.lg, paddingTop: S.sm, alignItems: 'flex-end' },
  credit: { color: C.onInverse, fontSize: 10, letterSpacing: 2, opacity: 0.9, fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }) },
  body: { padding: S.xl, minHeight: '70%' },
  hero: { color: C.onInverse, fontSize: 40, fontWeight: '900', letterSpacing: 2 },
  hero2: { color: C.onInverse, fontSize: 28, fontWeight: '900', letterSpacing: 1, marginTop: -4 },
  divider: { height: 3, backgroundColor: C.onInverse, width: 64, marginTop: S.lg },
  tagline: { color: C.onInverse, opacity: 0.9, fontSize: 16, marginTop: S.lg, lineHeight: 22 },
  langLabel: { color: C.onInverse, marginTop: S.xxl, fontSize: 11, letterSpacing: 2 },
  langRow: { flexDirection: 'row', flexWrap: 'wrap', marginTop: S.md, gap: S.sm },
  langChip: { paddingHorizontal: S.lg, paddingVertical: S.md, borderWidth: 1.5, borderColor: C.onInverse, backgroundColor: 'transparent' },
  langChipActive: { backgroundColor: C.onInverse },
  langChipText: { color: C.onInverse, fontWeight: '800', letterSpacing: 1, fontSize: 13 },
  langChipTextActive: { color: C.inverse },
  bottom: { padding: S.lg, gap: S.md },
  signBtn: { backgroundColor: C.onInverse, paddingVertical: 22, alignItems: 'center', borderWidth: 2, borderColor: C.onInverse },
  signBtnText: { color: C.inverse, fontSize: 18, fontWeight: '900', letterSpacing: 1.5 },
  footer: { color: C.onInverse, opacity: 0.6, fontSize: 10, letterSpacing: 2, textAlign: 'center' },
});
