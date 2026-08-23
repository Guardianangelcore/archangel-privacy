import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api } from './api';
import { C, S } from './theme';
import { t, Lang } from './i18n';

type Props = { module: string; buildContext: () => string; lang: Lang };

export default function JarvisAdvice({ module, buildContext, lang }: Props) {
  const [advice, setAdvice] = useState('');
  const [busy, setBusy] = useState(false);

  const ask = async () => {
    setBusy(true);
    try {
      const res: any = await api('/ai/advice', {
        method: 'POST',
        body: JSON.stringify({ module, context: buildContext(), language: lang }),
      });
      setAdvice(res.advice);
    } catch (e) { console.log('advice err', e); } finally { setBusy(false); }
  };

  return (
    <View style={styles.wrap}>
      <Pressable testID={`jarvis-advice-${module}`} onPress={ask} disabled={busy} style={styles.btn}>
        {busy ? <ActivityIndicator color={C.brand} size="small" /> : <Ionicons name="sparkles" size={16} color={C.brand} />}
        <Text style={styles.btnText}>{t('jarvis_advice', lang).toUpperCase()}</Text>
      </Pressable>
      {advice ? (
        <View testID={`jarvis-advice-out-${module}`} style={styles.card}>
          <Text style={styles.cardLabel}>JARVIS</Text>
          <Text style={styles.cardText}>{advice}</Text>
          <Text style={styles.disclosure}>⚠ {t('ai_disclosure', lang)}</Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginTop: S.md },
  btn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, borderWidth: 2, borderColor: C.brand, paddingVertical: S.md, backgroundColor: C.brandTer },
  btnText: { color: C.brand, fontWeight: '900', letterSpacing: 1.5, fontSize: 12 },
  card: { marginTop: S.sm, borderWidth: 1.5, borderColor: C.brand, padding: S.md },
  cardLabel: { fontSize: 10, letterSpacing: 2, color: C.brand, fontWeight: '900', marginBottom: 4 },
  cardText: { color: C.fg, fontSize: 14, lineHeight: 21 },
  disclosure: { marginTop: 8, fontSize: 8, letterSpacing: 0.5, color: C.onS3, fontWeight: '800' },
});
