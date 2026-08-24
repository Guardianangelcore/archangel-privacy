/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, TextInput, ScrollView, Switch, ActivityIndicator, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { sharePdf } from '@/src/pdf';
import { useAuth } from '@/src/auth';
import JarvisAdvice from '@/src/JarvisAdvice';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';

const RELATIONSHIPS = ['partner', 'manžel/ka', 'rodina', 'priateľ/ka'];
const SCOPES = [
  { key: 'full', label: 'PLNÉ' },
  { key: 'info_access', label: 'INFO PRÍSTUP' },
  { key: 'decisions', label: 'ROZHODNUTIA' },
];

export default function HealthcareProxy() {
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const router = useRouter();
  const [f, setF] = useState<any>({ proxy_full_name: '', proxy_relationship: 'partner', proxy_phone: '', proxy_email: '', scope: 'full', effective_immediately: true, alternate_name: '', notes: '' });
  const [doc, setDoc] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const res: any = await api('/proxy-directive');
      if (res?.proxy_full_name) { setF({ ...f, ...res }); setDoc(res); }
    } catch (e) { console.log(e); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => { load(); }, [load]);

  const generate = async () => {
    if (!f.proxy_full_name) return;
    setBusy(true);
    try {
      const res: any = await api('/proxy-directive', {
        method: 'PUT',
        body: JSON.stringify({
          proxy_full_name: f.proxy_full_name, proxy_relationship: f.proxy_relationship,
          proxy_phone: f.proxy_phone, proxy_email: f.proxy_email, scope: f.scope,
          effective_immediately: !!f.effective_immediately, alternate_name: f.alternate_name,
          notes: f.notes, language: lang,
        }),
      });
      setDoc(res);
    } catch (e) { console.log(e); } finally { setBusy(false); }
  };

  return (
    <SafeAreaView testID="proxy-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="hp-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={styles.title}>{t('healthcare_proxy', lang).toUpperCase()}</Text>
        <View style={{ width: 26 }} />
      </View>
      <View style={styles.sub}><Text style={styles.subText}>POWER OF ATTORNEY · PRÁVNE UZNANIE PARTNERA · DID-ANCHORED</Text></View>

      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
        <Text style={styles.lbl}>MENO SPLNOMOCNENCA (napr. Tomáš)</Text>
        <TextInput testID="hp-name" value={f.proxy_full_name} onChangeText={(v: string) => setF({ ...f, proxy_full_name: v })} style={styles.input} placeholder="Tomáš Novák" placeholderTextColor="#999" />

        <Text style={styles.lbl}>VZŤAH</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: S.sm }}>
          {RELATIONSHIPS.map(r => (
            <Pressable testID={`hp-rel-${r}`} key={r} onPress={() => setF({ ...f, proxy_relationship: r })} style={[styles.chip, f.proxy_relationship === r && styles.chipActive]}>
              <Text style={[styles.chipText, f.proxy_relationship === r && styles.chipTextActive]}>{r.toUpperCase()}</Text>
            </Pressable>
          ))}
        </View>

        <Text style={styles.lbl}>TELEFÓN</Text>
        <TextInput testID="hp-phone" value={f.proxy_phone} onChangeText={(v: string) => setF({ ...f, proxy_phone: v })} keyboardType="phone-pad" style={styles.input} placeholder="+421…" placeholderTextColor="#999" />
        <Text style={styles.lbl}>E-MAIL</Text>
        <TextInput testID="hp-email" value={f.proxy_email} onChangeText={(v: string) => setF({ ...f, proxy_email: v })} keyboardType="email-address" style={styles.input} placeholder="tomas@…" placeholderTextColor="#999" />

        <Text style={styles.lbl}>ROZSAH OPRÁVNENIA</Text>
        <View style={{ flexDirection: 'row', gap: S.sm }}>
          {SCOPES.map(s => (
            <Pressable testID={`hp-scope-${s.key}`} key={s.key} onPress={() => setF({ ...f, scope: s.key })} style={[styles.chip, { flex: 1, alignItems: 'center' }, f.scope === s.key && styles.chipActive]}>
              <Text style={[styles.chipText, f.scope === s.key && styles.chipTextActive]}>{s.label}</Text>
            </Pressable>
          ))}
        </View>

        <View style={styles.switchRow}>
          <Text style={styles.switchLbl}>ÚČINNÉ OKAMŽITE</Text>
          <Switch testID="hp-effective" value={!!f.effective_immediately} onValueChange={v => setF({ ...f, effective_immediately: v })} trackColor={{ true: C.brand, false: C.surface3 }} />
        </View>

        <Text style={styles.lbl}>NÁHRADNÝ ZÁSTUPCA (nepovinné)</Text>
        <TextInput testID="hp-alt" value={f.alternate_name} onChangeText={(v: string) => setF({ ...f, alternate_name: v })} style={styles.input} placeholderTextColor="#999" />
        <Text style={styles.lbl}>POZNÁMKY</Text>
        <TextInput testID="hp-notes" value={f.notes} onChangeText={(v: string) => setF({ ...f, notes: v })} multiline style={[styles.input, { minHeight: 60 }]} placeholderTextColor="#999" />

        <Pressable testID="hp-generate" onPress={generate} disabled={busy || !f.proxy_full_name} style={[styles.genBtn, !f.proxy_full_name && { opacity: 0.4 }]}>
          {busy ? <ActivityIndicator color={C.onInverse} /> : <>
            <Ionicons name="document-text-outline" size={18} color={C.onInverse} />
            <Text style={styles.genBtnText}>{t('generate_document', lang).toUpperCase()}</Text>
          </>}
        </Pressable>

        <JarvisAdvice module="healthcare_proxy" lang={lang} buildContext={() => `User is creating a healthcare proxy for ${f.proxy_full_name || 'their partner'} (${f.proxy_relationship}) with scope ${f.scope}. Explain their rights, how to make it legally binding in Slovakia, and how it protects same-sex partners from being denied access to medical information.`} />

        {doc?.document_text && (
          <View testID="hp-document" style={styles.docBox}>
            <View style={styles.docHead}>
              <Ionicons name="shield-checkmark" size={16} color={C.brand} />
              <Text style={styles.docHeadText}>DOKUMENT · SHA-256 UKOTVENÝ</Text>
            </View>
            <Text style={styles.docText}>{doc.document_text}</Text>
            <Pressable testID="hp-pdf" onPress={() => sharePdf('/legal/proxy.pdf', 'guardian_healthcare_proxy.pdf')} style={styles.pdfBtn}>
              <Ionicons name="share-outline" size={18} color={C.onInverse} />
              <Text style={styles.pdfBtnText}>{t('share_pdf', lang).toUpperCase()} — NOTÁR / NEMOCNICA</Text>
            </Pressable>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  sub: { paddingHorizontal: S.lg, paddingVertical: 6, backgroundColor: C.brandTer },
  subText: { color: C.brand, fontSize: 10, fontWeight: '900', letterSpacing: 1 },
  lbl: { fontSize: 10, letterSpacing: 2, color: C.onS3, fontWeight: '800', marginTop: S.md, marginBottom: 6 },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 15, color: C.fg },
  chip: { paddingHorizontal: S.md, paddingVertical: 10, borderWidth: 1.5, borderColor: C.borderStrong },
  chipActive: { backgroundColor: C.inverse },
  chipText: { fontWeight: '800', color: C.fg, fontSize: 11, letterSpacing: 1 },
  chipTextActive: { color: C.onInverse },
  switchRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: S.lg, borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md },
  switchLbl: { fontWeight: '900', letterSpacing: 1, fontSize: 12, color: C.fg },
  genBtn: { marginTop: S.lg, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.inverse, paddingVertical: S.lg },
  genBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 13 },
  docBox: { marginTop: S.lg, borderWidth: 2, borderColor: C.brand },
  docHead: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: S.md, backgroundColor: C.brandTer },
  docHeadText: { color: C.brand, fontWeight: '900', letterSpacing: 1, fontSize: 11 },
  docText: { padding: S.md, fontSize: 12, lineHeight: 18, color: C.fg, fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }) },
  pdfBtn: { flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.inverse, paddingVertical: S.md, margin: S.md },
  pdfBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
});
