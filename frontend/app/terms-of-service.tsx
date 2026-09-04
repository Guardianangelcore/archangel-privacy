/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// TERMS OF SERVICE — public page (reachable without login, linked from registration)
import React from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { C, S, R } from '@/src/theme';
import { LEGAL_VERSION as VERSION, LEGAL_EFFECTIVE as EFFECTIVE } from '@/src/legal';
import { useI18n } from '@/src/i18n-context';

function Section({ n, title, children }: { n: string; title: string; children: React.ReactNode }) {
  return (
    <View style={st.section}>
      <Text style={st.secTitle}>{n}. {title}</Text>
      {children}
    </View>
  );
}
const P = ({ children }: { children: React.ReactNode }) => <Text style={st.p}>{children}</Text>;
const B = ({ children }: { children: React.ReactNode }) => <Text style={st.bullet}>•  {children}</Text>;

export default function TermsOfService() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const { t, rtl } = useI18n();
  return (
    <SafeAreaView testID="tos-screen" style={st.root} edges={['top', 'bottom']}>
      <View style={st.header}>
        <Pressable testID="tos-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.fg} />
        </Pressable>
        <Text style={st.title}>{tt('terms_of_service.terms_of_service')}</Text>
        <View style={{ width: 26 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 80 }}>
        <Text style={st.meta}>{tt('terms_of_service.version')} {VERSION} {tt('terms_of_service.effective')} {EFFECTIVE}</Text>
        <Text style={st.meta}>Guardian Angel Sovereign Foundation (DAO) · guardian.angel.core@proton.me</Text>

        {/* CONSOLIDATED LEGAL DISCLAIMER — single clause, localized (key disclaimer.general) */}
        <View testID="tos-disclaimer" style={st.discBox}>
          <View style={st.discHead}>
            <Ionicons name="shield-checkmark-outline" size={18} color={C.brand} />
            <Text style={st.discTitle}>{t('disclaimer.title')}</Text>
          </View>
          <Text testID="tos-disclaimer-text" style={[st.discText, rtl && st.rtl]}>{t('disclaimer.general')}</Text>
        </View>

        <Section n="1" title={tt('terms_of_service.acceptance_of_terms')}>
          <P>{tt('terms_of_service.by_creating_an_account_or_using_arch')}</P>
        </Section>

        <Section n="2" title={tt('terms_of_service.the_service')}>
          <P>{tt('terms_of_service.archangel_os_is_a_personal_health_an')}</P>
          <B>{tt('terms_of_service.all_ai_generated_content_jarvis_is_l')}</B>
          <B>{tt('terms_of_service.the_service_does_not_provide_medical')}</B>
          <B>{tt('terms_of_service.medication_information_is_for_refere')}</B>
          <B>{tt('terms_of_service.health_data_tracked_by_this_app_step')}</B>
        </Section>

        <Section n="3" title={tt('terms_of_service.emergency_safety_features')}>
          <P>{tt('terms_of_service.sos_buttons_fall_detection_crisis_hu')}</P>
          <B>{tt('terms_of_service.this_app_does_not_replace_112_999_91')}</B>
          <B>{tt('terms_of_service.automatic_fall_detection_and_the_aco')}</B>
          <B>{tt('terms_of_service.never_rely_on_the_service_as_your_on')}</B>
          <B>{tt('terms_of_service.documents_generated_by_the_service_e')}</B>
        </Section>

        <Section n="4" title={tt('terms_of_service.your_account')}>
          <P>{tt('terms_of_service.you_must_provide_accurate_informatio')}</P>
        </Section>

        <Section n="5" title={tt('terms_of_service.acceptable_use')}>
          <B>{tt('terms_of_service.do_not_misuse_emergency_features_fal')}</B>
          <B>{tt('terms_of_service.do_not_upload_unlawful_content_or_co')}</B>
          <B>{tt('terms_of_service.do_not_attempt_to_breach_probe_or_re')}</B>
        </Section>

        <Section n="6" title={tt('terms_of_service.subscriptions_ga_t_tokens')}>
          <P>{tt('terms_of_service.some_features_require_a_paid_tier_gu')}</P>
          <B>{tt('terms_of_service.ga_t_tokens_are_not_financial_instru')}</B>
        </Section>

        <Section n="7" title={tt('terms_of_service.intellectual_property')}>
          <P>{tt('terms_of_service.the_service_its_design_and_its_logic')}</P>
        </Section>

        <Section n="8" title={tt('terms_of_service.limitation_of_liability')}>
          <P>{tt('terms_of_service.to_the_maximum_extent_permitted_by_l')}</P>
        </Section>

        <Section n="9" title={tt('terms_of_service.termination')}>
          <P>{tt('terms_of_service.you_may_delete_your_account_at_any_t')}</P>
        </Section>

        <Section n="10" title={tt('terms_of_service.changes_governing_law')}>
          <P>{tt('terms_of_service.we_may_update_these_terms_material_c')}</P>
        </Section>

        <Pressable testID="tos-privacy-link" onPress={() => router.push('/privacy-policy')} style={st.linkBtn}>
          <Ionicons name="shield-checkmark-outline" size={16} color={C.brand} />
          <Text style={st.linkBtnText}>{tt('terms_of_service.read_the_privacy_policy')}</Text>
        </Pressable>

        <Text style={st.footer}>{tt('terms_of_service.eu_ai_act_art_50_ai_outputs_are_info')}</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 2, fontSize: 14 },
  meta: { color: C.info, fontSize: 10.5, letterSpacing: 0.5, marginBottom: 4 },
  discBox: { borderWidth: 2, borderColor: C.brand, backgroundColor: 'rgba(212,175,55,0.08)', borderRadius: R.md, padding: S.lg, marginTop: S.md },
  discHead: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6 },
  discTitle: { color: C.brand, fontWeight: '900', fontSize: 12, letterSpacing: 2 },
  rtl: { writingDirection: 'rtl', textAlign: 'right' },
  discText: { color: C.fg, fontSize: 13, lineHeight: 20, fontWeight: '800' },
  section: { marginTop: S.xl },
  secTitle: { color: C.brand, fontWeight: '900', fontSize: 11.5, letterSpacing: 1.5, marginBottom: 6 },
  p: { color: C.fg, fontSize: 13, lineHeight: 20, marginBottom: 6 },
  bullet: { color: C.onS3, fontSize: 12.5, lineHeight: 19, marginBottom: 4, paddingLeft: 4 },
  linkBtn: { flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', borderWidth: 1.5, borderColor: C.brand, borderRadius: R.sm, minHeight: 48, marginTop: S.xl },
  linkBtnText: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 1.5 },
  footer: { textAlign: 'center', color: C.info, fontSize: 8.5, letterSpacing: 1, marginTop: S.xl, lineHeight: 13 },
});
