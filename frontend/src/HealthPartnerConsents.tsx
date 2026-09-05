// HEALTH PARTNER CONSENTS — a partner may write into my record ONLY after I link it here (UHP ingest → 403 otherwise).
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, ActivityIndicator } from 'react-native';
import Ionicons from '@react-native-vector-icons/ionicons';
import { api, errMsg } from '@/src/api';
import { useI18n } from '@/src/i18n-context';
import { tap } from '@/src/ui/glass';
import { C, S, R } from '@/src/theme';

type Partner = { partner_id: string; org_name: string; org_type: string; country: string };

export function HealthPartnerConsents() {
  const { t: tt } = useI18n();
  const [data, setData] = useState<{ consents: { partner_id: string }[]; partners: Partner[] } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState('');
  const load = useCallback(() => api<any>('/uhp/consents').then(setData).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  if (!data) return <ActivityIndicator color={C.brand} style={{ marginVertical: S.md }} />;
  const linked = new Set(data.consents.map(c => c.partner_id));
  const toggle = async (p: Partner) => {
    tap('light'); setBusy(p.partner_id); setMsg('');
    try {
      if (linked.has(p.partner_id)) await api(`/uhp/consents/${p.partner_id}`, { method: 'DELETE' });
      else await api('/uhp/consents', { method: 'POST', body: JSON.stringify({ partner_id: p.partner_id }) });
      await load();
    } catch (e) { setMsg(errMsg(e)); } finally { setBusy(null); }
  };
  return (
    <View style={st.wrap}>
      {data.partners.length === 0 && <Text style={st.empty}>{tt('uhp.no_partners')}</Text>}
      {data.partners.map(p => {
        const on = linked.has(p.partner_id);
        return (
          <Pressable key={p.partner_id} testID={`uhp-consent-${p.partner_id}`} onPress={() => toggle(p)} disabled={busy !== null} style={[st.row, on && st.rowOn]}>
            <Ionicons name={on ? 'checkmark-circle' : 'ellipse-outline'} size={18} color={on ? C.onInverse : C.brand} />
            <View style={{ flex: 1 }}>
              <Text style={[st.name, on && { color: C.onInverse }]}>{p.org_name}</Text>
              <Text style={[st.sub, on && { color: C.onInverse }]}>{p.org_type} · {p.country} · {on ? tt('uhp.linked') : tt('uhp.not_linked')}</Text>
            </View>
            {busy === p.partner_id && <ActivityIndicator size="small" color={on ? C.onInverse : C.brand} />}
          </Pressable>
        );
      })}
      {!!msg && <Text style={st.msg}>{msg}</Text>}
    </View>
  );
}

const st = StyleSheet.create({
  wrap: { gap: S.sm, marginBottom: S.sm },
  empty: { color: C.info, fontSize: 11.5 },
  row: { flexDirection: 'row', alignItems: 'center', gap: S.sm, borderWidth: 1.5, borderColor: C.borderStrong, padding: S.md, minHeight: 56, backgroundColor: C.bg, borderRadius: R.sm },
  rowOn: { backgroundColor: C.inverse, borderColor: C.inverse },
  name: { color: C.fg, fontWeight: '900', fontSize: 13, letterSpacing: 0.5 },
  sub: { color: C.onS3, fontSize: 11, marginTop: 2 },
  msg: { color: C.error, fontSize: 11 },
});
