/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React from 'react';
import PillarHub from '@/src/PillarHub';
import { sharePdf } from '@/src/pdf';

export default function HealthHub() {
  return (
    <PillarHub
      testID="hub-health"
      icon="sync"
      title="Moje uzdravovanie"
      subtitle="Pilier 1 · Kolotoč uzdravenia — od žiadanky cez peniaze a doktora až po 100 % fit."
      sections={[
        { title: '⚙️ KOLOTOČ UZDRAVENIA — JADRO', items: [
          { testID: 'hh-healing', icon: 'sync-outline', title: 'Kolotoč uzdravenia', subtitle: 'Úraz → peniaze hneď → doktor → PN → fyzio', route: '/healing' },
          { testID: 'hh-translate', icon: 'language-outline', title: 'Žiadanka a AI Prekladač', subtitle: 'Sken výmenného lístka · OCR → ľudská reč', route: '/translate' },
          { testID: 'hh-waitlist', icon: 'calendar-outline', title: 'Lovec termínov', subtitle: 'Automatický lov a rezervácia · podľa vašej polohy (GPS)', route: '/(tabs)/waitlist' },
          { testID: 'hh-arbitrage', icon: 'airplane-outline', title: 'Globálna arbitráž', subtitle: 'Operácie v 🇵🇱 🇭🇺 🇹🇷 · predikcia účtov', route: '/arbitrage' },
          { testID: 'hh-recovery', icon: 'bed-outline', title: 'Moje zotavenie (PN)', subtitle: 'ePN · vychádzky · kalkulačka nemocenského', route: '/my-recovery' },
          { testID: 'hh-physio', icon: 'body-outline', title: 'Physio-AI rehabilitácia', subtitle: 'Expertné video sprievodce · rutiny na mieru', route: '/physio' },
        ] },
        { title: '🗄 ZDRAVOTNÉ DÁTA', items: [
          { testID: 'hh-vault', icon: 'lock-closed-outline', title: 'Zdravotný trezor', subtitle: 'Dokumenty · OCR · AI preklad', choices: [
            { icon: 'folder-open-outline', label: 'Otvoriť trezor', sub: 'Zobraziť a spravovať dokumenty', route: '/(tabs)/vault' },
            { icon: 'camera-outline', label: 'Nahrať dokument + AI preklad', sub: 'Odfotiť / nahrať → ľudská reč', route: '/translate' },
            { icon: 'time-outline', label: 'Zdravotná časová os', sub: 'Všetky záznamy chronologicky', route: '/health-timeline' },
          ] },
          { testID: 'hh-timeline', icon: 'time-outline', title: 'Zdravotná časová os', subtitle: 'Vyšetrenia · história · vakcíny', route: '/health-timeline' },
          { testID: 'hh-lens', icon: 'aperture-outline', title: 'Guardian Lens', subtitle: 'Odfoť liek či nález · AI okamžite koná', route: '/lens' },
          { testID: 'hh-drop', icon: 'cloud-download-outline', title: 'Health Drop — od lekára', subtitle: 'Lekár → trezor · šifrované', route: '/health-drop' },
          { testID: 'hh-clinic-sync', icon: 'wifi-outline', title: 'Synchronizácia s klinikou', subtitle: 'Lekár „beamne" nález do trezora · QR', route: '/clinic-sync' },
          { testID: 'hh-news', icon: 'flask-outline', title: 'Medicínske novinky', subtitle: 'Prelomy krížené s tvojím trezorom · CZ/SK', route: '/medical-news' },
          { testID: 'hh-border', icon: 'airplane-outline', title: 'Cestovný certifikát', subtitle: 'Certifikát o liekoch · 14 jazykov', route: '/border-pass' },
          { testID: 'hh-ips', icon: 'globe-outline', title: 'Zdravotný sumár (IPS)', subtitle: '1 ťuk: HL7 FHIR export · EÚ / UK / USA', onPress: () => { sharePdf('/ips/summary.pdf', 'guardian_ips_summary.pdf').catch(() => {}); } },
          { testID: 'hh-bible', icon: 'book-outline', title: 'Biblia prežitia', subtitle: 'Jedným ťukom: tlačiteľné PDF kritických dát', onPress: () => { sharePdf('/survival/bible.pdf', 'guardian_survival_bible.pdf').catch(() => {}); } },
        ] },
        { title: '💊 LIEKY A TELO', items: [
          { testID: 'hh-meds', icon: 'alarm-outline', title: 'Lieky dnes', subtitle: 'Pripomienky · sken · interakcie · lekárne', choices: [
            { icon: 'aperture-outline', label: 'Skenovať obal lieku', sub: 'Guardian Lens — AI rozpozná liek', route: '/lens' },
            { icon: 'create-outline', label: 'Manuálne pridať / pripomienky', sub: 'Dávkovanie a hlasové upozornenia', route: '/meds' },
            { icon: 'git-compare-outline', label: 'Skontrolovať interakcie', sub: 'AI kontrola vašej lekárničky', route: '/medicine-cabinet' },
            { icon: 'flask-outline', label: 'Dostupnosť v lekárňach', sub: 'Lovec liekov — sklady vo vašom meste', route: '/pharmacy-hunter' },
          ] },
          { testID: 'hh-cabinet', icon: 'medkit-outline', title: 'Lekárnička', subtitle: 'Zásoby · expirácie · AI kontrola interakcií', route: '/medicine-cabinet' },
          { testID: 'hh-pharmacy', icon: 'flask-outline', title: 'Lovec liekov', subtitle: 'Dostupnosť liekov v lekárňach CZ/SK', route: '/pharmacy-hunter' },
          { testID: 'hh-bioscan', icon: 'scan-outline', title: 'Bio-skener vitálov', subtitle: 'Tep · SpO2 · tlak · stres kamerou', route: '/bioscan' },
          { testID: 'hh-longevity', icon: 'infinite-outline', title: 'Motor dlhovekosti', subtitle: 'Biologický vek · AI Bio-Hacks', route: '/longevity' },
          { testID: 'hh-mental', icon: 'shield-outline', title: 'Mentálna pevnosť', subtitle: 'Krízový audio sprievodca · akupresúra', route: '/mental-fortress' },
        ] },
      ]}
    />
  );
}
