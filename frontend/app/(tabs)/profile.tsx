/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, TextInput, ScrollView, Switch, Platform, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as Location from 'expo-location';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { ContactSheet } from '@/src/ui/ContactSheet';
import { C, S } from '@/src/theme';
import { t, LANG_NAMES, Lang } from '@/src/i18n';
import { WATERMARK } from '@/src/watermark';

export default function Profile() {
  const { user, signOut, setUser } = useAuth();
  const router = useRouter();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const [profile, setProfile] = useState<any>({});
  const [saving, setSaving] = useState(false);
  const [ecPick, setEcPick] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [admin, setAdmin] = useState<any>(null);
  const [demoBusy, setDemoBusy] = useState(false);
  const [demoMsg, setDemoMsg] = useState('');
  const [geo, setGeo] = useState<any>(null);
  const [geoMsg, setGeoMsg] = useState('');

  const toggleTravel = async (v: boolean) => {
    setGeoMsg('');
    try {
      if (v && Platform.OS !== 'web') {
        const p = await Location.getForegroundPermissionsAsync();
        if (!p.granted) {
          if (!p.canAskAgain) {
            setGeoMsg('Poloha je zablokovaná — povoľte ju v Nastaveniach telefónu.');
            return;
          }
          const r = await Location.requestForegroundPermissionsAsync();
          if (!r.granted) {
            setGeoMsg(r.canAskAgain ? 'Bez polohy sa mesto neprispôsobí automaticky.' : 'Poloha je zablokovaná — povoľte ju v Nastaveniach telefónu.');
            return;
          }
        }
      }
      const res: any = await api('/geo/travel-mode', { method: 'PUT', body: JSON.stringify({ enabled: v }) });
      setGeo(res.geo);
      if (v && Platform.OS !== 'web') {
        try {
          const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
          const loc: any = await api('/geo/locate', { method: 'POST', body: JSON.stringify({ lat: pos.coords.latitude, lng: pos.coords.longitude }) });
          setGeo(loc.geo);
          if (loc.language_switched) setGeoMsg(`Jazyk prepnutý podľa polohy: ${loc.geo.city} (${loc.language.toUpperCase()})`);
          else setGeoMsg(`Poloha: ${loc.geo.city} · ${loc.geo.country}`);
        } catch {}
      }
      const me: any = await api('/auth/me');
      if (me?.user) setUser(me.user);
    } catch (e: any) { setGeoMsg(String(e.message || e)); }
  };

  const toggleDemo = async (v: boolean) => {
    setDemoBusy(true); setDemoMsg('');
    try {
      const r: any = await api('/demo/toggle', { method: 'POST', body: JSON.stringify({ enabled: v }) });
      setAdmin({ ...admin, demo_mode: r.demo_mode });
      setDemoMsg(v ? 'DEMO MODE AKTÍVNY — dashboard naplnený ukážkovými dátami (lov termínu, 150 € refundácia, rodinný pulz).' : 'Demo dáta odstránené — čistý produkčný stav.');
    } catch (e: any) { setDemoMsg(String(e.message || e)); }
    finally { setDemoBusy(false); }
  };

  const deleteAccount = async () => {
    try { await api('/auth/account', { method: 'DELETE' }); } catch (e) { console.log(e); }
    await signOut();
  };

  const load = useCallback(async () => {
    try { setProfile(await api('/emergency-profile')); } catch (e) { console.log(e); }
    try { setAdmin(await api('/demo/status')); } catch { setAdmin(null); }
    try { const g: any = await api('/geo/context'); setGeo(g.geo); } catch {}
  }, []);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setSaving(true);
    try {
      const res = await api('/emergency-profile', { method: 'PUT', body: JSON.stringify(profile) });
      setProfile(res);
    } finally { setSaving(false); }
  };

  const setLang = async (l: Lang) => {
    const u: any = await api('/me/prefs', { method: 'PATCH', body: JSON.stringify({ language: l }) });
    setUser(u);
  };

  const setPref = async (patch: Record<string, any>) => {
    const u: any = await api('/me/prefs', { method: 'PATCH', body: JSON.stringify(patch) });
    setUser(u);
  };

  return (
    <SafeAreaView testID="profile-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>{t('profile', lang).toUpperCase()}</Text>
        <Pressable testID="logout-btn" onPress={signOut} hitSlop={10}>
          <Ionicons name="log-out-outline" size={22} color={C.onInverse} />
        </Pressable>
      </View>

      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 140 }}>
        <View style={styles.identityCard}>
          <Text style={styles.identityName}>{(user?.name || user?.email || '').toUpperCase()}</Text>
          <Text style={styles.identityEmail}>{user?.email}</Text>
          <Text style={styles.identityLbl}>DECENTRALIZED IDENTIFIER</Text>
          <Text style={styles.identityDid}>{user?.did}</Text>
        </View>

        <Text style={styles.section}>LANGUAGE</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: S.sm }}>
          {(Object.keys(LANG_NAMES) as Lang[]).map(l => (
            <Pressable testID={`prof-lang-${l}`} key={l} onPress={() => setLang(l)} style={[styles.chip, lang === l && styles.chipActive]}>
              <Text style={[styles.chipText, lang === l && styles.chipTextActive]}>{LANG_NAMES[l]}</Text>
            </Pressable>
          ))}
        </View>

        <Text style={styles.section}>{t('guardian_monitoring', lang).toUpperCase()}</Text>
        <View style={styles.guardRow}>
          <Ionicons name="body-outline" size={22} color={C.fg} />
          <View style={{ flex: 1 }}>
            <Text style={styles.guardTitle}>{t('fall_guard', lang).toUpperCase()}</Text>
            <Text style={styles.guardSub}>Akcelerometer · auto Fall-Verify</Text>
          </View>
          <Switch testID="prof-fall-guard" value={!!(user as any)?.fall_guard} onValueChange={v => setPref({ fall_guard: v })} trackColor={{ true: C.brand, false: C.surface3 }} />
        </View>
        <View style={styles.guardRow}>
          <Ionicons name="time-outline" size={22} color={C.fg} />
          <View style={{ flex: 1 }}>
            <Text style={styles.guardTitle}>{t('inactivity_guard', lang).toUpperCase()}</Text>
            <Text style={styles.guardSub}>08:00–21:00 · alarm rodine</Text>
          </View>
          <Switch testID="prof-inactivity-guard" value={!!(user as any)?.inactivity_guard} onValueChange={v => setPref({ inactivity_guard: v })} trackColor={{ true: C.brand, false: C.surface3 }} />
        </View>
        <View style={styles.guardRow}>
          <Ionicons name="heart-half-outline" size={22} color={C.fg} />
          <View style={{ flex: 1 }}>
            <Text style={styles.guardTitle}>GUARDIAN PULSE CHECK</Text>
            <Text style={styles.guardSub}>Tichý ping od rodiny · prísne opt-in, kedykoľvek vypnete</Text>
          </View>
          <Switch testID="prof-pulse-optin" value={!!(user as any)?.pulse_check_optin} onValueChange={v => setPref({ pulse_check_optin: v })} trackColor={{ true: C.brand, false: C.surface3 }} />
        </View>
        <View style={styles.guardRow}>
          <Ionicons name="airplane-outline" size={22} color={C.fg} />
          <View style={{ flex: 1 }}>
            <Text style={styles.guardTitle}>CESTOVNÝ REŽIM (GEO)</Text>
            <Text style={styles.guardSub}>{geo ? `📍 ${geo.city} · ${geo.country}` : '📍 Praha · CZ'} — automatické mesto, jazyk a predpisy podľa GPS</Text>
          </View>
          <Switch testID="prof-travel-mode" value={!!(user as any)?.travel_mode} onValueChange={toggleTravel} trackColor={{ true: C.brand, false: C.surface3 }} />
        </View>
        {!!geoMsg && <Text style={styles.geoMsg}>{geoMsg}</Text>}
        {!!(user as any)?.inactivity_guard && (
          <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.sm }}>
            {[4, 6, 8, 12].map(h => {
              const active = ((user as any)?.inactivity_hours || 6) === h;
              return (
                <Pressable testID={`inactivity-h-${h}`} key={h} onPress={() => setPref({ inactivity_hours: h })} style={[styles.chip, active && styles.chipActive]}>
                  <Text style={[styles.chipText, active && styles.chipTextActive]}>{h} h</Text>
                </Pressable>
              );
            })}
          </View>
        )}

        <Text style={styles.section}>{t('donor_card', lang).toUpperCase()} + EMERGENCY PROFILE</Text>
        <Text style={styles.lbl}>FULL NAME</Text>
        <TextInput testID="prof-name" value={profile.full_name || ''} onChangeText={v => setProfile({ ...profile, full_name: v })} style={styles.input} placeholder="Meno Priezvisko" placeholderTextColor="#999" />

        <Text style={styles.lbl}>{t('blood_type', lang).toUpperCase()}</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: S.sm }}>
          {['A+','A-','B+','B-','AB+','AB-','O+','O-'].map(b => (
            <Pressable testID={`blood-${b}`} key={b} onPress={() => setProfile({ ...profile, blood_type: b })} style={[styles.chip, profile.blood_type === b && styles.chipActive]}>
              <Text style={[styles.chipText, profile.blood_type === b && styles.chipTextActive]}>{b}</Text>
            </Pressable>
          ))}
        </View>

        <Text style={styles.lbl}>{t('allergies', lang).toUpperCase()}</Text>
        <TextInput testID="prof-allergies" value={profile.allergies || ''} onChangeText={v => setProfile({ ...profile, allergies: v })} style={[styles.input, { minHeight: 60 }]} multiline placeholder="penicilín, latex…" placeholderTextColor="#999" />

        <Text style={styles.lbl}>MEDICATIONS</Text>
        <TextInput testID="prof-meds" value={profile.medications || ''} onChangeText={v => setProfile({ ...profile, medications: v })} style={[styles.input, { minHeight: 60 }]} multiline placeholderTextColor="#999" />

        <Text style={styles.lbl}>CONDITIONS</Text>
        <TextInput testID="prof-conditions" value={profile.conditions || ''} onChangeText={v => setProfile({ ...profile, conditions: v })} style={[styles.input, { minHeight: 60 }]} multiline placeholderTextColor="#999" />

        <Text style={styles.lbl}>{t('emergency_contact', lang).toUpperCase()}</Text>
        <TextInput testID="prof-ec-name" value={profile.emergency_contact_name || ''} onChangeText={v => setProfile({ ...profile, emergency_contact_name: v })} style={styles.input} placeholder="Meno" placeholderTextColor="#999" />
        <TextInput testID="prof-ec-phone" value={profile.emergency_contact_phone || ''} onChangeText={v => setProfile({ ...profile, emergency_contact_phone: v })} style={styles.input} placeholder="+421…" keyboardType="phone-pad" placeholderTextColor="#999" />
        <Pressable testID="prof-ec-pick" onPress={() => setEcPick(true)} style={styles.pickBtn}>
          <Ionicons name="people-outline" size={16} color={C.brand} />
          <Text style={styles.pickBtnText}>{t('pick_from_contacts', lang)}</Text>
        </Pressable>
        <ContactSheet visible={ecPick} onClose={() => setEcPick(false)}
          onPick={c => setProfile((prev: any) => ({ ...prev, emergency_contact_name: c.name || prev.emergency_contact_name, emergency_contact_phone: c.phone || prev.emergency_contact_phone }))} />

        <View style={styles.donorRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.donorTitle}>ORGAN DONOR</Text>
            <Text style={styles.donorSub}>Blockchain-anchored consent</Text>
          </View>
          <Switch testID="prof-donor" value={!!profile.is_donor} onValueChange={v => setProfile({ ...profile, is_donor: v })} trackColor={{ true: C.brand, false: C.surface3 }} />
        </View>
        {profile.is_donor && (
          <TextInput testID="prof-donor-organs" value={profile.donor_organs || ''} onChangeText={v => setProfile({ ...profile, donor_organs: v })} style={styles.input} placeholder="All / Kidneys / …" placeholderTextColor="#999" />
        )}

        <Text style={styles.lbl}>LIFE TESTAMENT</Text>
        <TextInput testID="prof-testament" value={profile.life_testament || ''} onChangeText={v => setProfile({ ...profile, life_testament: v })} style={[styles.input, { minHeight: 80 }]} multiline placeholderTextColor="#999" />

        <Pressable testID="prof-save" onPress={save} disabled={saving} style={styles.saveBtn}>
          {saving ? <ActivityIndicator color={C.onInverse} /> : <Text style={styles.saveBtnText}>{t('save', lang).toUpperCase()}</Text>}
        </Pressable>

        <Pressable testID="view-qr-btn" onPress={() => router.push('/emergency-qr')} style={styles.qrBtn}>
          <Ionicons name="qr-code-outline" size={18} color={C.fg} />
          <Text style={styles.qrBtnText}>{t('emergency_qr', lang).toUpperCase()}</Text>
        </Pressable>

        <Pressable testID="onboarding-btn" onPress={() => router.push('/onboarding')} style={styles.qrBtn}>
          <Ionicons name="heart-outline" size={18} color={C.fg} />
          <Text style={styles.qrBtnText}>SPRIEVODCA PRE RODINU A SENIOROV</Text>
        </Pressable>

        <Pressable testID="recovery-suite-btn" onPress={() => router.push('/recovery-suite')} style={styles.qrBtn}>
          <Ionicons name="key-outline" size={18} color={C.fg} />
          <Text style={styles.qrBtnText}>SOVEREIGN RECOVERY & 2FA</Text>
        </Pressable>

        <Pressable testID="legal-btn" onPress={() => router.push('/legal')} style={styles.qrBtn}>
          <Ionicons name="shield-checkmark-outline" size={18} color={C.fg} />
          <Text style={styles.qrBtnText}>{t('legal_hub', lang).toUpperCase()} · 2026</Text>
        </Pressable>

        <Pressable testID="dignity-btn" onPress={() => router.push('/dignity')} style={styles.qrBtn}>
          <Ionicons name="rose-outline" size={18} color={C.fg} />
          <Text style={styles.qrBtnText}>FINAL DIGNITY · POHREBNÝ FOND</Text>
        </Pressable>

        {admin?.is_founder && (
          <View style={styles.adminBox}>
            <Text style={styles.adminTitle}>👁 FOUNDER ADMIN</Text>
            <View style={styles.guardRow}>
              <Ionicons name="film-outline" size={22} color="#B8860B" />
              <View style={{ flex: 1 }}>
                <Text style={styles.guardTitle}>INVESTOR DEMO MODE</Text>
                <Text style={styles.guardSub}>Ukážkové dáta pre porotu: lov termínu · 150 € refundácia · rodinný pulz</Text>
              </View>
              {demoBusy ? <ActivityIndicator color="#B8860B" /> : (
                <Switch testID="demo-toggle" value={!!admin?.demo_mode} onValueChange={toggleDemo} trackColor={{ true: '#B8860B', false: C.surface3 }} />
              )}
            </View>
            {!!demoMsg && <Text testID="demo-msg" style={styles.adminMsg}>{demoMsg}</Text>}
            <Pressable testID="launch-btn" onPress={() => router.push('/launch')} style={styles.launchBtn}>
              <Ionicons name="rocket-outline" size={18} color="#0B0B0D" />
              <Text style={styles.launchText}>LAUNCH CONTROL · DEPLOY TO PRODUCTION</Text>
            </Pressable>
          </View>
        )}

        {!confirmDelete ? (
          <Pressable testID="delete-account-btn" onPress={() => setConfirmDelete(true)} style={styles.delBtn}>
            <Ionicons name="trash-outline" size={18} color={C.error} />
            <Text style={styles.delBtnText}>VYMAZAŤ ÚČET A VŠETKY DÁTA</Text>
          </Pressable>
        ) : (
          <View style={styles.delConfirm}>
            <Text style={styles.delConfirmText}>NAOZAJ VYMAZAŤ ÚČET? TÁTO AKCIA JE NEVRATNÁ — ODSTRÁNIA SA VŠETKY VAŠE DÁTA.</Text>
            <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.sm }}>
              <Pressable testID="delete-account-cancel" onPress={() => setConfirmDelete(false)} style={[styles.delAction, { borderColor: C.borderStrong }]}>
                <Text style={styles.delActionText}>ZRUŠIŤ</Text>
              </Pressable>
              <Pressable testID="delete-account-confirm" onPress={deleteAccount} style={[styles.delAction, { backgroundColor: C.error, borderColor: C.error }]}>
                <Text style={[styles.delActionText, { color: C.onError }]}>ÁNO, VYMAZAŤ</Text>
              </Pressable>
            </View>
          </View>
        )}

        <View style={styles.credit}>
          <Text style={styles.creditTitle}>ABOUT</Text>
          <Text style={styles.creditText}>Guardian Health & Angel is a sovereign survival OS.{'\n'}Steward: <Text style={{ fontWeight: '900' }}>Guardian Angel Sovereign Foundation (DAO)</Text> — pseudonymous, decentralized governance.{'\n'}© 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. Proprietary · Zero-Knowledge.{'\n'}EU AI Act Art. 50: AI outputs are informational only — you act at your own risk.</Text>
          <Text style={styles.creditText}>{'\n'}Proof of Origin (DID):{'\n'}</Text>
          <Text testID="origin-did" style={[styles.creditText, { fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }), fontSize: 10 }]}>{WATERMARK.did}</Text>
          <Text style={[styles.creditText, { fontSize: 10, marginTop: 4 }]}>Build {WATERMARK.build} · anchored {WATERMARK.anchored_at?.slice(0, 10)}</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { paddingHorizontal: S.lg, paddingVertical: S.md, backgroundColor: C.inverse, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  title: { color: C.onInverse, fontSize: 22, fontWeight: '900', letterSpacing: 2 },
  identityCard: { borderWidth: 2, borderColor: C.borderStrong, padding: S.md, marginBottom: S.lg, backgroundColor: C.surface2 },
  identityName: { fontSize: 18, fontWeight: '900', color: C.fg, letterSpacing: 1 },
  identityEmail: { color: C.onS3, marginTop: 4, fontSize: 13 },
  identityLbl: { marginTop: S.md, fontSize: 9, letterSpacing: 2, color: C.onS3, fontWeight: '800' },
  identityDid: { fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }), fontSize: 11, color: C.fg, marginTop: 2 },
  section: { marginTop: S.xl, marginBottom: S.md, fontSize: 11, letterSpacing: 2, color: C.fg, fontWeight: '900' },
  guardRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginBottom: S.sm, backgroundColor: C.bg },
  guardTitle: { fontWeight: '900', letterSpacing: 1, color: C.fg, fontSize: 13 },
  guardSub: { color: C.onS3, fontSize: 11, marginTop: 2 },
  geoMsg: { color: C.brand, fontSize: 11, marginTop: S.sm, fontWeight: '700' },
  chip: { paddingHorizontal: S.md, paddingVertical: 8, borderWidth: 1.5, borderColor: C.borderStrong, height: 36, alignItems: 'center', justifyContent: 'center' },
  chipActive: { backgroundColor: C.inverse },
  chipText: { fontWeight: '800', color: C.fg, letterSpacing: 1, fontSize: 12 },
  chipTextActive: { color: C.onInverse },
  lbl: { fontSize: 10, letterSpacing: 2, color: C.onS3, fontWeight: '800', marginTop: S.md, marginBottom: 6 },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 15, color: C.fg, backgroundColor: C.bg, marginBottom: S.sm },
  pickBtn: { flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', borderWidth: 1.5, borderColor: C.brand, minHeight: 48, marginBottom: S.sm },
  pickBtnText: { color: C.brand, fontWeight: '900', fontSize: 12, letterSpacing: 1 },
  donorRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, marginTop: S.lg, borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, backgroundColor: C.brandTer },
  donorTitle: { fontWeight: '900', letterSpacing: 1.5, color: C.brand, fontSize: 13 },
  donorSub: { color: C.brand, fontSize: 11, marginTop: 2 },
  saveBtn: { backgroundColor: C.inverse, paddingVertical: S.lg, alignItems: 'center', marginTop: S.lg },
  saveBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 15 },
  qrBtn: { marginTop: S.md, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: C.borderStrong, paddingVertical: S.md, backgroundColor: C.bg },
  qrBtnText: { color: C.fg, fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  delBtn: { marginTop: S.xl, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: C.error, paddingVertical: S.md },
  delBtnText: { color: C.error, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
  delConfirm: { marginTop: S.xl, borderWidth: 2, borderColor: C.error, padding: S.md },
  delConfirmText: { color: C.error, fontWeight: '900', fontSize: 12, lineHeight: 18 },
  delAction: { flex: 1, alignItems: 'center', paddingVertical: S.md, borderWidth: 2 },
  delActionText: { fontWeight: '900', letterSpacing: 1, fontSize: 12, color: C.fg },
  credit: { marginTop: S.xl, padding: S.md, borderTopWidth: 1.5, borderColor: C.borderStrong },
  adminBox: { marginTop: S.xl, borderWidth: 2, borderColor: '#B8860B', padding: S.md, backgroundColor: C.surface2 },
  adminTitle: { color: '#B8860B', fontWeight: '900', fontSize: 10, letterSpacing: 2, marginBottom: S.sm },
  adminMsg: { color: '#B8860B', fontWeight: '800', fontSize: 11, lineHeight: 16, marginBottom: S.sm },
  launchBtn: { flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: '#E5E4E2', paddingVertical: S.md, minHeight: 48 },
  launchText: { color: '#0B0B0D', fontWeight: '900', letterSpacing: 1, fontSize: 11 },
  creditTitle: { fontWeight: '900', letterSpacing: 2, fontSize: 11, color: C.fg },
  creditText: { marginTop: 6, color: C.onS3, fontSize: 12, lineHeight: 18 },
});
