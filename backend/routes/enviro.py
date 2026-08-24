# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""Environmental Threat Fusion — Blackout Protocol × device sensors × P2P mesh.

Users report environmental hazards (heat, radiation patterns, air quality,
bio-indicators). Reports fuse into consensus threats; the Autonomous Swarm
escalates confirmed threats to the whole mesh (simulated broadcast)."""
from fastapi import HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid

from core import api, db, clean, get_current_user

THREAT_KINDS = {
    "heat": {"label": "Extrémne teplo", "icon": "sunny", "sensor": "Teplotný senzor / batéria zariadenia",
             "guidance": "Hydratácia 3 l/deň, tieň 11:00–16:00, kontrolujte seniorov 2× denne."},
    "cold": {"label": "Extrémny mráz", "icon": "snow", "sensor": "Teplotný senzor zariadenia",
             "guidance": "Vrstvenie, chráňte hlavu/krk, pozor na podchladenie (Tactical Medic)."},
    "radiation": {"label": "Radiačný vzorec", "icon": "nuclear", "sensor": "CMOS kamera (gama šum) — placeholder",
                  "guidance": "Zostaňte vnútri, utesnite okná, jód len na pokyn autorít. Sledujte mesh."},
    "air": {"label": "Kvalita vzduchu / dym", "icon": "cloud", "sensor": "Barometer + mikrofón (kašeľ index)",
            "guidance": "FFP2/FFP3 vonku, čistička alebo mokré plachty vnútri, obmedzte fyzickú záťaž."},
    "bio": {"label": "Bio-indikátor (epidémia)", "icon": "bug", "sensor": "Anonymný symptóm-mesh komunity",
            "guidance": "Hygiena rúk, rúško v interiéroch, sledujte teplotu 2× denne, izolujte symptómy."},
    "flood": {"label": "Povodeň / voda", "icon": "water", "sensor": "GPS + komunitné hlásenia",
              "guidance": "Presuňte sa vyššie, nevstupujte do prúdiacej vody ani autom."},
}

class ThreatReportIn(BaseModel):
    kind: str
    severity: int = 3  # 1-5
    city: str = ""
    note: Optional[str] = ""
    lat: Optional[float] = None
    lng: Optional[float] = None

@api.post("/enviro/report")
async def enviro_report(body: ThreatReportIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if body.kind not in THREAT_KINDS:
        raise HTTPException(400, f"kind must be one of {list(THREAT_KINDS)}")
    sev = max(1, min(5, body.severity))
    rec = {"report_id": uuid.uuid4().hex, "user_id": user["user_id"],
           "reporter": (user.get("name") or "Guardian").split(" ")[0],
           "kind": body.kind, "severity": sev, "city": body.city.strip()[:60],
           "note": (body.note or "")[:200], "lat": body.lat, "lng": body.lng,
           "mesh_hop": "P2P mesh (simulované šírenie)", "at": datetime.now(timezone.utc)}
    await db.enviro_reports.insert_one(rec.copy())
    try:
        from routes.swarm import bus_publish
        await bus_publish("enviro.threat_reported", "security_sentinel",
                          {"kind": body.kind, "severity": sev, "city": rec["city"]})
    except Exception:
        pass
    return clean(rec)

@api.get("/enviro/threats")
async def enviro_threats(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    rows = await db.enviro_reports.find({"at": {"$gte": since}}, {"_id": 0}).sort("at", -1).to_list(100)
    groups: dict = {}
    for r in rows:
        key = (r["kind"], r["city"].lower())
        g = groups.setdefault(key, {"kind": r["kind"], "label": THREAT_KINDS[r["kind"]]["label"],
                                    "icon": THREAT_KINDS[r["kind"]]["icon"], "city": r["city"],
                                    "reports": 0, "max_severity": 0, "last_at": r["at"],
                                    "guidance": THREAT_KINDS[r["kind"]]["guidance"],
                                    "sensor": THREAT_KINDS[r["kind"]]["sensor"]})
        g["reports"] += 1
        g["max_severity"] = max(g["max_severity"], r["severity"])
    threats = sorted(groups.values(), key=lambda g: (-g["max_severity"], -g["reports"]))
    for t in threats:
        t["status"] = "CONFIRMED" if t["reports"] >= 2 else "UNVERIFIED"
    return {"threats": threats, "kinds": THREAT_KINDS, "window_h": 24,
            "note": "Fúzia senzorov zariadenia + P2P mesh hlásení (SIMULÁCIA). Konsenzus = 2+ nezávislé hlásenia."}
