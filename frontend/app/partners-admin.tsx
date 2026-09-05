/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// PARTNER APPROVAL PANEL — Founder-only. Every self-registered UHP partner starts
// PENDING; nothing is ingested until the Foundation approves it here with one tap.
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator, RefreshControl, TextInput } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api, errMsg } from '@/src/api';
import { tap } from '@/src/ui/glass';
import { C, S, R } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

type Status = 'pending' | 'active' | 'suspended';
type Partner = {
  partner_id: string; org_name: string; org_type: string; country: string; contact_email: string;
  status: Status; ingested_total?: number; consents?: number; created_at?: string; approved_at?: string; suspended_at?: string;
};
type AdminData = { pending: Partner[]; active: Partner[]; suspended: Partner[]; counts: Record<string, number> };

const TABS: Status[] = ['pending', 'active', 'suspended'];
const STATUS_COLOR: Record<Status, string> = { pending: C.warn, active: C.accent, suspended: C.error };
const ORG_ICON: Record<string, string> = {
  clinic: 'medkit-outline', insurer: 'shield-checkmark-outline', lab: 'flask-outline',
  sensor_network: 'radio-outline', government: 'business-outline', pharmacy: 'bandage-outline',
};

const fmtDate = (s?: string) => (s ? String(s).slice(0, 10) : '—');

