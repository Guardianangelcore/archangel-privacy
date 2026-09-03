/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// VIDEO LEGACY VAULT — Family Peace Treaty: sealed video messages for the family
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator, Platform, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { api, apiUpload } from '@/src/api';
import { C, S } from '@/src/theme';
import { useI18n } from '@/src/i18n-context';

export default function VideoLegacy() {
  const { t: tt, tx } = useI18n();
  const router = useRouter();
  const [videos, setVideos] = useState<any[]>([]);
  const [recipient, setRecipient] = useState('');
  const [relationship, setRelationship] = useState('rodina');
  const [title, setTitle] = useState('');
  const [uploading, setUploading] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState('');
  const [permBlocked, setPermBlocked] = useState(false);

  const load = useCallback(async () => {
    try { const r: any = await api('/legacy/video'); setVideos(r.videos || []); } catch (e) { console.log(e); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const pickAndUpload = async () => {
    setErr('');
    if (!recipient.trim()) { setErr('Enter the recipient name (who the message is for).'); return; }
    try {
      const perm = await ImagePicker.getMediaLibraryPermissionsAsync();
      if (!perm.granted && Platform.OS !== 'web') {
        if (!perm.canAskAgain) { setPermBlocked(true); return; }
        const res = await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (!res.granted) { if (!res.canAskAgain) setPermBlocked(true); return; }
      }
      const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['videos'], quality: 0.7, videoMaxDuration: 180 });
      if (result.canceled || !result.assets?.length) return;
      const a = result.assets[0];
      setUploading(true);
      await apiUpload('/legacy/video', a.uri, a.fileName || 'legacy_message.mp4', a.mimeType || 'video/mp4', {
        recipient_name: recipient.trim(),
        relationship: relationship.trim() || 'rodina',
        title: title.trim() || 'Odkaz pre rodinu',
        unlock_condition: 'death_verified',
      });
      setRecipient(''); setTitle('');
      await load();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setUploading(false); }
  };

  const release = async (vid: string) => {
    setBusy(vid); setErr('');
    try { await api(`/legacy/video/${vid}/release`, { method: 'POST' }); await load(); }
    catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const remove = async (vid: string) => {
    setBusy(vid);
    try { await api(`/legacy/video/${vid}`, { method: 'DELETE' }); await load(); }
    catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(null); }
  };

  return (
    <SafeAreaView testID="video-legacy-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="vl-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.onInverse} />
        </Pressable>
        <Text style={st.title}>{tt('video_legacy.video_legacy')}</Text>
        <View style={{ width: 26 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
        <View style={st.heroIcon}><Ionicons name="videocam-outline" size={28} color={C.brand} /></View>
        <Text style={st.h1}>{tt('video_legacy.family_peace_treaty')}</Text>
        <Text style={st.sub}>
          {tt('video_legacy.upload_a_sealed_video_message_for_yo')}
        </Text>

        {permBlocked && (
          <View style={st.permBox}>
            <Text style={st.permText}>{tt('video_legacy.gallery_access_is_blocked_enable_it')}</Text>
            <Pressable testID="vl-settings" onPress={() => Linking.openSettings()} style={st.permBtn}>
              <Text style={st.permBtnText}>{tt('video_legacy.open_settings')}</Text>
            </Pressable>
          </View>
        )}

        <Text style={st.section}>{tt('video_legacy.new_message')}</Text>
        <TextInput testID="vl-title" value={title} onChangeText={setTitle} placeholder={tt('video_legacy.title_e_g_for_my_daughter')}
          placeholderTextColor="#777" style={st.input} />
        <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.sm }}>
          <TextInput testID="vl-recipient" value={recipient} onChangeText={setRecipient} placeholder={tt('video_legacy.recipient_name')}
            placeholderTextColor="#777" style={[st.input, { flex: 1, marginTop: 0 }]} />
          <TextInput testID="vl-relationship" value={relationship} onChangeText={setRelationship} placeholder={tt('video_legacy.relationship')}
            placeholderTextColor="#777" style={[st.input, { width: 110, marginTop: 0 }]} />
        </View>
        <Pressable testID="vl-upload" onPress={pickAndUpload} disabled={uploading} style={st.uploadBtn}>
          {uploading ? <ActivityIndicator color={C.onInverse} /> : (
            <>
              <Ionicons name="cloud-upload-outline" size={18} color={C.onInverse} />
              <Text style={st.uploadText}>{tt('video_legacy.pick_video_seal')}</Text>
            </>
          )}
        </Pressable>
        {!!err && <Text testID="vl-err" style={st.err}>{err}</Text>}

        <Text style={st.section}>{tt('video_legacy.sealed_messages')}{videos.length})</Text>
        {videos.length === 0 && <Text style={st.empty}>{tt('video_legacy.no_video_messages_yet')}</Text>}
        {videos.map(v => (
          <View testID={`vl-video-${v.video_id}`} key={v.video_id} style={st.card}>
            <View style={st.rowSpread}>
              <View style={[st.badge, { backgroundColor: v.unlocked_for_family ? '#1B4332' : C.surface3 }]}>
                <Text style={st.badgeText}>{v.status}</Text>
              </View>
              <Text style={st.meta}>{(v.size / 1024 / 1024).toFixed(1)} MB</Text>
            </View>
            <Text style={st.cardTitle}>{tx(v.title)}</Text>
            <Text style={st.meta}>{tt('video_legacy.pre')} {v.recipient_name} ({v.relationship}{tt('video_legacy.sha_256')}{v.sha256?.slice(0, 12)}</Text>
            <Text style={st.meta}>🔐 {v.encryption}</Text>
            <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.md }}>
              {!v.released && (
                <Pressable testID={`vl-release-${v.video_id}`} onPress={() => release(v.video_id)} disabled={busy === v.video_id} style={[st.actBtn, { backgroundColor: C.brand }]}>
                  <Text style={st.actText}>{tt('video_legacy.release_to_family')}</Text>
                </Pressable>
              )}
              <Pressable testID={`vl-delete-${v.video_id}`} onPress={() => remove(v.video_id)} disabled={busy === v.video_id} style={[st.actBtn, { backgroundColor: C.error }]}>
                <Text style={st.actText}>{tt('video_legacy.delete')}</Text>
              </Pressable>
            </View>
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.md, paddingVertical: S.md, backgroundColor: C.inverse },
  title: { color: C.onInverse, fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  heroIcon: { width: 56, height: 56, borderWidth: 1.5, borderColor: C.brand, alignItems: 'center', justifyContent: 'center', marginBottom: S.md },
  h1: { color: C.fg, fontSize: 20, fontWeight: '900', letterSpacing: 0.5 },
  sub: { color: C.onS3, fontSize: 12, lineHeight: 18, marginTop: S.sm },
  section: { color: C.info, fontSize: 11, fontWeight: '900', letterSpacing: 2, marginTop: S.xl, marginBottom: S.sm },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, fontSize: 14, color: C.fg, backgroundColor: C.surface2, marginTop: S.sm },
  uploadBtn: { flexDirection: 'row', gap: S.sm, backgroundColor: C.brand, alignItems: 'center', justifyContent: 'center', minHeight: 52, marginTop: S.md },
  uploadText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  err: { color: C.error, fontWeight: '800', fontSize: 12, marginTop: S.sm },
  empty: { textAlign: 'center', color: C.info, marginTop: S.lg, letterSpacing: 2, fontWeight: '800', fontSize: 11 },
  card: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginTop: S.md, backgroundColor: C.surface2 },
  rowSpread: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  badge: { paddingHorizontal: 8, paddingVertical: 4 },
  badgeText: { fontSize: 9, fontWeight: '900', letterSpacing: 1, color: '#FFFFFF' },
  cardTitle: { color: C.fg, fontSize: 15, fontWeight: '800', marginTop: S.sm },
  meta: { color: C.info, fontSize: 10, marginTop: 4, letterSpacing: 0.3 },
  actBtn: { flex: 1, alignItems: 'center', justifyContent: 'center', minHeight: 44 },
  actText: { color: '#FFFFFF', fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  permBox: { borderWidth: 1.5, borderColor: C.warn, padding: S.md, marginTop: S.md, backgroundColor: C.surface2 },
  permText: { color: C.onS3, fontSize: 12, lineHeight: 18 },
  permBtn: { backgroundColor: C.warn, minHeight: 44, alignItems: 'center', justifyContent: 'center', marginTop: S.sm },
  permBtnText: { color: C.onWarn, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
});
