/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// PHYSIO-AI — Video-Native Hub: premium video guides (expo-video, zero-stutter) + cached TTS narration
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, ActivityIndicator, LayoutAnimation, Platform, UIManager, Linking, Animated as RNAnimated } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { VideoView, useVideoPlayer } from 'expo-video';
import { api, apiUpload, API_BASE, getToken } from '@/src/api';
import { cachedVideo, prefetchVideo } from '@/src/media';
import { useAuth } from '@/src/auth';
import { C, S, R } from '@/src/theme';
import { GlassCard, tap } from '@/src/ui/glass';
import { t, Lang } from '@/src/i18n';
import { speak as jarvisSpeak } from '@/src/voice';

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

/** Zero-stutter guide video — hardware-accelerated player, local FS cache + native caching. */
function GuideVideo({ url, testID, muted = true }: { url: string; testID: string; muted?: boolean }) {
  const src = cachedVideo(url);
  const player = useVideoPlayer(
    src.startsWith('file') ? src : ({ uri: src, useCaching: true } as any),
    p => {
      p.loop = muted;
      p.muted = muted; // demonstration loops are silent — expert uploads keep their own narration
      p.bufferOptions = { preferredForwardBufferDuration: 10, waitsToMinimizeStalling: true } as any;
      if (muted) p.play();
    });
  return (
    <View style={styles.videoWrap}>
      <VideoView testID={testID} player={player} style={styles.video} contentFit="cover"
        nativeControls allowsFullscreen allowsPictureInPicture={false} />
      <View style={styles.videoBadge}><Text style={styles.videoBadgeText}>▶ VIDEO GUIDE · HD</Text></View>
    </View>
  );
}

/** CONFETTI BURST — small dependency-free celebration for recovery milestones. */
const CONF_COLORS = ['#D4AF37', '#E74C3C', '#2ECC71', '#3498DB', '#F1C40F', '#9B59B6'];
function ConfettiBurst() {
  const pieces = useRef(
    Array.from({ length: 18 }, () => ({
      a: new RNAnimated.Value(0),
      x: Math.random() * 260 - 130,
      r: Math.random() * 720 - 360,
      c: CONF_COLORS[Math.floor(Math.random() * CONF_COLORS.length)],
    }))
  ).current;
  useEffect(() => {
    pieces.forEach((p, i) =>
      RNAnimated.timing(p.a, { toValue: 1, duration: 1400 + Math.random() * 500, delay: i * 30, useNativeDriver: true }).start());
  }, [pieces]);
  return (
    <View pointerEvents="none" style={{ position: 'absolute', left: 0, right: 0, top: 0, bottom: 0, alignItems: 'center', overflow: 'hidden' }}>
      {pieces.map((p, i) => (
        <RNAnimated.View key={i} style={{
          position: 'absolute', top: 0, width: 8, height: 12, borderRadius: 2, backgroundColor: p.c,
          transform: [
            { translateY: p.a.interpolate({ inputRange: [0, 1], outputRange: [0, 170] }) },
            { translateX: p.a.interpolate({ inputRange: [0, 1], outputRange: [0, p.x] }) },
            { rotate: p.a.interpolate({ inputRange: [0, 1], outputRange: ['0deg', `${p.r}deg`] }) },
          ],
          opacity: p.a.interpolate({ inputRange: [0, 0.7, 1], outputRange: [1, 1, 0] }),
        }} />
      ))}
    </View>
  );
}

