/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// UHP PARTNERS — high-end landing for clinics & insurers: why + how to connect
// to the Universal Health Protocol (UHP/1.0). Live capacity, 4-step onboarding,
// sandbox registration issuing real credentials, security guarantees.
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator, Linking, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { tap } from '@/src/ui/glass';
import { C, S, R, GOLD } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

const VALUE_PROPS = [
  {
    icon: 'medkit-outline', title: 'FOR CLINICS',
    lines: [
      'Instant patient inflow from Arbitrage Brain — index of 10,500+ clinics, 32 countries',
      'Digital referrals and results straight into the patient vault (zero-knowledge)',
      'Auditable channel with HMAC signature — tamper-proof delivery history',
    ],
  },
  {
    icon: 'shield-checkmark-outline', title: 'FOR INSURERS',
    lines: [
      'Real-time vitals streams → predictive risk BEFORE the event',
      'Insurance claims (insurance_claim) with a cryptographic audit trail',
      'Lower costs through Predictive Sentinel prevention and the Bio-Digital Twin',
    ],
  },
  {
    icon: 'flask-outline', title: 'FOR LABS & SENSOR NETWORKS',
    lines: [
      'Fan-out 12 regions × 4096 shards × 32 nodes — 1.02 B concurrent streams',
      'Idempotent delivery · replay protection ±300 s · 240 msgs/min per partner',
      'Kinds: vitals · lab_result · document · insurance_claim · sensor · threat_mesh',
    ],
  },
];

const STEPS = [
  { n: '01', title: 'REGISTRATION', code: 'POST /api/uhp/partners/register', text: 'You receive partner_id, api_key and hmac_secret — shown only once.' },
  { n: '02', title: 'MESSAGE SIGNATURE', code: 'HMAC-SHA256("{ts}.{body}", secret)', text: 'Sign every ingest with a timestamp and the raw request body.' },
  { n: '03', title: 'DATA INGEST', code: 'POST /api/uhp/ingest', text: 'UHP/1.0 envelope with idempotency_key — duplicates are safely dropped.' },
  { n: '04', title: 'MONITORING', code: 'GET /api/uhp/partners/{id}/stats', text: 'Volume, status and health of your channel in real time.' },
];

