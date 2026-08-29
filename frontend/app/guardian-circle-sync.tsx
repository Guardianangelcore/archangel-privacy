/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// GUARDIAN CIRCLE — local-first contacts picker.
// Reads the on-device address book (opt-in, contextual permission), lets the
// Guardian Angel pick a small ring of trusted people ("Guardian Circle") and
// stores the DID-hashed selection ONLY in device-local SecureStore. No cloud sync.
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, ActivityIndicator, Platform, Linking, TextInput } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as Contacts from 'expo-contacts';
import * as SecureStore from 'expo-secure-store';
import * as Crypto from 'expo-crypto';
import { C, S, R } from '@/src/theme';
import { tap } from '@/src/ui/glass';

const CIRCLE_KEY = 'gh_guardian_circle_v1';
const MAX_CIRCLE = 8;

type PickedContact = {
  did_hash: string;     // sha-256 of "name|phone" — the only identity we persist
  name: string;         // display name kept locally (never leaves device)
  phone: string;        // primary phone kept locally
  role?: string;        // optional label ("Anjel", "Rodina", ...)
  added_at: string;
};

async function hashId(name: string, phone: string): Promise<string> {
  const key = `${(name || '').trim().toLowerCase()}|${(phone || '').replace(/\s/g, '')}`;
  return await Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256, key);
}

