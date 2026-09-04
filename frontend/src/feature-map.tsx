/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// FEATURE MAP — the single source of truth for the Spider Hub arms, the cascade sub-features and
// the full "Pavučina" web view. Five arms radiate from the Guardian Angel.
import React from 'react';
import Svg, { Circle, Path } from 'react-native-svg';

export type FeatureNode = { id: string; label: string; icon: string; route?: string; action?: 'classic' | 'agents' | 'web' };
export type Arm = FeatureNode & { color: string; subs: FeatureNode[] };

export const GOLD = '#D4AF37';

export const ARMS: Arm[] = [
  { id: 'health', label: 'Health', icon: 'heart-outline', color: '#FF6B8A', subs: [
    { id: 'card', label: 'Health Card', icon: 'id-card-outline', route: '/health-card' },
    { id: 'meds', label: 'Meds', icon: 'medkit-outline', route: '/meds' },
    { id: 'bioscan', label: 'BioScan', icon: 'pulse-outline', route: '/bioscan' },
    { id: 'nearby', label: 'Nearby Care', icon: 'navigate-outline', route: '/nearby-care' },
    { id: 'wellness', label: 'Wellness', icon: 'leaf-outline', route: '/wellness' },
    { id: 'timeline', label: 'Timeline', icon: 'time-outline', route: '/health-timeline' },
  ] },
  { id: 'safety', label: 'Safety', icon: 'shield-outline', color: '#40E0D0', subs: [
    { id: 'crisis', label: 'Crisis', icon: 'warning-outline', route: '/crisis-protocols' },
    { id: 'bunker', label: 'Bunker', icon: 'home-outline', route: '/bunker' },
    { id: 'mesh', label: 'Mesh SMS', icon: 'radio-outline', route: '/offline-mesh' },
    { id: 'ghost', label: 'Ghost Mode', icon: 'eye-off-outline', route: '/ghost-mode' },
    { id: 'blackout', label: 'Blackout', icon: 'flashlight-outline', route: '/blackout' },
    { id: 'scam', label: 'Scam Shield', icon: 'lock-closed-outline', route: '/scam-shield' },
  ] },
  { id: 'ai', label: 'AI', icon: 'planet-outline', color: GOLD, subs: [
    { id: 'jarvis', label: 'Jarvis', icon: 'chatbubbles-outline', route: '/jarvis' },
    { id: 'lens', label: 'Lens', icon: 'scan-outline', route: '/lens' },
    { id: 'agents', label: 'Agents', icon: 'git-network-outline', action: 'agents' },
    { id: 'brief', label: 'Daily Brief', icon: 'sunny-outline', route: '/daily-brief' },
    { id: 'translate', label: 'Translate', icon: 'language-outline', route: '/translate' },
    { id: 'mental', label: 'Mental Fortress', icon: 'flower-outline', route: '/mental-fortress' },
  ] },
  { id: 'community', label: 'Community', icon: 'people-outline', color: '#7C6CFF', subs: [
    { id: 'family', label: 'Family', icon: 'people-circle-outline', route: '/(tabs)/family' },
    { id: 'solidarity', label: 'Solidarity', icon: 'hand-left-outline', route: '/solidarity' },
    { id: 'circle', label: 'Guardian Circle', icon: 'sync-outline', route: '/guardian-circle-sync' },
    { id: 'gigs', label: 'Gigs', icon: 'briefcase-outline', route: '/gigs' },
    { id: 'barter', label: 'Barter', icon: 'swap-horizontal-outline', route: '/barter' },
    { id: 'dignity', label: 'Dignity Fund', icon: 'heart-circle-outline', route: '/dignity' },
  ] },
  { id: 'store', label: 'Store', icon: 'storefront-outline', color: '#F0D68C', subs: [
    { id: 'plans', label: 'Plans & Store', icon: 'ribbon-outline', route: '/store' },
    { id: 'market', label: 'Data Market', icon: 'stats-chart-outline', route: '/marketplace' },
    { id: 'insurance', label: 'Insurance', icon: 'shield-checkmark-outline', route: '/insurance' },
    { id: 'partners', label: 'Partners', icon: 'business-outline', route: '/partners' },
    { id: 'vault', label: 'Vault', icon: 'file-tray-full-outline', route: '/(tabs)/vault' },
    { id: 'settings', label: 'Settings', icon: 'settings-outline', route: '/(tabs)/profile' },
  ] },
];

/** Guardian Angel mark — halo + open wings, gold outline. */
export function AngelMark({ size = 44, color = GOLD }: { size?: number; color?: string }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 100 100" fill="none">
      <Circle cx="50" cy="22" r="11" stroke={color} strokeWidth="4" />
      <Path d="M50 38 C 44 52, 44 66, 50 84 C 56 66, 56 52, 50 38 Z" stroke={color} strokeWidth="4" strokeLinejoin="round" />
      <Path d="M46 48 C 30 40, 14 44, 6 60 C 20 58, 32 62, 44 74" stroke={color} strokeWidth="4" strokeLinecap="round" />
      <Path d="M54 48 C 70 40, 86 44, 94 60 C 80 58, 68 62, 56 74" stroke={color} strokeWidth="4" strokeLinecap="round" />
    </Svg>
  );
}
