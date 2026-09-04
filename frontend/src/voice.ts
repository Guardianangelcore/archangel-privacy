/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// SENTIENT VOICE — the single voice of Jarvis, app-wide (intro, AI replies, alerts, navigation).
// ONE preset: OpenAI TTS-1 'onyx' — deep, slow, authoritative (Tony Stark's JARVIS) — or the
// ElevenLabs deep voice the user picked in Settings (resolved server-side).
// Language-aware, hardware-cached, single-player (never doubles-up), and STREAMING: the
// reply is spoken sentence-by-sentence while the LLM is still typing (speakStream).
import { Platform } from 'react-native';
import { createAudioPlayer, setAudioModeAsync } from 'expo-audio';
import { api, API_BASE } from './api';
import { cachedAudioUri } from './media';
import type { Lang } from './i18n';

export type JarvisVoice = 'onyx' | 'nova' | 'coral' | 'sage' | 'alloy' | 'echo' | 'shimmer' | 'ash' | 'fable';

/** THE JARVIS PRESET — every TTS call in the app resolves to this (or the Settings voice). */
export const JARVIS_PRESET = { voice: 'onyx' as JarvisVoice, speed: 0.9 };
export const DEFAULT_VOICE: JarvisVoice = JARVIS_PRESET.voice;

// Mood-to-pacing mapping for the Living Soul. Jarvis has ONE voice; speed alone modulates the
// emotion — always on the slow, measured side (soothing under stress, a touch brisker on alert).
export const MOOD_VOICE: Record<string, { speed: number }> = {
  calm:       { speed: 0.9 },
  concerned:  { speed: 0.85 },
  energetic:  { speed: 0.95 },
  thinking:   { speed: 0.9 },
  alert:      { speed: 1.0 },
  onboarding: { speed: 0.88 }, // slow, warm welcome for first-run
};

// One module-level player — stopped on every new call, so a stale narration
// never plays over the next screen. Required by expo-audio best practices.
let _player: any = null;
let _speaking = false;
let _gen = 0;                                   // playback generation (ignores stale player events)
let _onStopped: (() => void) | null = null;     // resolves the pending playSrc() when STOP is pressed
let _playStart: number | null = null;           // wall-clock when the current clip actually started playing
let _playAccum = 0;                             // ms of real playback in this speaking session (barge-in learn window)
const _listeners = new Set<(speaking: boolean) => void>();

function setSpeaking(v: boolean) {
  if (_speaking === v) return;
  _speaking = v;
  if (v) { _playAccum = 0; _playStart = null; }
  _listeners.forEach((cb) => { try { cb(v); } catch {} });
}

/** True while Jarvis narration is playing (used to mute the wake-word + show STOP). */
export function isSpeaking(): boolean { return _speaking; }

/** True while audio is actually coming out of the loudspeaker right now (not buffering / gap). */
export function isPlayingNow(): boolean { return _speaking && _playStart !== null; }

/** Milliseconds of real audio output in the current speaking session (for the barge-in monitor). */
export function playedMs(): number {
  return _playAccum + (_playStart !== null ? Date.now() - _playStart : 0);
}

function markPlaying(playing: boolean) {
  if (playing && _playStart === null) _playStart = Date.now();
  else if (!playing && _playStart !== null) { _playAccum += Date.now() - _playStart; _playStart = null; }
}

/** Subscribe to speaking-state changes. Returns an unsubscribe function. */
export function onSpeakingChange(cb: (speaking: boolean) => void): () => void {
  _listeners.add(cb);
  return () => { _listeners.delete(cb); };
}

function killPlayer() {
  markPlaying(false);
  try {
    if (_player) {
      _player.pause?.();
      _player.remove?.();
      _player = null;
    }
  } catch {}
}

