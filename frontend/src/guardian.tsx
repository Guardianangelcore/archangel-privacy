/* Copyright © 2026 Guardian Angel. All Rights Reserved. This source code and its logic are the sole property of Guardian Angel. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useEffect, useRef } from 'react';
import { Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { Accelerometer } from 'expo-sensors';
import * as Haptics from 'expo-haptics';
import { api } from './api';
import { useAuth } from './auth';

/**
 * GuardianMonitor — real-time fall detection + inactivity watchdog.
 * Fall heuristic: free-fall (|a| < 0.35g) followed by impact (|a| > 2.7g) within 1.2s.
 * Runs only while the app is open (Expo limitation without native background tasks).
 */
export default function GuardianMonitor() {
  const { user } = useAuth();
  const router = useRouter();
  const freeFallAt = useRef(0);
  const lastFallNav = useRef(0);
  const lastMove = useRef(Date.now());
  const lastMag = useRef(1);
  const alertedDay = useRef('');

  const fallGuard = !!(user as any)?.fall_guard;
  const inactivityGuard = !!(user as any)?.inactivity_guard;
  const inactivityHours = Number((user as any)?.inactivity_hours) || 6;

  useEffect(() => {
    if (Platform.OS === 'web' || !user || (!fallGuard && !inactivityGuard)) return;
    Accelerometer.setUpdateInterval(60);
    const sub = Accelerometer.addListener(({ x, y, z }) => {
      const mag = Math.sqrt(x * x + y * y + z * z);
      const now = Date.now();
      if (Math.abs(mag - lastMag.current) > 0.12) lastMove.current = now;
      lastMag.current = mag;
      if (!fallGuard) return;
      if (mag < 0.35) {
        freeFallAt.current = now;
      } else if (
        mag > 2.7 &&
        freeFallAt.current > 0 &&
        now - freeFallAt.current < 1200 &&
        now - lastFallNav.current > 60000
      ) {
        lastFallNav.current = now;
        freeFallAt.current = 0;
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error).catch(() => {});
        router.push('/fall-verify');
      }
    });
    return () => sub.remove();
  }, [user?.user_id, fallGuard, inactivityGuard]);

  useEffect(() => {
    if (Platform.OS === 'web' || !user || !inactivityGuard) return;
    const iv = setInterval(async () => {
      const now = new Date();
      const h = now.getHours();
      if (h < 8 || h >= 21) return; // daytime only
      const inactiveMs = Date.now() - lastMove.current;
      if (inactiveMs >= inactivityHours * 3600 * 1000) {
        const day = now.toISOString().slice(0, 10);
        if (alertedDay.current === day) return;
        alertedDay.current = day;
        try {
          await api('/wellness/inactivity-alert', {
            method: 'POST',
            body: JSON.stringify({ hours_inactive: Math.round(inactiveMs / 3600000) }),
          });
        } catch {}
      }
    }, 60000);
    return () => clearInterval(iv);
  }, [user?.user_id, inactivityGuard, inactivityHours]);

  return null;
}
