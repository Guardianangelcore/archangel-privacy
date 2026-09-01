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
    {"id": "cpr", "title": "Heart attack – cardiac arrest", "icon": "heart", "priority": 1,
     "when": "The person is unresponsive and not breathing normally.",
     "source": "ERC Guidelines 2026 — BLS",
     "steps": [
         "Check for a response: shake their shoulders and shout loudly. No response? Continue.",
         "Tilt the head back, lift the chin. Look, listen, and feel for breathing for up to 10 seconds.",
         "Not breathing normally? Call 112 immediately and turn on speakerphone. If someone is with you, send them for the AED.",
         "Chest compressions: center of the breastbone, hands interlocked, shoulders vertical. Press down 5–6 cm deep.",
         "Rate 100–120 per minute — the rhythm of the song “Stayin' Alive”. Count aloud: 1, 2, 3…",
         "After 30 compressions, give 2 breaths (if you know how). Otherwise keep compressing without stopping.",
         "Do not stop until help arrives, the AED arrives, or the person starts breathing normally.",
         "AED available? Turn it on and do exactly what it says. Don't be afraid — you can't cause harm."],
     },
    {"id": "bleeding", "title": "Massive bleeding", "icon": "water", "priority": 2,
     "when": "Blood is spurting or flowing in a stream, and it does not stop.",
     "source": "TCCC / Stop the Bleed 2026",
     "steps": [
         "Apply direct pressure: press a clean cloth onto the wound with BOTH hands. Don't press lightly — press with your full body weight.",
         "Do not let go of the pressure. If the fabric soaks through, add another LAYER on top — never remove the bottom one.",
         "Limb + bleeding that won’t stop? Improvise a tourniquet: belt/scarf 5–7 cm ABOVE the wound, not over a joint.",
         "Tighten until the bleeding STOPS (it will hurt — that is correct). Write down the time it was applied.",
         "Call 112. Say: massive bleeding, location, number of injured.",
         "Keep the person warm (blanket/jacket) and legs slightly raised if they are not injured.",
         "Check consciousness every minute. Never loosen the tourniquet yourself."],
     },
    {"id": "choking", "title": "Choking (foreign object)", "icon": "alert-circle", "priority": 3,
     "when": "The person is holding their neck, cannot speak or cough.",
     "source": "ERC 2026 — FBAO",
     "steps": [
         "Ask: ‚Are you choking?‘ If they can cough — encourage coughing, do nothing else.",
         "Can’t cough? 5 blows between the shoulder blades: lean the person forward, heel of the hand, strong blows.",
         "Didn’t help? 5 Heimlich compressions: clasp your hands, fist above the navel, thrust sharply inward and upward.",
         "Alternate: 5 back blows ↔ 5 abdominal thrusts, until the object comes out.",
         "The person collapsed? Lay them on the ground, call 112, and start CPR (CPR protocol).",
         "Pregnant / obese person: press the chest instead of the abdomen."],
     },
    {"id": "burns", "title": "Burns", "icon": "flame", "priority": 4,
     "when": "Thermal, chemical, or electrical burn.",
     "source": "EBA Guidelines 2026",
     "steps": [
         "Stop the burning process. Electricity? First TURN OFF the source — do not touch the person before that.",
         "Cool with RUNNING lukewarm water (15–25 °C) for exactly 20 minutes. Not with ice!",
         "Remove rings and watches before it swells. Do not TEAR off stuck clothing.",
         "Cover with clean film/damp cloth. No ointments, butter, or toothpaste.",
         "Burn larger than the palm, on the face/neck, or a child/senior → 112.",
         "Monitor breathing — burned airways (hoarseness) are a critical condition."],
     },
    {"id": "shock", "title": "Shock (circulatory failure)", "icon": "pulse", "priority": 5,
     "when": "Paleness, cold sweat, rapid weak pulse, confusion.",
     "source": "ERC 2026 — First Aid",
     "steps": [
         "Lay the person on their back on a flat surface.",
         "Raise the legs to a height of ~30 cm (if they are not injured) — blood will flow to the organs.",
         "Stop visible bleeding (Massive bleeding protocol).",
         "Keep warm: cover with a blanket from below and above. Shock also kills by hypothermia.",
         "Do not give anything to drink or eat — not even 'to calm down'.",
         "Call 112. Talk to the person, keep them conscious, check their breathing every minute."],
     },
    {"id": "hypothermia", "title": "Podchladenie", "icon": "snow", "priority": 6,
     "when": "Shivering, slowed speech, apathy after being in the cold.",
     "source": "ICAR MedCom 2026",
     "steps": [
         "Get the person out of the cold environment — curtain, bunker, car, anything with a roof.",
         "Take off WET clothing and replace it with dry. Moisture draws heat away 25× faster.",
         "Wrap the entire body including the head — leave only the face. Insulate from the ground (sleeping mat, blankets).",
         "Warm sweet drinks ONLY if fully conscious. Never alcohol.",
         "Severe hypothermia (no shivering, impaired consciousness): DO NOT move abruptly — risk of cardiac arrest. Call 112.",
         "Do not warm with hot water or by massaging the limbs — warm the core, not the surface."],
     },
    {"id": "seizure", "title": "Epileptic seizure", "icon": "flash", "priority": 7,
     "when": "Whole-body convulsions, fall, unconsciousness.",
     "source": "ILAE First Aid 2026",
     "steps": [
         "Do not stop the convulsions by force. Remove hard/sharp objects from around the head.",
         "Place the head on something soft (hoodie, bag).",
         "NEVER put anything in the mouth — the tongue cannot be swallowed, that is a myth.",
         "Time the seizure. Over 5 minutes → call 112 immediately.",
         "After it ends: recovery position on the side, check breathing.",
         "The person will be confused — stay with them, speak calmly, do not leave."],
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
            "voice_note": "Voice guidance: online via Jarvis TTS. Offline: large text + step-by-step.",
            "disclaimer": "Protocols according to international guidelines 2026. They are not a substitute for emergency services — always call 112."}
