/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// EU AI Act Article 50 — global liability waiver footer (applicable 2 Aug 2026)
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { C, S } from './theme';
import { t, Lang } from './i18n';

export default function Art50({ lang = 'sk' }: { lang?: Lang }) {
  return (
    <View testID="art50-waiver" style={st.box}>
      <Text style={st.txt}>{t('art50_waiver', lang)}</Text>
    </View>
  );
}

const st = StyleSheet.create({
  box: { marginTop: S.xl, borderWidth: 1, borderColor: C.border, padding: S.md, backgroundColor: C.surface2 },
  txt: { color: C.info, fontSize: 9, letterSpacing: 0.5, lineHeight: 14, fontWeight: '700' },
});
