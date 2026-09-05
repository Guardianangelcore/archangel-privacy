# RevenueCat — integrated (2026-09-02)
This file is supposed to serve as a memory to you if you have to interact with user's RevenueCat account via integration proxy at any later point in time.

## Identifiers (from /setup response — copy verbatim)
- rc_project_id: proj10bfa652
- apple_app_id: app243f8b9cb6
- play_app_id: appec61efb634
- bundle_id / package_name: com.emergent.angelos.qvqss9
- entitlement_lookup_key: pro
- offering_lookup_key: default
- Packages (package -> product_id, current price) — ALL EUR-only Test Store products (single currency ⇒ SDK falls back to EUR in any locale; mixing USD+EUR made RC drop the EUR-only products in en-US previews):
  - guardian_monthly  -> proda0bf31c009  (pro.guardian_monthly,  €9 / P1M)
  - guardian_annual   -> prod1beb2d0696  (pro.guardian_annual,   €86 / P1Y)
  - sentinel_monthly_v2  -> prod5eade6865b  (pro.sentinel_monthly_v2,  €99 / P1M)   ← 2026-09-05 price update
  - sentinel_annual_v2   -> prod4b0645a2e3  (pro.sentinel_annual_v2,   €950 / P1Y)
  - archangel_monthly_v2 -> prod0fc2b47780  (pro.archangel_monthly_v2, €299 / P1M)
  - archangel_annual_v2  -> prodb516e31007  (pro.archangel_annual_v2,  €2990 / P1Y)
  - RETIRED (2026-09-05, NOT in the offering any more): sentinel_monthly prod698da21987 (€149), sentinel_annual prod8f5bf13a41 (€1490),
    archangel_monthly prod0f64cd08e6 (€499), archangel_annual prod8f12402bd8 (€4990). Test Store products are IMMUTABLE — a /products
    upsert with a new price returns 200 but the offering keeps the old price; DELETE detaches the package from the offering (the product
    itself stays if it has test transactions → 422, harmless). Price changes ⇒ always create *_vN packages + DELETE the old ones + update
    frontend/src/revenuecat.tsx IAP_PACKAGES. Backend iap_tier() matches by substring ("sentinel"/"archangel"), so v2 ids need no change.
  - ADD-ON SUBSCRIPTIONS (Iter 79, same "pro" entitlement, grant NO tier — backend routes/store.py ADDON_BY_RC_PRODUCT):
    - addon_perplexity_ultra_monthly -> prod74c8bb3982 (pro.addon_perplexity_ultra_monthly, €5 / P1M)
    - addon_premium_voice_monthly    -> prodfa6faead38 (pro.addon_premium_voice_monthly,    €3 / P1M)
    Client sends CustomerInfo.activeSubscriptions (+allExpirationDates) as `active_subscriptions` in /subscription/iap-sync; tier = best non-addon product, add-ons → users.addon_subs/addons_active (72 h grace, status active/expired). GET /store/addons/status.
  - LEGACY: $rc_monthly (pro.monthly, USD 9.99) could not be deleted (has test transactions) but is no longer in the offering; $rc_annual deleted. Never re-add USD packages.
- Tier mapping (one entitlement "pro" for all tiers): product id containing "archangel" → archangel, "sentinel" → sentinel, else guardian (backend routes/subscription.py iap_tier(), frontend src/revenuecat.tsx iapTierOf() + IAP_PACKAGES). Sovereign = free default, no product.
- entitlement_products.pro: prod88faf8e237, prod6547915e81, prodb7e5fb979b, prod9a550d12a1, prod54feb91c3d, prod842d5b8add (Test Store + Apple/Play mirrors)
- Dashboard: https://app.revenuecat.com/projects/proj10bfa652
- SDK keys live ONLY in frontend/.env (EXPO_PUBLIC_REVENUECAT_TEST_API_KEY / _IOS_API_KEY / _ANDROID_API_KEY) — never copy them here.

## App wiring
- frontend/src/revenuecat.tsx — SubscriptionProvider / useSubscription (entitlement "pro"), initializeRevenueCat() called at module scope in app/_layout.tsx (inside QueryClientProvider > AuthProvider > SubscriptionProvider > I18nProvider).
  Identity lives IN the provider (it sits inside AuthProvider): Purchases.logIn(user_id) on every auth path, logOut on sign-out; `identityError` surfaced; `identityReady` = Purchases.getAppUserID() === user_id (NOT originalAppUserId — that legitimately stays $RCAnonymousID after alias). Browser Mode has no customer-info listener → purchase/restore/logIn write CustomerInfo into the query cache explicitly.