export default function PartnersAdmin() {
  const { t: tt } = useI18n();
  const router = useRouter();
  const [data, setData] = useState<AdminData | null>(null);
  const [err, setErr] = useState('');
  const [forbidden, setForbidden] = useState(false);
  const [tab, setTab] = useState<Status>('pending');
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [msg, setMsg] = useState('');

  const load = useCallback(async (silent = false) => {
    if (!silent) setErr('');
    try {
      setData(await api('/uhp/partners/admin'));
      setForbidden(false);
    } catch (e: any) {
      if (/^403/.test(String(e?.message || e))) setForbidden(true);
      else setErr(errMsg(e));
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const onRefresh = async () => { setRefreshing(true); await load(true); setRefreshing(false); };

  const act = async (p: Partner, action: 'approve' | 'suspend') => {
    tap(action === 'approve' ? 'light' : 'medium');
    setBusy(p.partner_id);
    setMsg('');
    try {
      await api(`/uhp/partners/${p.partner_id}/${action}`, { method: 'POST' });
      const next: Status = action === 'approve' ? 'active' : 'suspended';
      // optimistic move between buckets
      setData(prev => {
        if (!prev) return prev;
        const out: AdminData = { pending: [], active: [], suspended: [], counts: {} };
        for (const s of TABS) out[s] = prev[s].filter(x => x.partner_id !== p.partner_id);
        out[next] = [{ ...p, status: next }, ...out[next]];
        out.counts = { pending: out.pending.length, active: out.active.length, suspended: out.suspended.length };
        return out;
      });
      setMsg(`${p.org_name} → ${tt(`partners_admin.${next}`)}`);
    } catch (e: any) {
      setErr(errMsg(e));
      load(true);
    }
    setBusy('');
  };

  const rows = useMemo(() => {
    const list = data?.[tab] || [];
    const needle = q.trim().toLowerCase();
    if (!needle) return list;
    return list.filter(p => [p.org_name, p.contact_email, p.country, p.org_type, p.partner_id].some(v => String(v || '').toLowerCase().includes(needle)));
  }, [data, tab, q]);

  return (
    <SafeAreaView testID="partners-admin-screen" style={st.root} edges={['top', 'bottom']}>
      <View style={st.header}>
        <Pressable testID="pa-back" onPress={() => { tap(); router.back(); }} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={st.headTitle}>{tt('partners_admin.title')}</Text>
        <Ionicons name="shield-checkmark-outline" size={20} color={C.brand} />
      </View>

      {forbidden ? (
        <View style={st.center}>
          <Ionicons name="lock-closed-outline" size={40} color={C.brand} />
          <Text testID="pa-forbidden" style={st.forbidTitle}>{tt('partners_admin.foundation_only')}</Text>
          <Text style={st.forbidSub}>{tt('partners_admin.foundation_only_sub')}</Text>
        </View>
      ) : (
        <>
          <Text style={st.kicker}>{tt('partners_admin.kicker')}</Text>
          <Text style={st.sub}>{tt('partners_admin.sub')}</Text>

          {/* STATUS TABS */}
          <View style={st.tabs}>
            {TABS.map(s => {
              const on = tab === s;
              const n = data?.counts?.[s] ?? 0;
              return (
                <Pressable key={s} testID={`pa-tab-${s}`} onPress={() => { tap('light'); setTab(s); }}
                  style={[st.tab, on && { borderColor: STATUS_COLOR[s], backgroundColor: 'rgba(255,255,255,0.06)' }]}>
                  <View style={[st.dot, { backgroundColor: STATUS_COLOR[s] }]} />
                  <Text style={[st.tabText, on && { color: C.fg }]}>{tt(`partners_admin.${s}`)}</Text>
                  <View style={[st.badge, on && { backgroundColor: STATUS_COLOR[s] }]}>
                    <Text testID={`pa-count-${s}`} style={[st.badgeText, on && { color: C.onWarn }]}>{n}</Text>
                  </View>
                </Pressable>
              );
            })}
          </View>

          <View style={st.search}>
            <Ionicons name="search-outline" size={16} color={C.info} />
            <TextInput testID="pa-search" value={q} onChangeText={setQ} placeholder={tt('partners_admin.search')}
              placeholderTextColor={C.info} style={st.searchInput} autoCapitalize="none" autoCorrect={false} />
            {!!q && (
              <Pressable onPress={() => setQ('')} hitSlop={10}><Ionicons name="close-circle" size={16} color={C.info} /></Pressable>
            )}
          </View>

          {!!msg && <Text testID="pa-msg" style={st.msg}>✓ {msg}</Text>}
          {!!err && <Text testID="pa-err" style={st.err}>{err}</Text>}

          <ScrollView contentContainerStyle={{ paddingBottom: 80 }} keyboardShouldPersistTaps="handled"
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={C.brand} />}>
            {!data && !err && <ActivityIndicator color={C.brand} style={{ marginTop: 60 }} />}

            {data && rows.length === 0 && (
              <View style={st.empty}>
                <Ionicons name={tab === 'pending' ? 'checkmark-done-outline' : 'folder-open-outline'} size={34} color={C.info} />
                <Text testID="pa-empty" style={st.emptyText}>
                  {q ? tt('partners_admin.no_match') : tt(`partners_admin.empty_${tab}`)}
                </Text>
              </View>
            )}

            {rows.map(p => {
              const isBusy = busy === p.partner_id;
              return (
                <View key={p.partner_id} testID={`pa-row-${p.partner_id}`} style={[st.card, { borderLeftColor: STATUS_COLOR[p.status] }]}>
                  <View style={st.cardHead}>
                    <View style={st.orgIcon}>
                      <Ionicons name={(ORG_ICON[p.org_type] || 'business-outline') as any} size={18} color={C.brand} />
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={st.orgName} numberOfLines={1}>{p.org_name}</Text>
                      <Text style={st.orgMeta}>{String(p.org_type || '').replace('_', ' ').toUpperCase()} · {p.country}</Text>
                    </View>
                    <View style={[st.statusPill, { borderColor: STATUS_COLOR[p.status] }]}>
                      <Text style={[st.statusText, { color: STATUS_COLOR[p.status] }]}>{tt(`partners_admin.${p.status}`)}</Text>
                    </View>
                  </View>

                  <Text style={st.email} numberOfLines={1}>
                    <Ionicons name="mail-outline" size={11} color={C.info} /> {p.contact_email}
                  </Text>
                  <View style={st.statsRow}>
                    <Text style={st.stat}>{tt('partners_admin.registered')} {fmtDate(p.created_at)}</Text>
                    <Text style={st.stat}>{tt('partners_admin.ingested')} {p.ingested_total ?? 0}</Text>
                    <Text style={st.stat}>{tt('partners_admin.consents')} {p.consents ?? 0}</Text>
                  </View>
                  <Text style={st.pid}>{p.partner_id}</Text>

                  <View style={st.actions}>
                    {p.status !== 'active' && (
                      <Pressable testID={`pa-approve-${p.partner_id}`} disabled={isBusy} onPress={() => act(p, 'approve')}
                        style={[st.btn, st.btnApprove, isBusy && st.btnDim]}>
                        {isBusy ? <ActivityIndicator size="small" color={C.onWarn} /> : <Ionicons name="checkmark-circle" size={18} color={C.onWarn} />}
                        <Text style={st.btnApproveText}>
                          {p.status === 'pending' ? tt('partners_admin.approve') : tt('partners_admin.reactivate')}
                        </Text>
                      </Pressable>
                    )}
                    {p.status !== 'suspended' && (
                      <Pressable testID={`pa-suspend-${p.partner_id}`} disabled={isBusy} onPress={() => act(p, 'suspend')}
                        style={[st.btn, st.btnSuspend, isBusy && st.btnDim]}>
                        {isBusy ? <ActivityIndicator size="small" color={C.error} /> : <Ionicons name="ban-outline" size={18} color={C.error} />}
                        <Text style={st.btnSuspendText}>
                          {p.status === 'pending' ? tt('partners_admin.reject') : tt('partners_admin.suspend')}
                        </Text>
                      </Pressable>
                    )}
                  </View>
                </View>
              );
            })}

            {data && <Text style={st.footer}>{tt('partners_admin.footer')}</Text>}
          </ScrollView>
        </>
      )}
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  headTitle: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 14 },
  kicker: { color: C.brand, fontWeight: '900', fontSize: 10, letterSpacing: 3, paddingHorizontal: S.lg, marginTop: S.xs },
  sub: { color: C.info, fontSize: 11.5, lineHeight: 16, paddingHorizontal: S.lg, marginTop: 4 },
  tabs: { flexDirection: 'row', gap: S.sm, paddingHorizontal: S.lg, marginTop: S.lg },
  tab: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, minHeight: 44, borderWidth: 1.5, borderColor: C.border, borderRadius: R.md, paddingHorizontal: 6 },
  dot: { width: 7, height: 7, borderRadius: 4 },
  tabText: { color: C.info, fontWeight: '900', fontSize: 9.5, letterSpacing: 1 },
  badge: { minWidth: 20, height: 20, borderRadius: R.pill, backgroundColor: C.surface3, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 5 },
  badgeText: { color: C.fg, fontWeight: '900', fontSize: 10 },
  search: { flexDirection: 'row', alignItems: 'center', gap: S.sm, marginHorizontal: S.lg, marginTop: S.md, borderWidth: 1, borderColor: C.border, borderRadius: R.md, backgroundColor: C.surface2, paddingHorizontal: S.md, minHeight: 44 },
  searchInput: { flex: 1, color: C.fg, fontSize: 13, paddingVertical: 10 },
  msg: { color: C.accent, fontWeight: '800', fontSize: 11.5, paddingHorizontal: S.lg, marginTop: S.sm },
  err: { color: C.error, fontSize: 11.5, paddingHorizontal: S.lg, marginTop: S.sm },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: S.xl, gap: S.sm },
  forbidTitle: { color: C.fg, fontWeight: '900', fontSize: 16, letterSpacing: 2, marginTop: S.sm },
  forbidSub: { color: C.info, fontSize: 12, textAlign: 'center', lineHeight: 17 },
  empty: { alignItems: 'center', paddingVertical: S.xxxl, gap: S.sm },
  emptyText: { color: C.info, fontSize: 12.5, textAlign: 'center', paddingHorizontal: S.xl },
  card: { marginHorizontal: S.lg, marginTop: S.md, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, borderLeftWidth: 4, padding: S.md },
  cardHead: { flexDirection: 'row', alignItems: 'center', gap: S.sm },
  orgIcon: { width: 38, height: 38, borderRadius: R.pill, backgroundColor: 'rgba(212,175,55,0.14)', alignItems: 'center', justifyContent: 'center' },
  orgName: { color: C.fg, fontWeight: '900', fontSize: 14 },
  orgMeta: { color: C.info, fontWeight: '800', fontSize: 9.5, letterSpacing: 1, marginTop: 2 },
  statusPill: { borderWidth: 1, borderRadius: R.pill, paddingHorizontal: 8, paddingVertical: 3 },
  statusText: { fontWeight: '900', fontSize: 8.5, letterSpacing: 1.5 },
  email: { color: C.onS3, fontSize: 11.5, marginTop: S.sm },
  statsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: S.md, marginTop: 6 },
  stat: { color: C.info, fontSize: 10.5 },
  pid: { color: C.info, fontSize: 9, marginTop: 4, opacity: 0.7 },
  actions: { flexDirection: 'row', gap: S.sm, marginTop: S.md },
  btn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, minHeight: 46, borderRadius: R.md, borderWidth: 1.5 },
  btnDim: { opacity: 0.6 },
  btnApprove: { backgroundColor: C.brand, borderColor: C.brand },
  btnApproveText: { color: C.onWarn, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  btnSuspend: { borderColor: C.error, backgroundColor: 'rgba(255,69,58,0.08)' },
  btnSuspendText: { color: C.error, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  footer: { textAlign: 'center', color: C.info, fontSize: 9, letterSpacing: 1.5, marginTop: S.xl, paddingHorizontal: S.lg, lineHeight: 14 },
});
