/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import PillarHub from '@/src/PillarHub';
import { useAuth } from '@/src/auth';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';
import { Pulse, tap } from '@/src/ui/glass';

export default function FamilyShield() {
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
      title="Family Shield"
      subtitle="Pillar 2 · Angel Shield Hub — heroic senior protection and family sync."
      hero={
        <>
          <Pulse minScale={1} maxScale={1.03} duration={1400} style={{ marginTop: S.lg }}>
            <Pressable testID="fs-angel" onPress={enableAngel} style={st.angelHero}>
              <View style={st.angelHeroIcon}>
                <Ionicons name="accessibility" size={30} color={C.onInverse} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={st.angelHeroTitle}>ANGEL MODE</Text>
                <Text style={st.angelHeroSub}>One tap — ultra-simple Senior OS with Jarvis, SOS and the Magic Lens</Text>
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
              <Text style={st.contactsHeroTitle}>+ ADD FAMILY MEMBER</Text>
              <Text style={st.contactsHeroSub}>Family emergency numbers · Call · SOS · encrypted</Text>
            </View>
            <Ionicons name="chevron-forward" size={22} color={C.brand} />
          </Pressable>
        </>
      }
      sections={[
        { title: '👵 HEROIC SENIOR SUITE', items: [
          { testID: 'fs-magic-lens', icon: 'aperture-outline', title: 'Magic Lens', subtitle: 'Photograph a pill or newspaper — Jarvis reads aloud', route: '/lens' },
          { testID: 'fs-echoes', icon: 'heart-outline', title: 'Family Messages', subtitle: 'Voice Echoes · your family voice · one tap', route: '/voice-echoes' },
          { testID: 'fs-voice-signature', icon: 'mic-circle-outline', title: 'Voice Signature', subtitle: '5-second voice-print · Jarvis announces the name', route: '/voice-signature' },
          { testID: 'fs-wellness', icon: 'sparkles-outline', title: 'Companion (daily check-in)', subtitle: 'How did you sleep? · emotional trends', route: '/wellness' },
          { testID: 'fs-fallverify', icon: 'body-outline', title: 'Safety Sentinel — Falls', subtitle: '120s verification loop · voice cancel', route: '/fall-verify' },
          { testID: 'fs-onboarding', icon: 'heart-outline', title: 'Senior Guide', subtitle: '3 steps: guardian · Jarvis · emergency QR', route: '/onboarding' },
        ] },
        { title: '👨‍👩‍👧 FAMILY SYNC', items: [
          { testID: 'fs-guardian-circle', icon: 'people-circle-outline', title: 'Guardian Circle', subtitle: 'Circle of trust from your device · local · DID hashes', route: '/guardian-circle-sync' },
          { testID: 'fs-calendar-sync', icon: 'calendar-outline', title: 'Native Calendar', subtitle: 'Meds + appointments in your phone calendar · local', route: '/calendar-sync' },
          { testID: 'fs-pulse', icon: 'pulse-outline', title: 'Family Pulse', subtitle: 'Mood · steps · family alarms', route: '/family-dashboard' },
          { testID: 'fs-angel-pulse', icon: 'heart-outline', title: 'Angel Pulse', subtitle: 'A heartbeat across the ocean · no words · vibration', route: '/angel-pulse' },
          { testID: 'fs-pulsecheck', icon: 'heart-half-outline', title: 'Silent Check', subtitle: 'An are-you-OK ping · strictly opt-in', route: '/pulse-check' },
          { testID: 'fs-respect', icon: 'star-outline', title: 'Respect Map', subtitle: 'Respectful doctors · community', route: '/respect-map' },
          { testID: 'fs-2fa', icon: 'key-outline', title: 'Social 2FA Handshake', subtitle: 'Guardians · family login confirmation', route: '/recovery-suite' },
          { testID: 'fs-monolith', icon: 'planet-outline', title: 'Command Panel', subtitle: 'UHP gateway · Arbitrage · Bank · Twin', route: '/monolith' },
          { testID: 'fs-gigs', icon: 'hand-left-outline', title: 'Neighbourly Help', subtitle: 'Small favours · GA-T / cash rewards', route: '/gigs' },
        ] },
        { title: '🛡 PROTECTION & EMERGENCY', items: [
          { testID: 'fs-scam', icon: 'shield-half-outline', title: 'Scam Shield', subtitle: 'AI fraud protection', route: '/scam-shield' },
          { testID: 'fs-silent-witness', icon: 'radio-outline', title: 'Silent Witness', subtitle: 'Encrypted recording to your Vault · conflict / official', route: '/silent-witness' },
          { testID: 'fs-duress', icon: 'hand-left-outline', title: 'Duress PIN', subtitle: 'Decoy vault · silent alarm', route: '/duress' },
          { testID: 'fs-medic', icon: 'medkit-outline', title: 'AI Field Medic', subtitle: 'Voice paramedic · CPR · bleeding · offline', route: '/tactical-medic' },
          { testID: 'fs-paramedic', icon: 'key-outline', title: 'Paramedic Key', subtitle: 'Emergency access code · national registries', route: '/paramedic' },
          { testID: 'fs-qr', icon: 'qr-code-outline', title: 'Emergency QR', subtitle: 'Blood type · allergies · contact', route: '/emergency-qr' },
          { testID: 'fs-wallpaper', icon: 'image-outline', title: 'Emergency Wallpaper', subtitle: 'QR on your lock screen', route: '/wallpaper' },
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