/** PAIN DIARY — record 1-10 after every exercise; the trend flows into the doctor's report. */
function PainLogger({ guideId }: { guideId: string }) {
  const [reply, setReply] = useState('');
  const [trend, setTrend] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [milestone, setMilestone] = useState('');
  const [confetti, setConfetti] = useState(0);

  useEffect(() => {
    (async () => { try { setTrend(await api('/physio/pain/trends')); } catch {} })();
  }, []);

  const log = async (level: number) => {
    setBusy(true);
    try {
      tap(level >= 8 ? 'heavy' : 'light');
      const r: any = await api('/physio/pain', { method: 'POST', body: JSON.stringify({ level, guide_id: guideId }) });
      setReply(r.reply);
      if (r.milestone) {
        tap('success');
        setMilestone(r.milestone_message);
        setConfetti(c => c + 1);
      }
      setTrend(await api('/physio/pain/trends'));
    } catch (e) { console.log(e); }
    setBusy(false);
  };

  const trendLabel = trend?.trend === 'improving' ? '↘ PAIN FALLING — HEALING'
    : trend?.trend === 'worsening' ? '↗ PAIN RISING — CAUTION'
    : '→ STABLE';

  return (
    <View style={styles.painBox}>
      <Text style={styles.painLbl}>🩹 HOW WAS THE PAIN AFTER EXERCISING? (1–10)</Text>
      <View style={styles.painRow}>
        {Array.from({ length: 10 }, (_, i) => i + 1).map(n => (
          <Pressable key={n} testID={`pain-${guideId}-${n}`} onPress={() => log(n)} disabled={busy}
            style={[styles.painDot, n >= 8 && { borderColor: C.error }, n >= 5 && n < 8 && { borderColor: C.warn }]}>
            <Text style={[styles.painDotText, n >= 8 && { color: C.error }]}>{n}</Text>
          </Pressable>
        ))}
      </View>
      {!!reply && <Text testID={`pain-reply-${guideId}`} style={styles.painReply}>💛 {reply}</Text>}
      {!!milestone && <Text testID={`pain-milestone-${guideId}`} style={styles.painMilestone}>{milestone}</Text>}
      {!!trend?.avg_14d && (
        <Text style={styles.painTrend}>14-day average: {trend.avg_14d}/10 · {trendLabel} · goes into your doctor report</Text>
      )}
      {confetti > 0 && <ConfettiBurst key={confetti} />}
    </View>
  );
}

