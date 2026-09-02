/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// Archangel OS — design tokens (2026 Glass/Luxe DARK · Guardian Gold)
export const C = {
  bg: '#050510',
  fg: '#FFFFFF',
  surface2: 'rgba(255,255,255,0.05)',
  surface3: 'rgba(255,255,255,0.10)',
  onS3: '#E0E0E0',
  inverse: '#F5F5F5',
  onInverse: '#050510',
  brand: '#D4AF37',
  brandPri: '#D4AF37',
  brandSec: '#F0D68C',
  brandTer: '#332A0D',
  primary: '#7C6CFF',
  accent: '#40E0D0',
  warn: '#FF9F0A',
  onWarn: '#050510',
  error: '#FF453A',
  onError: '#FFFFFF',
  info: 'rgba(255,255,255,0.7)',
  border: 'rgba(255,255,255,0.1)',
  borderStrong: 'rgba(212,175,55,0.45)',
};

// Guardian Gold gradient + glass surfaces (guardian-fest-final visual theme)
export const GOLD = ['#F0D68C', '#D4AF37', '#A8862B'] as const;
export const HEADER_GRADIENT = ['#0A0A2E', '#050510'] as const;
export const CARD_GRADIENT = ['rgba(124,108,255,0.15)', 'rgba(212,175,55,0.10)'] as const;
export const SHADOW = {
  shadowColor: '#7C6CFF',
  shadowOpacity: 0.3,
  shadowRadius: 12,
  shadowOffset: { width: 0, height: 4 },
  elevation: 8,
} as const;
export const GLASS = {
  bg: 'rgba(255,255,255,0.05)',
  bgStrong: 'rgba(10,10,30,0.92)',
  edge: ['rgba(124,108,255,0.30)', 'rgba(255,255,255,0.10)', 'rgba(212,175,55,0.25)'] as const,
};

export const R = { sm: 12, md: 16, lg: 28, xl: 32, pill: 999 };

export const S = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32, xxxl: 48 };

export const F = {
  display: 'System' as const,
  text: 'System' as const,
  sizes: { sm: 12, base: 14, lg: 16, xl: 20, xxl: 24, xxxl: 48 },
};
