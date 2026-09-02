/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// MAGIC LENS — point at ANY health document: AI reads it, explains it in plain
// language and files it into the Life Card. Senior-first, zero typing.
import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';
import Paywall from '@/src/Paywall';

const DETECTED_LABEL: Record<string, string> = {
  medications: 'a medication document', allergies: 'an allergy document',
  vaccinations: 'a vaccination record', lab_results: 'lab results',
  diagnoses: 'a diagnosis', surgeries: 'a surgery report',
  doctor_visits: 'a doctor visit report', insurance: 'an insurance document',
  emergency_contacts: 'emergency contact info', other: 'a health document',
};
const CATS: [string, string][] = [
  ['vaccine', '💉 VACCINATION'], ['disease', '🤒 DISEASE'], ['surgery', '🏥 SURGERY'],
  ['injury', '🩹 INJURY'], ['exam', '🩺 CHECK-UP'], ['dental', '🦷 DENTAL'],
];
const CAT_LABEL: Record<string, string> = {
  vaccine: 'Vaccinations', disease: 'Diseases', surgery: 'Surgeries',
  injury: 'Injuries', exam: 'Check-ups', dental: 'Dental',
};

type Scan = { found: boolean; extracted_text: string; summary: string; detected_category: string; suggested_title: string; lifecard_category: string };