/** WEEKLY RECOVERY PLAYLIST — 7-day plan guiding the patient through the whole week. */
function WeeklyPlan({ onOpenGuide }: { onOpenGuide: (id: string) => void }) {
  const [plan, setPlan] = useState<any>(null);
  const [pct, setPct] = useState(0);
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    try { const r: any = await api('/physio/plan'); setPlan(r.plan); setPct(r.progress_pct || 0); } catch (e) { console.log(e); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const gen = async () => {
    setBusy(true);
    try { tap('medium'); const r: any = await api('/physio/plan/generate', { method: 'POST' }); setPlan(r.plan); setPct(0); }
    catch (e) { console.log(e); }
    setBusy(false);
  };
  const doneDay = async (d: number) => {
    try { tap('success'); await api(`/physio/plan/day/${d}/complete`, { method: 'POST' }); await load(); }
    catch (e) { console.log(e); }
  };

  return (
    <View>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <Text style={styles.lbl}>📅 WEEKLY RECOVERY PLAN</Text>
        {!!plan && (
          <Pressable testID="ph-plan-regen" onPress={gen} hitSlop={10} disabled={busy}>
            {busy ? <ActivityIndicator size="small" color={C.brand} /> : <Ionicons name="refresh" size={16} color={C.info} />}
          </Pressable>
        )}
      </View>
      {!plan ? (
        <GlassCard pad={S.md} radius={R.md}>
          <Text style={styles.planIntro}>Jarvis arranges the guides and expert videos into a 7-day plan — day by day to relief. With an active Healing Loop it adds a daily anchor for the sore spot.</Text>
          <Pressable testID="ph-plan-generate" onPress={gen} disabled={busy} style={styles.planGenBtn}>
            {busy ? <ActivityIndicator color={C.onInverse} /> : (<>
              <Ionicons name="calendar" size={16} color={C.onInverse} />
              <Text style={styles.planGenText}>BUILD A 7-DAY PLAN</Text>
            </>)}
          </Pressable>
        </GlassCard>
      ) : (
        <View>
          <View style={styles.planProgress}>
            <View style={[styles.planProgressFill, { width: `${pct}%` }]} />
            <Text style={styles.planProgressText}>{plan.days.filter((d: any) => d.done).length}/7 DAYS · {pct} %</Text>
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: S.sm, paddingVertical: S.sm }}>
            {plan.days.map((d: any) => (
              <View key={d.day} testID={`plan-day-${d.day}`} style={[styles.dayCard, d.done && styles.dayCardDone]}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                  <Text style={styles.dayNum}>{d.day}</Text>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.dayWeekday}>{d.weekday.toUpperCase()}</Text>
                    <Text style={styles.dayTheme} numberOfLines={1}>{d.theme}</Text>
                  </View>
                  {d.done && <Ionicons name="checkmark-circle" size={18} color={C.brand} />}
                </View>
                <View style={{ gap: 4, marginTop: 8, flex: 1 }}>
                  {d.items.map((it: any, ix: number) => (
                    <Pressable key={ix} testID={`plan-item-${d.day}-${ix}`}
                      onPress={() => { tap('light'); onOpenGuide(it.type === 'guide' ? it.id : (it.guide_id || it.id)); }}
                      style={styles.dayItem}>
                      <Ionicons name={it.anchor ? 'star' : it.icon} size={12} color={it.anchor ? C.brand : C.info} />
                      <Text style={[styles.dayItemText, it.anchor && { color: C.brand, fontWeight: '900' }]} numberOfLines={1}>{it.title}</Text>
                    </Pressable>
                  ))}
                </View>
                {!d.done && (
                  <Pressable testID={`ph-plan-done-${d.day}`} onPress={() => doneDay(d.day)} style={styles.dayDoneBtn}>
                    <Text style={styles.dayDoneText}>DONE ✓</Text>
                  </Pressable>
                )}
              </View>
            ))}
          </ScrollView>
        </View>
      )}
    </View>
  );
}

