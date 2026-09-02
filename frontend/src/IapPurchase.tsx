/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// Native in-app subscription controls (RevenueCat · App Store / Google Play) for the GUARDIAN plan.
// Prices and packages ALWAYS come from offerings — never hardcoded.
import React, { useState } from 'react';
import { View, Text, StyleSheet, Pressable, ActivityIndicator, Modal, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { PurchasesPackage } from 'react-native-purchases';
import { rcEnabled, rcSimulated, useSubscription, IAP_PACKAGES, IapTier } from './revenuecat';
import { syncIapEntitlement, creditedGat, IapSyncResult } from './iap-mirror';
import { errMsg } from './api';
import { C, S, R } from './theme';
import { useI18n } from '@/src/i18n-context';

const OBSIDIAN = '#0B0B0D';
const GOLD = '#B8860B';
export const STORE_LABEL = Platform.OS === 'ios' ? 'APP STORE' : Platform.OS === 'android' ? 'GOOGLE PLAY' : 'APP STORE / GOOGLE PLAY';

type BuyProps = {
  tier?: IapTier;
  period: 'monthly' | 'annual';
  accent?: string;
  /** Called after the backend tier mirror; `message` is the human-readable confirmation (the button may unmount once the tier flips). */
  onSynced?: (r: IapSyncResult | null, message: string) => void;
};

/** RevenueCat cancel = PURCHASE_CANCELLED_ERROR ("1" native, numeric 1 in Browser Mode). */
const isUserCancelled = (e: any) => !!e?.userCancelled || String(e?.code) === '1';

export function IapBuyButton({ tier = 'guardian', period, accent = GOLD, onSynced }: BuyProps) {
  const { t: tt, tx } = useI18n();
  const { offerings, offeringsError, purchase, isPurchasing, identityReady, identityError, isLoading, activeTier, appUserId } = useSubscription();
  const TIER = tier.toUpperCase();
  const [confirm, setConfirm] = useState(false);
  const [err, setErr] = useState('');
  const [ok, setOk] = useState('');

  if (!rcEnabled) return null;
  const current = offerings?.current;
  const wanted = IAP_PACKAGES[tier][period];
  const pkg: PurchasesPackage | undefined = current?.availablePackages.find(p => p.identifier === wanted);

  if (isLoading && !pkg) return <ActivityIndicator testID="iap-loading" size="small" color={accent} style={{ marginTop: S.md }} />;
  if (!pkg) {
    return (
      <Text testID="iap-unavailable" style={st.hint}>
        {tt('c_IapPurchase.subscription_options_are_unavailable')}{offeringsError ? ` (${errMsg(offeringsError)})` : ''}
      </Text>
    );
  }

  const buy = async () => {
    setConfirm(false); setErr(''); setOk('');
    try {
      const info = await purchase(pkg);
      const r = await syncIapEntitlement(info, appUserId);
      const gat = creditedGat(r);
      const message = `✓ ${TIER} active via ${STORE_LABEL}${gat > 0 ? ` · +${gat.toFixed(0)} GA-T loyalty credited` : ''}`;
      setOk(message);
      onSynced?.(r, message);
    } catch (e: any) {
      if (isUserCancelled(e)) return;
      setErr(String(e?.message || '') === 'identity_not_ready'
        ? 'Purchase identity is not ready — please sign out and sign in again.'
        : errMsg(e));
    }
  };

  const disabled = !identityReady || isPurchasing;
  return (
    <View style={st.wrap}>
      {activeTier === tier ? (
        <Text testID={`iap-active-${tier}`} style={[st.active, { color: accent }]}>✓ {TIER} {tt('c_IapPurchase.active_via')} {STORE_LABEL}</Text>
      ) : (
        <Pressable testID={`iap-buy-${tier}-${period}`} onPress={() => setConfirm(true)} disabled={disabled}
          style={[st.buyBtn, { borderColor: accent, opacity: disabled ? 0.5 : 1 }]}>
          {isPurchasing ? <ActivityIndicator size="small" color={accent} /> : (
            <View style={st.row}>
              <Ionicons name={Platform.OS === 'ios' ? 'logo-apple' : Platform.OS === 'android' ? 'logo-google-playstore' : 'phone-portrait-outline'} size={15} color={accent} />
              <Text style={[st.buyText, { color: accent }]}>{STORE_LABEL} · {pkg.product.priceString}{period === 'annual' ? tt('c_IapPurchase.yr') : tt('c_IapPurchase.mo')}</Text>
            </View>
          )}
        </Pressable>
      )}
      {!!identityError && <Text testID="iap-identity-error" style={st.err}>{tt('c_IapPurchase.purchase_identity_error')} {identityError}</Text>}
      {!!err && <Text testID="iap-error" style={st.err}>{err}</Text>}
      {!!ok && <Text testID="iap-ok" style={st.ok}>{ok}</Text>}
      {rcSimulated && <Text testID="iap-simulated" style={st.hint}>{tt('c_IapPurchase.simulated_purchase_revenuecat_test_s')}</Text>}

      <Modal visible={confirm} transparent animationType="fade" onRequestClose={() => setConfirm(false)}>
        <View style={st.backdrop}>
          <View testID="iap-confirm" style={st.sheet}>
            <Ionicons name="shield-checkmark" size={30} color={accent} />
            <Text style={st.sheetTitle}>{tt('c_IapPurchase.confirm_subscription')}</Text>
            <Text style={st.sheetBody}>
              {TIER} · {pkg.product.priceString} {period === 'annual' ? tt('c_IapPurchase.per_year') : tt('c_IapPurchase.per_month')}
              {'\n'}{tt('c_IapPurchase.billed_through')} {STORE_LABEL}{tt('c_IapPurchase.cancel_anytime_in_your_store_subscri')}
              {rcSimulated ? '\n\n' + tt('c_IapPurchase.simulated_test_store_nothing_is_char') : ''}
            </Text>
            <Pressable testID="iap-confirm-yes" onPress={buy} style={[st.confirmBtn, { backgroundColor: accent }]}>
              <Text style={st.confirmText}>{tt('c_IapPurchase.subscribe')} {pkg.product.priceString}</Text>
            </Pressable>
            <Pressable testID="iap-confirm-no" onPress={() => setConfirm(false)} style={st.cancelBtn}>
              <Text style={st.cancelText}>{tt('c_IapPurchase.not_now')}</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </View>
  );
}

export function RestorePurchasesButton({ onSynced }: { onSynced?: (r: IapSyncResult | null) => void }) {
  const { t: tt, tx } = useI18n();
  const { restore, isRestoring, appUserId } = useSubscription();
  const [msg, setMsg] = useState('');
  const [isErr, setIsErr] = useState(false);
  if (!rcEnabled) return null;
  const run = async () => {
    setMsg(''); setIsErr(false);
    try {
      const info = await restore();
      const r = await syncIapEntitlement(info, appUserId);
      const active = r && (r.status === 'synced' || r.status === 'unchanged' || r.status === 'kept_higher_tier');
      setMsg(active ? `✓ Purchases restored — ${String(r!.tier).toUpperCase()} active.` : 'No active store subscription found for this account.');
      onSynced?.(r);
    } catch (e: any) {
      setIsErr(true); setMsg(errMsg(e));
    }
  };
  return (
    <View>
      <Pressable testID="iap-restore" onPress={run} disabled={isRestoring} style={st.restoreBtn}>
        {isRestoring ? <ActivityIndicator size="small" color={C.info} /> : (
          <View style={st.row}>
            <Ionicons name="refresh" size={14} color={C.info} />
            <Text style={st.restoreText}>{tt('c_IapPurchase.restore_purchases')}{STORE_LABEL})</Text>
          </View>
        )}
      </Pressable>
      {!!msg && <Text testID="iap-restore-msg" style={isErr ? st.err : st.ok}>{msg}</Text>}
    </View>
  );
}

