/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import PillarHub from '@/src/PillarHub';
import { sharePdf } from '@/src/pdf';
import { C, S, R } from '@/src/theme';
import { tap } from '@/src/ui/glass';
import { useI18n } from '@/src/i18n-context';

export default function HealthHub() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  return (
    <PillarHub
      testID="hub-health"
      icon="sync"
      title={tt('tabs_health.my_healing')}
      subtitle={tt('tabs_health.pillar_1_healing_loop_from_referral')}
      hero={
        /* KARTA ŽIVOTA — jadro aplikácie: zdravotná os od narodenia */
        <Pressable testID="hh-lifecard-hero" onPress={() => { tap('medium'); router.push('/health-timeline'); }} style={st.lifeHero}>
          <View style={st.lifeHeroIcon}>
            <Ionicons name="id-card" size={26} color={C.onInverse} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={st.lifeHeroTitle}>{tt('tabs_health.life_card')}</Text>
            <Text style={st.lifeHeroSub}>{tt('tabs_health.health_timeline_since_birth_vaccinat')}</Text>
          </View>
          <Ionicons name="chevron-forward" size={22} color={C.brand} />
        </Pressable>
      }
      sections={[
        { title: tt('tabs_health.healing_loop_the_core'), items: [
          { testID: 'hh-healing', icon: 'sync-outline', title: tt('tabs_health.healing_loop'), subtitle: tt('tabs_health.injury_instant_money_doctor_sick_lea'), route: '/healing' },
          { testID: 'hh-translate', icon: 'language-outline', title: tt('tabs_health.referral_ai_translator'), subtitle: tt('tabs_health.scan_a_referral_slip_ocr_plain_langu'), route: '/translate' },
          { testID: 'hh-waitlist', icon: 'calendar-outline', title: tt('tabs_health.appointment_hunter'), subtitle: tt('tabs_health.automatic_hunting_booking_based_on_y'), route: '/(tabs)/waitlist' },
          { testID: 'hh-arbitrage', icon: 'airplane-outline', title: tt('tabs_health.global_arbitrage'), subtitle: tt('tabs_health.surgeries_in_bill_prediction'), route: '/arbitrage' },
          { testID: 'hh-recovery', icon: 'bed-outline', title: tt('tabs_health.my_recovery_sick_leave'), subtitle: tt('tabs_health.esick_note_outings_sick_pay_calculat'), route: '/my-recovery' },
          { testID: 'hh-physio', icon: 'body-outline', title: tt('tabs_health.physio_ai_rehabilitation'), subtitle: tt('tabs_health.expert_video_guides_tailored_routine'), route: '/physio' },
        ] },
        { title: tt('tabs_health.health_data'), items: [
          { testID: 'hh-vault', icon: 'lock-closed-outline', title: tt('tabs_health.health_vault'), subtitle: tt('tabs_health.documents_ocr_ai_translation'), choices: [
            { icon: 'folder-open-outline', label: tt('tabs_health.open_vault'), sub: tt('tabs_health.view_and_manage_documents'), route: '/(tabs)/vault' },
            { icon: 'camera-outline', label: tt('tabs_health.upload_document_ai_translation'), sub: tt('tabs_health.photograph_upload_plain_language'), route: '/translate' },
            { icon: 'id-card-outline', label: tt('tabs_health.life_card_25m1'), sub: tt('tabs_health.all_records_chronologically'), route: '/health-timeline' },
          ] },
          { testID: 'hh-lens', icon: 'aperture-outline', title: tt('tabs_health.guardian_lens'), subtitle: tt('tabs_health.photograph_a_pill_or_report_ai_acts'), route: '/lens' },
          { testID: 'hh-drop', icon: 'cloud-download-outline', title: tt('tabs_health.health_drop_from_your_doctor'), subtitle: tt('tabs_health.doctor_vault_encrypted'), route: '/health-drop' },
          { testID: 'hh-clinic-sync', icon: 'wifi-outline', title: tt('tabs_health.clinic_sync'), subtitle: tt('tabs_health.doctor_beams_a_report_into_your_vaul'), route: '/clinic-sync' },
          { testID: 'hh-news', icon: 'flask-outline', title: tt('tabs_health.medical_news'), subtitle: tt('tabs_health.breakthroughs_matched_to_your_vault'), route: '/medical-news' },
          { testID: 'hh-border', icon: 'airplane-outline', title: tt('tabs_health.travel_certificate'), subtitle: tt('tabs_health.medication_certificate_14_languages'), route: '/border-pass' },
          { testID: 'hh-ips', icon: 'globe-outline', title: tt('tabs_health.health_summary_ips'), subtitle: tt('tabs_health.one_tap_hl7_fhir_export_eu_uk_usa'), onPress: () => { sharePdf('/ips/summary.pdf', 'guardian_ips_summary.pdf').catch(() => {}); } },
          { testID: 'hh-bible', icon: 'book-outline', title: tt('tabs_health.survival_bible'), subtitle: tt('tabs_health.one_tap_printable_pdf_of_critical_da'), onPress: () => { sharePdf('/survival/bible.pdf', 'guardian_survival_bible.pdf').catch(() => {}); } },
        ] },
        { title: tt('tabs_health.meds_body'), items: [
          { testID: 'hh-meds', icon: 'alarm-outline', title: tt('tabs_health.meds_today'), subtitle: tt('tabs_health.reminders_scan_interactions_pharmaci'), choices: [
            { icon: 'aperture-outline', label: tt('tabs_health.scan_medication_box'), sub: tt('tabs_health.guardian_lens_ai_recognizes_the_drug'), route: '/lens' },
            { icon: 'create-outline', label: tt('tabs_health.add_manually_reminders'), sub: tt('tabs_health.dosage_and_voice_alerts'), route: '/meds' },
            { icon: 'git-compare-outline', label: tt('tabs_health.check_interactions'), sub: tt('tabs_health.ai_check_of_your_medicine_cabinet'), route: '/medicine-cabinet' },
            { icon: 'flask-outline', label: tt('tabs_health.pharmacy_availability'), sub: tt('tabs_health.med_hunter_stock_in_your_city'), route: '/pharmacy-hunter' },
          ] },
          { testID: 'hh-cabinet', icon: 'medkit-outline', title: tt('tabs_health.medicine_cabinet'), subtitle: tt('tabs_health.stock_expiry_dates_ai_interaction_ch'), route: '/medicine-cabinet' },
          { testID: 'hh-pharmacy', icon: 'flask-outline', title: tt('tabs_health.med_hunter'), subtitle: tt('tabs_health.medication_availability_in_pharmacie'), route: '/pharmacy-hunter' },
          { testID: 'hh-bioscan', icon: 'scan-outline', title: tt('tabs_health.vitals_bio_scanner'), subtitle: tt('tabs_health.pulse_spo2_pressure_stress_via_camer'), route: '/bioscan' },
          { testID: 'hh-longevity', icon: 'infinite-outline', title: tt('tabs_health.longevity_engine'), subtitle: tt('tabs_health.biological_age_ai_bio_hacks'), route: '/longevity' },
          { testID: 'hh-mental', icon: 'shield-outline', title: tt('tabs_health.mental_fortress'), subtitle: tt('tabs_health.crisis_audio_guide_acupressure'), route: '/mental-fortress' },
        ] },
      ]}
    />
  );
}

const st = StyleSheet.create({
  lifeHero: { flexDirection: 'row', alignItems: 'center', gap: S.lg, backgroundColor: 'rgba(212,175,55,0.12)', borderRadius: R.lg, padding: S.lg, minHeight: 92, borderWidth: 2, borderColor: C.brand, marginTop: S.lg },
  lifeHeroIcon: { width: 54, height: 54, borderRadius: 27, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center' },
  lifeHeroTitle: { color: C.brand, fontWeight: '900', fontSize: 17, letterSpacing: 2 },
  lifeHeroSub: { color: C.onS3, fontSize: 11.5, lineHeight: 16, marginTop: 3 },
});
