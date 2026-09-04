/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// USER TYPE SELECTOR — shown once right after sign-in (and from Settings → change).
import React, { useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, S, R } from '@/src/theme';
import { USER_TYPES, UserType } from '@/src/user-type';
import { tap } from '@/src/ui/glass';

export default function UserTypeScreen() {
  const router = useRouter();
  const { user, refresh } = useAuth() as any;
  const [busy, setBusy] = useState<UserType | null>(null);
  const [err, setErr] = useState('');

  const pick = async (t: UserType) => {
    tap('medium'); setBusy(t); setErr('');
    try {
      await api('/me/user-type', { method: 'PUT', body: JSON.stringify({ user_type: t }) });
      await refresh?.();
      router.replace('/(tabs)');
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  return (
    <SafeAreaView style={st.root} edges={['top', 'bottom']}>
      <ScrollView contentContainerStyle={st.body}>
        {!!user?.user_type && (
          <Pressable testID="ut-back" onPress={() => router.back()} style={st.back} hitSlop={10}>
            <Ionicons name="chevron-back" size={22} color={C.brand} />
          </Pressable>
        )}
        <Text style={st.kicker}>ARCHANGEL OS</Text>
        <Text testID="ut-title" style={st.title}>Who is using the app?</Text>
        <Text style={st.sub}>The interface adapts to you — text size, tiles and which functions come first.</Text>
        {USER_TYPES.map(t => {
          const on = user?.user_type === t.id;
          return (
            <Pressable key={t.id} testID={`ut-${t.id}`} onPress={() => pick(t.id)} disabled={!!busy}
              style={[st.card, on && st.cardOn, t.id === 'senior' && st.cardSenior]}>
              <View style={[st.icon, on && { backgroundColor: C.brand }]}>
                <Ionicons name={t.icon as any} size={t.id === 'senior' ? 34 : 26} color={on ? C.onInverse : C.brand} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={[st.label, t.id === 'senior' && { fontSize: 24 }]}>{t.label}</Text>
                <Text style={[st.hint, t.id === 'senior' && { fontSize: 15 }]}>{t.sub}</Text>
              </View>
              {busy === t.id ? <ActivityIndicator color={C.brand} /> : <Ionicons name={on ? 'checkmark-circle' : 'chevron-forward'} size={22} color={on ? C.brand : C.info} />}
            </Pressable>
          );
        })}
        {!!err && <Text style={st.err}>{err}</Text>}
        <Text style={st.foot}>You can change this any time in Settings.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  body: { padding: S.xl, gap: S.md, paddingBottom: S.xxxl },
  back: { width: 44, height: 44, justifyContent: 'center' },
  kicker: { color: C.brand, fontWeight: '900', letterSpacing: 4, fontSize: 11 },
  title: { color: C.fg, fontWeight: '900', fontSize: 28, letterSpacing: 0.5 },
  sub: { color: C.info, fontSize: 13, lineHeight: 19, marginBottom: S.sm },
  card: { flexDirection: 'row', alignItems: 'center', gap: S.md, padding: S.lg, minHeight: 84, borderWidth: 1, borderColor: C.border, borderRadius: R.md, backgroundColor: C.surface2 },
  cardOn: { borderColor: C.brand, backgroundColor: 'rgba(212,175,55,0.10)' },
  cardSenior: { minHeight: 110, borderColor: 'rgba(212,175,55,0.5)' },
  icon: { width: 56, height: 56, borderRadius: R.md, backgroundColor: C.surface3, alignItems: 'center', justifyContent: 'center' },
  label: { color: C.fg, fontWeight: '900', fontSize: 17 },
  hint: { color: C.info, fontSize: 12, marginTop: 2, lineHeight: 17 },
  err: { color: C.error, fontWeight: '800', fontSize: 12 },
  foot: { color: C.info, fontSize: 11, textAlign: 'center', marginTop: S.md },
});
