/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// Native Contact Picker (expo-contacts) in a glass bottom sheet — with full permission contract
import React, { useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, TextInput, FlatList, Platform, Linking, ActivityIndicator } from 'react-native';
import * as Contacts from 'expo-contacts/legacy';
import Ionicons from '@react-native-vector-icons/ionicons';
import { C, S, R } from '@/src/theme';
import { Sheet } from '@/src/ui/sheets';
import { tap, GoldButton } from '@/src/ui/glass';

export type PickedContact = { name: string; phone?: string; email?: string };

export function ContactSheet({ visible, onClose, onPick }: {
  visible: boolean; onClose: () => void; onPick: (c: PickedContact) => void;
}) {
  const [perm, setPerm] = useState<'unknown' | 'granted' | 'ask' | 'blocked'>('unknown');
  const [contacts, setContacts] = useState<Contacts.ExistingContact[]>([]);
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(false);
  const [manualName, setManualName] = useState('');
  const [manualPhone, setManualPhone] = useState('');
  const web = Platform.OS === 'web';

  useEffect(() => {
    if (!visible || web) return;
    (async () => {
      const p = await Contacts.getPermissionsAsync();
      if (p.granted) { setPerm('granted'); loadContacts(); }
      else if (p.canAskAgain) setPerm('ask');
      else setPerm('blocked');
    })();
  }, [visible, web]);

  const loadContacts = async () => {
    setLoading(true);
    try {
      const { data } = await Contacts.getContactsAsync({ fields: [Contacts.Fields.PhoneNumbers, Contacts.Fields.Emails], sort: Contacts.SortTypes.FirstName });
      setContacts(data.filter(c => c.name && (c.phoneNumbers?.length || c.emails?.length)));
    } catch (e) { console.log('contacts err', e); }
    setLoading(false);
  };

  const request = async () => {
    tap();
    const p = await Contacts.requestPermissionsAsync();
    if (p.granted) { setPerm('granted'); loadContacts(); }
    else setPerm(p.canAskAgain ? 'ask' : 'blocked');
  };

  const filtered = q.trim()
    ? contacts.filter(c => (c.name || '').toLowerCase().includes(q.trim().toLowerCase()))
    : contacts;

  const manual = (
    <View style={{ paddingBottom: S.xl }}>
      <Text style={st.note}>
        {web ? 'The address book is not available on web — enter the contact manually. In the mobile app you pick a contact with one tap.' : 'Enter the contact manually.'}
      </Text>
      <TextInput testID="cs-manual-name" value={manualName} onChangeText={setManualName} placeholder="Meno" placeholderTextColor="#777" style={st.input} />
      <TextInput testID="cs-manual-phone" value={manualPhone} onChangeText={setManualPhone} placeholder="Phone or e-mail" placeholderTextColor="#777" style={st.input} keyboardType="email-address" autoCapitalize="none" />
      <GoldButton testID="cs-manual-pick" title="USE CONTACT" icon="checkmark"
        disabled={!manualName.trim() || !manualPhone.trim()}
        onPress={() => { const v = manualPhone.trim(); onPick({ name: manualName.trim(), phone: v.includes('@') ? undefined : v, email: v.includes('@') ? v : undefined }); onClose(); }}
        style={{ marginTop: S.md }} />
    </View>
  );

  return (
    <Sheet visible={visible} onClose={onClose} title="PICK FROM YOUR CONTACTS" testID="contact-sheet">
      {web ? manual : perm === 'ask' ? (
        <View style={{ paddingBottom: S.xl }}>
          <View style={st.permIcon}><Ionicons name="people" size={30} color={C.brand} /></View>
          <Text style={st.note}>Guardian needs access to your contacts so you can add a guardian with one tap — no retyping numbers. Contacts never leave your phone without your consent.</Text>
          <GoldButton testID="cs-perm-request" title="ALLOW CONTACT ACCESS" icon="people" onPress={request} style={{ marginTop: S.md }} />
        </View>
      ) : perm === 'blocked' ? (
        <View style={{ paddingBottom: S.xl }}>
          <Text style={st.note}>Contact access is blocked. Allow it in your phone settings — or enter the contact manually below.</Text>
          <GoldButton testID="cs-open-settings" title="OPEN SETTINGS" icon="settings-outline" onPress={() => Linking.openSettings()} style={{ marginVertical: S.md }} />
          {manual}
        </View>
      ) : (
        <View>
          <TextInput testID="cs-search" value={q} onChangeText={setQ} placeholder="Search contacts…" placeholderTextColor="#777" style={st.input} />
          {loading ? <ActivityIndicator color={C.brand} style={{ marginVertical: S.xl }} /> : (
            <FlatList
              data={filtered.slice(0, 100)}
              keyExtractor={(c, i) => c.id || String(i)}
              style={{ maxHeight: 360 }}
              renderItem={({ item }) => {
                const phone = item.phoneNumbers?.[0]?.number || undefined;
                const email = item.emails?.[0]?.email || undefined;
                return (
                  <Pressable testID={`cs-contact-${item.id}`}
                    onPress={() => { tap('light'); onPick({ name: item.name || '', phone, email }); onClose(); }}
                    style={({ pressed }) => [st.row, pressed && { opacity: 0.8 }]}>
                    <View style={st.avatar}><Text style={st.avatarText}>{(item.name || '?').slice(0, 1).toUpperCase()}</Text></View>
                    <View style={{ flex: 1 }}>
                      <Text style={st.name}>{item.name}</Text>
                      <Text style={st.sub}>{phone || email}</Text>
                    </View>
                    <Ionicons name="add-circle" size={24} color={C.brand} />
                  </Pressable>
                );
              }}
              ListEmptyComponent={<Text style={st.note}>No contacts with a number or e-mail.</Text>}
            />
          )}
        </View>
      )}
    </Sheet>
  );
}

const st = StyleSheet.create({
  note: { color: C.onS3, fontSize: 12.5, lineHeight: 19, textAlign: 'center', marginTop: S.sm },
  permIcon: { alignSelf: 'center', width: 64, height: 64, borderRadius: R.pill, backgroundColor: 'rgba(212,175,55,0.12)', alignItems: 'center', justifyContent: 'center', marginBottom: S.sm },
  input: { borderWidth: 1.5, borderColor: C.border, borderRadius: R.sm, padding: S.md, fontSize: 15, color: C.fg, backgroundColor: 'rgba(255,255,255,0.04)', marginTop: S.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: S.md, minHeight: 58, paddingHorizontal: S.xs },
  avatar: { width: 42, height: 42, borderRadius: R.pill, backgroundColor: 'rgba(212,175,55,0.14)', alignItems: 'center', justifyContent: 'center' },
  avatarText: { color: C.brand, fontWeight: '900', fontSize: 16 },
  name: { color: C.fg, fontWeight: '800', fontSize: 15 },
  sub: { color: C.info, fontSize: 11.5, marginTop: 2 },
});
