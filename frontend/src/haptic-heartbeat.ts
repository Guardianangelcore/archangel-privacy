/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// HAPTIC HEARTBEAT — Angel Pulse player.
// Rhythmic vibration patterns for "I'm alive, thinking of you" — no words needed.
// Falls back to a silent no-op on web (no vibration API is universally available).
import * as Haptics from 'expo-haptics';
import { Platform } from 'react-native';

export type PulsePattern = 'heartbeat' | 'soft' | 'strong' | 'sos';

async function tick(kind: 'light' | 'medium' | 'heavy') {
  if (Platform.OS === 'web') return;
  try {
    const map = {
      light: Haptics.ImpactFeedbackStyle.Light,
      medium: Haptics.ImpactFeedbackStyle.Medium,
      heavy: Haptics.ImpactFeedbackStyle.Heavy,
    };
    await Haptics.impactAsync(map[kind]);
  } catch {}
}

function sleep(ms: number) { return new Promise((r) => setTimeout(r, ms)); }

/**
 * Play a heartbeat pattern for ~15 seconds (or until stopped).
 * Returns a stop() function so the UI can end early.
 */
export function playPulse(pattern: PulsePattern = 'heartbeat', bpm: number = 72): () => void {
  const clampedBpm = Math.max(40, Math.min(120, bpm));
  const interval = Math.round(60000 / clampedBpm); // ms per beat
  let cancelled = false;

  const stop = () => { cancelled = true; };

  const run = async () => {
    const end = Date.now() + 15000; // hard cap 15s
    while (!cancelled && Date.now() < end) {
      switch (pattern) {
        case 'heartbeat': {
          // Classic "lub-dub" — a heavy tap followed by a lighter tap ~180ms later
          await tick('heavy');
          await sleep(180);
          await tick('light');
          await sleep(Math.max(300, interval - 180));
          break;
        }
        case 'soft': {
          await tick('light');
          await sleep(interval);
          break;
        }
        case 'strong': {
          await tick('heavy');
          await sleep(interval);
          break;
        }
        case 'sos': {
          // ... --- ... (3 short, 3 long-ish, 3 short)
          for (let i = 0; i < 3; i++) { await tick('light'); await sleep(140); }
          await sleep(220);
          for (let i = 0; i < 3; i++) { await tick('heavy'); await sleep(320); }
          await sleep(220);
          for (let i = 0; i < 3; i++) { await tick('light'); await sleep(140); }
          await sleep(700);
          break;
        }
      }
    }
  };
  run();
  return stop;
}