/** FOUNDER'S EXPERT VIDEOS — upload your own massage/rehab videos per guide (authentic rehab). */
function ExpertVideos({ guideId }: { guideId: string }) {
  const [videos, setVideos] = useState<any[]>([]);
  const [tk, setTk] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [camBlocked, setCamBlocked] = useState(false);
  const [ccOpen, setCcOpen] = useState<string | null>(null);
  const [ccBusy, setCcBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [r, tok] = await Promise.all([api(`/physio/videos?guide_id=${guideId}`), getToken()]);
      setVideos((r as any).videos || []);
      setTk(tok || '');
    } catch (e) { console.log(e); }
  }, [guideId]);
  useEffect(() => { load(); }, [load]);

  const upload = async (fromCamera: boolean) => {
    setErr('');
    try {
      let res: ImagePicker.ImagePickerResult;
      if (fromCamera) {
        let perm = await ImagePicker.getCameraPermissionsAsync();
        if (!perm.granted) {
          if (perm.canAskAgain === false) { setCamBlocked(true); return; }
          perm = await ImagePicker.requestCameraPermissionsAsync();
          if (!perm.granted) { if (perm.canAskAgain === false) setCamBlocked(true); return; }
        }
        res = await ImagePicker.launchCameraAsync({ mediaTypes: ['videos'], videoMaxDuration: 180, quality: 0.7 } as any);
      } else {
        res = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['videos'], quality: 0.7 } as any);
      }
      if (res.canceled || !res.assets?.[0]) return;
      const a = res.assets[0];
      setBusy(true);
      tap('success');
      await apiUpload('/physio/videos', a.uri, a.fileName || 'expert.mp4', a.mimeType || 'video/mp4', { guide_id: guideId });
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    setBusy(false);
  };

  const remove = async (id: string) => {
    try { await api(`/physio/videos/${id}`, { method: 'DELETE' }); await load(); } catch (e) { console.log(e); }
  };

  const retryCc = async (id: string) => {
    setCcBusy(id);
    try { tap('medium'); await api(`/physio/videos/${id}/transcribe`, { method: 'POST' }); await load(); }
    catch (e) { console.log(e); }
    setCcBusy(null);
  };

  return (
    <View style={{ marginTop: S.sm }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <Text style={styles.evLbl}>🎬 EXPERT VIDEOS — YOUR OWN NARRATION</Text>
        <Pressable testID={`ev-refresh-${guideId}`} onPress={load} hitSlop={10}>
          <Ionicons name="refresh" size={14} color={C.info} />
        </Pressable>
      </View>
      {videos.map(v => (
        <View key={v.video_id} style={styles.evCard}>
          {!!tk && <GuideVideo url={`${API_BASE}/api/physio/videos/${v.video_id}/file?token=${tk}`} testID={`ev-video-${v.video_id}`} muted={false} />}
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <Text style={styles.evTitle} numberOfLines={1}>{v.title}</Text>
            {v.is_global && <View style={styles.evBadge}><Text style={styles.evBadgeText}>FOUNDER</Text></View>}
            <View style={{ flex: 1 }} />
            {v.mine && (
              <Pressable testID={`ev-del-${v.video_id}`} onPress={() => remove(v.video_id)} hitSlop={10}>
                <Ionicons name="trash-outline" size={16} color={C.info} />
              </Pressable>
            )}
          </View>
          {/* ACCESSIBILITY — auto-captions from Jarvis (Whisper narration → steps for the deaf) */}
          {v.transcript_status === 'done' && (
            <Pressable testID={`ev-cc-${v.video_id}`} onPress={() => { tap('light'); setCcOpen(ccOpen === v.video_id ? null : v.video_id); }} style={styles.ccBtn}>
              <Ionicons name="chatbox-ellipses-outline" size={13} color={C.brand} />
              <Text style={styles.ccBtnText}>CAPTIONS FOR THE DEAF (CC)</Text>
              <Ionicons name={ccOpen === v.video_id ? 'chevron-up' : 'chevron-down'} size={12} color={C.info} />
            </Pressable>
          )}
          {ccOpen === v.video_id && (v.caption_steps || []).map((s: string, i: number) => (
            <Text key={i} style={styles.ccStep}>{i + 1}. {s}</Text>
          ))}
          {(v.transcript_status === 'processing' || v.transcript_status === 'pending') && (
            <Text style={styles.ccNote}>⏳ Jarvis is transcribing the narration into captions… (refresh in a moment)</Text>
          )}
          {v.transcript_status === 'too_large' && (
            <Text style={styles.ccNote}>ℹ️ Video over 24 MB — captions support shorter videos.</Text>
          )}
          {v.transcript_status === 'failed' && v.mine && (
            <Pressable testID={`ev-cc-retry-${v.video_id}`} onPress={() => retryCc(v.video_id)} disabled={ccBusy === v.video_id} style={styles.ccRetry}>
              {ccBusy === v.video_id ? <ActivityIndicator size="small" color={C.brand} /> : (<>
                <Ionicons name="refresh" size={12} color={C.brand} />
                <Text style={styles.ccBtnText}>CAPTIONS FAILED — TRY AGAIN</Text>
              </>)}
            </Pressable>
          )}
        </View>
      ))}
      {videos.length === 0 && <Text style={styles.evEmpty}>No own video for this exercise yet — upload the first one and your rehab becomes authentically yours.</Text>}
      {Platform.OS === 'web' ? (
        <Text style={styles.evEmpty}>📱 Video upload works in the mobile app (gallery or camera).</Text>
      ) : (
        <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.sm }}>
          <Pressable testID={`ev-record-${guideId}`} onPress={() => upload(true)} disabled={busy} style={styles.evBtn}>
            {busy ? <ActivityIndicator size="small" color={C.onInverse} /> : (<>
              <Ionicons name="videocam" size={15} color={C.onInverse} />
              <Text style={styles.evBtnText}>RECORD WITH CAMERA</Text>
            </>)}
          </Pressable>
          <Pressable testID={`ev-pick-${guideId}`} onPress={() => upload(false)} disabled={busy} style={[styles.evBtn, styles.evBtnGhost]}>
            <Ionicons name="images-outline" size={15} color={C.brand} />
            <Text style={[styles.evBtnText, { color: C.brand }]}>FROM GALLERY</Text>
          </Pressable>
        </View>
      )}
      {camBlocked && (
        <Pressable onPress={() => Linking.openSettings()} style={styles.evSettings}>
          <Text style={styles.evSettingsText}>Camera is blocked — OPEN SETTINGS</Text>
        </Pressable>
      )}
      {!!err && <Text style={styles.evErr}>{err}</Text>}
    </View>
  );
}

