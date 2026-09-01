#!/usr/bin/env python3
"""Language-consistency fix: translate the last Slovak UI strings to English.
Covers the 4 formerly-protected screens + billing.py + subscription.py + health.py prompt."""
import os

M = {
"/app/frontend/app/mosaic.tsx": [
("SIMULOVANÝ L2 · REÁLNE RPC (MOSAIC / BASE / POLYGON) VO PHASE 3", "SIMULATED L2 · REAL RPC (MOSAIC / BASE / POLYGON) IN PHASE 3"),
("val={`aktívny: ${status.bridge_watch?.active || 'Mosaic Chain'}", "val={`active: ${status.bridge_watch?.active || 'Mosaic Chain'}"),
(">POSLEDNÉ ZK-ROLLUP BLOKY<", ">LATEST ZK-ROLLUP BLOCKS<"),
("· gas užívateľ: 0 (treasury)", "· user gas: 0 (treasury)"),
("— zatiaľ žiadne bloky. Ťuknite ANCHOR BLOK alebo počkajte na Swarm.", "— no blocks yet. Tap ANCHOR BLOCK or wait for the Swarm."),
("👵 ZERO-FEE ABSTRAKCIA: babičky nikdy nevidia gas ani kryptomeny — všetko platí treasury nadácie zo Sentinel/Archangel výnosov.", "👵 ZERO-FEE ABSTRACTION: grandmas never see gas or crypto — the foundation treasury pays everything from Sentinel/Archangel revenue."),
],
"/app/frontend/app/barter.tsx": [
("{ health: 'ZDRAVIE', legal: 'PRÁVO', craft: 'REMESLO', care: 'OPATERA', food: 'JEDLO', other: 'INÉ' }", "{ health: 'HEALTH', legal: 'LEGAL', craft: 'CRAFT', care: 'CARE', food: 'FOOD', other: 'OTHER' }"),
("· SLUŽBA ZA SLUŽBU · FUNGUJE AJ BEZ PEŇAZÍ", "· SERVICE FOR SERVICE · WORKS WITHOUT MONEY"),
(">MOJE VÝMENY<", ">MY TRADES<"),
(">OTVORENÉ PONUKY<", ">OPEN OFFERS<"),
(">ZRUŠIŤ<", ">CANCEL<"),
('placeholder="Masáž chrbta 45 min"', 'placeholder="Back massage 45 min"'),
('placeholder="Za čo? (právna pomoc, lieky…)"', 'placeholder="In return for? (legal help, meds…)"'),
],
"/app/frontend/app/arbitrage.tsx": [
("Cezhraničná optimalizácia nákladov na operácie: 🇵🇱 Poľsko · 🇭🇺 Maďarsko · 🇹🇷 Turecko.", "Cross-border surgery cost optimization: 🇵🇱 Poland · 🇭🇺 Hungary · 🇹🇷 Türkiye."),
("Predikcia účtov vrátane cesty, ubytovania a S2 refundácie poisťovne (EÚ 2011/24).", "Bill prediction incl. travel, lodging and S2 insurer refund (EU 2011/24)."),
("PREDIKCIA ÚČTU", "BILL PREDICTION"),
("· čakanie {quote.wait_days_abroad} dní", "· wait {quote.wait_days_abroad} days"),
(">Zákrok</Text>", ">Procedure</Text>"),
(">S2 refundácia (predikcia)</Text>", ">S2 refund (prediction)</Text>"),
("💰 Úspora vs. SK: {quote.saving_vs_sk_eur.toLocaleString('sk-SK')} € · ⏱ čakanie kratšie o {quote.wait_cut_days} dní", "💰 Savings vs. SK: {quote.saving_vs_sk_eur.toLocaleString('sk-SK')} € · ⏱ wait shorter by {quote.wait_cut_days} days"),
("· Ghost Mode kompatibilné (anonymný pacientsky token)", "· Ghost Mode compatible (anonymous patient token)"),
(">ZÁKROKY ({data?.procedures?.length ?? 0})<", ">PROCEDURES ({data?.procedures?.length ?? 0})<"),
("€ · čakanie {p.sk_wait_days} dní", "€ · wait {p.sk_wait_days} days"),
("Najlepšie: {countries[p.best_country]?.flag} −{p.best_saving_eur.toLocaleString('sk-SK')} € · −{p.best_wait_cut_days} dní čakania", "Best: {countries[p.best_country]?.flag} −{p.best_saving_eur.toLocaleString('sk-SK')} € · −{p.best_wait_cut_days} days of waiting"),
(">{ab.wait_days} dní<", ">{ab.wait_days} days<"),
("DNA markery vo vašom suverénnom trezore — on-chain sa ukladá iba hash, surové dáta nikdy neopustia vaše chladné úložisko.", "DNA markers in your sovereign vault — only the hash goes on-chain, raw data never leaves your cold storage."),
("Poskytovateľ: {genomic.provider || '—'}", "Provider: {genomic.provider || '—'}"),
('placeholder="Poskytovateľ sekvenovania (napr. Dante Labs)"', 'placeholder="Sequencing provider (e.g. Dante Labs)"'),
('placeholder="Marker (napr. BRCA1: negatívny)"', 'placeholder="Marker (e.g. BRCA1: negative)"'),
(">ULOŽIŤ<", ">SAVE<"),
],
"/app/frontend/app/subscription.tsx": [
("'SENTINEL (RODINNÝ BALÍK)'", "'SENTINEL (FAMILY PLAN)'"),
("✓ Platba prijatá — ${label} je aktívny! Prémiové funkcie sú odomknuté. 🧾 Doklad o platbe bol uložený do Trezora.", "✓ Payment received — ${label} is active! Premium features unlocked. 🧾 The receipt was saved to your Vault."),
("'Platobná relácia expirovala — skúste znova.'", "'Payment session expired — try again.'"),
("setErr('Platba sa ešte spracováva — o chvíľu obnovte túto obrazovku.')", "setErr('Payment is still processing — refresh this screen in a moment.')"),
("setErr('Platba bola zrušená — nič nebolo účtované.')", "setErr('Payment cancelled — nothing was charged.')"),
("Vitajte v ${tier.toUpperCase()} ✓ (${annual ? 'ročne −20 %' : 'mesačne'}, zaplatené GA-T, spálené ${r.burned}). Platí do ${String(r.effect?.tier_until || '').slice(0, 10)}.", "Welcome to ${tier.toUpperCase()} ✓ (${annual ? 'yearly −20%' : 'monthly'}, paid in GA-T, burned ${r.burned}). Valid until ${String(r.effect?.tier_until || '').slice(0, 10)}."),
("setErr('Nedostatok GA-T — zarobte tokeny cez Proof-of-Help (Family Shield / Angel Gigs), zaplaťte kartou alebo skúste 7-dňový Sentinel trial.')", "setErr('Insufficient GA-T — earn tokens via Proof-of-Help (Family Shield / Angel Gigs), pay by card, or try the 7-day Sentinel trial.')"),
("r.message || 'Predplatné zrušené.'", "r.message || 'Subscription cancelled.'"),
("🎁 Darované: ${giftTier.toUpperCase()} na ${giftDays} dní pre ${r.gift.to_email}.", "🎁 Gifted: ${giftTier.toUpperCase()} for ${giftDays} days to ${r.gift.to_email}."),
("🎁 SENTINEL TRIAL AKTÍVNY do ${String(r.tier_until).slice(0, 10)} — satelit, Bio-Scanner, Tactical Medic aj Longevity odomknuté.", "🎁 SENTINEL TRIAL ACTIVE until ${String(r.tier_until).slice(0, 10)} — satellite, Bio-Scanner, Tactical Medic and Longevity unlocked."),
(">Štyri úrovne suverenity<", ">Four levels of sovereignty<"),
("EUR · CZK · GA-T. Mesačne alebo ročne so zľavou −20 % („Secure Your Future“). Platba kartou (Stripe) alebo GA-T tokenmi.", "EUR · CZK · GA-T. Monthly, or yearly at −20% (“Secure Your Future”). Pay by card (Stripe) or with GA-T tokens."),
("AKTUÁLNY TIER: {data.tier.toUpperCase()}{data.tier_until ? ` · do ${String(data.tier_until).slice(0, 10)}` : ''}", "CURRENT TIER: {data.tier.toUpperCase()}{data.tier_until ? ` · until ${String(data.tier_until).slice(0, 10)}` : ''}"),
(">🎁 7-DŇOVÝ SENTINEL TRIAL ZADARMO<", ">🎁 FREE 7-DAY SENTINEL TRIAL<"),
(">MESAČNE<", ">MONTHLY<"),
(">ROČNE −20 % · SECURE YOUR FUTURE<", ">YEARLY −20% · SECURE YOUR FUTURE<"),
("{active ? '  ✓ AKTÍVNY' : ''}", "{active ? '  ✓ ACTIVE' : ''}"),
(">ZAPLATIŤ {gat} GA-T<", ">PAY {gat} GA-T<"),
(">👨‍👩‍👧‍👦 RODINNÝ BALÍK<", ">👨‍👩‍👧‍👦 FAMILY PLAN<"),
(">SENTINEL PRE CELÚ RODINU<", ">SENTINEL FOR THE WHOLE FAMILY<"),
(">Jeden platca — vy + až 4 strážcovia z rodinného kruhu<", ">One payer — you + up to 4 guardians from your family circle<"),
("['Sentinel funkcie pre 5 ľudí (ušetríte až 66 %)', 'Aktivuje sa automaticky pre prepojených Strážcov', 'Nikdy neznižuje vyšší tier žiadneho člena']", "['Sentinel features for 5 people (save up to 66%)', 'Activates automatically for linked Guardians', 'Never downgrades any member’s higher tier']"),
("PAY-PER-USE: Bio-Scanner {data.payperuse?.bioscan_single} GA-T/sken · IPS export {data.payperuse?.ips_export_single} GA-T · Human Second Opinion podľa sadzby špecialistu (GA-T)", "PAY-PER-USE: Bio-Scanner {data.payperuse?.bioscan_single} GA-T/scan · IPS export {data.payperuse?.ips_export_single} GA-T · Human Second Opinion at the specialist’s rate (GA-T)"),
(">SPRÁVA PREDPLATNÉHO<", ">MANAGE SUBSCRIPTION<"),
(">ÁNO, ZRUŠIŤ HNEĎ<", ">YES, CANCEL NOW<"),
(">PONECHAŤ<", ">KEEP IT<"),
(">ZRUŠIŤ PREDPLATNÉ<", ">CANCEL SUBSCRIPTION<"),
(">👑 Inner Circle — doživotný Archangel, nie je čo rušiť.<", ">👑 Inner Circle — lifetime Archangel, nothing to cancel.<"),
(">Zatiaľ žiadne platby kartou.<", ">No card payments yet.<"),
("{tx.tier === 'family_sentinel' ? 'Rodinný balík (Sentinel)' : String(tx.tier).toUpperCase()} · {tx.billing === 'annual' ? 'ročné' : 'mesačné'}", "{tx.tier === 'family_sentinel' ? 'Family plan (Sentinel)' : String(tx.tier).toUpperCase()} · {tx.billing === 'annual' ? 'yearly' : 'monthly'}"),
("{tx.processed ? 'zaplatené · 🧾 doklad v Trezore' : tx.payment_status}", "{tx.processed ? 'paid · 🧾 receipt in Vault' : tx.payment_status}"),
(">🎁 DAROVAŤ PRÉMIUM (ZAKLADATEĽ)<", ">🎁 GIFT PREMIUM (FOUNDER)<"),
(">Darujte tier komukoľvek podľa e-mailu — zadarmo, okamžite, s notifikáciou.<", ">Gift any tier by e-mail — free, instant, with a notification.<"),
(">{d} DNÍ<", ">{d} DAYS<"),
(">DAROVAŤ {giftTier.toUpperCase()} · {giftDays} DNÍ<", ">GIFT {giftTier.toUpperCase()} · {giftDays} DAYS<"),
("— {String(g.tier).toUpperCase()} · {g.days} dní · {String(g.created_at).slice(0, 10)}", "— {String(g.tier).toUpperCase()} · {g.days} days · {String(g.created_at).slice(0, 10)}"),
],
"/app/backend/routes/billing.py": [
('label = ("Rodinný balík — Sentinel pre celú rodinu" if tx["tier"] == "family_sentinel"', 'label = ("Family plan — Sentinel for the whole family" if tx["tier"] == "family_sentinel"'),
('billing_sk = "ročné predplatné (−20 %)" if tx["billing"] == "annual" else "mesačné predplatné"', 'billing_sk = "annual subscription (−20%)" if tx["billing"] == "annual" else "monthly subscription"'),
('f"Číslo dokladu: {tx[\'session_id\']}\\n"', 'f"Receipt number: {tx[\'session_id\']}\\n"'),
('f"Dátum platby: {now.strftime(\'%d.%m.%Y %H:%M UTC\')}\\n\\n"', 'f"Payment date: {now.strftime(\'%d.%m.%Y %H:%M UTC\')}\\n\\n"'),
('f"Položka: {label} — {billing_sk}\\n"', 'f"Item: {label} — {billing_sk}\\n"'),
('f"Spôsob platby: Platobná karta (Stripe)\\n"', 'f"Payment method: Card (Stripe)\\n"'),
('f"Platnosť do: {tier_until.strftime(\'%d.%m.%Y\')}\\n"', 'f"Valid until: {tier_until.strftime(\'%d.%m.%Y\')}\\n"'),
('f"Členovia rodinného kruhu s aktivovaným Sentinelom: {family_members}\\n"', 'f"Family circle members with Sentinel activated: {family_members}\\n"'),
('"\\nĎakujeme, že chránite seba aj svoju rodinu s Guardian Health & Angel."', '"\\nThank you for protecting yourself and your family with Guardian Health & Angel."'),
('"founder_only: Darovanie prémia môže vykonať iba zakladateľ."', '"founder_only: Only the founder can gift premium."'),
('"user_not_found: Používateľ s týmto e-mailom zatiaľ nemá účet."', '"user_not_found: No account exists for this e-mail yet."'),
('"already_inner_circle: Tento používateľ má doživotný Archangel."', '"already_inner_circle: This user already has lifetime Archangel."'),
('{"title": "🎁 Darček od Guardian Angel",', '{"title": "🎁 A gift from Guardian Angel",'),
('"body": f"Zakladateľ vám daroval {body.tier.upper()} na {days} dní. Prémiové funkcie sú odomknuté!"}', '"body": f"The founder gifted you {body.tier.upper()} for {days} days. Premium features are unlocked!"}'),
],
"/app/backend/routes/subscription.py": [
('"tagline": "Základná suverenita — navždy zadarmo"', '"tagline": "Core sovereignty — free forever"'),
('"features": ["Šifrovaný Trezor (zero-knowledge)", "Emergency QR + SOS",\n                     "Základný Health Timeline", "Verejný Solidarity Hub"]', '"features": ["Encrypted Vault (zero-knowledge)", "Emergency QR + SOS",\n                     "Basic Health Timeline", "Public Solidarity Hub"]'),
('"tagline": "Proaktívna ochrana pre teba aj rodinu"', '"tagline": "Proactive protection for you and your family"'),
('"features": ["Všetko zo Sovereign", "Waitlist Hunter upozornenia",\n                     "AI preklady správ (Jarvis)", "Angel Mode (pády + bezpečnosť)",\n                     "Kompletná Physio-AI encyklopédia"]', '"features": ["Everything in Sovereign", "Waitlist Hunter alerts",\n                     "AI report translations (Jarvis)", "Angel Mode (falls + safety)",\n                     "Complete Physio-AI encyclopedia"]'),
('"tagline": "VIP prežitie — nemocnica vo vrecku"', '"tagline": "VIP survival — a hospital in your pocket"'),
('"features": ["Všetko z Guardian", "🛰️ Satellite Emergency Handshake",', '"features": ["Everything in Guardian", "🛰️ Satellite Emergency Handshake",'),
('"🧬 Longevity Engine + Bio-Age", "Autonómne rezervácie (Autopilot)",', '"🧬 Longevity Engine + Bio-Age", "Autonomous bookings (Autopilot)",'),
('"tagline": "Elitná suverenita — Zero-latency Swarm"', '"tagline": "Elite sovereignty — Zero-latency Swarm"'),
('"features": ["Všetko zo Sentinel", "⚡ Prioritná orchestrácia Swarmu (Zero-latency)",\n                     "👤 Concierge Human Expert — 1 konzultácia/mes.",\n                     "🏛️ DAO governance — hlasovacie práva nadácie",\n                     "White-Label prístup pre rodinné officy"]', '"features": ["Everything in Sentinel", "⚡ Priority Swarm orchestration (Zero-latency)",\n                     "👤 Concierge Human Expert — 1 consultation/mo.",\n                     "🏛️ DAO governance — foundation voting rights",\n                     "White-Label access for family offices"]'),
('f"{min_tier}_required: {feature} je exkluzívny pre {t[\'name\']} tier "', 'f"{min_tier}_required: {feature} is exclusive to the {t[\'name\']} tier "'),
('f"Aktivujte 7-dňový Sentinel trial zadarmo v Subscription."', 'f"Activate the free 7-day Sentinel trial in Subscription."'),
('"billing_note": "Platby kartou: Stripe TEST režim — použite testovaciu kartu 4242 4242 4242 4242. GA-T platby fungujú naplno."', '"billing_note": "Card payments: Stripe TEST mode — use test card 4242 4242 4242 4242. GA-T payments are fully live."'),
('"use_billing_checkout: Platby kartou idú cez POST /api/billing/checkout (Stripe)."', '"use_billing_checkout: Card payments go through POST /api/billing/checkout (Stripe)."'),
('"trial_used: 7-dňový trial už bol využitý. Pokračujte upgradom na Sentinel."', '"trial_used: The 7-day trial was already used. Continue by upgrading to Sentinel."'),
('"already_premium: Už máte Sentinel alebo vyšší tier."', '"already_premium: You already have Sentinel or a higher tier."'),
('"inner_circle_permanent: Doživotný Archangel (Inner Circle) sa nedá zrušiť."', '"inner_circle_permanent: Lifetime Archangel (Inner Circle) cannot be cancelled."'),
('"no_active_subscription: Nemáte aktívne predplatné."', '"no_active_subscription: You have no active subscription."'),
('"message": "Predplatné zrušené — vraciate sa na bezplatný Sovereign. Kedykoľvek sa môžete vrátiť."', '"message": "Subscription cancelled — you are back on the free Sovereign tier. You can return anytime."'),
],
"/app/backend/routes/health.py": [
('f"Structure the response as: 1) Súhrn / Summary in 1-2 sentences, "\n        f"2) Čo to znamená / What this means (bullet list of plain-language points), "\n        f"3) Odporúčania / Recommendations (2-3 practical next steps). "', 'f"Structure the response as: 1) Summary in 1-2 sentences, "\n        f"2) What this means (bullet list of plain-language points), "\n        f"3) Recommendations (2-3 practical next steps) — section headings in {lang}. "'),
],
}

total = 0
for path, pairs in M.items():
    src = open(path, encoding="utf-8").read()
    hits, misses = 0, []
    for old, new in pairs:
        if old in src:
            src = src.replace(old, new); hits += 1
        else:
            misses.append(old[:55])
    open(path, "w", encoding="utf-8").write(src)
    total += hits
    s = f"{os.path.basename(path)}: {hits}/{len(pairs)}"
    if misses: s += " | MISS: " + " ;; ".join(misses)
    print(s)
print("TOTAL:", total)
