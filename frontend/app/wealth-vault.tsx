/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// SOVEREIGN WEALTH VAULT — crypto + fiat accounts, Mosaic-anchored, Instant Card Payout
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { WheelField } from '@/src/ui/fields';
import { C, S } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

export default function WealthVault() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const [vault, setVault] = useState<any>(null);
  const [type, setType] = useState<'crypto' | 'bank'>('crypto');
  const [label, setLabel] = useState('');
  const [chain, setChain] = useState('BTC');
  const [address, setAddress] = useState('');
  const [secret, setSecret] = useState('');
  const [iban, setIban] = useState('');
  const [bankName, setBankName] = useState('');
  const [value, setValue] = useState('');
  const [payAmount, setPayAmount] = useState('');
  const [payCard, setPayCard] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    try { setVault(await api('/wealth/vault')); } catch (e) { console.log(e); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const addAsset = async () => {
    setBusy('add'); setErr(''); setMsg('');
    try {
      const body: any = { type, label, est_value_eur: parseFloat(value) || 0 };
      if (type === 'crypto') { body.chain = chain; body.address = address; body.secret = secret; }
      else { body.iban = iban; body.bank_name = bankName; }
      await api('/wealth/assets', { method: 'POST', body: JSON.stringify(body) });
      setLabel(''); setAddress(''); setSecret(''); setIban(''); setBankName(''); setValue('');
      await load();
      setMsg('Asset sealed in the vault (zero-knowledge).');
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const anchor = async () => {
    setBusy('anchor'); setErr(''); setMsg('');
    try {
      const r: any = await api('/wealth/anchor', { method: 'POST' });
      setMsg(`Anchored on Archangel Chain — block #${r.mosaic_block ?? '—'} · manifest ${r.manifest_sha256?.slice(0, 12)}…`);
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const payout = async () => {
    setBusy('payout'); setErr(''); setMsg('');
    try {
      const r: any = await api('/wealth/payout', { method: 'POST', body: JSON.stringify({ amount_eur: parseFloat(payAmount), card_last4: payCard }) });
      setMsg(`⚡ ${r.amount_eur} € sent to card ****${r.card_last4} — ${r.eta} (${r.rail}).`);
      setPayAmount(''); setPayCard('');
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const remove = async (id: string) => {
    setBusy(id);
    try { await api(`/wealth/assets/${id}`, { method: 'DELETE' }); await load(); }
    catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  return (
    <SafeAreaView testID="wealth-vault-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="wv-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={st.title}>{tt('wealth_vault.wealth_vault')}</Text>
        <View style={{ width: 26 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        <View style={st.totalCard}>
          <Text style={st.totalLbl}>{tt('wealth_vault.sovereign_wealth_estimate')}</Text>
          <Text testID="wv-total" style={st.totalVal}>{(vault?.total_est_value_eur ?? 0).toLocaleString('en-US')} €</Text>
          {vault?.anchor ? (
            <Text style={st.anchorInfo}>{tt('wealth_vault.proof_of_asset_stewardship_mosaic_bl')}{vault.anchor.mosaic_block ?? '—'} · {vault.anchor.manifest_sha256?.slice(0, 14)}…</Text>
          ) : (
            <Text style={st.anchorInfo}>{tt('wealth_vault.not_yet_anchored_on_archangel_chain')}</Text>
          )}
        </View>
        <Text style={st.policy}>{vault?.policy}</Text>

        <Text style={st.section}>{tt('wealth_vault.add_asset')}</Text>
        <View style={{ flexDirection: 'row', gap: S.sm }}>
          <Pressable testID="wv-type-crypto" onPress={() => setType('crypto')} style={[st.chip, type === 'crypto' && st.chipActive]}>
            <Text style={[st.chipText, type === 'crypto' && st.chipTextActive]}>{tt('wealth_vault.crypto')}</Text>
          </Pressable>
          <Pressable testID="wv-type-bank" onPress={() => setType('bank')} style={[st.chip, type === 'bank' && st.chipActive]}>
            <Text style={[st.chipText, type === 'bank' && st.chipTextActive]}>{tt('wealth_vault.bank_account')}</Text>
          </Pressable>
        </View>
        <TextInput testID="wv-label" value={label} onChangeText={setLabel} placeholder={tt('wealth_vault.label_e_g_btc_cold_wallet_my_bank')}
          placeholderTextColor="#777" style={st.input} />
        {type === 'crypto' ? (
          <>
            <View style={{ flexDirection: 'row', gap: S.sm }}>
              <TextInput testID="wv-chain" value={chain} onChangeText={setChain} placeholder={tt('wealth_vault.network_btc_eth')}
                placeholderTextColor="#777" style={[st.input, { width: 130 }]} />
              <TextInput testID="wv-address" value={address} onChangeText={setAddress} placeholder={tt('wealth_vault.wallet_address')}
                placeholderTextColor="#777" style={[st.input, { flex: 1 }]} />
            </View>
            <TextInput testID="wv-secret" value={secret} onChangeText={setSecret} secureTextEntry placeholder={tt('wealth_vault.seed_phrase_private_key_sealed_zero')}
              placeholderTextColor="#777" style={st.input} />
          </>
        ) : (
          <>
            <TextInput testID="wv-iban" value={iban} onChangeText={setIban} autoCapitalize="characters" placeholder={tt('wealth_vault.iban_sk31_1200')}
              placeholderTextColor="#777" style={st.input} />
            <TextInput testID="wv-bank" value={bankName} onChangeText={setBankName} placeholder={tt('wealth_vault.bank_name')}
              placeholderTextColor="#777" style={st.input} />
          </>
        )}
        <WheelField testID="wv-value" title={tt('wealth_vault.estimated_value')} min={0} max={500000} step={1000} unit="€" value={value} onChange={setValue} placeholder={tt('wealth_vault.estimated_value_in')} style={st.input} />
        <Pressable testID="wv-add" onPress={addAsset} disabled={busy === 'add' || !label.trim()} style={st.mainBtn}>
          {busy === 'add' ? <ActivityIndicator color={C.onInverse} /> : <Text style={st.mainBtnText}>{tt('wealth_vault.seal_into_vault')}</Text>}
        </Pressable>

        {!!msg && <Text testID="wv-msg" style={st.msg}>{msg}</Text>}
        {!!err && <Text testID="wv-err" style={st.err}>{err}</Text>}

        <Text style={st.section}>{tt('wealth_vault.assets')}{vault?.assets?.length ?? 0})</Text>
        {(vault?.assets ?? []).map((a: any) => (
          <View testID={`wv-asset-${a.asset_id}`} key={a.asset_id} style={st.card}>
            <View style={st.rowSpread}>
              <Text style={st.cardTitle}>{a.type === 'crypto' ? '₿' : '🏦'} {tx(a.label)}</Text>
              <Text style={st.cardVal}>{(a.est_value_eur ?? 0).toLocaleString('en-US')} €</Text>
            </View>
            {a.type === 'crypto' ? (
              <Text style={st.meta}>{a.chain} · {a.address_masked || '—'} · {a.has_sealed_secret ? tt('wealth_vault.seed_sealed') : tt('wealth_vault.no_seed')}</Text>
            ) : (
              <Text style={st.meta}>{a.bank_name} · {a.iban_masked}</Text>
            )}
            <Pressable testID={`wv-del-${a.asset_id}`} onPress={() => remove(a.asset_id)} hitSlop={8} style={st.delBtn}>
              <Text style={st.delText}>{tt('wealth_vault.remove')}</Text>
            </Pressable>
          </View>
        ))}

        <Pressable testID="wv-anchor" onPress={anchor} disabled={busy === 'anchor'} style={[st.mainBtn, { backgroundColor: '#8A2BE2', marginTop: S.lg }]}>
          {busy === 'anchor' ? <ActivityIndicator color="#FFF" /> : <Text style={[st.mainBtnText, { color: '#FFF' }]}>{tt('wealth_vault.anchor_hash_on_mosaic_chain')}</Text>}
        </Pressable>

        <Text style={st.section}>{tt('wealth_vault.instant_card_payout')}</Text>
        <Text style={st.policy}>{tt('wealth_vault.instant_card_payout_visa_direct_mast')}</Text>
        <View style={{ flexDirection: 'row', gap: S.sm }}>
          <WheelField testID="wv-pay-amount" title={tt('wealth_vault.amount')} min={10} max={5000} step={10} unit="€" value={payAmount} onChange={setPayAmount} placeholder={tt('wealth_vault.amount_kn5t')} style={[st.input, { flex: 1 }]} />
          <TextInput testID="wv-pay-card" value={payCard} onChangeText={setPayCard} keyboardType="numeric" maxLength={4} placeholder={tt('wealth_vault.card')}
            placeholderTextColor="#777" style={[st.input, { width: 110 }]} />
        </View>
        <Pressable testID="wv-payout" onPress={payout} disabled={busy === 'payout' || !payAmount || payCard.length !== 4} style={[st.mainBtn, { backgroundColor: '#1B4332' }]}>
          {busy === 'payout' ? <ActivityIndicator color="#FFF" /> : <Text style={[st.mainBtnText, { color: '#FFF' }]}>{tt('wealth_vault.send_instantly_to_card')}</Text>}
        </Pressable>

        {(vault?.payouts ?? []).length > 0 && (
          <>
            <Text style={st.section}>{tt('wealth_vault.payout_history')}</Text>
            {(vault?.payouts ?? []).map((p: any) => (
              <View key={p.payout_id} style={st.card}>
                <Text style={st.cardTitle}>⚡ {p.amount_eur} € → ****{p.card_last4}</Text>
                <Text style={st.meta}>{p.status.toUpperCase()} · {p.eta} · {p.rail}</Text>
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
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  totalCard: { borderWidth: 1.5, borderColor: C.brand, padding: S.lg, backgroundColor: C.surface2 },
  totalLbl: { color: C.info, fontSize: 10, fontWeight: '900', letterSpacing: 2 },
  totalVal: { color: C.brand, fontSize: 32, fontWeight: '900', marginTop: 4 },
  anchorInfo: { color: C.onS3, fontSize: 10, marginTop: S.sm, letterSpacing: 0.3 },
  policy: { color: C.onS3, fontSize: 11, lineHeight: 17, marginTop: S.md },
  section: { color: C.info, fontSize: 11, fontWeight: '900', letterSpacing: 2, marginTop: S.xl, marginBottom: S.sm },
  chip: { paddingHorizontal: S.md, paddingVertical: 10, borderWidth: 1.5, borderColor: C.borderStrong, minHeight: 44, justifyContent: 'center', flex: 1, alignItems: 'center' },
  chipActive: { backgroundColor: C.brand, borderColor: C.brand },
  chipText: { fontWeight: '800', color: C.fg, fontSize: 11, letterSpacing: 0.5 },
  chipTextActive: { color: C.onInverse },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 14, color: C.fg, backgroundColor: C.surface2, marginTop: S.sm },
  mainBtn: { backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center', minHeight: 52, marginTop: S.md },
  mainBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  msg: { color: C.brand, fontWeight: '800', fontSize: 12, marginTop: S.md, lineHeight: 18 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginTop: S.sm },
  card: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginTop: S.sm, backgroundColor: C.surface2 },
  rowSpread: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  cardTitle: { color: C.fg, fontSize: 14, fontWeight: '800' },
  cardVal: { color: C.brand, fontSize: 14, fontWeight: '900' },
  meta: { color: C.info, fontSize: 10, marginTop: 4, letterSpacing: 0.3 },
  delBtn: { marginTop: S.sm, minHeight: 32, justifyContent: 'center' },
  delText: { color: C.error, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
});
