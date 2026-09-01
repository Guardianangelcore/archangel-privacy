/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// COGNITIVE TRIAGE — Crisis HUD overlay.
// Full-screen high-contrast "Heads-Up Display" that mounts automatically when
// the backend's /api/triage/state reports `crisis_level === 'crisis'`.
// Two large buttons: (1) Emergency Call · (2) Survival Instructions. Everything
// else in the app is hidden until the user dismisses (15-min cooldown).
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, Pressable, Modal, Linking, ScrollView, Platform, ActivityIndicator, AppState } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { api } from './api';
import { useAuth } from './auth';

const POLL_MS = 30_000; // 30s poll while calm; disabled while HUD is open

async function callEmergency() {
  const num = '112';
  try {
    if (Platform.OS !== 'web') Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
  } catch {}
  const tel = `tel:${num}`;
  try {
    const supported = await Linking.canOpenURL(tel);
    if (supported) await Linking.openURL(tel);
  } catch {}
}

export function CrisisHUD() {
  const { user } = useAuth();
  const [state, setState] = useState<any>(null);
  const [showInstructions, setShowInstructions] = useState(false);
  const [dismissing, setDismissing] = useState(false);
  const timer = useRef<any>(null);

  const poll = useCallback(async () => {
    if (!user?.user_id) return;
    try {
      const r: any = await api('/triage/state');
      setState(r);
      if (r?.auto_open_hud) {
        try { if (Platform.OS !== 'web') Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning); } catch {}
      }
    } catch {}
  }, [user?.user_id]);

  useEffect(() => {
    if (!user?.user_id) return;
    poll();
    const kick = () => { if (timer.current) clearInterval(timer.current); timer.current = setInterval(poll, POLL_MS); };
    kick();
    const sub = AppState.addEventListener('change', (s) => { if (s === 'active') poll(); });
    return () => { if (timer.current) clearInterval(timer.current); sub.remove(); };
  }, [user?.user_id, poll]);

  const dismiss = async () => {
    setDismissing(true);
    try { await api('/triage/dismiss', { method: 'POST' }); await poll(); }
    catch {} finally { setDismissing(false); setShowInstructions(false); }
  };

  const visible = !!state?.auto_open_hud;
  if (!visible) return null;

  return (
    <Modal visible transparent={false} animationType="fade" onRequestClose={dismiss} statusBarTranslucent>
      <View style={styles.root} accessibilityViewIsModal>
        <View style={styles.headerRow}>
          <Ionicons name="warning" size={26} color="#FFD447" />
          <Text style={styles.title}>CRISIS MODE</Text>
          <Pressable testID="hud-dismiss" onPress={dismiss} hitSlop={16} disabled={dismissing} style={styles.close}>
            {dismissing ? <ActivityIndicator color="#FFD447" /> : <Ionicons name="close" size={26} color="#FFD447" />}
          </Pressable>
        </View>
        <Text style={styles.reason}>
          {(state.reasons || []).length ? (state.reasons || []).join(' · ') : 'Guardian Angel detected biological stress.'}
        </Text>
        <Text style={styles.guide}>Stay calm. Breathe slowly. Pick one.</Text>

        <Pressable testID="hud-call" onPress={callEmergency} style={styles.callBtn}>
          <Ionicons name="call" size={42} color="#050510" />
          <View style={{ flex: 1 }}>
            <Text style={styles.callTitle}>CALL 112</Text>
            <Text style={styles.callSub}>Emergency line · fast response</Text>
          </View>
        </Pressable>

        <Pressable testID="hud-instr" onPress={() => setShowInstructions(true)} style={styles.instrBtn}>
          <Ionicons name="list" size={38} color="#FFD447" />
          <View style={{ flex: 1 }}>
            <Text style={styles.instrTitle}>INSTANT INSTRUCTIONS</Text>
            <Text style={styles.instrSub}>5-step survival guide</Text>
          </View>
        </Pressable>

        <Text style={styles.footer}>A silent alert was sent to your Guardian Circle.  ·  AI Content · Sovereign Protocol</Text>
      </View>

      <Modal visible={showInstructions} transparent animationType="slide" onRequestClose={() => setShowInstructions(false)}>
        <View style={styles.sheetWrap}>
          <View style={styles.sheet}>
            <View style={styles.sheetHead}>
              <Ionicons name="medkit" size={22} color="#FFD447" />
              <Text style={styles.sheetTitle}>SURVIVAL INSTRUCTIONS</Text>
              <Pressable testID="hud-instr-close" onPress={() => setShowInstructions(false)} hitSlop={16}>
                <Ionicons name="close" size={24} color="#FFD447" />
              </Pressable>
            </View>
            <ScrollView style={{ maxHeight: 400 }} contentContainerStyle={{ paddingBottom: 20 }}>
              {(state.instructions || []).map((s: string, i: number) => (
                <View key={i} style={styles.step}>
                  <Text style={styles.stepText}>{s}</Text>
                </View>
              ))}
              <View style={styles.numbers}>
                <Text style={styles.numbersTitle}>EMERGENCY NUMBERS</Text>
                {Object.entries(state.emergency_numbers || {}).map(([k, v]) => (
                  <Pressable key={k} testID={`hud-num-${k}`} onPress={() => Linking.openURL(`tel:${v}`)} style={styles.numRow}>
                    <Text style={styles.numLabel}>{k}</Text>
                    <Text style={styles.numValue}>{String(v)}</Text>
                  </Pressable>
                ))}
              </View>
            </ScrollView>
            <Pressable testID="hud-instr-call" onPress={callEmergency} style={styles.sheetCall}>
              <Ionicons name="call" size={22} color="#050510" />
              <Text style={styles.sheetCallText}>CALL 112 NOW</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </Modal>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#050510', paddingHorizontal: 20, paddingTop: 60, paddingBottom: 30 },
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  title: { color: '#FFD447', fontSize: 20, fontWeight: '900', letterSpacing: 3, flex: 1 },
  close: { padding: 6 },
  reason: { color: '#FF6B6B', fontSize: 14, fontWeight: '800', marginTop: 12, letterSpacing: 0.4, lineHeight: 20 },
  guide: { color: '#FFFFFF', fontSize: 22, fontWeight: '900', letterSpacing: 1, marginTop: 28, lineHeight: 30 },
  callBtn: { marginTop: 32, flexDirection: 'row', gap: 20, alignItems: 'center', backgroundColor: '#FFD447', borderRadius: 24, padding: 24, minHeight: 120 },
  callTitle: { color: '#050510', fontSize: 28, fontWeight: '900', letterSpacing: 2 },
  callSub: { color: '#050510', fontSize: 14, fontWeight: '700', marginTop: 4, opacity: 0.85 },
  instrBtn: { marginTop: 18, flexDirection: 'row', gap: 20, alignItems: 'center', backgroundColor: 'rgba(255,212,71,0.12)', borderWidth: 2, borderColor: '#FFD447', borderRadius: 24, padding: 22, minHeight: 100 },
  instrTitle: { color: '#FFD447', fontSize: 22, fontWeight: '900', letterSpacing: 1.5 },
  instrSub: { color: '#FFFFFF', fontSize: 13, fontWeight: '700', marginTop: 4 },
  footer: { color: '#8A8A94', fontSize: 10, textAlign: 'center', marginTop: 'auto', letterSpacing: 1 },
  sheetWrap: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: 'rgba(255,255,255,0.05)', borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 22 },
  sheetHead: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 16 },
  sheetTitle: { color: '#FFD447', fontSize: 16, fontWeight: '900', letterSpacing: 2, flex: 1 },
  step: { paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: 'rgba(255,212,71,0.15)' },
  stepText: { color: '#FFFFFF', fontSize: 15, lineHeight: 22, fontWeight: '600' },
  numbers: { marginTop: 16, borderWidth: 1, borderColor: '#FFD447', borderRadius: 12, padding: 12 },
  numbersTitle: { color: '#FFD447', fontSize: 11, fontWeight: '900', letterSpacing: 2, marginBottom: 6 },
  numRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6 },
  numLabel: { color: '#FFFFFF', fontSize: 13, fontWeight: '700' },
  numValue: { color: '#FFD447', fontSize: 14, fontWeight: '900', letterSpacing: 1 },
  sheetCall: { marginTop: 12, flexDirection: 'row', gap: 12, alignItems: 'center', justifyContent: 'center', backgroundColor: '#FFD447', borderRadius: 16, paddingVertical: 16 },
  sheetCallText: { color: '#050510', fontSize: 15, fontWeight: '900', letterSpacing: 2 },
});
