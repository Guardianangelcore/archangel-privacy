/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// SILENT WITNESS PANIC GESTURE — accelerometer-based back-of-phone tap counter.
// Guardian Angel's original vision: an invisible trigger that only YOU know exists.
// - Threshold: 19 sharp Z-axis spikes within a rolling 10-second window (configurable).
// - No mic, no camera, no UI on the phone. Only vibration confirmations.
// - Fires a callback that opens Silent Witness and starts recording.
import { AppState, Platform } from 'react-native';
import { Accelerometer } from 'expo-sensors';
import * as Haptics from 'expo-haptics';
import AsyncStorage from '@react-native-async-storage/async-storage';

const DEFAULT_TAPS = 19;               // founder's spec
const WINDOW_MS = 10_000;              // rolling window
const MIN_TAP_INTERVAL_MS = 90;        // debounce individual spikes
const SPIKE_THRESHOLD_G = 1.8;         // change in |a| between samples (in g)
const CONFIRM_HAPTIC_EVERY = 5;        // give a subtle tick every 5 taps so user knows it's counting

const CFG_KEY = 'ga.panic.taps.v1';    // user-configurable number of taps

export async function getPanicTaps(): Promise<number> {
  try {
    const raw = await AsyncStorage.getItem(CFG_KEY);
    if (raw) {
      const n = parseInt(raw, 10);
      if (n >= 3 && n <= 30) return n;
    }
  } catch {}
  return DEFAULT_TAPS;
}

export async function setPanicTaps(n: number): Promise<void> {
  const clamped = Math.max(3, Math.min(30, Math.round(n)));
  try { await AsyncStorage.setItem(CFG_KEY, String(clamped)); } catch {}
}

type Cleanup = () => void;
export type PanicHandler = () => void | Promise<void>;

/** Start the global panic-gesture listener. Returns a cleanup that stops it. */
export function startPanicGesture(onPanic: PanicHandler): Cleanup {
  if (Platform.OS === 'web') return () => {};
  let sub: any = null;
  let appSub: any = null;
  let taps: number[] = [];
  let lastMag = 1;
  let lastTapAt = 0;
  let threshold = DEFAULT_TAPS;
  let paused = false;
  let cancelled = false;

  const arm = async () => {
    threshold = await getPanicTaps();
    try {
      Accelerometer.setUpdateInterval(80); // ~12 Hz — plenty for tap detection
    } catch {}
    sub = Accelerometer.addListener((data) => {
      if (paused || cancelled) return;
      // magnitude of acceleration vector (in g); resting ~ 1.0
      const mag = Math.sqrt(data.x * data.x + data.y * data.y + data.z * data.z);
      const delta = Math.abs(mag - lastMag);
      lastMag = mag;
      if (delta < SPIKE_THRESHOLD_G) return;
      const now = Date.now();
      if (now - lastTapAt < MIN_TAP_INTERVAL_MS) return;
      lastTapAt = now;
      taps.push(now);
      // drop old taps outside the window
      taps = taps.filter((t) => now - t <= WINDOW_MS);
      // Subtle progress haptic (only user notices — invisible to others)
      if (taps.length % CONFIRM_HAPTIC_EVERY === 0) {
        try { Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light); } catch {}
      }
      if (taps.length >= threshold) {
        // Trip! Reset counter and fire callback exactly once per detection window.
        taps = [];
        try { Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning); } catch {}
        Promise.resolve().then(onPanic);
      }
    });
  };

  arm();

  // Pause detection when app is backgrounded (Accelerometer in Expo Go can't stay in bg).
  appSub = AppState.addEventListener('change', (s) => {
    paused = s !== 'active';
    if (!paused && sub == null) arm();
  });

  return () => {
    cancelled = true;
    try { sub?.remove?.(); } catch {}
    try { appSub?.remove?.(); } catch {}
    sub = null; appSub = null;
  };
}
