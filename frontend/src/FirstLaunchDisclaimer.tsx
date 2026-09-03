/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// FIRST-LAUNCH DISCLAIMER — dismissible card shown once per device after sign-in with
// the two critical notices (not a medical device · does not replace 112). Localized via
// useI18n so it switches with the UI language.
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, Modal } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { C, S, R } from './theme';
import { useI18n } from './i18n-context';
import { LEGAL_VERSION } from './legal';

const KEY = `ga.disclaimer.seen.${LEGAL_VERSION}`;

export default function FirstLaunchDisclaimer() {
  const { t, rtl } = useI18n();
  const router = useRouter();
  const [show, setShow] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem(KEY).then(v => { if (!v) setShow(true); }).catch(() => {});
  }, []);

  const dismiss = () => {
    setShow(false);
    AsyncStorage.setItem(KEY, new Date().toISOString()).catch(() => {});
  };

  if (!show) return null;
  return (
    <Modal transparent animationType="fade" visible onRequestClose={dismiss}>
      <View style={st.backdrop}>
        <View testID="first-launch-disclaimer" style={st.card}>
          <View style={st.head}>
            <Ionicons name="warning-outline" size={22} color={C.brand} />
            <Text style={st.title}>{t('disclaimer.card_title')}</Text>
          </View>
          <View style={st.row}>
            <Ionicons name="medkit-outline" size={18} color={C.fg} />
            <Text style={[st.text, rtl && st.rtl]}>{t('disclaimer.medical_short')}</Text>
          </View>
          <View style={st.row}>
            <Ionicons name="call-outline" size={18} color={C.error} />
            <Text style={[st.text, rtl && st.rtl]}>{t('disclaimer.emergency_short')}</Text>
          </View>
          <Pressable testID="disclaimer-ok" onPress={dismiss} style={st.okBtn}>
            <Text style={st.okText}>{t('disclaimer.i_understand')}</Text>
          </Pressable>
          <Pressable testID="disclaimer-terms" onPress={() => { dismiss(); router.push('/terms-of-service'); }} style={st.linkBtn}>
            <Text style={st.linkText}>{t('disclaimer.read_terms')}</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const st = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.72)', justifyContent: 'flex-end', padding: S.lg },
  card: { backgroundColor: C.surface2, borderRadius: R.lg, borderWidth: 1.5, borderColor: C.brand, padding: S.lg, gap: S.md, marginBottom: S.lg },
  head: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  title: { color: C.brand, fontWeight: '900', letterSpacing: 1.5, fontSize: 13, flex: 1 },
  row: { flexDirection: 'row', gap: 10, alignItems: 'flex-start' },
  text: { color: C.fg, fontSize: 13.5, lineHeight: 20, flex: 1, fontWeight: '600' },
  rtl: { writingDirection: 'rtl', textAlign: 'right' },
  okBtn: { backgroundColor: C.brand, minHeight: 52, borderRadius: R.md, alignItems: 'center', justifyContent: 'center', marginTop: 4 },
  okText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 14 },
  linkBtn: { minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  linkText: { color: C.brand, fontWeight: '800', letterSpacing: 1, fontSize: 12, textDecorationLine: 'underline' },
});
