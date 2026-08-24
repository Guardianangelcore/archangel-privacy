/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// Guardian Health & Angel — design tokens (2026 Glass/Luxe DARK · Guardian Gold)
export const C = {
  bg: '#0A0A0F',
  fg: '#FFFFFF',
  surface2: '#16161E',
  surface3: '#20202B',
  onS3: '#E0E0E0',
  inverse: '#F5F5F5',
  onInverse: '#0A0A0F',
  brand: '#D4AF37',
  brandPri: '#D4AF37',
  brandSec: '#F2D879',
  brandTer: '#332A0D',
  warn: '#FF9F0A',
  onWarn: '#0A0A0F',
  error: '#FF453A',
  onError: '#FFFFFF',
  info: '#9B9BA6',
  border: 'rgba(255,255,255,0.12)',
  borderStrong: 'rgba(212,175,55,0.45)',
};

// Guardian Gold gradient + glass surfaces (2026 glassmorphism)
export const GOLD = ['#F2D879', '#D4AF37', '#A8862B'] as const;
export const GLASS = {
  bg: 'rgba(22,22,30,0.78)',
  bgStrong: 'rgba(14,14,20,0.92)',
  edge: ['rgba(242,216,121,0.38)', 'rgba(255,255,255,0.10)', 'rgba(212,175,55,0.30)'] as const,
};

export const R = { sm: 12, md: 20, lg: 28, xl: 32, pill: 999 };

export const S = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32, xxxl: 48 };

export const F = {
  display: 'System' as const,
  text: 'System' as const,
  sizes: { sm: 12, base: 14, lg: 16, xl: 20, xxl: 24, xxxl: 48 },
};
