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
      title="Rodinný štít"
      subtitle="Pilier 2 · Angel Shield Hub — hrdinská ochrana seniorov a rodinná synchronizácia."
      hero={
        <Pulse minScale={1} maxScale={1.03} duration={1400} style={{ marginTop: S.lg }}>
          <Pressable testID="fs-angel" onPress={enableAngel} style={st.angelHero}>
            <View style={st.angelHeroIcon}>
              <Ionicons name="accessibility" size={30} color={C.onInverse} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={st.angelHeroTitle}>ANGEL MODE</Text>
              <Text style={st.angelHeroSub}>1 ťuk — ultra-jednoduchý Senior OS s Jarvisom, SOS a Kúzelnou lupou</Text>
            </View>
            <Ionicons name="power" size={26} color={C.brand} />
          </Pressable>
        </Pulse>
      }
      sections={[
        { title: '👵 HEROIC SENIOR SUITE', items: [
          { testID: 'fs-magic-lens', icon: 'aperture-outline', title: 'Kúzelná lupa', subtitle: 'Odfoť liek či noviny — Jarvis číta nahlas', route: '/lens' },
          { testID: 'fs-echoes', icon: 'heart-outline', title: 'Odkazy od rodiny', subtitle: 'Voice Echoes · vlastný hlas rodiny · 1 ťuk', route: '/voice-echoes' },
          { testID: 'fs-voice-signature', icon: 'mic-circle-outline', title: 'Hlasový podpis', subtitle: '5-sekundový voice-print · Jarvis ohlási meno', route: '/voice-signature' },
          { testID: 'fs-wellness', icon: 'sparkles-outline', title: 'Spoločník (denná kontrola)', subtitle: '„Ako ste sa vyspali?" · emočné trendy', route: '/wellness' },
          { testID: 'fs-fallverify', icon: 'body-outline', title: 'Safety Sentinel — pád', subtitle: '120 s overovacia slučka · hlasové zrušenie', route: '/fall-verify' },
          { testID: 'fs-onboarding', icon: 'heart-outline', title: 'Sprievodca pre seniorov', subtitle: '3 kroky: strážca · Jarvis · núdzové QR', route: '/onboarding' },
        ] },
        { title: '👨‍👩‍👧 RODINNÁ SYNCHRONIZÁCIA', items: [
          { testID: 'fs-guardian-circle', icon: 'people-circle-outline', title: 'Guardian Circle', subtitle: 'Kruh dôvery zo zariadenia · lokálne · DID hashy', route: '/guardian-circle-sync' },
          { testID: 'fs-calendar-sync', icon: 'calendar-outline', title: 'Natívny kalendár', subtitle: 'Lieky + termíny do kalendára telefónu · lokálne', route: '/calendar-sync' },
          { testID: 'fs-pulse', icon: 'pulse-outline', title: 'Rodinný pulz', subtitle: 'Nálada · kroky · alarmy rodiny', route: '/family-dashboard' },
          { testID: 'fs-angel-pulse', icon: 'heart-outline', title: 'Angel Pulse', subtitle: 'Tep srdca cez oceán · bez slov · vibrácia', route: '/angel-pulse' },
          { testID: 'fs-pulsecheck', icon: 'heart-half-outline', title: 'Tichá kontrola', subtitle: 'Ping „si OK?" · prísne opt-in', route: '/pulse-check' },
          { testID: 'fs-respect', icon: 'star-outline', title: 'Mapa rešpektu', subtitle: 'Lekári s rešpektom · komunita', route: '/respect-map' },
          { testID: 'fs-2fa', icon: 'key-outline', title: 'Social 2FA Handshake', subtitle: 'Strážcovia · potvrdenie prihlásenia rodinou', route: '/recovery-suite' },
          { testID: 'fs-monolith', icon: 'planet-outline', title: 'Veliteľský panel', subtitle: 'UHP brána · Arbitráž · Banka · Dvojča', route: '/monolith' },
          { testID: 'fs-gigs', icon: 'hand-left-outline', title: 'Susedská pomoc', subtitle: 'Drobné služby · odmeny GA-T / hotovosť', route: '/gigs' },
        ] },
        { title: '🛡 OCHRANA A NÚDZA', items: [
          { testID: 'fs-scam', icon: 'shield-half-outline', title: 'Scam štít', subtitle: 'AI ochrana pred podvodmi', route: '/scam-shield' },
          { testID: 'fs-silent-witness', icon: 'radio-outline', title: 'Tichý svedok', subtitle: 'Šifrované nahrávanie do Trezoru · konflikt / úradník', route: '/silent-witness' },
          { testID: 'fs-duress', icon: 'hand-left-outline', title: 'Núdzový PIN (Duress)', subtitle: 'Falošný trezor · tichý alarm', route: '/duress' },
          { testID: 'fs-medic', icon: 'medkit-outline', title: 'AI poľný medik', subtitle: 'Hlasový záchranár · KPR · krvácanie · offline', route: '/tactical-medic' },
          { testID: 'fs-paramedic', icon: 'key-outline', title: 'Kľúč pre záchranárov', subtitle: 'Núdzový vstupný kód · NCZI/ÚZIS', route: '/paramedic' },
          { testID: 'fs-qr', icon: 'qr-code-outline', title: 'Núdzové QR', subtitle: 'Krvná skupina · alergie · kontakt', route: '/emergency-qr' },
          { testID: 'fs-wallpaper', icon: 'image-outline', title: 'Núdzová tapeta', subtitle: 'QR na zamknutej obrazovke', route: '/wallpaper' },
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
});
