/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// JARVIS 2.0 — THE LIVING SOUL: breathing AI Orb · Level 1→10 companion · full voice
// conversation (Whisper→gpt-5.4→emotional TTS) · self-teaching memory · visual thinking.
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator, Switch, Modal, Platform, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Svg, { Circle } from 'react-native-svg';
import { Image } from 'expo-image';
import Animated, {
  useSharedValue, useAnimatedStyle, withRepeat, withTiming, withSpring, withSequence, Easing, cancelAnimation,
} from 'react-native-reanimated';
import { setAudioModeAsync, useAudioRecorder, RecordingPresets, AudioModule } from 'expo-audio';
import { api, API_BASE, getToken } from '@/src/api';
import { useAuth } from '@/src/auth';
import { sharePdf } from '@/src/pdf';
import { tap } from '@/src/ui/glass';
import { C, S, R } from '@/src/theme';
import { speak as jarvisSpeak, stopSpeaking } from '@/src/voice';

type Mood = 'calm' | 'thinking' | 'alert' | 'energetic' | 'concerned';

const MOOD_CFG: Record<Mood, { color: string; glow: string; dur: number; label: string }> = {
  calm: { color: '#D4AF37', glow: 'rgba(212,175,55,0.35)', dur: 2600, label: 'POKOJNÝ' },
  energetic: { color: '#FFD75E', glow: 'rgba(255,215,94,0.4)', dur: 1200, label: 'ENERGICKÝ' },
  thinking: { color: '#9B6DFF', glow: 'rgba(155,109,255,0.4)', dur: 900, label: 'PREMÝŠĽAM…' },
  concerned: { color: '#4A90D9', glow: 'rgba(74,144,217,0.4)', dur: 2000, label: 'STAROSTLIVÝ' },
  alert: { color: '#FF453A', glow: 'rgba(255,69,58,0.45)', dur: 700, label: 'POPLACH' },
};
// Emotional voice coloring — Jarvis has ONE voice ('onyx' — deep, human, Tony Stark).
// Speed alone modulates emotion (soothing under stress, brisk in the morning).
const MOOD_VOICE: Record<Mood, { voice: string; speed: number }> = {
  calm: { voice: 'onyx', speed: 0.95 },
  concerned: { voice: 'onyx', speed: 0.9 },
  energetic: { voice: 'onyx', speed: 1.05 },
  thinking: { voice: 'onyx', speed: 1.0 },
  alert: { voice: 'onyx', speed: 1.1 },
};

const ORB = 190;
const RING_R = ORB / 2 + 14;

const CHAINS = [
  { id: 'healing', icon: 'medkit-outline', title: 'Healing Chain', sub: 'Žiadanka → Hunter → rezervácia → kalendár', body: { specialty: 'Ortopédia' } },
  { id: 'safety', icon: 'shield-outline', title: 'Safety Chain', sub: 'Pád/hluk → núdzová slučka → info pre záchranárov', body: { trigger: 'manual' } },
  { id: 'recovery', icon: 'walk-outline', title: 'Recovery Chain', sub: 'Nízky pohyb → Physio-AI → kontrola vychádzok', body: {} },
  { id: 'supply', icon: 'cube-outline', title: 'Supply Chain', sub: 'Chýbajúci liek → lekárne → barter → trasa', body: { med_name: 'Ibalgin' } },
];

/** Breathing Orb — the living heart of Jarvis. Tap = voice conversation. */
function Orb({ mood, progress, level, listening, onPress }: {
  mood: Mood; progress: number; level: number; listening: boolean; onPress: () => void;
}) {
  const cfg = listening ? MOOD_CFG.alert : MOOD_CFG[mood];
  const breath = useSharedValue(0);
  useEffect(() => {
    cancelAnimation(breath);
    breath.value = 0;
    breath.value = withRepeat(withTiming(1, { duration: listening ? 600 : cfg.dur, easing: Easing.inOut(Easing.sin) }), -1, true);
  }, [mood, listening, cfg.dur, breath]);
  const coreStyle = useAnimatedStyle(() => ({
    transform: [{ scale: 1 + breath.value * (listening ? 0.09 : 0.05) }],
  }));
  const glowStyle = useAnimatedStyle(() => ({
    opacity: 0.45 + breath.value * 0.5,
    transform: [{ scale: 1.06 + breath.value * 0.16 }],
  }));
  const circ = 2 * Math.PI * RING_R;
  return (
    <View style={{ alignItems: 'center', justifyContent: 'center', height: ORB + 70 }}>
      <Animated.View style={[orbSt.glow, { backgroundColor: cfg.glow, width: ORB, height: ORB, borderRadius: ORB / 2 }, glowStyle]} />
      <Svg width={ORB + 40} height={ORB + 40} style={{ position: 'absolute' }}>
        <Circle cx={(ORB + 40) / 2} cy={(ORB + 40) / 2} r={RING_R} stroke="rgba(255,255,255,0.10)" strokeWidth={5} fill="none" />
        <Circle cx={(ORB + 40) / 2} cy={(ORB + 40) / 2} r={RING_R} stroke={cfg.color} strokeWidth={5} fill="none"
          strokeDasharray={`${circ}`} strokeDashoffset={circ * (1 - Math.min(100, progress) / 100)}
          strokeLinecap="round" transform={`rotate(-90 ${(ORB + 40) / 2} ${(ORB + 40) / 2})`} />
      </Svg>
      <Animated.View style={coreStyle}>
        <Pressable testID="jv-orb" onPress={onPress} style={[orbSt.core, { borderColor: cfg.color, shadowColor: cfg.color }]}>
          <View style={[orbSt.inner, { backgroundColor: cfg.color }]} />
          <View style={[orbSt.inner2, { backgroundColor: cfg.color }]} />
          <Ionicons name={listening ? 'mic' : 'sparkles'} size={44} color={cfg.color} />
          <Text style={[orbSt.lvl, { color: cfg.color }]}>LVL {level}</Text>
        </Pressable>
      </Animated.View>
    </View>
  );
}

