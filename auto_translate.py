#!/usr/bin/env python3
"""Auto-translate hardcoded Slovak string literals in backend .py files to English.
Uses tokenize for exact literal extraction and GPT for translation, then exact replace + py_compile check."""
import asyncio, io, json, os, py_compile, re, sys, tokenize
import requests

KEY = [l.split("=", 1)[1].strip() for l in open("/app/backend/.env") if l.startswith("PERPLEXITY_API_KEY")][0]
SK = re.compile(r"[čďľĺňŕšťžôČĎĽĹŇŔŠŤŽÔäÄáéíóúýÁÉÍÓÚÝ]")

# second pass: whitelist of files that still contain hardcoded Slovak sentences
ONLY = {"medic.py", "swarm.py", "seal.py", "arbitrage.py", "healing.py", "neural.py",
        "interactions.py", "enviro.py", "streaks.py", "longevity.py", "recovery_suite.py",
        "paramedic.py", "family.py", "clinic_sync.py", "globalnet.py", "mosaic.py",
        "lens.py", "demo.py"}

def extract(path):
    src = open(path, encoding="utf-8").read()
    lits = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.STRING and SK.search(tok.string):
            if tok.string not in lits:
                lits.append(tok.string)
    return src, lits

SYSTEM = (
    "You translate Slovak text inside Python string literals to natural English. "
    "Input: JSON array of Python string literals (with quotes/prefixes exactly as in source). "
    "Output: ONLY a JSON array of the same length, each element the translated Python literal. "
    "RULES: keep the exact same quote style and string prefix (f, r, etc); preserve ALL "
    "placeholders like {x} and format specs untouched; preserve escape sequences (\\n), emoji, "
    "numbers, units, punctuation style; keep proper nouns, legal citations, product names "
    "(Jarvis, Guardian, Sentinel, GA-T); translate Trezor as Vault, "
    "'Karta života' as 'Life Card'; use standard ENGLISH forms of geographic names (Londýn->London). "
    "Slovak/Czech city and institution proper nouns like Košice, Dr. Max, Dôvera, Poliklinika Ružinov stay unchanged. "
    "Strings that are already fully English (accents only in proper nouns) MUST be returned unchanged. "
    "Every Slovak/Czech string MUST be translated — echoing Slovak back is an error. "
    "Result must be valid Python literals. Output raw JSON only - no prose, no code fences, no citations.")

async def translate_batch(lits, fname):
    def call():
        r = requests.post("https://api.perplexity.ai/chat/completions",
                          headers={"Authorization": f"Bearer {KEY}"},
                          json={"model": "sonar",
                                "messages": [{"role": "system", "content": SYSTEM},
                                             {"role": "user", "content": json.dumps(lits, ensure_ascii=False)}],
                                "temperature": 0.0, "max_tokens": 8000},
                          timeout=120)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    resp = await asyncio.to_thread(call)
    raw = re.sub(r"^```(json)?|```$", "", str(resp).strip(), flags=re.M).strip()
    out = json.loads(raw)
    assert isinstance(out, list) and len(out) == len(lits), f"len mismatch {len(out)} vs {len(lits)}"
    return out

async def process(path):
    src, lits = extract(path)
    if not lits:
        return 0
    new_src = src
    failed = 0
    for i in range(0, len(lits), 12):
        chunk = lits[i:i+12]
        for attempt in range(3):
            try:
                tr = await translate_batch(chunk, os.path.basename(path) + str(i))
                break
            except Exception as e:
                if attempt == 2:
                    print(f"  CHUNK FAIL {path} @{i}: {e}")
                    tr = None
        if tr is None:
            failed += len(chunk)
            continue
        for old, new in zip(chunk, tr):
            if old != new:
                new_src = new_src.replace(old, new)
    tmp = path + ".tmp"
    open(tmp, "w", encoding="utf-8").write(new_src)
    try:
        py_compile.compile(tmp, doraise=True)
    except Exception as e:
        os.remove(tmp)
        print(f"COMPILE FAIL {path}: {e}")
        return -1
    os.replace(tmp, path)
    return f"{len(lits)} literals" + (f" ({failed} FAILED)" if failed else "")

async def main():
    targets = []
    for root, _, files in os.walk("/app/backend"):
        if "__pycache__" in root or "test" in root:
            continue
        for f in files:
            if f.endswith(".py") and f in ONLY:
                p = os.path.join(root, f)
                if SK.search(open(p, encoding="utf-8").read()):
                    targets.append(p)
    print(f"{len(targets)} files to process")
    for p in sorted(targets):
        n = await process(p)
        print(f"{p}: {n} literals")

asyncio.run(main())
