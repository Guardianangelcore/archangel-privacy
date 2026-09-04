/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// CHOOSE LANGUAGE — step 1 of the entry flow. A standalone screen: nothing else on it.
// Language → Login/Register → Who uses the app → Spider Hub.
import React from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useI18n } from '@/src/i18n-context';
import { LANG_NAMES, Lang } from '@/src/i18n';
import { C, S } from '@/src/theme';
import { tap } from '@/src/ui/glass';
import { markLangChosen } from '@/src/entry-flow';

export default function ChooseLanguage() {
  const router = useRouter();
  const { lang, setLang, t } = useI18n();
  const pick = async (l: Lang) => {
    tap('light');
    setLang(l);
    markLangChosen(l);
    router.replace('/login');
  };
  return (
    <SafeAreaView testID="choose-language-screen" style={st.root}>
      <ScrollView contentContainerStyle={st.body}>
        <Text style={st.hero}>ARCHANGEL <Text style={{ color: C.brand }}>OS</Text></Text>
        <Text style={st.label}>{t('choose_language').toUpperCase()}</Text>
        <View style={st.grid}>
          {(Object.keys(LANG_NAMES) as Lang[]).map(l => {
            const active = l === lang;
            return (
              <Pressable key={l} testID={`lang-${l}`} onPress={() => pick(l)} style={[st.chip, active && st.chipActive]}>
                <Text style={[st.chipText, active && st.chipTextActive]}>{LANG_NAMES[l]}</Text>
              </Pressable>
            );
          })}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  body: { flexGrow: 1, justifyContent: 'center', padding: S.xl, gap: S.lg },
  hero: { color: C.fg, fontSize: 30, fontWeight: '900', letterSpacing: 5, textAlign: 'center' },
  label: { color: C.info, fontSize: 11, letterSpacing: 3, textAlign: 'center', marginTop: S.lg },
  grid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', gap: S.sm },
  chip: { minHeight: 52, minWidth: 100, paddingHorizontal: S.lg, justifyContent: 'center', alignItems: 'center', borderWidth: 1.5, borderColor: 'rgba(212,175,55,0.5)' },
  chipActive: { backgroundColor: C.brand, borderColor: C.brand },
  chipText: { color: C.fg, fontWeight: '800', letterSpacing: 1, fontSize: 14 },
  chipTextActive: { color: C.onInverse },
});
