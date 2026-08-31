/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import PillarHub from '@/src/PillarHub';
import { sharePdf } from '@/src/pdf';
import { C, S, R } from '@/src/theme';
import { tap } from '@/src/ui/glass';

export default function HealthHub() {
  const router = useRouter();
  return (
    <PillarHub
      testID="hub-health"
      icon="sync"
      title="My Healing"
      subtitle="Pillar 1 · Healing Loop — from referral through money and doctor to 100% fit."
      hero={
        /* KARTA ŽIVOTA — jadro aplikácie: zdravotná os od narodenia */
        <Pressable testID="hh-lifecard-hero" onPress={() => { tap('medium'); router.push('/health-timeline'); }} style={st.lifeHero}>
          <View style={st.lifeHeroIcon}>
            <Ionicons name="id-card" size={26} color={C.onInverse} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={st.lifeHeroTitle}>LIFE CARD</Text>
            <Text style={st.lifeHeroSub}>Health timeline since birth · Vaccinations · Diseases · Surgeries · Injuries · Check-ups</Text>
          </View>
          <Ionicons name="chevron-forward" size={22} color={C.brand} />
        </Pressable>
      }
      sections={[
        { title: '⚙️ HEALING LOOP — THE CORE', items: [
          { testID: 'hh-healing', icon: 'sync-outline', title: 'Healing Loop', subtitle: 'Injury → instant money → doctor → sick leave → physio', route: '/healing' },
          { testID: 'hh-translate', icon: 'language-outline', title: 'Referral & AI Translator', subtitle: 'Scan a referral slip · OCR → plain language', route: '/translate' },
          { testID: 'hh-waitlist', icon: 'calendar-outline', title: 'Appointment Hunter', subtitle: 'Automatic hunting & booking · based on your location (GPS)', route: '/(tabs)/waitlist' },
          { testID: 'hh-arbitrage', icon: 'airplane-outline', title: 'Global Arbitrage', subtitle: 'Surgeries in 🇵🇱 🇭🇺 🇹🇷 · bill prediction', route: '/arbitrage' },
          { testID: 'hh-recovery', icon: 'bed-outline', title: 'My Recovery (Sick Leave)', subtitle: 'eSick-note · outings · sick-pay calculator', route: '/my-recovery' },
          { testID: 'hh-physio', icon: 'body-outline', title: 'Physio-AI Rehabilitation', subtitle: 'Expert video guides · tailored routines', route: '/physio' },
        ] },
        { title: '🗄 HEALTH DATA', items: [
          { testID: 'hh-vault', icon: 'lock-closed-outline', title: 'Health Vault', subtitle: 'Documents · OCR · AI translation', choices: [
            { icon: 'folder-open-outline', label: 'Open vault', sub: 'View and manage documents', route: '/(tabs)/vault' },
            { icon: 'camera-outline', label: 'Upload document + AI translation', sub: 'Photograph / upload → plain language', route: '/translate' },
            { icon: 'id-card-outline', label: 'Life Card', sub: 'All records chronologically', route: '/health-timeline' },
          ] },
          { testID: 'hh-lens', icon: 'aperture-outline', title: 'Guardian Lens', subtitle: 'Photograph a pill or report · AI acts instantly', route: '/lens' },
          { testID: 'hh-drop', icon: 'cloud-download-outline', title: 'Health Drop — from your doctor', subtitle: 'Doctor → vault · encrypted', route: '/health-drop' },
          { testID: 'hh-clinic-sync', icon: 'wifi-outline', title: 'Clinic Sync', subtitle: 'Doctor beams a report into your vault · QR', route: '/clinic-sync' },
          { testID: 'hh-news', icon: 'flask-outline', title: 'Medical News', subtitle: 'Breakthroughs matched to your vault', route: '/medical-news' },
          { testID: 'hh-border', icon: 'airplane-outline', title: 'Travel Certificate', subtitle: 'Medication certificate · 14 languages', route: '/border-pass' },
          { testID: 'hh-ips', icon: 'globe-outline', title: 'Health Summary (IPS)', subtitle: 'One tap: HL7 FHIR export · EU / UK / USA', onPress: () => { sharePdf('/ips/summary.pdf', 'guardian_ips_summary.pdf').catch(() => {}); } },
          { testID: 'hh-bible', icon: 'book-outline', title: 'Survival Bible', subtitle: 'One tap: printable PDF of critical data', onPress: () => { sharePdf('/survival/bible.pdf', 'guardian_survival_bible.pdf').catch(() => {}); } },
        ] },
        { title: '💊 MEDS & BODY', items: [
          { testID: 'hh-meds', icon: 'alarm-outline', title: 'Meds Today', subtitle: 'Reminders · scan · interactions · pharmacies', choices: [
            { icon: 'aperture-outline', label: 'Scan medication box', sub: 'Guardian Lens — AI recognizes the drug', route: '/lens' },
            { icon: 'create-outline', label: 'Add manually / reminders', sub: 'Dosage and voice alerts', route: '/meds' },
            { icon: 'git-compare-outline', label: 'Check interactions', sub: 'AI check of your medicine cabinet', route: '/medicine-cabinet' },
            { icon: 'flask-outline', label: 'Pharmacy availability', sub: 'Med Hunter — stock in your city', route: '/pharmacy-hunter' },
          ] },
          { testID: 'hh-cabinet', icon: 'medkit-outline', title: 'Medicine Cabinet', subtitle: 'Stock · expiry dates · AI interaction check', route: '/medicine-cabinet' },
          { testID: 'hh-pharmacy', icon: 'flask-outline', title: 'Med Hunter', subtitle: 'Medication availability in pharmacies', route: '/pharmacy-hunter' },
          { testID: 'hh-bioscan', icon: 'scan-outline', title: 'Vitals Bio-Scanner', subtitle: 'Pulse · SpO2 · pressure · stress via camera', route: '/bioscan' },
          { testID: 'hh-longevity', icon: 'infinite-outline', title: 'Longevity Engine', subtitle: 'Biological age · AI Bio-Hacks', route: '/longevity' },
          { testID: 'hh-mental', icon: 'shield-outline', title: 'Mental Fortress', subtitle: 'Crisis audio guide · acupressure', route: '/mental-fortress' },
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
