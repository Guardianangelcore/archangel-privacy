/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// KARTA ŽIVOTA — zdravotná os od narodenia. Základné údaje (rodný list),
// 5 kategórií (Očkovania · Choroby · Operácie · Úrazy · Prehliadky),
// časová os, Jarvis predikcie → kalendár, hlasové pridávanie cez Jarvisa.
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator, Platform, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { api, apiUpload } from '@/src/api';
import { sharePdf } from '@/src/pdf';
import { DateField } from '@/src/ui/fields';
import { addToGuardianCalendar } from '@/src/native-calendar';
import { C, S, R } from '@/src/theme';

const CATS: any = {
  vaccine: { label: 'VACCINATION', plural: 'VACCINATIONS', icon: 'shield-checkmark-outline', color: '#5FA779', hint: 'Vaccine (e.g. Tetanus)' },
  disease: { label: 'DISEASE', plural: 'DISEASES', icon: 'thermometer-outline', color: '#BF5AF2', hint: 'Disease (e.g. Chickenpox)' },
  surgery: { label: 'SURGERY', plural: 'SURGERIES', icon: 'cut-outline', color: '#FF453A', hint: 'Surgery (e.g. Appendix)' },
  injury: { label: 'INJURY', plural: 'INJURIES', icon: 'bandage-outline', color: '#FF9F0A', hint: 'Injury (e.g. Fracture)' },
  exam: { label: 'CHECK-UP', plural: 'CHECK-UPS', icon: 'medkit-outline', color: '#D4AF37', hint: 'Check-up (e.g. Cardiology)' },
  dental: { label: 'DENTAL', plural: 'DENTAL', icon: 'tooth-outline', mci: true, color: '#64D2FF', hint: 'Procedure (e.g. Filling)' },
  history: { label: 'DOKUMENT', plural: 'DOKUMENTY', icon: 'document-text-outline', color: '#8E8E93', hint: '' },
};
const CAT_KEYS = ['vaccine', 'disease', 'surgery', 'injury', 'exam', 'dental'];
const BLOOD = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', '0+', '0-'];
const fmtDate = (iso?: string | null) => {
  if (!iso || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return iso || '—';
  const [y, m, d] = iso.split('-');
  return `${parseInt(d, 10)}. ${parseInt(m, 10)}. ${y}`;
};

const CatIcon = ({ cat, size, color }: { cat: string; size: number; color: string }) => {
  const ui = CATS[cat] || CATS.exam;
  return ui.mci
    ? <MaterialCommunityIcons name={ui.icon} size={size} color={color} />
    : <Ionicons name={ui.icon} size={size} color={color} />;
};

export default function LifeCard() {
  const router = useRouter();
  const [card, setCard] = useState<any>(null);
  const [data, setData] = useState<any>(null);
  const [filter, setFilter] = useState<string>('all');
  const [err, setErr] = useState('');

  // karty detí (Karta pre dieťa)
  const [children, setChildren] = useState<any[]>([]);
  const [activeChild, setActiveChild] = useState<any>(null); // null = moja karta

  // quick add (+)
  const [adding, setAdding] = useState(false);
  const [cat, setCat] = useState('vaccine');
  const [title, setTitle] = useState('');
  const [date, setDate] = useState('');
  const [notes, setNotes] = useState('');
  const [booster, setBooster] = useState('');
  const [tooth, setTooth] = useState('');
  const [busy, setBusy] = useState(false);

  // identity edit (+ nová karta dieťaťa)
  const [editing, setEditing] = useState(false);
  const [addingChild, setAddingChild] = useState(false);
  const [delChild, setDelChild] = useState(false);
  const [eName, setEName] = useState('');
  const [eBirth, setEBirth] = useState('');
  const [eBlood, setEBlood] = useState('');
  const [eSex, setESex] = useState('');
  const [cardBusy, setCardBusy] = useState(false);

  // predictions
  const [predBusy, setPredBusy] = useState(false);
  const [accepting, setAccepting] = useState<string>('');
  const [predMsg, setPredMsg] = useState('');

  // OCR rodného listu + PDF export + očkovací preukaz EÚ
  const [ocrBusy, setOcrBusy] = useState(false);
  const [ocrMsg, setOcrMsg] = useState('');
  const [camBlocked, setCamBlocked] = useState(false);
  const [pdfBusy, setPdfBusy] = useState(false);
  const [vaxBusy, setVaxBusy] = useState(false);

  // rodinné karty (Guardian Circle)
  const [fam, setFam] = useState<any>(null);
  const [famSel, setFamSel] = useState<string>('');
  const [famTl, setFamTl] = useState<any>(null);
  const [famBusy, setFamBusy] = useState(false);

  const tlQuery = (f: string, child: any) => {
    const p: string[] = [];
    if (f !== 'all') p.push(`category=${f}`);
    if (child) p.push(`child_id=${child.child_id}`);
    return p.length ? `?${p.join('&')}` : '';
  };

  const load = async (f = filter, child = activeChild) => {
    try {
      const [c, t, kids, fm] = await Promise.all([
        api('/lifecard'),
        api(`/calendar/timeline${tlQuery(f, child)}`),
        api('/lifecard/children').catch(() => null),
        api('/lifecard/family').catch(() => null),
      ]);
      setCard(c); setData(t); if (fm) setFam(fm);
      if (kids) {
        setChildren(kids.children || []);
        if (child) {
          const fresh = (kids.children || []).find((k: any) => k.child_id === child.child_id);
          if (fresh) setActiveChild(fresh);
        }
      }
    } catch (e: any) { setErr(String(e.message || e)); }
  };
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const setF = (f: string) => { setFilter(f); api(`/calendar/timeline${tlQuery(f, activeChild)}`).then(setData).catch(() => {}); };

  const switchCard = (child: any) => {
    setActiveChild(child); setFilter('all'); setEditing(false); setAddingChild(false); setDelChild(false);
    setPredMsg(''); setOcrMsg(''); setData(null);
    api(`/calendar/timeline${tlQuery('all', child)}`).then(setData).catch(() => {});
  };

  const openEdit = () => {
    const src = activeChild || card;
    setEName((activeChild ? activeChild.name : card?.full_name) || '');
    setEBirth(src?.birth_date || ''); setEBlood(src?.blood_type || '');
    setESex(activeChild?.sex || '');
    setAddingChild(false); setDelChild(false); setEditing(true);
  };

  const openAddChild = () => {
    setEName(''); setEBirth(''); setEBlood(''); setESex('');
    setEditing(false); setDelChild(false); setOcrMsg(''); setAddingChild(true);
  };

  const saveCard = async () => {
    setErr('');
    if (addingChild && (!eName.trim() || !eBirth)) { setErr('Enter the child name and date of birth.'); return; }
    setCardBusy(true);
    try {
      if (addingChild) {
        const ch = await api('/lifecard/children', { method: 'POST', body: JSON.stringify({ name: eName.trim(), birth_date: eBirth, blood_type: eBlood, sex: eSex }) });
        setAddingChild(false);
        setChildren(prev => [...prev, ch]);
        switchCard(ch);
      } else if (activeChild) {
        const ch = await api(`/lifecard/children/${activeChild.child_id}`, { method: 'PUT', body: JSON.stringify({ name: eName.trim() || null, birth_date: eBirth || null, blood_type: eBlood, sex: eSex }) });
        setActiveChild(ch);
        setChildren(prev => prev.map(k => (k.child_id === ch.child_id ? ch : k)));
        setEditing(false);
      } else {
        const c = await api('/lifecard', { method: 'PUT', body: JSON.stringify({ full_name: eName.trim() || null, birth_date: eBirth || null, blood_type: eBlood }) });
        setCard(c); setEditing(false);
      }
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setCardBusy(false); }
  };

  const removeChild = async () => {
    if (!activeChild) return;
    setCardBusy(true); setErr('');
    try {
      await api(`/lifecard/children/${activeChild.child_id}`, { method: 'DELETE' });
      setChildren(prev => prev.filter(k => k.child_id !== activeChild.child_id));
      switchCard(null);
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setCardBusy(false); }
  };

  const add = async () => {
    if (!title.trim() || !/^\d{4}-\d{2}-\d{2}$/.test(date)) { setErr('Enter a title and pick a date in the calendar.'); return; }
    setBusy(true); setErr('');
    try {
      await api('/calendar/events', { method: 'POST', body: JSON.stringify({ category: cat, title: title.trim(), date, notes: notes.trim(), booster_due: cat === 'vaccine' && booster ? booster : null, child_id: activeChild?.child_id || null, tooth: cat === 'dental' && tooth.trim() ? tooth.trim() : null }) });
      setTitle(''); setDate(''); setNotes(''); setBooster(''); setTooth(''); setAdding(false);
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(false); }
  };

  const del = async (id: string) => {
    try { await api(`/calendar/events/${id}`, { method: 'DELETE' }); await load(); } catch {}
  };

  // OCR rodného listu — Guardian Eye prefills the identity form (user confirms save)
  const runOcr = async (fromCamera: boolean) => {
    setErr(''); setOcrMsg(''); setCamBlocked(false);
    try {
      let res: any;
      if (fromCamera && Platform.OS !== 'web') {
        const p = await ImagePicker.getCameraPermissionsAsync();
        if (!p.granted) {
          if (!p.canAskAgain) { setCamBlocked(true); return; }
          const r = await ImagePicker.requestCameraPermissionsAsync();
          if (!r.granted) { if (!r.canAskAgain) setCamBlocked(true); return; }
        }
        res = await ImagePicker.launchCameraAsync({ quality: 0.8, allowsEditing: false });
      } else {
        res = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.8 });
      }
      if (res.canceled || !res.assets?.length) return;
      const a = res.assets[0];
      setOcrBusy(true);
      const r: any = await apiUpload('/lifecard/ocr', a.uri, a.fileName || 'rodny-list.jpg', a.mimeType || 'image/jpeg');
      if (!r.found) { setOcrMsg('Could not recognize the document in the photo. Try a sharper photo in better light.'); return; }
      if (r.full_name) setEName(r.full_name);
      if (r.birth_date) setEBirth(r.birth_date);
      if (r.blood_type) setEBlood(r.blood_type);
      setOcrMsg('📄 Data read from the document — review and press SAVE DETAILS.');
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setOcrBusy(false); }
  };

  // PDF Karty života — jedným ťukom pre lekára / rodinu
  const exportPdf = async () => {
    setPdfBusy(true); setErr('');
    try { await sharePdf(`/lifecard/report.pdf${activeChild ? `?child_id=${activeChild.child_id}` : ''}`, 'guardian_karta_zivota.pdf'); }
    catch (e: any) { setErr(String(e.message || e)); }
    finally { setPdfBusy(false); }
  };

  // Očkovací preukaz EÚ — viacjazyčný certifikát na cesty (14 jazykov)
  const exportVaxPass = async () => {
    setVaxBusy(true); setErr('');
    try { await sharePdf(`/lifecard/vaccine-pass.pdf${activeChild ? `?child_id=${activeChild.child_id}` : ''}`, 'guardian_ockovaci_preukaz_eu.pdf'); }
    catch (e: any) { setErr(String(e.message || e)); }
    finally { setVaxBusy(false); }
  };

  // Rodinná karta — načítanie očkovaní/prehliadok člena kruhu
  const openMember = async (m: any) => {
    if (famSel === m.user_id) { setFamSel(''); setFamTl(null); return; }
    setFamSel(m.user_id); setFamTl(null); setFamBusy(true);
    try { setFamTl(await api(`/lifecard/family/${m.user_id}/timeline`)); }
    catch (e: any) { setErr(String(e.message || e)); }
    finally { setFamBusy(false); }
  };

  const generatePredictions = async () => {
    setPredBusy(true); setPredMsg(''); setErr('');
    try {
      const r = await api('/lifecard/predictions', { method: 'POST', body: JSON.stringify({ child_id: activeChild?.child_id || null }) });
      if (activeChild) {
        setActiveChild((c: any) => ({ ...c, predictions: r.predictions }));
        setChildren(prev => prev.map(k => (k.child_id === activeChild.child_id ? { ...k, predictions: r.predictions } : k)));
      } else {
        setCard((c: any) => ({ ...c, predictions: r.predictions, predictions_at: r.generated_at }));
      }
      if (!r.predictions?.length) setPredMsg('Jarvis found no upcoming appointments — your history looks fine.');
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setPredBusy(false); }
  };

  const acceptPrediction = async (p: any) => {
    setAccepting(p.title); setPredMsg('');
    try {
      await api('/lifecard/predictions/accept', { method: 'POST', body: JSON.stringify({ title: p.title, category: p.category, date: p.suggested_date, reason: p.reason, child_id: activeChild?.child_id || null }) });
      let msg = '✅ Added to your Life Card.';
      if (Platform.OS !== 'web') {
        const nat = await addToGuardianCalendar(`🛡️ ${activeChild ? `${activeChild.name} — ` : ''}${p.title}`, p.suggested_date, `Guardian Angel · Jarvis predikcia\n${p.reason || ''}`);
        if (nat.ok) msg = '✅ Added to your Life Card and your phone calendar.';
        else if (nat.reason === 'blocked') msg = '✅ Added to your Life Card. Phone calendar is blocked — enable it in Settings.';
      }
      setPredMsg(msg);
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setAccepting(''); }
  };

  const events = data?.events || [];
  const counts = data?.counts || (activeChild ? activeChild.counts : card?.counts) || {};
  const predictions = (activeChild ? activeChild.predictions : card?.predictions) || [];
  const ident = activeChild || card;

  return (
    <SafeAreaView testID="health-timeline-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="ht-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>LIFE CARD</Text>
        <Pressable testID="ht-add" onPress={() => setAdding(!adding)} hitSlop={12}>
          <Ionicons name={adding ? 'close' : 'add'} size={26} color={C.brand} />
        </Pressable>
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
        <Text style={styles.h1}>Health timeline since birth</Text>
        <Text style={styles.sub}>Vaccinations · diseases · surgeries · injuries · check-ups — all on one timeline.</Text>
        {!!err && <Text style={styles.err}>{err}</Text>}

        {/* PREPÍNAČ KARIET — moja karta + karty detí */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginTop: S.md }} contentContainerStyle={{ gap: S.sm }}>
          <Pressable testID="lc-card-me" onPress={() => switchCard(null)} style={[styles.cardChip, !activeChild && styles.cardChipOn]}>
            <Ionicons name="shield" size={13} color={!activeChild ? C.onInverse : C.brand} />
            <Text style={[styles.cardChipText, !activeChild && { color: C.onInverse }]}>MY CARD</Text>
          </Pressable>
          {children.map(k => (
            <Pressable key={k.child_id} testID={`lc-card-${k.child_id}`} onPress={() => switchCard(k)} style={[styles.cardChip, activeChild?.child_id === k.child_id && styles.cardChipOn]}>
              <Ionicons name="happy-outline" size={13} color={activeChild?.child_id === k.child_id ? C.onInverse : C.brand} />
              <Text style={[styles.cardChipText, activeChild?.child_id === k.child_id && { color: C.onInverse }]}>{(k.name || '').toUpperCase()}</Text>
            </Pressable>
          ))}
          <Pressable testID="lc-add-child" onPress={openAddChild} style={styles.cardChip}>
            <Ionicons name="add" size={14} color={C.brand} />
            <Text style={styles.cardChipText}>CHILD</Text>
          </Pressable>
        </ScrollView>

        {/* ZÁKLADNÉ ÚDAJE — zdroj: rodný list */}
        {!card && <ActivityIndicator color={C.brand} style={{ marginTop: S.lg }} />}
        {card && (
          <View testID="lc-identity" style={styles.idCard}>
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <View style={styles.idIcon}><Ionicons name={activeChild ? 'happy' : 'person'} size={22} color={C.onInverse} /></View>
              <View style={{ flex: 1, marginLeft: S.md }}>
                <Text style={styles.idName}>{addingChild ? 'New child card' : (activeChild ? activeChild.name : (card.full_name || 'Guardian Angel'))}</Text>
                <Text style={styles.idSrc}>{activeChild || addingChild ? 'CHILD CARD · SOURCE: BIRTH CERTIFICATE' : 'IDENTITY · SOURCE: BIRTH CERTIFICATE'}</Text>
              </View>
              <Pressable testID="lc-edit" onPress={() => (editing || addingChild ? (setEditing(false), setAddingChild(false)) : openEdit())} hitSlop={10}>
                <Ionicons name={editing || addingChild ? 'close-circle-outline' : 'create-outline'} size={22} color={C.brand} />
              </Pressable>
            </View>
            {!addingChild && (
              <View style={styles.idRow}>
                <View style={styles.idCell}>
                  <Text style={styles.idLabel}>DATE OF BIRTH</Text>
                  <Text style={styles.idValue}>{ident?.birth_date ? fmtDate(ident.birth_date) : (!activeChild && card.birth_year ? String(card.birth_year) : '—')}</Text>
                </View>
                <View style={styles.idCell}>
                  <Text style={styles.idLabel}>AGE</Text>
                  <Text style={styles.idValue}>{ident?.age != null ? `${ident.age} y.` : '—'}</Text>
                </View>
                <View style={styles.idCell}>
                  <Text style={styles.idLabel}>BLOOD TYPE</Text>
                  <Text style={[styles.idValue, { color: C.error }]}>{ident?.blood_type || '—'}</Text>
                </View>
              </View>
            )}
            {(editing || addingChild) && (
              <View style={styles.editBox}>
                <View style={{ flexDirection: 'row', gap: S.sm }}>
                  <Pressable testID="lc-ocr-cam" onPress={() => runOcr(true)} disabled={ocrBusy} style={styles.ocrBtn}>
                    {ocrBusy ? <ActivityIndicator size="small" color={C.brand} /> : (
                      <>
                        <Ionicons name="camera-outline" size={15} color={C.brand} />
                        <Text style={styles.ocrBtnText}>SCAN BIRTH CERTIFICATE</Text>
                      </>
                    )}
                  </Pressable>
                  <Pressable testID="lc-ocr-pick" onPress={() => runOcr(false)} disabled={ocrBusy} style={styles.ocrBtn}>
                    <Ionicons name="image-outline" size={15} color={C.brand} />
                    <Text style={styles.ocrBtnText}>FROM GALLERY</Text>
                  </Pressable>
                </View>
                {camBlocked && (
                  <Pressable testID="lc-ocr-settings" onPress={() => Linking.openSettings()} style={styles.settingsBtn}>
                    <Ionicons name="settings-outline" size={14} color={C.onWarn} />
                    <Text style={styles.settingsText}>Camera is blocked — OPEN SETTINGS</Text>
                  </Pressable>
                )}
                {!!ocrMsg && <Text testID="lc-ocr-msg" style={styles.predMsg}>{ocrMsg}</Text>}
                <TextInput testID="lc-name" style={styles.input} placeholder={activeChild || addingChild ? 'Child name' : 'Full name'} placeholderTextColor={C.info} value={eName} onChangeText={setEName} />
                <DateField testID="lc-birth" title="DATE OF BIRTH" value={eBirth} onChange={setEBirth} placeholder="Date of birth" style={styles.input} />
                <Text style={styles.idLabel}>BLOOD TYPE</Text>
                <View style={styles.bloodRow}>
                  {BLOOD.map(b => (
                    <Pressable key={b} testID={`lc-blood-${b}`} onPress={() => setEBlood(eBlood === b ? '' : b)} style={[styles.bloodChip, eBlood === b && { backgroundColor: C.brand, borderColor: C.brand }]}>
                      <Text style={[styles.bloodChipText, eBlood === b && { color: C.onInverse }]}>{b}</Text>
                    </Pressable>
                  ))}
                </View>
                {(activeChild || addingChild) && (
                  <>
                    <Text style={styles.idLabel}>SEX (for WHO growth percentiles)</Text>
                    <View style={{ flexDirection: 'row', gap: S.sm }}>
                      <Pressable testID="lc-sex-m" onPress={() => setESex(eSex === 'm' ? '' : 'm')} style={[styles.bloodChip, { flex: 1 }, eSex === 'm' && { backgroundColor: C.brand, borderColor: C.brand }]}>
                        <Text style={[styles.bloodChipText, eSex === 'm' && { color: C.onInverse }]}>👦 BOY</Text>
                      </Pressable>
                      <Pressable testID="lc-sex-f" onPress={() => setESex(eSex === 'f' ? '' : 'f')} style={[styles.bloodChip, { flex: 1 }, eSex === 'f' && { backgroundColor: C.brand, borderColor: C.brand }]}>
                        <Text style={[styles.bloodChipText, eSex === 'f' && { color: C.onInverse }]}>👧 GIRL</Text>
                      </Pressable>
                    </View>
                  </>
                )}
                <Pressable testID="lc-save-card" onPress={saveCard} disabled={cardBusy} style={styles.cta}>
                  {cardBusy ? <ActivityIndicator color={C.onInverse} /> : <Text style={styles.ctaText}>{addingChild ? 'CREATE CHILD CARD' : 'SAVE DETAILS'}</Text>}
                </Pressable>
                {editing && activeChild && !delChild && (
                  <Pressable testID="lc-del-child" onPress={() => setDelChild(true)} style={styles.delBtn}>
                    <Ionicons name="trash-outline" size={14} color={C.error} />
                    <Text style={styles.delBtnText}>DELETE CHILD CARD</Text>
                  </Pressable>
                )}
                {editing && activeChild && delChild && (
                  <View style={{ flexDirection: 'row', gap: S.sm }}>
                    <Pressable testID="lc-del-child-yes" onPress={removeChild} style={[styles.delBtn, { flex: 1, backgroundColor: C.error, borderColor: C.error }]}>
                      <Text style={[styles.delBtnText, { color: C.onInverse }]}>YES, DELETE INCLUDING RECORDS</Text>
                    </Pressable>
                    <Pressable testID="lc-del-child-no" onPress={() => setDelChild(false)} style={[styles.delBtn, { flex: 1 }]}>
                      <Text style={[styles.delBtnText, { color: C.fg }]}>CANCEL</Text>
                    </Pressable>
                  </View>
                )}
              </View>
            )}
          </View>
        )}

        {/* PDF · PREUKAZ EÚ · TRENDY · RAST — 1 ťuk */}
        {card && (
          <View style={styles.btnRow}>
            <Pressable testID="lc-magic-lens" onPress={() => router.push('/magic-lens')} style={[styles.pdfBtn, { borderColor: C.brand, backgroundColor: 'rgba(212,175,55,0.12)' }]}>
              <Ionicons name="scan" size={16} color={C.brand} />
              <Text style={styles.pdfText}>✨ MAGIC LENS</Text>
            </Pressable>
            <Pressable testID="lc-pdf" onPress={exportPdf} disabled={pdfBusy} style={styles.pdfBtn}>
              {pdfBusy ? <ActivityIndicator size="small" color={C.brand} /> : (
                <>
                  <Ionicons name="print-outline" size={16} color={C.brand} />
                  <Text style={styles.pdfText}>PDF FOR DOCTOR</Text>
                </>
              )}
            </Pressable>
            <Pressable testID="lc-vaxpass" onPress={exportVaxPass} disabled={vaxBusy} style={styles.pdfBtn}>
              {vaxBusy ? <ActivityIndicator size="small" color={C.brand} /> : (
                <>
                  <Ionicons name="airplane-outline" size={16} color={C.brand} />
                  <Text style={styles.pdfText}>EU VACCINATION PASS</Text>
                </>
              )}
            </Pressable>
            <Pressable testID="lc-trends" onPress={() => router.push({ pathname: '/health-trends', params: activeChild ? { child_id: activeChild.child_id, name: activeChild.name } : {} } as any)} style={styles.pdfBtn}>
              <Ionicons name="bar-chart-outline" size={16} color={C.brand} />
              <Text style={styles.pdfText}>HEALTH TRENDS</Text>
            </Pressable>
            {activeChild && (
              <Pressable testID="lc-growth" onPress={() => router.push({ pathname: '/child-growth', params: { child_id: activeChild.child_id } } as any)} style={styles.pdfBtn}>
                <Ionicons name="trending-up-outline" size={16} color={C.brand} />
                <Text style={styles.pdfText}>GROWTH CURVE</Text>
              </Pressable>
            )}
          </View>
        )}

        {/* HLASOVÉ PRIDÁVANIE cez Jarvisa — len pre moju kartu */}
        {!activeChild && (
          <Pressable testID="lc-voice-hint" onPress={() => router.push('/jarvis')} style={styles.voiceHint}>
            <Ionicons name="mic-outline" size={20} color={C.brand} />
            <Text style={styles.voiceHintText}>Tell Jarvis: Today my doctor told me I have chickenpox — it will be filed here automatically.</Text>
            <Ionicons name="chevron-forward" size={16} color={C.info} />
          </Pressable>
        )}

        {(data?.booster_alerts || []).length > 0 && (
          <View style={styles.alertBox}>
            <Ionicons name="alarm-outline" size={18} color={C.onWarn} />
            <View style={{ flex: 1 }}>
              <Text style={styles.alertTitle}>BOOSTER DUE SOON</Text>
              {data.booster_alerts.map((b: any) => (
                <Text key={b.event_id} style={styles.alertText}>• {b.title} — booster do {b.booster_due}</Text>
              ))}
            </View>
          </View>
        )}

        {/* RÝCHLE PRIDANIE (+) — dátum + typ + popis */}
        {adding && (
          <View style={styles.addBox}>
            <View style={styles.catWrap}>
              {CAT_KEYS.map(k => (
                <Pressable key={k} testID={`ht-cat-${k}`} onPress={() => setCat(k)} style={[styles.catChip, cat === k && { backgroundColor: CATS[k].color, borderColor: CATS[k].color }]}>
                  <CatIcon cat={k} size={13} color={cat === k ? C.onInverse : CATS[k].color} />
                  <Text style={[styles.catChipText, cat === k && { color: C.onInverse }]}>{CATS[k].label}</Text>
                </Pressable>
              ))}
            </View>
            <TextInput testID="ht-title" style={styles.input} placeholder={CATS[cat].hint} placeholderTextColor={C.info} value={title} onChangeText={setTitle} />
            <DateField testID="ht-date" title="DATE" value={date} onChange={setDate} placeholder="Date" style={styles.input} />
            <TextInput testID="lc-notes" style={styles.input} placeholder="Notes (optional)" placeholderTextColor={C.info} value={notes} onChangeText={setNotes} />
            {cat === 'vaccine' && (
              <DateField testID="ht-booster" title="BOOSTER DUE" value={booster} onChange={setBooster} placeholder="Booster due (optional)" style={styles.input} />
            )}
            {cat === 'dental' && (
              <TextInput testID="lc-tooth" style={styles.input} placeholder="Tooth no. (optional, e.g. 36)" placeholderTextColor={C.info} keyboardType="number-pad" maxLength={4} value={tooth} onChangeText={setTooth} />
            )}
            <Pressable testID="ht-save" onPress={add} disabled={busy} style={styles.cta}>
              {busy ? <ActivityIndicator color={C.onInverse} /> : <Text style={styles.ctaText}>SAVE RECORD</Text>}
            </Pressable>
          </View>
        )}

        {/* PREDIKCIE — Jarvis navrhne ďalšie očkovanie / kontrolu */}
        <View testID="lc-predictions" style={styles.predBox}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.sm }}>
            <Ionicons name="sparkles" size={16} color={C.brand} />
            <Text style={styles.predTitle}>PREDICTIONS · JARVIS</Text>
            <View style={{ flex: 1 }} />
            <Pressable testID="lc-predict" onPress={generatePredictions} disabled={predBusy} style={styles.predBtn}>
              {predBusy ? <ActivityIndicator size="small" color={C.onInverse} /> : <Text style={styles.predBtnText}>{predictions.length ? 'REFRESH' : 'SUGGEST'}</Text>}
            </Pressable>
          </View>
          <Text style={styles.predSub}>{activeChild ? `Jarvis suggests the next vaccination or check-up for ${activeChild.name} based on the pediatric vaccination schedule.` : 'Based on your history, Jarvis suggests when your next vaccination or check-up is due.'}</Text>
          {!!predMsg && <Text testID="lc-pred-msg" style={styles.predMsg}>{predMsg}</Text>}
          {predictions.map((p: any, i: number) => {
            const ui = CATS[p.category] || CATS.exam;
            return (
              <View key={`${p.title}-${i}`} testID={`lc-pred-${i}`} style={styles.predCard}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.sm }}>
                  <CatIcon cat={p.category} size={15} color={ui.color} />
                  <Text style={[styles.tlCat, { color: ui.color }]}>{ui.label} · {p.suggested_date}</Text>
                </View>
                <Text style={styles.predCardTitle}>{p.title}</Text>
                {!!p.reason && <Text style={styles.predReason}>{p.reason}</Text>}
                <Pressable testID={`lc-accept-${i}`} onPress={() => acceptPrediction(p)} disabled={accepting === p.title} style={styles.acceptBtn}>
                  {accepting === p.title ? <ActivityIndicator size="small" color={C.onInverse} /> : (
                    <>
                      <Ionicons name="calendar-outline" size={14} color={C.onInverse} />
                      <Text style={styles.acceptText}>ADD TO CALENDAR</Text>
                    </>
                  )}
                </Pressable>
              </View>
            );
          })}
          {predictions.length > 0 && <Text style={styles.aiMark}>AI Content · Sovereign Protocol</Text>}
        </View>

        {/* RODINNÉ KARTY — Guardian Circle (len očkovania + prehliadky) — len pre moju kartu */}
        {!activeChild && (
        <View testID="lc-family" style={styles.famBox}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.sm }}>
            <Ionicons name="people" size={16} color={C.brand} />
            <Text style={styles.predTitle}>FAMILY CARDS · GUARDIAN CIRCLE</Text>
          </View>
          {!fam && <ActivityIndicator size="small" color={C.brand} style={{ marginTop: S.md }} />}
          {fam && (fam.members || []).length === 0 && (
            <Pressable testID="lc-fam-empty" onPress={() => router.push('/recovery-suite')} style={styles.famEmpty}>
              <Text style={styles.hint}>No Guardian Circle members yet. Add family as guardians (Social Recovery) to see their vaccinations and check-ups.</Text>
              <Text style={styles.famEmptyLink}>+ ADD GUARDIAN →</Text>
            </Pressable>
          )}
          {(fam?.members || []).map((m: any) => (
            <View key={m.user_id}>
              <Pressable testID={`lc-fam-${m.user_id}`} onPress={() => openMember(m)} style={styles.famRow}>
                <View style={styles.famAvatar}><Text style={styles.famInitial}>{(m.name || '?').charAt(0).toUpperCase()}</Text></View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.famName}>{m.name}</Text>
                  <Text style={styles.famMeta}>💉 {m.counts.vaccine} vaccinations · 🩺 {m.counts.exam} check-ups{m.booster_soon ? ` · ⏰ booster within 30 days` : ''}</Text>
                </View>
                <Ionicons name={famSel === m.user_id ? 'chevron-up' : 'chevron-down'} size={16} color={C.info} />
              </Pressable>
              {famSel === m.user_id && (
                <View style={styles.famDetail}>
                  {famBusy && <ActivityIndicator size="small" color={C.brand} />}
                  {famTl && (famTl.events || []).length === 0 && <Text style={styles.hint}>No vaccinations or check-ups.</Text>}
                  {(famTl?.events || []).map((e: any) => (
                    <View key={e.event_id} style={styles.famEvRow}>
                      <CatIcon cat={e.category} size={13} color={(CATS[e.category] || CATS.exam).color} />
                      <Text style={styles.famEvText}>{fmtDate(e.date)} — {e.title}{e.booster_due ? ` (booster do ${fmtDate(e.booster_due)})` : ''}</Text>
                    </View>
                  ))}
                  {famTl && <Text style={styles.famPrivacy}>For privacy, only vaccinations and check-ups are shared within the circle.</Text>}
                </View>
              )}
            </View>
          ))}
        </View>
        )}

        {/* FILTRE — 5 kategórií s počtami */}
        <View style={styles.filterRow}>
          <Pressable testID="ht-filter-all" onPress={() => setF('all')} style={[styles.fChip, filter === 'all' && { backgroundColor: C.brand, borderColor: C.brand }]}>
            <Text style={[styles.fChipText, filter === 'all' && { color: C.onInverse }]}>ALL</Text>
          </Pressable>
          {CAT_KEYS.map(k => (
            <Pressable key={k} testID={`ht-filter-${k}`} onPress={() => setF(k)} style={[styles.fChip, filter === k && { backgroundColor: CATS[k].color, borderColor: CATS[k].color }]}>
              <Text style={[styles.fChipText, filter === k && { color: C.onInverse }]}>{CATS[k].plural}{counts[k] ? ` (${counts[k]})` : ''}</Text>
            </Pressable>
          ))}
        </View>

        {!data && <ActivityIndicator color={C.brand} style={{ marginTop: 40 }} />}
        {data && events.length === 0 && <Text style={styles.hint}>No records yet. Add the first via + or just tell Jarvis.</Text>}

        {/* KARTA ZUBÁRA — história podľa zubov (pri filtri ZUBÁR) */}
        {filter === 'dental' && events.length > 0 && (
          <View testID="lc-dental-card" style={styles.dentalBox}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.sm }}>
              <MaterialCommunityIcons name="tooth-outline" size={16} color="#64D2FF" />
              <Text style={[styles.predTitle, { color: '#64D2FF' }]}>DENTAL CARD — BY TOOTH</Text>
            </View>
            {(() => {
              const byTooth: any = {};
              events.filter((e: any) => e.tooth).forEach((e: any) => { (byTooth[e.tooth] = byTooth[e.tooth] || []).push(e); });
              const teeth = Object.keys(byTooth).sort();
              if (!teeth.length) return <Text style={styles.hint}>Tip: add a tooth number to a record to see treatment history by tooth.</Text>;
              return teeth.map(t => (
                <Text key={t} style={styles.dentalRow}>🦷 Zub {t}: {byTooth[t].map((e: any) => `${e.title} (${fmtDate(e.date)})`).join(' · ')}</Text>
              ));
            })()}
          </View>
        )}

        {/* ČASOVÁ OS */}
        <View style={{ marginTop: S.lg }}>
          {events.map((e: any, i: number) => {
            const ui = CATS[e.category] || CATS.exam;
            const future = e.date >= (data?.today || '');
            return (
              <View key={e.event_id} style={styles.tlRow}>
                <View style={styles.tlLeft}>
                  <View style={[styles.tlDot, { backgroundColor: ui.color }]} />
                  {i < events.length - 1 && <View style={styles.tlLine} />}
                </View>
                <View style={[styles.tlCard, future && { borderColor: C.brand }]}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.sm }}>
                    <CatIcon cat={e.category} size={16} color={ui.color} />
                    <Text style={[styles.tlCat, { color: ui.color }]}>{ui.label}{future ? ' · UPCOMING' : ''}{e.source === 'voice' ? ' · 🎙 JARVIS' : e.source === 'jarvis' ? ' · ✨ PREDICTION' : ''}</Text>
                    <View style={{ flex: 1 }} />
                    <Pressable testID={`ht-del-${e.event_id}`} onPress={() => del(e.event_id)} hitSlop={8}>
                      <Ionicons name="trash-outline" size={15} color={C.info} />
                    </Pressable>
                  </View>
                  <Text style={styles.tlTitle}>{e.title}</Text>
                  <Text style={styles.tlDate}>{e.date}{e.tooth ? ` · zub ${e.tooth}` : ''}{e.booster_due ? ` · booster: ${e.booster_due}` : ''}{e.notes ? ` · ${e.notes}` : ''}</Text>
                </View>
              </View>
            );
          })}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 14 },
  h1: { fontSize: 24, fontWeight: '900', color: C.fg },
  sub: { marginTop: S.sm, fontSize: 13, color: C.onS3, lineHeight: 19 },
  // card switcher (moja karta / deti)
  cardChip: { flexDirection: 'row', alignItems: 'center', gap: 5, borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.pill, paddingVertical: 9, paddingHorizontal: 14, minHeight: 38 },
  cardChipOn: { backgroundColor: C.brand, borderColor: C.brand },
  cardChipText: { color: C.brand, fontWeight: '900', fontSize: 10.5, letterSpacing: 1 },
  delBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, borderWidth: 1, borderColor: C.error, borderRadius: R.sm, minHeight: 42 },
  delBtnText: { color: C.error, fontWeight: '900', fontSize: 10, letterSpacing: 0.5 },
  // identity card (rodný list)
  idCard: { marginTop: S.lg, backgroundColor: 'rgba(212,175,55,0.10)', borderRadius: R.lg, borderWidth: 1.5, borderColor: C.brand, padding: S.lg },
  idIcon: { width: 44, height: 44, borderRadius: 22, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center' },
  idName: { color: C.fg, fontWeight: '900', fontSize: 17 },
  idSrc: { color: C.brand, fontWeight: '800', fontSize: 9, letterSpacing: 1.5, marginTop: 2 },
  idRow: { flexDirection: 'row', marginTop: S.md, gap: S.sm },
  idCell: { flex: 1, backgroundColor: 'rgba(10,10,15,0.55)', borderRadius: R.sm, padding: S.md, borderWidth: 1, borderColor: C.border },
  idLabel: { color: C.info, fontWeight: '800', fontSize: 8.5, letterSpacing: 1 },
  idValue: { color: C.fg, fontWeight: '900', fontSize: 15, marginTop: 3 },
  editBox: { marginTop: S.md, gap: S.sm },
  bloodRow: { flexDirection: 'row', flexWrap: 'wrap', gap: S.sm },
  bloodChip: { borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.pill, paddingHorizontal: 14, paddingVertical: 8, minWidth: 52, alignItems: 'center' },
  bloodChipText: { color: C.fg, fontWeight: '900', fontSize: 12 },
  // OCR + PDF
  ocrBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.pill, minHeight: 42, paddingHorizontal: 10 },
  ocrBtnText: { color: C.brand, fontWeight: '900', fontSize: 9.5, letterSpacing: 0.5 },
  settingsBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, backgroundColor: C.warn, borderRadius: R.sm, minHeight: 40, paddingHorizontal: 10 },
  settingsText: { color: C.onWarn, fontWeight: '900', fontSize: 10 },
  btnRow: { flexDirection: 'row', flexWrap: 'wrap', gap: S.sm, marginTop: S.md },
  pdfBtn: { flexGrow: 1, flexBasis: '47%', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: S.sm, borderWidth: 1.5, borderColor: C.brand, borderRadius: R.md, minHeight: 48, backgroundColor: C.surface2 },
  pdfText: { color: C.brand, fontWeight: '900', fontSize: 10.5, letterSpacing: 0.8 },
  dentalBox: { marginTop: S.lg, backgroundColor: 'rgba(100,210,255,0.07)', borderRadius: R.md, borderWidth: 1, borderColor: '#64D2FF', padding: S.md },
  dentalRow: { color: C.onS3, fontSize: 12, marginTop: S.sm, lineHeight: 17 },
  // rodinné karty
  famBox: { marginTop: S.lg, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.md },
  famEmpty: { marginTop: S.xs },
  famEmptyLink: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 1, marginTop: S.sm },
  famRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, marginTop: S.md, minHeight: 52 },
  famAvatar: { width: 40, height: 40, borderRadius: 20, backgroundColor: C.brandTer, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: C.borderStrong },
  famInitial: { color: C.brand, fontWeight: '900', fontSize: 16 },
  famName: { color: C.fg, fontWeight: '800', fontSize: 14 },
  famMeta: { color: C.info, fontSize: 11, marginTop: 2 },
  famDetail: { marginTop: S.sm, marginLeft: 52, gap: 6, borderLeftWidth: 2, borderLeftColor: C.border, paddingLeft: S.md, paddingBottom: S.sm },
  famEvRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  famEvText: { color: C.onS3, fontSize: 12, flex: 1 },
  famPrivacy: { color: C.info, fontSize: 9.5, marginTop: 4, fontStyle: 'italic' },
  // voice hint
  voiceHint: { marginTop: S.md, flexDirection: 'row', alignItems: 'center', gap: S.md, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.md },
  voiceHintText: { flex: 1, color: C.onS3, fontSize: 12, lineHeight: 17 },
  // alerts + add
  alertBox: { marginTop: S.lg, flexDirection: 'row', gap: S.md, backgroundColor: C.warn, borderRadius: R.md, padding: S.md },
  alertTitle: { color: C.onWarn, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  alertText: { color: C.onWarn, fontSize: 12, marginTop: 2, fontWeight: '700' },
  addBox: { marginTop: S.lg, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.brand, padding: S.md, gap: S.sm },
  catWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: S.sm },
  catChip: { flexDirection: 'row', alignItems: 'center', gap: 5, borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.pill, paddingVertical: 8, paddingHorizontal: 12 },
  catChipText: { color: C.fg, fontWeight: '800', fontSize: 10, letterSpacing: 0.5 },
  input: { backgroundColor: C.bg, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, color: C.fg, paddingHorizontal: S.md, minHeight: 46, fontSize: 13 },
  cta: { backgroundColor: C.brand, borderRadius: R.sm, minHeight: 48, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
  // predictions
  predBox: { marginTop: S.lg, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md },
  predTitle: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 2 },
  predSub: { color: C.info, fontSize: 11, marginTop: 6, lineHeight: 16 },
  predBtn: { backgroundColor: C.brand, borderRadius: R.pill, paddingHorizontal: 14, minHeight: 32, alignItems: 'center', justifyContent: 'center' },
  predBtnText: { color: C.onInverse, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  predMsg: { color: C.brandSec, fontSize: 11.5, marginTop: S.sm, fontWeight: '700' },
  predCard: { marginTop: S.md, backgroundColor: C.bg, borderRadius: R.sm, borderWidth: 1, borderColor: C.border, padding: S.md },
  predCardTitle: { color: C.fg, fontWeight: '800', fontSize: 14, marginTop: 4 },
  predReason: { color: C.onS3, fontSize: 11.5, marginTop: 3, lineHeight: 16 },
  acceptBtn: { marginTop: S.md, flexDirection: 'row', gap: 6, backgroundColor: C.brand, borderRadius: R.pill, minHeight: 40, alignItems: 'center', justifyContent: 'center' },
  acceptText: { color: C.onInverse, fontWeight: '900', fontSize: 10.5, letterSpacing: 1 },
  aiMark: { color: C.info, fontSize: 9, letterSpacing: 1, marginTop: S.md, textAlign: 'right' },
  // filters + timeline
  filterRow: { flexDirection: 'row', flexWrap: 'wrap', gap: S.sm, marginTop: S.lg },
  fChip: { borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.pill, paddingHorizontal: S.md, paddingVertical: 8 },
  fChipText: { color: C.fg, fontWeight: '800', fontSize: 10, letterSpacing: 0.5 },
  hint: { marginTop: S.lg, color: C.onS3, fontSize: 12, lineHeight: 18 },
  tlRow: { flexDirection: 'row', gap: S.md },
  tlLeft: { width: 20, alignItems: 'center' },
  tlDot: { width: 12, height: 12, borderRadius: 6, marginTop: 18 },
  tlLine: { flex: 1, width: 2, backgroundColor: C.border, marginTop: 4 },
  tlCard: { flex: 1, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.md, marginBottom: S.md },
  tlCat: { fontWeight: '900', fontSize: 9, letterSpacing: 1 },
  tlTitle: { color: C.fg, fontWeight: '800', fontSize: 14, marginTop: 4 },
  tlDate: { color: C.info, fontSize: 11, marginTop: 2 },
  err: { color: C.error, marginTop: S.md, fontSize: 12 },
});