function stopCurrent() {
  _gen += 1;
  killPlayer();
  const r = _onStopped; _onStopped = null;
  r?.();
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

type Src = { uri: string; headers?: Record<string, string> };

/** Strip the EU AI Act watermark + markdown so Onyx never reads "asterisk asterisk" aloud. */
function cleanText(text: string): string {
  return String(text)
    .replace(/\n*—?\s*AI Content · Sovereign Protocol\s*$/i, '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/https?:\/\/\S+/g, '')
    .replace(/[*_#`>|]+/g, '')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

/**
 * Ask the backend for audio and return a playable source.
 * `live` = LIVE RELAY: the player pulls bytes straight from the engine (ElevenLabs Flash / OpenAI)
 * through a one-shot ticket URL — no wait for the full render, no second download round-trip.
 * Cached phrases (server hit) always come back as a regular file → local disk cache.
 */
async function fetchSrc(text: string, opts: SpeakOptions, live = false): Promise<Src | null> {
  const preset = opts.mood ? MOOD_VOICE[opts.mood] : undefined;
  const res: any = await api('/voice/tts', {
    method: 'POST',
    body: JSON.stringify({
      text: text.slice(0, 3800),
      voice: opts.voice || JARVIS_PRESET.voice,
      speed: opts.speed ?? preset?.speed ?? JARVIS_PRESET.speed,
      language: opts.language || 'en',
      engine: opts.engine, eleven_voice_id: opts.elevenVoiceId, override: !!opts.override,
      stream: live,
    }),
  });
  if (!res?.url) return null;
  await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false } as any);
  if (res.live) return { uri: `${API_BASE}${res.url}` };
  return cachedAudioUri(res.url.replace(/^\/api/, ''));
}

const START_WATCHDOG_MS = 9000;   // a live source that never starts (network / engine down) must not hang the queue

/** Play one clip; resolves when it finishes or when STOP / a newer narration supersedes it. */
function playSrc(src: Src, gen: number, onStart?: () => void): Promise<void> {
  return new Promise<void>((resolve) => {
    if (gen !== _gen) { resolve(); return; }
    killPlayer();
    let done = false;
    let startedAt = 0;
    const finish = () => { if (done) return; done = true; _onStopped = null; clearTimeout(watchdog); killPlayer(); resolve(); };
    const watchdog = setTimeout(() => { if (!startedAt) finish(); }, START_WATCHDOG_MS);
    _onStopped = finish;
    try {
      _player = createAudioPlayer(src.headers ? { uri: src.uri, headers: src.headers } : { uri: src.uri });
      try { _player.loop = false; } catch {}
      _player.addListener?.('playbackStatusUpdate', (s: any) => {
        if (gen !== _gen || done) return;
        if (s?.playing && !startedAt) { startedAt = Date.now(); markPlaying(true); onStart?.(); }
        else if (startedAt) markPlaying(!!s?.playing && !s?.didJustFinish);
        if (s?.didJustFinish || (s?.isLoaded && s?.playing === false && s?.currentTime > 0 && s?.currentTime >= (s?.duration || Infinity))) {
          finish();
        }
      });
      _player.play();
    } catch (e) {
      if (Platform.OS !== 'web') console.log('play err', e);
      finish();
    }
  });
}

/**
 * Speak text with the Jarvis voice (one clip, LIVE relay → first sound as early as possible).
 * - Stops any prior narration first, so overlap is impossible.
 */
export async function speak(text: string, opts: SpeakOptions = {}): Promise<void> {
  const clean = cleanText(text || '');
  if (!clean) return;
  try {
    const src = await fetchSrc(clean, opts, true);
    if (!src) return;
    stopCurrent();
    const gen = _gen;
    setSpeaking(true);
    await playSrc(src, gen);
    if (gen === _gen) setSpeaking(false);
  } catch (e) {
    // Never throw from a voice call — the caller UI must not crash if TTS fails.
    if (Platform.OS !== 'web') console.log('speak err', e);
  }
}

/**
 * Play a ready-made public clip (e.g. the intro narration) through the single Jarvis player.
 * Resolves when playback ends or is stopped. `onStart` fires when audio actually begins.
 */
export async function speakUri(uri: string, onStart?: () => void): Promise<void> {
  try {
    await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false } as any);
    stopCurrent();
    const gen = _gen;
    setSpeaking(true);
    await playSrc({ uri }, gen, onStart);
    if (gen === _gen) setSpeaking(false);
  } catch (e) {
    if (Platform.OS !== 'web') console.log('speakUri err', e);
  }
}

export type SpeechStream = {
  /** Feed the next LLM token(s). Complete sentences are voiced immediately. */
  push: (delta: string) => void;
  /** No more text — flush the tail and finish after the last clip. */
  end: () => void;
  /** Abort: drop queued clips and go silent. */
  cancel: () => void;
};

// Sentence boundary: . ! ? … followed by whitespace (closing quotes/brackets allowed).
const SENTENCE_END = /[.!?…]+["'”’)\]]?\s+/g;
const FIRST_CHUNK_MIN = 24;   // speak the opening sentence as early as possible
const CHUNK_MIN = 70;         // then merge short sentences for natural prosody

/**
 * STREAMING TTS — speak while the answer is still arriving.
 * Sentences are cut from the token stream, their audio is generated in parallel (prefetch),
 * and played strictly in order. First audio typically starts after the first sentence
 * (~1–2 s) instead of after the whole reply.
 */
export function speakStream(opts: SpeakOptions = {}): SpeechStream {
  stopCurrent();
  const gen = _gen;
  const clips: Promise<Src | null>[] = [];
  let buf = '';
  let ended = false;
  let started = false;
  let wake: (() => void) | null = null;
  const notify = () => { const w = wake; wake = null; w?.(); };

  const enqueue = (text: string) => {
    const clean = cleanText(text);
    if (!clean) return;
    // Opening sentence = LIVE relay (earliest possible first sound); the rest is prefetched as
    // whole files while the previous clip plays, so there is never a gap.
    const live = clips.length === 0;
    clips.push(fetchSrc(clean, opts, live).catch((e) => { if (Platform.OS !== 'web') console.log('tts chunk err', e); return null; }));
    notify();
  };

  const flushSentences = () => {
    const min = clips.length === 0 ? FIRST_CHUNK_MIN : CHUNK_MIN;
    let cut = 0;
    SENTENCE_END.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = SENTENCE_END.exec(buf))) {
      const end = m.index + m[0].length;
      if (end >= min) { cut = end; break; }
    }
    if (cut > 0) {
      enqueue(buf.slice(0, cut));
      buf = buf.slice(cut);
    }
  };

  (async () => {
    let i = 0;
    for (;;) {
      if (gen !== _gen) return;
      if (i < clips.length) {
        const src = await clips[i++];
        if (gen !== _gen) return;
        if (src) {
          if (!started) { started = true; setSpeaking(true); }
          await playSrc(src, gen);
        }
        continue;
      }
      if (ended) { if (gen === _gen) setSpeaking(false); return; }
      await new Promise<void>((r) => { wake = r; });
    }
  })();

  return {
    push: (delta: string) => {
      if (ended || gen !== _gen || !delta) return;
      buf += delta;
      flushSentences();
    },
    end: () => {
      if (ended) return;
      ended = true;
      if (buf.trim()) { enqueue(buf); buf = ''; }
      notify();
    },
    cancel: () => { if (gen === _gen) stopCurrent(); },
  };
}

/** Immediately stop any Jarvis narration in progress. */
export function stopSpeaking(): void {
  stopCurrent();
}
