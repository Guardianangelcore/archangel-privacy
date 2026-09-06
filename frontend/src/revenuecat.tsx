/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// REVENUECAT — Emergent-managed in-app subscriptions (App Store / Google Play).
// SDK init happens ONCE at module scope in app/_layout.tsx via initializeRevenueCat().
// The SDK's customerInfo.entitlements.active["pro"] is the source of truth for paid status.
// Expo Go / web preview run in Browser Mode against the RevenueCat Test Store (simulated).
// Identity: Purchases.logIn(user_id) on every auth path (session restore, Google, e-mail),
// logOut on sign-out — handled here because this provider sits inside AuthProvider.
import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { Platform } from 'react-native';
import Purchases, { LOG_LEVEL } from 'react-native-purchases';
import type { CustomerInfo, PurchasesPackage } from 'react-native-purchases';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from './auth';

const REVENUECAT_TEST_API_KEY = process.env.EXPO_PUBLIC_REVENUECAT_TEST_API_KEY;
const REVENUECAT_IOS_API_KEY = process.env.EXPO_PUBLIC_REVENUECAT_IOS_API_KEY;
const REVENUECAT_ANDROID_API_KEY = process.env.EXPO_PUBLIC_REVENUECAT_ANDROID_API_KEY;

export const REVENUECAT_ENTITLEMENT_IDENTIFIER = 'pro'; // from /setup: entitlement_lookup_key

export type IapTier = 'guardian' | 'sentinel' | 'archangel' | 'duo' | 'family' | 'family_xl';
/** Offering packages per tier (provisioned via the integration proxy — see memory/revenuecat.md). */
export const IAP_PACKAGES: Record<IapTier, { monthly: string; annual: string }> = {
  guardian: { monthly: 'guardian_monthly', annual: 'guardian_annual' },
  // v2 packages (Sept 2026 price update €99/€950 · €299/€2990) — Test Store products are immutable,
  // so the old sentinel_*/archangel_* packages were detached from the offering and replaced.
  sentinel: { monthly: 'sentinel_monthly_v2', annual: 'sentinel_annual_v2' },
  archangel: { monthly: 'archangel_monthly_v2', annual: 'archangel_annual_v2' },
  // Family plans (RevenueCat products provisioned alongside the tiers)
  duo: { monthly: 'duo_monthly', annual: 'duo_annual' },
  family: { monthly: 'family_monthly', annual: 'family_annual' },
  family_xl: { monthly: 'family_xl_monthly', annual: 'family_xl_annual' },
};
/** One entitlement covers all tiers — the tier is derived from the store product identifier. */
const TIER_ORDER: IapTier[] = ['duo', 'family', 'family_xl', 'guardian', 'sentinel', 'archangel'];
export function iapTierOf(productIdentifier?: string | null): IapTier {
  const pid = (productIdentifier || '').toLowerCase();
  if (pid.includes('archangel')) return 'archangel';
  if (pid.includes('sentinel')) return 'sentinel';
  if (pid.includes('family_xl')) return 'family_xl';
  if (pid.includes('family')) return 'family';
  if (pid.includes('duo')) return 'duo';
  return 'guardian';
}

export const rcEnabled = Platform.OS !== 'web' || __DEV__; // production web has no store
/** True when purchases are simulated against the Test Store (Expo Go / web preview). */
export const rcSimulated = Platform.OS === 'web' || __DEV__;

const CUSTOMER_INFO_KEY = ['revenuecat', 'customer-info'];
const isAnonymous = (id?: string | null) => !id || id.startsWith('$RCAnonymousID:');

function getRevenueCatApiKey() {
  if (!REVENUECAT_TEST_API_KEY || !REVENUECAT_IOS_API_KEY || !REVENUECAT_ANDROID_API_KEY) {
    throw new Error('RevenueCat public API keys not found — run the Setup section first');
  }
  if (Platform.OS === 'web' || __DEV__) return REVENUECAT_TEST_API_KEY; // Test Store
  if (Platform.OS === 'ios') return REVENUECAT_IOS_API_KEY;
  if (Platform.OS === 'android') return REVENUECAT_ANDROID_API_KEY;
  return REVENUECAT_TEST_API_KEY;
}

let configured = false;
export function initializeRevenueCat() {
  if (!rcEnabled) return;
  Purchases.setLogLevel(__DEV__ ? LOG_LEVEL.DEBUG : LOG_LEVEL.WARN);
  Purchases.configure({ apiKey: getRevenueCatApiKey() });
  configured = true;
}

