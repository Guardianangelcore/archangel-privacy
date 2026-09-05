/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// FEATURE GATE — subscription-tier paywall with:
//  • one-off "buy only this feature" (GA-T) ONLY for purchasable features (Ghost Mode, Analyst)
//  • subscription-only features (Bunker Mode, Mesh SMS → Sentinel+; Bio-Digital Twin → Archangel) — never sold one-off
//  • OFFLINE CACHE for emergency-core features: once the server confirms the entitlement, `offline_until`
//    (active plan → +90 d, lapsed plan → end of the 90-day grace) is stored on-device, so Bunker Mode and
//    Mesh SMS keep working with no internet and no payment check. The cache is refreshed on every successful
//    check and cleared the moment the server says the grace period is over.
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ActivityIndicator } from 'react-native';
import Ionicons from '@react-native-vector-icons/ionicons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Paywall from './Paywall';
import { api } from './api';
import { useAuth } from './auth';
import { C, S, R } from './theme';
import { tap } from './ui/glass';

export type FeatureId = 'ghost_mode' | 'bunker' | 'analyst' | 'mesh_sms' | 'twin';
type Cat = {
  id: FeatureId; label: string; tier: 'guardian' | 'sentinel' | 'archangel'; unlocked: boolean;
  purchasable?: boolean; eur?: number; gat?: number;
  in_grace?: boolean; grace_until?: string | null; offline_until?: string | null; grace_days?: number; emergency?: boolean;
};
const CACHE_KEY = (f: FeatureId) => `feature_cache.${f}`;

async function readCache(f: FeatureId): Promise<{ until: string; cat: Cat } | null> {
  try {
    const raw = await AsyncStorage.getItem(CACHE_KEY(f));
    if (!raw) return null;
    const v = JSON.parse(raw);
    return v?.until && new Date(v.until).getTime() > Date.now() ? v : null;
  } catch { return null; }
}

/** Resolves whether `feature` is unlocked (tier, grace period, one-off purchase or offline cache). */
export function useFeature(feature: FeatureId) {
  const { user } = useAuth() as any;
  const [state, setState] = useState<{ loading: boolean; unlocked: boolean; cat: Cat | null; offline: boolean }>({ loading: true, unlocked: false, cat: null, offline: false });
  const load = useCallback(async () => {
    try {
      const r: any = await api('/features/catalog');
      const cat = (r.features as Cat[]).find(f => f.id === feature) || null;
      setState({ loading: false, unlocked: !!cat?.unlocked, cat, offline: false });
      if (cat?.unlocked && cat.offline_until) await AsyncStorage.setItem(CACHE_KEY(feature), JSON.stringify({ until: cat.offline_until, cat }));
      else await AsyncStorage.removeItem(CACHE_KEY(feature));   // server verdict wins: grace over → cache cleared
    } catch {
      // no network / server unreachable → honour the on-device entitlement (emergency features must work offline)
      const cached = await readCache(feature);
      setState({ loading: false, unlocked: !!cached, cat: cached?.cat || null, offline: true });
    }
  }, [feature]);
  useEffect(() => { load(); }, [load, user?.tier, user?.demo_until, user?.features_owned?.length]);
  return { ...state, reload: load };
}

const fmt = (s?: string | null) => (s ? String(s).slice(0, 10) : '');

