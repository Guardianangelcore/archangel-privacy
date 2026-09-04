/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// PLANS & STORE — one simple surface: a card and a price in €. Subscriptions + family plans go
// through RevenueCat (App Store / Google Play); add-ons are one-tap purchases. Tokens stay hidden
// (Settings → Advanced → Blockchain & Tokens).
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, TextInput, ActivityIndicator, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, S, R } from '@/src/theme';
import { tap, GoldButton } from '@/src/ui/glass';
import { IapBuyButton, RestorePurchasesButton } from '@/src/IapPurchase';
import type { IapTier } from '@/src/revenuecat';

type Period = 'monthly' | 'annual';
const eur = (n: number) => `€${Number.isInteger(n) ? n : n.toFixed(2)}`;

export default function Store() {
  const router = useRouter();
  const { refresh } = useAuth() as any;
  const [tab, setTab] = useState<'plans' | 'addons'>('plans');
  const [period, setPeriod] = useState<Period>('monthly');
  const [cat, setCat] = useState<any>(null);
  const [promo, setPromo] = useState('');
  const [promoMsg, setPromoMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState('');

  const load = useCallback(async () => { try { setCat(await api('/store/catalog')); } catch (e) { console.log(e); } }, []);
  useEffect(() => { load(); }, [load]);

  const redeem = async () => {
    if (!promo.trim()) return;
    tap('medium'); setBusy('promo'); setPromoMsg(null);
    try {
      const r: any = await api('/store/promo', { method: 'POST', body: JSON.stringify({ code: promo.trim() }) });
      setPromoMsg({ ok: true, text: r.message }); setPromo(''); tap('success'); await refresh?.(); await load();
    } catch (e: any) { setPromoMsg({ ok: false, text: String(e.message || e).replace(/^\d+:\s*/, '') }); tap('error'); }
    finally { setBusy(null); }
  };
  const buyAddon = async (id: string, name: string) => {
    tap('medium'); setBusy(id); setMsg('');
    try {
      await api('/store/addon/buy', { method: 'POST', body: JSON.stringify({ addon_id: id }) });
      tap('success'); setMsg(`✓ ${name} is now active.`); await refresh?.(); await load();
    } catch (e: any) { setMsg(String(e.message || e).replace(/^\d+:\s*/, '')); tap('error'); }
    finally { setBusy(null); }
  };

  const PlanCard = ({ p, family }: { p: any; family?: boolean }) => {
    const price = period === 'monthly' ? p.price_eur : p.price_eur_year;
    const accent = p.accent || C.brand;
    return (
      <View testID={`plan-${p.id}`} style={[st.card, p.current && { borderColor: accent }]}>
        <View style={st.cardHead}>
          <View style={{ flex: 1 }}>
            <Text style={[st.planName, { color: accent }]}>{p.name.toUpperCase()}{family ? ` · ${p.seats} SEATS` : ''}</Text>
            <Text style={st.tagline}>{p.tagline}</Text>
          </View>
          <View style={{ alignItems: 'flex-end' }}>
            <Text style={st.price}>{eur(price)}</Text>
            <Text style={st.per}>{price === 0 ? 'forever' : period === 'monthly' ? '/ month' : '/ year'}</Text>
          </View>
        </View>
        {(p.features || []).slice(0, 5).map((f: string, i: number) => (
          <View key={i} style={st.feat}><Ionicons name="checkmark" size={14} color={accent} /><Text style={st.featText}>{f}</Text></View>
        ))}
        {p.current ? <Text testID={`plan-current-${p.id}`} style={[st.current, { color: accent }]}>✓ YOUR CURRENT PLAN</Text>
          : p.iap ? <IapBuyButton tier={p.id as IapTier} period={period} accent={accent} onSynced={() => { refresh?.(); load(); }} />
          : <Text style={st.per}>Free — the default for everyone.</Text>}
      </View>
    );
  };

  return (
    <SafeAreaView style={st.root} edges={['top']}>
      <View style={st.head}>
        <Pressable testID="store-back" onPress={() => router.back()} hitSlop={10} style={st.back}><Ionicons name="chevron-back" size={22} color={C.brand} /></Pressable>
        <Text style={st.title}>PLANS & STORE</Text>
      </View>
      <View style={st.tabs}>
        <Pressable testID="store-tab-plans" onPress={() => setTab('plans')} style={[st.tab, tab === 'plans' && st.tabOn]}><Text style={[st.tabText, tab === 'plans' && { color: C.onInverse }]}>PLANS</Text></Pressable>
        <Pressable testID="store-tab-addons" onPress={() => setTab('addons')} style={[st.tab, tab === 'addons' && st.tabOn]}><Text style={[st.tabText, tab === 'addons' && { color: C.onInverse }]}>ADD-ONS</Text></Pressable>
      </View>
      <ScrollView contentContainerStyle={st.body} refreshControl={<RefreshControl refreshing={false} onRefresh={load} tintColor={C.brand} />}>
        {!cat && <ActivityIndicator color={C.brand} />}
        {cat && tab === 'plans' && (
          <>
            <View style={st.period}>
              <Pressable testID="period-monthly" onPress={() => setPeriod('monthly')} style={[st.pBtn, period === 'monthly' && st.pOn]}><Text style={[st.pText, period === 'monthly' && { color: C.onInverse }]}>MONTHLY</Text></Pressable>
              <Pressable testID="period-annual" onPress={() => setPeriod('annual')} style={[st.pBtn, period === 'annual' && st.pOn]}><Text style={[st.pText, period === 'annual' && { color: C.onInverse }]}>YEARLY · 2 MONTHS FREE</Text></Pressable>
            </View>
            {cat.tiers.map((p: any) => <PlanCard key={p.id} p={p} />)}
            <Text style={st.section}>FAMILY PLANS</Text>
            {cat.family.map((p: any) => <PlanCard key={p.id} p={p} family />)}
            <Text style={st.section}>PROMO CODE</Text>
            <View style={st.promoRow}>
              <TextInput testID="promo-input" value={promo} onChangeText={setPromo} placeholder="Enter code" placeholderTextColor={C.info} autoCapitalize="characters" style={st.input} onSubmitEditing={redeem} />
              <GoldButton testID="promo-apply" title="APPLY" small onPress={redeem} loading={busy === 'promo'} disabled={!promo.trim()} />
            </View>
            {promoMsg && <Text testID="promo-msg" style={[st.msg, { color: promoMsg.ok ? C.accent : C.error }]}>{promoMsg.text}</Text>}
            <RestorePurchasesButton onSynced={() => { refresh?.(); load(); }} />
          </>
        )}
        {cat && tab === 'addons' && (
          <>
            <Text style={st.section}>ONE-TIME UNLOCKS</Text>
            {cat.addons.filter((a: any) => a.kind === 'one_time').map((a: any) => <AddonRow key={a.id} a={a} busy={busy} onBuy={buyAddon} />)}
            <Text style={st.section}>MONTHLY BOOSTS</Text>
            {cat.addons.filter((a: any) => a.kind === 'recurring').map((a: any) => <AddonRow key={a.id} a={a} busy={busy} onBuy={buyAddon} />)}
            {!!msg && <Text testID="addon-msg" style={[st.msg, { color: msg.startsWith('✓') ? C.accent : C.error }]}>{msg}</Text>}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function AddonRow({ a, busy, onBuy }: { a: any; busy: string | null; onBuy: (id: string, name: string) => void }) {
  return (
    <View testID={`addon-${a.id}`} style={st.addon}>
      <View style={{ flex: 1 }}>
        <Text style={st.addonName}>{a.name}</Text>
        <Text style={st.addonDesc}>{a.desc}</Text>
        {a.owned && a.until && <Text style={st.until}>Active until {String(a.until).slice(0, 10)}</Text>}
      </View>
      {a.owned && a.kind === 'one_time' ? <Text style={st.owned}>✓ OWNED</Text> : (
        <Pressable testID={`addon-buy-${a.id}`} onPress={() => onBuy(a.id, a.name)} disabled={!!busy} style={st.buy}>
          {busy === a.id ? <ActivityIndicator color={C.onInverse} /> : <Text style={st.buyText}>{a.price_gat} GA-T{a.kind === 'recurring' ? '/mo' : ''}</Text>}
        </Pressable>
      )}
    </View>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  head: { flexDirection: 'row', alignItems: 'center', gap: S.sm, paddingHorizontal: S.md, minHeight: 52 },
  back: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  title: { color: C.brand, fontWeight: '900', letterSpacing: 3, fontSize: 16 },
  tabs: { flexDirection: 'row', gap: S.sm, paddingHorizontal: S.lg, paddingBottom: S.sm },
  tab: { flex: 1, minHeight: 44, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: 'rgba(212,175,55,0.45)', borderRadius: R.sm },
  tabOn: { backgroundColor: C.brand, borderColor: C.brand },
  tabText: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 1.5 },
  body: { padding: S.lg, gap: S.md, paddingBottom: S.xxxl },
  period: { flexDirection: 'row', gap: S.sm },
  pBtn: { flex: 1, minHeight: 40, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: C.border, borderRadius: R.pill },
  pOn: { backgroundColor: C.brand, borderColor: C.brand },
  pText: { color: C.info, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  card: { borderWidth: 1, borderColor: C.border, borderRadius: R.md, padding: S.lg, gap: S.sm, backgroundColor: C.surface2 },
  cardHead: { flexDirection: 'row', gap: S.md, alignItems: 'flex-start' },
  planName: { fontWeight: '900', letterSpacing: 2, fontSize: 13 },
  tagline: { color: C.info, fontSize: 12, marginTop: 2 },
  price: { color: C.fg, fontWeight: '900', fontSize: 22 },
  per: { color: C.info, fontSize: 10 },
  feat: { flexDirection: 'row', gap: 8, alignItems: 'center' },
  featText: { color: C.onS3, fontSize: 12, flex: 1 },
  current: { fontWeight: '900', letterSpacing: 1.5, fontSize: 11, marginTop: S.xs },
  section: { color: C.brand, fontWeight: '900', letterSpacing: 2.5, fontSize: 11, marginTop: S.sm },
  promoRow: { flexDirection: 'row', gap: S.sm, alignItems: 'center' },
  input: { flex: 1, minHeight: 46, color: C.fg, paddingHorizontal: S.md, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, backgroundColor: C.surface2, letterSpacing: 1 },
  msg: { fontWeight: '800', fontSize: 12, lineHeight: 18 },
  addon: { flexDirection: 'row', alignItems: 'center', gap: S.md, padding: S.md, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, backgroundColor: C.surface2 },
  addonName: { color: C.fg, fontWeight: '900', fontSize: 13 },
  addonDesc: { color: C.info, fontSize: 11, marginTop: 2, lineHeight: 16 },
  until: { color: C.accent, fontSize: 10, marginTop: 4, fontWeight: '800' },
  owned: { color: C.accent, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  buy: { minHeight: 44, minWidth: 84, paddingHorizontal: S.md, backgroundColor: C.brand, borderRadius: R.pill, alignItems: 'center', justifyContent: 'center' },
  buyText: { color: C.onInverse, fontWeight: '900', fontSize: 13 },
});
