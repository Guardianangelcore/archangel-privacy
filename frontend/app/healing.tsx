/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// KOLOTOČ UZDRAVENIA — Sovereign Healing Loop: Úraz → Peniaze hneď → Doktor → Papiere → Fyzio
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, ScrollView, Modal, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { api } from '@/src/api';
import { sharePdf } from '@/src/pdf';
import { C, S, R } from '@/src/theme';
import { GlassCard, tap } from '@/src/ui/glass';

const SPECIALTIES = ['Ortopéd', 'Chirurg', 'Zubár', 'Neurológ', 'Kardiológ', 'Fyzioterapia', 'Všeobecný lekár'];
const BODY_PARTS = ['Koleno', 'Rameno', 'Chrbát', 'Ruka', 'Noha', 'Hlava', 'Zub', 'Iné'];

const STEP_ROUTES: Record<string, string> = {
  intake: '/translate', financial_shield: '/insurance', access: '/(tabs)/hunter',
  bureaucracy: '/my-recovery', recovery: '/physio',
};
const STEP_CTA: Record<string, string> = {
  intake: 'Skenovať žiadanku / správu', financial_shield: 'Moje poistky', access: 'Otvoriť Lovca termínov',
  bureaucracy: 'Neschopenka a vychádzky', recovery: 'Spustiť Physio-AI cviky',
};