export default function FeatureGate({ feature, message, children }: { feature: FeatureId; message: string; children: React.ReactNode }) {
  const { loading, unlocked, cat, offline, reload } = useFeature(feature);
  const { refresh } = useAuth() as any;
  const [busy, setBusy] = useState<'gat' | null>(null);
  const [err, setErr] = useState('');

  const buy = async (currency: 'gat') => {
    tap('medium'); setBusy(currency); setErr('');
    try {
      await api('/features/buy', { method: 'POST', body: JSON.stringify({ feature, currency }) });
      tap('success');
      await refresh?.(); await reload();
    } catch (e: any) { setErr(String(e.message || e)); tap('error'); }
    finally { setBusy(null); }
  };

  if (loading) return <ActivityIndicator color={C.brand} style={{ marginTop: S.xl }} />;
  if (unlocked) {
    return (
      <>
        {cat?.in_grace && (
          <View testID={`grace-${feature}`} style={st.grace}>
            <Ionicons name="time-outline" size={14} color={C.warn} />
            <Text style={st.graceText}>Subscription expired — {cat.label} stays active until {fmt(cat.grace_until)} (grace period). Renew to keep it.</Text>
          </View>
        )}
        {offline && (
          <View testID={`offline-${feature}`} style={st.grace}>
            <Ionicons name="cloud-offline-outline" size={14} color={C.info} />
            <Text style={[st.graceText, { color: C.info }]}>Offline — using the entitlement saved on this device.</Text>
          </View>
        )}
        {children}
      </>
    );
  }
  const tier = cat?.tier === 'archangel' ? 'archangel' : 'sentinel';
  return (
    <View testID={`gate-${feature}`}>
      <Paywall tier={tier} message={message} onUnlocked={() => { refresh?.(); reload(); }} />
      {!!cat && cat.purchasable !== false && typeof cat.gat === 'number' && (
        <View style={st.box}>
          <Text style={st.title}>OR BUY ONLY THIS FEATURE</Text>
          <Text style={st.sub}>{cat.label} · one-off · yours forever</Text>
          <View style={st.row}>
            <Pressable testID={`buy-gat-${feature}`} onPress={() => buy('gat')} disabled={!!busy} style={[st.btn, st.gat]}>
              {busy === 'gat' ? <ActivityIndicator color={C.brand} /> : <><Ionicons name="diamond" size={14} color={C.brand} /><Text style={st.gatText}>{cat.gat.toFixed(0)} GA-T</Text></>}
            </Pressable>
          </View>
          {!!err && <Text style={st.err}>{err}</Text>}
        </View>
      )}
      {!!cat && cat.purchasable === false && (
        <Text testID={`subonly-${feature}`} style={st.subOnly}>
          {cat.label} is a subscription feature ({cat.tier === 'archangel' ? 'Archangel' : 'Sentinel and above'}) — it is not sold one-off.
          {cat.emergency ? ` Once active it works offline and stays on for ${cat.grace_days} days after your plan ends.` : ''}
        </Text>
      )}
    </View>
  );
}

const st = StyleSheet.create({
  box: { marginTop: S.md, borderWidth: 1, borderColor: 'rgba(212,175,55,0.45)', backgroundColor: 'rgba(212,175,55,0.06)', padding: S.lg, gap: S.sm, alignItems: 'center', borderRadius: R.md },
  title: { color: C.brand, fontWeight: '900', letterSpacing: 2.5, fontSize: 11 },
  sub: { color: C.info, fontSize: 12 },
  row: { flexDirection: 'row', gap: S.sm, alignSelf: 'stretch' },
  btn: { flex: 1, minHeight: 48, flexDirection: 'row', gap: 6, alignItems: 'center', justifyContent: 'center', borderRadius: R.sm },
  gat: { borderWidth: 1, borderColor: C.brand },
  gatText: { color: C.brand, fontWeight: '900', letterSpacing: 1 },
  err: { color: C.error, fontSize: 11, fontWeight: '800', textAlign: 'center' },
  subOnly: { color: C.info, fontSize: 11, lineHeight: 16, textAlign: 'center', marginTop: S.md, paddingHorizontal: S.md },
  grace: { flexDirection: 'row', alignItems: 'center', gap: S.sm, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, padding: S.sm, marginBottom: S.sm, backgroundColor: 'rgba(255,255,255,0.03)' },
  graceText: { flex: 1, color: C.warn, fontSize: 11, lineHeight: 15 },
});
