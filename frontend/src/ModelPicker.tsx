// AI MODEL PICKER — ChatGPT model that powers Jarvis (Settings chips + Jarvis pill/sheet share this).
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, Modal, ActivityIndicator } from 'react-native';
import Ionicons from '@react-native-vector-icons/ionicons';
import { useRouter } from 'expo-router';
import { api, errMsg } from '@/src/api';
import { useAuth } from '@/src/auth';
import { useI18n } from '@/src/i18n-context';
import { tap } from '@/src/ui/glass';
import { C, S, R } from '@/src/theme';

export type AiModel = {
  id: string; name: string; tag: string; min_tier: string; min_tier_name: string;
  locked: boolean; active: boolean; speed: number; depth: number;
};
export type AiModels = { provider: string; default: string; selected: string; tier: string; models: AiModel[] };

const TAG_KEY: Record<string, string> = {
  'gpt-5.4-mini': 'ai_models.tag_mini', 'gpt-5.4': 'ai_models.tag_54',
  'gpt-5.6-luna': 'ai_models.tag_luna', 'gpt-5.6-terra': 'ai_models.tag_terra',
};

export function useAiModels() {
  const { refresh } = useAuth();
  const [data, setData] = useState<AiModels | null>(null);
  const [msg, setMsg] = useState('');
  const [locked, setLocked] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const load = useCallback(() => api<AiModels>('/ai/models').then(setData).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  const select = useCallback(async (id: string) => {
    setBusy(id); setMsg(''); setLocked(false);
    try {
      await api('/ai/models/select', { method: 'PUT', body: JSON.stringify({ model: id }) });
      await load();
      refresh?.();
      return true;
    } catch (e) {
      const m = errMsg(e);
      setLocked(/_required|^402/.test(String((e as Error)?.message || '')));
      setMsg(m);
      return false;
    } finally { setBusy(null); }
  }, [load, refresh]);
  return { data, select, busy, msg, locked, reload: load };
}

export function modelTag(m: AiModel, tt: (k: string) => string): string {
  const k = TAG_KEY[m.id];
  const s = k ? tt(k) : '';
  return s && s !== k ? s : m.tag;
}

/** Settings — one card per model with name, tag and lock state. */
export function ModelChips({ testIdPrefix = 'prof-model' }: { testIdPrefix?: string }) {
  const { t: tt } = useI18n();
  const router = useRouter();
  const { data, select, busy, msg, locked } = useAiModels();
  if (!data) return <ActivityIndicator color={C.brand} style={{ marginVertical: S.md }} />;
  return (
    <View>
      <View style={st.wrap}>
        {data.models.map(m => {
          const on = m.id === data.selected;
          return (
            <Pressable key={m.id} testID={`${testIdPrefix}-${m.id}`} onPress={() => { tap('light'); select(m.id); }}
              style={[st.card, on && st.cardOn, m.locked && st.cardLocked]} disabled={busy !== null}>
              <View style={st.cardHead}>
                <Ionicons name={m.locked ? 'lock-closed' : on ? 'checkmark-circle' : 'sparkles-outline'} size={16} color={on ? C.onInverse : m.locked ? C.onS3 : C.brand} />
                <Text style={[st.name, on && { color: C.onInverse }]}>{m.name}</Text>
                {busy === m.id && <ActivityIndicator size="small" color={on ? C.onInverse : C.brand} />}
              </View>
              <Text style={[st.tag, on && { color: C.onInverse }]}>{modelTag(m, tt)}</Text>
              {m.locked && <Text style={st.lock}>{tt('ai_models.locked').replace('{0}', m.min_tier_name)}</Text>}
            </Pressable>
          );
        })}
      </View>
      {!!msg && (
        <View style={st.msgRow}>
          <Text testID={`${testIdPrefix}-msg`} style={st.msg}>{msg}</Text>
          {locked && (
            <Pressable testID={`${testIdPrefix}-upgrade`} onPress={() => router.push('/store')} style={st.upBtn}>
              <Text style={st.upText}>{tt('ai_models.upgrade')}</Text>
            </Pressable>
          )}
        </View>
      )}
    </View>
  );
}

/** Jarvis — compact pill showing the active model; tap opens a sheet to switch. */
export function ModelPill({ accent = C.brand }: { accent?: string }) {
  const { t: tt } = useI18n();
  const router = useRouter();
  const { data, select, busy, msg, locked } = useAiModels();
  const [open, setOpen] = useState(false);
  const cur = data?.models.find(m => m.id === data.selected);
  return (
    <>
      <Pressable testID="jv-model" onPress={() => { tap('light'); setOpen(true); }} style={[st.pill, { borderColor: accent }]} hitSlop={6}>
        <Ionicons name="hardware-chip-outline" size={13} color={accent} />
        <Text style={[st.pillText, { color: accent }]}>{cur?.name || 'GPT'}</Text>
        <Ionicons name="chevron-down" size={12} color={accent} />
      </Pressable>
      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={st.backdrop} onPress={() => setOpen(false)} testID="jv-model-close">
          <Pressable style={st.sheet} onPress={() => {}} testID="jv-model-sheet">
            <Text style={st.sheetTitle}>{tt('ai_models.pick')}</Text>
            {(data?.models || []).map(m => {
              const on = m.id === data?.selected;
              return (
                <Pressable key={m.id} testID={`jv-model-${m.id}`} disabled={busy !== null}
                  onPress={async () => { tap('light'); if (await select(m.id)) setOpen(false); }}
                  style={[st.row, on && st.rowOn]}>
                  <Ionicons name={m.locked ? 'lock-closed' : on ? 'radio-button-on' : 'radio-button-off'} size={18} color={m.locked ? C.onS3 : accent} />
                  <View style={{ flex: 1 }}>
                    <Text style={st.rowName}>{m.name}</Text>
                    <Text style={st.rowTag}>{m.locked ? tt('ai_models.locked').replace('{0}', m.min_tier_name) : modelTag(m, tt)}</Text>
                  </View>
                  {busy === m.id && <ActivityIndicator size="small" color={accent} />}
                </Pressable>
              );
            })}
            {!!msg && <Text testID="jv-model-msg" style={st.msg}>{msg}</Text>}
            {locked && (
              <Pressable testID="jv-model-upgrade" onPress={() => { setOpen(false); router.push('/store'); }} style={[st.upBtn, { alignSelf: 'stretch', alignItems: 'center' }]}>
                <Text style={st.upText}>{tt('ai_models.upgrade')}</Text>
              </Pressable>
            )}
          </Pressable>
        </Pressable>
      </Modal>
    </>
  );
}

const st = StyleSheet.create({
  wrap: { gap: S.sm, marginBottom: S.sm },
  card: { borderWidth: 1.5, borderColor: C.borderStrong, backgroundColor: C.bg, padding: S.md, minHeight: 56, gap: 4 },
  cardOn: { backgroundColor: C.inverse, borderColor: C.inverse },
  cardLocked: { opacity: 0.75 },
  cardHead: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  name: { fontWeight: '900', letterSpacing: 0.8, color: C.fg, fontSize: 13, flex: 1 },
  tag: { color: C.onS3, fontSize: 11 },
  lock: { color: C.brand, fontSize: 10.5, fontWeight: '800', letterSpacing: 0.5 },
  msgRow: { flexDirection: 'row', alignItems: 'center', gap: S.sm, marginBottom: S.sm },
  msg: { color: C.error, fontSize: 11, flex: 1, marginTop: 4 },
  upBtn: { backgroundColor: C.brand, paddingHorizontal: S.md, paddingVertical: 10, borderRadius: R.pill, minHeight: 40, justifyContent: 'center' },
  upText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 11 },
  pill: { flexDirection: 'row', alignItems: 'center', gap: 5, borderWidth: 1, borderRadius: R.pill, paddingHorizontal: 10, minHeight: 32, alignSelf: 'center', marginTop: S.sm },
  pillText: { fontWeight: '900', fontSize: 10.5, letterSpacing: 0.8 },
  backdrop: { flex: 1, backgroundColor: C.surface3, justifyContent: 'flex-end' },
  sheet: { backgroundColor: C.bg, borderTopLeftRadius: R.lg, borderTopRightRadius: R.lg, padding: S.lg, paddingBottom: S.xl + 8, gap: S.sm, borderTopWidth: 1, borderColor: C.border },
  sheetTitle: { color: C.fg, fontWeight: '900', letterSpacing: 1.2, fontSize: 12, marginBottom: 4 },
  row: { flexDirection: 'row', alignItems: 'center', gap: S.md, paddingVertical: 10, paddingHorizontal: S.sm, borderRadius: R.md, minHeight: 52 },
  rowOn: { backgroundColor: C.surface2 },
  rowName: { color: C.fg, fontWeight: '800', fontSize: 14 },
  rowTag: { color: C.onS3, fontSize: 11, marginTop: 2 },
});
