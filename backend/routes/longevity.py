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
        raise HTTPException(409, "profile_missing: First, save the longevity profile (year of birth, height, weight).")
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
            add("BMI", 2.0, f"BMI {bmi:.1f} — obesity accelerates cellular aging.",
                "Bio-Hack: 300 kcal/day deficit + 8,000 steps = −1 year of bio-age in ~3 months.")
        elif bmi >= 27:
            add("BMI", 1.0, f"BMI {bmi:.1f} — light overweight.",
                "Bio-Hack: protein 1.6 g/kg + intermittent 12/12 eating window.")
        elif 20 <= bmi <= 24.9:
            add("BMI", -1.0, f"BMI {bmi:.1f} — optimal body composition.")
    # Smoking
    if prof.get("smoker"):
        add("Smoking", 4.0, "The strongest single accelerator of vascular aging.",
            "Bio-Hack: 8 weeks without nicotine returns ~2 years to the vessels. Set up Angel Mode support.")
    # Activity
    lvl = prof.get("activity_level", "medium")
    if lvl == "high":
        add("Activity", -2.0, "Regular training — VO2max is the top predictor of longevity.")
    elif lvl == "low":
        add("Activity", 2.0, "Sedentary routine slows mitochondria.",
            "Bio-Hack: 3× weekly 30 min zone 2 (brisk walking) = −1.5 years in half a year.")
    # Steps (7-day wellness vitals)
    vitals = await db.wellness_vitals.find({"user_id": uid}, {"_id": 0}).sort("date", -1).to_list(7)
    steps_vals = [v["steps"] for v in vitals if v.get("steps")]
    if steps_vals:
        avg_steps = sum(steps_vals) / len(steps_vals)
        if avg_steps >= 7000:
            add("Steps", -1.5, f"Average {avg_steps:.0f}/day — excellent baseline activity.")
        elif avg_steps < 3000:
            add("Steps", 1.5, f"Average {avg_steps:.0f}/day — low movement.",
                "Bio-Hack: a 10-minute walk after each meal (3×/day) adds ~3,000 steps.")
    # Resting heart rate
    hr_vals = [v["heart_rate"] for v in vitals if v.get("heart_rate")]
    if hr_vals:
        avg_hr = sum(hr_vals) / len(hr_vals)
        if avg_hr <= 62:
            add("Resting heart rate", -1.0, f"{avg_hr:.0f} bpm — athlete’s heart.")
        elif avg_hr >= 80:
            add("Resting heart rate", 1.5, f"{avg_hr:.0f} bpm — elevated cardiac load.",
                "Bio-Hack: 5 minutes of box breathing daily (Mental Fortress) lowers heart rate by 4–6 bpm.")
    # Conditions
    prof_e = await db.emergency_profiles.find_one({"user_id": uid}, {"_id": 0, "conditions": 1}) or {}
    conds = [c for c in (prof_e.get("conditions") or "").replace(";", ",").split(",") if c.strip()]
    if conds:
        add("Diagnoses", min(2.0, 0.5 * len(conds)), f"{len(conds)} chronic records in the profile.",
            "Bio-Hack: preventive checkup + Waitlist Hunter to monitor inflammation markers (CRP).")
    # Stress (latest bioscan)
    scan = await db.bioscan_results.find_one({"user_id": uid}, {"_id": 0}, sort=[("at", -1)])
    if scan:
        if scan.get("stress_level") == "high":
            add("Stres (Bio-Scan)", 1.0, f"Stress index {scan['stress_index']:.0f} — cortisol load.",
                "Bio-Hack: 20 minutes without screens before sleep + magnesium in the evening.")
        elif scan.get("stress_level") == "low":
            add("Stres (Bio-Scan)", -0.5, "Low stress index — the nervous system is regenerating.")

    delta = sum(f["impact_years"] for f in factors)
    bio_age = round(chrono + delta, 1)
    if not hacks:
        hacks = ["Bio-Hack: keep the routine — today’s data show no aging accelerator."]
    rec = {"score_id": uuid.uuid4().hex, "user_id": uid,
           "chronological_age": chrono, "biological_age": bio_age, "delta_years": round(delta, 1),
           "verdict": ("YOUNGER THAN THE CALENDAR 🟢" if delta < -0.5 else
                       "IN BALANCE ⚪" if delta <= 0.5 else "YOU'RE AGING FASTER 🔴"),
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
    out["disclaimer"] = "An estimate based on available data — this is not a medical diagnosis (EU AI Act Art. 50)."
    return out
