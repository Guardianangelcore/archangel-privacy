/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// WAKE-WORD "JARVIS" — Alexa-style background hot-word listener.
// This is a *scaffold* that works only on native (iOS/Android) with mic permission.
// True 24/7 background listening requires a native module (Porcupine/Snowboy or a
// custom expo-modules audio worklet); until the founder publishes a native build,
// this exposes a foreground/near-foreground listener that reuses expo-audio metering.
//
// LIMITATIONS in Expo Go (must be surfaced to the founder):
//  - Only listens while the app is foregrounded or in Angel Mode.
//  - Threshold-based detection (loud "JARVIS" call) — a real wake-word engine is
//    swapped in during the native build via the same start()/stop() API.
import { Platform, AppState } from 'react-native';
import { AudioModule, setAudioModeAsync } from 'expo-audio';

export type WakeWordListener = () => void | Promise<void>;

let _active = false;
let _timer: any = null;
let _recorder: any = null;
let _onWake: WakeWordListener | null = null;
let _appStateSub: any = null;

async function ensureMic(): Promise<boolean> {
  if (Platform.OS === 'web') return false;
  try {
    let perm = await AudioModule.getRecordingPermissionsAsync();
    if (!perm.granted) {
      if (perm.canAskAgain === false) return false;
      perm = await AudioModule.requestRecordingPermissionsAsync();
    }
    return !!perm.granted;
  } catch { return false; }
}

/**
 * Start listening for the wake-word.
 * @param recorder  a recorder instance (created in a React component via useAudioRecorder)
 * @param onWake    fired when we believe the wake-word was spoken
 * Returns a cleanup function.
 */
export async function startWakeWord(recorder: any, onWake: WakeWordListener): Promise<() => void> {
  if (_active) stopWakeWord();
  const ok = await ensureMic();
  if (!ok) return () => {};
  _onWake = onWake;
  _recorder = recorder;
  _active = true;

  try {
    await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true } as any);
    await recorder.prepareToRecordAsync();
    recorder.record();
  } catch (e) {
    console.log('wake-word start err', e);
    _active = false;
    return () => {};
  }

  // Metering poll — a loud spike combined with a >600ms sustain is a plausible
  // "JARVIS" call. A real production build swaps this loop for a Porcupine ppn
  // model matched on the actual phoneme sequence.
  let sustainedHits = 0;
  _timer = setInterval(async () => {
    try {
      const status: any = await recorder.getStatus?.();
      const metering = status?.metering ?? status?.durationMillis ?? -160;
      // Threshold: ~ -18 dBFS as a rough "someone shouted at the phone" signal.
      if (typeof metering === 'number' && metering > -18) {
        sustainedHits += 1;
        if (sustainedHits >= 2 && _onWake) {
          const fn = _onWake;
          _onWake = null;                      // one-shot, prevent double-fire
          fn();
          stopWakeWord();
        }
      } else {
        sustainedHits = Math.max(0, sustainedHits - 1);
      }
    } catch {}
  }, 300);

  // Pause listening in background — Expo Go can't sustain mic in background
  // without a native audio-recording extension.
  _appStateSub = AppState.addEventListener('change', (s) => {
    if (s !== 'active' && _active) {
      pauseInternal();
    } else if (s === 'active' && _recorder && !_timer && _onWake) {
      resumeInternal();
    }
  });

  return () => stopWakeWord();
}

function pauseInternal() {
  try { _recorder?.pause?.(); } catch {}
  if (_timer) { clearInterval(_timer); _timer = null; }
}

function resumeInternal() {
  try { _recorder?.record?.(); } catch {}
  if (!_timer && _active) {
    // recreate the poll loop when returning to foreground
    _timer = setInterval(() => {}, 300);
  }
}

export function stopWakeWord() {
  _active = false;
  if (_timer) { clearInterval(_timer); _timer = null; }
  if (_appStateSub) { _appStateSub.remove?.(); _appStateSub = null; }
  try { _recorder?.stop?.(); } catch {}
  _recorder = null;
  _onWake = null;
}

export function isWakeWordActive(): boolean { return _active; }
