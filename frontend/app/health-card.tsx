/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// HEALTH CARD HUB — every health document in one place: birth certificate, EU insurance card,
// medical records (uploaded · transcribed · OCR), insurance contracts & claims. Sub-tabs,
// expandable detail, "Scan Document" in every category (→ Agent Lens).
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, TextInput, ActivityIndicator, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';
import { useUserType } from '@/src/user-type';
import { tap, GoldButton } from '@/src/ui/glass';

type Tab = 'identity' | 'records' | 'insurance';
const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'identity', label: 'ID & CARDS', icon: 'id-card' },
  { id: 'records', label: 'RECORDS', icon: 'document-text' },
  { id: 'insurance', label: 'INSURANCE', icon: 'shield-checkmark' },
];

export default function HealthCard() {
  const router = useRouter();
  const { fs, clinician } = useUserType();
  const [tab, setTab] = useState<Tab>('identity');
  const [card, setCard] = useState<any>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [insNo, setInsNo] = useState('');
  const [insurer, setInsurer] = useState('');
  const [picker, setPicker] = useState<'birth_cert_doc_id' | 'eu_card_doc_id' | null>(null);

  const load = useCallback(async () => {
    try { const r: any = await api('/health-card'); setCard(r); setInsNo(r.insurance_number || ''); setInsurer(r.insurer || ''); } catch (e) { console.log(e); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const save = async (patch: any) => {
    setBusy(true);
    try { setCard(await api('/health-card', { method: 'PUT', body: JSON.stringify(patch) })); tap('success'); } catch (e) { console.log(e); tap('error'); }
    finally { setBusy(false); setPicker(null); }
  };
  const scan = (title: string) => { tap('medium'); router.push({ pathname: '/lens', params: { category: title } } as any); };

  const docs: any[] = card?.documents || [];
  const DocRow = ({ d }: { d: any }) => {
    const isOpen = open === d.doc_id;
    return (
      <Pressable testID={`hc-doc-${d.doc_id}`} onPress={() => { tap('light'); setOpen(isOpen ? null : d.doc_id); }} style={[st.row, isOpen && st.rowOpen]}>
        <View style={st.rowHead}>
          <Ionicons name={d.has_text ? 'document-text' : 'image'} size={20} color={C.brand} />
          <View style={{ flex: 1 }}>
            <Text style={[st.rowTitle, { fontSize: fs(14) }]} numberOfLines={isOpen ? 3 : 1}>{d.title || d.filename || 'Document'}</Text>
            <Text style={st.rowSub}>{(d.uploaded_at || '').slice(0, 10)} · {d.has_text ? 'OCR ✓' : 'not transcribed'}{d.has_translation ? ' · plain language ✓' : ''}</Text>
          </View>
          <Ionicons name={isOpen ? 'chevron-up' : 'chevron-down'} size={18} color={C.info} />
        </View>
        {isOpen && (
          <View style={st.detail}>
            {d.has_text ? <Text style={[st.detailText, { fontSize: fs(12) }]}>{d.extracted_text}</Text> : <Text style={st.detailText}>No text yet — run OCR in the Vault or re-scan with Lens.</Text>}
            {clinician && d.has_translation && <Text style={[st.detailText, { color: C.accent, marginTop: 6 }]}>{d.plain_language}</Text>}
            <View style={st.actions}>
              <Pressable onPress={() => router.push('/(tabs)/vault' as any)} style={st.smallBtn}><Text style={st.smallText}>OPEN IN VAULT</Text></Pressable>
              {picker && <Pressable testID={`hc-pick-${d.doc_id}`} onPress={() => save({ [picker]: d.doc_id })} style={[st.smallBtn, { borderColor: C.accent }]}><Text style={[st.smallText, { color: C.accent }]}>USE AS {picker === 'birth_cert_doc_id' ? 'BIRTH CERTIFICATE' : 'EU CARD'}</Text></Pressable>}
            </View>
          </View>
        )}
      </Pressable>
    );
  };

  const CardSlot = ({ title, icon, doc, field, extra }: { title: string; icon: string; doc: any; field: 'birth_cert_doc_id' | 'eu_card_doc_id'; extra?: React.ReactNode }) => (
    <View testID={`hc-slot-${field}`} style={st.slot}>
      <View style={st.rowHead}>
        <Ionicons name={icon as any} size={24} color={C.brand} />
        <Text style={[st.slotTitle, { fontSize: fs(15) }]}>{title}</Text>
        {doc ? <Ionicons name="checkmark-circle" size={20} color={C.accent} /> : <Text style={st.missing}>MISSING</Text>}
      </View>
      {doc ? <Text style={st.rowSub}>{doc.title || doc.filename} · {(doc.uploaded_at || '').slice(0, 10)}</Text> : <Text style={st.rowSub}>Scan the original or pick an existing document.</Text>}
      {extra}
      <View style={st.actions}>
        <Pressable testID={`hc-scan-${field}`} onPress={() => scan(title)} style={st.smallBtn}><Ionicons name="scan" size={12} color={C.brand} /><Text style={st.smallText}>SCAN DOCUMENT</Text></Pressable>
        <Pressable onPress={() => { tap('light'); setPicker(picker === field ? null : field); setTab('records'); }} style={st.smallBtn}><Text style={st.smallText}>PICK EXISTING</Text></Pressable>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={st.root} edges={['top']}>
      <View style={st.head}>
        <Pressable testID="hc-back" onPress={() => router.back()} hitSlop={10} style={st.back}><Ionicons name="chevron-back" size={22} color={C.brand} /></Pressable>
        <Text style={[st.title, { fontSize: fs(16) }]}>HEALTH CARD</Text>
        {busy && <ActivityIndicator color={C.brand} />}
      </View>
      <View style={st.tabs}>
        {TABS.map(t => (
          <Pressable key={t.id} testID={`hc-tab-${t.id}`} onPress={() => { tap('light'); setTab(t.id); }} style={[st.tab, tab === t.id && st.tabOn]}>
            <Ionicons name={t.icon as any} size={14} color={tab === t.id ? C.onInverse : C.brand} />
            <Text style={[st.tabText, tab === t.id && { color: C.onInverse }]}>{t.label}</Text>
          </Pressable>
        ))}
      </View>
      <ScrollView contentContainerStyle={st.body} refreshControl={<RefreshControl refreshing={false} onRefresh={load} tintColor={C.brand} />}>
        {!card && <ActivityIndicator color={C.brand} />}
        {card && tab === 'identity' && (
          <>
            <CardSlot title="Birth certificate" icon="ribbon" doc={card.birth_cert} field="birth_cert_doc_id" />
            <CardSlot title="EU health insurance card" icon="card" doc={card.eu_card} field="eu_card_doc_id" extra={
              <View style={{ gap: S.sm }}>
                <TextInput testID="hc-ins-no" value={insNo} onChangeText={setInsNo} placeholder="Insurance number" placeholderTextColor={C.info} style={st.input} />
                <TextInput testID="hc-insurer" value={insurer} onChangeText={setInsurer} placeholder="Insurer (e.g. VšZP, Dôvera, Union)" placeholderTextColor={C.info} style={st.input} />
                <GoldButton testID="hc-save-ins" title="SAVE" small onPress={() => save({ insurance_number: insNo, insurer })} disabled={busy} />
              </View>
            } />
          </>
        )}
        {card && tab === 'records' && (
          <>
            {picker && <Text style={st.pickHint}>Tap a document below → "USE AS …" to link it.</Text>}
            <View style={st.summary}>
              <Text style={st.sumNum}>{docs.length}</Text><Text style={st.sumLabel}>documents</Text>
              <Text style={st.sumNum}>{docs.filter(d => d.has_text).length}</Text><Text style={st.sumLabel}>transcribed (OCR)</Text>
            </View>
            <GoldButton testID="hc-scan-records" title="SCAN DOCUMENT" icon="scan" onPress={() => scan('Medical record')} />
            {docs.length === 0 && <Text style={st.rowSub}>No documents yet.</Text>}
            {docs.map(d => <DocRow key={d.doc_id} d={d} />)}
          </>
        )}
        {card && tab === 'insurance' && (
          <>
            <Text style={st.section}>CONTRACTS</Text>
            {(card.contracts || []).map((c: any, i: number) => (
              <Pressable key={i} testID={`hc-contract-${i}`} onPress={() => setOpen(open === `c${i}` ? null : `c${i}`)} style={[st.row, open === `c${i}` && st.rowOpen]}>
                <View style={st.rowHead}><Ionicons name="document-lock" size={20} color={C.brand} /><View style={{ flex: 1 }}><Text style={st.rowTitle}>{c.title}</Text><Text style={st.rowSub}>{c.insurer} · {c.number}</Text></View>
                  <Pressable onPress={() => save({ contracts: card.contracts.filter((_: any, j: number) => j !== i) })} hitSlop={8}><Ionicons name="trash" size={16} color={C.error} /></Pressable></View>
                {open === `c${i}` && <Text style={st.detailText}>Valid until: {c.valid_until || '—'}</Text>}
              </Pressable>
            ))}
            <ContractForm onAdd={(c) => save({ contracts: [...(card.contracts || []), c] })} />
            <Pressable testID="hc-scan-contract" onPress={() => scan('Insurance contract')} style={st.smallBtn}><Ionicons name="scan" size={12} color={C.brand} /><Text style={st.smallText}>SCAN CONTRACT</Text></Pressable>
            <Text style={st.section}>CLAIMS</Text>
            {(card.claims || []).length === 0 && <Text style={st.rowSub}>No insurance claims yet.</Text>}
            {(card.claims || []).map((k: any, i: number) => (
              <Pressable key={i} onPress={() => setOpen(open === `k${i}` ? null : `k${i}`)} style={[st.row, open === `k${i}` && st.rowOpen]}>
                <View style={st.rowHead}><Ionicons name="receipt" size={20} color={C.brand} /><View style={{ flex: 1 }}><Text style={st.rowTitle}>{k.title || k.type || 'Claim'}</Text><Text style={st.rowSub}>{k.status || ''} · {(k.created_at || '').slice(0, 10)}</Text></View></View>
                {open === `k${i}` && <Text style={st.detailText}>{k.summary || k.notes || JSON.stringify(k).slice(0, 400)}</Text>}
              </Pressable>
            ))}
            <GoldButton testID="hc-open-insurance" title="INSURANCE CENTRE (NEW CLAIM)" icon="shield-checkmark" onPress={() => router.push('/insurance')} />
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function ContractForm({ onAdd }: { onAdd: (c: any) => void }) {
  const [t, setT] = useState(''); const [ins, setIns] = useState(''); const [no, setNo] = useState(''); const [until, setUntil] = useState('');
  return (
    <View style={st.form}>
      <TextInput testID="hc-c-title" value={t} onChangeText={setT} placeholder="Contract title (e.g. Life insurance)" placeholderTextColor={C.info} style={st.input} />
      <View style={{ flexDirection: 'row', gap: S.sm }}>
        <TextInput value={ins} onChangeText={setIns} placeholder="Insurer" placeholderTextColor={C.info} style={[st.input, { flex: 1 }]} />
        <TextInput value={no} onChangeText={setNo} placeholder="Policy no." placeholderTextColor={C.info} style={[st.input, { flex: 1 }]} />
      </View>
      <TextInput value={until} onChangeText={setUntil} placeholder="Valid until (YYYY-MM-DD)" placeholderTextColor={C.info} style={st.input} />
      <GoldButton testID="hc-c-add" title="ADD CONTRACT" small disabled={!t.trim()} onPress={() => { onAdd({ title: t.trim(), insurer: ins, number: no, valid_until: until }); setT(''); setIns(''); setNo(''); setUntil(''); }} />
    </View>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  head: { flexDirection: 'row', alignItems: 'center', gap: S.sm, paddingHorizontal: S.md, minHeight: 52 },
  back: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  title: { color: C.brand, fontWeight: '900', letterSpacing: 3, flex: 1 },
  tabs: { flexDirection: 'row', gap: S.sm, paddingHorizontal: S.lg, paddingBottom: S.sm },
  tab: { flex: 1, flexDirection: 'row', gap: 6, alignItems: 'center', justifyContent: 'center', minHeight: 44, borderWidth: 1, borderColor: 'rgba(212,175,55,0.45)', borderRadius: R.sm },
  tabOn: { backgroundColor: C.brand, borderColor: C.brand },
  tabText: { color: C.brand, fontWeight: '900', fontSize: 10, letterSpacing: 1.2 },
  body: { padding: S.lg, gap: S.md, paddingBottom: S.xxxl },
  slot: { borderWidth: 1, borderColor: 'rgba(212,175,55,0.35)', borderRadius: R.md, padding: S.lg, gap: S.sm, backgroundColor: C.surface2 },
  slotTitle: { color: C.fg, fontWeight: '900', flex: 1 },
  missing: { color: C.warn, fontWeight: '900', fontSize: 10, letterSpacing: 1.5 },
  row: { borderWidth: 1, borderColor: C.border, borderRadius: R.sm, padding: S.md, gap: S.sm, backgroundColor: C.surface2 },
  rowOpen: { borderColor: 'rgba(212,175,55,0.5)' },
  rowHead: { flexDirection: 'row', alignItems: 'center', gap: S.md },
  rowTitle: { color: C.fg, fontWeight: '800' },
  rowSub: { color: C.info, fontSize: 11, marginTop: 2 },
  detail: { borderTopWidth: 1, borderTopColor: C.border, paddingTop: S.sm, gap: S.sm },
  detailText: { color: C.onS3, fontSize: 12, lineHeight: 18 },
  actions: { flexDirection: 'row', gap: S.sm, flexWrap: 'wrap' },
  smallBtn: { flexDirection: 'row', gap: 6, alignItems: 'center', minHeight: 40, paddingHorizontal: S.md, borderWidth: 1, borderColor: C.brand, borderRadius: R.pill },
  smallText: { color: C.brand, fontWeight: '900', fontSize: 10, letterSpacing: 1.2 },
  input: { minHeight: 46, color: C.fg, paddingHorizontal: S.md, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, backgroundColor: C.surface2 },
  pickHint: { color: C.accent, fontWeight: '800', fontSize: 12 },
  summary: { flexDirection: 'row', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' },
  sumNum: { color: C.brand, fontWeight: '900', fontSize: 26 },
  sumLabel: { color: C.info, fontSize: 12, marginRight: S.md },
  section: { color: C.brand, fontWeight: '900', letterSpacing: 2.5, fontSize: 11, marginTop: S.sm },
  form: { gap: S.sm, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, padding: S.md },
});
