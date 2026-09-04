/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// FULL-DUPLEX VOICE — hands-free conversation with Jarvis (native only, works in Expo Go).
//  • BARGE-IN: while Jarvis speaks, the mic is metered; the loudspeaker echo level is learned
//    and the user's voice (clearly above it) interrupts the narration and opens a new turn.
//  • AUTO END-OF-TURN: while the user speaks, ~1.3 s of silence sends the utterance; if nobody
//    speaks for 7 s the mic closes quietly.
// Metering comes from expo-audio recorders created with `isMeteringEnabled: true` (dBFS).
import { setAudioModeAsync } from 'expo-audio';
import { isPlayingNow, isSpeaking, playedMs } from './voice';

const POLL_MS = 120;
const LEARN_MS = 700;            // real playback needed before barge-in is armed
const BARGE_MARGIN_DB = 8;       // user must be this much louder than the loudest echo heard
const BARGE_FLOOR_DB = -26;      // …and at least this loud in absolute terms
const BARGE_HITS = 2;            // consecutive polls above threshold (~240 ms) — rejects clicks
const SPEECH_DB = -30;           // "someone is talking into the phone"
const END_SILENCE_MS = 1300;     // pause that ends the user's turn
const NO_SPEECH_MS = 7000;       // nobody spoke → close the mic

/**
 * Watch the mic while Jarvis talks. Calls `onBargeIn` once when the user speaks over him.
 * Returns a cleanup that stops the metering recorder.
 */
export async function watchBargeIn(recorder: any, onBargeIn: () => void): Promise<() => void> {
  let stopped = false;
  const stop = () => {
    if (stopped) return;
    stopped = true;
    clearInterval(timer);
    try { recorder.stop?.(); } catch {}
  };
  let timer: any = null;
  try {
    await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true } as any);
    await recorder.prepareToRecordAsync();
    recorder.record();
  } catch (e) {
    console.log('barge-in start err', e);
    return () => {};
  }
  let echoMax = -60;
  let hits = 0;
  timer = setInterval(async () => {
    if (stopped) return;
    try {
      if (!isSpeaking()) { stop(); return; }
      const s: any = await recorder.getStatus?.();
      const m = s?.metering;
      if (typeof m !== 'number' || !isFinite(m)) return;
      if (!isPlayingNow()) { hits = 0; return; }          // buffering / gap between clips — no reference echo
      if (playedMs() < LEARN_MS) { echoMax = Math.max(echoMax, m); hits = 0; return; }
      const threshold = Math.max(echoMax + BARGE_MARGIN_DB, BARGE_FLOOR_DB);
      if (m > threshold) {
        hits += 1;
        if (hits >= BARGE_HITS) { stop(); onBargeIn(); }
      } else {
        hits = 0;
        echoMax = Math.max(echoMax, m);                    // keep tracking the loudest echo
      }
    } catch {}
  }, POLL_MS);
  return stop;
}

/**
 * Watch the user's own recording for the end of the utterance.
 * `onSend` → speech was heard and then silence; `onIdle` → nobody spoke at all.
 * Returns a cleanup (call it when the recording stops for any other reason).
 */
export function watchEndOfTurn(recorder: any, onSend: () => void, onIdle: () => void): () => void {
  let stopped = false;
  let heard = false;
  const t0 = Date.now();
  let lastLoud = t0;
  const timer = setInterval(async () => {
    if (stopped) return;
    try {
      const s: any = await recorder.getStatus?.();
      const m = s?.metering;
      if (typeof m !== 'number' || !isFinite(m)) return;
      const now = Date.now();
      if (m > SPEECH_DB) { heard = true; lastLoud = now; return; }
      if (heard && now - lastLoud > END_SILENCE_MS) { stop(); onSend(); }
      else if (!heard && now - t0 > NO_SPEECH_MS) { stop(); onIdle(); }
    } catch {}
  }, POLL_MS);
  const stop = () => { stopped = true; clearInterval(timer); };
  return stop;
}
