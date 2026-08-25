/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, TextInput, ScrollView, Switch, ActivityIndicator, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { WheelField } from '@/src/ui/fields';
import JarvisAdvice from '@/src/JarvisAdvice';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';

const CURRENCIES = ['EUR', 'CZK', 'CRYPTO'];
const BURIALS = [
  { key: 'burial', label: 'POCHOVANIE' },
  { key: 'cremation', label: 'KREMÁCIA' },
  { key: 'natural', label: 'PRÍRODNÉ' },
];

export default function Dignity() {
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const router = useRouter();
  const [fund, setFund] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [amount, setAmount] = useState('25');
  const [currency, setCurrency] = useState('EUR');
  const [method, setMethod] = useState('card');
  const [plan, setPlan] = useState({ monthly_amount: '20', enabled: false });
  const [ben, setBen] = useState({ type: 'proxy', name: '', contact: '', iban: '' });
  const [wishes, setWishes] = useState({ burial_type: 'cremation', ceremony_music: '', guest_list: '', notes: '' });
  const [cert, setCert] = useState('');
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const f: any = await api('/dignity/fund');
      setFund(f);
      if (f.plan) setPlan({ monthly_amount: String(f.plan.monthly_amount), enabled: !!f.plan.enabled });
      if (f.beneficiary) setBen({ type: f.beneficiary.type || 'proxy', name: f.beneficiary.name || '', contact: f.beneficiary.contact || '', iban: f.beneficiary.iban || '' });
      if (f.wishes) setWishes({ burial_type: f.wishes.burial_type || 'cremation', ceremony_music: f.wishes.ceremony_music || '', guest_list: f.wishes.guest_list || '', notes: f.wishes.notes || '' });
    } catch (e) { console.log(e); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const deposit = async () => {
    setBusy(true); setMsg('');
    try {
      await api('/dignity/fund/deposit', { method: 'POST', body: JSON.stringify({ amount: parseFloat(amount) || 0, currency, method }) });
      load();
    } catch (e: any) { setMsg(String(e.message || e)); } finally { setBusy(false); }
  };
  const savePlan = async () => {
    await api('/dignity/fund/plan', { method: 'PUT', body: JSON.stringify({ monthly_amount: parseFloat(plan.monthly_amount) || 0, currency, enabled: plan.enabled }) });
    load();
  };
  const saveBen = async () => {
    await api('/dignity/beneficiary', { method: 'PUT', body: JSON.stringify(ben) });
    load();
  };
  const saveWishes = async () => {
    await api('/dignity/wishes', { method: 'PUT', body: JSON.stringify(wishes) });
    setMsg('✓ POSLEDNÉ PRIANIA ULOŽENÉ');
    load();
  };
  const verify = async () => {
    setMsg('');
    try {
      await api('/dignity/verify-death', { method: 'POST', body: JSON.stringify({ death_certificate_number: cert, registry_country: 'SK' }) });
      load();
    } catch (e: any) { setMsg(String(e.message || e)); }
  };
  const release = async () => {
    setMsg('');
    try {
      const r: any = await api('/dignity/release', { method: 'POST' });
      setMsg(`✓ UVOĽNENÉ ${r.amount} ${fund?.currency} → ${r.to?.name}`);
      load();
    } catch (e: any) { setMsg(String(e.message || e).includes('locked') ? '🔒 FOND JE UZAMKNUTÝ DO OVERENIA ÚMRTIA' : String(e.message || e)); }
  };

  const released = fund?.status === 'released';

  return (
    <SafeAreaView testID="dignity-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="dg-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={styles.title}>FINAL DIGNITY</Text>
        <View style={{ width: 26 }} />
      </View>
      <View style={styles.sub}><Text style={styles.subText}>POHREBNÝ FOND · DÔSTOJNOSŤ PRE KAŽDÉHO · ODBREMENÍ POZOSTALÝCH</Text></View>

      <ScrollView
        contentContainerStyle={{ padding: S.lg, paddingBottom: 60 }}
        keyboardShouldPersistTaps="handled"
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.fg} />}
      >
        {msg ? <Text style={styles.msg}>{msg}</Text> : null}

        {/* Fund balance */}
        <View style={[styles.fundCard, released && { borderColor: C.brand }]}>
          <View style={styles.lockRow}>
            <Ionicons name={released ? 'lock-open' : 'lock-closed'} size={18} color={released ? C.brand : C.error} />
            <Text style={[styles.lockText, { color: released ? C.brand : C.error }]}>
              {released ? 'UVOĽNENÉ' : fund?.death_verified ? 'OVERENÉ · PRIPRAVENÉ NA UVOĽNENIE' : 'UZAMKNUTÉ DO OVERENIA ÚMRTIA'}
            </Text>
          </View>
          <Text testID="dg-balance" style={styles.balance}>{(fund?.balance ?? 0).toFixed(0)}</Text>
          <Text style={styles.balanceCur}>{fund?.currency || 'EUR'} · POHREBNÝ FOND</Text>
          {released && fund?.released_to ? <Text style={styles.releasedTo}>→ {fund.released_to.name} ({fund.released_amount} {fund.currency})</Text> : null}
        </View>

        {!released && (
          <>
            {/* Deposit */}
            <Text style={styles.section}>VKLAD (MOCKED RAILS · REÁLNY AML LEDGER)</Text>
            <View style={{ flexDirection: 'row', gap: S.sm }}>
              {CURRENCIES.map(c => (
                <Pressable testID={`dg-cur-${c}`} key={c} onPress={() => setCurrency(c)} style={[styles.chip, currency === c && styles.chipActive]}>
                  <Text style={[styles.chipText, currency === c && styles.chipTextActive]}>{c}</Text>
                </Pressable>
              ))}
              {['card', 'crypto'].map(m => (
                <Pressable testID={`dg-method-${m}`} key={m} onPress={() => setMethod(m)} style={[styles.chip, method === m && styles.chipActive]}>
                  <Ionicons name={m === 'crypto' ? 'logo-bitcoin' : 'card-outline'} size={14} color={method === m ? C.onInverse : C.fg} />
                </Pressable>
              ))}
            </View>
            <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.sm }}>
              <WheelField testID="dg-amount" title="SUMA €" min={1} max={500} unit="€" value={amount} onChange={setAmount} placeholder="Suma €" style={[styles.input, { flex: 1 }]} />
              <Pressable testID="dg-deposit" onPress={deposit} disabled={busy} style={styles.priBtn}>
                {busy ? <ActivityIndicator color={C.onInverse} /> : <Text style={styles.priBtnText}>VLOŽIŤ</Text>}
              </Pressable>
            </View>

            {/* Recurring plan */}
            <Text style={styles.section}>AUTOMATICKÉ MESAČNÉ SPORENIE</Text>
            <View style={{ flexDirection: 'row', gap: S.sm, alignItems: 'center' }}>
              <WheelField testID="dg-plan-amount" title="MESAČNE €" min={5} max={500} step={5} unit="€" value={plan.monthly_amount} onChange={v => setPlan({ ...plan, monthly_amount: v })} placeholder="€/mes." style={[styles.input, { flex: 1 }]} />
              <Switch testID="dg-plan-enabled" value={plan.enabled} onValueChange={v => setPlan({ ...plan, enabled: v })} trackColor={{ true: C.brand, false: C.surface3 }} />
              <Pressable testID="dg-plan-save" onPress={savePlan} style={styles.priBtn}><Text style={styles.priBtnText}>{t('save', lang).toUpperCase()}</Text></Pressable>
            </View>
            <Text style={styles.hint}>Mesačne sa automaticky pripíše nastavená suma ({plan.monthly_amount || 0} {currency}/mes.).</Text>
          </>
        )}

        {/* Beneficiary */}
        <Text style={styles.section}>PRÍJEMCA PO UVOĽNENÍ</Text>
        <View style={{ flexDirection: 'row', gap: S.sm }}>
          {[{ k: 'proxy', l: 'SPLNOMOCNENEC' }, { k: 'funeral_director', l: 'POHREBNÁ SLUŽBA' }].map(o => (
            <Pressable testID={`dg-ben-${o.k}`} key={o.k} onPress={() => setBen({ ...ben, type: o.k })} style={[styles.chip, { flex: 1, alignItems: 'center' }, ben.type === o.k && styles.chipActive]}>
              <Text style={[styles.chipText, ben.type === o.k && styles.chipTextActive]}>{o.l}</Text>
            </Pressable>
          ))}
        </View>
        <TextInput testID="dg-ben-name" placeholder={ben.type === 'proxy' ? 'Tomáš Novák (auto zo splnomocnenia)' : 'Pohrebná služba, s.r.o.'} value={ben.name} onChangeText={v => setBen({ ...ben, name: v })} style={[styles.input, { marginTop: S.sm }]} placeholderTextColor="#999" />
        <TextInput testID="dg-ben-contact" placeholder="Kontakt / IBAN" value={ben.contact} onChangeText={v => setBen({ ...ben, contact: v })} style={[styles.input, { marginTop: S.sm }]} placeholderTextColor="#999" />
        <Pressable testID="dg-ben-save" onPress={saveBen} style={[styles.secBtn, { marginTop: S.sm }]}>
          <Text style={styles.secBtnText}>{t('save', lang).toUpperCase()}</Text>
        </Pressable>

        {/* Final wishes */}
        <Text style={styles.section}>POSLEDNÉ PRIANIA (FUNERAL DIRECTIVES)</Text>
        <View style={{ flexDirection: 'row', gap: S.sm }}>
          {BURIALS.map(b => (
            <Pressable testID={`dg-burial-${b.key}`} key={b.key} onPress={() => setWishes({ ...wishes, burial_type: b.key })} style={[styles.chip, { flex: 1, alignItems: 'center' }, wishes.burial_type === b.key && styles.chipActive]}>
              <Text style={[styles.chipText, wishes.burial_type === b.key && styles.chipTextActive]}>{b.label}</Text>
            </Pressable>
          ))}
        </View>
        <TextInput testID="dg-music" placeholder="Hudba na rozlúčke (Hallelujah…)" value={wishes.ceremony_music} onChangeText={v => setWishes({ ...wishes, ceremony_music: v })} style={[styles.input, { marginTop: S.sm }]} placeholderTextColor="#999" />
        <TextInput testID="dg-guests" placeholder="Koho pozvať (mená, kontakty)" value={wishes.guest_list} onChangeText={v => setWishes({ ...wishes, guest_list: v })} multiline style={[styles.input, { marginTop: S.sm, minHeight: 60 }]} placeholderTextColor="#999" />
        <TextInput testID="dg-notes" placeholder="Ďalšie priania" value={wishes.notes} onChangeText={v => setWishes({ ...wishes, notes: v })} multiline style={[styles.input, { marginTop: S.sm, minHeight: 60 }]} placeholderTextColor="#999" />
        <Pressable testID="dg-wishes-save" onPress={saveWishes} style={[styles.secBtn, { marginTop: S.sm }]}>
          <Text style={styles.secBtnText}>{t('save', lang).toUpperCase()}</Text>
        </Pressable>

        <JarvisAdvice module="dignity_fund" lang={lang} buildContext={() => `Funeral fund: balance ${fund?.balance ?? 0} ${fund?.currency}, monthly plan ${plan.enabled ? plan.monthly_amount : 'off'}, beneficiary ${ben.name || 'not set'}, wishes ${wishes.burial_type}. User wants dignity for those without heirs; advise on realistic funeral costs in Slovakia (~3000-5000 EUR) and savings pace.`} />

        {/* Death trigger */}
        {!released && (
          <>
            <Text style={styles.section}>PODMIENENÉ UVOĽNENIE (DEATH TRIGGER)</Text>
            <View style={styles.triggerBox}>
              <Text style={styles.triggerText}>
                Fond je uzamknutý a nedá sa minúť do úradného overenia úmrtia (štátny register — v MVP simulované číslom úmrtného listu). Po overení sa uvoľní priamo príjemcovi.
              </Text>
              {!fund?.death_verified ? (
                <>
                  <TextInput testID="dg-cert" placeholder="Číslo úmrtného listu (min. 6 znakov)" value={cert} onChangeText={setCert} style={[styles.input, { marginTop: S.sm }]} placeholderTextColor="#999" />
                  <Pressable testID="dg-verify" onPress={verify} disabled={cert.trim().length < 6} style={[styles.warnBtn, cert.trim().length < 6 && { opacity: 0.4 }]}>
                    <Ionicons name="shield-checkmark-outline" size={16} color={C.onWarn} />
                    <Text style={styles.warnBtnText}>OVERIŤ V REGISTRI (SIMULÁCIA)</Text>
                  </Pressable>
                </>
              ) : (
                <Pressable testID="dg-release" onPress={release} style={styles.releaseBtn}>
                  <Ionicons name="lock-open-outline" size={18} color={C.onInverse} />
                  <Text style={styles.releaseBtnText}>UVOĽNIŤ FOND PRÍJEMCOVI</Text>
                </Pressable>
              )}
            </View>
          </>
        )}

        {fund?.contributions?.length ? (
          <>
            <Text style={styles.section}>HISTÓRIA VKLADOV</Text>
            {fund.contributions.map((c: any) => (
              <View key={c.contribution_id} style={styles.contribRow}>
                <Ionicons name={c.method === 'recurring' ? 'repeat' : c.method === 'crypto' ? 'logo-bitcoin' : 'card-outline'} size={16} color={C.brand} />
                <Text style={styles.contribText}>+{c.amount} {c.currency} · {c.method.toUpperCase()} · {String(c.created_at).slice(0, 10)}</Text>
              </View>
            ))}
          </>
        ) : null}
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
  msg: { color: C.brand, fontWeight: '900', fontSize: 12, marginBottom: S.sm, letterSpacing: 0.5 },
  fundCard: { borderWidth: 2.5, borderColor: C.error, padding: S.lg, alignItems: 'center' },
  lockRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  lockText: { fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  balance: { fontSize: 56, fontWeight: '900', color: C.fg, marginTop: 4 },
  balanceCur: { fontSize: 11, letterSpacing: 2, color: C.onS3, fontWeight: '800' },
  releasedTo: { marginTop: S.sm, fontWeight: '900', color: C.brand, fontSize: 13 },
  section: { marginTop: S.xl, marginBottom: S.md, fontSize: 11, letterSpacing: 2, color: C.fg, fontWeight: '900' },
  chip: { paddingHorizontal: S.md, paddingVertical: 10, borderWidth: 1.5, borderColor: C.borderStrong },
  chipActive: { backgroundColor: C.inverse },
  chipText: { fontWeight: '800', color: C.fg, fontSize: 11, letterSpacing: 1 },
  chipTextActive: { color: C.onInverse },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 15, color: C.fg },
  priBtn: { backgroundColor: C.inverse, paddingHorizontal: S.lg, alignItems: 'center', justifyContent: 'center' },
  priBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  secBtn: { borderWidth: 2, borderColor: C.borderStrong, paddingVertical: S.md, alignItems: 'center' },
  secBtnText: { fontWeight: '900', letterSpacing: 1.5, fontSize: 12, color: C.fg },
  hint: { color: C.onS3, fontSize: 11, marginTop: 6, lineHeight: 15 },
  triggerBox: { borderWidth: 2, borderColor: C.error, padding: S.md },
  triggerText: { color: C.fg, fontSize: 12, lineHeight: 18 },
  warnBtn: { marginTop: S.sm, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.warn, paddingVertical: S.md },
  warnBtnText: { color: C.onWarn, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  releaseBtn: { marginTop: S.sm, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, paddingVertical: S.lg },
  releaseBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 13 },
  contribRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, borderWidth: 1, borderColor: C.border, padding: S.sm, marginBottom: 6 },
  contribText: { fontWeight: '700', color: C.fg, fontSize: 12 },
});
