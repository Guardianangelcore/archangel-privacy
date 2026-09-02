/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// Humanitarian Shield — verified-catastrophe identity + medical profile for Red Cross / UN aid
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, TextInput, ActivityIndicator, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import QRCode from 'react-native-qrcode-svg';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { sharePdf } from '@/src/pdf';
import Art50 from '@/src/Art50';
import { C, S } from '@/src/theme';
import { Lang } from '@/src/i18n';
import { useI18n } from '@/src/i18n-context';

export default function Humanitarian() {
  const { t: tt, tx } = useI18n();
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'en';
  const router = useRouter();
  const [status, setStatus] = useState<any>(null);
  const [kind, setKind] = useState('war');
  const [region, setRegion] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    try { setStatus(await api('/humanitarian/status')); }
    catch (e: any) { setErr(String(e.message || e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key); setErr(''); setMsg('');
    try { await fn(); await load(); } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const verify = () => run('verify', async () => {
    const ev: any = await api('/humanitarian/verify', { method: 'POST', body: JSON.stringify({ kind, region }) });
    setMsg(`Disaster VERIFIED by consensus of ${ev.consensus_sources.length} sources (simulation) — the shield is active.`);
  });
  const genProfile = () => run('profile', async () => {
    await api('/humanitarian/profile', { method: 'POST' });
    setMsg('Humanitarian profile generated — ready for Red Cross / UN intake.');
  });
  const share = () => run('pdf', async () => {
    await sharePdf('/humanitarian/card.pdf', 'guardian_humanitarian_card.pdf');
  });

  const verified = !!status?.catastrophe_verified;
  const profile = status?.profile;

  return (
    <SafeAreaView testID="humanitarian-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="hu-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={st.title}>{tt('humanitarian.humanitarian_shield')}</Text>
        <View style={{ width: 26 }} />
      </View>
      <View style={st.banner}><Text style={st.bannerText}>{tt('humanitarian.simulation_real_feeds_gdacs_who_in_p')}</Text></View>

      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        <View style={[st.statusCard, { borderColor: verified ? C.error : C.borderStrong }]}>
          <Ionicons name={verified ? 'alert-circle' : 'earth-outline'} size={30} color={verified ? C.error : C.brand} />
          <Text style={[st.statusText, verified && { color: C.error }]}>
            {verified ? tt('humanitarian.global_disaster_verified', [status.event?.label?.toUpperCase() || '']) : tt('humanitarian.no_verified_disaster_the_world_is_st')}
          </Text>
          {verified && <Text style={st.statusMeta}>{status.event?.region || tt('humanitarian.global')} {tt('humanitarian.konsenzus')} {status.event?.consensus_sources?.length} {tt('humanitarian.zdrojov')}</Text>}
        </View>

        {!!msg && <Text testID="hu-msg" style={st.msg}>{msg}</Text>}
        {!!err && <Text testID="hu-err" style={st.err}>{err}</Text>}

        <Text style={st.section}>{tt('humanitarian.1_overenie_katastrofy_konsenzus_feed')}</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: S.sm }}>
          {Object.entries(status?.kinds || {}).map(([k, v]) => (
            <Pressable testID={`hu-kind-${k}`} key={k} onPress={() => setKind(k)} style={[st.chip, kind === k && st.chipActive]}>
              <Text style={[st.chipText, kind === k && st.chipTextActive]}>{String(v).toUpperCase()}</Text>
            </Pressable>
          ))}
        </View>
        <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.sm }}>
          <TextInput testID="hu-region" value={region} onChangeText={setRegion} placeholder={tt('humanitarian.region_e_g_central_europe')}
            placeholderTextColor="#777" style={[st.input, { flex: 1 }]} />
          <Pressable testID="hu-verify" onPress={verify} disabled={busy === 'verify'} style={st.addBtn}>
            {busy === 'verify' ? <ActivityIndicator color={C.onInverse} size="small" /> : <Ionicons name="checkmark-done" size={20} color={C.onInverse} />}
          </Pressable>
        </View>

        <Text style={st.section}>{tt('humanitarian.2_humanitarian_identity_health_profi')}</Text>
        <Text style={st.intro}>{tt('humanitarian.jarvis_generates_an_official_profile')}</Text>
        <Pressable testID="hu-generate" onPress={genProfile} disabled={busy === 'profile' || !verified}
          style={[st.actionBtn, !verified && { opacity: 0.4 }]}>
          {busy === 'profile' ? <ActivityIndicator color={C.onInverse} /> : <>
            <Ionicons name="id-card-outline" size={20} color={C.onInverse} />
            <Text style={st.actionText}>{profile ? tt('humanitarian.refresh_humanitarian_profile') : tt('humanitarian.generate_humanitarian_profile')}</Text>
          </>}
        </Pressable>
        {!verified && <Text style={st.hint}>{tt('humanitarian.activates_only_after_global_disaster')}</Text>}

        {profile && (
          <View testID="hu-card" style={st.humCard}>
            <Text style={st.humId}>{profile.hum_id}</Text>
            <Text style={st.humName}>{profile.full_name}</Text>
            <Text style={st.humLine}>{tt('humanitarian.krv')} {profile.blood_type || '—'} {tt('humanitarian.alergie')} {profile.allergies || '—'}</Text>
            <Text style={st.humLine}>{tt('humanitarian.diagnoses')} {profile.conditions || '—'}</Text>
            <Text style={st.humLine}>{tt('humanitarian.lieky')} {profile.medications || '—'}</Text>
            <Text style={st.humLine}>{tt('humanitarian.vaccinations')} {(profile.vaccinations || []).map((v: any) => v.title).join(', ') || '—'}</Text>
            <View style={st.qrWrap}>
              <View style={{ backgroundColor: '#FFFFFF', padding: 10 }}>
                <QRCode value={profile.qr_payload || profile.hum_id} size={140} backgroundColor="#FFFFFF" color="#000000" />
              </View>
            </View>
            <Text style={st.humStd}>{(profile.standards || []).join(' · ')}</Text>
            <Pressable testID="hu-pdf" onPress={share} disabled={busy === 'pdf'} style={st.pdfBtn}>
              {busy === 'pdf' ? <ActivityIndicator color={C.fg} /> : <>
                <Ionicons name="share-outline" size={16} color={C.fg} />
                <Text style={st.pdfText}>{tt('humanitarian.share_card_pdf_for_aid_intake')}</Text>
              </>}
            </Pressable>
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
  title: { color: C.onInverse, fontSize: 17, fontWeight: '900', letterSpacing: 2 },
  banner: { backgroundColor: C.warn, paddingVertical: 6, alignItems: 'center' },
  bannerText: { color: C.onWarn, fontWeight: '900', letterSpacing: 0.5, fontSize: 8 },
  statusCard: { borderWidth: 2, padding: S.lg, alignItems: 'center', gap: S.sm, backgroundColor: C.surface2 },
  statusText: { color: C.fg, fontWeight: '900', fontSize: 13, letterSpacing: 1, textAlign: 'center', lineHeight: 19 },
  statusMeta: { color: C.info, fontSize: 11 },
  msg: { color: C.brand, fontWeight: '800', fontSize: 12, marginTop: S.md, lineHeight: 17 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginTop: S.md, lineHeight: 17 },
  section: { marginTop: S.xl, marginBottom: S.sm, fontSize: 11, letterSpacing: 2, color: C.fg, fontWeight: '900' },
  intro: { color: C.onS3, fontSize: 12, lineHeight: 18, marginBottom: S.sm },
  chip: { paddingHorizontal: S.md, paddingVertical: 8, borderWidth: 1.5, borderColor: C.borderStrong, minHeight: 36, justifyContent: 'center' },
  chipActive: { backgroundColor: C.error, borderColor: C.error },
  chipText: { fontWeight: '800', color: C.fg, fontSize: 10, letterSpacing: 0.5 },
  chipTextActive: { color: C.onError },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 14, color: C.fg, backgroundColor: C.surface2 },
  addBtn: { width: 50, backgroundColor: C.error, alignItems: 'center', justifyContent: 'center' },
  actionBtn: { flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, paddingVertical: S.lg, minHeight: 56 },
  actionText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  hint: { color: C.info, fontSize: 10, marginTop: 6, letterSpacing: 0.5 },
  humCard: { marginTop: S.lg, borderWidth: 2, borderColor: C.brand, padding: S.lg, backgroundColor: C.surface2, alignItems: 'center' },
  humId: { color: C.brand, fontWeight: '900', fontSize: 20, letterSpacing: 2, fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }) },
  humName: { color: C.fg, fontWeight: '900', fontSize: 16, marginTop: 4 },
  humLine: { color: C.onS3, fontSize: 12, marginTop: 4, textAlign: 'center', lineHeight: 17 },
  qrWrap: { marginTop: S.md, alignItems: 'center' },
  humStd: { color: C.info, fontSize: 9, letterSpacing: 0.5, marginTop: S.md, textAlign: 'center', lineHeight: 14 },
  pdfBtn: { marginTop: S.md, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', borderWidth: 1.5, borderColor: C.borderStrong, paddingVertical: S.md, minHeight: 48, alignSelf: 'stretch' },
  pdfText: { color: C.fg, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
});
