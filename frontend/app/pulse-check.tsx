/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator, Switch } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useAuth } from '@/src/auth';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

export default function PulseCheck() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const { user, setUser } = useAuth();
  const optin = !!(user as any)?.pulse_check_optin;
  const [inbox, setInbox] = useState<any[]>([]);
  const [sent, setSent] = useState<any[]>([]);
  const [did, setDid] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [info, setInfo] = useState('');

  const load = async () => {
    try {
      const [i, s] = await Promise.all([api('/pulse/requests'), api('/pulse/sent')]);
      setInbox(i); setSent(s);
    } catch {}
  };
  useEffect(() => { load(); }, []);

  const setOptin = async (v: boolean) => {
    try {
      const u: any = await api('/me/prefs', { method: 'PATCH', body: JSON.stringify({ pulse_check_optin: v }) });
      setUser(u);
    } catch (e: any) { setErr(String(e.message || e)); }
  };

  const send = async () => {
    if (!did.trim()) return;
    setBusy(true); setErr(''); setInfo('');
    try {
      await api('/pulse/request', { method: 'POST', body: JSON.stringify({ target_did: did.trim() }) });
      setInfo('Silent ping sent. You will see the reply below.');
      setDid('');
      await load();
    } catch (e: any) {
      const msg = String(e.message || e);
      setErr(msg.includes('opt_in_required') ? 'This user has not enabled Pulse Check — privacy is strictly opt-in.' : msg);
    } finally { setBusy(false); }
  };

  const respond = async (id: string, status: 'ok' | 'need_help') => {
    try { await api(`/pulse/requests/${id}/respond`, { method: 'POST', body: JSON.stringify({ status }) }); await load(); }
    catch (e: any) { setErr(String(e.message || e)); }
  };

  const pending = inbox.filter(r => r.status === 'pending');

  return (
    <SafeAreaView testID="pulse-check-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="pc-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>{tt('pulse_check.guardian_pulse')}</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
        <View style={styles.heroIcon}><Ionicons name="pulse-outline" size={28} color={C.brand} /></View>
        <Text style={styles.h1}>{tt('pulse_check.a_silent_ping_to_family')}</Text>
        <Text style={styles.sub}>
          {tt('pulse_check.your_inner_circle_can_discreetly_ask')}
        </Text>

        <View style={styles.privacyBox}>
          <Ionicons name="lock-closed-outline" size={20} color={C.brand} />
          <View style={{ flex: 1 }}>
            <Text style={styles.privacyTitle}>{tt('pulse_check.privacy_strictly_opt_in')}</Text>
            <Text style={styles.privacySub}>
              {tt('pulse_check.family_can_send_you_pings_only_if_yo')}
            </Text>
          </View>
          <Switch testID="pc-optin" value={optin} onValueChange={setOptin} trackColor={{ true: C.brand, false: C.surface3 }} />
        </View>

        {pending.length > 0 && (
          <>
            <Text style={styles.section}>{tt('pulse_check.awaiting_your_reply')}</Text>
            {pending.map(r => (
              <View key={r.req_id} style={styles.pingCard}>
                <Text style={styles.pingFrom}>💛 {r.from_name} {tt('pulse_check.is_asking_are_you_ok')}</Text>
                <View style={{ flexDirection: 'row', gap: S.md, marginTop: S.md }}>
                  <Pressable testID={`pc-ok-${r.req_id}`} onPress={() => respond(r.req_id, 'ok')} style={styles.okBtn}>
                    <Text style={styles.okText}>{tt('pulse_check.som_ok')}</Text>
                  </Pressable>
                  <Pressable testID={`pc-help-${r.req_id}`} onPress={() => respond(r.req_id, 'need_help')} style={styles.helpBtn}>
                    <Text style={styles.helpText}>{tt('pulse_check.potrebujem_pomoc')}</Text>
                  </Pressable>
                </View>
              </View>
            ))}
          </>
        )}

        <Text style={styles.section}>{tt('pulse_check.send_a_silent_ping')}</Text>
        <TextInput
          testID="pc-did-input"
          style={styles.input}
          placeholder={tt('pulse_check.family_member_did_did_guardian')}
          placeholderTextColor={C.info}
          value={did}
          onChangeText={setDid}
          autoCapitalize="none"
        />
        <Pressable testID="pc-send" onPress={send} disabled={busy || !did.trim()} style={[styles.cta, (!did.trim() || busy) && { opacity: 0.5 }]}>
          {busy ? <ActivityIndicator color={C.onInverse} /> : (
            <>
              <Ionicons name="paper-plane-outline" size={16} color={C.onInverse} />
              <Text style={styles.ctaText}>{tt('pulse_check.send_ping')}</Text>
            </>
          )}
        </Pressable>
        {!!err && <Text style={styles.err}>{err}</Text>}
        {!!info && <Text style={styles.info}>{info}</Text>}

        {sent.length > 0 && (
          <>
            <Text style={styles.section}>{tt('pulse_check.sent_pings')}</Text>
            {sent.map(r => (
              <View key={r.req_id} style={styles.sentRow}>
                <Text style={styles.sentDid} numberOfLines={1}>{r.target_did}</Text>
                <Text style={[styles.sentStatus, r.status === 'ok' && { color: '#5FA779' }, r.status === 'need_help' && { color: C.error }]}>
                  {r.status === 'pending' ? tt('pulse_check.waiting') : r.status === 'ok' ? tt('pulse_check.ok') : tt('pulse_check.needs_help')}
                </Text>
              </View>
            ))}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 14 },
  heroIcon: { width: 56, height: 56, borderRadius: R.lg, backgroundColor: C.brandTer, alignItems: 'center', justifyContent: 'center' },
  h1: { marginTop: S.lg, fontSize: 24, fontWeight: '900', color: C.fg },
  sub: { marginTop: S.sm, fontSize: 13, color: C.onS3, lineHeight: 19 },
  privacyBox: { marginTop: S.xl, flexDirection: 'row', alignItems: 'center', gap: S.md, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.brand, padding: S.lg },
  privacyTitle: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  privacySub: { color: C.onS3, fontSize: 11, lineHeight: 16, marginTop: 2 },
  section: { marginTop: S.xl, marginBottom: S.sm, fontSize: 11, letterSpacing: 2, color: C.info, fontWeight: '800' },
  pingCard: { backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.warn, padding: S.lg, marginBottom: S.sm },
  pingFrom: { color: C.fg, fontWeight: '800', fontSize: 14 },
  okBtn: { flex: 1, backgroundColor: '#5FA779', borderRadius: R.sm, minHeight: 52, alignItems: 'center', justifyContent: 'center' },
  okText: { color: '#0E1B12', fontWeight: '900', letterSpacing: 1, fontSize: 13 },
  helpBtn: { flex: 1, backgroundColor: C.error, borderRadius: R.sm, minHeight: 52, alignItems: 'center', justifyContent: 'center' },
  helpText: { color: C.onError, fontWeight: '900', letterSpacing: 0.5, fontSize: 11 },
  input: { backgroundColor: C.surface2, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, color: C.fg, paddingHorizontal: S.lg, minHeight: 50, fontSize: 13 },
  cta: { marginTop: S.md, flexDirection: 'row', gap: S.sm, backgroundColor: C.brand, borderRadius: R.sm, minHeight: 50, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  sentRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: S.md, backgroundColor: C.surface2, borderRadius: R.sm, padding: S.md, marginBottom: S.sm },
  sentDid: { color: C.onS3, fontSize: 11, fontFamily: 'monospace', flex: 1 },
  sentStatus: { color: C.info, fontWeight: '900', fontSize: 10, letterSpacing: 0.5 },
  err: { color: C.error, marginTop: S.md, fontSize: 12 },
  info: { color: '#5FA779', marginTop: S.md, fontSize: 12 },
});
