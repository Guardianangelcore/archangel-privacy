/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// Angel Gig Network — hyper-local help gigs, GA-T (Proof-of-Help) + cash rewards
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, FlatList, TextInput, Modal, ScrollView, RefreshControl, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { WheelField } from '@/src/ui/fields';
import Art50 from '@/src/Art50';
import { C, S } from '@/src/theme';
import { Lang } from '@/src/i18n';

const KIND_ICON: Record<string, any> = {
  transport: 'car-outline', grocery: 'cart-outline', pharmacy: 'medkit-outline',
  company: 'people-outline', tech: 'phone-portrait-outline',
};

export default function Gigs() {
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const router = useRouter();
  const [tab, setTab] = useState<'open' | 'mine'>('open');
  const [open, setOpen] = useState<any[]>([]);
  const [mine, setMine] = useState<any[]>([]);
  const [kinds, setKinds] = useState<Record<string, string>>({});
  const [modal, setModal] = useState(false);
  const [f, setF] = useState({ kind: 'transport', title: '', note: '', city: '', reward_gat: '10', reward_eur: '0' });
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res: any = await api('/gigs/nearby');
      setOpen(res.open || []); setMine(res.mine || []); setKinds(res.kinds || {});
    } catch (e: any) { setErr(String(e.message || e)); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key); setErr(''); setMsg('');
    try { await fn(); await load(); } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const create = () => run('create', async () => {
    await api('/gigs', { method: 'POST', body: JSON.stringify({ ...f, reward_gat: parseFloat(f.reward_gat) || 10, reward_eur: parseFloat(f.reward_eur) || 0 }) });
    setModal(false); setF({ kind: 'transport', title: '', note: '', city: '', reward_gat: '10', reward_eur: '0' });
    setMsg('Požiadavka odoslaná susedom v okolí (push).');
  });
  const accept = (id: string) => run(`acc-${id}`, async () => {
    await api(`/gigs/${id}/accept`, { method: 'POST' });
    setMsg('Gig prijatý — zadávateľ dostal push, že ste na ceste.');
    setTab('mine');
  });
  const complete = (id: string) => run(`cmp-${id}`, async () => {
    const res: any = await api(`/gigs/${id}/complete`, { method: 'POST' });
    setMsg(res.gat_reward ? `Hotovo — pomocník získal +${res.gat_reward} GA-T (Proof-of-Help).` : 'Hotovo — GA-T denný limit, odmena zajtra.');
  });

  const data = tab === 'open' ? open : mine;

  return (
    <SafeAreaView testID="gigs-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="gg-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={st.title}>ANGEL GIG NETWORK</Text>
        <Pressable testID="gg-token" onPress={() => router.push('/token')} hitSlop={12}>
          <Ionicons name="diamond-outline" size={22} color={C.onInverse} />
        </Pressable>
      </View>

      <View style={st.tabRow}>
        {(['open', 'mine'] as const).map(k => (
          <Pressable testID={`gg-tab-${k}`} key={k} onPress={() => setTab(k)} style={[st.tabBtn, tab === k && st.tabBtnActive]}>
            <Text style={[st.tabText, tab === k && st.tabTextActive]}>{k === 'open' ? 'V OKOLÍ' : 'MOJE GIGY'}</Text>
          </Pressable>
        ))}
      </View>

      <FlatList
        data={data}
        keyExtractor={g => g.gig_id}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.fg} />}
        contentContainerStyle={{ padding: S.lg, paddingBottom: 140 }}
        ListHeaderComponent={
          <View>
            <Text style={st.intro}>Susedia pomáhajú seniorom — odvoz, nákup, lieky, spoločnosť. Odmena: GA-T (Proof-of-Help) alebo hotovosť napriamo, bez provízie.</Text>
            {!!msg && <Text testID="gg-msg" style={st.msg}>{msg}</Text>}
            {!!err && <Text testID="gg-err" style={st.err}>{err}</Text>}
          </View>
        }
        ListEmptyComponent={!loading ? <Text style={st.empty}>{tab === 'open' ? 'ŽIADNE OTVORENÉ POŽIADAVKY V OKOLÍ' : 'ZATIAĽ ŽIADNE VLASTNÉ GIGY'}</Text> : null}
        renderItem={({ item }) => {
          const isMineReq = item.user_id === user?.user_id;
          return (
            <View testID={`gg-${item.gig_id}`} style={st.card}>
              <View style={st.rowSpread}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  <Ionicons name={KIND_ICON[item.kind] || 'hand-left-outline'} size={18} color={C.brand} />
                  <Text style={st.kind}>{(kinds[item.kind] || item.kind).toUpperCase()}</Text>
                </View>
                <Text style={[st.status, item.status === 'done' && { color: C.brand }, item.status === 'taken' && { color: C.warn }]}>{item.status.toUpperCase()}</Text>
              </View>
              <Text style={st.gigTitle}>{item.title}</Text>
              <Text style={st.meta}>{item.requester_name}{item.city ? ` · ${item.city}` : ''}{item.note ? ` · ${item.note}` : ''}</Text>
              <Text style={st.reward}>ODMENA: {item.reward_gat} GA-T{item.reward_eur ? ` + ${item.reward_eur} €` : ''}</Text>
              {item.status === 'open' && !isMineReq && (
                <Pressable testID={`gg-accept-${item.gig_id}`} onPress={() => accept(item.gig_id)} style={st.acceptBtn}>
                  {busy === `acc-${item.gig_id}` ? <ActivityIndicator color={C.onInverse} size="small" /> : <Text style={st.acceptText}>PRIJÍMAM — IDEM POMÔCŤ 😇</Text>}
                </Pressable>
              )}
              {item.status === 'taken' && isMineReq && (
                <Pressable testID={`gg-complete-${item.gig_id}`} onPress={() => complete(item.gig_id)} style={[st.acceptBtn, { backgroundColor: C.brand }]}>
                  {busy === `cmp-${item.gig_id}` ? <ActivityIndicator color={C.onInverse} size="small" /> : <Text style={st.acceptText}>POTVRDIŤ DOKONČENIE + ODMENU</Text>}
                </Pressable>
              )}
              {item.status === 'taken' && !isMineReq && item.taker_id === user?.user_id && (
                <Text style={st.taken}>POMÁHATE VY — po dokončení potvrdí zadávateľ odmenu</Text>
              )}
            </View>
          );
        }}
        ListFooterComponent={<Art50 lang={lang} />}
      />

      <Pressable testID="gg-add" onPress={() => setModal(true)} style={st.fab}>
        <Ionicons name="add" size={22} color={C.onInverse} />
        <Text style={st.fabText}>POŽIADAŤ O POMOC</Text>
      </Pressable>

      <Modal visible={modal} animationType="slide" transparent>
        <View style={st.modalRoot}>
          <View style={st.modalCard}>
            <View style={st.modalHead}>
              <Text style={st.modalTitle}>NOVÁ POŽIADAVKA</Text>
              <Pressable testID="gg-modal-close" onPress={() => setModal(false)}><Ionicons name="close" size={22} color={C.onInverse} /></Pressable>
            </View>
            <ScrollView contentContainerStyle={{ padding: S.lg, gap: S.md }} style={{ maxHeight: 460 }}>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: S.sm }}>
                {Object.entries(kinds).map(([k, v]) => (
                  <Pressable testID={`gg-kind-${k}`} key={k} onPress={() => setF({ ...f, kind: k })} style={[st.chip, f.kind === k && st.chipActive]}>
                    <Text style={[st.chipText, f.kind === k && st.chipTextActive]}>{v.toUpperCase()}</Text>
                  </Pressable>
                ))}
              </View>
              <TextInput testID="gg-title" placeholder="Napr.: Odvoz na kardiológiu v utorok 9:00" value={f.title} onChangeText={v => setF({ ...f, title: v })} style={st.input} placeholderTextColor="#777" />
              <TextInput testID="gg-city" placeholder="Mesto" value={f.city} onChangeText={v => setF({ ...f, city: v })} style={st.input} placeholderTextColor="#777" />
              <TextInput testID="gg-note" placeholder="Poznámka (nepovinné)" value={f.note} onChangeText={v => setF({ ...f, note: v })} style={st.input} placeholderTextColor="#777" />
              <View style={{ flexDirection: 'row', gap: S.sm }}>
                <View style={{ flex: 1 }}>
                  <Text style={st.lbl}>ODMENA GA-T (max 50)</Text>
                  <WheelField testID="gg-gat" title="ODMENA GA-T" min={0} max={500} step={5} unit="GA-T" value={f.reward_gat} onChange={v => setF({ ...f, reward_gat: v })} placeholder="0" style={st.input} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={st.lbl}>HOTOVOSŤ € (nepovinné)</Text>
                  <WheelField testID="gg-eur" title="ODMENA €" min={0} max={500} step={5} unit="€" value={f.reward_eur} onChange={v => setF({ ...f, reward_eur: v })} placeholder="0" style={st.input} />
                </View>
              </View>
            </ScrollView>
            <Pressable testID="gg-save" onPress={create} disabled={busy === 'create' || !f.title.trim()} style={st.saveBtn}>
              {busy === 'create' ? <ActivityIndicator color={C.onInverse} /> : <Text style={st.saveText}>ODOSLAŤ SUSEDOM</Text>}
            </Pressable>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 17, fontWeight: '900', letterSpacing: 2 },
  tabRow: { flexDirection: 'row', borderBottomWidth: 2, borderColor: C.borderStrong },
  tabBtn: { flex: 1, paddingVertical: S.md, alignItems: 'center', minHeight: 44, justifyContent: 'center' },
  tabBtnActive: { backgroundColor: C.brand },
  tabText: { fontWeight: '900', letterSpacing: 1, fontSize: 12, color: C.fg },
  tabTextActive: { color: C.onInverse },
  intro: { color: C.onS3, fontSize: 12, lineHeight: 18 },
  msg: { color: C.brand, fontWeight: '800', fontSize: 12, marginTop: S.sm, lineHeight: 17 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginTop: S.sm },
  empty: { textAlign: 'center', color: C.info, marginTop: 40, letterSpacing: 2, fontWeight: '800', fontSize: 11 },
  card: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginTop: S.md, backgroundColor: C.surface2 },
  rowSpread: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  kind: { color: C.brand, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  status: { color: C.info, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  gigTitle: { color: C.fg, fontWeight: '800', fontSize: 15, marginTop: 6, lineHeight: 20 },
  meta: { color: C.info, fontSize: 11, marginTop: 4 },
  reward: { color: '#B8860B', fontWeight: '900', fontSize: 12, letterSpacing: 0.5, marginTop: 6 },
  acceptBtn: { marginTop: S.md, backgroundColor: C.inverse, alignItems: 'center', paddingVertical: S.md, minHeight: 48, justifyContent: 'center' },
  acceptText: { color: C.onInverse, fontWeight: '900', fontSize: 12, letterSpacing: 1 },
  taken: { marginTop: S.sm, color: C.warn, fontWeight: '800', fontSize: 10, letterSpacing: 0.5 },
  fab: { position: 'absolute', bottom: 24, right: S.lg, flexDirection: 'row', gap: 8, alignItems: 'center', backgroundColor: C.brand, paddingHorizontal: S.lg, paddingVertical: S.md, minHeight: 52 },
  fabText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  modalRoot: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  modalCard: { backgroundColor: C.bg, borderTopWidth: 2, borderColor: C.borderStrong },
  modalHead: { flexDirection: 'row', justifyContent: 'space-between', padding: S.lg, backgroundColor: C.inverse },
  modalTitle: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 14 },
  chip: { paddingHorizontal: S.md, paddingVertical: 8, borderWidth: 1.5, borderColor: C.borderStrong, minHeight: 36, justifyContent: 'center' },
  chipActive: { backgroundColor: C.brand, borderColor: C.brand },
  chipText: { fontWeight: '800', color: C.fg, fontSize: 10, letterSpacing: 0.5 },
  chipTextActive: { color: C.onInverse },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 14, color: C.fg, backgroundColor: C.surface2 },
  lbl: { fontSize: 9, letterSpacing: 1.5, color: C.info, fontWeight: '800', marginBottom: 4 },
  saveBtn: { backgroundColor: C.brand, paddingVertical: S.lg, alignItems: 'center' },
  saveText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2 },
});
