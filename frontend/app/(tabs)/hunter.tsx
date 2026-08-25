/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React from 'react';
import PillarHub from '@/src/PillarHub';

export default function Hunter() {
  return (
    <PillarHub
      testID="hub-hunter"
      icon="search"
      title="Lovec termínov"
      subtitle="Lovec termínov a logistika prežitia — rýchlejšie termíny, pripravená domácnosť."
      items={[
        { testID: 'ht-waitlist', icon: 'calendar-outline', title: 'Skorší termín', subtitle: 'Automatický lov termínov u špecialistu', route: '/(tabs)/waitlist' },
        { testID: 'ht-arbitrage', icon: 'airplane-outline', title: 'Medicínska arbitráž', subtitle: 'Operácie v 🇵🇱 🇭🇺 🇹🇷 · predikcia účtov + S2', route: '/arbitrage' },
        { testID: 'ht-mesh', icon: 'radio-outline', title: 'Mesh správy', subtitle: 'P2P správy nezávislé od operátorov', route: '/mesh' },
        { testID: 'ht-ghost', icon: 'eye-off-outline', title: 'Ghost režim & šetrič', subtitle: 'Anonymný pacientsky token · Power-Saver', route: '/ghost-mode' },
        { testID: 'ht-pharmacy', icon: 'flask-outline', title: 'Lovec liekov', subtitle: 'Dostupnosť liekov v lekárňach CZ/SK', route: '/pharmacy-hunter' },
        { testID: 'ht-survival', icon: 'cube-outline', title: 'Zásoby prežitia', subtitle: 'Voda · jedlo · dni prežitia', route: '/survival-auditor' },
        { testID: 'ht-compass', icon: 'compass-outline', title: 'Kompas prežitia', subtitle: 'Offline balík · Bio-Beacon · satelitná núdza', route: '/compass' },
        { testID: 'ht-truth', icon: 'checkmark-done-outline', title: 'Overovač faktov', subtitle: 'Peer-konsenzus proti dezinformáciám', route: '/truth-validator' },
        { testID: 'ht-humanitarian', icon: 'earth-outline', title: 'Humanitárny štít', subtitle: 'Krízová identita · Červený kríž / UN', route: '/humanitarian' },
        { testID: 'ht-enviro', icon: 'thunderstorm-outline', title: 'Mapa hrozieb', subtitle: 'Environmentálne hrozby · mesh konsenzus', route: '/enviro' },
        { testID: 'ht-blackout', icon: 'flash-off-outline', title: 'Blackout protokol', subtitle: 'Offline režim · mesh sieť', route: '/blackout' },
      ]}
    />
  );
}
