/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// GUARDIAN EYE — always-visible camera FAB shown on every pillar hub.
// One-tap opens /lens for zero-UI OCR & vision analysis (pill, document, sign, etc.).
// Discreet: fixed bottom-right, matches the brutalist theme, respects safe area.
import React from 'react';
import { Pressable, StyleSheet, Text, View, Platform } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { C } from './theme';
import { useI18n } from '@/src/i18n-context';

export function GuardianEyeFAB({ testID = 'guardian-eye', bottom = 24, right = 20 }: {
  testID?: string; bottom?: number; right?: number;
}) {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const insets = useSafeAreaInsets();

  const open = () => {
    try { if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium); } catch {}
    router.push('/lens');
  };

  return (
    <View pointerEvents="box-none" style={[styles.wrap, { bottom: bottom + insets.bottom, right }]}>
      <Pressable
        testID={testID}
        onPress={open}
        style={({ pressed }) => [styles.fab, pressed && { transform: [{ scale: 0.94 }] }]}
        hitSlop={10}
        accessibilityLabel={tt('c_GuardianEye.guardian_eye_camera_for_instant_ocr')}
      >
        <Ionicons name="scan-outline" size={22} color={C.onInverse} />
        <View style={styles.dot} />
      </Pressable>
      <Text style={styles.label}>{tt('c_GuardianEye.eye')}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { position: 'absolute', alignItems: 'center', gap: 4 },
  fab: {
    width: 54, height: 54, borderRadius: 27,
    backgroundColor: C.inverse,
    borderWidth: 2, borderColor: C.brand,
    alignItems: 'center', justifyContent: 'center',
    shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.35, shadowRadius: 6,
    elevation: 6,
  },
  dot: { position: 'absolute', top: 8, right: 10, width: 6, height: 6, borderRadius: 3, backgroundColor: C.brand },
  label: { fontSize: 8.5, letterSpacing: 2, fontWeight: '900', color: C.brand },
});
