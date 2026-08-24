# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""AI Tactical Medic — voice-guided emergency trauma module (Sentinel tier).

Step-by-step life-saving protocols based on 2026 international guidelines
(ERC 2026 / AHA / TCCC civilian adaptation). The full protocol library is
returned in one payload so the client caches it and works 100% offline.
Ethical override: during a VERIFIED emergency the paywall is bypassed."""
from fastapi import Header
from typing import Optional

from core import api, get_current_user

PROTOCOLS = [
    {"id": "cpr", "title": "KPR — Zástava srdca", "icon": "heart", "priority": 1,
     "when": "Osoba nereaguje a nedýcha normálne.",
     "source": "ERC Guidelines 2026 — BLS",
     "steps": [
         "Skontroluj reakciu: zatras ramenami a hlasno zavolaj. Žiadna odpoveď? Pokračuj.",
         "Zakloň hlavu, zdvihni bradu. Pozeraj, počúvaj a vnímaj dych max. 10 sekúnd.",
         "Nedýcha normálne? Okamžite volaj 112 a zapni hlasitý odposluch. Ak je pri tebe niekto, pošli ho po AED.",
         "Stlačenia hrudníka: stred hrudnej kosti, prepletené dlane, ramená kolmo. Stláčaj 5–6 cm do hĺbky.",
         "Tempo 100–120 za minútu — rytmus piesne „Stayin' Alive“. Počítaj nahlas: 1, 2, 3…",
         "Po 30 stlačeniach 2 vdychy (ak vieš). Inak stláčaj bez prestávky ďalej.",
         "Neprestávaj, kým nepríde pomoc, AED, alebo osoba nezačne normálne dýchať.",
         "AED k dispozícii? Zapni ho a rob presne to, čo hovorí. Neboj sa — nemôžeš ublížiť."],
     },
    {"id": "bleeding", "title": "Masívne krvácanie", "icon": "water", "priority": 2,
     "when": "Krv strieka alebo tečie prúdom, nezastavuje sa.",
     "source": "TCCC / Stop the Bleed 2026",
     "steps": [
         "Priama sila: pritlač na ranu čistú tkaninu OBOMA rukami. Netlač málo — tlač celou váhou.",
         "Nepúšťaj tlak. Ak tkanina presiakne, pridaj ďalšiu VRSTVU navrch — nikdy neodstraňuj spodnú.",
         "Končatina + krvácanie neprestáva? Improvizuj turniket: opasok/šatka 5–7 cm NAD ranou, nie cez kĺb.",
         "Uťahuj, kým krvácanie NEZASTANE (bude to bolieť — je to správne). Zapíš si čas naloženia.",
         "Volaj 112. Povedz: masívne krvácanie, poloha, počet zranených.",
         "Drž osobu v teple (deka/bunda) a nohy mierne hore, ak nie sú zranené.",
         "Kontroluj vedomie každú minútu. Turniket NIKDY nepovoľuj sám."],
     },
    {"id": "choking", "title": "Dusenie (cudzí predmet)", "icon": "alert-circle", "priority": 3,
     "when": "Osoba sa drží za krk, nemôže hovoriť ani kašľať.",
     "source": "ERC 2026 — FBAO",
     "steps": [
         "Opýtaj sa: „Dusíš sa?“ Ak môže kašľať — povzbudzuj kašeľ, nič iné nerob.",
         "Nemôže kašľať? 5 úderov medzi lopatky: predkloň osobu, päta dlane, silné údery.",
         "Nepomohlo? 5 Heimlichových stlačení: obojmi rukami päsť nad pupok, prudko dnu a hore.",
         "Striedaj: 5 úderov do chrbta ↔ 5 stlačení brucha, kým predmet nevyletí.",
         "Osoba odpadla? Polož ju na zem, volaj 112 a začni KPR (protokol KPR).",
         "Tehotná / obézna osoba: stláčaj hrudník namiesto brucha."],
     },
    {"id": "burns", "title": "Popáleniny", "icon": "flame", "priority": 4,
     "when": "Tepelné, chemické alebo elektrické popálenie.",
     "source": "EBA Guidelines 2026",
     "steps": [
         "Zastav proces horenia. Elektrina? Najprv VYPNI zdroj — nedotýkaj sa osoby skôr.",
         "Chlaď TEČÚCOU vlažnou vodou (15–25 °C) presne 20 minút. Nie ľadom!",
         "Zlož prstene a hodinky skôr, než to opuchne. Prilepené oblečenie NESTRHÁVAJ.",
         "Prekry čistou fóliou/vlhkou tkaninou. Žiadne masti, maslo ani zubná pasta.",
         "Popálenina väčšia ako dlaň, na tvári/krku, alebo dieťa/senior → 112.",
         "Sleduj dýchanie — popálené dýchacie cesty (chrapot) sú kritický stav."],
     },
    {"id": "shock", "title": "Šok (obehové zlyhanie)", "icon": "pulse", "priority": 5,
     "when": "Bledosť, studený pot, zrýchlený slabý pulz, zmätenosť.",
     "source": "ERC 2026 — First Aid",
     "steps": [
         "Polož osobu na chrbát na rovnú podložku.",
         "Zdvihni nohy do výšky ~30 cm (ak nie sú zranené) — krv poputuje k orgánom.",
         "Zastav viditeľné krvácanie (protokol Masívne krvácanie).",
         "Teplo: prikry dekou zospodu aj zvrchu. Šok zabíja aj podchladením.",
         "Nedávaj nič piť ani jesť — ani „na upokojenie“.",
         "Volaj 112. Hovor s osobou, udržuj ju pri vedomí, kontroluj dych každú minútu."],
     },
    {"id": "hypothermia", "title": "Podchladenie", "icon": "snow", "priority": 6,
     "when": "Trasenie, spomalená reč, apatia po pobyte v chlade.",
     "source": "ICAR MedCom 2026",
     "steps": [
         "Dostaň osobu zo studeného prostredia — záves, bunker, auto, čokoľvek so strechou.",
         "Vyzleč MOKRÉ oblečenie a nahraď suchým. Vlhkosť odvádza teplo 25× rýchlejšie.",
         "Zabaľ celé telo vrátane hlavy — nechaj len tvár. Izoluj od zeme (karimatka, deky).",
         "Teplé sladké nápoje LEN pri plnom vedomí. Nikdy alkohol.",
         "Ťažké podchladenie (bez trasenia, porucha vedomia): NEHÝB prudko — riziko zástavy. Volaj 112.",
         "Nezohrievaj horúcou vodou ani masážou končatín — zohrieva sa jadro, nie povrch."],
     },
    {"id": "seizure", "title": "Epileptický záchvat", "icon": "flash", "priority": 7,
     "when": "Kŕče celého tela, pád, bezvedomie.",
     "source": "ILAE First Aid 2026",
     "steps": [
         "Nezastavuj kŕče násilím. Odstráň tvrdé/ostré predmety z okolia hlavy.",
         "Podlož hlavu niečím mäkkým (mikina, taška).",
         "NIKDY nedávaj nič do úst — jazyk si neprehltne, to je mýtus.",
         "Meraj čas záchvatu. Nad 5 minút → volaj 112 okamžite.",
         "Po odznení: stabilizovaná poloha na boku, skontroluj dýchanie.",
         "Osoba bude zmätená — zostaň pri nej, hovor pokojne, neodchádzaj."],
     },
]

@api.get("/medic/protocols")
async def medic_protocols(authorization: Optional[str] = Header(None)):
    """Full offline-cacheable protocol library. Sentinel tier — with a
    life-safety override: verified active emergency unlocks it for anyone."""
    user = await get_current_user(authorization)
    from routes.paramedic import _verified_emergency
    override = await _verified_emergency(user["user_id"])
    if not override:
        from routes.subscription import require_tier
        await require_tier(user, "sentinel", "AI Tactical Medic")
    return {"protocols": PROTOCOLS, "offline_cacheable": True,
            "emergency_override": override,
            "voice_note": "Hlasové vedenie: online cez Jarvis TTS. Offline: veľké písmo + krokovanie.",
            "disclaimer": "Protokoly podľa medzinárodných smerníc 2026. Nie sú náhradou záchrannej služby — vždy volajte 112."}
