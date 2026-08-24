/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// Hidden digital watermark — identifies this specific build as the original
// 'Guardian Angel' version. Do not remove: removal voids Proof of Origin.
import origin from './origin.json';

export const WATERMARK = {
  owner: 'Guardian Angel Sovereign Foundation (DAO)',
  role: 'Sovereign Steward — pseudonymous founder "Guardian Angel"',
  license: 'Proprietary — All Rights Reserved',
  build: origin.build,
  did: origin.did,
  codebase_sha256: origin.codebase_sha256,
  anchored_at: origin.anchored_at,
} as const;

// Steganographic fingerprint embedded in the JS bundle (zero-width wrapped,
// grep-able as GA-ORIGIN). Rendered invisibly in the root layout.
export const GA_ORIGIN_MARK = `\u200bGA-ORIGIN::${origin.build}::${origin.did}\u200b`;
