/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// SURVIVAL PANTRY — Guardian Lens for the bunker.
// List of tracked items with color-coded urgency + a big Jarvis alert if
// something is expiring within 30 days.
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator, RefreshControl, TextInput, Modal } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import * as DocumentPicker from 'expo-document-picker';
import { useAudioRecorder, RecordingPresets, AudioModule, setAudioModeAsync } from 'expo-audio';
import { api, apiUpload } from '@/src/api';
import { useAuth } from '@/src/auth';
import { C, S, R, GOLD } from '@/src/theme';
import { tap } from '@/src/ui/glass';
import { speak as jarvisSpeak } from '@/src/voice';

type Item = {
  pantry_id: string;
  name: string;
  category: string;
  expiration_date: string;
  quantity: number;
  location?: string;
  days_left: number | null;
  urgency: 'expired' | 'critical' | 'soon' | 'healthy' | 'fresh' | 'unknown';
};

const CATS = [
  { key: 'food', label: 'Konzervy · potraviny', icon: 'nutrition' },
  { key: 'water', label: 'Voda', icon: 'water' },
  { key: 'battery', label: 'Batteries', icon: 'battery-charging' },
  { key: 'gas', label: 'Plyn · palivo', icon: 'flame' },
  { key: 'med', label: 'Lieky', icon: 'medkit' },
  { key: 'filter', label: 'Filtre', icon: 'funnel' },
  { key: 'ammo', label: 'Ammo', icon: 'shield' },
  { key: 'tool', label: 'Tools', icon: 'construct' },
  { key: 'other', label: 'Other', icon: 'cube' },
];

const URGENCY_STYLE: Record<Item['urgency'], { color: string; label: string }> = {
  expired:  { color: '#EF4444', label: 'PO SPOTREBE' },
  critical: { color: '#F59E0B', label: 'ROTATE NOW' },
  soon:     { color: '#EAB308', label: 'SOON' },
  healthy:  { color: '#22C55E', label: 'V PORIADKU' },
  fresh:    { color: '#10B981', label: 'FRESH' },
  unknown:  { color: '#94A3B8', label: 'NO DATE' },
};

