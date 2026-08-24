/* Copyright © 2026 Guardian Angel. All Rights Reserved. This source code and its logic are the sole property of Guardian Angel. Unauthorized duplication, modification, or distribution is strictly prohibited. */
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
      title="Family Shield"
      subtitle="Rodinný štít — ochrana seniorov, wellness monitoring a bezpečná komunita."
      items={[
        { testID: 'fs-angel', icon: 'accessibility-outline', title: 'Angel Mode', subtitle: 'Jarvis hlas + SOS · pre seniorov', onPress: enableAngel },
        { testID: 'fs-pulse', icon: 'pulse-outline', title: 'Family Pulse', subtitle: 'Nálada · kroky · alarmy rodiny', route: '/family-dashboard' },
        { testID: 'fs-pulsecheck', icon: 'heart-half-outline', title: 'Guardian Pulse Check', subtitle: 'Tichý ping „si OK?" · prísne opt-in', route: '/pulse-check' },
        { testID: 'fs-wellness', icon: 'sparkles-outline', title: 'Denná kontrola', subtitle: 'Ako sa dnes cítite? · Jarvis', route: '/wellness' },
        { testID: 'fs-respect', icon: 'star-outline', title: 'Respect Map', subtitle: 'Lekári s rešpektom · komunita', route: '/respect-map' },
        { testID: 'fs-scam', icon: 'shield-half-outline', title: 'Scam štít', subtitle: 'AI ochrana pred podvodmi', route: '/scam-shield' },
        { testID: 'fs-qr', icon: 'qr-code-outline', title: 'Núdzové QR', subtitle: 'Krvná skupina · alergie · kontakt', route: '/emergency-qr' },
        { testID: 'fs-wallpaper', icon: 'image-outline', title: 'Núdzová tapeta', subtitle: 'QR na zamknutej obrazovke', route: '/wallpaper' },
      ]}
    />
  );
}
