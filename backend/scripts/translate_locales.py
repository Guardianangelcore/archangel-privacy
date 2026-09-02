# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
"""Generate the 13 non-English locale files for the deeper screens from src/locales/en.json.

    cd /app/backend && python scripts/translate_locales.py [--langs sk,cs] [--model gpt-5.4] [--batch 90]

Incremental: only keys that are missing in <lang>.json, or whose English source changed since the
last run (tracked in src/locales/.src_snapshot.json), are (re)translated. Unique English texts are
translated once per language and mapped back to every key that shares them. Uses the Emergent LLM
key through emergentintegrations (same as Jarvis)."""
import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")
from emergentintegrations.llm.chat import LlmChat, UserMessage  # noqa: E402

LOCALES = Path("/app/frontend/src/locales")
SNAPSHOT = LOCALES / ".src_snapshot.json"
LANG_NAMES = {"sk": "Slovak", "cs": "Czech", "de": "German", "pl": "Polish", "hu": "Hungarian", "ru": "Russian",
              "es": "Spanish", "fr": "French", "it": "Italian", "uk": "Ukrainian", "zh": "Simplified Chinese",
              "ja": "Japanese", "ar": "Arabic"}
KEY = os.environ["EMERGENT_LLM_KEY"]

SYSTEM = """You are the localisation engine of "Archangel OS", a premium EU health-guardian mobile app
(AI companion "Jarvis", emergency SOS, medical vault, subscriptions, GA-T loyalty token, family circle).
Translate UI strings from English (a few are Slovak/Czech leftovers — translate those too) into {lang}.
RULES
- Output ONLY a JSON object mapping each input index (string) to its translation. No prose, no markdown.
- Keep placeholders like {{0}} {{1}} {{name}} EXACTLY; keep emoji, arrows, "·", "—", "✓", "⚠", trailing colons and
  leading/trailing separators (e.g. "· burned:" → "· <translation>:").
- Never translate product/brand names: Archangel OS, Jarvis, Guardian, Sentinel, Sovereign, Archangel, GA-T,
  Angel Mode, Life Card, Swarm, Monolith, Vision Forge, Sonar, Stripe, RevenueCat, App Store, Google Play, Perplexity,
  Kč, EUR, CZK, SOS, QR, PDF, GDPR, EU AI Act.
- Preserve casing style: ALL-CAPS labels stay ALL-CAPS (in scripts with case); Title Case stays Title Case.
- Buttons/labels must stay short (about the same length). Tone: warm, respectful, formal "you" (vykanie / Sie / vous / usted).
- Medical wording must be accurate and patient-friendly; keep numbers, units and abbreviations (mmol/l, SpO₂, BP, kg)."""


def load(p: Path) -> dict:
    return json.loads(p.read_text()) if p.exists() else {}


def save(p: Path, d: dict) -> None:
    p.write_text(json.dumps(dict(sorted(d.items())), ensure_ascii=False, indent=2) + "\n")


def parse_json(text: str) -> dict:
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.S)
    try:
        return json.loads(t)
    except ValueError:
        i, j = t.find("{"), t.rfind("}")
        return json.loads(t[i:j + 1])


async def translate_batch(lang: str, texts: list, model: str, attempt: int = 0) -> dict:
    payload = {str(i): s for i, s in enumerate(texts)}
    chat = LlmChat(api_key=KEY, session_id=f"i18n-{lang}-{os.urandom(3).hex()}",
                   system_message=SYSTEM.format(lang=LANG_NAMES[lang])).with_model("openai", model)
    try:
        reply = await chat.send_message(UserMessage(text=json.dumps(payload, ensure_ascii=False)))
        out = parse_json(str(reply))
        good = {texts[int(k)]: str(v) for k, v in out.items() if k.isdigit() and int(k) < len(texts) and str(v).strip()}
        # placeholder integrity check — fall back to English for broken items (re-translated next run)
        for src, tr in list(good.items()):
            if sorted(re.findall(r"\{\w+\}", src)) != sorted(re.findall(r"\{\w+\}", tr)):
                del good[src]
        return good
    except Exception as e:  # noqa: BLE001
        if attempt < 2:
            await asyncio.sleep(3 * (attempt + 1))
            return await translate_batch(lang, texts, model, attempt + 1)
        print(f"  ! {lang}: batch failed: {e}", flush=True)
        return {}


async def do_lang(lang: str, en: dict, snapshot: dict, model: str, batch: int, sem: asyncio.Semaphore) -> None:
    path = LOCALES / f"{lang}.json"
    cur = load(path)
    todo_keys = [k for k, v in en.items() if k not in cur or snapshot.get(k) != v]
    texts = sorted({en[k] for k in todo_keys})
    if not texts:
        print(f"= {lang}: up to date ({len(cur)} keys)", flush=True)
        return
    print(f"> {lang}: {len(todo_keys)} keys / {len(texts)} unique texts in {-(-len(texts)//batch)} batches", flush=True)
    done: dict = {}

    async def run(chunk):
        async with sem:
            done.update(await translate_batch(lang, chunk, model))
            print(f"  {lang}: {len(done)}/{len(texts)}", flush=True)

    await asyncio.gather(*(run(texts[i:i + batch]) for i in range(0, len(texts), batch)))
    for k in todo_keys:
        if en[k] in done:
            cur[k] = done[en[k]]
    save(path, cur)
    print(f"✔ {lang}: {len(cur)} keys written ({len(texts) - len(done)} texts still missing)", flush=True)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", default=",".join(LANG_NAMES))
    ap.add_argument("--model", default="gpt-5.4")
    ap.add_argument("--batch", type=int, default=90)
    ap.add_argument("--parallel", type=int, default=6)
    a = ap.parse_args()
    en = load(LOCALES / "en.json")
    snapshot = load(SNAPSHOT)
    sem = asyncio.Semaphore(a.parallel)
    langs = [l.strip() for l in a.langs.split(",") if l.strip() in LANG_NAMES]
    await asyncio.gather(*(do_lang(l, en, snapshot, a.model, a.batch, sem) for l in langs))
    # snapshot = English source as of this run (keys fully translated in ALL requested langs)
    complete = {k: v for k, v in en.items() if all(k in load(LOCALES / f"{l}.json") for l in langs)}
    if set(langs) == set(LANG_NAMES):
        save(SNAPSHOT, complete)
    print("done", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
