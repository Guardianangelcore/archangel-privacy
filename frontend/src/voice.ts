/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// SENTIENT VOICE — the warm, human voice of Jarvis (OpenAI TTS 'onyx' by default).
// Language-aware, hardware-cached, and single-player: never doubles-up on playback.
// Replaces the on-device 'expo-speech' voice (which users rejected as robotic).
import { Platform } from 'react-native';
import { createAudioPlayer, setAudioModeAsync } from 'expo-audio';
import { api } from './api';
import { cachedAudioUri } from './media';
import type { Lang } from './i18n';

export type JarvisVoice = 'onyx' | 'nova' | 'coral' | 'sage' | 'alloy' | 'echo' | 'shimmer' | 'ash' | 'fable';

// Default voice: 'onyx' — deep, authoritative, Tony-Stark-Jarvis-like.
// The founder explicitly requested this over the cheerful 'nova' default.
export const DEFAULT_VOICE: JarvisVoice = 'onyx';

// Mood-to-pacing mapping for the Living Soul. Jarvis has ONE voice (the one chosen in
// Settings — resolved server-side from the user's preference); speed alone modulates the
// emotion (soothing under stress, brisk in the morning).
export const MOOD_VOICE: Record<string, { speed: number }> = {
  calm:       { speed: 0.95 },
  concerned:  { speed: 0.9 },
  energetic:  { speed: 1.05 },
  thinking:   { speed: 1.0 },
  alert:      { speed: 1.1 },
  onboarding: { speed: 0.92 }, // slow, warm welcome for first-run
};

// One module-level player — stopped on every new call, so a stale narration
// never plays over the next screen. Required by expo-audio best practices.
let _player: any = null;
let _speaking = false;
let _gen = 0;                                   // playback generation (ignores stale player events)
const _listeners = new Set<(speaking: boolean) => void>();

function setSpeaking(v: boolean) {
  if (_speaking === v) return;
  _speaking = v;
  _listeners.forEach((cb) => { try { cb(v); } catch {} });
}

/** True while Jarvis narration is playing (used to mute the wake-word + show STOP). */
export function isSpeaking(): boolean { return _speaking; }

/** Subscribe to speaking-state changes. Returns an unsubscribe function. */
export function onSpeakingChange(cb: (speaking: boolean) => void): () => void {
  _listeners.add(cb);
  return () => { _listeners.delete(cb); };
}

function stopCurrent() {
  _gen += 1;
  try {
    if (_player) {
      _player.pause?.();
      _player.remove?.();
      _player = null;
    }
  } catch {}
  setSpeaking(false);
}

export type SpeakOptions = {
  voice?: JarvisVoice;
  speed?: number;
  mood?: keyof typeof MOOD_VOICE;
  language?: Lang;
  engine?: 'openai' | 'elevenlabs';   // Settings preview only
  elevenVoiceId?: string;              // Settings preview only
  override?: boolean;                  // force exact engine/voice (bypass user preference)
};

/**
 * Speak text with the Jarvis voice.
 * - Uses OpenAI TTS via /api/voice/tts (already cached server-side).
 * - Downloads the mp3 to local disk (never plays a data: URI).
 * - Stops any prior narration first, so overlap is impossible.
 */
export async function speak(text: string, opts: SpeakOptions = {}): Promise<void> {
  if (!text || !text.trim()) return;
  // Strip the visible EU AI Act watermark suffix — the TTS should not read it aloud.
  // Also strip markdown syntax (Sonar/web answers arrive formatted) so Onyx never
  // reads "asterisk asterisk" or link URLs out loud.
  const cleanText = String(text)
    .replace(/\n*—?\s*AI Content · Sovereign Protocol\s*$/i, '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/https?:\/\/\S+/g, '')
    .replace(/[*_#`>|]+/g, '')
    .replace(/\s{2,}/g, ' ')
    .trim();
  if (!cleanText) return;
  const preset = opts.mood ? MOOD_VOICE[opts.mood] : undefined;
  const voice: JarvisVoice = opts.voice || DEFAULT_VOICE;   // request default — the user's Settings voice wins server-side
  const speed = opts.speed ?? preset?.speed ?? 1.0;
  const language = opts.language || 'en';

  try {
    // 1) Ask the backend to generate (or fetch cached) audio bytes. `override` (Settings
    //    preview) forces the exact engine/voice; otherwise the user's saved voice is used.
    const res: any = await api('/voice/tts', {
      method: 'POST',
      body: JSON.stringify({ text: cleanText.slice(0, 3800), voice, speed, language,
        engine: opts.engine, eleven_voice_id: opts.elevenVoiceId, override: !!opts.override }),
    });
    if (!res?.url) return;

    // 2) Configure the audio session — play through the loudspeaker even on silent.
    await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false } as any);

    // 3) Download to a stable local URI (Expo-safe; never uses data: base64).
    const src = await cachedAudioUri(res.url.replace(/^\/api/, ''));

    // 4) Play — replace any prior player instance. Plays exactly ONCE (no loop) and
    //    reports "finished" so the wake-word / STOP button can react.
    stopCurrent();
    const gen = _gen;
    _player = createAudioPlayer(
      src.headers ? { uri: src.uri, headers: src.headers } : { uri: src.uri }
    );
    try { _player.loop = false; } catch {}
    try {
      _player.addListener?.('playbackStatusUpdate', (s: any) => {
        if (gen !== _gen) return;
        if (s?.didJustFinish || (s?.isLoaded && s?.playing === false && s?.currentTime > 0 && s?.currentTime >= (s?.duration || Infinity))) {
          stopCurrent();
        }
      });
    } catch {}
    setSpeaking(true);
    _player.play();
  } catch (e) {
    // Never throw from a voice call — the caller UI must not crash if TTS fails.
    if (Platform.OS !== 'web') console.log('speak err', e);
  }
}

/** Immediately stop any Jarvis narration in progress. */
export function stopSpeaking(): void {
  stopCurrent();
}
