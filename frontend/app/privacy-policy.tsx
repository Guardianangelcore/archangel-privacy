/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// PRIVACY POLICY — GDPR-compliant, public page (reachable without login)
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

export default function PrivacyPolicy() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const { t, rtl } = useI18n();
  return (
    <SafeAreaView testID="privacy-screen" style={st.root} edges={['top', 'bottom']}>
      <View style={st.header}>
        <Pressable testID="privacy-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.fg} />
        </Pressable>
        <Text style={st.title}>{tt('privacy_policy.privacy_policy')}</Text>
        <View style={{ width: 26 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 80 }}>
        <Text style={st.meta}>{tt('privacy_policy.version')} {VERSION} {tt('privacy_policy.effective')} {EFFECTIVE} {tt('privacy_policy.gdpr_eu_2016_679')}</Text>
        <Text style={st.meta}>Data Controller: Guardian Angel Sovereign Foundation (DAO) · guardian.angel.core@proton.me</Text>

        {/* LOCAL-FIRST PROMISE */}
        <View testID="privacy-local-first" style={st.promiseBox}>
          <View style={st.promiseHead}>
            <Ionicons name="phone-portrait-outline" size={18} color={C.brand} />
            <Text style={st.promiseTitle}>{tt('privacy_policy.your_data_stays_on_your_device')}</Text>
          </View>
          <Text style={st.promiseText}>
            {tt('privacy_policy.archangel_os_is_local_first_and_zero')}
          </Text>
        </View>

        <Section n="1" title={tt('privacy_policy.what_we_process')}>
          <B>{tt('privacy_policy.account_data_e_mail_display_name_has')}</B>
          <B>{tt('privacy_policy.health_records_you_enter_life_card_e')}</B>
          <B>{tt('privacy_policy.family_data_you_add_guardian_circle')}</B>
          <B>{tt('privacy_policy.technical_data_session_tokens_timest')}</B>
        </Section>

        <Section n="2" title={tt('privacy_policy.local_first_storage')}>
          <P>{tt('privacy_policy.device_contacts_and_native_calendar')}</P>
        </Section>

        <Section n="3" title={tt('privacy_policy.sharing_is_opt_in')}>
          <P>{tt('privacy_policy.no_data_is_shared_by_default_sharing')}</P>
          <B>{tt('privacy_policy.guardian_circle_family_pulse_alerts')}</B>
          <B>{tt('privacy_policy.family_life_cards_only_vaccinations')}</B>
          <B>{tt('privacy_policy.emergency_qr_only_the_fields_you_cho')}</B>
          <P>{tt('privacy_policy.you_can_withdraw_any_of_these_consen')}</P>
        </Section>

        <Section n="4" title={tt('privacy_policy.legal_bases_gdpr')}>
          <B>{tt('privacy_policy.art_6_1_b_performance_of_contract_ru')}</B>
          <B>{tt('privacy_policy.art_6_1_a_art_9_2_a_your_explicit_co')}</B>
          <B>{tt('privacy_policy.art_6_1_f_legitimate_interest_in_sec')}</B>
        </Section>

        <Section n="5" title={tt('privacy_policy.ai_processing')}>
          <P>{tt('privacy_policy.when_you_use_ai_features_jarvis_magi')}</P>
        </Section>

        <Section n="6" title={tt('privacy_policy.retention_deletion')}>
          <P>{tt('privacy_policy.your_data_is_kept_only_while_your_ac')}</P>
        </Section>

        <Section n="7" title={tt('privacy_policy.your_gdpr_rights')}>
          <B>{tt('privacy_policy.access_rectification_and_erasure_of')}</B>
          <B>{tt('privacy_policy.data_portability_export_your_life_ca')}</B>
          <B>{tt('privacy_policy.withdraw_consent_at_any_time_without')}</B>
          <B>{tt('privacy_policy.object_to_processing_and_lodge_a_com')}</B>
          <P>Exercise these rights in-app or by writing to guardian.angel.core@proton.me.
            We respond within 30 days.</P>
        </Section>

        <Section n="8" title={tt('privacy_policy.security')}>
          <P>{tt('privacy_policy.encryption_in_transit_tls_and_at_res')}</P>
        </Section>

        <Section n="9" title={tt('privacy_policy.children')}>
          <P>{tt('privacy_policy.child_life_cards_are_managed_exclusi')}</P>
        </Section>

        <Section n="10" title={tt('privacy_policy.changes')}>
          <P>{tt('privacy_policy.material_changes_will_be_announced_i')}</P>
        </Section>

        <Pressable testID="privacy-tos-link" onPress={() => router.push('/terms-of-service')} style={st.linkBtn}>
          <Ionicons name="document-text-outline" size={16} color={C.brand} />
          <Text style={st.linkBtnText}>{tt('privacy_policy.read_the_terms_of_service')}</Text>
        </Pressable>

        {/* CONSOLIDATED LEGAL DISCLAIMER — footer (localized, key disclaimer.general) */}
        <View testID="privacy-disclaimer" style={st.discBox}>
          <Text style={st.discTitle}>{t('disclaimer.title')}</Text>
          <Text testID="privacy-disclaimer-text" style={[st.discText, rtl && st.rtl]}>{t('disclaimer.general')}</Text>
        </View>
        <Text style={st.footer}>{tt('privacy_policy.zero_surveillance_local_first_2026_g')}</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 2, fontSize: 14 },
  meta: { color: C.info, fontSize: 10.5, letterSpacing: 0.5, marginBottom: 4 },
  discBox: { borderWidth: 1.5, borderColor: C.brand, backgroundColor: 'rgba(212,175,55,0.08)', borderRadius: R.md, padding: S.lg, marginTop: S.xl, gap: 6 },
  discTitle: { color: C.brand, fontWeight: '900', fontSize: 12, letterSpacing: 1.5 },
  discText: { color: C.fg, fontSize: 12.5, lineHeight: 19, fontWeight: '700' },
  rtl: { writingDirection: 'rtl', textAlign: 'right' },
  promiseBox: { borderWidth: 2, borderColor: C.brand, backgroundColor: 'rgba(212,175,55,0.08)', borderRadius: R.md, padding: S.lg, marginTop: S.md },
  promiseHead: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6 },
  promiseTitle: { color: C.brand, fontWeight: '900', fontSize: 12, letterSpacing: 1.5 },
  promiseText: { color: C.fg, fontSize: 13, lineHeight: 20, fontWeight: '600' },
  section: { marginTop: S.xl },
  secTitle: { color: C.brand, fontWeight: '900', fontSize: 11.5, letterSpacing: 1.5, marginBottom: 6 },
  p: { color: C.fg, fontSize: 13, lineHeight: 20, marginBottom: 6 },
  bullet: { color: C.onS3, fontSize: 12.5, lineHeight: 19, marginBottom: 4, paddingLeft: 4 },
  linkBtn: { flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', borderWidth: 1.5, borderColor: C.brand, borderRadius: R.sm, minHeight: 48, marginTop: S.xl },
  linkBtnText: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 1.5 },
  footer: { textAlign: 'center', color: C.info, fontSize: 8.5, letterSpacing: 1, marginTop: S.xl, lineHeight: 13 },
});
