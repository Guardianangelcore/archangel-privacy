/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React from 'react';
import PillarHub from '@/src/PillarHub';

export default function LegacyWealth() {
  return (
    <PillarHub
      testID="hub-legacy"
      icon="shield-checkmark"
      title="Suverénny trezor"
      subtitle="Pilier 3 · Moc a prežitie — majetok, poistky, večný odkaz a bunker mód."
      sections={[
        { title: 'A · MAJETOK A POISTKY', items: [
          { testID: 'lw-wealth', icon: 'wallet-outline', title: 'Trezor majetku', subtitle: 'Krypto + IBAN · okamžitá výplata na kartu', route: '/wealth-vault' },
          { testID: 'lw-insurance', icon: 'umbrella-outline', title: 'Strážca poistiek', subtitle: 'Insurance Auditor · splatnosť · Jarvis alarm', route: '/insurance' },
          { testID: 'lw-healing', icon: 'sync-outline', title: 'Finančný štít pri úraze', subtitle: 'Kolotoč uzdravenia — poistka platí hneď', route: '/healing' },
          { testID: 'lw-refunds', icon: 'cash-outline', title: 'Moje nároky', subtitle: 'Refundácie poisťovne · daňový odpočet · 1 ťuk', route: '/refunds' },
          { testID: 'lw-token', icon: 'diamond-outline', title: 'GA-T peňaženka', subtitle: 'Guardian Token · GBI príjem · burn rate', route: '/token' },
          { testID: 'lw-subscription', icon: 'star-outline', title: 'Predplatné', subtitle: 'Guardian · Sentinel · Archangel — aj GA-T', route: '/subscription' },
          { testID: 'lw-protocol', icon: 'globe-outline', title: 'Data Marketplace', subtitle: 'API brána · predaj anonymných dát · Sentinel', route: '/protocol' },
          { testID: 'lw-market', icon: 'briefcase-outline', title: 'Služby expertov', subtitle: 'Cash / crypto · bez provízií', route: '/marketplace' },
          { testID: 'lw-barter', icon: 'swap-horizontal-outline', title: 'Výmena služieb', subtitle: 'Kredity dôvery · služba za službu', route: '/barter' },
          { testID: 'lw-solidarity', icon: 'heart-circle-outline', title: 'Solidarita', subtitle: 'P2P kampane · AML chránené', route: '/solidarity' },
          { testID: 'lw-inner-circle', icon: 'diamond-outline', title: 'Vnútorný kruh', subtitle: 'Doživotný Archangel pre rodinu zakladateľa', route: '/inner-circle' },
        ] },
        { title: 'B · ODKAZ — VEČNÝ TREZOR 🔒', items: [
          { testID: 'lw-eternal', icon: 'finger-print-outline', title: 'Večný trezor', subtitle: 'Biometrický zámok: video-závety · pohrebný fond · digitálny exekútor', route: '/eternal-vault' },
        ] },
        { title: 'C · PREŽITIE — BUNKER MODE', items: [
          { testID: 'lw-compass', icon: 'compass-outline', title: 'Kompas prežitia', subtitle: 'Satelitný handshake · Bio-Beacon · bod S3', route: '/compass' },
          { testID: 'lw-mesh', icon: 'radio-outline', title: 'Mesh správy', subtitle: 'P2P offline správy nezávislé od operátorov', route: '/mesh' },
          { testID: 'lw-blackout', icon: 'flash-off-outline', title: 'Blackout protokol', subtitle: 'Offline režim · mesh sieť', route: '/blackout' },
          { testID: 'lw-survival', icon: 'cube-outline', title: 'Zásoby prežitia', subtitle: 'Supply arbitráž · voda · jedlo · dni prežitia', route: '/survival-auditor' },
          { testID: 'lw-enviro', icon: 'thunderstorm-outline', title: 'Mapa hrozieb', subtitle: 'Environmentálne hrozby · mesh konsenzus', route: '/enviro' },
          { testID: 'lw-humanitarian', icon: 'earth-outline', title: 'Humanitárny štít', subtitle: 'Krízová identita · Červený kríž / UN', route: '/humanitarian' },
          { testID: 'lw-truth', icon: 'checkmark-done-outline', title: 'Overovač faktov', subtitle: 'Peer-konsenzus proti dezinformáciám', route: '/truth-validator' },
          { testID: 'lw-ghost', icon: 'eye-off-outline', title: 'Ghost režim & šetrič', subtitle: 'Anonymný pacientsky token · Power-Saver', route: '/ghost-mode' },
          { testID: 'lw-fortress', icon: 'shield-half-outline', title: 'Kyber pevnosť', subtitle: 'Zero-Knowledge · DePIN uzly · self-healing', route: '/fortress' },
          { testID: 'lw-recovery-suite', icon: 'key-outline', title: '3-stupňová obnova', subtitle: 'Social Recovery · QR Talizman · Biometria', route: '/recovery-suite' },
          { testID: 'lw-mosaic', icon: 'cube-outline', title: 'Mosaic Protocol', subtitle: 'ZK-Rollup L2 · PQC · zero-fee', route: '/mosaic' },
        ] },
      ]}
    />
  );
}
