/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// RODINNÉ KONTAKTY — encrypted emergency phone book of the Family Shield.
// Add · Call · SOS · Delete (with confirmation). Backend: /api/family-contacts.
import React, { useCallback, useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator,
  Modal, Platform, Linking, KeyboardAvoidingView, LayoutAnimation, UIManager,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { tap } from '@/src/ui/glass';
import { C, S, R } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}
const animate = () => { try { LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut); } catch {} };

type Contact = { contact_id: string; name: string; phone: string; relation: string; relation_label: string };

const RELATIONS = [
  { id: 'partner', label: 'Partner' },
  { id: 'rodic', label: 'Parent' },
  { id: 'surodenec', label: 'Sibling' },
  { id: 'dieta', label: 'Child' },
  { id: 'priatel', label: 'Friend' },
  { id: 'lekar', label: 'Doctor' },
  { id: 'ine', label: 'Other' },
];

export default function FamilyContacts() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [show, setShow] = useState(false);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('+421 ');
  const [relation, setRelation] = useState('rodic');
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [toast, setToast] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try { const r: any = await api('/family-contacts'); setContacts(r.contacts || []); } catch {}
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const showToast = (t: string) => { setToast(t); setTimeout(() => setToast(''), 3500); };

  const save = async () => {
    setSaving(true); setErr('');
    try {
      const c: any = await api('/family-contacts', {
        method: 'POST',
        body: JSON.stringify({ name: name.trim(), phone: phone.trim(), relation }),
      });
      animate();
      setContacts(prev => [...prev, c]);
      setShow(false); setName(''); setPhone('+421 '); setRelation('rodic');
      showToast(`✓ ${c.name} added to your Family Shield`);
    } catch (e: any) { setErr(String(e?.message || e).replace(/^\d+:\s*/, '')); }
    finally { setSaving(false); }
  };

  const call = (c: Contact) => {
    tap('medium');
    Linking.openURL(`tel:${c.phone.replace(/[^+0-9]/g, '')}`).catch(() => showToast('Dialing is not available on this device.'));
  };

  const sos = async (c: Contact) => {
    tap('heavy'); setBusyId(c.contact_id);
    try {
      const r: any = await api(`/family-contacts/${c.contact_id}/sos`, { method: 'POST' });
      showToast(`🆘 ${r.message}`);
      if (!r.sms_sent) {
        // Twilio not configured yet → open the device composer with the prefilled SOS text.
        const smsUrl = `sms:${c.phone.replace(/[^+0-9]/g, '')}${Platform.OS === 'ios' ? '&' : '?'}body=${encodeURIComponent(r.sms_body)}`;
        Linking.openURL(smsUrl).catch(() => {});
      }
    } catch (e: any) { showToast(String(e?.message || e)); }
    finally { setBusyId(null); }
  };

  const remove = async (c: Contact) => {
    setBusyId(c.contact_id);
    try {
      await api(`/family-contacts/${c.contact_id}`, { method: 'DELETE' });
      animate();
      setContacts(prev => prev.filter(x => x.contact_id !== c.contact_id));
      showToast(`Contact ${c.name} removed.`);
    } catch (e: any) { showToast(String(e?.message || e)); }
    finally { setBusyId(null); setConfirmId(null); }
  };

  return (
    <SafeAreaView testID="family-contacts-screen" style={st.root} edges={['top', 'bottom']}>
      <View style={st.header}>
        <Pressable testID="fc-back" onPress={() => { tap(); if (router.canGoBack()) { router.back(); } else { router.replace('/(tabs)/family'); } }} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={st.title}>{tt('family_contacts.family_contacts')}</Text>
        <Pressable testID="fc-settings" onPress={() => { tap(); router.push('/(tabs)/profile'); }} hitSlop={10}>
          <Ionicons name="settings-outline" size={20} color={C.onS3} />
        </Pressable>
      </View>

      {!!toast && (
        <View testID="fc-toast" style={st.toast}><Text style={st.toastText}>{toast}</Text></View>
      )}

      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        <Text style={st.sub}>{tt('family_contacts.your_family_emergency_numbers_encryp')}</Text>

        <Pressable testID="fc-add" onPress={() => { tap('medium'); setErr(''); setShow(true); }} style={st.addBtn}>
          <Ionicons name="person-add" size={20} color={C.onInverse} />
          <Text style={st.addBtnText}>{tt('family_contacts.add_family_member')}</Text>
        </Pressable>

        {loading && <ActivityIndicator color={C.brand} style={{ marginTop: S.xl }} />}
        {!loading && contacts.length === 0 && (
          <View style={st.empty}>
            <Ionicons name="people-outline" size={44} color={C.info} />
            <Text style={st.emptyText}>{tt('family_contacts.no_contacts_yet')}{'\n'}{tt('family_contacts.add_your_first_family_member_just_in')}</Text>
          </View>
        )}

        {contacts.map(c => (
          <View key={c.contact_id} testID={`fc-card-${c.contact_id}`} style={st.card}>
            <View style={st.cardHead}>
              <View style={st.avatar}><Text style={st.avatarText}>{(c.name[0] || '?').toUpperCase()}</Text></View>
              <View style={{ flex: 1 }}>
                <Text style={st.cardName}>{c.name}</Text>
                <Text style={st.cardPhone}>{c.phone}</Text>
              </View>
              <View style={st.relBadge}><Text style={st.relBadgeText}>{c.relation_label.toUpperCase()}</Text></View>
            </View>
            {confirmId === c.contact_id ? (
              <View style={st.confirmRow}>
                <Text style={st.confirmText}>{tt('family_contacts.really_remove')} {c.name}?</Text>
                <Pressable testID={`fc-del-yes-${c.contact_id}`} onPress={() => remove(c)} style={st.confirmYes}>
                  {busyId === c.contact_id ? <ActivityIndicator size="small" color={C.onError} /> : <Text style={st.confirmYesText}>{tt('family_contacts.yes_remove')}</Text>}
                </Pressable>
                <Pressable testID={`fc-del-no-${c.contact_id}`} onPress={() => setConfirmId(null)} style={st.confirmNo}>
                  <Text style={st.confirmNoText}>{tt('family_contacts.nie')}</Text>
                </Pressable>
              </View>
            ) : (
              <View style={st.actionRow}>
                <Pressable testID={`fc-call-${c.contact_id}`} onPress={() => call(c)} style={[st.action, st.actionCall]}>
                  <Ionicons name="call" size={16} color={C.onInverse} />
                  <Text style={st.actionTextInv}>{tt('family_contacts.call')}</Text>
                </Pressable>
                <Pressable testID={`fc-sos-${c.contact_id}`} onPress={() => sos(c)} disabled={busyId === c.contact_id} style={[st.action, st.actionSos]}>
                  {busyId === c.contact_id ? <ActivityIndicator size="small" color={C.onError} /> : (
                    <>
                      <Ionicons name="warning" size={16} color={C.onError} />
                      <Text style={[st.actionTextInv, { color: C.onError }]}>{tt('family_contacts.send_sos')}</Text>
                    </>
                  )}
                </Pressable>
                <Pressable testID={`fc-del-${c.contact_id}`} onPress={() => { tap('light'); setConfirmId(c.contact_id); }} hitSlop={6} style={st.actionDel}>
                  <Ionicons name="trash-outline" size={18} color={C.info} />
                </Pressable>
              </View>
            )}
          </View>
        ))}

        <Text style={st.footNote}>{tt('family_contacts.numbers_are_encrypted_fernet_aes_the')}</Text>
      </ScrollView>

      {/* ADD CONTACT MODAL */}
      <Modal visible={show} transparent animationType="slide" onRequestClose={() => setShow(false)}>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={st.overlay}>
          <Pressable style={{ flex: 1 }} onPress={() => setShow(false)} />
          <View style={st.sheet}>
            <View style={st.sheetHandle} />
            <Text style={st.sheetTitle}>{tt('family_contacts.new_family_member')}</Text>

            <Text style={st.label}>{tt('family_contacts.meno')}</Text>
            <TextInput testID="fc-name" value={name} onChangeText={setName} placeholder={tt('family_contacts.e_g_maria')}
              placeholderTextColor={C.info} style={st.input} autoCapitalize="words" />

            <Text style={st.label}>{tt('family_contacts.phone_number')}</Text>
            <TextInput testID="fc-phone" value={phone} onChangeText={setPhone} placeholder="+421 900 123 456"
              placeholderTextColor={C.info} style={st.input} keyboardType="phone-pad" />

            <Text style={st.label}>{tt('family_contacts.relationship')}</Text>
            <View style={st.relRow}>
              {RELATIONS.map(r => (
                <Pressable key={r.id} testID={`fc-rel-${r.id}`} onPress={() => { tap('light'); setRelation(r.id); }}
                  style={[st.relChip, relation === r.id && st.relChipActive]}>
                  <Text style={[st.relChipText, relation === r.id && { color: C.onInverse }]}>{tx(r.label)}</Text>
                </Pressable>
              ))}
            </View>

            {!!err && <Text testID="fc-err" style={st.err}>{err}</Text>}

            <Pressable testID="fc-save" onPress={save} disabled={saving || !name.trim() || phone.trim().length < 6} style={[st.saveBtn, (!name.trim() || phone.trim().length < 6) && { opacity: 0.5 }]}>
              {saving ? <ActivityIndicator color={C.onInverse} /> : (
                <>
                  <Ionicons name="shield-checkmark" size={18} color={C.onInverse} />
                  <Text style={st.saveBtnText}>{tt('family_contacts.save_to_family_shield')}</Text>
                </>
              )}
            </Pressable>
            <Pressable testID="fc-cancel" onPress={() => setShow(false)} style={st.cancelBtn}>
              <Text style={st.cancelText}>{tt('family_contacts.cancel')}</Text>
            </Pressable>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 2.5, fontSize: 14 },
  sub: { color: C.onS3, fontSize: 13, lineHeight: 19 },
  toast: { marginHorizontal: S.lg, marginTop: S.sm, backgroundColor: C.brand, borderRadius: R.pill, paddingHorizontal: S.md, paddingVertical: S.sm },
  toastText: { color: C.onInverse, fontWeight: '800', fontSize: 12 },
  addBtn: { flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, borderRadius: R.pill, minHeight: 56, marginTop: S.lg, shadowColor: C.brand, shadowOpacity: 0.4, shadowRadius: 14, shadowOffset: { width: 0, height: 5 }, elevation: 8 },
  addBtnText: { color: C.onInverse, fontWeight: '900', fontSize: 14, letterSpacing: 1.5 },
  empty: { alignItems: 'center', gap: S.md, paddingVertical: 50 },
  emptyText: { color: C.info, fontSize: 13, textAlign: 'center', lineHeight: 19 },
  card: { marginTop: S.md, backgroundColor: C.surface2, borderRadius: R.lg, borderWidth: 1, borderColor: C.border, padding: S.md },
  cardHead: { flexDirection: 'row', alignItems: 'center', gap: S.md },
  avatar: { width: 46, height: 46, borderRadius: 23, backgroundColor: C.brandTer, alignItems: 'center', justifyContent: 'center', borderWidth: 1.5, borderColor: C.brand },
  avatarText: { color: C.brand, fontWeight: '900', fontSize: 18 },
  cardName: { color: C.fg, fontWeight: '900', fontSize: 16 },
  cardPhone: { color: C.onS3, fontSize: 13, marginTop: 2, fontVariant: ['tabular-nums'] },
  relBadge: { borderWidth: 1, borderColor: C.brand, borderRadius: R.pill, paddingHorizontal: 10, paddingVertical: 4, backgroundColor: 'rgba(212,175,55,0.1)' },
  relBadgeText: { color: C.brand, fontWeight: '900', fontSize: 9, letterSpacing: 1 },
  actionRow: { flexDirection: 'row', gap: S.sm, marginTop: S.md, alignItems: 'center' },
  action: { flex: 1, flexDirection: 'row', gap: 6, alignItems: 'center', justifyContent: 'center', minHeight: 46, borderRadius: R.pill },
  actionCall: { backgroundColor: '#2E7D32' },
  actionSos: { backgroundColor: C.error },
  actionTextInv: { color: C.onInverse, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  actionDel: { width: 46, height: 46, borderRadius: 23, borderWidth: 1, borderColor: C.border, alignItems: 'center', justifyContent: 'center' },
  confirmRow: { marginTop: S.md, gap: S.sm },
  confirmText: { color: C.fg, fontWeight: '800', fontSize: 13 },
  confirmYes: { backgroundColor: C.error, borderRadius: R.pill, minHeight: 46, alignItems: 'center', justifyContent: 'center' },
  confirmYesText: { color: C.onError, fontWeight: '900', fontSize: 12, letterSpacing: 1 },
  confirmNo: { borderWidth: 1.5, borderColor: C.border, borderRadius: R.pill, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  confirmNoText: { color: C.info, fontWeight: '900', fontSize: 12, letterSpacing: 1 },
  footNote: { color: C.info, fontSize: 10.5, lineHeight: 15, marginTop: S.xl, textAlign: 'center' },
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.72)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: C.surface2, borderTopLeftRadius: R.lg, borderTopRightRadius: R.lg, padding: S.xl, paddingBottom: 34, borderWidth: 1, borderColor: C.borderStrong },
  sheetHandle: { alignSelf: 'center', width: 44, height: 5, borderRadius: 3, backgroundColor: C.surface3, marginBottom: S.md },
  sheetTitle: { color: C.fg, fontWeight: '900', fontSize: 17, letterSpacing: 1.5, marginBottom: S.sm },
  label: { color: C.brand, fontWeight: '900', fontSize: 10, letterSpacing: 2, marginTop: S.md, marginBottom: 6 },
  input: { backgroundColor: C.bg, borderWidth: 1.5, borderColor: C.border, borderRadius: R.md, color: C.fg, paddingHorizontal: S.md, minHeight: 52, fontSize: 15 },
  relRow: { flexDirection: 'row', flexWrap: 'wrap', gap: S.sm },
  relChip: { borderWidth: 1.5, borderColor: C.border, borderRadius: R.pill, paddingHorizontal: S.md, minHeight: 40, alignItems: 'center', justifyContent: 'center' },
  relChipActive: { backgroundColor: C.brand, borderColor: C.brand },
  relChipText: { color: C.onS3, fontWeight: '800', fontSize: 12 },
  err: { color: C.error, fontSize: 12, marginTop: S.md, fontWeight: '700' },
  saveBtn: { flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, borderRadius: R.pill, minHeight: 54, marginTop: S.lg },
  saveBtnText: { color: C.onInverse, fontWeight: '900', fontSize: 13, letterSpacing: 1 },
  cancelBtn: { alignItems: 'center', justifyContent: 'center', minHeight: 46, marginTop: S.sm },
  cancelText: { color: C.info, fontWeight: '900', fontSize: 12, letterSpacing: 2 },
});
