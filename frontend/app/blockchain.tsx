/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// BLOCKCHAIN & TOKENS — the hidden crypto layer (Settings → Advanced). GA-T balance, full history,
// transfer to another account, and the marketplace (sell / spend) via the existing wallet screen.
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, TextInput, ActivityIndicator, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { C, S, R } from '@/src/theme';
import { tap, GoldButton } from '@/src/ui/glass';

const KIND_LABEL: Record<string, string> = {
  earn: 'Earned', spend: 'Spent', purchase_grant: 'Purchase grant', subscription: 'Plan allocation',
  transfer_out: 'Sent', transfer_in: 'Received', burn: 'Burned', reward: 'Reward',
};

export default function Blockchain() {
  const router = useRouter();
  const [w, setW] = useState<any>(null);
  const [ledger, setLedger] = useState<any[]>([]);
  const [to, setTo] = useState(''); const [amt, setAmt] = useState(''); const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false); const [msg, setMsg] = useState('');

  const load = useCallback(async () => {
    try {
      const [wallet, led]: any[] = await Promise.all([api('/token/wallet'), api('/token/ledger').catch(() => null)]);
      setW(wallet); setLedger((led?.txs || led?.ledger || wallet?.txs || []) as any[]);
    } catch (e) { console.log(e); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const send = async () => {
    const n = parseFloat(amt.replace(',', '.'));
    if (!to.trim() || !(n > 0)) return;
    tap('medium'); setBusy(true); setMsg('');
    try {
      await api('/store/transfer', { method: 'POST', body: JSON.stringify({ to_email: to.trim(), amount: n, note }) });
      tap('success'); setMsg(`✓ Sent ${n} GA-T to ${to.trim()}`); setTo(''); setAmt(''); setNote(''); await load();
    } catch (e: any) { setMsg(String(e.message || e).replace(/^\d+:\s*/, '')); tap('error'); }
    finally { setBusy(false); }
  };

  return (
    <SafeAreaView style={st.root} edges={['top']}>
      <View style={st.head}>
        <Pressable testID="bc-back" onPress={() => router.back()} hitSlop={10} style={st.back}><Ionicons name="chevron-back" size={22} color={C.brand} /></Pressable>
        <Text style={st.title}>BLOCKCHAIN & TOKENS</Text>
      </View>
      <ScrollView contentContainerStyle={st.body} refreshControl={<RefreshControl refreshing={false} onRefresh={load} tintColor={C.brand} />}>
        {!w && <ActivityIndicator color={C.brand} />}
        {w && (
          <>
            <View style={st.balance}>
              <Text style={st.balLabel}>GA-T BALANCE</Text>
              <Text testID="bc-balance" style={st.balNum}>{Number(w.balance || 0).toFixed(2)}</Text>
              <View style={st.stats}>
                <Text style={st.stat}>earned {Number(w.earned_total || 0).toFixed(0)}</Text>
                <Text style={st.stat}>spent {Number(w.spent_total || 0).toFixed(0)}</Text>
                <Text style={st.stat}>from plans {Number(w.subscription_total || 0).toFixed(0)}</Text>
              </View>
            </View>
            <View style={st.rowBtns}>
              <GoldButton testID="bc-market" title="SELL / SPEND · MARKETPLACE" icon="storefront" onPress={() => router.push('/token')} />
            </View>
            <Text style={st.section}>TRANSFER</Text>
            <View style={st.form}>
              <TextInput testID="bc-to" value={to} onChangeText={setTo} placeholder="Recipient e-mail" placeholderTextColor={C.info} autoCapitalize="none" keyboardType="email-address" style={st.input} />
              <View style={{ flexDirection: 'row', gap: S.sm }}>
                <TextInput testID="bc-amount" value={amt} onChangeText={setAmt} placeholder="Amount GA-T" placeholderTextColor={C.info} keyboardType="decimal-pad" style={[st.input, { flex: 1 }]} />
                <TextInput value={note} onChangeText={setNote} placeholder="Note" placeholderTextColor={C.info} style={[st.input, { flex: 1 }]} />
              </View>
              <GoldButton testID="bc-send" title="SEND GA-T" small onPress={send} loading={busy} disabled={!to.trim() || !amt} />
              {!!msg && <Text testID="bc-msg" style={[st.msg, { color: msg.startsWith('✓') ? C.accent : C.error }]}>{msg}</Text>}
            </View>
            <Text style={st.section}>TRANSACTION HISTORY · {ledger.length}</Text>
            {ledger.length === 0 && <Text style={st.hint}>No transactions yet.</Text>}
            {ledger.map((t: any, i: number) => (
              <View key={t.tx_id || i} testID="bc-tx" style={st.tx}>
                <Ionicons name={t.amount >= 0 ? 'arrow-down-circle' : 'arrow-up-circle'} size={20} color={t.amount >= 0 ? C.accent : C.warn} />
                <View style={{ flex: 1 }}>
                  <Text style={st.txTitle}>{KIND_LABEL[t.kind] || t.kind}{t.meta?.activity ? ` · ${t.meta.activity}` : t.meta?.addon ? ` · ${t.meta.addon}` : t.meta?.item ? ` · ${t.meta.item}` : ''}</Text>
                  <Text style={st.txSub}>{String(t.at || '').slice(0, 16).replace('T', ' ')}{t.hash ? ` · ${String(t.hash).slice(0, 10)}…` : ''}</Text>
                </View>
                <Text style={[st.txAmt, { color: t.amount >= 0 ? C.accent : C.warn }]}>{t.amount >= 0 ? '+' : ''}{Number(t.amount).toFixed(2)}</Text>
              </View>
            ))}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  head: { flexDirection: 'row', alignItems: 'center', gap: S.sm, paddingHorizontal: S.md, minHeight: 52 },
  back: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  title: { color: C.brand, fontWeight: '900', letterSpacing: 3, fontSize: 16 },
  body: { padding: S.lg, gap: S.md, paddingBottom: S.xxxl },
  balance: { borderWidth: 1, borderColor: 'rgba(212,175,55,0.5)', borderRadius: R.md, padding: S.lg, alignItems: 'center', gap: 4, backgroundColor: 'rgba(212,175,55,0.06)' },
  balLabel: { color: C.info, fontSize: 10, fontWeight: '900', letterSpacing: 2.5 },
  balNum: { color: C.brand, fontWeight: '900', fontSize: 40 },
  stats: { flexDirection: 'row', gap: S.md, flexWrap: 'wrap', justifyContent: 'center' },
  stat: { color: C.info, fontSize: 11 },
  rowBtns: { gap: S.sm },
  section: { color: C.brand, fontWeight: '900', letterSpacing: 2.5, fontSize: 11, marginTop: S.sm },
  form: { gap: S.sm, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, padding: S.md },
  input: { minHeight: 46, color: C.fg, paddingHorizontal: S.md, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, backgroundColor: C.surface2 },
  msg: { fontWeight: '800', fontSize: 12 },
  hint: { color: C.info, fontSize: 12 },
  tx: { flexDirection: 'row', alignItems: 'center', gap: S.md, padding: S.md, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, backgroundColor: C.surface2 },
  txTitle: { color: C.fg, fontWeight: '800', fontSize: 13 },
  txSub: { color: C.info, fontSize: 10.5, marginTop: 2 },
  txAmt: { fontWeight: '900', fontSize: 14 },
});