export default function Healing() {
  const router = useRouter();
  const params = useLocalSearchParams<{ specialty?: string; auto?: string }>();
  const [state, setState] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [wizard, setWizard] = useState(false);
  const [kind, setKind] = useState<'injury' | 'illness'>('injury');
  const [spec, setSpec] = useState('Ortopéd');
  const [part, setPart] = useState('Koleno');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [autoOpened, setAutoOpened] = useState(false);

  const load = useCallback(async () => {
    try { setState(await api('/healing/state')); } catch (e) { console.log(e); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  // MAGIC LENS BRIDGE — a scanned referral pre-fills the specialist and opens the wizard
  useEffect(() => {
    if (loading || autoOpened || params.auto !== '1') return;
    setAutoOpened(true);
    if (state?.active) return;
    const s = String(params.specialty || '').trim();
    if (s) { setSpec(s); setKind('illness'); }
    setWizard(true);
  }, [loading, autoOpened, params.auto, params.specialty, state?.active]);

  const start = async () => {
    setBusy(true); setMsg('');
    try {
      tap('heavy');
      const res: any = await api('/healing/injury-event', {
        method: 'POST',
        body: JSON.stringify({ kind, specialty: spec, body_part: kind === 'injury' ? part : null }),
      });
      setWizard(false);
      setMsg(`⚡ Neural Bus: poistná žiadosť predvyplnená (${res.claim.estimated_total_eur} €) + termín zarezervovaný: ${res.access.slot}`);
      await load();
    } catch (e: any) { setMsg(String(e.message || e)); }
    setBusy(false);
  };

  const submitClaim = async () => {
    if (!state?.claim) return;
    setBusy(true);
    try {
      tap('success');
      await api(`/healing/claim/${state.claim.claim_id}/submit`, { method: 'POST' });
      await load();
    } catch (e: any) { setMsg(String(e.message || e)); }
    setBusy(false);
  };

  const closeLoop = async () => {
    setBusy(true);
    try {
      tap('success');
      const r: any = await api('/healing/close', { method: 'POST' });
      setMsg(r.message);
      await load();
    } catch (e: any) { setMsg(String(e.message || e)); }
    setBusy(false);
  };

  const j = state?.journey;
  const keys: string[] = state?.step_keys || [];
  const meta = state?.steps_meta || {};

  return (
    <SafeAreaView testID="healing-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="healing-back" onPress={() => router.back()} hitSlop={10}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={st.title}>KOLOTOČ UZDRAVENIA</Text>
        <Pressable testID="healing-jarvis" onPress={() => router.push('/jarvis')} hitSlop={10}>
          <Ionicons name="sparkles" size={20} color={C.brand} />
        </Pressable>
      </View>

      {loading ? <ActivityIndicator color={C.brand} style={{ marginTop: 60 }} /> : (
        <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 120 }}>
          {!!msg && <View style={st.msgBox}><Text testID="healing-msg" style={st.msgText}>{msg}</Text></View>}

          {!state?.active ? (
            <View>
              <View style={st.heroIcon}><Ionicons name="sync" size={34} color={C.brand} /></View>
              <Text style={st.heroTitle}>Od úrazu k 100 % fit.{'\n'}Jarvis vybaví všetko.</Text>
              <Text style={st.heroSub}>Jeden zápis spustí celý kolotoč: peniaze z poistky hneď, najskorší doktor v Prahe, neschopenka pod dozorom a fyzio na mieru.</Text>
              <View style={{ marginTop: S.xl, gap: S.sm }}>
                {keys.map((k, i) => (
                  <View key={k} style={st.previewRow}>
                    <Text style={st.previewNum}>{i + 1}</Text>
                    <Ionicons name={meta[k]?.icon as any} size={20} color={C.brand} />
                    <View style={{ flex: 1 }}>
                      <Text style={st.previewTitle}>{meta[k]?.title}</Text>
                      <Text style={st.previewSub}>{meta[k]?.sub}</Text>
                    </View>
                  </View>
                ))}
              </View>
              <Pressable testID="healing-start" onPress={() => { tap('medium'); setWizard(true); }} style={st.startBtn}>
                <Ionicons name="flash" size={20} color={C.onInverse} />
                <Text style={st.startText}>SPUSTIŤ KOLOTOČ</Text>
              </Pressable>
              {!!state?.last_recovered && (
                <Text style={st.lastNote}>✅ Posledný kolotoč dokončený — {state.last_recovered.specialty} ({state.last_recovered.kind_label})</Text>
              )}
            </View>
          ) : (
            <View>
              <GlassCard pad={S.lg} glow>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.md }}>
                  <View style={st.progressRing}>
                    <Text style={st.progressPct}>{state.progress_pct}%</Text>
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={st.jTitle}>{j.kind_label}{j.body_part ? ` · ${j.body_part}` : ''}</Text>
                    <Text style={st.jSub}>{j.specialty} · cesta k 100 % fit</Text>
                  </View>
                </View>
              </GlassCard>

              <View style={{ marginTop: S.lg, gap: S.md }}>
                {keys.map((k, i) => {
                  const status = j.steps?.[k] || 'pending';
                  const done = status === 'done';
                  const action = status === 'action_needed';
                  return (
                    <View key={k} testID={`healing-step-${k}`} style={[st.stepCard, done && st.stepDone, action && st.stepAction]}>
                      <View style={st.stepHead}>
                        <View style={[st.stepBadge, done && { backgroundColor: C.brand }]}>
                          {done ? <Ionicons name="checkmark" size={16} color={C.onInverse} /> : <Text style={st.stepNum}>{i + 1}</Text>}
                        </View>
                        <Ionicons name={meta[k]?.icon as any} size={20} color={done ? C.brand : C.fg} />
                        <View style={{ flex: 1 }}>
                          <Text style={st.stepTitle}>{meta[k]?.title?.toUpperCase()}</Text>
                          <Text style={st.stepSub}>{meta[k]?.sub}</Text>
                        </View>
                        <Text style={[st.stepStatus, done && { color: C.brand }, action && { color: C.warn }]}>
                          {done ? 'HOTOVO' : action ? 'DOPLNIŤ' : 'ČAKÁ'}
                        </Text>
                      </View>

                      {k === 'financial_shield' && !!state.claim && (
                        <View style={st.claimBox}>
                          <Text style={st.claimTitle}>💶 POISTNÁ ŽIADOSŤ — PENIAZE HNEĎ</Text>
                          <Text style={st.claimLine}>Poisťovňa: <Text style={st.claimVal}>{state.claim.provider}</Text></Text>
                          <Text style={st.claimLine}>Denná dávka: <Text style={st.claimVal}>{state.claim.daily_benefit_eur} € / deň</Text></Text>
                          <Text style={st.claimLine}>Odhad spolu (21 dní): <Text style={st.claimVal}>{state.claim.estimated_total_eur} €</Text></Text>
                          <Text style={st.claimLine}>Stav: <Text style={[st.claimVal, { color: state.claim.status === 'submitted' ? C.brand : C.warn }]}>
                            {state.claim.status === 'prefilled' ? 'PREDVYPLNENÁ — čaká na odoslanie' : state.claim.status === 'submitted' ? 'ODOSLANÁ POISŤOVNI ✓' : state.claim.status.toUpperCase()}</Text></Text>
                          {state.claim.status === 'prefilled' && (
                            <Pressable testID="claim-submit" onPress={submitClaim} disabled={busy} style={st.claimBtn}>
                              {busy ? <ActivityIndicator color={C.onInverse} /> : <Text style={st.claimBtnText}>ODOSLAŤ ŽIADOSŤ O ODŠKODNÉ</Text>}
                            </Pressable>
                          )}
                        </View>
                      )}

                      {k === 'access' && !!j.access?.slot && (
                        <View style={st.slotBox}>
                          <Ionicons name="calendar" size={16} color={C.brand} />
                          <Text style={st.slotText}>{j.access.slot}</Text>
                        </View>
                      )}

                      <Pressable testID={`healing-step-${k}-cta`} onPress={() => { tap(); router.push(STEP_ROUTES[k] as any); }} style={st.stepCta}>
                        <Text style={st.stepCtaText}>{STEP_CTA[k]}</Text>
                        <Ionicons name="chevron-forward" size={14} color={C.brand} />
                      </Pressable>
                    </View>
                  );
                })}
              </View>

              <Pressable testID="healing-close" onPress={closeLoop} disabled={busy} style={st.fitBtn}>
                <Ionicons name="trophy" size={18} color={C.onInverse} />
                <Text style={st.fitText}>SOM 100 % FIT — UKONČIŤ KOLOTOČ</Text>
              </Pressable>
            </View>
          )}

          {/* WEEKLY HEALING REPORT — mood graph + carousel progress for doctor & family */}
          <Pressable testID="healing-report" onPress={() => { tap(); sharePdf('/healing/report.pdf', 'guardian_healing_report.pdf').catch(() => {}); }} style={st.reportBtn}>
            <Ionicons name="document-attach-outline" size={18} color={C.brand} />
            <View style={{ flex: 1 }}>
              <Text style={st.reportTitle}>TÝŽDENNÝ REPORT UZDRAVENIA (PDF)</Text>
              <Text style={st.reportSub}>Graf nálady + postup kolotoča — pre lekára aj rodinu</Text>
            </View>
            <Ionicons name="share-outline" size={18} color={C.info} />
          </Pressable>
        </ScrollView>
      )}

      {/* SMART WIZARD — zero typing, choice pickers only */}
      <Modal visible={wizard} transparent animationType="fade" onRequestClose={() => setWizard(false)}>
        <Pressable style={st.overlay} onPress={() => setWizard(false)}>
          <Pressable style={st.sheet} onPress={() => {}}>
            <View style={st.sheetHandle} />
            <Text style={st.sheetTitle}>Čo sa stalo?</Text>
            <View style={{ flexDirection: 'row', gap: S.sm, marginTop: S.md }}>
              {([['injury', '🩹 Úraz'], ['illness', '🤒 Choroba']] as const).map(([v, l]) => (
                <Pressable testID={`healing-kind-${v}`} key={v} onPress={() => { tap(); setKind(v); }} style={[st.bigChip, kind === v && st.bigChipOn]}>
                  <Text style={[st.bigChipText, kind === v && { color: C.onInverse }]}>{l}</Text>
                </Pressable>
              ))}
            </View>
            {kind === 'injury' && (<>
              <Text style={st.sheetLbl}>ČO VÁS BOLÍ?</Text>
              <View style={st.chipWrap}>
                {BODY_PARTS.map(b => (
                  <Pressable testID={`healing-part-${b}`} key={b} onPress={() => { tap(); setPart(b); }} style={[st.chip, part === b && st.chipOn]}>
                    <Text style={[st.chipText, part === b && { color: C.onInverse }]}>{b}</Text>
                  </Pressable>
                ))}
              </View>
            </>)}
            <Text style={st.sheetLbl}>AKÝ ŠPECIALISTA?</Text>
            <View style={st.chipWrap}>
              {(SPECIALTIES.includes(spec) ? SPECIALTIES : [spec, ...SPECIALTIES]).map(s => (
                <Pressable testID={`healing-spec-${s}`} key={s} onPress={() => { tap(); setSpec(s); }} style={[st.chip, spec === s && st.chipOn]}>
                  <Text style={[st.chipText, spec === s && { color: C.onInverse }]}>{s}</Text>
                </Pressable>
              ))}
            </View>
            <Pressable testID="healing-wizard-go" onPress={start} disabled={busy} style={st.goBtn}>
              {busy ? <ActivityIndicator color={C.onInverse} /> : (<>
                <Ionicons name="flash" size={18} color={C.onInverse} />
                <Text style={st.goText}>SPUSTIŤ — POISTKA + DOKTOR NARAZ</Text>
              </>)}
            </Pressable>
          </Pressable>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md, borderBottomWidth: 1, borderBottomColor: C.border },
  title: { color: C.fg, fontWeight: '900', fontSize: 15, letterSpacing: 2 },
  msgBox: { backgroundColor: 'rgba(212,175,55,0.12)', borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.md, padding: S.md, marginBottom: S.md },
  msgText: { color: C.brand, fontWeight: '800', fontSize: 12, lineHeight: 18 },
  heroIcon: { width: 64, height: 64, borderRadius: R.lg, backgroundColor: 'rgba(212,175,55,0.14)', alignItems: 'center', justifyContent: 'center' },
  heroTitle: { marginTop: S.lg, fontSize: 26, fontWeight: '900', color: C.fg, lineHeight: 33 },
  heroSub: { marginTop: S.sm, color: C.onS3, fontSize: 13, lineHeight: 19 },
  previewRow: { flexDirection: 'row', alignItems: 'center', gap: S.md, backgroundColor: C.surface2, borderRadius: R.md, padding: S.md, borderWidth: 1, borderColor: C.border },
  previewNum: { color: C.info, fontWeight: '900', fontSize: 14, width: 18 },
  previewTitle: { color: C.fg, fontWeight: '800', fontSize: 14 },
  previewSub: { color: C.info, fontSize: 11, marginTop: 1 },
  startBtn: { marginTop: S.xl, flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, borderRadius: R.pill, minHeight: 58 },
  startText: { color: C.onInverse, fontWeight: '900', letterSpacing: 2, fontSize: 15 },
  lastNote: { marginTop: S.md, color: C.info, fontSize: 11, textAlign: 'center' },
  progressRing: { width: 62, height: 62, borderRadius: 31, borderWidth: 3, borderColor: C.brand, alignItems: 'center', justifyContent: 'center' },
  progressPct: { color: C.brand, fontWeight: '900', fontSize: 15 },
  jTitle: { color: C.fg, fontWeight: '900', fontSize: 17 },
  jSub: { color: C.info, fontSize: 12, marginTop: 2 },
  stepCard: { backgroundColor: C.surface2, borderRadius: R.lg, padding: S.md, borderWidth: 1, borderColor: C.border },
  stepDone: { borderColor: 'rgba(212,175,55,0.5)' },
  stepAction: { borderColor: C.warn },
  stepHead: { flexDirection: 'row', alignItems: 'center', gap: S.md },
  stepBadge: { width: 28, height: 28, borderRadius: 14, backgroundColor: C.surface3, alignItems: 'center', justifyContent: 'center' },
  stepNum: { color: C.fg, fontWeight: '900', fontSize: 13 },
  stepTitle: { color: C.fg, fontWeight: '900', fontSize: 12, letterSpacing: 1 },
  stepSub: { color: C.info, fontSize: 11, marginTop: 1 },
  stepStatus: { fontWeight: '900', fontSize: 9, letterSpacing: 1, color: C.info },
  claimBox: { marginTop: S.md, backgroundColor: 'rgba(212,175,55,0.08)', borderRadius: R.md, padding: S.md, borderWidth: 1, borderColor: C.borderStrong },
  claimTitle: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 1, marginBottom: 6 },
  claimLine: { color: C.onS3, fontSize: 12, marginTop: 3 },
  claimVal: { color: C.fg, fontWeight: '800' },
  claimBtn: { marginTop: S.md, backgroundColor: C.brand, borderRadius: R.pill, alignItems: 'center', justifyContent: 'center', minHeight: 48 },
  claimBtnText: { color: C.onInverse, fontWeight: '900', fontSize: 12, letterSpacing: 1 },
  slotBox: { marginTop: S.md, flexDirection: 'row', alignItems: 'center', gap: S.sm, backgroundColor: 'rgba(212,175,55,0.08)', borderRadius: R.md, padding: S.md },
  slotText: { color: C.fg, fontWeight: '800', fontSize: 12, flex: 1 },
  stepCta: { marginTop: S.md, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.pill, minHeight: 46 },
  stepCtaText: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 1 },
  fitBtn: { marginTop: S.xl, flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, borderRadius: R.pill, minHeight: 56 },
  fitText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1.5, fontSize: 13 },
  reportBtn: { marginTop: S.lg, flexDirection: 'row', alignItems: 'center', gap: S.md, borderWidth: 1.5, borderColor: C.borderStrong, borderRadius: R.lg, padding: S.md, minHeight: 64, backgroundColor: C.surface2 },
  reportTitle: { color: C.fg, fontWeight: '900', fontSize: 11.5, letterSpacing: 1 },
  reportSub: { color: C.info, fontSize: 10.5, marginTop: 2 },
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.72)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: C.surface2, borderTopLeftRadius: R.lg, borderTopRightRadius: R.lg, padding: S.xl, paddingBottom: 34, borderWidth: 1, borderColor: C.borderStrong },
  sheetHandle: { alignSelf: 'center', width: 44, height: 5, borderRadius: 3, backgroundColor: C.surface3, marginBottom: S.md },
  sheetTitle: { color: C.fg, fontWeight: '900', fontSize: 20 },
  sheetLbl: { marginTop: S.lg, marginBottom: S.sm, color: C.info, fontWeight: '900', fontSize: 10, letterSpacing: 2 },
  bigChip: { flex: 1, alignItems: 'center', justifyContent: 'center', minHeight: 56, borderRadius: R.md, borderWidth: 1.5, borderColor: C.borderStrong },
  bigChipOn: { backgroundColor: C.brand, borderColor: C.brand },
  bigChipText: { color: C.fg, fontWeight: '900', fontSize: 15 },
  chipWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: S.sm },
  chip: { paddingHorizontal: S.md, minHeight: 44, alignItems: 'center', justifyContent: 'center', borderRadius: R.pill, borderWidth: 1.5, borderColor: C.borderStrong },
  chipOn: { backgroundColor: C.brand, borderColor: C.brand },
  chipText: { color: C.fg, fontWeight: '800', fontSize: 13 },
  goBtn: { marginTop: S.xl, flexDirection: 'row', gap: S.sm, alignItems: 'center', justifyContent: 'center', backgroundColor: C.brand, borderRadius: R.pill, minHeight: 56 },
  goText: { color: C.onInverse, fontWeight: '900', letterSpacing: 1, fontSize: 13 },
});
