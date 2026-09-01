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
    ("0:20-1:20  ·  JARVIS", "/app/jury_assets/jarvis.png", GOLD, [
        "1. Home -> tap the glowing orb",
        "2. Tap orb -> speak: \"What's on my",
        "    health timeline this year?\"",
        "3. Jarvis answers OUT LOUD (Onyx)",
        "4. Tap SONAR -> live web search",
        "5. Hands-free: just say \"JARVIS\"",
        "    -- wake-word opens the mic",
    ]),
    ("1:20-2:20  ·  MAGIC LENS", "/app/jury_assets/lens.png", ACC, [
        "1. Home -> gold MAGIC LENS tile",
        "2. OPEN CAMERA -> aim at any",
        "    medical paper -> shutter",
        "3. AI reads it (~5 s): \"This looks",
        "    like a lab result -- save it?\"",
        "4. YES -- SAVE IT -> OPEN LIFE",
        "    CARD: entry is on the timeline",
    ]),
    ("2:20-3:00  ·  FALL DETECTION", "/app/jury_assets/fall.png", HexColor("#2DD4BF"), [
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
c.drawImage(ImageReader("/app/jury_assets/home.png"), hx, STRIP_TOP - home_h,
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

c.save()
print("PDF written")
