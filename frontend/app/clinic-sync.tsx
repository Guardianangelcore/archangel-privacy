/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// CLINIC SYNC — The Doctor Link: QR handshake + simulated BLE/NFC radar → reports beamed into the Vault
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import QRCode from 'react-native-qrcode-svg';
import Animated, { useSharedValue, useAnimatedStyle, withRepeat, withTiming, Easing } from 'react-native-reanimated';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';
import { GlassCard, GoldButton, tap } from '@/src/ui/glass';

function RadarRing({ delay }: { delay: number }) {
  const v = useSharedValue(0);
  useEffect(() => {
    const id = setTimeout(() => { v.value = withRepeat(withTiming(1, { duration: 2400, easing: Easing.out(Easing.quad) }), -1); }, delay);
    return () => clearTimeout(id);
  }, [v, delay]);
  const anim = useAnimatedStyle(() => ({
    transform: [{ scale: 0.3 + v.value * 1.1 }],
    opacity: 0.55 * (1 - v.value),
  }));
  return <Animated.View style={[st.ring, anim]} />;
}

export default function ClinicSync() {
  const router = useRouter();
  const [mode, setMode] = useState<'radar' | 'qr'>('radar');
  const [session, setSession] = useState<any>(null);
  const [radar, setRadar] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState('');
  const poll = useRef<any>(null);

  const loadSession = useCallback(async () => {
    try { setSession(await api('/clinic-sync/session')); } catch (e) { console.log(e); }
  }, []);

  useEffect(() => {
    loadSession();
    (async () => { try { setRadar(await api('/clinic-sync/radar')); } catch (e) { console.log(e); } })();
    poll.current = setInterval(loadSession, 5000);
    return () => clearInterval(poll.current);
  }, [loadSession]);

  const createSession = async () => {
    setBusy('create'); setErr('');
    try { setSession(await api('/clinic-sync/session', { method: 'POST' })); setMode('qr'); tap('success'); }
    catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const simulateBeam = async () => {
    setBusy('beam'); setErr('');
    try {
      await api('/clinic-sync/simulate-beam', { method: 'POST', body: JSON.stringify({}) });
      await loadSession();
      tap('success');
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const waiting = session?.status === 'waiting';
  const docs = session?.received_docs || [];

  return (
    <SafeAreaView testID="clinic-sync-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="csy-back" onPress={() => { tap(); router.back(); }} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.fg} />
        </Pressable>
        <Text style={st.title}>CLINIC SYNC</Text>
        <View style={{ width: 26 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        <Text style={st.tag}>Your doctor beams a report straight into your vault — no paper, no e-mails.</Text>

        <View style={st.toggle}>
          <Pressable testID="csy-mode-radar" onPress={() => { tap(); setMode('radar'); }} style={[st.toggleBtn, mode === 'radar' && st.toggleActive]}>
            <Ionicons name="radio-outline" size={16} color={mode === 'radar' ? C.onInverse : C.brand} />
            <Text style={[st.toggleText, mode === 'radar' && { color: C.onInverse }]}>RADAR (BLE/NFC)</Text>
          </Pressable>
          <Pressable testID="csy-mode-qr" onPress={() => { tap(); setMode('qr'); }} style={[st.toggleBtn, mode === 'qr' && st.toggleActive]}>
            <Ionicons name="qr-code-outline" size={16} color={mode === 'qr' ? C.onInverse : C.brand} />
            <Text style={[st.toggleText, mode === 'qr' && { color: C.onInverse }]}>QR HANDSHAKE</Text>
          </Pressable>
        </View>

        {mode === 'radar' ? (
          <GlassCard glow pad={S.lg} style={{ marginTop: S.lg }}>
            <View style={st.radarBox}>
              <RadarRing delay={0} />
              <RadarRing delay={800} />
              <RadarRing delay={1600} />
              <View style={st.radarCore}><Ionicons name="medkit" size={26} color={C.onInverse} /></View>
            </View>
            <Text style={st.radarLbl}>SCANNING NEARBY… ({radar?.nearby?.length ?? 0} devices)</Text>
            <Text style={st.simNote}>⚠ {radar?.transport || 'BLE/NFC simulation — real radio in a native build'}</Text>
            {(radar?.nearby || []).map((n: any, i: number) => (
              <View key={i} style={st.clinicRow}>
                <Ionicons name="business-outline" size={20} color={C.brand} />
                <View style={{ flex: 1 }}>
                  <Text style={st.clinicName}>{n.clinic}</Text>
                  <Text style={st.clinicSub}>{n.dept} · {n.distance_m} m · signal {n.signal}</Text>
                </View>
                <View style={st.signalDot} />
              </View>
            ))}
          </GlassCard>
        ) : (
          <GlassCard glow pad={S.lg} style={{ marginTop: S.lg }}>
            {waiting ? (
              <View style={{ alignItems: 'center' }}>
                <View style={st.qrWrap}>
                  <QRCode value={session.qr_payload} size={190} backgroundColor="#FFFFFF" color="#000000" />
                </View>
                <Text testID="csy-code" style={st.code}>{session.code}</Text>
                <Text style={st.qrHint}>The doctor scans the QR or enters the code — the report is instantly and encryptedly stored in your vault. Valid for 10 minutes.</Text>
              </View>
            ) : (
              <View style={{ alignItems: 'center', gap: S.md }}>
                <Ionicons name="qr-code-outline" size={56} color={C.brand} />
                <Text style={st.qrHint}>Generate a one-time security code for the practice.</Text>
              </View>
            )}
            <GoldButton testID="csy-create" title={waiting ? 'NEW CODE' : 'GENERATE QR HANDSHAKE'} icon="qr-code"
              onPress={createSession} loading={busy === 'create'} style={{ marginTop: S.lg }} />
            {waiting && (
              <Pressable testID="csy-simulate" onPress={simulateBeam} disabled={busy === 'beam'} style={st.simBtn}>
                {busy === 'beam' ? <ActivityIndicator size="small" color={C.brand} /> : (
                  <Text style={st.simBtnText}>▶ DEMO: SIMULATE RECEIVING A REPORT FROM A DOCTOR</Text>
                )}
              </Pressable>
            )}
          </GlassCard>
        )}

        {!!err && <Text testID="csy-err" style={st.err}>{err}</Text>}

        <Text style={st.section}>RECEIVED REPORTS ({docs.length})</Text>
        {docs.length === 0 && <Text style={st.empty}>NONE YET — WAITING FOR A DOCTOR BEAM</Text>}
        {docs.map((d: any, i: number) => (
          <GlassCard key={i} pad={S.md} style={{ marginTop: S.sm }} testID={`csy-doc-${d.doc_id}`}
            onPress={() => router.push('/(tabs)/vault')}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.md }}>
              <Ionicons name="document-text" size={24} color={C.brand} />
              <View style={{ flex: 1 }}>
                <Text style={st.docTitle}>{d.title}</Text>
                <Text style={st.docSub}>{d.clinic_name}{d.doctor_name ? ` · ${d.doctor_name}` : ''} → stored in the Vault ✓</Text>
              </View>
              <Ionicons name="chevron-forward" size={18} color={C.info} />
            </View>
          </GlassCard>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.brand, fontSize: 18, fontWeight: '900', letterSpacing: 3 },
  tag: { color: C.info, fontSize: 11.5, letterSpacing: 0.5, textAlign: 'center', lineHeight: 17 },
  toggle: { flexDirection: 'row', gap: S.sm, marginTop: S.lg },
  toggleBtn: { flex: 1, flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', minHeight: 52, borderRadius: R.pill, borderWidth: 1.5, borderColor: C.borderStrong },
  toggleActive: { backgroundColor: C.brand, borderColor: C.brand },
  toggleText: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  radarBox: { height: 200, alignItems: 'center', justifyContent: 'center' },
  ring: { position: 'absolute', width: 180, height: 180, borderRadius: 90, borderWidth: 2, borderColor: C.brand },
  radarCore: { width: 64, height: 64, borderRadius: 32, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center' },
  radarLbl: { color: C.fg, fontWeight: '900', fontSize: 12, letterSpacing: 1.5, textAlign: 'center', marginTop: S.sm },
  simNote: { color: C.info, fontSize: 10, textAlign: 'center', marginTop: 4 },
  clinicRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, minHeight: 56, borderTopWidth: 1, borderColor: C.border, marginTop: S.sm, paddingTop: S.sm },
  clinicName: { color: C.fg, fontWeight: '800', fontSize: 13.5 },
  clinicSub: { color: C.info, fontSize: 11, marginTop: 2 },
  signalDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: '#32D74B' },
  qrWrap: { backgroundColor: '#FFFFFF', padding: 14, borderRadius: R.md },
  code: { color: C.brand, fontSize: 30, fontWeight: '900', letterSpacing: 8, marginTop: S.md },
  qrHint: { color: C.onS3, fontSize: 12, lineHeight: 18, textAlign: 'center', marginTop: S.sm },
  simBtn: { marginTop: S.md, minHeight: 48, alignItems: 'center', justifyContent: 'center', borderRadius: R.pill, borderWidth: 1.5, borderColor: C.border, borderStyle: 'dashed' },
  simBtnText: { color: C.info, fontWeight: '800', fontSize: 11, letterSpacing: 0.5 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginTop: S.md, textAlign: 'center' },
  section: { color: C.info, fontSize: 11, fontWeight: '900', letterSpacing: 2, marginTop: S.xl, marginBottom: S.xs },
  empty: { textAlign: 'center', color: C.info, marginTop: S.md, letterSpacing: 1.5, fontWeight: '800', fontSize: 11 },
  docTitle: { color: C.fg, fontWeight: '800', fontSize: 14 },
  docSub: { color: C.info, fontSize: 11, marginTop: 2 },
});
