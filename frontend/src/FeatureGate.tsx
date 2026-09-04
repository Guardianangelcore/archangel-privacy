/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// FEATURE GATE — plan paywall PLUS "buy only this feature" (one-off, permanent; GA-T or EUR).
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ActivityIndicator } from 'react-native';
import Ionicons from '@react-native-vector-icons/ionicons';
import Paywall from './Paywall';
import { api } from './api';
import { useAuth } from './auth';
import { C, S, R } from './theme';
import { tap } from './ui/glass';

export type FeatureId = 'ghost_mode' | 'bunker' | 'analyst' | 'mesh_sms';
type Cat = { id: FeatureId; label: string; eur: number; gat: number; tier: string; unlocked: boolean };

/** Resolves whether `feature` is unlocked (tier or one-off purchase). */
export function useFeature(feature: FeatureId) {
  const { user } = useAuth() as any;
  const [state, setState] = useState<{ loading: boolean; unlocked: boolean; cat: Cat | null }>({ loading: true, unlocked: false, cat: null });
  const load = useCallback(async () => {
    try {
      const r: any = await api('/features/catalog');
      const cat = (r.features as Cat[]).find(f => f.id === feature) || null;
      setState({ loading: false, unlocked: !!cat?.unlocked, cat });
    } catch { setState(s => ({ ...s, loading: false })); }
  }, [feature]);
  useEffect(() => { load(); }, [load, user?.tier, user?.demo_until, user?.features_owned?.length]);
  return { ...state, reload: load };
}

export default function FeatureGate({ feature, message, children }: { feature: FeatureId; message: string; children: React.ReactNode }) {
  const { loading, unlocked, cat, reload } = useFeature(feature);
  const { refresh } = useAuth() as any;
  const [busy, setBusy] = useState<'gat' | 'eur' | null>(null);
  const [err, setErr] = useState('');

  const buy = async (currency: 'gat' | 'eur') => {
    tap('medium'); setBusy(currency); setErr('');
    try {
      await api('/features/buy', { method: 'POST', body: JSON.stringify({ feature, currency }) });
      tap('success');
      await refresh?.(); await reload();
    } catch (e: any) { setErr(String(e.message || e)); tap('error'); }
    finally { setBusy(null); }
  };

  if (loading) return <ActivityIndicator color={C.brand} style={{ marginTop: S.xl }} />;
  if (unlocked) return <>{children}</>;
  return (
    <View testID={`gate-${feature}`}>
      <Paywall tier="sentinel" message={message} onUnlocked={() => { refresh?.(); reload(); }} />
      {!!cat && (
        <View style={st.box}>
          <Text style={st.title}>OR BUY ONLY THIS FEATURE</Text>
          <Text style={st.sub}>{cat.label} · one-off · yours forever</Text>
          <View style={st.row}>
            <Pressable testID={`buy-gat-${feature}`} onPress={() => buy('gat')} disabled={!!busy} style={[st.btn, st.gat]}>
              {busy === 'gat' ? <ActivityIndicator color={C.brand} /> : <><Ionicons name="diamond" size={14} color={C.brand} /><Text style={st.gatText}>{cat.gat.toFixed(0)} GA-T</Text></>}
            </Pressable>
            <Pressable testID={`buy-eur-${feature}`} onPress={() => buy('eur')} disabled={!!busy} style={[st.btn, st.eur]}>
              {busy === 'eur' ? <ActivityIndicator color={C.onInverse} /> : <><Ionicons name="card" size={14} color={C.onInverse} /><Text style={st.eurText}>€{cat.eur.toFixed(2)}</Text></>}
            </Pressable>
          </View>
          {!!err && <Text style={st.err}>{err}</Text>}
        </View>
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
  eur: { backgroundColor: C.brand },
  gatText: { color: C.brand, fontWeight: '900', letterSpacing: 1 },
  eurText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1 },
  err: { color: C.error, fontSize: 11, fontWeight: '800', textAlign: 'center' },
});
