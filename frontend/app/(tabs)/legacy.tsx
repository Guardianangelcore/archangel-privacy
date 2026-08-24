import React from 'react';
import PillarHub from '@/src/PillarHub';

export default function LegacyWealth() {
  return (
    <PillarHub
      testID="hub-legacy"
      icon="rose"
      title="Legacy & Wealth"
      subtitle="Odkaz a majetok — solidarita, závety, pohrebný fond a priamy príjem."
      items={[
        { testID: 'lw-solidarity', icon: 'heart-circle-outline', title: 'Solidarity Hub', subtitle: 'P2P kampane · AML chránené', route: '/solidarity' },
        { testID: 'lw-dignity', icon: 'rose-outline', title: 'Final Dignity', subtitle: 'Pohrebný fond · posledné priania', route: '/dignity' },
        { testID: 'lw-legal', icon: 'shield-checkmark-outline', title: 'Právo a súlad', subtitle: 'Závet · TOS · KYC · 2026', route: '/legal' },
        { testID: 'lw-biometric', icon: 'finger-print-outline', title: 'Biometrický závet', subtitle: 'Hlas/video dôkaz · blockchain hash', route: '/biometric-will' },
        { testID: 'lw-proxy', icon: 'document-lock-outline', title: 'Splnomocnenec', subtitle: 'Právna ochrana partnera', route: '/healthcare-proxy' },
        { testID: 'lw-market', icon: 'briefcase-outline', title: 'Služby expertov', subtitle: 'Cash / crypto · bez provízií', route: '/marketplace' },
        { testID: 'lw-barter', icon: 'swap-horizontal-outline', title: 'Barter Engine', subtitle: 'Kredity dôvery · služba za službu', route: '/barter' },
      ]}
    />
  );
}
