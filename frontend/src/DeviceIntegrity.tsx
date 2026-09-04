/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// DEVICE INTEGRITY — root / jailbreak detection at startup (expo-device). A compromised OS means the
// Keychain, biometrics and the SOS pipeline cannot be trusted: the user is warned once per launch and
// the result is reported to the backend (users.device_integrity + security_events).
// Hardware attestation (Google Play Integrity / Apple App Attest) requires a native build + store
// credentials and is layered on top of this check when the build is generated.
import React, { useEffect, useRef, useState } from 'react';
import { View, Text, Modal, Pressable, StyleSheet, Platform } from 'react-native';
import * as Device from 'expo-device';
import Ionicons from '@react-native-vector-icons/ionicons';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { useI18n } from '@/src/i18n-context';
import { C, S, R } from '@/src/theme';

export async function checkDeviceIntegrity(): Promise<{ rooted: boolean; platform: string; model: string | null; os_version: string | null; is_device: boolean }> {
  let rooted = false;
  if (Platform.OS !== 'web') {
    try { rooted = await Device.isRootedExperimentalAsync(); } catch { rooted = false; }
  }
  return { rooted, platform: Platform.OS, model: Device.modelName ?? null, os_version: Device.osVersion ?? null, is_device: !!Device.isDevice };
}

export function DeviceIntegrityGuard() {
  const { t: tt } = useI18n();
  const { user } = useAuth();
  const [rooted, setRooted] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const reported = useRef(false);
  const result = useRef<Awaited<ReturnType<typeof checkDeviceIntegrity>> | null>(null);

  useEffect(() => {
    checkDeviceIntegrity().then(r => { result.current = r; setRooted(r.rooted); });
  }, []);

  // Report once per launch as soon as a session exists (works offline-tolerant: failures are ignored).
  useEffect(() => {
    if (!user?.user_id || !result.current || reported.current) return;
    reported.current = true;
    api('/security/device-integrity', { method: 'POST', body: JSON.stringify(result.current) }).catch(() => {});
  }, [user?.user_id, rooted]);

  if (!rooted || dismissed) return null;
  return (
    <Modal visible transparent animationType="fade" onRequestClose={() => setDismissed(true)}>
      <View style={st.backdrop}>
        <View style={st.card} testID="device-integrity-warning">
          <Ionicons name="warning" size={34} color={C.warn} />
          <Text style={st.title}>{tt('integrity.title')}</Text>
          <Text style={st.body}>{tt('integrity.body')}</Text>
          <Pressable testID="device-integrity-continue" onPress={() => setDismissed(true)} style={st.btn}>
            <Text style={st.btnText}>{tt('integrity.continue')}</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const st = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: C.surface3, alignItems: 'center', justifyContent: 'center', padding: S.lg },
  card: { backgroundColor: C.bg, borderWidth: 1.5, borderColor: C.warn, borderRadius: R.lg, padding: S.xl, gap: S.md, alignItems: 'center', width: '100%', maxWidth: 420 },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 1.5, fontSize: 14, textAlign: 'center' },
  body: { color: C.onS3, fontSize: 13, lineHeight: 19, textAlign: 'center' },
  btn: { backgroundColor: C.warn, borderRadius: R.sm, minHeight: 48, paddingHorizontal: S.xl, alignItems: 'center', justifyContent: 'center', alignSelf: 'stretch' },
  btnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.2 },
});
