# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
from fastapi import HTTPException, Header, UploadFile, File, Form
from fastapi.responses import Response, StreamingResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import os, uuid, hashlib, json, io, re, base64, httpx

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

from core import (
    api, db, logger, clean, get_current_user, send_push, _push_client,
    AI_COMPLIANCE_NOTE, _aml_ledger_append,
    AML_UNVERIFIED_DAILY, AML_VERIFIED_DAILY, AML_MAX_TX_PER_DAY,
    _FONT_R, _FONT_B, _make_pdf, _auth_pdf, _pdf_footer, _pdf_response,
    APP_NAME, put_object_sync, get_object_sync, init_storage,
    EMERGENT_LLM_KEY, AUTH_SESSION_URL,
)
from models import User, EmergencyProfile, Document, WaitlistItem, FallEvent

# --------- SOLIDARITY HUB (MOCKED P2P) ---------
class CampaignIn(BaseModel):
    title: str
    story: str
    goal_amount: float
    currency: str = "EUR"

@api.get("/solidarity/campaigns")
async def list_campaigns(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    items = await db.campaigns.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return items

@api.post("/solidarity/campaigns")
async def new_campaign(body: CampaignIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if not user.get("kyc_verified"):
        raise HTTPException(403, "kyc_required: Campaign creation requires KYC verification (AML). Complete it in Legal & Compliance.")
    doc = {
        "campaign_id": uuid.uuid4().hex,
        "user_id": user["user_id"],
        "owner_name": user.get("name") or user["email"],
        "owner_did": user["did"],
        "owner_kyc_attestation": user.get("kyc_attestation"),
        **body.model_dump(),
        "raised_amount": 0.0,
        "supporters": 0,
        "created_at": datetime.now(timezone.utc),
    }
    await db.campaigns.insert_one(doc.copy())
    await _aml_ledger_append(user["user_id"], "campaign_create", {"campaign_id": doc["campaign_id"], "goal": body.goal_amount})
    return clean(doc)

class DonateIn(BaseModel):
    amount: float
    message: Optional[str] = ""

@api.post("/solidarity/campaigns/{cid}/donate")
async def donate(cid: str, body: DonateIn, authorization: Optional[str] = Header(None)):
    """MOCKED payment rails — but real AML rules engine with tamper-evident ledger."""
    user = await get_current_user(authorization)
    if body.amount <= 0:
        raise HTTPException(400, "Invalid amount")
    camp = await db.campaigns.find_one({"campaign_id": cid}, {"_id": 0})
    if not camp:
        raise HTTPException(404, "not found")
    # AML checks: daily limit + velocity
    donated, tx = await _donations_today(user["user_id"])
    limit = AML_VERIFIED_DAILY if user.get("kyc_verified") else AML_UNVERIFIED_DAILY
    if tx >= AML_MAX_TX_PER_DAY:
        await _aml_ledger_append(user["user_id"], "aml_block_velocity", {"tx_today": tx})
        raise HTTPException(403, f"aml_velocity: Max {AML_MAX_TX_PER_DAY} donations per day exceeded.")
    if donated + body.amount > limit:
        await _aml_ledger_append(user["user_id"], "aml_block_limit", {"attempted": body.amount, "donated_today": donated, "limit": limit})
        raise HTTPException(403, f"aml_limit: Daily limit €{limit:.0f} exceeded (today €{donated:.0f}). {'Complete KYC to raise the limit.' if not user.get('kyc_verified') else ''}")
    await db.donations.insert_one({
        "donation_id": uuid.uuid4().hex,
        "campaign_id": cid,
        "donor_user_id": user["user_id"],
        "donor_did": user["did"],
        "amount": body.amount,
        "message": body.message,
        "created_at": datetime.now(timezone.utc),
        "mocked": True,
    })
    await db.campaigns.update_one(
        {"campaign_id": cid},
        {"$inc": {"raised_amount": body.amount, "supporters": 1}},
    )
    ledger_hash = await _aml_ledger_append(user["user_id"], "donation", {"campaign_id": cid, "amount": body.amount, "kyc": bool(user.get("kyc_verified"))})
    return {"ok": True, "mocked": True, "ledger_hash": ledger_hash}


# --------- DIGITAL HEALTHCARE PROXY ---------
class ProxyDirectiveIn(BaseModel):
    proxy_full_name: str
    proxy_relationship: str = "partner"
    proxy_phone: Optional[str] = ""
    proxy_email: Optional[str] = ""
    scope: str = "full"  # full | info_access | decisions
    effective_immediately: bool = True
    alternate_name: Optional[str] = ""
    notes: Optional[str] = ""
    language: str = "sk"

PROXY_TEMPLATES = {
    "sk": (
        "SPLNOMOCNENIE A URČENIE ZDRAVOTNÉHO ZÁSTUPCU\n"
        "==============================================\n\n"
        "Ja, {principal}, identifikovaný/á decentralizovaným identifikátorom (DID):\n{did}\n\n"
        "týmto v plnom rozsahu SPLNOMOCŇUJEM a určujem za svojho zdravotného zástupcu:\n\n"
        "  MENO: {proxy}\n  VZŤAH: {relationship}\n  TELEFÓN: {phone}\n  E-MAIL: {email}\n\n"
        "ROZSAH OPRÁVNENIA: {scope_text}\n\n"
        "Splnomocnenec je oprávnený v súlade s § 6 ods. 1 písm. b) zákona č. 576/2004 Z. z. "
        "o zdravotnej starostlivosti prijímať informácie o mojom zdravotnom stave, nahliadať do "
        "zdravotnej dokumentácie a — v rozsahu vyššie uvedenom — udeľovať informovaný súhlas v mojom mene, "
        "ak nebudem schopný/á prejaviť svoju vôľu.\n\n"
        "Toto splnomocnenie {effective}.\n"
        "Náhradný zástupca: {alternate}\n"
        "Poznámky: {notes}\n\n"
        "Dátum vystavenia: {date}\nKryptografický odtlačok (SHA-256): {hash}\n\n"
        "Tento dokument bol vytvorený v aplikácii Guardian Health & Angel a je ukotvený na DID vlastníka. "
        "Odporúčame notárske overenie podpisu pre plnú právnu istotu."
    ),
    "en": (
        "POWER OF ATTORNEY & HEALTHCARE PROXY DESIGNATION\n"
        "================================================\n\n"
        "I, {principal}, identified by decentralized identifier (DID):\n{did}\n\n"
        "hereby fully AUTHORIZE and designate as my healthcare proxy:\n\n"
        "  NAME: {proxy}\n  RELATIONSHIP: {relationship}\n  PHONE: {phone}\n  E-MAIL: {email}\n\n"
        "SCOPE OF AUTHORITY: {scope_text}\n\n"
        "The proxy is entitled to receive information about my health condition, access my medical records, "
        "and — to the extent stated above — give informed consent on my behalf if I am unable to express my will.\n\n"
        "This authorization {effective}.\nAlternate proxy: {alternate}\nNotes: {notes}\n\n"
        "Date of issue: {date}\nCryptographic fingerprint (SHA-256): {hash}\n\n"
        "Created in Guardian Health & Angel, anchored to the owner's DID. Notarization recommended for full legal certainty."
    ),
}
SCOPE_TEXT = {
    "sk": {"full": "PLNÉ — informácie, dokumentácia aj rozhodnutia o liečbe", "info_access": "PRÍSTUP K INFORMÁCIÁM a zdravotnej dokumentácii", "decisions": "ROZHODNUTIA o liečbe pri mojej nespôsobilosti"},
    "en": {"full": "FULL — information, records and treatment decisions", "info_access": "ACCESS TO INFORMATION and medical records", "decisions": "TREATMENT DECISIONS during my incapacity"},
}

@api.get("/proxy-directive")
async def get_proxy(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    doc = await db.proxy_directives.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return doc or {}

@api.put("/proxy-directive")
async def put_proxy(body: ProxyDirectiveIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    lang = body.language if body.language in PROXY_TEMPLATES else ("sk" if body.language in ("sk", "cs") else "en")
    now = datetime.now(timezone.utc)
    principal = user.get("name") or user["email"]
    scope_text = SCOPE_TEXT[lang].get(body.scope, SCOPE_TEXT[lang]["full"])
    effective = ("nadobúda účinnosť okamžite podpisom" if body.effective_immediately else "nadobúda účinnosť pri strate spôsobilosti") if lang == "sk" \
        else ("takes effect immediately upon signature" if body.effective_immediately else "takes effect upon my incapacity")
    base = f"{principal}|{user['did']}|{body.proxy_full_name}|{body.scope}|{now.date().isoformat()}"
    doc_hash = hashlib.sha256(base.encode()).hexdigest()
    document_text = PROXY_TEMPLATES[lang].format(
        principal=principal, did=user["did"], proxy=body.proxy_full_name,
        relationship=body.proxy_relationship, phone=body.proxy_phone or "—", email=body.proxy_email or "—",
        scope_text=scope_text, effective=effective, alternate=body.alternate_name or "—",
        notes=body.notes or "—", date=now.strftime("%Y-%m-%d"), hash=doc_hash,
    )
    doc = {
        "user_id": user["user_id"], **body.model_dump(),
        "document_text": document_text, "doc_hash": doc_hash,
        "principal_name": principal, "principal_did": user["did"],
        "updated_at": now,
    }
    await db.proxy_directives.update_one({"user_id": user["user_id"]}, {"$set": doc}, upsert=True)
    return await db.proxy_directives.find_one({"user_id": user["user_id"]}, {"_id": 0})

# --------- DIRECT SERVICE MARKETPLACE ---------
class ServiceIn(BaseModel):
    title: str
    description: Optional[str] = ""
    category: str = "massage"  # massage | consultation | physio | care | other
    price: float = 0
    currency: str = "EUR"
    payment_methods: List[str] = ["cash"]  # cash | crypto
    city: str = ""
    contact: Optional[str] = ""

@api.get("/market/services")
async def market_list(city: Optional[str] = None, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    q: dict = {"active": True}
    if city:
        q["city"] = city
    return await db.market_services.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)

@api.post("/market/services")
async def market_add(body: ServiceIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    doc = {
        "service_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "provider_name": user.get("name") or user["email"], "provider_did": user["did"],
        **body.model_dump(), "active": True, "bookings": 0,
        "created_at": datetime.now(timezone.utc),
    }
    await db.market_services.insert_one(doc.copy())
    return clean(doc)

@api.delete("/market/services/{service_id}")
async def market_del(service_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.market_services.update_one({"service_id": service_id, "user_id": user["user_id"]}, {"$set": {"active": False}})
    if res.matched_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}

class BookIn(BaseModel):
    message: Optional[str] = ""
    payment_method: str = "cash"

@api.post("/market/services/{service_id}/book")
async def market_book(service_id: str, body: BookIn, authorization: Optional[str] = Header(None)):
    """Direct booking — payment happens cash/crypto peer-to-peer, no middleman."""
    user = await get_current_user(authorization)
    svc = await db.market_services.find_one({"service_id": service_id, "active": True}, {"_id": 0})
    if not svc:
        raise HTTPException(404, "Not found")
    booking = {
        "booking_id": uuid.uuid4().hex, "service_id": service_id,
        "provider_user_id": svc["user_id"], "client_user_id": user["user_id"],
        "client_name": user.get("name") or user["email"],
        "message": body.message, "payment_method": body.payment_method,
        "status": "requested", "created_at": datetime.now(timezone.utc),
    }
    await db.market_bookings.insert_one(booking.copy())
    await db.market_services.update_one({"service_id": service_id}, {"$inc": {"bookings": 1}})
    # Hard-coded 15% Guardian Tax → foundation treasury (all tiers, no exceptions)
    if svc.get("price"):
        try:
            from routes.subscription import record_revenue
            await record_revenue("guardian_tax", float(svc["price"]) * 0.15, user["user_id"],
                                 {"source": "marketplace", "service_id": service_id,
                                  "gross": svc["price"], "currency": svc.get("currency", "EUR")})
        except Exception:
            pass
    try:
        await send_push(
            recipients=[svc["user_id"]],
            data={"title": "Nová objednávka 💼", "message": f"{booking['client_name']}: {svc['title']} ({body.payment_method})", "action_url": "/marketplace"},
        )
    except Exception as e:
        logger.warning(f"push failed: {e}")
    return clean(booking)

@api.get("/market/bookings")
async def market_bookings(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    uid = user["user_id"]
    docs = await db.market_bookings.find({"$or": [{"provider_user_id": uid}, {"client_user_id": uid}]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return docs


# --------- SKILL BARTER ENGINE ---------
BARTER_START_CREDITS = 10

async def _barter_credits(user_id: str) -> int:
    u = await db.users.find_one({"user_id": user_id}, {"_id": 0, "barter_credits": 1})
    c = u.get("barter_credits") if u else None
    if c is None:
        await db.users.update_one({"user_id": user_id}, {"$set": {"barter_credits": BARTER_START_CREDITS}})
        return BARTER_START_CREDITS
    return int(c)

class BarterOfferIn(BaseModel):
    offer_skill: str
    want_in_return: Optional[str] = ""
    category: str = "other"  # health | legal | craft | care | food | other
    city: str = ""
    credits_value: int = Field(default=1, ge=1, le=50)

@api.get("/barter/me")
async def barter_me(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    credits = await _barter_credits(user["user_id"])
    trades = await db.barter_trades.find(
        {"$or": [{"provider_user_id": user["user_id"]}, {"client_user_id": user["user_id"]}]}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return {"credits": credits, "trades": trades}

@api.get("/barter/offers")
async def barter_list(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    return await db.barter_offers.find({"status": "open"}, {"_id": 0}).sort("created_at", -1).to_list(200)

@api.post("/barter/offers")
async def barter_add(body: BarterOfferIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await _barter_credits(user["user_id"])
    doc = {
        "offer_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "owner_name": user.get("name") or user["email"], "owner_did": user["did"],
        **body.model_dump(), "status": "open", "created_at": datetime.now(timezone.utc),
    }
    await db.barter_offers.insert_one(doc.copy())
    return clean(doc)

@api.post("/barter/offers/{offer_id}/accept")
async def barter_accept(offer_id: str, authorization: Optional[str] = Header(None)):
    """Trust-credit trade: client spends credits, provider earns them."""
    user = await get_current_user(authorization)
    offer = await db.barter_offers.find_one({"offer_id": offer_id, "status": "open"}, {"_id": 0})
    if not offer:
        raise HTTPException(404, "Not found or closed")
    if offer["user_id"] == user["user_id"]:
        raise HTTPException(400, "Cannot accept your own offer")
    cost = int(offer.get("credits_value") or 1)
    balance = await _barter_credits(user["user_id"])
    if balance < cost:
        raise HTTPException(402, f"Not enough trust credits ({balance}/{cost})")
    await _barter_credits(offer["user_id"])
    await db.users.update_one({"user_id": user["user_id"]}, {"$inc": {"barter_credits": -cost}})
    await db.users.update_one({"user_id": offer["user_id"]}, {"$inc": {"barter_credits": cost}})
    await db.barter_offers.update_one({"offer_id": offer_id}, {"$set": {"status": "traded"}})
    trade = {
        "trade_id": uuid.uuid4().hex, "offer_id": offer_id,
        "offer_skill": offer["offer_skill"], "credits": cost,
        "provider_user_id": offer["user_id"], "provider_name": offer["owner_name"],
        "client_user_id": user["user_id"], "client_name": user.get("name") or user["email"],
        "created_at": datetime.now(timezone.utc),
    }
    await db.barter_trades.insert_one(trade.copy())
    try:
        await send_push(
            recipients=[offer["user_id"]],
            data={"title": "Barter dohodnutý 🔁", "message": f"{trade['client_name']} prijal: {offer['offer_skill']} (+{cost} kreditov)", "action_url": "/barter"},
        )
    except Exception as e:
        logger.warning(f"push failed: {e}")
    return clean(trade)

@api.delete("/barter/offers/{offer_id}")
async def barter_del(offer_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.barter_offers.delete_one({"offer_id": offer_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}


# --------- GLOBAL LEGAL ENGINE (2026 standards) ---------
from core import TOS_VERSION
EU_CC = {"SK","CZ","DE","AT","PL","HU","FR","IT","ES","PT","NL","BE","LU","IE","DK","SE","FI","EE","LV","LT","SI","HR","RO","BG","GR","CY","MT"}
COMMON_LAW_CC = {"US","CA","AU","NZ","IE"}

def resolve_jurisdiction(country: Optional[str]) -> str:
    cc = (country or "").upper()
    if cc in ("GB", "UK"):
        return "UK"
    if cc == "US":
        return "US"
    if cc in EU_CC:
        return "EU"
    return "OTHER"

def _lang_key(language: str) -> str:
    return "sk" if language in ("sk", "cs") else "en"

DISCLAIMERS = {
    "EU": {
        "sk": [
            {"id": "eu_ai_act", "title": "EU AI Act — Čl. 50 (účinné od 2. 8. 2026)", "text": "Komunikujete s AI systémom. Všetok obsah generovaný Jarvisom je označený ako AI výstup. Aplikácia nie je vysokorizikový AI systém ani zdravotnícka pomôcka podľa MDR (EÚ) 2017/745 — slúži na všeobecné wellness a informačné účely."},
            {"id": "eu_gdpr", "title": "GDPR (EÚ) 2016/679", "text": "Vaše zdravotné údaje (čl. 9) sú spracúvané výlučne s vaším súhlasom, uložené šifrovane a ukotvené na vašom DID. Máte právo na prístup, opravu, vymazanie a prenositeľnosť. Prevádzkovateľ nezdieľa údaje s tretími stranami."},
            {"id": "eu_medical", "title": "Nie je lekárska rada", "text": "AI preklady, wellness analýzy a fyzio-rutiny sú informačné. Nenahrádzajú lekára. V núdzi volajte 112 / 155."},
        ],
        "en": [
            {"id": "eu_ai_act", "title": "EU AI Act — Art. 50 (effective 2 Aug 2026)", "text": "You are interacting with an AI system. All Jarvis content is labelled as AI-generated. This app is not a high-risk AI system nor a medical device under MDR (EU) 2017/745 — it serves general wellness and informational purposes."},
            {"id": "eu_gdpr", "title": "GDPR (EU) 2016/679", "text": "Your health data (Art. 9) is processed only with your consent, stored encrypted and anchored to your DID. You have rights of access, rectification, erasure and portability."},
            {"id": "eu_medical", "title": "Not medical advice", "text": "AI translations, wellness analyses and physio routines are informational. They do not replace a doctor. In emergency call 112 / 155."},
        ],
    },
    "UK": {
        "sk": [
            {"id": "uk_dpa", "title": "UK GDPR · Data Protection Act 2018 · DUAA 2025", "text": "Spracovanie osobných a zdravotných údajov podlieha UK GDPR a Data (Use and Access) Act 2025. Údaje sú šifrované a viazané na váš DID."},
            {"id": "uk_ai", "title": "AI transparentnosť", "text": "Komunikujete s AI systémom. Výstupy sú informačné, nie odborná rada. V núdzi volajte 999 / 111 (NHS)."},
        ],
        "en": [
            {"id": "uk_dpa", "title": "UK GDPR · Data Protection Act 2018 · DUAA 2025", "text": "Processing of personal and health data is subject to UK GDPR and the Data (Use and Access) Act 2025. Data is encrypted and bound to your DID."},
            {"id": "uk_ai", "title": "AI transparency", "text": "You are interacting with an AI system. Outputs are informational, not professional advice. In emergency call 999 / 111 (NHS)."},
        ],
    },
    "US": {
        "sk": [
            {"id": "us_fda", "title": "FDA — General Wellness", "text": "Táto aplikácia je „general wellness product” podľa usmernenia FDA — nie je zdravotnícka pomôcka, nediagnostikuje ani nelieči. AI výstupy sú informačné."},
            {"id": "us_hipaa", "title": "HIPAA", "text": "Prevádzkovateľ nie je „covered entity” podľa HIPAA. Údaje sú šifrované a pod vašou kontrolou cez DID. V núdzi volajte 911."},
        ],
        "en": [
            {"id": "us_fda", "title": "FDA — General Wellness", "text": "This app is a general wellness product under FDA guidance — not a medical device; it does not diagnose or treat. AI outputs are informational only."},
            {"id": "us_hipaa", "title": "HIPAA", "text": "The operator is not a HIPAA covered entity. Data is encrypted and under your control via DID. In emergency call 911."},
        ],
    },
    "OTHER": {
        "sk": [
            {"id": "global", "title": "Globálne upozornenie", "text": "Komunikujete s AI systémom. Všetky výstupy sú informačné, nie lekárska či právna rada. Používate ich na vlastné riziko. V núdzi kontaktujte miestne tiesňové služby."},
        ],
        "en": [
            {"id": "global", "title": "Global notice", "text": "You are interacting with an AI system. All outputs are informational, not medical or legal advice. You use them at your own risk. In emergency contact local emergency services."},
        ],
    },
}

TOS_TEXT = {
    "sk": (
        "PODMIENKY POUŽÍVANIA — GUARDIAN HEALTH & ANGEL (v{ver})\n"
        "=====================================================\n\n"
        "1. POVAHA SLUŽBY: Aplikácia je suverénny informačný a wellness nástroj. NIE JE poskytovateľom zdravotnej starostlivosti, zdravotníckou pomôckou, právnou kanceláriou ani finančnou inštitúciou.\n\n"
        "2. AI VÝSTUPY (EU AI Act čl. 50): Všetok obsah generovaný AI (Jarvis) je označený a je VÝLUČNE INFORMAČNÝ. Používateľ berie na vedomie a súhlasí, že AI výstupy používa NA VLASTNÉ RIZIKO a pred akýmkoľvek rozhodnutím o zdraví, práve či financiách sa poradí s kvalifikovaným odborníkom.\n\n"
        "3. ÚPLNÉ ZBAVENIE ZODPOVEDNOSTI: Zakladateľ a autor („Guardian Angel”), vývojári a prevádzkovatelia NENESÚ ŽIADNU ZODPOVEDNOSŤ za akúkoľvek priamu, nepriamu, náhodnú, následnú alebo exemplárnu škodu vzniknutú použitím aplikácie, AI výstupov, P2P výmen, barterov, majáku, detekcie pádu či komunitných funkcií — v maximálnom rozsahu povolenom právom jurisdikcie používateľa.\n\n"
        "4. BEZPEČNOSTNÉ FUNKCIE: Detekcia pádu, strážca nečinnosti, scam štít a núdzový maják sú POMOCNÉ funkcie typu best-effort. Nenahrádzajú tiesňové linky ani profesionálny dohľad. Ich zlyhanie nezakladá nárok na náhradu škody.\n\n"
        "5. P2P A KOMUNITA: Výmeny liekov (len voľnopredajné), barter a trhovisko prebiehajú priamo medzi používateľmi. Prevádzkovateľ nie je zmluvnou stranou, neručí za kvalitu, zákonnosť ani bezpečnosť plnení. Solidarity Hub podlieha AML pravidlám (denné limity, KYC).\n\n"
        "6. DÁTA: Zero-knowledge princíp; údaje sú viazané na váš DID. Právne dokumenty (splnomocnenia, testamenty) sú ŠABLÓNY — pre plnú právnu záväznosť sa vyžaduje vlastnoručný podpis, prípadne svedkovia či notár podľa vašej jurisdikcie.\n\n"
        "7. SÚHLAS: Potvrdením vyhlasujete, že máte 18+ rokov, prečítali ste si tieto podmienky, rozumiete im a prijímate ich vrátane úplného zbavenia zodpovednosti podľa bodu 3.\n\n"
        "AGPL-v3 · Vízia a autorstvo: Guardian Angel · Verzia {ver}"
    ),
    "en": (
        "TERMS OF SERVICE — GUARDIAN HEALTH & ANGEL (v{ver})\n"
        "===================================================\n\n"
        "1. NATURE OF SERVICE: The app is a sovereign informational and wellness tool. It is NOT a healthcare provider, medical device, law firm or financial institution.\n\n"
        "2. AI OUTPUTS (EU AI Act Art. 50): All AI-generated content (Jarvis) is labelled and STRICTLY INFORMATIONAL. The user acknowledges and agrees that AI outputs are used AT THE USER'S OWN RISK and that a qualified professional must be consulted before any health, legal or financial decision.\n\n"
        "3. TOTAL WAIVER OF LIABILITY: The founder and author (\"Guardian Angel\"), developers and operators BEAR NO LIABILITY WHATSOEVER for any direct, indirect, incidental, consequential or exemplary damages arising from use of the app, AI outputs, P2P exchanges, barter, beacon, fall detection or community features — to the maximum extent permitted by the law of the user's jurisdiction.\n\n"
        "4. SAFETY FEATURES: Fall detection, inactivity guard, scam shield and the emergency beacon are best-effort AUXILIARY features. They do not replace emergency lines or professional supervision; their failure creates no claim for damages.\n\n"
        "5. P2P & COMMUNITY: Medicine exchange (OTC only), barter and marketplace occur directly between users. The operator is not a contracting party and does not warrant quality, legality or safety. The Solidarity Hub is subject to AML rules (daily limits, KYC).\n\n"
        "6. DATA: Zero-knowledge principle; data is bound to your DID. Legal documents (proxies, wills) are TEMPLATES — full legal validity requires a handwritten signature and, depending on your jurisdiction, witnesses or a notary.\n\n"
        "7. CONSENT: By accepting you declare you are 18+, have read and understood these terms and accept them, including the total waiver of liability in clause 3.\n\n"
        "AGPL-v3 · Vision & authorship: Guardian Angel · Version {ver}"
    ),
}

@api.get("/legal/region")
async def legal_region(country: Optional[str] = None, language: str = "sk", authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    jur = resolve_jurisdiction(country)
    lk = _lang_key(language)
    testament_format = "common_law_uk" if jur == "UK" else ("common_law" if (country or "").upper() in COMMON_LAW_CC else "civil_law_holograph")
    return {
        "jurisdiction": jur,
        "country": (country or "").upper(),
        "disclaimers": DISCLAIMERS[jur][lk],
        "tos_version": TOS_VERSION,
        "testament_format": testament_format,
        "aml": {"unverified_daily_limit": 150, "verified_daily_limit": 5000, "max_tx_per_day": 10, "currency": "EUR"},
    }

@api.get("/legal/tos")
async def legal_tos(country: Optional[str] = None, language: str = "sk", authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    return {"version": TOS_VERSION, "jurisdiction": resolve_jurisdiction(country), "text": TOS_TEXT[_lang_key(language)].format(ver=TOS_VERSION)}

class TosAcceptIn(BaseModel):
    country: Optional[str] = ""
    language: str = "sk"

@api.post("/legal/accept")
async def legal_accept(body: TosAcceptIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {
        "tos_accepted_version": TOS_VERSION,
        "tos_accepted_at": datetime.now(timezone.utc),
        "tos_jurisdiction": resolve_jurisdiction(body.country),
    }})
    await _aml_ledger_append(user["user_id"], "tos_accept", {"version": TOS_VERSION, "jurisdiction": resolve_jurisdiction(body.country)})
    return clean(await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0}))


class KycIn(BaseModel):
    full_name: str
    birth_year: int = Field(ge=1900, le=2010)
    country: str
    declaration: bool = False  # sanctions & source-of-funds self-declaration

@api.post("/aml/kyc")
async def aml_kyc(body: KycIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if not body.declaration:
        raise HTTPException(400, "Sanctions & source-of-funds declaration is required")
    attestation = hashlib.sha256(f"{user['did']}|{body.full_name}|{body.birth_year}|{body.country.upper()}|{datetime.now(timezone.utc).date()}".encode()).hexdigest()
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {
        "kyc_verified": True,
        "kyc_attestation": attestation,
        "kyc_country": body.country.upper(),
        "kyc_verified_at": datetime.now(timezone.utc),
    }})
    ledger_hash = await _aml_ledger_append(user["user_id"], "kyc_attestation", {"attestation": attestation, "did": user["did"], "country": body.country.upper()})
    return {"kyc_verified": True, "attestation": attestation, "ledger_hash": ledger_hash}

async def _donations_today(user_id: str):
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    docs = await db.donations.find({"donor_user_id": user_id, "created_at": {"$gte": start}}, {"_id": 0, "amount": 1}).to_list(500)
    return sum(d.get("amount", 0) for d in docs), len(docs)

@api.get("/aml/status")
async def aml_status(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    donated, tx = await _donations_today(user["user_id"])
    verified = bool(user.get("kyc_verified"))
    limit = AML_VERIFIED_DAILY if verified else AML_UNVERIFIED_DAILY
    entries = await db.aml_ledger.count_documents({"user_id": user["user_id"]})
    return {
        "kyc_verified": verified,
        "attestation": user.get("kyc_attestation"),
        "donated_today": donated,
        "tx_today": tx,
        "daily_limit": limit,
        "remaining_today": max(0.0, limit - donated),
        "max_tx_per_day": AML_MAX_TX_PER_DAY,
        "ledger_entries": entries,
    }


# --------- INTERNATIONAL LEGACY / TESTAMENT ENGINE ---------
class TestamentIn(BaseModel):
    country: str = "SK"
    language: str = "sk"
    full_name: str
    wishes: str
    executor_name: Optional[str] = ""
    witness1: Optional[str] = ""
    witness2: Optional[str] = ""

TESTAMENT_INSTRUCTIONS = {
    "civil_law_holograph": {
        "sk": "HOLOGRAFNÝ TESTAMENT (kontinentálne právo, napr. § 476 Občianskeho zákonníka SR): Aby bol PLATNÝ, musí byť CELÝ napísaný VLASTNOU RUKOU poručiteľa a vlastnoručne PODPÍSANÝ s uvedením dňa, mesiaca a roku. Svedkovia nie sú potrební. Nižšie uvedený text si ODPÍŠTE rukou — vytlačená verzia NIE JE platná.",
        "en": "HOLOGRAPHIC WILL (civil law, e.g. § 476 Slovak Civil Code): To be VALID it must be written ENTIRELY in the testator's OWN HAND and personally SIGNED with day, month and year. No witnesses required. COPY the text below by hand — a printed version is NOT valid.",
    },
    "common_law_uk": {
        "sk": "ZÁVET PODĽA UK PRÁVA (Wills Act 1837, s. 9 — Anglicko a Wales): Musí byť PÍSOMNÝ, PODPÍSANÝ poručiteľom v SÚČASNEJ prítomnosti DVOCH svedkov, ktorí ho tiež podpíšu. POZOR: holografný (rukou písaný nesvedčený) závet NIE JE v Anglicku a Walese platný. V Škótsku postačuje vlastnoručný podpis na každej strane („self-proving” pri podpise pred 1 svedkom).",
        "en": "WILL UNDER UK LAW (Wills Act 1837, s. 9 — England & Wales): Must be IN WRITING, SIGNED by the testator in the SIMULTANEOUS presence of TWO witnesses who also sign. NOTE: a holograph (handwritten unwitnessed) will is NOT valid in England & Wales. In Scotland a will subscribed on every page is self-proving if signed before 1 witness.",
    },
    "common_law": {
        "sk": "ZÁVET (common law — napr. USA): Vyžaduje sa PÍSOMNÁ forma, podpis poručiteľa a DVAJA svedkovia (vo väčšine štátov). Niektoré štáty USA uznávajú aj holografný závet — overte miestne právo. Odporúčame notárske overenie (self-proving affidavit).",
        "en": "WILL (common law — e.g. US): Requires WRITING, the testator's signature and TWO witnesses (most states). Some US states also accept holographic wills — verify local law. A notarized self-proving affidavit is recommended.",
    },
}

@api.post("/legal/testament")
async def legal_testament(body: TestamentIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    cc = body.country.upper()
    fmt = "common_law_uk" if cc in ("GB", "UK") else ("common_law" if cc in COMMON_LAW_CC else "civil_law_holograph")
    lk = _lang_key(body.language)
    now = datetime.now(timezone.utc)
    witnesses = ""
    if fmt != "civil_law_holograph":
        w1 = body.witness1 or "________________"
        w2 = body.witness2 or "________________"
        witnesses = (f"\n\nSVEDOK 1 / WITNESS 1: {w1}  Podpis/Signature: ____________\nSVEDOK 2 / WITNESS 2: {w2}  Podpis/Signature: ____________")
    head = "ZÁVET / POSLEDNÁ VÔĽA" if lk == "sk" else "LAST WILL AND TESTAMENT"
    doc_body = (
        f"{head}\n{'=' * len(head)}\n\n"
        f"{'Ja' if lk == 'sk' else 'I'}, {body.full_name}, DID: {user['did']},\n"
        f"{'týmto vyhlasujem svoju poslednú vôľu' if lk == 'sk' else 'hereby declare my last will'} ({now.strftime('%Y-%m-%d')}):\n\n"
        f"{body.wishes}\n\n"
        f"{'Vykonávateľ závetu' if lk == 'sk' else 'Executor'}: {body.executor_name or '—'}\n"
        f"{'Miesto a dátum' if lk == 'sk' else 'Place and date'}: ____________, {now.strftime('%d.%m.%Y')}\n"
        f"{'Vlastnoručný podpis' if lk == 'sk' else 'Handwritten signature'}: ____________"
        f"{witnesses}"
    )
    doc_hash = hashlib.sha256(f"{user['did']}|{body.full_name}|{fmt}|{now.date()}".encode()).hexdigest()
    document_text = f"{TESTAMENT_INSTRUCTIONS[fmt][lk]}\n\n----------------------------------------\n\n{doc_body}\n\nSHA-256: {doc_hash}"
    saved = {
        "user_id": user["user_id"], "format": fmt, "country": cc, "language": body.language,
        "full_name": body.full_name, "wishes": body.wishes, "executor_name": body.executor_name,
        "witness1": body.witness1, "witness2": body.witness2,
        "document_text": document_text, "doc_hash": doc_hash, "updated_at": now,
    }
    await db.legal_testaments.update_one({"user_id": user["user_id"]}, {"$set": saved}, upsert=True)
    return await db.legal_testaments.find_one({"user_id": user["user_id"]}, {"_id": 0})

@api.get("/legal/testament")
async def get_testament(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.legal_testaments.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}



@api.get("/legal/testament.pdf")
async def testament_pdf(token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    doc = await db.legal_testaments.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "No testament generated yet")
    pdf = await run_in_threadpool(_make_pdf, "ZÁVET / LAST WILL AND TESTAMENT", doc["document_text"], _pdf_footer(doc.get("doc_hash")))
    return _pdf_response(pdf, "guardian_testament.pdf")

@api.get("/legal/proxy.pdf")
async def proxy_pdf(token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    doc = await db.proxy_directives.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not doc or not doc.get("document_text"):
        raise HTTPException(404, "No proxy directive generated yet")
    pdf = await run_in_threadpool(_make_pdf, "SPLNOMOCNENIE / HEALTHCARE PROXY", doc["document_text"], _pdf_footer(doc.get("doc_hash")))
    return _pdf_response(pdf, "guardian_healthcare_proxy.pdf")

@api.get("/legal/tos.pdf")
async def tos_pdf(language: str = "sk", token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    await _auth_pdf(authorization, token)
    text = TOS_TEXT[_lang_key(language)].format(ver=TOS_VERSION)
    pdf = await run_in_threadpool(_make_pdf, f"PODMIENKY POUŽÍVANIA / TERMS OF SERVICE v{TOS_VERSION}", text, _pdf_footer())
    return _pdf_response(pdf, "guardian_tos.pdf")


# --------- FINAL DIGNITY & FUNERAL FUND (Legacy module) ---------
class DignityDepositIn(BaseModel):
    amount: float = Field(gt=0)
    currency: str = "EUR"  # EUR | CZK | CRYPTO
    method: str = "card"   # card | crypto

class DignityPlanIn(BaseModel):
    monthly_amount: float = Field(ge=0)
    currency: str = "EUR"
    enabled: bool = True

class DignityBeneficiaryIn(BaseModel):
    type: str = "proxy"  # proxy | funeral_director
    name: Optional[str] = ""
    contact: Optional[str] = ""
    iban: Optional[str] = ""

class DignityWishesIn(BaseModel):
    burial_type: str = "cremation"  # burial | cremation | natural
    ceremony_music: Optional[str] = ""
    guest_list: Optional[str] = ""
    notes: Optional[str] = ""

async def _dignity_fund(user_id: str) -> dict:
    fund = await db.dignity_funds.find_one({"user_id": user_id}, {"_id": 0})
    if not fund:
        fund = {
            "user_id": user_id, "balance": 0.0, "currency": "EUR", "status": "locked",
            "death_verified": False, "plan": None, "beneficiary": None,
            "last_plan_run": None, "created_at": datetime.now(timezone.utc),
        }
        await db.dignity_funds.insert_one(fund.copy())
    return fund

async def _apply_recurring(user_id: str, fund: dict) -> dict:
    """Simulated automated recurring transfers — applies missed monthly deposits."""
    plan = fund.get("plan")
    if not plan or not plan.get("enabled") or plan.get("monthly_amount", 0) <= 0 or fund.get("status") == "released":
        return fund
    now = datetime.now(timezone.utc)
    cur = now.strftime("%Y-%m")
    last = fund.get("last_plan_run")
    if last == cur:
        return fund
    # apply one automated deposit for the current month
    amt = float(plan["monthly_amount"])
    await db.dignity_contributions.insert_one({
        "contribution_id": uuid.uuid4().hex, "user_id": user_id, "amount": amt,
        "currency": plan.get("currency", "EUR"), "method": "recurring",
        "mocked": True, "created_at": now,
    })
    await db.dignity_funds.update_one({"user_id": user_id}, {"$inc": {"balance": amt}, "$set": {"last_plan_run": cur}})
    await _aml_ledger_append(user_id, "dignity_recurring", {"amount": amt, "month": cur})
    return await db.dignity_funds.find_one({"user_id": user_id}, {"_id": 0})

@api.get("/dignity/fund")
async def dignity_fund(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    fund = await _dignity_fund(user["user_id"])
    fund = await _apply_recurring(user["user_id"], fund)
    contributions = await db.dignity_contributions.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(20)
    wishes = await db.dignity_wishes.find_one({"user_id": user["user_id"]}, {"_id": 0})
    # default beneficiary = primary healthcare proxy
    if not fund.get("beneficiary"):
        proxy = await db.proxy_directives.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if proxy and proxy.get("proxy_full_name"):
            fund["beneficiary"] = {"type": "proxy", "name": proxy["proxy_full_name"], "contact": proxy.get("proxy_phone") or proxy.get("proxy_email") or "", "iban": "", "auto": True}
    return {**clean(fund), "contributions": contributions, "wishes": clean(wishes) if wishes else None}

@api.post("/dignity/fund/deposit")
async def dignity_deposit(body: DignityDepositIn, authorization: Optional[str] = Header(None)):
    """MOCKED payment rails — real ledger + AML audit."""
    user = await get_current_user(authorization)
    fund = await _dignity_fund(user["user_id"])
    if fund.get("status") == "released":
        raise HTTPException(400, "Fund already released")
    await db.dignity_contributions.insert_one({
        "contribution_id": uuid.uuid4().hex, "user_id": user["user_id"],
        "amount": body.amount, "currency": body.currency, "method": body.method,
        "mocked": True, "created_at": datetime.now(timezone.utc),
    })
    await db.dignity_funds.update_one({"user_id": user["user_id"]}, {"$inc": {"balance": body.amount}, "$set": {"currency": body.currency}})
    ledger = await _aml_ledger_append(user["user_id"], "dignity_deposit", {"amount": body.amount, "currency": body.currency, "method": body.method})
    fund = await db.dignity_funds.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return {**clean(fund), "ledger_hash": ledger, "mocked": True}

@api.put("/dignity/fund/plan")
async def dignity_plan(body: DignityPlanIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await _dignity_fund(user["user_id"])
    await db.dignity_funds.update_one({"user_id": user["user_id"]}, {"$set": {"plan": body.model_dump()}})
    return clean(await db.dignity_funds.find_one({"user_id": user["user_id"]}, {"_id": 0}))

@api.put("/dignity/beneficiary")
async def dignity_beneficiary(body: DignityBeneficiaryIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await _dignity_fund(user["user_id"])
    ben = body.model_dump()
    if body.type == "proxy" and not body.name:
        proxy = await db.proxy_directives.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if proxy and proxy.get("proxy_full_name"):
            ben["name"] = proxy["proxy_full_name"]
            ben["contact"] = ben.get("contact") or proxy.get("proxy_phone") or proxy.get("proxy_email") or ""
    await db.dignity_funds.update_one({"user_id": user["user_id"]}, {"$set": {"beneficiary": ben}})
    return clean(await db.dignity_funds.find_one({"user_id": user["user_id"]}, {"_id": 0}))

@api.put("/dignity/wishes")
async def dignity_wishes(body: DignityWishesIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    now = datetime.now(timezone.utc)
    doc = {**body.model_dump(), "user_id": user["user_id"], "updated_at": now}
    doc["doc_hash"] = hashlib.sha256(f"{user['did']}|{body.burial_type}|{body.ceremony_music}|{now.date()}".encode()).hexdigest()
    await db.dignity_wishes.update_one({"user_id": user["user_id"]}, {"$set": doc}, upsert=True)
    return clean(await db.dignity_wishes.find_one({"user_id": user["user_id"]}, {"_id": 0}))

class DeathVerifyIn(BaseModel):
    death_certificate_number: str
    registry_country: str = "SK"

@api.post("/dignity/verify-death")
async def dignity_verify_death(body: DeathVerifyIn, authorization: Optional[str] = Header(None)):
    """SIMULATED state registry check — production hook point for official registry API.
    Would be called by the proxy/family with the official death certificate number."""
    user = await get_current_user(authorization)
    cert = body.death_certificate_number.strip()
    if len(cert) < 6:
        raise HTTPException(400, "Invalid death certificate number format")
    await _dignity_fund(user["user_id"])
    verification = {
        "verified": True,
        "simulated": True,
        "certificate_number": cert,
        "registry_country": body.registry_country.upper(),
        "verified_at": datetime.now(timezone.utc),
    }
    await db.dignity_funds.update_one({"user_id": user["user_id"]}, {"$set": {"death_verified": True, "verification": verification}})
    await _aml_ledger_append(user["user_id"], "death_verification", {"cert": cert, "country": body.registry_country.upper(), "simulated": True})
    return clean({**verification})

@api.post("/dignity/release")
async def dignity_release(authorization: Optional[str] = Header(None)):
    """Conditional release — funds stay locked until official death verification."""
    user = await get_current_user(authorization)
    fund = await _dignity_fund(user["user_id"])
    if fund.get("status") == "released":
        raise HTTPException(400, "Already released")
    if not fund.get("death_verified"):
        raise HTTPException(403, "locked: Funds are locked until official death verification is confirmed")
    ben = fund.get("beneficiary")
    if not ben or not ben.get("name"):
        proxy = await db.proxy_directives.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if proxy and proxy.get("proxy_full_name"):
            ben = {"type": "proxy", "name": proxy["proxy_full_name"], "contact": proxy.get("proxy_phone", "")}
    if not ben or not ben.get("name"):
        raise HTTPException(400, "No beneficiary designated (set a proxy or funeral director)")
    amount = float(fund.get("balance") or 0)
    now = datetime.now(timezone.utc)
    await db.dignity_funds.update_one({"user_id": user["user_id"]}, {"$set": {
        "status": "released", "released_at": now, "released_to": ben, "released_amount": amount, "balance": 0.0,
    }})
    ledger = await _aml_ledger_append(user["user_id"], "dignity_release", {"amount": amount, "to": ben.get("name"), "type": ben.get("type")})
    try:
        await send_push(recipients=[user["user_id"]], data={
            "title": "🕊 FINAL DIGNITY", "message": f"Fund of {amount:.0f} {fund.get('currency','EUR')} released to: {ben.get('name')}", "action_url": "/dignity",
        })
    except Exception as e:
        logger.warning(f"push failed: {e}")
    return {"released": True, "amount": amount, "to": ben, "ledger_hash": ledger, "mocked": True}


# --------- BIOMETRIC WILL CONFIRMATION (Legacy) ---------

@api.post("/legal/testament/biometric")
async def biometric_will_upload(file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(400, "Empty file")
    if len(data) > 50 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 50MB)")
    ctype = file.content_type or "application/octet-stream"
    if not (ctype.startswith("audio/") or ctype.startswith("video/")):
        raise HTTPException(400, "Only audio or video statements are accepted")
    file_hash = hashlib.sha256(data).hexdigest()
    rec_id = uuid.uuid4().hex
    ext = (file.filename or "").split(".")[-1].lower() if "." in (file.filename or "") else ("mp4" if ctype.startswith("video/") else "m4a")
    path = f"{APP_NAME}/biometric/{user['user_id']}/{rec_id}.{ext}"
    try:
        await run_in_threadpool(put_object_sync, path, data, ctype)
    except Exception as e:
        logger.error(f"biometric upload failed: {e}")
        raise HTTPException(502, "Storage upload failed")
    # Tamper-evident notarization on the hash-chain ledger (blockchain simulation)
    ledger_hash = await _aml_ledger_append(user["user_id"], "biometric_will", {"sha256": file_hash, "media": ctype, "size": len(data), "did": user["did"]})
    now = datetime.now(timezone.utc)
    rec = {
        "user_id": user["user_id"], "rec_id": rec_id, "media_type": ctype,
        "file_name": file.filename or f"{rec_id}.{ext}", "size": len(data),
        "sha256": file_hash, "storage_path": path, "ledger_hash": ledger_hash,
        "did": user["did"], "recorded_at": now.isoformat(),
    }
    await db.biometric_wills.update_one({"user_id": user["user_id"]}, {"$set": rec}, upsert=True)
    await db.legal_testaments.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"biometric_hash": file_hash, "biometric_ledger_hash": ledger_hash, "biometric_at": now.isoformat()}},
    )
    return clean(rec)

@api.get("/legal/testament/biometric")
async def biometric_will_get(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return await db.biometric_wills.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}

@api.get("/legal/testament/biometric/file")
async def biometric_will_file(token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await _auth_pdf(authorization, token)
    rec = await db.biometric_wills.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "No biometric statement recorded")
    try:
        content, ctype = await run_in_threadpool(get_object_sync, rec["storage_path"])
    except Exception as e:
        raise HTTPException(502, f"Storage read failed: {e}")
    return Response(content=content, media_type=ctype)

@api.delete("/legal/testament/biometric")
async def biometric_will_delete(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.biometric_wills.delete_one({"user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    await db.legal_testaments.update_one({"user_id": user["user_id"]}, {"$unset": {"biometric_hash": "", "biometric_ledger_hash": "", "biometric_at": ""}})
    return {"ok": True}


# --------- DIGITAL EXECUTOR — Digital Legacy checklist + subscription liquidator ---------
LEGACY_CHECKLIST_TEMPLATE = [
    {"item_id": "fin-accounts", "cat": "financial", "title": "List of bank accounts and access details for the notary"},
    {"item_id": "fin-insurance", "cat": "financial", "title": "Insurance policies (life, accident, property) in one place"},
    {"item_id": "fin-pension", "cat": "financial", "title": "Pension savings (2nd/3rd pillar) — designated beneficiary"},
    {"item_id": "fin-crypto", "cat": "financial", "title": "Crypto wallets: seed phrases in a safe / at the notary (NOT on the phone)"},
    {"item_id": "fin-debts", "cat": "financial", "title": "List of debts and liabilities (so heirs face no surprises)"},
    {"item_id": "soc-google", "cat": "social", "title": "Google Inactive Account Manager configured"},
    {"item_id": "soc-facebook", "cat": "social", "title": "Facebook/Instagram: memorialization contact chosen"},
    {"item_id": "soc-email", "cat": "social", "title": "Access to the primary e-mail for the executor of the will"},
    {"item_id": "soc-photos", "cat": "social", "title": "Family photos and videos: export/backup for the family"},
    {"item_id": "prop-deeds", "cat": "property", "title": "Title deeds / lease agreements — copies in the vault"},
    {"item_id": "prop-vehicle", "cat": "property", "title": "Vehicle / boat: registration papers + keys (storage location)"},
    {"item_id": "prop-keys", "cat": "property", "title": "Physical keys and codes (house, mailbox, safe) — who holds them"},
    {"item_id": "dig-passwords", "cat": "digital", "title": "Password manager: emergency access for a trusted person"},
    {"item_id": "dig-cloud", "cat": "digital", "title": "Cloud storage (Drive/iCloud): handover plan"},
    {"item_id": "dig-domains", "cat": "digital", "title": "Domains and websites: renewal/transfer secured"},
    {"item_id": "dig-subs", "cat": "digital", "title": "Subscriptions: list in the Liquidator below (auto-cancel)"},
]
CHECKLIST_CATS = {"financial": "FINANCES", "social": "SOCIAL MEDIA", "property": "PROPERTY", "digital": "DIGITAL WORLD"}

@api.get("/legacy/checklist")
async def legacy_checklist(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    states = await db.legacy_checklist.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(100)
    smap = {s["item_id"]: s for s in states}
    items = [{**it, "checked": bool(smap.get(it["item_id"], {}).get("checked"))} for it in LEGACY_CHECKLIST_TEMPLATE]
    done = sum(1 for i in items if i["checked"])
    return {"items": items, "categories": CHECKLIST_CATS,
            "progress": {"done": done, "total": len(items), "pct": round(done / len(items) * 100)}}

class ChecklistIn(BaseModel):
    checked: bool

@api.put("/legacy/checklist/{item_id}")
async def legacy_checklist_set(item_id: str, body: ChecklistIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if item_id not in {i["item_id"] for i in LEGACY_CHECKLIST_TEMPLATE}:
        raise HTTPException(404, "Unknown checklist item")
    await db.legacy_checklist.update_one(
        {"user_id": user["user_id"], "item_id": item_id},
        {"$set": {"checked": body.checked, "updated_at": datetime.now(timezone.utc)}}, upsert=True)
    return {"item_id": item_id, "checked": body.checked}

SUB_ACTIONS = ["cancel", "transfer", "memorialize"]

class SubscriptionIn(BaseModel):
    name: str
    cost_monthly: float = 0.0
    currency: str = "EUR"
    action: str = "cancel"

@api.get("/legacy/subscriptions")
async def legacy_subscriptions(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    subs = await db.legacy_subscriptions.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)
    saving = round(sum(s.get("cost_monthly", 0) for s in subs if s.get("action") == "cancel"), 2)
    return {"subscriptions": subs, "monthly_liquidation_saving": saving,
            "note": "The Liquidator runs when the digital will is executed — the executor/notary receives the instructions."}

@api.post("/legacy/subscriptions")
async def legacy_subscription_add(body: SubscriptionIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if body.action not in SUB_ACTIONS:
        raise HTTPException(400, f"action must be one of {SUB_ACTIONS}")
    sub = {"sub_id": uuid.uuid4().hex, "user_id": user["user_id"], "name": body.name.strip()[:80],
           "cost_monthly": round(body.cost_monthly, 2), "currency": body.currency.upper()[:4],
           "action": body.action, "created_at": datetime.now(timezone.utc)}
    await db.legacy_subscriptions.insert_one(sub.copy())
    return clean(sub)

@api.delete("/legacy/subscriptions/{sub_id}")
async def legacy_subscription_delete(sub_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.legacy_subscriptions.delete_one({"sub_id": sub_id, "user_id": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}

