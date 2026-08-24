# Copyright © 2026 Guardian Angel. All Rights Reserved.
# This source code and its logic are the sole property of Guardian Angel.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
# Guardian Health & Angel — Founder expert content (Mental Fortress + Physio-AI guides)
# Languages: sk / cs / en / de. Informational content only (EU AI Act Art. 50).

STEP_WORD = {"sk": "Krok", "cs": "Krok", "en": "Step", "de": "Schritt"}

MENTAL_DISCLAIMERS = {
    "sk": "Toto nie je zdravotná starostlivosť ani krízová linka. Pri ohrození života volajte 112. Linka dôvery Nezábudka: 0800 800 566. (EU AI Act Art. 50 — informačný obsah)",
    "cs": "Toto není zdravotní péče ani krizová linka. Při ohrožení života volejte 112. Linka první psychické pomoci: 116 123. (EU AI Act čl. 50 — informační obsah)",
    "en": "This is not medical care or a crisis line. In a life-threatening emergency call 112. (EU AI Act Art. 50 — informational content)",
    "de": "Dies ist keine medizinische Versorgung und keine Krisenhotline. Bei Lebensgefahr rufen Sie 112. Telefonseelsorge: 0800 111 0 111. (EU-KI-Verordnung Art. 50 — informativer Inhalt)",
}

