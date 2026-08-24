import React, { useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, ScrollView, Platform, ActivityIndicator, ImageBackground, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import * as Location from 'expo-location';
import Animated, { useSharedValue, useAnimatedStyle, withRepeat, withSequence, withTiming } from 'react-native-reanimated';
import { useAuth } from '@/src/auth';
import { api } from '@/src/api';
import { useAcousticGuard } from '@/src/acoustic';
import { C, S, R } from '@/src/theme';
import { t, Lang } from '@/src/i18n';

const ANGEL_BG = 'https://images.pexels.com/photos/31622917/pexels-photo-31622917.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940';

async function fireBeacon() {
  let lat: number | null = null, lng: number | null = null;
  try {
    if (Platform.OS !== 'web') {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status === 'granted') {
        const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
        lat = pos.coords.latitude; lng = pos.coords.longitude;
      }
    }
  } catch {}
  await api('/beacon/trigger', { method: 'POST', body: JSON.stringify({ lat, lng, note: 'stealth' }) });
}

export default function Home() {
  const { user, setUser } = useAuth();
  const router = useRouter();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const angel = !!user?.angel_mode;
  const [busy, setBusy] = useState(false);
  const [beaconSent, setBeaconSent] = useState(false);

  const toggleAngel = async () => {
    if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
    setBusy(true);
    try {
      const updated: any = await api('/me/prefs', { method: 'PATCH', body: JSON.stringify({ angel_mode: !angel }) });
      setUser(updated as any);
    } finally { setBusy(false); }
  };

  // Emergency Beacon (stealth): long-press the GUARDIAN logo — silent signal + location
  const beacon = async () => {
    try {
      if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      setBeaconSent(true);
      setTimeout(() => setBeaconSent(false), 3000);
      await fireBeacon();
    } catch (e) { console.log('beacon err', e); }
  };

  if (user && (user as any).tos_accepted_version !== '2026-06.1') {
    return <TosGate lang={lang} setUser={setUser} />;
  }

  if (angel) return <AngelHome onToggle={toggleAngel} lang={lang} router={router} onBeacon={beacon} beaconSent={beaconSent} />;

  return (
    <SafeAreaView testID="standard-home" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="brand-beacon" onLongPress={beacon} delayLongPress={700}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
            <Text style={styles.brand}>GUARDIAN</Text>
            {beaconSent && <View testID="beacon-dot" style={styles.beaconDot} />}
          </View>
          <Text style={styles.brandSub}>SOVEREIGN SURVIVAL OS</Text>
        </Pressable>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.lg }}>
          <Pressable testID="angel-toggle" onPress={toggleAngel} disabled={busy} hitSlop={8} style={styles.angelToggle}>
            <Ionicons name="accessibility-outline" size={18} color={C.brand} />
          </Pressable>
          <Pressable testID="home-profile" onPress={() => router.push('/(tabs)/profile')} hitSlop={8}>
            <Ionicons name="settings-outline" size={22} color={C.onS3} />
          </Pressable>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.body}>
        <Text style={styles.greeting}>Dobrý deň,{'\n'}{(user?.name || 'Guardian').split(' ')[0]}.</Text>

        <View style={styles.pillarGrid}>
          <PillarTile testID="pillar-health" icon="heart" title="Health Hub" sub="Trezor · AI prekladač · Physio" onPress={() => router.navigate('/(tabs)/health')} />
          <PillarTile testID="pillar-family" icon="people" title="Family Shield" sub="Angel Mode · Family Pulse" onPress={() => router.navigate('/(tabs)/family')} />
          <PillarTile testID="pillar-legacy" icon="rose" title="Legacy & Wealth" sub="Solidarita · Závet · Fond" onPress={() => router.navigate('/(tabs)/legacy')} />
          <PillarTile testID="pillar-hunter" icon="search" title="The Hunter" sub="Termíny · Zásoby · Blackout" onPress={() => router.navigate('/(tabs)/hunter')} />
        </View>

        <Pressable testID="fab-emergency-qr" onPress={() => router.push('/emergency-qr')} style={styles.sosPill}>
          <Ionicons name="qr-code-outline" size={18} color={C.onError} />
          <Text style={styles.sosPillText}>{t('emergency_qr', lang).toUpperCase()}</Text>
        </Pressable>
        <Text style={styles.beaconHint}>◉ Tichý maják: podržte logo GUARDIAN 1 sekundu</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

function PillarTile({ testID, icon, title, sub, onPress }: any) {
  const press = () => {
    if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
    onPress();
  };
  return (
    <Pressable testID={testID} onPress={press} style={({ pressed }) => [styles.pillar, pressed && { backgroundColor: C.surface3 }]}>
      <View style={styles.pillarIcon}>
        <Ionicons name={icon} size={26} color={C.brand} />
      </View>
      <View>
        <Text style={styles.pillarTitle}>{title}</Text>
        <Text style={styles.pillarSub}>{sub}</Text>
      </View>
    </Pressable>
  );
}

