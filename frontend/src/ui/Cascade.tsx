/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// CASCADE — premium staggered entrance: children "fall" into place from above, one after another.
// Slow & smooth (560 ms, cubic-out), delay = index × 90 ms. Re-mount (change `key`) to replay.
import React, { useEffect, useRef } from 'react';
import { Animated, Easing, StyleProp, ViewStyle } from 'react-native';

export function Cascade({ index, children, style, from = -56, delayStep = 90, duration = 560 }: {
  index: number; children: React.ReactNode; style?: StyleProp<ViewStyle>; from?: number; delayStep?: number; duration?: number;
}) {
  const v = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    v.setValue(0);
    Animated.timing(v, { toValue: 1, duration, delay: index * delayStep, easing: Easing.out(Easing.cubic), useNativeDriver: true }).start();
  }, [v, index, delayStep, duration]);
  return (
    <Animated.View style={[style, { opacity: v, transform: [{ translateY: v.interpolate({ inputRange: [0, 1], outputRange: [from, 0] }) }, { scale: v.interpolate({ inputRange: [0, 1], outputRange: [0.9, 1] }) }] }]}>
      {children}
    </Animated.View>
  );
}

/** Slow breathing glow (loop) — used for the Guardian Angel centre and web halos. */
export function Breathe({ children, style, min = 0.55, max = 1, duration = 2600 }: {
  children?: React.ReactNode; style?: StyleProp<ViewStyle>; min?: number; max?: number; duration?: number;
}) {
  const v = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    const loop = Animated.loop(Animated.sequence([
      Animated.timing(v, { toValue: 1, duration, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
      Animated.timing(v, { toValue: 0, duration, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
    ]));
    loop.start();
    return () => loop.stop();
  }, [v, duration]);
  return (
    <Animated.View style={[style, { opacity: v.interpolate({ inputRange: [0, 1], outputRange: [min, max] }), transform: [{ scale: v.interpolate({ inputRange: [0, 1], outputRange: [0.97, 1.03] }) }] }]}>
      {children}
    </Animated.View>
  );
}
