/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

const EARN_META: Record<string, { icon: string; hint: string }> = {
  proof_of_help: { icon: 'people', hint: 'Answer a family pulse ping or help a senior' },
  proof_of_health: { icon: 'pulse', hint: 'Share an anonymous signal in the Sentinel network / Marketplace' },
  community_support: { icon: 'heart', hint: 'Contribute to the Solidarity Hub or the Barter network' },
};
const SPEND_META: Record<string, string> = {
  vip_sentinel_30d: 'shield-checkmark',
  expert_consult: 'school',
  priority_hunter_7d: 'flash',
};

export default function TokenWallet() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const [wallet, setWallet] = useState<any>(null);
  const [supply, setSupply] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    try {
      const [w, s] = await Promise.all([api('/token/wallet'), api('/token/supply')]);
      setWallet(w); setSupply(s);
    } catch (e: any) { setErr(String(e.message || e)); }
  };
  useEffect(() => { load(); }, []);

  const earn = async (activity: string) => {
    setBusy(`e-${activity}`); setErr(''); setMsg('');
    try {
      const r: any = await api('/token/earn', { method: 'POST', body: JSON.stringify({ activity }) });
      setMsg(`+${r.tx.amount} GA-T credited. Balance: ${r.balance} GA-T`);
      await load();
    } catch (e: any) {
      const m = String(e.message || e);
      setErr(m.includes('daily_limit') ? 'Daily limit for this activity reached — try again tomorrow.' : m);
    } finally { setBusy(null); }
  };

  const spend = async (item: string) => {
    setBusy(`s-${item}`); setErr(''); setMsg('');
    try {
      const r: any = await api('/token/spend', { method: 'POST', body: JSON.stringify({ item }) });
      setMsg(`Purchased ✓ (burned ${r.burned} GA-T). Balance: ${r.balance} GA-T`);
      await load();
    } catch (e: any) {
      const m = String(e.message || e);
      setErr(m.includes('insufficient_balance') ? 'Insufficient GA-T balance — earn tokens first.' : m);
    } finally { setBusy(null); }
  };

  const pct = (v: number) => supply ? Math.max(0.5, (v / supply.total_supply) * 100) : 0;
  const vipActive = wallet?.vip_until && new Date(wallet.vip_until) > new Date();

  return (
    <SafeAreaView testID="token-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="tk-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>{tt('token.ga_t_guardian_token')}</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView
        contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} tintColor={C.brand} />}
      >
        <View style={styles.hero}>
          <Text style={styles.heroLbl}>{tt('token.your_balance')}</Text>
          <Text testID="tk-balance" style={styles.heroVal}>{wallet ? wallet.balance.toFixed(1) : '—'} <Text style={styles.heroSym}>GA-T</Text></Text>
          <Text style={styles.heroSub}>{tt('token.earned')} {wallet?.earned_total?.toFixed(1) ?? 0} {tt('token.spent')} {wallet?.spent_total?.toFixed(1) ?? 0}</Text>
          {vipActive && (
            <View style={styles.vipBadge}>
              <Ionicons name="shield-checkmark" size={14} color={C.onInverse} />
              <Text style={styles.vipText}>{tt('token.vip_sentinel_until')} {String(wallet.vip_until).slice(0, 10)}</Text>
            </View>
          )}
        </View>
        {!!msg && <Text style={styles.info}>{msg}</Text>}
        {!!err && <Text style={styles.err}>{err}</Text>}

        {/* PREMIUM LOYALTY LOOP — fiat subscription → automatic monthly GA-T allocation */}
        {wallet?.subscription_allocation && (
          <View testID="tk-loyalty" style={[styles.loyalty, wallet.subscription_allocation.eligible && styles.loyaltyOn]}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <Ionicons name="diamond" size={18} color={C.brand} />
              <Text style={styles.loyaltyTitle}>{tt('token.premium_loyalty_allocation')}</Text>
            </View>
            {wallet.subscription_allocation.eligible ? (
              <>
                <Text testID="tk-loyalty-status" style={styles.loyaltyBig}>
                  +{Number(wallet.subscription_allocation.next_amount).toFixed(0)} {tt('token.ga_t_on')} {String(wallet.subscription_allocation.next_at || '').slice(0, 10) || '—'}
                </Text>
                <Text style={styles.loyaltySub}>
                  {wallet.subscription_allocation.tier.toUpperCase()} {tt('token.plan')} {wallet.subscription_allocation.months_collected} {tt('token.month')}{wallet.subscription_allocation.months_collected === 1 ? '' : 's'} {tt('token.collected_loyalty_bonus')}{wallet.subscription_allocation.next_bonus_pct}{tt('token.grows')}{wallet.subscription_allocation.loyalty_bonus_per_month_pct}{tt('token.month_max')}{wallet.subscription_allocation.loyalty_bonus_cap_pct}{tt('token.total')} {Number(wallet.subscription_total || 0).toFixed(0)} GA-T
                </Text>
                {wallet.subscription_allocation.credited_now > 0 && (
                  <Text testID="tk-loyalty-credited" style={styles.loyaltyCredit}>✓ {wallet.subscription_allocation.credited_now} {tt('token.allocation')}{wallet.subscription_allocation.credited_now === 1 ? '' : 's'} {tt('token.just_credited')}</Text>
                )}
              </>
            ) : (
              <>
                <Text testID="tk-loyalty-status" style={styles.loyaltySub}>
                  {wallet.subscription_allocation.reason === 'paid_with_gat_or_trial'
                    ? tt('token.monthly_ga_t_allocations_are_reserve')
                    : tt('token.subscribe_to_guardian_9_month_and_re', [Number(wallet.subscription_allocation.monthly_amount).toFixed(0)])}
                </Text>
                {wallet.subscription_allocation.reason !== 'paid_with_gat_or_trial' && (
                  <Pressable testID="tk-loyalty-upgrade" onPress={() => router.push('/subscription')} style={styles.loyaltyBtn}>
                    <Text style={styles.loyaltyBtnText}>{tt('token.view_plans')}</Text>
                  </Pressable>
                )}
              </>
            )}
          </View>
        )}

        <Text style={styles.section}>{tt('token.earn_ga_t_proof_of_help_proof_of_hea')}</Text>
        {wallet && Object.entries(wallet.earn_rules || {}).map(([k, r]: any) => (
          <View key={k} style={styles.row}>
            <Ionicons name={(EARN_META[k]?.icon || 'add') as any} size={20} color={C.brand} />
            <View style={{ flex: 1 }}>
              <Text style={styles.rowTitle}>{tx(r.label)}</Text>
              <Text style={styles.rowSub}>{EARN_META[k]?.hint} {tt('token.max')} {r.daily_max}{tt('token.day')}</Text>
            </View>
            <Pressable testID={`tk-earn-${k}`} onPress={() => earn(k)} disabled={busy === `e-${k}`} style={styles.earnBtn}>
              {busy === `e-${k}` ? <ActivityIndicator size="small" color={C.onInverse} /> : <Text style={styles.earnText}>+{r.amount}</Text>}
            </Pressable>
          </View>
        ))}

        <Text style={styles.section}>{tt('token.spend_ga_t_utility')}</Text>
        {wallet && Object.entries(wallet.spend_items || {}).map(([k, it]: any) => (
          <View key={k} style={styles.row}>
            <Ionicons name={(SPEND_META[k] || 'cart') as any} size={20} color={C.fg} />
            <View style={{ flex: 1 }}>
              <Text style={styles.rowTitle}>{tx(it.label)}</Text>
              <Text style={styles.rowSub}>{tt('token.2_of_the_price_is_burned_deflationar')}</Text>
            </View>
            <Pressable testID={`tk-spend-${k}`} onPress={() => spend(k)} disabled={busy === `s-${k}`} style={styles.spendBtn}>
              {busy === `s-${k}` ? <ActivityIndicator size="small" color={C.brand} /> : <Text style={styles.spendText}>{it.price} GA-T</Text>}
            </Pressable>
          </View>
        ))}

        <Text style={styles.section}>{tt('token.tokenomics_supply')}</Text>
        {supply && (
          <View style={styles.supplyBox}>
            <SupplyBar label={tt('token.treasury_rewards')} value={supply.treasury} pct={pct(supply.treasury)} color={C.brand} />
            <SupplyBar label={tt('token.founder_s_reserve_25_time_lock')} value={supply.founder_reserve} pct={pct(supply.founder_reserve)} color="#B8860B" />
            <SupplyBar label={tt('token.in_circulation')} value={supply.circulating} pct={pct(supply.circulating)} color="#5FA779" />
            <SupplyBar label={tt('token.burned_burn', [supply.burn_stats?.burn_rate_pct])} value={supply.burned} pct={pct(supply.burned)} color={C.error} />
            <Text style={styles.lockNote}>{tt('token.founder_s_reserve_locked_until')} {String(supply.founder_locked_until).slice(0, 10)} {tt('token.governance_long_term_development')}</Text>
            <Text style={styles.lockNote}>{tt('token.network')} {supply.chain} {tt('token.total_pdje')} {supply.total_supply.toLocaleString()} GA-T</Text>
          </View>
        )}

        <Text style={styles.section}>{tt('token.recent_transactions')}</Text>
        {(wallet?.txs || []).slice(0, 12).map((t: any) => (
          <View key={t.tx_id} style={styles.txRow}>
            <Ionicons name={t.kind === 'earn' ? 'arrow-down-circle' : t.kind === 'subscription_allocation' ? 'diamond' : t.kind === 'burn' ? 'flame' : 'arrow-up-circle'} size={16} color={t.kind === 'earn' ? '#5FA779' : t.kind === 'subscription_allocation' ? C.brand : t.kind === 'burn' ? C.error : C.fg} />
            <Text style={styles.txText} numberOfLines={1}>{t.kind === 'subscription_allocation' ? tt('token.loyalty') : t.kind.toUpperCase()} {t.amount > 0 ? '+' : ''}{t.amount} · {t.meta?.activity || t.meta?.item || t.meta?.note || ''}</Text>
            <Text style={styles.txAt}>{String(t.at).slice(5, 16).replace('T', ' ')}</Text>
          </View>
        ))}
        {(!wallet?.txs || wallet.txs.length === 0) && <Text style={styles.rowSub}>{tt('token.no_transactions_yet_start_earning_pr')}</Text>}

        <Text style={styles.disclaimer}>{tt('token.ga_t_runs_on_an_internal_hash_chaine')}</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

