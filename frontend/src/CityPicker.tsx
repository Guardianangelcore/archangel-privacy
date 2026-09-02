/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// CityPicker — bottom-sheet chooser for manual city override + language suggestion banner.
// Used from Profile > Cestovný režim when GPS is unavailable / user wants to override.
import React, { useCallback, useEffect, useState } from 'react';
import { Modal, Pressable, View, Text, StyleSheet, ScrollView, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api } from './api';
import { C, S, R } from './theme';
import { useI18n } from '@/src/i18n-context';

type City = { city: string; country: string; lang: string };

export function CityPicker({ visible, onClose, onPicked }: {
  visible: boolean;
  onClose: () => void;
  onPicked?: (result: any) => void;
}) {
  const { t: tt, tx } = useI18n();
  const [cities, setCities] = useState<City[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState('');
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    if (!visible) return;
    setLoading(true); setErr('');
    try {
      const c: any = await api('/geo/context');
      setCities(c.supported_cities || []);
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setLoading(false); }
  }, [visible]);

  useEffect(() => { load(); }, [load]);

  const pick = async (city: string) => {
    setBusy(city); setErr('');
    try {
      const r: any = await api('/geo/set-city', { method: 'POST', body: JSON.stringify({ city }) });
      onPicked?.(r);
      onClose();
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(''); }
  };

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <Pressable style={styles.overlay} onPress={onClose}>
        <Pressable style={styles.sheet} onPress={() => {}}>
          <View style={styles.handle} />
          <Text style={styles.title}>{tt('c_CityPicker.manual_city_selection')}</Text>
          <Text style={styles.sub}>{tt('c_CityPicker.gps_and_ip_were_blocked_or_inaccurat')}</Text>
          {!!err && <Text style={styles.err}>{err}</Text>}
          {loading ? <ActivityIndicator color={C.brand} style={{ marginVertical: S.lg }} /> : (
            <ScrollView style={{ maxHeight: 380 }} contentContainerStyle={{ paddingBottom: S.md }}>
              {cities.map(c => (
                <Pressable
                  key={c.city}
                  testID={`cp-city-${c.city}`}
                  onPress={() => pick(c.city)}
                  disabled={!!busy}
                  style={({ pressed }) => [styles.row, pressed && { backgroundColor: C.surface3 }]}
                >
                  <View style={{ flex: 1 }}>
                    <Text style={styles.rowCity}>{c.city}</Text>
                    <Text style={styles.rowSub}>{c.country} · {c.lang.toUpperCase()}</Text>
                  </View>
                  {busy === c.city ? <ActivityIndicator size="small" color={C.brand} /> :
                    <Ionicons name="location-outline" size={18} color={C.info} />}
                </Pressable>
              ))}
            </ScrollView>
          )}
          <Pressable testID="cp-cancel" onPress={onClose} style={styles.cancel}>
            <Text style={styles.cancelText}>{tt('c_CityPicker.cancel')}</Text>
          </Pressable>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

export function LanguageSuggestionBanner({ suggestion, onAccept, onDismiss }: {
  suggestion: { from: string; to: string; city: string; country: string } | null;
  onAccept: () => void;
  onDismiss: () => void;
}) {
  const { t: tt, tx } = useI18n();
  if (!suggestion) return null;
  const LANG_LABEL: Record<string, string> = {
    sk: 'slovenčina', cs: 'čeština', en: 'English', de: 'Deutsch', pl: 'polski',
    hu: 'magyar', fr: 'français', it: 'italiano', es: 'español', uk: 'українська',
  };
  return (
    <View testID="lang-suggestion" style={styles.bannerBox}>
      <Ionicons name="language" size={20} color={C.brand} />
      <View style={{ flex: 1 }}>
        <Text style={styles.bannerTitle}>{tt('c_CityPicker.you_crossed_a_border')} {suggestion.country}</Text>
        <Text style={styles.bannerSub}>
          {tt('c_CityPicker.switch_the_app_from')} {LANG_LABEL[suggestion.from] || suggestion.from} {tt('c_CityPicker.to')}{' '}
          <Text style={{ fontWeight: '900' }}>{LANG_LABEL[suggestion.to] || suggestion.to}</Text>?
        </Text>
      </View>
      <View style={{ gap: 6 }}>
        <Pressable testID="lang-suggest-accept" onPress={onAccept} style={styles.bannerAccept}>
          <Text style={styles.bannerAcceptText}>{tt('c_CityPicker.yes')}</Text>
        </Pressable>
        <Pressable testID="lang-suggest-dismiss" onPress={onDismiss} style={styles.bannerDismiss}>
          <Text style={styles.bannerDismissText}>{tt('c_CityPicker.nie')}</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: C.surface2, borderTopLeftRadius: R.lg, borderTopRightRadius: R.lg, padding: S.xl, paddingBottom: 34, borderWidth: 1, borderColor: C.borderStrong },
  handle: { alignSelf: 'center', width: 44, height: 5, borderRadius: 3, backgroundColor: C.surface3, marginBottom: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 2, fontSize: 13 },
  sub: { color: C.info, fontSize: 12, marginTop: 4, marginBottom: S.md, lineHeight: 17 },
  err: { color: C.error, fontSize: 12, marginBottom: S.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: S.md, paddingVertical: S.md, borderBottomWidth: 1, borderColor: C.border },
  rowCity: { color: C.fg, fontWeight: '800', fontSize: 15 },
  rowSub: { color: C.info, fontSize: 11, marginTop: 2 },
  cancel: { marginTop: S.md, alignItems: 'center', justifyContent: 'center', minHeight: 48, borderWidth: 1.5, borderColor: C.border, borderRadius: R.pill },
  cancelText: { color: C.info, fontWeight: '900', letterSpacing: 2, fontSize: 12 },
  bannerBox: { flexDirection: 'row', alignItems: 'center', gap: S.md, borderWidth: 1.5, borderColor: C.brand, backgroundColor: C.brandTer, padding: S.md, borderRadius: R.md, marginBottom: S.md },
  bannerTitle: { color: C.fg, fontWeight: '900', fontSize: 11, letterSpacing: 1.5 },
  bannerSub: { color: C.onS3, fontSize: 12, marginTop: 3, lineHeight: 16 },
  bannerAccept: { backgroundColor: C.brand, paddingHorizontal: S.md, paddingVertical: 6, borderRadius: R.sm, minWidth: 54, alignItems: 'center' },
  bannerAcceptText: { color: C.onInverse, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  bannerDismiss: { paddingHorizontal: S.md, paddingVertical: 6, borderRadius: R.sm, borderWidth: 1, borderColor: C.border, minWidth: 54, alignItems: 'center' },
  bannerDismissText: { color: C.info, fontWeight: '800', fontSize: 11, letterSpacing: 1 },
});
