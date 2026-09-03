/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// SOVEREIGN CONFETTI — a lightweight gold-burst overlay for badge unlocks.
// Fires one particle sheet on demand, auto-cleans after ~2.4s.
// Zero deps beyond react-native-reanimated (already in the app).
import React, { useEffect, useMemo } from 'react';
import { View, StyleSheet, Platform, Dimensions } from 'react-native';
import Animated, {
  useSharedValue, useAnimatedStyle, withTiming, withDelay, Easing,
} from 'react-native-reanimated';

const GOLDS = ['#FFD700', '#F4C542', '#D4AF37', '#B8860B', '#FFF3B0', '#E8C86A'];
const PIECE_COUNT = 42;

type Piece = { id: number; x: number; delay: number; color: string; rot: number; size: number; sway: number };

function makePieces(width: number): Piece[] {
  const arr: Piece[] = [];
  for (let i = 0; i < PIECE_COUNT; i++) {
    arr.push({
      id: i,
      x: Math.random() * width,
      delay: Math.random() * 320,
      color: GOLDS[i % GOLDS.length],
      rot: Math.random() * 720 - 360,
      size: 8 + Math.random() * 8,
      sway: (Math.random() - 0.5) * 90,
    });
  }
  return arr;
}

function PieceView({ piece, height }: { piece: Piece; height: number }) {
  const y = useSharedValue(-30);
  const x = useSharedValue(0);
  const rot = useSharedValue(0);
  const opacity = useSharedValue(1);

  useEffect(() => {
    y.value = withDelay(piece.delay, withTiming(height + 40, { duration: 1900, easing: Easing.out(Easing.quad) }));
    x.value = withDelay(piece.delay, withTiming(piece.sway, { duration: 1900, easing: Easing.inOut(Easing.sin) }));
    rot.value = withDelay(piece.delay, withTiming(piece.rot, { duration: 1900, easing: Easing.linear }));
    opacity.value = withDelay(piece.delay + 1400, withTiming(0, { duration: 500 }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const style = useAnimatedStyle(() => ({
    transform: [
      { translateX: x.value },
      { translateY: y.value },
      { rotate: `${rot.value}deg` },
    ],
    opacity: opacity.value,
  }));

  return (
    <Animated.View
      pointerEvents="none"
      style={[
        {
          position: 'absolute',
          left: piece.x,
          top: 0,
          width: piece.size,
          height: piece.size * 0.6,
          backgroundColor: piece.color,
          borderRadius: 2,
        },
        style,
      ]}
    />
  );
}

export function ConfettiBurst({ onDone }: { onDone?: () => void }) {
  const { width, height } = Dimensions.get('window');
  const pieces = useMemo(() => makePieces(width), [width]);

  useEffect(() => {
    const t = setTimeout(() => onDone?.(), 2400);
    return () => clearTimeout(t);
  }, [onDone]);

  return (
    <View
      pointerEvents="none"
      style={[
        StyleSheet.absoluteFill,
        Platform.OS === 'web' ? ({ position: 'fixed' as any } as any) : null,
        { overflow: 'hidden', zIndex: 10000 },
      ]}
    >
      {pieces.map((p) => (
        <PieceView key={p.id} piece={p} height={height} />
      ))}
    </View>
  );
}