MENTAL_TECHNIQUES = {
    "sk": [
        {"id": "box", "icon": "square-outline", "title": "Dychový štvorec (Box Breathing)", "subtitle": "60 sekúnd · okamžité upokojenie nervového systému",
         "steps": ["Sadnite si rovno, uvoľnite ramená.", "Nádych nosom — počítajte do 4.", "Zadržte dych — počítajte do 4.", "Výdych ústami — počítajte do 4.", "Zadržte prázdne pľúca — počítajte do 4.", "Opakujte 4 až 6 kôl."]},
        {"id": "grounding", "icon": "earth-outline", "title": "Ukotvenie 5-4-3-2-1", "subtitle": "2 minúty · zastavenie panickej špirály",
         "steps": ["Pomenujte 5 vecí, ktoré vidíte.", "Pomenujte 4 veci, ktoré cítite dotykom.", "Pomenujte 3 zvuky, ktoré počujete.", "Pomenujte 2 vône, ktoré cítite.", "Pomenujte 1 chuť v ústach.", "Dýchajte pomaly a vnímajte, že ste tu a teraz v bezpečí."]},
        {"id": "li4", "icon": "hand-left-outline", "title": "Akupresúra LI4 (Hegu)", "subtitle": "Bod medzi palcom a ukazovákom · úzkosť a napätie",
         "steps": ["Nájdite mäkké miesto medzi palcom a ukazovákom druhej ruky.", "Stlačte palcom pevne, ale nie bolestivo.", "Masírujte krúživými pohybmi 60 sekúnd.", "Dýchajte pomaly a zhlboka.", "Vymeňte ruky a opakujte.", "Pozor: nepoužívajte počas tehotenstva."]},
        {"id": "pc6", "icon": "watch-outline", "title": "Akupresúra PC6 (Neiguan)", "subtitle": "Vnútro zápästia · panika, nevoľnosť, búšenie srdca",
         "steps": ["Otočte dlaň nahor.", "Priložte tri prsty druhej ruky pod zápästné ohyby.", "Bod je pod ukazovákom, medzi dvoma šľachami.", "Tlačte palcom jemne 60 až 90 sekúnd.", "Pri tlaku pomaly vydychujte.", "Vymeňte ruky a opakujte."]},
        {"id": "yintang", "icon": "eye-outline", "title": "Akupresúra Yintang (Tretie oko)", "subtitle": "Bod medzi obočím · okamžité upokojenie mysle",
         "steps": ["Zatvorte oči.", "Priložte ukazovák medzi obočie.", "Jemne masírujte malými krúžkami.", "Pokračujte 1 až 2 minúty.", "Sústreďte sa iba na dotyk a dych."]},
        {"id": "pmr", "icon": "body-outline", "title": "Progresívna svalová relaxácia", "subtitle": "5 minút · uvoľnenie tela pri strese a nespavosti",
         "steps": ["Zatnite päste na 5 sekúnd — potom úplne uvoľnite.", "Zatnite ramená k ušiam na 5 sekúnd — uvoľnite.", "Zatnite brucho na 5 sekúnd — uvoľnite.", "Zatnite stehná na 5 sekúnd — uvoľnite.", "Zatnite lýtka a chodidlá na 5 sekúnd — uvoľnite.", "Vnímajte teplo a ťažobu v celom tele."]},
    ],
    "cs": [
        {"id": "box", "icon": "square-outline", "title": "Dechový čtverec (Box Breathing)", "subtitle": "60 sekund · okamžité zklidnění nervového systému",
         "steps": ["Posaďte se rovně, uvolněte ramena.", "Nádech nosem — počítejte do 4.", "Zadržte dech — počítejte do 4.", "Výdech ústy — počítejte do 4.", "Zadržte prázdné plíce — počítejte do 4.", "Opakujte 4 až 6 kol."]},
        {"id": "grounding", "icon": "earth-outline", "title": "Ukotvení 5-4-3-2-1", "subtitle": "2 minuty · zastavení panické spirály",
         "steps": ["Pojmenujte 5 věcí, které vidíte.", "Pojmenujte 4 věci, které cítíte dotykem.", "Pojmenujte 3 zvuky, které slyšíte.", "Pojmenujte 2 vůně, které cítíte.", "Pojmenujte 1 chuť v ústech.", "Dýchejte pomalu a vnímejte, že jste tady a teď v bezpečí."]},
        {"id": "li4", "icon": "hand-left-outline", "title": "Akupresura LI4 (Hegu)", "subtitle": "Bod mezi palcem a ukazováčkem · úzkost a napětí",
         "steps": ["Najděte měkké místo mezi palcem a ukazováčkem druhé ruky.", "Stiskněte palcem pevně, ale ne bolestivě.", "Masírujte krouživými pohyby 60 sekund.", "Dýchejte pomalu a zhluboka.", "Vyměňte ruce a opakujte.", "Pozor: nepoužívejte během těhotenství."]},
        {"id": "pc6", "icon": "watch-outline", "title": "Akupresura PC6 (Neiguan)", "subtitle": "Vnitřní strana zápěstí · panika, nevolnost, bušení srdce",
         "steps": ["Otočte dlaň nahoru.", "Přiložte tři prsty druhé ruky pod ohyb zápěstí.", "Bod je pod ukazováčkem, mezi dvěma šlachami.", "Tlačte palcem jemně 60 až 90 sekund.", "Při tlaku pomalu vydechujte.", "Vyměňte ruce a opakujte."]},
        {"id": "yintang", "icon": "eye-outline", "title": "Akupresura Yintang (Třetí oko)", "subtitle": "Bod mezi obočím · okamžité zklidnění mysli",
         "steps": ["Zavřete oči.", "Přiložte ukazováček mezi obočí.", "Jemně masírujte malými krouživými pohyby.", "Pokračujte 1 až 2 minuty.", "Soustřeďte se pouze na dotek a dech."]},
        {"id": "pmr", "icon": "body-outline", "title": "Progresivní svalová relaxace", "subtitle": "5 minut · uvolnění těla při stresu a nespavosti",
         "steps": ["Zatněte pěsti na 5 sekund — poté zcela uvolněte.", "Zvedněte ramena k uším na 5 sekund — uvolněte.", "Zatněte břicho na 5 sekund — uvolněte.", "Zatněte stehna na 5 sekund — uvolněte.", "Zatněte lýtka a chodidla na 5 sekund — uvolněte.", "Vnímejte teplo a tíhu v celém těle."]},
    ],
    "en": [
        {"id": "box", "icon": "square-outline", "title": "Box Breathing", "subtitle": "60 seconds · instantly calms the nervous system",
         "steps": ["Sit upright and relax your shoulders.", "Inhale through the nose — count to 4.", "Hold your breath — count to 4.", "Exhale through the mouth — count to 4.", "Hold with empty lungs — count to 4.", "Repeat for 4 to 6 rounds."]},
        {"id": "grounding", "icon": "earth-outline", "title": "5-4-3-2-1 Grounding", "subtitle": "2 minutes · stops the panic spiral",
         "steps": ["Name 5 things you can see.", "Name 4 things you can feel by touch.", "Name 3 sounds you can hear.", "Name 2 things you can smell.", "Name 1 taste in your mouth.", "Breathe slowly and notice you are safe, here and now."]},
        {"id": "li4", "icon": "hand-left-outline", "title": "Acupressure LI4 (Hegu)", "subtitle": "Point between thumb and index finger · anxiety and tension",
         "steps": ["Find the soft spot between the thumb and index finger of the other hand.", "Press firmly with your thumb, but not painfully.", "Massage in circles for 60 seconds.", "Breathe slowly and deeply.", "Switch hands and repeat.", "Caution: do not use during pregnancy."]},
        {"id": "pc6", "icon": "watch-outline", "title": "Acupressure PC6 (Neiguan)", "subtitle": "Inner wrist · panic, nausea, racing heart",
         "steps": ["Turn your palm upward.", "Place three fingers of the other hand below the wrist crease.", "The point is under your index finger, between two tendons.", "Press gently with the thumb for 60 to 90 seconds.", "Exhale slowly while pressing.", "Switch hands and repeat."]},
        {"id": "yintang", "icon": "eye-outline", "title": "Acupressure Yintang (Third Eye)", "subtitle": "Point between the eyebrows · instantly calms the mind",
         "steps": ["Close your eyes.", "Place your index finger between the eyebrows.", "Massage gently in small circles.", "Continue for 1 to 2 minutes.", "Focus only on the touch and your breath."]},
        {"id": "pmr", "icon": "body-outline", "title": "Progressive Muscle Relaxation", "subtitle": "5 minutes · releases body tension from stress and insomnia",
         "steps": ["Clench your fists for 5 seconds — then fully release.", "Raise your shoulders to your ears for 5 seconds — release.", "Tense your abdomen for 5 seconds — release.", "Tense your thighs for 5 seconds — release.", "Tense calves and feet for 5 seconds — release.", "Notice the warmth and heaviness in your whole body."]},
    ],
    "de": [
        {"id": "box", "icon": "square-outline", "title": "Box-Atmung (Box Breathing)", "subtitle": "60 Sekunden · beruhigt sofort das Nervensystem",
         "steps": ["Setzen Sie sich aufrecht hin, entspannen Sie die Schultern.", "Einatmen durch die Nase — zählen Sie bis 4.", "Atem anhalten — zählen Sie bis 4.", "Ausatmen durch den Mund — zählen Sie bis 4.", "Mit leerer Lunge anhalten — zählen Sie bis 4.", "Wiederholen Sie 4 bis 6 Runden."]},
        {"id": "grounding", "icon": "earth-outline", "title": "5-4-3-2-1 Erdung", "subtitle": "2 Minuten · stoppt die Panikspirale",
         "steps": ["Nennen Sie 5 Dinge, die Sie sehen.", "Nennen Sie 4 Dinge, die Sie ertasten können.", "Nennen Sie 3 Geräusche, die Sie hören.", "Nennen Sie 2 Gerüche, die Sie wahrnehmen.", "Nennen Sie 1 Geschmack in Ihrem Mund.", "Atmen Sie langsam und spüren Sie: Sie sind hier und jetzt in Sicherheit."]},
        {"id": "li4", "icon": "hand-left-outline", "title": "Akupressur LI4 (Hegu)", "subtitle": "Punkt zwischen Daumen und Zeigefinger · Angst und Anspannung",
         "steps": ["Finden Sie die weiche Stelle zwischen Daumen und Zeigefinger der anderen Hand.", "Drücken Sie mit dem Daumen fest, aber nicht schmerzhaft.", "Massieren Sie 60 Sekunden in kreisenden Bewegungen.", "Atmen Sie langsam und tief.", "Wechseln Sie die Hände und wiederholen Sie.", "Achtung: nicht während der Schwangerschaft anwenden."]},
        {"id": "pc6", "icon": "watch-outline", "title": "Akupressur PC6 (Neiguan)", "subtitle": "Innenseite des Handgelenks · Panik, Übelkeit, Herzrasen",
         "steps": ["Drehen Sie die Handfläche nach oben.", "Legen Sie drei Finger der anderen Hand unter die Handgelenksfalte.", "Der Punkt liegt unter dem Zeigefinger, zwischen zwei Sehnen.", "Drücken Sie sanft mit dem Daumen für 60 bis 90 Sekunden.", "Atmen Sie beim Drücken langsam aus.", "Wechseln Sie die Hände und wiederholen Sie."]},
        {"id": "yintang", "icon": "eye-outline", "title": "Akupressur Yintang (Drittes Auge)", "subtitle": "Punkt zwischen den Augenbrauen · beruhigt sofort den Geist",
         "steps": ["Schließen Sie die Augen.", "Legen Sie den Zeigefinger zwischen die Augenbrauen.", "Massieren Sie sanft in kleinen Kreisen.", "Fahren Sie 1 bis 2 Minuten fort.", "Konzentrieren Sie sich nur auf die Berührung und den Atem."]},
        {"id": "pmr", "icon": "body-outline", "title": "Progressive Muskelentspannung", "subtitle": "5 Minuten · löst Körperspannung bei Stress und Schlaflosigkeit",
         "steps": ["Ballen Sie die Fäuste für 5 Sekunden — dann vollständig loslassen.", "Ziehen Sie die Schultern für 5 Sekunden zu den Ohren — loslassen.", "Spannen Sie den Bauch für 5 Sekunden an — loslassen.", "Spannen Sie die Oberschenkel für 5 Sekunden an — loslassen.", "Spannen Sie Waden und Füße für 5 Sekunden an — loslassen.", "Spüren Sie die Wärme und Schwere im ganzen Körper."]},
    ],
}

