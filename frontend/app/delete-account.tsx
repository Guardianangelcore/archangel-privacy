/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// DATA DELETION — PUBLIC page (no login), required by Google Play "Data deletion" & Apple 5.1.1(v).
// Two paths: in-app (Profile → Delete account, immediate) or this form (e-mail → Founder processes within 30 days).
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator, KeyboardAvoidingView, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api, errMsg } from '@/src/api';
import { C, S, R } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/;

export default function DeleteAccount() {
  const { t: tt } = useI18n();
  const router = useRouter();
  const [policy, setPolicy] = useState<{ processing_days: number; erased: string[]; retained: string[] } | null>(null);
  const [email, setEmail] = useState('');
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [done, setDone] = useState<{ req_id: string; processing_days: number } | null>(null);

  useEffect(() => { api('/account/deletion-policy').then(setPolicy).catch(() => {}); }, []);

  const submit = async () => {
    setErr(''); setBusy(true);
    try {
      const r: any = await api('/account/deletion-request', { method: 'POST', body: JSON.stringify({ email: email.trim(), reason: reason.trim() }) });
      setDone({ req_id: r.req_id, processing_days: r.processing_days });
    } catch (e) { setErr(errMsg(e)); }
    finally { setBusy(false); }
  };

  const goBack = () => { if (router.canGoBack()) router.back(); else router.replace('/login'); };
  const days = policy?.processing_days ?? 30;

  return (
    <SafeAreaView testID="delete-account-screen" style={st.root} edges={['top', 'bottom']}>
      <View style={st.header}>
        <Pressable testID="da-back" onPress={goBack} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.fg} />
        </Pressable>
        <Text style={st.title}>{tt('delete_account.title')}</Text>
        <View style={{ width: 26 }} />
      </View>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 80 }} keyboardShouldPersistTaps="handled">
          <Text style={st.meta}>Archangel OS · Guardian Angel Sovereign Foundation (DAO) · guardianangel.core@proton.me</Text>
          <Text style={st.lead}>{tt('delete_account.lead')}</Text>

          <View style={st.box}>
            <View style={st.boxHead}>
              <Ionicons name="phone-portrait-outline" size={18} color={C.brand} />
              <Text style={st.boxTitle}>{tt('delete_account.in_app_title')}</Text>
            </View>
            <Text style={st.p}>{tt('delete_account.in_app_steps')}</Text>
          </View>

          <View style={st.box}>
            <View style={st.boxHead}>
              <Ionicons name="mail-outline" size={18} color={C.brand} />
              <Text style={st.boxTitle}>{tt('delete_account.request_title')}</Text>
            </View>
            {done ? (
              <View testID="da-done">
                <Text style={st.ok}>{tt('delete_account.done', { days: done.processing_days })}</Text>
                <Text style={st.ref}>{tt('delete_account.reference')} {done.req_id}</Text>
              </View>
            ) : (
              <>
                <Text style={st.p}>{tt('delete_account.request_text', { days })}</Text>
                <TextInput
                  testID="da-email"
                  value={email}
                  onChangeText={setEmail}
                  placeholder={tt('delete_account.email_placeholder')}
                  placeholderTextColor={C.info}
                  keyboardType="email-address"
                  autoCapitalize="none"
                  autoCorrect={false}
                  style={st.input}
                />
                <TextInput
                  testID="da-reason"
                  value={reason}
                  onChangeText={setReason}
                  placeholder={tt('delete_account.reason_placeholder')}
                  placeholderTextColor={C.info}
                  multiline
                  maxLength={500}
                  style={[st.input, { minHeight: 80, paddingTop: 12 }]}
                />
                {!!err && <Text testID="da-err" style={st.err}>{err}</Text>}
                <Pressable
                  testID="da-submit"
                  onPress={submit}
                  disabled={busy || !EMAIL_RE.test(email.trim())}
                  style={[st.cta, (busy || !EMAIL_RE.test(email.trim())) && { opacity: 0.5 }]}
                >
                  {busy ? <ActivityIndicator color={C.onInverse} /> : (
                    <>
                      <Ionicons name="trash-outline" size={18} color={C.onInverse} />
                      <Text style={st.ctaText}>{tt('delete_account.submit')}</Text>
                    </>
                  )}
                </Pressable>
              </>
            )}
          </View>

          <Text style={st.secTitle}>{tt('delete_account.erased_title')}</Text>
          {(policy?.erased || []).map((x) => <Text key={x} style={st.bullet}>•  {x}</Text>)}
          <Text style={st.secTitle}>{tt('delete_account.retained_title')}</Text>
          {(policy?.retained || []).map((x) => <Text key={x} style={st.bullet}>•  {x}</Text>)}
          <Text style={st.p}>{tt('delete_account.timeline', { days })}</Text>

          <Pressable testID="da-privacy" onPress={() => router.push('/privacy-policy')} style={st.linkBtn}>
            <Ionicons name="lock-closed-outline" size={16} color={C.brand} />
            <Text style={st.linkBtnText}>{tt('privacy_policy.privacy_policy')}</Text>
          </Pressable>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 2, fontSize: 14 },
  meta: { color: C.info, fontSize: 10.5, letterSpacing: 0.5, marginBottom: S.sm },
  lead: { color: C.fg, fontSize: 13.5, lineHeight: 21, fontWeight: '600', marginBottom: S.md },
  box: { borderWidth: 1.5, borderColor: 'rgba(212,175,55,0.45)', backgroundColor: 'rgba(212,175,55,0.06)', borderRadius: R.md, padding: S.lg, marginTop: S.md, gap: S.sm },
  boxHead: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  boxTitle: { color: C.brand, fontWeight: '900', fontSize: 12, letterSpacing: 1.5 },
  p: { color: C.fg, fontSize: 13, lineHeight: 20 },
  input: { minHeight: 48, color: C.fg, paddingHorizontal: S.md, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, backgroundColor: C.surface2, fontSize: 14 },
  cta: { flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.error, borderRadius: R.sm, minHeight: 50 },
  ctaText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
  err: { color: C.error, fontSize: 12, fontWeight: '700' },
  ok: { color: C.accent, fontSize: 13.5, lineHeight: 20, fontWeight: '700' },
  ref: { color: C.info, fontSize: 11, marginTop: 6, letterSpacing: 0.5 },
  secTitle: { color: C.brand, fontWeight: '900', fontSize: 11.5, letterSpacing: 1.5, marginTop: S.xl, marginBottom: 6 },
  bullet: { color: C.onS3, fontSize: 12.5, lineHeight: 19, marginBottom: 4, paddingLeft: 4 },
  linkBtn: { flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', borderWidth: 1.5, borderColor: C.brand, borderRadius: R.sm, minHeight: 48, marginTop: S.xl },
  linkBtnText: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 1.5 },
});
