/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React from 'react';
import PillarHub from '@/src/PillarHub';

export default function Hunter() {
  return (
    <PillarHub
      testID="hub-hunter"
      icon="search"
      title="Appointment Hunter"
      subtitle="Appointment hunting and survival logistics — faster appointments, a prepared household."
      items={[
        { testID: 'ht-waitlist', icon: 'calendar-outline', title: 'Earlier Appointment', subtitle: 'Automatic slot hunting at specialists', route: '/(tabs)/waitlist' },
        { testID: 'ht-arbitrage', icon: 'airplane-outline', title: 'Medical Arbitrage', subtitle: 'Surgeries in 🇵🇱 🇭🇺 🇹🇷 · bill prediction + S2', route: '/arbitrage' },
        { testID: 'ht-mesh', icon: 'radio-outline', title: 'Mesh Messages', subtitle: 'P2P messages independent of carriers', route: '/mesh' },
        { testID: 'ht-ghost', icon: 'eye-off-outline', title: 'Ghost Mode & Power Saver', subtitle: 'Anonymous patient token · Power Saver', route: '/ghost-mode' },
        { testID: 'ht-pharmacy', icon: 'flask-outline', title: 'Med Hunter', subtitle: 'Medication availability in pharmacies', route: '/pharmacy-hunter' },
        { testID: 'ht-survival', icon: 'cube-outline', title: 'Survival Supplies', subtitle: 'Water · food · survival days', route: '/survival-auditor' },
        { testID: 'ht-compass', icon: 'compass-outline', title: 'Survival Compass', subtitle: 'Offline pack · Bio-Beacon · satellite emergency', route: '/compass' },
        { testID: 'ht-truth', icon: 'checkmark-done-outline', title: 'Fact Validator', subtitle: 'Peer consensus against disinformation', route: '/truth-validator' },
        { testID: 'ht-humanitarian', icon: 'earth-outline', title: 'Humanitarian Shield', subtitle: 'Crisis identity · Red Cross / UN', route: '/humanitarian' },
        { testID: 'ht-enviro', icon: 'thunderstorm-outline', title: 'Threat Map', subtitle: 'Environmental threats · mesh consensus', route: '/enviro' },
        { testID: 'ht-blackout', icon: 'flash-off-outline', title: 'Blackout Protocol', subtitle: 'Offline mode · mesh network', route: '/blackout' },
      ]}
    />
  );
}
