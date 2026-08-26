/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// HOME 2026 — Glass/Luxe command center: Guardian Lens FAB, glass pillars, breathing Jarvis
import React, { useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, ScrollView, Platform, ActivityIndicator, ImageBackground, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import * as Haptics from 'expo-haptics';
import * as Location from 'expo-location';
import Animated, { useSharedValue, useAnimatedStyle, withRepeat, withSequence, withTiming, Easing, cancelAnimation } from 'react-native-reanimated';
import { useAuth } from '@/src/auth';
import { api } from '@/src/api';
import { useAcousticGuard } from '@/src/acoustic';
import { C, S, R, GOLD } from '@/src/theme';
import { GlassCard, tap } from '@/src/ui/glass';
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
          <Text style={styles.brandSub}>{t('brand_sub', lang)}</Text>
        </Pressable>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.lg }}>
          <Pressable testID="home-jarvis" onPress={() => { tap(); router.push('/jarvis'); }} hitSlop={8}>
            <Ionicons name="sparkles" size={20} color={C.brand} />
          </Pressable>
          <Pressable testID="angel-toggle" onPress={toggleAngel} disabled={busy} hitSlop={8} style={styles.angelToggle}>
            <Ionicons name="accessibility-outline" size={18} color={C.brand} />
          </Pressable>
          <Pressable testID="home-profile" onPress={() => { tap(); router.push('/(tabs)/profile'); }} hitSlop={8}>
            <Ionicons name="settings-outline" size={22} color={C.onS3} />
          </Pressable>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.body}>
        <Text style={styles.greeting}>{t('greeting_hello', lang)}{'\n'}<Text style={{ color: C.brand }}>{(user?.name || 'Guardian').split(' ')[0]}.</Text></Text>

        {/* JARVIS PRESENCE — pulsing AI Orb, the primary welcome interface */}
        <HomeOrb lang={lang} onPress={() => { tap('heavy'); router.push('/jarvis'); }} />

        {/* THE HEALING CAROUSEL — the ENGINE of the app: injury → money → doctor → papers → fit */}
        <HealingStrip router={router} />

        <GlassCard testID="home-daily-brief" onPress={() => router.push('/daily-brief')} pad={S.md} style={{ marginTop: S.lg }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.md }}>
            <View style={styles.briefIcon}><Ionicons name="sunny" size={22} color={C.brand} /></View>
            <View style={{ flex: 1 }}>
              <Text style={styles.briefTitle}>{t('daily_brief', lang)}</Text>
              <Text style={styles.briefSub}>{t('daily_brief_sub', lang)}</Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color={C.info} />
          </View>
        </GlassCard>

        {/* ONE-LENS SYSTEM — quick action */}
        <GlassCard testID="home-lens" onPress={() => router.push('/lens')} pad={S.md} style={{ marginTop: S.md }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.md }}>
            <LinearGradient colors={GOLD as any} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.lensMini}>
              <Ionicons name="aperture" size={26} color={C.onInverse} />
            </LinearGradient>
            <View style={{ flex: 1 }}>
              <Text style={styles.briefTitle}>GUARDIAN LENS</Text>
              <Text style={styles.briefSub}>{t('lens_sub', lang)}</Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color={C.info} />
          </View>
        </GlassCard>

        {/* SOVEREIGN TRIANGLE — the three pillars of the OS */}
        <View style={styles.pillarGrid}>
          <PillarTile testID="pillar-health" icon="sync-circle" title="Moje uzdravovanie" sub="Kolotoč: žiadanka → peniaze → doktor → fyzio" onPress={() => router.navigate('/(tabs)/health')} />
          <PillarTile testID="pillar-family" icon="people" title="Rodinný štít" sub="Angel Mode · Kúzelná lupa · Voice Echoes · SOS" onPress={() => router.navigate('/(tabs)/family')} />
          <PillarTile testID="pillar-legacy" icon="shield-checkmark" title="Suverénny trezor" sub="Majetok a poistky · Večný odkaz · Bunker mód" onPress={() => router.navigate('/(tabs)/legacy')} />
        </View>

        <View style={styles.ecoRow}>
          <Pressable testID="home-token" onPress={() => { tap(); router.push('/token'); }} style={({ pressed }) => [styles.ecoTile, pressed && { backgroundColor: C.surface3 }]}>
            <Ionicons name="diamond" size={18} color={C.brand} />
            <Text style={styles.ecoText}>{t('gat_wallet', lang)}</Text>
          </Pressable>
          <Pressable testID="home-fortress" onPress={() => { tap(); router.push('/fortress'); }} style={({ pressed }) => [styles.ecoTile, pressed && { backgroundColor: C.surface3 }]}>
            <Ionicons name="shield-half" size={18} color={C.brand} />
            <Text style={styles.ecoText}>{t('cyber_fortress', lang)}</Text>
          </Pressable>
        </View>

        <Pressable testID="fab-emergency-qr" onPress={() => { tap('heavy'); router.push('/emergency-qr'); }} style={styles.sosPill}>
          <Ionicons name="qr-code-outline" size={18} color={C.onError} />
          <Text style={styles.sosPillText}>{t('emergency_qr', lang).toUpperCase()}</Text>
        </Pressable>
        <Text style={styles.beaconHint}>{t('beacon_hint', lang)}</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