const st = StyleSheet.create({
  wrap: { marginTop: S.sm, gap: 6 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  buyBtn: { borderWidth: 1.5, borderRadius: R.sm, minHeight: 48, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(184,134,11,0.08)' },
  buyText: { fontWeight: '900', fontSize: 10.5, letterSpacing: 0.8 },
  active: { fontWeight: '900', fontSize: 10.5, letterSpacing: 1, textAlign: 'center', paddingVertical: S.sm },
  hint: { color: '#8A8A93', fontSize: 9.5, lineHeight: 13 },
  err: { color: C.error, fontSize: 11, lineHeight: 15, fontWeight: '700' },
  ok: { color: '#5FA779', fontSize: 11, lineHeight: 15, fontWeight: '700' },
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.75)', alignItems: 'center', justifyContent: 'center', padding: S.xl },
  sheet: { width: '100%', maxWidth: 420, backgroundColor: OBSIDIAN, borderWidth: 2, borderColor: GOLD, borderRadius: R.md, padding: S.xl, alignItems: 'center', gap: S.sm },
  sheetTitle: { color: '#E5E4E2', fontWeight: '900', letterSpacing: 3, fontSize: 13 },
  sheetBody: { color: '#B9B9C0', fontSize: 12, lineHeight: 18, textAlign: 'center' },
  confirmBtn: { alignSelf: 'stretch', minHeight: 50, alignItems: 'center', justifyContent: 'center', borderRadius: R.sm, marginTop: S.sm },
  confirmText: { color: OBSIDIAN, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  cancelBtn: { alignSelf: 'stretch', minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  cancelText: { color: '#8A8A93', fontWeight: '800', fontSize: 11, letterSpacing: 1 },
  restoreBtn: { borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.sm, minHeight: 48, alignItems: 'center', justifyContent: 'center', marginTop: S.md },
  restoreText: { color: C.info, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
});
