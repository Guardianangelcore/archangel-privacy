/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// GHOST MODE & SOVEREIGN IDENTITY — foundation identity, anonymized patient tokens, power-saver
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, Switch, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { C, S } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

export default function GhostMode() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const [foundation, setFoundation] = useState<any>(null);
  const [ghost, setGhost] = useState<any>(null);
  const [power, setPower] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    try {
      const [f, g, p]: any[] = await Promise.all([api('/foundation/identity'), api('/ghost/status'), api('/power-saver')]);
      setFoundation(f); setGhost(g); setPower(p);
    } catch (e: any) { setErr(String(e.message || e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const toggleGhost = async (v: boolean) => {
    setBusy('ghost'); setErr('');
    try { setGhost(await api('/ghost/toggle', { method: 'POST', body: JSON.stringify({ enabled: v }) })); }
    catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const togglePower = async (v: boolean) => {
    setBusy('power'); setErr('');
    try {
      const r: any = await api('/power-saver', { method: 'PUT', body: JSON.stringify({ enabled: v }) });
      setPower({ power_saver: r.power_saver, profile: r.profile || power?.profile });
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  return (
    <SafeAreaView testID="ghost-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="gh-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={st.title}>{tt('ghost_mode.ghost_power')}</Text>
        <View style={{ width: 26 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        <Text style={st.section}>{tt('ghost_mode.official_foundation_identity')}</Text>
        {foundation && (
          <View style={st.card}>
            <Text testID="gh-foundation-email" style={st.emailText} selectable>{foundation.official_email}</Text>
            <Text style={st.meta}>{foundation.provider}</Text>
            <Text style={st.meta}>{foundation.entity}</Text>
            <Text style={[st.meta, { marginTop: S.sm }]}>{foundation.purpose}</Text>
            <Text style={st.meta}>{foundation.pgp}</Text>
            <View style={st.immutableBadge}><Text style={st.immutableText}>{tt('ghost_mode.immutable_hardcoded_on_chain')}</Text></View>
          </View>
        )}

        <Text style={st.section}>{tt('ghost_mode.ghost_mode')}</Text>
        <View style={st.card}>
          <View style={st.rowSpread}>
            <View style={{ flex: 1, paddingRight: S.md }}>
              <Text style={st.cardTitle}>{tt('ghost_mode.anonymized_patient_token')}</Text>
              <Text style={st.meta}>{tt('ghost_mode.clinics_even_during_medical_arbitrag')}</Text>
            </View>
            {busy === 'ghost' ? <ActivityIndicator color={C.brand} /> : (
              <Switch testID="gh-ghost-switch" value={!!ghost?.ghost_mode} onValueChange={toggleGhost}
                trackColor={{ false: C.surface3, true: C.brand }} thumbColor={C.fg} />
            )}
          </View>
          {ghost?.ghost_mode && ghost?.patient_token && (
            <View style={st.tokenBox}>
              <Text style={st.tokenLbl}>{tt('ghost_mode.your_patient_token')}</Text>
              <Text testID="gh-token" style={st.tokenVal} selectable>{ghost.patient_token}</Text>
              <Text style={st.meta}>{tt('ghost_mode.expiruje')} {ghost.expires_at ? new Date(ghost.expires_at).toLocaleString('sk-SK') : '—'}</Text>
            </View>
          )}
        </View>

        <Text style={st.section}>{tt('ghost_mode.power_saver_survival_mode')}</Text>
        <View style={st.card}>
          <View style={st.rowSpread}>
            <View style={{ flex: 1, paddingRight: S.md }}>
              <Text style={st.cardTitle}>{tt('ghost_mode.maximum_battery_life')}</Text>
              <Text style={st.meta}>{tt('ghost_mode.black_theme_animations_and_backgroun')}</Text>
            </View>
            {busy === 'power' ? <ActivityIndicator color={C.brand} /> : (
              <Switch testID="gh-power-switch" value={!!power?.power_saver} onValueChange={togglePower}
                trackColor={{ false: C.surface3, true: C.brand }} thumbColor={C.fg} />
            )}
          </View>
          {power?.power_saver && power?.profile && (
            <View style={st.tokenBox}>
              <Text style={st.tokenLbl}>{tt('ghost_mode.active_profile')}</Text>
              <Text style={st.meta}>{tt('ghost_mode.sync_interval')} {power.profile.poll_interval_sec}{tt('ghost_mode.s_estimated_battery_gain')}{power.profile.estimated_battery_gain_pct}%</Text>
              <Text style={st.meta}>{tt('ghost_mode.active_only')} {(power.profile.essential_only || []).join(' · ')}</Text>
            </View>
          )}
        </View>

        {!!err && <Text testID="gh-err" style={st.err}>{err}</Text>}
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  section: { color: C.info, fontSize: 11, fontWeight: '900', letterSpacing: 2, marginTop: S.xl, marginBottom: S.sm },
  card: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.lg, backgroundColor: C.surface2 },
  rowSpread: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  cardTitle: { color: C.fg, fontSize: 14, fontWeight: '800' },
  emailText: { color: C.brand, fontSize: 16, fontWeight: '900' },
  meta: { color: C.info, fontSize: 11, marginTop: 4, lineHeight: 16 },
  immutableBadge: { backgroundColor: '#1B4332', paddingHorizontal: 8, paddingVertical: 4, alignSelf: 'flex-start', marginTop: S.md },
  immutableText: { color: '#FFFFFF', fontSize: 9, fontWeight: '900', letterSpacing: 1 },
  tokenBox: { borderWidth: 1.5, borderColor: C.brand, padding: S.md, marginTop: S.md },
  tokenLbl: { color: C.info, fontSize: 9, fontWeight: '900', letterSpacing: 2 },
  tokenVal: { color: C.brand, fontSize: 20, fontWeight: '900', marginTop: 4 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginTop: S.md },
});