// ---- JARVIS PRESENCE — breathing AI Orb on the home screen (mood-aware) ----
const ORB_MOOD: Record<string, { color: string; glow: string; dur: number }> = {
  calm: { color: '#D4AF37', glow: 'rgba(212,175,55,0.35)', dur: 2600 },
  energetic: { color: '#FFD75E', glow: 'rgba(255,215,94,0.4)', dur: 1200 },
  thinking: { color: '#9B6DFF', glow: 'rgba(155,109,255,0.4)', dur: 900 },
  concerned: { color: '#4A90D9', glow: 'rgba(74,144,217,0.4)', dur: 2000 },
  alert: { color: '#FF453A', glow: 'rgba(255,69,58,0.45)', dur: 700 },
};
const HOME_ORB = 150;

function HomeOrb({ lang, onPress }: { lang: Lang; onPress: () => void }) {
  const [agent, setAgent] = useState<any>(null);
  const [geo, setGeo] = useState<any>(null);
  useEffect(() => {
    (async () => { try { setAgent(await api('/agent/state')); } catch {} })();
    (async () => { try { const g: any = await api('/geo/context'); setGeo(g.geo); } catch {} })();
  }, []);
  const cfg = ORB_MOOD[agent?.mood as string] || ORB_MOOD.calm;
  const breath = useSharedValue(0);
  useEffect(() => {
    cancelAnimation(breath);
    breath.value = 0;
    breath.value = withRepeat(withTiming(1, { duration: cfg.dur, easing: Easing.inOut(Easing.sin) }), -1, true);
  }, [cfg.dur, breath]);
  const core = useAnimatedStyle(() => ({ transform: [{ scale: 1 + breath.value * 0.05 }] }));
  const glow = useAnimatedStyle(() => ({
    opacity: 0.4 + breath.value * 0.5,
    transform: [{ scale: 1.08 + breath.value * 0.18 }],
  }));
  return (
    <View style={styles.orbWrap}>
      <Animated.View pointerEvents="none" style={[styles.orbGlow, { backgroundColor: cfg.glow }, glow]} />
      <Animated.View style={core}>
        <Pressable testID="home-orb" onPress={onPress} style={[styles.orbCore, { borderColor: cfg.color, shadowColor: cfg.color }]}>
          <View style={[styles.orbInner, { backgroundColor: cfg.color }]} />
          <Ionicons name="sparkles" size={40} color={cfg.color} />
          <Text style={[styles.orbLvl, { color: cfg.color }]}>LVL {agent?.level ?? 1}</Text>
        </Pressable>
      </Animated.View>
      <Text style={styles.orbTitle}>JARVIS</Text>
      <Text style={styles.orbSub}>{t('orb_sub', lang)}</Text>
      {!!geo && <Text style={styles.orbGeo}>📍 {geo.city} · {geo.country}</Text>}
    </View>
  );
}

