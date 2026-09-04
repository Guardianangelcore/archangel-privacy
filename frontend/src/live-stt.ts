/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// LIVE STT — on-device speech recognition (expo-speech-recognition) that streams partial words under
// the Jarvis orb while the user speaks. Native module = dev/production build only; in Expo Go the
// module is absent and Jarvis silently keeps the recorder → Whisper path. Web uses the Web Speech API.
import { Platform } from 'react-native';

let Mod: any = null;
try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  Mod = require('expo-speech-recognition').ExpoSpeechRecognitionModule;
} catch { Mod = null; }

const LANG_TAG: Record<string, string> = { sk: 'sk-SK', cs: 'cs-CZ', en: 'en-US', de: 'de-DE', pl: 'pl-PL', hu: 'hu-HU', uk: 'uk-UA', ru: 'ru-RU', es: 'es-ES', fr: 'fr-FR', it: 'it-IT', ja: 'ja-JP', zh: 'zh-CN', hi: 'hi-IN' };

export function nativeSttAvailable(): boolean {
  if (!Mod) return false;
  try {
    if (Platform.OS === 'web') return !!((globalThis as any).webkitSpeechRecognition || (globalThis as any).SpeechRecognition);
    return typeof Mod.isRecognitionAvailable === 'function' ? Mod.isRecognitionAvailable() : true;
  } catch { return false; }
}

export type SttPermission = 'granted' | 'denied' | 'blocked';

/** Contextual permission flow: check → ask once → 'blocked' when the OS will not ask again. */
export async function ensureSttPermission(): Promise<SttPermission> {
  if (!Mod) return 'denied';
  try {
    let p = await Mod.getPermissionsAsync();
    if (p.granted) return 'granted';
    if (p.canAskAgain === false) return 'blocked';
    p = await Mod.requestPermissionsAsync();
    if (p.granted) return 'granted';
    return p.canAskAgain === false ? 'blocked' : 'denied';
  } catch { return 'denied'; }
}

export type LiveSttHandlers = {
  onPartial: (text: string) => void;
  onFinal: (text: string) => void;
  onEnd: () => void;
  onError: (code: string) => void;
};

/** Starts recognition; resolves a controller. `stop()` lets the recognizer flush a final result, `abort()` discards. */
export function startLiveStt(lang: string, h: LiveSttHandlers): { stop: () => void; abort: () => void } {
  const subs: any[] = [];
  let ended = false;
  const cleanup = () => { subs.forEach(s => { try { s.remove(); } catch {} }); subs.length = 0; };
  const end = () => { if (ended) return; ended = true; cleanup(); h.onEnd(); };
  subs.push(Mod.addListener('result', (ev: any) => {
    const text = (ev?.results?.[0]?.transcript || '').trim();
    if (!text) return;
    if (ev.isFinal) h.onFinal(text); else h.onPartial(text);
  }));
  subs.push(Mod.addListener('error', (ev: any) => { h.onError(String(ev?.error || 'unknown')); }));
  subs.push(Mod.addListener('end', end));
  try {
    Mod.start({
      lang: LANG_TAG[lang] || 'en-US',
      interimResults: true,
      continuous: false,              // auto end-of-turn on silence (natural "hands-free" stop)
      maxAlternatives: 1,
      requiresOnDeviceRecognition: false,
      addsPunctuation: true,
      androidIntentOptions: { EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS: 1500 },
    });
  } catch (e: any) { cleanup(); h.onError(String(e?.message || e)); }
  return {
    stop: () => { try { Mod.stop(); } catch { end(); } },
    abort: () => { try { Mod.abort(); } catch {} end(); },
  };
}