function TosGate({ lang, setUser }: any) {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    (async () => {
      try { const res: any = await api(`/legal/tos?country=SK&language=${lang}`); setText(res.text); } catch (e) { console.log(e); }
    })();
  }, [lang]);
  const accept = async () => {
    setBusy(true);
    try {
      const u: any = await api('/legal/accept', { method: 'POST', body: JSON.stringify({ country: 'SK', language: lang }) });
      setUser(u);
    } finally { setBusy(false); }
  };
  return (
    <SafeAreaView testID="tos-gate" style={{ flex: 1, backgroundColor: C.bg }} edges={['top']}>
      <View style={styles.tosHead}>
        <Ionicons name="shield-checkmark-outline" size={22} color={C.onInverse} />
        <Text style={styles.tosHeadText}>{t('tos_title', lang).toUpperCase()} · v2026-06.1</Text>
      </View>
      <View style={styles.tosBanner}>
        <Text style={styles.tosBannerText}>AI VÝSTUPY SÚ LEN INFORMAČNÉ · POUŽÍVATE ICH NA VLASTNÉ RIZIKO · ÚPLNÉ ZBAVENIE ZODPOVEDNOSTI AUTORA</Text>
      </View>
      <ScrollView contentContainerStyle={{ padding: S.lg }}>
        {text ? <Text style={styles.tosBody}>{text}</Text> : <ActivityIndicator color={C.brand} style={{ marginTop: 40 }} />}
      </ScrollView>
      <Pressable testID="tos-gate-accept" onPress={accept} disabled={busy || !text} style={styles.tosAccept}>
        {busy ? <ActivityIndicator color={C.onInverse} /> : <Text style={styles.tosAcceptText}>{t('tos_accept', lang).toUpperCase()}</Text>}
      </Pressable>
    </SafeAreaView>
  );
}

