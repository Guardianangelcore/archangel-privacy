/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// ANGEL PULSE — the Haptic Heartbeat inbox + sender.
// Wordless "I'm alive, thinking of you" between Inner Circle members.
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator, RefreshControl, TextInput } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, { useSharedValue, useAnimatedStyle, withRepeat, withTiming, Easing, cancelAnimation } from 'react-native-reanimated';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, S, R, GOLD } from '@/src/theme';
import { tap } from '@/src/ui/glass';
import { playPulse, PulsePattern } from '@/src/haptic-heartbeat';

const PATTERNS: { key: PulsePattern; label: string; icon: any }[] = [
  { key: 'heartbeat', label: 'Tep srdca', icon: 'heart' },
  { key: 'soft',      label: 'Gentle',    icon: 'water' },
  { key: 'strong',    label: 'Strong',    icon: 'flash' },
  { key: 'sos',       label: 'SOS',       icon: 'warning' },
];

export default function AngelPulse() {
  const router = useRouter();
  const params = useLocalSearchParams<{ id?: string }>();
  const { user } = useAuth();  // eslint-disable-line @typescript-eslint/no-unused-vars
  const [inbox, setInbox] = useState<any[]>([]);
  const [circle, setCircle] = useState<any[]>([]);
  const [pattern, setPattern] = useState<PulsePattern>('heartbeat');
  const [bpm, setBpm] = useState('72');
  const [target, setTarget] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [msg, setMsg] = useState('');
  const beatPulse = useSharedValue(0);

  const load = useCallback(async () => {
    try {
      const [ib, cr]: any = await Promise.all([
        api('/angel/pulse/inbox'),
        api('/family/voice-signature/circle'),
      ]);
      setInbox(ib.pulses || []);
      // circle = everyone except self, only names + user_ids
      const members = (cr.members || []).filter((m: any) => !m.is_self);
      setCircle(members);
      if (!target && members[0]) setTarget(members[0].user_id);
    } catch (e) { console.log(e); }
  }, [target]);
  useEffect(() => { load(); }, [load]);

  // Auto-play a pulse when deep-linked with ?id=xxx
  useEffect(() => {
    if (!params.id || !inbox.length) return;
    const p = inbox.find((x) => x.pulse_id === params.id);
    if (p && !p.delivered) feel(p);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id, inbox]);

  const send = async () => {
    if (!target) return;
    setBusy(true); setMsg('');
    try {
      await api('/angel/pulse', {
        method: 'POST',
        body: JSON.stringify({ to_user_id: target, pattern, bpm: parseInt(bpm || '72', 10) }),
      });
      tap('success');
      setMsg('💛 Heartbeat delivered. Your family member will feel it.');
    } catch (e: any) {
      setMsg(String(e?.message || e));
    }
    setBusy(false);
  };

  const feel = (p: any) => {
    setPlayingId(p.pulse_id);
    // Animate a big pulsing heart on screen matched to the pattern
    beatPulse.value = withRepeat(
      withTiming(1, { duration: Math.max(240, 30000 / (p.bpm || 72)), easing: Easing.inOut(Easing.sin) }),
      -1, true,
    );
    const stop = playPulse(p.pattern || 'heartbeat', p.bpm || 72);
    // Acknowledge receipt after 8s so the sender sees 💛
    setTimeout(async () => {
      try { await api(`/angel/pulse/${p.pulse_id}/felt`, { method: 'POST' }); } catch {}
      stop();
      cancelAnimation(beatPulse);
      beatPulse.value = 0;
      setPlayingId(null);
      load();
    }, 8000);
  };

  const heartStyle = useAnimatedStyle(() => ({
    transform: [{ scale: 1 + beatPulse.value * 0.35 }],
    opacity: 0.75 + beatPulse.value * 0.25,
  }));

  return (
    <SafeAreaView testID="angel-pulse-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="ap-back" onPress={() => { tap(); router.back(); }} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>ANGEL PULSE</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView
        contentContainerStyle={{ padding: S.xl, paddingBottom: 120 }}
        refreshControl={<RefreshControl refreshing={false} onRefresh={load} tintColor={C.brand} />}
      >
        {playingId && (
          <View testID="ap-live" style={styles.liveWrap}>
            <Animated.View style={[styles.heartBg, heartStyle]}>
              <Ionicons name="heart" size={100} color={C.brand} />
            </Animated.View>
            <Text style={styles.liveText}>YOU FEEL A HEARTBEAT…</Text>
          </View>
        )}

        {!playingId && (
          <>
            <Text style={styles.intro}>
              No words. No message. Just a <Text style={{ color: C.brand, fontWeight: '900' }}>tangible connection</Text>.
              Your angel heartbeat arrives as a gentle vibration right into your family’s palm.
            </Text>

            {inbox.length > 0 && (
              <>
                <Text style={styles.section}>DELIVERED TO YOU · {inbox.length}</Text>
                {inbox.slice(0, 6).map((p) => (
                  <Pressable key={p.pulse_id} testID={`ap-inbox-${p.pulse_id}`} onPress={() => feel(p)} style={styles.inCard}>
                    <View style={styles.inRing}>
                      <Ionicons name="heart" size={20} color={C.brand} />
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.inName}>{p.from_name}</Text>
                      <Text style={styles.inMeta}>
                        {p.pattern} · {p.bpm} bpm · {new Date(p.created_at).toLocaleString('sk-SK')}
                      </Text>
                    </View>
                    {p.delivered ? (
                      <Ionicons name="checkmark-circle" size={20} color={C.brand} />
                    ) : (
                      <View style={styles.newDot}>
                        <Text style={styles.newDotText}>NEW</Text>
                      </View>
                    )}
                  </Pressable>
                ))}
              </>
            )}

            <Text style={styles.section}>SEND A HEARTBEAT</Text>
            {circle.length === 0 ? (
              <Text style={styles.empty}>First add someone to your family circle.</Text>
            ) : (
              <>
                <View style={styles.targetRow}>
                  {circle.map((m: any) => (
                    <Pressable
                      key={m.user_id}
                      testID={`ap-target-${m.user_id}`}
                      onPress={() => setTarget(m.user_id)}
                      style={[styles.tChip, target === m.user_id && styles.tChipActive]}
                    >
                      <Ionicons name="person-circle" size={14} color={target === m.user_id ? C.onInverse : C.brand} />
                      <Text style={[styles.tChipText, target === m.user_id && { color: C.onInverse }]}>{m.name}</Text>
                    </Pressable>
                  ))}
                </View>

                <Text style={styles.lbl}>VZOR</Text>
                <View style={styles.pRow}>
                  {PATTERNS.map((p) => (
                    <Pressable
                      key={p.key}
                      testID={`ap-pattern-${p.key}`}
                      onPress={() => setPattern(p.key)}
                      style={[styles.pChip, pattern === p.key && styles.pChipActive]}
                    >
                      <Ionicons name={p.icon} size={14} color={pattern === p.key ? C.onInverse : C.brand} />
                      <Text style={[styles.pText, pattern === p.key && { color: C.onInverse }]}>{p.label}</Text>
                    </Pressable>
                  ))}
                </View>

                <Text style={styles.lbl}>BPM (40 – 120)</Text>
                <TextInput
                  testID="ap-bpm"
                  value={bpm}
                  onChangeText={setBpm}
                  keyboardType="number-pad"
                  maxLength={3}
                  style={styles.input}
                />

                <Pressable testID="ap-send" onPress={send} disabled={busy || !target} style={styles.sendCta}>
                  <LinearGradient colors={GOLD as any} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.sendBg}>
                    {busy ? <ActivityIndicator color={C.onInverse} /> : <Ionicons name="heart" size={22} color={C.onInverse} />}
                    <Text style={styles.sendText}>SEND A HEARTBEAT</Text>
                  </LinearGradient>
                </Pressable>

                {!!msg && <Text style={styles.msg}>{msg}</Text>}
              </>
            )}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.brand, fontWeight: '900', fontSize: 13, letterSpacing: 2.5 },
  intro: { color: C.fg, fontSize: 13, lineHeight: 20, marginBottom: S.lg },
  section: { color: C.brand, fontWeight: '900', fontSize: 10, letterSpacing: 2, marginTop: S.xl, marginBottom: S.sm },
  empty: { color: C.info, fontSize: 12, fontStyle: 'italic' },
  inCard: { flexDirection: 'row', gap: S.md, alignItems: 'center', backgroundColor: C.surface2, borderRadius: R.md, padding: S.md, marginBottom: S.sm, borderWidth: 1, borderColor: C.border },
  inRing: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(212,175,55,0.1)', borderWidth: 1.5, borderColor: C.brand },
  inName: { color: C.fg, fontWeight: '900', fontSize: 14 },
  inMeta: { color: C.onS3, fontSize: 11, marginTop: 2 },
  newDot: { backgroundColor: C.brand, paddingHorizontal: 8, paddingVertical: 4, borderRadius: 10 },
  newDotText: { color: C.onInverse, fontSize: 8, letterSpacing: 1, fontWeight: '900' },
  targetRow: { flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  tChip: { flexDirection: 'row', gap: 6, alignItems: 'center', borderWidth: 1.5, borderColor: C.brand, borderRadius: R.pill, paddingHorizontal: 10, paddingVertical: 6, backgroundColor: C.surface2 },
  tChipActive: { backgroundColor: C.brand },
  tChipText: { color: C.brand, fontSize: 12, fontWeight: '900' },
  lbl: { color: C.onS3, fontSize: 10, letterSpacing: 2, fontWeight: '900', marginTop: S.lg, marginBottom: S.sm },
  pRow: { flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  pChip: { flexDirection: 'row', gap: 6, alignItems: 'center', borderWidth: 1, borderColor: C.brand, borderRadius: R.pill, paddingHorizontal: 12, paddingVertical: 8, backgroundColor: C.surface2 },
  pChipActive: { backgroundColor: C.brand },
  pText: { color: C.brand, fontSize: 12, fontWeight: '900' },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.sm, padding: S.md, fontSize: 15, color: C.fg, backgroundColor: C.surface2 },
  sendCta: { borderRadius: R.pill, overflow: 'hidden', marginTop: S.xl, shadowColor: C.brand, shadowOpacity: 0.45, shadowRadius: 16, shadowOffset: { width: 0, height: 6 }, elevation: 10 },
  sendBg: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, minHeight: 60 },
  sendText: { color: C.onInverse, fontWeight: '900', fontSize: 14, letterSpacing: 2.5 },
  msg: { color: C.brand, textAlign: 'center', fontWeight: '900', fontSize: 12, marginTop: S.md },
  liveWrap: { alignItems: 'center', justifyContent: 'center', paddingVertical: 60, gap: S.xl },
  heartBg: { alignItems: 'center', justifyContent: 'center' },
  liveText: { color: C.brand, fontSize: 14, fontWeight: '900', letterSpacing: 3 },
});
