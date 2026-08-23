// Simple i18n dictionary for Guardian Health & Angel
export type Lang = 'sk' | 'cs' | 'en' | 'de';

export const LANG_NAMES: Record<Lang, string> = {
  sk: 'Slovenčina',
  cs: 'Čeština',
  en: 'English',
  de: 'Deutsch',
};

type Dict = Record<string, Record<Lang, string>>;

export const T: Dict = {
  app_name: { sk: 'Guardian Health & Angel', cs: 'Guardian Health & Angel', en: 'Guardian Health & Angel', de: 'Guardian Health & Angel' },
  author_credit: { sk: 'Vízia: Guardian Angel', cs: 'Vize: Guardian Angel', en: 'Vision by Guardian Angel', de: 'Vision von Guardian Angel' },
  sign_in_google: { sk: 'Prihlásiť sa cez Google', cs: 'Přihlásit se přes Google', en: 'Sign in with Google', de: 'Mit Google anmelden' },
  choose_language: { sk: 'Vyberte jazyk', cs: 'Vyberte jazyk', en: 'Choose language', de: 'Sprache wählen' },
  standard_mode: { sk: 'Štandardný režim', cs: 'Standardní režim', en: 'Standard Mode', de: 'Standard-Modus' },
  angel_mode: { sk: 'Angel režim', cs: 'Angel režim', en: 'Angel Mode', de: 'Angel-Modus' },
  home: { sk: 'Domov', cs: 'Domů', en: 'Home', de: 'Start' },
  vault: { sk: 'Trezor', cs: 'Trezor', en: 'Vault', de: 'Tresor' },
  waitlist: { sk: 'Termíny', cs: 'Termíny', en: 'Waitlist', de: 'Wartelisten' },
  profile: { sk: 'Profil', cs: 'Profil', en: 'Profile', de: 'Profil' },
  sos: { sk: 'SOS', cs: 'SOS', en: 'SOS', de: 'SOS' },
  call_family: { sk: 'Zavolať rodinu', cs: 'Zavolat rodinu', en: 'Call Family', de: 'Familie anrufen' },
  medications: { sk: 'Lieky', cs: 'Léky', en: 'Medications', de: 'Medikamente' },
  documents: { sk: 'Dokumenty', cs: 'Dokumenty', en: 'Documents', de: 'Dokumente' },
  upload_doc: { sk: 'Nahrať dokument', cs: 'Nahrát dokument', en: 'Upload document', de: 'Dokument hochladen' },
  translate: { sk: 'AI Preklad', cs: 'AI Překlad', en: 'AI Translate', de: 'KI-Übersetzung' },
  emergency_qr: { sk: 'Núdzový QR', cs: 'Nouzový QR', en: 'Emergency QR', de: 'Notfall-QR' },
  im_ok: { sk: 'SOM V PORIADKU', cs: 'JSEM V POŘÁDKU', en: "I'M OK", de: 'MIR GEHT ES GUT' },
  get_help_now: { sk: 'Pomoc HNEĎ', cs: 'Pomoc HNED', en: 'Get Help Now', de: 'Sofort Hilfe' },
  fall_detected: { sk: 'Detekovaný pád', cs: 'Detekován pád', en: 'Fall detected', de: 'Sturz erkannt' },
  add: { sk: 'Pridať', cs: 'Přidat', en: 'Add', de: 'Hinzufügen' },
  scan: { sk: 'Skenovať', cs: 'Skenovat', en: 'Scan now', de: 'Jetzt scannen' },
  slot_found: { sk: 'Termín nájdený!', cs: 'Termín nalezen!', en: 'Slot found!', de: 'Termin gefunden!' },
  no_documents: { sk: 'Trezor je prázdny', cs: 'Trezor je prázdný', en: 'Your vault is empty', de: 'Ihr Tresor ist leer' },
  translating: { sk: 'Prekladám…', cs: 'Překládám…', en: 'Translating…', de: 'Übersetze…' },
  paste_medical: { sk: 'Vložte lekársku správu…', cs: 'Vložte lékařskou zprávu…', en: 'Paste your medical report…', de: 'Medizinischen Bericht einfügen…' },
  logout: { sk: 'Odhlásiť', cs: 'Odhlásit', en: 'Log out', de: 'Abmelden' },
  donor_card: { sk: 'Darcovský preukaz', cs: 'Dárcovský průkaz', en: 'Donor Card', de: 'Spenderausweis' },
  blood_type: { sk: 'Krvná skupina', cs: 'Krevní skupina', en: 'Blood type', de: 'Blutgruppe' },
  allergies: { sk: 'Alergie', cs: 'Alergie', en: 'Allergies', de: 'Allergien' },
  emergency_contact: { sk: 'Kontakt v núdzi', cs: 'Kontakt v nouzi', en: 'Emergency contact', de: 'Notfallkontakt' },
  save: { sk: 'Uložiť', cs: 'Uložit', en: 'Save', de: 'Speichern' },
  cancel: { sk: 'Zrušiť', cs: 'Zrušit', en: 'Cancel', de: 'Abbrechen' },
  loading: { sk: 'Dešifrujem identitu…', cs: 'Dešifruji identitu…', en: 'Decrypting identity…', de: 'Identität entschlüsseln…' },
  specialty: { sk: 'Špecializácia', cs: 'Specializace', en: 'Specialty', de: 'Fachrichtung' },
  clinic: { sk: 'Klinika', cs: 'Klinika', en: 'Clinic', de: 'Klinik' },
  city: { sk: 'Mesto', cs: 'Město', en: 'City', de: 'Stadt' },
  current_date: { sk: 'Aktuálny termín', cs: 'Aktuální termín', en: 'Current date', de: 'Aktueller Termin' },
  target_before: { sk: 'Cieľ do', cs: 'Cíl do', en: 'Target before', de: 'Ziel vor' },
  no_waitlist: { sk: 'Zatiaľ žiadne sledované termíny', cs: 'Zatím žádné sledované termíny', en: 'No tracked appointments yet', de: 'Noch keine überwachten Termine' },
  scanning: { sk: 'Skenujem…', cs: 'Skenuji…', en: 'Scanning…', de: 'Suche…' },
  simulate_fall: { sk: 'Simulovať pád', cs: 'Simulovat pád', en: 'Simulate fall', de: 'Sturz simulieren' },
  colors: { sk: '', cs: '', en: '', de: '' },
};

export function t(key: string, lang: Lang): string {
  return T[key]?.[lang] ?? T[key]?.en ?? key;
}
