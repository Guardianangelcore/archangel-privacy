/* Copyright © 2026 Guardian Angel. All Rights Reserved. This source code and its logic are the sole property of Guardian Angel. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, FlatList, RefreshControl, ActivityIndicator, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as DocumentPicker from 'expo-document-picker';
import { useRouter } from 'expo-router';
import { api, apiUpload } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, S } from '@/src/theme';
import { t, Lang } from '@/src/i18n';

type Doc = { doc_id: string; title: string; file_name: string; content_type: string; size: number; uploaded_at: string; plain_language?: string; extracted_text?: string };

export default function Vault() {
  const { user } = useAuth();
  const lang: Lang = (user?.language as Lang) || 'sk';
  const router = useRouter();
  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [busyDoc, setBusyDoc] = useState<string | null>(null);

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

  const ocrAndTranslate = async (doc: Doc) => {
    setBusyDoc(doc.doc_id);
    try {
      const ocr: any = await api(`/vault/documents/${doc.doc_id}/ocr`, { method: 'POST' });
      setDocs(prev => prev.map(d => d.doc_id === doc.doc_id ? { ...d, extracted_text: ocr.extracted_text } : d));
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

  return (
    <SafeAreaView testID="vault-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>{t('vault', lang).toUpperCase()}</Text>
        <Text style={styles.sub}>ZERO-KNOWLEDGE STORAGE</Text>
      </View>

      <FlatList
        data={docs}
        keyExtractor={i => i.doc_id}
        contentContainerStyle={{ padding: S.lg, paddingBottom: 160 }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.fg} />}
        ListEmptyComponent={
          !loading ? (
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
                <Text style={styles.docTitle} numberOfLines={2}>{item.title}</Text>
                <Text style={styles.docMeta}>{new Date(item.uploaded_at).toISOString().slice(0,10)} · {Math.round(item.size/1024)} KB</Text>
              </View>
              <Pressable testID={`doc-delete-${item.doc_id}`} onPress={() => remove(item)} hitSlop={10}>
                <Ionicons name="trash-outline" size={18} color={C.error} />
              </Pressable>
            </View>
            {item.plain_language ? (
              <View style={styles.translation}>
                <Text style={styles.translationLabel}>{t('translate', lang).toUpperCase()}</Text>
                <Text style={styles.translationText}>{item.plain_language}</Text>
              </View>
            ) : busyDoc === item.doc_id ? (
              <View style={styles.translateBtn}>
                <ActivityIndicator color={C.onInverse} size="small" />
                <Text style={styles.translateBtnText}>{t('reading_document', lang).toUpperCase()}</Text>
              </View>
            ) : (
              <View style={{ flexDirection: 'row', gap: S.sm }}>
                {isOcrable(item) && (
                  <Pressable testID={`doc-ocr-${item.doc_id}`} onPress={() => ocrAndTranslate(item)} style={[styles.translateBtn, { flex: 1, backgroundColor: C.brand }]}>
                    <Ionicons name="scan-outline" size={16} color={C.onInverse} />
                    <Text style={styles.translateBtnText}>{t('ocr_translate', lang).toUpperCase()}</Text>
                  </Pressable>
                )}
                <Pressable testID={`doc-translate-${item.doc_id}`} onPress={() => translate(item)} style={[styles.translateBtn, { flex: 1 }]}>
                  <Ionicons name="language-outline" size={16} color={C.onInverse} />
                  <Text style={styles.translateBtnText}>{t('translate', lang).toUpperCase()}</Text>
                </Pressable>
              </View>
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
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { paddingHorizontal: S.lg, paddingVertical: S.md, backgroundColor: C.inverse, borderBottomWidth: 2, borderBottomColor: C.inverse },
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
});
