/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// SENTIENT BIOMETRIC GATE — FaceID / Fingerprint / Iris re-auth on app open.
// Runs AFTER Google OAuth (Emergent) succeeds and after every cold start.
// Fails soft on: web, hardware-less devices, disabled biometrics, or opt-out.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ActivityIndicator, AppState, Platform, Linking } from 'react-native';
import Ionicons from '@react-native-vector-icons/ionicons';
import * as LocalAuthentication from 'expo-local-authentication';
import { useAuth } from './auth';
import { speak } from './voice';
import { stageFromUser, jarvisToneFor } from './age';
import { C, S, R } from './theme';
import { useI18n } from '@/src/i18n-context';

const UNLOCK_GRACE_MS = 60 * 1000; // don't re-prompt if you unlocked within the last minute

async function isBiometryAvailable(): Promise<boolean> {
  if (Platform.OS === 'web') return false;
  try {
    const hasHw = await LocalAuthentication.hasHardwareAsync();
    if (!hasHw) return false;
    const enrolled = await LocalAuthentication.isEnrolledAsync();
    return enrolled;
  } catch { return false; }
}

async function biometryLabel(): Promise<string> {
  try {
    const types = await LocalAuthentication.supportedAuthenticationTypesAsync();
    if (types.includes(LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION)) return 'FaceID';
    if (types.includes(LocalAuthentication.AuthenticationType.FINGERPRINT)) return 'Fingerprint';
    if (types.includes(LocalAuthentication.AuthenticationType.IRIS)) return 'Iris';
  } catch {}
  return 'Biometrics';
}

export function BiometricGate({ children }: { children: React.ReactNode }) {
  const { t: tt, tx } = useI18n();
  const { user, signOut } = useAuth();
  const enabled = !!user?.biometric_enabled;
  const [unlocked, setUnlocked] = useState(false);
  const [prompting, setPrompting] = useState(false);
  const [err, setErr] = useState('');
  const [label, setLabel] = useState('FaceID');
  const [available, setAvailable] = useState<boolean | null>(null);
  const lastUnlockRef = useRef(0);
  const greetedRef = useRef(false);

  // Detect biometry once per user session.
  useEffect(() => {
    (async () => {
      const ok = await isBiometryAvailable();
      setAvailable(ok);
      if (ok) setLabel(await biometryLabel());
    })();
  }, [user?.user_id]);

  const authenticate = useCallback(async () => {
    setErr(''); setPrompting(true);
    try {
      const res = await LocalAuthentication.authenticateAsync({
        promptMessage: 'Odomknite Guardian Angel',
        cancelLabel: 'Cancel',
        fallbackLabel: 'Use PIN',
        disableDeviceFallback: false,
      });
      if (res.success) {
        setUnlocked(true);
        lastUnlockRef.current = Date.now();
        // Warm voice greeting on first unlock of the session — Jarvis welcomes back.
        if (!greetedRef.current) {
          greetedRef.current = true;
          const stage = stageFromUser(user);
          // Founder directive: default greeting is "Guardian Angel" — never a raw email/first-name.
          const displayName = (user?.name && user.name.trim() && user.name.trim() !== user?.email)
            ? user.name.split(' ')[0]
            : 'Guardian Angel';
          speak(`Welcome home, ${displayName}. I am your Jarvis.`, {
            mood: jarvisToneFor(stage),
            language: (user?.language as any) || 'en',
          });
        }
      } else {
        // User cancelled or failed — stay locked; show retry.
        setErr(res.error ? 'Verification failed. Try again.' : 'Unlock cancelled.');
      }
    } catch (e: any) {
      setErr(String(e?.message || e));
    } finally {
      setPrompting(false);
    }
  }, [user?.user_id]);

  // Auto-prompt when the gate first mounts with biometry enabled.
  useEffect(() => {
    if (!enabled || available !== true || unlocked || prompting) return;
    authenticate();
  }, [enabled, available, unlocked, prompting, authenticate]);

  // Re-lock on app going background (>60s) — Apple/Tesla-grade privacy.
  useEffect(() => {
    if (!enabled || available !== true) return;
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'background') {
        // remember the timestamp; if user resumes >60s later, re-prompt
        lastUnlockRef.current = 0;
      } else if (state === 'active' && unlocked && lastUnlockRef.current === 0) {
        setUnlocked(false);
      }
    });
    return () => sub.remove();
  }, [enabled, available, unlocked]);

  // No gate → pass-through.
  if (!enabled) return <>{children}</>;
  // Hardware unavailable → soft-fail gracefully (do NOT block the user).
  if (available === false) return <>{children}</>;
  // Still probing → tiny splash so we don't flash unauthenticated content.
  if (available === null) {
    return (
      <View style={styles.root}>
        <ActivityIndicator color={C.brand} size="large" />
      </View>
    );
  }

  if (unlocked) return <>{children}</>;

  // Locked screen — warm, single-purpose, apple-grade.
  return (
    <View testID="biometric-gate" style={styles.root}>
      <View style={styles.iconRing}>
        <Ionicons name={label === 'FaceID' ? 'scan-outline' : 'finger-print'} size={72} color={C.brand} />
      </View>
      <Text style={styles.brand}>{tt('c_biometric_gate.guardian')}</Text>
      <Text style={styles.tag}>{tt('c_biometric_gate.unlock_with_your_personal_signal')}</Text>
      <Text style={styles.method}>{label.toUpperCase()}</Text>
      {!!err && <Text style={styles.err}>{err}</Text>}
      <Pressable testID="biometric-unlock" onPress={authenticate} disabled={prompting} style={styles.cta}>
        {prompting ? <ActivityIndicator color={C.onInverse} /> : (
          <>
            <Ionicons name="lock-open" size={18} color={C.onInverse} />
            <Text style={styles.ctaText}>{tt('c_biometric_gate.unlock')}</Text>
          </>
        )}
      </Pressable>
      <Pressable testID="biometric-signout" onPress={signOut} style={styles.ghost}>
        <Text style={styles.ghostText}>{tt('c_biometric_gate.sign_in_with_another_account')}</Text>
      </Pressable>
      {Platform.OS !== 'web' && (
        <Pressable onPress={() => Linking.openSettings()} hitSlop={10}>
          <Text style={styles.hint}>{tt('c_biometric_gate.nastavenia_biometrie')}</Text>
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg, alignItems: 'center', justifyContent: 'center', padding: S.xl, gap: S.md },
  iconRing: { width: 130, height: 130, borderRadius: 65, borderWidth: 2, borderColor: C.brand, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(212,175,55,0.08)' },
  brand: { color: C.fg, fontSize: 26, fontWeight: '900', letterSpacing: 4, marginTop: S.lg },
  tag: { color: C.info, fontSize: 11, letterSpacing: 2, marginTop: 4 },
  method: { color: C.brand, fontSize: 13, letterSpacing: 3, fontWeight: '900', marginTop: S.md },
  err: { color: C.error, fontSize: 12, textAlign: 'center', marginTop: S.sm },
  cta: { flexDirection: 'row', gap: 8, marginTop: S.xl, backgroundColor: C.brand, borderRadius: R.pill, paddingHorizontal: S.xxl, minHeight: 56, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 14 },
  ghost: { minHeight: 44, alignItems: 'center', justifyContent: 'center', marginTop: S.md },
  ghostText: { color: C.info, fontSize: 12, letterSpacing: 1 },
  hint: { color: C.onS3, fontSize: 10, letterSpacing: 1, marginTop: S.md },
});
