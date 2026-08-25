/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, useLocalSearchParams } from 'expo-router';
import * as Haptics from 'expo-haptics';
import * as WebBrowser from 'expo-web-browser';
import * as Linking from 'expo-linking';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';

const TIER_ICON: Record<string, string> = { sovereign: 'earth', guardian: 'shield-checkmark', sentinel: 'diamond', archangel: 'flame' };
const OBSIDIAN = '#0B0B0D';
const PLATINUM = '#E5E4E2';

export default function Subscription() {
  const router = useRouter();
  const params = useLocalSearchParams<{ session_id?: string; payment?: string }>();
  const [data, setData] = useState<any>(null);
  const [annual, setAnnual] = useState(false);
  const [founder, setFounder] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const polledRef = useRef(false);

  const load = useCallback(async () => {
    try {
      setData(await api('/subscription'));
      try { setFounder(await api('/wealth/founder-dashboard')); } catch { setFounder(null); }
    } catch (e: any) { setErr(String(e.message || e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  // Poll Stripe payment status until paid (also used after web redirect back)
  const pollPayment = useCallback(async (sid: string) => {
    setMsg('⏳ Overujem platbu kartou…'); setErr('');
    for (let i = 0; i < 12; i++) {
      try {
        const s: any = await api(`/billing/status/${sid}`);
        if (s.payment_status === 'paid') {
          setMsg(`✓ Platba prijatá — ${String(s.tier).toUpperCase()} je aktívny! Prémiové funkcie sú odomknuté.`);
          await load();
          return;
        }
        if (s.status === 'expired') { setErr('Platobná relácia expirovala — skúste znova.'); setMsg(''); return; }
      } catch {}
      await new Promise(r => setTimeout(r, 2000));
    }
    setMsg(''); setErr('Platba sa ešte spracováva — o chvíľu obnovte túto obrazovku.');
  }, [load]);

  // Web redirect back from Stripe Checkout: /subscription?session_id=...
  useEffect(() => {
    if (polledRef.current) return;
    if (params.session_id) { polledRef.current = true; pollPayment(String(params.session_id)); }
    else if (params.payment === 'cancelled') { polledRef.current = true; setErr('Platba bola zrušená — nič nebolo účtované.'); }
  }, [params.session_id, params.payment, pollPayment]);

  const cardCheckout = async (tier: string) => {
    if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
    setBusy(`${tier}-card`); setErr(''); setMsg('');
    try {
      const origin = Platform.OS === 'web' && typeof window !== 'undefined'
        ? window.location.origin
        : (process.env.EXPO_PUBLIC_BACKEND_URL || '');
      const r: any = await api('/billing/checkout', {
        method: 'POST',
        body: JSON.stringify({ tier, billing: annual ? 'annual' : 'monthly', origin_url: origin }),
      });
      if (Platform.OS === 'web' && typeof window !== 'undefined') {
        window.location.assign(r.checkout_url); // same-tab → Stripe → redirect back with session_id
        return;
      }
      await WebBrowser.openAuthSessionAsync(r.checkout_url, Linking.createURL('/subscription'));
      await pollPayment(r.session_id);
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const upgrade = async (tier: string, method: 'gat' | 'card') => {
    if (method === 'card') { await cardCheckout(tier); return; }
    if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
    setBusy(`${tier}-${method}`); setErr(''); setMsg('');
    try {
      const r: any = await api('/subscription/upgrade', { method: 'POST', body: JSON.stringify({ tier, method, billing: annual ? 'annual' : 'monthly' }) });
      setMsg(`Vitajte v ${tier.toUpperCase()} ✓ (${annual ? 'ročne −20 %' : 'mesačne'}, zaplatené GA-T, spálené ${r.burned}). Platí do ${String(r.effect?.tier_until || '').slice(0, 10)}.`);
      await load();
    } catch (e: any) {
      const m = String(e.message || e);
      if (m.includes('insufficient_balance')) setErr('Nedostatok GA-T — zarobte tokeny cez Proof-of-Help (Family Shield / Angel Gigs), zaplaťte kartou alebo skúste 7-dňový Sentinel trial.');
      else setErr(m);
    } finally { setBusy(null); }
  };

  const trial = async () => {
    setBusy('trial'); setErr(''); setMsg('');
    try {
      const r: any = await api('/subscription/trial', { method: 'POST' });
      setMsg(`🎁 SENTINEL TRIAL AKTÍVNY do ${String(r.tier_until).slice(0, 10)} — satelit, Bio-Scanner, Tactical Medic aj Longevity odomknuté.`);
      await load();
    } catch (e: any) { setErr(String(e.message || e).replace('trial_used:', '').replace('already_premium:', '').trim()); }
    finally { setBusy(null); }
  };

  const order: string[] = ['sovereign', 'guardian', 'sentinel', 'archangel'];
  const premium = (k: string) => k === 'sentinel' || k === 'archangel';

  return (
    <SafeAreaView testID="subscription-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="sb-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>SUBSCRIPTION & WEALTH</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }}>
        <Text style={styles.h1}>Štyri úrovne suverenity</Text>
        <Text style={styles.sub}>EUR · CZK · GA-T. Mesačne alebo ročne so zľavou −20 % („Secure Your Future“). Platba kartou (Stripe) alebo GA-T tokenmi.</Text>
        {data && (
          <View style={styles.currentBox}>
            <Ionicons name={(TIER_ICON[data.tier] || 'earth') as any} size={18} color={(data.tiers[data.tier] || {}).accent || '#5FA779'} />
            <Text testID="sb-current" style={styles.currentText}>AKTUÁLNY TIER: {data.tier.toUpperCase()}{data.tier_until ? ` · do ${String(data.tier_until).slice(0, 10)}` : ''}</Text>
            <Text style={styles.gat}>💎 {Number(data.gat_balance).toFixed(0)} GA-T</Text>
          </View>
        )}

        {data?.trial_available && (
          <Pressable testID="sb-trial" onPress={trial} disabled={busy === 'trial'} style={styles.trialBtn}>
            {busy === 'trial' ? <ActivityIndicator color={OBSIDIAN} /> : <Text style={styles.trialText}>🎁 7-DŇOVÝ SENTINEL TRIAL ZADARMO</Text>}
          </Pressable>
        )}

        <View style={styles.billingRow}>
          <Pressable testID="sb-monthly" onPress={() => setAnnual(false)} style={[styles.billBtn, !annual && styles.billBtnActive]}>
            <Text style={[styles.billText, !annual && styles.billTextActive]}>MESAČNE</Text>
          </Pressable>
          <Pressable testID="sb-annual" onPress={() => setAnnual(true)} style={[styles.billBtn, annual && styles.billBtnActive]}>
            <Text style={[styles.billText, annual && styles.billTextActive]}>ROČNE −20 % · SECURE YOUR FUTURE</Text>
          </Pressable>
        </View>

        {!!msg && <Text style={styles.info}>{msg}</Text>}
        {!!err && <Text style={styles.err}>{err}</Text>}

        {data && order.map(k => {
          const t2 = data.tiers[k];
          const active = data.tier === k;
          const accent = t2.accent || '#5FA779';
          const eur = annual ? t2.price_eur_year : t2.price_eur;
          const czk = annual ? t2.price_czk_year : t2.price_czk;
          const gat = annual ? t2.price_gat_year : t2.price_gat;
          const per = annual ? '/rok' : '/mes.';
          return (
            <View key={k} style={[styles.tierCard, { borderColor: accent }, premium(k) && { backgroundColor: OBSIDIAN, borderWidth: 2.5 }, active && { borderStyle: 'solid', borderWidth: 3 }]}>
              {premium(k) && <Text style={[styles.vipRibbon, { color: accent }]}>{k === 'archangel' ? '👑 ELITE SOVEREIGNTY' : '🛰️ VIP SURVIVAL'}</Text>}
              <View style={styles.tierHead}>
                <Ionicons name={TIER_ICON[k] as any} size={24} color={accent} />
                <View style={{ flex: 1 }}>
                  <Text style={[styles.tierName, premium(k) && { color: PLATINUM }]}>{t2.name.toUpperCase()}{active ? '  ✓ AKTÍVNY' : ''}</Text>
                  <Text style={styles.tierTagline}>{t2.tagline}</Text>
                </View>
                <View style={{ alignItems: 'flex-end' }}>
                  <Text style={[styles.tierPrice, premium(k) && { color: PLATINUM }]}>{eur === 0 ? 'ZADARMO' : `${eur} €${per}`}</Text>
                  {gat > 0 && <Text style={styles.tierGat}>{czk} Kč · {gat} GA-T</Text>}
                </View>
              </View>
              {t2.features.map((f: string, i: number) => (
                <View key={i} style={styles.featRow}>
                  <Ionicons name="checkmark" size={14} color={accent} />
                  <Text style={[styles.featText, premium(k) && { color: '#B9B9C0' }]}>{f}</Text>
                </View>
              ))}
              {k !== 'sovereign' && !active && (
                <View style={styles.btnRow}>
                  <Pressable testID={`sb-upgrade-${k}-gat`} onPress={() => upgrade(k, 'gat')} disabled={!!busy} style={[styles.payBtn, { backgroundColor: accent }]}>
                    {busy === `${k}-gat` ? <ActivityIndicator size="small" color={OBSIDIAN} /> : <Text style={[styles.payText, premium(k) && { color: OBSIDIAN }]}>ZAPLATIŤ {gat} GA-T</Text>}
                  </Pressable>
                  <Pressable testID={`sb-upgrade-${k}-card`} onPress={() => upgrade(k, 'card')} disabled={!!busy} style={[styles.cardBtn, { borderColor: accent }]}>
                    {busy === `${k}-card` ? <ActivityIndicator size="small" color={accent} /> : (
                      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                        <Ionicons name="card-outline" size={14} color={accent} />
                        <Text style={[styles.cardText, { color: accent }]}>KARTOU {eur} €</Text>
                      </View>
                    )}
                  </Pressable>
                </View>
              )}
            </View>
          );
        })}

        {data && (
          <Text style={styles.ppu}>PAY-PER-USE: Bio-Scanner {data.payperuse?.bioscan_single} GA-T/sken · IPS export {data.payperuse?.ips_export_single} GA-T · Human Second Opinion podľa sadzby špecialistu (GA-T)</Text>
        )}

        {founder && (
          <View testID="sb-founder" style={styles.founderBox}>
            <Text style={styles.founderTitle}>👁 FOUNDER ADMIN · WEALTH ENGINE {founder.wealth_engine?.startsWith('SECURED') ? 'SECURED ✓' : ''}</Text>
            <View style={styles.founderGrid}>
              <View style={styles.founderCell}><Text style={styles.founderVal}>{founder.mrr_eur} €</Text><Text style={styles.founderLbl}>MRR</Text></View>
              <View style={styles.founderCell}><Text style={styles.founderVal}>{founder.acv_eur} €</Text><Text style={styles.founderLbl}>ACV</Text></View>
              <View style={styles.founderCell}><Text style={styles.founderVal}>{(founder.revenue_by_kind?.guardian_tax || 0).toFixed(0)} €</Text><Text style={styles.founderLbl}>GUARDIAN TAX 15%</Text></View>
              <View style={styles.founderCell}><Text style={styles.founderVal}>{(founder.revenue_by_kind?.payperuse || 0).toFixed(0)} €</Text><Text style={styles.founderLbl}>PAY-PER-USE</Text></View>
            </View>
            <Text style={styles.founderMeta}>Tiery: {Object.entries(founder.tier_distribution || {}).map(([k, v]) => `${k}:${v}`).join(' · ') || '—'} · GA-T treasury: {Number(founder.gat_treasury).toFixed(0)} · burned: {Number(founder.gat_burned).toFixed(1)}</Text>
          </View>
        )}

        <Text style={styles.disclaimer}>{data?.billing_note || ''}</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 2, fontSize: 13 },
  h1: { fontSize: 24, fontWeight: '900', color: C.fg },
  sub: { marginTop: S.sm, fontSize: 12.5, color: C.onS3, lineHeight: 18 },
  currentBox: { flexDirection: 'row', alignItems: 'center', gap: S.sm, backgroundColor: C.surface2, borderRadius: R.sm, padding: S.md, marginTop: S.lg },
  currentText: { flex: 1, color: C.fg, fontWeight: '900', fontSize: 11, letterSpacing: 0.5 },
  gat: { color: '#B8860B', fontWeight: '800', fontSize: 11 },
  trialBtn: { marginTop: S.md, backgroundColor: PLATINUM, minHeight: 52, alignItems: 'center', justifyContent: 'center' },
  trialText: { color: OBSIDIAN, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
  billingRow: { flexDirection: 'row', marginTop: S.md, borderWidth: 1.5, borderColor: C.borderStrong },
  billBtn: { flex: 1, paddingVertical: S.md, alignItems: 'center', minHeight: 44, justifyContent: 'center' },
  billBtnActive: { backgroundColor: C.inverse },
  billText: { fontWeight: '900', fontSize: 9.5, letterSpacing: 0.8, color: C.fg },
  billTextActive: { color: C.onInverse },
  tierCard: { borderWidth: 2, borderRadius: R.md, padding: S.md, marginTop: S.md, backgroundColor: C.surface2 },
  vipRibbon: { fontSize: 9, fontWeight: '900', letterSpacing: 2, marginBottom: S.sm },
  tierHead: { flexDirection: 'row', alignItems: 'center', gap: S.md, marginBottom: S.sm },
  tierName: { color: C.fg, fontWeight: '900', fontSize: 15, letterSpacing: 1 },
  tierTagline: { color: C.info, fontSize: 10.5, marginTop: 2 },
  tierPrice: { color: C.fg, fontWeight: '900', fontSize: 14 },
  tierGat: { color: '#B8860B', fontSize: 10, fontWeight: '700', marginTop: 2 },
  featRow: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 3 },
  featText: { flex: 1, color: C.onS3, fontSize: 11.5 },
  btnRow: { flexDirection: 'row', gap: S.sm, marginTop: S.md },
  payBtn: { flex: 1, borderRadius: R.sm, minHeight: 48, alignItems: 'center', justifyContent: 'center' },
  payText: { color: C.onInverse, fontWeight: '900', fontSize: 11 },
  cardBtn: { flex: 1, borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.sm, minHeight: 48, alignItems: 'center', justifyContent: 'center' },
  cardText: { color: C.info, fontWeight: '900', fontSize: 10 },
  ppu: { marginTop: S.lg, color: '#B8860B', fontSize: 10.5, lineHeight: 16, fontWeight: '800' },
  founderBox: { marginTop: S.lg, borderWidth: 2, borderColor: '#B8860B', padding: S.md, backgroundColor: OBSIDIAN },
  founderTitle: { color: '#B8860B', fontWeight: '900', fontSize: 10, letterSpacing: 1.5 },
  founderGrid: { flexDirection: 'row', flexWrap: 'wrap', marginTop: S.sm },
  founderCell: { width: '50%', paddingVertical: S.sm, alignItems: 'center' },
  founderVal: { color: PLATINUM, fontWeight: '900', fontSize: 18 },
  founderLbl: { color: '#8A8A93', fontSize: 8.5, letterSpacing: 1.5, fontWeight: '800', marginTop: 2 },
  founderMeta: { color: '#8A8A93', fontSize: 9.5, marginTop: S.sm, lineHeight: 14 },
  info: { color: '#5FA779', marginTop: S.md, fontSize: 12, lineHeight: 17 },
  err: { color: C.error, marginTop: S.md, fontSize: 12, lineHeight: 16 },
  disclaimer: { marginTop: S.xl, color: C.info, fontSize: 10, lineHeight: 15, textAlign: 'center' },
});
