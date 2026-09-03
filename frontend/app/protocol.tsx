/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator, Switch } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';
import Paywall from '@/src/Paywall';

const SCOPES = [
  ['emergency_profile', 'Emergency profile'],
  ['vault_list', 'Document list (metadata only)'],
  ['recovery_status', 'Sick leave / recovery status'],
];
const MARKET_CATS: [string, string, any][] = [
  ['medication', 'protocol.cat_medication', 'flask-outline'],
  ['wellness', 'protocol.cat_wellness', 'walk-outline'],
  ['vaccination', 'protocol.cat_vaccination', 'shield-checkmark-outline'],
];
const SIGNALS = [
  ['pharmacy_out', 'Medication unavailable', 'flask-outline'],
  ['supply_shortage', 'Supply shortage', 'cube-outline'],
  ['grid_down', 'Power outage', 'flash-outline'],
  ['water_issue', 'Water issue', 'water-outline'],
];

export default function Protocol() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const [grants, setGrants] = useState<any[]>([]);
  const [audit, setAudit] = useState<any[]>([]);
  const [partner, setPartner] = useState('');
  const [scopes, setScopes] = useState<string[]>(['emergency_profile']);
  const [newToken, setNewToken] = useState('');
  const [market, setMarket] = useState<any>(null);
  const [offers, setOffers] = useState<any[]>([]);
  const [agg, setAgg] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState('');
  const [info, setInfo] = useState('');
  const [marketLocked, setMarketLocked] = useState(false);   // Guardian+ tier gate (402)

  const load = async () => {
    try {
      const [g, a, m, o, ag] = await Promise.all([
        api('/gateway/grants'), api('/gateway/audit'), api('/marketplace/me'), api('/marketplace/offers'), api('/sentinel/aggregate'),
      ]);
      setGrants(g); setAudit(a); setMarket(m); setOffers(o.offers || []); setAgg(ag);
    } catch (e: any) { setErr(String(e.message || e)); }
  };
  useEffect(() => { load(); }, []);

  const createGrant = async () => {
    if (!partner.trim() || !scopes.length) return;
    setBusy('grant'); setErr(''); setNewToken('');
    try {
      const g: any = await api('/gateway/grants', { method: 'POST', body: JSON.stringify({ partner_name: partner, scopes, expires_days: 30 }) });
      setNewToken(g.token); setPartner('');
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const revoke = async (id: string) => {
    try { await api(`/gateway/grants/${id}`, { method: 'DELETE' }); await load(); } catch {}
  };

  const saveOptin = async (enabled: boolean, categories: string[]) => {
    setErr('');
    try { await api('/marketplace/optin', { method: 'PUT', body: JSON.stringify({ enabled, categories }) }); await load(); }
    catch (e: any) {
      const m = String(e.message || e);
      if (/^402:/.test(m)) { setMarketLocked(true); return; }
      setErr(m);
    }
  };
  const sharedCats: string[] = !market ? [] : market.categories?.length ? market.categories : (market.enabled ? [] : MARKET_CATS.map(c => c[0]));
  const setOptin = (v: boolean) => saveOptin(v, sharedCats.length ? sharedCats : MARKET_CATS.map(c => c[0]));
  const toggleCat = (c: string) => saveOptin(!!market?.enabled, sharedCats.includes(c) ? sharedCats.filter(x => x !== c) : [...sharedCats, c]);

  const accept = async (id: string) => {
    setBusy(id); setErr(''); setInfo('');
    try { const s: any = await api(`/marketplace/offers/${id}/accept`, { method: 'POST' }); setInfo(`Sold anonymously: +${s.reward_eur} € (${s.reward_crypto}) · +${s.gat_reward ?? 0} GA-T — DEMO payout.`); await load(); }
    catch (e: any) {
      const m = String(e.message || e);
      if (/^402:/.test(m)) { setMarketLocked(true); return; }
      setErr(m.includes('optin_required') ? 'First enable anonymized sharing (opt-in).' : m.includes('category_not_shared') ? tt('protocol.enable_this_category_first') : m.includes('409') ? 'You already accepted this offer.' : m);
    }
    finally { setBusy(null); }
  };

  const report = async (kind: string) => {
    setBusy(`sig-${kind}`); setErr('');
    try { await api('/sentinel/report', { method: 'POST', body: JSON.stringify({ kind, region: 'SK' }) }); setInfo('Anonymous signal sent to the Sentinel network.'); await load(); }
    catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  return (
    <SafeAreaView testID="protocol-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="pr-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>{tt('protocol.guardian_protocol')}</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
        <Text style={styles.h1}>{tt('protocol.global_infrastructure')}</Text>
        <Text style={styles.sub}>{tt('protocol.guardian_os_as_a_universal_protocol')}</Text>
        {!!err && <Text style={styles.err}>{err}</Text>}
        {!!info && <Text style={styles.info}>{info}</Text>}

        <Text style={styles.section}>{tt('protocol.1_partner_api_gateway_only_with_your')}</Text>
        <TextInput testID="pr-partner" style={styles.input} placeholder={tt('protocol.partner_name_clinic_insurer_ambulanc')} placeholderTextColor={C.info} value={partner} onChangeText={setPartner} />
        {SCOPES.map(([k, l]) => (
          <Pressable key={k} testID={`pr-scope-${k}`} onPress={() => setScopes(scopes.includes(k) ? scopes.filter(s => s !== k) : [...scopes, k])} style={styles.scopeRow}>
            <Ionicons name={scopes.includes(k) ? 'checkbox' : 'square-outline'} size={20} color={C.brand} />
            <Text style={styles.scopeText}>{l}</Text>
          </Pressable>
        ))}
        <Pressable testID="pr-grant" onPress={createGrant} disabled={busy === 'grant'} style={styles.cta}>
          {busy === 'grant' ? <ActivityIndicator color={C.onInverse} /> : <Text style={styles.ctaText}>{tt('protocol.issue_partner_key_30_days')}</Text>}
        </Pressable>
        {!!newToken && (
          <View style={styles.tokenBox}>
            <Text style={styles.tokenLbl}>{tt('protocol.partner_key_shown_only_once_hand_ove')}</Text>
            <Text testID="pr-token" style={styles.tokenVal} selectable>{newToken}</Text>
          </View>
        )}
        {grants.map(g => (
          <View key={g.grant_id} style={styles.grantRow}>
            <View style={{ flex: 1 }}>
              <Text style={styles.grantName}>{g.partner_name}{g.revoked ? '  ' + tt('protocol.revoked') : ''}</Text>
              <Text style={styles.grantSub}>{(g.scopes || []).join(', ')} · {g.token_preview}</Text>
            </View>
            {!g.revoked && (
              <Pressable testID={`pr-revoke-${g.grant_id}`} onPress={() => revoke(g.grant_id)} style={styles.revokeBtn}>
                <Text style={styles.revokeText}>{tt('protocol.cancel')}</Text>
              </Pressable>
            )}
          </View>
        ))}
        {audit.length > 0 && (
          <>
            <Text style={styles.mini}>{tt('protocol.access_audit')}{audit.length})</Text>
            {audit.slice(0, 5).map((a, i) => (
              <Text key={i} style={styles.auditRow}>• {a.partner_name} → {a.scope} · {(a.at || '').slice(0, 16).replace('T', ' ')}</Text>
            ))}
          </>
        )}

        <Text style={styles.section}>{tt('protocol.2_sovereign_data_marketplace_demo_pa')}</Text>
        {marketLocked ? (
          <View testID="pr-market-paywall">
            <Paywall tier="guardian" message={tt('protocol.anonymized_data_monetization_opt_in') + ' — Guardian Plan'} onUnlocked={() => { setMarketLocked(false); load(); }} />
          </View>
        ) : (
          <>
            <View style={styles.optinRow}>
              <Ionicons name="lock-closed-outline" size={18} color={C.brand} />
              <View style={{ flex: 1 }}>
                <Text style={styles.optinTitle}>{tt('protocol.anonymized_data_monetization_opt_in')}</Text>
                <Text style={styles.optinSub}>{tt('protocol.earned')} {market?.earnings_eur ?? 0} € · <Text testID="pr-market-gat" style={{ color: C.brand, fontWeight: '900' }}>{market?.earnings_gat ?? 0} GA-T</Text> {tt('protocol.data_always_anonymous_gdpr_art_9')}</Text>
              </View>
              <Switch testID="pr-market-optin" value={!!market?.enabled} onValueChange={setOptin} disabled={!market} trackColor={{ true: C.brand, false: C.surface3 }} />
            </View>
            {/* WHAT YOU SHARE — per-category consent (anonymized, GDPR Art. 9) */}
            <Text style={styles.catTitle}>{tt('protocol.what_you_share')}</Text>
            <View style={styles.catRow}>
              {MARKET_CATS.map(([c, key, icon]) => {
                const on = sharedCats.includes(c);
                return (
                  <Pressable key={c} testID={`pr-cat-${c}`} onPress={() => toggleCat(c)} disabled={!market} style={[styles.catChip, on && styles.catChipOn]}>
                    <Ionicons name={icon} size={14} color={on ? C.brand : C.info} />
                    <Text style={[styles.catText, on && { color: C.brand }]}>{tt(key)}</Text>
                  </Pressable>
                );
              })}
            </View>
            {offers.map(o => {
              const sold = (market?.sales || []).some((s: any) => s.offer_id === o.offer_id);
              const shared = sharedCats.includes(o.category);
              return (
                <View key={o.offer_id} style={[styles.offerRow, !shared && { opacity: 0.45 }]}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.grantName}>{tx(o.title)}</Text>
                    <Text style={styles.grantSub}>{o.institution} · {o.reward_eur} € / {o.reward_crypto} · <Text style={{ color: C.brand, fontWeight: '900' }}>+{o.reward_gat ?? 0} GA-T</Text></Text>
                  </View>
                  <Pressable testID={`pr-offer-${o.offer_id}`} onPress={() => accept(o.offer_id)} disabled={sold || busy === o.offer_id} style={[styles.sellBtn, sold && { opacity: 0.4 }]}>
                    {busy === o.offer_id ? <ActivityIndicator size="small" color={C.onInverse} /> : <Text style={styles.sellText}>{sold ? tt('protocol.sold') : tt('protocol.sell')}</Text>}
                  </Pressable>
                </View>
              );
            })}
          </>
        )}

        <Text style={styles.section}>{tt('protocol.3_global_sentinel_network')}</Text>
        <Text style={styles.sub}>{tt('protocol.report_outages_and_shortages_anonymo')}</Text>
        <View style={styles.sigGrid}>
          {SIGNALS.map(([k, l, ic]) => (
            <Pressable key={k} testID={`pr-signal-${k}`} onPress={() => report(k)} disabled={busy === `sig-${k}`} style={styles.sigBtn}>
              <Ionicons name={ic as any} size={18} color={C.brand} />
              <Text style={styles.sigText}>{l}</Text>
            </Pressable>
          ))}
        </View>
        {agg && (
          <View style={styles.aggBox}>
            <Text style={styles.mini}>{tt('protocol.live_signals_7_days_active_nodes')} {agg.active_nodes}</Text>
            {(agg.signals || []).slice(0, 6).map((s: any, i: number) => (
              <Text key={i} style={styles.auditRow}>• {s.region}: {s.kind} × {s.count}</Text>
            ))}
            {(agg.signals || []).length === 0 && <Text style={styles.auditRow}>{tt('protocol.no_signals_yet')}</Text>}
          </View>
        )}
        <Text style={styles.disclaimer}>{tt('protocol.marketplace_payouts_and_the_sentinel')}</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 14 },
  h1: { fontSize: 24, fontWeight: '900', color: C.fg },
  sub: { marginTop: S.sm, fontSize: 12.5, color: C.onS3, lineHeight: 18 },
  section: { marginTop: S.xl, marginBottom: S.sm, fontSize: 11, letterSpacing: 1.5, color: C.brand, fontWeight: '900' },
  mini: { marginTop: S.md, marginBottom: 4, fontSize: 10, letterSpacing: 1, color: C.info, fontWeight: '800' },
  input: { backgroundColor: C.surface2, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, color: C.fg, paddingHorizontal: S.md, minHeight: 48, fontSize: 13, marginBottom: S.sm },
  scopeRow: { flexDirection: 'row', alignItems: 'center', gap: S.sm, minHeight: 40 },
  scopeText: { color: C.fg, fontSize: 13 },
  cta: { marginTop: S.md, backgroundColor: C.brand, borderRadius: R.sm, minHeight: 48, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  tokenBox: { marginTop: S.md, backgroundColor: C.surface2, borderRadius: R.sm, borderWidth: 1, borderColor: C.brand, padding: S.md },
  tokenLbl: { color: C.info, fontSize: 9.5, letterSpacing: 0.5, fontWeight: '800' },
  tokenVal: { color: C.brand, fontSize: 11, fontFamily: 'monospace', marginTop: 4 },
  grantRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, backgroundColor: C.surface2, borderRadius: R.sm, padding: S.md, marginTop: S.sm },
  grantName: { color: C.fg, fontWeight: '800', fontSize: 13 },
  grantSub: { color: C.info, fontSize: 10.5, marginTop: 2 },
  revokeBtn: { borderWidth: 1, borderColor: C.error, borderRadius: R.sm, paddingHorizontal: S.md, minHeight: 40, alignItems: 'center', justifyContent: 'center' },
  revokeText: { color: C.error, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  auditRow: { color: C.onS3, fontSize: 11, lineHeight: 17 },
  optinRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.brand, padding: S.md },
  optinTitle: { color: C.brand, fontWeight: '900', fontSize: 10.5, letterSpacing: 0.5 },
  optinSub: { color: C.onS3, fontSize: 11, marginTop: 2 },
  catTitle: { color: C.info, fontWeight: '800', fontSize: 10, letterSpacing: 1, marginTop: S.md, marginBottom: S.sm },
  catRow: { flexDirection: 'row', gap: S.sm, marginBottom: S.md },
  catChip: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 4, minHeight: 44, borderRadius: R.pill, borderWidth: 1, borderColor: C.border, backgroundColor: 'rgba(255,255,255,0.04)' },
  catChipOn: { borderColor: C.brand, backgroundColor: 'rgba(212,175,55,0.12)' },
  catText: { color: C.info, fontWeight: '800', fontSize: 10, letterSpacing: 0.3 },
  offerRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, backgroundColor: C.surface2, borderRadius: R.sm, padding: S.md, marginTop: S.sm },
  sellBtn: { backgroundColor: C.brand, borderRadius: R.sm, paddingHorizontal: S.md, minHeight: 42, alignItems: 'center', justifyContent: 'center' },
  sellText: { color: C.onInverse, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  sigGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: S.sm, marginTop: S.md },
  sigBtn: { width: '48%', flexGrow: 1, flexDirection: 'row', alignItems: 'center', gap: S.sm, borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.sm, padding: S.md, minHeight: 48 },
  sigText: { color: C.fg, fontWeight: '700', fontSize: 12 },
  aggBox: { marginTop: S.md, backgroundColor: C.surface2, borderRadius: R.sm, padding: S.md },
  disclaimer: { marginTop: S.xl, color: C.info, fontSize: 10, lineHeight: 15, textAlign: 'center' },
  err: { color: C.error, marginTop: S.md, fontSize: 12 },
  info: { color: '#5FA779', marginTop: S.md, fontSize: 12 },
});