export default function Pantry() {
  const router = useRouter();
  const { user } = useAuth();
  const [items, setItems] = useState<Item[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [alertLine, setAlertLine] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newCat, setNewCat] = useState('food');
  const [newExp, setNewExp] = useState('');
  const [newQty, setNewQty] = useState('1');
  const [newLoc, setNewLoc] = useState('');
  const [scanning, setScanning] = useState(false);
  const [scanCat, setScanCat] = useState('food');
  const [voiceOpen, setVoiceOpen] = useState(false);
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [voiceHeard, setVoiceHeard] = useState<string>('');
  const voiceRecorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [list, alerts]: any = await Promise.all([
        api('/pantry'),
        api('/pantry/alerts'),
      ]);
      setItems(list.items || []);
      setCounts(list.counts || {});
      setAlertLine(alerts.top_line || null);
      if (alerts.top_line) {
        jarvisSpeak(alerts.top_line, { voice: 'onyx', speed: 0.95, language: (user?.language as any) || 'en' });
      }
    } catch (e) { console.log(e); }
    setLoading(false);
  }, [user?.language]);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    if (!newName.trim()) return;
    try {
      await api('/pantry', {
        method: 'POST',
        body: JSON.stringify({
          name: newName.trim(),
          category: newCat,
          expiration_date: newExp.trim() || null,
          quantity: parseInt(newQty || '1', 10),
          location: newLoc.trim() || null,
        }),
      });
      setAddOpen(false); setNewName(''); setNewExp(''); setNewQty('1'); setNewLoc('');
      await load();
    } catch (e: any) { console.log(e); }
  };

  const scan = async () => {
    // Uses the same OCR pipeline as Guardian Lens: pick a photo, upload to Vault,
    // then POST /pantry/scan with the doc_id to auto-extract the expiration.
    try {
      const res = await DocumentPicker.getDocumentAsync({ type: ['image/*', 'application/pdf'], copyToCacheDirectory: true });
      if (res.canceled || !res.assets?.[0]) return;
      const a = res.assets[0];
      setScanning(true);
      // 1) Upload to Vault documents
      const up: any = await apiUpload('/vault/documents/upload', a.uri, a.name || 'pantry.jpg', a.mimeType || 'image/jpeg', { title: a.name || 'Pantry scan' });
      // 2) OCR + create pantry entry
      const pr: any = await api('/pantry/scan', {
        method: 'POST',
        body: JSON.stringify({ doc_id: up.doc_id, hint_category: scanCat, location: newLoc.trim() || null }),
      });
      const stage = pr.extracted_expiry ? 'from label' : 'standard shelf life';
      jarvisSpeak(`${pr.name} added. Expiry (${stage}): ${pr.expiration_date}.`,
        { voice: 'onyx', speed: 0.95, language: (user?.language as any) || 'en' });
      await load();
    } catch (e) { console.log('scan err', e); }
    finally { setScanning(false); }
  };

  const remove = async (id: string) => {
    try { await api(`/pantry/${id}`, { method: 'DELETE' }); await load(); }
    catch (e) { console.log(e); }
  };

  // VOICE-FIRST ADD — Whisper → LLM parse → insert. Zero typing for seniors.
  const startVoice = async () => {
    setVoiceOpen(true); setVoiceHeard('');
    if (Platform.OS === 'web') return;
    try {
      let perm = await AudioModule.getRecordingPermissionsAsync();
      if (!perm.granted) {
        perm = await AudioModule.requestRecordingPermissionsAsync();
        if (!perm.granted) return;
      }
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true } as any);
      await voiceRecorder.prepareToRecordAsync();
      voiceRecorder.record();
      jarvisSpeak('Listening. Tell me what to add to your supplies.', {
        voice: 'onyx', speed: 1.0, language: (user?.language as any) || 'en',
      });
    } catch (e) { console.log('voice start', e); }
  };

  const stopVoice = async () => {
    if (Platform.OS === 'web') { setVoiceOpen(false); return; }
    setVoiceBusy(true);
    try {
      await voiceRecorder.stop();
      const uri = voiceRecorder.uri;
      if (!uri) { setVoiceOpen(false); setVoiceBusy(false); return; }
      const name = uri.endsWith('.m4a') ? 'pantry.m4a' : 'pantry.webm';
      const ct = uri.endsWith('.m4a') ? 'audio/m4a' : 'audio/webm';
      const parsed: any = await apiUpload('/pantry/voice', uri, name, ct, {});
      setVoiceHeard(`${parsed.quantity}× „${parsed.name}"${parsed.location ? ` v „${parsed.location}"` : ''}`);
      jarvisSpeak(`Added: ${parsed.quantity} pcs of ${parsed.name}${parsed.location ? `, in ${parsed.location}` : ''}.`, {
        voice: 'onyx', speed: 0.95, language: (user?.language as any) || 'en',
      });
      await load();
      setTimeout(() => setVoiceOpen(false), 2000);
    } catch (e: any) { console.log('voice stop', e); setVoiceOpen(false); }
    setVoiceBusy(false);
  };

  return (
    <SafeAreaView testID="pantry-screen" style={styles.root} edges={['top']}>
      <View style={styles.header}>
        <Pressable testID="pantry-back" onPress={() => { tap(); router.back(); }} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.fg} />
        </Pressable>
        <Text style={styles.title}>SURVIVAL PANTRY</Text>
        <Pressable testID="pantry-add" onPress={() => setAddOpen(true)} hitSlop={12}>
          <Ionicons name="add-circle" size={26} color={C.brand} />
        </Pressable>
      </View>

      {alertLine && (
        <Pressable
          testID="pantry-alert"
          onPress={() => jarvisSpeak(alertLine, { voice: 'onyx', speed: 0.95, language: (user?.language as any) || 'en' })}
          style={styles.alertRow}
        >
          <Ionicons name="warning" size={20} color={C.onInverse} />
          <Text style={styles.alertText}>{alertLine}</Text>
        </Pressable>
      )}

      <View style={styles.chipRow}>
        {(['critical', 'soon', 'healthy', 'expired'] as const).map((k) => (
          <View key={k} style={[styles.chip, { borderColor: URGENCY_STYLE[k].color }]}>
            <View style={[styles.chipDot, { backgroundColor: URGENCY_STYLE[k].color }]} />
            <Text style={styles.chipText}>{URGENCY_STYLE[k].label}</Text>
            <Text style={styles.chipCount}>{counts[k] || 0}</Text>
          </View>
        ))}
      </View>

      <ScrollView
        contentContainerStyle={{ padding: S.lg, paddingBottom: 200 }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor={C.brand} />}
      >
        {items.length === 0 && !loading && (
          <View style={styles.empty}>
            <Ionicons name="cube-outline" size={48} color={C.onS3} />
            <Text style={styles.emptyText}>GET STARTED — SCAN YOUR FIRST SUPPLY</Text>
            <Text style={styles.emptyHint}>Jarvis reads the expiry date from the label.</Text>
          </View>
        )}
        {items.map((it) => {
          const u = URGENCY_STYLE[it.urgency];
          const catMeta = CATS.find((c) => c.key === it.category) || CATS[8];
          return (
            <View key={it.pantry_id} testID={`pantry-item-${it.pantry_id}`} style={styles.card}>
              <View style={[styles.itemIcon, { borderColor: u.color }]}>
                <Ionicons name={catMeta.icon as any} size={22} color={u.color} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.itemName} numberOfLines={1}>{it.name}</Text>
                <Text style={styles.itemMeta}>
                  {it.quantity}× · {catMeta.label}{it.location ? ` · ${it.location}` : ''}
                </Text>
                <View style={styles.itemFooter}>
                  <View style={[styles.miniPill, { borderColor: u.color }]}>
                    <Text style={[styles.miniPillText, { color: u.color }]}>{u.label}</Text>
                  </View>
                  <Text style={styles.itemDays}>
                    {it.days_left === null ? '—'
                      : it.days_left < 0 ? `-${Math.abs(it.days_left)} d`
                      : `${it.days_left} d`}
                  </Text>
                </View>
              </View>
              <Pressable testID={`pantry-del-${it.pantry_id}`} onPress={() => remove(it.pantry_id)} hitSlop={10}>
                <Ionicons name="trash-outline" size={18} color={C.error} />
              </Pressable>
            </View>
          );
        })}

        {/* Bulk actions */}
        <Pressable
          testID="pantry-scan"
          onPress={scan}
          disabled={scanning}
          style={styles.scanCta}
        >
          <LinearGradient colors={GOLD as any} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.scanCtaBg}>
            {scanning ? <ActivityIndicator color={C.onInverse} /> : <Ionicons name="scan-circle" size={26} color={C.onInverse} />}
            <View style={{ flex: 1 }}>
              <Text style={styles.scanCtaTitle}>SCAN LABEL</Text>
              <Text style={styles.scanCtaSub}>Jarvis reads the expiry and adds the supply — no typing.</Text>
            </View>
          </LinearGradient>
        </Pressable>

        {/* VOICE-FIRST — nula ťukania, iba hlas */}
        <Pressable
          testID="pantry-voice"
          onPress={startVoice}
          style={styles.voiceCta}
        >
          <Ionicons name="mic-circle" size={26} color={C.brand} />
          <View style={{ flex: 1 }}>
            <Text style={styles.voiceCtaTitle}>DICTATE TO JARVIS</Text>
              <Text style={styles.voiceCtaSub}>“Three cans of beans in bunker A.” — done.</Text>
          </View>
        </Pressable>

        {/* Category chip picker for the next scan */}
        <Text style={styles.section}>CATEGORY FOR NEXT SCAN</Text>
        <View style={styles.catRow}>
          {CATS.map((c) => (
            <Pressable
              key={c.key}
              testID={`pantry-cat-${c.key}`}
              onPress={() => setScanCat(c.key)}
              style={[styles.catChip, scanCat === c.key && styles.catChipActive]}
            >
              <Ionicons name={c.icon as any} size={13} color={scanCat === c.key ? C.onInverse : C.brand} />
              <Text style={[styles.catChipText, scanCat === c.key && { color: C.onInverse }]}>{c.label}</Text>
            </Pressable>
          ))}
        </View>
      </ScrollView>

      {/* VOICE OVERLAY — the "listening…" modal */}
      <Modal visible={voiceOpen} transparent animationType="fade" onRequestClose={() => setVoiceOpen(false)}>
        <View style={styles.voiceBg}>
          <View style={styles.voiceCard}>
            <View style={styles.voiceRing}>
              <Ionicons name="mic" size={64} color={C.brand} />
            </View>
            <Text style={styles.voiceTitle}>{voiceBusy ? 'RECOGNIZING…' : 'SPEAK'}</Text>
            <Text style={styles.voiceHint}>
              {voiceBusy ? 'Jarvis understands your language.' : 'E.g.: “Three cans of beans in bunker A.”'}
            </Text>
            {!!voiceHeard && <Text testID="pantry-voice-heard" style={styles.voiceHeard}>✓ {voiceHeard}</Text>}
            {!voiceBusy && (
              <Pressable testID="pantry-voice-stop" onPress={stopVoice} style={styles.voiceStopBtn}>
                <Ionicons name="stop-circle" size={22} color={C.onInverse} />
                <Text style={styles.voiceStopText}>FINISH · SAVE</Text>
              </Pressable>
            )}
            {voiceBusy && <ActivityIndicator color={C.brand} size="large" />}
            <Pressable onPress={() => { try { voiceRecorder.stop(); } catch {}; setVoiceOpen(false); }} hitSlop={12}>
              <Text style={styles.voiceCancel}>Cancel</Text>
            </Pressable>
          </View>
        </View>
      </Modal>

      {/* Manual add modal */}
      <Modal visible={addOpen} transparent animationType="slide" onRequestClose={() => setAddOpen(false)}>
        <View style={styles.modalBg}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>ADD SUPPLY MANUALLY</Text>
            <TextInput testID="pantry-name" value={newName} onChangeText={setNewName} placeholder="Name (Can of beans)" placeholderTextColor="#999" style={styles.input} />
            <View style={styles.catRow}>
              {CATS.map((c) => (
                <Pressable key={c.key} onPress={() => setNewCat(c.key)} style={[styles.catChip, newCat === c.key && styles.catChipActive]}>
                  <Ionicons name={c.icon as any} size={12} color={newCat === c.key ? C.onInverse : C.brand} />
                  <Text style={[styles.catChipText, newCat === c.key && { color: C.onInverse }]}>{c.label}</Text>
                </Pressable>
              ))}
            </View>
            <TextInput testID="pantry-exp" value={newExp} onChangeText={setNewExp} placeholder="Expiry date (2028-03-15)" placeholderTextColor="#999" style={styles.input} maxLength={10} />
            <TextInput testID="pantry-qty" value={newQty} onChangeText={setNewQty} placeholder="Quantity" placeholderTextColor="#999" keyboardType="number-pad" style={styles.input} maxLength={4} />
            <TextInput testID="pantry-loc" value={newLoc} onChangeText={setNewLoc} placeholder="Miesto (Bunker A · polica 2)" placeholderTextColor="#999" style={styles.input} maxLength={80} />
            <View style={{ flexDirection: 'row', gap: S.md, marginTop: S.md }}>
              <Pressable onPress={() => setAddOpen(false)} style={[styles.mBtn, styles.mBtnGhost]}>
                <Text style={styles.mBtnGhostText}>Cancel</Text>
              </Pressable>
              <Pressable testID="pantry-save" onPress={save} style={[styles.mBtn, styles.mBtnPrimary]}>
                <Text style={styles.mBtnPrimaryText}>ADD</Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.brand, fontWeight: '900', fontSize: 13, letterSpacing: 2.5 },
  alertRow: { flexDirection: 'row', gap: 8, alignItems: 'center', backgroundColor: C.brand, paddingHorizontal: S.lg, paddingVertical: S.md, marginHorizontal: S.lg, borderRadius: R.md, marginBottom: S.md },
  alertText: { flex: 1, color: C.onInverse, fontWeight: '900', fontSize: 12, letterSpacing: 0.3 },
  chipRow: { flexDirection: 'row', gap: 6, paddingHorizontal: S.lg, marginBottom: S.md, flexWrap: 'wrap' },
  chip: { flexDirection: 'row', gap: 4, alignItems: 'center', borderWidth: 1, borderRadius: R.pill, paddingHorizontal: 10, paddingVertical: 5, backgroundColor: C.surface2 },
  chipDot: { width: 8, height: 8, borderRadius: 4 },
  chipText: { color: C.onS3, fontSize: 9, letterSpacing: 1, fontWeight: '900' },
  chipCount: { color: C.brand, fontWeight: '900', fontSize: 12 },
  empty: { alignItems: 'center', paddingVertical: 60, gap: S.md },
  emptyText: { color: C.brand, letterSpacing: 2, fontWeight: '900', fontSize: 12 },
  emptyHint: { color: C.info, fontSize: 11 },
  card: { flexDirection: 'row', gap: S.md, alignItems: 'center', backgroundColor: C.surface2, borderRadius: R.md, padding: S.md, marginBottom: S.sm, borderWidth: 1, borderColor: C.border },
  itemIcon: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center', borderWidth: 1.5 },
  itemName: { color: C.fg, fontWeight: '900', fontSize: 14 },
  itemMeta: { color: C.onS3, fontSize: 11, marginTop: 2 },
  itemFooter: { flexDirection: 'row', gap: 8, alignItems: 'center', marginTop: 6 },
  miniPill: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 10, borderWidth: 1 },
  miniPillText: { fontSize: 8, letterSpacing: 1, fontWeight: '900' },
  itemDays: { color: C.brand, fontWeight: '900', fontSize: 12 },
  scanCta: { borderRadius: R.md, overflow: 'hidden', marginTop: S.lg, shadowColor: C.brand, shadowOpacity: 0.4, shadowRadius: 14, shadowOffset: { width: 0, height: 4 }, elevation: 8 },
  scanCtaBg: { flexDirection: 'row', alignItems: 'center', gap: S.md, padding: S.md, minHeight: 64 },
  scanCtaTitle: { color: C.onInverse, fontWeight: '900', fontSize: 14, letterSpacing: 2 },
  scanCtaSub: { color: 'rgba(255,255,255,0.9)', fontSize: 11, lineHeight: 15, marginTop: 2 },
  section: { color: C.brand, fontWeight: '900', fontSize: 10, letterSpacing: 2, marginTop: S.xl, marginBottom: S.sm },
  catRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  catChip: { flexDirection: 'row', gap: 4, alignItems: 'center', borderWidth: 1, borderColor: C.brand, borderRadius: R.pill, paddingHorizontal: 10, paddingVertical: 6, backgroundColor: C.surface2 },
  catChipActive: { backgroundColor: C.brand },
  catChipText: { color: C.brand, fontSize: 10, letterSpacing: 0.5, fontWeight: '900' },
  modalBg: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  modalCard: { backgroundColor: C.surface2, borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: S.xl, gap: S.sm },
  modalTitle: { color: C.brand, fontWeight: '900', fontSize: 13, letterSpacing: 2, marginBottom: S.sm },
  input: { borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.sm, padding: S.md, fontSize: 14, color: C.fg, backgroundColor: C.bg },
  mBtn: { flex: 1, minHeight: 52, borderRadius: R.pill, alignItems: 'center', justifyContent: 'center' },
  mBtnGhost: { borderWidth: 1.5, borderColor: C.border },
  mBtnGhostText: { color: C.info, fontWeight: '900', fontSize: 12, letterSpacing: 1 },
  mBtnPrimary: { backgroundColor: C.brand },
  mBtnPrimaryText: { color: C.onInverse, fontWeight: '900', fontSize: 12, letterSpacing: 2 },
  voiceCta: { flexDirection: 'row', gap: S.md, alignItems: 'center', backgroundColor: C.surface2, borderRadius: R.md, padding: S.md, marginTop: S.md, borderWidth: 1.5, borderColor: C.brand, minHeight: 64 },
  voiceCtaTitle: { color: C.brand, fontWeight: '900', fontSize: 13, letterSpacing: 2 },
  voiceCtaSub: { color: C.info, fontSize: 11, lineHeight: 15, marginTop: 3 },
  voiceBg: { flex: 1, backgroundColor: 'rgba(6,6,10,0.95)', alignItems: 'center', justifyContent: 'center', padding: S.xl },
  voiceCard: { alignSelf: 'stretch', backgroundColor: C.surface2, borderRadius: R.lg, borderWidth: 2, borderColor: C.brand, padding: S.xl, gap: S.md, alignItems: 'center' },
  voiceRing: { width: 120, height: 120, borderRadius: 60, borderWidth: 2, borderColor: C.brand, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(212,175,55,0.08)' },
  voiceTitle: { color: C.brand, fontWeight: '900', fontSize: 16, letterSpacing: 3 },
  voiceHint: { color: C.info, fontSize: 12, lineHeight: 17, textAlign: 'center' },
  voiceHeard: { color: C.brand, fontSize: 14, fontWeight: '900', textAlign: 'center', marginTop: S.md },
  voiceStopBtn: { flexDirection: 'row', gap: 8, alignItems: 'center', backgroundColor: C.brand, borderRadius: R.pill, minHeight: 54, paddingHorizontal: S.xxl, marginTop: S.md },
  voiceStopText: { color: C.onInverse, fontWeight: '900', fontSize: 13, letterSpacing: 2 },
  voiceCancel: { color: C.info, fontSize: 12, marginTop: S.sm, textDecorationLine: 'underline' },
});
