/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// Glass UI kit — GlassCard, GoldButton, Pulse + haptic helper (2026 Wow standard)
import React, { useEffect } from 'react';
import { View, Text, Pressable, StyleSheet, Platform, ActivityIndicator, ViewStyle } from 'react-native';
import * as Haptics from 'expo-haptics';
import { LinearGradient } from 'expo-linear-gradient';
import { BlurView } from 'expo-blur';
import Ionicons from '@react-native-vector-icons/ionicons';
import Animated, { useSharedValue, useAnimatedStyle, withRepeat, withSequence, withTiming } from 'react-native-reanimated';
import { C, S, R, GOLD, GLASS, SHADOW } from '@/src/theme';

export function tap(kind: 'light' | 'medium' | 'heavy' | 'success' | 'error' = 'light') {
  if (Platform.OS === 'web') return;
  try {
    if (kind === 'success') Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    else if (kind === 'error') Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error).catch(() => {});
    else {
      const map = { light: Haptics.ImpactFeedbackStyle.Light, medium: Haptics.ImpactFeedbackStyle.Medium, heavy: Haptics.ImpactFeedbackStyle.Heavy } as const;
      Haptics.impactAsync(map[kind]).catch(() => {});
    }
  } catch {}
}

type GlassProps = { children: React.ReactNode; style?: ViewStyle | ViewStyle[]; pad?: number; radius?: number; glow?: boolean; testID?: string; onPress?: () => void };

export function GlassCard({ children, style, pad = S.lg, radius = R.md, glow, testID, onPress }: GlassProps) {
  const body = (
    <LinearGradient colors={GLASS.edge as any} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
      style={[{ borderRadius: radius, padding: StyleSheet.hairlineWidth * 3 }, Platform.OS !== 'web' && (SHADOW as any), glow && st.glow, style as any]}>
      <View style={{ borderRadius: radius - 2, overflow: 'hidden', backgroundColor: GLASS.bg }}>
        {Platform.OS !== 'android' && <BlurView intensity={22} tint="dark" style={StyleSheet.absoluteFill} />}
        <View style={{ padding: pad }}>{children}</View>
      </View>
    </LinearGradient>
  );
  if (!onPress) return testID ? <View testID={testID}>{body}</View> : body;
  return (
    <Pressable testID={testID} onPress={() => { tap('light'); onPress(); }} style={({ pressed }) => [pressed && { transform: [{ scale: 0.985 }], opacity: 0.92 }]}>
      {body}
    </Pressable>
  );
}

export function GoldButton({ title, onPress, icon, testID, disabled, loading, style, small }: {
  title: string; onPress: () => void; icon?: any; testID?: string; disabled?: boolean; loading?: boolean; style?: ViewStyle | ViewStyle[]; small?: boolean;
}) {
  return (
    <Pressable testID={testID} disabled={disabled || loading}
      onPress={() => { tap('medium'); onPress(); }}
      style={({ pressed }) => [style as any, (disabled || loading) && { opacity: 0.45 }, pressed && { transform: [{ scale: 0.98 }] }]}>
      <LinearGradient colors={GOLD as any} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
        style={[st.goldBtn, small && { minHeight: 48, paddingHorizontal: S.lg }]}>
        {loading ? <ActivityIndicator color={C.onInverse} /> : (
          <>
            {icon && <Ionicons name={icon} size={small ? 16 : 19} color={C.onInverse} />}
            <Text style={[st.goldBtnText, small && { fontSize: 12 }]}>{title}</Text>
          </>
        )}
      </LinearGradient>
    </Pressable>
  );
}

export function Pulse({ children, minScale = 1, maxScale = 1.06, duration = 1400, style }: {
  children: React.ReactNode; minScale?: number; maxScale?: number; duration?: number; style?: ViewStyle | ViewStyle[];
}) {
  const scale = useSharedValue(minScale);
  useEffect(() => {
    scale.value = withRepeat(withSequence(withTiming(maxScale, { duration }), withTiming(minScale, { duration })), -1);
  }, [scale, minScale, maxScale, duration]);
  const anim = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  return <Animated.View style={[anim, style as any]}>{children}</Animated.View>;
}

const st = StyleSheet.create({
  glow: Platform.select({
    web: { boxShadow: '0 0 28px rgba(212,175,55,0.35)' } as any,
    default: { shadowColor: '#D4AF37', shadowOpacity: 0.38, shadowRadius: 18, shadowOffset: { width: 0, height: 0 }, elevation: 10 },
  }),
  goldBtn: { flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', minHeight: 56, borderRadius: R.pill, paddingHorizontal: S.xl },
  goldBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 14 },
});