// ---- THE HEALING CAROUSEL STRIP — the engine of the app on the home screen ----
const HEAL_FALLBACK_META: Record<string, { title: string; icon: string }> = {
  intake: { title: 'Príjem', icon: 'scan' },
  financial_shield: { title: 'Peniaze', icon: 'umbrella' },
  access: { title: 'Doktor', icon: 'search' },
  bureaucracy: { title: 'PN', icon: 'document-text' },
  recovery: { title: 'Fyzio', icon: 'body' },
};

function HealingStrip({ router }: any) {
  const [hs, setHs] = useState<any>(null);
  useEffect(() => { (async () => { try { setHs(await api('/healing/state')); } catch {} })(); }, []);
  const keys: string[] = hs?.step_keys || Object.keys(HEAL_FALLBACK_META);
  const meta = hs?.steps_meta || {};
  const steps = hs?.journey?.steps || {};
  return (
    <GlassCard testID="home-healing" onPress={() => { tap('medium'); router.push('/healing'); }} pad={S.md} style={{ marginTop: S.lg }} glow>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <Text style={styles.healTitle}>⚙️ KOLOTOČ UZDRAVENIA</Text>
        <Text style={styles.healPct}>{hs?.active ? `${hs.progress_pct} %` : 'MOTOR APPKY'}</Text>
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: S.sm, paddingTop: S.md }}>
        {keys.map((k, i) => {
          const done = steps[k] === 'done';
          const m = meta[k] || HEAL_FALLBACK_META[k];
          return (
            <View key={k} style={[styles.healStep, done && styles.healStepOn]}>
              <Ionicons name={(m?.icon || 'ellipse') as any} size={18} color={done ? C.onInverse : C.brand} />
              <Text style={[styles.healStepText, done && { color: C.onInverse }]}>{i + 1}. {(m?.title || k).toUpperCase()}</Text>
            </View>
          );
        })}
      </ScrollView>
      <Text style={styles.healSub}>
        {hs?.active
          ? `${hs.journey.kind_label} · ${hs.journey.specialty} — Jarvis riadi celú cestu k 100 % fit`
          : 'Úraz či choroba? 1 ťuk — poistka platí hneď, doktor nájdený, neschopenka strážená.'}
      </Text>
    </GlassCard>
  );
}

// ---- THE COMPANION — empathetic caregiver check-in (Angel Shield 2.0) ----
function CompanionCard() {
  const [g, setG] = useState<any>(null);
  const [reply, setReply] = useState('');
  useEffect(() => { (async () => { try { setG(await api('/companion/greeting')); } catch {} })(); }, []);
  const answer = async (mood: number) => {
    tap('medium');
    try {
      const r: any = await api('/companion/checkin', { method: 'POST', body: JSON.stringify({ mood, topic: g?.topic }) });
      setReply(r.reply);
    } catch (e) { console.log(e); }
  };
  if (!g) return null;
  return (
    <View testID="angel-companion" style={styles.compCard}>
      <Text style={styles.compQ}>{g.question}</Text>
      {!!g.care_note && <Text style={styles.compCare}>{g.care_note}</Text>}
      {reply ? (
        <Text testID="companion-reply" style={styles.compReply}>💛 {reply}</Text>
      ) : g.answered_today ? (
        <Text style={styles.compReply}>Dnes ste mi už odpovedali — ďakujem. 💛</Text>
      ) : (
        <View style={{ flexDirection: 'row', gap: S.md, marginTop: S.md }}>
          {([[5, '😊'], [3, '😐'], [1, '😞']] as const).map(([m, e]) => (
            <Pressable key={m} testID={`companion-mood-${m}`} onPress={() => answer(m)} style={styles.compBtn}>
              <Text style={{ fontSize: 36 }}>{e}</Text>
            </Pressable>
          ))}
        </View>
      )}
    </View>
  );
}

