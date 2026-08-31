/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React from 'react';
import PillarHub from '@/src/PillarHub';

export default function LegacyWealth() {
  return (
    <PillarHub
      testID="hub-legacy"
      icon="shield-checkmark"
      title="Sovereign Vault"
      subtitle="Pillar 3 · Power & survival — wealth, insurance, eternal legacy and bunker mode."
      sections={[
        { title: 'A · WEALTH & INSURANCE', items: [
          { testID: 'lw-wealth', icon: 'wallet-outline', title: 'Wealth Vault', subtitle: 'Crypto + IBAN · instant card payout', route: '/wealth-vault' },
          { testID: 'lw-insurance', icon: 'umbrella-outline', title: 'Insurance Guardian', subtitle: 'Insurance Auditor · due dates · Jarvis alarm', route: '/insurance' },
          { testID: 'lw-healing', icon: 'sync-outline', title: 'Financial Shield on Injury', subtitle: 'Healing Loop — insurance pays instantly', route: '/healing' },
          { testID: 'lw-refunds', icon: 'cash-outline', title: 'My Claims', subtitle: 'Insurance refunds · tax deduction · one tap', route: '/refunds' },
          { testID: 'lw-token', icon: 'diamond-outline', title: 'GA-T Wallet', subtitle: 'Guardian Token · GBI income · burn rate', route: '/token' },
          { testID: 'lw-subscription', icon: 'star-outline', title: 'Subscription', subtitle: 'Guardian · Sentinel · Archangel — GA-T accepted', route: '/subscription' },
          { testID: 'lw-protocol', icon: 'globe-outline', title: 'Data Marketplace', subtitle: 'API gateway · sell anonymous data · Sentinel', route: '/protocol' },
          { testID: 'lw-market', icon: 'briefcase-outline', title: 'Expert Services', subtitle: 'Cash / crypto · zero commission', route: '/marketplace' },
          { testID: 'lw-impact', icon: 'planet-outline', title: 'My World Impact', subtitle: 'How many people you helped today · profit + heroism', route: '/impact' },
          { testID: 'lw-barter', icon: 'swap-horizontal-outline', title: 'Service Barter', subtitle: 'Trust credits · service for service', route: '/barter' },
          { testID: 'lw-solidarity', icon: 'heart-circle-outline', title: 'Solidarity', subtitle: 'P2P campaigns · AML protected', route: '/solidarity' },
          { testID: 'lw-inner-circle', icon: 'diamond-outline', title: 'Inner Circle', subtitle: 'Lifetime Archangel for the founder family', route: '/inner-circle' },
        ] },
        { title: 'B · LEGACY — ETERNAL VAULT 🔒', items: [
          { testID: 'lw-eternal', icon: 'finger-print-outline', title: 'Eternal Vault', subtitle: 'Biometric lock: video wills · funeral fund · digital executor', route: '/eternal-vault' },
        ] },
        { title: 'C · SURVIVAL — BUNKER MODE', items: [
          { testID: 'lw-compass', icon: 'compass-outline', title: 'Survival Compass', subtitle: 'Satellite handshake · Bio-Beacon · point S3', route: '/compass' },
          { testID: 'lw-mesh', icon: 'radio-outline', title: 'Mesh Messages', subtitle: 'P2P offline messages independent of carriers', route: '/mesh' },
          { testID: 'lw-blackout', icon: 'flash-off-outline', title: 'Blackout Protocol', subtitle: 'Offline mode · mesh network', route: '/blackout' },
          { testID: 'lw-survival', icon: 'cube-outline', title: 'Survival Supplies', subtitle: 'Supply arbitrage · water · food · survival days', route: '/survival-auditor' },
          { testID: 'lw-pantry', icon: 'scan-circle-outline', title: 'Survival Pantry Scanner', subtitle: 'Jarvis guards cans · batteries · filters · expiry', route: '/pantry' },
          { testID: 'lw-enviro', icon: 'thunderstorm-outline', title: 'Threat Map', subtitle: 'Environmental threats · mesh consensus', route: '/enviro' },
          { testID: 'lw-humanitarian', icon: 'earth-outline', title: 'Humanitarian Shield', subtitle: 'Crisis identity · Red Cross / UN', route: '/humanitarian' },
          { testID: 'lw-truth', icon: 'checkmark-done-outline', title: 'Fact Validator', subtitle: 'Peer consensus against disinformation', route: '/truth-validator' },
          { testID: 'lw-ghost', icon: 'eye-off-outline', title: 'Ghost Mode & Power Saver', subtitle: 'Anonymous patient token · Power Saver', route: '/ghost-mode' },
          { testID: 'lw-fortress', icon: 'shield-half-outline', title: 'Cyber Fortress', subtitle: 'Zero-Knowledge · DePIN nodes · self-healing', route: '/fortress' },
          { testID: 'lw-recovery-suite', icon: 'key-outline', title: '3-Tier Recovery', subtitle: 'Social Recovery · QR Talisman · Biometrics', route: '/recovery-suite' },
          { testID: 'lw-mosaic', icon: 'cube-outline', title: 'Mosaic Protocol', subtitle: 'ZK-Rollup L2 · PQC · zero-fee', route: '/mosaic' },
        ] },
      ]}
    />
  );
}
