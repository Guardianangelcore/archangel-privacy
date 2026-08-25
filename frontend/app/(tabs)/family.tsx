/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React from 'react';
import { useRouter } from 'expo-router';
import PillarHub from '@/src/PillarHub';
import { useAuth } from '@/src/auth';
import { api } from '@/src/api';

export default function FamilyShield() {
  const { setUser } = useAuth();
  const router = useRouter();
  const enableAngel = async () => {
    const u: any = await api('/me/prefs', { method: 'PATCH', body: JSON.stringify({ angel_mode: true }) });
    setUser(u);
    router.navigate('/(tabs)');
  };
  return (
    <PillarHub
      testID="hub-family"
      icon="people"
      title="Rodina a ochrana"
      subtitle="Rodinný štít — ochrana seniorov, wellness monitoring a bezpečná komunita."
      items={[
        { testID: 'fs-angel', icon: 'accessibility-outline', title: 'Angel režim', subtitle: 'Jarvis hlas + SOS · pre seniorov', onPress: enableAngel },
        { testID: 'fs-monolith', icon: 'planet-outline', title: 'Veliteľský panel', subtitle: 'UHP brána · Arbitráž · Banka · Dvojča', route: '/monolith' },
        { testID: 'fs-pulse', icon: 'pulse-outline', title: 'Rodinný pulz', subtitle: 'Nálada · kroky · alarmy rodiny', route: '/family-dashboard' },
        { testID: 'fs-pulsecheck', icon: 'heart-half-outline', title: 'Tichá kontrola', subtitle: 'Ping „si OK?" · prísne opt-in', route: '/pulse-check' },
        { testID: 'fs-wellness', icon: 'sparkles-outline', title: 'Denná kontrola', subtitle: 'Ako sa dnes cítite? · Jarvis', route: '/wellness' },
        { testID: 'fs-respect', icon: 'star-outline', title: 'Mapa rešpektu', subtitle: 'Lekári s rešpektom · komunita', route: '/respect-map' },
        { testID: 'fs-scam', icon: 'shield-half-outline', title: 'Scam štít', subtitle: 'AI ochrana pred podvodmi', route: '/scam-shield' },
        { testID: 'fs-duress', icon: 'hand-left-outline', title: 'Núdzový PIN (Duress)', subtitle: 'Falošný trezor · tichý alarm', route: '/duress' },
        { testID: 'fs-onboarding', icon: 'heart-outline', title: 'Sprievodca pre seniorov', subtitle: '3 kroky: strážca · Jarvis · núdzové QR', route: '/onboarding' },
        { testID: 'fs-medic', icon: 'medkit-outline', title: 'AI poľný medik', subtitle: 'Hlasový záchranár · KPR · krvácanie · offline', route: '/tactical-medic' },
        { testID: 'fs-paramedic', icon: 'key-outline', title: 'Kľúč pre záchranárov', subtitle: 'Núdzový vstupný kód · NCZI/ÚZIS', route: '/paramedic' },
        { testID: 'fs-gigs', icon: 'hand-left-outline', title: 'Susedská pomoc', subtitle: 'Drobné služby · odmeny GA-T / hotovosť', route: '/gigs' },
        { testID: 'fs-qr', icon: 'qr-code-outline', title: 'Núdzové QR', subtitle: 'Krvná skupina · alergie · kontakt', route: '/emergency-qr' },
        { testID: 'fs-wallpaper', icon: 'image-outline', title: 'Núdzová tapeta', subtitle: 'QR na zamknutej obrazovke', route: '/wallpaper' },
      ]}
    />
  );
}
