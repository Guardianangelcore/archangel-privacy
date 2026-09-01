#!/usr/bin/env python3
"""Build the one-page A4 Jury Cheat Sheet PDF → /app/release_package/JURY_CHEAT_SHEET.pdf"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

W, H = A4  # 595 x 842 pt
GOLD = HexColor("#D4AF37")
BG = HexColor("#0B0B0F")
CARD = HexColor("#16161D")
FG = HexColor("#F2F2F5")
MUT = HexColor("#9C9CA8")
ACC = HexColor("#8B5CF6")

c = canvas.Canvas("/app/release_package/JURY_CHEAT_SHEET.pdf", pagesize=A4)
c.setFillColor(BG); c.rect(0, 0, W, H, stroke=0, fill=1)

# ---------- Header ----------
c.setFillColor(GOLD); c.rect(0, H - 6, W, 6, stroke=0, fill=1)
c.setFillColor(FG); c.setFont("Helvetica-Bold", 21)
c.drawString(36, H - 42, "GUARDIAN HEALTH & ANGEL")
c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 10.5)
c.drawString(36, H - 58, "3-MINUTE LIVE DEMO — JUDGE CHEAT SHEET")
c.setFillColor(MUT); c.setFont("Helvetica", 8)
c.drawRightString(W - 36, H - 42, "Guardian Angel Sovereign Foundation (DAO)")
c.drawRightString(W - 36, H - 54, "Sovereign Survival OS · Expo + FastAPI + Jarvis AI")
c.setFillColor(MUT); c.setFont("Helvetica-Oblique", 8.5)
c.drawString(36, H - 74, 'Login: tap English -> gold button "ENTER AS GUARDIAN ANGEL (FOUNDER)". Everything below runs live.')

# ---------- 3 columns ----------
TOP = H - 92
COL_W = (W - 36 * 2 - 2 * 14) / 3   # 3 cols, 14pt gutters
IMG_H = 300

sections = [
    ("0:20-1:20  ·  JARVIS", "/app/release_package/tools/assets/jarvis.png", GOLD, [
        "1. Home -> tap the glowing orb",
        "2. Tap orb -> speak: \"What's on my",
        "    health timeline this year?\"",
        "3. Jarvis answers OUT LOUD (Onyx)",
        "4. Tap SONAR -> live web search",
        "5. Hands-free: just say \"JARVIS\"",
        "    -- wake-word opens the mic",
    ]),
    ("1:20-2:20  ·  MAGIC LENS", "/app/release_package/tools/assets/lens.png", ACC, [
        "1. Home -> gold MAGIC LENS tile",
        "2. OPEN CAMERA -> aim at any",
        "    medical paper -> shutter",
        "3. AI reads it (~5 s): \"This looks",
        "    like a lab result -- save it?\"",
        "4. YES -- SAVE IT -> OPEN LIFE",
        "    CARD: entry is on the timeline",
    ]),
    ("2:20-3:00  ·  FALL DETECTION", "/app/release_package/tools/assets/fall.png", HexColor("#2DD4BF"), [
        "Prep: Profile -> Fall Guard ON",
        "1. Real physics: 80 ms free-fall",
        "    + 2.5 g impact (no shake trick)",
        "2. Drop phone ~30 cm on cushion",
        "3. Red screen: countdown + voice",
        "    check (\"I am OK!\") + I'M OK",
        "4. No answer -> SOS + GPS to circle",
    ]),
]

c.setFont("Helvetica-Bold", 9.5)
for i, (title, img, accent, steps) in enumerate(sections):
    x = 36 + i * (COL_W + 14)
    # title bar
    c.setFillColor(accent); c.roundRect(x, TOP - 16, COL_W, 16, 3, stroke=0, fill=1)
    c.setFillColor(BG); c.setFont("Helvetica-Bold", 8.6)
    c.drawCentredString(x + COL_W / 2, TOP - 11.5, title)
    # screenshot (phone aspect 390x844)
    img_w = IMG_H * (390 / 844)
    ix = x + (COL_W - img_w) / 2
    c.setStrokeColor(accent); c.setLineWidth(1.2)
    c.roundRect(ix - 3, TOP - 24 - IMG_H - 3, img_w + 6, IMG_H + 6, 6, stroke=1, fill=0)
    c.drawImage(ImageReader(img), ix, TOP - 24 - IMG_H, width=img_w, height=IMG_H)
    # steps card
    sy = TOP - 24 - IMG_H - 16
    card_h = 12 + len(steps) * 11.5 + 6
    c.setFillColor(CARD); c.roundRect(x, sy - card_h, COL_W, card_h, 4, stroke=0, fill=1)
    c.setFillColor(FG); c.setFont("Helvetica", 7.8)
    ty = sy - 14
    for s in steps:
        if s.startswith("Prep:"):
            c.setFillColor(GOLD); c.drawString(x + 8, ty, s); c.setFillColor(FG)
        else:
            c.drawString(x + 8, ty, s)
        ty -= 11.5

# ---------- Home screenshot strip + talking points ----------
STRIP_TOP = TOP - 24 - IMG_H - 16 - 110 - 14
img_w2 = 120 * (390 / 844) * 2.2  # small home shot
home_h = 120
c.setStrokeColor(GOLD); c.setLineWidth(1)
hx = 36
c.roundRect(hx - 2, STRIP_TOP - home_h - 2, home_h * (390 / 844) + 4, home_h + 4, 5, stroke=1, fill=0)
c.drawImage(ImageReader("/app/release_package/tools/assets/home.png"), hx, STRIP_TOP - home_h,
            width=home_h * (390 / 844), height=home_h)
c.setFillColor(MUT); c.setFont("Helvetica", 6.5)
c.drawString(hx, STRIP_TOP - home_h - 12, "HOME — orb + Magic Lens tile")

tx = hx + home_h * (390 / 844) + 18
c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 9)
c.drawString(tx, STRIP_TOP - 12, "WHY IT MATTERS (30-second pitch)")
c.setFillColor(FG); c.setFont("Helvetica", 8)
points = [
    "· Voice-first: seniors never navigate menus — they talk to Jarvis (wake-word, TTS answers, 14 languages).",
    "· One-photo records: Magic Lens turns any medical paper into a plain-language Life Card entry. Zero typing.",
    "· Acts when you can't: accelerometer fall detection -> voice check -> automatic SOS + GPS to the Guardian Circle.",
    "· Sovereign by design: DID-signed documents, zero-knowledge vault, GDPR Art. 9, EU AI Act Art. 50 labelling.",
]
py = STRIP_TOP - 26
for p in points:
    c.drawString(tx, py, p); py -= 12

c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 8.5)
c.drawString(tx, py - 4, "BACKUP PLANS")
c.setFillColor(MUT); c.setFont("Helvetica", 7.6)
c.drawString(tx, py - 15, "Slow Wi-Fi -> typed chat instead of voice · Camera issue -> CHOOSE FROM GALLERY (pre-loaded photo) ·")
c.drawString(tx, py - 25, "Fall demo re-run -> wait 30 s cooldown · Jarvis/Fall need a real phone (Expo Go QR) — web preview shows UI only.")

# ---------- Footer ----------
c.setFillColor(CARD); c.rect(0, 0, W, 26, stroke=0, fill=1)
c.setFillColor(MUT); c.setFont("Helvetica", 6.8)
c.drawString(36, 10, "© 2026 Guardian Angel. All Rights Reserved. Proprietary — competition evaluation only. Proof of Origin: /api/origin.")
c.setFillColor(GOLD)
c.drawRightString(W - 36, 10, "guardian.angel.core@proton.me")

# ============================ PAGE 2 — INVESTOR ONE-PAGER ============================
c.showPage()
c.setFillColor(BG); c.rect(0, 0, W, H, stroke=0, fill=1)
c.setFillColor(GOLD); c.rect(0, H - 6, W, 6, stroke=0, fill=1)
c.setFillColor(FG); c.setFont("Helvetica-Bold", 21)
c.drawString(36, H - 42, "INVESTOR ONE-PAGER")
c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 10.5)
c.drawString(36, H - 58, "FINANCIAL FORECAST 2026-2030 · 22ND-CENTURY ROADMAP")
c.setFillColor(MUT); c.setFont("Helvetica", 8)
c.drawRightString(W - 36, H - 42, "Guardian Angel Sovereign Foundation (DAO)")
c.drawRightString(W - 36, H - 54, "Deterministic tier-mix model — live at /api/founder/toolkit")

# ---- Forecast (mirrors backend routes/founder.py exactly) ----
TIER_MIX = {"guardian": (29.0, 0.80), "sentinel": (149.0, 0.17), "archangel": (499.0, 0.03)}
ARPU = round(sum(p * w for p, w in TIER_MIX.values()), 2)
YEARS = [(2026, 12_000, 0.05, 1.5), (2027, 85_000, 0.06, 2.5), (2028, 420_000, 0.07, 3.5),
         (2029, 1_600_000, 0.08, 4.5), (2030, 5_000_000, 0.09, 5.5)]

def fmt(n):
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.0f}k"
    return str(int(n))

# assumptions strip
ay = H - 84
c.setFillColor(CARD); c.roundRect(36, ay - 40, W - 72, 40, 4, stroke=0, fill=1)
c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 8)
c.drawString(46, ay - 12, "ASSUMPTIONS")
c.setFillColor(FG); c.setFont("Helvetica", 8)
c.drawString(46, ay - 24, f"Blended ARPU €{ARPU}/mo (Guardian €29 · Sentinel €149 · Archangel €499)   ·   Guardian Tax 15% of marketplace GMV")
c.drawString(46, ay - 34, "Gross margin 87%   ·   LTV/CAC 4.8   ·   Churn 2.1%/mo   ·   Paid conversion 5% → 9% (2026 → 2030)")

# forecast table
ty = ay - 56
cols = [(36, "YEAR"), (86, "USERS"), (156, "PAID"), (226, "SUBSCRIPTION MRR"), (330, "GUARDIAN TAX MRR"), (434, "TOTAL MRR"), (500, "ARR")]
c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 7.5)
for x, hcol in cols:
    c.drawString(x + 6, ty - 10, hcol)
ty -= 16
c.setFont("Helvetica", 8.5)
for i, (year, users, conv, gmv) in enumerate(YEARS):
    paid = int(users * conv)
    sub = paid * ARPU
    tax = users * gmv * 0.15
    mrr = sub + tax
    if i % 2 == 0:
        c.setFillColor(CARD); c.rect(36, ty - 14, W - 72, 15, stroke=0, fill=1)
    c.setFillColor(FG)
    c.drawString(42, ty - 10, str(year))
    c.drawString(92, ty - 10, fmt(users))
    c.drawString(162, ty - 10, fmt(paid))
    c.drawString(232, ty - 10, f"EUR {fmt(round(sub))}/mo")
    c.drawString(336, ty - 10, f"EUR {fmt(round(tax))}/mo")
    c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 8.5)
    c.drawString(440, ty - 10, f"EUR {fmt(round(mrr))}")
    c.drawString(506, ty - 10, f"EUR {fmt(round(mrr * 12))}")
    c.setFillColor(FG); c.setFont("Helvetica", 8.5)
    ty -= 15

# revenue bar mini-chart (ARR growth)
ty -= 14
c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 8)
c.drawString(36, ty, "ARR TRAJECTORY")
max_arr = (YEARS[-1][1] * YEARS[-1][3] * 0.15 + int(YEARS[-1][1] * YEARS[-1][2]) * ARPU) * 12
bx = 36
for year, users, conv, gmv in YEARS:
    arr = (int(users * conv) * ARPU + users * gmv * 0.15) * 12
    bw = max(4, (W - 72) * (arr / max_arr) * 0.92)
    ty -= 14
    c.setFillColor(HexColor("#3a3120")); c.roundRect(bx + 40, ty - 2, W - 72 - 44, 9, 2, stroke=0, fill=1)
    c.setFillColor(GOLD); c.roundRect(bx + 40, ty - 2, bw * ((W - 72 - 44) / (W - 72)), 9, 2, stroke=0, fill=1)
    c.setFillColor(MUT); c.setFont("Helvetica", 7)
    c.drawString(bx, ty, str(year))

# ---- Roadmap ----
ROADMAP = [
    ("2026 Q3", "LAUNCH", "Global launch", "iOS/Android builds, UHP pilot SK/CZ — first 50 partner clinics, Investor Demo Mode."),
    ("2027", "RAILS", "Real settlement rails", "Visa Direct / Mastercard Send replace SimulatedRails; cross-border arbitrage fully automated."),
    ("2028", "GRID", "Sentinel Grid goes live", "BLE mesh + satellite nano-packets on real hardware; 1M+ concurrent sensor streams."),
    ("2030", "TWIN", "Certified Bio-Digital Twin", "EU MDR class IIa — simulating treatment BEFORE dosing becomes the standard of care."),
    ("2035", "GBI", "Living currency at national scale", "GA-T Guardian Basic Income — data dividends for millions; sovereign health-data ownership."),
    ("2040", "MESH", "Quantum network", "Post-quantum cryptography (Kyber/Dilithium); Collective Truth ledger as public infrastructure."),
    ("2075", "ECHO", "Cognitive handover", "Legally recognized digital echoes — the Personality Blueprint carries wisdom across generations."),
    ("2100+", "ARCHANGEL", "The 22nd-century standard", "UHP as the default protocol of human health sovereignty — Archangel OS on every device."),
]
ty -= 28
c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 11)
c.drawString(36, ty, "ROADMAP — FROM LAUNCH TO THE 22ND CENTURY")
ty -= 8
era_colors = [GOLD, ACC, HexColor("#2DD4BF"), GOLD, ACC, HexColor("#2DD4BF"), GOLD, ACC]
row_h = 42
for i, (year, era, title, detail) in enumerate(ROADMAP):
    ty -= row_h
    ec = era_colors[i]
    # timeline dot + line
    c.setStrokeColor(HexColor("#2A2A33")); c.setLineWidth(1.4)
    if i < len(ROADMAP) - 1:
        c.line(46, ty + 6, 46, ty - row_h + 20)
    c.setFillColor(ec); c.circle(46, ty + 14, 3.4, stroke=0, fill=1)
    # card
    c.setFillColor(CARD); c.roundRect(60, ty - 8, W - 96, 36, 4, stroke=0, fill=1)
    c.setFillColor(ec); c.setFont("Helvetica-Bold", 8.5)
    c.drawString(70, ty + 16, year)
    c.setFillColor(FG); c.setFont("Helvetica-Bold", 9)
    c.drawString(114, ty + 16, title)
    c.setFillColor(ec); c.setFont("Helvetica-Bold", 6.5)
    c.drawRightString(W - 46, ty + 17, era)
    c.setFillColor(MUT); c.setFont("Helvetica", 7.4)
    c.drawString(70, ty + 4, detail[:118])

# footer page 2
c.setFillColor(CARD); c.rect(0, 0, W, 26, stroke=0, fill=1)
c.setFillColor(MUT); c.setFont("Helvetica", 6.8)
c.drawString(36, 10, "© 2026 Guardian Angel. All Rights Reserved. Forward-looking projections — not investment advice. Live model: /api/founder/toolkit.")
c.setFillColor(GOLD)
c.drawRightString(W - 36, 10, "guardian.angel.core@proton.me")

c.save()
print("PDF written")
