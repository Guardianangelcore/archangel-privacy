/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import * as Crypto from 'expo-crypto';
import nacl from 'tweetnacl';

// PRNG for tweetnacl (Hermes/web safe)
nacl.setPRNG((x: Uint8Array, n: number) => {
  const b = new Uint8Array(n);
  Crypto.getRandomValues(b);
  x.set(b);
});

// --- base64 helpers (no Buffer/atob dependency) ---
const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
export function b64encode(bytes: Uint8Array): string {
  let out = '';
  for (let i = 0; i < bytes.length; i += 3) {
    const b1 = bytes[i], b2 = bytes[i + 1], b3 = bytes[i + 2];
    out += B64[b1 >> 2] + B64[((b1 & 3) << 4) | ((b2 ?? 0) >> 4)];
    out += b2 === undefined ? '=' : B64[((b2 & 15) << 2) | ((b3 ?? 0) >> 6)];
    out += b3 === undefined ? '=' : B64[b3 & 63];
  }
  return out;
}
export function b64decode(s: string): Uint8Array {
  const clean = s.replace(/[^A-Za-z0-9+/]/g, '');
  const len = Math.floor((clean.length * 3) / 4);
  const out = new Uint8Array(len);
  let p = 0;
  for (let i = 0; i < clean.length; i += 4) {
    const n = (B64.indexOf(clean[i]) << 18) | (B64.indexOf(clean[i + 1]) << 12) |
              ((B64.indexOf(clean[i + 2]) & 63) << 6) | (B64.indexOf(clean[i + 3]) & 63);
    out[p++] = (n >> 16) & 255;
    if (p < len) out[p++] = (n >> 8) & 255;
    if (p < len) out[p++] = n & 255;
  }
  return out;
}

const SK_KEY = 'gh_drop_sk';
const PK_KEY = 'gh_drop_pk';

async function store(key: string, val: string) {
  if (Platform.OS === 'web') { try { localStorage.setItem(key, val); } catch {} }
  else await SecureStore.setItemAsync(key, val);
}
async function read(key: string): Promise<string | null> {
  if (Platform.OS === 'web') { try { return localStorage.getItem(key); } catch { return null; } }
  return await SecureStore.getItemAsync(key);
}

/** Get or create the device X25519 keypair. Secret key NEVER leaves the device. */
export async function ensureDropKeys(): Promise<{ publicKey: string; created: boolean }> {
  const existing = await read(PK_KEY);
  const sk = await read(SK_KEY);
  if (existing && sk) return { publicKey: existing, created: false };
  const kp = nacl.box.keyPair();
  const pk = b64encode(kp.publicKey);
  await store(SK_KEY, b64encode(kp.secretKey));
  await store(PK_KEY, pk);
  return { publicKey: pk, created: true };
}

/** Encrypt bytes for a recipient public key (used in the provider portal — in-browser). */
export function encryptForRecipient(bytes: Uint8Array, recipientPubB64: string) {
  const eph = nacl.box.keyPair();
  const nonce = new Uint8Array(24);
  Crypto.getRandomValues(nonce);
  const ct = nacl.box(bytes, nonce, b64decode(recipientPubB64), eph.secretKey);
  return { ciphertext: ct, nonce: b64encode(nonce), ephPub: b64encode(eph.publicKey) };
}

/** Decrypt a received drop with the device secret key. Returns null if tampered. */
export async function decryptDrop(ct: Uint8Array, nonceB64: string, ephPubB64: string): Promise<Uint8Array | null> {
  const skB64 = await read(SK_KEY);
  if (!skB64) return null;
  return nacl.box.open(ct, b64decode(nonceB64), b64decode(ephPubB64), b64decode(skB64));
}
