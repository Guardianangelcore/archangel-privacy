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

// Mood-to-voice mapping for the Living Soul.
// All moods keep 'onyx' as the base timbre — Jarvis has ONE voice, not a chorus.
// Speed alone modulates the emotion (soothing under stress, brisk in the morning).
export const MOOD_VOICE: Record<string, { voice: JarvisVoice; speed: number }> = {
  calm:       { voice: 'onyx', speed: 0.95 },
  concerned:  { voice: 'onyx', speed: 0.9 },
  energetic:  { voice: 'onyx', speed: 1.05 },
  thinking:   { voice: 'onyx', speed: 1.0 },
  alert:      { voice: 'onyx', speed: 1.1 },
  onboarding: { voice: 'onyx', speed: 0.92 }, // slow, warm welcome for first-run
};

// One module-level player — stopped on every new call, so a stale narration
// never plays over the next screen. Required by expo-audio best practices.
let _player: any = null;

function stopCurrent() {
  try {
    if (_player) {
      _player.pause?.();
      _player.remove?.();
      _player = null;
    }
  } catch {}
}

export type SpeakOptions = {
  voice?: JarvisVoice;
  speed?: number;
  mood?: keyof typeof MOOD_VOICE;
  language?: Lang;
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
  const voice: JarvisVoice = opts.voice || preset?.voice || DEFAULT_VOICE;
  const speed = opts.speed ?? preset?.speed ?? 1.0;
  const language = opts.language || 'sk';

  try {
    // 1) Ask the backend to generate (or fetch cached) audio bytes.
    const res: any = await api('/voice/tts', {
      method: 'POST',
      body: JSON.stringify({ text: cleanText.slice(0, 3800), voice, speed, language }),
    });
    if (!res?.url) return;

    // 2) Configure the audio session — play through the loudspeaker even on silent.
    await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false } as any);

    // 3) Download to a stable local URI (Expo-safe; never uses data: base64).
    const src = await cachedAudioUri(res.url.replace(/^\/api/, ''));

    // 4) Play — replace any prior player instance.
    stopCurrent();
    _player = createAudioPlayer(
      src.headers ? { uri: src.uri, headers: src.headers } : { uri: src.uri }
    );
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
