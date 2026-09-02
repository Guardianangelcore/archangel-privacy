/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import { useEffect, useRef, useState } from 'react';
import { Alert, Linking, Platform } from 'react-native';
import { useAudioRecorder, RecordingPresets, AudioModule, setAudioModeAsync } from 'expo-audio';
import { API_BASE, getToken } from './api';

export type KeywordResult = { sos: boolean; transcript: string };

/**
 * Acoustic Threat Detection — local processing only.
 * Monitors mic metering (dBFS) and fires onLoud on a sudden very loud noise
 * (glass break / scream / bang heuristic). No audio ever leaves the device
 * on its own. A loud noise NEVER triggers an alarm by itself — the caller must
 * gate any emergency action behind `captureKeyword()` (explicit spoken "SOS"/
 * "help") or an intentional long-press.
 */
export function useAcousticGuard(onLoud: (dbLevel: number) => void) {
  const recorder = useAudioRecorder({ ...RecordingPresets.LOW_QUALITY, isMeteringEnabled: true } as any);
  const [active, setActive] = useState(false);
  const activeRef = useRef(false);
  const capturing = useRef(false);
  const lastFire = useRef(0);
  const startedAt = useRef(0);
  const onLoudRef = useRef(onLoud);
  onLoudRef.current = onLoud;

  const showBlocked = () => {
    Alert.alert(
      'The microphone is blocked',
      'The Acoustic Guardian needs the microphone for local noise detection (broken glass, a scream). No audio ever leaves your device.',
      [
        { text: 'Later' },
        { text: 'Open settings', onPress: () => Linking.openSettings() },
      ]
    );
  };

  const start = async () => {
    try {
      const cur = await AudioModule.getRecordingPermissionsAsync();
      if (!cur.granted) {
        if (!cur.canAskAgain) { showBlocked(); return; }
        const res = await AudioModule.requestRecordingPermissionsAsync();
        if (!res.granted) { if (!res.canAskAgain) showBlocked(); return; }
      }
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true } as any);
      await recorder.prepareToRecordAsync();
      recorder.record();
      startedAt.current = Date.now();
      activeRef.current = true;
      setActive(true);
    } catch (e) {
      console.log('acoustic start err', e);
    }
  };

  const stop = async () => {
    activeRef.current = false;
    setActive(false);
    try { await recorder.stop(); } catch {}
  };

  /**
   * EXPLICIT SOS GATE — records ~5 s right after a loud noise and asks the server
   * (Whisper) whether an intentional keyword ("SOS", "help", "pomoc"…) was spoken.
   * Metering is paused during the capture and resumed afterwards.
   */
  const captureKeyword = async (): Promise<KeywordResult> => {
    if (capturing.current) return { sos: false, transcript: '' };
    capturing.current = true;
    try {
      try { await recorder.stop(); } catch {}
      await recorder.prepareToRecordAsync();
      recorder.record();
      await new Promise(r => setTimeout(r, 5000));
      await recorder.stop();
      const uri = recorder.uri;
      if (!uri) return { sos: false, transcript: '' };
      const form = new FormData();
      if (Platform.OS === 'web') {
        const blob = await (await fetch(uri)).blob();
        form.append('file', blob, 'sos.webm');
      } else {
        const m4a = uri.endsWith('.m4a');
        form.append('file', { uri, name: m4a ? 'sos.m4a' : 'sos.webm', type: m4a ? 'audio/mp4' : 'audio/webm' } as any);
      }
      const token = await getToken();
      const res = await fetch(`${API_BASE}/api/voice/sos-keyword`, {
        method: 'POST', body: form, headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body?.detail || 'STT failed');
      return { sos: !!body.sos_detected, transcript: String(body.transcript || '') };
    } catch (e) {
      console.log('sos keyword err', e);
      return { sos: false, transcript: '' };
    } finally {
      capturing.current = false;
      if (activeRef.current) {
        try { await recorder.prepareToRecordAsync(); recorder.record(); startedAt.current = Date.now(); } catch {}
      }
    }
  };

  useEffect(() => {
    if (!active) return;
    const t = setInterval(() => {
      if (capturing.current) return;
      try {
        const st: any = recorder.getStatus();
        const m = st?.metering;
        // warm-up 3s, threshold -8 dBFS (very loud, close-range), 10s cooldown
        if (
          typeof m === 'number' &&
          Date.now() - startedAt.current > 3000 &&
          m > -8 &&
          Date.now() - lastFire.current > 10000
        ) {
          lastFire.current = Date.now();
          onLoudRef.current(m);
        }
      } catch {}
    }, Platform.OS === 'web' ? 500 : 300);
    return () => clearInterval(t);
  }, [active]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => () => {
    // Best-effort cleanup: recorder may never have started; stop() returns a Promise
    // whose rejection must be swallowed to avoid dev red-screen on Angel Mode exit.
    try { Promise.resolve(recorder.stop()).catch(() => {}); } catch {}
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const toggle = () => (active ? stop() : start());
  return { active, toggle, captureKeyword };
}