// ---- VOICE ECHOES CARD — family voice-stream, one tap, no menus ----
function VoiceEchoCard({ router }: any) {
  const [unheard, setUnheard] = useState(0);
  useEffect(() => { (async () => { try { const r: any = await api('/family/echoes'); setUnheard(r.unheard || 0); } catch {} })(); }, []);
  return (
    <Pressable testID="angel-voice-echoes" onPress={() => { tap('heavy'); router.push('/voice-echoes'); }} style={styles.angelBigCard}>
      <View style={styles.angelBigIcon}>
        <Ionicons name="heart" size={32} color={C.onInverse} />
        {unheard > 0 && <View style={styles.echoBadge}><Text style={styles.echoBadgeText}>{unheard}</Text></View>}
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.angelBigTitle}>ODKAZY OD RODINY</Text>
        <Text style={styles.angelBigSub}>{unheard > 0 ? `Máte ${unheard} nové odkazy — ťuknite a vypočujte si ich.` : 'Vypočujte si hlasové odkazy od najbližších.'}</Text>
      </View>
      <Ionicons name="chevron-forward" size={22} color={C.brand} />
    </Pressable>
  );
}

function PillarTile({ testID, icon, title, sub, onPress }: any) {  return (
    <View style={{ width: '48%', flexGrow: 1 }}>
      <GlassCard testID={testID} onPress={onPress} pad={S.lg} radius={R.md}>
        <View style={{ minHeight: 118, justifyContent: 'space-between', gap: S.md }}>
          <View style={styles.pillarIcon}>
            <Ionicons name={icon} size={24} color={C.brand} />
          </View>
          <View>
            <Text style={styles.pillarTitle}>{title}</Text>
            <Text style={styles.pillarSub}>{sub}</Text>
          </View>
        </View>
      </GlassCard>
    </View>
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

            <ScrollView contentContainerStyle={styles.angelScroll} showsVerticalScrollIndicator={false}>
              {/* THE COMPANION — Jarvis as a caregiver, not an alarm clock */}
              <CompanionCard />

              <View style={{ alignItems: 'center', gap: S.md, marginTop: S.lg }}>
                <Animated.View style={[styles.jarvisOrbOuter, pulse]}>
                  <Pressable
                    testID="angel-jarvis"
                    onPress={() => {
                      if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy).catch(() => {});
                      router.push('/jarvis');
                    }}
                    style={styles.jarvisOrb}
                  >
                    <Ionicons name="mic" size={52} color={C.onInverse} />
                  </Pressable>
                </Animated.View>
                <Text style={styles.jarvisLabel}>HOVORIŤ S JARVISOM</Text>
              </View>

              {/* MAGIC LENS — one tap: photograph a label, Jarvis reads it aloud */}
              <Pressable testID="angel-magic-lens" onPress={() => { tap('heavy'); router.push('/lens'); }} style={styles.angelBigCard}>
                <View style={styles.angelBigIcon}><Ionicons name="aperture" size={32} color={C.onInverse} /></View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.angelBigTitle}>KÚZELNÁ LUPA</Text>
                  <Text style={styles.angelBigSub}>Odfoťte krabičku lieku či noviny — prečítam vám to nahlas.</Text>
                </View>
                <Ionicons name="chevron-forward" size={22} color={C.brand} />
              </Pressable>

              {/* FAMILY VOICE-STREAM */}
              <VoiceEchoCard router={router} />

              <Pressable testID="angel-daily-brief" onPress={() => { tap(); router.push('/daily-brief'); }} style={[styles.angelBrief, { alignSelf: 'center', marginTop: S.md }]}>
                <Ionicons name="sunny" size={22} color={C.brand} />
                <Text style={styles.angelBriefText}>MÔJ DEŇ</Text>
              </Pressable>
            </ScrollView>

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
  greeting: { fontSize: 28, fontWeight: '900', color: C.fg, letterSpacing: 0.5, lineHeight: 36 },
  briefIcon: { width: 44, height: 44, borderRadius: R.pill, backgroundColor: 'rgba(212,175,55,0.14)', alignItems: 'center', justifyContent: 'center' },
  briefTitle: { color: C.fg, fontWeight: '900', fontSize: 12, letterSpacing: 1 },
  briefSub: { color: C.info, fontSize: 10.5, marginTop: 2 },
  orbWrap: { alignItems: 'center', marginTop: S.xl, gap: 4 },
  orbGlow: { position: 'absolute', top: 0, width: HOME_ORB, height: HOME_ORB, borderRadius: HOME_ORB / 2 },
  orbCore: { width: HOME_ORB, height: HOME_ORB, borderRadius: HOME_ORB / 2, borderWidth: 2, alignItems: 'center', justifyContent: 'center', backgroundColor: '#101017', shadowOpacity: 0.9, shadowRadius: 26, shadowOffset: { width: 0, height: 0 }, elevation: 14, overflow: 'hidden' },
  orbInner: { position: 'absolute', width: HOME_ORB * 0.7, height: HOME_ORB * 0.7, borderRadius: HOME_ORB, opacity: 0.15 },
  orbLvl: { marginTop: 4, fontWeight: '900', fontSize: 11, letterSpacing: 2 },
  orbTitle: { color: C.brand, fontWeight: '900', fontSize: 14, letterSpacing: 5, marginTop: S.sm },
  orbSub: { color: C.info, fontSize: 11 },
  orbGeo: { color: C.brand, fontSize: 10, letterSpacing: 1.5, fontWeight: '800', marginTop: 4 },
  lensMini: { width: 52, height: 52, borderRadius: 26, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: 'rgba(255,255,255,0.3)' },
  pillarGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: S.md, marginTop: S.xl },
  ecoRow: { flexDirection: 'row', gap: S.md, marginTop: S.md },
  ecoTile: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: S.sm, borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.pill, minHeight: 50, backgroundColor: 'rgba(212,175,55,0.05)' },
  ecoText: { color: C.fg, fontWeight: '900', fontSize: 10.5, letterSpacing: 1 },
  pillarIcon: { width: 46, height: 46, borderRadius: R.pill, backgroundColor: 'rgba(212,175,55,0.14)', alignItems: 'center', justifyContent: 'center' },
  pillarTitle: { color: C.fg, fontWeight: '800', fontSize: 16, letterSpacing: 0.3 },
  pillarSub: { color: C.info, fontSize: 11, marginTop: 4, lineHeight: 15 },
  sosPill: { marginTop: S.xl, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: S.sm, backgroundColor: C.error, borderRadius: R.pill, paddingVertical: S.lg, minHeight: 56 },
  sosPillText: { color: C.onError, fontWeight: '900', letterSpacing: 2, fontSize: 13 },
  beaconDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: C.error },
  beaconHint: { marginTop: S.md, fontSize: 9, letterSpacing: 1, color: C.onS3, fontWeight: '700', textAlign: 'center' },
  tosHead: { flexDirection: 'row', alignItems: 'center', gap: S.md, paddingHorizontal: S.lg, paddingVertical: S.md, backgroundColor: C.inverse },
  tosHeadText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 14 },
  tosBanner: { backgroundColor: C.warn, padding: S.md },
  tosBannerText: { color: C.onWarn, fontWeight: '900', fontSize: 10, letterSpacing: 0.5 },
  tosBody: { fontSize: 12, lineHeight: 18, color: C.fg, fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }) },
  tosAccept: { backgroundColor: C.brand, paddingVertical: S.lg, alignItems: 'center', margin: S.lg, borderRadius: R.pill },
  tosAcceptText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 15 },
  // Angel Mode 2.0
  angelScrim: { flex: 1, backgroundColor: 'rgba(10,10,15,0.62)' },
  angelTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.lg, paddingTop: S.md },
  angelWordmark: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 14 },
  angelExit: { width: 44, height: 44, borderRadius: R.pill, backgroundColor: 'rgba(32,32,43,0.85)', alignItems: 'center', justifyContent: 'center' },
  acousticRow: { alignItems: 'center', marginTop: S.md },
  acousticBtn: { flexDirection: 'row', alignItems: 'center', gap: 8, borderWidth: 1.5, borderColor: C.brand, borderRadius: R.pill, paddingHorizontal: S.lg, minHeight: 44, backgroundColor: 'rgba(10,10,15,0.55)' },
  acousticBtnOn: { backgroundColor: C.brand },
  acousticText: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 1.5 },
  angelCenter: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: S.xl },
  angelScroll: { padding: S.lg, paddingBottom: S.md, gap: S.md },
  jarvisOrbOuter: { width: 170, height: 170, borderRadius: 85, backgroundColor: 'rgba(212,175,55,0.18)', alignItems: 'center', justifyContent: 'center' },
  jarvisOrb: { width: 132, height: 132, borderRadius: 66, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center', borderWidth: 3, borderColor: C.brandSec },
  jarvisLabel: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 15 },
  angelBigCard: { flexDirection: 'row', alignItems: 'center', gap: S.lg, backgroundColor: 'rgba(16,16,23,0.92)', borderRadius: R.lg, padding: S.lg, minHeight: 96, borderWidth: 2, borderColor: C.brand, marginTop: S.md },
  angelBigIcon: { width: 62, height: 62, borderRadius: 31, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center' },
  angelBigTitle: { color: C.fg, fontWeight: '900', fontSize: 17, letterSpacing: 1 },
  angelBigSub: { color: C.onS3, fontSize: 13, lineHeight: 18, marginTop: 3 },
  echoBadge: { position: 'absolute', top: -4, right: -4, minWidth: 24, height: 24, borderRadius: 12, backgroundColor: C.error, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 5 },
  echoBadgeText: { color: C.onError, fontWeight: '900', fontSize: 12 },
  compCard: { backgroundColor: 'rgba(16,16,23,0.92)', borderRadius: R.lg, padding: S.lg, borderWidth: 1.5, borderColor: 'rgba(212,175,55,0.5)' },
  compQ: { color: C.fg, fontWeight: '800', fontSize: 18, lineHeight: 26 },
  compCare: { color: C.brand, fontSize: 13, marginTop: 6, lineHeight: 18 },
  compReply: { color: C.brand, fontWeight: '700', fontSize: 14, lineHeight: 20, marginTop: S.md },
  compBtn: { flex: 1, alignItems: 'center', justifyContent: 'center', minHeight: 64, borderRadius: R.md, borderWidth: 1.5, borderColor: C.borderStrong, backgroundColor: 'rgba(32,32,43,0.8)' },
  healTitle: { color: C.fg, fontWeight: '900', fontSize: 12, letterSpacing: 1 },
  healPct: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  healStep: { flexDirection: 'row', alignItems: 'center', gap: 6, borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.pill, paddingHorizontal: S.md, minHeight: 40 },
  healStepOn: { backgroundColor: C.brand, borderColor: C.brand },
  healStepText: { color: C.fg, fontWeight: '900', fontSize: 9.5, letterSpacing: 0.5 },
  healSub: { color: C.info, fontSize: 10.5, marginTop: S.md, lineHeight: 15 },
  angelBrief: { flexDirection: 'row', alignItems: 'center', gap: S.sm, borderWidth: 2, borderColor: C.brand, borderRadius: R.pill, paddingHorizontal: S.xl, minHeight: 56, backgroundColor: 'rgba(10,10,15,0.5)' },
  angelBriefText: { color: C.brand, fontWeight: '900', fontSize: 15, letterSpacing: 2 },
  angelBottom: { flexDirection: 'row', justifyContent: 'space-evenly', alignItems: 'center', paddingBottom: S.xxl, paddingTop: S.lg },
  angelEmg: { width: 96, height: 96, borderRadius: 48, backgroundColor: 'rgba(22,22,30,0.9)', alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: C.borderStrong },
});
