# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Longevity Engine — Bio-Age Dashboard (Sentinel tier).

Cross-references Vault/wellness data to compute biological vs. chronological
age and prescribes rule-based AI 'Bio-Hacks' for recovery and longevity."""
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid

from core import api, db, clean, get_current_user

class LongevityProfileIn(BaseModel):
    birth_year: int
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    smoker: bool = False
    activity_level: str = "medium"  # low | medium | high

@api.put("/longevity/profile")
async def longevity_profile(body: LongevityProfileIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    year = datetime.now(timezone.utc).year
    if not (year - 120 <= body.birth_year <= year - 10):
        raise HTTPException(400, "birth_year mimo rozsahu")
    if body.activity_level not in ("low", "medium", "high"):
        raise HTTPException(400, "activity_level must be low|medium|high")
    doc = {"user_id": user["user_id"], **body.model_dump(), "updated_at": datetime.now(timezone.utc)}
    await db.longevity_profiles.update_one({"user_id": user["user_id"]}, {"$set": doc}, upsert=True)
    return clean(doc)

@api.get("/longevity/bioage")
async def longevity_bioage(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    from routes.subscription import require_tier
    await require_tier(user, "sentinel", "Longevity Engine")
    uid = user["user_id"]
    prof = await db.longevity_profiles.find_one({"user_id": uid}, {"_id": 0})
    if not prof:
        raise HTTPException(409, "profile_missing: Najprv uložte longevity profil (rok narodenia, výška, váha).")
    now = datetime.now(timezone.utc)
    chrono = now.year - prof["birth_year"]
    factors, hacks = [], []

    def add(factor: str, impact: float, note: str, hack: Optional[str] = None):
        factors.append({"factor": factor, "impact_years": round(impact, 1), "note": note})
        if hack and impact > 0:
            hacks.append(hack)

    # BMI
    if prof.get("height_cm") and prof.get("weight_kg"):
        bmi = prof["weight_kg"] / ((prof["height_cm"] / 100) ** 2)
        if bmi >= 30:
            add("BMI", 2.0, f"BMI {bmi:.1f} — obezita zrýchľuje bunkové starnutie.",
                "Bio-Hack: deficit 300 kcal/deň + 8 000 krokov = −1 rok bio-veku za ~3 mesiace.")
        elif bmi >= 27:
            add("BMI", 1.0, f"BMI {bmi:.1f} — mierna nadváha.",
                "Bio-Hack: proteín 1.6 g/kg + prerušované 12/12 okno stravovania.")
        elif 20 <= bmi <= 24.9:
            add("BMI", -1.0, f"BMI {bmi:.1f} — optimálna telesná kompozícia.")
    # Smoking
    if prof.get("smoker"):
        add("Fajčenie", 4.0, "Najsilnejší jednotlivý akcelerátor starnutia ciev.",
            "Bio-Hack: 8 týždňov bez nikotínu vráti cievam ~2 roky. Nastavte si Angel Mode podporu.")
    # Activity
    lvl = prof.get("activity_level", "medium")
    if lvl == "high":
        add("Aktivita", -2.0, "Pravidelný tréning — VO2max je top prediktor dlhovekosti.")
    elif lvl == "low":
        add("Aktivita", 2.0, "Sedavý režim spomaľuje mitochondrie.",
            "Bio-Hack: 3× týždenne 30 min zóna 2 (svižná chôdza) = −1.5 roka do pol roka.")
    # Steps (7-day wellness vitals)
    vitals = await db.wellness_vitals.find({"user_id": uid}, {"_id": 0}).sort("date", -1).to_list(7)
    steps_vals = [v["steps"] for v in vitals if v.get("steps")]
    if steps_vals:
        avg_steps = sum(steps_vals) / len(steps_vals)
        if avg_steps >= 7000:
            add("Kroky", -1.5, f"Priemer {avg_steps:.0f}/deň — výborná bazálna aktivita.")
        elif avg_steps < 3000:
            add("Kroky", 1.5, f"Priemer {avg_steps:.0f}/deň — málo pohybu.",
                "Bio-Hack: 10-min prechádzka po každom jedle (3×/deň) pridá ~3 000 krokov.")
    # Resting heart rate
    hr_vals = [v["heart_rate"] for v in vitals if v.get("heart_rate")]
    if hr_vals:
        avg_hr = sum(hr_vals) / len(hr_vals)
        if avg_hr <= 62:
            add("Pokojový tep", -1.0, f"{avg_hr:.0f} bpm — športové srdce.")
        elif avg_hr >= 80:
            add("Pokojový tep", 1.5, f"{avg_hr:.0f} bpm — zvýšená kardiálna záťaž.",
                "Bio-Hack: 5 min box-breathing denne (Mental Fortress) znižuje tep o 4–6 bpm.")
    # Conditions
    prof_e = await db.emergency_profiles.find_one({"user_id": uid}, {"_id": 0, "conditions": 1}) or {}
    conds = [c for c in (prof_e.get("conditions") or "").replace(";", ",").split(",") if c.strip()]
    if conds:
        add("Diagnózy", min(2.0, 0.5 * len(conds)), f"{len(conds)} chronických záznamov v profile.",
            "Bio-Hack: preventívna prehliadka + Waitlist Hunter na kontrolu markerov zápalu (CRP).")
    # Stress (latest bioscan)
    scan = await db.bioscan_results.find_one({"user_id": uid}, {"_id": 0}, sort=[("at", -1)])
    if scan:
        if scan.get("stress_level") == "high":
            add("Stres (Bio-Scan)", 1.0, f"Stress index {scan['stress_index']:.0f} — kortizolová záťaž.",
                "Bio-Hack: 20 min bez obrazoviek pred spánkom + horčík večer.")
        elif scan.get("stress_level") == "low":
            add("Stres (Bio-Scan)", -0.5, "Nízky stresový index — nervový systém regeneruje.")

    delta = sum(f["impact_years"] for f in factors)
    bio_age = round(chrono + delta, 1)
    if not hacks:
        hacks = ["Bio-Hack: udržujte rutinu — dnešné dáta neukazujú žiadny akcelerátor starnutia."]
    rec = {"score_id": uuid.uuid4().hex, "user_id": uid,
           "chronological_age": chrono, "biological_age": bio_age, "delta_years": round(delta, 1),
           "verdict": ("MLADŠÍ AKO KALENDÁR 🟢" if delta < -0.5 else
                       "V ROVNOVÁHE ⚪" if delta <= 0.5 else "STARNETE RÝCHLEJŠIE 🔴"),
           "factors": factors, "bio_hacks": hacks[:5], "at": now}
    await db.longevity_scores.insert_one(rec.copy())
    history = await db.longevity_scores.find({"user_id": uid}, {"_id": 0, "biological_age": 1, "at": 1}).sort("at", -1).to_list(10)
    try:
        from routes.swarm import bus_publish
        await bus_publish("longevity.bioage_computed", "health_sentinel",
                          {"chrono": chrono, "bio": bio_age, "delta": round(delta, 1)})
    except Exception:
        pass
    out = clean(rec)
    out["history"] = history
    out["disclaimer"] = "Odhad na základe dostupných dát — nie je lekárska diagnóza (EU AI Act čl. 50)."
    return out
