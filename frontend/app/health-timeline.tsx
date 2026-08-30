/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// KARTA ŽIVOTA — zdravotná os od narodenia. Základné údaje (rodný list),
// 5 kategórií (Očkovania · Choroby · Operácie · Úrazy · Prehliadky),
// časová os, Jarvis predikcie → kalendár, hlasové pridávanie cez Jarvisa.
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { DateField } from '@/src/ui/fields';
import { addToGuardianCalendar } from '@/src/native-calendar';
import { C, S, R } from '@/src/theme';

const CATS: any = {
  vaccine: { label: 'OČKOVANIE', plural: 'OČKOVANIA', icon: 'shield-checkmark-outline', color: '#5FA779', hint: 'Vakcína (napr. Tetanus)' },
  disease: { label: 'CHOROBA', plural: 'CHOROBY', icon: 'thermometer-outline', color: '#BF5AF2', hint: 'Choroba (napr. Kiahne)' },
  surgery: { label: 'OPERÁCIA', plural: 'OPERÁCIE', icon: 'cut-outline', color: '#FF453A', hint: 'Operácia (napr. Slepé črevo)' },
  injury: { label: 'ÚRAZ', plural: 'ÚRAZY', icon: 'bandage-outline', color: '#FF9F0A', hint: 'Úraz (napr. Zlomenina)' },
  exam: { label: 'PREHLIADKA', plural: 'PREHLIADKY', icon: 'medkit-outline', color: '#D4AF37', hint: 'Prehliadka (napr. Kardiológia)' },
  history: { label: 'DOKUMENT', plural: 'DOKUMENTY', icon: 'document-text-outline', color: '#8E8E93', hint: '' },
};
const CAT_KEYS = ['vaccine', 'disease', 'surgery', 'injury', 'exam'];
const BLOOD = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', '0+', '0-'];
const fmtDate = (iso?: string | null) => {
  if (!iso || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return iso || '—';
  const [y, m, d] = iso.split('-');
  return `${parseInt(d, 10)}. ${parseInt(m, 10)}. ${y}`;
};

export default function LifeCard() {
  const router = useRouter();
  const [card, setCard] = useState<any>(null);
  const [data, setData] = useState<any>(null);
  const [filter, setFilter] = useState<string>('all');
  const [err, setErr] = useState('');

  // quick add (+)
  const [adding, setAdding] = useState(false);
  const [cat, setCat] = useState('vaccine');
  const [title, setTitle] = useState('');
  const [date, setDate] = useState('');
  const [notes, setNotes] = useState('');
  const [booster, setBooster] = useState('');
  const [busy, setBusy] = useState(false);

  // identity edit
  const [editing, setEditing] = useState(false);
  const [eName, setEName] = useState('');
  const [eBirth, setEBirth] = useState('');
  const [eBlood, setEBlood] = useState('');
  const [cardBusy, setCardBusy] = useState(false);

  // predictions
  const [predBusy, setPredBusy] = useState(false);
  const [accepting, setAccepting] = useState<string>('');
  const [predMsg, setPredMsg] = useState('');

  const load = async (f = filter) => {
    try {
      const [c, t] = await Promise.all([
        api('/lifecard'),
        api(`/calendar/timeline${f !== 'all' ? `?category=${f}` : ''}`),
      ]);
      setCard(c); setData(t);
    } catch (e: any) { setErr(String(e.message || e)); }
  };
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const setF = (f: string) => { setFilter(f); api(`/calendar/timeline${f !== 'all' ? `?category=${f}` : ''}`).then(setData).catch(() => {}); };

  const openEdit = () => {
    setEName(card?.full_name || ''); setEBirth(card?.birth_date || ''); setEBlood(card?.blood_type || '');
    setEditing(true);
  };

  const saveCard = async () => {
    setCardBusy(true); setErr('');
    try {
      const c = await api('/lifecard', { method: 'PUT', body: JSON.stringify({ full_name: eName.trim() || null, birth_date: eBirth || null, blood_type: eBlood }) });
      setCard(c); setEditing(false);
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setCardBusy(false); }
  };

  const add = async () => {
    if (!title.trim() || !/^\d{4}-\d{2}-\d{2}$/.test(date)) { setErr('Zadajte názov a vyberte dátum v kalendári.'); return; }
    setBusy(true); setErr('');
    try {
      await api('/calendar/events', { method: 'POST', body: JSON.stringify({ category: cat, title: title.trim(), date, notes: notes.trim(), booster_due: cat === 'vaccine' && booster ? booster : null }) });
      setTitle(''); setDate(''); setNotes(''); setBooster(''); setAdding(false);
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(false); }
  };

  const del = async (id: string) => {
    try { await api(`/calendar/events/${id}`, { method: 'DELETE' }); await load(); } catch {}
  };

  const generatePredictions = async () => {
    setPredBusy(true); setPredMsg(''); setErr('');
    try {
      const r = await api('/lifecard/predictions', { method: 'POST' });
      setCard((c: any) => ({ ...c, predictions: r.predictions, predictions_at: r.generated_at }));
      if (!r.predictions?.length) setPredMsg('Jarvis nenašiel žiadne blížiace sa termíny — história je v poriadku.');
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setPredBusy(false); }
  };

  const acceptPrediction = async (p: any) => {
    setAccepting(p.title); setPredMsg('');
    try {
      await api('/lifecard/predictions/accept', { method: 'POST', body: JSON.stringify({ title: p.title, category: p.category, date: p.suggested_date, reason: p.reason }) });
      let msg = '✅ Pridané do Karty života.';
      if (Platform.OS !== 'web') {
        const nat = await addToGuardianCalendar(`🛡️ ${p.title}`, p.suggested_date, `Guardian Angel · Jarvis predikcia\n${p.reason || ''}`);
        if (nat.ok) msg = '✅ Pridané do Karty života aj do kalendára telefónu.';
        else if (nat.reason === 'blocked') msg = '✅ Pridané do Karty života. Kalendár telefónu je zablokovaný — povoľte ho v Nastaveniach.';
      }
      setPredMsg(msg);
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setAccepting(''); }
  };

  const events = data?.events || [];
  const counts = data?.counts || card?.counts || {};
  const predictions = card?.predictions || [];

  return (
    <SafeAreaView testID="health-timeline-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="ht-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>KARTA ŽIVOTA</Text>
        <Pressable testID="ht-add" onPress={() => setAdding(!adding)} hitSlop={12}>
          <Ionicons name={adding ? 'close' : 'add'} size={26} color={C.brand} />
        </Pressable>
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
        <Text style={styles.h1}>Zdravotná os od narodenia</Text>
        <Text style={styles.sub}>Očkovania · choroby · operácie · úrazy · prehliadky — všetko na jednej časovej osi.</Text>
        {!!err && <Text style={styles.err}>{err}</Text>}

        {/* ZÁKLADNÉ ÚDAJE — zdroj: rodný list */}
        {!card && <ActivityIndicator color={C.brand} style={{ marginTop: S.lg }} />}
        {card && (
          <View testID="lc-identity" style={styles.idCard}>
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <View style={styles.idIcon}><Ionicons name="person" size={22} color={C.onInverse} /></View>
              <View style={{ flex: 1, marginLeft: S.md }}>
                <Text style={styles.idName}>{card.full_name || 'Guardian Angel'}</Text>
                <Text style={styles.idSrc}>ZÁKLADNÉ ÚDAJE · ZDROJ: RODNÝ LIST</Text>
              </View>
              <Pressable testID="lc-edit" onPress={() => (editing ? setEditing(false) : openEdit())} hitSlop={10}>
                <Ionicons name={editing ? 'close-circle-outline' : 'create-outline'} size={22} color={C.brand} />
              </Pressable>
            </View>
            <View style={styles.idRow}>
              <View style={styles.idCell}>
                <Text style={styles.idLabel}>DÁTUM NARODENIA</Text>
                <Text style={styles.idValue}>{card.birth_date ? fmtDate(card.birth_date) : (card.birth_year ? String(card.birth_year) : '—')}</Text>
              </View>
              <View style={styles.idCell}>
                <Text style={styles.idLabel}>VEK</Text>
                <Text style={styles.idValue}>{card.age != null ? `${card.age} r.` : '—'}</Text>
              </View>
              <View style={styles.idCell}>
                <Text style={styles.idLabel}>KRVNÁ SKUPINA</Text>
                <Text style={[styles.idValue, { color: C.error }]}>{card.blood_type || '—'}</Text>
              </View>
            </View>
            {editing && (
              <View style={styles.editBox}>
                <TextInput testID="lc-name" style={styles.input} placeholder="Meno a priezvisko" placeholderTextColor={C.info} value={eName} onChangeText={setEName} />
                <DateField testID="lc-birth" title="DÁTUM NARODENIA" value={eBirth} onChange={setEBirth} placeholder="Dátum narodenia" style={styles.input} />
                <Text style={styles.idLabel}>KRVNÁ SKUPINA</Text>
                <View style={styles.bloodRow}>
                  {BLOOD.map(b => (
                    <Pressable key={b} testID={`lc-blood-${b}`} onPress={() => setEBlood(eBlood === b ? '' : b)} style={[styles.bloodChip, eBlood === b && { backgroundColor: C.brand, borderColor: C.brand }]}>
                      <Text style={[styles.bloodChipText, eBlood === b && { color: C.onInverse }]}>{b}</Text>
                    </Pressable>
                  ))}
                </View>
                <Pressable testID="lc-save-card" onPress={saveCard} disabled={cardBusy} style={styles.cta}>
                  {cardBusy ? <ActivityIndicator color={C.onInverse} /> : <Text style={styles.ctaText}>ULOŽIŤ ÚDAJE</Text>}
                </Pressable>
              </View>
            )}
          </View>
        )}

        {/* HLASOVÉ PRIDÁVANIE cez Jarvisa */}
        <Pressable testID="lc-voice-hint" onPress={() => router.push('/jarvis')} style={styles.voiceHint}>
          <Ionicons name="mic-outline" size={20} color={C.brand} />
          <Text style={styles.voiceHintText}>Povedzte Jarvisovi: „Dnes mi doktor povedal, že mám kiahne“ — zaradí to sem automaticky.</Text>
          <Ionicons name="chevron-forward" size={16} color={C.info} />
        </Pressable>

        {(data?.booster_alerts || []).length > 0 && (
          <View style={styles.alertBox}>
            <Ionicons name="alarm-outline" size={18} color={C.onWarn} />
            <View style={{ flex: 1 }}>
              <Text style={styles.alertTitle}>BLÍŽIACE SA PRESKOČKOVANIE</Text>
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
                  <Ionicons name={CATS[k].icon} size={13} color={cat === k ? C.onInverse : CATS[k].color} />
                  <Text style={[styles.catChipText, cat === k && { color: C.onInverse }]}>{CATS[k].label}</Text>
                </Pressable>
              ))}
            </View>
            <TextInput testID="ht-title" style={styles.input} placeholder={CATS[cat].hint} placeholderTextColor={C.info} value={title} onChangeText={setTitle} />
            <DateField testID="ht-date" title="DÁTUM" value={date} onChange={setDate} placeholder="Dátum" style={styles.input} />
            <TextInput testID="lc-notes" style={styles.input} placeholder="Popis (voliteľné)" placeholderTextColor={C.info} value={notes} onChangeText={setNotes} />
            {cat === 'vaccine' && (
              <DateField testID="ht-booster" title="BOOSTER DO" value={booster} onChange={setBooster} placeholder="Booster do (voliteľné)" style={styles.input} />
            )}
            <Pressable testID="ht-save" onPress={add} disabled={busy} style={styles.cta}>
              {busy ? <ActivityIndicator color={C.onInverse} /> : <Text style={styles.ctaText}>ULOŽIŤ ZÁZNAM</Text>}
            </Pressable>
          </View>
        )}

        {/* PREDIKCIE — Jarvis navrhne ďalšie očkovanie / kontrolu */}
        <View testID="lc-predictions" style={styles.predBox}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.sm }}>
            <Ionicons name="sparkles" size={16} color={C.brand} />
            <Text style={styles.predTitle}>PREDIKCIE · JARVIS</Text>
            <View style={{ flex: 1 }} />
            <Pressable testID="lc-predict" onPress={generatePredictions} disabled={predBusy} style={styles.predBtn}>
              {predBusy ? <ActivityIndicator size="small" color={C.onInverse} /> : <Text style={styles.predBtnText}>{predictions.length ? 'OBNOVIŤ' : 'NAVRHNÚŤ'}</Text>}
            </Pressable>
          </View>
          <Text style={styles.predSub}>Jarvis podľa histórie navrhne, kedy je ďalšie očkovanie alebo prehliadka.</Text>
          {!!predMsg && <Text testID="lc-pred-msg" style={styles.predMsg}>{predMsg}</Text>}
          {predictions.map((p: any, i: number) => {
            const ui = CATS[p.category] || CATS.exam;
            return (
              <View key={`${p.title}-${i}`} testID={`lc-pred-${i}`} style={styles.predCard}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.sm }}>
                  <Ionicons name={ui.icon} size={15} color={ui.color} />
                  <Text style={[styles.tlCat, { color: ui.color }]}>{ui.label} · {p.suggested_date}</Text>
                </View>
                <Text style={styles.predCardTitle}>{p.title}</Text>
                {!!p.reason && <Text style={styles.predReason}>{p.reason}</Text>}
                <Pressable testID={`lc-accept-${i}`} onPress={() => acceptPrediction(p)} disabled={accepting === p.title} style={styles.acceptBtn}>
                  {accepting === p.title ? <ActivityIndicator size="small" color={C.onInverse} /> : (
                    <>
                      <Ionicons name="calendar-outline" size={14} color={C.onInverse} />
                      <Text style={styles.acceptText}>PRIDAŤ DO KALENDÁRA</Text>
                    </>
                  )}
                </Pressable>
              </View>
            );
          })}
          {predictions.length > 0 && <Text style={styles.aiMark}>AI Content · Sovereign Protocol</Text>}
        </View>

        {/* FILTRE — 5 kategórií s počtami */}
        <View style={styles.filterRow}>
          <Pressable testID="ht-filter-all" onPress={() => setF('all')} style={[styles.fChip, filter === 'all' && { backgroundColor: C.brand, borderColor: C.brand }]}>
            <Text style={[styles.fChipText, filter === 'all' && { color: C.onInverse }]}>VŠETKO</Text>
          </Pressable>
          {CAT_KEYS.map(k => (
            <Pressable key={k} testID={`ht-filter-${k}`} onPress={() => setF(k)} style={[styles.fChip, filter === k && { backgroundColor: CATS[k].color, borderColor: CATS[k].color }]}>
              <Text style={[styles.fChipText, filter === k && { color: C.onInverse }]}>{CATS[k].plural}{counts[k] ? ` (${counts[k]})` : ''}</Text>
            </Pressable>
          ))}
        </View>

        {!data && <ActivityIndicator color={C.brand} style={{ marginTop: 40 }} />}
        {data && events.length === 0 && <Text style={styles.hint}>Žiadne záznamy. Pridajte prvý cez + alebo to povedzte Jarvisovi.</Text>}

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
                    <Ionicons name={ui.icon} size={16} color={ui.color} />
                    <Text style={[styles.tlCat, { color: ui.color }]}>{ui.label}{future ? ' · NADCHÁDZA' : ''}{e.source === 'voice' ? ' · 🎙 JARVIS' : e.source === 'jarvis' ? ' · ✨ PREDIKCIA' : ''}</Text>
                    <View style={{ flex: 1 }} />
                    <Pressable testID={`ht-del-${e.event_id}`} onPress={() => del(e.event_id)} hitSlop={8}>
                      <Ionicons name="trash-outline" size={15} color={C.info} />
                    </Pressable>
                  </View>
                  <Text style={styles.tlTitle}>{e.title}</Text>
                  <Text style={styles.tlDate}>{e.date}{e.booster_due ? ` · booster: ${e.booster_due}` : ''}{e.notes ? ` · ${e.notes}` : ''}</Text>
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
