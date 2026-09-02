/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// PRIVACY POLICY — GDPR-compliant, public page (reachable without login)
import React from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { C, S, R } from '@/src/theme';
import { LEGAL_VERSION as VERSION, LEGAL_EFFECTIVE as EFFECTIVE } from '@/src/legal';
import { useI18n } from '@/src/i18n-context';

function Section({ n, title, children }: { n: string; title: string; children: React.ReactNode }) {
  return (
    <View style={st.section}>
      <Text style={st.secTitle}>{n}. {title}</Text>
      {children}
    </View>
  );
}
const P = ({ children }: { children: React.ReactNode }) => <Text style={st.p}>{children}</Text>;
const B = ({ children }: { children: React.ReactNode }) => <Text style={st.bullet}>•  {children}</Text>;

export default function PrivacyPolicy() {
  const router = useRouter();
  const { t, rtl } = useI18n();
  return (
    <SafeAreaView testID="privacy-screen" style={st.root} edges={['top']}>
      <View style={st.header}>
        <Pressable testID="privacy-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={C.fg} />
        </Pressable>
        <Text style={st.title}>PRIVACY POLICY</Text>
        <View style={{ width: 26 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.lg, paddingBottom: 80 }}>
        <Text style={st.meta}>Version {VERSION} · Effective {EFFECTIVE} · GDPR (EU 2016/679)</Text>
        <Text style={st.meta}>Data Controller: Guardian Angel Sovereign Foundation (DAO) · guardian.angel.core@proton.me</Text>

        {/* LOCAL-FIRST PROMISE */}
        <View testID="privacy-local-first" style={st.promiseBox}>
          <View style={st.promiseHead}>
            <Ionicons name="phone-portrait-outline" size={18} color={C.brand} />
            <Text style={st.promiseTitle}>YOUR DATA STAYS ON YOUR DEVICE</Text>
          </View>
          <Text style={st.promiseText}>
            Archangel OS is local-first and zero-surveillance. Contacts, calendar,
            and sensitive identifiers are stored on your device (SecureStore / encrypted
            storage). Nothing is shared with anyone unless you explicitly opt in. We never
            sell data and we show no advertising.
          </Text>
        </View>

        <Section n="1" title="WHAT WE PROCESS">
          <B>Account data: e-mail, display name, hashed password (bcrypt) or Google sign-in identifier.</B>
          <B>Health records you enter: Life Card entries (vaccinations, diseases, surgeries, exams, injuries, dental), medications, documents you scan into the Vault.</B>
          <B>Family data you add: Guardian Circle contacts — stored locally on your device; only pseudonymous DID hashes are used in metadata.</B>
          <B>Technical data: session tokens, timestamps needed to run the Service.</B>
        </Section>

        <Section n="2" title="LOCAL-FIRST STORAGE">
          <P>Device contacts and native calendar entries never leave your phone. Server-side
            records are linked to a pseudonymous decentralized identifier (DID), phone
            numbers are encrypted at rest, and vault secrets are sealed zero-knowledge.</P>
        </Section>

        <Section n="3" title="SHARING IS OPT-IN">
          <P>No data is shared by default. Sharing happens only when you actively enable it:</P>
          <B>Guardian Circle / Family Pulse — alerts you explicitly send or enable.</B>
          <B>Family Life Cards — only vaccinations and check-ups, only within your circle.</B>
          <B>Emergency QR — only the fields you choose to publish.</B>
          <P>You can withdraw any of these consents at any time in the app.</P>
        </Section>

        <Section n="4" title="LEGAL BASES (GDPR)">
          <B>Art. 6(1)(b) — performance of contract (running your account).</B>
          <B>Art. 6(1)(a) & Art. 9(2)(a) — your explicit consent for health data and any sharing.</B>
          <B>Art. 6(1)(f) — legitimate interest in securing the Service (fraud & abuse prevention).</B>
        </Section>

        <Section n="5" title="AI PROCESSING">
          <P>When you use AI features (Jarvis, Magic Lens, predictions), the content you
            submit is processed by AI providers solely to generate your answer. It is not
            used to train models. Every AI response carries the EU AI Act Article 50
            watermark.</P>
        </Section>

        <Section n="6" title="RETENTION & DELETION">
          <P>Your data is kept only while your account exists. Deleting your account removes
            your records; reset codes expire in 15 minutes; sessions expire automatically.
            Local data can be wiped by uninstalling the app or via in-app deletion.</P>
        </Section>

        <Section n="7" title="YOUR GDPR RIGHTS">
          <B>Access, rectification, and erasure of your data.</B>
          <B>Data portability (export your Life Card as PDF / vaccine pass).</B>
          <B>Withdraw consent at any time without affecting prior processing.</B>
          <B>Object to processing and lodge a complaint with your supervisory authority.</B>
          <P>Exercise these rights in-app or by writing to guardian.angel.core@proton.me.
            We respond within 30 days.</P>
        </Section>

        <Section n="8" title="SECURITY">
          <P>Encryption in transit (TLS) and at rest (Fernet for phone numbers, bcrypt for
            passwords, hashed reset codes), pseudonymous DIDs, session revocation on
            password reset, and zero-knowledge sealing of vault secrets.</P>
        </Section>

        <Section n="9" title="CHILDREN">
          <P>Child Life Cards are managed exclusively by the parent's account. We do not
            knowingly collect data directly from children.</P>
        </Section>

        <Section n="10" title="CHANGES">
          <P>Material changes will be announced in the app and, where required, will ask for
            renewed consent.</P>
        </Section>

        <Pressable testID="privacy-tos-link" onPress={() => router.push('/terms-of-service')} style={st.linkBtn}>
          <Ionicons name="document-text-outline" size={16} color={C.brand} />
          <Text style={st.linkBtnText}>READ THE TERMS OF SERVICE</Text>
        </Pressable>

        {/* CONSOLIDATED LEGAL DISCLAIMER — footer (localized, key disclaimer.general) */}
        <View testID="privacy-disclaimer" style={st.discBox}>
          <Text style={st.discTitle}>{t('disclaimer.title')}</Text>
          <Text testID="privacy-disclaimer-text" style={[st.discText, rtl && st.rtl]}>{t('disclaimer.general')}</Text>
        </View>
        <Text style={st.footer}>ZERO SURVEILLANCE · LOCAL-FIRST · © 2026 GUARDIAN ANGEL SOVEREIGN FOUNDATION (DAO)</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.lg, paddingVertical: S.md },
  title: { color: C.fg, fontWeight: '900', letterSpacing: 2, fontSize: 14 },
  meta: { color: C.info, fontSize: 10.5, letterSpacing: 0.5, marginBottom: 4 },
  discBox: { borderWidth: 1.5, borderColor: C.brand, backgroundColor: 'rgba(212,175,55,0.08)', borderRadius: R.md, padding: S.lg, marginTop: S.xl, gap: 6 },
  discTitle: { color: C.brand, fontWeight: '900', fontSize: 12, letterSpacing: 1.5 },
  discText: { color: C.fg, fontSize: 12.5, lineHeight: 19, fontWeight: '700' },
  rtl: { writingDirection: 'rtl', textAlign: 'right' },
  promiseBox: { borderWidth: 2, borderColor: C.brand, backgroundColor: 'rgba(212,175,55,0.08)', borderRadius: R.md, padding: S.lg, marginTop: S.md },
  promiseHead: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6 },
  promiseTitle: { color: C.brand, fontWeight: '900', fontSize: 12, letterSpacing: 1.5 },
  promiseText: { color: C.fg, fontSize: 13, lineHeight: 20, fontWeight: '600' },
  section: { marginTop: S.xl },
  secTitle: { color: C.brand, fontWeight: '900', fontSize: 11.5, letterSpacing: 1.5, marginBottom: 6 },
  p: { color: C.fg, fontSize: 13, lineHeight: 20, marginBottom: 6 },
  bullet: { color: C.onS3, fontSize: 12.5, lineHeight: 19, marginBottom: 4, paddingLeft: 4 },
  linkBtn: { flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', borderWidth: 1.5, borderColor: C.brand, borderRadius: R.sm, minHeight: 48, marginTop: S.xl },
  linkBtnText: { color: C.brand, fontWeight: '900', fontSize: 11, letterSpacing: 1.5 },
  footer: { textAlign: 'center', color: C.info, fontSize: 8.5, letterSpacing: 1, marginTop: S.xl, lineHeight: 13 },
});
