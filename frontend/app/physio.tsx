/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// PHYSIO-AI — Video-Native Hub: premium video guides (expo-video, zero-stutter) + cached TTS narration
import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, ActivityIndicator, LayoutAnimation, Platform, UIManager } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { createAudioPlayer, setAudioModeAsync } from 'expo-audio';
import { VideoView, useVideoPlayer } from 'expo-video';
import { api } from '@/src/api';
import { cachedAudioUri } from '@/src/media';
import { useAuth } from '@/src/auth';
import { C, S, R } from '@/src/theme';
import { GlassCard, tap } from '@/src/ui/glass';
import { t, Lang } from '@/src/i18n';

if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

const REGIONS = [
  { id: 'neck', tKey: 'region_neck', icon: 'body-outline' },
  { id: 'back', tKey: 'region_back', icon: 'walk-outline' },
  { id: 'shoulders', tKey: 'region_shoulders', icon: 'accessibility-outline' },
  { id: 'hips', tKey: 'region_hips', icon: 'body-outline' },
  { id: 'knees', tKey: 'region_knees', icon: 'walk-outline' },
  { id: 'hands', tKey: 'region_hands', icon: 'hand-left-outline' },
];
const INTENSITY = ['light', 'medium', 'firm'];

/** Zero-stutter guide video — buffered player, poster-free instant layout. */
function GuideVideo({ url, testID }: { url: string; testID: string }) {
  const player = useVideoPlayer(url, p => {
    p.loop = true;
    p.muted = true; // demonstration loop — narration comes from Jarvis TTS
    p.bufferOptions = { preferredForwardBufferDuration: 8 } as any;
    p.play();
  });
  return (
    <View style={styles.videoWrap}>
      <VideoView testID={testID} player={player} style={styles.video} contentFit="cover"
        nativeControls allowsFullscreen allowsPictureInPicture={false} />
      <View style={styles.videoBadge}><Text style={styles.videoBadgeText}>▶ VIDEO-NÁVOD · HD</Text></View>
    </View>
  );
}

