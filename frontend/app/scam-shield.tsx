/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, Pressable, StyleSheet, TextInput, ScrollView, ActivityIndicator, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import * as Clipboard from 'expo-clipboard';
import { createAudioPlayer, setAudioModeAsync } from 'expo-audio';
import { api, API_BASE, getToken } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';
import { useI18n } from '@/src/i18n-context';

type Check = { check_id: string; text: string; risk: string; verdict: string; reasons: string[]; advice: string; created_at: string };

const RISK_COLORS: Record<string, { bg: string; fg: string }> = {
  high: { bg: C.error, fg: C.onError },
  medium: { bg: C.warn, fg: C.onWarn },
  low: { bg: C.brand, fg: C.onInverse },
};

export default function ScamShield() {
  const { t: tt, tx } = useI18n();
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'en';
  const router = useRouter();
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Check | null>(null);
  const [history, setHistory] = useState<Check[]>([]);
  const playerRef = useRef<any>(null);

  const load = useCallback(async () => {
    try { setHistory(await api<Check[]>('/scam/history')); } catch {}
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => () => { try { playerRef.current?.remove?.(); } catch {} }, []);

  const speak = async (msg: string) => {
    try {
      const res: any = await api('/voice/tts', { method: 'POST', body: JSON.stringify({ text: msg, voice: 'nova', language: lang }) });
      const token = await getToken();
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false } as any);
      try { playerRef.current?.remove?.(); } catch {}
      const player = createAudioPlayer({ uri: `${API_BASE}${res.url}`, headers: token ? { Authorization: `Bearer ${token}` } : {} });
      playerRef.current = player;
      player.play();
    } catch (e) { console.log('tts err', e); }
  };

  const paste = async () => {
    try {
      const v = await Clipboard.getStringAsync();
      if (v) setText(v);
    } catch (e) { console.log('clipboard err', e); }
  };

  const analyze = async () => {
    if (!text.trim()) return;
    setBusy(true); setResult(null);
    try {
      const res: any = await api('/scam/check', { method: 'POST', body: JSON.stringify({ text, language: lang }) });
      setResult(res);
      load();
      if (res.risk === 'high') speak(`${res.verdict} ${res.advice}`);
    } catch (e) { console.log(e); } finally { setBusy(false); }
  };

  return (
    <SafeAreaView testID="scam-shield-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="ss-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={styles.title}>{t('scam_shield', lang).toUpperCase()}</Text>
        <View style={{ width: 26 }} />
      </View>
      <View style={styles.sub}><Text style={styles.subText}>{tt('scam_shield.ai_fraud_protection_voice_warning_fa')}</Text></View>

      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
        <Text style={styles.lbl}>{tt('scam_shield.sms_e_mail_odkaz_na_kontrolu')}</Text>
        <TextInput
          testID="ss-input"
          value={text}
          onChangeText={setText}
          multiline
          style={styles.input}
          placeholder={tt('scam_shield.paste_a_suspicious_message_or_link')}
          placeholderTextColor="#999"
        />
        <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.sm }}>
          {Platform.OS !== 'web' && (
            <Pressable testID="ss-paste" onPress={paste} style={styles.secBtn}>
              <Ionicons name="clipboard-outline" size={16} color={C.fg} />
              <Text style={styles.secBtnText}>{t('paste_clipboard', lang).toUpperCase()}</Text>
            </Pressable>
          )}
          <Pressable testID="ss-analyze" onPress={analyze} disabled={busy || !text.trim()} style={[styles.priBtn, !text.trim() && { opacity: 0.4 }]}>
            {busy ? <ActivityIndicator color={C.onInverse} /> : <>
              <Ionicons name="shield-checkmark-outline" size={16} color={C.onInverse} />
              <Text style={styles.priBtnText}>{t('analyze', lang).toUpperCase()}</Text>
            </>}
          </Pressable>
        </View>

        {result && (
          <View testID="ss-result" style={[styles.resultCard, { borderColor: RISK_COLORS[result.risk]?.bg || C.borderStrong }]}>
            <View style={[styles.riskBadge, { backgroundColor: RISK_COLORS[result.risk]?.bg || C.info }]}>
              <Ionicons name={result.risk === 'high' ? 'alert' : result.risk === 'medium' ? 'warning-outline' : 'checkmark-circle-outline'} size={18} color={RISK_COLORS[result.risk]?.fg} />
              <Text style={[styles.riskText, { color: RISK_COLORS[result.risk]?.fg }]}>{result.risk.toUpperCase()} {tt('scam_shield.risk')}</Text>
              <Pressable testID="ss-speak" onPress={() => speak(`${result.verdict} ${result.advice}`)} hitSlop={10}>
                <Ionicons name="volume-high-outline" size={20} color={RISK_COLORS[result.risk]?.fg} />
              </Pressable>
            </View>
            <Text style={styles.verdict}>{result.verdict}</Text>
            {result.reasons?.map((r, i) => (
              <View key={i} style={styles.reasonRow}>
                <Ionicons name="remove" size={14} color={C.onS3} />
                <Text style={styles.reasonText}>{r}</Text>
              </View>
            ))}
            <View style={styles.adviceBox}>
              <Text style={styles.adviceLbl}>{tt('scam_shield.jarvis')}</Text>
              <Text style={styles.adviceText}>{result.advice}</Text>
            </View>
          </View>
        )}

        <Text style={styles.section}>{tt('scam_shield.check_history')}</Text>
        {history.length === 0 ? <Text style={styles.noData}>{t('no_data', lang).toUpperCase()}</Text> : history.map(h => (
          <View key={h.check_id} style={styles.histRow}>
            <View style={[styles.dot, { backgroundColor: RISK_COLORS[h.risk]?.bg || C.info }]} />
            <View style={{ flex: 1 }}>
              <Text style={styles.histText} numberOfLines={1}>{tx(h.text)}</Text>
              <Text style={styles.histMeta}>{h.risk.toUpperCase()} · {String(h.created_at).slice(0, 16).replace('T', ' ')}</Text>
            </View>
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  sub: { paddingHorizontal: S.lg, paddingVertical: 6, backgroundColor: C.brandTer },
  subText: { color: C.brand, fontSize: 10, fontWeight: '900', letterSpacing: 1 },
  lbl: { fontSize: 10, letterSpacing: 2, color: C.onS3, fontWeight: '800', marginBottom: 6 },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 15, color: C.fg, minHeight: 110, textAlignVertical: 'top' },
  secBtn: { flex: 1, flexDirection: 'row', gap: 6, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: C.borderStrong, paddingVertical: S.md },
  secBtnText: { fontWeight: '900', letterSpacing: 1, fontSize: 11, color: C.fg },
  priBtn: { flex: 1, flexDirection: 'row', gap: 6, alignItems: 'center', justifyContent: 'center', backgroundColor: C.inverse, paddingVertical: S.md },
  priBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 11 },
  resultCard: { marginTop: S.lg, borderWidth: 2.5, padding: 0 },
  riskBadge: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: S.md },
  riskText: { flex: 1, fontWeight: '900', letterSpacing: 2, fontSize: 14 },
  verdict: { padding: S.md, fontWeight: '900', fontSize: 16, color: C.fg },
  reasonRow: { flexDirection: 'row', gap: 6, paddingHorizontal: S.md, marginBottom: 4, alignItems: 'flex-start' },
  reasonText: { flex: 1, color: C.onS3, fontSize: 13, lineHeight: 18 },
  adviceBox: { margin: S.md, borderTopWidth: 1.5, borderColor: C.border, paddingTop: S.md },
  adviceLbl: { fontSize: 10, letterSpacing: 2, color: C.brand, fontWeight: '900', marginBottom: 4 },
  adviceText: { color: C.fg, fontSize: 14, lineHeight: 20 },
  section: { marginTop: S.xl, marginBottom: S.md, fontSize: 11, letterSpacing: 2, color: C.fg, fontWeight: '900' },
  noData: { color: C.onS3, fontSize: 12, letterSpacing: 1 },
  histRow: { flexDirection: 'row', gap: S.md, alignItems: 'center', borderWidth: 1.5, borderColor: C.border, padding: S.md, marginBottom: S.sm },
  dot: { width: 12, height: 12 },
  histText: { fontWeight: '700', color: C.fg, fontSize: 12 },
  histMeta: { color: C.onS3, fontSize: 10, marginTop: 2, letterSpacing: 1 },
});
