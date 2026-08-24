/* Copyright © 2026 Guardian Angel. All Rights Reserved. This source code and its logic are the sole property of Guardian Angel. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React from 'react';
import PillarHub from '@/src/PillarHub';

export default function Hunter() {
  return (
    <PillarHub
      testID="hub-hunter"
      icon="search"
      title="The Hunter"
      subtitle="Lovec termínov a logistika prežitia — rýchlejšie termíny, pripravená domácnosť."
      items={[
        { testID: 'ht-waitlist', icon: 'calendar-outline', title: 'Waitlist Hunter', subtitle: 'Skorší termín u špecialistu', route: '/(tabs)/waitlist' },
        { testID: 'ht-pharmacy', icon: 'flask-outline', title: 'Pharmacy Hunter', subtitle: 'Dostupnosť liekov v lekárňach CZ/SK', route: '/pharmacy-hunter' },
        { testID: 'ht-survival', icon: 'cube-outline', title: 'Zásoby prežitia', subtitle: 'Voda · jedlo · dni prežitia', route: '/survival-auditor' },
        { testID: 'ht-blackout', icon: 'flash-off-outline', title: 'Blackout Protokol', subtitle: 'Offline režim · mesh sieť', route: '/blackout' },
      ]}
    />
  );
}