function AngelHome({ onToggle, lang, router, onBeacon, beaconSent }: any) {
  const scale = useSharedValue(1);
  useEffect(() => {
    scale.value = withRepeat(withSequence(withTiming(1.07, { duration: 1200 }), withTiming(1, { duration: 1200 })), -1);
  }, [scale]);
  const pulse = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));

  // Acoustic Threat Detection — local-only mic metering; on threat: log + Fall-Verify flow
  const acoustic = useAcousticGuard(async (dbLevel: number) => {
    try { await api('/acoustic-event', { method: 'POST', body: JSON.stringify({ kind: 'loud_noise', db_level: dbLevel }) }); } catch {}
    router.push('/fall-verify');
  });

  const callFamily = async () => {
    try {
      const prof: any = await api('/emergency-profile');
      if (prof?.emergency_contact_phone) {
        Linking.openURL(`tel:${prof.emergency_contact_phone}`);
        return;
      }
    } catch {}
    router.push('/emergency-qr');
  };

  return (
    <View testID="angel-home" style={{ flex: 1, backgroundColor: C.bg }}>
      <ImageBackground source={{ uri: ANGEL_BG }} style={{ flex: 1 }} imageStyle={{ opacity: 0.55 }}>
        <View style={styles.angelScrim}>
          <SafeAreaView style={{ flex: 1 }} edges={['top', 'bottom']}>
            <View style={styles.angelTop}>
              <Pressable testID="angel-beacon" onLongPress={onBeacon} delayLongPress={700} hitSlop={10}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                  <Text style={styles.angelWordmark}>GUARDIAN ANGEL</Text>
                  {beaconSent && <View style={styles.beaconDot} />}
                </View>
              </Pressable>
              <Pressable testID="angel-toggle-back" onPress={onToggle} hitSlop={10} style={styles.angelExit}>
                <Ionicons name="close" size={22} color={C.fg} />
              </Pressable>
            </View>
            <View style={styles.acousticRow}>
              <Pressable
                testID="angel-acoustic"
                onPress={acoustic.toggle}
                style={[styles.acousticBtn, acoustic.active && styles.acousticBtnOn]}
              >
                <Ionicons name={acoustic.active ? 'ear' : 'ear-outline'} size={16} color={acoustic.active ? C.onInverse : C.brand} />
                <Text style={[styles.acousticText, acoustic.active && { color: C.onInverse }]}>
                  {acoustic.active ? 'STRÁŽIM ZVUK — LOKÁLNE' : 'AKUSTICKÝ STRÁŽCA'}
                </Text>
              </Pressable>
            </View>

            <View style={styles.angelCenter}>
              <Animated.View style={[styles.jarvisOrbOuter, pulse]}>
                <Pressable
                  testID="angel-jarvis"
                  onPress={() => {
                    if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy).catch(() => {});
                    router.push('/wellness');
                  }}
                  style={styles.jarvisOrb}
                >
                  <Ionicons name="mic" size={64} color={C.onInverse} />
                </Pressable>
              </Animated.View>
              <Text style={styles.jarvisLabel}>HOVORIŤ S JARVISOM</Text>
            </View>

            <View style={styles.angelBottom}>
              <Pressable testID="angel-sos" onPress={() => router.push('/fall-verify')} style={[styles.angelEmg, { backgroundColor: C.error }]}>
                <Ionicons name="alert" size={44} color={C.onError} />
              </Pressable>
              <Pressable testID="angel-family" onPress={callFamily} style={styles.angelEmg}>
                <Ionicons name="call" size={44} color={C.brand} />
              </Pressable>
              <Pressable testID="angel-doctor" onPress={() => router.navigate('/(tabs)/hunter')} style={styles.angelEmg}>
                <Ionicons name="medkit" size={44} color={C.brand} />
              </Pressable>
            </View>
          </SafeAreaView>
        </View>
      </ImageBackground>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.lg, paddingVertical: S.md, backgroundColor: C.bg, borderBottomWidth: 1, borderBottomColor: C.border },
  brand: { color: C.fg, fontSize: 22, fontWeight: '900', letterSpacing: 2 },
  brandSub: { color: C.info, fontSize: 10, letterSpacing: 2, marginTop: 2 },
  angelToggle: { flexDirection: 'row', alignItems: 'center', gap: 6, borderWidth: 1.5, borderColor: C.brand, borderRadius: R.sm, paddingHorizontal: S.md, paddingVertical: 8 },
  body: { padding: S.lg, paddingBottom: 120 },
  greeting: { fontSize: 26, fontWeight: '900', color: C.fg, letterSpacing: 0.5, lineHeight: 34 },
  pillarGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: S.md, marginTop: S.xl },
  pillar: { width: '48%', flexGrow: 1, minHeight: 156, backgroundColor: C.surface2, borderWidth: 1, borderColor: C.border, borderRadius: R.md, padding: S.lg, justifyContent: 'space-between', gap: S.lg },
  pillarIcon: { width: 48, height: 48, borderRadius: R.pill, backgroundColor: C.brandTer, alignItems: 'center', justifyContent: 'center' },
  pillarTitle: { color: C.fg, fontWeight: '800', fontSize: 16, letterSpacing: 0.3 },
  pillarSub: { color: C.info, fontSize: 11, marginTop: 4, lineHeight: 15 },
  sosPill: { marginTop: S.xl, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: S.sm, backgroundColor: C.error, borderRadius: R.pill, paddingVertical: S.lg, minHeight: 52 },
  sosPillText: { color: C.onError, fontWeight: '900', letterSpacing: 2, fontSize: 13 },
  beaconDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: C.error },
  beaconHint: { marginTop: S.md, fontSize: 9, letterSpacing: 1, color: C.onS3, fontWeight: '700', textAlign: 'center' },
  tosHead: { flexDirection: 'row', alignItems: 'center', gap: S.md, paddingHorizontal: S.lg, paddingVertical: S.md, backgroundColor: C.inverse },
  tosHeadText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 14 },
  tosBanner: { backgroundColor: C.warn, padding: S.md },
  tosBannerText: { color: C.onWarn, fontWeight: '900', fontSize: 10, letterSpacing: 0.5 },
  tosBody: { fontSize: 12, lineHeight: 18, color: C.fg, fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }) },
  tosAccept: { backgroundColor: C.brand, paddingVertical: S.lg, alignItems: 'center', margin: S.lg, borderRadius: R.sm },
  tosAcceptText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 15 },
  // Angel Mode (radical reset)
  angelScrim: { flex: 1, backgroundColor: 'rgba(18,18,18,0.6)' },
  angelTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.lg, paddingTop: S.md },
  angelWordmark: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 14 },
  angelExit: { width: 44, height: 44, borderRadius: R.pill, backgroundColor: 'rgba(44,44,46,0.85)', alignItems: 'center', justifyContent: 'center' },
  acousticRow: { alignItems: 'center', marginTop: S.md },
  acousticBtn: { flexDirection: 'row', alignItems: 'center', gap: 8, borderWidth: 1.5, borderColor: C.brand, borderRadius: R.pill, paddingHorizontal: S.lg, minHeight: 44, backgroundColor: 'rgba(18,18,18,0.55)' },
  acousticBtnOn: { backgroundColor: C.brand },
  acousticText: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 1.5 },
  angelCenter: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: S.xl },
  jarvisOrbOuter: { width: 210, height: 210, borderRadius: 105, backgroundColor: 'rgba(212,175,55,0.18)', alignItems: 'center', justifyContent: 'center' },
  jarvisOrb: { width: 164, height: 164, borderRadius: 82, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center', borderWidth: 3, borderColor: C.brandSec },
  jarvisLabel: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 16 },
  angelBottom: { flexDirection: 'row', justifyContent: 'space-evenly', alignItems: 'center', paddingBottom: S.xxl, paddingTop: S.lg },
  angelEmg: { width: 96, height: 96, borderRadius: 48, backgroundColor: C.surface2, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: C.borderStrong },
});
