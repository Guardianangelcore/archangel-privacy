/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import * as Location from 'expo-location';
import { api } from './api';

export type LocateResult = { located: boolean; source: 'gps' | 'ip' | 'none'; blocked?: boolean };

/** Device public-IP geolocation (HTTPS, keyless). Runs ON THE DEVICE so the result is the
 *  user's real network, not the cloud ingress the backend sees behind the proxy. */
const IP_PROVIDERS: { url: string; parse: (d: any) => { lat: number; lng: number; city: string; country: string } | null }[] = [
  { url: 'https://ipapi.co/json/', parse: (d) => (typeof d?.latitude === 'number' && typeof d?.longitude === 'number'
      ? { lat: d.latitude, lng: d.longitude, city: d.city || '', country: d.country_code || '' } : null) },
  { url: 'https://ipwho.is/', parse: (d) => (d?.success !== false && typeof d?.latitude === 'number' && typeof d?.longitude === 'number'
      ? { lat: d.latitude, lng: d.longitude, city: d.city || '', country: d.country_code || '' } : null) },
];

async function ipLookup(): Promise<{ lat: number; lng: number; city: string; country: string } | null> {
  for (const p of IP_PROVIDERS) {
    const ctl = new AbortController();
    const to = setTimeout(() => ctl.abort(), 5000);
    try {
      const r = await fetch(p.url, { signal: ctl.signal });
      const row = p.parse(await r.json());
      if (row) return row;
    } catch {} finally {
      clearTimeout(to);
    }
  }
  return null;
}

/**
 * Locate the device and sync the user's geo to the backend.
 *  1. GPS (expo-location — native + browser geolocation on web). With `askPermission`
 *     the OS/browser prompt is shown when the status is still undetermined.
 *  2. Fallback: client-side IP lookup → POST /geo/ip-locate with coords.
 *  3. Last resort: server-side IP lookup (X-Forwarded-For).
 */
export async function locateDevice(opts: { askPermission?: boolean } = {}): Promise<LocateResult> {
  let blocked = false;
  try {
    let p = await Location.getForegroundPermissionsAsync();
    if (!p.granted && opts.askPermission && p.canAskAgain) p = await Location.requestForegroundPermissionsAsync();
    if (p.granted) {
      const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      await api('/geo/locate', { method: 'POST', body: JSON.stringify({ lat: pos.coords.latitude, lng: pos.coords.longitude }) });
      return { located: true, source: 'gps' };
    }
    blocked = !p.granted && !p.canAskAgain;
  } catch {}
  try {
    const ip = await ipLookup();
    await api('/geo/ip-locate', { method: 'POST', body: JSON.stringify(ip || {}) });
    return { located: !!ip, source: 'ip', blocked };
  } catch {
    return { located: false, source: 'none', blocked };
  }
}