- frontend/src/IapPurchase.tsx — IapBuyButton (period monthly|annual, price from offerings, custom confirm modal, "simulated" label) + RestorePurchasesButton. Used in app/subscription.tsx (Guardian card, testID sb-iap-guardian; restore in MANAGE section) and src/Paywall.tsx (tier="guardian" → Jarvis gate).
- frontend/src/iap-mirror.ts — syncIapEntitlement(info, appUserId) → POST /api/subscription/iap-sync; useIapMirror() in RootNav mirrors renewals/restores/lapses whenever CustomerInfo changes (only if entitlements.all.pro exists).
- Tier mirror (user requirement): active `pro` entitlement → users.tier="guardian", tier_until=expires, tier_paid_with="iap" → Jarvis gate + GA-T loyalty allocation (100 GA-T/30d, start_subscription_allocation). Lapse → downgrade to sovereign only if tier_paid_with=="iap". Never downgrades a higher tier. Client entitlement remains the source of truth; no webhooks / no RC REST calls.
- In-app CANCEL button hidden for paid_with=="iap" (store manages renewal); note sb-iap-note shown instead.
- Test Store (web preview / Expo Go): purchase opens RevenueCat's own "Test Store Purchase" HTML dialog (Test valid purchase / Test failed purchase / Cancel); subscriptions last ~5 min then lapse → mirror downgrades.
- .env GOTCHA (fixed 2026-09-02): the TEST key had been appended WITHOUT newline onto the protected EXPO_PACKAGER_PROXY_URL line — always `printf '\n...'` when appending.

## Check for project_state in revenuecat status api response. if the project_state is less then project_created, re-fetch RevenueCat playbook via the integration expert tool.
Status check:
`curl -sS -H "$AUTH" "$INTEGRATION_PROXY_URL/internal/revenuecat/projects/f0fab338-47bc-4384-9882-3cf2c8a64656/status"`
→ `{"connection_state":"connected","project_state":"...","rc_project_id":"..."}`

## Later updates to user's products (integration proxy apis ONLY — NEVER call the RevenueCat REST API)
- Change price/duration/trial OR add a package (upsert):
  POST $INTEGRATION_PROXY_URL/internal/revenuecat/projects/f0fab338-47bc-4384-9882-3cf2c8a64656/products
  body: {"products":[{"package":"$rc_monthly","price":14.99,"currency":"USD",
         "period":"P1M","trial":"P1W",
         "prices":[{"amount_micros":14990000,"currency":"USD"}]}]}
  (amount_micros = price × 1,000,000; omit "trial" for none)
- Remove a package:
  DELETE $INTEGRATION_PROXY_URL/internal/revenuecat/projects/f0fab338-47bc-4384-9882-3cf2c8a64656/products/%24rc_monthly
  ($ -> %24)
- Recover identifiers / repopulate .env: re-run the idempotent /setup call.

## Taking in-app purchases LIVE — store-side steps (USER does these — agent cannot verify or perform)
Needed ONLY for REAL purchases in published store builds. Test Store (Expo Go / web preview / dev build) needs none of this.
- Step 1 — Upload App Store / Play Store credentials to the RevenueCat dashboard (Home → project → Apps → App name)
  - iOS: In-app purchase key configuration — https://www.revenuecat.com/docs/service-credentials/itunesconnect-app-specific-shared-secret/in-app-purchase-key-configuration
    App Store Connect API key — https://www.revenuecat.com/docs/service-credentials/itunesconnect-app-specific-shared-secret/app-store-connect-api-key-configuration
  - Android: Google Play service-account credentials JSON — https://www.revenuecat.com/docs/service-credentials/creating-play-service-credentials
- Step 2 — Set up payment profiles in App Store Connect and Play Console
  - https://developer.apple.com/help/app-store-connect/configure-in-app-purchase-settings/overview-for-configuring-in-app-purchases/
  - https://support.google.com/googleplay/android-developer/answer/7161426
- Step 3 — Create matching in-app purchase products in App Store Connect and Google Play using the SAME product IDs shown in the RevenueCat dashboard
  - https://developer.apple.com/help/app-store-connect/manage-subscriptions/offer-auto-renewable-subscriptions/
  - https://support.google.com/googleplay/android-developer/answer/140504
- Step 4 — Release build → TestFlight / Play internal testing → submit for review.
All the steps needed to integrate RevenueCat in their production app are present in FAQ section of payments panel.

## 2026-09-05 — server-side verification (security audit SEC-001)
- Backend `/subscription/iap-sync` re-fetches `GET https://api.revenuecat.com/v1/subscribers/{app_user_id}` with the PUBLIC SDK keys (backend/.env REVENUECAT_PUBLIC_KEY_TEST/IOS/ANDROID) before granting any tier/GA-T. Read-only; still no secret key, no webhook, no provisioning via REST (all provisioning stays on the integration proxy).
