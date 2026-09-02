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
import { CityPicker, LanguageSuggestionBanner } from '@/src/CityPicker';
import { C, S } from '@/src/theme';
import { t, LANG_NAMES, Lang } from '@/src/i18n';
import { useI18n } from '@/src/i18n-context';
import { WATERMARK } from '@/src/watermark';
import { AGE_LABEL_EN, ageFromBirthYear, stageFromAge } from '@/src/age';
import { speak as jarvisSpeak } from '@/src/voice';
import { getPanicTaps, setPanicTaps } from '@/src/panic-gesture';
import { useDemoMode, setDemoMode } from '@/src/demo-mode';
import * as LocalAuthentication from 'expo-local-authentication';

export default function Profile() {
  const { user, signOut, setUser } = useAuth();
  const router = useRouter();
  const { lang, setLang } = useI18n();   // instant, app-wide re-render on change
  const [profile, setProfile] = useState<any>({});
  const [saving, setSaving] = useState(false);
  const [ecPick, setEcPick] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [admin, setAdmin] = useState<any>(null);
  const [demoBusy, setDemoBusy] = useState(false);
  const [demoMsg, setDemoMsg] = useState('');
  const [geo, setGeo] = useState<any>(null);
  const [geoMsg, setGeoMsg] = useState('');
  const [cityPick, setCityPick] = useState(false);
  const [langSuggest, setLangSuggest] = useState<any>(null);
  const demoBadge = useDemoMode();

  const applyLangSuggestion = async () => {
    if (!langSuggest) return;
    try {
      await setPref({ language: langSuggest.to });
      setGeoMsg(`Language switched to ${langSuggest.to.toUpperCase()} based on ${langSuggest.city}.`);
    } catch (e: any) { setGeoMsg(String(e.message || e)); }
    finally { setLangSuggest(null); }
  };

  const tryIpFallback = async () => {
    setGeoMsg('Trying IP-based location…');
    try {
      const r: any = await api('/geo/ip-locate', { method: 'POST' });
      setGeo(r.geo);
      if (r.language_suggestion) setLangSuggest(r.language_suggestion);
      setGeoMsg(r.geo.source === 'ip-fallback'
        ? `IP location unavailable — pick your city manually. (${r.geo.city})`
        : `IP: ${r.geo.city} · ${r.geo.country}`);
      const me: any = await api('/auth/me');
      if (me?.user) setUser(me.user);
    } catch (e: any) { setGeoMsg(String(e.message || e)); }
  };

  const toggleTravel = async (v: boolean) => {
    setGeoMsg(''); setLangSuggest(null);
    try {
      if (v && Platform.OS !== 'web') {
        const p = await Location.getForegroundPermissionsAsync();
        if (!p.granted) {
          if (!p.canAskAgain) {
            setGeoMsg('Location blocked — trying IP fallback. If needed, open the manual city picker.');
            await tryIpFallback();
            return;
          }
          const r = await Location.requestForegroundPermissionsAsync();
          if (!r.granted) {
            setGeoMsg(r.canAskAgain
              ? 'No GPS — trying IP fallback.'
              : 'Location blocked — trying IP fallback, then you can pick a city manually.');
            await tryIpFallback();
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
          if (loc.language_switched) setGeoMsg(`Language auto-switched: ${loc.geo.city} (${loc.language.toUpperCase()})`);
          else if (loc.language_suggestion) { setGeoMsg(`Location: ${loc.geo.city} · ${loc.geo.country}`); setLangSuggest(loc.language_suggestion); }
          else setGeoMsg(`Location: ${loc.geo.city} · ${loc.geo.country}`);
        } catch {
          await tryIpFallback();
        }
      } else if (v && Platform.OS === 'web') {
        // Web preview — GPS API unreliable, use IP fallback directly.
        await tryIpFallback();
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
      setDemoMsg(v ? 'DEMO MODE ACTIVE — dashboard filled with showcase data (slot hunt, €150 refund, family pulse).' : 'Demo data removed — clean production state.');
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

  const setPref = async (patch: Record<string, any>) => {
    const u: any = await api('/me/prefs', { method: 'PATCH', body: JSON.stringify(patch) });
    setUser(u);
  };

  // Sentient UX — Bio-Timeline (age-adaptive UI + medical logic)
  const [birthYearTxt, setBirthYearTxt] = useState<string>(
    (user as any)?.birth_year ? String((user as any).birth_year) : ''
  );
  useEffect(() => {
    setBirthYearTxt((user as any)?.birth_year ? String((user as any).birth_year) : '');
  }, [user]);
  const [bioMsg, setBioMsg] = useState('');
  const saveBirthYear = async () => {
    const by = parseInt(birthYearTxt, 10);
    if (!by || by < 1900 || by > 2030) {
      setBioMsg('Enter a valid birth year (1900–2030).');
      return;
    }
    setBioMsg('');
    try {
      await setPref({ birth_year: by });
      setBioMsg('Bio-Timeline updated. The interface will adapt to your stage of life.');
    } catch (e: any) {
      setBioMsg(String(e.message || e));
    }
  };
  const currentStage = stageFromAge(ageFromBirthYear((user as any)?.birth_year));

  // Sentient UX — Biometric gate toggle (FaceID/Fingerprint on app open)
  const [bioLabel, setBioLabel] = useState('FaceID / Fingerprint');
  useEffect(() => {
    (async () => {
      try {
        if (Platform.OS === 'web') return;
        const types = await LocalAuthentication.supportedAuthenticationTypesAsync();
        if (types.includes(LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION)) setBioLabel('FaceID');
        else if (types.includes(LocalAuthentication.AuthenticationType.FINGERPRINT)) setBioLabel('Fingerprint');
        else if (types.includes(LocalAuthentication.AuthenticationType.IRIS)) setBioLabel('Iris');
      } catch {}
    })();
  }, []);
  const toggleBiometric = async (v: boolean) => {
    if (v && Platform.OS !== 'web') {
      // Verify the user is who they say they are before enabling the gate.
      try {
        const hasHw = await LocalAuthentication.hasHardwareAsync();
        const enrolled = await LocalAuthentication.isEnrolledAsync();
        if (!hasHw || !enrolled) {
          setBioMsg('This device has no biometrics enrolled. Set up FaceID/fingerprint in system settings.');
          return;
        }
        const r = await LocalAuthentication.authenticateAsync({ promptMessage: 'Confirm enabling biometrics' });
        if (!r.success) { setBioMsg('Verification cancelled.'); return; }
      } catch {}
    }
    await setPref({ biometric_enabled: v });
  };

  // Sentient UX — Wake-Word "JARVIS" toggle
  const toggleWakeWord = async (v: boolean) => {
    await setPref({ wake_word_enabled: v });
  };

  // Sentient UX — voice-preview button ("Ako znie Jarvis?")
  const previewVoice = () => {
    jarvisSpeak(
      'Good day. I am Jarvis, your guardian angel. From now on I will speak to you in a human voice.',
      { voice: 'onyx', speed: 0.95, language: lang }
    );
  };

  // Panic gesture threshold (default 19 taps on back of phone)
  const [panicTapsTxt, setPanicTapsTxt] = useState<string>('19');
  useEffect(() => { (async () => { const n = await getPanicTaps(); setPanicTapsTxt(String(n)); })(); }, []);
  const savePanicTaps = async () => {
    const n = parseInt(panicTapsTxt, 10);
    if (!n || n < 3 || n > 30) { setBioMsg('The tap count must be between 3 and 30.'); return; }
    await setPanicTaps(n);
    setPanicTapsTxt(String(Math.max(3, Math.min(30, n))));
    setBioMsg(`Panic gesture set to ${n} taps on the back of the phone.`);
    jarvisSpeak(`Panic gesture set to ${n} taps.`, { voice: 'onyx', speed: 0.95, language: lang });
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
          <Text style={styles.identityLbl}>{t('decentralized_id', lang)}</Text>
          <Text style={styles.identityDid}>{user?.did}</Text>
        </View>

        {/* COMPETITION DEMO BADGE — global "DEMO" pill in the top-right corner */}
        <Text style={styles.section}>{t('demo_mode', lang)}</Text>
        <View style={styles.guardRow}>
          <Ionicons name="pricetag-outline" size={22} color={C.brand} />
          <View style={{ flex: 1 }}>
            <Text style={styles.guardTitle}>DEMO BADGE</Text>
            <Text style={styles.guardSub}>Shows a DEMO badge in the top-right corner on every screen.</Text>
          </View>
          <Switch
            testID="prof-demo-badge"
            value={demoBadge}
            onValueChange={v => setDemoMode(v)}
            trackColor={{ true: C.brand, false: C.surface3 }}
          />
        </View>

        <Text testID="prof-lang-title" style={styles.section}>{t('language', lang)}</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: S.sm }}>
          {(Object.keys(LANG_NAMES) as Lang[]).map(l => (
            <Pressable testID={`prof-lang-${l}`} key={l} onPress={() => setLang(l)} style={[styles.chip, lang === l && styles.chipActive]}>
              <Text style={[styles.chipText, lang === l && styles.chipTextActive]}>{LANG_NAMES[l]}</Text>
            </Pressable>
          ))}
        </View>

        {/* ===== SENTIENT UX — the human soul of the OS ===== */}
        <Text style={styles.section}>{t('sentient_ux', lang)}</Text>

        {/* JARVIS VOICE PREVIEW */}
        <View style={styles.guardRow}>
          <Ionicons name="mic-circle" size={24} color={C.brand} />
          <View style={{ flex: 1 }}>
            <Text style={styles.guardTitle}>JARVIS VOICE · ONYX</Text>
            <Text style={styles.guardSub}>Deep human voice (OpenAI TTS). Robotic system voice disabled.</Text>
          </View>
          <Pressable testID="prof-voice-preview" onPress={previewVoice} style={styles.previewBtn}>
            <Ionicons name="volume-high" size={16} color={C.onInverse} />
            <Text style={styles.previewText}>PREVIEW</Text>
          </Pressable>
        </View>

        {/* BIO-TIMELINE — the Growth Engine */}
        <View style={styles.guardRow}>
          <Ionicons name="calendar-outline" size={22} color={C.fg} />
          <View style={{ flex: 1 }}>
            <Text style={styles.guardTitle}>BIO-TIMELINE · BIRTH YEAR</Text>
            <Text style={styles.guardSub}>
              The interface adapts to your stage of life — from infant to senior.
            </Text>
          </View>
        </View>
        <View style={{ flexDirection: 'row', gap: S.sm, alignItems: 'center' }}>
          <TextInput
            testID="prof-birth-year"
            value={birthYearTxt}
            onChangeText={setBirthYearTxt}
            style={[styles.input, { flex: 1 }]}
            placeholder="e.g. 1958"
            placeholderTextColor="#999"
            keyboardType="number-pad"
            maxLength={4}
          />
          <Pressable testID="prof-birth-year-save" onPress={saveBirthYear} style={styles.saveMini}>
            <Text style={styles.saveMiniText}>SAVE</Text>
          </Pressable>
        </View>
        {(user as any)?.birth_year && (
          <Text testID="prof-stage-label" style={styles.stageLabel}>
            STAGE: {AGE_LABEL_EN[currentStage].toUpperCase()}
          </Text>
        )}

        {/* BIOMETRIC GATE */}
        <View style={styles.guardRow}>
          <Ionicons name="finger-print" size={22} color={C.fg} />
          <View style={{ flex: 1 }}>
            <Text style={styles.guardTitle}>BIOMETRIC LOCK · {bioLabel.toUpperCase()}</Text>
            <Text style={styles.guardSub}>
              Unlock with your personal signal every time the app opens. Health data stays private.
            </Text>
          </View>
          <Switch
            testID="prof-biometric"
            value={!!(user as any)?.biometric_enabled}
            onValueChange={toggleBiometric}
            trackColor={{ true: C.brand, false: C.surface3 }}
          />
        </View>

        {/* WAKE-WORD */}
        <View style={styles.guardRow}>
          <Ionicons name="radio-outline" size={22} color={C.fg} />
          <View style={{ flex: 1 }}>
            <Text style={styles.guardTitle}>WAKE-WORD JARVIS</Text>
            <Text style={styles.guardSub}>
              Hands-free voice activation. Fully works only in a native build (not Expo Go).
            </Text>
          </View>
          <Switch
            testID="prof-wake-word"
            value={!!(user as any)?.wake_word_enabled}
            onValueChange={toggleWakeWord}
            trackColor={{ true: C.brand, false: C.surface3 }}
          />
        </View>

        {/* PANIC GESTURE — Silent Witness back-of-phone tap threshold */}
        <View style={styles.guardRow}>
          <Ionicons name="hand-left" size={22} color={C.fg} />
          <View style={{ flex: 1 }}>
            <Text style={styles.guardTitle}>PANIC GESTURE · SILENT WITNESS</Text>
            <Text style={styles.guardSub}>
              Tap the back of your phone N times within 10 seconds → hidden Silent Witness launch.
            </Text>
          </View>
        </View>
        <View style={{ flexDirection: 'row', gap: S.sm, alignItems: 'center' }}>
          <TextInput
            testID="prof-panic-taps"
            value={panicTapsTxt}
            onChangeText={setPanicTapsTxt}
            style={[styles.input, { flex: 1 }]}
            placeholder="19"
            placeholderTextColor="#999"
            keyboardType="number-pad"
            maxLength={2}
          />
          <Pressable testID="prof-panic-taps-save" onPress={savePanicTaps} style={styles.saveMini}>
            <Text style={styles.saveMiniText}>SAVE</Text>
          </Pressable>
        </View>
        {!!bioMsg && <Text style={styles.geoMsg}>{bioMsg}</Text>}
        {/* ===== END SENTIENT UX ===== */}

        <Text style={styles.section}>{t('guardian_monitoring', lang).toUpperCase()}</Text>
        <View style={styles.guardRow}>
          <Ionicons name="body-outline" size={22} color={C.fg} />
          <View style={{ flex: 1 }}>
            <Text style={styles.guardTitle}>{t('fall_guard', lang).toUpperCase()}</Text>
            <Text style={styles.guardSub}>Accelerometer · auto Fall-Verify</Text>
          </View>
          <Switch testID="prof-fall-guard" value={!!(user as any)?.fall_guard} onValueChange={v => setPref({ fall_guard: v })} trackColor={{ true: C.brand, false: C.surface3 }} />
        </View>
        <View style={styles.guardRow}>
          <Ionicons name="time-outline" size={22} color={C.fg} />
          <View style={{ flex: 1 }}>
            <Text style={styles.guardTitle}>{t('inactivity_guard', lang).toUpperCase()}</Text>
            <Text style={styles.guardSub}>08:00–21:00 · alerts your family</Text>
          </View>
          <Switch testID="prof-inactivity-guard" value={!!(user as any)?.inactivity_guard} onValueChange={v => setPref({ inactivity_guard: v })} trackColor={{ true: C.brand, false: C.surface3 }} />
        </View>
        <View style={styles.guardRow}>
          <Ionicons name="heart-half-outline" size={22} color={C.fg} />
          <View style={{ flex: 1 }}>
            <Text style={styles.guardTitle}>GUARDIAN PULSE CHECK</Text>
            <Text style={styles.guardSub}>A silent ping from family · strictly opt-in, disable any time</Text>
          </View>
          <Switch testID="prof-pulse-optin" value={!!(user as any)?.pulse_check_optin} onValueChange={v => setPref({ pulse_check_optin: v })} trackColor={{ true: C.brand, false: C.surface3 }} />
        </View>
        <View style={styles.guardRow}>
          <Ionicons name="airplane-outline" size={22} color={C.fg} />
          <View style={{ flex: 1 }}>
            <Text style={styles.guardTitle}>TRAVEL MODE (GEO)</Text>
            <Text style={styles.guardSub}>{geo ? `📍 ${geo.city} · ${geo.country}${geo.source ? ` · ${String(geo.source).toUpperCase()}` : ''}` : '📍 Automatic location (GPS/IP) — allow location access'} — automatic city, language and regulations by GPS</Text>
          </View>
          <Switch testID="prof-travel-mode" value={!!(user as any)?.travel_mode} onValueChange={toggleTravel} trackColor={{ true: C.brand, false: C.surface3 }} />
        </View>
        <LanguageSuggestionBanner
          suggestion={langSuggest}
          onAccept={applyLangSuggestion}
          onDismiss={() => setLangSuggest(null)}
        />
        <View style={{ flexDirection: 'row', gap: S.sm }}>
          <Pressable testID="prof-geo-ip" onPress={tryIpFallback} style={[styles.pickBtn, { flex: 1 }]}>
            <Ionicons name="globe-outline" size={16} color={C.brand} />
            <Text style={styles.pickBtnText}>IP LOCATION</Text>
          </Pressable>
          <Pressable testID="prof-geo-manual" onPress={() => setCityPick(true)} style={[styles.pickBtn, { flex: 1 }]}>
            <Ionicons name="map-outline" size={16} color={C.brand} />
            <Text style={styles.pickBtnText}>PICK CITY</Text>
          </Pressable>
        </View>
        <CityPicker
          visible={cityPick}
          onClose={() => setCityPick(false)}
          onPicked={(r) => {
            setGeo(r.geo);
            if (r.language_suggestion) setLangSuggest(r.language_suggestion);
            setGeoMsg(`Manual: ${r.geo.city} · ${r.geo.country}`);
          }}
        />
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

        <Text style={styles.section}>{t('donor_card', lang).toUpperCase()} + {t('emergency_profile', lang)}</Text>
        <Text style={styles.lbl}>FULL NAME</Text>
        <TextInput testID="prof-name" value={profile.full_name || ''} onChangeText={v => setProfile({ ...profile, full_name: v })} style={styles.input} placeholder="First Last" placeholderTextColor="#999" />

        <Text style={styles.lbl}>{t('blood_type', lang).toUpperCase()}</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: S.sm }}>
          {['A+','A-','B+','B-','AB+','AB-','O+','O-'].map(b => (
            <Pressable testID={`blood-${b}`} key={b} onPress={() => setProfile({ ...profile, blood_type: b })} style={[styles.chip, profile.blood_type === b && styles.chipActive]}>
              <Text style={[styles.chipText, profile.blood_type === b && styles.chipTextActive]}>{b}</Text>
            </Pressable>
          ))}
        </View>

        <Text style={styles.lbl}>{t('allergies', lang).toUpperCase()}</Text>
        <TextInput testID="prof-allergies" value={profile.allergies || ''} onChangeText={v => setProfile({ ...profile, allergies: v })} style={[styles.input, { minHeight: 60 }]} multiline placeholder="penicillin, latex…" placeholderTextColor="#999" />

        <Text style={styles.lbl}>MEDICATIONS</Text>
        <TextInput testID="prof-meds" value={profile.medications || ''} onChangeText={v => setProfile({ ...profile, medications: v })} style={[styles.input, { minHeight: 60 }]} multiline placeholderTextColor="#999" />

        <Text style={styles.lbl}>CONDITIONS</Text>
        <TextInput testID="prof-conditions" value={profile.conditions || ''} onChangeText={v => setProfile({ ...profile, conditions: v })} style={[styles.input, { minHeight: 60 }]} multiline placeholderTextColor="#999" />

        <Text style={styles.lbl}>{t('emergency_contact', lang).toUpperCase()}</Text>
        <TextInput testID="prof-ec-name" value={profile.emergency_contact_name || ''} onChangeText={v => setProfile({ ...profile, emergency_contact_name: v })} style={styles.input} placeholder="Name" placeholderTextColor="#999" />
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
          <Text style={styles.qrBtnText}>GUIDE FOR FAMILY & SENIORS</Text>
        </Pressable>

        <Pressable testID="recovery-suite-btn" onPress={() => router.push('/recovery-suite')} style={styles.qrBtn}>
          <Ionicons name="key-outline" size={18} color={C.fg} />
          <Text style={styles.qrBtnText}>SOVEREIGN RECOVERY & 2FA</Text>
        </Pressable>

        <Pressable testID="legal-btn" onPress={() => router.push('/legal')} style={styles.qrBtn}>
          <Ionicons name="shield-checkmark-outline" size={18} color={C.fg} />
          <Text style={styles.qrBtnText}>{t('legal_hub', lang).toUpperCase()} · 2026</Text>
        </Pressable>

        <Pressable testID="eternal-vault-btn" onPress={() => router.push('/eternal-vault')} style={styles.qrBtn}>
          <Ionicons name="lock-closed-outline" size={18} color={C.fg} />
          <Text style={styles.qrBtnText}>ETERNAL VAULT · LEGACY & LAST WILL</Text>
        </Pressable>

        {admin?.is_founder && (
          <View style={styles.adminBox}>
            <Text style={styles.adminTitle}>👁 FOUNDER ADMIN</Text>
            <View style={styles.guardRow}>
              <Ionicons name="film-outline" size={22} color="#B8860B" />
              <View style={{ flex: 1 }}>
                <Text style={styles.guardTitle}>INVESTOR DEMO MODE</Text>
                <Text style={styles.guardSub}>Showcase data for the jury: slot hunt · €150 refund · family pulse</Text>
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
            <Text style={styles.delBtnText}>DELETE ACCOUNT & ALL DATA</Text>
          </Pressable>
        ) : (
          <View style={styles.delConfirm}>
            <Text style={styles.delConfirmText}>REALLY DELETE YOUR ACCOUNT? THIS ACTION IS IRREVERSIBLE — ALL YOUR DATA WILL BE REMOVED.</Text>
            <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.sm }}>
              <Pressable testID="delete-account-cancel" onPress={() => setConfirmDelete(false)} style={[styles.delAction, { borderColor: C.borderStrong }]}>
                <Text style={styles.delActionText}>CANCEL</Text>
              </Pressable>
              <Pressable testID="delete-account-confirm" onPress={deleteAccount} style={[styles.delAction, { backgroundColor: C.error, borderColor: C.error }]}>
                <Text style={[styles.delActionText, { color: C.onError }]}>YES, DELETE</Text>
              </Pressable>
            </View>
          </View>
        )}

        <View style={styles.credit}>
          <Text style={styles.creditTitle}>ABOUT</Text>
          <Text style={styles.creditText}>Archangel OS is a sovereign survival OS.{'\n'}Steward: <Text style={{ fontWeight: '900' }}>Guardian Angel Sovereign Foundation (DAO)</Text> — pseudonymous, decentralized governance.{'\n'}© 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. Proprietary · Zero-Knowledge.{'\n'}EU AI Act Art. 50: AI outputs are informational only — you act at your own risk.</Text>
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
  previewBtn: { flexDirection: 'row', gap: 6, alignItems: 'center', backgroundColor: C.brand, paddingHorizontal: S.md, paddingVertical: 8, borderRadius: 20 },
  previewText: { color: C.onInverse, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  saveMini: { backgroundColor: C.inverse, paddingHorizontal: S.lg, minHeight: 48, alignItems: 'center', justifyContent: 'center', marginBottom: S.sm },
  saveMiniText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
  stageLabel: { color: C.brand, fontSize: 11, letterSpacing: 1.5, fontWeight: '900', marginTop: 4, marginBottom: S.sm },
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
