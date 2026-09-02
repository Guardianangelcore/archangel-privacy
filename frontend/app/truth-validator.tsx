/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// Truth-Validator — peer-consensus verification of community claims (ZK-hash anchored)
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, TextInput, FlatList, RefreshControl, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import Art50 from '@/src/Art50';
import { C, S } from '@/src/theme';
import { Lang } from '@/src/i18n';
import { useI18n } from '@/src/i18n-context';

const BADGE: Record<string, { text: string; bg: string; fg: string }> = {
  verified: { text: 'COMMUNITY VERIFIED', bg: '#1B4332', fg: '#FFFFFF' },
  disputed: { text: 'DISPUTED', bg: '#C25450', fg: '#FFFFFF' },
  pending: { text: 'AWAITING CONSENSUS', bg: '#2C2C2E', fg: '#D1D1D6' },
};

export default function TruthValidator() {
  const { t: tt, tx } = useI18n();
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'en';
  const router = useRouter();
  const [claims, setClaims] = useState<any[]>([]);
  const [cats, setCats] = useState<Record<string, string>>({});
  const [text, setText] = useState('');
  const [cat, setCat] = useState('shortage');
  const [city, setCity] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res: any = await api('/truth/claims');
      setClaims(res.claims || []); setCats(res.categories || {});
    } catch (e: any) { setErr(String(e.message || e)); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    setBusy('submit'); setErr('');
    try {
      await api('/truth/claims', { method: 'POST', body: JSON.stringify({ text, category: cat, city }) });
      setText(''); setCity(''); await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };
  const vote = async (id: string, v: string) => {
    setBusy(`${v}-${id}`); setErr('');
    try {
      const fresh: any = await api(`/truth/claims/${id}/vote`, { method: 'POST', body: JSON.stringify({ vote: v }) });
      setClaims(prev => prev.map(c => c.claim_id === id ? { ...fresh, my_vote: v } : c));
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  return (
    <SafeAreaView testID="truth-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="tv-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={st.title}>{tt('truth_validator.truth_validator')}</Text>
        <View style={{ width: 26 }} />
      </View>

      <FlatList
        data={claims}
        keyExtractor={c => c.claim_id}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.fg} />}
        contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}
        ListHeaderComponent={
          <View>
            <Text style={st.intro}>{tt('truth_validator.peer_consensus_against_crisis_disinf')}</Text>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: S.sm, marginTop: S.md }}>
              {Object.entries(cats).map(([k, v]) => (
                <Pressable testID={`tv-cat-${k}`} key={k} onPress={() => setCat(k)} style={[st.chip, cat === k && st.chipActive]}>
                  <Text style={[st.chipText, cat === k && st.chipTextActive]}>{v.toUpperCase()}</Text>
                </Pressable>
              ))}
            </View>
            <TextInput testID="tv-text" value={text} onChangeText={setText} multiline
              placeholder={tt('truth_validator.e_g_pharmacy_at_main_st_12_has_paral')}
              placeholderTextColor="#777" style={[st.input, { minHeight: 70, marginTop: S.sm }]} />
            <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.sm }}>
              <TextInput testID="tv-city" value={city} onChangeText={setCity} placeholder={tt('truth_validator.city')}
                placeholderTextColor="#777" style={[st.input, { flex: 1 }]} />
              <Pressable testID="tv-submit" onPress={submit} disabled={busy === 'submit' || text.trim().length < 10} style={st.submitBtn}>
                {busy === 'submit' ? <ActivityIndicator color={C.onInverse} size="small" /> : <Text style={st.submitText}>{tt('truth_validator.send')}</Text>}
              </Pressable>
            </View>
            {!!err && <Text testID="tv-err" style={st.err}>{err}</Text>}
          </View>
        }
        ListEmptyComponent={!loading ? <Text style={st.empty}>{tt('truth_validator.no_claims_yet_be_the_first')}</Text> : null}
        renderItem={({ item }) => {
          const b = BADGE[item.status] || BADGE.pending;
          const mine = item.user_id === user?.user_id;
          return (
            <View testID={`tv-claim-${item.claim_id}`} style={st.card}>
              <View style={st.rowSpread}>
                <View style={[st.badge, { backgroundColor: b.bg }]}><Text style={[st.badgeText, { color: b.fg }]}>{tx(b.text)}</Text></View>
                <Text style={st.meta}>{(cats[item.category] || item.category).toUpperCase()}</Text>
              </View>
              <Text style={st.claimText}>{tx(item.text)}</Text>
              <Text style={st.meta}>{item.author_name}{item.city ? ` · ${item.city}` : ''} · ✓ {item.verify_votes} · ✗ {item.dispute_votes} · #{item.claim_sha256?.slice(0, 10)}</Text>
              {!mine && !item.my_vote && (
                <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.md }}>
                  <Pressable testID={`tv-verify-${item.claim_id}`} onPress={() => vote(item.claim_id, 'verify')} style={[st.voteBtn, { backgroundColor: C.brand }]}>
                    <Text style={st.voteText}>{tt('truth_validator.i_verify')}</Text>
                  </Pressable>
                  <Pressable testID={`tv-dispute-${item.claim_id}`} onPress={() => vote(item.claim_id, 'dispute')} style={[st.voteBtn, { backgroundColor: C.error }]}>
                    <Text style={st.voteText}>{tt('truth_validator.i_dispute')}</Text>
                  </Pressable>
                </View>
              )}
              {!!item.my_vote && <Text style={st.voted}>{tt('truth_validator.your_vote')} {item.my_vote === 'verify' ? tt('truth_validator.verified') : tt('truth_validator.disputed')}</Text>}
            </View>
          );
        }}
        ListFooterComponent={<Art50 lang={lang} />}
      />
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  intro: { color: C.onS3, fontSize: 12, lineHeight: 18 },
  chip: { paddingHorizontal: S.md, paddingVertical: 8, borderWidth: 1.5, borderColor: C.borderStrong, minHeight: 36, justifyContent: 'center' },
  chipActive: { backgroundColor: C.brand, borderColor: C.brand },
  chipText: { fontWeight: '800', color: C.fg, fontSize: 10, letterSpacing: 0.5 },
  chipTextActive: { color: C.onInverse },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 14, color: C.fg, backgroundColor: C.surface2 },
  submitBtn: { backgroundColor: C.brand, paddingHorizontal: S.lg, justifyContent: 'center', minHeight: 48 },
  submitText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginTop: S.sm },
  empty: { textAlign: 'center', color: C.info, marginTop: 40, letterSpacing: 2, fontWeight: '800', fontSize: 11 },
  card: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginTop: S.md, backgroundColor: C.surface2 },
  rowSpread: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  badge: { paddingHorizontal: 8, paddingVertical: 4 },
  badgeText: { fontSize: 9, fontWeight: '900', letterSpacing: 1 },
  claimText: { color: C.fg, fontSize: 14, lineHeight: 20, marginTop: S.sm },
  meta: { color: C.info, fontSize: 10, marginTop: 6, letterSpacing: 0.5 },
  voteBtn: { flex: 1, alignItems: 'center', paddingVertical: S.md, minHeight: 44, justifyContent: 'center' },
  voteText: { color: C.onInverse, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  voted: { color: C.brand, fontWeight: '900', fontSize: 10, letterSpacing: 1, marginTop: S.sm },
});
