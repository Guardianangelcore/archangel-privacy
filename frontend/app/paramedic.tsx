/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// The Paramedic Key — smart-lock emergency entry codes + NCZI/ÚZIS registry verification
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, TextInput, ActivityIndicator, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import Art50 from '@/src/Art50';
import { C, S } from '@/src/theme';
import { Lang } from '@/src/i18n';
import { useI18n } from '@/src/i18n-context';

export default function Paramedic() {
  const { t: tt, tx } = useI18n();
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'en';
  const router = useRouter();
  const [locks, setLocks] = useState<any[]>([]);
  const [vendors, setVendors] = useState<string[]>([]);
  const [active, setActive] = useState<any[]>([]);
  const [lockName, setLockName] = useState('Front door');
  const [vendor, setVendor] = useState('nuki');
  const [lic, setLic] = useState('');
  const [country, setCountry] = useState<'SK' | 'CZ'>('SK');
  const [regResult, setRegResult] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    try {
      const [l, a] = await Promise.all([api('/paramedic/locks'), api('/paramedic/access/active')]);
      setLocks((l as any).locks || []); setVendors((l as any).vendors || []);
      setActive((a as any).active || []);
    } catch (e: any) { setErr(String(e.message || e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key); setErr(''); setMsg('');
    try { await fn(); await load(); } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const addLock = () => run('addlock', async () => {
    await api('/paramedic/locks', { method: 'POST', body: JSON.stringify({ vendor, name: lockName }) });
    setMsg('Smart lock registered.');
  });
  const delLock = (id: string) => run(`dl-${id}`, async () => {
    await api(`/paramedic/locks/${id}`, { method: 'DELETE' });
  });
  const issueCode = (confirm: boolean) => run('issue', async () => {
    try {
      const rec: any = await api('/paramedic/access', { method: 'POST', body: JSON.stringify({ reason: 'emergency', confirm }) });
      setMsg(`ENTRY CODE ${rec.code} issued (valid 60 min) — guardians were notified. Verification: ${rec.emergency_verified}.`);
    } catch (e: any) {
      const m = String(e.message || e);
      if (m.includes('no_verified_emergency')) {
        setErr('No verified emergency in the last 30 min. Tap MANUAL ISSUE again to override.');
      } else { throw e; }
    }
  });
  const verifyRegistry = () => run('reg', async () => {
    const r: any = await api('/paramedic/verify-registry', { method: 'POST', body: JSON.stringify({ license_number: lic, country }) });
    setRegResult(r);
  });

  return (
    <SafeAreaView testID="paramedic-screen" style={st.root} edges={['top', 'bottom']}>
      <View style={st.header}>
        <Pressable testID="pm-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={st.title}>{tt('paramedic.paramedic_key')}</Text>
        <View style={{ width: 26 }} />
      </View>
      <View style={st.banner}><Text style={st.bannerText}>{tt('paramedic.smart_lock_api_placeholder_nuki_somf')}</Text></View>

      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        <Text style={st.intro}>{tt('paramedic.during_a_verified_emergency_beacon_f')}</Text>

        {!!msg && <Text testID="pm-msg" style={st.msg}>{msg}</Text>}
        {!!err && <Text testID="pm-err" style={st.err}>{err}</Text>}

        {/* ACTIVE CODES */}
        {active.map(a => (
          <View key={a.access_id} style={st.codeCard}>
            <Text style={st.codeLbl}>{tt('paramedic.active_entry_code')} {a.emergency_verified?.toUpperCase()}</Text>
            <Text testID={`pm-code-${a.access_id}`} style={st.codeVal}>{a.code}</Text>
            <Text style={st.codeMeta}>{tt('paramedic.locks')} {(a.locks || []).join(', ')} {tt('paramedic.valid_until')} {String(a.expires_at).slice(11, 16)} {tt('paramedic.utc')}</Text>
          </View>
        ))}

        {/* LOCKS */}
        <Text style={st.section}>{tt('paramedic.my_smart_locks')}</Text>
        {locks.map(l => (
          <View key={l.lock_id} style={st.row}>
            <Ionicons name="lock-closed-outline" size={20} color={C.brand} />
            <View style={{ flex: 1 }}>
              <Text style={st.rowTitle}>{l.name}</Text>
              <Text style={st.rowSub}>{l.vendor.toUpperCase()} {tt('paramedic.api')} {l.api_status}</Text>
            </View>
            <Pressable testID={`pm-dellock-${l.lock_id}`} onPress={() => delLock(l.lock_id)} hitSlop={10}>
              <Ionicons name="trash-outline" size={18} color={C.error} />
            </Pressable>
          </View>
        ))}
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: S.sm, marginTop: S.sm }}>
          {vendors.map(v => (
            <Pressable testID={`pm-vendor-${v}`} key={v} onPress={() => setVendor(v)} style={[st.chip, vendor === v && st.chipActive]}>
              <Text style={[st.chipText, vendor === v && st.chipTextActive]}>{v.toUpperCase()}</Text>
            </Pressable>
          ))}
        </View>
        <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.sm }}>
          <TextInput testID="pm-lockname" value={lockName} onChangeText={setLockName} style={[st.input, { flex: 1 }]} placeholderTextColor="#777" />
          <Pressable testID="pm-addlock" onPress={addLock} disabled={busy === 'addlock'} style={st.addBtn}>
            {busy === 'addlock' ? <ActivityIndicator color={C.onInverse} size="small" /> : <Ionicons name="add" size={22} color={C.onInverse} />}
          </Pressable>
        </View>

        {/* ISSUE CODE */}
        <Pressable testID="pm-issue" onPress={() => issueCode(false)} disabled={busy === 'issue' || locks.length === 0} style={[st.actionBtn, locks.length === 0 && { opacity: 0.5 }]}>
          {busy === 'issue' ? <ActivityIndicator color={C.onError} /> : <>
            <Ionicons name="key" size={20} color={C.onError} />
            <Text style={st.actionText}>{tt('paramedic.issue_emergency_entry_code')}</Text>
          </>}
        </Pressable>
        <Pressable testID="pm-issue-manual" onPress={() => issueCode(true)} disabled={busy === 'issue' || locks.length === 0} style={st.manualBtn}>
          <Text style={st.manualText}>{tt('paramedic.manual_issue_override_without_emerge')}</Text>
        </Pressable>

        {/* REGISTRY */}
        <Text style={st.section}>{tt('paramedic.paramedic_verification_state_registr')}</Text>
        <Text style={st.intro}>{tt('paramedic.before_issuing_a_code_verify_the_cli')}</Text>
        <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.sm }}>
          {(['SK', 'CZ'] as const).map(cc => (
            <Pressable testID={`pm-country-${cc}`} key={cc} onPress={() => setCountry(cc)} style={[st.chip, country === cc && st.chipActive]}>
              <Text style={[st.chipText, country === cc && st.chipTextActive]}>{cc === 'SK' ? tt('paramedic.sk_nczi') : tt('paramedic.cz_uzis')}</Text>
            </Pressable>
          ))}
        </View>
        <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.sm }}>
          <TextInput testID="pm-license" value={lic} onChangeText={setLic} placeholder={tt('paramedic.licence_number_e_g_a1234567')}
            autoCapitalize="characters" placeholderTextColor="#777" style={[st.input, { flex: 1 }]} />
          <Pressable testID="pm-verify" onPress={verifyRegistry} disabled={busy === 'reg' || !lic.trim()} style={st.addBtn}>
            {busy === 'reg' ? <ActivityIndicator color={C.onInverse} size="small" /> : <Ionicons name="shield-checkmark" size={20} color={C.onInverse} />}
          </Pressable>
        </View>
        {regResult && (
          <View testID="pm-reg-result" style={[st.regCard, { borderColor: regResult.valid ? C.brand : C.error }]}>
            <Text style={[st.regVerdict, { color: regResult.valid ? C.brand : C.error }]}>
              {regResult.valid ? tt('paramedic.verified_clinician') : tt('paramedic.not_found_in_registry')}
            </Text>
            <Text style={st.rowSub}>{regResult.registry}</Text>
            <Text style={[st.rowSub, { marginTop: 4 }]}>{regResult.detail} {tt('paramedic.simulation')}</Text>
          </View>
        )}

        <Art50 lang={lang} />
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  banner: { backgroundColor: C.warn, paddingVertical: 6, alignItems: 'center' },
  bannerText: { color: C.onWarn, fontWeight: '900', letterSpacing: 1, fontSize: 8.5 },
  intro: { color: C.onS3, fontSize: 12, lineHeight: 18 },
  msg: { color: C.brand, fontWeight: '800', fontSize: 12, marginTop: S.md, lineHeight: 17 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginTop: S.md, lineHeight: 17 },
  codeCard: { marginTop: S.md, borderWidth: 2, borderColor: C.brand, padding: S.lg, alignItems: 'center', backgroundColor: C.surface2 },
  codeLbl: { color: C.info, fontSize: 9, letterSpacing: 2, fontWeight: '800' },
  codeVal: { color: C.brand, fontSize: 44, fontWeight: '900', letterSpacing: 8, marginVertical: 4, fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }) },
  codeMeta: { color: C.onS3, fontSize: 10, letterSpacing: 0.5 },
  section: { marginTop: S.xl, marginBottom: S.sm, fontSize: 11, letterSpacing: 2, color: C.fg, fontWeight: '900' },
  row: { flexDirection: 'row', alignItems: 'center', gap: S.md, borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginBottom: S.sm, backgroundColor: C.surface2 },
  rowTitle: { fontWeight: '900', color: C.fg, fontSize: 13 },
  rowSub: { color: C.info, fontSize: 11, marginTop: 2, lineHeight: 15 },
  chip: { paddingHorizontal: S.md, paddingVertical: 8, borderWidth: 1.5, borderColor: C.borderStrong, minHeight: 36, justifyContent: 'center' },
  chipActive: { backgroundColor: C.brand, borderColor: C.brand },
  chipText: { fontWeight: '800', color: C.fg, fontSize: 11, letterSpacing: 1 },
  chipTextActive: { color: C.onInverse },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 14, color: C.fg, backgroundColor: C.surface2 },
  addBtn: { width: 50, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center' },
  actionBtn: { marginTop: S.xl, flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', backgroundColor: C.error, paddingVertical: S.lg, minHeight: 56 },
  actionText: { color: C.onError, fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  manualBtn: { marginTop: S.sm, alignItems: 'center', paddingVertical: S.md, borderWidth: 1.5, borderColor: C.borderStrong, minHeight: 44, justifyContent: 'center' },
  manualText: { color: C.onS3, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  regCard: { marginTop: S.md, borderWidth: 2, padding: S.md, backgroundColor: C.surface2 },
  regVerdict: { fontWeight: '900', fontSize: 14, letterSpacing: 1 },
});