function useSubscriptionContext() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [appUserId, setAppUserId] = useState<string | null>(null);
  const [identitySettled, setIdentitySettled] = useState(false);
  const [identityError, setIdentityError] = useState<string | null>(null);
  const boundRef = useRef<string | null>(null);
  const active = rcEnabled && configured;

  const setInfo = useCallback((info: CustomerInfo) => queryClient.setQueryData(CUSTOMER_INFO_KEY, info), [queryClient]);

  // IDENTITY — bind purchases to the stable backend user_id; never swallow failures (blocks the buy button).
  useEffect(() => {
    if (!active) return;
    const uid = user?.user_id || null;
    (async () => {
      try {
        if (uid && boundRef.current !== uid) {
          const { customerInfo } = await Purchases.logIn(uid);
          boundRef.current = uid;
          setInfo(customerInfo);
        } else if (!uid && boundRef.current) {
          setInfo(await Purchases.logOut());
          boundRef.current = null;
        }
        setAppUserId(await Purchases.getAppUserID());
        setIdentityError(null);
      } catch (e: any) {
        setIdentityError(String(e?.message || e));
      } finally {
        setIdentitySettled(true);
      }
    })();
  }, [active, user?.user_id, setInfo]);

  // Customer info is fetched only after identity settled, so an anonymous snapshot never overwrites the bound user.
  const customerInfoQuery = useQuery({
    queryKey: CUSTOMER_INFO_KEY,
    queryFn: () => Purchases.getCustomerInfo(),
    enabled: active && identitySettled,
    staleTime: 60 * 1000,
  });

  const offeringsQuery = useQuery({
    queryKey: ['revenuecat', 'offerings'],
    queryFn: () => Purchases.getOfferings(),
    enabled: active,
    staleTime: 300 * 1000,
  });

  // Reactive entitlement updates on native (purchase / restore / renewal). Never poll.
  useEffect(() => {
    if (!active) return;
    const listener = (info: CustomerInfo) => setInfo(info);
    Purchases.addCustomerInfoUpdateListener(listener);
    return () => { Purchases.removeCustomerInfoUpdateListener(listener); };
  }, [active, setInfo]);

  const purchaseMutation = useMutation({
    mutationFn: async (packageToPurchase: PurchasesPackage) => {
      // Choke point: never let an anonymous purchase through.
      const id = await Purchases.getAppUserID();
      if (isAnonymous(id) || (user?.user_id && id !== user.user_id)) throw new Error('identity_not_ready');
      const { customerInfo } = await Purchases.purchasePackage(packageToPurchase);
      setInfo(customerInfo); // Browser Mode has no update listener — write the fresh snapshot explicitly
      return customerInfo;
    },
  });

  const restoreMutation = useMutation({
    mutationFn: async () => {
      const info = await Purchases.restorePurchases();
      setInfo(info);
      return info;
    },
  });

  const entitlement = customerInfoQuery.data?.entitlements.active?.[REVENUECAT_ENTITLEMENT_IDENTIFIER];
  // Add-on subscriptions (addon_*) share the "pro" entitlement but grant NO tier.
  const activeProducts = customerInfoQuery.data?.activeSubscriptions || [];
  const tierProducts = activeProducts.filter(p => !p.toLowerCase().includes('addon_'));
  const activeAddonPackages = activeProducts.filter(p => p.toLowerCase().includes('addon_')).map(p => p.replace(/^pro\./, ''));
  const activeTier: IapTier | null = !entitlement ? null
    : tierProducts.length ? tierProducts.map(iapTierOf).sort((a, b) => TIER_ORDER.indexOf(b) - TIER_ORDER.indexOf(a))[0]
    : entitlement.productIdentifier.toLowerCase().includes('addon_') ? null : iapTierOf(entitlement.productIdentifier);
  const isSubscribed = activeTier !== null;   // add-on-only subscribers are NOT tier subscribers

  const identityReady = !isAnonymous(appUserId) && (!user?.user_id || appUserId === user.user_id) && !identityError;

  return {
    customerInfo: customerInfoQuery.data,
    entitlement,
    activeTier,
    activeAddonPackages,
    offerings: offeringsQuery.data,
    offeringsError: offeringsQuery.error,
    isSubscribed,
    appUserId,
    identityReady,
    identityError,
    isLoading: customerInfoQuery.isLoading || offeringsQuery.isLoading,
    purchase: purchaseMutation.mutateAsync,
    restore: restoreMutation.mutateAsync,
    isPurchasing: purchaseMutation.isPending,
    isRestoring: restoreMutation.isPending,
  };
}

type SubscriptionContextValue = ReturnType<typeof useSubscriptionContext>;
const Context = createContext<SubscriptionContextValue | null>(null);

export function SubscriptionProvider({ children }: { children: React.ReactNode }) {
  const value = useSubscriptionContext();
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useSubscription() {
  const ctx = useContext(Context);
  if (!ctx) throw new Error('useSubscription must be used within a SubscriptionProvider');
  return ctx;
}
