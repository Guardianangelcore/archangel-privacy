/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// Professional empty-state card — no more blank screens. 14-language ready (pass translated strings).
import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import Ionicons from '@react-native-vector-icons/ionicons';
import { C, S, R } from '@/src/theme';
import { tap } from '@/src/ui/glass';

export function EmptyState({ icon, title, sub, ctaLabel, onCta, testID }: {
  icon: any; title: string; sub: string; ctaLabel?: string; onCta?: () => void; testID?: string;
}) {
  return (
    <View testID={testID} style={es.wrap}>
      <View style={es.iconRing}>
        <Ionicons name={icon} size={34} color={C.brand} />
      </View>
      <Text style={es.title}>{title}</Text>
      <Text style={es.sub}>{sub}</Text>
      {!!ctaLabel && !!onCta && (
        <Pressable testID={testID ? `${testID}-cta` : undefined} onPress={() => { tap('light'); onCta(); }} style={es.cta}>
          <Ionicons name="add" size={18} color={C.onInverse} />
          <Text style={es.ctaText}>{ctaLabel}</Text>
        </Pressable>
      )}
    </View>
  );
}

const es = StyleSheet.create({
  wrap: { alignItems: 'center', paddingVertical: S.xl, paddingHorizontal: S.lg, marginTop: S.lg, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border },
  iconRing: { width: 72, height: 72, borderRadius: 36, borderWidth: 1.5, borderColor: C.borderStrong, backgroundColor: 'rgba(212,175,55,0.08)', alignItems: 'center', justifyContent: 'center' },
  title: { color: C.fg, fontWeight: '900', fontSize: 16, letterSpacing: 0.5, marginTop: S.md, textAlign: 'center' },
  sub: { color: C.onS3, fontSize: 13, lineHeight: 19, textAlign: 'center', marginTop: S.sm },
  cta: { flexDirection: 'row', gap: 6, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, borderRadius: R.pill, minHeight: 50, paddingHorizontal: S.xl, marginTop: S.lg },
  ctaText: { color: C.onInverse, fontWeight: '900', fontSize: 12, letterSpacing: 1.5 },
});
