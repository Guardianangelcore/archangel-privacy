/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// INNER CIRCLE — founder-managed whitelist: permanent Archangel status for the family
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { C, S } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

export default function InnerCircle() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const [members, setMembers] = useState<any[]>([]);
  const [isFounder, setIsFounder] = useState<boolean | null>(null);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [relationship, setRelationship] = useState('rodina');
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    try {
      const r: any = await api('/inner-circle');
      setMembers(r.members || []);
      setIsFounder(true);
    } catch (e: any) {
      if (String(e.message || e).includes('founder_only')) setIsFounder(false);
      else setErr(String(e.message || e));
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const add = async () => {
    setBusy('add'); setErr('');
    try {
      await api('/inner-circle', { method: 'POST', body: JSON.stringify({ email, name, relationship }) });
      setEmail(''); setName('');
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const remove = async (id: string) => {
    setBusy(id);
    try { await api(`/inner-circle/${id}`, { method: 'DELETE' }); await load(); }
    catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  return (
    <SafeAreaView testID="inner-circle-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="ic-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={st.title}>{tt('inner_circle.inner_circle')}</Text>
        <View style={{ width: 26 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        <View style={st.heroIcon}><Ionicons name="diamond" size={28} color="#8A2BE2" /></View>
        <Text style={st.h1}>{tt('inner_circle.founder_s_inner_circle')}</Text>
        <Text style={st.sub}>
          {tt('inner_circle.inner_circle_members_receive_lifetim')}
        </Text>

        {isFounder === false && (
          <View style={st.lockedCard}>
            <Ionicons name="lock-closed" size={22} color={C.info} />
            <Text style={st.lockedText}>{tt('inner_circle.the_inner_circle_is_managed_solely_b')}</Text>
          </View>
        )}

        {isFounder && (
          <>
            <Text style={st.section}>{tt('inner_circle.add_member')}</Text>
            <TextInput testID="ic-email" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address"
              placeholder={tt('inner_circle.family_member_e_mail')} placeholderTextColor="#777" style={st.input} />
            <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.sm }}>
              <TextInput testID="ic-name" value={name} onChangeText={setName} placeholder={tt('inner_circle.meno')}
                placeholderTextColor="#777" style={[st.input, { flex: 1, marginTop: 0 }]} />
              <TextInput testID="ic-relationship" value={relationship} onChangeText={setRelationship} placeholder={tt('inner_circle.relationship')}
                placeholderTextColor="#777" style={[st.input, { width: 110, marginTop: 0 }]} />
            </View>
            <Pressable testID="ic-add" onPress={add} disabled={busy === 'add' || !email.includes('@')} style={st.mainBtn}>
              {busy === 'add' ? <ActivityIndicator color="#FFF" /> : <Text style={st.mainBtnText}>{tt('inner_circle.grant_lifetime_archangel')}</Text>}
            </Pressable>
            {!!err && <Text testID="ic-err" style={st.err}>{err}</Text>}

            <Text style={st.section}>{tt('inner_circle.members')}{members.length})</Text>
            {members.length === 0 && <Text style={st.empty}>{tt('inner_circle.the_circle_is_empty_so_far')}</Text>}
            {members.map(m => (
              <View testID={`ic-member-${m.member_id}`} key={m.member_id} style={st.card}>
                <View style={st.rowSpread}>
                  <Text style={st.cardTitle}>{m.name || m.email}</Text>
                  <View style={st.badge}><Text style={st.badgeText}>{tt('inner_circle.archangel')}</Text></View>
                </View>
                <Text style={st.meta}>{m.email} · {m.relationship}{m.linked_did ? tt('inner_circle.did_linked') : ' ' + tt('inner_circle.awaiting_first_login')}</Text>
                <Pressable testID={`ic-del-${m.member_id}`} onPress={() => remove(m.member_id)} disabled={busy === m.member_id} style={st.delBtn}>
                  <Text style={st.delText}>{tt('inner_circle.remove_from_circle')}</Text>
                </Pressable>
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
  heroIcon: { width: 56, height: 56, borderWidth: 1.5, borderColor: '#8A2BE2', alignItems: 'center', justifyContent: 'center', marginBottom: S.md },
  h1: { color: C.fg, fontSize: 20, fontWeight: '900', letterSpacing: 0.5 },
  sub: { color: C.onS3, fontSize: 12, lineHeight: 18, marginTop: S.sm },
  section: { color: C.info, fontSize: 11, fontWeight: '900', letterSpacing: 2, marginTop: S.xl, marginBottom: S.sm },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 14, color: C.fg, backgroundColor: C.surface2, marginTop: S.sm },
  mainBtn: { backgroundColor: '#8A2BE2', alignItems: 'center', justifyContent: 'center', minHeight: 52, marginTop: S.md },
  mainBtnText: { color: '#FFFFFF', fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginTop: S.sm },
  empty: { textAlign: 'center', color: C.info, marginTop: S.lg, letterSpacing: 2, fontWeight: '800', fontSize: 11 },
  card: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginTop: S.sm, backgroundColor: C.surface2 },
  rowSpread: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  cardTitle: { color: C.fg, fontSize: 14, fontWeight: '800', flex: 1 },
  badge: { backgroundColor: '#8A2BE2', paddingHorizontal: 8, paddingVertical: 4 },
  badgeText: { fontSize: 9, fontWeight: '900', letterSpacing: 1, color: '#FFFFFF' },
  meta: { color: C.info, fontSize: 10, marginTop: 4, letterSpacing: 0.3 },
  delBtn: { marginTop: S.sm, minHeight: 32, justifyContent: 'center' },
  delText: { color: C.error, fontWeight: '900', fontSize: 10, letterSpacing: 1 },
  lockedCard: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.lg, marginTop: S.xl, backgroundColor: C.surface2, alignItems: 'center', gap: S.sm },
  lockedText: { color: C.onS3, fontSize: 12, lineHeight: 18, textAlign: 'center' },
});
