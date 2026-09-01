/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import { useEffect, useRef, useState } from 'react';
import { Alert, Linking, Platform } from 'react-native';
import { useAudioRecorder, RecordingPresets, AudioModule, setAudioModeAsync } from 'expo-audio';

/**
 * Acoustic Threat Detection — local processing only.
 * Monitors mic metering (dBFS) and fires onThreat on a sudden very loud noise
 * (glass break / scream / bang heuristic). No audio ever leaves the device.
 */
export function useAcousticGuard(onThreat: (dbLevel: number) => void) {
  const recorder = useAudioRecorder({ ...RecordingPresets.LOW_QUALITY, isMeteringEnabled: true } as any);
  const [active, setActive] = useState(false);
  const lastFire = useRef(0);
  const startedAt = useRef(0);
  const onThreatRef = useRef(onThreat);
  onThreatRef.current = onThreat;

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
      setActive(true);
    } catch (e) {
      console.log('acoustic start err', e);
    }
  };

  const stop = async () => {
    setActive(false);
    try { await recorder.stop(); } catch {}
  };

  useEffect(() => {
    if (!active) return;
    const t = setInterval(() => {
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
          onThreatRef.current(m);
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
  return { active, toggle };
}
