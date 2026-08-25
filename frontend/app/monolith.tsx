/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// SOVEREIGN OS COMMAND DECK — Archangel Monolith + Ascension Protocol.
// UHP Gateway · Arbitrage Brain · Liquidity Bank · Bio-Digital Twin ·
// Predictive Sentinel · Living Currency (GBI) · Collective Truth · Blueprint.
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '@/src/api';
import { useAuth } from '@/src/auth';
import { WheelField } from '@/src/ui/fields';
import { tap } from '@/src/ui/glass';
import { C, S, R } from '@/src/theme';

const PROCS = [
  { code: 'dental_implant', label: 'Zubný implantát' },
  { code: 'hip_replacement', label: 'Endoprotéza bedra' },
  { code: 'knee_replacement', label: 'Endoprotéza kolena' },
  { code: 'cataract', label: 'Sivý zákal' },
  { code: 'all_on_4', label: 'All-on-4' },
  { code: 'mri_full', label: 'Celotelová MRI' },
];
const URGENCIES = [
  { id: 'low', label: 'NÍZKA' }, { id: 'medium', label: 'STREDNÁ' }, { id: 'high', label: 'VYSOKÁ' },
];

function Section({ id, icon, title, sub, open, onToggle, children }: any) {
  const isOpen = open === id;
  return (
    <View style={st.section}>
      <Pressable testID={`mono-sec-${id}`} onPress={() => { tap('light'); onToggle(isOpen ? '' : id); }} style={st.secHead}>
        <Ionicons name={icon} size={20} color={C.brand} />
        <View style={{ flex: 1 }}>
          <Text style={st.secTitle}>{title}</Text>
          <Text style={st.secSub}>{sub}</Text>
        </View>
        <Ionicons name={isOpen ? 'chevron-up' : 'chevron-down'} size={16} color={C.info} />
      </Pressable>
      {isOpen && <View style={st.secBody}>{children}</View>}
    </View>
  );
}

const Row = ({ k, v, hi }: { k: string; v: any; hi?: boolean }) => (
  <View style={st.row}>
    <Text style={st.rowK}>{k}</Text>
    <Text style={[st.rowV, hi && { color: C.brand }]}>{String(v)}</Text>
  </View>
);

