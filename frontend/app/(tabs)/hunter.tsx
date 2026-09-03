/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React from 'react';
import PillarHub from '@/src/PillarHub';
import { useI18n } from '@/src/i18n-context';

export default function Hunter() {
  const { t: tt, tx } = useI18n();
  return (
    <PillarHub
      testID="hub-hunter"
      icon="search"
      title={tt('tabs_hunter.appointment_hunter')}
      subtitle={tt('tabs_hunter.appointment_hunting_and_survival_log')}
      items={[
        { testID: 'ht-waitlist', icon: 'calendar-outline', title: tt('tabs_hunter.earlier_appointment'), subtitle: tt('tabs_hunter.automatic_slot_hunting_at_specialist'), route: '/(tabs)/waitlist' },
        { testID: 'ht-arbitrage', icon: 'airplane-outline', title: tt('tabs_hunter.medical_arbitrage'), subtitle: tt('tabs_hunter.surgeries_in_bill_prediction_s2'), route: '/arbitrage' },
        { testID: 'ht-mesh', icon: 'radio-outline', title: tt('tabs_hunter.mesh_messages'), subtitle: tt('tabs_hunter.p2p_messages_independent_of_carriers'), route: '/mesh' },
        { testID: 'ht-ghost', icon: 'eye-off-outline', title: tt('tabs_hunter.ghost_mode_power_saver'), subtitle: tt('tabs_hunter.anonymous_patient_token_power_saver'), route: '/ghost-mode' },
        { testID: 'ht-pharmacy', icon: 'flask-outline', title: tt('tabs_hunter.med_hunter'), subtitle: tt('tabs_hunter.medication_availability_in_pharmacie'), route: '/pharmacy-hunter' },
        { testID: 'ht-survival', icon: 'cube-outline', title: tt('tabs_hunter.survival_supplies'), subtitle: tt('tabs_hunter.water_food_survival_days'), route: '/survival-auditor' },
        { testID: 'ht-compass', icon: 'compass-outline', title: tt('tabs_hunter.survival_compass'), subtitle: tt('tabs_hunter.offline_pack_bio_beacon_satellite_em'), route: '/compass' },
        { testID: 'ht-truth', icon: 'checkmark-done-outline', title: tt('tabs_hunter.fact_validator'), subtitle: tt('tabs_hunter.peer_consensus_against_disinformatio'), route: '/truth-validator' },
        { testID: 'ht-humanitarian', icon: 'earth-outline', title: tt('tabs_hunter.humanitarian_shield'), subtitle: tt('tabs_hunter.crisis_identity_red_cross_un'), route: '/humanitarian' },
        { testID: 'ht-enviro', icon: 'thunderstorm-outline', title: tt('tabs_hunter.threat_map'), subtitle: tt('tabs_hunter.environmental_threats_mesh_consensus'), route: '/enviro' },
        { testID: 'ht-blackout', icon: 'flash-off-outline', title: tt('tabs_hunter.blackout_protocol'), subtitle: tt('tabs_hunter.offline_mode_mesh_network'), route: '/blackout' },
        { testID: 'ht-crisis', icon: 'list-outline', title: tt('crisis.crisis_protocols'), subtitle: tt('crisis.step_by_step_checklists_blackout_med'), route: '/crisis-protocols' },
      ]}
    />
  );
}
