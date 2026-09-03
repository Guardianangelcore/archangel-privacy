/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import { Stack, useRouter, useSegments } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect } from "react";
import { LogBox, View, Text, ActivityIndicator, Platform, Alert } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";
import * as Notifications from "expo-notifications";
import * as Linking from "expo-linking";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useIconFonts } from "@/src/hooks/use-icon-fonts";
import { AuthProvider, useAuth } from "@/src/auth";
import { I18nProvider } from "@/src/i18n-context";
import { initializeRevenueCat, SubscriptionProvider } from "@/src/revenuecat";
import { useIapMirror } from "@/src/iap-mirror";
import { registerForPush } from "@/src/push";
import GuardianMonitor from "@/src/guardian";
import { C } from "@/src/theme";
import { GA_ORIGIN_MARK } from "@/src/watermark";
import { BiometricGate } from "@/src/biometric-gate";
import { DemoBanner } from "@/src/DemoMode";   // DEMO_ONLY
import { JudgeTourOverlay } from "@/src/judge-tour";   // DEMO_ONLY — 3-minute judge walkthrough
import { LaunchSequence } from "@/src/LaunchSequence";   // cinematic intro (every start) → onboarding (first launch)
import { OnboardingTour } from "@/src/onboarding-tour";
import { startPanicGesture } from "@/src/panic-gesture";
import { CrisisHUD } from "@/src/CrisisHUD";
import { useDemoMode } from "@/src/demo-mode";

// COMPETITION DEMO BADGE — small pill, top-right, on all screens (toggle in Settings)
function DemoBadge() {
  const on = useDemoMode();
  if (!on) return null;
  return (
    <View
      testID="demo-badge"
      pointerEvents="none"
      style={{
        position: "absolute", top: Platform.OS === "web" ? 8 : 52, right: 10, zIndex: 9999,
        backgroundColor: "rgba(212,175,55,0.16)", borderColor: "rgba(212,175,55,0.6)",
        borderWidth: 1, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 3,
      }}
    >
      <Text style={{ color: "#D4AF37", fontSize: 9, fontWeight: "900", letterSpacing: 2 }}>DEMO</Text>
    </View>
  );
}

LogBox.ignoreAllLogs(true);
SplashScreen.preventAutoHideAsync();

// REVENUECAT — SDK init ONCE at module scope (before any component mounts). A config error must never crash the app.
try {
  initializeRevenueCat();
} catch (err) {
  console.warn("RevenueCat unavailable:", err);
}
const queryClient = new QueryClient();

// Push: foreground display behaviour — MODULE SCOPE
if (Platform.OS !== "web") {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowAlert: true,
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });
}

// Push: Android channel — MODULE SCOPE
if (Platform.OS === "android") {
  Notifications.setNotificationChannelAsync("default", {
    name: "Default",
    importance: Notifications.AndroidImportance.MAX,
    sound: "default",
  });
}

