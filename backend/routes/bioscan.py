# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Vitals Bio-Scanner — non-invasive vital-sign estimation via camera/flash
photoplethysmography (rPPG). PLACEHOLDER computer-vision logic: the signal
pipeline is simulated deterministically until the native CV build (Phase 3).
Monetization: Sentinel unlimited · others 5 GA-T per scan."""
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid, random, hashlib

from core import api, db, clean, get_current_user

class ScanIn(BaseModel):
    duration_s: int = 10
    samples: Optional[List[float]] = None  # luminance series from camera (rPPG placeholder)
    pay_gat: bool = False

def _estimate(uid: str, samples: Optional[List[float]]) -> dict:
    """rPPG placeholder: derive plausible vitals from the sample variance
    (or a per-scan seed). Real FFT peak-detection lands with the CV build."""
    if samples and len(samples) >= 8:
        var = sum((s - sum(samples) / len(samples)) ** 2 for s in samples) / len(samples)
        seed = int(var * 1000) + len(samples)
    else:
        seed = int(hashlib.sha256(f"{uid}{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest(), 16)
    rng = random.Random(seed)
    hr = rng.randint(58, 92)
    spo2 = rng.randint(95, 99)
    stress = round(min(100, max(5, (hr - 55) * 1.8 + rng.randint(-8, 8))), 0)
    stress_level = "low" if stress < 35 else ("moderate" if stress < 65 else "high")
    bp_sys = rng.randint(108, 138)
    bp_dia = rng.randint(68, 88)
    return {"heart_rate": hr, "spo2": spo2, "stress_index": stress, "stress_level": stress_level,
            "bp_estimate": f"{bp_sys}/{bp_dia}", "hrv_ms": rng.randint(28, 72)}

@api.post("/bioscan/measure")
async def bioscan_measure(body: ScanIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    from routes.subscription import get_active_tier, TIER_RANK, record_revenue
    tier = await get_active_tier(uid)
    if TIER_RANK.get(tier, 0) >= TIER_RANK["sentinel"]:
        access = "tier"
    else:
        if not body.pay_gat:
            raise HTTPException(402, "payment_required: Bio-Scanner = 5 GA-T per scan, or unlimited with Sentinel (€149/mo.). Activate the free 7-day trial in Subscription.")
        from routes.token import token_spend, SpendIn
        await token_spend(SpendIn(item="bioscan_single"), authorization)  # raises 402 if insufficient
        await record_revenue("payperuse", 0.5, uid, {"item": "bioscan_single", "gat": 5})
        access = "gat"
    vitals = _estimate(uid, body.samples)
    rec = {"scan_id": uuid.uuid4().hex, "user_id": uid, **vitals,
           "duration_s": body.duration_s, "method": "rPPG camera/flash (placeholder CV)",
           "access": access, "simulated": True, "at": datetime.now(timezone.utc)}
    await db.bioscan_results.insert_one(rec.copy())
    try:
        from routes.swarm import bus_publish
        await bus_publish("bioscan.measured", "health_sentinel",
                          {"hr": vitals["heart_rate"], "spo2": vitals["spo2"], "stress": vitals["stress_level"]})
    except Exception:
        pass
    try:
        from routes.agent import award_xp
        await award_xp(uid, 15, "bioscan")
    except Exception:
        pass
    return clean(rec)

@api.get("/bioscan/history")
async def bioscan_history(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.bioscan_results.find({"user_id": user["user_id"]}, {"_id": 0}).sort("at", -1).to_list(20)
    return {"scans": rows,
            "note": "SIMULATION — the camera rPPG signal activates in the native CV build (Phase 3). Values are indicative, not a diagnosis."}

# --------- MANUAL CALIBRATION (Wheel-Picker) — BP / glucose / HR ---------
class CalibrateIn(BaseModel):
    systolic: Optional[int] = None      # mmHg 70-250
    diastolic: Optional[int] = None     # mmHg 40-150
    glucose_mmol: Optional[float] = None  # 2.0-30.0
    heart_rate: Optional[int] = None    # 30-220

@api.post("/bioscan/calibrate")
async def bioscan_calibrate(body: CalibrateIn, authorization: Optional[str] = Header(None)):
    """Manual reading calibration from the premium wheel-picker (no typing)."""
    user = await get_current_user(authorization)
    if body.systolic is not None and not (70 <= body.systolic <= 250):
        raise HTTPException(400, "systolic out of range (70-250)")
    if body.diastolic is not None and not (40 <= body.diastolic <= 150):
        raise HTTPException(400, "diastolic out of range (40-150)")
    if body.glucose_mmol is not None and not (2.0 <= body.glucose_mmol <= 30.0):
        raise HTTPException(400, "glucose out of range (2.0-30.0)")
    if body.heart_rate is not None and not (30 <= body.heart_rate <= 220):
        raise HTTPException(400, "heart_rate out of range (30-220)")
    if body.systolic is None and body.glucose_mmol is None and body.heart_rate is None:
        raise HTTPException(400, "Provide at least one reading")
    rec = {"scan_id": uuid.uuid4().hex, "user_id": user["user_id"],
           "method": "manual_calibration (wheel-picker)", "access": "free", "simulated": False,
           "at": datetime.now(timezone.utc)}
    if body.systolic is not None and body.diastolic is not None:
        rec["bp_estimate"] = f"{body.systolic}/{body.diastolic}"
        rec["bp_manual"] = True
    if body.glucose_mmol is not None:
        rec["glucose_mmol"] = round(body.glucose_mmol, 1)
    if body.heart_rate is not None:
        rec["heart_rate"] = body.heart_rate
    await db.bioscan_results.insert_one(rec.copy())
    try:
        from routes.agent import award_xp
        await award_xp(user["user_id"], 10, "calibration")
    except Exception:
        pass
    return clean(rec)
