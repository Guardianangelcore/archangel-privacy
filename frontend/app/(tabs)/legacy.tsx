/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React from 'react';
import PillarHub from '@/src/PillarHub';

export default function LegacyWealth() {
  return (
    <PillarHub
      testID="hub-legacy"
      icon="rose"
      title="Odkaz a majetok"
      subtitle="Odkaz a majetok — solidarita, závety, pohrebný fond a priamy príjem."
      items={[
        { testID: 'lw-video-legacy', icon: 'videocam-outline', title: 'Video odkaz rodine', subtitle: 'Zapečatené video-odkazy · rodinný zmier', route: '/video-legacy' },
        { testID: 'lw-wealth', icon: 'wallet-outline', title: 'Trezor majetku', subtitle: 'Krypto + IBAN · okamžitá výplata na kartu', route: '/wealth-vault' },
        { testID: 'lw-inner-circle', icon: 'diamond-outline', title: 'Vnútorný kruh', subtitle: 'Doživotný Archangel pre rodinu zakladateľa', route: '/inner-circle' },
        { testID: 'lw-solidarity', icon: 'heart-circle-outline', title: 'Solidarita', subtitle: 'P2P kampane · AML chránené', route: '/solidarity' },
        { testID: 'lw-insurance', icon: 'umbrella-outline', title: 'Strážca poistiek', subtitle: 'Poistky · splatnosť · Jarvis', route: '/insurance' },
        { testID: 'lw-digital', icon: 'cloud-done-outline', title: 'Digitálne dedičstvo', subtitle: 'Účty · likvidátor predplatných', route: '/digital-legacy' },
        { testID: 'lw-subscription', icon: 'diamond-outline', title: 'Predplatné', subtitle: 'Guardian · Sentinel · Archangel — aj GA-T', route: '/subscription' },
        { testID: 'lw-mosaic', icon: 'cube-outline', title: 'Mosaic Protocol', subtitle: 'ZK-Rollup L2 · PQC · zero-fee', route: '/mosaic' },
        { testID: 'lw-refunds', icon: 'cash-outline', title: 'Moje nároky', subtitle: 'Refundácie poisťovne · daňový odpočet · 1 ťuk', route: '/refunds' },
        { testID: 'lw-dignity', icon: 'rose-outline', title: 'Dôstojná rozlúčka', subtitle: 'Pohrebný fond · posledné priania', route: '/dignity' },
        { testID: 'lw-legal', icon: 'shield-checkmark-outline', title: 'Právo a súlad', subtitle: 'Závet · TOS · KYC · 2026', route: '/legal' },
        { testID: 'lw-biometric', icon: 'finger-print-outline', title: 'Biometrický závet', subtitle: 'Hlas/video dôkaz · blockchain hash', route: '/biometric-will' },
        { testID: 'lw-protocol', icon: 'globe-outline', title: 'Guardian Protocol', subtitle: 'API brána · data marketplace · Sentinel sieť', route: '/protocol' },
        { testID: 'lw-proxy', icon: 'document-lock-outline', title: 'Splnomocnenec', subtitle: 'Právna ochrana partnera', route: '/healthcare-proxy' },
        { testID: 'lw-market', icon: 'briefcase-outline', title: 'Služby expertov', subtitle: 'Cash / crypto · bez provízií', route: '/marketplace' },
        { testID: 'lw-barter', icon: 'swap-horizontal-outline', title: 'Výmena služieb', subtitle: 'Kredity dôvery · služba za službu', route: '/barter' },
      ]}
    />
  );
}
