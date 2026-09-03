/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// DURESS PROTOCOL — decoy PIN (empty vault) + silent alarm
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { C, S } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

export default function Duress() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const [status, setStatus] = useState<any>(null);
  const [realPin, setRealPin] = useState('');
  const [duressPin, setDuressPin] = useState('');
  const [testPin, setTestPin] = useState('');
  const [testResult, setTestResult] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    try { setStatus(await api('/duress/status')); } catch (e) { console.log(e); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setBusy('save'); setErr(''); setMsg('');
    try {
      const r: any = await api('/duress/pin', { method: 'PUT', body: JSON.stringify({ real_pin: realPin, duress_pin: duressPin }) });
      setMsg(r.note); setRealPin(''); setDuressPin('');
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const test = async () => {
    setBusy('test'); setErr(''); setTestResult(null);
    try {
      const r: any = await api('/duress/verify', { method: 'POST', body: JSON.stringify({ pin: testPin }) });
      setTestResult(r); setTestPin('');
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  return (
    <SafeAreaView testID="duress-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="du-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={st.title}>{tt('duress.duress_protokol')}</Text>
        <View style={{ width: 26 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        <View style={st.heroIcon}><Ionicons name="hand-left-outline" size={28} color={C.error} /></View>
        <Text style={st.h1}>{tt('duress.protection_under_duress')}</Text>
        <Text style={st.sub}>
          {tt('duress.set_two_pin_codes_the_real_pin_unloc')}
        </Text>

        <View style={[st.stateCard, { borderColor: status?.configured ? C.brand : C.borderStrong }]}>
          <Ionicons name={status?.configured ? 'shield-checkmark' : 'shield-outline'} size={20} color={status?.configured ? C.brand : C.info} />
          <Text style={st.stateText}>{status?.configured ? tt('duress.duress_pin_active') : tt('duress.not_set_up_yet')}</Text>
        </View>

        <Text style={st.section}>{tt('duress.set_pin_codes')}</Text>
        <View style={{ flexDirection: 'row', gap: S.sm }}>
          <TextInput testID="du-real" value={realPin} onChangeText={setRealPin} keyboardType="numeric" maxLength={8} secureTextEntry
            placeholder={tt('duress.real_pin')} placeholderTextColor="#777" style={[st.input, { flex: 1 }]} />
          <TextInput testID="du-duress" value={duressPin} onChangeText={setDuressPin} keyboardType="numeric" maxLength={8} secureTextEntry
            placeholder={tt('duress.duress_pin')} placeholderTextColor="#777" style={[st.input, { flex: 1 }]} />
        </View>
        <Pressable testID="du-save" onPress={save} disabled={busy === 'save' || realPin.length < 4 || duressPin.length < 4} style={st.mainBtn}>
          {busy === 'save' ? <ActivityIndicator color={C.onInverse} /> : <Text style={st.mainBtnText}>{tt('duress.activate_the_duress_protocol')}</Text>}
        </Pressable>
        {!!msg && <Text testID="du-msg" style={st.msg}>{msg}</Text>}
        {!!err && <Text testID="du-err" style={st.err}>{err}</Text>}

        {status?.configured && (
          <>
            <Text style={st.section}>{tt('duress.test_the_unlock')}</Text>
            <View style={{ flexDirection: 'row', gap: S.sm }}>
              <TextInput testID="du-test-pin" value={testPin} onChangeText={setTestPin} keyboardType="numeric" maxLength={8} secureTextEntry
                placeholder={tt('duress.zadajte_pin')} placeholderTextColor="#777" style={[st.input, { flex: 1 }]} />
              <Pressable testID="du-test" onPress={test} disabled={busy === 'test' || testPin.length < 4} style={st.testBtn}>
                {busy === 'test' ? <ActivityIndicator size="small" color={C.onInverse} /> : <Text style={st.mainBtnText}>{tt('duress.verify')}</Text>}
              </Pressable>
            </View>
            {testResult && (
              <View testID="du-test-result" style={[st.resultCard, {
                borderColor: testResult.vault_mode === 'full' ? C.brand : testResult.vault_mode === 'decoy' ? C.warn : C.error,
              }]}>
                {testResult.vault_mode === 'full' && <Text style={[st.resultText, { color: C.brand }]}>{tt('duress.full_vault_real_pin_recognized')}</Text>}
                {testResult.vault_mode === 'decoy' && <Text style={[st.resultText, { color: C.warn }]}>{tt('duress.decoy_mode_an_empty_vault_would_be_s')}</Text>}
                {testResult.vault_mode === 'invalid' && <Text style={[st.resultText, { color: C.error }]}>{tt('duress.invalid_pin')}</Text>}
              </View>
            )}
          </>
        )}

        <Text style={st.section}>{tt('duress.silent_alarms')}{status?.alarms?.length ?? 0})</Text>
        {(status?.alarms ?? []).length === 0 && <Text style={st.empty}>{tt('duress.no_security_events')}</Text>}
        {(status?.alarms ?? []).map((a: any) => (
          <View key={a.event_id} style={st.alarmCard}>
            <Ionicons name="alert-circle" size={16} color={C.error} />
            <Text style={st.alarmText}>{tt('duress.silent_alarm')} {new Date(a.at).toLocaleString('en-GB')}</Text>
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  heroIcon: { width: 56, height: 56, borderWidth: 1.5, borderColor: C.error, alignItems: 'center', justifyContent: 'center', marginBottom: S.md },
  h1: { color: C.fg, fontSize: 20, fontWeight: '900', letterSpacing: 0.5 },
  sub: { color: C.onS3, fontSize: 12, lineHeight: 18, marginTop: S.sm },
  stateCard: { flexDirection: 'row', alignItems: 'center', gap: S.sm, borderWidth: 1.5, padding: S.md, marginTop: S.lg, backgroundColor: C.surface2 },
  stateText: { color: C.fg, fontWeight: '900', fontSize: 12, letterSpacing: 1 },
  section: { color: C.info, fontSize: 11, fontWeight: '900', letterSpacing: 2, marginTop: S.xl, marginBottom: S.sm },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 14, color: C.fg, backgroundColor: C.surface2 },
  mainBtn: { backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center', minHeight: 52, marginTop: S.md },
  mainBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  testBtn: { backgroundColor: C.brand, paddingHorizontal: S.lg, justifyContent: 'center', minHeight: 48 },
  msg: { color: C.brand, fontWeight: '800', fontSize: 12, marginTop: S.md, lineHeight: 18 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginTop: S.sm },
  resultCard: { borderWidth: 2, padding: S.md, marginTop: S.md, backgroundColor: C.surface2 },
  resultText: { fontWeight: '900', fontSize: 12, lineHeight: 18 },
  empty: { textAlign: 'center', color: C.info, marginTop: S.lg, letterSpacing: 2, fontWeight: '800', fontSize: 11 },
  alarmCard: { flexDirection: 'row', alignItems: 'center', gap: S.sm, borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginTop: S.sm, backgroundColor: C.surface2 },
  alarmText: { color: C.onS3, fontSize: 12 },
});
