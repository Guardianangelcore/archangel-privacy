/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// Sovereign Recovery Suite — Social Recovery (guardians), QR Talisman, Passkeys + Social 2FA
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, TextInput, Switch, ActivityIndicator, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import QRCode from 'react-native-qrcode-svg';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import Art50 from '@/src/Art50';
import { C, S } from '@/src/theme';
import { ContactSheet } from '@/src/ui/ContactSheet';
import { Lang } from '@/src/i18n';
import { useI18n } from '@/src/i18n-context';

export default function RecoverySuite() {
  const { t: tt, tx } = useI18n();
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'en';
  const router = useRouter();
  const [status, setStatus] = useState<any>(null);
  const [guardians, setGuardians] = useState<any[]>([]);
  const [pending2fa, setPending2fa] = useState<any[]>([]);
  const [recRequests, setRecRequests] = useState<any[]>([]);
  const [contact, setContact] = useState('');
  const [pickerOpen, setPickerOpen] = useState(false);
  const [talisman, setTalisman] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const [st, g, p, r] = await Promise.all([
        api('/recovery-suite/status'), api('/recovery-suite/guardians'),
        api('/recovery-suite/2fa/pending'), api('/recovery-suite/social/requests'),
      ]);
      setStatus(st); setGuardians((g as any).guardians || []);
      setPending2fa((p as any).pending || []); setRecRequests((r as any).requests || []);
    } catch (e: any) { setErr(String(e.message || e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key); setErr(''); setMsg('');
    try { await fn(); await load(); } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const addGuardian = () => run('addg', async () => {
    if (!contact.trim()) return;
    await api('/recovery-suite/guardians', { method: 'POST', body: JSON.stringify({ contact: contact.trim() }) });
    setContact(''); setMsg('Guardian added ✓');
  });
  const delGuardian = (id: string) => run(`delg-${id}`, async () => {
    await api(`/recovery-suite/guardians/${id}`, { method: 'DELETE' });
  });
  const toggle2fa = (v: boolean) => run('2fa', async () => {
    await api('/recovery-suite/social-2fa', { method: 'PATCH', body: JSON.stringify({ enabled: v }) });
    setMsg(v ? 'Social 2FA enabled — guardians get a handshake on every login.' : 'Social 2FA disabled.');
  });
  const genTalisman = () => run('tal', async () => {
    const res: any = await api('/recovery-suite/talisman', { method: 'POST' });
    setTalisman(res.payload);
    setMsg('Talisman generated — PRINT IT NOW. Shown only once.');
  });
  const regPasskey = () => run('pk', async () => {
    await api('/recovery-suite/passkey/register', { method: 'POST', body: JSON.stringify({ device_name: 'Toto zariadenie' }) });
    setMsg('Passkey registered (native biometrics after build).');
  });
  const confirm2fa = (hid: string, legit: boolean) => run(`c2fa-${hid}`, async () => {
    await api(`/recovery-suite/2fa/${hid}/confirm`, { method: 'POST', body: JSON.stringify({ legit }) });
    setMsg(legit ? 'Login confirmed ✓' : 'Login flagged as SUSPICIOUS — user notified.');
  });
  const approveRec = (rid: string) => run(`apr-${rid}`, async () => {
    const res: any = await api(`/recovery-suite/social/${rid}/approve`, { method: 'POST' });
    setMsg(res.status === 'approved' ? 'Quorum reached — recovery APPROVED ✓' : `Approved ${res.approvals}/${res.needed} — waiting for another guardian.`);
  });

  const score = status?.security_score ?? 0;

  return (
    <SafeAreaView testID="recovery-suite-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="rs-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={st.title}>{tt('recovery_suite.sovereign_recovery')}</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} tintColor={C.fg} />}>

        <View style={st.scoreCard}>
          <Text style={st.scoreLbl}>{tt('recovery_suite.security_score')}</Text>
          <Text testID="rs-score" style={st.scoreVal}>{score}/100</Text>
          <View style={st.scoreBarBg}><View style={[st.scoreBar, { width: `${score}%` }]} /></View>
          <Text style={st.scoreHint}>{tt('recovery_suite.guardian_25_social_2fa_25_talisman_2')}</Text>
        </View>

        {!!msg && <Text testID="rs-msg" style={st.msg}>{msg}</Text>}
        {!!err && <Text testID="rs-err" style={st.err}>{err}</Text>}

        {/* 1 — SOCIAL RECOVERY */}
        <Text style={st.section}>{tt('recovery_suite.1_social_recovery_guardians')}</Text>
        <Text style={st.note}>{tt('recovery_suite.if_you_lose_access')} {status?.guardians >= 2 ? tt('recovery_suite.2_guardians') : tt('recovery_suite.a_guardian')} {tt('recovery_suite.will_approve_recovery_2_of_n_quorum')}</Text>
        {guardians.map(g => (
          <View key={g.guardian_id} style={st.row}>
            <Ionicons name="shield-checkmark-outline" size={20} color={C.brand} />
            <View style={{ flex: 1 }}>
              <Text style={st.rowTitle}>{g.guardian_name}</Text>
              <Text style={st.rowSub}>{g.guardian_email}</Text>
            </View>
            <Pressable testID={`rs-delg-${g.guardian_id}`} onPress={() => delGuardian(g.guardian_id)} hitSlop={10}>
              <Ionicons name="trash-outline" size={18} color={C.error} />
            </Pressable>
          </View>
        ))}
        <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.sm }}>
          <TextInput testID="rs-guardian-input" value={contact} onChangeText={setContact}
            placeholder={tt('recovery_suite.guardian_e_mail_or_did')} placeholderTextColor="#777"
            autoCapitalize="none" style={[st.input, { flex: 1 }]} />
          <Pressable testID="rs-guardian-contacts" onPress={() => setPickerOpen(true)} style={st.addBtn}>
            <Ionicons name="people-circle-outline" size={22} color={C.onInverse} />
          </Pressable>
          <Pressable testID="rs-guardian-add" onPress={addGuardian} disabled={busy === 'addg'} style={st.addBtn}>
            {busy === 'addg' ? <ActivityIndicator color={C.onInverse} size="small" /> : <Ionicons name="add" size={22} color={C.onInverse} />}
          </Pressable>
        </View>

        {/* SOCIAL 2FA */}
        <View style={[st.row, { marginTop: S.lg, borderColor: C.brand }]}>
          <Ionicons name="finger-print-outline" size={22} color={C.brand} />
          <View style={{ flex: 1 }}>
            <Text style={st.rowTitle}>{tt('recovery_suite.social_2fa_guardian_handshake')}</Text>
            <Text style={st.rowSub}>{tt('recovery_suite.on_every_new_login_a_guardian_gets_a')}</Text>
          </View>
          <Switch testID="rs-2fa-switch" value={!!status?.social_2fa_enabled} onValueChange={toggle2fa}
            trackColor={{ true: C.brand, false: C.surface3 }} />
        </View>

        {/* 2 — QR TALISMAN */}
        <Text style={st.section}>{tt('recovery_suite.2_qr_talisman_paper_rescue_key')}</Text>
        <Text style={st.note}>{tt('recovery_suite.one_time_offline_key_print_and_store')} {status?.talisman_ready ? tt('recovery_suite.active') : tt('recovery_suite.not_generated_yet')}</Text>
        {talisman && (
          <View testID="rs-talisman-qr" style={st.qrBox}>
            <View style={{ backgroundColor: '#FFFFFF', padding: 12 }}>
              <QRCode value={talisman} size={180} backgroundColor="#FFFFFF" color="#000000" />
            </View>
            <Text style={st.qrWarn}>{tt('recovery_suite.shown_only_once_print_copy_to_paper')}</Text>
          </View>
        )}
        <Pressable testID="rs-talisman-gen" onPress={genTalisman} disabled={busy === 'tal'} style={st.actionBtn}>
          {busy === 'tal' ? <ActivityIndicator color={C.onInverse} /> : <>
            <Ionicons name="qr-code-outline" size={18} color={C.onInverse} />
            <Text style={st.actionText}>{status?.talisman_ready ? tt('recovery_suite.regenerate_talisman') : tt('recovery_suite.generate_talisman')}</Text>
          </>}
        </Pressable>

        {/* 3 — PASSKEYS */}
        <Text style={st.section}>{tt('recovery_suite.3_passkey_biometria_zariadenia')}</Text>
        {(status?.passkeys || []).map((k: any) => (
          <View key={k.cred_id} style={st.row}>
            <Ionicons name="phone-portrait-outline" size={20} color={C.brand} />
            <View style={{ flex: 1 }}>
              <Text style={st.rowTitle}>{k.device_name}</Text>
              <Text style={st.rowSub}>{k.algorithm}</Text>
            </View>
          </View>
        ))}
        <Pressable testID="rs-passkey-reg" onPress={regPasskey} disabled={busy === 'pk'} style={[st.actionBtn, { backgroundColor: C.surface3 }]}>
          {busy === 'pk' ? <ActivityIndicator color={C.fg} /> : <>
            <Ionicons name="finger-print" size={18} color={C.fg} />
            <Text style={[st.actionText, { color: C.fg }]}>{tt('recovery_suite.register_passkey_placeholder')}</Text>
          </>}
        </Pressable>

        {/* GUARDIAN INBOX */}
        {(pending2fa.length > 0 || recRequests.length > 0) && (
          <>
            <Text style={st.section}>{tt('recovery_suite.i_am_a_guardian_pending_confirmation')}</Text>
            {pending2fa.map(h => (
              <View key={h.handshake_id} style={[st.row, { borderColor: C.warn, flexWrap: 'wrap' }]}>
                <View style={{ flex: 1, minWidth: 150 }}>
                  <Text style={st.rowTitle}>{tt('recovery_suite.2fa')} {h.user_name}</Text>
                  <Text style={st.rowSub}>{tt('recovery_suite.new_login')}{h.session_tail}</Text>
                </View>
                <View style={{ flexDirection: 'row', gap: S.sm }}>
                  <Pressable testID={`rs-2fa-ok-${h.handshake_id}`} onPress={() => confirm2fa(h.handshake_id, true)} style={st.miniOk}>
                    <Text style={st.miniText}>{tt('recovery_suite.je_to_on_ona')}</Text>
                  </Pressable>
                  <Pressable testID={`rs-2fa-flag-${h.handshake_id}`} onPress={() => confirm2fa(h.handshake_id, false)} style={st.miniBad}>
                    <Text style={[st.miniText, { color: C.onError }]}>{tt('recovery_suite.suspicious')}</Text>
                  </Pressable>
                </View>
              </View>
            ))}
            {recRequests.map(r => (
              <View key={r.req_id} style={[st.row, { borderColor: C.error, flexWrap: 'wrap' }]}>
                <View style={{ flex: 1, minWidth: 150 }}>
                  <Text style={st.rowTitle}>{tt('recovery_suite.obnova')} {r.user_name}</Text>
                  <Text style={st.rowSub}>{tt('recovery_suite.approved')} {r.approvals?.length || 0}/{r.needed}</Text>
                </View>
                <Pressable testID={`rs-rec-approve-${r.req_id}`} onPress={() => approveRec(r.req_id)} style={st.miniOk}>
                  <Text style={st.miniText}>{tt('recovery_suite.approve')}</Text>
                </Pressable>
              </View>
            ))}
          </>
        )}

        <Art50 lang={lang} />
      </ScrollView>

      <ContactSheet visible={pickerOpen} onClose={() => setPickerOpen(false)}
        onPick={c => setContact(c.email || c.phone || '')} />
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  scoreCard: { borderWidth: 2, borderColor: C.brand, padding: S.lg, backgroundColor: C.surface2 },
  scoreLbl: { color: C.info, fontSize: 10, letterSpacing: 2, fontWeight: '800' },
  scoreVal: { color: C.brand, fontSize: 34, fontWeight: '900', marginTop: 4 },
  scoreBarBg: { height: 8, backgroundColor: C.surface3, marginTop: S.sm },
  scoreBar: { height: 8, backgroundColor: C.brand },
  scoreHint: { color: C.info, fontSize: 10, marginTop: S.sm, letterSpacing: 0.5 },
  msg: { color: C.brand, fontWeight: '800', fontSize: 12, marginTop: S.md, lineHeight: 17 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginTop: S.md, lineHeight: 17 },
  section: { marginTop: S.xl, marginBottom: S.sm, fontSize: 11, letterSpacing: 2, color: C.fg, fontWeight: '900' },
  note: { color: C.onS3, fontSize: 12, lineHeight: 17, marginBottom: S.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: S.md, borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginBottom: S.sm, backgroundColor: C.surface2 },
  rowTitle: { fontWeight: '900', color: C.fg, fontSize: 13, letterSpacing: 0.5 },
  rowSub: { color: C.info, fontSize: 11, marginTop: 2 },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 14, color: C.fg, backgroundColor: C.bg },
  addBtn: { width: 50, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center' },
  actionBtn: { marginTop: S.sm, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, paddingVertical: S.lg, minHeight: 52 },
  actionText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  qrBox: { alignItems: 'center', gap: S.md, padding: S.lg, borderWidth: 2, borderColor: C.brand, marginBottom: S.sm },
  qrWarn: { color: C.warn, fontWeight: '900', fontSize: 10, letterSpacing: 1, textAlign: 'center' },
  miniOk: { backgroundColor: C.brand, paddingHorizontal: S.md, paddingVertical: 10, minHeight: 40, justifyContent: 'center' },
  miniBad: { backgroundColor: C.error, paddingHorizontal: S.md, paddingVertical: 10, minHeight: 40, justifyContent: 'center' },
  miniText: { color: C.onInverse, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
});
