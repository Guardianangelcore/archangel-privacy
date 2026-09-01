/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator, Platform, Share } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import QRCode from 'react-native-qrcode-svg';
import * as Clipboard from 'expo-clipboard';
import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';
import { api, API_BASE, getToken } from '@/src/api';
import { useAuth } from '@/src/auth';
import { ensureDropKeys, decryptDrop, b64encode } from '@/src/dropcrypto';
import { C, S, R } from '@/src/theme';

export default function HealthDrop() {
  const router = useRouter();
  const { user } = useAuth();
  const [me, setMe] = useState<any>(null);
  const [inbox, setInbox] = useState<any[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [booked, setBooked] = useState<any>(null);
  const [copied, setCopied] = useState(false);
  const [err, setErr] = useState('');

  const dropUrl = me?.drop_id ? `${API_BASE}/drop/${me.drop_id}` : '';

  const load = async () => {
    try { setInbox(await api('/health-drop/inbox')); } catch {}
  };

  useEffect(() => {
    (async () => {
      try {
        const info: any = await api('/health-drop/me');
        // ensure device keypair + register public key (zero-knowledge: secret never leaves device)
        const { publicKey } = await ensureDropKeys();
        if (info.public_key !== publicKey) {
          const upd: any = await api('/health-drop/pubkey', { method: 'PUT', body: JSON.stringify({ public_key: publicKey }) });
          setMe({ ...info, ...upd });
        } else setMe(info);
        await load();
      } catch (e: any) { setErr(String(e.message || e)); }
    })();
  }, []);

  const copy = async () => {
    await Clipboard.setStringAsync(dropUrl);
    setCopied(true); setTimeout(() => setCopied(false), 2000);
  };

  const shareLink = async () => {
    try {
      if (Platform.OS === 'web' && (navigator as any).share) await (navigator as any).share({ title: 'Guardian Health Drop', url: dropUrl });
      else if (Platform.OS === 'web') await copy();
      else await Share.share({ message: `Guardian Health Drop — send me medical documents securely: ${dropUrl}\nGuardian-ID: ${user?.did?.slice(-6)}` });
    } catch {}
  };

  const openDoc = async (item: any) => {
    setBusy(item.drop_doc_id); setErr('');
    try {
      const token = await getToken();
      const r = await fetch(`${API_BASE}/api/health-drop/items/${item.drop_doc_id}/file`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) throw new Error('Download failed');
      const ct = new Uint8Array(await r.arrayBuffer());
      const plain = await decryptDrop(ct, item.nonce, item.eph_pub);
      if (!plain) throw new Error('Decryption failed — key mismatch (was the document sent to another device?).');
      const ext = (item.orig_type || '').includes('pdf') ? 'pdf' : ((item.orig_type || '').split('/')[1] || 'bin');
      const fname = `guardian_drop_${item.drop_doc_id.slice(0, 6)}.${ext}`;
      if (Platform.OS === 'web') {
        const blob = new Blob([plain as any], { type: item.orig_type || 'application/octet-stream' });
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
      } else {
        const dest = `${FileSystem.cacheDirectory}${fname}`;
        await FileSystem.writeAsStringAsync(dest, b64encode(plain), { encoding: 'base64' as any });
        if (await Sharing.isAvailableAsync()) await Sharing.shareAsync(dest, { mimeType: item.orig_type || 'application/pdf', dialogTitle: fname });
      }
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const autobook = async (item: any) => {
    setBusy(`ab-${item.drop_doc_id}`); setErr('');
    try {
      const res: any = await api('/autobook', {
        method: 'POST',
        body: JSON.stringify({ specialty: item.specialty_guess || item.doc_title, source: 'health_drop', source_id: item.drop_doc_id }),
      });
      setBooked(res.booking);
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  return (
    <SafeAreaView testID="health-drop-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="hd-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>HEALTH DROP</Text>
        <View style={{ width: 24 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60 }}>
        <Text style={styles.h1}>Referral Bridge</Text>
        <Text style={styles.sub}>
          Your doctor sends a report or referral straight into your vault — no paper. Documents are
          encrypted with your public key already in the doctor browser (zero-knowledge).
        </Text>
        {!!err && <Text style={styles.err}>{err}</Text>}

        {me ? (
          <View style={styles.linkCard}>
            <View style={{ alignItems: 'center' }}>
              <View style={styles.qrBox}><QRCode value={dropUrl} size={150} backgroundColor="#FFFFFF" color="#121212" /></View>
            </View>
            <Text style={styles.linkText} numberOfLines={1}>{dropUrl}</Text>
            <Text style={styles.gid}>Guardian-ID for your doctor: <Text style={{ color: C.brand, fontWeight: '900' }}>{(user?.did || '').slice(-6).toUpperCase()}</Text></Text>
            <View style={{ flexDirection: 'row', gap: S.md, marginTop: S.md }}>
              <Pressable testID="hd-copy" onPress={copy} style={styles.ctaOutline}>
                <Ionicons name={copied ? 'checkmark' : 'copy-outline'} size={16} color={C.brand} />
                <Text style={styles.ctaOutlineText}>{copied ? 'COPIED' : 'COPY'}</Text>
              </Pressable>
              <Pressable testID="hd-share" onPress={shareLink} style={styles.cta}>
                <Ionicons name="share-social-outline" size={16} color={C.onInverse} />
                <Text style={styles.ctaText}>SHARE LINK</Text>
              </Pressable>
            </View>
          </View>
        ) : <ActivityIndicator color={C.brand} style={{ marginTop: 30 }} />}

        {booked && (
          <View style={styles.bookedBox}>
            <Ionicons name="checkmark-circle" size={22} color="#5FA779" />
            <View style={{ flex: 1 }}>
              <Text style={styles.bookedTitle}>APPOINTMENT BOOKED</Text>
              <Text style={styles.bookedSub}>{booked.specialty}: {booked.found_slot}</Text>
              <Pressable testID="hd-open-timeline" onPress={() => router.push('/health-timeline')}>
                <Text style={styles.bookedLink}>View in Health Timeline →</Text>
              </Pressable>
            </View>
          </View>
        )}

        <Text style={styles.section}>RECEIVED DOCUMENTS ({inbox.length})</Text>
        {inbox.length === 0 && <Text style={styles.hint}>None yet. Send the Drop link to your doctor.</Text>}
        {inbox.map(item => (
          <View key={item.drop_doc_id} style={styles.docCard}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.md }}>
              <View style={styles.docIcon}><Ionicons name="document-lock-outline" size={20} color={C.brand} /></View>
              <View style={{ flex: 1 }}>
                <Text style={styles.docTitle}>{item.doc_title}</Text>
                <Text style={styles.docSub}>{item.sender_name} · {(item.created_at || '').slice(0, 10)} · encrypted</Text>
              </View>
              <Pressable testID={`hd-open-${item.drop_doc_id}`} onPress={() => openDoc(item)} disabled={busy === item.drop_doc_id} style={styles.openBtn}>
                {busy === item.drop_doc_id ? <ActivityIndicator size="small" color={C.onInverse} /> : <Ionicons name="lock-open-outline" size={17} color={C.onInverse} />}
              </Pressable>
            </View>
            {item.is_referral && !item.autobooked && (
              <View style={styles.jarvisBox}>
                <Text style={styles.jarvisText}>
                  🤖 Jarvis: I can see a referral{item.specialty_guess ? ` for ${item.specialty_guess}` : ''}. Shall I find and book the earliest available appointment?
                </Text>
                <Pressable testID={`hd-autobook-${item.drop_doc_id}`} onPress={() => autobook(item)} disabled={busy === `ab-${item.drop_doc_id}`} style={styles.jarvisBtn}>
                  {busy === `ab-${item.drop_doc_id}` ? <ActivityIndicator size="small" color={C.onInverse} /> : <Text style={styles.jarvisBtnText}>YES, BOOK (AUTO-BOOKER)</Text>}
                </Pressable>
              </View>
            )}
            {item.autobooked && <Text style={styles.bookedFlag}>✓ Appointment booked by the Auto-Booker</Text>}
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 3, fontSize: 14 },
  h1: { fontSize: 24, fontWeight: '900', color: C.fg },
  sub: { marginTop: S.sm, fontSize: 13, color: C.onS3, lineHeight: 19 },
  linkCard: { marginTop: S.xl, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.brand, padding: S.lg },
  qrBox: { backgroundColor: '#FFFFFF', padding: S.md, borderRadius: R.sm },
  linkText: { marginTop: S.md, color: C.onS3, fontSize: 11, fontFamily: 'monospace', textAlign: 'center' },
  gid: { marginTop: 6, color: C.info, fontSize: 12, textAlign: 'center' },
  cta: { flex: 1, flexDirection: 'row', gap: 8, backgroundColor: C.brand, borderRadius: R.sm, minHeight: 48, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  ctaOutline: { flex: 1, flexDirection: 'row', gap: 8, borderWidth: 1.5, borderColor: C.brand, borderRadius: R.sm, minHeight: 48, alignItems: 'center', justifyContent: 'center' },
  ctaOutlineText: { color: C.brand, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  section: { marginTop: S.xl, marginBottom: S.sm, fontSize: 11, letterSpacing: 2, color: C.info, fontWeight: '800' },
  hint: { color: C.onS3, fontSize: 12 },
  docCard: { backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.md, marginBottom: S.sm },
  docIcon: { width: 40, height: 40, borderRadius: R.sm, backgroundColor: C.brandTer, alignItems: 'center', justifyContent: 'center' },
  docTitle: { color: C.fg, fontWeight: '800', fontSize: 13 },
  docSub: { color: C.info, fontSize: 11, marginTop: 2 },
  openBtn: { width: 44, height: 44, borderRadius: R.sm, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center' },
  jarvisBox: { marginTop: S.md, backgroundColor: C.brandTer, borderRadius: R.sm, padding: S.md },
  jarvisText: { color: C.fg, fontSize: 12, lineHeight: 18 },
  jarvisBtn: { marginTop: S.sm, backgroundColor: C.brand, borderRadius: R.sm, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  jarvisBtnText: { color: C.onInverse, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  bookedFlag: { marginTop: S.sm, color: '#5FA779', fontSize: 11, fontWeight: '800' },
  bookedBox: { marginTop: S.lg, flexDirection: 'row', gap: S.md, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: '#5FA779', padding: S.md },
  bookedTitle: { color: '#5FA779', fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  bookedSub: { color: C.fg, fontSize: 12, marginTop: 2 },
  bookedLink: { color: C.brand, fontSize: 12, fontWeight: '800', marginTop: 4 },
  err: { color: C.error, marginTop: S.md, fontSize: 12 },
});