function RootNav() {
  const { user, loading } = useAuth();
  const segments = useSegments();
  const router = useRouter();
  // IAP → tier mirror (renewals / restores / lapses) whenever RevenueCat CustomerInfo changes
  useIapMirror();

  useEffect(() => {
    if (loading) return;
    const seg0 = segments[0] as string | undefined;
    const inAuthGroup = seg0 === 'login' || seg0 === undefined || seg0 === 'index';
    const isPublic = seg0 === 'drop' || seg0 === 'terms-of-service' || seg0 === 'privacy-policy'; // public — no login
    if (isPublic) return;
    if (!user && !inAuthGroup) {
      router.replace('/login');
    } else if (user && (seg0 === 'login' || seg0 === 'index' || seg0 === undefined)) {
      router.replace('/(tabs)');
    }
  }, [user, loading, segments]);

  // Push: register token on login / app open (tokens rotate)
  useEffect(() => {
    if (user?.user_id) registerForPush(user.user_id);
  }, [user?.user_id]);

  // SILENT WITNESS PANIC GESTURE — global back-of-phone tap listener.
  // Only armed when a real user is logged in (avoid firing on login screen).
  useEffect(() => {
    if (!user?.user_id) return;
    const cleanup = startPanicGesture(async () => {
      try {
        // 1) Open a Silent Witness session immediately (silent — no confirm)
        const { api } = await import('@/src/api');
        const opened: any = await api('/silent-witness/session', { method: 'POST' });
        // 2) Route to the Silent Witness screen so recording UI can start
        router.push(`/silent-witness?panic=1&sid=${opened.session_id}`);
      } catch {
        router.push('/silent-witness?panic=1');
      }
    });
    return cleanup;
  }, [user?.user_id, router]);

  // Push: tap handlers + denied-permission nudge
  useEffect(() => {
    if (Platform.OS === "web") return;

    const openFrom = (data: any) => {
      const url = data?.deeplink || data?.action_url;
      if (!url) return;
      if (typeof url === "string" && url.startsWith("http")) Linking.openURL(url);
      else router.push(url);
    };

    const tapSub = Notifications.addNotificationResponseReceivedListener((response) => {
      openFrom(response.notification.request.content.data || {});
    });

    Notifications.getLastNotificationResponseAsync().then((response) => {
      if (response) openFrom(response.notification.request.content.data || {});
    });

    (async () => {
      try {
        const { status, canAskAgain } = await Notifications.getPermissionsAsync();
        if (status !== "denied" || canAskAgain) return;
        const lastNudge = await AsyncStorage.getItem("pushNudgeAt");
        const oneWeek = 7 * 24 * 60 * 60 * 1000;
        if (lastNudge && Date.now() - Number(lastNudge) <= oneWeek) return;
        Alert.alert(
          "Notifications are off",
          "Turn on notifications so you never miss a found appointment or a safety alert.",
          [
            { text: "Later", onPress: () => AsyncStorage.setItem("pushNudgeAt", String(Date.now())) },
            {
              text: "Open settings",
              onPress: async () => {
                await AsyncStorage.setItem("pushNudgeAt", String(Date.now()));
                Linking.openSettings();
              },
            },
          ]
        );
      } catch {}
    })();

    return () => {
      tapSub.remove();
    };
  }, []);

  if (loading) {
    return (
      <View testID="app-loading" style={{ flex: 1, backgroundColor: C.bg, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator size="large" color={C.brand} />
        <Text style={{ marginTop: 12, color: C.fg, fontWeight: '700', letterSpacing: 1 }}>DECRYPTING IDENTITY…</Text>
      </View>
    );
  }
  return (
    <>
      <GuardianMonitor />
      <DemoBanner />
      <BiometricGate>
        <Stack screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: C.bg },
          // 60FPS native-driver transitions (react-native-screens) + memory freeze off-screen
          animation: Platform.OS === 'web' ? 'none' : 'slide_from_right',
          animationDuration: 240,
          freezeOnBlur: true,
          gestureEnabled: true,
        }} />
        {/* SENTIENT ONBOARDING — 30-second Sovereign Tour on first launch (Onyx narrated) */}
        <OnboardingTour />
        <JudgeTourOverlay />
        <LaunchSequence />
        {/* COGNITIVE TRIAGE — auto Crisis HUD when biometrics cross distress threshold */}
        <CrisisHUD />
      </BiometricGate>
      {/* COMPETITION DEMO BADGE — toggle in Settings → Demo Mode */}
      <DemoBadge />
      {/* Hidden digital watermark — original Guardian Angel build fingerprint */}
      <Text
        accessibilityElementsHidden
        importantForAccessibility="no-hide-descendants"
        style={{ position: "absolute", opacity: 0, width: 1, height: 1, left: -9999 }}
      >
        {GA_ORIGIN_MARK}
      </Text>
    </>
  );
}

export default function RootLayout() {
  const [loaded, error] = useIconFonts();

  useEffect(() => {
    if (loaded || error) SplashScreen.hideAsync();
  }, [loaded, error]);

  if (!loaded && !error) return null;

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <SubscriptionProvider>
              <I18nProvider>
                <RootNav />
              </I18nProvider>
            </SubscriptionProvider>
          </AuthProvider>
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
