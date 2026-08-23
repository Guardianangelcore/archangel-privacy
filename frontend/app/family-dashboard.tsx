import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, TextInput, ScrollView, ActivityIndicator, Platform, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Pedometer } from 'expo-sensors';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';

type Dash = {
  checkins: any[]; vitals: any[]; fall_events: any[]; inactivity_alerts: any[];
  avg_steps: number; avg_heart_rate: number; anomalies: { type: string; detail: string }[];
  checked_in_today: boolean;
};

const MOOD_ICONS: Record<number, any> = { 5: 'sunny', 4: 'partly-sunny', 3: 'cloud-outline', 2: 'rainy-outline', 1: 'thunderstorm-outline' };

export default function FamilyDashboard() {
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const router = useRouter();
  const [dash, setDash] = useState<Dash | null>(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [hr, setHr] = useState('');
  const [stepsMsg, setStepsMsg] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try { setDash(await api<Dash>('/wellness/dashboard')); } catch (e) { console.log(e); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const syncSteps = async () => {
    setSyncing(true); setStepsMsg('');
    try {
      if (Platform.OS === 'web') { setStepsMsg('WEB: N/A — use phone'); return; }
      const perm = await Pedometer.requestPermissionsAsync();
      if (perm.status !== 'granted') { setStepsMsg('PERMISSION DENIED'); return; }
      const avail = await Pedometer.isAvailableAsync();
      if (!avail) { setStepsMsg('SENSOR N/A'); return; }
      const start = new Date(); start.setHours(0, 0, 0, 0);
      const res = await Pedometer.getStepCountAsync(start, new Date());
      await api('/wellness/vitals', { method: 'POST', body: JSON.stringify({ steps: res.steps }) });
      setStepsMsg(`✓ ${res.steps}`);
      load();
    } catch (e: any) {
      // getStepCountAsync is iOS-only; Android needs Health Connect (native build)
      setStepsMsg(Platform.OS === 'android' ? 'ANDROID: HEALTH CONNECT PO BUILDE' : 'N/A');
    } finally { setSyncing(false); }
  };

  const saveHr = async () => {
    const v = parseInt(hr, 10);
    if (!v || v < 20 || v > 250) return;
    await api('/wellness/vitals', { method: 'POST', body: JSON.stringify({ heart_rate: v }) });
    setHr('');
    load();
  };

  const todayVital = dash?.vitals?.find(v => v.date === new Date().toISOString().slice(0, 10));
  const maxSteps = Math.max(1, ...(dash?.vitals || []).map(v => v.steps || 0));

  return (
    <SafeAreaView testID="family-dashboard-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="fd-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={styles.title}>{t('family_dashboard', lang).toUpperCase()}</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView
        contentContainerStyle={{ padding: S.lg, paddingBottom: 60 }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.fg} />}
      >
        {dash?.anomalies?.length ? (
          <View testID="fd-anomalies" style={styles.anomalyBox}>
            <Ionicons name="warning" size={20} color={C.onError} />
            <View style={{ flex: 1 }}>
              {dash.anomalies.map((a, i) => (
                <Text key={i} style={styles.anomalyText}>{a.type.replace(/_/g, ' ').toUpperCase()} — {a.detail}</Text>
              ))}
            </View>
          </View>
        ) : null}

        {!dash?.checked_in_today && (
          <Pressable testID="fd-goto-checkin" onPress={() => router.push('/wellness')} style={styles.checkinBanner}>
            <Ionicons name="sparkles" size={18} color={C.brand} />
            <Text style={styles.checkinBannerText}>{t('how_feel_today', lang).toUpperCase()}</Text>
            <Ionicons name="chevron-forward" size={18} color={C.brand} />
          </Pressable>
        )}

        <Text style={styles.section}>{t('mood_trend', lang).toUpperCase()}</Text>
        {dash?.checkins?.length ? (
          <View style={styles.moodStrip}>
            {[...dash.checkins].reverse().map((c: any) => (
              <View key={c.checkin_id} style={styles.moodDot}>
                <Ionicons name={MOOD_ICONS[c.sentiment_score] || 'cloud-outline'} size={26} color={c.sentiment_score <= 2 ? C.error : C.brand} />
                <Text style={styles.moodDotDate}>{String(c.created_at).slice(5, 10)}</Text>
              </View>
            ))}
          </View>
        ) : <Text style={styles.noData}>{t('no_data', lang).toUpperCase()}</Text>}
        {dash?.checkins?.[0] && (
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLbl}>STATUS:</Text>
            <Text style={styles.summaryVal}>{dash.checkins[0].summary}</Text>
          </View>
        )}

        <Text style={styles.section}>{t('steps_today', lang).toUpperCase()}</Text>
        <View style={styles.vitalsRow}>
          <View style={styles.bigStat}>
            <Text style={styles.bigStatNum}>{todayVital?.steps ?? '—'}</Text>
            <Text style={styles.bigStatLbl}>Ø {dash?.avg_steps || '—'}</Text>
          </View>
          <Pressable testID="fd-sync-steps" onPress={syncSteps} disabled={syncing} style={styles.syncBtn}>
            {syncing ? <ActivityIndicator color={C.onInverse} /> : <>
              <Ionicons name="walk-outline" size={18} color={C.onInverse} />
              <Text style={styles.syncBtnText}>{t('sync_steps', lang).toUpperCase()}</Text>
            </>}
          </Pressable>
        </View>
        {stepsMsg ? <Text style={styles.stepsMsg}>{stepsMsg}</Text> : null}
        {dash?.vitals?.length ? (
          <View style={styles.barRow}>
            {[...dash.vitals].reverse().map((v: any) => (
              <View key={v.date} style={styles.barCol}>
                <View style={[styles.bar, { height: Math.max(4, ((v.steps || 0) / maxSteps) * 60) }]} />
                <Text style={styles.barLbl}>{v.date.slice(8)}</Text>
              </View>
            ))}
          </View>
        ) : null}

        <Text style={styles.section}>{t('heart_rate', lang).toUpperCase()}</Text>
        <View style={styles.vitalsRow}>
          <View style={styles.bigStat}>
            <Text style={styles.bigStatNum}>{todayVital?.heart_rate ?? '—'}</Text>
            <Text style={styles.bigStatLbl}>Ø {dash?.avg_heart_rate || '—'} BPM</Text>
          </View>
          <View style={{ flex: 1, flexDirection: 'row', gap: S.sm }}>
            <TextInput testID="fd-hr-input" value={hr} onChangeText={setHr} keyboardType="number-pad" style={styles.hrInput} placeholder="72" placeholderTextColor="#999" />
            <Pressable testID="fd-hr-save" onPress={saveHr} style={styles.hrBtn}>
              <Ionicons name="checkmark" size={20} color={C.onInverse} />
            </Pressable>
          </View>
        </View>

        <Text style={styles.section}>{t('alerts', lang).toUpperCase()}</Text>
        {(dash?.fall_events?.length || dash?.inactivity_alerts?.length) ? (
          <>
            {dash?.fall_events?.map((f: any) => (
              <View key={f.event_id} style={[styles.alertRow, f.verified && { borderColor: C.error }]}>
                <Ionicons name="warning-outline" size={18} color={f.verified ? C.error : C.onS3} />
                <Text style={styles.alertText}>
                  {f.cancelled ? 'PÁD — ZRUŠENÝ (OK)' : 'PÁD — ESKALOVANÝ'} · {String(f.triggered_at).slice(0, 16).replace('T', ' ')}
                </Text>
              </View>
            ))}
            {dash?.inactivity_alerts?.map((a: any) => (
              <View key={a.alert_id} style={[styles.alertRow, { borderColor: C.warn }]}>
                <Ionicons name="time-outline" size={18} color={C.onWarn} />
                <Text style={styles.alertText}>NEČINNOSŤ {a.hours_inactive}h · {String(a.created_at).slice(0, 16).replace('T', ' ')}</Text>
              </View>
            ))}
          </>
        ) : <Text style={styles.noData}>{t('no_data', lang).toUpperCase()}</Text>}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.lg, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  anomalyBox: { flexDirection: 'row', gap: S.md, backgroundColor: C.error, padding: S.md, marginBottom: S.lg, alignItems: 'center' },
  anomalyText: { color: C.onError, fontWeight: '900', fontSize: 12, letterSpacing: 1 },
  checkinBanner: { flexDirection: 'row', alignItems: 'center', gap: S.sm, borderWidth: 2, borderColor: C.brand, backgroundColor: C.brandTer, padding: S.md, marginBottom: S.md },
  checkinBannerText: { flex: 1, fontWeight: '900', letterSpacing: 1, color: C.brand, fontSize: 13 },
  section: { marginTop: S.lg, marginBottom: S.md, fontSize: 11, letterSpacing: 2, color: C.fg, fontWeight: '900' },
  noData: { color: C.onS3, fontSize: 12, letterSpacing: 1 },
  moodStrip: { flexDirection: 'row', gap: S.md, flexWrap: 'wrap' },
  moodDot: { alignItems: 'center', gap: 4 },
  moodDotDate: { fontSize: 9, color: C.onS3, letterSpacing: 1 },
  summaryRow: { flexDirection: 'row', gap: 8, marginTop: S.md, alignItems: 'center' },
  summaryLbl: { fontSize: 10, letterSpacing: 2, color: C.onS3, fontWeight: '800' },
  summaryVal: { fontWeight: '900', color: C.fg, fontSize: 14, flex: 1 },
  vitalsRow: { flexDirection: 'row', gap: S.md, alignItems: 'center' },
  bigStat: { borderWidth: 2, borderColor: C.borderStrong, padding: S.md, minWidth: 110, alignItems: 'center' },
  bigStatNum: { fontSize: 28, fontWeight: '900', color: C.fg },
  bigStatLbl: { fontSize: 10, letterSpacing: 1, color: C.onS3, marginTop: 2 },
  syncBtn: { flex: 1, flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.inverse, paddingVertical: S.lg },
  syncBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  stepsMsg: { marginTop: 6, fontSize: 11, color: C.onS3, letterSpacing: 1, fontWeight: '700' },
  barRow: { flexDirection: 'row', gap: S.sm, marginTop: S.md, alignItems: 'flex-end' },
  barCol: { alignItems: 'center', gap: 4, flex: 1 },
  bar: { width: '70%', backgroundColor: C.brandPri },
  barLbl: { fontSize: 9, color: C.onS3 },
  hrInput: { flex: 1, borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 18, fontWeight: '800', color: C.fg, textAlign: 'center' },
  hrBtn: { backgroundColor: C.inverse, paddingHorizontal: S.lg, alignItems: 'center', justifyContent: 'center' },
  alertRow: { flexDirection: 'row', gap: S.md, alignItems: 'center', borderWidth: 1.5, borderColor: C.border, padding: S.md, marginBottom: S.sm },
  alertText: { flex: 1, fontWeight: '800', color: C.fg, fontSize: 12, letterSpacing: 0.5 },
});