async function loadCircle(): Promise<PickedContact[]> {
  try {
    if (Platform.OS === 'web') {
      const raw = localStorage.getItem(CIRCLE_KEY);
      return raw ? JSON.parse(raw) : [];
    }
    const raw = await SecureStore.getItemAsync(CIRCLE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}
async function saveCircle(list: PickedContact[]) {
  const json = JSON.stringify(list);
  if (Platform.OS === 'web') { try { localStorage.setItem(CIRCLE_KEY, json); } catch {} }
  else await SecureStore.setItemAsync(CIRCLE_KEY, json);
}

export default function GuardianCircleSync() {
  const router = useRouter();
  const [circle, setCircle] = useState<PickedContact[]>([]);
  const [phoneContacts, setPhoneContacts] = useState<Contacts.Contact[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState('');
  const [permStatus, setPermStatus] = useState<'undetermined' | 'granted' | 'denied' | 'blocked'>('undetermined');
  const [err, setErr] = useState('');

  const refresh = useCallback(async () => setCircle(await loadCircle()), []);
  useEffect(() => { refresh(); }, [refresh]);

  const askPermissionAndLoad = async () => {
    setErr(''); tap('medium');
    if (Platform.OS === 'web') { setErr('Kontakty sú dostupné len na mobilnom zariadení.'); return; }
    setBusy(true);
    try {
      const current = await Contacts.getPermissionsAsync();
      let status = current.status;
      let canAskAgain = current.canAskAgain;
      if (status !== 'granted') {
        if (!canAskAgain) { setPermStatus('blocked'); setBusy(false); return; }
        const r = await Contacts.requestPermissionsAsync();
        status = r.status; canAskAgain = r.canAskAgain;
        if (status !== 'granted') { setPermStatus(canAskAgain ? 'denied' : 'blocked'); setBusy(false); return; }
      }
      setPermStatus('granted');
      const { data } = await Contacts.getContactsAsync({
        fields: [Contacts.Fields.Name, Contacts.Fields.PhoneNumbers],
        sort: Contacts.SortTypes.FirstName,
        pageSize: 500,
      });
      // keep only contacts with at least one phone — Guardian Circle needs a way to call
      setPhoneContacts(data.filter(c => (c.phoneNumbers || []).length > 0));
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(false); }
  };

  const addToCircle = async (c: Contacts.Contact) => {
    if (circle.length >= MAX_CIRCLE) { setErr(`Kruh je plný (max ${MAX_CIRCLE}).`); return; }
    const phone = c.phoneNumbers?.[0]?.number || '';
    const name = c.name || 'Unknown';
    const did_hash = await hashId(name, phone);
    if (circle.some(p => p.did_hash === did_hash)) { setErr('Tento kontakt už v kruhu je.'); return; }
    const next = [...circle, { did_hash, name, phone, added_at: new Date().toISOString() }];
    setCircle(next); await saveCircle(next); tap('success');
  };
  const removeFromCircle = async (did_hash: string) => {
    const next = circle.filter(p => p.did_hash !== did_hash);
    setCircle(next); await saveCircle(next); tap();
  };
  const clearAll = async () => { setCircle([]); await saveCircle([]); tap(); };

  const filtered = useMemo(() => {
    if (!phoneContacts) return [];
    const s = q.trim().toLowerCase();
    if (!s) return phoneContacts.slice(0, 60);
    return phoneContacts.filter(c => (c.name || '').toLowerCase().includes(s)).slice(0, 60);
  }, [phoneContacts, q]);

  return (
    <SafeAreaView testID="gcs-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="gcs-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.fg} />
        </Pressable>
        <Text style={st.title}>GUARDIAN CIRCLE</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        <Text style={st.tag}>LOKÁLNY KRUH · MAX {MAX_CIRCLE} OSÔB · KONTAKTY NIKDY NEOPUSTIA ZARIADENIE</Text>

        {/* Current Circle */}
        <View style={st.card}>
          <View style={st.cardHead}>
            <Text style={st.cardTitle}>MÔJ KRUH</Text>
            <Text style={st.cardMeta}>{circle.length}/{MAX_CIRCLE}</Text>
          </View>
          {circle.length === 0 ? (
            <Text style={st.empty}>Kruh je zatiaľ prázdny. Pridajte dôveryhodné osoby zo svojich kontaktov.</Text>
          ) : circle.map(p => (
            <View key={p.did_hash} style={st.row}>
              <View style={st.avatar}><Text style={st.avatarText}>{(p.name || '?').charAt(0).toUpperCase()}</Text></View>
              <View style={{ flex: 1 }}>
                <Text style={st.rowName}>{p.name}</Text>
                <Text style={st.rowSub}>{p.phone}  ·  DID {p.did_hash.slice(0, 10)}…</Text>
              </View>
              <Pressable testID={`gcs-remove-${p.did_hash.slice(0, 8)}`} onPress={() => removeFromCircle(p.did_hash)} hitSlop={8}>
                <Ionicons name="close-circle" size={22} color={C.error} />
              </Pressable>
            </View>
          ))}
          {circle.length > 0 && (
            <Pressable testID="gcs-clear" onPress={clearAll} style={st.clearBtn}>
              <Text style={st.clearText}>VYPRÁZDNIŤ KRUH</Text>
            </Pressable>
          )}
        </View>

        {/* Picker */}
        <View style={st.card}>
          <Text style={st.cardTitle}>PRIDAŤ ZO ZARIADENIA</Text>
          {permStatus !== 'granted' && (
            <>
              <Text style={st.explain}>
                Guardian Angel potrebuje jednorazový prístup k vašim kontaktom, aby ste mohli vybrať dôveryhodných ľudí do Kruhu.
                {'\n'}Kontakty zostávajú lokálne v zašifrovanom úložisku vášho telefónu.
              </Text>
              <Pressable testID="gcs-perm" onPress={askPermissionAndLoad} style={st.primaryBtn} disabled={busy}>
                {busy ? <ActivityIndicator color={C.onInverse} /> : (
                  <>
                    <Ionicons name="people" size={18} color={C.onInverse} />
                    <Text style={st.primaryText}>POVOLIŤ · NAČÍTAŤ KONTAKTY</Text>
                  </>
                )}
              </Pressable>
              {permStatus === 'blocked' && (
                <Pressable testID="gcs-settings" onPress={() => Linking.openSettings()} style={st.warnBtn}>
                  <Text style={st.warnBtnText}>KONTAKTY SÚ ZABLOKOVANÉ — OTVORIŤ NASTAVENIA</Text>
                </Pressable>
              )}
              {permStatus === 'denied' && <Text style={st.info}>Prístup zamietnutý — môžete to skúsiť neskôr znovu.</Text>}
            </>
          )}
          {permStatus === 'granted' && phoneContacts && (
            <>
              <View style={st.search}>
                <Ionicons name="search" size={16} color={C.info} />
                <TextInput testID="gcs-search" value={q} onChangeText={setQ}
                  placeholder="Hľadať v kontaktoch…" placeholderTextColor={C.info}
                  style={st.searchInput} autoCapitalize="none" />
              </View>
              {filtered.length === 0 ? (
                <Text style={st.empty}>Žiadny kontakt sa nezhoduje.</Text>
              ) : filtered.map(c => {
                const phone = c.phoneNumbers?.[0]?.number || '';
                return (
                  <Pressable key={c.id} testID={`gcs-add-${c.id?.slice(0, 8)}`} onPress={() => addToCircle(c)} style={st.pickRow}>
                    <View style={st.avatarS}><Text style={st.avatarText}>{(c.name || '?').charAt(0).toUpperCase()}</Text></View>
                    <View style={{ flex: 1 }}>
                      <Text style={st.rowName}>{c.name || 'Bez mena'}</Text>
                      <Text style={st.rowSub}>{phone}</Text>
                    </View>
                    <Ionicons name="add-circle" size={22} color={C.brand} />
                  </Pressable>
                );
              })}
            </>
          )}
        </View>

        {!!err && <Text testID="gcs-err" style={st.err}>{err}</Text>}
        <Text style={st.footer}>Zápis je lokálny a šifrovaný (Keychain / Android Keystore). Guardian Angel nevidí obsah — iba anonymné DID hashy.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.brand, fontSize: 18, fontWeight: '900', letterSpacing: 3 },
  tag: { color: C.info, fontSize: 10, letterSpacing: 1.5, fontWeight: '800', textAlign: 'center' },
  card: { marginTop: S.md, borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.sm, padding: S.md, backgroundColor: C.surface2 },
  cardHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  cardTitle: { color: C.brand, fontSize: 12, letterSpacing: 2, fontWeight: '900' },
  cardMeta: { color: C.info, fontSize: 11, fontWeight: '800' },
  empty: { color: C.info, fontSize: 12, fontStyle: 'italic', marginTop: 6 },
  explain: { color: C.onS3, fontSize: 12.5, lineHeight: 19, marginTop: 6 },
  primaryBtn: { flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, minHeight: 50, borderRadius: R.pill, marginTop: S.md },
  primaryText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  warnBtn: { marginTop: S.sm, minHeight: 48, alignItems: 'center', justifyContent: 'center', borderRadius: R.sm, backgroundColor: C.warn },
  warnBtnText: { color: C.onWarn, fontWeight: '900', fontSize: 11, letterSpacing: 0.5 },
  row: { flexDirection: 'row', gap: 10, alignItems: 'center', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: 'rgba(212,175,55,0.10)' },
  pickRow: { flexDirection: 'row', gap: 10, alignItems: 'center', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: 'rgba(212,175,55,0.08)' },
  avatar: { width: 40, height: 40, borderRadius: 20, backgroundColor: 'rgba(212,175,55,0.15)', alignItems: 'center', justifyContent: 'center' },
  avatarS: { width: 34, height: 34, borderRadius: 17, backgroundColor: 'rgba(212,175,55,0.12)', alignItems: 'center', justifyContent: 'center' },
  avatarText: { color: C.brand, fontWeight: '900' },
  rowName: { color: C.fg, fontSize: 14, fontWeight: '700' },
  rowSub: { color: C.info, fontSize: 11, marginTop: 2 },
  clearBtn: { marginTop: S.sm, alignSelf: 'flex-end', paddingHorizontal: 10, paddingVertical: 6 },
  clearText: { color: C.error, fontSize: 10.5, fontWeight: '900', letterSpacing: 1 },
  search: { flexDirection: 'row', alignItems: 'center', gap: 6, borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.pill, paddingHorizontal: 10, marginVertical: S.sm },
  searchInput: { flex: 1, color: C.fg, paddingVertical: 8, fontSize: 13 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginTop: S.md, textAlign: 'center' },
  info: { color: C.info, fontSize: 12, marginTop: 6 },
  footer: { color: C.info, fontSize: 10, lineHeight: 15, marginTop: S.lg, textAlign: 'center' },
});