export default function Partners() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const [cap, setCap] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [creds, setCreds] = useState<any>(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    (async () => { try { setCap(await api('/uhp/capacity')); } catch {} })();
  }, []);

  const sandbox = async () => {
    setBusy(true); setErr('');
    try {
      const res: any = await api('/uhp/partners/register', {
        method: 'POST',
        body: JSON.stringify({
          org_name: `Sandbox Clinic ${Math.random().toString(36).slice(2, 6).toUpperCase()}`,
          org_type: 'clinic', country: 'SK', contact_email: 'sandbox@uhp.dev',
        }),
      });
      setCreds(res);
      const c: any = await api('/uhp/capacity');
      setCap(c);
    } catch (e: any) { setErr(String(e.message || e)); }
    setBusy(false);
  };

  const contact = () => {
    const url = 'mailto:guardian.angel.core@proton.me?subject=UHP%20Partner%20Onboarding';
    Linking.openURL(url).catch(() => {});
  };

  return (
    <SafeAreaView testID="partners-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="pt-back" onPress={() => { tap(); router.back(); }} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={st.headTitle}>{tt('partners.uhp_partners')}</Text>
        <Ionicons name="git-network-outline" size={20} color={C.brand} />
      </View>

      <ScrollView contentContainerStyle={{ paddingBottom: 80 }}>
        {/* HERO */}
        <View style={st.hero}>
          <Text style={st.heroKicker}>{tt('partners.universal_health_protocol_uhp_1_0')}</Text>
          <Text style={st.heroTitle}>{tt('partners.join_the_sovereign')}{'\n'}{tt('partners.health_infrastructure')}</Text>
          <Text style={st.heroSub}>
            {tt('partners.one_gateway_for_clinics_insurers_lab')}
          </Text>
        </View>

        {/* LIVE STATS */}
        <View style={st.statsRow}>
          <View style={st.statBox}>
            <Text style={st.statVal}>{cap ? cap.stream_capacity_human : '—'}</Text>
            <Text style={st.statLbl}>{tt('partners.concurrent_streams')}</Text>
          </View>
          <View style={st.statBox}>
            <Text style={st.statVal}>{cap ? cap.active_partners : '—'}</Text>
            <Text style={st.statLbl}>{tt('partners.active_partners')}</Text>
          </View>
          <View style={st.statBox}>
            <Text style={st.statVal}>{cap ? cap.events_ingested_total : '—'}</Text>
            <Text style={st.statLbl}>{tt('partners.events_ingested')}</Text>
          </View>
        </View>

        {/* VALUE PROPS */}
        {VALUE_PROPS.map(v => (
          <View key={v.title} style={st.valueCard}>
            <View style={st.valueHead}>
              <View style={st.valueIcon}><Ionicons name={v.icon as any} size={20} color={C.brand} /></View>
              <Text style={st.valueTitle}>{tx(v.title)}</Text>
            </View>
            {v.lines.map((l, i) => (
              <View key={i} style={st.valueLine}>
                <Ionicons name="checkmark" size={13} color={C.brand} style={{ marginTop: 2 }} />
                <Text style={st.valueText}>{l}</Text>
              </View>
            ))}
          </View>
        ))}

        {/* HOW TO CONNECT */}
        <Text style={st.section}>{tt('partners.how_to_connect_4_steps')}</Text>
        {STEPS.map(s => (
          <View key={s.n} style={st.stepCard}>
            <Text style={st.stepNum}>{s.n}</Text>
            <View style={{ flex: 1 }}>
              <Text style={st.stepTitle}>{tx(s.title)}</Text>
              <Text style={st.stepCode}>{s.code}</Text>
              <Text style={st.stepText}>{tx(s.text)}</Text>
            </View>
          </View>
        ))}

        {/* SECURITY BAR */}
        <View style={st.secBar}>
          {['HMAC-SHA256', 'REPLAY ±300 s', 'IDEMPOTENCIA', '240/min LIMIT'].map(x => (
            <View key={x} style={st.secPill}><Text style={st.secPillText}>{x}</Text></View>
          ))}
        </View>

        {/* SANDBOX */}
        <Text style={st.section}>{tt('partners.sandbox_try_it_right_now')}</Text>
        <Text style={st.sandboxNote}>{tt('partners.one_tap_issues_real_uhp_credentials')}</Text>
        <Pressable testID="pt-sandbox" onPress={() => { tap('medium'); sandbox(); }} disabled={busy} style={{ marginHorizontal: S.lg, marginTop: S.md }}>
          <LinearGradient colors={GOLD as any} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={st.cta}>
            {busy ? <ActivityIndicator color={C.onInverse} /> : (
              <>
                <Ionicons name="key-outline" size={18} color={C.onInverse} />
                <Text style={st.ctaText}>{tt('partners.generate_sandbox_access')}</Text>
              </>
            )}
          </LinearGradient>
        </Pressable>
        {!!err && <Text style={st.err}>{err}</Text>}
        {creds && (
          <View testID="pt-creds" style={st.credsCard}>
            <Text style={st.credsLbl}>{tt('partners.partner_id')}</Text>
            <Text style={st.credsVal}>{creds.partner_id}</Text>
            <Text style={st.credsLbl}>{tt('partners.api_key')}</Text>
            <Text style={st.credsVal}>{creds.api_key}</Text>
            <Text style={st.credsLbl}>{tt('partners.hmac_secret_shown_only_once')}</Text>
            <Text style={st.credsVal}>{String(creds.hmac_secret).slice(0, 16)}…{String(creds.hmac_secret).slice(-8)}</Text>
            <Text style={st.credsNote}>{tt('partners.protocol_documentation_get_api_uhp_s')}</Text>
          </View>
        )}

        {/* CONTACT CTA */}
        <View style={st.contactCard}>
          <Ionicons name="business" size={30} color={C.brand} />
          <Text style={st.contactTitle}>{tt('partners.production_onboarding_sla')}</Text>
          <Text style={st.contactText}>
            {tt('partners.for_production_onboarding_dedicated')}
          </Text>
          <Pressable testID="pt-contact" onPress={() => { tap('light'); contact(); }} style={st.contactBtn}>
            <Ionicons name="mail-outline" size={16} color={C.brand} />
            <Text style={st.contactBtnText}>guardian.angel.core@proton.me</Text>
          </Pressable>
        </View>

        <Text style={st.footer}>{tt('partners.uhp_1_0_guardian_angel_sovereign_fou')} {Platform.OS === 'web' ? tt('partners.web_preview') : tt('partners.native')}</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  headTitle: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 14 },
  hero: { paddingHorizontal: S.lg, paddingTop: S.md },
  heroKicker: { color: C.brand, fontWeight: '900', fontSize: 10, letterSpacing: 3 },
  heroTitle: { color: C.fg, fontWeight: '900', fontSize: 28, lineHeight: 34, marginTop: S.sm, letterSpacing: 0.3 },
  heroSub: { color: C.info, fontSize: 13, lineHeight: 19, marginTop: S.md },
  statsRow: { flexDirection: 'row', gap: S.sm, paddingHorizontal: S.lg, marginTop: S.xl },
  statBox: { flex: 1, borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.md, backgroundColor: 'rgba(212,175,55,0.06)', padding: S.md, alignItems: 'center', minHeight: 76, justifyContent: 'center' },
  statVal: { color: C.brand, fontWeight: '900', fontSize: 17 },
  statLbl: { color: C.info, fontWeight: '800', fontSize: 8, letterSpacing: 1, marginTop: 4, textAlign: 'center' },
  valueCard: { marginHorizontal: S.lg, marginTop: S.md, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.lg },
  valueHead: { flexDirection: 'row', alignItems: 'center', gap: S.md, marginBottom: S.sm },
  valueIcon: { width: 40, height: 40, borderRadius: R.pill, backgroundColor: 'rgba(212,175,55,0.14)', alignItems: 'center', justifyContent: 'center' },
  valueTitle: { color: C.fg, fontWeight: '900', fontSize: 13, letterSpacing: 1.5 },
  valueLine: { flexDirection: 'row', gap: 8, marginTop: 6, alignItems: 'flex-start' },
  valueText: { flex: 1, color: C.onS3, fontSize: 12, lineHeight: 17 },
  section: { color: C.info, fontWeight: '800', fontSize: 11, letterSpacing: 2, paddingHorizontal: S.lg, marginTop: S.xl },
  stepCard: { flexDirection: 'row', gap: S.md, marginHorizontal: S.lg, marginTop: S.sm, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.md },
  stepNum: { color: C.brand, fontWeight: '900', fontSize: 22, letterSpacing: 1, width: 36 },
  stepTitle: { color: C.fg, fontWeight: '900', fontSize: 12, letterSpacing: 1.5 },
  stepCode: { color: C.brand, fontSize: 11, marginTop: 3, fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }) },
  stepText: { color: C.info, fontSize: 11, marginTop: 3, lineHeight: 15 },
  secBar: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, paddingHorizontal: S.lg, marginTop: S.lg, justifyContent: 'center' },
  secPill: { borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.pill, paddingHorizontal: 12, paddingVertical: 6, backgroundColor: 'rgba(212,175,55,0.05)' },
  secPillText: { color: C.brand, fontWeight: '900', fontSize: 9, letterSpacing: 1 },
  sandboxNote: { color: C.info, fontSize: 11.5, lineHeight: 16, paddingHorizontal: S.lg, marginTop: S.sm },
  cta: { flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', minHeight: 54, borderRadius: R.pill },
  ctaText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
  err: { color: C.error, fontSize: 12, paddingHorizontal: S.lg, marginTop: S.sm },
  credsCard: { marginHorizontal: S.lg, marginTop: S.md, borderWidth: 1.5, borderColor: C.brand, borderRadius: R.md, padding: S.lg, backgroundColor: C.surface2 },
  credsLbl: { color: C.brand, fontWeight: '900', fontSize: 9, letterSpacing: 2, marginTop: 6 },
  credsVal: { color: C.fg, fontSize: 12, marginTop: 2, fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }) },
  credsNote: { color: C.info, fontSize: 10, marginTop: S.sm },
  contactCard: { marginHorizontal: S.lg, marginTop: S.xl, borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.lg, padding: S.xl, alignItems: 'center', gap: S.sm, backgroundColor: 'rgba(212,175,55,0.05)' },
  contactTitle: { color: C.fg, fontWeight: '900', fontSize: 15, letterSpacing: 0.5 },
  contactText: { color: C.info, fontSize: 12, lineHeight: 17, textAlign: 'center' },
  contactBtn: { flexDirection: 'row', gap: 8, alignItems: 'center', borderWidth: 1.5, borderColor: C.brand, borderRadius: R.pill, paddingHorizontal: S.lg, minHeight: 48, marginTop: S.sm },
  contactBtnText: { color: C.brand, fontWeight: '900', fontSize: 12 },
  footer: { textAlign: 'center', color: C.info, fontSize: 9, letterSpacing: 1.5, marginTop: S.xl, paddingHorizontal: S.lg },
});
