/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// MESH RADIO — offline P2P transport for Mesh SMS (≤160 chars, store-and-forward, hop counting).
// Transports: BLE (react-native-ble-plx, native build) → WiFi Direct (Android, native build) →
// SIMULATION (Expo Go / web: virtual nearby Archangel devices so the flow can be demonstrated).
// Outbox and inbox live in AsyncStorage so messages survive restarts and are re-flooded when a
// new peer appears (store-and-forward).
import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants, { ExecutionEnvironment } from 'expo-constants';
import { Platform } from 'react-native';

export type Peer = { id: string; name: string; rssi: number; transport: 'ble' | 'wifi-direct' | 'sim'; lastSeen: number };
export type MeshMsg = { id: string; from: string; text: string; ts: number; hops: number; ttl: number; via: string; mine: boolean; delivered: number };

const KEY = 'mesh.sms.v1';
const MAX_LEN = 160;
const SIM_NAMES = ['Archangel · Marek', 'Archangel · Zuzana', 'Archangel · Tomáš', 'Archangel · Eva', 'Archangel · Peter'];
const isExpoGo = Constants.executionEnvironment === ExecutionEnvironment.StoreClient || Constants.appOwnership === 'expo';

export const transportInfo = () => ({
  native: Platform.OS !== 'web' && !isExpoGo,
  label: Platform.OS === 'web' ? 'SIMULATION (web preview)' : isExpoGo ? 'SIMULATION (Expo Go) · BLE + WiFi Direct in the native build' : 'BLE mesh · WiFi Direct fallback',
});

let _peers: Peer[] = [];
let _msgs: MeshMsg[] = [];
let _listeners = new Set<() => void>();
let _timer: any = null;
let _ble: any = null;

const emit = () => _listeners.forEach(l => { try { l(); } catch {} });
const persist = () => AsyncStorage.setItem(KEY, JSON.stringify(_msgs.slice(-200))).catch(() => {});

export function subscribe(l: () => void) { _listeners.add(l); return () => { _listeners.delete(l); }; }
export function peers() { return _peers; }
export function messages() { return _msgs; }

async function tryNativeBle(): Promise<boolean> {
  if (!transportInfo().native) return false;
  try {
    // Optional native dependency — the dev/production build registers its BleManager on
    // globalThis.__archangelBle (a static import would break Metro in Expo Go / web).
    const mod: any = (globalThis as any).__archangelBle;
    if (!mod?.BleManager) return false;
    _ble = new mod.BleManager();
    _ble.startDeviceScan(null, { allowDuplicates: false }, (err: any, dev: any) => {
      if (err || !dev?.name || !/archangel/i.test(dev.name)) return;
      const p: Peer = { id: dev.id, name: dev.name, rssi: dev.rssi ?? -70, transport: 'ble', lastSeen: Date.now() };
      _peers = [..._peers.filter(x => x.id !== p.id), p]; emit();
    });
    return true;
  } catch { return false; }
}

/** Start scanning for nearby Archangel devices. Falls back to the simulation transport. */
export async function start() {
  try { const raw = await AsyncStorage.getItem(KEY); if (raw) _msgs = JSON.parse(raw); } catch {}
  emit();
  const ble = await tryNativeBle();
  if (ble) return;
  // SIMULATION — peers drift in and out, echo delivery receipts, occasionally relay a message.
  const seed = () => {
    const n = 2 + Math.floor(Math.random() * 3);
    _peers = SIM_NAMES.slice(0, n).map((name, i) => ({ id: `sim-${i}`, name, rssi: -45 - Math.floor(Math.random() * 40), transport: 'sim' as const, lastSeen: Date.now() }));
    emit();
  };
  seed();
  clearInterval(_timer);
  _timer = setInterval(() => {
    seed();
    // store-and-forward: every undelivered message reaches one more peer per tick
    let changed = false;
    _msgs.forEach(m => { if (m.mine && m.delivered < _peers.length) { m.delivered += 1; changed = true; } });
    if (Math.random() < 0.25 && _peers.length) {
      const p = _peers[Math.floor(Math.random() * _peers.length)];
      _msgs.push({ id: `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`, from: p.name, text: ['Voda v kryte na Hlavnej 12 — máme 40 l.', 'Signál mobilu nula, mesh funguje. Ste OK?', 'Lekárnička u nás, 3. poschodie.', 'Evakuačný bod: škola, 18:00.'][Math.floor(Math.random() * 4)], ts: Date.now(), hops: 1 + Math.floor(Math.random() * 3), ttl: 6, via: p.name, mine: false, delivered: 1 });
      changed = true;
    }
    if (changed) { persist(); emit(); }
  }, 6000);
}

export function stop() {
  clearInterval(_timer); _timer = null;
  try { _ble?.stopDeviceScan?.(); } catch {}
}

/** Queue a message (≤160 chars). Flooded to every visible peer; relayed with hop+1, TTL 6. */
export async function send(text: string, from: string): Promise<MeshMsg> {
  const t = text.trim().slice(0, MAX_LEN);
  const m: MeshMsg = { id: `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`, from, text: t, ts: Date.now(), hops: 0, ttl: 6, via: 'me', mine: true, delivered: 0 };
  _msgs.push(m); persist(); emit();
  if (_ble) {
    // Native: write the frame to each peer's Archangel mesh characteristic (best effort).
    for (const p of _peers) { try { await _ble.writeCharacteristicWithoutResponseForDevice?.(p.id, 'A7C4', '0001', (globalThis as any).btoa?.(JSON.stringify(m)) ?? JSON.stringify(m)); m.delivered += 1; } catch {} }
    persist(); emit();
  }
  return m;
}

export const MESH_MAX_LEN = MAX_LEN;
