/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// Family & Seniors Onboarding — warm 3-step guide (guardian link · Jarvis · QR Talisman)
import React, { useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, TextInput, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { api } from '@/src/api';
import { C, S } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

const STEPS = [
  { icon: 'people', title: 'Link with your guardian', color: '#5FA779' },
  { icon: 'chatbubbles', title: 'How to talk to Jarvis', color: '#B8860B' },
  { icon: 'qr-code', title: 'Your emergency QR & Talisman', color: '#C25450' },
];

export default function Onboarding() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [contact, setContact] = useState('');
  const [linked, setLinked] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const linkGuardian = async () => {
    setBusy(true); setErr('');
    try {
      const g: any = await api('/recovery-suite/guardians', { method: 'POST', body: JSON.stringify({ contact: contact.trim() }) });
      setLinked(g.guardian_name || contact.trim());
    } catch (e: any) {
      const m = String(e.message || e);
      setErr(m.includes('already') ? 'This guardian is already linked ✓' : m);
      if (m.includes('already')) setLinked(contact.trim());
    } finally { setBusy(false); }
  };

  const finish = async () => {
    await AsyncStorage.setItem('gh_onboarding_done', '1');
    router.replace('/(tabs)');
  };

  const s = STEPS[step];

  return (
    <SafeAreaView testID="onboarding-screen" style={st.root} edges={['top', 'bottom']}>
      <ScrollView contentContainerStyle={{ padding: S.xl, flexGrow: 1 }}>
        <View style={st.dots}>
          {STEPS.map((_, i) => <View key={i} style={[st.dot, i === step && { backgroundColor: STEPS[step].color, width: 26 }]} />)}
        </View>

        <View style={[st.iconWrap, { borderColor: s.color }]}>
          <Ionicons name={s.icon as any} size={56} color={s.color} />
        </View>
        <Text style={st.stepNo}>{tt('onboarding.step')} {step + 1} {tt('onboarding.of_3')}</Text>
        <Text style={st.title}>{tx(s.title)}</Text>

        {step === 0 && (
          <View>
            <Text style={st.body}>{tt('onboarding.a_guardian_is_a_family_member_you_tr')} <Text style={st.bold}>{tt('onboarding.your_guardian_angel')}</Text>{tt('onboarding.whenever_anything_happens_they_get_a')}</Text>
            {linked ? (
              <View style={st.okBox}>
                <Ionicons name="checkmark-circle" size={22} color="#5FA779" />
                <Text style={st.okText}>{tt('onboarding.linked_with_guardian')} {linked.toUpperCase()} ✓</Text>
              </View>
            ) : (
              <>
                <Text style={st.lbl}>{tt('onboarding.guardian_e_mail')}</Text>
                <View style={{ flexDirection: 'row', gap: S.sm }}>
                  <TextInput testID="ob-contact" value={contact} onChangeText={setContact} placeholder="guardian@family.com"
                    autoCapitalize="none" keyboardType="email-address" placeholderTextColor="#999" style={[st.input, { flex: 1 }]} />
                  <Pressable testID="ob-link" onPress={linkGuardian} disabled={busy || !contact.trim()} style={st.linkBtn}>
                    {busy ? <ActivityIndicator color={C.onInverse} size="small" /> : <Ionicons name="link" size={22} color={C.onInverse} />}
                  </Pressable>
                </View>
                {!!err && <Text style={st.err}>{err}</Text>}
                <Text style={st.hint}>{tt('onboarding.the_guardian_also_needs_the_guardian')}</Text>
              </>
            )}
          </View>
        )}

        {step === 1 && (
          <View>
            <Text style={st.body}>{tt('onboarding.jarvis_is_your_personal_helper_write')} <Text style={st.bold}>{tt('onboarding.completely_naturally_like_to_a_grand')}</Text>:</Text>
            {['"Jarvis, my knee hurts, what should I do?"',
              '"Translate this doctor report into plain language."',
              '"Remind me of my blood pressure pill every morning at eight."'].map((ex, i) => (
              <View key={i} style={st.exampleBox}>
                <Ionicons name="chatbubble-ellipses-outline" size={18} color="#B8860B" />
                <Text style={st.exampleText}>{ex}</Text>
              </View>
            ))}
            <Pressable testID="ob-jarvis" onPress={() => router.push('/jarvis')} style={[st.tryBtn, { backgroundColor: '#B8860B' }]}>
              <Text style={st.tryText}>{tt('onboarding.try_jarvis_now')}</Text>
            </Pressable>
            <Text style={st.hint}>{tt('onboarding.jarvis_is_an_ai_it_informs_but_does')}</Text>
          </View>
        )}

        {step === 2 && (
          <View>
            <Text style={st.body}>{tt('onboarding.your')} <Text style={st.bold}>{tt('onboarding.emergency_qr')}</Text> {tt('onboarding.lives_in_your_profile_a_paramedic_sc')}{'\n\n'}<Text style={st.bold}>{tt('onboarding.qr_talisman')}</Text> {tt('onboarding.is_a_paper_recovery_key_for_your_acc')}</Text>
            <Pressable testID="ob-qr" onPress={() => router.push('/emergency-qr')} style={[st.tryBtn, { backgroundColor: '#C25450' }]}>
              <Text style={st.tryText}>{tt('onboarding.show_my_emergency_qr')}</Text>
            </Pressable>
            <Pressable testID="ob-talisman" onPress={() => router.push('/recovery-suite')} style={st.outlineBtn}>
              <Text style={st.outlineText}>{tt('onboarding.print_qr_talisman_recovery')}</Text>
            </Pressable>
          </View>
        )}

        <View style={{ flex: 1 }} />
        <View style={st.navRow}>
          {step > 0 ? (
            <Pressable testID="ob-prev" onPress={() => setStep(step - 1)} style={st.navBack}>
              <Text style={st.navBackText}>{tt('onboarding.back')}</Text>
            </Pressable>
          ) : (
            <Pressable testID="ob-skip" onPress={finish} style={st.navBack}>
              <Text style={st.navBackText}>{tt('onboarding.skip')}</Text>
            </Pressable>
          )}
          <Pressable testID="ob-next" onPress={() => (step < 2 ? setStep(step + 1) : finish())}
            style={[st.navNext, { backgroundColor: s.color }]}>
            <Text style={st.navNextText}>{step < 2 ? tt('onboarding.continue') : tt('onboarding.done_i_am_ready')}</Text>
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  dots: { flexDirection: 'row', gap: 8, justifyContent: 'center', marginBottom: S.xl },
  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: C.surface3 },
  iconWrap: { alignSelf: 'center', width: 110, height: 110, borderRadius: 55, borderWidth: 3, alignItems: 'center', justifyContent: 'center', marginBottom: S.lg },
  stepNo: { textAlign: 'center', color: C.info, fontSize: 11, letterSpacing: 3, fontWeight: '800' },
  title: { textAlign: 'center', color: C.fg, fontSize: 26, fontWeight: '900', marginTop: 6, marginBottom: S.lg, lineHeight: 34 },
  body: { color: C.onS3, fontSize: 16, lineHeight: 26 },
  bold: { fontWeight: '900', color: C.fg },
  lbl: { fontSize: 10, letterSpacing: 2, color: C.info, fontWeight: '800', marginTop: S.lg, marginBottom: 6 },
  input: { borderWidth: 2, borderColor: C.borderStrong, padding: S.lg, fontSize: 16, color: C.fg, backgroundColor: C.surface2 },
  linkBtn: { width: 56, backgroundColor: '#5FA779', alignItems: 'center', justifyContent: 'center' },
  err: { color: '#5FA779', fontWeight: '800', fontSize: 12, marginTop: S.sm },
  hint: { color: C.info, fontSize: 12, marginTop: S.md, lineHeight: 17 },
  okBox: { flexDirection: 'row', gap: S.sm, alignItems: 'center', borderWidth: 2, borderColor: '#5FA779', padding: S.lg, marginTop: S.lg },
  okText: { flex: 1, color: '#5FA779', fontWeight: '900', fontSize: 12, letterSpacing: 0.5 },
  exampleBox: { flexDirection: 'row', gap: S.sm, alignItems: 'center', borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginTop: S.sm, backgroundColor: C.surface2 },
  exampleText: { flex: 1, color: C.fg, fontSize: 14, lineHeight: 20, fontStyle: 'italic' },
  tryBtn: { marginTop: S.lg, alignItems: 'center', paddingVertical: S.lg, minHeight: 56, justifyContent: 'center' },
  tryText: { color: '#FFFFFF', fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  outlineBtn: { marginTop: S.sm, alignItems: 'center', paddingVertical: S.md, minHeight: 48, justifyContent: 'center', borderWidth: 2, borderColor: C.borderStrong },
  outlineText: { color: C.fg, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  navRow: { flexDirection: 'row', gap: S.sm, marginTop: S.xl },
  navBack: { paddingHorizontal: S.lg, justifyContent: 'center', minHeight: 56, borderWidth: 2, borderColor: C.borderStrong },
  navBackText: { color: C.onS3, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  navNext: { flex: 1, alignItems: 'center', justifyContent: 'center', minHeight: 56 },
  navNextText: { color: '#FFFFFF', fontWeight: '900', letterSpacing: 1, fontSize: 13 },
});
