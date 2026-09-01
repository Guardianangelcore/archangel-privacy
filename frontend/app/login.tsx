/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet, ScrollView, Platform, TextInput, ActivityIndicator } from 'react-native';
import { Image } from 'expo-image';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '@/src/auth';
import { api as apiCall } from '@/src/api';
import { C, S } from '@/src/theme';
import { t, LANG_NAMES, Lang, isRTL } from '@/src/i18n';

const BG = 'https://images.pexels.com/photos/18459247/pexels-photo-18459247.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=1200&w=940';
const FOUNDER_EMAIL = 'guardian.angel.core@proton.me';

export default function Login() {
  const { signIn, signInDev, signInPassword, registerPassword, authError } = useAuth();
  const [lang, setLang] = useState<Lang>('en');
  const [busy, setBusy] = useState<'google' | 'dev' | 'pw' | null>(null);
  const [showBypass, setShowBypass] = useState(false);
  const [bypassEmail, setBypassEmail] = useState(FOUNDER_EMAIL);
  const [err, setErr] = useState('');
  // Classic e-mail & password login/registration
  const [pwMode, setPwMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  // Forgot-password flow
  const [resetMode, setResetMode] = useState(false);
  const [codeSent, setCodeSent] = useState(false);
  const [resetCode, setResetCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [info, setInfo] = useState('');

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

  const onPassword = async () => {
    setBusy('pw'); setErr('');
    try {
      if (pwMode === 'register') {
        if (password.length < 12) throw new Error('Password must be at least 12 characters.');
        await registerPassword(email, password);
      } else {
        await signInPassword(email, password);
      }
    } catch (e: any) {
      const m = String(e?.message || e);
      if (m.startsWith('401')) setErr('Incorrect email or password.');
      else if (m.startsWith('409')) setErr('Unable to create account — try signing in instead.');
      else if (m.includes('at least 12')) setErr('Password must be at least 12 characters.');
      else setErr(m);
    } finally { setBusy(null); }
  };

  const onForgot = async () => {
    setBusy('pw'); setErr(''); setInfo('');
    try {
      const res: any = await apiCall('/auth/forgot-password', {
        method: 'POST',
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });
      setCodeSent(true);
      setInfo(res.message || 'If an account exists, a reset code has been sent.');
    } catch (e: any) { setErr(String(e?.message || e)); }
    finally { setBusy(null); }
  };

  const onReset = async () => {
    setBusy('pw'); setErr(''); setInfo('');
    try {
      if (newPassword.length < 12) throw new Error('Password must be at least 12 characters.');
      const res: any = await apiCall('/auth/reset-password', {
        method: 'POST',
        body: JSON.stringify({ email: email.trim().toLowerCase(), code: resetCode.trim(), new_password: newPassword }),
      });
      setResetMode(false); setCodeSent(false); setResetCode(''); setNewPassword('');
      setPwMode('login'); setPassword('');
      setInfo(res.message || 'Password updated — sign in with your new password.');
    } catch (e: any) {
      const m = String(e?.message || e);
      if (m.startsWith('400')) setErr('Invalid or expired code.');
      else if (m.includes('at least 12')) setErr('Password must be at least 12 characters.');
      else setErr(m);
    } finally { setBusy(null); }
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
          {/* CLASSIC E-MAIL & PASSWORD */}
          {!resetMode && (
          <View style={styles.pwTabs}>
            <Pressable testID="pw-tab-login" onPress={() => { setPwMode('login'); setErr(''); }}
              style={[styles.pwTab, pwMode === 'login' && styles.pwTabActive]}>
              <Text style={[styles.pwTabText, pwMode === 'login' && styles.pwTabTextActive]}>SIGN IN</Text>
            </Pressable>
            <Pressable testID="pw-tab-register" onPress={() => { setPwMode('register'); setErr(''); }}
              style={[styles.pwTab, pwMode === 'register' && styles.pwTabActive]}>
              <Text style={[styles.pwTabText, pwMode === 'register' && styles.pwTabTextActive]}>CREATE ACCOUNT</Text>
            </Pressable>
          </View>
          )}
          {resetMode && <Text style={styles.resetTitle}>FORGOT PASSWORD</Text>}
          <TextInput
            testID="pw-email"
            value={email}
            onChangeText={setEmail}
            placeholder="E-mail"
            placeholderTextColor="rgba(255,255,255,0.5)"
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
            autoComplete="email"
            style={styles.pwInput}
          />
          {!resetMode && (
          <View style={styles.pwRow}>
            <TextInput
              testID="pw-password"
              value={password}
              onChangeText={setPassword}
              placeholder={pwMode === 'register' ? 'Password (min. 12 characters)' : 'Password'}
              placeholderTextColor="rgba(255,255,255,0.5)"
              secureTextEntry={!showPw}
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete={pwMode === 'register' ? 'new-password' : 'password'}
              style={[styles.pwInput, { flex: 1, marginTop: 0 }]}
            />
            <Pressable testID="pw-eye" onPress={() => setShowPw(v => !v)} hitSlop={8} style={styles.pwEye}>
              <Ionicons name={showPw ? 'eye-off' : 'eye'} size={20} color="rgba(255,255,255,0.7)" />
            </Pressable>
          </View>
          )}
          {resetMode && codeSent && (
            <>
              <TextInput
                testID="reset-code"
                value={resetCode}
                onChangeText={setResetCode}
                placeholder="6-digit code from e-mail"
                placeholderTextColor="rgba(255,255,255,0.5)"
                keyboardType="number-pad"
                maxLength={6}
                style={styles.pwInput}
              />
              <TextInput
                testID="reset-new-password"
                value={newPassword}
                onChangeText={setNewPassword}
                placeholder="New password (min. 12 characters)"
                placeholderTextColor="rgba(255,255,255,0.5)"
                secureTextEntry
                autoCapitalize="none"
                autoCorrect={false}
                autoComplete="new-password"
                style={styles.pwInput}
              />
            </>
          )}
          {!resetMode ? (
          <Pressable
            testID="pw-submit"
            onPress={onPassword}
            disabled={busy !== null || !email.includes('@') || password.length === 0}
            style={({ pressed }) => [styles.signBtn, pressed && { opacity: 0.85 },
              (busy !== null || !email.includes('@') || password.length === 0) && { opacity: 0.55 }]}
          >
            {busy === 'pw'
              ? <ActivityIndicator color={C.inverse} />
              : <Text style={styles.signBtnText}>{pwMode === 'register' ? 'CREATE ACCOUNT' : 'SIGN IN'}</Text>}
          </Pressable>
          ) : (
          <Pressable
            testID="reset-submit"
            onPress={codeSent ? onReset : onForgot}
            disabled={busy !== null || !email.includes('@') || (codeSent && (resetCode.length !== 6 || newPassword.length === 0))}
            style={({ pressed }) => [styles.signBtn, pressed && { opacity: 0.85 },
              (busy !== null || !email.includes('@')) && { opacity: 0.55 }]}
          >
            {busy === 'pw'
              ? <ActivityIndicator color={C.inverse} />
              : <Text style={styles.signBtnText}>{codeSent ? 'RESET PASSWORD' : 'SEND RESET CODE'}</Text>}
          </Pressable>
          )}
          <View style={styles.linkRow}>
            {!resetMode && pwMode === 'login' && (
              <Pressable testID="forgot-link" onPress={() => { setResetMode(true); setErr(''); setInfo(''); setCodeSent(false); }} hitSlop={8}>
                <Text style={styles.linkText}>FORGOT PASSWORD?</Text>
              </Pressable>
            )}
            {resetMode && (
              <>
                {codeSent && (
                  <Pressable testID="resend-code" onPress={onForgot} hitSlop={8}>
                    <Text style={styles.linkText}>RESEND CODE</Text>
                  </Pressable>
                )}
                <Pressable testID="back-to-login" onPress={() => { setResetMode(false); setCodeSent(false); setErr(''); setInfo(''); }} hitSlop={8}>
                  <Text style={styles.linkText}>BACK TO SIGN IN</Text>
                </Pressable>
              </>
            )}
          </View>

          <View style={styles.orRow}>
            <View style={styles.orLine} />
            <Text style={styles.orText}>OR</Text>
            <View style={styles.orLine} />
          </View>

          <Pressable
            testID="google-signin-button"
            onPress={onSignIn}
            disabled={busy !== null}
            style={({ pressed }) => [styles.googleBtn, pressed && { opacity: 0.85 }]}
          >
            {busy === 'google'
              ? <ActivityIndicator color={C.onInverse} />
              : <>
                  <Ionicons name="logo-google" size={18} color={C.onInverse} />
                  <Text style={styles.googleBtnText}>{t('sign_in_google', lang).toUpperCase()}</Text>
                </>}
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

          {(!!err || !!authError) && <Text testID="login-err" style={styles.err}>{err || authError}</Text>}
          {!!info && !err && <Text testID="login-info" style={styles.info}>{info}</Text>}

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
  pwTabs: { flexDirection: 'row', gap: 8 },
  pwTab: { flex: 1, alignItems: 'center', paddingVertical: 10, borderWidth: 1.5, borderColor: 'rgba(255,255,255,0.35)' },
  pwTabActive: { borderColor: C.onInverse, backgroundColor: 'rgba(255,255,255,0.10)' },
  pwTabText: { color: C.onInverse, opacity: 0.6, fontSize: 11.5, fontWeight: '800', letterSpacing: 1.5 },
  pwTabTextActive: { opacity: 1 },
  pwInput: { borderWidth: 1.5, borderColor: 'rgba(255,255,255,0.4)', color: C.onInverse, paddingHorizontal: 14, minHeight: 50, fontSize: 14, backgroundColor: 'rgba(0,0,0,0.45)' },
  pwRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  pwEye: { borderWidth: 1.5, borderColor: 'rgba(255,255,255,0.4)', minHeight: 50, minWidth: 50, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(0,0,0,0.45)' },
  orRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginVertical: 2 },
  orLine: { flex: 1, height: 1, backgroundColor: 'rgba(255,255,255,0.25)' },
  orText: { color: C.onInverse, opacity: 0.6, fontSize: 10, letterSpacing: 2, fontWeight: '800' },
  googleBtn: { flexDirection: 'row', gap: 10, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: 'rgba(255,255,255,0.6)', paddingVertical: 16, minHeight: 52 },
  googleBtnText: { color: C.onInverse, fontSize: 13.5, fontWeight: '900', letterSpacing: 1.5 },
  signBtn: { backgroundColor: C.onInverse, paddingVertical: 18, alignItems: 'center', borderWidth: 2, borderColor: C.onInverse, minHeight: 54 },
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
  info: { color: '#7BE0AD', fontSize: 11, textAlign: 'center', marginTop: 6, fontWeight: '700' },
  resetTitle: { color: C.onInverse, fontSize: 12, fontWeight: '900', letterSpacing: 2, textAlign: 'center', paddingVertical: 6 },
  linkRow: { flexDirection: 'row', justifyContent: 'center', gap: 24, paddingVertical: 2 },
  footer: { color: C.onInverse, opacity: 0.6, fontSize: 10, letterSpacing: 2, textAlign: 'center', marginTop: 6 },
  footerArt50: { color: C.onInverse, opacity: 0.45, fontSize: 8, letterSpacing: 1, textAlign: 'center', marginTop: 2 },
  rtl: { writingDirection: 'rtl', textAlign: 'right' },
});
