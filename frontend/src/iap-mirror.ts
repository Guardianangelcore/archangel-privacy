/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// IAP MIRROR — copies the device's RevenueCat `pro` entitlement into the backend tier system
// (users.tier = guardian, tier_paid_with = "iap") so the Jarvis Guardian gate and the monthly
// GA-T loyalty allocation apply to App Store / Google Play subscribers.
// The SDK's CustomerInfo remains the source of truth; this is a one-way, idempotent mirror.
import { useEffect, useRef } from 'react';
import type { CustomerInfo } from 'react-native-purchases';
import { api, errMsg } from './api';
import { useAuth } from './auth';
import { rcEnabled, REVENUECAT_ENTITLEMENT_IDENTIFIER, useSubscription } from './revenuecat';

export type IapSyncResult = {
  status: 'synced' | 'unchanged' | 'downgraded' | 'noop' | 'kept_higher_tier' | 'addons_synced';
  tier: string;
  addons?: Record<string, { active: boolean; until?: string | null; will_renew?: boolean | null; status: string }>;
  tier_until?: string | null;
  gat_allocation?: { eligible: boolean; credited_now?: number; credited_txs?: { amount: number }[]; next_amount?: number; next_at?: string | null; reason?: string };
};

/** POST the entitlement state to the backend. Returns null when the user never had the entitlement.
 *  Concurrent callers with the same entitlement snapshot (buy button + useIapMirror) share ONE request. */
export const isAddonProduct = (pid?: string | null) => (pid || '').toLowerCase().includes('addon_');

export function activeSubs(info: CustomerInfo) {
  return (info.activeSubscriptions || []).map(pid => ({
    product_identifier: pid,
    expires_date: info.allExpirationDates?.[pid] ?? null,
    store: info.entitlements.all[REVENUECAT_ENTITLEMENT_IDENTIFIER]?.store,
  }));
}

const inflight = new Map<string, Promise<IapSyncResult | null>>();
export function syncIapEntitlement(info: CustomerInfo, appUserId: string | null): Promise<IapSyncResult | null> {
  const ent = info.entitlements.all[REVENUECAT_ENTITLEMENT_IDENTIFIER];
  if (!ent) return Promise.resolve(null);
  const active = info.entitlements.active[REVENUECAT_ENTITLEMENT_IDENTIFIER] !== undefined;
  // ONE entitlement aggregates tier plans AND add-on subscriptions → send every active product with its
  // own expiry so the backend can run separate lifecycles (tier vs Perplexity Ultra / Premium Voice).
  const active_subscriptions = activeSubs(info);
  const sig = `${appUserId}|${active}|${ent.expirationDate}|${ent.productIdentifier}|${active_subscriptions.map(s => s.product_identifier + s.expires_date).join(',')}`;
  const existing = inflight.get(sig);
  if (existing) return existing;
  const p = api<IapSyncResult>('/subscription/iap-sync', {
    method: 'POST',
    body: JSON.stringify({
      entitlement: REVENUECAT_ENTITLEMENT_IDENTIFIER,
      active,
      product_identifier: ent.productIdentifier,
      expires_date: ent.expirationDate,
      store: ent.store,
      period_type: ent.periodType,
      app_user_id: appUserId,
      will_renew: ent.willRenew,
      active_subscriptions,
    }),
  }).finally(() => { setTimeout(() => inflight.delete(sig), 3000); });
  inflight.set(sig, p);
  return p;
}

/** Sum of GA-T credited by this sync call (0 when nothing new). */
export function creditedGat(r: IapSyncResult | null): number {
  const txs = r?.gat_allocation?.credited_txs || [];
  return txs.reduce((s, t) => s + Number(t.amount || 0), 0);
}

/** Mounted once in the root layout: mirrors renewals / restores / lapses whenever CustomerInfo changes. */
export function useIapMirror() {
  const { user } = useAuth();
  const { customerInfo, identityReady, appUserId } = useSubscription();
  const lastSig = useRef('');
  useEffect(() => {
    if (!rcEnabled || !user?.user_id || !customerInfo || !identityReady) return;
    const ent = customerInfo.entitlements.all[REVENUECAT_ENTITLEMENT_IDENTIFIER];
    if (!ent) return;
    const sig = `${user.user_id}|${ent.isActive}|${ent.expirationDate}|${ent.productIdentifier}|${(customerInfo.activeSubscriptions || []).join(',')}`;
    if (lastSig.current === sig) return;
    lastSig.current = sig;
    syncIapEntitlement(customerInfo, appUserId).catch(e => console.log('[IAP mirror] sync failed:', errMsg(e)));
  }, [user?.user_id, customerInfo, identityReady, appUserId]);
}