export default function Physio() {
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'en';
  const router = useRouter();
  const [region, setRegion] = useState('neck');
  const [intensity, setIntensity] = useState('light');
  const [routine, setRoutine] = useState('');
  const [busy, setBusy] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [guides, setGuides] = useState<any[]>([]);
  const [catLabels, setCatLabels] = useState<Record<string, string>>({});
  const [openGuide, setOpenGuide] = useState<string | null>(null);
  // Note: voice playback is now handled centrally by src/voice.ts (single module-level player).

  useEffect(() => {
    (async () => {
      try {
        const res: any = await api(`/physio/guides?language=${lang}`);
        setGuides(res.guides || []);
        setCatLabels(res.category_labels || {});
        // Zero-Stutter: warm the video cache in background so playback starts instantly
        (res.guides || []).forEach((g: any) => { if (g.video_url) prefetchVideo(g.video_url); });
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

  const speakText = async (text: string) => {
    if (!text || speaking) return;
    setSpeaking(true);
    try {
      // Sentient voice — Jarvis speaks with the deep, warm 'onyx' timbre.
      await jarvisSpeak(text, { voice: 'onyx', speed: 0.95, language: lang });
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
      <View style={styles.sub}><Text style={styles.subText}>FOUNDER’S LEGACY · VIDEO-NATIVE GUIDES · SELF-MASSAGE</Text></View>

      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        {/* WEEKLY RECOVERY PLAYLIST — day-by-day guidance through the whole week */}
        <WeeklyPlan onOpenGuide={(id) => {
          LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
          setOpenGuide(id);
        }} />

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
                            <ExpertVideos guideId={g.id} />
                            <PainLogger guideId={g.id} />
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
  evLbl: { fontSize: 10, letterSpacing: 1.5, color: C.brand, fontWeight: '900', marginTop: S.sm, marginBottom: 6 },
  evCard: { marginBottom: S.sm, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, padding: 8, backgroundColor: 'rgba(212,175,55,0.04)' },
  evTitle: { color: C.fg, fontWeight: '800', fontSize: 11.5, flexShrink: 1 },
  evBadge: { backgroundColor: C.brand, borderRadius: R.pill, paddingHorizontal: 6, paddingVertical: 1 },
  evBadgeText: { color: C.onInverse, fontWeight: '900', fontSize: 8, letterSpacing: 1 },
  evEmpty: { color: C.info, fontSize: 10.5, lineHeight: 15 },
  evBtn: { flex: 1, flexDirection: 'row', gap: 6, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, borderRadius: R.pill, minHeight: 44 },
  evBtnGhost: { backgroundColor: 'transparent', borderWidth: 1.5, borderColor: C.brand },
  evBtnText: { color: C.onInverse, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  evSettings: { marginTop: S.sm, minHeight: 42, alignItems: 'center', justifyContent: 'center', borderRadius: R.sm, backgroundColor: C.warn },
  evSettingsText: { color: C.onWarn, fontWeight: '900', fontSize: 10.5 },
  evErr: { color: C.error, fontSize: 10.5, marginTop: 6, fontWeight: '700' },
  planIntro: { color: C.onS3, fontSize: 12, lineHeight: 17 },
  planGenBtn: { marginTop: S.md, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, borderRadius: R.pill, minHeight: 50 },
  planGenText: { color: C.onInverse, fontWeight: '900', fontSize: 12, letterSpacing: 1.5 },
  planProgress: { height: 26, borderRadius: R.pill, backgroundColor: C.surface2, borderWidth: 1, borderColor: C.border, overflow: 'hidden', justifyContent: 'center' },
  planProgressFill: { position: 'absolute', left: 0, top: 0, bottom: 0, backgroundColor: 'rgba(212,175,55,0.35)' },
  planProgressText: { color: C.fg, fontWeight: '900', fontSize: 10, letterSpacing: 1, textAlign: 'center' },
  dayCard: { width: 235, borderWidth: 1.5, borderColor: C.border, borderRadius: R.md, padding: S.md, backgroundColor: C.surface2, minHeight: 170 },
  dayCardDone: { borderColor: 'rgba(212,175,55,0.55)', backgroundColor: 'rgba(212,175,55,0.06)' },
  dayNum: { color: C.brand, fontWeight: '900', fontSize: 22, width: 24 },
  dayWeekday: { color: C.fg, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  dayTheme: { color: C.info, fontSize: 10, marginTop: 1 },
  dayItem: { flexDirection: 'row', alignItems: 'center', gap: 6, minHeight: 30, borderRadius: R.sm, paddingHorizontal: 6, backgroundColor: 'rgba(255,255,255,0.03)' },
  dayItemText: { color: C.fg, fontSize: 10.5, flex: 1 },
  dayDoneBtn: { marginTop: 8, minHeight: 38, alignItems: 'center', justifyContent: 'center', borderRadius: R.pill, borderWidth: 1.5, borderColor: C.brand },
  dayDoneText: { color: C.brand, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  ccBtn: { marginTop: 6, flexDirection: 'row', alignItems: 'center', gap: 6, minHeight: 34, borderRadius: R.sm, paddingHorizontal: 8, backgroundColor: 'rgba(212,175,55,0.08)', borderWidth: 1, borderColor: C.border },
  ccBtnText: { color: C.brand, fontWeight: '900', fontSize: 9.5, letterSpacing: 0.5, flex: 1 },
  ccStep: { color: C.fg, fontSize: 11.5, lineHeight: 17, marginTop: 4, paddingLeft: 4 },
  ccNote: { color: C.info, fontSize: 10, marginTop: 6 },
  ccRetry: { marginTop: 6, flexDirection: 'row', alignItems: 'center', gap: 6, minHeight: 34, borderRadius: R.sm, paddingHorizontal: 8, borderWidth: 1, borderColor: C.warn },
  painBox: { marginTop: S.md, borderTopWidth: 1, borderTopColor: C.border, paddingTop: S.md },
  painLbl: { fontSize: 10, letterSpacing: 1.5, color: C.brand, fontWeight: '900', marginBottom: 8 },
  painRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  painDot: { width: 44, height: 44, borderRadius: 22, borderWidth: 1.5, borderColor: C.borderStrong, alignItems: 'center', justifyContent: 'center' },
  painDotText: { color: C.fg, fontWeight: '900', fontSize: 13 },
  painReply: { color: C.brand, fontSize: 11.5, lineHeight: 16, marginTop: 8, fontWeight: '700' },
  painMilestone: { color: C.brand, fontSize: 13, lineHeight: 18, marginTop: 8, fontWeight: '900' },
  painTrend: { color: C.info, fontSize: 10, marginTop: 6 },
});
