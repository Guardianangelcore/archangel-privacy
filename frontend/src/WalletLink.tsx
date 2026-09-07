/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// WALLET LINK — one-tap wallet connection without WalletConnect: open MetaMask / Coinbase Wallet
// (deep link → app, or the store when not installed), then paste the copied 0x… address from the
// clipboard with a single tap. Works in Expo Go and on web.
import React, { useState } from 'react';
import { View, Text, StyleSheet, Pressable, TextInput, Linking, Platform } from 'react-native';
import * as Clipboard from 'expo-clipboard';
import Ionicons from '@react-native-vector-icons/ionicons';
import { C, S, R } from './theme';
import { GoldButton, tap } from './ui/glass';
import { useI18n } from './i18n-context';

export const EVM_ADDRESS_RE = /^0x[0-9a-fA-F]{40}$/;
const FIND_ADDRESS_RE = /0x[0-9a-fA-F]{40}/;

// Wallet apps: native scheme first, universal link as fallback (opens the app when installed,
// otherwise the App Store / Play listing).
const WALLETS = [
  { id: 'metamask', label: 'wallet_link.open_metamask', icon: 'flame-outline' as const, scheme: 'metamask://', universal: 'https://metamask.app.link/' },
  { id: 'coinbase', label: 'wallet_link.open_coinbase', icon: 'wallet-outline' as const, scheme: 'cbwallet://', universal: 'https://go.cb-w.com/' },
];

async function openWallet(w: typeof WALLETS[number]) {
  tap('light');
  if (Platform.OS === 'web') { Linking.openURL(w.universal); return; }
  try { await Linking.openURL(w.scheme); }
  catch { Linking.openURL(w.universal).catch(() => {}); }
}

type Props = {
  value: string;
  onChange: (address: string) => void;
  onLink: () => void;
  busy?: boolean;
  testID?: string;
};

export function WalletLink({ value, onChange, onLink, busy, testID = 'wl' }: Props) {
  const { t: tt } = useI18n();
  const [note, setNote] = useState<{ ok: boolean; text: string } | null>(null);

  const paste = async () => {
    tap('medium');
    try {
      const raw = await Clipboard.getStringAsync();
      const m = FIND_ADDRESS_RE.exec(raw || '');
      if (!m) { setNote({ ok: false, text: tt('wallet_link.no_address') }); return; }
      onChange(m[0]);
      setNote({ ok: true, text: tt('wallet_link.pasted') });
    } catch { setNote({ ok: false, text: tt('wallet_link.no_address') }); }
  };

  const valid = EVM_ADDRESS_RE.test(value.trim());
  return (
    <View testID={testID} style={st.root}>
      <Text style={st.title}>{tt('wallet_link.title')}</Text>
      <Text style={st.hint}>{tt('wallet_link.hint')}</Text>
      <View style={st.row}>
        {WALLETS.map(w => (
          <Pressable key={w.id} testID={`${testID}-${w.id}`} onPress={() => openWallet(w)} style={st.walletBtn}>
            <Ionicons name={w.icon} size={18} color={C.brand} />
            <Text style={st.walletText}>{tt(w.label)}</Text>
            <Ionicons name="open-outline" size={13} color={C.info} />
          </Pressable>
        ))}
      </View>
      <Pressable testID={`${testID}-paste`} onPress={paste} style={st.pasteBtn}>
        <Ionicons name="clipboard-outline" size={18} color={C.onInverse} />
        <Text style={st.pasteText}>{tt('wallet_link.paste')}</Text>
      </Pressable>
      <Text style={st.manual}>{tt('wallet_link.manual')}</Text>
      <TextInput
        testID={`${testID}-addr`}
        value={value}
        onChangeText={(v) => { onChange(v); setNote(null); }}
        placeholder="0x…"
        placeholderTextColor={C.info}
        autoCapitalize="none"
        autoCorrect={false}
        style={[st.input, valid && st.inputOk]}
      />
      {!!note && <Text testID={`${testID}-note`} style={[st.note, { color: note.ok ? C.accent : C.error }]}>{note.text}</Text>}
      <GoldButton testID={`${testID}-link`} title={tt('wallet_link.link')} small onPress={onLink} loading={!!busy} disabled={!valid} />
    </View>
  );
}

const st = StyleSheet.create({
  root: { gap: S.sm },
  title: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 1.5 },
  hint: { color: C.info, fontSize: 11.5, lineHeight: 17 },
  row: { flexDirection: 'row', gap: S.sm },
  walletBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, minHeight: 48, borderWidth: 1.5, borderColor: 'rgba(212,175,55,0.5)', borderRadius: R.sm, backgroundColor: 'rgba(212,175,55,0.06)', paddingHorizontal: S.sm },
  walletText: { color: C.fg, fontWeight: '800', fontSize: 12 },
  pasteBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, minHeight: 48, borderRadius: R.sm, backgroundColor: C.brand },
  pasteText: { color: C.onInverse, fontWeight: '900', fontSize: 12, letterSpacing: 1.5 },
  manual: { color: C.info, fontSize: 10.5, textAlign: 'center', letterSpacing: 0.5 },
  input: { minHeight: 46, color: C.fg, paddingHorizontal: S.md, borderWidth: 1, borderColor: C.border, borderRadius: R.sm, backgroundColor: C.surface2, fontSize: 13 },
  inputOk: { borderColor: C.accent },
  note: { fontSize: 11.5, fontWeight: '700' },
});
