/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet, ScrollView, Platform, TextInput, ActivityIndicator } from 'react-native';
import { Image } from 'expo-image';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '@/src/auth';
import { C, S } from '@/src/theme';
import { t, LANG_NAMES, Lang, isRTL } from '@/src/i18n';

const BG = 'https://images.pexels.com/photos/18459247/pexels-photo-18459247.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=1200&w=940';
const FOUNDER_EMAIL = 'guardian.angel.core@proton.me';

export default function Login() {
  const { signIn, signInDev } = useAuth();
  const [lang, setLang] = useState<Lang>('en');
  const [busy, setBusy] = useState<'google' | 'dev' | null>(null);
  const [showBypass, setShowBypass] = useState(false);
  const [bypassEmail, setBypassEmail] = useState(FOUNDER_EMAIL);
  const [err, setErr] = useState('');

  // SECURITY — the dev/founder bypass is auto-disabled in production. It only
  // renders on preview / localhost / native-dev builds, never on a public deploy.
  const isDevEnv = __DEV__ || (Platform.OS === 'web' && typeof window !== 'undefined'
    && (window.location.hostname.includes('preview')
        || window.location.hostname === 'localhost'
        || window.location.hostname.startsWith('127.')));

  const onSignIn = async () => {
    setBusy('google'); setErr('');
    try { await signIn(); }
    catch (e: any) { setErr(String(e?.message || e)); }
    finally { setBusy(null); }
  };

  const onDevBypass = async () => {
    setBusy('dev'); setErr('');
    try {
      await signInDev(bypassEmail.trim(), bypassEmail === FOUNDER_EMAIL ? 'Guardian Angel' : undefined);
    } catch (e: any) { setErr(String(e?.message || e)); setBusy(null); }
  };

  const asFounder = async () => {
    setBypassEmail(FOUNDER_EMAIL);
    setBusy('dev'); setErr('');
    try { await signInDev(FOUNDER_EMAIL, 'Guardian Angel'); }
    catch (e: any) { setErr(String(e?.message || e)); setBusy(null); }
  };

  return (
    <View testID="login-screen" style={styles.root}>
      <Image source={BG} style={StyleSheet.absoluteFill} contentFit="cover" />
      <LinearGradient
        colors={['rgba(10,10,46,0.30)', 'rgba(5,5,16,0.88)', 'rgba(5,5,16,0.98)']}
        style={StyleSheet.absoluteFill}
      />
      <SafeAreaView style={{ flex: 1 }}>
        <View style={styles.creditRow}>
          <Text testID="guardian-credit" style={styles.credit}>{t('author_credit', lang).toUpperCase()}</Text>
        </View>
        <ScrollView contentContainerStyle={styles.body} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
          <View style={{ flex: 1 }} />
          <Text style={styles.hero}>GUARDIAN</Text>
          <Text style={styles.hero2}>HEALTH & ANGEL</Text>
          <View style={styles.divider} />
          <Text style={[styles.tagline, isRTL(lang) && styles.rtl]}>{t('tagline', lang)}</Text>

          <Text style={[styles.langLabel, isRTL(lang) && styles.rtl]}>{t('choose_language', lang).toUpperCase()}</Text>
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
            disabled={busy !== null}
            style={({ pressed }) => [styles.signBtn, pressed && { opacity: 0.85 }]}
          >
            {busy === 'google'
              ? <ActivityIndicator color={C.inverse} />
              : <Text style={styles.signBtnText}>{t('sign_in_google', lang).toUpperCase()}</Text>}
          </Pressable>

          {/* SOVEREIGN BYPASS — Founder / preview access without Google OAuth.
              Auto-hidden in production (only preview / localhost / dev). */}
          {isDevEnv && (
          <Pressable
            testID="founder-bypass-btn"
            onPress={asFounder}
            disabled={busy !== null}
            style={styles.founderBtn}
          >
            {busy === 'dev'
              ? <ActivityIndicator color={C.brand} />
              : <>
                  <Ionicons name="key" size={18} color={C.brand} />
                  <Text style={styles.founderText}>ENTER AS GUARDIAN ANGEL (FOUNDER)</Text>
                </>}
          </Pressable>
          )}

          {isDevEnv && (
          <Pressable
            testID="bypass-toggle"
            onPress={() => setShowBypass(v => !v)}
            hitSlop={8}
            style={styles.linkBtn}
          >
            <Text style={styles.linkText}>{showBypass ? 'CLOSE' : 'OTHER EMAIL · DEVELOPER BYPASS'}</Text>
          </Pressable>
          )}

          {isDevEnv && showBypass && (
            <View style={styles.bypassBox}>
              <TextInput
                testID="bypass-email"
                value={bypassEmail}
                onChangeText={setBypassEmail}
                placeholder="email@guardian"
                placeholderTextColor="rgba(255,255,255,0.5)"
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
                style={styles.bypassInput}
              />
              <Pressable
                testID="bypass-submit"
                onPress={onDevBypass}
                disabled={busy !== null || !bypassEmail.includes('@')}
                style={styles.bypassSubmit}
              >
                <Text style={styles.bypassSubmitText}>{busy === 'dev' ? '…' : 'ENTER'}</Text>
              </Pressable>
            </View>
          )}

          {!!err && <Text testID="login-err" style={styles.err}>{err}</Text>}

          <Text style={styles.footer}>© 2026 GUARDIAN ANGEL SOVEREIGN FOUNDATION (DAO) · PROPRIETARY · ZERO-KNOWLEDGE</Text>
          <Text style={styles.footerArt50}>EU AI ACT ART. 50 · AI OUTPUTS ARE INFORMATIONAL ONLY · YOU ACT AT YOUR OWN RISK</Text>
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#000' },
  creditRow: { paddingHorizontal: S.lg, paddingTop: S.sm, alignItems: 'flex-end' },
  credit: { color: C.onInverse, fontSize: 10, letterSpacing: 2, opacity: 0.9, fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }) },
  body: { padding: S.xl, minHeight: '60%' },
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
  bottom: { padding: S.lg, gap: S.sm },
  signBtn: { backgroundColor: C.onInverse, paddingVertical: 20, alignItems: 'center', borderWidth: 2, borderColor: C.onInverse, minHeight: 56 },
  signBtnText: { color: C.inverse, fontSize: 17, fontWeight: '900', letterSpacing: 1.5 },
  founderBtn: { flexDirection: 'row', gap: 10, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: C.brand, backgroundColor: 'rgba(212,175,55,0.10)', paddingVertical: 16, minHeight: 52 },
  founderText: { color: C.brand, fontSize: 12.5, fontWeight: '900', letterSpacing: 1.5 },
  linkBtn: { alignItems: 'center', paddingVertical: 6 },
  linkText: { color: C.onInverse, opacity: 0.7, fontSize: 11, letterSpacing: 1.5, fontWeight: '700' },
  bypassBox: { flexDirection: 'row', gap: 6, marginTop: 4 },
  bypassInput: { flex: 1, borderWidth: 1.5, borderColor: 'rgba(212,175,55,0.5)', color: C.onInverse, paddingHorizontal: 12, minHeight: 48, fontSize: 13, backgroundColor: 'rgba(0,0,0,0.4)' },
  bypassSubmit: { backgroundColor: C.brand, paddingHorizontal: 20, alignItems: 'center', justifyContent: 'center', minHeight: 48 },
  bypassSubmitText: { color: C.onInverse, fontWeight: '900', fontSize: 13, letterSpacing: 1 },
  err: { color: C.error, fontSize: 11, textAlign: 'center', marginTop: 6, fontWeight: '700' },
  footer: { color: C.onInverse, opacity: 0.6, fontSize: 10, letterSpacing: 2, textAlign: 'center', marginTop: 6 },
  footerArt50: { color: C.onInverse, opacity: 0.45, fontSize: 8, letterSpacing: 1, textAlign: 'center', marginTop: 2 },
  rtl: { writingDirection: 'rtl', textAlign: 'right' },
});