/** Visual-thinking step with animated data-ray. */
function ThinkStep({ step, detail, active, done }: { step: string; detail: string; active: boolean; done: boolean }) {
  const w = useSharedValue(0);
  useEffect(() => {
    if (active) w.value = withTiming(1, { duration: 700, easing: Easing.out(Easing.quad) });
    else if (done) w.value = 1;
  }, [active, done, w]);
  const bar = useAnimatedStyle(() => ({ width: `${w.value * 100}%` }));
  return (
    <View style={st.thinkRow}>
      <Ionicons name={done ? 'checkmark-circle' : active ? 'flash' : 'ellipse-outline'} size={16}
        color={done ? C.brand : active ? '#9B6DFF' : C.info} />
      <View style={{ flex: 1 }}>
        <Text style={[st.thinkStep, (active || done) && { color: C.fg }]}>{step}</Text>
        <Text style={st.thinkDetail}>{detail}</Text>
        <View style={st.thinkBarBg}><Animated.View style={[st.thinkBar, bar]} /></View>
      </View>
    </View>
  );
}

export default function Jarvis() {
  const router = useRouter();
  const { user } = useAuth();
  const [state, setState] = useState<any>(null);
  const [briefing, setBriefing] = useState<any>(null);
  const [msgs, setMsgs] = useState<{ role: 'user' | 'agent'; text: string; citations?: string[]; image?: string; vaultDocId?: string }[]>([]);
  const [mode, setMode] = useState<'chat' | 'sonar' | 'imagine'>('chat');
  const [input, setInput] = useState('');
  const [mood, setMood] = useState<Mood>('calm');
  const [busy, setBusy] = useState<string | null>(null);
  const [status, setStatus] = useState('');
  const [xpToast, setXpToast] = useState('');
  const [levelUp, setLevelUp] = useState<any>(null);
  const [thinkSteps, setThinkSteps] = useState<any[]>([]);
  const [thinkIdx, setThinkIdx] = useState(-1);
  const [insight, setInsight] = useState('');
  const [memories, setMemories] = useState<any[]>([]);
  const [showMems, setShowMems] = useState(false);
  const [showAbil, setShowAbil] = useState(false);
  const [micDenied, setMicDenied] = useState(false);
  const [sonarHist, setSonarHist] = useState<any[]>([]);
  const [showHist, setShowHist] = useState(false);
  const [recording, setRecording] = useState(false);
  const [auto, setAuto] = useState<any>(null);
  const [traces, setTraces] = useState<Record<string, any>>({});
  const [err, setErr] = useState('');
  // Voice playback centralised in src/voice.ts (single module-level player, auto-cleanup)
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const toastY = useSharedValue(0);
  const toastStyle = useAnimatedStyle(() => ({ opacity: toastY.value, transform: [{ translateY: (1 - toastY.value) * 12 }] }));

  const loadState = useCallback(async () => {
    try { const s: any = await api('/agent/state'); setState(s); setMood((s.mood as Mood) || 'calm'); } catch {}
  }, []);
  const loadMems = useCallback(async () => {
    try { const m: any = await api('/agent/memories'); setMemories(m.memories || []); } catch {}
  }, []);
  const loadHist = useCallback(async () => {
    try { const h: any = await api('/agent/search/history'); setSonarHist(h.items || []); } catch {}
  }, []);
  useEffect(() => { if (mode === 'sonar') loadHist(); }, [mode, loadHist]);
  useEffect(() => {
    loadState(); loadMems();
    (async () => {
      try { const b: any = await api('/agent/briefing'); setBriefing(b); if (b.mood) setMood(b.mood); } catch {}
      try { setAuto(await api('/jarvis/actions')); } catch {}
      try { await api('/agent/anomalies'); } catch {}
    })();
    return () => { stopSpeaking(); };
  }, [loadState, loadMems]);

  const showXp = (gained: number) => {
    if (!gained) return;
    setXpToast(`+${gained} XP`);
    toastY.value = withSequence(withTiming(1, { duration: 250 }), withTiming(1, { duration: 1400 }), withTiming(0, { duration: 400 }));
  };

  const speak = useCallback(async (text: string, m: Mood) => {
    if (!text) return;
    try {
      const v = MOOD_VOICE[m] || MOOD_VOICE.calm;
      await jarvisSpeak(text.slice(0, 2000), {
        voice: v.voice as any,
        speed: v.speed,
        language: (user?.language as any) || 'sk',
      });
    } catch (e) { console.log('tts err', e); }
  }, [user?.language]);

  // Stop any ongoing narration when Jarvis unmounts.
  useEffect(() => () => { stopSpeaking(); }, []);

  const sendMessage = useCallback(async (text: string, viaVoice = false) => {
    const q = text.trim();
    if (!q || busy === 'chat') return;
    setBusy('chat'); setErr(''); setInput('');
    setMsgs(prev => [...prev.slice(-8), { role: 'user', text: mode === 'imagine' ? `🎨 ${q}` : q }]);
    setMood('thinking');
    setStatus(mode === 'sonar' ? 'Prehľadávam web (Sonar)…' : mode === 'imagine' ? 'Maľujem obraz… (môže trvať až minútu)' : 'Premýšľam…');
    try {
      if (mode === 'imagine') {
        const res: any = await api('/agent/imagine', { method: 'POST', body: JSON.stringify({ prompt: q }) });
        setMsgs(prev => [...prev.slice(-8), {
          role: 'agent',
          text: res.saved_to_vault ? 'Váš obraz je pripravený a uložený v Trezore, Guardian Angel.' : 'Váš obraz je pripravený, Guardian Angel.',
          image: res.image_base64,
          vaultDocId: res.doc_id || undefined,
        }]);
        setMood('energetic'); setStatus('');
        showXp(res.xp_gained);
        if (res.level_up) setLevelUp({ level: res.level, name: res.level_name });
        loadState();
        if (viaVoice) speak('Váš obraz je pripravený a uložený v Trezore.', 'energetic');
      } else if (mode === 'sonar') {
        const res: any = await api('/agent/search', { method: 'POST', body: JSON.stringify({ query: q, language: user?.language || 'sk' }) });
        const note = res.degraded ? '\n\n⚠️ Živé vyhľadávanie je offline (chýba Perplexity kľúč) — odpovedám z internej znalosti.' : '';
        setMsgs(prev => [...prev.slice(-8), { role: 'agent', text: res.reply + note, citations: res.citations }]);
        setMood('calm'); setStatus('');
        showXp(res.xp_gained);
        if (res.level_up) setLevelUp({ level: res.level, name: res.level_name });
        loadState();
        loadHist();
        // VOICE SONAR — the Orb answers in Onyx and announces verified sources.
        if (viaVoice) {
          const n = res.citations?.length || 0;
          const spoken = n > 0 ? `${res.reply} Našiel som ${n === 1 ? 'jeden overený zdroj' : n < 5 ? `${n} overené zdroje` : `${n} overených zdrojov`} — nájdete ich pod odpoveďou.` : res.reply;
          speak(spoken, 'calm');
        }
      } else {
        const res: any = await api('/agent/chat', { method: 'POST', body: JSON.stringify({ message: q, language: user?.language || 'sk' }) });
        setMsgs(prev => [...prev.slice(-8), { role: 'agent', text: res.reply }]);
        const m: Mood = res.mood || 'calm';
        setMood(m); setStatus('');
        showXp(res.xp_gained);
        if (res.level_up) setLevelUp({ level: res.level, name: res.level_name });
        loadState(); loadMems();
        if (viaVoice) speak(res.reply, m);
      }
    } catch (e: any) { setErr(String(e.message || e)); setMood('calm'); setStatus(''); }
    setBusy(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [busy, mode, user?.language, speak, loadState, loadMems, loadHist]);

  // SONAR HISTORY — return to a past web answer (re-injects it into the chat).
  const openHist = (h: any) => {
    tap('light');
    setMsgs(prev => [...prev.slice(-6), { role: 'user', text: h.query }, { role: 'agent', text: h.reply, citations: h.citations }]);
    setShowHist(false);
  };
  const delHist = async (id: string) => {
    try { await api(`/agent/search/history/${id}`, { method: 'DELETE' }); setSonarHist(prev => prev.filter(x => x.conv_id !== id)); } catch {}
  };

  // ---- FULL VOICE CONVERSATION (tap Orb: record → Whisper → gpt-5.4 → emotional TTS) ----
  const orbPress = async () => {
    tap('medium');
    if (recording) { await stopVoice(); return; }
    try {
      let perm = await AudioModule.getRecordingPermissionsAsync();
      if (!perm.granted) {
        if (perm.canAskAgain === false) { setMicDenied(true); return; }
        perm = await AudioModule.requestRecordingPermissionsAsync();
        if (!perm.granted) { setMicDenied(perm.canAskAgain === false); return; }
      }
      setMicDenied(false);
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true } as any);
      await recorder.prepareToRecordAsync();
      recorder.record();
      setRecording(true); setStatus('Počúvam… ťuknite na guľu pre odoslanie');
    } catch (e) { console.log('rec err', e); }
  };

  const stopVoice = async () => {
    setRecording(false); setStatus('Prepisujem hlas…'); setMood('thinking');
    try {
      await recorder.stop();
      const uri = recorder.uri;
      if (!uri) { setStatus(''); return; }
      const form = new FormData();
      if (Platform.OS === 'web') {
        const blob = await (await fetch(uri)).blob();
        form.append('file', blob, 'voice.webm');
      } else {
        form.append('file', { uri, name: uri.endsWith('.m4a') ? 'voice.m4a' : 'voice.webm', type: uri.endsWith('.m4a') ? 'audio/mp4' : 'audio/webm' } as any);
      }
      const token = await getToken();
      const res = await fetch(`${API_BASE}/api/agent/transcribe`, {
        method: 'POST', headers: token ? { Authorization: `Bearer ${token}` } : undefined, body: form,
      });
      const data = await res.json();
      if (data.transcript) await sendMessage(data.transcript, true);
      else { setStatus(''); setMood('calm'); }
    } catch (e) { console.log('voice err', e); setStatus(''); setMood('calm'); }
  };

  // ---- VISUAL THINKING (deep analysis with data rays) ----
  const runAnalysis = async () => {
    if (busy === 'analyze') return;
    setBusy('analyze'); setErr(''); setInsight(''); setThinkSteps([]); setThinkIdx(-1);
    setMood('thinking'); setStatus('Hĺbková analýza dát…');
    try {
      const res: any = await api('/agent/analyze', { method: 'POST' });
      setThinkSteps(res.steps);
      for (let i = 0; i < res.steps.length; i++) {
        setThinkIdx(i);
        await new Promise(r => setTimeout(r, res.steps[i].ms || 600));
      }
      setThinkIdx(res.steps.length);
      setInsight(res.insight);
      setMood(res.alerts?.length ? 'concerned' : 'calm'); setStatus('');
      showXp(res.xp_gained);
      if (res.level_up) setLevelUp({ level: res.level, name: '' });
      loadState();
    } catch (e: any) { setErr(String(e.message || e)); setMood('calm'); setStatus(''); }
    setBusy(null);
  };

  const delMemory = async (id: string) => {
    try { await api(`/agent/memories/${id}`, { method: 'DELETE' }); loadMems(); loadState(); } catch {}
  };
  const toggleAutopilot = async (v: boolean) => {
    setAuto({ ...(auto || {}), autopilot: v });
    try { await api('/jarvis/autopilot', { method: 'PUT', body: JSON.stringify({ enabled: v }) }); } catch {}
  };
  const runChain = async (c: any) => {
    setBusy(c.id); setErr('');
    try { const res: any = await api(`/chains/${c.id}`, { method: 'POST', body: JSON.stringify(c.body) }); setTraces({ ...traces, [c.id]: res }); }
    catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const cfg = MOOD_CFG[mood];
  const nextAbility = state?.abilities?.find((a: any) => !a.unlocked);

  return (
    <SafeAreaView testID="jarvis-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="jv-back" onPress={() => { tap(); if (router.canGoBack()) { router.back(); } else { router.replace('/'); } }} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={st.title}>JARVIS 2.0 · ŽIVÁ DUŠA</Text>
        <View style={st.streak}>
          <Ionicons name="flame" size={13} color={C.brand} />
          <Text style={st.streakText}>{state?.streak_days ?? 0}</Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={{ paddingBottom: 80 }} keyboardShouldPersistTaps="handled">
        <Orb mood={mood} progress={state?.progress_pct ?? 0} level={state?.level ?? 1} listening={recording} onPress={orbPress} />

        <Animated.View style={[st.xpToast, toastStyle]} pointerEvents="none">
          <Text style={st.xpToastText}>{xpToast}</Text>
        </Animated.View>

        <View style={{ alignItems: 'center', paddingHorizontal: S.xl }}>
          <Text style={[st.moodLabel, { color: cfg.color }]}>{recording ? '🎙 POČÚVAM…' : cfg.label}</Text>
          <Text style={st.levelName}>LEVEL {state?.level ?? 1} · {state?.level_name ?? 'ISKRA'}</Text>
          <Text style={st.xpText}>{state?.xp ?? 0} / {state?.xp_next ?? 100} XP · {state?.memories_count ?? 0} spomienok</Text>
          {!!nextAbility && <Text style={st.nextAbility}>ĎALŠIE ODOMKNUTIE (LVL {nextAbility.level}): {nextAbility.name}</Text>}
          {!!status && <Text style={st.status}>{status}</Text>}
          <Text style={st.orbHint}>Ťuknite na guľu a hovorte — Jarvis odpovie hlasom</Text>
          {micDenied && (
            <Pressable testID="jv-mic-settings" onPress={() => Linking.openSettings()} style={st.settingsBtn}>
              <Ionicons name="settings-outline" size={14} color={C.brand} />
              <Text style={st.settingsText}>Mikrofón je zablokovaný — otvoriť Nastavenia</Text>
            </Pressable>
          )}
        </View>

        {/* MORNING BRIEFING */}
        {briefing && (
          <View style={[st.card, { borderColor: cfg.color }]}>
            <View style={st.cardHead}>
              <Text style={st.cardTitle}>☀️ RANNÝ BRÍFING</Text>
              <Pressable testID="jv-brief-play" onPress={() => speak(briefing.briefing, (briefing.mood as Mood) || 'energetic')} hitSlop={8} style={st.playBtn}>
                <Ionicons name="volume-high" size={16} color={C.onInverse} />
              </Pressable>
            </View>
            {!!briefing.weather && (
              <Text style={st.weather}>🌤 {briefing.weather.city}: {briefing.weather.now_c} °C · {briefing.weather.desc} · min {briefing.weather.min_c} / max {briefing.weather.max_c} °C</Text>
            )}
            <Text style={st.briefText}>{briefing.briefing}</Text>
            {(briefing.alerts || []).map((a: any, i: number) => (
              <View key={i} style={[st.alertRow, a.severity === 'high' && { borderColor: C.error }]}>
                <Ionicons name="warning" size={14} color={a.severity === 'high' ? C.error : '#FFC53D'} />
                <Text style={st.alertText}>{a.text}</Text>
              </View>
            ))}
          </View>
        )}

        {/* CHAT */}
        {msgs.map((m, i) => (
          <View key={i} testID={`jv-msg-${i}-${m.role}`} style={[st.bubble, m.role === 'user' ? st.bubbleUser : st.bubbleAgent]}>
            <Text style={[st.bubbleText, m.role === 'user' && { color: C.onInverse }]}>{m.text}</Text>
            {!!m.image && (
              <Image source={{ uri: `data:image/png;base64,${m.image}` }} style={st.genImage} contentFit="cover" transition={300} />
            )}
            {!!m.vaultDocId && (
              <Pressable testID={`jv-vault-open-${i}`} onPress={() => { tap('light'); router.push('/(tabs)/vault'); }} style={st.vaultChip}>
                <Ionicons name="lock-closed" size={12} color={C.brand} />
                <Text style={st.vaultChipText}>ULOŽENÉ V TREZORE · OTVORIŤ GALÉRIU</Text>
              </Pressable>
            )}
            {!!m.citations?.length && (
              <View style={st.citeBox}>
                <Text style={st.citeLbl}>🌐 ZDROJE · SONAR</Text>
                {m.citations.slice(0, 5).map((c, j) => (
                  <Pressable key={j} testID={`jv-cite-${i}-${j}`} onPress={() => Linking.openURL(c)} hitSlop={4} style={{ minHeight: 28, justifyContent: 'center' }}>
                    <Text style={st.citeLink} numberOfLines={1}>{j + 1}. {c.replace(/^https?:\/\//, '')}</Text>
                  </Pressable>
                ))}
              </View>
            )}
          </View>
        ))}
        {busy === 'chat' && <ActivityIndicator color={cfg.color} style={{ marginTop: S.md }} />}
        {!!err && <Text style={st.err}>{err}</Text>}

        {/* JARVIS ULTRA — MODE SELECTOR (Chat · Sonar Web · Vision Forge) */}
        <View style={st.modeRow}>
          {([
            { id: 'chat', icon: 'chatbubble-ellipses-outline', label: 'CHAT' },
            { id: 'sonar', icon: 'globe-outline', label: 'SONAR · WEB' },
            { id: 'imagine', icon: 'color-palette-outline', label: 'OBRAZ' },
          ] as const).map(m => (
            <Pressable key={m.id} testID={`jv-mode-${m.id}`} onPress={() => { tap('light'); setMode(m.id); }}
              style={[st.modeChip, mode === m.id && st.modeChipActive]}>
              <Ionicons name={m.icon as any} size={14} color={mode === m.id ? C.onInverse : C.info} />
              <Text style={[st.modeText, mode === m.id && { color: C.onInverse }]}>{m.label}</Text>
            </Pressable>
          ))}
        </View>

        <View style={st.askRow}>
          <TextInput testID="jv-input" style={st.input}
            placeholder={mode === 'sonar' ? 'Opýtajte sa webu — medicína · EÚ…' : mode === 'imagine' ? 'Opíšte obraz, ktorý mám vytvoriť…' : 'Napíšte Jarvisovi… (alebo ťuknite na guľu)'}
            placeholderTextColor={C.info}
            value={input} onChangeText={setInput} onSubmitEditing={() => sendMessage(input)} returnKeyType="send" />
          <Pressable testID="jv-ask" onPress={() => sendMessage(input)} disabled={busy === 'chat'} style={st.askBtn}>
            {busy === 'chat' ? <ActivityIndicator size="small" color={C.onInverse} /> : <Ionicons name={mode === 'imagine' ? 'color-palette' : mode === 'sonar' ? 'globe' : 'arrow-up'} size={20} color={C.onInverse} />}
          </Pressable>
        </View>

        {/* SONAR HISTÓRIA — every web search with its sources, one tap away */}
        {mode === 'sonar' && sonarHist.length > 0 && (
          <>
            <Pressable testID="jv-hist-toggle" onPress={() => { tap('light'); setShowHist(!showHist); }} style={st.sectionRow}>
              <Text style={st.section}>🌐 SONAR HISTÓRIA ({sonarHist.length})</Text>
              <Ionicons name={showHist ? 'chevron-up' : 'chevron-down'} size={14} color={C.info} />
            </Pressable>
            {showHist && sonarHist.slice(0, 15).map((h: any) => (
              <View key={h.conv_id} testID={`jv-hist-${h.conv_id}`} style={st.histRow}>
                <Pressable testID={`jv-hist-open-${h.conv_id}`} onPress={() => openHist(h)} style={{ flex: 1 }}>
                  <Text style={st.histQuery} numberOfLines={1}>{h.query || '—'}</Text>
                  <Text style={st.histMeta}>
                    {String(h.at).slice(0, 10)} · {h.citations?.length
                      ? `${h.citations.length} ${h.citations.length === 1 ? 'zdroj' : h.citations.length < 5 ? 'zdroje' : 'zdrojov'}`
                      : 'bez živých zdrojov'}
                  </Text>
                </Pressable>
                <Pressable testID={`jv-hist-del-${h.conv_id}`} onPress={() => delHist(h.conv_id)} hitSlop={10}>
                  <Ionicons name="trash-outline" size={15} color={C.info} />
                </Pressable>
              </View>
            ))}
          </>
        )}

        {/* VISUAL THINKING */}
        <Pressable testID="jv-analyze" onPress={runAnalysis} disabled={busy === 'analyze'} style={st.analyzeBtn}>
          {busy === 'analyze' ? <ActivityIndicator color="#9B6DFF" /> : <Ionicons name="scan-circle-outline" size={18} color="#9B6DFF" />}
          <Text style={st.analyzeText}>HĹBKOVÁ ANALÝZA — VIZUÁLNE MYSLENIE</Text>
        </Pressable>
        {thinkSteps.length > 0 && (
          <View style={st.thinkBox}>
            {thinkSteps.map((s: any, i: number) => (
              <ThinkStep key={i} step={s.step} detail={s.detail} active={i === thinkIdx} done={i < thinkIdx} />
            ))}
            {!!insight && (
              <View style={st.insightBox}>
                <Text style={st.insightLbl}>💡 SYNTÉZA JARVISA</Text>
                <Text style={st.insightText}>{insight}</Text>
                <Pressable testID="jv-insight-play" onPress={() => speak(insight, 'calm')} style={st.speakSmall}>
                  <Ionicons name="volume-medium-outline" size={14} color={C.brand} />
                  <Text style={st.speakSmallText}>PREHRAŤ</Text>
                </Pressable>
              </View>
            )}
          </View>
        )}

        {/* ABILITIES */}
        <Pressable testID="jv-abil-toggle" onPress={() => { tap('light'); setShowAbil(!showAbil); }} style={st.sectionRow}>
          <Text style={st.section}>SCHOPNOSTI SPOLOČNÍKA ({state?.abilities?.filter((a: any) => a.unlocked).length ?? 1}/10)</Text>
          <Ionicons name={showAbil ? 'chevron-up' : 'chevron-down'} size={14} color={C.info} />
        </Pressable>
        {showAbil && (state?.abilities || []).map((a: any) => (
          <View key={a.level} testID={`jv-abil-${a.level}`} style={[st.abilRow, !a.unlocked && { opacity: 0.45 }]}>
            <Ionicons name={a.unlocked ? 'checkmark-circle' : 'lock-closed'} size={15} color={a.unlocked ? C.brand : C.info} />
            <Text style={st.abilText}>LVL {a.level} · {a.name}</Text>
          </View>
        ))}

        {/* MEMORIES */}
        <Pressable testID="jv-mem-toggle" onPress={() => { tap('light'); setShowMems(!showMems); }} style={st.sectionRow}>
          <Text style={st.section}>ČO SI PAMÄTÁM ({memories.length})</Text>
          <Ionicons name={showMems ? 'chevron-up' : 'chevron-down'} size={14} color={C.info} />
        </Pressable>
        {showMems && memories.slice(0, 12).map((m: any) => (
          <View key={m.memory_id} testID={`jv-mem-${m.memory_id}`} style={st.memRow}>
            <Ionicons name={m.topic === 'health' ? 'heart' : m.topic === 'family' ? 'people' : 'bookmark'} size={14} color={C.brand} />
            <Text style={st.memText}>{m.text}</Text>
            <Pressable testID={`jv-mem-del-${m.memory_id}`} onPress={() => delMemory(m.memory_id)} hitSlop={10}>
              <Ionicons name="trash-outline" size={15} color={C.info} />
            </Pressable>
          </View>
        ))}
        {showMems && memories.length === 0 && <Text style={st.memEmpty}>Zatiaľ žiadne spomienky — porozprávajte sa so mnou.</Text>}

        {/* AUTOPILOT + CHAINS */}
        <Text style={[st.section, { paddingHorizontal: S.xl, marginTop: S.xl }]}>AUTOPILOT — MEDICAL SENTINEL</Text>
        <View style={st.autoRow}>
          <Ionicons name="infinite" size={20} color={C.brand} />
          <View style={{ flex: 1 }}>
            <Text style={st.chainTitle}>Automatické spracovanie Trezoru</Text>
            <Text style={st.chainSub}>Nový dokument → OCR → AI preklad → kalendár → rezervácia. Bez pýtania.</Text>
          </View>
          <Switch testID="jv-autopilot" value={auto?.autopilot !== false} onValueChange={toggleAutopilot} trackColor={{ true: C.brand, false: C.surface3 }} />
        </View>

        <Text style={[st.section, { paddingHorizontal: S.xl, marginTop: S.lg }]}>SENTIENT REŤAZE</Text>
        {CHAINS.map(c => {
          const tr = traces[c.id];
          return (
            <View key={c.id} style={st.chainCard}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.md }}>
                <Ionicons name={c.icon as any} size={18} color={C.brand} />
                <View style={{ flex: 1 }}>
                  <Text style={st.chainTitle}>{c.title}</Text>
                  <Text style={st.chainSub}>{c.sub}</Text>
                </View>
                <Pressable testID={`jv-chain-${c.id}`} onPress={() => runChain(c)} disabled={busy === c.id} style={st.runBtn}>
                  {busy === c.id ? <ActivityIndicator size="small" color={C.onInverse} /> : <Text style={st.runText}>SPUSTIŤ</Text>}
                </Pressable>
              </View>
              {tr && (
                <View style={st.traceBox}>
                  {tr.steps.map((s: any, i: number) => (
                    <Text key={i} style={st.traceText}>✓ <Text style={{ fontWeight: '900' }}>{s.step}:</Text> {s.detail}</Text>
                  ))}
                  <Text style={st.traceSummary}>▶ {tr.summary}</Text>
                </View>
              )}
            </View>
          );
        })}

        <Pressable
          testID="jv-weekly"
          onPress={async () => { setBusy('pdf'); try { await sharePdf('/reports/weekly.pdf', 'guardian_pulse_report.pdf'); } catch (e: any) { setErr(String(e.message || e)); } finally { setBusy(null); } }}
          disabled={busy === 'pdf'} style={st.cta}>
          {busy === 'pdf' ? <ActivityIndicator color={C.onInverse} /> : (
            <>
              <Ionicons name="document-text-outline" size={16} color={C.onInverse} />
              <Text style={st.ctaText}>TÝŽDENNÝ GUARDIAN PULSE REPORT (PDF)</Text>
            </>
          )}
        </Pressable>
        <Text style={st.disclaimer}>AI spoločník — informačný obsah, nie zdravotná starostlivosť (EU AI Act čl. 50). Pamäť môžete kedykoľvek vymazať.</Text>
      </ScrollView>

      {/* LEVEL-UP OVERLAY */}
      <Modal visible={!!levelUp} transparent animationType="fade" onRequestClose={() => setLevelUp(null)}>
        <View style={st.lvlOverlay}>
          <LevelUpBurst level={levelUp?.level} name={levelUp?.name} onClose={() => setLevelUp(null)} />
        </View>
      </Modal>
    </SafeAreaView>
  );
}

function LevelUpBurst({ level, name, onClose }: { level: number; name: string; onClose: () => void }) {
  const scale = useSharedValue(0);
  useEffect(() => {
    scale.value = withSpring(1, { damping: 9 });
    tap('success');
  }, [scale]);
  const style = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  return (
    <Animated.View style={[st.lvlCard, style]}>
      <View style={st.lvlBurst}><Ionicons name="sparkles" size={54} color={C.onInverse} /></View>
      <Text style={st.lvlTitle}>LEVEL {level}!</Text>
      {!!name && <Text style={st.lvlName}>{name}</Text>}
      <Text style={st.lvlSub}>Váš anjel je múdrejší — odomkli ste novú schopnosť.</Text>
      <Pressable testID="jv-levelup-close" onPress={onClose} style={st.lvlBtn}>
        <Text style={st.lvlBtnText}>POKRAČOVAŤ</Text>
      </Pressable>
    </Animated.View>
  );
}

const orbSt = StyleSheet.create({
  glow: { position: 'absolute' },
  core: {
    width: ORB, height: ORB, borderRadius: ORB / 2, borderWidth: 2,
    alignItems: 'center', justifyContent: 'center', backgroundColor: '#101017',
    shadowOpacity: 0.9, shadowRadius: 30, shadowOffset: { width: 0, height: 0 }, elevation: 16, overflow: 'hidden',
  },
  inner: { position: 'absolute', width: ORB * 0.72, height: ORB * 0.72, borderRadius: ORB, opacity: 0.14 },
  inner2: { position: 'absolute', width: ORB * 0.45, height: ORB * 0.45, borderRadius: ORB, opacity: 0.2 },
  lvl: { marginTop: 6, fontWeight: '900', fontSize: 13, letterSpacing: 2 },
});

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 2.5, fontSize: 14 },
  streak: { flexDirection: 'row', alignItems: 'center', gap: 4, borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.pill, paddingHorizontal: 10, paddingVertical: 4 },
  streakText: { color: C.brand, fontWeight: '900', fontSize: 12 },
  xpToast: { alignSelf: 'center', backgroundColor: C.brand, borderRadius: R.pill, paddingHorizontal: 14, paddingVertical: 4, marginTop: -10 },
  xpToastText: { color: C.onInverse, fontWeight: '900', fontSize: 13, letterSpacing: 1 },
  moodLabel: { marginTop: S.sm, fontWeight: '900', fontSize: 11, letterSpacing: 3 },
  levelName: { color: C.fg, fontWeight: '900', fontSize: 20, letterSpacing: 1, marginTop: 4 },
  xpText: { color: C.info, fontSize: 12, marginTop: 2, fontWeight: '700' },
  nextAbility: { color: C.onS3, fontSize: 10, marginTop: 6, textAlign: 'center', letterSpacing: 0.5 },
  status: { color: '#9B6DFF', fontWeight: '800', fontSize: 12, marginTop: S.sm },
  orbHint: { color: C.info, fontSize: 11, marginTop: S.md, textAlign: 'center' },
  settingsBtn: { flexDirection: 'row', gap: 6, alignItems: 'center', marginTop: S.sm, minHeight: 44, paddingHorizontal: S.md, borderWidth: 1, borderColor: C.brand, borderRadius: R.pill },
  settingsText: { color: C.brand, fontWeight: '800', fontSize: 11 },
  card: { marginTop: S.lg, marginHorizontal: S.xl, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1.5, padding: S.lg },
  cardHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: S.sm },
  cardTitle: { color: C.fg, fontWeight: '900', fontSize: 12, letterSpacing: 2 },
  playBtn: { width: 40, height: 40, borderRadius: 20, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center' },
  weather: { color: C.onS3, fontSize: 12, marginBottom: S.sm, fontWeight: '700' },
  briefText: { color: C.fg, fontSize: 14, lineHeight: 21 },
  alertRow: { flexDirection: 'row', gap: 8, alignItems: 'flex-start', marginTop: S.sm, borderWidth: 1, borderColor: '#FFC53D', borderRadius: R.sm, padding: S.sm },
  alertText: { flex: 1, color: C.fg, fontSize: 12, lineHeight: 17 },
  bubble: { marginTop: S.md, marginHorizontal: S.xl, borderRadius: R.md, padding: S.md, maxWidth: '86%' },
  bubbleUser: { alignSelf: 'flex-end', backgroundColor: C.brand },
  bubbleAgent: { alignSelf: 'flex-start', backgroundColor: C.surface2, borderWidth: 1, borderColor: C.border },
  bubbleText: { color: C.fg, fontSize: 14, lineHeight: 20 },
  modeRow: { flexDirection: 'row', gap: S.sm, marginTop: S.lg, marginHorizontal: S.xl },
  modeChip: { flexDirection: 'row', gap: 6, alignItems: 'center', borderWidth: 1, borderColor: C.border, borderRadius: R.pill, paddingHorizontal: S.md, minHeight: 40, justifyContent: 'center' },
  modeChipActive: { backgroundColor: C.brand, borderColor: C.brand },
  modeText: { color: C.info, fontWeight: '900', fontSize: 10.5, letterSpacing: 1 },
  genImage: { width: '100%', aspectRatio: 1, borderRadius: R.sm, marginTop: S.sm, backgroundColor: C.surface3 },
  vaultChip: { flexDirection: 'row', gap: 6, alignItems: 'center', justifyContent: 'center', marginTop: S.sm, borderWidth: 1, borderColor: C.brand, borderRadius: R.pill, minHeight: 38, paddingHorizontal: S.md, backgroundColor: 'rgba(212,175,55,0.08)' },
  vaultChipText: { color: C.brand, fontWeight: '900', fontSize: 9.5, letterSpacing: 1 },
  citeBox: { marginTop: S.sm, borderTopWidth: 1, borderTopColor: C.border, paddingTop: S.sm, gap: 2 },
  citeLbl: { color: C.brand, fontWeight: '900', fontSize: 9, letterSpacing: 1.5 },
  citeLink: { color: '#4A90D9', fontSize: 11, textDecorationLine: 'underline' },
  histRow: { flexDirection: 'row', gap: S.sm, alignItems: 'center', marginHorizontal: S.xl, marginTop: S.sm, backgroundColor: C.surface2, borderRadius: R.sm, borderWidth: 1, borderColor: C.border, padding: S.md, minHeight: 52 },
  histQuery: { color: C.fg, fontSize: 12.5, fontWeight: '700' },
  histMeta: { color: C.info, fontSize: 10, marginTop: 2 },
  askRow: { flexDirection: 'row', gap: S.sm, marginTop: S.lg, marginHorizontal: S.xl, alignItems: 'center' },
  input: { flex: 1, backgroundColor: C.surface2, borderWidth: 1, borderColor: C.border, borderRadius: R.pill, color: C.fg, paddingHorizontal: S.lg, minHeight: 50, fontSize: 14 },
  askBtn: { width: 50, height: 50, borderRadius: 25, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center' },
  analyzeBtn: { marginTop: S.lg, marginHorizontal: S.xl, flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', borderWidth: 1.5, borderColor: '#9B6DFF', borderRadius: R.pill, minHeight: 52 },
  analyzeText: { color: '#9B6DFF', fontWeight: '900', fontSize: 12, letterSpacing: 1 },
  thinkBox: { marginTop: S.md, marginHorizontal: S.xl, backgroundColor: 'rgba(155,109,255,0.06)', borderWidth: 1, borderColor: 'rgba(155,109,255,0.35)', borderRadius: R.md, padding: S.md, gap: S.md },
  thinkRow: { flexDirection: 'row', gap: S.sm, alignItems: 'flex-start' },
  thinkStep: { color: C.info, fontWeight: '800', fontSize: 12.5 },
  thinkDetail: { color: C.info, fontSize: 10.5, marginTop: 1 },
  thinkBarBg: { height: 3, backgroundColor: 'rgba(255,255,255,0.08)', borderRadius: 2, marginTop: 5, overflow: 'hidden' },
  thinkBar: { height: 3, backgroundColor: '#9B6DFF', borderRadius: 2 },
  insightBox: { borderTopWidth: 1, borderTopColor: 'rgba(155,109,255,0.3)', paddingTop: S.md },
  insightLbl: { color: '#9B6DFF', fontWeight: '900', fontSize: 10, letterSpacing: 2, marginBottom: 4 },
  insightText: { color: C.fg, fontSize: 13.5, lineHeight: 20 },
  speakSmall: { flexDirection: 'row', gap: 5, alignItems: 'center', marginTop: S.sm, minHeight: 40 },
  speakSmallText: { color: C.brand, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  sectionRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.xl, marginTop: S.xl, minHeight: 44 },
  section: { fontSize: 11, letterSpacing: 2, color: C.info, fontWeight: '800' },
  abilRow: { flexDirection: 'row', gap: S.sm, alignItems: 'center', paddingHorizontal: S.xl, paddingVertical: 7 },
  abilText: { color: C.fg, fontSize: 12.5, fontWeight: '700' },
  memRow: { flexDirection: 'row', gap: S.sm, alignItems: 'center', marginHorizontal: S.xl, marginTop: S.sm, backgroundColor: C.surface2, borderRadius: R.sm, borderWidth: 1, borderColor: C.border, padding: S.md },
  memText: { flex: 1, color: C.fg, fontSize: 12.5, lineHeight: 17 },
  memEmpty: { color: C.info, fontSize: 12, paddingHorizontal: S.xl, marginTop: S.sm },
  autoRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.brand, padding: S.md, marginHorizontal: S.xl, marginTop: S.sm },
  chainCard: { backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.md, marginHorizontal: S.xl, marginTop: S.sm },
  chainTitle: { color: C.fg, fontWeight: '900', fontSize: 13 },
  chainSub: { color: C.info, fontSize: 10, marginTop: 2, lineHeight: 14 },
  runBtn: { backgroundColor: C.brand, borderRadius: R.sm, paddingHorizontal: S.md, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  runText: { color: C.onInverse, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  traceBox: { marginTop: S.md, borderTopWidth: 1, borderTopColor: C.border, paddingTop: S.md, gap: 5 },
  traceText: { color: C.onS3, fontSize: 11.5, lineHeight: 16 },
  traceSummary: { marginTop: 4, color: C.brand, fontWeight: '800', fontSize: 12 },
  cta: { flexDirection: 'row', gap: S.sm, backgroundColor: C.brand, borderRadius: R.pill, minHeight: 52, alignItems: 'center', justifyContent: 'center', marginHorizontal: S.xl, marginTop: S.xl },
  ctaText: { color: C.onInverse, fontWeight: '900', letterSpacing: 0.5, fontSize: 11 },
  disclaimer: { marginTop: S.lg, color: C.info, fontSize: 10, lineHeight: 15, textAlign: 'center', paddingHorizontal: S.xl },
  err: { color: C.error, marginTop: S.md, fontSize: 12, paddingHorizontal: S.xl },
  lvlOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.82)', alignItems: 'center', justifyContent: 'center', padding: S.xl },
  lvlCard: { alignItems: 'center', backgroundColor: C.surface2, borderRadius: R.xl, borderWidth: 2, borderColor: C.brand, padding: S.xxl, alignSelf: 'stretch' },
  lvlBurst: { width: 110, height: 110, borderRadius: 55, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center', marginBottom: S.lg },
  lvlTitle: { color: C.brand, fontWeight: '900', fontSize: 30, letterSpacing: 3 },
  lvlName: { color: C.fg, fontWeight: '900', fontSize: 17, letterSpacing: 2, marginTop: 4 },
  lvlSub: { color: C.onS3, fontSize: 13, textAlign: 'center', marginTop: S.sm, lineHeight: 19 },
  lvlBtn: { marginTop: S.xl, backgroundColor: C.brand, borderRadius: R.pill, minHeight: 52, paddingHorizontal: S.xxl, alignItems: 'center', justifyContent: 'center', alignSelf: 'stretch' },
  lvlBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 14 },
});
