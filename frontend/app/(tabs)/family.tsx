/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import PillarHub from '@/src/PillarHub';
import { useAuth } from '@/src/auth';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';
import { Pulse, tap } from '@/src/ui/glass';
import { useI18n } from '@/src/i18n-context';

export default function FamilyShield() {
  const { t: tt, tx } = useI18n();
  const { setUser } = useAuth();
  const router = useRouter();
  const enableAngel = async () => {
    tap('heavy');
    const u: any = await api('/me/prefs', { method: 'PATCH', body: JSON.stringify({ angel_mode: true }) });
    setUser(u);
    router.navigate('/(tabs)');
  };
  return (
    <PillarHub
      testID="hub-family"
      icon="people"
      title={tt('tabs_family.family_shield')}
      subtitle={tt('tabs_family.pillar_2_angel_shield_hub_heroic_sen')}
      hero={
        <>
          <Pulse minScale={1} maxScale={1.03} duration={1400} style={{ marginTop: S.lg }}>
            <Pressable testID="fs-angel" onPress={enableAngel} style={st.angelHero}>
              <View style={st.angelHeroIcon}>
                <Ionicons name="accessibility" size={30} color={C.onInverse} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={st.angelHeroTitle}>{tt('tabs_family.angel_mode')}</Text>
                <Text style={st.angelHeroSub}>{tt('tabs_family.one_tap_ultra_simple_senior_os_with')}</Text>
              </View>
              <Ionicons name="power" size={26} color={C.brand} />
            </Pressable>
          </Pulse>
          {/* RODINNÉ KONTAKTY — encrypted emergency phone book, prominent at the top */}
          <Pressable testID="fs-contacts" onPress={() => { tap('medium'); router.push('/family-contacts'); }} style={st.contactsHero}>
            <View style={st.contactsHeroIcon}>
              <Ionicons name="person-add" size={26} color={C.onInverse} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={st.contactsHeroTitle}>{tt('tabs_family.add_family_member')}</Text>
              <Text style={st.contactsHeroSub}>{tt('tabs_family.family_emergency_numbers_call_sos_en')}</Text>
            </View>
            <Ionicons name="chevron-forward" size={22} color={C.brand} />
          </Pressable>
        </>
      }
      sections={[
        { title: tt('tabs_family.heroic_senior_suite'), items: [
          { testID: 'fs-magic-lens', icon: 'aperture-outline', title: tt('tabs_family.magic_lens'), subtitle: tt('tabs_family.photograph_a_pill_or_newspaper_jarvi'), route: '/lens' },
          { testID: 'fs-echoes', icon: 'heart-outline', title: tt('tabs_family.family_messages'), subtitle: tt('tabs_family.voice_echoes_your_family_voice_one_t'), route: '/voice-echoes' },
          { testID: 'fs-voice-signature', icon: 'mic-circle-outline', title: tt('tabs_family.voice_signature'), subtitle: tt('tabs_family.5_second_voice_print_jarvis_announce'), route: '/voice-signature' },
          { testID: 'fs-wellness', icon: 'sparkles-outline', title: tt('tabs_family.companion_daily_check_in'), subtitle: tt('tabs_family.how_did_you_sleep_emotional_trends'), route: '/wellness' },
          { testID: 'fs-fallverify', icon: 'body-outline', title: tt('tabs_family.safety_sentinel_falls'), subtitle: tt('tabs_family.120s_verification_loop_voice_cancel'), route: '/fall-verify' },
          { testID: 'fs-onboarding', icon: 'heart-outline', title: tt('tabs_family.senior_guide'), subtitle: tt('tabs_family.3_steps_guardian_jarvis_emergency_qr'), route: '/onboarding' },
        ] },
        { title: tt('tabs_family.family_sync'), items: [
          { testID: 'fs-guardian-circle', icon: 'people-circle-outline', title: tt('tabs_family.guardian_circle'), subtitle: tt('tabs_family.circle_of_trust_from_your_device_loc'), route: '/guardian-circle-sync' },
          { testID: 'fs-calendar-sync', icon: 'calendar-outline', title: tt('tabs_family.native_calendar'), subtitle: tt('tabs_family.meds_appointments_in_your_phone_cale'), route: '/calendar-sync' },
          { testID: 'fs-pulse', icon: 'pulse-outline', title: tt('tabs_family.family_pulse'), subtitle: tt('tabs_family.mood_steps_family_alarms'), route: '/family-dashboard' },
          { testID: 'fs-angel-pulse', icon: 'heart-outline', title: tt('tabs_family.angel_pulse'), subtitle: tt('tabs_family.a_heartbeat_across_the_ocean_no_word'), route: '/angel-pulse' },
          { testID: 'fs-pulsecheck', icon: 'heart-half-outline', title: tt('tabs_family.silent_check'), subtitle: tt('tabs_family.an_are_you_ok_ping_strictly_opt_in'), route: '/pulse-check' },
          { testID: 'fs-respect', icon: 'star-outline', title: tt('tabs_family.respect_map'), subtitle: tt('tabs_family.respectful_doctors_community'), route: '/respect-map' },
          { testID: 'fs-2fa', icon: 'key-outline', title: tt('tabs_family.social_2fa_handshake'), subtitle: tt('tabs_family.guardians_family_login_confirmation'), route: '/recovery-suite' },
          { testID: 'fs-monolith', icon: 'planet-outline', title: tt('tabs_family.command_panel'), subtitle: tt('tabs_family.uhp_gateway_arbitrage_bank_twin'), route: '/monolith' },
          { testID: 'fs-gigs', icon: 'hand-left-outline', title: tt('tabs_family.neighbourly_help'), subtitle: tt('tabs_family.small_favours_ga_t_cash_rewards'), route: '/gigs' },
        ] },
        { title: tt('tabs_family.protection_emergency'), items: [
          { testID: 'fs-scam', icon: 'shield-half-outline', title: tt('tabs_family.scam_shield'), subtitle: tt('tabs_family.ai_fraud_protection'), route: '/scam-shield' },
          { testID: 'fs-silent-witness', icon: 'radio-outline', title: tt('tabs_family.silent_witness'), subtitle: tt('tabs_family.encrypted_recording_to_your_vault_co'), route: '/silent-witness' },
          { testID: 'fs-duress', icon: 'hand-left-outline', title: tt('tabs_family.duress_pin'), subtitle: tt('tabs_family.decoy_vault_silent_alarm'), route: '/duress' },
          { testID: 'fs-medic', icon: 'medkit-outline', title: tt('tabs_family.ai_field_medic'), subtitle: tt('tabs_family.voice_paramedic_cpr_bleeding_offline'), route: '/tactical-medic' },
          { testID: 'fs-paramedic', icon: 'key-outline', title: tt('tabs_family.paramedic_key'), subtitle: tt('tabs_family.emergency_access_code_national_regis'), route: '/paramedic' },
          { testID: 'fs-qr', icon: 'qr-code-outline', title: tt('tabs_family.emergency_qr'), subtitle: tt('tabs_family.blood_type_allergies_contact'), route: '/emergency-qr' },
          { testID: 'fs-wallpaper', icon: 'image-outline', title: tt('tabs_family.emergency_wallpaper'), subtitle: tt('tabs_family.qr_on_your_lock_screen'), route: '/wallpaper' },
        ] },
      ]}
    />
  );
}

const st = StyleSheet.create({
  angelHero: { flexDirection: 'row', alignItems: 'center', gap: S.lg, backgroundColor: 'rgba(212,175,55,0.12)', borderRadius: R.lg, padding: S.lg, minHeight: 92, borderWidth: 2, borderColor: C.brand },
  angelHeroIcon: { width: 58, height: 58, borderRadius: 29, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center' },
  angelHeroTitle: { color: C.brand, fontWeight: '900', fontSize: 18, letterSpacing: 2 },
  angelHeroSub: { color: C.onS3, fontSize: 12, lineHeight: 17, marginTop: 3 },
  contactsHero: { flexDirection: 'row', alignItems: 'center', gap: S.lg, backgroundColor: C.surface2, borderRadius: R.lg, padding: S.lg, minHeight: 84, borderWidth: 1.5, borderColor: C.brand, marginTop: S.md },
  contactsHeroIcon: { width: 50, height: 50, borderRadius: 25, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center' },
  contactsHeroTitle: { color: C.fg, fontWeight: '900', fontSize: 15, letterSpacing: 1 },
  contactsHeroSub: { color: C.onS3, fontSize: 11.5, lineHeight: 16, marginTop: 3 },
});
