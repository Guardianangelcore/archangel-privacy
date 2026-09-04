// COMMUNITY HELP — peer-verified Proof-of-Help. Requester escrows 10 GA-T (Community Fund tops up),
// helper accepts → done, requester confirms → escrow paid out. 24 h confirmation window, 5/day caps.
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator, Modal, RefreshControl, KeyboardAvoidingView, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api, errMsg } from '@/src/api';
import { useAuth } from '@/src/auth';
import { useI18n } from '@/src/i18n-context';
import { tap } from '@/src/ui/glass';
import { C, S, R } from '@/src/theme';

type Req = {
  req_id: string; title: string; details: string; category: string; status: string; reward: number;
  requester_name: string; helper_name?: string | null; mine: boolean; helping: boolean; helper_reputation?: Rep | null;
  created_at: string; expires_at: string; reserved: { wallet: number; fund: number };
};
type Rep = { completed: number; badge: 'bronze' | 'silver' | 'gold' | null; earned_gat: number; next_badge?: { badge: string; need: number } | null };
type Scope = 'open' | 'mine' | 'helping';
const BADGE_COLOR: Record<string, string> = { bronze: '#CD7F32', silver: '#C0C0C0', gold: '#D4AF37' };

/** Trust badge + confirmed-help count — driven only by requester-confirmed GA-T help flows. */
function HelperBadge({ rep, testID, big }: { rep?: Rep | null; testID: string; big?: boolean }) {
  const { t: tt } = useI18n();
  const n = rep?.completed ?? 0;
  const badge = rep?.badge;
  const color = badge ? BADGE_COLOR[badge] : C.info;
  return (
    <View testID={testID} style={[st.badge, { borderColor: color }, big && { paddingVertical: 6 }]}>
      <Ionicons name={badge ? 'shield-checkmark' : 'shield-outline'} size={big ? 16 : 12} color={color} />
      <Text style={[st.badgeText, { color }, big && { fontSize: 11 }]}>
        {badge ? tt(`help.badge_${badge}`) : tt('help.badge_none')} · {tt('help.completed').replace('{0}', String(n))}
      </Text>
    </View>
  );
}
const CAT_ICON: Record<string, string> = { errand: 'walk-outline', medication: 'medkit-outline', transport: 'car-outline', companionship: 'chatbubbles-outline', household: 'home-outline', tech: 'phone-portrait-outline', other: 'hand-right-outline' };
const STATUS_COLOR: Record<string, string> = { open: C.accent, accepted: C.primary, done: C.warn, confirmed: C.brand, expired: C.info, cancelled: C.info };

