/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React from 'react';
import PillarHub from '@/src/PillarHub';

export default function LegacyWealth() {
  return (
    <PillarHub
      testID="hub-legacy"
      icon="wallet"
      title="Majetok a príjem"
      subtitle="Majetok a príjem — peniaze, nároky a suverénna ekonomika. Život prvé, odkaz v Trezore."
      items={[
        { testID: 'lw-healing', icon: 'sync-outline', title: 'Finančný štít pri úraze', subtitle: 'Kolotoč uzdravenia — poistka platí hneď', route: '/healing' },
        { testID: 'lw-wealth', icon: 'wallet-outline', title: 'Trezor majetku', subtitle: 'Krypto + IBAN · okamžitá výplata na kartu', route: '/wealth-vault' },
        { testID: 'lw-refunds', icon: 'cash-outline', title: 'Moje nároky', subtitle: 'Refundácie poisťovne · daňový odpočet · 1 ťuk', route: '/refunds' },
        { testID: 'lw-inner-circle', icon: 'diamond-outline', title: 'Vnútorný kruh', subtitle: 'Doživotný Archangel pre rodinu zakladateľa', route: '/inner-circle' },
        { testID: 'lw-solidarity', icon: 'heart-circle-outline', title: 'Solidarita', subtitle: 'P2P kampane · AML chránené', route: '/solidarity' },
        { testID: 'lw-subscription', icon: 'diamond-outline', title: 'Predplatné', subtitle: 'Guardian · Sentinel · Archangel — aj GA-T', route: '/subscription' },
        { testID: 'lw-mosaic', icon: 'cube-outline', title: 'Mosaic Protocol', subtitle: 'ZK-Rollup L2 · PQC · zero-fee', route: '/mosaic' },
        { testID: 'lw-protocol', icon: 'globe-outline', title: 'Guardian Protocol', subtitle: 'API brána · data marketplace · Sentinel sieť', route: '/protocol' },
        { testID: 'lw-market', icon: 'briefcase-outline', title: 'Služby expertov', subtitle: 'Cash / crypto · bez provízií', route: '/marketplace' },
        { testID: 'lw-barter', icon: 'swap-horizontal-outline', title: 'Výmena služieb', subtitle: 'Kredity dôvery · služba za službu', route: '/barter' },
      ]}
    />
  );
}
