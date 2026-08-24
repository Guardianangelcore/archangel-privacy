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
            raise HTTPException(402, "payment_required: Bio-Scanner = 5 GA-T za sken, alebo Sentinel (€149/mes.) neobmedzene. Aktivujte 7-dňový trial zadarmo v Subscription.")
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
    return clean(rec)

@api.get("/bioscan/history")
async def bioscan_history(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows = await db.bioscan_results.find({"user_id": user["user_id"]}, {"_id": 0}).sort("at", -1).to_list(20)
    return {"scans": rows,
            "note": "SIMULÁCIA — rPPG signál z kamery sa aktivuje v natívnom CV builde (Phase 3). Hodnoty sú orientačné, nie diagnóza."}
