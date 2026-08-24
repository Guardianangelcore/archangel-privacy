# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
"""One-Click Refund Engine — 'Claim My Benefits'. AI-prepopulated insurance
refund forms (dental/physio) and tax-deduction summaries from Vault data."""
from fastapi import HTTPException, Header, Response
from typing import Optional
from datetime import datetime, timezone
import uuid

from core import api, db, clean, get_current_user, _make_pdf, _auth_pdf, _pdf_footer

CLAIMABLE = {
    "Stomatológia": "dental", "Fyzioterapia": "physio", "Ortopédia": "physio",
    "Oftalmológia": "optical", "Rádiológia (RTG)": "diagnostics", "Rádiológia (sono)": "diagnostics",
}

async def _build_claim(uid: str) -> dict:
    user = await db.users.find_one({"user_id": uid}, {"_id": 0}) or {}
    pols = await db.insurance_policies.find({"user_id": uid}, {"_id": 0}).to_list(20)
    health_pol = next((p for p in pols if p["type"] == "health"), None)
    acts = await db.jarvis_actions.find({"user_id": uid, "specialty": {"$ne": None}}, {"_id": 0}).to_list(50)
    docs = await db.documents.find({"user_id": uid}, {"_id": 0, "title": 1, "doc_id": 1, "uploaded_at": 1}).sort("uploaded_at", -1).to_list(30)
    items = []
    for a in acts:
        cat = CLAIMABLE.get(a.get("specialty") or "")
        if cat:
            items.append({"specialty": a["specialty"], "category": cat,
                          "source_doc": a.get("doc_title", ""), "booked_slot": a.get("booked_slot"),
                          "estimated_refund_eur": {"dental": 150, "physio": 80, "optical": 60, "diagnostics": 40}[cat]})
    est = round(sum(i["estimated_refund_eur"] for i in items), 2)
    return {"claim_id": uuid.uuid4().hex, "user_name": user.get("name") or "—",
            "insurer": (health_pol or {}).get("provider") or "— (pridajte zdravotnú poistku v Insurance Guard)",
            "policy_paid": bool(health_pol and (health_pol.get("paid_until") or "") >= datetime.now(timezone.utc).strftime("%Y-%m-%d")),
            "items": items, "vault_docs": len(docs),
            "estimated_refund_eur": est,
            "tax_note": "Nezdaniteľná časť / bonusy: doklady o zdravotných výdavkoch si odložte k daňovému priznaniu.",
            "created_at": datetime.now(timezone.utc)}

@api.post("/refunds/claim")
async def refunds_claim(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    claim = await _build_claim(user["user_id"])
    await db.refund_claims.insert_one({**claim, "user_id": user["user_id"]})
    return clean(claim)

@api.get("/refunds/claim.pdf")
async def refunds_claim_pdf(token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    claim = await _build_claim(user["user_id"])
    lines = [
        f"Žiadateľ: {claim['user_name']}",
        f"Zdravotná poisťovňa: {claim['insurer']}",
        f"Stav poistky: {'zaplatená' if claim['policy_paid'] else 'NEZAPLATENÁ / neuvedená'}",
        f"Dátum: {datetime.now(timezone.utc).strftime('%d.%m.%Y')}",
        "",
        "POLOŽKY NÁROKU (predvyplnené z Trezoru):",
    ]
    if claim["items"]:
        for i, it in enumerate(claim["items"], 1):
            lines.append(f"{i}. {it['specialty']} — doklad: {it['source_doc'] or '—'}"
                         + (f" · termín: {it['booked_slot']}" if it.get("booked_slot") else "")
                         + f" · odhad refundácie: {it['estimated_refund_eur']} EUR")
    else:
        lines.append("— Zatiaľ žiadne refundovateľné úkony (nahrajte doklady zo zubára/fyzioterapie do Trezoru).")
    lines += ["", f"ODHAD SPOLU: {claim['estimated_refund_eur']} EUR",
              "", "DAŇOVÝ ODPOČET:", claim["tax_note"],
              "", "Podpis žiadateľa: ______________________",
              "Prílohy: kópie dokladov z Health Vault (Guardian OS)."]
    pdf = _make_pdf("ŽIADOSŤ O REFUNDÁCIU ZDRAVOTNÝCH VÝDAVKOV — Claim My Benefits",
                    "\n".join(lines), _pdf_footer())
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="refund_claim.pdf"'})