export default function MagicLens() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const camRef = useRef<CameraView>(null);
  const [perm, requestPerm] = useCameraPermissions();
  const [phase, setPhase] = useState<'intro' | 'camera' | 'analyzing' | 'result' | 'edit' | 'saved'>('intro');
  const [scan, setScan] = useState<Scan | null>(null);
  const [err, setErr] = useState('');
  const [saving, setSaving] = useState(false);
  // edit form
  const [eTitle, setETitle] = useState('');
  const [eCat, setECat] = useState('exam');
  const [eNotes, setENotes] = useState('');

  const openCamera = async () => {
    setErr('');
    if (perm?.granted) { setPhase('camera'); return; }
    if (perm && !perm.canAskAgain) return; // settings button shown below
    const r = await requestPerm();
    if (r.granted) setPhase('camera');
  };

  // TIER GATE — Magic Lens is Guardian+ (proactive check on mount + 402 from the analyzer)
  const [locked, setLocked] = useState(false);
  useEffect(() => {
    api<any>('/subscription').then(s => setLocked(s?.tier === 'sovereign')).catch(() => {});
  }, []);
  const analyze = async (base64: string) => {
    setPhase('analyzing'); setErr('');
    try {
      const r: Scan = await api('/magic-lens', { method: 'POST', body: JSON.stringify({ image_base64: base64 }) });
      if (!r.found) {
        setErr('I could not read a document in that photo. Try again with better light, closer to the paper.');
        setPhase('intro');
        return;
      }
      setScan(r);
      setETitle(r.suggested_title); setECat(r.lifecard_category); setENotes(r.summary);
      setPhase('result');
    } catch (e: any) {
      if (/^402:/.test(String(e?.message))) { setLocked(true); setPhase('intro'); return; }
      setErr('The AI reader is unavailable right now. Please try again in a moment.');
      setPhase('intro');
    }
  };

  const capture = async () => {
    try {
      const photo = await camRef.current?.takePictureAsync({ base64: true, quality: 0.7 });
      if (photo?.base64) await analyze(photo.base64);
      else { setErr('Could not take the photo — try again.'); setPhase('intro'); }
    } catch {
      setErr('Could not take the photo — try again.'); setPhase('intro');
    }
  };

  const pickFromGallery = async () => {
    setErr('');
    const res = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.7, base64: true });
    if (!res.canceled && res.assets?.[0]?.base64) await analyze(res.assets[0].base64);
  };

  const save = async (title: string, cat: string, notes: string) => {
    setSaving(true); setErr('');
    try {
      const today = new Date().toISOString().slice(0, 10);
      await api('/calendar/events', {
        method: 'POST',
        body: JSON.stringify({ category: cat, title: title.trim() || 'Health document', date: today, notes: notes.trim() }),
      });
      setPhase('saved');
    } catch {
      setErr('Saving failed — please try again.');
    } finally { setSaving(false); }
  };

  return (
    <SafeAreaView style={st.root} edges={['top']}>
      {locked && (
        <View testID="ml-paywall" style={{ padding: S.lg }}>
          <Paywall tier="guardian" message={tt('magic_lens.magic_lens') + ' — Guardian Plan'} onUnlocked={() => setLocked(false)} />
        </View>
      )}
      <View style={st.header}>
        <Pressable testID="ml-back" onPress={() => (phase === 'camera' || phase === 'result' || phase === 'edit' ? setPhase('intro') : router.back())} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.fg} />
        </Pressable>
        <Text style={st.headerTitle}>{tt('magic_lens.magic_lens')}</Text>
        <View style={{ width: 26 }} />
      </View>

      {phase === 'camera' && perm?.granted ? (
        <View style={{ flex: 1 }}>
          <CameraView ref={camRef} style={{ flex: 1 }} facing="back">
            <View style={st.overlay}>
              <View style={st.frame} />
              <Text style={st.overlayText}>{tt('magic_lens.scan_document')}</Text>
              <Text style={st.overlaySub}>{tt('magic_lens.hold_the_paper_inside_the_frame')}</Text>
            </View>
          </CameraView>
          <View style={st.camBar}>
            <Pressable testID="ml-gallery" onPress={pickFromGallery} style={st.camSmallBtn}>
              <Ionicons name="image-outline" size={24} color={C.fg} />
            </Pressable>
            <Pressable testID="ml-shutter" onPress={capture} style={st.shutter}>
              <View style={st.shutterInner} />
            </Pressable>
            <View style={st.camSmallBtn} />
          </View>
        </View>
      ) : (
        <ScrollView contentContainerStyle={st.body}>
          {phase === 'intro' && (
            <>
              <View style={st.heroIcon}><Ionicons name="scan" size={54} color={C.brand} /></View>
              <Text style={st.heroTitle}>{tt('magic_lens.point_me_at_any')}{'\n'}{tt('magic_lens.health_document')}</Text>
              <Text style={st.heroSub}>{tt('magic_lens.a_letter_from_your_doctor_a_vaccinat')}</Text>
              {!!err && <Text testID="ml-err" style={st.err}>{err}</Text>}
              <Pressable testID="ml-open-camera" onPress={openCamera} style={st.goldBtn}>
                <Ionicons name="camera" size={24} color={C.onInverse} />
                <Text style={st.goldBtnText}>{tt('magic_lens.open_camera')}</Text>
              </Pressable>
              {perm && !perm.granted && !perm.canAskAgain && (
                <Pressable testID="ml-settings" onPress={() => Linking.openSettings()} style={st.settingsBtn}>
                  <Ionicons name="settings-outline" size={16} color={C.onWarn} />
                  <Text style={st.settingsText}>{tt('magic_lens.camera_is_blocked_open_settings')}</Text>
                </Pressable>
              )}
              <Pressable testID="ml-pick" onPress={pickFromGallery} style={st.ghostBtn}>
                <Ionicons name="image-outline" size={20} color={C.brand} />
                <Text style={st.ghostBtnText}>{tt('magic_lens.choose_a_photo_from_gallery')}</Text>
              </Pressable>
              <Text style={st.hint}>{tt('magic_lens.the_photo_is_analyzed_by_guardian_ai')}</Text>
            </>
          )}

          {phase === 'analyzing' && (
            <View style={st.center}>
              <ActivityIndicator size="large" color={C.brand} />
              <Text testID="ml-analyzing" style={st.analyzing}>{tt('magic_lens.reading_your_document')}</Text>
              <Text style={st.heroSub}>{tt('magic_lens.i_am_extracting_the_text_and_prepari')}</Text>
            </View>
          )}

          {phase === 'result' && scan && (
            <>
              <View style={st.detectBox}>
                <Ionicons name="sparkles" size={18} color={C.brand} />
                <Text testID="ml-detect" style={st.detectText}>
                  {tt('magic_lens.this_looks_like')} {DETECTED_LABEL[scan.detected_category] || tt('magic_lens.a_health_document')} {tt('magic_lens.save_to')} {CAT_LABEL[scan.lifecard_category]}?
                </Text>
              </View>
              <Text style={st.resTitle}>{scan.suggested_title}</Text>
              <View style={st.sumBox}>
                <Text style={st.sumLabel}>{tt('magic_lens.in_simple_words')}</Text>
                <Text testID="ml-summary" style={st.sumText}>{scan.summary}</Text>
              </View>
              {!!err && <Text style={st.err}>{err}</Text>}
              <Pressable testID="ml-yes" onPress={() => save(scan.suggested_title, scan.lifecard_category, scan.summary)} disabled={saving} style={st.goldBtn}>
                {saving ? <ActivityIndicator size="small" color={C.onInverse} /> : (
                  <>
                    <Ionicons name="checkmark-circle" size={24} color={C.onInverse} />
                    <Text style={st.goldBtnText}>{tt('magic_lens.yes_save_it')}</Text>
                  </>
                )}
              </Pressable>
              <Pressable testID="ml-edit" onPress={() => setPhase('edit')} style={st.ghostBtn}>
                <Ionicons name="create-outline" size={20} color={C.brand} />
                <Text style={st.ghostBtnText}>{tt('magic_lens.edit_before_saving')}</Text>
              </Pressable>
              <Pressable testID="ml-retake" onPress={openCamera} style={st.plainBtn}>
                <Text style={st.plainBtnText}>{tt('magic_lens.scan_another_document')}</Text>
              </Pressable>
            </>
          )}

          {phase === 'edit' && (
            <>
              <Text style={st.lbl}>{tt('magic_lens.title')}</Text>
              <TextInput testID="ml-e-title" style={st.input} value={eTitle} onChangeText={setETitle} placeholder={tt('magic_lens.document_title')} placeholderTextColor={C.info} />
              <Text style={st.lbl}>{tt('magic_lens.category')}</Text>
              <View style={st.catWrap}>
                {CATS.map(([k, label]) => (
                  <Pressable key={k} testID={`ml-cat-${k}`} onPress={() => setECat(k)} style={[st.catChip, eCat === k && st.catChipOn]}>
                    <Text style={[st.catChipText, eCat === k && { color: C.onInverse }]}>{label}</Text>
                  </Pressable>
                ))}
              </View>
              <Text style={st.lbl}>{tt('magic_lens.summary_notes')}</Text>
              <TextInput testID="ml-e-notes" style={[st.input, { minHeight: 110, textAlignVertical: 'top' }]} value={eNotes} onChangeText={setENotes} multiline placeholder={tt('magic_lens.notes')} placeholderTextColor={C.info} />
              {!!err && <Text style={st.err}>{err}</Text>}
              <Pressable testID="ml-e-save" onPress={() => save(eTitle, eCat, eNotes)} disabled={saving} style={st.goldBtn}>
                {saving ? <ActivityIndicator size="small" color={C.onInverse} /> : <Text style={st.goldBtnText}>{tt('magic_lens.save_to_life_card')}</Text>}
              </Pressable>
            </>
          )}

          {phase === 'saved' && (
            <View style={st.center}>
              <View style={st.heroIcon}><Ionicons name="checkmark-circle" size={54} color={C.brand} /></View>
              <Text testID="ml-saved" style={st.heroTitle}>{tt('magic_lens.saved_to_your')}{'\n'}{tt('magic_lens.life_card')}</Text>
              <Pressable testID="ml-open-lifecard" onPress={() => router.replace('/health-timeline')} style={st.goldBtn}>
                <Text style={st.goldBtnText}>{tt('magic_lens.open_life_card')}</Text>
              </Pressable>
              <Pressable testID="ml-again" onPress={() => { setScan(null); setPhase('intro'); }} style={st.ghostBtn}>
                <Text style={st.ghostBtnText}>{tt('magic_lens.scan_another_document_1izo')}</Text>
              </Pressable>
            </View>
          )}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  headerTitle: { color: C.brand, fontWeight: '900', fontSize: 16, letterSpacing: 2 },
  body: { padding: S.lg, paddingBottom: 60 },
  center: { alignItems: 'center', paddingTop: S.xl },
  heroIcon: { alignSelf: 'center', width: 96, height: 96, borderRadius: 48, borderWidth: 2, borderColor: C.brand, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(212,175,55,0.08)', marginTop: S.lg },
  heroTitle: { color: C.fg, fontSize: 26, fontWeight: '900', textAlign: 'center', marginTop: S.lg, lineHeight: 33 },
  heroSub: { color: C.info, fontSize: 15, textAlign: 'center', marginTop: S.md, lineHeight: 22 },
  goldBtn: { flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, borderRadius: R.md, paddingVertical: 16, marginTop: S.lg, minHeight: 54 },
  goldBtnText: { color: C.onInverse, fontWeight: '900', fontSize: 16, letterSpacing: 1 },
  ghostBtn: { flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', borderWidth: 1.5, borderColor: C.brand, borderRadius: R.md, paddingVertical: 14, marginTop: S.md, minHeight: 50 },
  ghostBtnText: { color: C.brand, fontWeight: '800', fontSize: 13, letterSpacing: 1 },
  plainBtn: { alignItems: 'center', paddingVertical: 14, marginTop: S.sm },
  plainBtnText: { color: C.info, fontWeight: '800', fontSize: 12, letterSpacing: 1 },
  settingsBtn: { flexDirection: 'row', gap: 6, alignItems: 'center', justifyContent: 'center', backgroundColor: C.warn, borderRadius: R.md, paddingVertical: 12, marginTop: S.md },
  settingsText: { color: C.onWarn, fontWeight: '800', fontSize: 12 },
  hint: { color: C.info, fontSize: 12, textAlign: 'center', marginTop: S.lg, lineHeight: 18 },
  err: { color: C.error, fontSize: 13, marginTop: S.md, textAlign: 'center', lineHeight: 19 },
  analyzing: { color: C.fg, fontSize: 20, fontWeight: '900', marginTop: S.lg },
  overlay: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  frame: { width: '82%', height: '55%', borderWidth: 2.5, borderColor: C.brand, borderRadius: R.lg, backgroundColor: 'transparent' },
  overlayText: { color: '#FFFFFF', fontWeight: '900', fontSize: 18, letterSpacing: 3, marginTop: S.md, textShadowColor: '#000', textShadowRadius: 6 },
  overlaySub: { color: '#FFFFFF', fontSize: 13, marginTop: 4, textShadowColor: '#000', textShadowRadius: 6 },
  camBar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-around', paddingVertical: S.lg, backgroundColor: C.bg },
  camSmallBtn: { width: 52, height: 52, borderRadius: 26, alignItems: 'center', justifyContent: 'center' },
  shutter: { width: 76, height: 76, borderRadius: 38, borderWidth: 4, borderColor: C.brand, alignItems: 'center', justifyContent: 'center' },
  shutterInner: { width: 58, height: 58, borderRadius: 29, backgroundColor: C.brand },
  detectBox: { flexDirection: 'row', gap: S.sm, alignItems: 'center', borderWidth: 1.5, borderColor: C.brand, backgroundColor: 'rgba(212,175,55,0.10)', borderRadius: R.md, padding: S.md },
  detectText: { flex: 1, color: C.fg, fontSize: 15, fontWeight: '700', lineHeight: 22 },
  resTitle: { color: C.fg, fontSize: 22, fontWeight: '900', marginTop: S.lg },
  sumBox: { backgroundColor: C.surface2, borderRadius: R.md, padding: S.md, marginTop: S.md, borderWidth: 1, borderColor: C.border },
  sumLabel: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 2 },
  sumText: { color: C.fg, fontSize: 17, lineHeight: 26, marginTop: 6 },
  lbl: { color: C.info, fontWeight: '900', fontSize: 11, letterSpacing: 1.5, marginTop: S.md, marginBottom: 6 },
  input: { backgroundColor: C.surface2, borderWidth: 1, borderColor: C.border, borderRadius: R.md, color: C.fg, paddingHorizontal: S.md, paddingVertical: 13, fontSize: 16 },
  catWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: S.sm },
  catChip: { borderWidth: 1.5, borderColor: C.border, borderRadius: R.pill, paddingHorizontal: 12, paddingVertical: 9 },
  catChipOn: { backgroundColor: C.brand, borderColor: C.brand },
  catChipText: { color: C.fg, fontWeight: '800', fontSize: 12 },
});
