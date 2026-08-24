/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, Pressable, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';

const TOTAL = 30;

export default function FallVerify() {
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const router = useRouter();
  const [remain, setRemain] = useState(TOTAL);
  const [phase, setPhase] = useState<'countdown' | 'sent' | 'ok'>('countdown');
  const timer = useRef<any>(null);

  useEffect(() => {
    timer.current = setInterval(() => {
      setRemain(r => {
        if (r <= 1) { clearInterval(timer.current); triggerSent(); return 0; }
        if (Platform.OS !== 'web') {
          if (r <= 10) Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
          else if (r <= 20) Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
          else Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
        }
        return r - 1;
      });
    }, 1000);
    return () => clearInterval(timer.current);
  }, []);

  const triggerSent = async () => {
    setPhase('sent');
    try { await api('/fall-event', { method: 'POST', body: JSON.stringify({ verified: true, cancelled: false }) }); } catch {}
  };

  const cancel = async () => {
    clearInterval(timer.current);
    setPhase('ok');
    if (Platform.OS !== 'web') Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    try { await api('/fall-event', { method: 'POST', body: JSON.stringify({ verified: false, cancelled: true }) }); } catch {}
    setTimeout(() => router.back(), 900);
  };

  const helpNow = async () => {
    clearInterval(timer.current);
    triggerSent();
  };

  const bg = remain <= 10 ? C.error : C.warn;
  const fg = remain <= 10 ? C.onError : C.onWarn;

  if (phase === 'ok') {
    return (
      <View testID="fall-ok" style={[styles.root, { backgroundColor: C.brandPri }]}>
        <Ionicons name="checkmark-circle" size={80} color={C.onInverse} />
        <Text style={[styles.big, { color: C.onInverse }]}>OK</Text>
      </View>
    );
  }
  if (phase === 'sent') {
    return (
      <SafeAreaView testID="fall-sent" style={[styles.root, { backgroundColor: C.error }]}>
        <Ionicons name="alert" size={80} color={C.onError} />
        <Text style={[styles.big, { color: C.onError }]}>{t('get_help_now', lang).toUpperCase()}</Text>
        <Text style={[styles.subBig, { color: C.onError }]}>NOTIFYING FAMILY & CONTACTS</Text>
        <Pressable testID="fall-back" onPress={() => router.back()} style={styles.exitBtn}>
          <Text style={styles.exitBtnText}>DISMISS</Text>
        </Pressable>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView testID="fall-verify-screen" style={[styles.root, { backgroundColor: bg }]}>
      <Pressable testID="fall-help-now" onPress={helpNow} style={[styles.topBtn, { borderColor: fg }]}>
        <Ionicons name="alert-circle-outline" size={20} color={fg} />
        <Text style={[styles.topBtnText, { color: fg }]}>{t('get_help_now', lang).toUpperCase()}</Text>
      </Pressable>

      <View style={styles.center}>
        <Text style={[styles.fallLabel, { color: fg }]}>{t('fall_detected', lang).toUpperCase()}</Text>
        <Text style={[styles.countdown, { color: fg }]}>{remain.toString().padStart(2, '0')}</Text>
        <Text style={[styles.subBig, { color: fg }]}>SECONDS TO CANCEL</Text>
      </View>

      <Pressable testID="fall-im-ok" onPress={cancel} style={styles.okBtn}>
        <Text style={styles.okBtnText}>{t('im_ok', lang).toUpperCase()}</Text>
      </Pressable>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, justifyContent: 'space-between', alignItems: 'center', padding: S.lg },
  topBtn: { flexDirection: 'row', alignItems: 'center', gap: 8, borderWidth: 2, paddingHorizontal: S.lg, paddingVertical: S.md, alignSelf: 'stretch', justifyContent: 'center', marginTop: S.md },
  topBtnText: { fontWeight: '900', letterSpacing: 2, fontSize: 14 },
  center: { alignItems: 'center', gap: S.md },
  fallLabel: { fontSize: 18, fontWeight: '900', letterSpacing: 3 },
  countdown: { fontSize: 140, fontWeight: '900', fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }), letterSpacing: 2 },
  subBig: { fontSize: 14, letterSpacing: 3, fontWeight: '800' },
  big: { fontSize: 40, fontWeight: '900', letterSpacing: 3, marginTop: S.lg },
  okBtn: { alignSelf: 'stretch', backgroundColor: '#000', paddingVertical: 40, alignItems: 'center', borderWidth: 3, borderColor: '#000', marginBottom: S.md },
  okBtnText: { color: '#FFF', fontSize: 34, fontWeight: '900', letterSpacing: 3 },
  exitBtn: { marginTop: S.xl, borderWidth: 2, borderColor: C.onError, paddingHorizontal: S.xl, paddingVertical: S.md },
  exitBtnText: { color: C.onError, fontWeight: '900', letterSpacing: 2 },
});
