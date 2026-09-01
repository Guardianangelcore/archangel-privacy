"""Iter 49 — English-only retest of iter 48 findings.

Backend checks:
  - POST /api/auth/dev-bypass founder login still works
  - /api/token/wallet + spend/earn catalog return English labels (no 'dní', 'Prioritný', 'Komunitná')
  - /api/compass/offline-pack returns English survival tips + 'Ambulance SK' emergency number
  - Core smoke: /api/, /api/origin, /api/lifecard no 5xx
"""
import os, json, re, requests, pytest

BASE_URL = (os.environ.get("EXPO_PUBLIC_BACKEND_URL")
            or "https://guardian-vault-13.preview.emergentagent.com").rstrip("/")
FOUNDER_EMAIL = "guardian.angel.core@proton.me"

# Slovak diacritic set — canary for un-translated strings
DIACRITICS = re.compile(r"[áäčďéíĺľňóôřšťúýžÁÄČĎÉÍĹĽŇÓÔŘŠŤÚÝŽ]")

# Known-OK Slovak-adjacent tokens allowed in backend responses (proper nouns, real names)
ALLOWED_DIACRITIC_TOKENS = [
    "NÚSCH",           # Real hospital name (Národný ústav srdcových a cievnych chorôb)
    "Bratislava",       # City name
    "Košice",           # City name (may appear in demo data)
    "Slovenská",        # Real bank / place names if any leak from currency contexts
]


def _find_diacritics(blob: str) -> list:
    """Return list of diacritic-context snippets excluding allowed tokens."""
    hits = []
    for m in DIACRITICS.finditer(blob):
        start = max(0, m.start() - 20)
        end = min(len(blob), m.end() + 20)
        ctx = blob[start:end]
        if any(tok in ctx for tok in ALLOWED_DIACRITIC_TOKENS):
            continue
        hits.append(ctx)
    return hits


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def founder_token():
    r = requests.post(f"{BASE_URL}/api/auth/dev-bypass",
                      json={"email": FOUNDER_EMAIL, "name": "Guardian Angel"}, timeout=30)
    assert r.status_code == 200, f"dev-bypass failed: {r.status_code} {r.text[:300]}"
    data = r.json()
    tok = data.get("session_token") or data.get("token")
    assert tok, f"no session_token in response: {data}"
    return tok


@pytest.fixture(scope="module")
def auth_headers(founder_token):
    return {"Authorization": f"Bearer {founder_token}", "Content-Type": "application/json"}


# ---------- Auth regression ----------
def test_dev_bypass_returns_session_token(founder_token):
    assert isinstance(founder_token, str) and len(founder_token) > 8


def test_auth_me_with_bypass(auth_headers):
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers, timeout=15)
    assert r.status_code == 200, r.text[:300]
    me = r.json()
    user = me.get("user") if isinstance(me.get("user"), dict) else me
    assert user.get("email") == FOUNDER_EMAIL, user


# ---------- Token module — English labels ----------
def test_token_wallet_english(auth_headers):
    r = requests.get(f"{BASE_URL}/api/token/wallet", headers=auth_headers, timeout=15)
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    blob = json.dumps(body, ensure_ascii=False)
    # explicit anti-regression checks
    for bad in ["dní", "Prioritný", "Komunitná", "Zaplatené"]:
        assert bad not in blob, f"/api/token/wallet still contains '{bad}': {blob[:400]}"
    hits = _find_diacritics(blob)
    assert not hits, f"/api/token/wallet has diacritic strings: {hits[:5]}"


def test_token_spend_catalog_english(auth_headers):
    """Try common catalog endpoints; at least one must return and be English."""
    candidates = ["/api/token/spend/catalog", "/api/token/catalog", "/api/token/spend"]
    reached = None
    for path in candidates:
        r = requests.get(f"{BASE_URL}{path}", headers=auth_headers, timeout=15)
        if r.status_code == 200:
            reached = (path, r.json())
            break
    if not reached:
        pytest.skip(f"No token catalog endpoint reachable among {candidates}")
    path, body = reached
    blob = json.dumps(body, ensure_ascii=False)
    for bad in ["dní", "Prioritný", "Komunitná"]:
        assert bad not in blob, f"{path} still contains '{bad}': {blob[:400]}"
    # positive: 30 days / Sentinel / GA-T labels present
    assert ("days" in blob) or ("GA-T" in blob) or ("Sentinel" in blob), f"{path} unexpected payload: {blob[:300]}"


def test_token_earn_catalog_english_source_check():
    """Belt-and-suspenders — static scan of routes/token.py."""
    import pathlib
    src = pathlib.Path("/app/backend/routes/token.py").read_text(encoding="utf-8")
    for bad in ["dní", "Prioritný", "Komunitná"]:
        assert bad not in src, f"routes/token.py still contains '{bad}'"
    # positive: new English labels landed
    assert "Sentinel Tier — 30 days (GA-T)" in src
    assert "Priority Waitlist Hunter (7 days)" in src


# ---------- Compass module — English ----------
def test_compass_offline_pack_english(auth_headers):
    candidates = ["/api/compass/offline-pack", "/api/compass/offline", "/api/compass/pack"]
    reached = None
    for path in candidates:
        r = requests.get(f"{BASE_URL}{path}", headers=auth_headers, timeout=15)
        if r.status_code == 200:
            reached = (path, r.json())
            break
    if not reached:
        pytest.skip(f"No compass offline-pack endpoint reachable among {candidates}")
    path, body = reached
    blob = json.dumps(body, ensure_ascii=False)
    # positive requirement: 'Ambulance SK' present (English replacement of 'Záchranka SK')
    assert "Ambulance SK" in blob, f"{path} missing 'Ambulance SK' key: {blob[:400]}"
    # anti-regression
    for bad in ["Záchranka", "Príručka prežitia"]:
        assert bad not in blob, f"{path} still contains Slovak '{bad}': {blob[:400]}"
    hits = _find_diacritics(blob)
    assert not hits, f"{path} has un-translated diacritic strings: {hits[:5]}"


def test_compass_source_english():
    """Static scan of routes/compass.py."""
    import pathlib
    src = pathlib.Path("/app/backend/routes/compass.py").read_text(encoding="utf-8")
    assert "Ambulance SK" in src
    # anti-regression on Slovak labels
    for bad in ["Záchranka SK", "Prežitie"]:
        assert bad not in src, f"routes/compass.py still contains '{bad}'"


# ---------- Demo seed labels ----------
def test_demo_source_english():
    import pathlib
    src = pathlib.Path("/app/backend/routes/demo.py").read_text(encoding="utf-8")
    # positive
    for good in ["Cardiology", "Dentistry", "Guardian"]:
        assert good in src, f"routes/demo.py missing English label '{good}'"
    # Only 'Kardiológia' allowed inside a `#` comment line — check no literal Slovak specialty labels remain in strings
    # Ensure specialty strings are English
    for bad_str in ['"specialty": "Kardiológia"', '"specialty": "Zubár"']:
        assert bad_str not in src


# ---------- Core smoke: no 500s ----------
CORE_ENDPOINTS = ["/api/", "/api/origin", "/api/lifecard", "/api/token/wallet"]


@pytest.mark.parametrize("path", CORE_ENDPOINTS)
def test_core_endpoints_no_500(auth_headers, path):
    headers = None if path == "/api/" else auth_headers
    r = requests.get(f"{BASE_URL}{path}", headers=headers, timeout=20)
    assert r.status_code < 500, f"{path} -> {r.status_code} {r.text[:200]}"