function SupplyBar({ label, value, pct, color }: any) {
  return (
    <View style={{ marginBottom: S.sm }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
        <Text style={styles.barLbl}>{label}</Text>
        <Text style={styles.barVal}>{Number(value).toLocaleString()}</Text>
      </View>
      <View style={styles.barTrack}>
        <View style={[styles.barFill, { width: `${pct}%`, backgroundColor: color }]} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 14 },
  hero: { backgroundColor: C.inverse, borderRadius: R.md, padding: S.xl, alignItems: 'center' },
  heroLbl: { color: C.onInverse, opacity: 0.7, fontSize: 10, letterSpacing: 2, fontWeight: '800' },
  heroVal: { color: C.onInverse, fontSize: 42, fontWeight: '900', marginTop: 4 },
  heroSym: { fontSize: 18, fontWeight: '800' },
  heroSub: { color: C.onInverse, opacity: 0.75, fontSize: 11, marginTop: 4 },
  vipBadge: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#B8860B', borderRadius: R.sm, paddingHorizontal: S.md, paddingVertical: 6, marginTop: S.md },
  vipText: { color: C.onInverse, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  section: { marginTop: S.xl, marginBottom: S.sm, fontSize: 11, letterSpacing: 1.5, color: C.brand, fontWeight: '900' },
  loyalty: { marginTop: S.lg, borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.md, padding: S.lg, gap: 6, backgroundColor: C.surface2 },
  loyaltyOn: { borderColor: C.brand, backgroundColor: 'rgba(212,175,55,0.08)' },
  loyaltyTitle: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 1.5 },
  loyaltyBig: { color: C.fg, fontWeight: '900', fontSize: 20, marginTop: 4 },
  loyaltySub: { color: C.info, fontSize: 11, lineHeight: 16 },
  loyaltyCredit: { color: '#5FA779', fontWeight: '900', fontSize: 11 },
  loyaltyBtn: { alignSelf: 'flex-start', backgroundColor: C.brand, borderRadius: R.sm, paddingHorizontal: S.lg, minHeight: 40, justifyContent: 'center', marginTop: 4 },
  loyaltyBtnText: { color: C.onInverse, fontWeight: '900', fontSize: 12, letterSpacing: 1 },
  row: { flexDirection: 'row', alignItems: 'center', gap: S.md, backgroundColor: C.surface2, borderRadius: R.sm, padding: S.md, marginTop: S.sm },
  rowTitle: { color: C.fg, fontWeight: '800', fontSize: 12.5 },
  rowSub: { color: C.info, fontSize: 10.5, marginTop: 2 },
  earnBtn: { backgroundColor: C.brand, borderRadius: R.sm, paddingHorizontal: S.md, minHeight: 44, minWidth: 64, alignItems: 'center', justifyContent: 'center' },
  earnText: { color: C.onInverse, fontWeight: '900', fontSize: 13 },
  spendBtn: { borderWidth: 1.5, borderColor: C.brand, borderRadius: R.sm, paddingHorizontal: S.md, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  spendText: { color: C.brand, fontWeight: '900', fontSize: 11 },
  supplyBox: { backgroundColor: C.surface2, borderRadius: R.md, padding: S.md },
  barLbl: { color: C.fg, fontSize: 11, fontWeight: '700' },
  barVal: { color: C.info, fontSize: 10.5 },
  barTrack: { height: 8, backgroundColor: C.surface3, borderRadius: 4, marginTop: 4, overflow: 'hidden' },
  barFill: { height: 8, borderRadius: 4 },
  lockNote: { color: C.info, fontSize: 10, marginTop: 6, lineHeight: 14 },
  txRow: { flexDirection: 'row', alignItems: 'center', gap: S.sm, paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: C.border },
  txText: { flex: 1, color: C.fg, fontSize: 11 },
  txAt: { color: C.info, fontSize: 9.5 },
  info: { color: '#5FA779', marginTop: S.md, fontSize: 12 },
  err: { color: C.error, marginTop: S.md, fontSize: 12 },
  disclaimer: { marginTop: S.xl, color: C.info, fontSize: 10, lineHeight: 15, textAlign: 'center' },
});