export default function Physio() {
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const router = useRouter();
  const [region, setRegion] = useState('neck');
  const [intensity, setIntensity] = useState('light');
  const [routine, setRoutine] = useState('');
  const [busy, setBusy] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [guides, setGuides] = useState<any[]>([]);
  const [catLabels, setCatLabels] = useState<Record<string, string>>({});
  const [openGuide, setOpenGuide] = useState<string | null>(null);
  const playerRef = useRef<any>(null);

  useEffect(() => () => { try { playerRef.current?.remove?.(); } catch {} }, []);

  useEffect(() => {
    (async () => {
      try {
        const res: any = await api(`/physio/guides?language=${lang}`);
        setGuides(res.guides || []);
        setCatLabels(res.category_labels || {});
      } catch {}
    })();
  }, [lang]);

  const run = async () => {
    setBusy(true); setRoutine('');
    try {
      const res: any = await api('/physio/session', { method: 'POST', body: JSON.stringify({ region, intensity, language: lang }) });
      setRoutine(res.routine);
    } catch (e) { console.log(e); }
    setBusy(false);
  };

  // Zero-Stutter: TTS is fully downloaded to local cache before playback (no network hiccups)
  const speakText = async (text: string) => {
    if (!text || speaking) return;
    setSpeaking(true);
    try {
      const res: any = await api('/voice/tts', { method: 'POST', body: JSON.stringify({ text, voice: 'coral', language: lang }) });
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false } as any);
      const src = await cachedAudioUri(res.url.replace(/^\/api/, ''));
      try { playerRef.current?.remove?.(); } catch {}
      const p = createAudioPlayer(src.headers ? { uri: src.uri, headers: src.headers } : { uri: src.uri });
      playerRef.current = p; p.play();
    } catch (e) { console.log(e); }
    setSpeaking(false);
  };

  const toggleGuide = (id: string) => {
    tap('light');
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setOpenGuide(openGuide === id ? null : id);
  };

  return (
    <SafeAreaView testID="physio-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="ph-back" onPress={() => { tap(); router.back(); }} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>PHYSIO-AI</Text>
        <View style={{ width: 26 }} />
      </View>
      <View style={styles.sub}><Text style={styles.subText}>FOUNDER'S LEGACY · VIDEO-NATÍVNE NÁVODY · SELF-MASSAGE</Text></View>

      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        <Text style={styles.lbl}>REGION</Text>
        <View style={styles.grid}>
          {REGIONS.map(r => (
            <Pressable testID={`region-${r.id}`} key={r.id} onPress={() => { tap('light'); setRegion(r.id); }} style={[styles.regTile, region === r.id && styles.regTileActive]}>
              <Ionicons name={r.icon as any} size={26} color={region === r.id ? C.onInverse : C.fg} />
              <Text style={[styles.regText, region === r.id && styles.regTextActive]}>{t(r.tKey, lang).toUpperCase()}</Text>
            </Pressable>
          ))}
        </View>

        <Text style={styles.lbl}>INTENSITY</Text>
        <View style={{ flexDirection: 'row', gap: S.sm }}>
          {INTENSITY.map(i => (
            <Pressable testID={`int-${i}`} key={i} onPress={() => { tap('light'); setIntensity(i); }} style={[styles.chip, intensity === i && styles.chipActive]}>
              <Text style={[styles.chipText, intensity === i && styles.chipTextActive]}>{i.toUpperCase()}</Text>
            </Pressable>
          ))}
        </View>

        <Pressable testID="ph-generate" onPress={() => { tap('medium'); run(); }} disabled={busy} style={styles.runBtn}>
          {busy ? <ActivityIndicator color={C.onInverse} /> : <>
            <Ionicons name="sparkles-outline" size={16} color={C.onInverse} />
            <Text style={styles.runText}>GENERATE ROUTINE</Text>
          </>}
        </Pressable>

        {!!routine && (
          <View style={styles.outBox}>
            <Text style={styles.outLbl}>ROUTINE</Text>
            <Text style={styles.outText}>{routine}</Text>
            <Pressable testID="ph-speak" onPress={() => speakText(routine)} disabled={speaking} style={styles.speakBtn}>
              {speaking ? <ActivityIndicator size="small" color={C.brand} /> : <Ionicons name="volume-medium-outline" size={18} color={C.brand} />}
              <Text style={styles.speakBtnText}>{t('speak', lang).toUpperCase()}</Text>
            </Pressable>
          </View>
        )}

        {guides.length > 0 && (
          <>
            {(['body', 'expert', 'stress'] as const).map(cat => {
              const catGuides = guides.filter((g: any) => (g.category || 'body') === cat);
              if (catGuides.length === 0) return null;
              return (
                <View key={cat}>
                  <Text style={styles.lbl}>{catLabels[cat] || cat.toUpperCase()}</Text>
                  {catGuides.map(g => {
                    const open = openGuide === g.id;
                    return (
                      <GlassCard key={g.id} pad={0} radius={R.md} style={{ marginBottom: S.sm }}>
                        <Pressable testID={`guide-${g.id}`} onPress={() => toggleGuide(g.id)} style={styles.guideHead}>
                          <Ionicons name={g.icon} size={20} color={C.brand} />
                          <View style={{ flex: 1 }}>
                            <Text style={styles.guideTitle}>{g.title}</Text>
                            <Text style={styles.guideSub}>{g.subtitle}{g.video_url ? ' · 🎬 VIDEO' : ''}</Text>
                          </View>
                          <Pressable testID={`guide-play-${g.id}`} onPress={() => speakText(g.tts_text)} hitSlop={8} style={styles.guidePlay}>
                            <Ionicons name="volume-high" size={16} color={C.onInverse} />
                          </Pressable>
                          <Ionicons name={open ? 'chevron-up' : 'chevron-down'} size={16} color={C.info} />
                        </Pressable>
                        {open && (
                          <View style={styles.guideSteps}>
                            {!!g.video_url && <GuideVideo url={g.video_url} testID={`guide-video-${g.id}`} />}
                            {g.steps.map((s: string, i: number) => (
                              <Text key={i} style={styles.guideStep}>{i + 1}. {s}</Text>
                            ))}
                            {!!g.video_note && <Text style={styles.videoNote}>{g.video_note}</Text>}
                          </View>
                        )}
                      </GlassCard>
                    );
                  })}
                </View>
              );
            })}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.brand, fontSize: 18, fontWeight: '900', letterSpacing: 3 },
  sub: { paddingHorizontal: S.lg, paddingVertical: 6, backgroundColor: C.brandTer },
  subText: { color: C.brand, fontSize: 10, fontWeight: '900', letterSpacing: 1.5 },
  lbl: { fontSize: 11, letterSpacing: 2, color: C.fg, fontWeight: '900', marginTop: S.lg, marginBottom: S.sm },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: S.sm },
  regTile: { width: '31.5%', aspectRatio: 1, borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.md, alignItems: 'center', justifyContent: 'center', gap: 6, backgroundColor: 'rgba(212,175,55,0.05)' },
  regTileActive: { backgroundColor: C.brand, borderColor: C.brand },
  regText: { fontWeight: '900', fontSize: 11, letterSpacing: 1, color: C.fg },
  regTextActive: { color: C.onInverse },
  chip: { paddingHorizontal: S.md, paddingVertical: 10, borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.pill, flex: 1, alignItems: 'center' },
  chipActive: { backgroundColor: C.brand, borderColor: C.brand },
  chipText: { fontWeight: '900', color: C.fg, letterSpacing: 1, fontSize: 12 },
  chipTextActive: { color: C.onInverse },
  runBtn: { marginTop: S.lg, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, paddingVertical: S.lg, borderRadius: R.pill, minHeight: 56 },
  runText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 14 },
  outBox: { marginTop: S.lg, borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.md, padding: S.md, backgroundColor: C.surface2 },
  outLbl: { fontSize: 10, letterSpacing: 2, fontWeight: '900', color: C.brand, marginBottom: S.sm },
  outText: { color: C.fg, fontSize: 15, lineHeight: 22 },
  speakBtn: { marginTop: S.md, flexDirection: 'row', gap: 8, alignItems: 'center', alignSelf: 'flex-start', borderWidth: 1.5, borderColor: C.brand, borderRadius: R.pill, paddingHorizontal: S.md, minHeight: 44, backgroundColor: 'rgba(212,175,55,0.06)' },
  speakBtnText: { color: C.brand, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
  guideHead: { flexDirection: 'row', alignItems: 'center', gap: S.md, padding: S.md },
  guideTitle: { color: C.fg, fontWeight: '800', fontSize: 13 },
  guideSub: { color: C.info, fontSize: 10.5, marginTop: 2 },
  guidePlay: { width: 40, height: 40, borderRadius: 20, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center' },
  guideSteps: { borderTopWidth: 1, borderTopColor: C.border, padding: S.md, gap: 6 },
  guideStep: { color: C.fg, fontSize: 12.5, lineHeight: 18 },
  videoWrap: { borderRadius: R.sm, overflow: 'hidden', marginBottom: S.sm },
  video: { width: '100%', height: 200, backgroundColor: '#000' },
  videoBadge: { position: 'absolute', top: 8, left: 8, backgroundColor: 'rgba(10,10,15,0.72)', borderRadius: R.pill, paddingHorizontal: 10, paddingVertical: 4 },
  videoBadgeText: { color: C.brand, fontSize: 9, fontWeight: '900', letterSpacing: 1 },
  videoNote: { color: C.info, fontSize: 9, marginTop: 4 },
});
