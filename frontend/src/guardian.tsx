/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useEffect, useRef } from 'react';
import { Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { Accelerometer } from 'expo-sensors';
import * as Haptics from 'expo-haptics';
import * as Location from 'expo-location';
import { api, API_BASE } from './api';
import { useAuth } from './auth';

/**
 * GuardianMonitor — kernel-level survival service.
 * 1. Real-time fall detection (free-fall → impact) + inactivity watchdog.
 * 2. PREDICTIVE SENTINEL: micro-vibration (tremor) + gait-regularity sampling
 *    → behavioural risk forecast BEFORE an event occurs.
 * 3. GRID WATCHDOG: when the internet dies, the app switches itself to
 *    PRIMARY NODE mode (BLE-mesh Blackout screen) — survival communication core.
 */
export default function GuardianMonitor() {
  const { user, setUser } = useAuth();
  const router = useRouter();
  const freeFallAt = useRef(0);
  const freeFallStart = useRef(0);
  const lastFallNav = useRef(0);
  const lastMove = useRef(Date.now());
  const lastMag = useRef(1);
  const alertedDay = useRef('');
  const magWindow = useRef<number[]>([]);
  const lastGaitPost = useRef(0);
  const gridFails = useRef(0);
  const lastGridNav = useRef(0);

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
      // PREDICTIVE SENTINEL — rolling tremor window (micro-vibrations)
      magWindow.current.push(mag);
      if (magWindow.current.length > 300) magWindow.current.shift();
      if (now - lastGaitPost.current > 10 * 60 * 1000 && magWindow.current.length >= 120) {
        lastGaitPost.current = now;
        const w = magWindow.current;
        const mean = w.reduce((a, b) => a + b, 0) / w.length;
        const variance = w.reduce((a, b) => a + (b - mean) ** 2, 0) / w.length;
        const tremor = Math.min(10, variance * 100);
        const regularity = Math.max(0, Math.min(1, 1 - variance * 2));
        api('/sentinel/gait', { method: 'POST', body: JSON.stringify({ tremor_index: Number(tremor.toFixed(2)), gait_regularity: Number(regularity.toFixed(2)) }) }).catch(() => {});
      }
      if (!fallGuard) return;
      // REAL fall = sustained free-fall (< 0.3g for >= 80ms) FOLLOWED BY a > 2.5g
      // impact spike. Keys rattling, bumps and ambient vibration never satisfy the
      // full two-phase sequence, so they can't false-trigger the alarm.
      if (mag < 0.3) {
        if (freeFallStart.current === 0) freeFallStart.current = now;        // free-fall begins
        if (now - freeFallStart.current >= 80) freeFallAt.current = now;     // confirmed >= 80ms
      } else {
        if (
          mag > 2.5 &&                              // impact spike (> 2.5g)
          freeFallAt.current > 0 &&                 // preceded by a confirmed free-fall
          now - freeFallAt.current < 1200 &&        // impact within 1.2s of the free-fall
          now - lastFallNav.current > 30000         // 30s cooldown between alarms
        ) {
          lastFallNav.current = now;
          freeFallAt.current = 0;
          freeFallStart.current = 0;
          Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error).catch(() => {});
          router.push('/fall-verify');
        } else if (mag > 0.5) {
          // no longer in free-fall and no valid impact → reset the window
          freeFallStart.current = 0;
          freeFallAt.current = 0;
        }
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

  // GEOGRAPHIC FLUIDITY — Travel Mode: GPS → nearest city → re-index providers,
  // switch UI/voice language. Never prompts for permission here (asked in Profile).
  const travelMode = !!(user as any)?.travel_mode;
  useEffect(() => {
    if (Platform.OS === 'web' || !user || !travelMode) return;
    let cancelled = false;
    const locate = async () => {
      try {
        const p = await Location.getForegroundPermissionsAsync();
        if (!p.granted) return;
        const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
        const res: any = await api('/geo/locate', {
          method: 'POST',
          body: JSON.stringify({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
        });
        if (!cancelled && res?.language_switched) {
          const me: any = await api('/auth/me');
          if (me?.user) setUser(me.user);
        }
      } catch {}
    };
    locate();
    const iv = setInterval(locate, 15 * 60 * 1000);
    return () => { cancelled = true; clearInterval(iv); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.user_id, travelMode]);

  // KERNEL GRID WATCHDOG — total grid failure → become the PRIMARY NODE
  useEffect(() => {
    if (!user) return;
    const iv = setInterval(async () => {
      try {
        const ctl = new AbortController();
        const to = setTimeout(() => ctl.abort(), 4000);
        await fetch(`${API_BASE}/api/`, { signal: ctl.signal });
        clearTimeout(to);
        gridFails.current = 0;
      } catch {
        gridFails.current += 1;
        if (gridFails.current >= 2 && Date.now() - lastGridNav.current > 15 * 60 * 1000) {
          lastGridNav.current = Date.now();
          gridFails.current = 0;
          Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning).catch(() => {});
          router.push('/blackout');
        }
      }
    }, 20000);
    return () => clearInterval(iv);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.user_id]);

  return null;
}
