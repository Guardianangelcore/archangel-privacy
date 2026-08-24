/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React from 'react';
import PillarHub from '@/src/PillarHub';
import { sharePdf } from '@/src/pdf';

export default function HealthHub() {
  return (
    <PillarHub
      testID="hub-health"
      icon="heart"
      title="Health Hub"
      subtitle="Váš zdravotný trezor, AI prekladač a rehabilitácia — všetko na jednom mieste."
      items={[
        { testID: 'hh-vault', icon: 'lock-closed-outline', title: 'Zdravotný trezor', subtitle: 'Dokumenty · OCR · AI preklad', route: '/(tabs)/vault' },
        { testID: 'hh-news', icon: 'flask-outline', title: 'Medical News Sentinel', subtitle: 'Prelomy krížené s tvojím trezorom · Tech-Tracker CZ/SK', route: '/medical-news' },
        { testID: 'hh-drop', icon: 'cloud-download-outline', title: 'Health Drop', subtitle: 'Lekár → trezor · zero-knowledge', route: '/health-drop' },
        { testID: 'hh-timeline', icon: 'time-outline', title: 'Health Timeline', subtitle: 'Vyšetrenia · história · vakcíny', route: '/health-timeline' },
        { testID: 'hh-recovery', icon: 'bed-outline', title: 'Moje zotavenie', subtitle: 'ePN · vychádzky · nemocenské', route: '/my-recovery' },
        { testID: 'hh-translate', icon: 'language-outline', title: 'AI Prekladač (Jarvis)', subtitle: 'Lekárčina → ľudská reč · hlas', route: '/translate' },
        { testID: 'hh-physio', icon: 'body-outline', title: 'Physio-AI', subtitle: 'Rehabilitačné rutiny na mieru', route: '/physio' },
        { testID: 'hh-mental', icon: 'shield-outline', title: 'Mental Fortress', subtitle: 'Krízový audio sprievodca · akupresúra', route: '/mental-fortress' },
        { testID: 'hh-border', icon: 'airplane-outline', title: 'Border Crosser', subtitle: 'Certifikát o liekoch · 14 jazykov', route: '/border-pass' },
        { testID: 'hh-meds', icon: 'alarm-outline', title: 'Lieky dnes', subtitle: 'Pripomienky · hlasové upozornenia', route: '/meds' },
        { testID: 'hh-cabinet', icon: 'medkit-outline', title: 'Lekárnička', subtitle: 'Zásoby · expirácie · AI kontrola interakcií · P2P', route: '/medicine-cabinet' },
        { testID: 'hh-bioscan', icon: 'scan-outline', title: 'Vitals Bio-Scanner', subtitle: 'Tep · SpO2 · tlak · stres kamerou (Sentinel / 5 GA-T)', route: '/bioscan' },
        { testID: 'hh-longevity', icon: 'infinite-outline', title: 'Longevity Engine', subtitle: 'Biologický vek · AI Bio-Hacks (Sentinel)', route: '/longevity' },
        { testID: 'hh-ips', icon: 'globe-outline', title: 'Universal Health Resume (IPS)', subtitle: '1 ťuk: HL7 FHIR export · EÚ / UK / USA interoperabilita', onPress: () => { sharePdf('/ips/summary.pdf', 'guardian_ips_summary.pdf').catch(() => {}); } },
        { testID: 'hh-bible', icon: 'book-outline', title: 'Survival Bible', subtitle: 'Jedným ťukom: tlačiteľné PDF všetkých kritických dát', onPress: () => { sharePdf('/survival/bible.pdf', 'guardian_survival_bible.pdf').catch(() => {}); } },
      ]}
    />
  );
}
