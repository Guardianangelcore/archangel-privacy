/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator, Platform, TextInput } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter, useLocalSearchParams } from 'expo-router';
import * as Haptics from 'expo-haptics';
import * as WebBrowser from 'expo-web-browser';
import * as Linking from 'expo-linking';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';
import { IapBuyButton, RestorePurchasesButton } from '@/src/IapPurchase';
import { useI18n } from '@/src/i18n-context';
import { startDemoMode } from '@/src/DemoMode';   // DEMO_ONLY
import { startJudgeTour } from '@/src/judge-tour';   // DEMO_ONLY
import { useAuth } from '@/src/auth';

const TIER_ICON: Record<string, string> = { sovereign: 'earth', guardian: 'shield-checkmark', sentinel: 'diamond', archangel: 'flame' };
const OBSIDIAN = '#0B0B0D';
const PLATINUM = '#E5E4E2';

export default function Subscription() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const params = useLocalSearchParams<{ session_id?: string; payment?: string }>();
  const [data, setData] = useState<any>(null);
  const [annual, setAnnual] = useState(false);
  const [founder, setFounder] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [txs, setTxs] = useState<any[]>([]);
  const [cancelConfirm, setCancelConfirm] = useState(false);
  const [gifts, setGifts] = useState<any[]>([]);
  const [giftEmail, setGiftEmail] = useState('');
  const [giftTier, setGiftTier] = useState<'guardian' | 'sentinel' | 'archangel'>('sentinel');
  const [giftDays, setGiftDays] = useState(30);
  const polledRef = useRef(false);

  const { refresh } = useAuth();
  const load = useCallback(async () => {
    try {
      setData(await api('/subscription'));
      try { setTxs(await api('/billing/transactions')); } catch {}
      try {
        setFounder(await api('/wealth/founder-dashboard'));
        try { setGifts(await api('/billing/gifts')); } catch {}
      } catch { setFounder(null); }
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
          const label = String(s.tier) === 'family_sentinel' ? 'SENTINEL (FAMILY PLAN)' : String(s.tier).toUpperCase();
          setMsg(`✓ Payment received — ${label} is active! Premium features unlocked. 🧾 The receipt was saved to your Vault.`);
          await load();
          return;
        }
        if (s.status === 'expired') { setErr('Payment session expired — try again.'); setMsg(''); return; }
      } catch {}
      await new Promise(r => setTimeout(r, 2000));
    }
    setMsg(''); setErr('Payment is still processing — refresh this screen in a moment.');
  }, [load]);

  // Web redirect back from Stripe Checkout: /subscription?session_id=...
  useEffect(() => {
    if (polledRef.current) return;
    if (params.session_id) { polledRef.current = true; pollPayment(String(params.session_id)); }
    else if (params.payment === 'cancelled') { polledRef.current = true; setErr('Payment cancelled — nothing was charged.'); }
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
      setMsg(`Welcome to ${tier.toUpperCase()} ✓ (${annual ? 'yearly −20%' : 'monthly'}, paid in GA-T, burned ${r.burned}). Valid until ${String(r.effect?.tier_until || '').slice(0, 10)}.`);
      await load();
    } catch (e: any) {
      const m = String(e.message || e);
      if (m.includes('insufficient_balance')) setErr('Insufficient GA-T — earn tokens via Proof-of-Help (Family Shield / Angel Gigs), pay by card, or try the 7-day Sentinel trial.');
      else setErr(m);
    } finally { setBusy(null); }
  };

  const cancelSub = async () => {
    setBusy('cancel'); setErr(''); setMsg('');
    try {
      const r: any = await api('/subscription/cancel', { method: 'POST' });
      setMsg(r.message || 'Subscription cancelled.');
      setCancelConfirm(false);
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const sendGift = async () => {
    if (!giftEmail.trim()) return;
    setBusy('gift'); setErr(''); setMsg('');
    try {
      const r: any = await api('/billing/gift', { method: 'POST', body: JSON.stringify({ email: giftEmail.trim(), tier: giftTier, days: giftDays }) });
      setMsg(`🎁 Gifted: ${giftTier.toUpperCase()} for ${giftDays} days to ${r.gift.to_email}.`);
      setGiftEmail('');
      try { setGifts(await api('/billing/gifts')); } catch {}
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  // DEMO_ONLY — judges: 30-minute full-access session, no payment
  const demoStart = async () => { setBusy('demo'); await startDemoMode(refresh); await load(); setBusy(null); };
  const trial = async () => {
    setBusy('trial'); setErr(''); setMsg('');
    try {
      const r: any = await api('/subscription/trial', { method: 'POST' });
      setMsg(`🎁 SENTINEL TRIAL ACTIVE until ${String(r.tier_until).slice(0, 10)} — satellite, Bio-Scanner, Tactical Medic and Longevity unlocked.`);
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
        <Text style={styles.title}>{tt('subscription.subscription_wealth')}</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }}>
        <Text style={styles.h1}>{tt('subscription.four_levels_of_sovereignty')}</Text>
        <Text style={styles.sub}>{tt('subscription.eur_czk_ga_t_monthly_or_yearly_secur')}</Text>
        {data && (
          <View style={styles.currentBox}>
            <Ionicons name={(TIER_ICON[data.tier] || 'earth') as any} size={18} color={(data.tiers[data.tier] || {}).accent || '#5FA779'} />
            <Text testID="sb-current" style={styles.currentText}>{tt('subscription.current_tier')} {data.tier.toUpperCase()}{data.tier_until ? tt('subscription.until', [String(data.tier_until).slice(0, 10)]) : ''}</Text>
            <Text style={styles.gat}>💎 {Number(data.gat_balance).toFixed(0)} GA-T</Text>
          </View>
        )}
        {/* LOYALTY LOOP — paid plan → automatic monthly GA-T allocation */}
        {data?.gat_allocation && (
          <Text testID="sb-loyalty" style={styles.loyalty}>
            {data.gat_allocation.eligible
              ? tt('subscription.loyalty_ga_t_on_month_s_collected_bo', [Number(data.gat_allocation.next_amount).toFixed(0), String(data.gat_allocation.next_at || '').slice(0, 10), data.gat_allocation.months_collected, data.gat_allocation.next_bonus_pct])
              : tt('subscription.every_paid_plan_credits_ga_t_automat', [data.gat_monthly_by_tier?.guardian ?? 100, data.gat_monthly_by_tier?.sentinel ?? 300, data.gat_monthly_by_tier?.archangel ?? 1000])}
          </Text>
        )}

        {data?.trial_available && (
          <Pressable testID="sb-trial" onPress={trial} disabled={busy === 'trial'} style={styles.trialBtn}>
            {busy === 'trial' ? <ActivityIndicator color={OBSIDIAN} /> : <Text style={styles.trialText}>{tt('subscription.free_7_day_sentinel_trial')}</Text>}
          </Pressable>
        )}
        {/* DEMO_ONLY — competition judges */}
        <Pressable testID="sb-judge-tour" onPress={() => startJudgeTour(refresh)} style={[styles.demoBtn, { backgroundColor: '#FFD60A', borderStyle: 'solid' }]}>
          <Ionicons name="play-circle" size={16} color="#0B0B0D" /><Text style={[styles.demoText, { color: '#0B0B0D' }]}>{tt('judge_tour.judge_quick_tour_3_min')}</Text>
        </Pressable>
        {!data?.demo_active && (
          <Pressable testID="sb-demo" onPress={demoStart} disabled={busy === 'demo'} style={styles.demoBtn}>
            {busy === 'demo' ? <ActivityIndicator color="#FFD60A" /> : (<><Ionicons name="flask-outline" size={16} color="#FFD60A" /><Text style={styles.demoText}>DEMO MODE — 30 MIN FULL ACCESS (NO PAYMENT)</Text></>)}
          </Pressable>
        )}

        <View style={styles.billingRow}>
          <Pressable testID="sb-monthly" onPress={() => setAnnual(false)} style={[styles.billBtn, !annual && styles.billBtnActive]}>
            <Text style={[styles.billText, !annual && styles.billTextActive]}>{tt('subscription.monthly')}</Text>
          </Pressable>
          <Pressable testID="sb-annual" onPress={() => setAnnual(true)} style={[styles.billBtn, annual && styles.billBtnActive]}>
            <Text style={[styles.billText, annual && styles.billTextActive]}>{tt('subscription.yearly_20_secure_your_future')}</Text>
          </Pressable>
        </View>

        {!!msg && <Text testID="sb-msg" style={styles.info}>{msg}</Text>}
        {!!err && <Text style={styles.err}>{err}</Text>}

        {data && order.map(k => {
          const t2 = data.tiers[k];
          const active = data.tier === k;
          const accent = t2.accent || '#5FA779';
          const eur = annual ? t2.price_eur_year : t2.price_eur;
          const czk = annual ? t2.price_czk_year : t2.price_czk;
          const gat = annual ? t2.price_gat_year : t2.price_gat;
          const per = annual ? '/yr' : '/mo';
          return (
            <View key={k} style={[styles.tierCard, { borderColor: accent }, premium(k) && { backgroundColor: OBSIDIAN, borderWidth: 2.5 }, active && { borderStyle: 'solid', borderWidth: 3 }]}>
              {premium(k) && <Text style={[styles.vipRibbon, { color: accent }]}>{k === 'archangel' ? tt('subscription.elite_sovereignty') : tt('subscription.vip_survival')}</Text>}
              <View style={styles.tierHead}>
                <Ionicons name={TIER_ICON[k] as any} size={24} color={accent} />
                <View style={{ flex: 1 }}>
                  <Text style={[styles.tierName, premium(k) && { color: PLATINUM }]}>{t2.name.toUpperCase()}{active ? '  ' + tt('subscription.active') : ''}</Text>
                  <Text style={styles.tierTagline}>{tx(t2.tagline)}</Text>
                </View>
                <View style={{ alignItems: 'flex-end' }}>
                  <Text style={[styles.tierPrice, premium(k) && { color: PLATINUM }]}>{eur === 0 ? tt('subscription.free') : `${eur} €${per}`}</Text>
                  {gat > 0 && <Text style={styles.tierGat}>{czk} {tt('subscription.kc')} {gat} GA-T</Text>}
                </View>
              </View>
              {t2.features.map((f: string, i: number) => (
                <View key={i} style={styles.featRow}>
                  <Ionicons name="checkmark" size={14} color={accent} />
                  <Text style={[styles.featText, premium(k) && { color: '#B9B9C0' }]}>{tx(f)}</Text>
                </View>
              ))}
              {k !== 'sovereign' && !active && (
                <View style={styles.btnRow}>
                  <Pressable testID={`sb-upgrade-${k}-gat`} onPress={() => upgrade(k, 'gat')} disabled={!!busy} style={[styles.payBtn, { backgroundColor: accent }]}>
                    {busy === `${k}-gat` ? <ActivityIndicator size="small" color={OBSIDIAN} /> : <Text style={[styles.payText, premium(k) && { color: OBSIDIAN }]}>{tt('subscription.pay')} {gat} GA-T</Text>}
                  </Pressable>
                  <Pressable testID={`sb-upgrade-${k}-card`} onPress={() => upgrade(k, 'card')} disabled={!!busy} style={[styles.cardBtn, { borderColor: accent }]}>
                    {busy === `${k}-card` ? <ActivityIndicator size="small" color={accent} /> : (
                      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                        <Ionicons name="card-outline" size={14} color={accent} />
                        <Text style={[styles.cardText, { color: accent }]}>{tt('subscription.kartou')} {eur} €</Text>
                      </View>
                    )}
                  </Pressable>
                </View>
              )}
              {/* SOVEREIGN — free default plan, no purchase path */}
              {k === 'sovereign' && (
                <Text testID="sb-sovereign-free" style={styles.tierTagline}>{active ? tt('subscription.your_current_plan_free_forever_no_pa') : tt('subscription.free_default_plan_included_for_every')}</Text>
              )}
              {/* NATIVE IN-APP SUBSCRIPTION (RevenueCat · App Store / Google Play) — Guardian / Sentinel / Archangel; price comes from the store offering */}
              {k !== 'sovereign' && !active && (
                <View testID={`sb-iap-${k}`}>
                  <IapBuyButton tier={k as 'guardian' | 'sentinel' | 'archangel'} period={annual ? 'annual' : 'monthly'} accent={accent} onSynced={(_r, message) => { setMsg(message); setErr(''); load(); }} />
                </View>
              )}
            </View>
          );
        })}

        {/* RODINNÝ BALÍK — one payer unlocks Sentinel for the whole family circle */}
        {data && (
          <View testID="sb-family-pack" style={[styles.tierCard, { borderColor: '#B8860B', backgroundColor: OBSIDIAN, borderWidth: 2.5 }]}>
            <Text style={[styles.vipRibbon, { color: '#B8860B' }]}>{tt('subscription.family_plan')}</Text>
            <View style={styles.tierHead}>
              <Ionicons name="people" size={24} color="#B8860B" />
              <View style={{ flex: 1 }}>
                <Text style={[styles.tierName, { color: PLATINUM }]}>{tt('subscription.sentinel_for_the_whole_family')}</Text>
                <Text style={styles.tierTagline}>{tt('subscription.one_payer_you_up_to_4_guardians_from')}</Text>
              </View>
              <Text style={[styles.tierPrice, { color: PLATINUM }]}>{annual ? tt('subscription.2390_rok') : tt('subscription.249_mes')}</Text>
            </View>
            {['Sentinel features for 5 people (save up to 66%)', 'Activates automatically for linked Guardians', 'Never downgrades any member’s higher tier'].map((f, i) => (
              <View key={i} style={styles.featRow}>
                <Ionicons name="checkmark" size={14} color="#B8860B" />
                <Text style={[styles.featText, { color: '#B9B9C0' }]}>{f}</Text>
              </View>
            ))}
            <Pressable testID="sb-family-card" onPress={() => cardCheckout('family_sentinel')} disabled={!!busy} style={[styles.payBtn, { backgroundColor: '#B8860B', marginTop: S.md }]}>
              {busy === 'family_sentinel-card' ? <ActivityIndicator size="small" color={OBSIDIAN} /> : (
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                  <Ionicons name="card-outline" size={14} color={OBSIDIAN} />
                  <Text style={[styles.payText, { color: OBSIDIAN }]}>{tt('subscription.kartou')} {annual ? '2390' : '249'} €</Text>
                </View>
              )}
            </Pressable>
          </View>
        )}

        {data && (
          <Text style={styles.ppu}>{tt('subscription.pay_per_use_bio_scanner')} {data.payperuse?.bioscan_single} {tt('subscription.ga_t_scan_ips_export')} {data.payperuse?.ips_export_single} {tt('subscription.ga_t_human_second_opinion_at_the_spe')}</Text>
        )}

        {/* SPRÁVA PREDPLATNÉHO — payment history + one-tap cancel */}
        <Text style={styles.mgmtTitle}>{tt('subscription.manage_subscription')}</Text>
        {data && data.tier !== 'sovereign' && !data.inner_circle && data.paid_with !== 'iap' && (
          cancelConfirm ? (
            <View style={styles.cancelRow}>
              <Pressable testID="sb-cancel-yes" onPress={cancelSub} disabled={busy === 'cancel'} style={[styles.cancelBtn, { backgroundColor: C.error, borderColor: C.error }]}>
                {busy === 'cancel' ? <ActivityIndicator size="small" color="#fff" /> : <Text style={[styles.cancelText, { color: '#fff' }]}>{tt('subscription.yes_cancel_now')}</Text>}
              </Pressable>
              <Pressable testID="sb-cancel-no" onPress={() => setCancelConfirm(false)} style={styles.cancelBtn}>
                <Text style={styles.cancelText}>{tt('subscription.keep_it')}</Text>
              </Pressable>
            </View>
          ) : (
            <Pressable testID="sb-cancel" onPress={() => setCancelConfirm(true)} style={styles.cancelBtn}>
              <Text style={styles.cancelText}>{tt('subscription.cancel_subscription')}</Text>
            </Pressable>
          )
        )}
        {data?.inner_circle && <Text style={styles.txEmpty}>{tt('subscription.inner_circle_lifetime_archangel_noth')}</Text>}
        {/* Apple requires a Restore Purchases entry point — re-syncs the store entitlement into the tier */}
        <RestorePurchasesButton onSynced={load} />
        {data?.paid_with === 'iap' && (
          <Text testID="sb-iap-note" style={styles.txEmpty}>{tt('subscription.paid_through_your_app_store_manage_o')}</Text>
        )}
        {txs.length === 0 ? (
          <Text style={styles.txEmpty}>{tt('subscription.no_card_payments_yet')}</Text>
        ) : txs.map((tx: any) => (
          <View key={tx.session_id} testID={`sb-tx-${tx.session_id}`} style={styles.txRow}>
            <Ionicons name={tx.processed ? 'checkmark-circle' : tx.payment_status === 'expired' ? 'close-circle' : 'time-outline'} size={16} color={tx.processed ? '#5FA779' : tx.payment_status === 'expired' ? C.error : C.info} />
            <View style={{ flex: 1 }}>
              <Text style={styles.txTitle}>{tx.tier === 'family_sentinel' ? tt('subscription.family_plan_sentinel') : String(tx.tier).toUpperCase()} · {tx.billing === 'annual' ? tt('subscription.yearly') : tt('subscription.monthly_1n63')}</Text>
              <Text style={styles.txMeta}>{String(tx.created_at).slice(0, 10)} · {tx.processed ? tt('subscription.paid_receipt_in_vault') : tx.payment_status}</Text>
            </View>
            <Text style={styles.txAmount}>{tx.amount_eur} €</Text>
          </View>
        ))}

        {founder && (
          <View testID="sb-founder" style={styles.founderBox}>
            <Text style={styles.founderTitle}>{tt('subscription.founder_admin_wealth_engine')} {founder.wealth_engine?.startsWith('SECURED') ? tt('subscription.secured') : ''}</Text>
            <View style={styles.founderGrid}>
              <View style={styles.founderCell}><Text style={styles.founderVal}>{founder.mrr_eur} €</Text><Text style={styles.founderLbl}>{tt('subscription.mrr')}</Text></View>
              <View style={styles.founderCell}><Text style={styles.founderVal}>{founder.acv_eur} €</Text><Text style={styles.founderLbl}>{tt('subscription.acv')}</Text></View>
              <View style={styles.founderCell}><Text style={styles.founderVal}>{(founder.revenue_by_kind?.guardian_tax || 0).toFixed(0)} €</Text><Text style={styles.founderLbl}>{tt('subscription.guardian_tax_15')}</Text></View>
              <View style={styles.founderCell}><Text style={styles.founderVal}>{(founder.revenue_by_kind?.payperuse || 0).toFixed(0)} €</Text><Text style={styles.founderLbl}>{tt('subscription.pay_per_use')}</Text></View>
            </View>
            <Text style={styles.founderMeta}>{tt('subscription.tiery')} {Object.entries(founder.tier_distribution || {}).map(([k, v]) => `${k}:${v}`).join(' · ') || '—'} {tt('subscription.ga_t_treasury')} {Number(founder.gat_treasury).toFixed(0)} {tt('subscription.burned')} {Number(founder.gat_burned).toFixed(1)}</Text>
          </View>
        )}

        {/* FOUNDER GIFTING — darovanie prémia */}
        {founder && (
          <View testID="sb-gift" style={styles.giftBox}>
            <Text style={styles.founderTitle}>{tt('subscription.gift_premium_founder')}</Text>
            <Text style={styles.giftHint}>{tt('subscription.gift_any_tier_by_e_mail_free_instant')}</Text>
            <TextInput
              testID="sb-gift-email"
              value={giftEmail}
              onChangeText={setGiftEmail}
              placeholder="email@pouzivatela.sk"
              placeholderTextColor="#666"
              autoCapitalize="none"
              keyboardType="email-address"
              style={styles.giftInput}
            />
            <View style={styles.chipRow}>
              {(['guardian', 'sentinel', 'archangel'] as const).map(t3 => (
                <Pressable key={t3} testID={`sb-gift-tier-${t3}`} onPress={() => setGiftTier(t3)} style={[styles.chip, giftTier === t3 && styles.chipActive]}>
                  <Text style={[styles.chipText, giftTier === t3 && styles.chipTextActive]}>{t3.toUpperCase()}</Text>
                </Pressable>
              ))}
            </View>
            <View style={styles.chipRow}>
              {[30, 90, 365].map(d => (
                <Pressable key={d} testID={`sb-gift-days-${d}`} onPress={() => setGiftDays(d)} style={[styles.chip, giftDays === d && styles.chipActive]}>
                  <Text style={[styles.chipText, giftDays === d && styles.chipTextActive]}>{d} {tt('subscription.days_yjqb')}</Text>
                </Pressable>
              ))}
            </View>
            <Pressable testID="sb-gift-send" onPress={sendGift} disabled={!!busy || !giftEmail.trim()} style={[styles.payBtn, { backgroundColor: '#B8860B', marginTop: S.md, opacity: giftEmail.trim() ? 1 : 0.5 }]}>
              {busy === 'gift' ? <ActivityIndicator size="small" color={OBSIDIAN} /> : <Text style={[styles.payText, { color: OBSIDIAN }]}>{tt('subscription.gift')} {giftTier.toUpperCase()} · {giftDays} {tt('subscription.days_yjqb')}</Text>}
            </Pressable>
            {gifts.slice(0, 5).map((g: any) => (
              <Text key={g.gift_id} style={styles.giftRow}>🎁 {g.to_email} — {String(g.tier).toUpperCase()} · {g.days} {tt('subscription.days')} {String(g.created_at).slice(0, 10)}</Text>
            ))}
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
  loyalty: { color: '#B8860B', fontSize: 11, lineHeight: 16, fontWeight: '800', marginBottom: S.md },
  gat: { color: '#B8860B', fontWeight: '800', fontSize: 11 },
  trialBtn: { marginTop: S.md, backgroundColor: PLATINUM, minHeight: 52, alignItems: 'center', justifyContent: 'center' },
  demoBtn: { flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderStyle: 'dashed', borderColor: '#FFD60A', paddingVertical: S.md, minHeight: 48, marginBottom: S.md },
  demoText: { color: '#FFD60A', fontWeight: '900', letterSpacing: 1, fontSize: 11 },
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
  mgmtTitle: { marginTop: S.xl, color: C.info, fontWeight: '800', fontSize: 11, letterSpacing: 2 },
  cancelRow: { flexDirection: 'row', gap: S.sm, marginTop: S.md },
  cancelBtn: { flex: 1, borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.sm, minHeight: 48, alignItems: 'center', justifyContent: 'center', marginTop: S.md },
  cancelText: { color: C.info, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  txEmpty: { color: C.info, fontSize: 11, marginTop: S.md },
  txRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, backgroundColor: C.surface2, borderRadius: R.sm, padding: S.md, marginTop: S.sm },
  txTitle: { color: C.fg, fontWeight: '800', fontSize: 12 },
  txMeta: { color: C.info, fontSize: 10, marginTop: 2 },
  txAmount: { color: C.fg, fontWeight: '900', fontSize: 13 },
  giftBox: { marginTop: S.md, borderWidth: 2, borderColor: '#B8860B', padding: S.md, backgroundColor: OBSIDIAN },
  giftHint: { color: '#8A8A93', fontSize: 10.5, marginTop: 4, lineHeight: 14 },
  giftInput: { marginTop: S.md, borderWidth: 1.5, borderColor: '#3A3A44', color: PLATINUM, paddingHorizontal: S.md, minHeight: 48, fontSize: 14, borderRadius: R.sm },
  chipRow: { flexDirection: 'row', gap: S.sm, marginTop: S.sm },
  chip: { flex: 1, borderWidth: 1.5, borderColor: '#3A3A44', borderRadius: R.pill, minHeight: 40, alignItems: 'center', justifyContent: 'center' },
  chipActive: { borderColor: '#B8860B', backgroundColor: 'rgba(184,134,11,0.15)' },
  chipText: { color: '#8A8A93', fontWeight: '900', fontSize: 9.5, letterSpacing: 1 },
  chipTextActive: { color: '#B8860B' },
  giftRow: { color: '#8A8A93', fontSize: 10.5, marginTop: S.sm },
});