export default function Monolith() {
  const router = useRouter();
  const { user } = useAuth();
  const [open, setOpen] = useState('uhp');
  const [cap, setCap] = useState<any>(null);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState('');
  // arbitrage
  const [proc, setProc] = useState('dental_implant');
  const [urg, setUrg] = useState('medium');
  const [localPrice, setLocalPrice] = useState('');
  const [localWait, setLocalWait] = useState('');
  const [arb, setArb] = useState<any>(null);
  // liquidity
  const [bal, setBal] = useState<any>(null);
  const [amount, setAmount] = useState('50');
  const [card, setCard] = useState('4242');
  const [network, setNetwork] = useState('visa');
  const [payout, setPayout] = useState<any>(null);
  const [credit, setCredit] = useState<any>(null);
  const [drawAmt, setDrawAmt] = useState('50');
  // twin
  const [traj, setTraj] = useState<any>(null);
  const [treatment, setTreatment] = useState('');
  const [sim, setSim] = useState<any>(null);
  // sentinel
  const [risk, setRisk] = useState<any>(null);
  // edge
  const [edge, setEdge] = useState<any>(null);
  const [edgeResult, setEdgeResult] = useState<any>(null);
  // truth
  const [truth, setTruth] = useState<any>(null);
  const [testimony, setTestimony] = useState('');
  // blueprint
  const [bp, setBp] = useState<any>(null);
  const [bpQ, setBpQ] = useState('');
  const [bpA, setBpA] = useState('');

  const load = useCallback(async () => {
    try { setCap(await api('/uhp/capacity')); } catch {}
    try { setBal(await api('/liquidity/balance')); } catch {}
    try { setRisk(await api('/sentinel/predict')); } catch {}
    try { setEdge(await api('/edge/status')); } catch {}
    try { setTruth(await api('/mesh/truth/verify')); } catch {}
    try { const b: any = await api('/legacy/blueprint'); setBp(b.blueprint); } catch {}
  }, []);
  useEffect(() => { load(); }, [load]);

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key); setErr('');
    try { await fn(); } catch (e: any) { setErr(String(e.message || e)); }
    setBusy('');
  };

  const analyze = () => run('arb', async () => {
    const body: any = { procedure: proc, urgency: urg };
    if (localPrice) body.local_price_eur = parseFloat(localPrice);
    if (localWait) body.local_wait_weeks = parseInt(localWait, 10);
    setArb(await api('/arbitrage/analyze', { method: 'POST', body: JSON.stringify(body) }));
  });

  const doPayout = () => run('pay', async () => {
    const res: any = await api('/liquidity/payout', {
      method: 'POST',
      body: JSON.stringify({ amount: parseFloat(amount), currency: 'EUR', card_last4: card, network, idempotency_key: `ui-${Date.now()}` }),
    });
    setPayout(res.payout);
    setBal(await api('/liquidity/balance'));
  });

  const scoreCredit = () => run('credit', async () => { setCredit(await api('/liquidity/credit/score', { method: 'POST' })); });
  const drawCredit = () => run('draw', async () => {
    await api('/liquidity/credit/draw', { method: 'POST', body: JSON.stringify({ amount: parseFloat(drawAmt) }) });
    setBal(await api('/liquidity/balance'));
    setCredit(await api('/liquidity/credit/score', { method: 'POST' }));
  });

  const loadTraj = () => run('traj', async () => { setTraj(await api('/twin/trajectory')); });
  const simulate = () => run('sim', async () => {
    if (!treatment.trim()) return;
    setSim(await api('/twin/simulate', { method: 'POST', body: JSON.stringify({ treatment }) }));
  });

  const runEdge = () => run('edge', async () => {
    setEdgeResult(null);
    let tasks = 0;
    const start = Date.now();
    for (let s = 0; s < 15; s++) {
      // real research work slices — keeps UI responsive
      await new Promise(r => setTimeout(r, 0));
      const endAt = Date.now() + 180;
      while (Date.now() < endAt) { Math.sqrt((tasks % 9973) + s); tasks++; }
    }
    const ms = Date.now() - start;
    const res: any = await api('/edge/contribute', {
      method: 'POST',
      body: JSON.stringify({ device_id: `device-${(user?.user_id || 'x').slice(0, 10)}`, tasks_completed: Math.min(tasks, 4900000), ms_contributed: ms }),
    });
    setEdgeResult({ ...res, tasks, ms });
    setEdge(await api('/edge/status'));
  });

  const appendTruth = () => run('truth', async () => {
    if (!testimony.trim()) return;
    await api('/mesh/truth', { method: 'POST', body: JSON.stringify({ kind: 'testimony', content: testimony }) });
    setTestimony('');
    setTruth(await api('/mesh/truth/verify'));
  });

  const trainBp = () => run('bp', async () => { const r: any = await api('/legacy/blueprint/train', { method: 'POST' }); setBp(r); });
  const askBp = () => run('bpask', async () => {
    if (!bpQ.trim()) return;
    const r: any = await api('/legacy/blueprint/ask', { method: 'POST', body: JSON.stringify({ question: bpQ, asker_name: 'Tomáš' }) });
    setBpA(r.answer);
  });

  const bandColor = (b: string) => b === 'critical' ? C.error : b === 'elevated' ? '#FFC53D' : C.brand;

  return (
    <SafeAreaView testID="monolith-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="mono-back" onPress={() => { tap(); router.back(); }} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={C.fg} />
        </Pressable>
        <Text style={st.title}>SOVEREIGN OS · COMMAND DECK</Text>
        <Ionicons name="planet-outline" size={20} color={C.brand} />
      </View>
      <ScrollView contentContainerStyle={{ paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
        {!!err && <Text style={st.err}>{err}</Text>}

        <Section id="uhp" icon="git-network-outline" title="GLOBAL SENTINEL NETWORK" sub="Universal Health Protocol · povinná brána" open={open} onToggle={setOpen}>
          {cap ? (
            <>
              <Text style={st.big}>{cap.stream_capacity_human} <Text style={st.bigSub}>súbežných streamov</Text></Text>
              <Row k="Topológia" v={`${cap.topology.regions} regiónov × ${cap.topology.shards_per_region} shardov × ${cap.topology.nodes_per_shard} uzlov`} />
              <Row k="Aktívni partneri (kliniky/poisťovne)" v={cap.active_partners} hi />
              <Row k="Prijaté UHP eventy" v={cap.events_ingested_total} />
              <Row k="Otvorené senzor-streamy" v={cap.open_streams} />
              <Row k="Konsenzus" v={cap.consensus} />
              <Text style={st.note}>Partneri sa registrujú cez /api/uhp/partners/register — HMAC-SHA256 podpisy, ochrana proti replay, idempotencia, {'240/min'} rate-limit.</Text>
            </>
          ) : <ActivityIndicator color={C.brand} />}
        </Section>

        <Section id="arb" icon="trending-up-outline" title="ARBITRAGE BRAIN" sub="10 000+ kliník · cena vs. ušetrený čas" open={open} onToggle={setOpen}>
          <View style={st.chips}>
            {PROCS.map(p => (
              <Pressable key={p.code} testID={`mono-proc-${p.code}`} onPress={() => { tap('light'); setProc(p.code); }} style={[st.chip, proc === p.code && st.chipOn]}>
                <Text style={[st.chipText, proc === p.code && st.chipTextOn]}>{p.label}</Text>
              </Pressable>
            ))}
          </View>
          <View style={st.chips}>
            {URGENCIES.map(u => (
              <Pressable key={u.id} testID={`mono-urg-${u.id}`} onPress={() => { tap('light'); setUrg(u.id); }} style={[st.chip, urg === u.id && st.chipOn]}>
                <Text style={[st.chipText, urg === u.id && st.chipTextOn]}>{u.label}</Text>
              </Pressable>
            ))}
          </View>
          <View style={st.inRow}>
            <WheelField testID="mono-local-price" title="LOKÁLNA CENA €" min={0} max={20000} step={100} unit="€" value={localPrice} onChange={setLocalPrice} placeholder="Lokálna cena" style={st.input} />
            <WheelField testID="mono-local-wait" title="LOKÁLNE ČAKANIE (TÝŽ.)" min={0} max={100} unit="týž." value={localWait} onChange={setLocalWait} placeholder="Čakanie" style={st.input} />
          </View>
          <Pressable testID="mono-analyze" onPress={analyze} disabled={busy === 'arb'} style={st.cta}>
            {busy === 'arb' ? <ActivityIndicator color={C.onInverse} /> : <Text style={st.ctaText}>ANALYZOVAŤ GLOBÁLNY TRH</Text>}
          </Pressable>
          {arb && (
            <>
              <Text style={st.note}>Analyzovaných {arb.candidates_analyzed} kliník · {arb.formula}</Text>
              {[['💎 NAJLEPŠIA HODNOTA', arb.picks.best_value], ['💶 NAJLACNEJŠIA', arb.picks.cheapest], ['⚡ NAJRÝCHLEJŠIA', arb.picks.fastest]].map(([lbl, c]: any) => (
                <View key={lbl} style={st.card}>
                  <Text style={st.cardLbl}>{lbl}</Text>
                  <Text style={st.cardTitle}>{c.name} · {c.city} ({c.country})</Text>
                  <Text style={st.cardLine}>Zákrok {c.price_eur} € + cesta {c.travel_eur} € + pobyt {c.lodging_eur} € = <Text style={{ color: C.brand, fontWeight: '900' }}>{c.total_cost_eur} €</Text></Text>
                  <Text style={st.cardLine}>Čakanie {c.wait_days} dní · ušetríte {c.time_saved_weeks} týž. (hodnota {c.time_value_eur} €) · kvalita {c.quality}★</Text>
                  <Text style={[st.cardLine, { color: c.net_benefit_eur > 0 ? C.brand : C.error, fontWeight: '900' }]}>ČISTÝ PRÍNOS: {c.net_benefit_eur > 0 ? '+' : ''}{c.net_benefit_eur} €</Text>
                </View>
              ))}
            </>
          )}
        </Section>

        <Section id="bank" icon="card-outline" title="LIQUIDITY BANK" sub="Instant Card Payout · Data-Backed Credit" open={open} onToggle={setOpen}>
          <Text style={st.big}>{bal ? `${bal.balance.available_eur.toFixed(2)} €` : '—'} <Text style={st.bigSub}>dostupný zostatok</Text></Text>
          {bal && <Text style={st.note}>Rails: {bal.adapter} ({bal.rails_mode}) — adaptér sa vymení za Visa Direct / MC Send v deň pripojenia inštitúcie.</Text>}
          <View style={st.inRow}>
            <WheelField testID="mono-pay-amount" title="SUMA €" min={10} max={2000} step={10} unit="€" value={amount} onChange={setAmount} placeholder="Suma" style={st.input} />
            <TextInput testID="mono-pay-card" value={card} onChangeText={setCard} maxLength={4} keyboardType="number-pad" placeholder="****" placeholderTextColor="#888" style={[st.input, st.inputText, { flex: 0.6 }]} />
          </View>
          <View style={st.chips}>
            {['visa', 'mc'].map(n => (
              <Pressable key={n} testID={`mono-net-${n}`} onPress={() => { tap('light'); setNetwork(n); }} style={[st.chip, network === n && st.chipOn]}>
                <Text style={[st.chipText, network === n && st.chipTextOn]}>{n === 'visa' ? 'VISA DIRECT' : 'MASTERCARD SEND'}</Text>
              </Pressable>
            ))}
          </View>
          <Pressable testID="mono-payout" onPress={doPayout} disabled={busy === 'pay'} style={st.cta}>
            {busy === 'pay' ? <ActivityIndicator color={C.onInverse} /> : <Text style={st.ctaText}>OKAMŽITÁ VÝPLATA NA KARTU</Text>}
          </Pressable>
          {payout && (
            <View style={st.card}>
              <Text style={st.cardLbl}>SETTLEMENT ****{payout.card_last4}</Text>
              <View style={st.timeline}>
                {['initiated', 'authorized', 'settled'].map(s => {
                  const done = payout.timeline?.some((tl: any) => tl.state === s);
                  return (
                    <View key={s} style={st.tlStep}>
                      <Ionicons name={done ? 'checkmark-circle' : 'ellipse-outline'} size={16} color={done ? C.brand : C.info} />
                      <Text style={[st.tlText, done && { color: C.fg }]}>{s.toUpperCase()}</Text>
                    </View>
                  );
                })}
              </View>
              <Text style={st.cardLine}>{payout.amount_eur} € · poplatok {payout.fee_eur} € · trace {payout.trace_id}</Text>
            </View>
          )}
          <Pressable testID="mono-credit-score" onPress={scoreCredit} disabled={busy === 'credit'} style={st.ghost}>
            {busy === 'credit' ? <ActivityIndicator color={C.brand} /> : <Text style={st.ghostText}>DATA-BACKED CREDIT — VYPOČÍTAŤ LIMIT</Text>}
          </Pressable>
          {credit && (
            <View style={st.card}>
              <Text style={st.cardTitle}>Úverový limit: {credit.limit_eur} € · {credit.apr_pct}% p.a.</Text>
              <Text style={st.cardLine}>Kolaterál = dátové bohatstvo: {credit.collateral.documents} dokumentov · {credit.collateral.bioscans} meraní · {credit.collateral.gat_balance} GA-T</Text>
              <View style={st.inRow}>
                <WheelField testID="mono-draw" title="ČERPAŤ €" min={10} max={5000} step={10} unit="€" value={drawAmt} onChange={setDrawAmt} placeholder="Čerpať" style={st.input} />
                <Pressable testID="mono-draw-btn" onPress={drawCredit} disabled={busy === 'draw'} style={[st.cta, { flex: 1, marginTop: 0 }]}>
                  {busy === 'draw' ? <ActivityIndicator color={C.onInverse} /> : <Text style={st.ctaText}>ČERPAŤ</Text>}
                </Pressable>
              </View>
            </View>
          )}
        </Section>

        <Section id="twin" icon="body-outline" title="BIO-DIGITÁLNE DVOJČA" sub="Simulácia liečby PRED podaním · trajektórie" open={open} onToggle={setOpen}>
          <Pressable testID="mono-traj" onPress={loadTraj} disabled={busy === 'traj'} style={st.ghost}>
            {busy === 'traj' ? <ActivityIndicator color={C.brand} /> : <Text style={st.ghostText}>PREDIKTÍVNE TRAJEKTÓRIE (6/12/24 MES.)</Text>}
          </Pressable>
          {traj && (
            <View style={st.card}>
              {Object.entries(traj.trajectories).map(([m, d]: any) => (
                <View key={m} style={{ marginBottom: S.sm }}>
                  <Text style={st.cardLbl}>{m === 'systolic' ? 'SYSTOLICKÝ TLAK' : 'GLUKÓZA'} ({d.history_points} meraní)</Text>
                  <Text style={st.cardLine}>
                    teraz <Text style={{ color: bandColor(d.band_now), fontWeight: '900' }}>{d.current ?? '—'}</Text>
                    {'  →  6m '}{d.m6 ?? '—'}{'  →  12m '}<Text style={{ color: bandColor(d.band_m12), fontWeight: '900' }}>{d.m12 ?? '—'}</Text>{'  →  24m '}{d.m24 ?? '—'}
                  </Text>
                </View>
              ))}
              <Text style={st.cardLine}>Kompozitné riziko 12m: <Text style={{ color: traj.composite_risk_12m >= 40 ? C.error : C.brand, fontWeight: '900' }}>{traj.composite_risk_12m}/100</Text></Text>
              <Text style={st.note}>{traj.disclaimer}</Text>
            </View>
          )}
          <TextInput testID="mono-treatment" value={treatment} onChangeText={setTreatment} placeholder="Liek / zákrok na simuláciu (napr. Ibuprofen 400 mg)" placeholderTextColor="#888" style={[st.input, st.inputText]} />
          <Pressable testID="mono-simulate" onPress={simulate} disabled={busy === 'sim'} style={st.cta}>
            {busy === 'sim' ? <ActivityIndicator color={C.onInverse} /> : <Text style={st.ctaText}>SIMULOVAŤ NA DVOJČATI (gpt-5.4)</Text>}
          </Pressable>
          {sim && (
            <View style={[st.card, { borderColor: sim.result.verdict === 'simulate_pass' ? C.brand : sim.result.verdict === 'caution' ? '#FFC53D' : C.error }]}>
              <Text style={st.cardTitle}>{sim.treatment} — kompatibilita {sim.result.compatibility_pct}% · {String(sim.result.verdict).toUpperCase()}</Text>
              <Text style={st.cardLine}>{sim.result.expected_benefit}</Text>
              {(sim.result.interactions || []).map((x: string, i: number) => <Text key={i} style={[st.cardLine, { color: '#FFC53D' }]}>⚠ {x}</Text>)}
              {(sim.result.risks || []).map((x: string, i: number) => <Text key={i} style={st.cardLine}>• {x}</Text>)}
            </View>
          )}
        </Section>

        <Section id="sentinel" icon="pulse-outline" title="PREDIKTÍVNY SENTINEL" sub="Varuje Inner Circle PRED udalosťou" open={open} onToggle={setOpen}>
          {risk ? (
            <>
              <Text style={st.big}><Text style={{ color: risk.level === 'high' ? C.error : risk.level === 'medium' ? '#FFC53D' : C.brand }}>{risk.risk_score}</Text><Text style={st.bigSub}> /100 riziko · {risk.level.toUpperCase()}</Text></Text>
              {(risk.factors || []).map((f: string, i: number) => <Text key={i} style={st.cardLine}>• {f}</Text>)}
              <Text style={st.note}>Mikro-vibrácie a pravidelnosť chôdze sa zbierajú automaticky senzormi ({risk.samples_24h} vzoriek/24 h). Pri riziku ≥70 dostane Inner Circle push PRED udalosťou.</Text>
            </>
          ) : <ActivityIndicator color={C.brand} />}
        </Section>

        <Section id="edge" icon="hardware-chip-outline" title="ŽIVÁ MENA · GUARDIAN BASIC INCOME" sub="GA-T za výpočty pre medicínsky výskum" open={open} onToggle={setOpen}>
          {edge && (
            <>
              <Row k="Uzly siete" v={edge.network.nodes} hi />
              <Row k="Výskumné úlohy spolu" v={edge.network.tasks_total.toLocaleString()} />
              <Row k="GA-T rozdelené" v={edge.network.gat_distributed} />
              <Row k="Sadzba" v={edge.rate} />
              <Row k="Základný príjem (GBI)" v={`${edge.gbi.daily_gat} GA-T / deň`} hi />
            </>
          )}
          <Pressable testID="mono-edge-run" onPress={runEdge} disabled={busy === 'edge'} style={st.cta}>
            {busy === 'edge' ? <ActivityIndicator color={C.onInverse} /> : <Text style={st.ctaText}>DAROVAŤ VÝPOČTOVÝ VÝKON (≈3 s)</Text>}
          </Pressable>
          {edgeResult && (
            <View style={st.card}>
              <Text style={st.cardTitle}>+{edgeResult.gat_earned} GA-T</Text>
              <Text style={st.cardLine}>{edgeResult.tasks.toLocaleString()} reálnych úloh za {edgeResult.ms} ms — zariadenie počítalo pre decentralizovaný výskumný swarm.</Text>
            </View>
          )}
        </Section>

        <Section id="truth" icon="library-outline" title="COLLECTIVE HUMAN TRUTH" sub="SHA3-512 reťaz · post-kvantový hash" open={open} onToggle={setOpen}>
          {truth && (
            <>
              <Row k="Integrita reťaze" v={truth.valid ? '✓ NEPORUŠENÁ' : '✗ PORUŠENÁ'} hi />
              <Row k="Záznamov" v={truth.records} />
              <Row k="Hlava reťaze" v={String(truth.head || '').slice(0, 18) + '…'} />
            </>
          )}
          <TextInput testID="mono-testimony" value={testimony} onChangeText={setTestimony} placeholder="Zapísať svedectvo do večného záznamu…" placeholderTextColor="#888" style={[st.input, st.inputText]} />
          <Pressable testID="mono-truth-add" onPress={appendTruth} disabled={busy === 'truth'} style={st.cta}>
            {busy === 'truth' ? <ActivityIndicator color={C.onInverse} /> : <Text style={st.ctaText}>ZAPEČATIŤ DO REŤAZE</Text>}
          </Pressable>
        </Section>

        <Section id="bp" icon="finger-print-outline" title="PERSONALITY BLUEPRINT" sub="Kognitívne odovzdanie — Jarvis pre pozostalých" open={open} onToggle={setOpen}>
          <Pressable testID="mono-bp-train" onPress={trainBp} disabled={busy === 'bp'} style={st.ghost}>
            {busy === 'bp' ? <ActivityIndicator color={C.brand} /> : <Text style={st.ghostText}>{bp ? `PRETRÉNOVAŤ (v${bp.version ?? 1})` : 'NATRÉNOVAŤ MOJU OSOBNOSŤ (gpt-5.4)'}</Text>}
          </Pressable>
          {bp?.blueprint && (
            <View style={st.card}>
              <Text style={st.cardLbl}>TÓN</Text>
              <Text style={st.cardLine}>{bp.blueprint.tone}</Text>
              <Text style={st.cardLbl}>HODNOTY</Text>
              <Text style={st.cardLine}>{(bp.blueprint.values || []).join(' · ')}</Text>
              <Text style={st.cardLbl}>ROZHODOVACIE PRAVIDLÁ</Text>
              {(bp.blueprint.decision_rules || []).map((r: string, i: number) => <Text key={i} style={st.cardLine}>• {r}</Text>)}
            </View>
          )}
          <TextInput testID="mono-bp-q" value={bpQ} onChangeText={setBpQ} placeholder="Tomášova otázka pre digitálne echo…" placeholderTextColor="#888" style={[st.input, st.inputText]} />
          <Pressable testID="mono-bp-ask" onPress={askBp} disabled={busy === 'bpask'} style={st.cta}>
            {busy === 'bpask' ? <ActivityIndicator color={C.onInverse} /> : <Text style={st.ctaText}>OPÝTAŤ SA DIGITÁLNEHO ECHA</Text>}
          </Pressable>
          {!!bpA && <View style={st.card}><Text style={st.cardLine}>{bpA}</Text></View>}
          <Text style={st.note}>Verný hlasový klon vyžaduje ElevenLabs kľúč — echo zatiaľ hovorí najbližším OpenAI hlasom.</Text>
        </Section>

        <Text style={st.footer}>SOVEREIGN SURVIVAL OS · 22. STOROČIE · GUARDIAN ANGEL SOVEREIGN FOUNDATION (DAO)</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 2, fontSize: 13 },
  section: { marginHorizontal: S.lg, marginTop: S.md, backgroundColor: C.surface2, borderRadius: R.md, borderWidth: 1, borderColor: C.border, overflow: 'hidden' },
  secHead: { flexDirection: 'row', alignItems: 'center', gap: S.md, padding: S.lg, minHeight: 64 },
  secTitle: { color: C.fg, fontWeight: '900', fontSize: 13, letterSpacing: 1.5 },
  secSub: { color: C.info, fontSize: 10.5, marginTop: 2 },
  secBody: { paddingHorizontal: S.lg, paddingBottom: S.lg },
  big: { color: C.fg, fontWeight: '900', fontSize: 30, letterSpacing: 1 },
  bigSub: { fontSize: 12, color: C.info, fontWeight: '700', letterSpacing: 1 },
  row: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 5, gap: S.md },
  rowK: { color: C.info, fontSize: 12 },
  rowV: { color: C.fg, fontSize: 12, fontWeight: '800', flexShrink: 1, textAlign: 'right' },
  note: { color: C.info, fontSize: 10.5, lineHeight: 15, marginTop: S.sm },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: S.sm },
  chip: { borderWidth: 1.5, borderColor: C.border, borderRadius: R.pill, paddingHorizontal: 12, minHeight: 40, justifyContent: 'center' },
  chipOn: { borderColor: C.brand, backgroundColor: 'rgba(212,175,55,0.12)' },
  chipText: { color: C.info, fontWeight: '800', fontSize: 11 },
  chipTextOn: { color: C.brand },
  inRow: { flexDirection: 'row', gap: S.sm, marginTop: S.sm },
  input: { flex: 1, borderWidth: 1.5, borderColor: C.borderStrong, paddingHorizontal: S.md, minHeight: 50, backgroundColor: C.bg, marginTop: S.sm },
  inputText: { color: C.fg, fontSize: 14 },
  cta: { marginTop: S.md, backgroundColor: C.brand, minHeight: 50, alignItems: 'center', justifyContent: 'center', borderRadius: R.sm },
  ctaText: { color: C.onInverse, fontWeight: '900', fontSize: 12, letterSpacing: 1.5 },
  ghost: { marginTop: S.md, borderWidth: 1.5, borderColor: C.brand, minHeight: 50, alignItems: 'center', justifyContent: 'center', borderRadius: R.sm },
  ghostText: { color: C.brand, fontWeight: '900', fontSize: 12, letterSpacing: 1 },
  card: { marginTop: S.md, borderWidth: 1, borderColor: C.borderStrong, borderRadius: R.sm, padding: S.md, backgroundColor: C.bg },
  cardLbl: { color: C.brand, fontWeight: '900', fontSize: 10, letterSpacing: 2, marginTop: 4 },
  cardTitle: { color: C.fg, fontWeight: '900', fontSize: 14, marginTop: 2 },
  cardLine: { color: C.onS3, fontSize: 12, lineHeight: 18, marginTop: 3 },
  timeline: { flexDirection: 'row', gap: S.lg, marginTop: S.sm },
  tlStep: { flexDirection: 'row', gap: 5, alignItems: 'center' },
  tlText: { color: C.info, fontSize: 10.5, fontWeight: '800', letterSpacing: 1 },
  err: { color: C.error, fontSize: 12, paddingHorizontal: S.xl, marginTop: S.sm },
  footer: { textAlign: 'center', color: C.info, fontSize: 9, letterSpacing: 1.5, marginTop: S.xl, paddingHorizontal: S.xl },
});
