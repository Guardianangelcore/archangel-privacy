/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, FlatList, RefreshControl, ActivityIndicator, Platform, Modal, Image } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@react-native-vector-icons/ionicons';
import * as DocumentPicker from 'expo-document-picker';
import { useRouter } from 'expo-router';
import { api, apiUpload, API_BASE, getToken } from '@/src/api';
import { shareFile } from '@/src/pdf';
import { useAuth } from '@/src/auth';
import { AGE_LABEL_SK, ageFromBirthYear, stageFromAge } from '@/src/age';
import { speak as jarvisSpeak } from '@/src/voice';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';
import { useI18n } from '@/src/i18n-context';

type Doc = { doc_id: string; title: string; file_name: string; content_type: string; size: number; uploaded_at: string; plain_language?: string; extracted_text?: string; source?: string; prompt?: string };

export default function Vault() {
  const { t: tt, tx } = useI18n();
  const { user, setUser } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'en';
  const router = useRouter();
  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [busyDoc, setBusyDoc] = useState<string | null>(null);
  const [opening, setOpening] = useState<string | null>(null);
  const [preview, setPreview] = useState<{ title: string; uri: string } | null>(null);
  const [tok, setTok] = useState<string | null>(null);
  useEffect(() => { getToken().then(setTok).catch(() => {}); }, []);

  // JARVIS ART GALLERY — generated images live separately from medical documents.
  const art = docs.filter(d => d.source === 'jarvis_art');
  const files = docs.filter(d => d.source !== 'jarvis_art');
  const fileUri = (id: string) => `${API_BASE}/api/vault/documents/${id}/file?token=${tok}`;

  const load = useCallback(async () => {
    setLoading(true);
    try { setDocs(await api<Doc[]>('/vault/documents')); } catch (e) { console.log(e); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const upload = async () => {
    const res = await DocumentPicker.getDocumentAsync({ type: '*/*', copyToCacheDirectory: true });
    if (res.canceled) return;
    const asset = res.assets[0];
    setUploading(true);
    try {
      await apiUpload('/vault/documents', asset.uri, asset.name, asset.mimeType || 'application/octet-stream', { title: asset.name });
      await load();
    } catch (e: any) {
      console.log('upload err', e);
    } finally { setUploading(false); }
  };

  const translate = async (doc: Doc) => {
    setBusyDoc(doc.doc_id);
    try {
      const res: any = await api('/ai/translate-document', {
        method: 'POST',
        body: JSON.stringify({ doc_id: doc.doc_id, language: lang }),
      });
      setDocs(prev => prev.map(d => d.doc_id === doc.doc_id ? { ...d, plain_language: res.plain_language } : d));
    } catch (e) { console.log(e); } finally { setBusyDoc(null); }
  };

  const isOcrable = (doc: Doc) => {
    const ct = (doc.content_type || '').toLowerCase();
    const fn = (doc.file_name || '').toLowerCase();
    return ct.startsWith('image/') || ct.includes('pdf') || /\.(pdf|jpe?g|png|webp|heic)$/.test(fn);
  };

  const [ageToast, setAgeToast] = useState('');

  const ocrAndTranslate = async (doc: Doc) => {
    setBusyDoc(doc.doc_id);
    try {
      const ocr: any = await api(`/vault/documents/${doc.doc_id}/ocr`, { method: 'POST' });
      setDocs(prev => prev.map(d => d.doc_id === doc.doc_id ? { ...d, extracted_text: ocr.extracted_text } : d));
      // ZERO-FRICTION AGE SYNC — the backend auto-detected the user's birth year
      // from an ID/DOB/RČ pattern and silently updated Bio-Timeline. Announce it.
      if (ocr.birth_year_applied && ocr.birth_year_detected) {
        const stage = stageFromAge(ageFromBirthYear(ocr.birth_year_detected));
        const stageLbl = AGE_LABEL_SK[stage];
        setAgeToast(`✨ Bio-Timeline updated: ${stageLbl} (year ${ocr.birth_year_detected})`);
        try {
          const me: any = await api('/auth/me');
          if (me?.user) setUser(me.user);
        } catch {}
        try {
          jarvisSpeak(`Understood. Age set — ${stageLbl}. I adapted the interface.`,
            { voice: 'onyx', speed: 0.95, language: (user?.language as any) || 'en' });
        } catch {}
        setTimeout(() => setAgeToast(''), 6000);
      }
      const res: any = await api('/ai/translate-document', {
        method: 'POST',
        body: JSON.stringify({ doc_id: doc.doc_id, language: lang }),
      });
      setDocs(prev => prev.map(d => d.doc_id === doc.doc_id ? { ...d, plain_language: res.plain_language } : d));
    } catch (e) { console.log('ocr err', e); } finally { setBusyDoc(null); }
  };

  const remove = async (doc: Doc) => {
    await api(`/vault/documents/${doc.doc_id}`, { method: 'DELETE' });
    setDocs(prev => prev.filter(d => d.doc_id !== doc.doc_id));
  };

  const isImage = (doc: Doc) =>
    /\.(jpe?g|png|webp|gif)$/i.test(doc.file_name || '') ||
    ['image/jpeg', 'image/png', 'image/webp', 'image/gif'].includes((doc.content_type || '').toLowerCase());

  // View/Open — images open in a full-screen preview, PDFs & other files open natively
  const view = async (doc: Doc) => {
    if (isImage(doc)) {
      const token = await getToken();
      setPreview({ title: doc.title, uri: `${API_BASE}/api/vault/documents/${doc.doc_id}/file?token=${token}` });
      return;
    }
    setOpening(doc.doc_id);
    try {
      await shareFile(`/vault/documents/${doc.doc_id}/file`, doc.file_name || 'dokument.pdf', doc.content_type || 'application/octet-stream');
    } catch (e) { console.log('open err', e); }
    finally { setOpening(null); }
  };

  return (
    <SafeAreaView testID="vault-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>{t('vault', lang).toUpperCase()}</Text>
          <Text style={styles.sub}>{tt('tabs_vault.encrypted_storage_only_you_hold_the')}</Text>
        </View>
        <Pressable testID="vault-settings" onPress={() => router.push('/(tabs)/profile')} hitSlop={10}>
          <Ionicons name="settings-outline" size={22} color={C.onInverse} />
        </Pressable>
      </View>

      <FlatList
        data={files}
        keyExtractor={i => i.doc_id}
        contentContainerStyle={{ padding: S.lg, paddingBottom: 160 }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.fg} />}
        ListHeaderComponent={
          <>
            {/* GALÉRIA OBRAZOV — every Jarvis-generated image, forever yours */}
            {art.length > 0 && !!tok && (
              <View style={styles.gallery}>
                <View style={styles.galleryHead}>
                  <Ionicons name="color-palette" size={15} color={C.brand} />
                  <Text style={styles.galleryTitle}>{tt('tabs_vault.image_gallery_jarvis')}{art.length})</Text>
                </View>
                <View style={styles.galleryGrid}>
                  {art.map(a => (
                    <View key={a.doc_id} style={styles.thumbWrap}>
                      <Pressable
                        testID={`art-thumb-${a.doc_id}`}
                        onPress={() => setPreview({ title: a.title, uri: fileUri(a.doc_id) })}
                        style={styles.thumbPress}
                      >
                        <Image source={{ uri: fileUri(a.doc_id) }} style={styles.thumb} resizeMode="cover" />
                      </Pressable>
                      <Pressable testID={`art-del-${a.doc_id}`} onPress={() => remove(a)} hitSlop={8} style={styles.thumbDel}>
                        <Ionicons name="trash" size={12} color="#fff" />
                      </Pressable>
                    </View>
                  ))}
                </View>
              </View>
            )}
            {ageToast ? (
              <View testID="vault-age-toast" style={styles.ageToast}>
                <Ionicons name="sparkles" size={16} color={C.onInverse} />
                <Text style={styles.ageToastText}>{ageToast}</Text>
              </View>
            ) : null}
            {/* OCR VAULT ONBOARDING — first-visit prompt if user has no birth_year AND no docs.
                One-tap: Jarvis will fill Bio-Timeline + insurance fields from the scanned ID. */}
            {!loading && !docs.length && !(user as any)?.birth_year && (
              <Pressable testID="vault-first-scan" onPress={upload} disabled={uploading} style={styles.firstScan}>
                <View style={styles.firstScanIcon}>
                  {uploading ? <ActivityIndicator color={C.onInverse} /> : <Ionicons name="scan-outline" size={38} color={C.onInverse} />}
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.firstScanTitle}>{tt('tabs_vault.scan_your_id_card')}</Text>
                  <Text style={styles.firstScanSub}>{tt('tabs_vault.jarvis_fills_in_age_bio_timeline_and')}</Text>
                </View>
                <Ionicons name="chevron-forward" size={20} color={C.onInverse} />
              </Pressable>
            )}
          </>
        }
        ListEmptyComponent={
          !loading && art.length === 0 ? (
            <View style={styles.empty}>
              <Ionicons name="lock-closed-outline" size={48} color={C.fg} />
              <Text style={styles.emptyText}>{t('no_documents', lang).toUpperCase()}</Text>
            </View>
          ) : null
        }
        renderItem={({ item }) => (
          <View testID={`doc-${item.doc_id}`} style={styles.docCard}>
            <View style={styles.docHeader}>
              <View style={{ flex: 1 }}>
                <Text style={styles.docTitle} numberOfLines={2}>{tx(item.title)}</Text>
                <Text style={styles.docMeta}>{new Date(item.uploaded_at).toISOString().slice(0,10)} · {Math.round(item.size/1024)} KB</Text>
              </View>
              <Pressable testID={`doc-delete-${item.doc_id}`} onPress={() => remove(item)} hitSlop={10}>
                <Ionicons name="trash-outline" size={18} color={C.error} />
              </Pressable>
            </View>
            <Pressable testID={`doc-view-${item.doc_id}`} onPress={() => view(item)} style={styles.viewBtn}>
              {opening === item.doc_id ? <ActivityIndicator size="small" color={C.brand} /> : <Ionicons name="eye-outline" size={16} color={C.brand} />}
              <Text style={styles.viewBtnText}>{tt('tabs_vault.view_open')}</Text>
            </Pressable>
            {item.plain_language ? (
              <View style={styles.translation}>
                <Text style={styles.translationLabel}>{tt('tabs_vault.jarvis_zhrnutie')}</Text>
                <Text style={styles.translationText}>{item.plain_language}</Text>
              </View>
            ) : busyDoc === item.doc_id ? (
              <View style={styles.translateBtn}>
                <ActivityIndicator color={C.onInverse} size="small" />
                <Text style={styles.translateBtnText}>{t('reading_document', lang).toUpperCase()}</Text>
              </View>
            ) : (
              <Pressable testID={`doc-jarvis-${item.doc_id}`} onPress={() => (isOcrable(item) ? ocrAndTranslate(item) : translate(item))} style={[styles.translateBtn, { backgroundColor: C.brand }]}>
                <Ionicons name="sparkles" size={16} color={C.onInverse} />
                <Text style={styles.translateBtnText}>{tt('tabs_vault.jarvis_zhrnutie')}</Text>
              </Pressable>
            )}
          </View>
        )}
      />

      <View style={styles.footer}>
        <Pressable testID="translate-text-btn" onPress={() => router.push('/translate')} style={styles.secBtn}>
          <Ionicons name="language-outline" size={18} color={C.fg} />
          <Text style={styles.secBtnText}>{t('translate', lang).toUpperCase()}</Text>
        </Pressable>
        <Pressable testID="upload-doc-btn" onPress={upload} disabled={uploading} style={styles.priBtn}>
          {uploading ? <ActivityIndicator color={C.onInverse} /> : <Ionicons name="cloud-upload-outline" size={18} color={C.onInverse} />}
          <Text style={styles.priBtnText}>{t('upload_doc', lang).toUpperCase()}</Text>
        </Pressable>
      </View>

      {/* FULL-SCREEN IMAGE PREVIEW */}
      <Modal visible={!!preview} animationType="slide" onRequestClose={() => setPreview(null)}>
        <SafeAreaView style={{ flex: 1, backgroundColor: C.bg }} edges={['top', 'bottom']}>
          <View style={styles.pvHeader}>
            <Pressable testID="doc-preview-close" onPress={() => setPreview(null)} hitSlop={12}>
              <Ionicons name="close" size={26} color={C.fg} />
            </Pressable>
            <Text style={styles.pvTitle} numberOfLines={1}>{preview?.title}</Text>
            <View style={{ width: 26 }} />
          </View>
          {preview && (
            <Image testID="doc-preview-image" source={{ uri: preview.uri }} style={{ flex: 1 }} resizeMode="contain" />
          )}
        </SafeAreaView>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  gallery: { marginBottom: S.lg, borderWidth: 1.5, borderColor: C.brand, padding: S.md, backgroundColor: 'rgba(212,175,55,0.05)' },
  galleryHead: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: S.md },
  galleryTitle: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 2 },
  galleryGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  thumbWrap: { width: '31%', aspectRatio: 1, position: 'relative' },
  thumbPress: { flex: 1 },
  thumb: { width: '100%', height: '100%', borderRadius: 6, backgroundColor: 'rgba(255,255,255,0.06)' },
  thumbDel: { position: 'absolute', top: 4, right: 4, width: 26, height: 26, borderRadius: 13, backgroundColor: 'rgba(0,0,0,0.65)', alignItems: 'center', justifyContent: 'center' },
  ageToast: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: C.brand, borderRadius: 12, paddingHorizontal: S.md, paddingVertical: S.sm, marginBottom: S.md },
  ageToastText: { color: C.onInverse, fontWeight: '900', fontSize: 12, letterSpacing: 0.5, flex: 1 },
  firstScan: { flexDirection: 'row', alignItems: 'center', gap: S.md, backgroundColor: C.brand, borderRadius: 16, padding: S.md, marginBottom: S.lg, shadowColor: C.brand, shadowOpacity: 0.4, shadowRadius: 16, shadowOffset: { width: 0, height: 6 }, elevation: 10 },
  firstScanIcon: { width: 58, height: 58, borderRadius: 29, backgroundColor: 'rgba(255,255,255,0.22)', alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: 'rgba(255,255,255,0.35)' },
  firstScanTitle: { color: C.onInverse, fontWeight: '900', fontSize: 14, letterSpacing: 2 },
  firstScanSub: { color: 'rgba(255,255,255,0.9)', fontSize: 12, lineHeight: 16, marginTop: 3 },
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', gap: S.md, paddingHorizontal: S.lg, paddingVertical: S.md, backgroundColor: C.inverse, borderBottomWidth: 2, borderBottomColor: C.inverse },
  title: { color: C.onInverse, fontSize: 22, fontWeight: '900', letterSpacing: 2 },
  sub: { color: C.onInverse, opacity: 0.6, fontSize: 10, letterSpacing: 2, marginTop: 2 },
  empty: { alignItems: 'center', paddingVertical: 60, gap: S.md },
  emptyText: { color: C.fg, fontWeight: '800', letterSpacing: 1, fontSize: 13 },
  docCard: { borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, marginBottom: S.md, backgroundColor: C.bg },
  docHeader: { flexDirection: 'row', alignItems: 'flex-start', gap: S.md },
  docTitle: { fontSize: 16, fontWeight: '800', color: C.fg },
  docMeta: { fontSize: 11, color: C.onS3, marginTop: 4, letterSpacing: 1 },
  translateBtn: { marginTop: S.md, backgroundColor: C.inverse, paddingVertical: S.md, alignItems: 'center', flexDirection: 'row', justifyContent: 'center', gap: 8, paddingHorizontal: 4 },
  translateBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 12 },
  translation: { marginTop: S.md, borderTopWidth: 1.5, borderColor: C.borderStrong, paddingTop: S.md },
  translationLabel: { fontSize: 10, letterSpacing: 2, color: C.brand, fontWeight: '900', marginBottom: 6 },
  translationText: { color: C.fg, fontSize: 14, lineHeight: 20 },
  footer: { position: 'absolute', bottom: Platform.OS === 'ios' ? 96 : 76, left: S.lg, right: S.lg, flexDirection: 'row', gap: S.md },
  priBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, backgroundColor: C.inverse, paddingVertical: S.md, borderWidth: 2, borderColor: C.borderStrong },
  priBtnText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  secBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, backgroundColor: C.bg, paddingVertical: S.md, borderWidth: 2, borderColor: C.borderStrong },
  secBtnText: { color: C.fg, fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  viewBtn: { marginTop: S.md, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, borderWidth: 2, borderColor: C.brand, paddingVertical: S.md, backgroundColor: 'rgba(212,175,55,0.08)', minHeight: 48 },
  viewBtnText: { color: C.brand, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
  pvHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md, gap: S.md },
  pvTitle: { flex: 1, color: C.fg, fontWeight: '800', fontSize: 14, textAlign: 'center' },
});
