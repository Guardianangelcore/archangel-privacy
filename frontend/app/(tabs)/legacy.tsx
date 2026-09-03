/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React from 'react';
import PillarHub from '@/src/PillarHub';
import { useI18n } from '@/src/i18n-context';

export default function LegacyWealth() {
  const { t: tt, tx } = useI18n();
  return (
    <PillarHub
      testID="hub-legacy"
      icon="shield-checkmark"
      title={tt('tabs_legacy.sovereign_vault')}
      subtitle={tt('tabs_legacy.pillar_3_power_survival_wealth_insur')}
      sections={[
        { title: tt('tabs_legacy.a_wealth_insurance'), items: [
          { testID: 'lw-wealth', icon: 'wallet-outline', title: tt('tabs_legacy.wealth_vault'), subtitle: tt('tabs_legacy.crypto_iban_instant_card_payout'), route: '/wealth-vault' },
          { testID: 'lw-insurance', icon: 'umbrella-outline', title: tt('tabs_legacy.insurance_guardian'), subtitle: tt('tabs_legacy.insurance_auditor_due_dates_jarvis_a'), route: '/insurance' },
          { testID: 'lw-healing', icon: 'sync-outline', title: tt('tabs_legacy.financial_shield_on_injury'), subtitle: tt('tabs_legacy.healing_loop_insurance_pays_instantl'), route: '/healing' },
          { testID: 'lw-refunds', icon: 'cash-outline', title: tt('tabs_legacy.my_claims'), subtitle: tt('tabs_legacy.insurance_refunds_tax_deduction_one'), route: '/refunds' },
          { testID: 'lw-token', icon: 'diamond-outline', title: tt('tabs_legacy.ga_t_wallet'), subtitle: tt('tabs_legacy.guardian_token_gbi_income_burn_rate'), route: '/token' },
          { testID: 'lw-subscription', icon: 'star-outline', title: tt('tabs_legacy.subscription'), subtitle: tt('tabs_legacy.guardian_sentinel_archangel_ga_t_acc'), route: '/subscription' },
          { testID: 'lw-protocol', icon: 'globe-outline', title: tt('tabs_legacy.data_marketplace'), subtitle: tt('tabs_legacy.api_gateway_sell_anonymous_data_sent'), route: '/protocol' },
          { testID: 'lw-market', icon: 'briefcase-outline', title: tt('tabs_legacy.expert_services'), subtitle: tt('tabs_legacy.cash_crypto_zero_commission'), route: '/marketplace' },
          { testID: 'lw-impact', icon: 'planet-outline', title: tt('tabs_legacy.my_world_impact'), subtitle: tt('tabs_legacy.how_many_people_you_helped_today_pro'), route: '/impact' },
          { testID: 'lw-barter', icon: 'swap-horizontal-outline', title: tt('tabs_legacy.service_barter'), subtitle: tt('tabs_legacy.trust_credits_service_for_service'), route: '/barter' },
          { testID: 'lw-solidarity', icon: 'heart-circle-outline', title: tt('tabs_legacy.solidarity'), subtitle: tt('tabs_legacy.p2p_campaigns_aml_protected'), route: '/solidarity' },
          { testID: 'lw-inner-circle', icon: 'diamond-outline', title: tt('tabs_legacy.inner_circle'), subtitle: tt('tabs_legacy.lifetime_archangel_for_the_founder_f'), route: '/inner-circle' },
        ] },
        { title: tt('tabs_legacy.b_legacy_eternal_vault'), items: [
          { testID: 'lw-eternal', icon: 'finger-print-outline', title: tt('tabs_legacy.eternal_vault'), subtitle: tt('tabs_legacy.biometric_lock_video_wills_funeral_f'), route: '/eternal-vault' },
        ] },
        { title: tt('tabs_legacy.c_survival_bunker_mode'), items: [
          { testID: 'lw-compass', icon: 'compass-outline', title: tt('tabs_legacy.survival_compass'), subtitle: tt('tabs_legacy.satellite_handshake_bio_beacon_point'), route: '/compass' },
          { testID: 'lw-mesh', icon: 'radio-outline', title: tt('tabs_legacy.mesh_messages'), subtitle: tt('tabs_legacy.p2p_offline_messages_independent_of'), route: '/mesh' },
          { testID: 'lw-blackout', icon: 'flash-off-outline', title: tt('tabs_legacy.blackout_protocol'), subtitle: tt('tabs_legacy.offline_mode_mesh_network'), route: '/blackout' },
          { testID: 'lw-crisis', icon: 'list-outline', title: tt('crisis.crisis_protocols'), subtitle: tt('crisis.step_by_step_checklists_blackout_med'), route: '/crisis-protocols' },
          { testID: 'lw-survival', icon: 'cube-outline', title: tt('tabs_legacy.survival_supplies'), subtitle: tt('tabs_legacy.supply_arbitrage_water_food_survival'), route: '/survival-auditor' },
          { testID: 'lw-pantry', icon: 'scan-circle-outline', title: tt('tabs_legacy.survival_pantry_scanner'), subtitle: tt('tabs_legacy.jarvis_guards_cans_batteries_filters'), route: '/pantry' },
          { testID: 'lw-enviro', icon: 'thunderstorm-outline', title: tt('tabs_legacy.threat_map'), subtitle: tt('tabs_legacy.environmental_threats_mesh_consensus'), route: '/enviro' },
          { testID: 'lw-humanitarian', icon: 'earth-outline', title: tt('tabs_legacy.humanitarian_shield'), subtitle: tt('tabs_legacy.crisis_identity_red_cross_un'), route: '/humanitarian' },
          { testID: 'lw-truth', icon: 'checkmark-done-outline', title: tt('tabs_legacy.fact_validator'), subtitle: tt('tabs_legacy.peer_consensus_against_disinformatio'), route: '/truth-validator' },
          { testID: 'lw-ghost', icon: 'eye-off-outline', title: tt('tabs_legacy.ghost_mode_power_saver'), subtitle: tt('tabs_legacy.anonymous_patient_token_power_saver'), route: '/ghost-mode' },
          { testID: 'lw-fortress', icon: 'shield-half-outline', title: tt('tabs_legacy.cyber_fortress'), subtitle: tt('tabs_legacy.zero_knowledge_depin_nodes_self_heal'), route: '/fortress' },
          { testID: 'lw-recovery-suite', icon: 'key-outline', title: tt('tabs_legacy.3_tier_recovery'), subtitle: tt('tabs_legacy.social_recovery_qr_talisman_biometri'), route: '/recovery-suite' },
          { testID: 'lw-mosaic', icon: 'cube-outline', title: tt('tabs_legacy.mosaic_protocol'), subtitle: tt('tabs_legacy.zk_rollup_l2_pqc_zero_fee'), route: '/mosaic' },
        ] },
      ]}
    />
  );
}