PHYSIO_GUIDES = {
    "sk": [
        {"id": "knee", "icon": "walk-outline", "title": "Obnova kolena po operácii/úraze", "subtitle": "Denná rutina 10 min · prvé 6 týždňov",
         "steps": ["Ľah na chrbte: podložte koleno zrolovaným uterákom.", "Zatlačte koleno do uteráka, stehno spevnite na 5 sekúnd — 10 opakovaní.", "Pätové kĺzanie: pomaly priťahujte pätu k zadku, len do miernej bolesti — 10 opakovaní.", "Sed na stoličke: pomaly vystrite koleno, podržte 5 sekúnd — 10 opakovaní.", "Státie s oporou: prenášajte váhu na operovanú nohu 10 sekúnd — 5 opakovaní.", "Na záver: 10 minút ľad cez utierku.", "Bolesť nad 5/10 alebo opuch = deň pauzy a konzultácia s lekárom."]},
        {"id": "panic-acupressure", "icon": "hand-left-outline", "title": "Akupresúra pri panickom záchvate", "subtitle": "Expertný protokol 3 bodov · 4 minúty",
         "steps": ["Sadnite si, nohy pevne na zemi.", "1. bod PC6: tri prsty pod zápästím, tlačte 60 sekúnd, pomaly vydychujte.", "2. bod LI4: medzi palcom a ukazovákom, krúživá masáž 60 sekúnd (nie v tehotenstve).", "3. bod Yintang: medzi obočím, jemné krúžky 60 sekúnd so zatvorenými očami.", "Ukončite dychovým štvorcom: 4-4-4-4, štyri kolá.", "Ak záchvat trvá dlhšie ako 20 minút alebo je bolesť na hrudi — volajte 112."]},
        {"id": "ergonomics", "icon": "desktop-outline", "title": "Ergonómia: chrbát a krk bez bolesti", "subtitle": "Nastavenie pracoviska + 3 cviky · prevencia",
         "steps": ["Monitor: horný okraj vo výške očí, na dĺžku paže.", "Sed: chodidlá na zemi, kolená 90°, bedrová opierka.", "Každých 30 minút vstante a prejdite sa 1 minútu.", "Cvik 1 — brada dozadu: zasuňte bradu ako 'dvojitá brada', 5 s, 10×.", "Cvik 2 — lopatky: stiahnite lopatky k sebe a dole, 5 s, 10×.", "Cvik 3 — hrudný most: ruky za hlavu, prehnite sa cez operadlo, 3 hlboké dychy, 5×.", "Bolesť vystreľujúca do ruky/nohy = vyšetrenie u lekára."]},
    ],
    "cs": [
        {"id": "knee", "icon": "walk-outline", "title": "Obnova kolena po operaci/úrazu", "subtitle": "Denní rutina 10 min · prvních 6 týdnů",
         "steps": ["Leh na zádech: podložte koleno srolovaným ručníkem.", "Zatlačte koleno do ručníku, zpevněte stehno na 5 sekund — 10 opakování.", "Patní klouzání: pomalu přitahujte patu k hýždím, jen do mírné bolesti — 10 opakování.", "Sed na židli: pomalu propněte koleno, držte 5 sekund — 10 opakování.", "Stoj s oporou: přenášejte váhu na operovanou nohu 10 sekund — 5 opakování.", "Na závěr: 10 minut led přes utěrku.", "Bolest nad 5/10 nebo otok = den pauzy a konzultace s lékařem."]},
        {"id": "panic-acupressure", "icon": "hand-left-outline", "title": "Akupresura při panické atace", "subtitle": "Expertní protokol 3 bodů · 4 minuty",
         "steps": ["Posaďte se, chodidla pevně na zemi.", "1. bod PC6: tři prsty pod zápěstím, tlačte 60 sekund, pomalu vydechujte.", "2. bod LI4: mezi palcem a ukazováčkem, krouživá masáž 60 sekund (ne v těhotenství).", "3. bod Yintang: mezi obočím, jemné kroužky 60 sekund se zavřenýma očima.", "Zakončete dechovým čtvercem: 4-4-4-4, čtyři kola.", "Pokud ataka trvá déle než 20 minut nebo je bolest na hrudi — volejte 112."]},
        {"id": "ergonomics", "icon": "desktop-outline", "title": "Ergonomie: záda a krk bez bolesti", "subtitle": "Nastavení pracoviště + 3 cviky · prevence",
         "steps": ["Monitor: horní okraj ve výšce očí, na délku paže.", "Sed: chodidla na zemi, kolena 90°, bederní opěrka.", "Každých 30 minut vstaňte a projděte se 1 minutu.", "Cvik 1 — brada dozadu: zasuňte bradu jako 'dvojitá brada', 5 s, 10×.", "Cvik 2 — lopatky: stáhněte lopatky k sobě a dolů, 5 s, 10×.", "Cvik 3 — hrudní most: ruce za hlavu, prohněte se přes opěradlo, 3 hluboké dechy, 5×.", "Bolest vystřelující do ruky/nohy = vyšetření u lékaře."]},
    ],
    "en": [
        {"id": "knee", "icon": "walk-outline", "title": "Knee Recovery After Surgery/Injury", "subtitle": "10-min daily routine · first 6 weeks",
         "steps": ["Lie on your back: place a rolled towel under the knee.", "Press the knee into the towel, tighten the thigh for 5 seconds — 10 reps.", "Heel slides: slowly pull the heel toward your buttocks, only to mild pain — 10 reps.", "Seated on a chair: slowly straighten the knee, hold 5 seconds — 10 reps.", "Standing with support: shift weight onto the operated leg for 10 seconds — 5 reps.", "Finish: 10 minutes of ice wrapped in a towel.", "Pain above 5/10 or swelling = rest day and consult your doctor."]},
        {"id": "panic-acupressure", "icon": "hand-left-outline", "title": "Acupressure for a Panic Attack", "subtitle": "Expert 3-point protocol · 4 minutes",
         "steps": ["Sit down, feet firmly on the floor.", "Point 1 PC6: three fingers below the wrist crease, press for 60 seconds, exhale slowly.", "Point 2 LI4: between thumb and index finger, circular massage for 60 seconds (not during pregnancy).", "Point 3 Yintang: between the eyebrows, gentle circles for 60 seconds with eyes closed.", "Finish with box breathing: 4-4-4-4, four rounds.", "If the attack lasts over 20 minutes or you have chest pain — call 112."]},
        {"id": "ergonomics", "icon": "desktop-outline", "title": "Ergonomics: Pain-Free Back and Neck", "subtitle": "Workstation setup + 3 exercises · prevention",
         "steps": ["Monitor: top edge at eye level, an arm's length away.", "Sitting: feet on the floor, knees at 90°, lumbar support.", "Every 30 minutes stand up and walk for 1 minute.", "Exercise 1 — chin tucks: pull the chin back into a 'double chin', 5 s, 10×.", "Exercise 2 — shoulder blades: squeeze them together and down, 5 s, 10×.", "Exercise 3 — thoracic bridge: hands behind head, arch over the backrest, 3 deep breaths, 5×.", "Pain radiating into an arm/leg = see a doctor."]},
    ],
    "de": [
        {"id": "knee", "icon": "walk-outline", "title": "Knie-Reha nach Operation/Verletzung", "subtitle": "10-Min-Tagesroutine · erste 6 Wochen",
         "steps": ["Rückenlage: legen Sie ein gerolltes Handtuch unter das Knie.", "Drücken Sie das Knie ins Handtuch, Oberschenkel 5 Sekunden anspannen — 10 Wiederholungen.", "Fersengleiten: ziehen Sie die Ferse langsam zum Gesäß, nur bis zu leichtem Schmerz — 10 Wiederholungen.", "Auf dem Stuhl: strecken Sie das Knie langsam, 5 Sekunden halten — 10 Wiederholungen.", "Stehen mit Halt: verlagern Sie das Gewicht 10 Sekunden auf das operierte Bein — 5 Wiederholungen.", "Zum Abschluss: 10 Minuten Eis im Tuch.", "Schmerz über 5/10 oder Schwellung = Pausentag und Arzt konsultieren."]},
        {"id": "panic-acupressure", "icon": "hand-left-outline", "title": "Akupressur bei Panikattacke", "subtitle": "Experten-Protokoll mit 3 Punkten · 4 Minuten",
         "steps": ["Setzen Sie sich, Füße fest auf den Boden.", "Punkt 1 PC6: drei Finger unter der Handgelenksfalte, 60 Sekunden drücken, langsam ausatmen.", "Punkt 2 LI4: zwischen Daumen und Zeigefinger, 60 Sekunden kreisend massieren (nicht in der Schwangerschaft).", "Punkt 3 Yintang: zwischen den Augenbrauen, 60 Sekunden sanfte Kreise mit geschlossenen Augen.", "Abschluss mit Box-Atmung: 4-4-4-4, vier Runden.", "Dauert die Attacke länger als 20 Minuten oder bei Brustschmerz — rufen Sie 112."]},
        {"id": "ergonomics", "icon": "desktop-outline", "title": "Ergonomie: Rücken und Nacken ohne Schmerzen", "subtitle": "Arbeitsplatz-Setup + 3 Übungen · Prävention",
         "steps": ["Monitor: Oberkante auf Augenhöhe, eine Armlänge entfernt.", "Sitzen: Füße am Boden, Knie 90°, Lendenstütze.", "Alle 30 Minuten aufstehen und 1 Minute gehen.", "Übung 1 — Kinn zurück: Kinn zum 'Doppelkinn' einziehen, 5 s, 10×.", "Übung 2 — Schulterblätter: zusammen und nach unten ziehen, 5 s, 10×.", "Übung 3 — Brustwirbel-Brücke: Hände hinter den Kopf, über die Lehne strecken, 3 tiefe Atemzüge, 5×.", "In Arm/Bein ausstrahlender Schmerz = ärztliche Untersuchung."]},
    ],
}