export default function CommunityHelp() {
  const { t: tt } = useI18n();
  const router = useRouter();
  const { refresh } = useAuth();
  const [scope, setScope] = useState<Scope>('open');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [title, setTitle] = useState('');
  const [details, setDetails] = useState('');
  const [category, setCategory] = useState('other');

  const load = useCallback(async (s: Scope = scope) => {
    try { setData(await api(`/help/requests?scope=${s}`)); } catch (e) { setMsg({ ok: false, text: errMsg(e) }); }
    finally { setLoading(false); }
  }, [scope]);
  useEffect(() => { load(scope); }, [scope, load]);

  const act = async (id: string, action: 'accept' | 'done' | 'confirm' | 'cancel', okText: string) => {
    tap('medium'); setBusy(`${id}-${action}`); setMsg(null);
    try {
      await api(`/help/requests/${id}/${action}`, { method: 'POST' });
      tap('success'); setMsg({ ok: true, text: okText });
      if (action === 'confirm' || action === 'cancel') refresh?.();
      await load();
    } catch (e) { tap('error'); setMsg({ ok: false, text: errMsg(e) }); }
    finally { setBusy(null); }
  };

  const create = async () => {
    if (title.trim().length < 3) { setMsg({ ok: false, text: tt('help.title_too_short') }); return; }
    tap('medium'); setBusy('new'); setMsg(null);
    try {
      await api('/help/requests', { method: 'POST', body: JSON.stringify({ title: title.trim(), details: details.trim(), category }) });
      tap('success'); setShowNew(false); setTitle(''); setDetails(''); setCategory('other');
      setMsg({ ok: true, text: tt('help.created') }); refresh?.();
      setScope('mine');
    } catch (e) { tap('error'); setMsg({ ok: false, text: errMsg(e) }); }
    finally { setBusy(null); }
  };

  const Row = ({ r }: { r: Req }) => {
    const color = STATUS_COLOR[r.status] || C.info;
    const b = (a: string) => busy === `${r.req_id}-${a}`;
    return (
      <View testID={`help-req-${r.req_id}`} style={st.card}>
        <View style={st.cardHead}>
          <Ionicons name={(CAT_ICON[r.category] || 'hand-right-outline') as any} size={20} color={C.brand} />
          <View style={{ flex: 1 }}>
            <Text style={st.title}>{r.title}</Text>
            <Text style={st.sub}>{r.mine ? tt('help.you') : r.requester_name}{r.helper_name ? ` · ${tt('help.helper')}: ${r.helping ? tt('help.you') : r.helper_name}` : ''}</Text>
          </View>
          <View style={st.reward}><Ionicons name="diamond" size={12} color={C.brand} /><Text style={st.rewardText}>{r.reward} GA-T</Text></View>
        </View>
        {!!r.details && <Text style={st.details}>{r.details}</Text>}
        {!!r.helper_name && (
          <View style={st.helperRow}>
            <Ionicons name="person-circle-outline" size={16} color={C.onS3} />
            <Text style={st.helperName}>{r.helping ? tt('help.you') : r.helper_name}</Text>
            <HelperBadge rep={r.helper_reputation} testID={`help-badge-${r.req_id}`} />
          </View>
        )}
        <View style={st.foot}>
          <View style={[st.status, { borderColor: color }]}><Text style={[st.statusText, { color }]}>{tt(`help.status_${r.status}`)}</Text></View>
          <View style={st.actions}>
            {r.status === 'open' && !r.mine && (
              <Pressable testID={`help-accept-${r.req_id}`} onPress={() => act(r.req_id, 'accept', tt('help.accepted_msg'))} disabled={!!busy} style={[st.btn, st.btnPri]}>
                {b('accept') ? <ActivityIndicator size="small" color={C.onInverse} /> : <Text style={st.btnPriText}>{tt('help.accept')}</Text>}
              </Pressable>
            )}
            {r.status === 'open' && r.mine && (
              <Pressable testID={`help-cancel-${r.req_id}`} onPress={() => act(r.req_id, 'cancel', tt('help.cancelled_msg'))} disabled={!!busy} style={st.btn}>
                {b('cancel') ? <ActivityIndicator size="small" color={C.fg} /> : <Text style={st.btnText}>{tt('help.cancel')}</Text>}
              </Pressable>
            )}
            {r.status === 'accepted' && r.helping && (
              <Pressable testID={`help-done-${r.req_id}`} onPress={() => act(r.req_id, 'done', tt('help.done_msg'))} disabled={!!busy} style={[st.btn, st.btnPri]}>
                {b('done') ? <ActivityIndicator size="small" color={C.onInverse} /> : <Text style={st.btnPriText}>{tt('help.mark_done')}</Text>}
              </Pressable>
            )}
            {r.status === 'done' && r.mine && (
              <Pressable testID={`help-confirm-${r.req_id}`} onPress={() => act(r.req_id, 'confirm', tt('help.confirmed_msg'))} disabled={!!busy} style={[st.btn, st.btnGold]}>
                {b('confirm') ? <ActivityIndicator size="small" color={C.onInverse} /> : <><Ionicons name="checkmark-circle" size={16} color={C.onInverse} /><Text style={st.btnPriText}>{tt('help.confirm')}</Text></>}
              </Pressable>
            )}
            {r.status === 'done' && r.helping && <Text style={st.wait}>{tt('help.waiting_confirm')}</Text>}
          </View>
        </View>
      </View>
    );
  };

  const reqs: Req[] = data?.requests || [];
  return (
    <SafeAreaView style={st.root} edges={['top', 'bottom']} testID="community-help-screen">
      <View style={st.header}>
        <Pressable testID="help-back" onPress={() => router.back()} hitSlop={12}><Ionicons name="chevron-back" size={26} color={C.fg} /></Pressable>
        <View style={{ flex: 1 }}>
          <Text style={st.h1}>{tt('help.title')}</Text>
          <Text style={st.h2}>{tt('help.subtitle')}</Text>
        </View>
        <Pressable testID="help-wallet" onPress={() => router.push('/token')} hitSlop={10}><Ionicons name="wallet-outline" size={22} color={C.brand} /></Pressable>
      </View>

      <Pressable testID="help-new" onPress={() => { tap('medium'); setMsg(null); setShowNew(true); }} style={st.newBtn}>
        <Ionicons name="hand-left" size={20} color={C.onInverse} />
        <Text style={st.newText}>{tt('help.request_help')}</Text>
        <Text style={st.newSub}>{tt('help.reward_note').replace('{0}', String(data?.reward ?? 10))}</Text>
      </Pressable>

      <View style={st.tabs}>
        {(['open', 'mine', 'helping'] as Scope[]).map(s => (
          <Pressable key={s} testID={`help-tab-${s}`} onPress={() => { tap('light'); setScope(s); }} style={[st.tab, scope === s && st.tabOn]}>
            <Text style={[st.tabText, scope === s && { color: C.onInverse }]}>{tt(`help.tab_${s}`)}</Text>
          </Pressable>
        ))}
      </View>

      {!!msg && <Text testID="help-msg" style={[st.msg, { color: msg.ok ? C.accent : C.error }]}>{msg.text}</Text>}
      {data?.my_reputation && (
        <View style={st.myRep}>
          <Text style={st.myRepLabel}>{tt('help.my_reputation')}</Text>
          <HelperBadge rep={data.my_reputation} testID="help-my-badge" big />
          {!!data.my_reputation.next_badge && (
            <Text style={st.nextBadge}>{tt('help.next_badge').replace('{0}', String(data.my_reputation.next_badge.need)).replace('{1}', tt(`help.badge_${data.my_reputation.next_badge.badge}`))}</Text>
          )}
        </View>
      )}
      {data?.limits && (
        <Text style={st.limits}>{tt('help.limits').split('{1}').join(String(data.limits.daily_max)).replace('{0}', String(data.limits.requests_today)).replace('{2}', String(data.limits.confirms_today))}</Text>
      )}

      <ScrollView contentContainerStyle={st.body} refreshControl={<RefreshControl refreshing={loading} onRefresh={() => load()} tintColor={C.brand} />}>
        {loading && !data ? <ActivityIndicator color={C.brand} style={{ marginTop: S.xl }} /> :
          reqs.length === 0 ? (
            <View style={st.empty}>
              <Ionicons name="people-outline" size={36} color={C.info} />
              <Text style={st.emptyText}>{tt(`help.empty_${scope}`)}</Text>
            </View>
          ) : reqs.map(r => <Row key={r.req_id} r={r} />)}
        <Text style={st.rules}>{tt('help.rules')}</Text>
      </ScrollView>

      <Modal visible={showNew} transparent animationType="slide" onRequestClose={() => setShowNew(false)}>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={st.backdrop}>
          <Pressable style={{ flex: 1 }} onPress={() => setShowNew(false)} />
          <View style={st.sheet} testID="help-new-sheet">
            <Text style={st.sheetTitle}>{tt('help.what_do_you_need')}</Text>
            <TextInput testID="help-new-title" style={st.input} placeholder={tt('help.title_ph')} placeholderTextColor={C.info} value={title} onChangeText={setTitle} maxLength={80} />
            <TextInput testID="help-new-details" style={[st.input, { minHeight: 72 }]} placeholder={tt('help.details_ph')} placeholderTextColor={C.info} value={details} onChangeText={setDetails} multiline maxLength={400} />
            <View style={st.cats}>
              {(data?.categories || Object.keys(CAT_ICON)).map((c: string) => (
                <Pressable key={c} testID={`help-cat-${c}`} onPress={() => { tap('light'); setCategory(c); }} style={[st.cat, category === c && st.catOn]}>
                  <Ionicons name={(CAT_ICON[c] || 'hand-right-outline') as any} size={14} color={category === c ? C.onInverse : C.fg} />
                  <Text style={[st.catText, category === c && { color: C.onInverse }]}>{tt(`help.cat_${c}`)}</Text>
                </Pressable>
              ))}
            </View>
            <Text style={st.escrow}>{tt('help.escrow_note').replace('{0}', String(data?.reward ?? 10))}</Text>
            {!!msg && !msg.ok && <Text style={[st.msg, { color: C.error, paddingHorizontal: 0 }]}>{msg.text}</Text>}
            <Pressable testID="help-new-submit" onPress={create} disabled={busy === 'new'} style={st.submit}>
              {busy === 'new' ? <ActivityIndicator color={C.onInverse} /> : <Text style={st.submitText}>{tt('help.submit')}</Text>}
            </Pressable>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', gap: S.sm, paddingHorizontal: S.lg, paddingVertical: S.md },
  h1: { color: C.fg, fontWeight: '900', fontSize: 16, letterSpacing: 2 },
  h2: { color: C.info, fontSize: 11, marginTop: 2 },
  newBtn: { marginHorizontal: S.lg, backgroundColor: C.brand, borderRadius: R.md, padding: S.lg, minHeight: 64, flexDirection: 'row', alignItems: 'center', gap: S.sm, flexWrap: 'wrap' },
  newText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 14 },
  newSub: { color: C.onInverse, fontSize: 11, opacity: 0.8, width: '100%' },
  tabs: { flexDirection: 'row', gap: S.sm, paddingHorizontal: S.lg, marginTop: S.md },
  tab: { flex: 1, minHeight: 40, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: C.border, borderRadius: R.pill },
  tabOn: { backgroundColor: C.inverse, borderColor: C.inverse },
  tabText: { color: C.fg, fontWeight: '900', fontSize: 10.5, letterSpacing: 1 },
  msg: { paddingHorizontal: S.lg, marginTop: S.sm, fontSize: 12, fontWeight: '700' },
  limits: { paddingHorizontal: S.lg, marginTop: S.xs, color: C.info, fontSize: 10.5 },
  body: { padding: S.lg, gap: S.md, paddingBottom: S.xxl },
  card: { borderWidth: 1, borderColor: C.border, backgroundColor: C.surface2, borderRadius: R.md, padding: S.md, gap: S.sm },
  cardHead: { flexDirection: 'row', alignItems: 'center', gap: S.sm },
  title: { color: C.fg, fontWeight: '800', fontSize: 14 },
  sub: { color: C.info, fontSize: 11, marginTop: 2 },
  details: { color: C.onS3, fontSize: 12, lineHeight: 17 },
  reward: { flexDirection: 'row', alignItems: 'center', gap: 4, borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.pill, paddingHorizontal: 8, paddingVertical: 4 },
  rewardText: { color: C.brand, fontWeight: '900', fontSize: 11 },
  helperRow: { flexDirection: 'row', alignItems: 'center', gap: 6, flexWrap: 'wrap' },
  helperName: { color: C.onS3, fontSize: 12, fontWeight: '700' },
  badge: { flexDirection: 'row', alignItems: 'center', gap: 4, borderWidth: 1, borderRadius: R.pill, paddingHorizontal: 8, paddingVertical: 3 },
  badgeText: { fontSize: 9.5, fontWeight: '900', letterSpacing: 0.6 },
  myRep: { flexDirection: 'row', alignItems: 'center', gap: S.sm, paddingHorizontal: S.lg, marginTop: S.sm, flexWrap: 'wrap' },
  myRepLabel: { color: C.info, fontSize: 10.5, fontWeight: '800', letterSpacing: 1 },
  nextBadge: { color: C.info, fontSize: 10.5, width: '100%' },
  foot: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: S.sm, flexWrap: 'wrap' },
  status: { borderWidth: 1, borderRadius: R.pill, paddingHorizontal: 8, paddingVertical: 3 },
  statusText: { fontSize: 9.5, fontWeight: '900', letterSpacing: 1 },
  actions: { flexDirection: 'row', gap: S.sm, alignItems: 'center' },
  btn: { minHeight: 44, paddingHorizontal: S.md, borderRadius: R.sm, borderWidth: 1, borderColor: C.border, alignItems: 'center', justifyContent: 'center', flexDirection: 'row', gap: 6 },
  btnPri: { backgroundColor: C.primary, borderColor: C.primary },
  btnGold: { backgroundColor: C.brand, borderColor: C.brand },
  btnText: { color: C.fg, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  btnPriText: { color: C.onInverse, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  wait: { color: C.warn, fontSize: 11, fontWeight: '700' },
  empty: { alignItems: 'center', gap: S.sm, paddingVertical: S.xxl },
  emptyText: { color: C.info, fontSize: 12, textAlign: 'center', paddingHorizontal: S.xl },
  rules: { color: C.info, fontSize: 10.5, lineHeight: 15, marginTop: S.md, textAlign: 'center' },
  backdrop: { flex: 1, backgroundColor: C.surface3 },
  sheet: { backgroundColor: C.bg, borderTopLeftRadius: R.lg, borderTopRightRadius: R.lg, borderTopWidth: 1, borderColor: C.borderStrong, padding: S.lg, paddingBottom: S.xxl, gap: S.sm },
  sheetTitle: { color: C.brand, fontWeight: '900', letterSpacing: 2, fontSize: 12 },
  input: { borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.sm, padding: S.md, color: C.fg, fontSize: 14, minHeight: 48 },
  cats: { flexDirection: 'row', flexWrap: 'wrap', gap: S.xs },
  cat: { flexDirection: 'row', alignItems: 'center', gap: 4, borderWidth: 1, borderColor: C.border, borderRadius: R.pill, paddingHorizontal: 10, minHeight: 34 },
  catOn: { backgroundColor: C.inverse, borderColor: C.inverse },
  catText: { color: C.fg, fontSize: 10.5, fontWeight: '800' },
  escrow: { color: C.info, fontSize: 11, lineHeight: 15 },
  submit: { backgroundColor: C.brand, borderRadius: R.sm, minHeight: 50, alignItems: 'center', justifyContent: 'center' },
  submitText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5 },
});
