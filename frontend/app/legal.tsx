/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, TextInput, ScrollView, Switch, ActivityIndicator, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import * as Location from 'expo-location';
import { api } from '@/src/api';
import { sharePdf } from '@/src/pdf';
import { WheelField } from '@/src/ui/fields';
import { useAuth } from '@/src/auth';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';
import { useI18n } from '@/src/i18n-context';

const COUNTRIES = ['SK', 'CZ', 'DE', 'AT', 'GB', 'US', 'OTHER'];
const TOS_VERSION = '2026-06.1';

export default function Legal() {
  const { t: tt, tx } = useI18n();
  const { user, setUser } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'en';
  const router = useRouter();
  const [country, setCountry] = useState('SK');
  const [region, setRegion] = useState<any>(null);
  const [tosText, setTosText] = useState('');
  const [showTos, setShowTos] = useState(false);
  const [aml, setAml] = useState<any>(null);
  const [kycForm, setKycForm] = useState({ full_name: '', birth_year: '', declaration: false });
  const [kycBusy, setKycBusy] = useState(false);
  const [tf, setTf] = useState({ full_name: '', wishes: '', executor_name: '', witness1: '', witness2: '' });
  const [testDoc, setTestDoc] = useState<any>(null);
  const [testBusy, setTestBusy] = useState(false);
  const [err, setErr] = useState('');

  const cc = country === 'OTHER' ? 'XX' : country;

  const loadRegion = useCallback(async (c: string) => {
    try { setRegion(await api(`/legal/region?country=${c}&language=${lang}`)); } catch (e) { console.log(e); }
  }, [lang]);

  useEffect(() => { loadRegion(cc); }, [cc, loadRegion]);
  useEffect(() => {
    (async () => {
      try {
        const [a, td] = await Promise.all([api('/aml/status'), api('/legal/testament')]);
        setAml(a);
        if ((td as any)?.document_text) setTestDoc(td);
      } catch (e) { console.log(e); }
    })();
  }, []);

  const detectGps = async () => {
    if (Platform.OS === 'web') return;
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') return;
      const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Low });
      const geo = await Location.reverseGeocodeAsync({ latitude: pos.coords.latitude, longitude: pos.coords.longitude });
      const iso = geo?.[0]?.isoCountryCode;
      if (iso) setCountry(COUNTRIES.includes(iso) ? iso : 'OTHER');
    } catch (e) { console.log('gps err', e); }
  };

  const openTos = async () => {
    if (!tosText) {
      try {
        const res: any = await api(`/legal/tos?country=${cc}&language=${lang}`);
        setTosText(res.text);
      } catch (e) { console.log(e); }
    }
    setShowTos(v => !v);
  };

  const acceptTos = async () => {
    const u: any = await api('/legal/accept', { method: 'POST', body: JSON.stringify({ country: cc, language: lang }) });
    setUser(u);
  };

  const submitKyc = async () => {
    if (!kycForm.full_name || !kycForm.birth_year || !kycForm.declaration) return;
    setKycBusy(true); setErr('');
    try {
      await api('/aml/kyc', { method: 'POST', body: JSON.stringify({ full_name: kycForm.full_name, birth_year: parseInt(kycForm.birth_year, 10), country: cc, declaration: true }) });
      setAml(await api('/aml/status'));
      const me: any = await api('/auth/me');
      setUser(me.user);
    } catch (e: any) { setErr(String(e.message || e)); } finally { setKycBusy(false); }
  };

  const generateTestament = async () => {
    if (!tf.full_name || !tf.wishes) return;
    setTestBusy(true);
    try {
      const res: any = await api('/legal/testament', { method: 'POST', body: JSON.stringify({ ...tf, country: cc, language: lang }) });
      setTestDoc(res);
    } catch (e) { console.log(e); } finally { setTestBusy(false); }
  };

  const tosOk = (user as any)?.tos_accepted_version === TOS_VERSION;
  const isCommonLaw = region?.testament_format && region.testament_format !== 'civil_law_holograph';

  return (
    <SafeAreaView testID="legal-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="lg-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={styles.title}>{t('legal_hub', lang).toUpperCase()}</Text>
        <View style={{ width: 26 }} />
      </View>
      <View style={styles.sub}><Text style={styles.subText}>{tt('legal.eu_ai_act_art_50_gdpr_uk_dpa_duaa_fd')}</Text></View>

      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
        {/* Jurisdiction */}
        <Text style={styles.section}>{t('jurisdiction', lang).toUpperCase()} {region ? `· ${region.jurisdiction}` : ''}</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: S.sm }}>
          {COUNTRIES.map(c => (
            <Pressable testID={`lg-cc-${c}`} key={c} onPress={() => setCountry(c)} style={[styles.chip, country === c && styles.chipActive]}>
              <Text style={[styles.chipText, country === c && styles.chipTextActive]}>{c}</Text>
            </Pressable>
          ))}
          {Platform.OS !== 'web' && (
            <Pressable testID="lg-gps" onPress={detectGps} style={[styles.chip, { flexDirection: 'row', gap: 4, alignItems: 'center' }]}>
              <Ionicons name="locate-outline" size={14} color={C.fg} />
              <Text style={styles.chipText}>GPS</Text>
            </Pressable>
          )}
        </View>

        {region?.disclaimers?.map((d: any) => (
          <View key={d.id} testID={`disc-${d.id}`} style={styles.discCard}>
            <Text style={styles.discTitle}>{d.title.toUpperCase()}</Text>
            <Text style={styles.discText}>{tx(d.text)}</Text>
          </View>
        ))}

        {/* TOS */}
        <Text style={styles.section}>{t('tos_title', lang).toUpperCase()} · v{TOS_VERSION}</Text>
        <View style={[styles.statusRow, { borderColor: tosOk ? C.brand : C.error }]}>
          <Ionicons name={tosOk ? 'checkmark-circle' : 'alert-circle-outline'} size={20} color={tosOk ? C.brand : C.error} />
          <Text style={[styles.statusText, { color: tosOk ? C.brand : C.error }]}>
            {tosOk ? t('tos_accepted', lang).toUpperCase() : tt('legal.awaiting_acceptance')}
          </Text>
        </View>
        <Pressable testID="lg-tos-view" onPress={openTos} style={styles.secBtn}>
          <Ionicons name={showTos ? 'chevron-up' : 'document-text-outline'} size={16} color={C.fg} />
          <Text style={styles.secBtnText}>{showTos ? tt('legal.hide') : tt('legal.show_full_terms')}</Text>
        </Pressable>
        <Pressable testID="lg-tos-pdf" onPress={() => sharePdf(`/legal/tos.pdf?language=${lang}`, 'guardian_tos.pdf')} style={[styles.secBtn, { marginTop: S.sm }]}>
          <Ionicons name="share-outline" size={16} color={C.fg} />
          <Text style={styles.secBtnText}>{t('share_pdf', lang).toUpperCase()}</Text>
        </Pressable>
        {showTos && tosText ? <Text style={styles.tosText}>{tosText}</Text> : null}
        {!tosOk && (
          <Pressable testID="lg-tos-accept" onPress={acceptTos} style={styles.priBtn}>
            <Text style={styles.priBtnText}>{t('tos_accept', lang).toUpperCase()}</Text>
          </Pressable>
        )}

        {/* KYC / AML */}
        <Text style={styles.section}>{t('kyc_title', lang).toUpperCase()}</Text>
        {err ? <Text style={styles.err}>{err}</Text> : null}
        {aml?.kyc_verified ? (
          <View style={[styles.statusRow, { borderColor: C.brand }]}>
            <Ionicons name="shield-checkmark" size={20} color={C.brand} />
            <View style={{ flex: 1 }}>
              <Text style={[styles.statusText, { color: C.brand }]}>{t('kyc_verified', lang).toUpperCase()} {tt('legal.limit')}{aml.daily_limit?.toFixed(0)}/DAY</Text>
              <Text style={styles.attText}>{tt('legal.did_attestation')} {String(aml.attestation).slice(0, 24)}…</Text>
            </View>
          </View>
        ) : (
          <View>
            <Text style={styles.hint}>{tt('legal.without_kyc_limit')}{aml?.daily_limit?.toFixed(0) ?? 150}{tt('legal.day_in_solidarity_hub_campaigns_requ')}</Text>
            <TextInput testID="kyc-name" placeholder={tt('legal.full_name')} value={kycForm.full_name} onChangeText={v => setKycForm({ ...kycForm, full_name: v })} style={styles.input} placeholderTextColor="#999" />
            <WheelField testID="kyc-year" title={tt('legal.birth_year')} min={1920} max={2012} value={kycForm.birth_year} onChange={v => setKycForm({ ...kycForm, birth_year: v })} placeholder={tt('legal.birth_year_5ci2')} style={styles.input} />
            <View style={styles.switchRow}>
              <Text style={styles.switchLbl}>{tt('legal.i_declare_i_am_not_on_a_sanctions_li')}</Text>
              <Switch testID="kyc-declaration" value={kycForm.declaration} onValueChange={v => setKycForm({ ...kycForm, declaration: v })} trackColor={{ true: C.brand, false: C.surface3 }} />
            </View>
            <Pressable testID="kyc-submit" onPress={submitKyc} disabled={kycBusy || !kycForm.declaration} style={[styles.priBtn, !kycForm.declaration && { opacity: 0.4 }]}>
              {kycBusy ? <ActivityIndicator color={C.onInverse} /> : <Text style={styles.priBtnText}>{tt('legal.verify_did_attestation')}</Text>}
            </Pressable>
          </View>
        )}
        {aml ? <Text style={styles.hint}>{tt('legal.donated_today')}{aml.donated_today?.toFixed(0)} / €{aml.daily_limit?.toFixed(0)} {tt('legal.transactions')} {aml.tx_today}/{aml.max_tx_per_day} {tt('legal.aml_records')} {aml.ledger_entries}</Text> : null}

        {/* Testament */}
        <Text style={styles.section}>{t('testament', lang).toUpperCase()} · {region?.testament_format === 'common_law_uk' ? tt('legal.uk_wills_act_1837') : region?.testament_format === 'common_law' ? tt('legal.common_law') : tt('legal.holograph_476_civil_code')}</Text>
        <TextInput testID="tw-name" placeholder={tt('legal.testator_full_name')} value={tf.full_name} onChangeText={v => setTf({ ...tf, full_name: v })} style={styles.input} placeholderTextColor="#999" />
        <TextInput testID="tw-wishes" placeholder={tt('legal.my_last_will_who_gets_what')} value={tf.wishes} onChangeText={v => setTf({ ...tf, wishes: v })} multiline style={[styles.input, { minHeight: 90 }]} placeholderTextColor="#999" />
        <TextInput testID="tw-executor" placeholder={tt('legal.will_executor_optional')} value={tf.executor_name} onChangeText={v => setTf({ ...tf, executor_name: v })} style={styles.input} placeholderTextColor="#999" />
        {isCommonLaw && (
          <View style={{ flexDirection: 'row', gap: S.sm }}>
            <TextInput testID="tw-w1" placeholder={tt('legal.witness_1')} value={tf.witness1} onChangeText={v => setTf({ ...tf, witness1: v })} style={[styles.input, { flex: 1 }]} placeholderTextColor="#999" />
            <TextInput testID="tw-w2" placeholder={tt('legal.witness_2')} value={tf.witness2} onChangeText={v => setTf({ ...tf, witness2: v })} style={[styles.input, { flex: 1 }]} placeholderTextColor="#999" />
          </View>
        )}
        <Pressable testID="tw-generate" onPress={generateTestament} disabled={testBusy || !tf.full_name || !tf.wishes} style={[styles.priBtn, (!tf.full_name || !tf.wishes) && { opacity: 0.4 }]}>
          {testBusy ? <ActivityIndicator color={C.onInverse} /> : <Text style={styles.priBtnText}>{t('generate_document', lang).toUpperCase()}</Text>}
        </Pressable>
        {testDoc?.document_text ? (
          <View testID="tw-document" style={styles.docBox}>
            <View style={styles.docHead}>
              <Ionicons name="shield-checkmark" size={16} color={C.brand} />
              <Text style={styles.docHeadText}>{String(testDoc.format).toUpperCase()} {tt('legal.sha_256_anchored')}</Text>
            </View>
            <Text style={styles.docText}>{testDoc.document_text}</Text>
            <Pressable testID="tw-pdf" onPress={() => sharePdf('/legal/testament.pdf', 'guardian_testament.pdf')} style={styles.pdfBtn}>
              <Ionicons name="share-outline" size={18} color={C.onInverse} />
              <Text style={styles.pdfBtnText}>{t('share_pdf', lang).toUpperCase()} {tt('legal.notary_family')}</Text>
            </Pressable>
          </View>
        ) : null}

        <Pressable testID="lg-dignity-link" onPress={() => router.push('/dignity')} style={[styles.secBtn, { marginTop: S.lg }]}>
          <Ionicons name="rose-outline" size={16} color={C.fg} />
          <Text style={styles.secBtnText}>{tt('legal.final_dignity_funeral_fund_last_wish')}</Text>
        </Pressable>

        <Text style={styles.footer}>⚠ {t('ai_disclosure', lang)}</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  sub: { paddingHorizontal: S.lg, paddingVertical: 6, backgroundColor: C.brandTer },
  subText: { color: C.brand, fontSize: 9, fontWeight: '900', letterSpacing: 0.5 },
  section: { marginTop: S.xl, marginBottom: S.md, fontSize: 11, letterSpacing: 2, color: C.fg, fontWeight: '900' },
  chip: { paddingHorizontal: S.md, paddingVertical: 10, borderWidth: 1.5, borderColor: C.borderStrong },
  chipActive: { backgroundColor: C.inverse },
  chipText: { fontWeight: '800', color: C.fg, fontSize: 12, letterSpacing: 1 },
  chipTextActive: { color: C.onInverse },
  discCard: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginTop: S.md },
  discTitle: { fontWeight: '900', fontSize: 11, letterSpacing: 1, color: C.brand, marginBottom: 4 },
  discText: { color: C.fg, fontSize: 13, lineHeight: 19 },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, borderWidth: 2, padding: S.md, marginBottom: S.sm },
  statusText: { fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  attText: { color: C.onS3, fontSize: 10, marginTop: 2, letterSpacing: 0.5 },
  secBtn: { flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: C.borderStrong, paddingVertical: S.md },
  secBtnText: { fontWeight: '900', letterSpacing: 1, fontSize: 12, color: C.fg },
  tosText: { marginTop: S.sm, borderWidth: 1.5, borderColor: C.border, padding: S.md, fontSize: 11, lineHeight: 17, color: C.fg, fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }) },
  priBtn: { marginTop: S.sm, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: C.inverse, paddingVertical: S.lg },
  priBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 13 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginBottom: S.sm },
  hint: { color: C.onS3, fontSize: 11, lineHeight: 16, marginBottom: S.sm },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 15, color: C.fg, marginBottom: S.sm },
  switchRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginBottom: S.sm },
  switchLbl: { flex: 1, fontWeight: '800', fontSize: 10, letterSpacing: 0.5, color: C.fg },
  docBox: { marginTop: S.md, borderWidth: 2, borderColor: C.brand },
  docHead: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: S.md, backgroundColor: C.brandTer },
  docHeadText: { color: C.brand, fontWeight: '900', letterSpacing: 1, fontSize: 11 },
  docText: { padding: S.md, fontSize: 12, lineHeight: 18, color: C.fg, fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }) },
  pdfBtn: { flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.inverse, paddingVertical: S.md, margin: S.md },
  pdfBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  footer: { marginTop: S.xl, fontSize: 9, letterSpacing: 1, color: C.onS3, fontWeight: '800', textAlign: 'center' },
});
